# Workflow

1. Scope: confirm region, project_id, cluster_id, namespace, target_name/service_name/workload_name, label_selector, and failure symptom.
2. Read `references/kubectl-cce.md`, verify `hcloud`, `kubectl`, and `kubectl-cce`, and resolve cluster metadata with hcloud.
3. Snapshot: collect Deployments, StatefulSets, DaemonSets, ReplicaSets, Pods, Services, Ingresses, Endpoints, EndpointSlices, Nodes, and related Events through `kubectl cce`.
4. Target matching: prefer explicit label_selector; otherwise match target Pods by
   Service selector, ownerReference, workload prefix, Pod name, or stable labels.
   Follow Pod -> ReplicaSet -> Deployment and equivalent StatefulSet/DaemonSet chains.
5. Upstream mapping: find Services whose selectors match target Pod labels; flag
   selector mismatches and Services with zero ready endpoints. Treat selectorless and
   ExternalName Services as special cases and inspect type and associated endpoints.
6. Entrypoint mapping: find Ingress rules/default backends that point to the matched Services; include host/path/class/backend details when present.
7. Node distribution: map target and endpoint Pods to Nodes; flag single-node concentration, NotReady/pressure nodes, and zone concentration.
8. Propagation paths: model external traffic as Ingress -> Service -> EndpointSlice/Endpoints -> Pods -> Nodes and internal traffic as Service DNS -> EndpointSlice/Endpoints -> Pods -> Nodes.
9. Impact scoring: combine Pod readiness, Service/Ingress exposure, endpoint availability,
   node concentration, and corroborating alarms, logs, metrics, Events, or user-visible
   symptoms. Label static-only paths as possible impact.
10. Handoff: if root cause is needed, use root-cause/workload/pod/node/network/change diagnosers; if remediation is needed, hand off to auto-remediation runner after confirmation.
