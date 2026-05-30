# huawei-cloudnative-skills

华为云云原生运维 Skill 集合，面向 CCE、AOM、LTS、ELB、EIP、VPC、ECS、HSS 等云服务，提供资源查询、可观测上下文、告警关联、故障诊断、巡检和恢复预案能力。

## 简化后的多 Skill 架构

第一阶段不引入复杂 `skill-router`，也不建设完整 runtime 平台。每个 skill 仍然是独立目录，但共享根目录 `scripts` 下的 Python 能力：

```text
skills/<skill>/SKILL.md
skills/<skill>/skill-profile.yaml
skills/<skill>/manifest.json
skills/<skill>/references/*.md
skills/<skill>/scripts -> ../../scripts

scripts/huawei-cloud.py
scripts/huawei_cloud/dispatcher.py
```

`skills/_catalog/skill-index.md` 是人和 agent 的总目录，不是 skill。它说明 L1-L7 分类、第一阶段启用的 skill、常见问题应该找哪个 skill。

`skill-profile.yaml` 是机器可读的工具边界。生成器读取 profile 中的 `tools`，再从 `dispatcher.py` 的 `ACTION_SPECS` 生成最小 `manifest.json`。

## 第一阶段 Skill

- `observability-context-builder`：汇聚告警、指标、日志、事件上下文。
- `alarm-correlation-engine`：AOM active/history 告警归并、去重、分级。
- `pod-failure-diagnoser`：Pod 单资源异常诊断。
- `workload-failure-diagnoser`：发布失败、滚动升级卡住、副本不满足和探针异常诊断。
- `node-failure-diagnoser`：节点 NotReady、资源压力、NPD、漏洞诊断。
- `network-failure-diagnoser`：Service、Ingress、ELB、EIP、NAT、VPC 链路诊断。
- `root-cause-analyzer`：跨域根因分析和诊断报告。
- `auto-remediation-runner`：恢复动作预览、确认、执行后验证。
- `daily-cluster-inspector`：每日巡检、快检、深度巡检。
- `cost-optimization-advisor`：空闲资源、过量 Request、低利用率节点、HPA/autoscaler 弹性策略优化建议和 HPA 配置预览；组合 action 为 `huawei_analyze_cce_cost_optimization`。
- `availability-risk-scanner`：单副本、PDB 缺失、健康检查、亲和性、AZ 均衡、网关和核心插件可用性风险扫描；组合 action 为 `huawei_scan_cce_availability_risk`。
- `capacity-trend-forecaster`：1 小时到 1 个月的周期性容量趋势分析、资源瓶颈预测、弹性策略模拟、曲线图、历史记录比对和 HPA/autoscaler 优化建议；组合 action 为 `huawei_analyze_cce_capacity_trend`。
- `container-migration-planner`：迁移盘点、依赖矩阵、交付方案。

## 初始化链接

Windows 下运行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\dev\create_skill_links.ps1
```

脚本会为每个带 `skill-profile.yaml` 的 skill 创建 `scripts` SymbolicLink；如果权限不足，则回退为 Junction。不要把根目录 `scripts` 复制到每个 skill。

## 生成 Manifest

```powershell
python scripts\dev\generate_manifests.py
python scripts\dev\generate_manifests.py --check
```

如果本机没有 `python` 命令，可以使用 Codex 桌面自带 Python 或系统 Python 的完整路径运行同一脚本。

## 校验

```powershell
python scripts\dev\validate_skills.py
python scripts\test_skill_profiles.py
python scripts\test_manifest_generation.py
python scripts\test_skill_links.py
python scripts\test_modular_dispatch.py
```

`validate_skills.py` 和 manifest 生成器只做静态校验，不访问华为云 API，不需要 AK/SK。

## 安全约束

- 禁止把 AK/SK、token、证书、真实 project_id 写入仓库。
- 禁止在脚本或测试里默认传 `confirm=true`。
- 所有删除、扩缩容、drain、reboot、HSS 状态变更等动作必须先预览，再由用户明确确认。
- `auto-remediation-runner` 负责恢复类高风险动作；`cost-optimization-advisor` 和 `capacity-trend-forecaster` 只允许 HPA 配置预览，真实应用必须由用户明确确认。
- 诊断类、巡检类、迁移规划类 skill 只执行只读查询和报告生成。
