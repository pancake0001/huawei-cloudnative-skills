---
name: huawei-cloud-cce-network-failure-diagnoser
description: >
  使用 hcloud 获取华为云 CCE 集群和云侧网络元数据，并通过只读 kubectl-cce 证据诊断网络故障。 适用于 Service 不可达、DNS/CoreDNS 错误、Ingress
  502/504、NetworkPolicy 阻断、 EndpointSlice 或后端 Ready 异常、ELB 健康检查、EIP、NAT、VPC、安全组或 ACL 问题。
version: 1.0.0
tags: [huawei-cloud, cce, kubectl, network, diagnosis]
---

# 华为云 CCE 网络故障诊断

## 概述

本技能通过华为云 `hcloud` CLI 和 Kubernetes `kubectl` 诊断 CCE 网络故障。

执行模型：

```text
hcloud CCE 查询集群 -> kubectl cce 网络证据 -> 可选 hcloud ELB/VPC/EIP/NAT 只读证据 -> 排名诊断报告
```

CCE hcloud 用于集群发现和元数据读取，Kubernetes 访问使用 kubectl-cce 插件：

- `hcloud CCE ListClusters`
- `hcloud CCE ShowCluster`
- `hcloud CCE ShowClusterEndpoints`

Kubernetes 网络对象使用 `kubectl cce`
读取：Nodes、Pods、Services、Endpoints、EndpointSlices、Ingresses、NetworkPolicies、Events、CoreDNS/kube-dns 资源，以及 RBAC 允许时的相关 controller 日志。

北南向链路需要云侧证据时，使用只读 hcloud 网络命令：

- `hcloud ELB ListLoadBalancers/v3`
- `hcloud ELB ListListeners/v3`
- `hcloud ELB ListPools/v3`
- `hcloud ELB ListMembers/v3`
- `hcloud ELB ListHealthMonitors/v3`
- `hcloud VPC ListSecurityGroups/v3`
- `hcloud VPC ListSecurityGroupRules/v3`
- `hcloud VPC ListVpcs/v3`
- `hcloud VPC ListSubnets`
- `hcloud EIP ListPublicips/v3`
- `hcloud NAT ListNatGateways`

不要使用 Python SDK dispatcher、旧 skill 执行动作、旧 Huawei network action 或 Huawei Cloud SDK import。

**相关前置 skill**：如果需要安装或修复 `kubectl`/`kubectl-cce`，使用 `huawei-cloud-kubectl-cce-installer`。插件接入约束见 `references/kubectl-cce.md`。

## 使用场景

适用于：

- Service 不通、间歇性不可达、selector 或 EndpointSlice 异常。
- DNS/CoreDNS 故障，例如 NXDOMAIN、timeout、kube-dns endpoints 缺失。
- Ingress 502/504、ingress controller upstream error 或 LoadBalancer 创建/后端异常。
- NetworkPolicy 阻断东西向访问。
- ELB 后端 unhealthy、listener/pool/member 映射异常、EIP/NAT/VPC/安全组/ACL 问题。
- 需要端到端网络 Markdown 诊断报告。

本技能不修改资源。绑定/解绑 EIP、修改安全组、更新 ELB listener、编辑 CoreDNS、创建 NetworkPolicy、扩缩容或重启组件都只能作为建议输出并移交。

## 参数确认

| 输入              | 必填     | 说明                                                                                                                      |
| ----------------- | -------- | ------------------------------------------------------------------------------------------------------------------------- |
| `region`          | 是       | 请求上下文或 `HW_REGION_NAME`，否则要求用户输入                                                                                                         |
| `project_id`      | 通常需要 | 大多数 hcloud 操作需要                                                                                                    |
| `cluster_id`      | 推荐     | 没有时用 `ListClusters` 解析                                                                                              |
| `namespace`       | 通常需要 | namespaced K8s 对象需要                                                                                                   |
| `failure_symptom` | 推荐     | `dns_failure`、`service_unreachable`、`ingress_502_504`、`external_access_failed`、`network_policy_block`、`intermittent` |
| `service_name`    | 可选     | 目标 Service                                                                                                              |
| `ingress_name`    | 可选     | 目标 Ingress                                                                                                              |
| `source_pod`      | 可选     | 源 Pod 名或 selector                                                                                                      |
| `destination_pod` | 可选     | 目标 Pod 名或 selector                                                                                                    |
| `domain`          | 可选     | DNS/Ingress 涉及域名                                                                                                      |
| `elb_id`          | 可选     | 北南向排查中的 ELB ID                                                                                                     |

目标不清晰时，先做 namespace 扫描，再让用户明确 service、ingress、source、destination 或 domain，避免强行下结论。

## 区域选择

优先使用当前请求或已建立任务上下文中的 `region`；未提供时读取 `HW_REGION_NAME`；两者都没有时停止执行并要求用户提供 `region` 或设置 `HW_REGION_NAME`，不得从 hcloud profile 推断区域。

## 前置条件

1. `hcloud` 已安装并在 `PATH` 中，或已找到平台原生二进制并用 `hcloud version` 验证。
2. `kubectl` 已安装并兼容目标 Kubernetes 版本。Linux sandbox 使用 Linux kubectl；Windows 工作站使用 `kubectl.exe`。
3. hcloud 有认证配置，或本次命令通过临时参数传入凭据。只用 `hcloud configure list` 做脱敏验证。
4. IAM 允许读取 CCE 集群并使用 kubectl-cce API Gateway 接入。只有诊断云侧网络对象时才需要 ELB/VPC/EIP/NAT 读权限。
5. Kubernetes RBAC 允许读取 Services、Endpoints、EndpointSlices、Ingresses、NetworkPolicies、Pods、Nodes、Events 和相关日志。

不要打印 AK、SK、security token、kubectl-cce 代理凭据、Authorization header 或应用密钥。

## 核心命令与准备流程

### 1. 确认 CLI 工具

```bash
hcloud version
hcloud configure list
kubectl version --client
```

如果工具缺失，停止当前诊断流程，改用 `huawei-cloud-kubectl-cce-installer`
或批准的平台安装流程。本诊断技能不得下载或执行安装脚本。安装时固定批准版本、校验官方 checksum 或签名，再重新执行上述检查。

### 2. 定位并检查集群

```bash
hcloud CCE ListClusters --project_id=<project-id> --detail=true --cli-region=<region> --cli-output=json
hcloud CCE ShowCluster --cluster_id=<cluster-id> --project_id=<project-id> --detail=true --cli-region=<region> --cli-output=json
hcloud CCE ShowClusterEndpoints --cluster_id=<cluster-id> --project_id=<project-id> --cli-region=<region> --cli-output=json
```

若只有私网 API endpoint，kubectl 必须在可达 VPC 的环境中运行。

### 3. 配置 kubectl-cce 插件

执行 Kubernetes 命令前先阅读 `references/kubectl-cce.md`。本 skill 以 kubectl CCE 插件作为主要 Kubernetes 访问路径；不要生成 kubeconfig、不要改写 kubeconfig
server 字段、不要调用 Kubernetes SDK，也不要退回 SDK dispatcher 动作。

如果缺少 `kubectl` 或 `kubectl-cce`，使用 `huawei-cloud-kubectl-cce-installer`
安装或修复本地前置工具。本诊断 skill 只负责验证和使用插件，不负责定义插件安装策略。

先验证本地工具和插件发现：

```bash
kubectl version --client
kubectl plugin list
```

通过受批准的工具参数、受保护的 shell 环境或本地凭据提供方配置插件认证，不要打印凭据值。诊断命令中显式传入集群、区域和项目 ID：

```bash
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get namespaces
```

仅当默认 `<cluster-id>.cce.<region>.myhuaweicloud.com` endpoint 不适用于当前环境时，才设置 `CCE_ENDPOINT` 或传入
`--endpoint`。如果插件访问失败，在报告中记录脱敏后的安装、凭据、API Gateway 可达性或 Kubernetes RBAC 缺口；不要切换到 kubeconfig 生成或 SDK 调用。

插件会阻断 `exec`、`attach`、`port-forward` 等流式命令；`logs -f` 和 `watch` 未强化，诊断报告中使用有限 `logs --tail` 和普通 `get` 命令。

### 4. 验证 Kubernetes 只读权限

```bash
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> cluster-info
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i list services -n <namespace>
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i list endpoints -n <namespace>
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i list endpointslices.discovery.k8s.io -n <namespace>
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i list networkpolicies.networking.k8s.io -n <namespace>
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i list ingresses.networking.k8s.io -n <namespace>
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i list pods -n <namespace>
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i list events -n <namespace>
```

若 RBAC 拒绝某项读取，在报告中记录缺失权限，只继续采集允许读取的证据。

## 诊断流程

详细证据顺序和故障规则见 `references/workflow.md`。

Kubernetes 网络基线：

```bash
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get nodes -o wide
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get svc,endpoints,endpointslice,ingress,networkpolicy -n <namespace> -o wide
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods -n <namespace> -o wide
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get events -n <namespace> --sort-by=.lastTimestamp
```

Service：

```bash
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get svc <service-name> -n <namespace> -o yaml
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get endpoints <service-name> -n <namespace> -o yaml
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get endpointslice -n <namespace> -l kubernetes.io/service-name=<service-name> -o yaml
```

DNS：

```bash
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get svc,endpoints,endpointslice -n kube-system -o wide
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods -n kube-system -o wide | grep -E 'coredns|kube-dns|node-local-dns'
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> logs -n kube-system -l k8s-app=kube-dns --tail=200
```

PowerShell 中用 `Select-String` 替代 `grep`。

Ingress/LoadBalancer：

```bash
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get ingress <ingress-name> -n <namespace> -o yaml
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> describe ingress <ingress-name> -n <namespace>
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> describe svc <service-name> -n <namespace>
```

必要时使用云网络只读命令：

```bash
hcloud ELB ListLoadBalancers/v3 --project_id=<project-id> --cli-region=<region> --cli-output=json
hcloud ELB ListListeners/v3 --project_id=<project-id> --cli-region=<region> --cli-output=json
hcloud ELB ListPools/v3 --project_id=<project-id> --cli-region=<region> --cli-output=json
hcloud ELB ListMembers/v3 --project_id=<project-id> --pool_id=<pool-id> --cli-region=<region> --cli-output=json
hcloud VPC ListSecurityGroups/v3 --project_id=<project-id> --cli-region=<region> --cli-output=json
hcloud VPC ListSecurityGroupRules/v3 --project_id=<project-id> --cli-region=<region> --cli-output=json
hcloud EIP ListPublicips/v3 --project_id=<project-id> --cli-region=<region> --cli-output=json
hcloud NAT ListNatGateways --project_id=<project-id> --cli-region=<region> --cli-output=json
```

不同 API 版本过滤参数不一致时，用 `hcloud <service> <operation> --help` 确认。

## 主动测试边界

kubectl-cce 插件会阻断 `exec`、`attach` 和
`port-forward`。本只读技能不得通过kubeconfig、SDK、抓包、压测或主动流量生成绕过该边界。用户要求主动连通性测试时，记录源端、目标端、范围、风险和预期信号，取得明确授权后移交给批准的测试路径。

## 原因排序

按最先失败的链路层级排序：

1. 集群/API/RBAC 可达性缺口。
2. 节点或 CNI 健康问题。
3. DNS/CoreDNS/kube-dns/node-local-dns。
4. Service selector 和 EndpointSlice readiness。
5. NetworkPolicy 和命名空间策略。
6. Ingress/controller/backend 映射。
7. 云 ELB listener/pool/member/health monitor。
8. VPC/安全组/ACL/EIP/NAT。
9. 应用后端 readiness 或过载。

常见原因标签：

| 原因                      | 证据                                                                  |
| ------------------------- | --------------------------------------------------------------------- |
| `NodeOrCNIUnhealthy`      | Node NotReady、CNIProblem、FailedCreatePodSandBox                     |
| `DnsCoreDNSFailure`       | kube-dns/CoreDNS 无 Ready endpoint、持续重启、timeout 或异常 NXDOMAIN |
| `ServiceNoReadyEndpoint`  | Service 存在，但 EndpointSlice 没有 Ready 地址                        |
| `ServiceSelectorMismatch` | Service selector 未匹配任何 Pod                                       |
| `NetworkPolicyBlocked`    | NetworkPolicy 选中目标，但未放行来源或端口                            |
| `IngressBackendMismatch`  | Ingress 指向不存在的 Service/端口或非健康后端                         |
| `ELBBackendUnhealthy`     | Kubernetes 对象映射正常，但 ELB member 不健康                         |
| `SecurityPolicyBlocked`   | 安全组、ACL 或路由证据显示流量被阻断                                  |
| `EgressNatOrEipIssue`     | 外部出/入方向所需 NAT/EIP 缺失或异常                                  |
| `BackendApplicationIssue` | 网络链路存在，但后端 Pod 未 Ready 或日志显示应用错误                  |

## 输出格式

按 `references/output-schema.md` 输出。报告要先给结论、根因和行动建议；拓扑、对象快照和命令轨迹放在后面。

报告至少按这个顺序包含：

- 执行摘要：症状状态、置信度、根因分类和一句话结论。
- 根因分析：Top causes，附直接证据和解释。
- 下一步措施：验证检查、候选修复路径、移交对象或 skill。
- 目标：region、project、cluster、namespace、symptom、source/destination、Service/Ingress/domain/ELB。
- 网络链路漏斗，标明 checked、abnormal、skipped、pruned。
- 反向证据：已检查层级为什么不优先。
- 关键对象快照：Service、EndpointSlice、Pods、Ingress、NetworkPolicy、CoreDNS、相关 ELB/VPC 对象。
- 验证缺口。
- 证据矩阵和详细支撑证据。
- CLI 路径：hcloud CCE、kubectl-cce、可选 hcloud ELB/VPC/EIP/NAT。
- 明确说明没有执行变更命令。

## 最佳实践

- 从客户端入口沿链路追踪到 Ready backend，在第一个失败跳点停止并取证。
- 关联 selectors、endpoints、policies、DNS、Ingress 和云网络对象标识。
- 主动连通性测试作为独立授权事项移交，并记录范围、风险和预期信号。
- 将只读诊断和网络或工作负载变更分离，并注明移交对象。

## 注意事项与安全边界

执行建议前先读 `references/risk-rules.md`。本技能只读，不运行：

- `kubectl cce ... apply`、`create`、`patch`、`edit`、`delete`、`scale`、`rollout undo` 或组件重启
- `kubectl exec`、抓包、压测或主动流量测试
- hcloud create/update/delete 操作
- 任意 SDK dispatcher action

## 验证

见 `references/verification-method.md`。有效实现应满足：

- `hcloud version`、`hcloud configure list`、`kubectl version --client` 可用。
- `hcloud CCE ListClusters`、`ShowCluster` 可用，`kubectl cce ...` 能读取目标集群。
- `kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id>` 能读取目标 namespace 网络对象。
- 云侧排查需要时，hcloud ELB/VPC/EIP/NAT 只读命令可用。
- 技能包中没有 SDK dispatcher 入口残留。

## 参考文档

- `references/workflow.md` - 分层网络证据顺序和故障规则。
- `references/common-pitfalls.md` - 网络诊断常见坑和 CLI 示例。
- `references/output-schema.md` - Markdown 和 JSON 报告结构。
- `references/risk-rules.md` - 只读边界和移交规则。
- `references/verification-method.md` - 环境和 CLI 验证。
- `references/iam-policies.md` - IAM 与 Kubernetes RBAC 要求。


## x509 TLS 重试

当 `kubectl cce` 返回 `x509` 证书校验错误时，使用完全相同的命令，并在 `cce` 后追加 `--cce-insecure-upstream-tls=true` 重试。例如：`kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> ...`。仅在出现该 TLS 校验错误时使用此参数。
