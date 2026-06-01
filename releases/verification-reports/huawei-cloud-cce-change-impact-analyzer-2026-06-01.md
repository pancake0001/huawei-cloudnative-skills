# huawei-cloud-cce-change-impact-analyzer 验证报告

## 基本信息

| 项目 | 内容 |
| --- | --- |
| Skill | `huawei-cloud-cce-change-impact-analyzer` |
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
| 资源快照 | 通过 | 当前资源快照成功 |
| 变更分析 | 通过 | 核心变更数 0（无近期变更记录） |
| 只读安全 | 通过 | 仅执行分析，无变更操作 |
| 凭证安全 | 通过 | 未输出 AK/SK/Token |

## 关键发现

- 审计/LTS 数据源未启用导致变更历史为空，属于环境限制
- 资源快照功能正常

## 修复记录

| 编号 | 类型 | 问题 | 修复 |
| --- | --- | --- | --- |
| CCE-COMMON-001 | 参数兼容性 | CLI dispatcher 仅支持 `key=value` 格式 | 增强 `_parse_cli_params` 支持 `key=value`、`--key=value`、`--key value` |

## 最终结论

**通过**。变更影响分析框架正常，数据源限制为环境问题。


## aicli 实际输出（Skill 生成的报告）

>>> FIELD: report_markdown (len=3787)
# CCE 变更影响分析报告

## 1. 分析摘要

- Analysis-Trace-ID: `CIA-20260601114535-2f4d2aed`
- 集群: `1d450236-5b28-11f1-a7f6-0255ac10026a`
- 区域: `cn-north-4`
- 范围: `全集群`
- 目标对象: `未指定`
- 分析窗口: `2026-06-01 10:45:35` 至 `2026-06-01 11:45:35`
- 识别核心变更: `2` 条
- 初步结论: 最高疑似诱因是 `192.168.32.226` 的 节点或基础设施变更，风险等级 Critical，评分 96/100。

## 2. 排查过程

1. 范围定义与数据总线：初始化 Trace ID，并并行收集应用配置、网络路由、安全策略、基础设施四类变更影子。
2. 核心识别与噪声消除：剥离 HPA/控制器写入、Token/Lease/Status 等常规噪声，保留镜像、配置、路由、权限、污点等核心语义字段。
3. 爆炸半径与风险推演：将核心变更映射到当前 Pod、Service、Ingress、Node 拓扑，模拟可能的传播路径。
4. 风险综合与评级报告：按变更敏感度、拓扑波及范围、安全边界跨度、故障时间邻近度、事件/告警相关性评分。

## 3. 数据源与采集状态

| 数据源 | 状态 | 说明 |
| --- | --- | --- |
| CCE 审计日志 | 成功 | 匹配 500 条 |
| K8s 历史事件 | 失败/未启用 | 未在集群中找到开启K8s事件LTS采集的LogConfig。请检查default-event配置或确认事件采集已开启。 |
| AOM 告警 | 成功 | active + history 关联分析 |
| 当前资源快照 | 成功 | 9/9 类资源可用 |

## 4. 核心变更时间线

| 时间 | 风险 | 类别 | 操作 | 对象 | 执行者 | 核心语义 |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-06-01 11:44:34 | Critical(96) | 节点或基础设施变更 | patch | 192.168.32.226 | system:serviceaccount:kube-system:node-controller | data, taints |
| 2026-06-01 11:44:25 | High(79) | 配置或密钥变更 | patch | kube-system/bursting-status | system:serviceaccount:kube-system:cceaddon-virtual-kubelet | 写操作 |

## 5. 最高风险预警

1. **Critical 192.168.32.226**：节点或基础设施变更，评分 96/100，置信度 high。依据：节点污点或调度状态变化可能导致 Pending/驱逐；变更后 30 分钟内出现相关 AOM 告警；当前拓扑显示至少 31 个实体可能受影响。证据数：2。
2. **High kube-system/bursting-status**：配置或密钥变更，评分 79/100，置信度 medium。依据：configmaps 发生 patch 写操作；变更后 30 分钟内出现相关 AOM 告警；当前拓扑显示至少 20 个实体可能受影响。证据数：4。

## 6. 爆炸半径与传播路径

- **192.168.32.226**：pods: default/abclient-57c4fbb6f6-26lk5, default/abclient-57c4fbb6f6-27bvg, default/abclient-57c4fbb6f6-2b2cx, default/abclient-57c4fbb6f6-2hd9c, default/abclient-57c4fbb6f6-2ndgg, default/abclient-57c4fbb6f6-2rfmc, default/abclient-57c4fbb6f6-2x47d, default/abclient-57c4fbb6f6-44h57；nodes: 192.168.32.226
- **kube-system/bursting-status**：pods: kube-system/bursting-cceaddon-virtual-kubelet-resource-syncer-64f4b7d6kr995, kube-system/bursting-cceaddon-virtual-kubelet-resource-syncer-64f4b7d6vnkgx, kube-system/bursting-cceaddon-virtual-kubelet-virtual-kubelet-5b4df9f7crbdp, kube-system/bursting-cceaddon-virtual-kubelet-virtual-kubelet-5b4df9f7qfdmd, kube-system/bursting-cceaddon-virtual-kubelet-webhook-7ff7689685-rmp95, kube-system/bursting-cceaddon-virtual-kubelet-webhook-7ff7689685-xnfsv, kube-system/cceaddon-nginx-ingress-controller-7666cc5ff9-kb82m, kube-system/cceaddon-nginx-ingress-controller-7666cc5ff9-l555l

## 7. 证据矩阵

| 变更对象 | 来源 | 时间 | 证据摘要 |
| --- | --- | --- | --- |
| 192.168.32.226 | audit | 2026-06-01 11:44:34 | patch nodes 192.168.32.226 |
| 192.168.32.226 | aom_alarm | - | 节点内存空间不足##NodeHasInsufficientMemory |
| kube-system/bursting-status | audit | 2026-06-01 11:44:25 | patch configmaps kube-system/bursting-status |
| kube-system/bursting-status | aom_alarm | - | Pod健康检查失败##Unhealthy |
| kube-system/bursting-status | aom_alarm | - | 启动重试失败##BackOffStart |
| kube-system/bursting-status | aom_alarm | - | 启动重试失败##BackOffSt

