---
name: huawei-cloud-cce-log-analyzer
description: >-
  查询和分析华为云 CCE 工作负载、审计和控制面日志。适用于 Pod 标准输出、由 CCE LogConfig 或 LTS Access Config 采集的应用日志、Kubernetes 审计证据、kube-apiserver API 错误和时延、kube-scheduler 调度失败，以及日志采集规则管理。
metadata:
  tags: [cce, kubernetes, logs, lts, observability]
---

# Huawei Cloud CCE Log Analyzer

## 适用范围

该技能用于只读日志查询和分析，以及经确认后的 CCE LogConfig、LTS Access Config 日志采集规则管理。不修改工作负载、日志组、日志流、LTS 日志数据或其他云资源。

| 用户目标 | 使用方式 |
|---|---|
| Pod 标准输出、标准错误或已终止容器日志 | Pod 日志工具 |
| 已采集到 LTS 的应用日志 | 应用日志流程，由用户选择采集规则 |
| 查询资源何时被谁创建、更新或删除 | 审计日志工具 |
| 分析 API 状态码和时延 | kube-apiserver 日志工具 |
| 分析 Pod Pending 和调度决策 | kube-scheduler 日志工具 |
| 创建或删除日志采集规则 | LogConfig 或 LTS Access Config 工具，先预览再确认 |

## 前置条件

- 需要 Python 3.8+、`hcloud` 以及 CCE、LTS 所需 IAM 权限。
- Pod 标准输出和 CCE LogConfig 工具需要 `kubectl`；外网 kubeconfig 不可用时使用 `kubectl cce`。安装方式见 `huawei-cloud-kubectl-cce-installer`。
- CCE LogConfig 依赖集群的云原生日志采集插件；LTS `AGENT` 采集依赖健康的 iCagent。
- 审计、kube-apiserver、kube-scheduler 工具分别要求 CCE Log Center 中对应的控制面日志开关已开启。工具会通过 `CCE ShowClusterConfig` 检查开关，不会自动开启。
- 认证优先级为工具入参 `ak`、`sk`、`project_id`，其次本机 hcloud profile，最后环境变量 `HUAWEI_AK`、`HUAWEI_SK`、`HUAWEI_PROJECT_ID`。
- LTS 的 `start_time`、`end_time` 必须使用 UTC `YYYY-MM-DD HH:MM:SS`；未传时按 UTC 生成最近时间窗口。

## 工具路由

| 工具 | 风险级别 | 用途 |
|---|---:|---|
| `huawei_get_pod_stdout_logs` | R3 | 获取当前或已终止容器的 stdout/stderr |
| `huawei_analyze_pod_stdout_realtime_logs` | R3 | 两次采样并分析新增 stdout |
| `huawei_get_cce_logconfigs` | R3 | 查询 CCE LogConfig |
| `huawei_list_lts_access_configs` | R3 | 查询 LTS Access Config |
| `huawei_query_application_logs` | R3 | 查询一条由用户选择的采集规则对应的日志 |
| `huawei_analyze_application_logs` | R3 | 分析一条由用户选择的采集规则对应的日志 |
| `huawei_query_cce_audit_logs` | R3 | 查询保留的 Kubernetes 审计事件 |
| `huawei_analyze_cce_audit_timeline` | R3 | 从审计事件构建资源变更时间线 |
| `huawei_query_kube_apiserver_logs` | R3 | 查询 kube-apiserver 控制面日志 |
| `huawei_analyze_kube_apiserver_logs` | R3 | 分析 API 状态码、错误和时延 |
| `huawei_query_kube_scheduler_logs` | R3 | 查询 kube-scheduler 控制面日志 |
| `huawei_analyze_kube_scheduler_logs` | R3 | 分析调度、绑定、抢占和 Leader Election 日志 |
| `huawei_create_cce_logconfig` | R2 | 预览并创建 CCE LogConfig |
| `huawei_create_lts_access_config` | R2 | 预览并创建 LTS Access Config |
| `huawei_delete_cce_logconfig` | R1 | 预览并删除 CCE LogConfig |
| `huawei_delete_lts_access_config` | R1 | 预览并删除 LTS Access Config |

执行 `python3 scripts/huawei-cloud.py help` 可查看全部工具和必填入参。完整命令和参数说明见 [references/tool-reference.md](references/tool-reference.md)。

## 使用步骤

### 1. 确定日志来源

- 用户指定 Pod 时，先用 `huawei_get_pod_stdout_logs`。
- 用户指定应用时，先查询 CCE LogConfig 和 LTS Access Config，展示目标集群相关规则，等待用户明确选择一条。
- 需要操作人、资源变更证据时，优先查询审计日志；apiserver 日志只能作为 HTTP 请求补充证据。
- 需要 API 可用性或时延时，使用 apiserver 分析；性能结论使用 `non_success_status_count` 和 `non_watch_latency`。
- 需要分析 Pending 或无法调度的 Pod 时，使用 scheduler 分析；重复出现的调度和抢占日志通常表示重试，不代表多个 Pod。

### 2. 先小范围查询

优先使用 `hours=1`、具体 namespace、Pod 或用户已选择的采集规则。仅在结果不足时启用 `auto_paginate=true` 并设置 `limit`、`max_pages`。除非用户明确要求关键字范围内的比例，否则应用日志异常率分析不要传 `keywords`。

### 3. 解释结果

- 审计日志没有记录不代表操作未发生，可能超出保留周期或未投递。若对应控制面日志已开启，可补充查询 apiserver 请求日志；不要仅凭 user agent 推断操作者身份。
- apiserver 的 `WATCH` 时延表示连接持续时间，不代表普通请求处理慢；性能判断使用 `summary.non_watch_latency`。
- scheduler 的 `preemption_issue` 常与 PV 节点亲和性、Pod 反亲和性等硬约束同时出现。先检查约束，再建议扩容或抢占。
- 输出中必须脱敏令牌、密码、Authorization、Cookie 和个人信息。

### 4. 变更前必须确认

R2、R1 工具必须先发现目标或日志目的端、执行不带 `confirm=true` 的预览、展示预览并等待用户明确确认，之后才能带 `confirm=true` 执行。工具不会自动创建或选择 LTS 日志组和日志流，用户必须明确提供所选的目的端 ID。

## 参考文档

| 文档 | 使用场景 |
|---|---|
| [workflow.md](references/workflow.md) | Pod、应用、审计、控制面和采集规则完整流程 |
| [tool-reference.md](references/tool-reference.md) | 工具参数和命令示例 |
| [risk-rules.md](references/risk-rules.md) | 风险、确认和数据安全边界 |
| [output-schema.md](references/output-schema.md) | 查询与分析结果字段解释 |
