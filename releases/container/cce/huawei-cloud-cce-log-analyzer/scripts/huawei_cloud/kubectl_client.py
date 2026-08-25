"""kubectl access for CCE log queries and LogConfig management."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from typing import Any, Dict, List, Optional

from . import common

def _run(command: List[str], *, environment: Optional[Dict[str, str]] = None, stdin: Optional[str] = None, expect_json: bool = True) -> Dict[str, Any]:
    safe_command = common.redact_command(command)
    common.emit_diagnostic("kubectl.command.start", command=safe_command, expect_json=expect_json)
    try:
        process = subprocess.run(command, text=True, input=stdin, capture_output=True, timeout=60, env=environment)
    except FileNotFoundError:
        common.emit_diagnostic("kubectl.command.failure", command=safe_command, reason="binary_not_found")
        return {"success": False, "error": f"{command[0]} not found in PATH", "command": safe_command}
    except subprocess.TimeoutExpired:
        common.emit_diagnostic("kubectl.command.failure", command=safe_command, reason="timeout", timeout_seconds=60)
        return {"success": False, "error": "command timed out after 60s", "command": safe_command}
    if process.returncode:
        error = (process.stderr or process.stdout or f"command exited with code {process.returncode}")[:2000]
        common.emit_diagnostic("kubectl.command.failure", command=safe_command, returncode=process.returncode, error=error)
        return {"success": False, "error": error, "command": safe_command}
    if not expect_json:
        common.emit_diagnostic("kubectl.command.success", command=safe_command, output_bytes=len(process.stdout or ""))
        return {"success": True, "output": process.stdout, "command": safe_command}
    try:
        data = json.loads(process.stdout or "{}")
        common.emit_diagnostic("kubectl.command.success", command=safe_command, output_bytes=len(process.stdout or ""))
        return {"success": True, "data": data, "command": safe_command}
    except json.JSONDecodeError as exc:
        error = f"kubectl returned non-JSON output: {exc}"
        common.emit_diagnostic("kubectl.command.failure", command=safe_command, reason="non_json_output", error=error)
        return {"success": False, "error": error, "command": safe_command}


def _hcloud(region: str, operation: str, params: Dict[str, str], ak: Optional[str], sk: Optional[str], project_id: Optional[str], security_token: Optional[str]) -> Dict[str, Any]:
    command = common.hcloud_command("CCE", operation, region, ak, sk, project_id, security_token)
    command.extend(f"--{key}={value}" for key, value in params.items() if value is not None)
    return common.run_hcloud(command)


def _has_external_access(cluster: Dict[str, Any]) -> bool:
    status = cluster.get("status") or {}
    return any(endpoint.get("type") == "External" and endpoint.get("url") for endpoint in status.get("endpoints", []) or []) or any(
        condition.get("type") == "ElasticPublicIP" and condition.get("status") not in {"UNBOUND", "False", "", None}
        for condition in status.get("conditions", []) or []
    )


def _prefer_external_context(kubeconfig: Dict[str, Any]) -> None:
    cluster_name = next((item.get("name") for item in kubeconfig.get("clusters", []) or [] if "external" in item.get("name", "") and "TLS" not in item.get("name", "")), None)
    if not cluster_name:
        return
    for context in kubeconfig.get("contexts", []) or []:
        if (context.get("context") or {}).get("cluster") == cluster_name:
            kubeconfig["current-context"] = context.get("name")
            return


def _external_kubectl(region: str, cluster_id: str, arguments: List[str], ak: Optional[str], sk: Optional[str], project_id: Optional[str], security_token: Optional[str], stdin: Optional[str], expect_json: bool) -> Dict[str, Any]:
    common.emit_diagnostic("kubectl.external.start", region=region, cluster_id=cluster_id)
    cluster = _hcloud(region, "ShowCluster", {"cluster_id": cluster_id}, ak, sk, project_id, security_token)
    if not cluster.get("success"):
        common.emit_diagnostic("kubectl.external.failure", stage="show_cluster", error=cluster.get("error"))
        return cluster
    if not _has_external_access(cluster.get("data") or {}):
        error = "cluster has no bound EIP/external endpoint"
        common.emit_diagnostic("kubectl.external.skipped", reason=error)
        return {"success": False, "error": error}
    certificate = _hcloud(region, "CreateKubernetesClusterCert", {"cluster_id": cluster_id, "duration": "1"}, ak, sk, project_id, security_token)
    if not certificate.get("success"):
        common.emit_diagnostic("kubectl.external.failure", stage="create_cluster_certificate", error=certificate.get("error"))
        return certificate
    kubeconfig = certificate.get("data") or {}
    if not kubeconfig.get("clusters"):
        return {"success": False, "error": "CreateKubernetesClusterCert returned no kubeconfig clusters"}
    _prefer_external_context(kubeconfig)
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as handle:
        json.dump(kubeconfig, handle)
        kubeconfig_path = handle.name
    try:
        result = _run(["kubectl", "--kubeconfig", kubeconfig_path, *arguments], stdin=stdin, expect_json=expect_json)
        if result.get("success"):
            result["access_method"] = "kubectl_kubeconfig_external"
        return result
    finally:
        os.remove(kubeconfig_path)


def _plugin_kubectl(region: str, cluster_id: str, arguments: List[str], ak: Optional[str], sk: Optional[str], project_id: Optional[str], security_token: Optional[str], explicit_cli_credentials: bool, stdin: Optional[str], expect_json: bool) -> Dict[str, Any]:
    env_ak, env_sk, env_project = (None, None, None) if explicit_cli_credentials else common.get_credentials()
    environment = os.environ.copy()
    if explicit_cli_credentials:
        for name in (
            "HW_ACCESS_KEY", "HUAWEICLOUD_SDK_AK", "HW_SECRET_KEY", "HUAWEICLOUD_SDK_SK",
            "CCE_PROJECT_ID", "HW_PROJECT_ID", "HW_SECURITY_TOKEN", "HUAWEICLOUD_SECURITY_TOKEN", "HCLOUD_CONFIG_DIR",
        ):
            environment.pop(name, None)
    environment.update({"CCE_CLUSTER_ID": cluster_id, "CCE_REGION": region, "HW_REGION": region})
    if not explicit_cli_credentials:
        credentials = ((ak or env_ak, ("HW_ACCESS_KEY", "HUAWEICLOUD_SDK_AK")), (sk or env_sk, ("HW_SECRET_KEY", "HUAWEICLOUD_SDK_SK")), (project_id or env_project, ("CCE_PROJECT_ID", "HW_PROJECT_ID")))
        for value, names in credentials:
            if value:
                environment.update(dict.fromkeys(names, value))
    token = security_token if explicit_cli_credentials else security_token or os.environ.get("HW_SECURITY_TOKEN")
    if token and not explicit_cli_credentials:
        environment.update({"HW_SECURITY_TOKEN": token, "HUAWEICLOUD_SECURITY_TOKEN": token})
    command = ["kubectl", "cce", "--cce-insecure-upstream-tls=true", "--cluster-id", cluster_id, "--region", region]
    resolved_project_id = project_id if explicit_cli_credentials else project_id or env_project
    if resolved_project_id:
        command.extend(["--project-id", resolved_project_id])
    if explicit_cli_credentials:
        command.extend([f"--cli-access-key={ak}", f"--cli-secret-key={sk}"])
        if security_token:
            command.append(f"--cli-security-token={security_token}")
    command.extend(arguments)
    common.emit_diagnostic(
        "kubectl.plugin.start",
        region=region,
        cluster_id=cluster_id,
        explicit_cli_credentials=explicit_cli_credentials,
        has_project_id=bool(resolved_project_id),
        has_security_token=bool(security_token),
    )
    result = _run(command, environment=environment, stdin=stdin, expect_json=expect_json)
    if result.get("success"):
        result["access_method"] = "kubectl_cce_plugin"
        common.emit_diagnostic("kubectl.plugin.success", command=result.get("command"))
    else:
        common.emit_diagnostic("kubectl.plugin.failure", command=result.get("command"), error=result.get("error"))
    return result


def run_kubectl(region: str, cluster_id: str, arguments: List[str], *, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None, security_token: Optional[str] = None, explicit_cli_credentials: bool = False, stdin: Optional[str] = None, expect_json: bool = True) -> Dict[str, Any]:
    """Run a Kubernetes command through external access, then kubectl-cce."""
    common.emit_diagnostic("kubectl.access.start", region=region, cluster_id=cluster_id, arguments=arguments)
    external = _external_kubectl(region, cluster_id, arguments, ak, sk, project_id, security_token, stdin, expect_json)
    if external.get("success"):
        common.emit_diagnostic("kubectl.access.success", method="external_kubeconfig")
        return external
    plugin = _plugin_kubectl(region, cluster_id, arguments, ak, sk, project_id, security_token, explicit_cli_credentials, stdin, expect_json)
    if plugin.get("success"):
        common.emit_diagnostic("kubectl.access.success", method="kubectl_cce_plugin", external_error=external.get("error"))
        return plugin
    common.emit_diagnostic(
        "kubectl.access.failure",
        external_error=external.get("error"),
        plugin_error=plugin.get("error"),
        plugin_command=plugin.get("command"),
    )
    return {"success": False, "error": "kubectl access failed through external kubeconfig and kubectl cce", "kubeconfig_error": external.get("error"), "plugin_error": plugin.get("error")}


def get_pod_logs(region: str, cluster_id: str, pod_name: str, namespace: str, container: Optional[str], previous: bool, tail_lines: int, ak: Optional[str], sk: Optional[str], project_id: Optional[str], security_token: Optional[str] = None, explicit_cli_credentials: bool = False) -> Dict[str, Any]:
    args = ["logs", pod_name, "--namespace", namespace, f"--tail={tail_lines}"]
    if container:
        args.extend(["--container", container])
    if previous:
        args.append("--previous")
    result = run_kubectl(region, cluster_id, args, ak=ak, sk=sk, project_id=project_id, security_token=security_token, explicit_cli_credentials=explicit_cli_credentials, expect_json=False)
    if result.get("success"):
        result["logs"] = result.pop("output")
    return result


class KubectlCustomObjectsApi:
    """Subset of CustomObjectsApi backed by kubectl resource commands."""

    def __init__(self, params: Dict[str, str]):
        self.params = params

    def _resource(self, group: str, plural: str) -> str:
        return f"{plural}.{group}"

    def _run(self, arguments: List[str], *, stdin: Optional[str] = None, expect_json: bool = True) -> Dict[str, Any]:
        result = run_kubectl(
            self.params["region"], self.params["cluster_id"], arguments, ak=self.params.get("ak"),
            sk=self.params.get("sk"), project_id=self.params.get("project_id"), security_token=self.params.get("security_token"),
            explicit_cli_credentials=self.params.get("_explicit_cli_credentials") == "true", stdin=stdin, expect_json=expect_json,
        )
        if not result.get("success"):
            details = [result.get("error", "kubectl command failed")]
            if result.get("kubeconfig_error"):
                details.append(f"external kubeconfig: {result['kubeconfig_error']}")
            if result.get("plugin_error"):
                details.append(f"kubectl cce: {result['plugin_error']}")
            raise RuntimeError("; ".join(details))
        return result.get("data") or {}

    def list_namespaced_custom_object(self, group: str, version: str, namespace: str, plural: str) -> Dict[str, Any]:
        return self._run(["get", self._resource(group, plural), "--namespace", namespace, "--output=json"])

    def list_cluster_custom_object(self, group: str, version: str, plural: str) -> Dict[str, Any]:
        return self._run(["get", self._resource(group, plural), "--all-namespaces", "--output=json"])

    def get_namespaced_custom_object(self, group: str, version: str, namespace: str, plural: str, name: str) -> Dict[str, Any]:
        return self._run(["get", self._resource(group, plural), name, "--namespace", namespace, "--output=json"])

    def create_namespaced_custom_object(self, group: str, version: str, namespace: str, plural: str, body: Dict[str, Any]) -> Dict[str, Any]:
        # CCE does not expose OpenAPI schemas for every custom resource; let the API server validate the object.
        return self._run(["apply", "--namespace", namespace, "--filename=-", "--output=json", "--validate=false"], stdin=json.dumps(body))

    def delete_namespaced_custom_object(self, group: str, version: str, namespace: str, plural: str, name: str) -> Dict[str, Any]:
        self._run(["delete", self._resource(group, plural), name, "--namespace", namespace, "--output=name"], expect_json=False)
        return {"metadata": {"name": name, "namespace": namespace}}
