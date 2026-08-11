# CCE Pressure-Test Verification Method

Use this checklist to verify that the skill is really using hcloud CLI and kubectl instead of the old SDK dispatcher.

## Repository Verification

From the repository root:

```bash
rg --files releases/container/cce/huawei-cloud-cce-pressure-test
rg --files releases/container/cce/huawei-cloud-cce-pressure-test | rg "scripts/|scripts\\|skill-profile\\.yaml$|\\.py$"
rg -n "huaweicloudsdk|BasicCredentials|new_global_credentials|huawei_.*pressure" releases/container/cce/huawei-cloud-cce-pressure-test --glob "!*.md"
```

Expected result:

- The file-list search finds no `scripts/`, `.py`, or `skill-profile.yaml` entries.
- The non-Markdown content search finds no SDK imports or old dispatcher actions.
- Skill files and references describe hcloud CCE, kubectl, and k6.

If a broad Markdown search finds phrases such as "Python SDK dispatcher" or `scripts/huawei-cloud.py`, those should appear only as explicit prohibition text, not as an execution path.

## Tool Verification

```bash
hcloud version
hcloud configure list
kubectl version --client
k6 version
```

If k6 is not installed locally, record it and use an approved in-cluster Job only when the user accepts the manifest and image source.

Keep examples as `hcloud` and `kubectl`. Local debug notes may contain absolute paths, but the skill itself should stay platform-neutral.

## CCE CLI Verification

```bash
hcloud CCE ListClusters --project_id=<project-id> --cli-region=<region> --cli-output=json
hcloud CCE ShowCluster --cluster_id=<cluster-id> --project_id=<project-id> --detail=true --cli-region=<region> --cli-output=json
hcloud CCE ShowClusterEndpoints --cluster_id=<cluster-id> --project_id=<project-id> --cli-region=<region> --cli-output=json
hcloud CCE CreateKubernetesClusterCert --cluster_id=<cluster-id> --project_id=<project-id> --duration=1 --cli-region=<region> --cli-output=json > <kubeconfig-file>
```

The kubeconfig may be JSON or YAML. `kubectl` accepts both. Store it outside the repository and remove it when no longer needed.

If the kubeconfig server points to a private endpoint and the current runtime cannot reach it, report the network placement issue rather than switching to SDK.

## Kubernetes Access Verification

```bash
kubectl --kubeconfig=<kubeconfig-file> cluster-info
kubectl --kubeconfig=<kubeconfig-file> auth can-i list pods -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> auth can-i list events -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> auth can-i get pods/log -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> get deploy,sts,ds,svc,endpoints,endpointslice,ingress,hpa,pdb -n <namespace> -o wide
kubectl --kubeconfig=<kubeconfig-file> get pods -n <namespace> -o wide
```

For metrics:

```bash
kubectl --kubeconfig=<kubeconfig-file> top pods -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> top nodes
```

If metrics are unavailable, record a gap.

## Traffic Verification

Before a large test:

1. Run a smoke phase with 1 to 2 VUs for 30 to 60 seconds.
2. Confirm target URL, Host header, route, and success rate.
3. Confirm no unexpected Pod restarts, NotReady Pods, or critical Events appeared.
4. Only then run the approved baseline or ramp phase.

For in-cluster Job mode:

```bash
kubectl --kubeconfig=<kubeconfig-file> get job,pod -n <client-namespace> -o wide
kubectl --kubeconfig=<kubeconfig-file> describe pod -n <client-namespace> -l job-name=<job-name>
kubectl --kubeconfig=<kubeconfig-file> logs job/<job-name> -n <client-namespace> --all-containers
```

Do not continue if the k6 Job cannot pull its image, cannot resolve the target, or exits before producing a k6 summary.

## Report Verification

The final report should prove:

- The CLI path used hcloud CCE and kubectl.
- The test target, traffic limits, and approvals are recorded.
- Summary, root/bottleneck analysis, and next steps are at the top.
- k6 results are tied to Kubernetes and optional ELB/VPC evidence.
- Mutations and traffic generation are explicitly listed as approved and executed, or marked as not run.
- Data gaps are explicit and do not inflate confidence.
