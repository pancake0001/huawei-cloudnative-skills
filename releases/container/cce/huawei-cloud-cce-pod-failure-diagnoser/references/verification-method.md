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
- If tools are not in `PATH`, validate the explicit local binary path with the same version commands before using it. A file that exists but fails with a platform error is not usable.

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
kubectl --kubeconfig=<kubeconfig-file> auth can-i get pods -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> auth can-i list pods -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> auth can-i list events -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> auth can-i get pods/log -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> auth can-i get nodes
```

Expected:

- Cluster API is reachable.
- Required read permissions return `yes`, or missing permissions are reported as verification gaps.

## Step 5: Pod Evidence Baseline

For a known Pod, run only read commands:

```bash
kubectl --kubeconfig=<kubeconfig-file> get pods -A -o wide
kubectl --kubeconfig=<kubeconfig-file> get pods -A --field-selector=status.phase!=Running -o wide
kubectl --kubeconfig=<kubeconfig-file> get pods -A -o custom-columns="NAMESPACE:.metadata.namespace,NAME:.metadata.name,READY:.status.containerStatuses[*].ready,RESTARTS:.status.containerStatuses[*].restartCount,PHASE:.status.phase,NODE:.spec.nodeName"
kubectl --kubeconfig=<kubeconfig-file> get pod <pod-name> -n <namespace> -o wide
kubectl --kubeconfig=<kubeconfig-file> get pod <pod-name> -n <namespace> -o yaml
kubectl --kubeconfig=<kubeconfig-file> describe pod <pod-name> -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> get events -n <namespace> --field-selector involvedObject.name=<pod-name> --sort-by=.lastTimestamp
kubectl --kubeconfig=<kubeconfig-file> logs <pod-name> -n <namespace> --all-containers --tail=50
kubectl --kubeconfig=<kubeconfig-file> logs <pod-name> -n <namespace> --all-containers --previous --tail=50
kubectl --kubeconfig=<kubeconfig-file> top pod <pod-name> -n <namespace>
```

Expected:

- Pod status, Events, and logs can be inspected or produce explicit read/RBAC gaps.
- Previous logs may be empty for Pods that have not restarted; that is not a failure.
- `kubectl top` may fail if metrics-server is missing; record it as a metric gap.
- No mutating kubectl command is run.

## Step 6: Selector Or Workload Baseline

If Pod name is unknown, derive the selector from a workload and inspect selected Pods:

```bash
kubectl --kubeconfig=<kubeconfig-file> get deployment <workload-name> -n <namespace> -o yaml
kubectl --kubeconfig=<kubeconfig-file> get pods -n <namespace> --selector='<selector>' -o wide
kubectl --kubeconfig=<kubeconfig-file> get pods -n <namespace> --selector='<selector>' -o yaml
```

Adjust `deployment` to `statefulset` or `daemonset` when needed.

Expected:

- The diagnosis can explain whether matching Pods are healthy, abnormal, missing, or blocked.
- Events are filtered to relevant Pods/owners before being cited.

## Step 7: Repository Residual Check

From the skill package directory, run:

```bash
rg -n "scripts/huawei-cloud.py|skill action=exec|huawei_pod_|Python SDK dispatcher|Huawei Cloud Python SDK|huaweicloudsdk|CreateKubernetesClusterCertRequest|BasicCredentials|Signer\\(" . --glob "!*.md"
```

Expected:

- No matches for SDK dispatcher entrypoints, old tool mappings, scripts, or Huawei SDK imports in executable/non-document files.
- Markdown files may mention old SDK terms only as explicit prohibitions or residual-check instructions.
- Matches for plain `hcloud CCE CreateKubernetesClusterCert` are allowed.

## Step 8: Log Review

Review terminal output or saved verification logs:

- Commands used `hcloud CCE ...` and `kubectl --kubeconfig=...`.
- No command begins with `python`, `python3`, `skill action=exec`, or `scripts/huawei-cloud.py`.
- Secrets are absent or redacted.
- Kubeconfig file path is known, secured, and cleaned up if temporary.

## Pass Criteria

The skill passes verification when:

1. `hcloud` can list/show the target CCE cluster.
2. `CreateKubernetesClusterCert` can produce kubeconfig.
3. `kubectl` can read the target Pod/namespace or reports explicit RBAC gaps.
4. The package contains no SDK dispatcher scripts, skill profile tool mapping, or `huawei_pod_*` actions.
5. The diagnosis workflow remains read-only.
