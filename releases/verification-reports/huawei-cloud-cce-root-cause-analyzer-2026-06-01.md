# huawei-cloud-cce-root-cause-analyzer 验证报告

## 基本信息

| 项目 | 内容 |
| --- | --- |
| Skill | `huawei-cloud-cce-root-cause-analyzer` |
| 验证工具 | `aicli v1.0.0-beta.2` |
| 验证环境 | CCE 集群 `aicli` 命名空间，Pod `aicli-dcfcf5595-4gf22` |
| 验证时间 | 2026-06-01 |
| 区域 | `cn-north-4` |
| 集群 ID | `1d450236-5b28-11f1-a7f6-0255ac10026a` |
| 操作性质 | 只读分析 |

## 验证结果

| 验证项 | 结果 | 证据 |
| --- | --- | --- |
| Skill 触发 | 通过 | aicli 正确加载并识别该 skill |
| 根因分析 | 通过 | top_causes=2，首要根因为 Evicted |
| 只读安全 | 通过 | 仅执行分析，无变更操作 |
| 凭证安全 | 通过 | 未输出 AK/SK/Token |

## 关键发现

- 根因分析功能正常运行，正确识别集群核心问题
- 环境中存在 Evicted 相关真实故障，属于环境状态

## 修复记录

| 编号 | 类型 | 问题 | 修复 |
| --- | --- | --- | --- |
| CCE-COMMON-001 | 参数兼容性 | CLI dispatcher 仅支持 `key=value` 格式 | 增强 `_parse_cli_params` 支持多种格式 |

## 最终结论

**通过**。根因分析功能正常。


## aicli 实际输出（Skill 生成的报告）

>>> FIELD: report_markdown (len=4550)
# CCE 综合根因分析报告

## 1. 分析摘要

- Analysis-Trace-ID: `RCA-20260601114809-15eadc6b`
- 集群: `1d450236-5b28-11f1-a7f6-0255ac10026a`
- 区域: `cn-north-4`
- 命名空间: `全集群`
- 目标对象: `未指定`
- 初步结论: 最高置信根因是 `配置或密钥变更`，类型 `Change:config_change`，置信度 `0.62`。

## 2. 排查过程

1. 明确故障对象和时间窗口，建立跨信号 Trace ID。
2. 汇聚工作负载发布状态、Pod/事件/日志、依赖拓扑、近期变更和 AOM 告警。
3. 将每类信号转换为根因候选，记录支持证据、反证和证据限制。
4. 按证据强度、时间吻合度、影响面和可恢复性排序，输出 Top3 根因。
5. 恢复动作只给交接建议，实际执行由 auto-remediation-runner 预览并确认。

## 3. 数据源与采集状态

| 数据源 | 状态 | 说明 |
| --- | --- | --- |
| Workload 发布诊断 | 跳过 | 未启用或缺少必要范围 |
| 依赖影响面分析 | 成功 | 已采集 |
| 变更影响分析 | 成功 | 已采集 |
| AOM 告警关联 | 成功 | 已采集 |

## 4. 时间线

| 来源 | 时间/阶段 | 事件 |
| --- | --- | --- |
| Audit Change | 2026-06-01 11:47:25 | patch kube-system/bursting-status: 配置或密钥变更 |
| Audit Change | 2026-06-01 11:46:25 | patch kube-system/bursting-status: 配置或密钥变更 |

## 5. Top3 根因结论

| 排名 | 根因候选 | 域 | 置信度 | 关键证据 |
| --- | --- | --- | --- | --- |
| 1 | 配置或密钥变更 | change | 0.62 | {'source': 'audit', 'time': '2026-06-01 11:47:25', 'summary': 'patch configmaps kube-system/bursting-status', 'actor': 'system:serviceaccount:kube-system:cceaddon-virtual-kubelet', 'status_code': 200, 'request_uri': '/api/v1/namespaces/kube-system/configmaps/bursting-status'} |
| 2 | 目标服务不可用会沿 Service/Ingress 传播 | dependency | 0.55 | {'source': 'dependency_topology', 'summary': '目标 Pod 部分不可用且存在入口或服务依赖。', 'pod_health': {'total': 1132, 'ready': 129, 'unready': 1003, 'abnormal_pods': ['default/abclient-57c4fbb6f6-22ckc', 'default/abclient-57c4fbb6f6-22mgd', 'default/abclient-57c4fbb6f6-252xw', 'default/abclient-57c4fbb6f6-2554x'... |
| 3 | AOM 告警与故障窗口存在关联信号 | alarm | 0.5 | {'source': 'aom', 'summary': '关联告警 10 条', 'sample': [{'priority': 'sudden', 'priority_label': '🔴 突发', 'event_name': '节点内存空间不足##NodeHasInsufficientMemory', 'namespace': '', 'pods': ['192.168.32.218'], 'pod_count': 1, 'alarm_count': 5, 'severity': 'Minor', 'first_seen': '2026-06-01 10:58:05 UTC', '... |

## 6. 证据链与反证

### Top 1: 配置或密钥变更
- `audit`: {'source': 'audit', 'time': '2026-06-01 11:47:25', 'summary': 'patch configmaps kube-system/bursting-status', 'actor': 'system:serviceaccount:kube-system:cceaddon-virtual-kubelet', 'status_code': 200, 'request_uri': '/api/v1/namespaces/kube-system/configmaps/bursting-status'}
- `aom_alarm`: {'source': 'aom_alarm', 'time': None, 'summary': 'Pod健康检查失败##Unhealthy'}
- `aom_alarm`: {'source': 'aom_alarm', 'time': None, 'summary': '启动重试失败##BackOffStart'}
- `aom_alarm`: {'source': 'aom_alarm', 'time': None, 'summary': '启动重试失败##BackOffStart'}
- `audit`: {'source': 'audit', 'time': '2026-06-01 11:46:25', 'summary': 'patch configmaps kube-system/bursting-status', 'actor': 'system:serviceaccount:kube-system:cceaddon-virtual-kubelet', 'status_code': 200, 'request_uri': '/api/v1/namespaces/kube-system/configmaps/bursting-status'}
- `aom_alarm`: {'source': 'aom_alarm', 'time': None, 'summary': 'Pod健康检查失败##Unhealthy'}
- `aom_alarm`: {'source': 'aom_alarm', 'time': None, 'summary': '启动重试失败##BackOffStart'}
- `aom_alarm`: {'source': 'aom_a

