#!/usr/bin/env python3
"""Unit tests for the modular Huawei Cloud dispatcher."""

import sys
import unittest
import json
import re
from pathlib import Path
from unittest import mock
import io
import runpy


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from huawei_cloud import dispatcher  # noqa: E402


class DispatcherTests(unittest.TestCase):
    def test_main_exits_with_error_when_action_missing(self):
        script_path = SCRIPT_DIR / "huawei-cloud.py"
        stdout = io.StringIO()

        with mock.patch.object(sys, "argv", ["huawei-cloud.py"]), \
            mock.patch("sys.stdout", stdout):
            with self.assertRaises(SystemExit) as exc:
                runpy.run_path(str(script_path), run_name="__main__")

        self.assertEqual(exc.exception.code, 1)
        self.assertEqual(json.loads(stdout.getvalue()), {"success": False, "error": "Missing action parameter"})

    def test_main_unknown_action_returns_structured_error(self):
        script_path = SCRIPT_DIR / "huawei-cloud.py"
        stdout = io.StringIO()

        with mock.patch.object(sys, "argv", ["huawei-cloud.py", "huawei_unknown"]), \
            mock.patch("sys.stdout", stdout):
            with self.assertRaises(SystemExit) as exc:
                runpy.run_path(str(script_path), run_name="__main__")

        self.assertEqual(exc.exception.code, 1)
        self.assertEqual(json.loads(stdout.getvalue()), {"success": False, "error": "Unknown action: huawei_unknown"})

    def test_parse_cli_params_ignores_non_key_value_args(self):
        module_globals = runpy.run_path(str(SCRIPT_DIR / "huawei-cloud.py"), run_name="huawei_cloud_cli_test")

        parse_cli_params = module_globals["_parse_cli_params"]
        result = parse_cli_params(["region=cn-north-4", "invalid", "limit=5", "name=a=b"])

        self.assertEqual(result, {"region": "cn-north-4", "limit": "5", "name": "a=b"})

    def test_coerce_helpers_handle_defaults_and_invalid_values(self):
        module_globals = runpy.run_path(str(SCRIPT_DIR / "huawei-cloud.py"), run_name="huawei_cloud_cli_test")

        coerce_int = module_globals["_coerce_int"]
        coerce_bool = module_globals["_coerce_bool"]

        self.assertEqual(coerce_int("7", 1), 7)
        self.assertEqual(coerce_int("bad", 3), 3)
        self.assertEqual(coerce_int(None, 9), 9)
        self.assertTrue(coerce_bool("true"))
        self.assertFalse(coerce_bool("false"))
        self.assertTrue(coerce_bool(None, True))

    def test_select_external_cluster_prefers_external_non_tls_entry(self):
        module_globals = runpy.run_path(str(SCRIPT_DIR / "huawei-cloud.py"), run_name="huawei_cloud_cli_test")
        select_external_cluster = module_globals["_select_external_cluster"]

        kubeconfig_data = {
            "clusters": [
                {"name": "internal-cluster", "cluster": {"server": "https://internal"}},
                {"name": "external-cluster", "cluster": {"server": "https://external"}},
                {"name": "external-TLS-cluster", "cluster": {"server": "https://external-tls"}},
            ]
        }

        result = select_external_cluster(kubeconfig_data)
        self.assertEqual(result["cluster"]["server"], "https://external")

    def test_select_external_cluster_falls_back_to_first_cluster(self):
        module_globals = runpy.run_path(str(SCRIPT_DIR / "huawei-cloud.py"), run_name="huawei_cloud_cli_test")
        select_external_cluster = module_globals["_select_external_cluster"]

        kubeconfig_data = {
            "clusters": [
                {"name": "internal-cluster", "cluster": {"server": "https://internal"}},
            ]
        }

        result = select_external_cluster(kubeconfig_data)
        self.assertEqual(result["cluster"]["server"], "https://internal")

    def test_get_kubeconfig_user_data_returns_named_user_payload(self):
        module_globals = runpy.run_path(str(SCRIPT_DIR / "huawei-cloud.py"), run_name="huawei_cloud_cli_test")
        get_user_data = module_globals["_get_kubeconfig_user_data"]

        kubeconfig_data = {
            "users": [
                {"name": "other", "user": {"token": "ignored"}},
                {"name": "user", "user": {"client_certificate_data": "abc", "client_key_data": "xyz"}},
            ]
        }

        self.assertEqual(
            get_user_data(kubeconfig_data),
            {"client_certificate_data": "abc", "client_key_data": "xyz"},
        )

    def test_get_kubeconfig_user_data_returns_empty_dict_when_missing(self):
        module_globals = runpy.run_path(str(SCRIPT_DIR / "huawei-cloud.py"), run_name="huawei_cloud_cli_test")
        get_user_data = module_globals["_get_kubeconfig_user_data"]

        self.assertEqual(get_user_data({"users": []}), {})

    def test_cleanup_cert_pair_deletes_both_paths(self):
        module_globals = runpy.run_path(str(SCRIPT_DIR / "huawei-cloud.py"), run_name="huawei_cloud_cli_test")
        cleanup_cert_pair = module_globals["_cleanup_cert_pair"]
        safe_delete = mock.Mock()

        with mock.patch.dict(cleanup_cert_pair.__globals__, {"_safe_delete_file": safe_delete}):
            cleanup_cert_pair("/tmp/a.crt", "/tmp/b.key")

        self.assertEqual(safe_delete.call_args_list, [mock.call("/tmp/a.crt"), mock.call("/tmp/b.key")])

    def test_dispatch_query_logs_parses_labels_and_boolean_flags(self):
        params = {
            "region": "cn-north-4",
            "log_group_id": "g1",
            "log_stream_id": "s1",
            "labels": '{"app":"demo"}',
            "is_desc": "false",
            "is_iterative": "true",
            "limit": "25",
        }

        with mock.patch("huawei_cloud.dispatcher.lts.query_logs", return_value={"success": True}) as mocked:
            result = dispatcher.dispatch_action("huawei_query_logs", params)

        self.assertTrue(result["success"])
        mocked.assert_called_once_with(
            "cn-north-4",
            "g1",
            "s1",
            None,
            None,
            None,
            25,
            None,
            False,
            True,
            {"app": "demo"},
            None,
            None,
            None,
        )

    def test_dispatch_query_logs_invalid_labels_json_raises(self):
        with self.assertRaises(json.JSONDecodeError):
            dispatcher.dispatch_action(
                "huawei_query_logs",
                {"region": "cn-north-4", "log_group_id": "g1", "log_stream_id": "s1", "labels": "{bad json}"},
            )

    def test_dispatch_get_recent_logs_parses_hours_keywords_and_labels(self):
        params = {
            "region": "cn-north-4",
            "log_group_id": "g1",
            "log_stream_id": "s1",
            "hours": "6",
            "limit": "50",
            "keywords": "error",
            "labels": '{"namespace":"default"}',
        }

        with mock.patch("huawei_cloud.dispatcher.lts.get_recent_logs", return_value={"success": True}) as mocked:
            result = dispatcher.dispatch_action("huawei_get_recent_logs", params)

        self.assertTrue(result["success"])
        mocked.assert_called_once_with(
            "cn-north-4",
            "g1",
            "s1",
            6,
            50,
            "error",
            {"namespace": "default"},
            None,
            None,
            None,
        )

    def test_parse_json_param_returns_none_for_empty_values(self):
        self.assertIsNone(dispatcher._parse_json_param(None))
        self.assertIsNone(dispatcher._parse_json_param(""))

    def test_dispatch_resize_nodepool_parses_scale_group_names(self):
        params = {
            "region": "cn-north-4",
            "cluster_id": "c1",
            "nodepool_id": "np1",
            "node_count": "3",
            "scale_group_names": "asg-a, asg-b ,",
            "confirm": "true",
        }

        with mock.patch("huawei_cloud.dispatcher.cce.resize_node_pool", return_value={"success": True}) as mocked:
            result = dispatcher.dispatch_action("huawei_resize_cce_nodepool", params)

        self.assertTrue(result["success"])
        mocked.assert_called_once_with("cn-north-4", "c1", "np1", 3, True, ["asg-a", "asg-b"], None, None, None)

    def test_main_legacy_dispatch_branches_removed(self):
        script_text = (SCRIPT_DIR / "huawei-cloud.py").read_text()
        legacy_actions = set(re.findall(r'(?:if|elif) action == "([^"]+)"', script_text))
        self.assertEqual(legacy_actions, set())

    def test_main_prefers_modular_dispatch_for_registered_action(self):
        script_path = SCRIPT_DIR / "huawei-cloud.py"
        stdout = io.StringIO()

        with mock.patch("huawei_cloud.dispatcher.is_registered_action", return_value=True), \
            mock.patch("huawei_cloud.dispatcher.dispatch_action", return_value={"success": True, "source": "modular"}), \
            mock.patch.object(sys, "argv", ["huawei-cloud.py", "huawei_list_ecs", "region=cn-north-4"]), \
            mock.patch("sys.stdout", stdout):
            runpy.run_path(str(script_path), run_name="__main__")

        self.assertEqual(json.loads(stdout.getvalue()), {"success": True, "source": "modular"})

    def test_legacy_compat_aliases_point_to_modular_modules(self):
        module_globals = runpy.run_path(str(SCRIPT_DIR / "huawei-cloud.py"), run_name="huawei_cloud_cli_test")

        self.assertIs(module_globals["list_cce_clusters"], dispatcher.cce.list_cce_clusters)
        self.assertIs(module_globals["list_eip_addresses"], dispatcher.network.list_eip_addresses)
        self.assertIs(module_globals["get_aom_prom_metrics_http"], dispatcher.aom.get_aom_prom_metrics_http)
        self.assertIs(module_globals["get_cce_node_metrics"], dispatcher.cce_metrics.get_cce_node_metrics)
        self.assertIs(module_globals["get_cce_addon_detail"], dispatcher.cce.get_cce_addon_detail)
        self.assertEqual(module_globals["cce_cluster_inspection"].__module__, "huawei_cloud.cce_inspection")
        self.assertEqual(module_globals["generate_inspection_html_report"].__module__, "huawei_cloud.cce_inspection")

    def test_registered_actions_cover_first_wave(self):
        for action in [
            "huawei_list_ecs",
            "huawei_list_vpc",
            "huawei_list_evs",
            "huawei_list_elb",
            "huawei_list_supported_regions",
            "huawei_get_project_by_region",
            "huawei_list_cce_clusters",
            "huawei_scale_cce_workload",
            "huawei_list_aom_instances",
            "huawei_list_log_groups",
            "huawei_cce_cluster_inspection",
            "huawei_get_application_log_stream",
            "huawei_get_cce_node_metrics",
            "huawei_node_diagnose",
        ]:
            self.assertTrue(dispatcher.is_registered_action(action))

    def test_missing_required_param_returns_structured_error(self):
        result = dispatcher.dispatch_action("huawei_get_ecs_metrics", {"region": "cn-north-4"})
        self.assertFalse(result["success"])
        self.assertIn("instance_id", result["error"])

    def test_dispatch_calls_target_handler(self):
        with mock.patch("huawei_cloud.dispatcher.ecs.list_ecs_instances", return_value={"success": True, "count": 0}) as mocked:
            result = dispatcher.dispatch_action("huawei_list_ecs", {"region": "cn-north-4", "limit": "5"})
        self.assertTrue(result["success"])
        mocked.assert_called_once_with("cn-north-4", None, None, None, 5, 0)

    def test_supported_regions_dispatch_works_without_params(self):
        result = dispatcher.dispatch_action("huawei_list_supported_regions", {})
        self.assertTrue(result["success"])
        self.assertIn("china_mainland", result)

    def test_cce_cluster_dispatch_calls_target_handler(self):
        with mock.patch("huawei_cloud.dispatcher.cce.list_cce_clusters", return_value={"success": True, "count": 1}) as mocked:
            result = dispatcher.dispatch_action("huawei_list_cce_clusters", {"region": "cn-north-4", "limit": "3"})
        self.assertTrue(result["success"])
        mocked.assert_called_once_with("cn-north-4", None, None, None, 3, 0)

    def test_scale_workload_preview_dispatch(self):
        preview = {"success": False, "requires_confirmation": True}
        with mock.patch("huawei_cloud.dispatcher.cce.scale_cce_workload", return_value=preview) as mocked:
            result = dispatcher.dispatch_action(
                "huawei_scale_cce_workload",
                {
                    "region": "cn-north-4",
                    "cluster_id": "cluster-1",
                    "workload_type": "deployment",
                    "name": "demo",
                    "namespace": "default",
                    "replicas": "2",
                },
            )
        self.assertEqual(result, preview)
        mocked.assert_called_once_with("cn-north-4", "cluster-1", "deployment", "demo", "default", 2, False, None, None, None)

    def test_aom_dispatch_calls_target_handler(self):
        with mock.patch("huawei_cloud.dispatcher.aom.list_aom_instances", return_value={"success": True, "count": 2}) as mocked:
            result = dispatcher.dispatch_action("huawei_list_aom_instances", {"region": "cn-north-4", "prom_type": "CCE"})
        self.assertTrue(result["success"])
        mocked.assert_called_once_with("cn-north-4", None, None, None, "CCE")

    def test_lts_dispatch_calls_target_handler(self):
        with mock.patch("huawei_cloud.dispatcher.lts.list_log_groups", return_value={"success": True, "total": 1}) as mocked:
            result = dispatcher.dispatch_action("huawei_list_log_groups", {"region": "cn-north-4"})
        self.assertTrue(result["success"])
        mocked.assert_called_once_with("cn-north-4", None, None, None)

    def test_inspection_dispatch_calls_target_handler(self):
        with mock.patch("huawei_cloud.dispatcher.cce_inspection.cce_cluster_inspection", return_value={"success": True}) as mocked:
            result = dispatcher.dispatch_action("huawei_cce_cluster_inspection", {"region": "cn-north-4", "cluster_id": "c1"})
        self.assertTrue(result["success"])
        mocked.assert_called_once()

    def test_app_log_stream_dispatch_calls_target_handler(self):
        with mock.patch("huawei_cloud.dispatcher.cce_app_logs.get_application_log_stream_action", return_value={"success": True, "log_group_id": "g1"}) as mocked:
            result = dispatcher.dispatch_action("huawei_get_application_log_stream", {"region": "cn-north-4", "cluster_id": "c1", "app_name": "demo"})
        self.assertTrue(result["success"])
        mocked.assert_called_once()

    def test_node_metric_dispatch_calls_target_handler(self):
        with mock.patch("huawei_cloud.dispatcher.cce_metrics.get_cce_node_metrics", return_value={"success": True}) as mocked:
            result = dispatcher.dispatch_action("huawei_get_cce_node_metrics", {"region": "cn-north-4", "cluster_id": "c1", "node_ip": "192.168.1.1"})
        self.assertTrue(result["success"])
        mocked.assert_called_once()

    def test_node_diagnose_dispatch_calls_target_handler(self):
        with mock.patch("huawei_cloud.dispatcher.cce_diagnosis.diagnose_single_node", return_value={"success": True}) as mocked:
            result = dispatcher.dispatch_action("huawei_node_diagnose", {"region": "cn-north-4", "cluster_id": "c1", "node_ip": "192.168.1.1"})
        self.assertTrue(result["success"])
        mocked.assert_called_once()



    # ==================== 高优先级补充用例 ====================

    def test_require_missing_param_returns_error(self):
        """_require 缺少必填参数时返回格式错误"""
        result = dispatcher.dispatch_action("huawei_get_ecs_metrics", {"region": "cn-north-4"})
        self.assertFalse(result["success"])
        self.assertIn("instance_id", result["error"])

    def test_delete_cce_cluster_preview_mode(self):
        """huawei_delete_cce_cluster preview模式下不执行删除"""
        preview = {"success": False, "requires_confirmation": True, "message": "Preview: cluster deletion skipped"}
        with mock.patch("huawei_cloud.dispatcher.cce.delete_cce_cluster", return_value=preview) as mocked:
            result = dispatcher.dispatch_action("huawei_delete_cce_cluster", {
                "region": "cn-north-4", "cluster_id": "c1", "confirm": "false"
            })
        self.assertEqual(result, preview)
        mocked.assert_called_once()

    def test_delete_cce_node_preview_mode(self):
        """huawei_delete_cce_node preview模式下不执行删除"""
        preview = {"success": False, "requires_confirmation": True}
        with mock.patch("huawei_cloud.dispatcher.cce.delete_cce_node", return_value=preview) as mocked:
            result = dispatcher.dispatch_action("huawei_delete_cce_node", {
                "region": "cn-north-4", "cluster_id": "c1", "node_id": "n1", "confirm": "false"
            })
        self.assertEqual(result, preview)
        mocked.assert_called_once()

    def test_network_diagnose_dispatch(self):
        """huawei_network_diagnose 正确调用 diagnose 函数"""
        with mock.patch("huawei_cloud.dispatcher.cce_diagnosis.network_diagnose", return_value={"success": True, "report": {}}) as mocked:
            result = dispatcher.dispatch_action("huawei_network_diagnose", {
                "region": "cn-north-4", "cluster_id": "c1", "workload_name": "demo", "namespace": "default"
            })
        self.assertTrue(result["success"])
        mocked.assert_called_once()

    def test_network_verify_pod_scheduling_dispatch(self):
        """huawei_network_verify_pod_scheduling 正确调用验证函数"""
        with mock.patch("huawei_cloud.dispatcher.cce_diagnosis.verify_pod_scheduling_after_scale", return_value={"success": True, "running_pods": 3}) as mocked:
            result = dispatcher.dispatch_action("huawei_network_verify_pod_scheduling", {
                "region": "cn-north-4", "cluster_id": "c1", "workload_name": "demo", "namespace": "default"
            })
        self.assertTrue(result["success"])
        mocked.assert_called_once()

    def test_node_batch_diagnose_dispatch(self):
        """huawei_node_batch_diagnose 支持多节点"""
        with mock.patch("huawei_cloud.dispatcher.cce_diagnosis.batch_node_diagnose", return_value={"success": True, "diagnoses": []}) as mocked:
            result = dispatcher.dispatch_action("huawei_node_batch_diagnose", {
                "region": "cn-north-4", "cluster_id": "c1", "node_ips": "192.168.1.1,192.168.1.2"
            })
        self.assertTrue(result["success"])
        mocked.assert_called_once()

    def test_cce_cluster_inspection_subagent_returns_task_list(self):
        """huawei_cce_cluster_inspection_subagent 返回正确的任务结构"""
        with mock.patch("huawei_cloud.dispatcher.cce_inspection.generate_auto_subagent_info", return_value={
            "success": True, "mode": "auto", "total_tasks": 8, "tasks": []
        }) as mocked:
            result = dispatcher.dispatch_action("huawei_cce_cluster_inspection_subagent", {
                "region": "cn-north-4", "cluster_id": "c1"
            })
        self.assertTrue(result["success"])
        self.assertEqual(result["mode"], "auto")
        self.assertEqual(result["total_tasks"], 8)
        mocked.assert_called_once()

    def test_aggregate_inspection_results_dispatch(self):
        """huawei_aggregate_inspection_results 正确聚合结果"""
        with mock.patch("huawei_cloud.dispatcher.cce_inspection.aggregate_subagent_results", return_value={
            "success": True, "result": {"status": "HEALTHY", "total_issues": 0}
        }) as mocked:
            result = dispatcher.dispatch_action("huawei_aggregate_inspection_results", {
                "results": '[{"task_id":"pods","success":true}]',
                "cluster_info": '{"cluster_id":"c1","region":"cn-north-4"}'
            })
        self.assertTrue(result["success"])
        mocked.assert_called_once()

    def test_query_aom_logs_dispatch(self):
        """huawei_query_aom_logs 正确调用 LTS 查询"""
        with mock.patch("huawei_cloud.dispatcher.lts.query_aom_logs", return_value={"success": True, "logs": []}) as mocked:
            result = dispatcher.dispatch_action("huawei_query_aom_logs", {
                "region": "cn-north-4", "cluster_id": "c1", "log_group_id": "g1", "log_stream_id": "s1"
            })
        self.assertTrue(result["success"])
        mocked.assert_called_once()

    # ==================== workload_diagnose 新增用例 ====================

    def test_workload_diagnose_dispatch(self):
        """huawei_workload_diagnose 正确调用 workload_diagnose 函数"""
        with mock.patch("huawei_cloud.dispatcher.cce_diagnosis.workload_diagnose", return_value={"success": True, "report": {}}) as mocked:
            result = dispatcher.dispatch_action("huawei_workload_diagnose", {
                "region": "cn-north-4",
                "cluster_id": "c1",
                "workload_name": "demo-app",
                "namespace": "default",
                "fault_time": "2026-04-05 10:00:00",
            })
        self.assertTrue(result["success"])
        mocked.assert_called_once()
        # 参数以 positional 传入: region, cluster_id, workload_name, namespace, ak, sk, project_id, fault_time
        args = mocked.call_args[0]
        self.assertEqual(args[0], "cn-north-4")
        self.assertEqual(args[1], "c1")
        self.assertEqual(args[2], "demo-app")
        self.assertEqual(args[3], "default")
        self.assertEqual(args[7], "2026-04-05 10:00:00")

    def test_workload_diagnose_dispatch_without_optional_params(self):
        """huawei_workload_diagnose 可选参数为空时也能正常调用"""
        with mock.patch("huawei_cloud.dispatcher.cce_diagnosis.workload_diagnose", return_value={"success": True, "report": {}}) as mocked:
            result = dispatcher.dispatch_action("huawei_workload_diagnose", {
                "region": "cn-north-4",
                "cluster_id": "c1",
            })
        self.assertTrue(result["success"])
        mocked.assert_called_once()

    def test_workload_diagnose_by_alarm_dispatch(self):
        """huawei_workload_diagnose_by_alarm 正确调用 workload_diagnose_by_alarm 函数"""
        alarm_info = '{"workload_name":"demo-app","namespace":"default"}'
        with mock.patch("huawei_cloud.dispatcher.cce_diagnosis.workload_diagnose_by_alarm", return_value={"success": True, "report": {}}) as mocked:
            result = dispatcher.dispatch_action("huawei_workload_diagnose_by_alarm", {
                "region": "cn-north-4",
                "cluster_id": "c1",
                "alarm_info": alarm_info,
            })
        self.assertTrue(result["success"])
        mocked.assert_called_once()
        # 参数以 positional 传入: region, cluster_id, alarm_info, ak, sk, project_id
        args = mocked.call_args[0]
        self.assertEqual(args[0], "cn-north-4")
        self.assertEqual(args[1], "c1")
        self.assertEqual(args[2], alarm_info)

    def test_workload_diagnose_by_alarm_requires_alarm_info(self):
        """huawei_workload_diagnose_by_alarm 缺少 alarm_info 时返回格式错误"""
        result = dispatcher.dispatch_action("huawei_workload_diagnose_by_alarm", {
            "region": "cn-north-4",
            "cluster_id": "c1",
        })
        self.assertFalse(result["success"])
        self.assertIn("alarm_info", result["error"])

    def test_workload_diagnose_requires_region_and_cluster(self):
        """huawei_workload_diagnose 缺少必填参数时返回格式错误"""
        result = dispatcher.dispatch_action("huawei_workload_diagnose", {"region": "cn-north-4"})
        self.assertFalse(result["success"])
        self.assertIn("cluster_id", result["error"])

        result = dispatcher.dispatch_action("huawei_workload_diagnose", {"cluster_id": "c1"})
        self.assertFalse(result["success"])
        self.assertIn("region", result["error"])

    def test_workload_diagnose_action_exception_handling(self):
        """huawei_workload_diagnose 函数抛出异常时返回结构化错误"""
        with mock.patch("huawei_cloud.dispatcher.cce_diagnosis.workload_diagnose", side_effect=RuntimeError("test error")):
            result = dispatcher.dispatch_action("huawei_workload_diagnose", {
                "region": "cn-north-4",
                "cluster_id": "c1",
            })
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "test error")
        self.assertEqual(result["error_type"], "RuntimeError")
        self.assertEqual(result["stage"], "workload_diagnose")

    def test_workload_diagnose_by_alarm_action_exception_handling(self):
        """huawei_workload_diagnose_by_alarm 函数抛出异常时返回结构化错误"""
        with mock.patch("huawei_cloud.dispatcher.cce_diagnosis.workload_diagnose_by_alarm", side_effect=ValueError("parse error")):
            result = dispatcher.dispatch_action("huawei_workload_diagnose_by_alarm", {
                "region": "cn-north-4",
                "cluster_id": "c1",
                "alarm_info": "{}",
            })
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "parse error")
        self.assertEqual(result["error_type"], "ValueError")
        self.assertEqual(result["stage"], "workload_diagnose_by_alarm")

    def test_workload_diagnose_in_action_specs(self):
        """huawei_workload_diagnose 和 huawei_workload_diagnose_by_alarm 已注册到 ACTION_SPECS"""
        self.assertTrue(dispatcher.is_registered_action("huawei_workload_diagnose"))
        self.assertTrue(dispatcher.is_registered_action("huawei_workload_diagnose_by_alarm"))
        spec1 = dispatcher.ACTION_SPECS["huawei_workload_diagnose"]
        spec2 = dispatcher.ACTION_SPECS["huawei_workload_diagnose_by_alarm"]
        self.assertEqual(spec1[0], ("region", "cluster_id"))
        self.assertEqual(spec2[0], ("region", "cluster_id", "alarm_info"))

    # ==================== hibernate/awake cluster 新增用例 ====================

    def test_hibernate_cce_cluster_dispatch(self):
        """huawei_hibernate_cce_cluster 正确调用 hibernate_cce_cluster 函数"""
        with mock.patch("huawei_cloud.dispatcher.cce.hibernate_cce_cluster", return_value={"success": True, "message": "ok"}) as mocked:
            result = dispatcher.dispatch_action("huawei_hibernate_cce_cluster", {
                "region": "cn-north-4",
                "cluster_id": "c1",
            })
        self.assertTrue(result["success"])
        mocked.assert_called_once_with("cn-north-4", "c1", None, None, None)

    def test_awake_cce_cluster_dispatch(self):
        """huawei_awake_cce_cluster 正确调用 awake_cce_cluster 函数"""
        with mock.patch("huawei_cloud.dispatcher.cce.awake_cce_cluster", return_value={"success": True, "message": "ok"}) as mocked:
            result = dispatcher.dispatch_action("huawei_awake_cce_cluster", {
                "region": "cn-north-4",
                "cluster_id": "c1",
            })
        self.assertTrue(result["success"])
        mocked.assert_called_once_with("cn-north-4", "c1", None, None, None)

    def test_hibernate_cce_cluster_requires_params(self):
        """缺少必填参数时返回格式错误"""
        result = dispatcher.dispatch_action("huawei_hibernate_cce_cluster", {"region": "cn-north-4"})
        self.assertFalse(result["success"])
        self.assertIn("cluster_id", result["error"])

        result = dispatcher.dispatch_action("huawei_hibernate_cce_cluster", {"cluster_id": "c1"})
        self.assertFalse(result["success"])
        self.assertIn("region", result["error"])

    def test_awake_cce_cluster_requires_params(self):
        """缺少必填参数时返回格式错误"""
        result = dispatcher.dispatch_action("huawei_awake_cce_cluster", {"region": "cn-north-4"})
        self.assertFalse(result["success"])
        self.assertIn("cluster_id", result["error"])

        result = dispatcher.dispatch_action("huawei_awake_cce_cluster", {"cluster_id": "c1"})
        self.assertFalse(result["success"])
        self.assertIn("region", result["error"])

    def test_hibernate_awake_cce_cluster_in_action_specs(self):
        """两个新 action 已注册且参数定义正确"""
        self.assertTrue(dispatcher.is_registered_action("huawei_hibernate_cce_cluster"))
        self.assertTrue(dispatcher.is_registered_action("huawei_awake_cce_cluster"))
        spec1 = dispatcher.ACTION_SPECS["huawei_hibernate_cce_cluster"]
        spec2 = dispatcher.ACTION_SPECS["huawei_awake_cce_cluster"]
        self.assertEqual(spec1[0], ("region", "cluster_id"))
        self.assertEqual(spec2[0], ("region", "cluster_id"))

    # ==================== ECS stop/start 新增用例 ====================

    def test_stop_ecs_instance_dispatch(self):
        """huawei_stop_ecs_instance 正确调用 stop_ecs_instance 函数"""
        with mock.patch("huawei_cloud.dispatcher.ecs.stop_ecs_instance", return_value={"success": True}) as mocked:
            result = dispatcher.dispatch_action("huawei_stop_ecs_instance", {
                "region": "cn-north-4",
                "instance_id": "i-xxx",
                "stop_type": "SOFT",
                "confirm": "true",
            })
        self.assertTrue(result["success"])
        mocked.assert_called_once()
        args = mocked.call_args[0]
        self.assertEqual(args[0], "cn-north-4")
        self.assertEqual(args[1], "i-xxx")
        self.assertEqual(args[2], "SOFT")
        self.assertEqual(args[6], True)

    def test_stop_ecs_instance_preview_mode(self):
        """huawei_stop_ecs_instance 不带 confirm 时返回预览"""
        preview = {"success": False, "error": "Operation not confirmed."}
        with mock.patch("huawei_cloud.dispatcher.ecs.stop_ecs_instance", return_value=preview) as mocked:
            result = dispatcher.dispatch_action("huawei_stop_ecs_instance", {
                "region": "cn-north-4",
                "instance_id": "i-xxx",
                "confirm": "false",
            })
        self.assertFalse(result["success"])
        self.assertIn("not confirmed", result["error"])
        mocked.assert_called_once()

    def test_start_ecs_instance_dispatch(self):
        """huawei_start_ecs_instance 正确调用 start_ecs_instance 函数"""
        with mock.patch("huawei_cloud.dispatcher.ecs.start_ecs_instance", return_value={"success": True}) as mocked:
            result = dispatcher.dispatch_action("huawei_start_ecs_instance", {
                "region": "cn-north-4",
                "instance_id": "i-xxx",
            })
        self.assertTrue(result["success"])
        mocked.assert_called_once()
        args = mocked.call_args[0]
        self.assertEqual(args[0], "cn-north-4")
        self.assertEqual(args[1], "i-xxx")

    def test_stop_ecs_instance_requires_params(self):
        """缺少必填参数时返回格式错误"""
        result = dispatcher.dispatch_action("huawei_stop_ecs_instance", {"region": "cn-north-4"})
        self.assertFalse(result["success"])
        self.assertIn("instance_id", result["error"])

        result = dispatcher.dispatch_action("huawei_stop_ecs_instance", {"instance_id": "i-xxx"})
        self.assertFalse(result["success"])
        self.assertIn("region", result["error"])

    def test_start_ecs_instance_requires_params(self):
        """缺少必填参数时返回格式错误"""
        result = dispatcher.dispatch_action("huawei_start_ecs_instance", {"region": "cn-north-4"})
        self.assertFalse(result["success"])
        self.assertIn("instance_id", result["error"])

        result = dispatcher.dispatch_action("huawei_start_ecs_instance", {"instance_id": "i-xxx"})
        self.assertFalse(result["success"])
        self.assertIn("region", result["error"])

    def test_stop_start_ecs_in_action_specs(self):
        """两个新 action 已注册且参数定义正确"""
        self.assertTrue(dispatcher.is_registered_action("huawei_stop_ecs_instance"))
        self.assertTrue(dispatcher.is_registered_action("huawei_start_ecs_instance"))
        spec1 = dispatcher.ACTION_SPECS["huawei_stop_ecs_instance"]
        spec2 = dispatcher.ACTION_SPECS["huawei_start_ecs_instance"]
        self.assertEqual(spec1[0], ("region", "instance_id"))
        self.assertEqual(spec2[0], ("region", "instance_id"))

    # ==================== get_cce_pods labels 过滤新增用例 ====================

    def test_get_cce_pods_dispatch_with_labels(self):
        """huawei_get_cce_pods 支持 labels 参数"""
        with mock.patch("huawei_cloud.dispatcher.cce.get_kubernetes_pods", return_value={"success": True, "pods": []}) as mocked:
            result = dispatcher.dispatch_action("huawei_get_cce_pods", {
                "region": "cn-north-4",
                "cluster_id": "c1",
                "namespace": "default",
                "labels": "app=nginx",
            })
        self.assertTrue(result["success"])
        mocked.assert_called_once()
        args = mocked.call_args[0]
        self.assertEqual(args[0], "cn-north-4")
        self.assertEqual(args[1], "c1")
        self.assertEqual(args[5], "default")
        self.assertEqual(args[6], "app=nginx")

    def test_get_cce_pods_dispatch_without_optional_params(self):
        """huawei_get_cce_pods 不传 labels 时也能正常工作"""
        with mock.patch("huawei_cloud.dispatcher.cce.get_kubernetes_pods", return_value={"success": True, "pods": []}) as mocked:
            result = dispatcher.dispatch_action("huawei_get_cce_pods", {
                "region": "cn-north-4",
                "cluster_id": "c1",
            })
        self.assertTrue(result["success"])
        mocked.assert_called_once()
        args = mocked.call_args[0]
        self.assertEqual(args[6], None)

    # ==================== list_cce_cronjobs 新增用例 ====================

    def test_list_cce_cronjobs_dispatch(self):
        """huawei_list_cce_cronjobs 正确调用 list_cce_cronjobs 函数"""
        with mock.patch("huawei_cloud.dispatcher.cce.list_cce_cronjobs", return_value={"success": True, "cronjobs": []}) as mocked:
            result = dispatcher.dispatch_action("huawei_list_cce_cronjobs", {
                "region": "cn-north-4",
                "cluster_id": "c1",
                "namespace": "default",
            })
        self.assertTrue(result["success"])
        mocked.assert_called_once()
        args = mocked.call_args[0]
        self.assertEqual(args[0], "cn-north-4")
        self.assertEqual(args[1], "c1")
        self.assertEqual(args[2], "default")

    def test_list_cce_cronjobs_dispatch_without_namespace(self):
        """huawei_list_cce_cronjobs 不传 namespace 时也能正常工作"""
        with mock.patch("huawei_cloud.dispatcher.cce.list_cce_cronjobs", return_value={"success": True, "cronjobs": []}) as mocked:
            result = dispatcher.dispatch_action("huawei_list_cce_cronjobs", {
                "region": "cn-north-4",
                "cluster_id": "c1",
            })
        self.assertTrue(result["success"])
        mocked.assert_called_once()
        args = mocked.call_args[0]
        self.assertEqual(args[2], None)

    def test_list_cce_cronjobs_requires_params(self):
        """缺少必填参数时返回格式错误"""
        result = dispatcher.dispatch_action("huawei_list_cce_cronjobs", {"region": "cn-north-4"})
        self.assertFalse(result["success"])
        self.assertIn("cluster_id", result["error"])

        result = dispatcher.dispatch_action("huawei_list_cce_cronjobs", {"cluster_id": "c1"})
        self.assertFalse(result["success"])
        self.assertIn("region", result["error"])

    def test_list_cce_cronjobs_in_action_specs(self):
        """huawei_list_cce_cronjobs 已注册且参数定义正确"""
        self.assertTrue(dispatcher.is_registered_action("huawei_list_cce_cronjobs"))
        spec = dispatcher.ACTION_SPECS["huawei_list_cce_cronjobs"]
        self.assertEqual(spec[0], ("region", "cluster_id"))


if __name__ == "__main__":
    unittest.main()
