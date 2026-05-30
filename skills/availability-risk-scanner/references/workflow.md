# Workflow

## 1. 采集范围

优先使用 `huawei_scan_cce_availability_risk`。常用参数：

- `region`、`cluster_id`：必填。
- `exclude_namespaces`：默认 `kube-system`；核心插件仍会被单独识别。
- `gateway_keywords`：默认 `nginx,gateway,ingress,proxy,kong,apisix,traefik`。
- `metrics_hours`：默认 24，用于 master/节点 CPU、内存趋势。
- `output_dir`：输出 `availability-risk-summary.json` 和 `availability-risk-report.md`。

## 2. 控制面和节点风险

检查项：

- 可见 master/control-plane 节点数量是否小于 3。
- 可见 master 是否跨 AZ。
- master CPU/内存平均值是否偏高。
- Ready 节点是否集中在单 AZ，或某个 AZ 占比过高。
- 节点池/节点 AZ 分布是否和业务 HA 目标匹配。

如果 CCE 托管控制面不暴露 master 节点，必须在报告中标记数据缺口，不要假设 master 一定高可用。

## 3. 工作负载风险

检查 Deployment、StatefulSet、DaemonSet：

- 单副本：业务或网关类工作负载副本数小于 2。
- PDB 缺失：多副本业务或网关工作负载没有匹配 PodDisruptionBudget。
- Pod 分布：多个副本集中在一个节点，或在多 AZ 集群中集中在一个 AZ。
- 健康检查：缺少 readinessProbe 或 livenessProbe。
- 亲和性：硬性绑定到单 AZ、单节点、某个节点池，或缺少反亲和/拓扑分散。
- 核心插件：CoreDNS、nginx-ingress、ingress-nginx 是否多副本反亲和或拓扑分散。
- 网关应用：nginx、gateway、ingress、proxy、kong、apisix、traefik 等是否均衡部署、配置 PDB 和健康检查。

## 4. 资源超配

检查 request/limit：

- request 未配置：标记为中风险，因为调度、HPA、驱逐和容量评估会失真。
- CPU limit/request 比例大于默认 4：标记为低风险，需确认是否为有意突发。
- Memory limit/request 比例大于默认 2：标记为中风险，需优先评估 OOM 与 bin-packing 风险。
- 汇总集群 request 和 limit 占 allocatable 比例，用于发现整体超配或容量假象。

## 5. 输出和整改

输出顺序：

1. 总体风险等级和问题计数。
2. 控制面、节点 AZ、Pod AZ、资源超配摘要。
3. Top 风险问题清单。
4. 网关和核心插件专项问题。
5. 数据缺口。
6. 整改建议和授权后执行计划。

整改必须先获得客户明确授权，再生成或应用 PDB、探针、反亲和、拓扑分散、扩副本或资源 request/limit 调整。
