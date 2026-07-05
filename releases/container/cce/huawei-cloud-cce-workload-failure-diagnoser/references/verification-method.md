# Verification Method

Verification must prove that this skill uses CCE `hcloud` CLI plus `kubectl`, and no SDK dispatcher path remains.

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

Do not print AK, SK, token, kubeconfig certificate data, or Authorization headers.

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
- `ShowClusterEndpoints` shows whether the API server has a public endpoint. If `publicEndpoint` is empty and the kubeconfig points to a private IP, run `kubectl` from a VPC/VPN/Direct Connect/Cloud Desktop/sandbox network that can reach the private endpoint.
- No Python SDK process or local dispatcher script is used.

## Step 3: Kubeconfig Acquisition

Run:

```bash
hcloud CCE CreateKubernetesClusterCert --cluster_id=<cluster-id> --project_id=<project-id> --duration=1 --cli-region=<region> --cli-output=json > <kubeconfig-file>
```

Expected:

- Command returns Kubernetes kubeconfig content. KooCLI may emit JSON-formatted kubeconfig; `kubectl` accepts JSON or YAML kubeconfig.
- If KooCLI times out on a recently awakened cluster, retry with explicit values such as `--cli-connect-timeout=20 --cli-read-timeout=90 --cli-retry-count=2`.
- If the kubeconfig server is private while `ShowClusterEndpoints.publicEndpoint` is available and the agent is outside the VPC, use a temporary kubeconfig copy with only the `clusters[].cluster.server` field replaced by the public endpoint.
- File is stored outside the repository or in a temporary ignored location.
- File permissions are restricted where the OS supports it.
- File is deleted after validation if it is not needed.

## Step 4: Kubernetes Read Access

Run:

```bash
kubectl --kubeconfig=<kubeconfig-file> cluster-info
kubectl --kubeconfig=<kubeconfig-file> auth can-i get deployments -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> auth can-i list pods -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> auth can-i get events -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> auth can-i get pods/log -n <namespace>
```

Expected:

- Cluster API is reachable.
- Required read permissions return `yes`, or missing permissions are reported as gaps.

## Step 5: Healthy Or Known Workload Baseline

For a known workload, run only read commands:

```bash
kubectl --kubeconfig=<kubeconfig-file> get deployment <name> -n <namespace> -o yaml
kubectl --kubeconfig=<kubeconfig-file> describe deployment <name> -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> rollout status deployment/<name> -n <namespace> --timeout=30s
kubectl --kubeconfig=<kubeconfig-file> get rs -n <namespace> --selector='<selector>' -o yaml
kubectl --kubeconfig=<kubeconfig-file> get pods -n <namespace> --selector='<selector>' -o wide
kubectl --kubeconfig=<kubeconfig-file> get events -n <namespace> --sort-by=.lastTimestamp
```

Adjust resource names for StatefulSet or DaemonSet.

Expected:

- The diagnosis can explain whether the workload is healthy, stuck, or blocked.
- Events are filtered to workload/ReplicaSet/Pod evidence before citing them.
- No mutating kubectl command is run.

## Step 6: Repository Residual Check

From the skill package directory, run:

```bash
rg -n "scripts/huawei-cloud.py|skill action=exec|huawei_workload|Python SDK dispatcher|huaweicloudsdk|CreateKubernetesClusterCertRequest" . --glob "!*.md"
```

Expected:

- No matches for SDK dispatcher entrypoints, old tool mappings, scripts, or Huawei SDK imports in executable/non-document files.
- Markdown files may mention old SDK terms only as explicit prohibitions or residual-check instructions.
- Matches for plain `hcloud CCE CreateKubernetesClusterCert` are allowed.

## Step 7: Log Review

Review terminal output or saved verification logs:

- Commands used `hcloud CCE ...` and `kubectl --kubeconfig=...`.
- No command begins with `python`, `python3`, `skill action=exec`, or `scripts/huawei-cloud.py`.
- Secrets are absent or redacted.
- Kubeconfig file path is known, secured, and cleaned up if temporary.

## Pass Criteria

The skill passes verification when:

1. `hcloud` can list/show the target CCE cluster.
2. `CreateKubernetesClusterCert` can produce kubeconfig.
3. `kubectl` can read the target namespace or reports explicit RBAC gaps.
4. The package contains no SDK dispatcher scripts, skill profile tool mapping, or `huawei_workload_*` actions.
5. The diagnosis workflow remains read-only.
