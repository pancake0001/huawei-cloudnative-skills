# Releases Skill 验证跟踪表

用途：记录 `releases` 目录下所有 skill 在真实 `aicli` 环境中的验证进度、问题、修复和报告链接。

当前基线：

| 项目 | 值 |
| --- | --- |
| Skill 总数 | 34（含 DevTools）；云原生业务 skill 为 33 |
| aicli 环境 | CCE 集群 `aicli` 命名空间，Pod `aicli-dcfcf5595-4gf22` |
| aicli 版本 | `v1.0.0-beta.2` |
| 当前验证日期 | 2026-06-01 |
| 默认区域 | `cn-north-4` |
| 默认集群 ID | `1d450236-5b28-11f1-a7f6-0255ac10026a` |
| CCE 验证进度 | 26/26 已通过 |

状态枚举：

| 状态 | 含义 |
| --- | --- |
| 待验证 | 尚未在真实 aicli 环境执行 |
| 验证中 | 已开始执行，结果未完成 |
| 通过 | 已在真实 aicli 环境验证通过 |
| 有问题 | 发现不可用、逻辑错误、安全风险或体验问题 |
| 已修复 | 已提交修复并验证通过 |

## aicli 真实环境验证范式

### 1. 领取范围

- 每次领取 1 个 skill，优先选择下表中 `待验证` 的行。
- 避免同时修改同一个 skill 或同一个报告文件。
- 每个 skill 单独生成报告：`releases/verification-reports/<skill-name>-YYYY-MM-DD.md`。
- 发现问题进行修复后，需要重新在真实环境验证，确认问题闭环。

### 2. 进入真实 aicli 环境

```bash
kubectl get pod -n aicli
kubectl exec -it -n aicli aicli-dcfcf5595-4gf22 -- sh -lc '
  export PATH=/root/.huawei/bin:$PATH
  cd /root/.agents/skills/<skill-name>
  aicli chat --compatible --cwd /root/.agents/skills/<skill-name> --resume=false
'
```

注意：已验证 `aicli chat --no-interactive` 不适合直接传 prompt，会报 `prompt is null`；当前稳定方式是 TTY 交互。

### 3. 统一验证 Prompt

```text
请使用 skill <skill-name> 在真实环境做一次验证。
要求：
1. 不输出任何 AK/SK/Token/Authorization。
2. 除非该 skill 本身是变更类能力，否则只执行只读命令。
3. 变更类 skill 只能做 preview/dry-run，不允许 confirm=true，不允许真实创建、删除、扩缩容。
4. 严格使用该 skill 文档指定的执行方式，例如 scripts/huawei-cloud.py 或 hcloud，不要私自替换工具。
5. 区域使用 cn-north-4；如是 CCE skill，cluster_id 优先使用环境变量 CCE_CLUSTER_ID。
6. 参考 releases/test-prompts.md 中该 skill 的测试用例，选择 1-2 个最安全、最能覆盖核心能力的场景。
7. 输出中文验证报告：是否触发正确 skill、实际执行命令、成功/失败、关键输出、发现的问题、风险等级、修复建议、结论。
```

### 4. 最小验证闭环

| 阶段 | 要求 |
| --- | --- |
| 安装检查 | 确认 `SKILL.md`、`scripts/`、`references/` 等关键文件存在 |
| 依赖检查 | 确认 Python、hcloud、kubectl、SDK 等 skill 所需依赖可用 |
| 环境检查 | 只检查必要环境变量是否存在，不打印密钥值 |
| 核心能力检查 | 执行 1 个该 skill 的主命令或主流程 |
| 辅助证据检查 | 执行 1 个 list/get/events/logs/metrics 等只读证据命令 |
| 安全检查 | 确认无 `confirm=true`、无真实写操作、无密钥输出 |
| 输出检查 | 确认输出结构、字段、报告内容符合 skill 文档中的 schema 或 acceptance criteria |

### 5. 问题判定规则

| 情况 | 记录方式 |
| --- | --- |
| 环境真实异常，例如 Pod Evicted、节点 MemoryPressure、资源不足 | 记录为环境发现，不直接判定 skill 不可用 |
| 文档和代码不一致、参数格式不兼容、命令不可执行、依赖缺失、输出 schema 缺字段 | 记录为 skill 问题 |
| 能小范围修复的问题 | 修复本地仓库后同步到容器验证 |
| 变更类能力 | 只允许 preview/dry-run，禁止真实执行 create/delete/scale/drain/install 等操作 |

容器内同步命令示例：

```bash
kubectl cp <local-file> aicli/aicli-dcfcf5595-4gf22:<container-file>
```

容器内同步仅作为验证手段，最终以本地仓库改动为准，后续需要重新构建镜像才能持久生效。

### 6. 单 skill 报告建议结构

- 基本信息：skill、aicli 版本、Pod、时间、区域、集群 ID、测试样本。
- 实际执行命令。
- 验证结果表：触发、主能力、辅助能力、安全、输出格式。
- 关键发现。
- 问题清单：编号、严重度、复现、影响、修复建议。
- 修复记录。
- 最终结论：通过 / 有问题 / 已修复。

一句话原则：每个 skill 独立验证，在真实 aicli 容器内按 skill 文档跑最小安全闭环，保留实际命令和结果，问题修复后验证闭环，最后写单 skill 报告，统一更新本总表。

| # | 类别 | Skill | 路径 | aicli 验证状态 | 验证结果 | 问题/风险 | 修复建议 | 是否已修复 | 验证报告 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | CCE | `huawei-cloud-cce-alarm-correlation-engine` | `releases/container/cce/huawei-cloud-cce-alarm-correlation-engine` | 通过 | AOM 告警巡检成功，原始告警聚合为 23 组，噪音削减 78.4% | 无安全风险；环境存在真实告警 | CCE-COMMON-001 | 是 | [报告](verification-reports/huawei-cloud-cce-alarm-correlation-engine-2026-06-01.md) |
| 2 | CCE | `huawei-cloud-cce-auto-remediation-runner` | `releases/container/cce/huawei-cloud-cce-auto-remediation-runner` | 通过 | preview 模式正确判断 Evicted 不适合自动回滚，未执行变更 | 无安全风险；保护逻辑生效 | CCE-COMMON-001 | 是 | [报告](verification-reports/huawei-cloud-cce-auto-remediation-runner-2026-06-01.md) |
| 3 | CCE | `huawei-cloud-cce-autoscaling-diagnoser` | `releases/container/cce/huawei-cloud-cce-autoscaling-diagnoser` | 通过 | 伸缩诊断成功，发现无 HPA/Autoscaler 插件 | 环境发现，不判定为 skill 缺陷 | CCE-COMMON-001 | 是 | [报告](verification-reports/huawei-cloud-cce-autoscaling-diagnoser-2026-06-01.md) |
| 4 | CCE | `huawei-cloud-cce-availability-risk-scanner` | `releases/container/cce/huawei-cloud-cce-availability-risk-scanner` | 通过 | 扫描 11 节点、18 工作负载、1182 Pod，参数兼容性已验证 | 环境存在真实告警，无 skill 安全风险 | CCE-COMMON-001 | 是 | [报告](verification-reports/huawei-cloud-cce-availability-risk-scanner-2026-06-01.md) |
| 5 | CCE | `huawei-cloud-cce-capacity-trend-forecaster` | `releases/container/cce/huawei-cloud-cce-capacity-trend-forecaster` | 通过 | 容量趋势分析成功，生成 122 个序列点和 3 条建议 | 无安全风险 | CCE-COMMON-001 | 是 | [报告](verification-reports/huawei-cloud-cce-capacity-trend-forecaster-2026-06-01.md) |
| 6 | CCE | `huawei-cloud-cce-cci-bursting-deployer` | `releases/container/cce/huawei-cloud-cce-cci-bursting-deployer` | 通过 | CCE to CCI bursting 预检查成功，issues=0 | 未执行部署或变更 | CCE-COMMON-001 | 是 | [报告](verification-reports/huawei-cloud-cce-cci-bursting-deployer-2026-06-01.md) |
| 7 | CCE | `huawei-cloud-cce-change-impact-analyzer` | `releases/container/cce/huawei-cloud-cce-change-impact-analyzer` | 通过 | 变更影响分析成功，当前资源快照成功，核心变更数 0 | 审计/LTS 数据源未启用为环境限制 | CCE-COMMON-001 | 是 | [报告](verification-reports/huawei-cloud-cce-change-impact-analyzer-2026-06-01.md) |
| 8 | CCE | `huawei-cloud-cce-cluster-management` | `releases/container/cce/huawei-cloud-cce-cluster-management` | 通过 | 集群、节点池、插件列表查询均通过 | 低风险：文档示例路径与 scripts/huawei-cloud.py 不一致 | CCE-COMMON-002（修正文档命令路径） | 是 | [报告](verification-reports/huawei-cloud-cce-cluster-management-2026-06-01.md) |
| 9 | CCE | `huawei-cloud-cce-cluster-upgrade-planner` | `releases/container/cce/huawei-cloud-cce-cluster-upgrade-planner` | 通过 | hcloud 只读查询集群、插件、节点池均通过 | 首次 PATH 未包含 /root/.huawei/bin，环境配置问题 | CCE-COMMON-001 + 显式设置 PATH | 是 | [报告](verification-reports/huawei-cloud-cce-cluster-upgrade-planner-2026-06-01.md) |
| 10 | CCE | `huawei-cloud-cce-container-migration-planner` | `releases/container/cce/huawei-cloud-cce-container-migration-planner` | 通过 | 迁移清单查询通过，default 下 3 Deployment、5 Service、0 PVC | 无安全风险 | CCE-COMMON-001 | 是 | [报告](verification-reports/huawei-cloud-cce-container-migration-planner-2026-06-01.md) |
| 11 | CCE | `huawei-cloud-cce-cost-optimization-advisor` | `releases/container/cce/huawei-cloud-cce-cost-optimization-advisor` | 通过 | 成本优化分析成功，扫描 11 节点、1130 Pod | 环境存在大量 Failed Pod | CCE-COMMON-001 | 是 | [报告](verification-reports/huawei-cloud-cce-cost-optimization-advisor-2026-06-01.md) |
| 12 | CCE | `huawei-cloud-cce-daily-cluster-inspector` | `releases/container/cce/huawei-cloud-cce-daily-cluster-inspector` | 通过 | huawei_cce_quick_check 成功，检测到副本不匹配异常 | 副本不匹配为环境异常 | CCE-COMMON-001 | 是 | [报告](verification-reports/huawei-cloud-cce-daily-cluster-inspector-2026-06-01.md) |
| 13 | CCE | `huawei-cloud-cce-dependency-impact-analyzer` | `releases/container/cce/huawei-cloud-cce-dependency-impact-analyzer` | 通过 | 依赖影响分析成功，风险等级 Medium，path_count=1 | 目标 workload 有 Evicted 历史 Pod | CCE-COMMON-001 | 是 | [报告](verification-reports/huawei-cloud-cce-dependency-impact-analyzer-2026-06-01.md) |
| 14 | CCE | `huawei-cloud-cce-kubernetes-event-analyzer` | `releases/container/cce/huawei-cloud-cce-kubernetes-event-analyzer` | 通过 | 事件查询成功，返回 MemoryPressure/Eviction 相关事件 | 环境真实事件，无 skill 风险 | CCE-COMMON-001 | 是 | [报告](verification-reports/huawei-cloud-cce-kubernetes-event-analyzer-2026-06-01.md) |
| 15 | CCE | `huawei-cloud-cce-log-analyzer` | `releases/container/cce/huawei-cloud-cce-log-analyzer` | 通过 | LogConfig、Pod logs、审计日志查询路径均可用 | 无安全风险 | CCE-COMMON-001 | 是 | [报告](verification-reports/huawei-cloud-cce-log-analyzer-2026-06-01.md) |
| 16 | CCE | `huawei-cloud-cce-metric-analyzer` | `releases/container/cce/huawei-cloud-cce-metric-analyzer` | 通过 | Pod/Node TopN 指标查询成功 | 节点 CPU/内存压力为环境发现 | CCE-COMMON-001 | 是 | [报告](verification-reports/huawei-cloud-cce-metric-analyzer-2026-06-01.md) |
| 17 | CCE | `huawei-cloud-cce-network-failure-diagnoser` | `releases/container/cce/huawei-cloud-cce-network-failure-diagnoser` | 通过 | 网络诊断成功，finding=1，top_causes=1 | 结论指向节点资源或网络压力 | CCE-COMMON-001 | 是 | [报告](verification-reports/huawei-cloud-cce-network-failure-diagnoser-2026-06-01.md) |
| 18 | CCE | `huawei-cloud-cce-node-failure-diagnoser` | `releases/container/cce/huawei-cloud-cce-node-failure-diagnoser` | 通过 | 节点诊断成功，参数兼容性已验证（含 --node-name 连字符归一化） | 目标节点有 MemoryProblem=True | CCE-COMMON-001 | 是 | [报告](verification-reports/huawei-cloud-cce-node-failure-diagnoser-2026-06-01.md) |
| 19 | CCE | `huawei-cloud-cce-observability-context-builder` | `releases/container/cce/huawei-cloud-cce-observability-context-builder` | 通过 | 监控上下文构建成功，生成本地 HTML dashboard | 无安全风险 | CCE-COMMON-001 | 是 | [报告](verification-reports/huawei-cloud-cce-observability-context-builder-2026-06-01.md) |
| 20 | CCE | `huawei-cloud-cce-ops-report-generator` | `releases/container/cce/huawei-cloud-cce-ops-report-generator` | 通过 | 使用 report_type=weekly 生成综合报告，recommendations=14 | 首次 daily 为未注册类型，改用合法类型后通过 | CCE-COMMON-001 | 是 | [报告](verification-reports/huawei-cloud-cce-ops-report-generator-2026-06-01.md) |
| 21 | CCE | `huawei-cloud-cce-pod-failure-diagnoser` | `releases/container/cce/huawei-cloud-cce-pod-failure-diagnoser` | 通过 | 核心诊断和事件查询均通过 | 低风险：验证文档 --region 参数格式与原 dispatcher 不兼容；凭证变量说明不一致 | CCE-COMMON-001（参数格式）+ CCE-COMMON-003（凭证变量） | 是 | [报告](verification-reports/huawei-cloud-cce-pod-failure-diagnoser-2026-06-01.md) |
| 22 | CCE | `huawei-cloud-cce-root-cause-analyzer` | `releases/container/cce/huawei-cloud-cce-root-cause-analyzer` | 通过 | 根因分析成功，top_causes=2，首要根因为 Evicted | 环境真实故障，无 skill 风险 | CCE-COMMON-001 | 是 | [报告](verification-reports/huawei-cloud-cce-root-cause-analyzer-2026-06-01.md) |
| 23 | CCE | `huawei-cloud-cce-storage-failure-diagnoser` | `releases/container/cce/huawei-cloud-cce-storage-failure-diagnoser` | 通过 | 存储诊断成功，findings=0，未命中明确存储根因 | 输出合理，无风险 | CCE-COMMON-001 | 是 | [报告](verification-reports/huawei-cloud-cce-storage-failure-diagnoser-2026-06-01.md) |
| 24 | CCE | `huawei-cloud-cce-workload-failure-diagnoser` | `releases/container/cce/huawei-cloud-cce-workload-failure-diagnoser` | 通过 | 发布诊断成功，Deployment abclient 当前 20/20 ready | 历史 Evicted 不影响当前发布状态 | CCE-COMMON-001 | 是 | [报告](verification-reports/huawei-cloud-cce-workload-failure-diagnoser-2026-06-01.md) |
| 25 | CCE | `huawei-cloud-cce-workload-manager` | `releases/container/cce/huawei-cloud-cce-workload-manager` | 通过 | hcloud 获取短期 kubeconfig 成功，kubectl 只读列出资源 | 首次 in-cluster SA RBAC 不足为环境限制 | 使用 hcloud kubeconfig 流程（非 script 类 skill） | 是 | [报告](verification-reports/huawei-cloud-cce-workload-manager-2026-06-01.md) |
| 26 | CCE | `huawei-cloud-cce-pressure-test` | `releases/container/cce/huawei-cloud-cce-pressure-test` | 通过 | client manifest 生成成功；run/route 不带 confirm 均正确返回 `requires_confirmation=true`；Service 只读查询成功 | 压测类变更保护生效；aicli 原始输出已入库 | CCE-COMMON-001（补齐新增 skill 参数解析） | 是 | [报告](verification-reports/huawei-cloud-cce-pressure-test-2026-06-01.md) |
| 27 | CCI | `huawei-cloud-cci-instance-management` | `releases/container/cci/huawei-cloud-cci-instance-management` | 待验证 | - | - | - | - | - |
| 28 | SWR | `huawei-cloud-swr-enterprise-instance` | `releases/container/swr/huawei-cloud-swr-enterprise-instance` | 待验证 | - | - | - | - | - |
| 29 | SWR | `huawei-cloud-swr-image-automation` | `releases/container/swr/huawei-cloud-swr-image-automation` | 待验证 | - | - | - | - | - |
| 30 | SWR | `huawei-cloud-swr-image-governance` | `releases/container/swr/huawei-cloud-swr-image-governance` | 待验证 | - | - | - | - | - |
| 31 | SWR | `huawei-cloud-swr-image-management` | `releases/container/swr/huawei-cloud-swr-image-management` | 待验证 | - | - | - | - | - |
| 32 | UCS | `ucs-cluster-onboarding-manager` | `releases/container/ucs/ucs-cluster-onboarding-manager` | 待验证 | - | - | - | - | - |
| 33 | UCS | `ucs-policy-governor` | `releases/container/ucs/ucs-policy-governor` | 待验证 | - | - | - | - | - |
| 34 | DevTools | `huawei-cloud-cli-guidance` | `releases/devtools/huawei-cloud-cli-guidance` | 待验证 | - | - | - | - | - |

备注：`releases/test-prompts.md` 原写的是 32 个云原生 skill；主干新增 `huawei-cloud-cce-pressure-test` 后统计口径为 26 CCE + 1 CCI + 4 SWR + 2 UCS。如果把 DevTools 的 `huawei-cloud-cli-guidance` 也纳入 `releases` 目录 skill 清单，则总表为 34 行。

## 通用修复记录

| 编号 | 问题 | 修复 | 影响范围 |
| --- | --- | --- | --- |
| CCE-COMMON-001 | 多个 `scripts/huawei-cloud.py` 的 CLI dispatcher 原本只稳定支持 `key=value`，与部分验证文档中的 `--key=value` / `--key value` 示例不一致；主干新增 `pressure-test` 后也命中同类问题 | 已增强 `_parse_cli_params`，支持 `key=value`、`--key=value`、`--key value`，并将 `--cluster-id` 归一为 `cluster_id` | 含 `scripts/huawei-cloud.py` 的 CCE skill（含本次 pressure-test 补齐） |
| CCE-COMMON-002 | `huawei-cloud-cce-cluster-management` 文档示例使用 `python3 huawei-cloud.py`，与实际 `scripts/huawei-cloud.py` 不一致 | 已修正 SKILL.md 与 references/verification-method.md | cluster-management |
| CCE-COMMON-003 | pod-failure-diagnoser 文档凭证变量说明与实际支持变量不一致 | 已校正为 HUAWEI_AK/HUAWEI_SK 或 HW_ACCESS_KEY/HW_SECRET_KEY | pod-failure-diagnoser |
