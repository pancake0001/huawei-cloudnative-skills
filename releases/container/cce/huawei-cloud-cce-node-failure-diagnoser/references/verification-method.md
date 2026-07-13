# Verification Method

Verification must prove that this skill uses CCE `hcloud` CLI plus `kubectl`, and no SDK dispatcher path remains.

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

## Step 3: Kubeconfig Acquisition

```bash
hcloud CCE CreateKubernetesClusterCert --cluster_id=<cluster-id> --project_id=<project-id> --duration=1 --cli-region=<region> --cli-output=json > <kubeconfig-file>
```

Expected:

- Kubeconfig content is produced and stored outside the repository.
- The file is deleted after validation if it is temporary.

## Step 4: Kubernetes Read Access

```bash
kubectl --kubeconfig=<kubeconfig-file> cluster-info
kubectl --kubeconfig=<kubeconfig-file> auth can-i get nodes
kubectl --kubeconfig=<kubeconfig-file> auth can-i list leases -n kube-node-lease
kubectl --kubeconfig=<kubeconfig-file> auth can-i list events -A
kubectl --kubeconfig=<kubeconfig-file> auth can-i list pods -A
kubectl --kubeconfig=<kubeconfig-file> auth can-i get pods/log -A
```

Expected:

- Required read permissions return `yes`, or missing permissions are reported as verification gaps.

## Step 5: Node Evidence Baseline

```bash
kubectl --kubeconfig=<kubeconfig-file> get nodes -o wide
kubectl --kubeconfig=<kubeconfig-file> describe node <node-name>
kubectl --kubeconfig=<kubeconfig-file> get lease <node-name> -n kube-node-lease -o yaml
kubectl --kubeconfig=<kubeconfig-file> get events -A --field-selector involvedObject.kind=Node,involvedObject.name=<node-name> --sort-by=.lastTimestamp
kubectl --kubeconfig=<kubeconfig-file> get pods -A --field-selector spec.nodeName=<node-name> -o wide
kubectl --kubeconfig=<kubeconfig-file> top node <node-name>
```

Expected:

- Node state, lease, Events, and workload impact can be inspected.
- `kubectl top` may fail when metrics-server is unavailable; record the gap.
- No mutating kubectl command is run.

## Step 6: Repository Residual Check

From the skill package directory, run:

```bash
rg -n "scripts/huawei-cloud.py|skill action=exec|huawei_node_|Python SDK dispatcher|Huawei Cloud Python SDK|huaweicloudsdk|CreateKubernetesClusterCertRequest|BasicCredentials|Signer\\(" . --glob "!*.md"
```

Expected:

- No matches in executable or non-document files.
- Markdown may mention old terms only as explicit prohibitions or residual-check patterns.

## Pass Criteria

1. hcloud can list/show the target CCE cluster and nodes.
2. hcloud can create a short-lived kubeconfig.
3. kubectl can read target node evidence or reports explicit RBAC gaps.
4. The package contains no SDK dispatcher scripts or skill profile tool mapping.
5. The diagnosis workflow remains read-only.
