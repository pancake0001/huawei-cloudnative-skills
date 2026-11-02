# Risk Rules

- Creating a diagnostic `NodeConfigurationCollection` is R2 because it asks a node agent to collect configuration. Show the preview and require
  `confirm=true` before creation.
- Do not create a CR without an exact node name and the node's own `spec.providerID`.
- Do not mutate Nodes, Pods, node pools, CCE configuration, or previous diagnostic CRs.
- Findings are evidence and recommendations only. Remediation requires the appropriate skill and explicit confirmation.
