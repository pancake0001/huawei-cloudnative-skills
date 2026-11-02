"""Collect and analyze CCE NodeConfigurationCollection diagnostic results."""

from __future__ import annotations

import json
import os
import re
import secrets
import subprocess
import time
from typing import Any, Dict, Iterable, Optional


_UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
_LABEL_VALUE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9_.-]{0,61}[A-Za-z0-9])?$")
_ERROR_TEXT = re.compile(r"(?:\bfailed\b|\berror\b|\bnot found\b|\bexit status\b|\bunavailable\b)", re.IGNORECASE)
_DNS_NAMESERVER = re.compile(r"(?:^|[;\s])nameserver\s+([^;\s]+)")
_NETWORK_EXACT_BASELINES = {
    "net.netfilter.nf_conntrack_tcp_be_liberal": "1",
    "net.ipv4.tcp_max_tw_buckets": "5000",
    "net.ipv4.tcp_tw_reuse": "2",
    "net.ipv4.ip_local_port_range": "32768-60999",
    "net.ipv4.ip_local_reserved_ports": "3125-3126,3225-3226,4789,5137,8080,9253,9353,10248-10250,10255-10256,20101,20104,20202,20256-20257,28001-28002",
    "net.ipv4.conf.eth0.arp_ignore": "0",
    "net.ipv4.ip_forward": "1",
}
_NETWORK_MINIMUM_BASELINES = {
    "net.core.somaxconn": 32768,
    "net.ipv4.neigh.default.gc_thresh3": 163790,
}


def _isolated_env(explicit_credentials: bool) -> Optional[Dict[str, str]]:
    if not explicit_credentials:
        return None
    return {"PATH": os.environ.get("PATH", ""), "HOME": os.environ.get("HOME", "")}


def _credential_args(ak: Optional[str], sk: Optional[str], token: Optional[str]) -> list[str]:
    args: list[str] = []
    if ak:
        args.append(f"--cli-access-key={ak}")
    if sk:
        args.append(f"--cli-secret-key={sk}")
    if token:
        args.append(f"--cli-security-token={token}")
    return args


def _redact(command: Iterable[str]) -> str:
    hidden = ("--cli-access-key=", "--cli-secret-key=", "--cli-security-token=")
    return " ".join(f"{part.split('=', 1)[0]}=***" if part.startswith(hidden) else part for part in command)


def _run(command: list[str], explicit_credentials: bool, debug_trace: list[Dict[str, Any]], debug: bool, input_text: Optional[str] = None) -> Dict[str, Any]:
    try:
        completed = subprocess.run(command, input=input_text, capture_output=True, text=True, timeout=75, check=False, env=_isolated_env(explicit_credentials))
    except FileNotFoundError:
        return {"success": False, "error": f"{command[0]} was not found in PATH"}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"{command[0]} request timed out"}
    if debug:
        debug_trace.append({"command": _redact(command), "exit_code": completed.returncode, "stdout": (completed.stdout or "").strip()[:2000], "stderr": (completed.stderr or "").strip()[:2000]})
    if completed.returncode:
        return {"success": False, "error": (completed.stderr or completed.stdout or "command failed").strip().replace("\n", " ")[:1000]}
    return {"success": True, "stdout": completed.stdout or ""}


def _run_json(command: list[str], explicit_credentials: bool, trace: list[Dict[str, Any]], debug: bool) -> Dict[str, Any]:
    result = _run(command, explicit_credentials, trace, debug)
    if not result.get("success"):
        return result
    try:
        data = json.loads(result["stdout"])
    except json.JSONDecodeError:
        return {"success": False, "error": "command returned non-JSON output"}
    if isinstance(data, dict) and (data.get("status") == "Failure" or data.get("error_code") or data.get("errorCode")):
        message = data.get("message") or data.get("error_msg") or data.get("errorMessage") or data.get("reason") or "service request failed"
        return {"success": False, "error": str(message)}
    return {"success": True, "data": data}


def _hcloud(region: str, operation: str, ak: Optional[str], sk: Optional[str], token: Optional[str], *arguments: str) -> list[str]:
    return ["hcloud", "CCE", operation, f"--cli-region={region}", "--cli-output=json", "--cli-connect-timeout=10", "--cli-read-timeout=60", *_credential_args(ak, sk, token), *arguments]


def _resolve_cluster(region: str, cluster_id: str, ak: Optional[str], sk: Optional[str], token: Optional[str], explicit_credentials: bool, trace: list[Dict[str, Any]], debug: bool) -> Dict[str, Any]:
    if _UUID.fullmatch(cluster_id):
        result = _run_json(_hcloud(region, "ShowCluster", ak, sk, token, f"--cluster_id={cluster_id}"), explicit_credentials, trace, debug)
        if not result.get("success"):
            return {"success": False, "error": f"Unable to verify CCE cluster_id '{cluster_id}': {result.get('error')}"}
        return {"success": True, "cluster_id": cluster_id, "cluster_name": (result["data"].get("metadata") or {}).get("name")}
    listed = _run_json(_hcloud(region, "ListClusters", ak, sk, token), explicit_credentials, trace, debug)
    if not listed.get("success"):
        return {"success": False, "error": f"Unable to resolve CCE cluster name '{cluster_id}': {listed.get('error')}"}
    matches = [item for item in (listed["data"].get("items") or []) if (item.get("metadata") or {}).get("name") == cluster_id]
    if len(matches) != 1:
        return {"success": False, "error": f"cluster_id '{cluster_id}' {'matched multiple clusters' if matches else 'was not found'}; provide a valid cluster UUID or exact unique cluster name"}
    resolved_id = (matches[0].get("metadata") or {}).get("uid")
    verified = _run_json(_hcloud(region, "ShowCluster", ak, sk, token, f"--cluster_id={resolved_id}"), explicit_credentials, trace, debug)
    if not verified.get("success"):
        return {"success": False, "error": f"Unable to verify CCE cluster resolved from '{cluster_id}': {verified.get('error')}"}
    return {"success": True, "cluster_id": resolved_id, "cluster_name": (verified["data"].get("metadata") or {}).get("name"), "resolved_from_name": cluster_id}


def _project_id(region: str, project_id: Optional[str], ak: Optional[str], sk: Optional[str], token: Optional[str], explicit_credentials: bool, trace: list[Dict[str, Any]], debug: bool) -> Optional[str]:
    if project_id:
        return project_id
    if not explicit_credentials and os.environ.get("HW_PROJECT_ID"):
        return os.environ["HW_PROJECT_ID"]
    command = ["hcloud", "IAM", "KeystoneListProjects", f"--cli-region={region}", f"--name={region}", "--cli-output=json", "--cli-connect-timeout=10", "--cli-read-timeout=60", *_credential_args(ak, sk, token)]
    result = _run_json(command, explicit_credentials, trace, debug)
    if not result.get("success"):
        return None
    for project in (result["data"].get("projects") or []):
        if project.get("name") == region and project.get("id"):
            return project["id"]
    return None


def _kubectl(region: str, cluster_id: str, project_id: Optional[str], ak: Optional[str], sk: Optional[str], token: Optional[str], *arguments: str) -> list[str]:
    command = ["kubectl", "cce", f"--cluster-id={cluster_id}", f"--region={region}"]
    if project_id:
        command.append(f"--project-id={project_id}")
    command.extend(_credential_args(ak, sk, token))
    return [*command, *arguments]


def _kubectl_json(command: list[str], explicit_credentials: bool, trace: list[Dict[str, Any]], debug: bool) -> Dict[str, Any]:
    result = _run_json(command, explicit_credentials, trace, debug)
    if result.get("success") or "x509" not in (result.get("error") or "").lower():
        return result
    retry = [command[0], command[1], "--cce-insecure-upstream-tls=true", *command[2:]]
    return _run_json(retry, explicit_credentials, trace, debug)


def _safe_json(value: Any, default: Any) -> Any:
    if not isinstance(value, str) or not value.strip():
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def _number(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _severity(value: float, warning: int, critical: int) -> Optional[str]:
    if value >= critical:
        return "critical"
    if value >= warning:
        return "warning"
    return None


def _finding(identifier: str, severity: str, summary: str, evidence: Dict[str, Any], recommendation: str) -> Dict[str, Any]:
    return {"id": identifier, "severity": severity, "summary": summary, "evidence": evidence, "recommendation": recommendation}


def _baseline_check(identifier: str, category: str, source: str, expected: Any, comparison: str, actual: Any, state: str, severity: str, message: str) -> Dict[str, Any]:
    return {
        "id": identifier,
        "category": category,
        "source": source,
        "expected": expected,
        "comparison": comparison,
        "actual": actual,
        "state": state,
        "severity": severity,
        "message": message,
    }


def _baseline_summary(checks: list[Dict[str, Any]]) -> Dict[str, int]:
    summary = {"total": len(checks), "passed": 0, "warning": 0, "critical": 0, "unavailable": 0, "informational": 0}
    for check in checks:
        state = check.get("state")
        if state in summary:
            summary[state] += 1
    return summary


def _usage_baseline_check(identifier: str, source: str, actual: Optional[float], warning: int, critical: int) -> Dict[str, Any]:
    if actual is None:
        return _baseline_check(identifier, "resource", source, f"<{warning}%", "<", None, "unavailable", "none", f"{source} was not collected")
    severity = _severity(actual, warning, critical)
    if severity:
        return _baseline_check(identifier, "resource", source, f"<{warning}%", "<", actual, severity, severity, f"{source} is {actual:.2f}%")
    return _baseline_check(identifier, "resource", source, f"<{warning}%", "<", actual, "passed", "none", f"{source} is within the baseline")


def _network_baseline_checks(network: Dict[str, Any], findings: list[Dict[str, Any]], data_gaps: list[str]) -> list[Dict[str, Any]]:
    """Compare only the network values returned by NodeConfigurationCollection."""
    checks: list[Dict[str, Any]] = []
    for key, expected in _NETWORK_EXACT_BASELINES.items():
        actual = network.get(key)
        if actual is None:
            data_gaps.append(f"Network baseline value {key} was not collected")
            checks.append(_baseline_check(f"network:{key}", "network", key, expected, "exact", None, "unavailable", "none", f"{key} was not collected"))
        elif str(actual) == expected:
            checks.append(_baseline_check(f"network:{key}", "network", key, expected, "exact", str(actual), "passed", "none", f"{key} matches the baseline"))
        else:
            checks.append(_baseline_check(f"network:{key}", "network", key, expected, "exact", str(actual), "warning", "warning", f"{key} does not match the baseline"))
            findings.append(_finding("NETWORK_BASELINE_MISMATCH", "warning", f"{key} is {actual!s}, expected {expected}", {"parameter": key, "actual": str(actual), "expected": expected}, "Review the CCE node network baseline before changing the parameter."))
    for key, expected in _NETWORK_MINIMUM_BASELINES.items():
        actual = _number(network.get(key))
        if actual is None:
            data_gaps.append(f"Network baseline value {key} was not collected")
            checks.append(_baseline_check(f"network:{key}", "network", key, expected, ">=", None, "unavailable", "none", f"{key} was not collected"))
        elif actual >= expected:
            checks.append(_baseline_check(f"network:{key}", "network", key, expected, ">=", actual, "passed", "none", f"{key} meets the minimum baseline"))
        else:
            checks.append(_baseline_check(f"network:{key}", "network", key, expected, ">=", actual, "warning", "warning", f"{key} is below the minimum baseline"))
            findings.append(_finding("NETWORK_BASELINE_MISMATCH", "warning", f"{key} is {actual:g}, below baseline {expected}", {"parameter": key, "actual": actual, "minimum": expected}, "Review the CCE node network baseline before changing the parameter."))

    nameservers = _DNS_NAMESERVER.findall(str(network.get("DNS") or ""))
    invalid_nameservers = [address for address in nameservers if not address.startswith("100.125.")]
    if not nameservers:
        data_gaps.append("No DNS nameserver was collected")
        checks.append(_baseline_check("network:dns", "network", "DNS", "100.125.0.0/16", "all nameservers in CIDR", [], "unavailable", "none", "No DNS nameserver was collected"))
    elif invalid_nameservers:
        checks.append(_baseline_check("network:dns", "network", "DNS", "100.125.0.0/16", "all nameservers in CIDR", nameservers, "warning", "warning", "One or more DNS nameservers are outside the baseline CIDR"))
        findings.append(_finding("DNS_BASELINE_MISMATCH", "warning", "One or more DNS nameservers are outside 100.125.0.0/16", {"nameservers": nameservers, "outside_baseline": invalid_nameservers}, "Verify the node resolver configuration against the CCE network baseline."))
    else:
        checks.append(_baseline_check("network:dns", "network", "DNS", "100.125.0.0/16", "all nameservers in CIDR", nameservers, "passed", "none", "All DNS nameservers match the baseline CIDR"))
    for key, expected in {"net.ipv4.neigh.default.gc_thresh1": "0", "net.ipv4.neigh.default.gc_thresh2": "4096"}.items():
        checks.append(_baseline_check(f"network:{key}", "network", key, expected, "informational", network.get(key), "informational", "none", f"{key} is reported for reference only"))
    return checks


def _analyze(resource: Dict[str, Any], warning: int, critical: int) -> Dict[str, Any]:
    findings: list[Dict[str, Any]] = []
    data_gaps: list[str] = []
    baseline_checks: list[Dict[str, Any]] = []
    result = resource.get("result") or {}
    agent = result.get("agentConfiguration") or {}
    os_configuration = result.get("osConfiguration") or {}
    status = resource.get("status") or {}

    components = _safe_json(agent.get("componentStatus"), [])
    if not isinstance(components, list):
        data_gaps.append("agentConfiguration.componentStatus is not valid JSON")
        components = []
    unhealthy = [component for component in components if component.get("healthy") is not True]
    if components:
        for component in components:
            name = str(component.get("name") or "unknown")
            healthy = component.get("healthy")
            passed = healthy is True
            baseline_checks.append(_baseline_check(f"component:{name}", "agent", f"componentStatus[{name}].healthy", True, "exact", healthy, "passed" if passed else "critical", "none" if passed else "critical", f"Component {name} is {'healthy' if passed else 'not healthy'}"))
    else:
        baseline_checks.append(_baseline_check("component:all", "agent", "componentStatus[*].healthy", True, "all exact", None, "unavailable", "none", "No component health records were collected"))
    if unhealthy:
        findings.append(_finding("AGENT_COMPONENT_UNHEALTHY", "critical", "One or more node agent components are unhealthy", {"components": unhealthy}, "Inspect the affected component logs and service state on the node."))
    if not components:
        data_gaps.append("No component health records were collected")

    consistency = _safe_json(agent.get("configurationConsistent"), [])
    if isinstance(consistency, list):
        baseline_checks.append(_baseline_check("agent:configuration_consistency", "agent", "configurationConsistent", [], "empty", consistency, "passed" if not consistency else "warning", "none" if not consistency else "warning", "All component configurations are consistent" if not consistency else "Configuration differences were reported"))
    else:
        data_gaps.append("agentConfiguration.configurationConsistent is not valid JSON")
        baseline_checks.append(_baseline_check("agent:configuration_consistency", "agent", "configurationConsistent", [], "empty", None, "unavailable", "none", "Configuration consistency data is not valid JSON"))
    if isinstance(consistency, list) and consistency:
        findings.append(_finding("CONFIGURATION_INCONSISTENCY", "warning", "The collector reported configuration consistency findings", {"items": consistency}, "Review the reported component configuration against the CCE node baseline before changing it."))

    dependencies = _safe_json(agent.get("criticalDependency"), {})
    if isinstance(dependencies, dict):
        failures = {key: value for key, value in dependencies.items() if isinstance(value, str) and _ERROR_TEXT.search(value)}
        if dependencies:
            for key, value in dependencies.items():
                failed = isinstance(value, str) and _ERROR_TEXT.search(value) is not None
                baseline_checks.append(_baseline_check(f"dependency:{key}", "dependency", f"criticalDependency.{key}", "no error", "no error markers", value, "warning" if failed else "passed", "warning" if failed else "none", f"Dependency {key} {'reported an error' if failed else 'passed'}"))
        else:
            baseline_checks.append(_baseline_check("dependency:all", "dependency", "criticalDependency", "no error", "no error markers", {}, "unavailable", "none", "No critical dependency records were collected"))
        if failures:
            findings.append(_finding("CRITICAL_DEPENDENCY_CHECK_FAILED", "warning", "One or more critical dependency checks reported an error", {"dependencies": failures}, "Restore the failed dependency check, then run a new configuration collection."))
    elif agent.get("criticalDependency"):
        data_gaps.append("agentConfiguration.criticalDependency is not valid JSON")

    base = _safe_json(os_configuration.get("baseResourceConfiguration"), {})
    resources: Dict[str, Any] = {}
    if isinstance(base, dict):
        for key in ("cpu", "memory"):
            sample = _safe_json(base.get(key), {})
            ratio = _number(sample.get("usageRatio") if isinstance(sample, dict) else None)
            resources[key] = sample
            baseline_checks.append(_usage_baseline_check(f"resource:{key}", f"baseResourceConfiguration.{key}.usageRatio", ratio, warning, critical))
            if ratio is not None and (severity := _severity(ratio, warning, critical)):
                findings.append(_finding(f"{key.upper()}_USAGE_HIGH", severity, f"{key.upper()} usage is {ratio:.2f}%", {key: sample}, "Check node workloads and capacity before the resource reaches exhaustion."))
        disks = _safe_json(base.get("disk"), [])
        resources["disk"] = disks
        if isinstance(disks, list):
            for disk in disks:
                ratio = _number(disk.get("usageRatio") if isinstance(disk, dict) else None)
                disk_name = str(disk.get("deviceName") or "unknown") if isinstance(disk, dict) else "unknown"
                baseline_checks.append(_usage_baseline_check(f"resource:disk:{disk_name}", f"baseResourceConfiguration.disk[{disk_name}].usageRatio", ratio, warning, critical))
                if ratio is not None and (severity := _severity(ratio, warning, critical)):
                    findings.append(_finding("DISK_USAGE_HIGH", severity, f"Disk {disk.get('deviceName', 'unknown')} usage is {ratio:.2f}%", {"disk": disk}, "Reclaim disk space or expand the affected node volume."))
    else:
        data_gaps.append("No base resource configuration was collected")
        for key in ("cpu", "memory", "disk"):
            baseline_checks.append(_usage_baseline_check(f"resource:{key}", f"baseResourceConfiguration.{key}.usageRatio", None, warning, critical))

    network = _safe_json(os_configuration.get("networkConfiguration"), {})
    network_summary: Dict[str, Any] = {}
    if isinstance(network, dict):
        count, maximum = _number(network.get("net.netfilter.nf_conntrack_count")), _number(network.get("net.netfilter.nf_conntrack_max"))
        if count is not None and maximum and maximum > 0:
            ratio = count / maximum * 100
            network_summary["conntrack_usage_percent"] = round(ratio, 2)
            baseline_checks.append(_usage_baseline_check("network:conntrack_utilization", "net.netfilter.nf_conntrack_count / net.netfilter.nf_conntrack_max", ratio, warning, critical))
            if severity := _severity(ratio, warning, critical):
                findings.append(_finding("CONNTRACK_USAGE_HIGH", severity, f"Conntrack table usage is {ratio:.2f}%", {"count": count, "max": maximum}, "Reduce connection churn or raise conntrack capacity after assessing node memory impact."))
        network_summary["dns"] = network.get("DNS")
        network_summary["tcp_connections"] = _safe_json(network.get("tcpConnections"), {})
        network_checks = _network_baseline_checks(network, findings, data_gaps)
        baseline_checks.extend(network_checks)
        network_summary["baseline_checks"] = network_checks
    else:
        data_gaps.append("No network configuration was collected")
        baseline_checks.append(_usage_baseline_check("network:conntrack_utilization", "net.netfilter.nf_conntrack_count / net.netfilter.nf_conntrack_max", None, warning, critical))

    system = _safe_json(os_configuration.get("systemConfiguration"), {})
    system_summary: Dict[str, Any] = {}
    if isinstance(system, dict):
        for key, identifier in (("fileDescriptor", "FILE_DESCRIPTOR_USAGE_HIGH"), ("pid", "PID_USAGE_HIGH")):
            sample = _safe_json(system.get(key), {})
            ratio = _number(sample.get("usageRatio") if isinstance(sample, dict) else None)
            system_summary[key] = sample
            baseline_checks.append(_usage_baseline_check(f"system:{key}", f"systemConfiguration.{key}.usageRatio", ratio, warning, critical))
            if ratio is not None and (severity := _severity(ratio, warning, critical)):
                findings.append(_finding(identifier, severity, f"{key} usage is {ratio:.2f}%", {key: sample}, "Identify the processes consuming this resource before increasing node limits."))
        system_summary["kernel_version"] = system.get("kernelVersion")
        system_summary["mtu"] = system.get("mtu")
    else:
        data_gaps.append("No system configuration was collected")
        for key in ("fileDescriptor", "pid"):
            baseline_checks.append(_usage_baseline_check(f"system:{key}", f"systemConfiguration.{key}.usageRatio", None, warning, critical))

    phase = status.get("phase")
    if phase == "Succeeded":
        baseline_checks.append(_baseline_check("collection:phase", "collection", "status.phase", "Succeeded", "exact", phase, "passed", "none", "Configuration collection succeeded"))
    elif phase:
        level = "critical" if phase in {"Failed", "Error"} else "warning"
        baseline_checks.append(_baseline_check("collection:phase", "collection", "status.phase", "Succeeded", "exact", phase, level, level, f"Configuration collection phase is {phase}"))
    else:
        baseline_checks.append(_baseline_check("collection:phase", "collection", "status.phase", "Succeeded", "exact", None, "unavailable", "none", "Collection phase was not returned"))
    if phase and phase != "Succeeded":
        level = "critical" if phase in {"Failed", "Error"} else "warning"
        findings.append(_finding("COLLECTION_NOT_SUCCEEDED", level, f"Node configuration collection phase is {phase}", {"status": status}, "Review the collection status and create a new diagnostic CR after resolving the reported issue."))

    severity_order = {"critical": 0, "warning": 1, "info": 2}
    findings.sort(key=lambda item: severity_order.get(item["severity"], 3))
    health = "unhealthy" if any(item["severity"] == "critical" for item in findings) else "warning" if findings else "healthy"
    return {
        "health": health,
        "baseline_summary": _baseline_summary(baseline_checks),
        "baseline_checks": baseline_checks,
        "findings": findings,
        "data_gaps": data_gaps,
        "observations": {
            "component_status": components,
            "resource_usage": resources,
            "network": network_summary,
            "system": system_summary,
            "collection_status": status,
        },
    }


def _diagnostic_name(node_name: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", node_name.lower()).strip("-") or "node"
    return f"ncc-{normalized[:45]}-{secrets.token_hex(4)}"[:63].rstrip("-")


def diagnose_node_configuration(region: str, cluster_id: str, node_name: str, project_id: Optional[str] = None, ak: Optional[str] = None, sk: Optional[str] = None, security_token: Optional[str] = None, poll_timeout_seconds: int = 120, warning_threshold: int = 80, critical_threshold: int = 90, debug: bool = False) -> Dict[str, Any]:
    """Create a unique diagnostic CR, wait for collection, and analyze the result."""
    explicit_credentials = bool(ak and sk)
    trace: list[Dict[str, Any]] = []
    cluster = _resolve_cluster(region, cluster_id, ak, sk, security_token, explicit_credentials, trace, debug)
    if not cluster.get("success"):
        return {"success": False, "action": "huawei_diagnose_cce_node_configuration", "error": cluster.get("error"), "debug_trace": trace if debug else None}
    resolved_cluster_id = cluster["cluster_id"]
    resolved_project_id = _project_id(region, project_id, ak, sk, security_token, explicit_credentials, trace, debug)
    node = _kubectl_json(_kubectl(region, resolved_cluster_id, resolved_project_id, ak, sk, security_token, "get", "node", node_name, "-o", "json"), explicit_credentials, trace, debug)
    if not node.get("success"):
        return {"success": False, "action": "huawei_diagnose_cce_node_configuration", "error": f"Unable to read node '{node_name}': {node.get('error')}", "debug_trace": trace if debug else None}
    provider_id = (node["data"].get("spec") or {}).get("providerID")
    if not provider_id or not _LABEL_VALUE.fullmatch(provider_id):
        return {"success": False, "action": "huawei_diagnose_cce_node_configuration", "error": f"Node '{node_name}' has no valid spec.providerID for agent.cce.io/node-id", "debug_trace": trace if debug else None}

    command = _kubectl(region, resolved_cluster_id, resolved_project_id, ak, sk, security_token, "create", "--validate=false", "-f", "-")
    cr_name = ""
    manifest: Dict[str, Any] = {}
    created: Dict[str, Any] = {}
    for _ in range(3):
        cr_name = _diagnostic_name(node_name)
        manifest = {
            "apiVersion": "node.cce.io/v1alpha1",
            "kind": "NodeConfigurationCollection",
            "metadata": {"name": cr_name, "labels": {"agent.cce.io/node-id": provider_id}},
            "status": {"phase": "Pending"},
        }
        created = _run(command, explicit_credentials, trace, debug, json.dumps(manifest))
        if created.get("success") or "alreadyexists" not in (created.get("error") or "").lower():
            break
    if not created.get("success"):
        return {"success": False, "action": "huawei_diagnose_cce_node_configuration", "error": f"Unable to create a unique diagnostic CR after three attempts: {created.get('error')}", "debug_trace": trace if debug else None}

    deadline = time.monotonic() + poll_timeout_seconds
    latest: Optional[Dict[str, Any]] = None
    while time.monotonic() < deadline:
        fetched = _kubectl_json(_kubectl(region, resolved_cluster_id, resolved_project_id, ak, sk, security_token, "get", "nodeconfigurationcollections.node.cce.io", cr_name, "-o", "json"), explicit_credentials, trace, debug)
        if not fetched.get("success"):
            return {"success": False, "action": "huawei_diagnose_cce_node_configuration", "error": f"Diagnostic CR '{cr_name}' disappeared or could not be read: {fetched.get('error')}", "diagnostic_cr": {"name": cr_name, "manifest": manifest}, "debug_trace": trace if debug else None}
        latest = fetched["data"]
        phase = (latest.get("status") or {}).get("phase")
        if phase in {"Succeeded", "Failed", "Error"}:
            break
        time.sleep(5)
    if latest is None:
        return {"success": False, "action": "huawei_diagnose_cce_node_configuration", "error": "No diagnostic CR result was returned", "diagnostic_cr": {"name": cr_name, "manifest": manifest}, "debug_trace": trace if debug else None}
    phase = (latest.get("status") or {}).get("phase")
    if phase not in {"Succeeded", "Failed", "Error"}:
        return {"success": False, "action": "huawei_diagnose_cce_node_configuration", "error": f"Timed out after {poll_timeout_seconds} seconds waiting for NodeConfigurationCollection; current phase is {phase or 'unknown'}", "diagnostic_cr": {"name": cr_name, "manifest": manifest, "status": latest.get("status")}, "debug_trace": trace if debug else None}

    analysis = _analyze(latest, warning_threshold, critical_threshold)
    response: Dict[str, Any] = {
        "success": phase == "Succeeded",
        "action": "huawei_diagnose_cce_node_configuration",
        "risk_level": "R2",
        "target": {"region": region, "project_id": resolved_project_id, "cluster_id": resolved_cluster_id, "cluster_name": cluster.get("cluster_name"), "node_name": node_name, "node_provider_id": provider_id},
        "diagnostic_cr": {
            "name": cr_name,
            "manifest": manifest,
            "status": latest.get("status"),
            "lifecycle": "CCE-managed; the controller may delete this CR after collection completes",
        },
        "diagnosis": analysis,
    }
    if phase != "Succeeded":
        response["error"] = f"Node configuration collection finished with phase {phase}"
    if debug:
        response["debug_trace"] = trace
    return response
