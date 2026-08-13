# Verification Method

Verification must prove that this skill uses CCE `hcloud` CLI plus `kubectl cce` plugin commands, and no SDK dispatcher path remains.

## Step 1: Tooling Check

Run:

```bash
hcloud version
hcloud configure list
kubectl version --client
```

Expected:

- `hcloud` exists and reports KooCLI version. Linux sandboxes should use the Linux KooCLI binary; Windows workstations may use `hcloud.exe`, but the skill workflow should stay platform-neutral.
- Credential profiles are present, with secret values masked.
- `kubectl` client exists and matches the runtime platform. Linux sandboxes should use a Linux `kubectl` binary; Windows workstations should use `kubectl.exe`.

Do not print AK, SK, token, kubectl-cce proxy credentials, or Authorization headers.

## Step 2: CCE Cluster Discovery

Run:

```bash
hcloud CCE ListClusters --project_id=<project-id> --cli-region=<region> --cli-output=json
hcloud CCE ShowCluster --cluster_id=<cluster-id> --project_id=<project-id> --detail=true --cli-region=<region> --cli-output=json
hcloud CCE ShowClusterEndpoints --cluster_id=<cluster-id> --project_id=<project-id> --cli-region=<region> --cli-output=json
```

Expected:

- Target cluster appears in the list.
- `ShowCluster` returns the same cluster ID and expected status.
- `ShowClusterEndpoints` records endpoint context. Kubernetes access uses kubectl-cce through the CCE API Gateway; if the default gateway endpoint is not valid, set `CCE_ENDPOINT` or pass `--endpoint`.
- No Python SDK process or local dispatcher script is used.

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

Run:

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> cluster-info
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i get deployments -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i list pods -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i get events -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i get pods/log -n <namespace>
```

Expected:

- Cluster API is reachable.
- Required read permissions return `yes`, or missing permissions are reported as gaps.

## Step 5: Healthy Or Known Workload Baseline

For a known workload, run only read commands:

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get deployment <name> -n <namespace> -o yaml
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> describe deployment <name> -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> rollout status deployment/<name> -n <namespace> --timeout=30s
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get rs -n <namespace> --selector='<selector>' -o yaml
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods -n <namespace> --selector='<selector>' -o wide
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get events -n <namespace> --sort-by=.lastTimestamp
```

Adjust resource names for StatefulSet or DaemonSet.

Expected:

- The diagnosis can explain whether the workload is healthy, stuck, or blocked.
- Events are filtered to workload/ReplicaSet/Pod evidence before citing them.
- No mutating kubectl command is run.

## Step 6: Repository Residual Check

From the skill package directory, run:

```bash
rg -n "scripts/huawei-cloud.py|skill action=exec|huawei_workload|Python SDK dispatcher|huaweicloudsdk|KubernetesClusterCertRequest" . --glob "!*.md"
```

Expected:

- No matches for SDK dispatcher entrypoints, old tool mappings, scripts, or Huawei SDK imports in executable/non-document files.
- Markdown files may mention old SDK terms only as explicit prohibitions or residual-check instructions.
- Certificate-generation hcloud commands should not remain in the skill workflow.

## Step 7: Log Review

Review terminal output or saved verification logs:

- Commands used `hcloud CCE ...` for discovery and `kubectl cce ...` for Kubernetes evidence.
- No command begins with `python`, `python3`, `skill action=exec`, or `scripts/huawei-cloud.py`.
- Secrets are absent or redacted.
- No kubeconfig file is generated or stored by the skill path.

## Pass Criteria

The skill passes verification when:

1. `hcloud` can list/show the target CCE cluster.
2. `kubectl cce ...` can reach the target cluster through the CCE API Gateway.
3. `kubectl` can read the target namespace or reports explicit RBAC gaps.
4. The package contains no SDK dispatcher scripts, skill profile tool mapping, or `huawei_workload_*` actions.
5. The diagnosis workflow remains read-only.
