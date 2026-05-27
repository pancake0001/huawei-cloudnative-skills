#!/usr/bin/env python3
"""
Huawei Cloud Tools Tester
Tests all tools in the huawei-cloud skill, automatically fetches test resources
"""

import os
import sys
import json
import subprocess
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

# Add the skill directory to Python path
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(SKILL_DIR, "scripts"))

class HuaweiCloudTester:
    def __init__(self, ak: str, sk: str, region: str = "cn-north-4"):
        self.ak = ak
        self.sk = sk
        self.region = region
        self.project_id: Optional[str] = None
        self.cluster_id: Optional[str] = None
        self.ecs_instance_id: Optional[str] = None
        self.cce_node_ip: Optional[str] = None
        self.cce_node_name: Optional[str] = None
        self.cce_node_id: Optional[str] = None
        self.cce_nodepool_id: Optional[str] = None
        self.cce_deployment: Optional[str] = None
        self.cce_pod_name: Optional[str] = None
        self.cce_namespace: str = "default"
        self.cce_service_name: Optional[str] = None
        self.cce_workload_type: str = "deployment"
        self.app_name: str = "online-products"
        self.ecs_eip_id: Optional[str] = None
        self.elb_id: Optional[str] = None
        self.nat_gateway_id: Optional[str] = None
        self.evs_id: Optional[str] = None
        self.log_group_id: Optional[str] = None
        self.log_stream_id: Optional[str] = None
        self.aom_instance_id: Optional[str] = None
        self.test_results: List[Dict[str, Any]] = []
        self.log_file = os.path.join(SKILL_DIR, "test_results.log")

    def log(self, message: str):
        """Log message to console and file"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] {message}"
        print(log_line)
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_line + "\n")

    def _extract_last_json_object(self, output: str) -> Dict[str, Any]:
        """Extract and parse the last complete JSON object from mixed text output."""
        decoder = json.JSONDecoder()
        idx = 0
        last_obj: Optional[Dict[str, Any]] = None
        n = len(output)

        while idx < n:
            start = output.find("{", idx)
            if start == -1:
                break

            try:
                obj, end = decoder.raw_decode(output[start:])
                if isinstance(obj, dict):
                    last_obj = obj
                idx = start + end
            except json.JSONDecodeError:
                idx = start + 1

        if last_obj is None:
            raise json.JSONDecodeError("No valid JSON objects found", output, 0)

        return last_obj

    def run_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Run a huawei-cloud tool and return the result"""
        cmd = [
            sys.executable,
            os.path.join(SKILL_DIR, "scripts", "huawei-cloud.py"),
            tool_name,
            f"region={self.region}",
            f"ak={self.ak}",
            f"sk={self.sk}"
        ]
        if self.project_id:
            cmd.append(f"project_id={self.project_id}")
        for key, value in kwargs.items():
            cmd.append(f"{key}={value}")
        
        self.log(f"Running: {tool_name}")
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            output = result.stdout.strip()
            if result.stderr:
                self.log(f"  Stderr: {result.stderr.strip()}")
            
            try:
                # Handle cases where output contains multiple JSON objects or non-JSON text
                if tool_name in [
                    "huawei_query_application_recent_logs",
                    "huawei_query_application_logs",
                    "huawei_cce_cluster_inspection_parallel",
                ]:
                    parsed = self._extract_last_json_object(output)
                else:
                    parsed = json.loads(output)
                success = parsed.get("success", False)

                # Preview-only dangerous operations are expected to return success=false
                # with a confirmation hint when confirm=true is not provided.
                preview_only_tools = {
                    "huawei_scale_cce_workload",
                    "huawei_resize_cce_nodepool",
                    "huawei_delete_cce_node",
                    "huawei_delete_cce_workload",
                    "huawei_delete_cce_cluster",
                }
                if tool_name in preview_only_tools:
                    if parsed.get("requires_confirmation") or "confirm=true" in output or "Deletion not confirmed" in output:
                        success = True
                self.test_results.append({
                    "tool": tool_name,
                    "success": success,
                    "timestamp": datetime.now().isoformat(),
                    "output": output[:2000]  # Truncate long output
                })
                return parsed
            except json.JSONDecodeError:
                self.test_results.append({
                    "tool": tool_name,
                    "success": False,
                    "timestamp": datetime.now().isoformat(),
                    "output": output[:2000]
                })
                return {"success": False, "output": output}
        except Exception as e:
            self.log(f"  Error: {str(e)}")
            self.test_results.append({
                "tool": tool_name,
                "success": False,
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            })
            return {"success": False, "error": str(e)}

    def fetch_test_resources(self):
        """Fetch test resources automatically"""
        self.log("=" * 50)
        self.log("Fetching test resources...")
        self.log("=" * 50)

        # Get project ID
        self.log("Fetching project ID...")
        result = self.run_tool("huawei_get_project_by_region")
        if result.get("success"):
            self.project_id = result.get("project_id")
            self.log(f"  Project ID: {self.project_id}")

        # List ECS instances
        self.log("Fetching ECS instances...")
        result = self.run_tool("huawei_list_ecs")
        if result.get("success") and result.get("instances"):
            instance = result["instances"][0]
            self.ecs_instance_id = instance["id"]
            self.log(f"  ECS Instance ID: {self.ecs_instance_id}")
            volume_ids = instance.get("os-extended-volumes:volumes_attached") or instance.get("volumes_attached") or []
            if volume_ids:
                self.evs_id = volume_ids[0].get("id")
                self.log(f"  Attached EVS ID: {self.evs_id}")

        # List CCE clusters
        self.log("Fetching CCE clusters...")
        result = self.run_tool("huawei_list_cce_clusters")
        if result.get("success") and result.get("clusters"):
            for cluster in result["clusters"]:
                if cluster.get("status") == "Available":
                    self.cluster_id = cluster["id"]
                    self.log(f"  CCE Cluster ID: {self.cluster_id} (Available)")
                    break
            if not self.cluster_id:
                self.cluster_id = result["clusters"][0]["id"]
                self.log(f"  CCE Cluster ID: {self.cluster_id}")

        # List EIP
        self.log("Fetching EIPs...")
        result = self.run_tool("huawei_list_eip")
        if result.get("success") and result.get("eips"):
            self.ecs_eip_id = result["eips"][0].get("id")
            self.log(f"  EIP ID: {self.ecs_eip_id}")

        # List NAT gateways
        self.log("Fetching NAT gateways...")
        result = self.run_tool("huawei_list_nat")
        if result.get("success") and result.get("nat_gateways"):
            self.nat_gateway_id = result["nat_gateways"][0].get("id")
            self.log(f"  NAT Gateway ID: {self.nat_gateway_id}")

        # List ELB listeners / loadbalancers
        self.log("Fetching ELB listeners...")
        result = self.run_tool("huawei_list_elb_listeners")
        if result.get("success") and result.get("listeners"):
            listener_desc = result["listeners"][0].get("description")
            self.log("  ELB listener found")

        self.log("Fetching ELBs...")
        result = self.run_tool("huawei_list_elb")
        if result.get("success") and result.get("loadbalancers"):
            self.elb_id = result["loadbalancers"][0].get("id")
            self.log(f"  ELB ID: {self.elb_id}")

        # List EVS
        self.log("Fetching EVS volumes...")
        result = self.run_tool("huawei_list_evs")
        if result.get("success") and result.get("volumes"):
            self.evs_id = result["volumes"][0].get("id")
            self.log(f"  EVS ID: {self.evs_id}")

        # List AOM instances
        self.log("Fetching AOM instances...")
        result = self.run_tool("huawei_list_aom_instances")
        if result.get("success") and result.get("instances"):
            for instance in result["instances"]:
                if instance.get("type") == "CCE":
                    self.aom_instance_id = instance.get("id")
                    break
            if not self.aom_instance_id:
                self.aom_instance_id = result["instances"][0].get("id")
            self.log(f"  AOM Instance ID: {self.aom_instance_id}")

        # List log groups / streams
        self.log("Fetching log groups...")
        result = self.run_tool("huawei_list_log_groups")
        if result.get("success") and result.get("log_groups"):
            self.log_group_id = result["log_groups"][0].get("id")
            self.log(f"  Log Group ID: {self.log_group_id}")

        if self.log_group_id:
            self.log("Fetching log streams...")
            result = self.run_tool("huawei_list_log_streams", log_group_id=self.log_group_id)
            if result.get("success") and result.get("log_streams"):
                self.log_stream_id = result["log_streams"][0].get("id")
                self.log(f"  Log Stream ID: {self.log_stream_id}")

        # List CCE nodes and nodepools
        if self.cluster_id:
            self.log("Fetching CCE nodes...")
            result = self.run_tool("huawei_list_cce_nodes", cluster_id=self.cluster_id)
            if result.get("success") and result.get("nodes"):
                first_node = result["nodes"][0]
                self.cce_node_name = first_node.get("name")
                self.cce_node_id = first_node.get("id")
                self.log(f"  CCE Node Name: {self.cce_node_name}")

            self.log("Fetching Kubernetes nodes...")
            result = self.run_tool("huawei_get_kubernetes_nodes", cluster_id=self.cluster_id)
            if result.get("success") and result.get("nodes"):
                first_k8s_node = result["nodes"][0]
                self.cce_node_ip = first_k8s_node.get("internal_ip") or first_k8s_node.get("hostname")
                self.log(f"  CCE Node IP: {self.cce_node_ip}")

            self.log("Fetching CCE nodepools...")
            result = self.run_tool("huawei_list_cce_nodepools", cluster_id=self.cluster_id)
            if result.get("success") and result.get("nodepools"):
                self.cce_nodepool_id = result["nodepools"][0].get("metadata", {}).get("uid") or result["nodepools"][0].get("id")
                self.log(f"  CCE Nodepool ID: {self.cce_nodepool_id}")

            self.log("Fetching CCE deployments...")
            result = self.run_tool("huawei_get_cce_deployments", cluster_id=self.cluster_id)
            if result.get("success") and result.get("deployments"):
                preferred = None
                for dep in result["deployments"]:
                    ns = dep.get("namespace")
                    name = dep.get("name")
                    replicas = dep.get("desired_replicas") or dep.get("replicas") or 0
                    if ns == "default" and name and replicas and replicas > 0:
                        preferred = dep
                        break
                if not preferred:
                    for dep in result["deployments"]:
                        ns = dep.get("namespace")
                        name = dep.get("name")
                        replicas = dep.get("desired_replicas") or dep.get("replicas") or 0
                        if name and replicas and replicas > 0:
                            preferred = dep
                            break
                if preferred:
                    self.cce_namespace = preferred.get("namespace") or self.cce_namespace
                    self.cce_deployment = preferred.get("name")
                    self.cce_service_name = preferred.get("name")
                    self.app_name = preferred.get("name")
                    self.log(f"  Selected Deployment For Diagnostics: {self.cce_namespace}/{self.cce_deployment}")

            self.log("Fetching CCE pods for log test...")
            result = self.run_tool("huawei_get_cce_pods", cluster_id=self.cluster_id, namespace="default")
            if result.get("success") and result.get("pods"):
                for pod in result["pods"]:
                    status = pod.get("status", "")
                    if status == "Running":
                        self.cce_pod_name = pod.get("name")
                        self.log(f"  Selected Pod For Log Test: {self.cce_namespace}/{self.cce_pod_name}")
                        break

            if self.app_name:
                self.log("Fetching application log stream...")
                result = self.run_tool("huawei_get_application_log_stream", cluster_id=self.cluster_id, app_name=self.app_name, namespace=self.cce_namespace)
                if result.get("success"):
                    self.log_group_id = result.get("log_group_id") or self.log_group_id
                    self.log_stream_id = result.get("log_stream_id") or self.log_stream_id
                    if self.log_group_id:
                        self.log(f"  App Log Group ID: {self.log_group_id}")
                    if self.log_stream_id:
                        self.log(f"  App Log Stream ID: {self.log_stream_id}")

        self.log("Test resources fetched!")
        self.log("")

    def test_all_tools(self):
        """Test all tools in the skill"""
        self.log("=" * 50)
        self.log("Starting tool tests...")
        self.log("=" * 50)

        # --------------------------
        # IAM Project Management
        # --------------------------
        self.log("\n--- IAM Project Management ---")
        self.run_tool("huawei_list_supported_regions")
        self.run_tool("huawei_list_projects")
        self.run_tool("huawei_get_project_by_region")

        # --------------------------
        # ECS Elastic Cloud Server
        # --------------------------
        self.log("\n--- ECS Elastic Cloud Server ---")
        self.run_tool("huawei_list_ecs")
        self.run_tool("huawei_list_flavors")
        if self.ecs_instance_id:
            self.run_tool("huawei_get_ecs_metrics", instance_id=self.ecs_instance_id)

        # --------------------------
        # EVS Elastic Volume Service
        # --------------------------
        self.log("\n--- EVS Elastic Volume Service ---")
        self.run_tool("huawei_list_evs")
        if self.evs_id and self.ecs_instance_id:
            self.run_tool("huawei_get_evs_metrics", volume_id=self.evs_id, instance_id=self.ecs_instance_id)

        # --------------------------
        # VPC Virtual Private Cloud
        # --------------------------
        self.log("\n--- VPC Virtual Private Cloud ---")
        self.run_tool("huawei_list_vpc")
        self.run_tool("huawei_list_vpc_subnets")
        self.run_tool("huawei_list_security_groups")
        self.run_tool("huawei_list_vpc_acls")
        self.run_tool("huawei_list_nat")
        if self.nat_gateway_id:
            self.run_tool("huawei_get_nat_gateway_metrics", nat_gateway_id=self.nat_gateway_id)

        # --------------------------
        # SFS File Storage
        # --------------------------
        self.log("\n--- SFS File Storage ---")
        self.run_tool("huawei_list_sfs")
        self.run_tool("huawei_list_sfs_turbo")

        # --------------------------
        # ELB Elastic Load Balance
        # --------------------------
        self.log("\n--- ELB Elastic Load Balance ---")
        self.run_tool("huawei_list_elb")
        self.run_tool("huawei_list_elb_listeners")
        if self.elb_id:
            self.run_tool("huawei_get_elb_metrics", elb_id=self.elb_id)

        # --------------------------
        # EIP Elastic IP
        # --------------------------
        self.log("\n--- EIP Elastic IP ---")
        self.run_tool("huawei_list_eip")
        if self.ecs_eip_id:
            self.run_tool("huawei_get_eip_metrics", eip_id=self.ecs_eip_id)

        # --------------------------
        # CCE Cloud Container Engine
        # --------------------------
        if self.cluster_id:
            self.log("\n--- CCE Cloud Container Engine ---")
            self.run_tool("huawei_list_cce_addons", cluster_id=self.cluster_id)
            self.run_tool("huawei_get_cce_namespaces", cluster_id=self.cluster_id)
            self.run_tool("huawei_list_cce_configmaps", cluster_id=self.cluster_id)
            self.run_tool("huawei_list_cce_secrets", cluster_id=self.cluster_id)
            self.run_tool("huawei_get_cce_kubeconfig", cluster_id=self.cluster_id)
            self.run_tool("huawei_get_kubernetes_nodes", cluster_id=self.cluster_id)
            self.run_tool("huawei_list_cce_nodes", cluster_id=self.cluster_id)
            self.run_tool("huawei_get_cce_nodes", cluster_id=self.cluster_id)
            self.run_tool("huawei_list_cce_nodepools", cluster_id=self.cluster_id)
            self.run_tool("huawei_get_cce_pods", cluster_id=self.cluster_id)
            if self.cce_pod_name:
                self.run_tool("huawei_get_pod_logs", cluster_id=self.cluster_id, pod_name=self.cce_pod_name, namespace="default", tail_lines=20)
            self.run_tool("huawei_get_cce_deployments", cluster_id=self.cluster_id)
            self.run_tool("huawei_get_cce_services", cluster_id=self.cluster_id)
            self.run_tool("huawei_get_cce_ingresses", cluster_id=self.cluster_id)
            self.run_tool("huawei_get_cce_events", cluster_id=self.cluster_id)
            self.run_tool("huawei_get_cce_pvcs", cluster_id=self.cluster_id)
            self.run_tool("huawei_get_cce_pvs", cluster_id=self.cluster_id)
            self.run_tool("huawei_list_cce_daemonsets", cluster_id=self.cluster_id)
            self.run_tool("huawei_list_cce_statefulsets", cluster_id=self.cluster_id)
            self.run_tool("huawei_get_cce_pod_metrics_topN", cluster_id=self.cluster_id)
            if self.cce_namespace:
                self.run_tool("huawei_get_cce_pod_metrics", cluster_id=self.cluster_id, namespace=self.cce_namespace, pod_name=self.app_name, hours=1)
            self.run_tool("huawei_get_cce_node_metrics_topN", cluster_id=self.cluster_id)
            if self.cce_node_ip:
                self.run_tool("huawei_get_cce_node_metrics", cluster_id=self.cluster_id, node_ip=self.cce_node_ip)
            self.run_tool("huawei_get_cce_logconfigs", cluster_id=self.cluster_id)
            if self.app_name:
                self.run_tool("huawei_get_application_log_stream", cluster_id=self.cluster_id, app_name=self.app_name, namespace=self.cce_namespace)
                self.run_tool("huawei_query_application_recent_logs", cluster_id=self.cluster_id, app_name=self.app_name, namespace=self.cce_namespace, hours=1, limit=10)
                self.run_tool("huawei_query_application_logs", cluster_id=self.cluster_id, app_name=self.app_name, namespace=self.cce_namespace, start_time="2026-04-02 00:00:00", end_time="2026-04-02 23:59:59", limit=10)

            if self.cce_namespace and self.cce_service_name:
                self.run_tool("huawei_network_diagnose", cluster_id=self.cluster_id, namespace=self.cce_namespace, workload_type=self.cce_workload_type, workload_name=self.cce_service_name)
                alarm_payload = json.dumps({"namespace": self.cce_namespace, "workload_name": self.cce_service_name}, ensure_ascii=False)
                self.run_tool("huawei_network_diagnose_by_alarm", cluster_id=self.cluster_id, alarm_info=alarm_payload)

            if self.cce_node_ip:
                self.run_tool("huawei_node_diagnose", cluster_id=self.cluster_id, node_ip=self.cce_node_ip)
            if self.cce_node_ip:
                self.run_tool("huawei_node_batch_diagnose", cluster_id=self.cluster_id, node_ips=self.cce_node_ip)

            # --------------------------
            # CCE Cluster Inspection
            # --------------------------
            self.log("\n--- CCE Cluster Inspection ---")
            self.run_tool("huawei_pod_status_inspection", cluster_id=self.cluster_id)
            self.run_tool("huawei_addon_pod_monitoring_inspection", cluster_id=self.cluster_id)
            self.run_tool("huawei_biz_pod_monitoring_inspection", cluster_id=self.cluster_id)
            self.run_tool("huawei_node_status_inspection", cluster_id=self.cluster_id)
            self.run_tool("huawei_node_resource_inspection", cluster_id=self.cluster_id)
            self.run_tool("huawei_event_inspection", cluster_id=self.cluster_id)
            self.run_tool("huawei_aom_alarm_inspection", cluster_id=self.cluster_id)
            self.run_tool("huawei_elb_monitoring_inspection", cluster_id=self.cluster_id)
            self.run_tool("huawei_cce_cluster_inspection", cluster_id=self.cluster_id)
            self.run_tool("huawei_cce_cluster_inspection_parallel", cluster_id=self.cluster_id, max_workers=2)
            self.run_tool("huawei_cce_cluster_inspection_subagent", cluster_id=self.cluster_id)
            self.run_tool("huawei_aggregate_inspection_results", results='[]', cluster_info='{}')
            self.run_tool("huawei_export_inspection_report", cluster_id=self.cluster_id)

        # --------------------------
        # AOM Application Operations Management
        # --------------------------
        self.log("\n--- AOM Application Operations Management ---")
        self.run_tool("huawei_list_aom_instances")
        self.run_tool("huawei_list_aom_alerts")
        self.run_tool("huawei_list_aom_current_alarms")
        self.run_tool("huawei_list_aom_alarm_rules")
        self.run_tool("huawei_list_aom_action_rules")
        self.run_tool("huawei_list_aom_mute_rules")
        if self.aom_instance_id:
            now = datetime.now()
            end_ts = int(now.timestamp())
            start_ts = int((now - timedelta(hours=1)).timestamp())
            self.run_tool("huawei_get_aom_metrics", aom_instance_id=self.aom_instance_id, query='up', start=start_ts, end=end_ts)
        if self.cluster_id:
            self.run_tool("huawei_query_aom_logs", cluster_id=self.cluster_id, namespace=self.cce_namespace, limit=10)

        # --------------------------
        # LTS Log Tank Service
        # --------------------------
        self.log("\n--- LTS Log Tank Service ---")
        self.run_tool("huawei_list_log_groups")
        if self.log_group_id:
            self.run_tool("huawei_list_log_streams", log_group_id=self.log_group_id)
        if self.log_group_id and self.log_stream_id:
            self.run_tool("huawei_query_logs", log_group_id=self.log_group_id, log_stream_id=self.log_stream_id, limit=10)
            self.run_tool("huawei_get_recent_logs", log_group_id=self.log_group_id, log_stream_id=self.log_stream_id, hours=1, limit=10)

        # --------------------------
        # Modify Operations (Preview Only)
        # --------------------------
        if self.cluster_id:
            self.log("\n--- Modify Operations (PREVIEW ONLY) ---")
            self.log("Testing scale workload (preview)...")
            if self.cce_deployment:
                self.run_tool(
                    "huawei_scale_cce_workload",
                    cluster_id=self.cluster_id,
                    workload_type="deployment",
                    name=self.cce_deployment,
                    namespace=self.cce_namespace,
                    replicas=3
                )
            if self.cce_nodepool_id:
                self.run_tool(
                    "huawei_resize_cce_nodepool",
                    cluster_id=self.cluster_id,
                    nodepool_id=self.cce_nodepool_id,
                    node_count=2
                )
            if self.cce_node_id:
                self.run_tool(
                    "huawei_delete_cce_node",
                    cluster_id=self.cluster_id,
                    node_id=self.cce_node_id
                )
            if self.cce_deployment:
                self.run_tool(
                    "huawei_delete_cce_workload",
                    cluster_id=self.cluster_id,
                    workload_type="deployment",
                    name=self.cce_deployment,
                    namespace=self.cce_namespace
                )
            self.run_tool(
                "huawei_delete_cce_cluster",
                cluster_id=self.cluster_id
            )

        self.log("\n" + "=" * 50)
        self.log("All tests complete!")
        self.log("=" * 50)

    def generate_report(self):
        """Generate test report"""
        report_file = os.path.join(SKILL_DIR, "test_report.json")
        report = {
            "timestamp": datetime.now().isoformat(),
            "region": self.region,
            "total_tests": len(self.test_results),
            "passed": sum(1 for r in self.test_results if r["success"]),
            "failed": sum(1 for r in self.test_results if not r["success"]),
            "results": self.test_results
        }
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        self.log(f"\nTest report saved to: {report_file}")
        self.log(f"Test log saved to: {self.log_file}")

def main():
    if len(sys.argv) < 3:
        print("Usage: python test_huawei_cloud_tools.py <AK> <SK> [region]")
        sys.exit(1)

    ak = sys.argv[1]
    sk = sys.argv[2]
    region = sys.argv[3] if len(sys.argv) > 3 else "cn-north-4"

    tester = HuaweiCloudTester(ak, sk, region)
    tester.fetch_test_resources()
    tester.test_all_tools()
    tester.generate_report()

if __name__ == "__main__":
    main()
