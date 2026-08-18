# Verification Method

Verification must prove that this skill uses `hcloud` CLI plus `kubectl cce` plugin commands, and no SDK dispatcher path remains.

## Step 1: Tooling Check

```bash
hcloud version
hcloud configure list
kubectl version --client
```

Expected:

- `hcloud` reports a KooCLI version.
- `kubectl` matches the current OS and architecture.
- Secrets are not printed.

## Step 2: CCE Cluster Discovery

```bash
hcloud CCE ListClusters --project_id=<project-id> --detail=true --cli-region=<region> --cli-output=json
hcloud CCE ShowCluster --cluster_id=<cluster-id> --project_id=<project-id> --detail=true --cli-region=<region> --cli-output=json
hcloud CCE ShowClusterEndpoints --cluster_id=<cluster-id> --project_id=<project-id> --cli-region=<region> --cli-output=json
```

Expected:

- Target cluster appears and endpoint reachability is understood.
- No Python process or local dispatcher script is used.

## Step 3: kubectl-cce Plugin Access

Run:

```bash
kubectl plugin list
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get ns
```

Expected:

- `kubectl` discovers the plugin as `kubectl-cce`.
- The plugin uses `HUAWEICLOUD_SDK_AK`/`HUAWEICLOUD_SDK_SK` plus `CCE_PROJECT_ID` and temporary `HUAWEICLOUD_SECURITY_TOKEN` when needed.
- The plugin starts its short-lived local proxy and reaches the CCE API Gateway endpoint.
- If the default `<cluster-id>.cce.<region>.myhuaweicloud.com` endpoint is not valid, set `CCE_ENDPOINT` or pass `--endpoint`.
- Do not generate, store, or patch kubeconfig files for this skill path.

## Step 4: Kubernetes Network Read Access

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> cluster-info
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i list services -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i list endpoints -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i list endpointslices.discovery.k8s.io -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i list ingresses.networking.k8s.io -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i list networkpolicies.networking.k8s.io -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i list pods -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i list events -n <namespace>
```

Expected:

- Required read permissions return `yes`, or missing permissions are reported as verification gaps.

## Step 5: Network Evidence Baseline

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get nodes -o wide
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get svc,endpoints,endpointslice,ingress,networkpolicy -n <namespace> -o wide
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods -n <namespace> -o wide
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get events -n <namespace> --sort-by=.lastTimestamp
```

Expected:

- Network objects can be inspected or explicit RBAC gaps are recorded.
- No mutating kubectl command is run.

## Step 6: Optional Cloud Network Read Checks

Use only when cloud-side north-south evidence is needed:

```bash
hcloud ELB ListLoadBalancers/v3 --project_id=<project-id> --cli-region=<region> --cli-output=json
hcloud ELB ListListeners/v3 --project_id=<project-id> --cli-region=<region> --cli-output=json
hcloud VPC ListSecurityGroups/v3 --project_id=<project-id> --cli-region=<region> --cli-output=json
hcloud VPC ListSecurityGroupRules/v3 --project_id=<project-id> --cli-region=<region> --cli-output=json
hcloud EIP ListPublicips/v3 --project_id=<project-id> --cli-region=<region> --cli-output=json
hcloud NAT ListNatGateways --project_id=<project-id> --cli-region=<region> --cli-output=json
```

Expected:

- Only list/show style operations are used.
- Parameter filters are confirmed with `--help` when needed.

## Step 7: Repository Residual Check

From the skill package directory, run:

```bash
rg -n "huawei-cloud[.]py|skill action=ex[e]c|huawei[-_]network|Python SDK dispatcher|Huawei Cloud Python SDK|huaweicloudsdk|KubernetesClusterCertRequest|BasicCredentials|Signer\\(" . --glob "!*.md"
```

Expected:

- No matches in executable or non-document files.
- Markdown may mention old terms only as explicit prohibitions or residual-check patterns.

## Pass Criteria

1. hcloud can list/show the target CCE cluster.
2. `kubectl cce ...` can reach the target cluster through the CCE API Gateway.
3. kubectl can read target namespace network objects or reports explicit RBAC gaps.
4. Optional cloud network evidence uses hcloud read-only list/show commands.
5. The package contains no SDK dispatcher scripts or skill profile tool mapping.
6. The workflow remains read-only.
