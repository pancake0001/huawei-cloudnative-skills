---
id: huawei-cloud-cce-network-failure-diagnoser
name: huawei-cloud-cce-network-failure-diagnoser
description: >
  使用 hcloud CLI 做 CCE 集群发现、kubeconfig 获取，以及可选的 ELB/VPC/EIP/NAT 只读证据采集，再使用 kubectl 采集 Kubernetes 网络对象来诊断华为云 CCE 网络故障。适用于 Service 不通、DNS/CoreDNS 异常、Ingress 502/504、NetworkPolicy 阻断、EndpointSlice/后端就绪异常、ELB 后端健康、EIP/NAT/VPC/安全组/ACL 问题和端到端网络诊断报告。不使用 Python SDK dispatcher。
tags: [huawei-cloud, cce, hcloud, koocli, kubectl, network, elb, vpc, diagnosis]
---

# Huawei Cloud CCE Network Failure Diagnoser

本技能通过华为云 `hcloud` CLI 和 Kubernetes `kubectl` 诊断 CCE 网络故障。

执行模型：

```text
hcloud CCE -> 短期 kubeconfig -> kubectl 网络证据 -> 可选 hcloud ELB/VPC/EIP/NAT 只读证据 -> 排名诊断报告
```

CCE hcloud 用于集群发现和 kubeconfig：

- `hcloud CCE ListClusters`
- `hcloud CCE ShowCluster`
- `hcloud CCE ShowClusterEndpoints`
- `hcloud CCE CreateKubernetesClusterCert`

Kubernetes 网络对象使用 `kubectl` 读取：Nodes、Pods、Services、Endpoints、EndpointSlices、Ingresses、NetworkPolicies、Events、CoreDNS/kube-dns 资源，以及 RBAC 允许时的相关 controller 日志。

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

不要使用 Python SDK dispatcher、`scripts/huawei-cloud.py`、`skill action=exec`、旧 `huawei_network_*` action 或 Huawei Cloud SDK import。

## 使用场景

适用于：

- Service 不通、间歇性不可达、selector 或 EndpointSlice 异常。
- DNS/CoreDNS 故障，例如 NXDOMAIN、timeout、kube-dns endpoints 缺失。
- Ingress 502/504、ingress controller upstream error 或 LoadBalancer 创建/后端异常。
- NetworkPolicy 阻断东西向访问。
- ELB 后端 unhealthy、listener/pool/member 映射异常、EIP/NAT/VPC/安全组/ACL 问题。
- 需要端到端网络 Markdown 诊断报告。

本技能不修改资源。绑定/解绑 EIP、修改安全组、更新 ELB listener、编辑 CoreDNS、创建 NetworkPolicy、扩缩容或重启组件都只能作为建议输出并移交。

## 必要输入

| 输入 | 必填 | 说明 |
| --- | --- | --- |
| `region` | 是 | 例如 `cn-north-4` |
| `project_id` | 通常需要 | 大多数 hcloud 操作需要 |
| `cluster_id` | 推荐 | 没有时用 `ListClusters` 解析 |
| `namespace` | 通常需要 | namespaced K8s 对象需要 |
| `failure_symptom` | 推荐 | `dns_failure`、`service_unreachable`、`ingress_502_504`、`external_access_failed`、`network_policy_block`、`intermittent` |
| `service_name` | 可选 | 目标 Service |
| `ingress_name` | 可选 | 目标 Ingress |
| `source_pod` | 可选 | 源 Pod 名或 selector |
| `destination_pod` | 可选 | 目标 Pod 名或 selector |
| `domain` | 可选 | DNS/Ingress 涉及域名 |
| `elb_id` | 可选 | 北南向排查中的 ELB ID |

目标不清晰时，先做 namespace 扫描，再让用户明确 service、ingress、source、destination 或 domain，避免强行下结论。

## 前置条件

1. `hcloud` 已安装并在 `PATH` 中，或已找到平台原生二进制并用 `hcloud version` 验证。
2. `kubectl` 已安装并兼容目标 Kubernetes 版本。Linux sandbox 使用 Linux kubectl；Windows 工作站使用 `kubectl.exe`。
3. hcloud 有认证配置，或本次命令通过临时参数传入凭据。只用下面命令做脱敏验证：

```bash
hcloud configure list
```

4. IAM 允许读取 CCE 集群并创建 kubeconfig 证书。只有诊断云侧网络对象时才需要 ELB/VPC/EIP/NAT 读权限。
5. Kubernetes RBAC 允许读取 Services、Endpoints、EndpointSlices、Ingresses、NetworkPolicies、Pods、Nodes、Events 和相关日志。

不要打印 AK、SK、security token、kubeconfig 证书、Authorization header 或应用密钥。

## CCE hcloud 设置流程

### 1. 确认 CLI 工具

```bash
hcloud version
hcloud configure list
kubectl version --client
```

工具不在 `PATH` 中时，先定位或安装平台原生二进制，并验证实际使用的二进制。

### 2. 定位并检查集群

```bash
hcloud CCE ListClusters --project_id=<project-id> --detail=true --cli-region=<region> --cli-output=json
hcloud CCE ShowCluster --cluster_id=<cluster-id> --project_id=<project-id> --detail=true --cli-region=<region> --cli-output=json
hcloud CCE ShowClusterEndpoints --cluster_id=<cluster-id> --project_id=<project-id> --cli-region=<region> --cli-output=json
```

若只有私网 API endpoint，kubectl 必须在可达 VPC 的环境中运行。

### 3. 获取短期 kubeconfig

```bash
hcloud CCE CreateKubernetesClusterCert --cluster_id=<cluster-id> --project_id=<project-id> --duration=1 --cli-region=<region> --cli-output=json > <temp-kubeconfig-file>
chmod 600 <temp-kubeconfig-file>
```

kubeconfig 放在仓库外，诊断结束后删除。集群刚唤醒或 EIP 刚绑定时，可加 `--cli-connect-timeout=20 --cli-read-timeout=90 --cli-retry-count=2`。

### 4. 验证 Kubernetes 只读权限

```bash
kubectl --kubeconfig=<kubeconfig-file> cluster-info
kubectl --kubeconfig=<kubeconfig-file> auth can-i list services -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> auth can-i list endpoints -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> auth can-i list endpointslices.discovery.k8s.io -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> auth can-i list networkpolicies.networking.k8s.io -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> auth can-i list ingresses.networking.k8s.io -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> auth can-i list pods -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> auth can-i list events -n <namespace>
```

若 RBAC 拒绝某项读取，在报告中记录缺失权限，只继续采集允许读取的证据。

## 诊断流程

详细证据顺序和故障规则见 `references/workflow.md`。

Kubernetes 网络基线：

```bash
kubectl --kubeconfig=<kubeconfig-file> get nodes -o wide
kubectl --kubeconfig=<kubeconfig-file> get svc,endpoints,endpointslice,ingress,networkpolicy -n <namespace> -o wide
kubectl --kubeconfig=<kubeconfig-file> get pods -n <namespace> -o wide
kubectl --kubeconfig=<kubeconfig-file> get events -n <namespace> --sort-by=.lastTimestamp
```

Service：

```bash
kubectl --kubeconfig=<kubeconfig-file> get svc <service-name> -n <namespace> -o yaml
kubectl --kubeconfig=<kubeconfig-file> get endpoints <service-name> -n <namespace> -o yaml
kubectl --kubeconfig=<kubeconfig-file> get endpointslice -n <namespace> -l kubernetes.io/service-name=<service-name> -o yaml
```

DNS：

```bash
kubectl --kubeconfig=<kubeconfig-file> get svc,endpoints,endpointslice -n kube-system -o wide
kubectl --kubeconfig=<kubeconfig-file> get pods -n kube-system -o wide | grep -E 'coredns|kube-dns|node-local-dns'
kubectl --kubeconfig=<kubeconfig-file> logs -n kube-system -l k8s-app=kube-dns --tail=200
```

PowerShell 中用 `Select-String` 替代 `grep`。

Ingress/LoadBalancer：

```bash
kubectl --kubeconfig=<kubeconfig-file> get ingress <ingress-name> -n <namespace> -o yaml
kubectl --kubeconfig=<kubeconfig-file> describe ingress <ingress-name> -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> describe svc <service-name> -n <namespace>
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

默认不执行 `kubectl exec`、抓包、压测或主动流量生成。用户明确要求主动连通性测试时，先说明范围和风险，再选择侵入性最低的命令，并写入报告。

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

## 报告格式

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
- CLI 路径：hcloud CCE、kubectl、可选 hcloud ELB/VPC/EIP/NAT。
- 明确说明没有执行变更命令。

## 安全边界

执行建议前先读 `references/risk-rules.md`。本技能只读，不运行：

- `kubectl apply`、`create`、`patch`、`edit`、`delete`、`scale`、`rollout undo` 或组件重启
- 未经明确授权的 `kubectl exec`、抓包或主动流量测试
- hcloud create/update/delete 操作
- 任意 SDK dispatcher action

## 验证

见 `references/verification-method.md`。有效实现应满足：

- `hcloud version`、`hcloud configure list`、`kubectl version --client` 可用。
- `hcloud CCE ListClusters`、`ShowCluster`、`CreateKubernetesClusterCert` 可用。
- `kubectl --kubeconfig=<file>` 能读取目标 namespace 网络对象。
- 云侧排查需要时，hcloud ELB/VPC/EIP/NAT 只读命令可用。
- 技能包中没有 SDK dispatcher 入口残留。

## References

- `references/workflow.md` - 分层网络证据顺序和故障规则。
- `references/common-pitfalls.md` - 网络诊断常见坑和 CLI 示例。
- `references/output-schema.md` - Markdown 和 JSON 报告结构。
- `references/risk-rules.md` - 只读边界和移交规则。
- `references/verification-method.md` - 环境和 CLI 验证。
- `references/iam-policies.md` - IAM 与 Kubernetes RBAC 要求。
