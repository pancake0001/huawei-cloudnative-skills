# Workflow

# # 1. Collection range

Prefer using `huawei_scan_cce_availability_risk`. Commonly used parameters:

- `region`, `cluster_id`: required.
- `exclude_namespaces`: default `kube-system`; core plugins will still be recognized individually.
- `gateway_keywords`: default `nginx,gateway,ingress,proxy,kong,apisix,traefik`.
- `metrics_hours`: Default 24, used for master/node CPU and memory trends.
- `output_dir`: Output `availability-risk-summary.json` and `availability-risk-report.md`.

# # 2. Control plane and node risks

Check items:

- It can be seen whether the number of master/control-plane nodes is less than 3.
- It is visible whether the master spans AZ.
- Whether the master CPU/memory average is too high.
- Whether the Ready nodes are concentrated in a single AZ, or the proportion of a certain AZ is too high.
- Whether the node pool/node AZ distribution matches the business HA target.

If the CCE hosting control plane does not expose the master node, data gaps must be marked in the report and do not assume that the master must be highly available.

# # 3. Workload risk

Check Deployment, StatefulSet, DaemonSet:

- Single copy: The number of business or gateway workload copies is less than 2.
- PDB missing: The multi-copy business or gateway workload does not match the PodDisruptionBudget.
- Pod distribution: Multiple replicas are concentrated on one node, or in one AZ in a multi-AZ cluster.
- Health check: readinessProbe or livenessProbe missing.
- Affinity: Hard binding to a single AZ, single node, a certain node pool, or lack of anti-affinity/topological dispersion.
- Core plug-ins: CoreDNS, nginx-ingress, ingress-nginx whether multi-copy anti-affinity or topological dispersion.
- Gateway applications: whether nginx, gateway, ingress, proxy, kong, apisix, traefik, etc. are deployed in a balanced manner, configured with PDB and health check.

# # 4. Resource overallocation

Check request/limit:

- request not configured: Marked as medium risk because scheduling, HPA, evictions, and capacity estimates are distorted.
- The CPU limit/request ratio is greater than the default 4: Marked as low risk, need to confirm whether it is an intentional burst.
- Memory limit/request ratio is greater than the default 2: Marked as medium risk, OOM and bin-packing risks need to be evaluated first.
- Summarize the proportion of cluster request and limit in allocatable to discover overall overprovisioning or capacity artifacts.

# # 5. Output and rectification

Output order:

1. Overall risk level and issue count.
2. Summary of control plane, node AZ, Pod AZ, and resource overprovisioning.
3. Top list of risk issues.
4. Special issues with gateway and core plug-ins.
5. Data gaps.
6. Make rectification suggestions and implement plans after authorization.

Corrections must be explicitly authorized by the customer before generating or applying PDBs, probes, anti-affinity, topology dispersion, scaling, or resource request/limit adjustments.