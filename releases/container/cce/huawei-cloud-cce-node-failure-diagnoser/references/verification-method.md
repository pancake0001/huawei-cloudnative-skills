# Verification Method

Verification must prove that this skill uses CCE `hcloud` CLI plus `kubectl cce` plugin commands, and no SDK dispatcher path remains.

## Step 1: Tooling Check

```bash
hcloud version
hcloud configure list
kubectl version --client
```

Expected:

- `hcloud` reports a KooCLI version.
- `kubectl` matches the current OS and architecture.
- Credentials are masked or passed as one-off parameters. Secrets are not printed.

## Step 2: CCE Cluster And Node Discovery

```bash
hcloud CCE ListClusters --project_id=<project-id> --detail=true --cli-region=<region> --cli-output=json
hcloud CCE ShowCluster --cluster_id=<cluster-id> --project_id=<project-id> --detail=true --cli-region=<region> --cli-output=json
hcloud CCE ShowClusterEndpoints --cluster_id=<cluster-id> --project_id=<project-id> --cli-region=<region> --cli-output=json
hcloud CCE ListNodes --cluster_id=<cluster-id> --project_id=<project-id> --cli-region=<region> --cli-output=json
```

Expected:

- Target cluster and node can be found.
- Endpoint information explains whether kubectl should use public or private API reachability.
- No Python process or local dispatcher script is used.

## Step 3: kubectl-cce Plugin Access

Run:

```bash
kubectl plugin list
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get ns
```

Expected:

- `kubectl` discovers the plugin as `kubectl-cce`.
- The plugin uses `HUAWEICLOUD_SDK_AK`/`HUAWEICLOUD_SDK_SK` plus `CCE_PROJECT_ID`, temporary `HUAWEICLOUD_SECURITY_TOKEN` when needed, or `HUAWEI_IAM_TOKEN`.
- The plugin starts its short-lived local proxy and reaches the CCE API Gateway endpoint.
- If the default `<cluster-id>.cce.<region>.myhuaweicloud.com` endpoint is not valid, set `CCE_ENDPOINT` or pass `--endpoint`.
- Do not generate, store, or patch kubeconfig files for this skill path.
## Step 4: Kubernetes Read Access

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> cluster-info
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i get nodes
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i list leases -n kube-node-lease
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i list events -A
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i list pods -A
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i get pods/log -A
```

Expected:

- Required read permissions return `yes`, or missing permissions are reported as verification gaps.

## Step 5: Node Evidence Baseline

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get nodes -o wide
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> describe node <node-name>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get lease <node-name> -n kube-node-lease -o yaml
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get events -A --field-selector involvedObject.kind=Node,involvedObject.name=<node-name> --sort-by=.lastTimestamp
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods -A --field-selector spec.nodeName=<node-name> -o wide
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> top node <node-name>
```

Expected:

- Node state, lease, Events, and workload impact can be inspected.
- `kubectl cce ... top` may fail when metrics-server is unavailable; record the gap.
- No mutating kubectl command is run.

## Step 6: Repository Residual Check

From the skill package directory, run:

```bash
rg -n "scripts/huawei-cloud.py|skill action=exec|huawei_node_|Python SDK dispatcher|Huawei Cloud Python SDK|huaweicloudsdk|KubernetesClusterCertRequest|BasicCredentials|Signer\\(" . --glob "!*.md"
```

Expected:

- No matches in executable or non-document files.
- Markdown may mention old terms only as explicit prohibitions or residual-check patterns.

## Pass Criteria

1. hcloud can list/show the target CCE cluster and nodes.
2. `kubectl cce ...` can reach the target cluster through the CCE API Gateway.
3. kubectl can read target node evidence or reports explicit RBAC gaps.
4. The package contains no SDK dispatcher scripts or skill profile tool mapping.
5. The diagnosis workflow remains read-only.
