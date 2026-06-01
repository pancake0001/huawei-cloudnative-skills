# Skill参考

> **说明：**
> 本章节面向使用CCE（云容器引擎）及相关云服务的开发者、运维工程师和架构师，介绍华为云云原生Skill的能力定位、使用方式和详细参考。
---

## 1 Skill概述

### 1.1 什么是Skill

Skill（技能）是将专业知识、操作流程和最佳实践转化为**可复用能力单元**的开放能力。

在AI Agent体系中，Skill用于扩展Agent的专业领域能力，使Agent能够按照预定义的流程和规则，自动执行特定领域的复杂任务。

Skill的核心特点：

- **意图驱动**：Agent通过读取Skill的description描述，自动理解何时应该触发该Skill，无需用户显式指定。
- **场景编排**：单个Skill内部串联多个操作步骤，自动完成上下文收集、分析和结论输出。
- **可复用**：同一个Skill可以在不同的Agent平台（Web、CLI、API）上运行，无需为每个平台单独适配。
- **可组合**：多个Skill可以按工作流组合使用，Agent会根据任务需要自动选择和调用合适的Skill。
- **安全护栏**：Skill内部定义风险约束，高危操作必须经过预览和用户确认。

华为云云原生Skill将华为云CCE、AOM、LTS、ELB、ECS、HSS等云服务的运维能力，按照故障诊断、可观测分析、巡检治理、自动恢复等场景封装为一系列Skill，使AI Agent具备专业的云原生运维能力。

### 1.2 适用场景

本Skill主要适用于以下场景：

- **故障诊断**：Pod CrashLoopBackOff、节点NotReady、Ingress 502、PVC Pending等。
- **可观测分析**：汇聚AOM告警、LTS日志、K8s事件、Pod/Node指标形成诊断上下文。
- **巡检治理**：每日集群健康检查、容量趋势预测、成本优化建议、可用性风险扫描。
- **自动恢复**：扩缩容、cordon/drain节点、重启ECS、HSS漏洞修复等受控变更。
- **交付方案**：容器迁移规划、资源盘点、依赖矩阵分析。
- **集群管理**：CCE集群升级规划、工作负载管理、UCS集群纳管与策略治理。

### 1.3 安全约束与风险分级

所有涉及变更的操作均遵循风险分级机制：

| 风险级别 | 示例 | 默认行为 |
|---------|------|---------|
| **R0** | list/get/query/analyze | 直接执行 |
| **R1** | 生成报告、方案、看板 | 直接执行 |
| **R2** | 重启异常Pod、查询后建议 | 默认预览，可配置自动执行 |
| **R3** | 扩容、回滚、cordon、uncordon | 必须`confirm=true` |
| **R4** | 删除集群、drain、休眠生产集群 | 必须`confirm=true` + 强风险提示 |
| **R5** | 清空数据、不可逆跨域删除 | 默认禁止 |

**核心安全约束**：

- 禁止在脚本、日志、报告中输出AK/SK。
- 所有删除、扩缩容、drain、reboot等动作必须先预览，再由用户明确确认。
- 临时kubeconfig和证书文件必须在使用后清理。
- 诊断类、巡检类、迁移规划类Skill只执行只读查询和报告生成。

---

## 2 使用说明

### 2.1 原理说明

Skill通过**意图匹配**机制工作：Agent读取Skill目录中 `SKILL.md` 文件头部的description描述，当用户输入的问题与description描述的场景匹配时，Agent自动触发该Skill。Skill内部定义了完整的处理流程、可调用的工具清单和风险约束，Agent按照Skill的指引逐步执行。

例如，当用户问"Pod一直重启怎么办"时，Agent读取到 `pod-failure-diagnoser` 的description为：

```yaml
---
name: pod-failure-diagnoser
description: Diagnose CCE Pod failures such as CrashLoopBackOff, ImagePullBackOff, OOMKilled, Pending, Evicted, restart storms, or workload unavailable.
---
```

Agent判断该问题与description匹配，于是自动触发 `pod-failure-diagnoser`，按照其定义的工作流执行诊断。

### 2.2 获取和使用Skill

华为云云原生Skill通过开放仓库提供：

- GitHub仓库：[huaweicloud/huaweicloud-skills](https://github.com/huaweicloud/huaweicloud-skills)
- CCE产品资料：[云容器引擎 CCE 文档](https://support.huaweicloud.com/intl/zh-cn/cce/index.html)

#### Skill包结构

每个Skill采用自包含目录结构，包含运行该能力所需的说明和配套文件：

```text
skill-name/
├── SKILL.md       # Skill定义文件，唯一入口
├── references/    # 参考资料
├── scripts/       # 可执行脚本
├── templates/     # 模板文件
└── demo/          # 演示样例
```

#### 安装方式

**方式一：使用npx安装**

```bash
# 安装单个Skill
npx skills add huaweicloud/huaweicloud-skills --skill <skill-name>

# 安装全部Skill
npx skills add huaweicloud/huaweicloud-skills
```

**方式二：从GitHub仓库手动安装**

```bash
git clone https://github.com/huaweicloud/huaweicloud-skills.git

# 安装指定Skill
npx skills add <path>/huaweicloud-skills/skills/<skill-name>
```

不同Agent平台的加载路径和集成方式略有差异，参见“附录A：在各Agent平台中使用”。

#### 认证配置

使用华为云产品相关Skill前，需要根据目标云服务配置认证信息。

**交互式配置**

```text
Access Key Id: <your AK>
Secret Access Key: <your SK>
```

**使用KooCLI配置AccessKey认证**

```bash
hcloud configure set --cli-access-key="<your AK>" --cli-secret-key="<your SK>" --cli-mode="AKSK"
```

> **安全提示**
>
> - 仅在受信任的本地测试环境中使用明文AK/SK认证，避免凭证泄露。
> - 云上环境应遵循最小权限原则，并参考 [KooCLI安全配置要求](https://support.huaweicloud.com/productdesc-hcli/hcli_26_002.html)。
> - 禁止将AK/SK写入脚本、日志、报告或代码仓库。

---

## 3 详细参考

### 3.1 概述

华为云云原生Skill围绕云原生资源管理和持续运维场景组织，覆盖资源生命周期、可观测与告警、故障诊断与恢复、巡检治理、解决方案交付以及多云多集群管理等能力域。

每个Skill均以独立目录提供，包含能力说明、适用场景和必要的参考资料。用户可以根据业务需求选择单个Skill，也可以组合多个Skill完成跨服务、跨步骤的运维任务。以下章节按能力域列出可用Skill。

### 3.2 生命周期与资源管理

生命周期与资源管理包含 CCE、CCI、SWR 三类产品能力。产品名称仅用于分组，下面表格中的每一行才是一个独立 Skill。

#### 3.2.1 CCE

| Skill | 目录路径 | 能力说明 |
| --- | --- | --- |
| `huawei-cloud-cce-cluster-management` | `skills/huawei-cloud-cce-cluster-management` | 管理 CCE 集群、节点池、节点、插件、EIP 和 kubeconfig 的全生命周期。 |
| `cce-cluster-upgrade-planner` | `skills/cce/cce-cluster-upgrade-planner` | 规划 CCE Kubernetes 版本升级，检查升级路径、插件兼容性、差异项和升级窗口。 |
| `cce-workload-manager` | `skills/cce/cce-workload-manager` | 管理 CCE 工作负载及 Kubernetes 资源，包括 Deployment、StatefulSet、DaemonSet、Job、CronJob、HPA、Service、Ingress 和配置资源。 |

#### 3.2.2 CCI

| Skill | 目录路径 | 能力说明 |
| --- | --- | --- |
| `huawei-cloud-cci-instance-management` | `skills/cci/huawei-cloud-cci-instance-management` | 管理 CCI 容器实例，包括 Namespace、网络、Deployment、StatefulSet、Pod、EIPPool、日志和指标。 |

#### 3.2.3 SWR

| Skill | 目录路径 | 能力说明 |
| --- | --- | --- |
| `huawei-cloud-swr-image-management` | `skills/swr/huawei-cloud-swr-image-management` | 管理 SWR 命名空间、镜像仓库、标签、登录凭证和配额。 |
| `huawei-cloud-swr-image-governance` | `skills/swr/huawei-cloud-swr-image-governance` | 管理 SWR 权限、保留策略、共享策略、委托和不可变规则。 |
| `huawei-cloud-swr-image-automation` | `skills/swr/huawei-cloud-swr-image-automation` | 管理 SWR 镜像同步、触发器和自动部署流程。 |
| `huawei-cloud-swr-enterprise-instance` | `skills/swr/huawei-cloud-swr-enterprise-instance` | 管理 SWR 企业实例、实例内命名空间、仓库、制品、凭证、端点和域名。 |

### 3.3 可观测与智能告警

| Skill | 目录路径 | 能力说明 |
| --- | --- | --- |
| `observability-context-builder` | `skills/observability-context-builder` | 汇聚 AOM 告警、指标、LTS 日志、Pod 日志和 Kubernetes 事件，形成诊断上下文。 |
| `alarm-correlation-engine` | `skills/alarm-correlation-engine` | 关联分析 AOM active/history 告警，完成去重归并、严重级别分组和告警规则核对。 |
| `log-analyzer` | `skills/log-analyzer` | 查询和分析 Pod 标准输出、CCE LogConfig 应用日志和 LTS 日志。 |
| `kubernetes-event-analyzer` | `skills/kubernetes-event-analyzer` | 查询和分析 Kubernetes Warning 事件、重复模式及 Pod、Node、Workload 异常。 |
| `metric-analyzer` | `skills/metric-analyzer` | 查询和分析 CCE Pod、Node 及 ECS、ELB、EIP、NAT 指标，识别阈值异常。 |

### 3.4 故障诊断与自愈恢复

| Skill | 目录路径 | 能力说明 |
| --- | --- | --- |
| `pod-failure-diagnoser` | `skills/pod-failure-diagnoser` | 诊断 CrashLoopBackOff、ImagePullBackOff、OOMKilled、Pending、Evicted 和频繁重启等 Pod 故障。 |
| `workload-failure-diagnoser` | `skills/workload-failure-diagnoser` | 诊断 Deployment、StatefulSet、DaemonSet 发布失败、滚动升级卡住、副本不足和探针异常。 |
| `node-failure-diagnoser` | `skills/node-failure-diagnoser` | 诊断 Node NotReady、资源压力、NPD、CNI、kubelet 和容器运行时异常。 |
| `autoscaling-diagnoser` | `skills/autoscaling-diagnoser` | 诊断 HPA、Cluster Autoscaler 和 CCE 弹性引擎链路故障。 |
| `network-failure-diagnoser` | `skills/network-failure-diagnoser` | 诊断 Service、DNS、Ingress、NetworkPolicy、ELB、EIP、NAT 和 VPC 网络故障。 |
| `storage-failure-diagnoser` | `skills/storage-failure-diagnoser` | 诊断 PVC、PV、EVS、SFS、OBS、挂载、容量和删除保护相关故障。 |
| `root-cause-analyzer` | `skills/root-cause-analyzer` | 汇总跨域证据，输出 Top 根因、影响范围、置信度和恢复交接。 |
| `change-impact-analyzer` | `skills/change-impact-analyzer` | 分析发布、配置、网络、安全策略和节点变更造成的故障影响。 |
| `dependency-impact-analyzer` | `skills/dependency-impact-analyzer` | 基于 Service、Ingress、Pod 和 Node 拓扑分析故障传播路径和上下游影响。 |
| `auto-remediation-runner` | `skills/auto-remediation-runner` | 生成并执行受控恢复动作，所有高风险变更默认预览并要求明确确认。 |

### 3.5 巡检、治理与持续运维

| Skill | 目录路径 | 能力说明 |
| --- | --- | --- |
| `daily-cluster-inspector` | `skills/daily-cluster-inspector` | 执行周期性 CCE 健康检查、快速巡检和持续运维摘要。 |
| `availability-risk-scanner` | `skills/availability-risk-scanner` | 扫描高可用、AZ 分布、单副本、PDB、探针、亲和性、网关和资源超配风险。 |
| `capacity-trend-forecaster` | `skills/capacity-trend-forecaster` | 分析周期性容量趋势，预测资源瓶颈，模拟 HPA 和节点弹性策略。 |
| `cost-optimization-advisor` | `skills/cost-optimization-advisor` | 分析空闲资源、过量 Request、低利用率节点和弹性策略优化机会。 |
| `ops-report-generator` | `skills/ops-report-generator` | 汇总巡检、容量、可用性、成本和 on-call 上下文，生成周报、月报、SLA、容量和稳定性报告。 |

### 3.6 解决方案与交付

| Skill | 目录路径 | 能力说明 |
| --- | --- | --- |
| `cce-cci-bursting-deployer` | `skills/cce-cci-bursting-deployer` | 配置、部署并验证 CCE 到 CCI 2.0 的弹性扩容能力，包括 VPCEP、virtual-kubelet 和冒烟验证。 |
| `container-migration-planner` | `skills/container-migration-planner` | 盘点容器平台资源和依赖，输出迁移批次、风险和验证方案，不执行真实迁移。 |
| `全链路压测` | `skills/pressure-test` | 构建从 k6 客户端经 ELB、nginx-ingress 到业务 Pod 的压测链路，收集观测数据并输出性能报告。 |

### 3.7 多云、多集群管理

UCS 相关 Skill 统一放在本分类，不再混入 CCE 生命周期管理。

| Skill | 目录路径 | 能力说明 |
| --- | --- | --- |
| `ucs-cluster-onboarding-manager` | `skills/ucs/ucs-cluster-onboarding-manager` | 管理 UCS 集群纳管、生命周期、舰队分组、kubeconfig 和资源配额。 |
| `ucs-policy-governor` | `skills/ucs/ucs-policy-governor` | 管理 UCS 策略实例、策略定义、启停操作、执行状态和舰队合规审计。 |

### 3.8 使用方式

Agent 根据各 Skill 的 `SKILL.md` 中的 `description` 自动匹配能力。需要人工定位时，先按本文档找到目标 Skill，再进入对应目录查看完整说明和引用资料。

---

## 4 附录

### 4.1 附录A：在各Agent平台中使用

#### 在OpenCode中使用

OpenCode是面向终端的AI编程助手，支持通过项目目录或用户目录加载Skill。

**项目级Skill：**

将Skill目录放入项目根目录的 `skills/` 文件夹下：

```text
my-project/
├── src/
├── skills/
│   ├── pod-failure-diagnoser/
│   │   ├── SKILL.md
│   │   ├── manifest.json
│   │   ├── skill-profile.yaml
│   │   └── references/
│   ├── node-failure-diagnoser/
│   └── ...
```

OpenCode启动时会自动扫描项目目录下的 `skills/` 文件夹，加载所有Skill。用户可以直接在对话中描述问题，Agent根据description自动匹配合适的Skill。

**用户级Skill：**

将Skill目录放入用户配置目录：

- **Windows**：`%USERPROFILE%\.opencode\skills\`
- **Linux/macOS**：`~/.opencode/skills/`

用户级Skill对所有项目生效，适合放置通用的运维Skill。

**使用示例：**

```bash
# 进入项目目录
cd my-project

# 启动OpenCode，Skill已自动加载
opencode

# 在对话中描述问题
> 我的Pod一直在重启，帮我看看
# Agent自动触发 pod-failure-diagnoser
```

#### 在OpenClaw中使用

OpenClaw是一个开源、自托管的Gateway，用于将聊天应用和渠道接入AI Agent。用户可以在本地或自有服务器上运行Gateway，并通过Skill扩展Agent能力。

OpenClaw可以从以下目录加载Skill：

| 目录 | 说明 |
|------|------|
| `<workspace>/skills/` | 当前工作区Skill，适合项目级定制 |
| `<workspace>/.agents/skills/` | 当前工作区内的Agent项目级Skill |
| `~/.agents/skills/` | 多个Agent可共享的Skill |
| `~/.openclaw/skills/` | OpenClaw管理的Skill |
| `skills.load.extraDirs` | 通过配置追加的Skill目录 |

OpenClaw还会加载安装时自带的Skill。将需要使用的Skill目录复制到相应的加载目录即可。例如：

```bash
mkdir -p ~/.agents/skills
cp -R ./skills/pod-failure-diagnoser ~/.agents/skills/
cp -R ./skills/node-failure-diagnoser ~/.agents/skills/
```

每个Skill目录应包含 `SKILL.md`。OpenClaw加载Skill后，Agent可以根据用户意图选择合适的Skill，并按其中定义的工作流执行任务。

关于OpenClaw的定位、Skill加载顺序和目录说明，参见 [OpenClaw文档](https://docs.openclaw.ai/) 和 [OpenClaw Skills](https://docs.openclaw.ai/tools/skills)。

#### 在Hermes中使用

Hermes是面向企业级AI Agent的服务编排平台，支持通过声明式配置集成Skill。

**配置Skill：**

在Hermes的Agent配置文件中声明要加载的Skill：

```yaml
# hermes-agent.yaml
agent:
  name: cce-ops-agent
  skills:
    - source: git
      url: https://github.com/huaweicloud/huaweicloud-skills.git
      path: skills/pod-failure-diagnoser
    - source: git
      url: https://github.com/huaweicloud/huaweicloud-skills.git
      path: skills/daily-cluster-inspector
    - source: local
      path: /opt/skills/auto-remediation-runner
```

Hermes启动时会从指定源拉取Skill，解析 `SKILL.md` 和 `manifest.json`，将工具注册到Agent的工具链中。

**工作流编排：**

Hermes支持通过工作流模板组合多个Skill：

```yaml
# workflow.yaml
name: daily-ops-workflow
triggers:
  - schedule: "0 9 * * *"  # 每天9点
tasks:
  - skill: daily-cluster-inspector
    output: inspection_result
  - skill: alarm-correlation-engine
    input:
      alarms: "{{ inspection_result.alarms }}"
    output: alarm_analysis
  - skill: ops-report-generator
    input:
      inspection: "{{ inspection_result }}"
      alarms: "{{ alarm_analysis }}"
    output: report
actions:
  - type: notify
    target: ops-team@example.com
    content: "{{ report }}"
```

**通过MCP协议使用：**

Hermes支持Model Context Protocol（MCP），Skill可以通过MCP server方式暴露工具：

```json
{
  "mcpServers": {
    "huawei-cloudnative-skills": {
      "type": "stdio",
      "command": "python",
      "args": ["scripts/huawei-cloud.py", "--mcp"]
    }
  }
}
```

连接后，Hermes的Agent可以直接调用所有云原生Skill中定义的工具。

### 4.2 附录B：常见问题路由

当用户描述问题时，可参考下表快速定位推荐Skill：

| 用户问题 | 推荐Skill |
|---------|----------|
| Pod一直重启、Pending、OOMKilled | `pod-failure-diagnoser` |
| 发布失败、滚动升级卡住、副本不满足 | `workload-failure-diagnoser` |
| 节点NotReady、资源压力、节点漏洞 | `node-failure-diagnoser` |
| HPA不扩Pod、CA不扩节点、自动弹性不生效 | `autoscaling-diagnoser` |
| Ingress 502、Service不通、ELB链路异常 | `network-failure-diagnoser` |
| PVC Pending、FailedMount、容量耗尽 | `storage-failure-diagnoser` |
| CCE告警很多，需要合并分析 | `alarm-correlation-engine` |
| 查询Pod标准输出或LTS应用日志 | `log-analyzer` |
| 分析Kubernetes事件趋势 | `kubernetes-event-analyzer` |
| 查询CCE Pod/Node指标和资源使用排名 | `metric-analyzer` |
| 需要汇聚日志、事件、指标、告警 | `observability-context-builder` |
| 业务不可用，需要综合根因分析 | `root-cause-analyzer` |
| 发布、配置、网络、安全策略或节点变更后出现故障 | `change-impact-analyzer` |
| 某个服务故障会影响哪些入口和上下游 | `dependency-impact-analyzer` |
| 需要扩容、重启、drain、漏洞修复 | `auto-remediation-runner` |
| 做每日巡检或周期性健康检查 | `daily-cluster-inspector` |
| 做成本优化、Request过量分析 | `cost-optimization-advisor` |
| 做容量趋势预测、弹性模拟 | `capacity-trend-forecaster` |
| 做可用性风险扫描、PDB/探针检查 | `availability-risk-scanner` |
| 做周报、月报、SLA运维报告 | `ops-report-generator` |
| 做容器迁移方案和资源盘点 | `container-migration-planner` |
| CCE到CCI弹性扩容配置 | `cce-cci-bursting-deployer` |
| CCE集群版本升级规划 | `cce-cluster-upgrade-planner` |
| CCE/UCS工作负载管理 | `cce-workload-manager` |
| UCS集群纳管和舰队管理 | `ucs-cluster-onboarding-manager` |
| UCS策略治理和合规审计 | `ucs-policy-governor` |
| SWR镜像生命周期管理 | `huawei-cloud-swr-image-management` |
| SWR镜像治理 | `huawei-cloud-swr-image-governance` |
| SWR镜像自动化 | `huawei-cloud-swr-image-automation` |
| 压力测试方案和执行 | `全链路压测` |

### 4.3 附录C：术语表

| 术语 | 说明 |
|------|------|
| **Skill** | 将专业知识、操作流程和最佳实践转化为可复用能力单元的开放能力 |
| **Action** | Skill暴露的具体操作，对应脚本中的一个函数调用 |
| **Dispatcher** | 脚本层的请求分发器，负责将action路由到对应的服务模块 |
| **Profile** | Skill的元数据声明文件（skill-profile.yaml），定义Skill的能力边界 |
| **Manifest** | 机器可读的Skill工具声明文件（manifest.json），供Agent集成使用 |
| **R0-R5** | 风险等级，R0为只读，R5为禁止自动化 |
| **AIOps** | 人工智能运维 |
| **UCS** | 华为云统一云服务（Universal Cloud Service），多云管理平台 |
| **SWR** | 软件容器镜像仓库（Software Repository for Container） |
| **Fleet** | UCS舰队分组，用于多集群统一管理 |
| **HPA** | Horizontal Pod Autoscaler，Pod水平自动伸缩 |
| **CA** | Cluster Autoscaler，集群自动伸缩 |

### 4.4 附录D：限制说明

- 当前Skill主要面向CCE集群及其关联云服务（AOM、LTS、ELB、ECS、HSS等）。
- CCI、CCE-AP等产品的Skill正在陆续扩展中。
- UCS多集群联邦管理和策略治理能力当前处于活跃开发阶段。
- 所有变更类Action默认预览模式，不自动执行。

### 4.5 附录E：相关文档

| 文档 | 说明 | 路径 |
|------|------|------|
| CCE产品资料 | 云容器引擎CCE官方文档 | [华为云CCE文档](https://support.huaweicloud.com/intl/zh-cn/cce/index.html) |
| Skill开放仓库 | 华为云云原生Skill代码仓库 | [huaweicloud/huaweicloud-skills](https://github.com/huaweicloud/huaweicloud-skills) |
| 项目README | 项目概述和快速开始 | `README.md` |
| Skill索引 | 完整Skill列表和路由 | `skills/_catalog/skill-index.md` |
| 参数处理规范 | API参数处理最佳实践 | `docs/superpowers/skill-api-parameter-guidelines.md` |
| CCE模块拆分计划 | CCE脚本模块化设计 | `docs/superpowers/cce-split-plan.md` |

### 4.6 附录F：版本记录

| 版本 | 日期 | 变更内容 |
|------|------|---------|
| 1.2.2 | 2026-06-01 | 调整Skill概述，仅说明Skill与API、SDK在产品资料目录中的同级关系 |
| 1.2.1 | 2026-06-01 | 完善Skill安装和认证说明；修正OpenClaw定位与加载方式；精简详细参考中的维护口径和重复说明 |
| 1.2.0 | 2026-06-01 | 新增Skill参考章节；补充GitHub获取说明；将平台集成说明迁入附录；按六类能力域重组详细参考 |
| 1.1.0 | 2026-06-01 | 新增autoscaling-diagnoser、metric-analyzer、change-impact-analyzer、dependency-impact-analyzer、cce-cluster-upgrade-planner、cce-workload-manager、ucs-cluster-onboarding-manager、ucs-policy-governor、SWR镜像管理系列Skill |
| 1.0.0 | 2026-05-31 | 初始版本，包含核心Skill参考 |
