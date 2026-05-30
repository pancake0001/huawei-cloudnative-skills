# Workflow

## 复用优先级

已有能力必须优先复用：

- K8s 对象：`huawei_get_cce_services`、`huawei_get_cce_ingresses`、`huawei_get_cce_pods`、`huawei_get_kubernetes_nodes`、`huawei_get_cce_events`、`huawei_get_pod_logs`。
- 云网络：`huawei_list_elb`、`huawei_list_elb_listeners`、`huawei_get_elb_metrics`、`huawei_list_eip`、`huawei_get_eip_metrics`、`huawei_list_nat`、`huawei_get_nat_gateway_metrics`、`huawei_list_security_groups`、`huawei_list_vpc_acls`。
- 旧版综合诊断：`huawei_network_diagnose`、`huawei_network_diagnose_by_alarm`，可继续用于工作负载维度的链路和监控粗诊断。
- 日志与观测：已有 LTS/AOM 日志、Pod 日志、AOM 指标能力，不重新实现日志平台或指标平台。

本 skill 新补齐的薄层能力：

- `huawei_network_failure_diagnose`：一次性采集 Service、Ingress、EndpointSlice、NetworkPolicy、Node、Pod、Events、CoreDNS/Ingress 日志和云 ELB 后端健康，直接生成 Markdown 报告。
- `huawei_get_elb_backend_status`：读取 ELB pool/member/health monitor/load balancer status，补齐只看 ELB 指标无法确认具体后端健康的问题。

仍不做的事：

- 不执行 `kubectl exec` 主动探测，不修改安全组/ACL/ELB/Ingress/Service。
- 不替代 `pod-failure-diagnoser`、`node-failure-diagnoser`、`workload-failure-diagnoser`；遇到 Pod/Node/发布根因时只交叉引用。

## 输入与采集

最小输入为 `region`、`cluster_id`、`namespace`。尽量补齐以下字段：

- `failure_symptom`：`域名无法解析`、`集群内服务不通`、`服务偶现抖动`、`外部域名/IP 无法访问`、`Ingress 502/504`。
- `target_kind` + `target_name`：Pod、Service、Ingress 等。
- `service_name`、`ingress_name`、`source_pod`、`destination_pod`、`domain`、`elb_id`。

默认先调用 `huawei_network_failure_diagnose`。它会形成同一时刻附近的只读上下文快照，并返回：

- `snapshot`：原始对象和云侧上下文。
- `findings` / `top_causes`：结构化诊断命中项。
- `report_markdown`：最终交付给客户的完整 Markdown 报告。

## 分层诊断流水线

### 1. 基础设施与节点层

先检查目标源/目的 Pod、后端 Pod、CoreDNS/Ingress Controller 所在节点：

- `Ready=False` 或 `Ready=Unknown`：直接输出节点底座故障，并剪枝跳过上层应用诊断。
- `MemoryPressure`、`DiskPressure`、`PIDPressure`、`NetworkUnavailable=True`：关联 `OOMKilled`、`KubeletNotReady`、`Evicted`、`FailedCreatePodSandBox` 等事件。若与故障窗口重合，可剪枝。

### 2. DNS 链路

触发条件：`failure_symptom` 包含 DNS、域名、解析、NXDOMAIN 等。

路径：客户端 Pod -> `kube-dns` Service -> CoreDNS Pods -> 上游 DNS / 集群 Service DNS。

断言：

- 客户端 Pod `dnsPolicy=None` 且无 `dnsConfig`：输出 Pod DNS 配置缺失。
- `kube-dns` EndpointSlice ready endpoint 为 0：输出 CoreDNS 后端不可用。
- CoreDNS Events 中有 `OOMKilled`、`Liveness probe failed`、`Unhealthy`、`BackOff`：输出 CoreDNS 重启/探针失败导致解析抖动。
- CoreDNS logs 中有 `NXDOMAIN`：输出服务名拼写、namespace 后缀或服务不存在。
- CoreDNS logs 中有 `i/o timeout` / timeout：输出上游 DNS 或集群外网络故障候选。

### 3. 东西向 Service 与策略

触发条件：集群内 Service 不通、偶现不通、服务抖动，或未指定外部链路时的默认检查。

路径：源 Pod -> NetworkPolicy -> Service -> EndpointSlice -> 目的 Pod。

断言：

- 目标 Pod 被 NetworkPolicy 选中，但规则未放行源 Pod 标签、namespace 标签或端口：输出 NetworkPolicy 拦截，置信度 100%。
- Service selector 无匹配 Pod，或 EndpointSlice ready endpoint 为 0：输出 Service selector/后端拓扑断裂。
- 后端 Pod Events 有密集 `Readiness probe failed` 或 `Unhealthy`：输出 readiness 抖动导致后端被摘除。
- 后端应用日志有 OOM、连接池耗尽、connection refused：输出应用自身过载/拒绝服务候选。

### 4. 南北向 Ingress/ELB

触发条件：外部域名/IP 访问失败、Ingress 502/504、ELB 后端异常。

路径：外部请求 -> 云 ELB/EIP -> Ingress Controller -> Service -> EndpointSlice -> Pod。

断言：

- Ingress 或 LoadBalancer Service 的 `status.loadBalancer.ingress` 为空：关联 CCM/CCE Events 中的 ELB 创建失败、配额不足、权限不足、安全组/子网错误。
- ELB member/pool 状态非健康，K8s 后端 Pod Ready：输出云安全组未放行 NodePort、健康检查端口错误、节点 IPVS/Iptables/kube-proxy 同步异常候选。
- Ingress Controller logs 中有 `502 Bad Gateway`、`504 Gateway Timeout`：输出 Ingress 到后端或后端应用响应异常，继续核对 Service/Endpoint 和应用超时。

## 报告要求

Markdown 报告必须包含：

1. 诊断总览：目标、故障现象、结论、置信度、采集时间、是否剪枝。
2. 排查过程：四阶段逐项状态，说明检查过、异常或剪枝跳过。
3. 链路拓扑：按故障类型输出 DNS、东西向或南北向链路。
4. 关键对象快照：Service、EndpointSlice、Backend Pods、Ingress、NetworkPolicy、Cloud ELB。
5. 证据矩阵：阶段、类型、置信度、证据摘要。
6. Top 根因：最多 3 个，必须有证据支撑。
7. 建议动作与验证标准：只读验证或转交恢复 skill 的变更建议。
