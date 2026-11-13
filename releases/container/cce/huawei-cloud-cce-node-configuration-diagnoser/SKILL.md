---
name: huawei-cloud-cce-node-configuration-diagnoser
description: Diagnose Huawei Cloud CCE node operating-system and agent configuration by creating a uniquely named NodeConfigurationCollection for one specified node, waiting for CCE collection, and analyzing the returned configuration and health findings. Trigger for node configuration, kubelet/runtime health, dependency, OS resource, network, or time-sync inspection requests; do not use for node remediation.
---

# Huawei Cloud CCE Node Configuration Diagnoser

## Overview

This skill triggers CCE's node configuration collector for one specified node and evaluates the returned `NodeConfigurationCollection`. It detects unhealthy
agent components, configuration consistency findings, dependency check errors, high CPU/memory/disk/conntrack/file-descriptor/PID use, and collection
failures. It does not repair nodes or alter node configuration.

The implementation uses `hcloud` only to validate the target CCE cluster and resolve its project. It uses `kubectl cce` to read the node, create the
diagnostic CR, and poll its result. No Kubernetes Python SDK or direct Kubernetes API client is used.

## Dependencies And Authentication

- `hcloud` (KooCLI) and `kubectl` with the `kubectl-cce` plugin are required. Use `huawei-cloud-kubectl-cce-installer` when either Kubernetes CLI is missing.
- Use explicit `--cli-access-key`, `--cli-secret-key`, and optional `--cli-security-token` when supplied. They take precedence over an hcloud profile and
  environment credentials and are passed to every internal `hcloud` and `kubectl cce` command without printing their values.
- Without explicit credentials, hcloud profile and `HW_ACCESS_KEY`/`HW_SECRET_KEY` are allowed. Region comes from the input/context, then `HW_REGION_NAME`.
- `project_id` is optional. The tool first uses it when supplied, otherwise resolves the project matching the target region through IAM. It passes a resolved
  project ID explicitly to `kubectl cce`.

## Tools

| Tool | Purpose | Risk |
| --- | --- | --- |
| `huawei_diagnose_cce_node_configuration` | Create one unique NodeConfigurationCollection, wait for collection completion, and analyze node configuration evidence | R2 |

## Parameter Reference

| Parameter | Required | Description |
| --- | --- | --- |
| `region` | Yes | Target Huawei Cloud region. |
| `cluster_id` | Yes | CCE cluster UUID or exact unique cluster name. |
| `node_name` | Yes | Exact Kubernetes node name. In CCE this is often the node internal IP. |
| `confirm` | Yes for execution | Set to `true` only after reviewing the R2 preview. It permits creation of the temporary diagnostic CR. |
| `project_id` | No | Target project ID. The tool resolves it through IAM when omitted. |
| `poll_timeout_seconds` | No | Collection wait limit, `30`-`300`; default `120`. |
| `warning_threshold`, `critical_threshold` | No | Percentage thresholds for CPU, memory, disk, conntrack, file descriptor, and PID usage; defaults `80` and `90`. |
| `debug` | No | Include sanitized hcloud/kubectl command trace and bounded output. Never includes credentials. |
| `--cli-access-key`, `--cli-secret-key`, `--cli-security-token` | No | Explicit permanent or temporary credentials. AK/SK are required together; token requires AK/SK. |

### Input Parameter Validation

`region`, `cluster_id`, and `node_name` are required. Before any Kubernetes command, the tool validates a UUID with `hcloud CCE ShowCluster`; a non-UUID is
resolved only by exact, unique `hcloud CCE ListClusters` name match and then verified with `ShowCluster`. Missing, invalid, unmatched, or ambiguous cluster
input stops execution. The tool never broadens to another cluster or selects a node automatically.

## Confirmation And Risk

Creating a `NodeConfigurationCollection` requests configuration collection from the node agent, so it is R2. The tool first returns a preview unless
`confirm=true` is supplied. CCE owns the CR lifecycle and can delete completed CRs automatically; the tool returns its parsed result before that cleanup.
Each run generates a new unique name in the form `ncc-<node>-<random-suffix>`, avoiding name collisions.

## Core Commands

```bash
# Preview the R2 action; no CR is created.
python3 scripts/huawei-cloud.py huawei_diagnose_cce_node_configuration \
  region=<region> cluster_id=<cluster-id-or-name> node_name=<node-name>

# Execute after explicit confirmation.
python3 scripts/huawei-cloud.py huawei_diagnose_cce_node_configuration \
  region=<region> cluster_id=<cluster-id-or-name> node_name=<node-name> \
  confirm=true
```

When a caller supplies explicit credentials, add the three supported CLI credential arguments. Do not place credential values in files, debug output, or
shell history.

## Workflow

1. Validate the target cluster and read the exact target node.
2. Read the node's `spec.providerID` and create a unique cluster-scoped `NodeConfigurationCollection` labelled
   `agent.cce.io/node-id=<provider-id>`, with initial `status.phase: Pending`.
3. Poll only that CR until `Succeeded`, `Failed`, `Error`, or timeout. CCE owns collection state and may change `Pending` to `Running` immediately.
4. Parse the returned agent health, configuration consistency, critical dependencies, resource usage, network settings, and system settings.
5. Return ranked findings and safe next steps. Do not change node configuration, workloads, or CCE resources.

Every tool execution returns the fixed response envelope defined in [Output Schema](references/output-schema.md), including preview, validation failure,
collection failure, timeout, and successful diagnosis. Consumers can rely on the same top-level fields for every outcome.

## Notes

- The CR is cluster-scoped; it is neither a namespace resource nor an `AgentConfiguration` resource.
- Use [Node Kernel Baseline](references/node-kernel-baseline.md) only as a context-aware comparison reference. It does not trigger automatic findings or
  remediation.
- A controller can remove malformed or stale collection CRs. If the CR disappears before completion, report the failure and create a new diagnostic run only
  after user confirmation.
- A `Succeeded` collection can still contain warning or critical findings. In particular, failed dependency checks and component health are evaluated from
  the returned content, not merely the collection phase.
- All internal `kubectl cce` calls include `--cce-insecure-upstream-tls=true` as required for the target environment. This skips upstream TLS certificate
  verification; use it only where the network path and CCE endpoint are trusted.

## References

[Workflow](references/workflow.md) · [Output Schema](references/output-schema.md) · [IAM Policies](references/iam-policies.md) ·
[CLI Installation](references/cli-installation-guide.md) · [Verification](references/verification-method.md) ·
[Acceptance Criteria](references/acceptance-criteria.md) · [Risk Rules](references/risk-rules.md) ·
[Node Kernel Baseline](references/node-kernel-baseline.md)
