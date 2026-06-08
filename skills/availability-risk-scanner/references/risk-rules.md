# RiskRules

- Allows automated execution of R1 read-only queries for: Node, Pod, Deployment, StatefulSet, DaemonSet, Service, Ingress, PDB, ReplicaSet, Node Metrics and Report Generation.
- Disable scanner from automatically modifying the number of replicas, PDB, probes, affinity, topology dispersion, request/limit, node pool, master, or plugin configuration.
- Any real remediation must be explicitly authorized by the customer and describe the scope of impact, rollback method, and verification metrics.
- `kube-system` Ordinary workloads are not treated as business risks by default, but core plug-ins such as CoreDNS, nginx-ingress, ingress-nginx need to check anti-affinity and distribution risks.
- When the hosting control plane master is not visible, do not assume that the master is highly available; data gaps must be marked and it is recommended to review the CCE console/API.
- Before rectifying single-copy, stateful services, and gateway services, you must first confirm that the business can run multiple copies, session persistence, storage binding, and traffic entry strategies.
- Before modifying the health check, you must confirm the detection path, port, timeout, initial delay, and failure threshold to avoid batch restarts caused by incorrect probes.
- Node pool capacity, AZ resources, storage AZ binding, taint and tolerance configuration must be confirmed before modifying affinity or topology dispersion.