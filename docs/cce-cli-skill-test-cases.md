# CCE CLI Skill 测试用例与异常构造方法

本文用于验证已改造为 `hcloud` + `kubectl cce` 路径的 CCE skills。测试目标是覆盖可构造的工作负载、Pod、节点、网络、存储、事件、指标、告警、变更、依赖、可观测上下文、根因分析和压测场景。

## 1. 测试范围

覆盖以下 skill：

| Skill | 覆盖目标 |
| --- | --- |
| `huawei-cloud-cce-workload-failure-diagnoser` | Deployment/StatefulSet/DaemonSet rollout、可用副本、Pod 下钻、事件过滤、下一步建议 |
| `huawei-cloud-cce-pod-failure-diagnoser` | ImagePull、CrashLoop、OOM、Pending、Probe、Mount、Evicted/压力类信号 |
| `huawei-cloud-cce-node-failure-diagnoser` | 调度失败、节点资源/压力、taint/toleration、NodeNotReady 类证据 |
| `huawei-cloud-cce-network-failure-diagnoser` | Service selector、EndpointSlice、DNS、NetworkPolicy、Ingress/ELB、后端应用异常 |
| `huawei-cloud-cce-storage-failure-diagnoser` | PVC Pending、PV/StorageClass、FailedMount、CSI/VolumeAttachment 数据缺口 |
| `huawei-cloud-cce-pressure-test` | local/in-cluster k6、路由预检、压测瓶颈、HPA/容量、压测失败归因 |
| `huawei-cloud-cce-kubernetes-event-analyzer` | 当前 Event 聚合、历史 Event/LTS 缺口、事件模式映射 |
| `huawei-cloud-cce-metric-analyzer` | Pod/Node/组件/云资源指标、指标缺口、指标与事件/告警/变更关联 |
| `huawei-cloud-cce-alarm-correlation-engine` | 告警分组、告警时间线、无告警/无权限/无历史的判断 |
| `huawei-cloud-cce-change-impact-analyzer` | rollout、配置、selector、scale、HPA 等变更影响 |
| `huawei-cloud-cce-dependency-impact-analyzer` | Ingress/Service/Endpoint/Pod/Node 依赖路径和影响半径 |
| `huawei-cloud-cce-observability-context-builder` | 现网可观测上下文包、时间线、高信号发现、数据缺口和 handoff |
| `huawei-cloud-cce-root-cause-analyzer` | 聚合上下文、跨域证据排序、Top3 根因、反证和下一步措施 |

## 2. 通用测试约束

1. 默认只在专用命名空间内创建资源，不修改生产命名空间。
2. 节点类强干扰测试必须使用专用测试节点池；没有专用节点池时，只跑 namespace 级可构造用例。
3. 所有 skill 诊断过程必须使用 `hcloud` 和 `kubectl cce`。
4. 诊断报告中不能出现 AK/SK、token、Authorization header、临时凭证或完整 kubeconfig。
5. 报告必须把 `Summary`、`Root Cause Analysis`、`Next Actions` 放在前面。
6. 如果某类证据拿不到，例如 AOM、CES、LTS、metrics-server、Ingress controller、VolumeAttachment RBAC，必须写入 `Data Gaps`，不能把缺失证据当作健康。
7. 清理命令只清理测试命名空间和明确创建的测试资源。

## 3. 通用准备

测试时填入实际集群信息：

```text
REGION=<region>
PROJECT_ID=<project-id>
CLUSTER_ID=<cluster-id>
NS=cce-skill-chaos
RUN_ID=<yyyyMMddHHmm>
```

Linux/macOS 参数写法：

```bash
K_ARGS=(--cluster-id "$CLUSTER_ID" --region "$REGION" --project-id "$PROJECT_ID")
kubectl cce "${K_ARGS[@]}" get ns
```

PowerShell 参数写法：

```powershell
$KArgs = @("--cluster-id", $env:CLUSTER_ID, "--region", $env:REGION, "--project-id", $env:PROJECT_ID)
kubectl cce @KArgs get ns
```

`hcloud` 基础连通性检查：

```bash
hcloud CCE ListClusters --project_id=<project-id> --cli-region=<region> --cli-output=json
hcloud CCE ShowCluster --cluster_id=<cluster-id> --project_id=<project-id> --detail=true --cli-region=<region> --cli-output=json
hcloud CCE ShowClusterEndpoints --cluster_id=<cluster-id> --project_id=<project-id> --cli-region=<region> --cli-output=json
```

创建测试命名空间：

```bash
kubectl cce "${K_ARGS[@]}" create namespace "$NS"
kubectl cce "${K_ARGS[@]}" label namespace "$NS" cce-skill-test=true run-id="$RUN_ID"
```

PowerShell：

```powershell
kubectl cce @KArgs create namespace $env:NS
kubectl cce @KArgs label namespace $env:NS cce-skill-test=true run-id=$env:RUN_ID
```

下文 YAML 默认使用 `cce-skill-chaos` 命名空间；如果实际使用其他命名空间，先批量替换再 apply。

通用清理：

```bash
kubectl cce "${K_ARGS[@]}" delete namespace "$NS" --wait=false
```

## 4. 静态回归用例

### ST-01 CLI 路径残留检查

覆盖：全部已整改 skill。

执行：

```bash
rg -n "huaweicloudsdk|BasicCredentials|KubernetesClusterCert|CreateKubernetesClusterCert|skill action=exec|scripts/huawei-cloud.py|dispatch_action|is_registered_action" releases/container/cce skills --glob "!*.md" --glob "!*.MD"
rg -n -P -- "^kubectl (?!cce|version|plugin)" releases/container/cce skills
git diff --check -- releases/container/cce skills
```

期望：

- 非 Markdown 可执行文件中无 SDK、dispatcher、kubeconfig 生成残留。
- 无裸 `kubectl get/describe/logs/top` 形式；读取集群时必须是 `kubectl cce`。
- `git diff --check` 无空白错误。

### ST-02 报告格式检查

覆盖：全部诊断/分析类 skill。

方法：对每个 skill 选择一个下方对应异常进行诊断。

期望：

- 报告前置包含 `Summary`、`Root Cause Analysis` 或 `Root Cause Signal`、`Next Actions`。
- 证据表里有命令来源、对象名、命名空间、时间窗口。
- 有反证和数据缺口。
- 没有输出敏感信息。

## 5. Namespace 级可构造异常用例

### TC-01 ImagePullBackOff / ErrImagePull

覆盖：

- `pod-failure-diagnoser`
- `workload-failure-diagnoser`
- `kubernetes-event-analyzer`
- `change-impact-analyzer`
- `observability-context-builder`
- `root-cause-analyzer`

构造：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: bad-image
  namespace: cce-skill-chaos
  labels:
    app: bad-image
spec:
  replicas: 2
  selector:
    matchLabels:
      app: bad-image
  template:
    metadata:
      labels:
        app: bad-image
    spec:
      containers:
      - name: app
        image: azxsdc:latest
        imagePullPolicy: Always
```

执行：

```bash
kubectl cce "${K_ARGS[@]}" apply -f tc-01-bad-image.yaml
kubectl cce "${K_ARGS[@]}" -n "$NS" rollout status deploy/bad-image --timeout=90s
kubectl cce "${K_ARGS[@]}" -n "$NS" get pod -l app=bad-image
kubectl cce "${K_ARGS[@]}" -n "$NS" get events --sort-by=.lastTimestamp
```

诊断入口示例：

```text
使用 huawei-cloud-cce-pod-failure-diagnoser 诊断 <cluster-id>/<region>/<project-id> 中命名空间 cce-skill-chaos 的 bad-image Pod。
```

期望：

- 直接根因不是笼统“镜像拉取失败”，必须包含镜像名、解析后的 registry/repository/tag、Event message、HTTP/status 或权限/DNS线索。
- 下一步建议至少区分：镜像名错误、未推送到 SWR、缺少 imagePullSecret、外网/DNS/镜像仓库访问异常。
- Event analyzer 应聚合 `FailedPull`、`BackOff`、`ErrImagePull` 类原因。
- Change analyzer 如果先部署正常镜像再改成错误镜像，应识别 rollout/change 与故障时间相关。
- Root cause 应把 ImagePull 置为高优先级，并说明网络/节点/存储为何不是首因。

清理：

```bash
kubectl cce "${K_ARGS[@]}" -n "$NS" delete deploy bad-image --ignore-not-found
```

### TC-02 CrashLoopBackOff

覆盖：

- `pod-failure-diagnoser`
- `workload-failure-diagnoser`
- `metric-analyzer`
- `observability-context-builder`
- `root-cause-analyzer`

构造：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: crashloop
  namespace: cce-skill-chaos
  labels:
    app: crashloop
spec:
  replicas: 1
  selector:
    matchLabels:
      app: crashloop
  template:
    metadata:
      labels:
        app: crashloop
    spec:
      containers:
      - name: app
        image: busybox:1.36
        command: ["/bin/sh", "-c"]
        args: ["echo test-crashloop; sleep 2; exit 42"]
```

期望：

- 读取 current logs 和 `--previous` logs。
- 报告 last state、exit code、restart count、BackOff Event。
- 下一步建议指向启动命令、配置、依赖检查，而不是只建议扩容。
- Metric analyzer 如果没有 Pod 指标，要记录缺口；不能说指标正常。

清理：

```bash
kubectl cce "${K_ARGS[@]}" -n "$NS" delete deploy crashloop --ignore-not-found
```

### TC-03 OOMKilled

覆盖：

- `pod-failure-diagnoser`
- `node-failure-diagnoser`
- `metric-analyzer`
- `kubernetes-event-analyzer`
- `root-cause-analyzer`

构造：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: oom
  namespace: cce-skill-chaos
  labels:
    app: oom
spec:
  replicas: 1
  selector:
    matchLabels:
      app: oom
  template:
    metadata:
      labels:
        app: oom
    spec:
      containers:
      - name: app
        image: polinux/stress
        command: ["stress"]
        args: ["--vm", "1", "--vm-bytes", "128M", "--vm-hang", "1"]
        resources:
          requests:
            memory: "32Mi"
            cpu: "20m"
          limits:
            memory: "64Mi"
            cpu: "200m"
```

期望：

- Pod diagnoser 报告 `OOMKilled`、exit code 137、内存 limit/request、重启次数。
- Metric analyzer 尝试读取 Pod/Node memory；指标不可用时记录 `Data Gaps`。
- Node diagnoser 不能把单 Pod OOM 误判成节点故障，除非节点 Conditions/Events 支持。

清理：

```bash
kubectl cce "${K_ARGS[@]}" -n "$NS" delete deploy oom --ignore-not-found
```

### TC-04 FailedScheduling: 资源请求过大

覆盖：

- `workload-failure-diagnoser`
- `pod-failure-diagnoser`
- `node-failure-diagnoser`
- `kubernetes-event-analyzer`
- `root-cause-analyzer`

构造：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: unschedulable-cpu
  namespace: cce-skill-chaos
  labels:
    app: unschedulable-cpu
spec:
  replicas: 1
  selector:
    matchLabels:
      app: unschedulable-cpu
  template:
    metadata:
      labels:
        app: unschedulable-cpu
    spec:
      containers:
      - name: app
        image: busybox:1.36
        command: ["sleep", "3600"]
        resources:
          requests:
            cpu: "999"
            memory: "1Ti"
```

期望：

- 报告 `Pending`、`PodScheduled=False`、`FailedScheduling`。
- Node diagnoser 应引用节点 allocatable/capacity、现有 requests、scheduler event。
- 下一步建议是降低 request、扩容节点池或调整调度约束，而不是重启 Pod。

清理：

```bash
kubectl cce "${K_ARGS[@]}" -n "$NS" delete deploy unschedulable-cpu --ignore-not-found
```

### TC-05 FailedScheduling: nodeSelector 不匹配

覆盖：

- `workload-failure-diagnoser`
- `pod-failure-diagnoser`
- `node-failure-diagnoser`
- `kubernetes-event-analyzer`

构造：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: bad-nodeselector
  namespace: cce-skill-chaos
  labels:
    app: bad-nodeselector
spec:
  replicas: 1
  selector:
    matchLabels:
      app: bad-nodeselector
  template:
    metadata:
      labels:
        app: bad-nodeselector
    spec:
      nodeSelector:
        cce-skill-test/nonexistent: "true"
      containers:
      - name: app
        image: busybox:1.36
        command: ["sleep", "3600"]
```

期望：

- 报告 nodeSelector 与实际节点 label 不匹配。
- Node diagnoser 不能误判为资源不足或 NodeNotReady。

清理：

```bash
kubectl cce "${K_ARGS[@]}" -n "$NS" delete deploy bad-nodeselector --ignore-not-found
```

### TC-06 Readiness Probe 失败导致 Service 无 ready endpoint

覆盖：

- `pod-failure-diagnoser`
- `workload-failure-diagnoser`
- `network-failure-diagnoser`
- `dependency-impact-analyzer`
- `pressure-test`
- `root-cause-analyzer`

构造：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: probe-fail
  namespace: cce-skill-chaos
  labels:
    app: probe-fail
spec:
  replicas: 2
  selector:
    matchLabels:
      app: probe-fail
  template:
    metadata:
      labels:
        app: probe-fail
    spec:
      containers:
      - name: app
        image: nginx:1.25
        ports:
        - containerPort: 80
        readinessProbe:
          httpGet:
            path: /not-exist
            port: 80
          periodSeconds: 5
          failureThreshold: 1
---
apiVersion: v1
kind: Service
metadata:
  name: probe-fail
  namespace: cce-skill-chaos
spec:
  selector:
    app: probe-fail
  ports:
  - name: http
    port: 80
    targetPort: 80
```

期望：

- Pod diagnoser 报告 readiness probe 失败路径、端口、Event。
- Network diagnoser 报告 Service 存在但 ready endpoints 为空。
- Dependency analyzer 展示 Service -> Pod 路径断在 Pod readiness。
- Pressure-test 预检应阻止压测或明确“目标无可用后端”，不能把压测 5xx 当作容量瓶颈。

清理：

```bash
kubectl cce "${K_ARGS[@]}" -n "$NS" delete deploy,svc probe-fail --ignore-not-found
```

### TC-07 Service selector 不匹配

覆盖：

- `network-failure-diagnoser`
- `dependency-impact-analyzer`
- `change-impact-analyzer`
- `root-cause-analyzer`

构造：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: svc-selector-backend
  namespace: cce-skill-chaos
  labels:
    app: svc-selector-backend
spec:
  replicas: 1
  selector:
    matchLabels:
      app: svc-selector-backend
  template:
    metadata:
      labels:
        app: svc-selector-backend
    spec:
      containers:
      - name: app
        image: nginx:1.25
        ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: svc-selector-bad
  namespace: cce-skill-chaos
spec:
  selector:
    app: not-matching
  ports:
  - name: http
    port: 80
    targetPort: 80
```

期望：

- Network diagnoser 报告 selector 匹配 0 个 Pod，Endpoints/EndpointSlices 为空。
- Dependency analyzer 展示入口断在 Service selector。
- Change analyzer 如果先创建正确 selector 再 patch 错误 selector，应把 selector 变更列为首要可疑变更。

变更构造：

```bash
kubectl cce "${K_ARGS[@]}" -n "$NS" patch svc svc-selector-bad -p '{"spec":{"selector":{"app":"svc-selector-backend"}}}'
kubectl cce "${K_ARGS[@]}" -n "$NS" patch svc svc-selector-bad -p '{"spec":{"selector":{"app":"not-matching"}}}'
```

清理：

```bash
kubectl cce "${K_ARGS[@]}" -n "$NS" delete deploy svc-selector-backend --ignore-not-found
kubectl cce "${K_ARGS[@]}" -n "$NS" delete svc svc-selector-bad --ignore-not-found
```

### TC-08 Service targetPort 错误

覆盖：

- `network-failure-diagnoser`
- `dependency-impact-analyzer`
- `pressure-test`

构造：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: wrong-port
  namespace: cce-skill-chaos
  labels:
    app: wrong-port
spec:
  replicas: 1
  selector:
    matchLabels:
      app: wrong-port
  template:
    metadata:
      labels:
        app: wrong-port
    spec:
      containers:
      - name: app
        image: nginx:1.25
        ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: wrong-port
  namespace: cce-skill-chaos
spec:
  selector:
    app: wrong-port
  ports:
  - name: http
    port: 80
    targetPort: 8081
```

期望：

- Service 有 endpoints，但目标端口与容器监听端口不一致。
- Network diagnoser 应区分“无 endpoint”和“endpoint 存在但端口错误/连接失败”。
- Pressure-test 应把失败归因为路由/后端端口问题，而不是吞吐不足。

清理：

```bash
kubectl cce "${K_ARGS[@]}" -n "$NS" delete deploy,svc wrong-port --ignore-not-found
```

### TC-09 NetworkPolicy 阻断

前提：集群 CNI 支持 NetworkPolicy。

覆盖：

- `network-failure-diagnoser`
- `dependency-impact-analyzer`
- `root-cause-analyzer`

构造：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: np-backend
  namespace: cce-skill-chaos
  labels:
    app: np-backend
spec:
  replicas: 1
  selector:
    matchLabels:
      app: np-backend
  template:
    metadata:
      labels:
        app: np-backend
    spec:
      containers:
      - name: app
        image: nginx:1.25
        ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: np-backend
  namespace: cce-skill-chaos
spec:
  selector:
    app: np-backend
  ports:
  - port: 80
    targetPort: 80
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-all-ingress
  namespace: cce-skill-chaos
spec:
  podSelector:
    matchLabels:
      app: np-backend
  policyTypes:
  - Ingress
```

验证请求：

```bash
kubectl cce "${K_ARGS[@]}" -n "$NS" run np-client --rm -i --restart=Never --image=curlimages/curl -- curl -m 5 http://np-backend
```

期望：

- Service/Endpoint 正常但流量不可达。
- Network diagnoser 应引用 NetworkPolicy 作为可能阻断层。
- 如果 CNI 不执行 NetworkPolicy，应把此用例标记为环境不支持，而不是 skill 失败。

清理：

```bash
kubectl cce "${K_ARGS[@]}" -n "$NS" delete deploy,svc np-backend --ignore-not-found
kubectl cce "${K_ARGS[@]}" -n "$NS" delete networkpolicy deny-all-ingress --ignore-not-found
```

### TC-10 PVC Pending: 不存在的 StorageClass

覆盖：

- `storage-failure-diagnoser`
- `pod-failure-diagnoser`
- `workload-failure-diagnoser`
- `kubernetes-event-analyzer`
- `root-cause-analyzer`

构造：

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: pvc-missing-sc
  namespace: cce-skill-chaos
spec:
  accessModes:
  - ReadWriteOnce
  storageClassName: cce-skill-missing-sc
  resources:
    requests:
      storage: 1Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pvc-missing-sc
  namespace: cce-skill-chaos
  labels:
    app: pvc-missing-sc
spec:
  replicas: 1
  selector:
    matchLabels:
      app: pvc-missing-sc
  template:
    metadata:
      labels:
        app: pvc-missing-sc
    spec:
      containers:
      - name: app
        image: busybox:1.36
        command: ["sleep", "3600"]
        volumeMounts:
        - mountPath: /data
          name: data
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: pvc-missing-sc
```

期望：

- Storage diagnoser 报告 PVC Pending、StorageClass 不存在或 provisioner 不可用。
- Pod/workload diagnoser 将 Pending/FailedScheduling 与 PVC 证据关联。
- 如果没有 VolumeAttachment 权限，应写数据缺口。

清理：

```bash
kubectl cce "${K_ARGS[@]}" -n "$NS" delete deploy pvc-missing-sc --ignore-not-found
kubectl cce "${K_ARGS[@]}" -n "$NS" delete pvc pvc-missing-sc --ignore-not-found
```

### TC-11 FailedMount: 引用不存在的 ConfigMap

覆盖：

- `pod-failure-diagnoser`
- `storage-failure-diagnoser`
- `kubernetes-event-analyzer`

构造：

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: missing-configmap-mount
  namespace: cce-skill-chaos
  labels:
    app: missing-configmap-mount
spec:
  containers:
  - name: app
    image: busybox:1.36
    command: ["sleep", "3600"]
    volumeMounts:
    - name: cfg
      mountPath: /etc/test
  volumes:
  - name: cfg
    configMap:
      name: missing-configmap
```

期望：

- Event analyzer 聚合 `FailedMount`。
- Pod diagnoser 报告挂载对象不存在。
- Storage diagnoser 应说明这是 Kubernetes volume mount 配置问题，不是 EVS/SFS 后端容量问题。

清理：

```bash
kubectl cce "${K_ARGS[@]}" -n "$NS" delete pod missing-configmap-mount --ignore-not-found
```

### TC-12 ResourceQuota 阻断副本创建

覆盖：

- `workload-failure-diagnoser`
- `pod-failure-diagnoser`
- `kubernetes-event-analyzer`
- `change-impact-analyzer`

构造：

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: rq-pods-one
  namespace: cce-skill-chaos
spec:
  hard:
    pods: "1"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: quota-blocked
  namespace: cce-skill-chaos
  labels:
    app: quota-blocked
spec:
  replicas: 3
  selector:
    matchLabels:
      app: quota-blocked
  template:
    metadata:
      labels:
        app: quota-blocked
    spec:
      containers:
      - name: app
        image: nginx:1.25
```

期望：

- Workload diagnoser 报告 desired/updated/available 差异。
- Event 中应出现 quota exceeded 或 replica creation blocked。
- 下一步建议包括调整 quota 或缩小副本数。

清理：

```bash
kubectl cce "${K_ARGS[@]}" -n "$NS" delete deploy quota-blocked --ignore-not-found
kubectl cce "${K_ARGS[@]}" -n "$NS" delete resourcequota rq-pods-one --ignore-not-found
```

### TC-13 StatefulSet 更新异常

覆盖：

- `workload-failure-diagnoser`
- `pod-failure-diagnoser`
- `change-impact-analyzer`

构造：

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: sts-bad-image
  namespace: cce-skill-chaos
spec:
  serviceName: sts-bad-image
  replicas: 2
  selector:
    matchLabels:
      app: sts-bad-image
  template:
    metadata:
      labels:
        app: sts-bad-image
    spec:
      containers:
      - name: app
        image: nginx:1.25
        ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: sts-bad-image
  namespace: cce-skill-chaos
spec:
  clusterIP: None
  selector:
    app: sts-bad-image
  ports:
  - port: 80
```

变更构造：

```bash
kubectl cce "${K_ARGS[@]}" apply -f tc-13-sts.yaml
kubectl cce "${K_ARGS[@]}" -n "$NS" rollout status statefulset/sts-bad-image --timeout=120s
kubectl cce "${K_ARGS[@]}" -n "$NS" set image statefulset/sts-bad-image app=azxsdc:latest
```

期望：

- Workload diagnoser 识别 StatefulSet ordinal、currentRevision/updateRevision、未 Ready Pod。
- Change analyzer 将镜像更新作为相关变更。

清理：

```bash
kubectl cce "${K_ARGS[@]}" -n "$NS" delete statefulset sts-bad-image --ignore-not-found
kubectl cce "${K_ARGS[@]}" -n "$NS" delete svc sts-bad-image --ignore-not-found
```

### TC-14 DaemonSet rollout 异常

覆盖：

- `workload-failure-diagnoser`
- `pod-failure-diagnoser`
- `node-failure-diagnoser`

构造：

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: ds-bad-selector
  namespace: cce-skill-chaos
  labels:
    app: ds-bad-selector
spec:
  selector:
    matchLabels:
      app: ds-bad-selector
  template:
    metadata:
      labels:
        app: ds-bad-selector
    spec:
      nodeSelector:
        cce-skill-test/nonexistent: "true"
      containers:
      - name: app
        image: busybox:1.36
        command: ["sleep", "3600"]
```

期望：

- Workload diagnoser 报告 desired/current/ready/available 差异。
- Node diagnoser 识别没有节点满足 selector，而不是节点全部故障。

清理：

```bash
kubectl cce "${K_ARGS[@]}" -n "$NS" delete daemonset ds-bad-selector --ignore-not-found
```

### TC-15 依赖链断裂: frontend -> api -> db

覆盖：

- `dependency-impact-analyzer`
- `network-failure-diagnoser`
- `root-cause-analyzer`
- `observability-context-builder`

构造：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: cce-skill-chaos
  labels:
    app: frontend
spec:
  replicas: 1
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      containers:
      - name: app
        image: nginx:1.25
---
apiVersion: v1
kind: Service
metadata:
  name: frontend
  namespace: cce-skill-chaos
spec:
  selector:
    app: frontend
  ports:
  - port: 80
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
  namespace: cce-skill-chaos
  labels:
    app: api
spec:
  replicas: 1
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
    spec:
      containers:
      - name: app
        image: nginx:1.25
---
apiVersion: v1
kind: Service
metadata:
  name: api
  namespace: cce-skill-chaos
spec:
  selector:
    app: api
  ports:
  - port: 80
---
apiVersion: v1
kind: Service
metadata:
  name: db
  namespace: cce-skill-chaos
spec:
  selector:
    app: db-missing
  ports:
  - port: 5432
```

期望：

- Dependency analyzer 输出入口、Service、Endpoint、Pod、Node 路径。
- 影响半径应识别 `db` 无后端，而不是把 frontend/api 本身作为根因。
- Root cause 可以把“下游依赖 Service 无 endpoints”作为候选根因。

清理：

```bash
kubectl cce "${K_ARGS[@]}" -n "$NS" delete deploy frontend api --ignore-not-found
kubectl cce "${K_ARGS[@]}" -n "$NS" delete svc frontend api db --ignore-not-found
```

## 6. 受控节点池用例

这些用例只在专用测试节点池执行。没有专用节点池时跳过，并在测试报告中标记为 `not run: requires isolated node pool`。

### TC-16 taint/toleration 不匹配

覆盖：

- `node-failure-diagnoser`
- `workload-failure-diagnoser`
- `pod-failure-diagnoser`
- `kubernetes-event-analyzer`

构造：

```bash
TEST_NODE=<dedicated-test-node-name>
kubectl cce "${K_ARGS[@]}" label node "$TEST_NODE" cce-skill-test-node=tainted
kubectl cce "${K_ARGS[@]}" taint node "$TEST_NODE" cce-skill-test=only:NoSchedule
```

创建不带 toleration 但只允许调度到该测试节点的 Pod：

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: taint-blocked
  namespace: cce-skill-chaos
spec:
  nodeSelector:
    cce-skill-test-node: tainted
  containers:
  - name: app
    image: busybox:1.36
    command: ["sleep", "3600"]
```

期望：

- Event 包含 untolerated taint 或调度阻断。
- Node diagnoser 报告 taint/toleration 不匹配。

清理：

```bash
kubectl cce "${K_ARGS[@]}" -n "$NS" delete pod taint-blocked --ignore-not-found
kubectl cce "${K_ARGS[@]}" taint node "$TEST_NODE" cce-skill-test=only:NoSchedule-
kubectl cce "${K_ARGS[@]}" label node "$TEST_NODE" cce-skill-test-node-
```

### TC-17 节点压力信号

覆盖：

- `node-failure-diagnoser`
- `metric-analyzer`
- `pod-failure-diagnoser`
- `root-cause-analyzer`

构造方法：

1. 在专用测试节点池上加 label：`cce-skill-test=pressure`。
2. 创建限定到测试节点的 stress Deployment，逐步增加 CPU 或 memory 压力。
3. 观察 node `Conditions`、Pod eviction/OOM、metrics-server 或 AOM 指标。

安全边界：

- 不在生产节点池执行。
- 不制造磁盘写满类测试，除非节点可重建。
- 压力持续时间建议小于 10 分钟。

期望：

- Node diagnoser 先看 Node Conditions/taints/events，再看 Pod 分布。
- Metric analyzer 输出节点 CPU/memory 趋势或数据缺口。
- Root cause 不能仅凭单个 stress Pod 就判定全局节点故障，必须说明影响范围。

### TC-18 NodeNotReady

覆盖：

- `node-failure-diagnoser`
- `workload-failure-diagnoser`
- `root-cause-analyzer`
- `alarm-correlation-engine`

构造方法：

- 首选：使用可销毁测试节点池，手动停止/隔离一台测试节点，使其进入 NotReady。
- 备选：如果不允许影响真实节点，跳过该用例，并用已有历史 NodeNotReady 事件/告警验证只读分析能力。

期望：

- Node diagnoser 报告 Node condition、taints、受影响 Pod 和调度影响。
- Root cause 把 NodeNotReady 与 Pod Pending/Evicted/Unavailable 关联。
- Alarm analyzer 如果没有 CCE 节点告警，要写明告警证据缺口。

## 7. Ingress / ELB / 外部访问用例

这些用例依赖集群已安装 Ingress controller 或支持 LoadBalancer Service。

### TC-19 Ingress backend service 不存在或端口不匹配

覆盖：

- `network-failure-diagnoser`
- `dependency-impact-analyzer`
- `change-impact-analyzer`
- `pressure-test`

构造：

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: bad-ingress
  namespace: cce-skill-chaos
spec:
  rules:
  - host: bad-ingress.example.test
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: missing-service
            port:
              number: 80
```

期望：

- Network diagnoser 报告 Ingress backend 指向不存在 Service。
- Dependency analyzer 输出 Ingress -> Service 断点。
- Pressure-test 路由预检失败，不应进入正式压测。

清理：

```bash
kubectl cce "${K_ARGS[@]}" -n "$NS" delete ingress bad-ingress --ignore-not-found
```

### TC-20 LoadBalancer Service 后端不健康

覆盖：

- `network-failure-diagnoser`
- `metric-analyzer`
- `alarm-correlation-engine`
- `pressure-test`

构造方法：

1. 创建 LoadBalancer Service 指向 TC-06 的 readiness 失败后端，或 TC-08 的错误端口后端。
2. 等待 ELB 资源创建。
3. 使用 hcloud 查询 ELB/listener/pool/member/health 状态。

期望：

- Network diagnoser 能把 Kubernetes Service/Endpoint 与 ELB 后端状态关联。
- Metric analyzer 可查询 ELB/CES 指标；不可用时记录缺口。
- Alarm analyzer 尝试关联 ELB/CCE 告警，不能因无 active alarm 就判定健康。

清理：

```bash
kubectl cce "${K_ARGS[@]}" -n "$NS" delete svc <loadbalancer-service-name> --ignore-not-found
```

## 8. 可观测与分析类用例

### TC-21 Kubernetes Event 聚合

覆盖：

- `kubernetes-event-analyzer`
- `observability-context-builder`
- `root-cause-analyzer`

构造：

同时运行 TC-01、TC-04、TC-10，产生 ImagePull、FailedScheduling、PVC Pending/FailedMount 类 Warning Event。

期望：

- Event analyzer 按 reason 分组，输出 count、样例 message、影响对象和时间线。
- Recommended handoff 应分别指向 pod/workload/node/storage/network 等具体 skill。
- 如果查询历史窗口超出现有 Event retention，应记录 LTS/retention gap。

### TC-22 Metric Analyzer: Pod CPU 压力

覆盖：

- `metric-analyzer`
- `pressure-test`
- `root-cause-analyzer`

构造：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cpu-hot
  namespace: cce-skill-chaos
  labels:
    app: cpu-hot
spec:
  replicas: 1
  selector:
    matchLabels:
      app: cpu-hot
  template:
    metadata:
      labels:
        app: cpu-hot
    spec:
      containers:
      - name: app
        image: polinux/stress
        command: ["stress"]
        args: ["--cpu", "1"]
        resources:
          requests:
            cpu: "100m"
            memory: "64Mi"
          limits:
            cpu: "500m"
            memory: "128Mi"
```

期望：

- Metric analyzer 尝试读取 Pod/Node top、AOM 或 CES 指标。
- 如果 metrics-server 不可用，应报告 `metrics unavailable`，并建议用 AOM/CES 或安装 metrics-server 验证。
- Root cause 只能在指标与事件/症状时间对齐时提升置信度。

清理：

```bash
kubectl cce "${K_ARGS[@]}" -n "$NS" delete deploy cpu-hot --ignore-not-found
```

### TC-23 Alarm Correlation: 有异常但无告警

覆盖：

- `alarm-correlation-engine`
- `observability-context-builder`
- `root-cause-analyzer`

构造：

运行 TC-01 或 TC-03 后查询相同时间窗口内的 AOM/CES 告警。

期望：

- 如果没有 active/history alarm，报告应写“未发现可用告警证据”或“告警规则/历史不可用”，不能写“集群健康”。
- 如果存在告警，应按资源、严重级别、首次/最后时间、状态分组。
- Next Actions 应建议继续查看 Events/Pods/metrics，而不是只依赖告警。

### TC-24 Observability Context Package

覆盖：

- `observability-context-builder`
- `root-cause-analyzer`

构造：

同时保留 TC-01、TC-06、TC-10 中至少两个异常，并给出统一故障窗口。

期望：

- 输出 `Summary`、`Scope`、`High-Signal Findings`、`Timeline`、`Evidence By Source`、`Data Gaps`、`Recommended Handoff`。
- Recommended handoff 应指向具体 domain skill。
- Root cause analyzer 使用该上下文时，应复用时间线和数据缺口，而不是重新散乱采集。

### TC-25 Root Cause: rollout 镜像变更导致服务不可用

覆盖：

- `root-cause-analyzer`
- `observability-context-builder`
- `change-impact-analyzer`
- `workload-failure-diagnoser`
- `pod-failure-diagnoser`
- `event/metric/alarm` 辅助证据

构造：

1. 先部署一个正常 Deployment + Service。
2. 记录正常 ready endpoints。
3. 执行 `kubectl cce ... set image deploy/<name> app=azxsdc:latest`。
4. 等待新 Pod 进入 ImagePullBackOff。
5. 让 root-cause 对“服务不可用”做跨域分析。

期望：

- Top1 根因：最近 rollout 镜像变更引入无法拉取镜像。
- 直接证据：rollout revision/change time、Pod Event、image string、available replicas/endpoints 变化。
- 反证：节点 Ready、Service selector 未变、PVC 无关、网络无明显阻断。
- 下一步：回滚镜像、修正 SWR/镜像 tag/imagePullSecret、再验证 rollout。

### TC-26 Root Cause: Service selector 变更导致入口无后端

覆盖：

- `root-cause-analyzer`
- `change-impact-analyzer`
- `network-failure-diagnoser`
- `dependency-impact-analyzer`
- `observability-context-builder`

构造：

1. 使用 TC-07，先让 selector 正确。
2. 再 patch 成不匹配 selector。
3. 以“入口 503/连接失败”为症状触发 root-cause。

期望：

- Top1 根因：Service selector 变更导致 Endpoints/EndpointSlices 为空。
- 反证：后端 Pod Running/Ready，节点 Ready，镜像正常。
- 下一步：恢复 selector 或后端 label，验证 endpoints 和请求成功率。

## 9. 压测 skill 用例

### TC-27 压测预检通过的基线服务

覆盖：

- `pressure-test`
- `metric-analyzer`

构造：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: baseline-nginx
  namespace: cce-skill-chaos
  labels:
    app: baseline-nginx
spec:
  replicas: 2
  selector:
    matchLabels:
      app: baseline-nginx
  template:
    metadata:
      labels:
        app: baseline-nginx
    spec:
      containers:
      - name: app
        image: nginx:1.25
        ports:
        - containerPort: 80
        resources:
          requests:
            cpu: "50m"
            memory: "64Mi"
          limits:
            cpu: "500m"
            memory: "128Mi"
---
apiVersion: v1
kind: Service
metadata:
  name: baseline-nginx
  namespace: cce-skill-chaos
spec:
  selector:
    app: baseline-nginx
  ports:
  - port: 80
    targetPort: 80
```

期望：

- 压测前检查 Service、Endpoint、Pod Ready、Events。
- 压测结果包含吞吐、p95/p99、错误率、资源水位、数据缺口。
- 如果 local k6 不可用，允许切换 in-cluster k6；如果 k6 Job image pull 失败，必须把它作为压测执行失败根因。

清理：

```bash
kubectl cce "${K_ARGS[@]}" -n "$NS" delete deploy,svc baseline-nginx --ignore-not-found
```

### TC-28 压测目标无可用后端

覆盖：

- `pressure-test`
- `network-failure-diagnoser`
- `dependency-impact-analyzer`

构造：

使用 TC-06 或 TC-07 的 Service。

期望：

- Pressure-test 在预检阶段发现无 ready endpoint 或 selector mismatch。
- 报告结论应为目标不可压测/路由异常，而不是性能瓶颈。

### TC-29 HPA 扩容滞后或达到上限

覆盖：

- `pressure-test`
- `metric-analyzer`
- `workload-failure-diagnoser`
- `root-cause-analyzer`

前提：集群支持 metrics-server/HPA 指标。

构造方法：

1. 给 baseline-nginx 或 CPU 消耗服务配置 HPA，`maxReplicas` 设置较小，例如 2。
2. 用 k6 逐步增压。
3. 观察 HPA current/desired、Pod CPU、延迟、错误率。

期望：

- Pressure-test 报告瓶颈是 HPA 上限/扩容滞后/节点容量，而不是单纯应用错误。
- Metric analyzer 关联延迟上升和 CPU/HPA 时间线。

## 10. 变更分析用例

### TC-30 Deployment scale-to-zero

覆盖：

- `change-impact-analyzer`
- `workload-failure-diagnoser`
- `dependency-impact-analyzer`
- `root-cause-analyzer`

构造：

```bash
kubectl cce "${K_ARGS[@]}" -n "$NS" scale deploy baseline-nginx --replicas=0
```

期望：

- Change analyzer 将 scale 变更列为高相关变更。
- Workload diagnoser 报告 desired=0 和业务不可用之间的关系。
- Root cause 应说明这是人为缩容/变更影响，不是 Pod 异常。

恢复：

```bash
kubectl cce "${K_ARGS[@]}" -n "$NS" scale deploy baseline-nginx --replicas=2
```

### TC-31 ConfigMap 变更后应用 CrashLoop

覆盖：

- `change-impact-analyzer`
- `pod-failure-diagnoser`
- `root-cause-analyzer`

构造方法：

1. 创建 Deployment 从 ConfigMap 读取启动参数。
2. 先使用正常参数启动。
3. 修改 ConfigMap 为非法参数，并 rollout restart。
4. Pod 进入 CrashLoop。

期望：

- Change analyzer 识别 ConfigMap 变更和 rollout restart。
- Pod diagnoser 报告 previous logs 中的应用错误。
- Root cause 将配置变更作为高置信候选，并给出回滚配置/重启验证建议。

## 11. 数据缺口与权限用例

### TC-32 RBAC 缺口

覆盖：全部读集群类 skill。

构造方法：

使用一个只允许读取 Pods、但不允许读取 Events/Logs/Nodes/PVC 的低权限身份执行诊断。

期望：

- skill 不尝试绕过 `kubectl cce`、不生成 kubeconfig、不改用 SDK。
- 报告写明 RBAC denied 的资源类型和对置信度的影响。

### TC-33 metrics-server/AOM/CES/LTS 不可用

覆盖：

- `metric-analyzer`
- `alarm-correlation-engine`
- `kubernetes-event-analyzer`
- `observability-context-builder`
- `root-cause-analyzer`

构造方法：

- 在没有配置 metrics-server、AOM、CES 告警、LTS 事件日志的集群上运行 TC-01 或 TC-03。

期望：

- 报告明确写数据源不可用或无权限。
- 不把“查不到指标/告警/历史事件”解释为“没有异常”。
- Root cause 仍可基于 Kubernetes 当前对象、Events、logs 给出有限置信判断。

## 12. 一次完整联测路线

建议按以下顺序跑，既能覆盖主要能力，又方便清理：

1. ST-01、ST-02：先做静态和报告格式回归。
2. TC-01：镜像拉取异常，验证 Pod/workload/event/root-cause 基础链路。
3. TC-06、TC-07、TC-08：验证网络、依赖和压测预检。
4. TC-10、TC-11：验证存储和挂载异常。
5. TC-21、TC-24、TC-25：验证 observability context 和 root-cause 聚合。
6. TC-27、TC-28：验证 pressure-test 正常和异常前置判断。
7. TC-16 到 TC-18：只有专用节点池时再跑。
8. TC-19、TC-20、TC-29：只有 Ingress/ELB/HPA 条件满足时再跑。

## 13. 每个 skill 的最低验收清单

| Skill | 最低通过标准 |
| --- | --- |
| workload | 能从 workload 状态下钻到 ReplicaSet/Pod/Event，并明确第一个失败层 |
| pod | 能识别 ImagePull、CrashLoop、OOM、Pending、Probe、Mount 中至少 5 类，并提供证据和下一步 |
| node | 能区分资源不足、约束不匹配、节点压力、NodeNotReady/数据缺口 |
| network | 能区分无 endpoint、selector 错误、端口错误、NetworkPolicy、Ingress/ELB 断点 |
| storage | 能区分 PVC Pending、StorageClass、FailedMount、CSI/云侧证据缺口 |
| pressure-test | 预检能阻止无效压测，正式压测能输出瓶颈、指标和清理建议 |
| event | 能按 reason 聚合、给样例、映射 handoff skill、说明历史事件缺口 |
| metric | 能输出指标信号/缺口，并要求与其他证据关联后再定高置信 |
| alarm | 能分组告警，也能正确处理“无告警/无历史/无权限” |
| change | 能把 rollout、scale、selector、config 变更与症状时间线关联 |
| dependency | 能输出入口到后端的依赖路径和影响半径 |
| observability | 能形成上下文包，包含时间线、高信号发现、数据缺口和 handoff |
| root-cause | 能复用上下文，输出 Top3 根因、证据、反证、置信度和下一步 |

## 14. 最终测试报告模板

每次实测后按下面格式记录：

```markdown
# CCE CLI Skill 联测报告

## Summary
- 集群：
- 命名空间：
- 时间窗口：
- 结论：

## Root Cause / Capability Result
| 用例 | Skill | 结果 | 主要结论 | 数据缺口 |
| --- | --- | --- | --- | --- |

## Next Actions
-

## Evidence
- Commands used:
- Key Events:
- Key Logs:
- Metrics/Alarms:

## Cleanup
- 已清理：
- 未清理：

## Guardrail Check
- 未发现 AK/SK/token 泄露：
- 未发现 SDK/dispatcher/kubeconfig 路径：
- 所有 Kubernetes 访问均使用 kubectl cce：
```
