# CCE Pressure-Test Workflow

Use this workflow whenever a user asks to run, prepare, or analyze a CCE pressure test.

## 1. Scope The Test

Collect and record:

- Region, project ID, cluster ID or cluster name.
- Namespace, workload kind, workload name, target port, and expected route.
- Target URL and optional Host header.
- Traffic model: smoke, keepalive, short-connection, ramp, or custom k6.
- VUs, duration, optional RPS cap, thresholds, and stop conditions.
- Whether the target is production, staging, or lab.
- Who approved traffic generation and any Kubernetes/cloud mutations.
- Output directory for scripts, manifests, logs, evidence, and report.

If the target is production or customer-facing, require an approved window and stop conditions before any traffic.

## 2. Verify Tooling And Cluster Access

Use platform-neutral command names in skill output:

```bash
hcloud version
hcloud configure list
kubectl version --client
k6 version
```

If local k6 is unavailable, use an in-cluster k6 Job only after approval.

Locate the cluster and endpoints:

```bash
hcloud CCE ListClusters --project_id=<project-id> --cli-region=<region> --cli-output=json
hcloud CCE ShowCluster --cluster_id=<cluster-id> --project_id=<project-id> --detail=true --cli-region=<region> --cli-output=json
hcloud CCE ShowClusterEndpoints --cluster_id=<cluster-id> --project_id=<project-id> --cli-region=<region> --cli-output=json
```

Read `references/kubectl-cce.md`, then configure kubectl-cce plugin access and verify the plugin path:

```bash
kubectl plugin list
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get ns
```

The plugin uses `HUAWEICLOUD_SDK_AK`/`HUAWEICLOUD_SDK_SK` plus `CCE_PROJECT_ID`, temporary `HUAWEICLOUD_SECURITY_TOKEN` when needed, or `HUAWEI_IAM_TOKEN`. It
starts a short-lived local proxy for the CCE API Gateway and does not generate or store kubeconfig. Use `CCE_ENDPOINT` or `--endpoint` only when the default
`<cluster-id>.cce.<region>.myhuaweicloud.com` endpoint is not valid.

## 3. Run Read-Only Kubernetes Preflight

Verify cluster and RBAC:

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> cluster-info
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i list pods -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i list events -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i get pods/log -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i list jobs -n <client-namespace>
```

Collect baseline objects:

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get nodes -o wide
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get deploy,sts,ds -n <namespace> -o wide
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get svc,endpoints,endpointslice,ingress -n <namespace> -o wide
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get hpa,pdb -n <namespace> -o wide
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods -n <namespace> -o wide
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get events -n <namespace> --sort-by=.lastTimestamp
```

Collect metrics if available:

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> top pods -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> top nodes
```

Record `Metrics API not available` as a data gap instead of switching to SDK or guessing trends.

## 4. Check The Route Funnel

For an existing Ingress route:

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get ingress <ingress-name> -n <namespace> -o yaml
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> describe ingress <ingress-name> -n <namespace>
```

For a Service route:

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get svc <service-name> -n <namespace> -o yaml
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get endpoints <service-name> -n <namespace> -o yaml
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get endpointslice -n <namespace> -l kubernetes.io/service-name=<service-name> -o yaml
```

For the target workload:

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get <workload-kind> <workload-name> -n <namespace> -o yaml
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods -n <namespace> -l '<selector>' -o wide
```

Do not create or patch Service/Ingress until the user approves an exact manifest.

## 5. Optional Cloud Network Context

Use read-only hcloud ELB/VPC/EIP/NAT commands only when needed for north-south traffic:

```bash
hcloud ELB ListLoadBalancers/v3 --project_id=<project-id> --cli-region=<region> --cli-output=json
hcloud ELB ListListeners/v3 --project_id=<project-id> --cli-region=<region> --cli-output=json
hcloud ELB ListPools/v3 --project_id=<project-id> --cli-region=<region> --cli-output=json
hcloud ELB ListMembers/v3 --project_id=<project-id> --pool_id=<pool-id> --cli-region=<region> --cli-output=json
hcloud ELB ListHealthMonitors/v3 --project_id=<project-id> --cli-region=<region> --cli-output=json
hcloud VPC ListSubnets --project_id=<project-id> --cli-region=<region> --cli-output=json
hcloud EIP ListPublicips/v3 --project_id=<project-id> --cli-region=<region> --cli-output=json
hcloud NAT ListNatGateways --project_id=<project-id> --cli-region=<region> --cli-output=json
```

If an operation's filter syntax is uncertain, run `hcloud <service> <operation> --help` and quote the supported parameters in the report.

## 6. Choose Traffic Mode

Use local k6 when the current runtime can reach the target:

```bash
k6 run --vus <vus> --duration <duration> <script.js>
```

Use an in-cluster k6 Job when the target is internal or local reachability is not available. This requires approval because it creates resources and sends
traffic. Read `manifest-templates.md`, write a manifest, show it to the user, and only then run:

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> apply -f <approved-k6-manifest.yaml>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> wait --for=condition=complete job/<job-name> -n <client-namespace> --timeout=<timeout>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> logs job/<job-name> -n <client-namespace> --all-containers
```

## 7. Smoke Before Load

Always run a small smoke phase first:

- 1 to 2 VUs.
- 30 to 60 seconds.
- Strict success-rate and latency thresholds.
- No ramp until smoke proves target, Host header, route, and k6 client are correct.

If the smoke phase fails, stop and report the first failing layer. Do not continue to higher traffic.

## 8. Run Approved Test Phases

For each phase, record:

- Phase name and approval.
- Target URL and Host header.
- k6 script checksum or embedded script.
- VUs, duration, RPS cap, stages, thresholds.
- Start and end time.
- k6 summary and errors.
- Workload replica count and Pod readiness before, during, and after.
- HPA status when relevant.

Collect after each phase:

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods -n <namespace> -o wide
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get hpa -n <namespace> -o yaml
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get events -n <namespace> --sort-by=.lastTimestamp
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> top pods -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> logs job/<job-name> -n <client-namespace> --all-containers
```

If a local k6 process is used, save stdout/stderr and the script.

## 9. Elasticity Evaluation

Use at least two phases:

| Phase      | Purpose                                                                                             |
| ---------- | --------------------------------------------------------------------------------------------------- |
| Baseline   | Establish traffic, latency, error rate, Pod metrics, and current replicas.                          |
| Elasticity | Apply an approved HPA or replica change, repeat traffic, and compare scale-up delay and saturation. |

Manual scaling requires an approved command:

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> scale deployment/<workload-name> -n <namespace> --replicas=<replicas>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> rollout status deployment/<workload-name> -n <namespace> --timeout=180s
```

Do not change HPA, nodepool, cluster autoscaler, or resource limits inside this skill unless the user explicitly approves the exact command and rollback.

## 10. Report And Cleanup Guidance

Generate the report using `output-schema.md`. Put summary, bottleneck/root analysis, and next steps first.

Cleanup is also a mutation. Show delete commands separately and run them only after approval:

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> delete job/<job-name> -n <client-namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> delete configmap/<configmap-name> -n <client-namespace>
```

Never delete user workloads, Services, Ingresses, ELBs, EIPs, or namespaces automatically.
