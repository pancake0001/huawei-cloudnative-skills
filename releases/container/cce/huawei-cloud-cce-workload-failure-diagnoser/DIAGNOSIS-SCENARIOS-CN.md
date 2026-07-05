# CCE 工作负载故障诊断场景与步骤说明

## Skill 定位

`huawei-cloud-cce-workload-failure-diagnoser` 用于诊断华为云 CCE 集群中的工作负载发布和可用性问题。它不负责修复资源，只负责通过 `hcloud CCE` 获取集群访问入口和 kubeconfig，再通过 `kubectl` 只读采集 Kubernetes 证据，最后输出根因判断、证据链和移交建议。

核心链路：

```text
hcloud CCE 查询集群 -> hcloud CCE 生成短期 kubeconfig -> kubectl 只读采集资源 -> 发布漏斗分析 -> Top causes -> 移交建议
```

## 主要诊断场景

1. Deployment 发布卡住

   典型表现包括 `rollout status` 超时、`ProgressDeadlineExceeded`、旧版本副本一直存在、新版本 ReplicaSet 没有 Pod、`updatedReplicas` 或 `availableReplicas` 不达预期。

2. StatefulSet 或 DaemonSet 更新异常

   典型表现包括 `updatedReplicas` 不增长、`numberReady`/`numberAvailable` 不足、partition 设置导致不更新、节点选择器或污点导致 DaemonSet 无法调度到目标节点。

3. Pod 无法创建或无法调度

   典型表现包括 `Pending`、`FailedScheduling`、资源不足、节点 taint/toleration 不匹配、nodeSelector/affinity 不匹配、配额或准入策略阻断。

4. Pod 启动失败或运行后反复重启

   典型表现包括 `ImagePullBackOff`、`ErrImagePull`、`CrashLoopBackOff`、`OOMKilled`、启动命令不存在、容器非零退出、previous logs 中有应用错误。

5. Pod Running 但不 Ready

   典型表现包括 readiness/liveness/startup probe 的 `Unhealthy` 事件、探针路径/端口/协议错误、应用启动慢、依赖服务不可达。

6. 存储、网络或节点侧原因影响工作负载可用性

   典型表现包括 `FailedMount`、PVC Pending、节点 NotReady/Pressure、Service selector 不匹配、Endpoints 为空、Ingress 或后端服务路径异常。

7. 控制面未观察到最新变更

   典型表现包括 `status.observedGeneration < metadata.generation`。这种情况优先判断为控制面尚未处理最新 spec，而不是直接下钻 Pod。

## 标准诊断步骤

1. 明确目标

   收集 `region`、`project_id`、`cluster_id`、`namespace`、`kind`、`name`。如果没有 `cluster_id`，先用 `hcloud CCE ListClusters` 查找。

2. 验证工具和凭据

   执行 `hcloud version`、`hcloud configure list`、`kubectl version --client`。`hcloud` 和 `kubectl` 都要使用运行环境对应的平台版本，Linux sandbox 使用 Linux 二进制，Windows 工作站才使用 `.exe`。

3. 查询集群和访问入口

   使用 `hcloud CCE ListClusters`、`ShowCluster`、`ShowClusterEndpoints` 确认集群存在、状态可用、region/project 正确，并检查是否有公网 API 入口。如果 `publicEndpoint` 为空，后续 `kubectl` 必须运行在能访问 CCE 私网 API Server 的网络里。

4. 生成短期 kubeconfig

   使用 `hcloud CCE CreateKubernetesClusterCert --duration=1` 生成 kubeconfig，保存到临时或用户 kubeconfig 路径，并限制文件权限。KooCLI 可能输出 JSON 格式 kubeconfig，`kubectl` 可以直接读取 JSON 或 YAML。

5. 验证 Kubernetes 读权限

   先跑 `kubectl --kubeconfig=<file> cluster-info`，再用 `kubectl auth can-i` 检查目标命名空间里的 Deployment/Pod/Event/Pod logs 读取权限。网络不可达或 RBAC 不足要作为诊断缺口写入报告。

6. 采集工作负载证据

   对 Deployment、StatefulSet 或 DaemonSet 执行 `get -o yaml`、`describe`、`rollout status`。重点读取 generation、observedGeneration、replicas、conditions、selector 和 update strategy。

7. 采集关联对象证据

   Deployment 要按 selector 找 ReplicaSet，并按 ownerReference 过滤出属于该 Deployment 的 RS；再识别最高 revision 的新版本 RS。所有 workload 类型都要按 selector 找 Pod，查看 Pod Ready 状态、重启次数、节点、container states 和 ownerReferences。

8. 过滤事件和日志

   事件要按 workload、ReplicaSet、Pod 的 UID/name 进行过滤，避免把命名空间下所有 Warning 都当作目标证据。对异常 Pod 执行 `describe pod`、当前日志、previous logs，必要时查看 PVC、Node、Service、Endpoints、Ingress。

9. 构建发布漏斗

   按“控制面观察到变更 -> 新版本对象存在 -> 新版本 Pod 创建 -> Pod Ready -> 工作负载 available”的顺序找到第一个失败层。根因判断优先基于第一个失败层和最直接事件/日志。

10. 输出报告和移交

   报告必须包含目标、使用过的 hcloud/kubectl 命令、发布漏斗、Top causes、证据、建议和未执行变更命令的说明。需要修复时只给建议，涉及变更的动作移交到 remediation skill。

## 只读边界

允许：

- `hcloud CCE ListClusters`、`ShowCluster`、`ShowClusterEndpoints`
- `hcloud CCE CreateKubernetesClusterCert`
- `kubectl get`、`describe`、`logs`、`rollout status`、`rollout history`、`auth can-i`、`cluster-info`、`top`

禁止：

- `kubectl apply/create/patch/edit/delete/scale/rollout undo/cordon/drain/taint`
- 除 `CreateKubernetesClusterCert` 之外的 hcloud create/update/delete 操作
- Python SDK dispatcher、`scripts/huawei-cloud.py`、`skill action=exec`、`huawei_workload_*`
- 在报告或日志中输出 AK/SK、token、kubeconfig 证书或 Authorization header
