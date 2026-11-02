# Acceptance Criteria

- The only public action validates a specific region, cluster, and node name.
- It requires explicit confirmation before creating a diagnostic CR.
- It uses a unique CR name and the target node `spec.providerID` label.
- It waits for a terminal collection result and reports evidence-based findings.
- It does not perform node, workload, node pool, or CCE configuration remediation.
