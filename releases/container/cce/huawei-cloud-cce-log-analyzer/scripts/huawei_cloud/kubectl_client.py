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
    try:
        process = subprocess.run(command, text=True, input=stdin, capture_output=True, timeout=60, env=environment)
    except FileNotFoundError:
        return {"success": False, "error": f"{command[0]} not found in PATH", "command": safe_command}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "command timed out after 60s", "command": safe_command}
    if process.returncode:
        return {"success": False, "error": (process.stderr or process.stdout or f"command exited with code {process.returncode}")[:2000], "command": safe_command}
    if not expect_json:
        return {"success": True, "output": process.stdout, "command": safe_command}
    try:
        return {"success": True, "data": json.loads(process.stdout or "{}"), "command": safe_command}
    except json.JSONDecodeError as exc:
        return {"success": False, "error": f"kubectl returned non-JSON output: {exc}", "command": safe_command}


def _hcloud(region: str, operation: str, params: Dict[str, str], ak: Optional[str], sk: Optional[str], project_id: Optional[str]) -> Dict[str, Any]:
    command = common.hcloud_command("CCE", operation, region, ak, sk, project_id)
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


def _external_kubectl(region: str, cluster_id: str, arguments: List[str], ak: Optional[str], sk: Optional[str], project_id: Optional[str], stdin: Optional[str], expect_json: bool) -> Dict[str, Any]:
    cluster = _hcloud(region, "ShowCluster", {"cluster_id": cluster_id}, ak, sk, project_id)
    if not cluster.get("success"):
        return cluster
    if not _has_external_access(cluster.get("data") or {}):
        return {"success": False, "error": "cluster has no bound EIP/external endpoint"}
    certificate = _hcloud(region, "CreateKubernetesClusterCert", {"cluster_id": cluster_id, "duration": "1"}, ak, sk, project_id)
    if not certificate.get("success"):
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


def _plugin_kubectl(region: str, cluster_id: str, arguments: List[str], ak: Optional[str], sk: Optional[str], project_id: Optional[str], security_token: Optional[str], stdin: Optional[str], expect_json: bool) -> Dict[str, Any]:
    env_ak, env_sk, env_project = common.get_credentials()
    environment = os.environ.copy()
    environment.update({"CCE_CLUSTER_ID": cluster_id, "CCE_REGION": region, "HW_REGION": region})
    credentials = ((ak or env_ak, ("HW_ACCESS_KEY", "HUAWEICLOUD_SDK_AK")), (sk or env_sk, ("HW_SECRET_KEY", "HUAWEICLOUD_SDK_SK")), (project_id or env_project, ("CCE_PROJECT_ID", "HW_PROJECT_ID")))
    for value, names in credentials:
        if value:
            environment.update(dict.fromkeys(names, value))
    token = security_token or os.environ.get("HUAWEI_SECURITY_TOKEN") or os.environ.get("HW_SECURITY_TOKEN")
    if token:
        environment.update({"HW_SECURITY_TOKEN": token, "HUAWEICLOUD_SECURITY_TOKEN": token})
    command = ["kubectl", "cce", "--cluster-id", cluster_id, "--region", region]
    if project_id or env_project:
        command.extend(["--project-id", project_id or env_project])
    command.extend(arguments)
    result = _run(command, environment=environment, stdin=stdin, expect_json=expect_json)
    if result.get("success"):
        result["access_method"] = "kubectl_cce_plugin"
    return result


def run_kubectl(region: str, cluster_id: str, arguments: List[str], *, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None, security_token: Optional[str] = None, stdin: Optional[str] = None, expect_json: bool = True) -> Dict[str, Any]:
    """Run a Kubernetes command through external access, then kubectl-cce."""
    external = _external_kubectl(region, cluster_id, arguments, ak, sk, project_id, stdin, expect_json)
    if external.get("success"):
        return external
    plugin = _plugin_kubectl(region, cluster_id, arguments, ak, sk, project_id, security_token, stdin, expect_json)
    if plugin.get("success"):
        return plugin
    return {"success": False, "error": "kubectl access failed through external kubeconfig and kubectl cce", "kubeconfig_error": external.get("error"), "plugin_error": plugin.get("error")}


def get_pod_logs(region: str, cluster_id: str, pod_name: str, namespace: str, container: Optional[str], previous: bool, tail_lines: int, ak: Optional[str], sk: Optional[str], project_id: Optional[str]) -> Dict[str, Any]:
    args = ["logs", pod_name, "--namespace", namespace, f"--tail={tail_lines}"]
    if container:
        args.extend(["--container", container])
    if previous:
        args.append("--previous")
    result = run_kubectl(region, cluster_id, args, ak=ak, sk=sk, project_id=project_id, expect_json=False)
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
            sk=self.params.get("sk"), project_id=self.params.get("project_id"), stdin=stdin, expect_json=expect_json,
        )
        if not result.get("success"):
            raise RuntimeError(result.get("error", "kubectl command failed"))
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
