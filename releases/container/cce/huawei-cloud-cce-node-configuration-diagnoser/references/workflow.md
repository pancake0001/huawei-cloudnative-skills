# Node Configuration Workflow

The collector is deliberately one-node-at-a-time. It must receive an exact Kubernetes `node_name`; do not enumerate nodes and diagnose every node in a
cluster.

1. Resolve and verify `cluster_id` through hcloud.
2. Read the named Kubernetes Node through `kubectl cce` and obtain `spec.providerID`.
3. Create a uniquely named `NodeConfigurationCollection` with `agent.cce.io/node-id=<provider-id>` and `status.phase: Pending`.
4. Poll only the generated CR. `Pending -> Running -> Succeeded` is normal. `Failed`, `Error`, CR disappearance, or timeout is an inconclusive collection,
   not a healthy node conclusion.
5. Analyze only fields returned by the CR. Do not infer component health or resource use when a field is absent.

CCE may automatically delete a completed CR. Preserve the tool response as the diagnostic evidence; do not rely on a completed CR remaining available. Do not
modify or delete prior collection CRs as part of a new diagnosis.
