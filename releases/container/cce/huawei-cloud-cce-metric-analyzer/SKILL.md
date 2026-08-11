---
id: huawei-cloud-cce-metric-analyzer
name: huawei-cloud-cce-metric-analyzer
description: |
  Analyze Huawei Cloud CCE, Kubernetes component, and related cloud-resource metrics with hcloud CLI, kubectl-cce plugin commands, and approved AOM/CES evidence paths. Use this skill when the user needs Pod/Node TopN usage, component metrics, ECS/ELB/EIP/NAT metrics, threshold classification, anomaly evidence, or metric correlation for root-cause analysis. Do not use Huawei Cloud SDKs, generated kubeconfig, or legacy dispatcher actions.
tags: [cce, metrics, aom, ces, observability, analysis, hcloud, kubectl-cce]
---

# Huawei Cloud CCE Metric Analyzer

## Overview

This skill collects read-only metric evidence for CCE incidents. It is normally used by root-cause, change-impact, workload, Pod, node, and network diagnosis flows when metric evidence is needed to prove or reject resource pressure, traffic drops, component latency, scaling behavior, or cloud-resource bottlenecks.

Primary access paths:

1. `hcloud` CLI for CCE metadata, CES cloud metrics, and cloud-resource discovery.
2. `kubectl cce` for Kubernetes resource relationships and live Metrics API checks.
3. Approved AOM Prometheus range-query evidence for CCE Pod/Node/component time series when the cluster has AOM Prometheus integration. If the current runtime cannot query the AOM range endpoint safely, record it as a data gap.

Do not call Huawei Cloud SDK imports, generate kubeconfig, patch kubeconfig servers, use Kubernetes SDK clients, or fall back to old dispatcher-style actions.

## Related Skills

| Skill | Use When |
| ----- | -------- |
| `huawei-cloud-cce-root-cause-analyzer` | Metrics are part of a cross-domain incident timeline |
| `huawei-cloud-cce-workload-failure-diagnoser` | Metric spikes align with rollout, HPA, replica, or readiness symptoms |
| `huawei-cloud-cce-pod-failure-diagnoser` | A Pod has high CPU/memory, restart loops, throttling, or OOM suspicion |
| `huawei-cloud-cce-node-failure-diagnoser` | Node CPU/memory/disk/network pressure may affect workloads |
| `huawei-cloud-cce-network-failure-diagnoser` | ELB/EIP/NAT/Ingress traffic or packet-loss metrics may explain access failures |
| `huawei-cloud-cce-kubernetes-event-analyzer` | Events are needed to explain a metric spike or missing metrics |

## Prerequisites

- `hcloud` is installed, works on the current platform, and can run read-only Huawei Cloud commands.
- `kubectl` and the `kubectl-cce` plugin are installed when Kubernetes resource relationships are needed. Read [references/kubectl-cce.md](references/kubectl-cce.md) first.
- Region, project ID, and cluster ID are known or can be discovered with `hcloud CCE ListClusters`.
- AOM Prometheus integration exists for Pod/Node/component time-series evidence. Missing AOM data is a data gap, not proof of health.
- CES permissions exist for ECS/ELB/EIP/NAT cloud-resource metrics.

Never print AK/SK, security tokens, Authorization headers, kubeconfig content, or signed request material. Use environment variables, protected local profiles, or tool-provided credentials.

## Inputs

| Input | Required | Notes |
| ----- | -------- | ----- |
| `region` | Yes | Example: `cn-north-4` |
| `project_id` | Recommended | Required for AK/SK and `kubectl cce` reliability |
| `cluster_id` | Required for CCE metrics | Resolve by exact cluster name when only a name is supplied |
| `namespace` | Optional | Narrows Pod/workload/component evidence |
| `pod_name`, `node_name`, `node_ip`, `workload_name` | Optional | Use when drilling into a specific resource |
| `hours`, `start_time`, `end_time` | Recommended | Default to the smallest useful incident window |
| `elb_id`, `eip_id`, `nat_gateway_id`, `ecs_id` | Optional | Discover before asking if the context is unambiguous |

## Evidence Commands

Use platform-neutral commands and quote values that contain spaces, JSON, comparison operators, or PromQL.

### Cluster Context

```bash
hcloud CCE ListClusters --cli-region=<region> --cli-output=json --project_id=<project-id>
hcloud CCE ShowCluster --cli-region=<region> --cli-output=json --cluster_id=<cluster-id> --project_id=<project-id>
hcloud CCE ListNodes --cli-region=<region> --cli-output=json --cluster_id=<cluster-id> --project_id=<project-id>
```

### Kubernetes Resource Relationships

Use these only when AOM/CES metrics need Kubernetes labels, Service/Ingress associations, TLS Secret metadata, or live Metrics API confirmation.

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods -A -o wide
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods -n <namespace> -l '<selector>' -o json
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get svc,ingress -A -o json
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> top pods -A
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> top nodes
```

If `top` fails because Metrics API is unavailable, report the gap and continue with AOM/CES or other evidence. Do not generate kubeconfig as a fallback.

### AOM Prometheus Evidence

Use AOM Prometheus for Pod, Node, CoreDNS, nginx-ingress, autoscaler, and control-plane time series when available. Keep queries scoped by `cluster="<cluster_id>"` and add namespace, Pod, or component filters only to reduce noise.

Recommended metric families:

| Target | Evidence |
| ------ | -------- |
| Pod | CPU usage, memory working set, restart-aligned spikes, disk/container filesystem usage |
| Node | CPU, memory, disk, filesystem pressure, GPU/xGPU if relevant |
| CoreDNS | QPS, NXDOMAIN, error rate, P95 latency, replica count, Pod CPU/memory |
| nginx-ingress | QPS, 4xx/5xx, success rate, P95 latency, active connections, controller Pod CPU/memory |
| Autoscaler/HPA | unschedulable Pods, scale-up/down activity, HPA current/desired replicas |
| Control plane | apiserver latency/error rate, etcd leader/proposals/DB/disk latency, scheduler pending/scheduling latency |

When an AOM range-query path cannot be executed through the approved runtime, write a clear data gap:

```text
AOM Prometheus range-query was not available in this runtime; Pod/Node time-series metrics could not be confirmed.
```

### CES Cloud Resource Metrics

Use CES through `hcloud` for cloud resources related to the cluster:

```bash
hcloud CES ShowMetricData --cli-region=<region> --cli-output=json --namespace=SYS.ECS --metric_name=cpu_util --dim.0=instance_id,<ecs-id> --from=<start-ms> --to=<end-ms> --period=60 --filter=average
hcloud CES ShowMetricData --cli-region=<region> --cli-output=json --namespace=SYS.ELB --metric_name=mb_l7_qps --dim.0=lbaas_instance_id,<elb-id> --from=<start-ms> --to=<end-ms> --period=60 --filter=average
hcloud CES ShowMetricData --cli-region=<region> --cli-output=json --namespace=SYS.VPC --metric_name=upstream_bandwidth_usage --dim.0=publicip_id,<eip-id> --from=<start-ms> --to=<end-ms> --period=60 --filter=average
hcloud CES ShowMetricData --cli-region=<region> --cli-output=json --namespace=SYS.NAT --metric_name=snat_connection --dim.0=nat_gateway_id,<nat-gateway-id> --from=<start-ms> --to=<end-ms> --period=60 --filter=average
```

Discover resource IDs before querying metrics:

```bash
hcloud ELB ListLoadBalancers --cli-region=<region> --cli-output=json --project_id=<project-id>
hcloud ELB ShowLoadBalancer --cli-region=<region> --cli-output=json --loadbalancer_id=<elb-id> --project_id=<project-id>
hcloud EIP ListPublicips/v3 --cli-region=<region> --cli-output=json --project_id=<project-id>
hcloud NAT ListNatGateways --cli-region=<region> --cli-output=json --project_id=<project-id>
```

## Workflow

1. Resolve cluster context: region, project ID, cluster ID, cluster phase, VPC/subnet, nodes, and relevant namespace.
2. Define the incident time window. Use user-provided times first; otherwise use a short recent window such as 1 hour.
3. Pick the metric lane:
   - Pod or workload symptoms: Pod TopN, target Pod time series, HPA/autoscaler, and rollout/event correlation.
   - Node symptoms: Node TopN, target Node time series, disk/memory pressure, and node event correlation.
   - DNS/Ingress symptoms: CoreDNS or nginx-ingress metrics plus Service/Ingress topology.
   - External access symptoms: ELB/EIP/NAT CES metrics plus Service/Ingress association.
   - Cluster-wide uncertainty: collect Pod TopN, Node TopN, component metrics, and cloud-resource metrics.
4. Correlate metric changes with Events, alarms, rollouts, and user symptom time.
5. Classify severity with thresholds, but do not treat thresholds alone as a root cause.
6. Produce a Markdown report with key findings first and raw evidence later.

## Threshold Guidance

| Resource | Critical | Warning | Notes |
| -------- | -------- | ------- | ----- |
| CPU | >80% sustained or sharp incident-time spike | >50% sustained | Check throttling/restarts before concluding |
| Memory | >85% or OOM-adjacent trend | >50% sustained | Correlate with OOMKilled, eviction, or restart Events |
| Disk | >85% | >70% | Check node pressure, image GC, PVC capacity |
| ELB latency/error | Incident-time jump against baseline | Clear degradation after change | Compare with 4xx/5xx and backend health |
| EIP bandwidth/packet loss | Saturation or non-zero packet loss matching symptom | High utilization trend | Confirm linked service/ELB/NAT before attribution |
| NAT SNAT connection | Near capacity or drop counters rising | Elevated sustained use | Confirm egress path and affected workloads |

## Output Format

Every answer should be Markdown. Put the high-signal result first:

1. `## Summary`: metric status, affected scope, and confidence.
2. `## Root Cause Signal`: whether metrics support, weaken, or cannot verify the suspected cause.
3. `## Next Actions`: concrete checks or remediations to hand off to the right diagnoser.
4. `## Metric Findings`: tables for Pod/Node/component/cloud metrics with time window and source.
5. `## Evidence Timeline`: align metric spikes/drops with Events, alarms, changes, and user symptoms.
6. `## Data Gaps`: unavailable AOM/CES/Metrics API/RBAC evidence and impact on confidence.
7. `## Commands Used`: sanitized `hcloud` and `kubectl cce` commands; never include secrets.

See [references/output-schema.md](references/output-schema.md) for table fields and recommended wording.

## Risk Rules

Read [references/risk-rules.md](references/risk-rules.md) before acting.

- Read-only only. Do not scale, restart, patch, delete, apply, edit, create, or modify resources.
- Use `hcloud` for cloud metadata/CES evidence and `kubectl cce` for Kubernetes evidence.
- Do not generate kubeconfig or use SDK clients.
- Treat missing metric series as a data gap unless another source confirms the condition.
- Do not recommend remediation from metrics alone; require corroborating Events, logs, alarms, or user symptoms.

## Verification

Before considering this skill converted, run:

```bash
kubectl version --client
kubectl plugin list
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get ns
hcloud CCE ShowCluster --cli-region=<region> --cli-output=json --cluster_id=<cluster-id> --project_id=<project-id>
hcloud CES ShowMetricData --cli-region=<region> --cli-output=json --namespace=SYS.ECS --metric_name=cpu_util --dim.0=instance_id,<ecs-id> --from=<start-ms> --to=<end-ms> --period=60 --filter=average
```

Repository checks:

```bash
rg -n "huaweicloudsdk|KubernetesClusterCertRequest|CreateKubernetesClusterCert|--kubeconfig" . --glob "!*.md"
rg -n -P "^kubectl (?!cce|version|plugin)" .
git diff --check
```

## References

| Document | Description |
| -------- | ----------- |
| [Workflow](references/workflow.md) | Metric collection lanes and correlation flow |
| [Risk Rules](references/risk-rules.md) | Read-only constraints and data-gap handling |
| [Output Schema](references/output-schema.md) | Markdown report sections and table fields |
| [kubectl-cce Usage](references/kubectl-cce.md) | Plugin setup and safe Kubernetes evidence commands |
