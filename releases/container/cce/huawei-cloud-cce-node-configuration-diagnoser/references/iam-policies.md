# IAM And RBAC Requirements

The caller needs IAM permission to read CCE clusters and query IAM projects, plus Kubernetes RBAC permission to get Nodes and create/get the
`nodeconfigurationcollections.node.cce.io` resource. The CCE node agent must be authorized and healthy enough to write collection results.

Use least privilege and never expose permanent or temporary credential values.
