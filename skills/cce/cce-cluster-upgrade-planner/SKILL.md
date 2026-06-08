---
name: cce-cluster-upgrade-planner
description: >-
  Use when planning CCE Kubernetes cluster version upgrades, evaluating upgrade path compatibility, addon compatibility, pre-upgrade difference checks, and estimating upgrade window duration to avoid insufficient upgrade windows. Covers version-specific breaking changes, deprecated APIs, 76-item pre-check checklist, in-place upgrade vs migration strategy comparison, and execution preview with two-step confirmation.
  Triggers: CCE cluster upgrade, upgrade evaluation, version compatibility, upgrade window, pre-upgrade check, Kubernetes upgrade, addon upgrade, difference check, upgrade plan, cluster upgrade, version upgrade, upgrade window, compatibility check
tags: [cce, kubernetes, upgrade, compatibility, assessment]
version: 1.0.0
---

# CCE Cluster Upgrade Planner

# # Overview

Plan and assess CCE (Cloud Container Engine) Kubernetes cluster version upgrades using hcloud CLI. Covers upgrade path validation, 76-item pre-check checklist, addon compatibility, version-specific breaking changes, deprecated APIs, upgrade window estimation, and execution preview with two-step confirmation.

**Architecture**: hcloud CLI → CCE OpenAPI → Cluster Info / Upgrade Paths / Upgrade Workflow / Addon Info / Node Pool Info

 Nodes

**Standard workflow**:
```
1. Collect cluster current state (version, nodes, addons, node pools)
2. Query upgrade paths via ListClusterUpgradePaths
3. Run pre-check via ShowClusterUpgradeInfo (or CreateUpgradeWorkFlow)
4. Evaluate addon compatibility for each installed addon
5. Estimate upgrade window based on node count, addon count, batch strategy
6. Generate upgrade plan with specific hcloud CLI commands (execution preview)
7. Provide rollback strategy and post-upgrade verification checklist
```

# # Prerequisites

> **Prerequisite check: hcloud (KooCLI) >= 7.2.2 required**
> Run `hcloud version` to verify, and `hcloud configure list` to check profile exists.

```bash
hcloud version
hcloud configure list
```

# # Security Constraints

## # Dangerous Operation Confirmation Mechanism

> **This skill strictly enforces a two-step confirmation mechanism for upgrade execution preview.**

All upgrade execution previews require explicit user confirmation before any changes are made. The process:

**Step 1: Preview** — Show upgrade commands, target version, affected components, and risk warnings

**Step 2: Confirm & Execute** — Only after user explicitly confirms

### # Operations Requiring Confirmation

| Operation | Risk Level | Description |
|----------|------------|-------------|
| UpgradeCluster | 🔴 Critical | Upgrades Kubernetes control plane, irreversible once started |
| UpgradeNodePool | 🟠 High | Upgrades node pool Kubernetes version, nodes become temporarily unschedulable |
| CreateUpgradeWorkFlow | 🟠 High | Creates upgrade workflow with pre-check, cluster upgrade, and post-check phases |

## # Credential Security

- **Never expose AK/SK values** in conversation, commands, or output
- **Never ask user to input AK/SK directly** in conversation
- **Only use** `hcloud configure list` to check credential status (presence only, not values)
- **Prefer** profile mode or environment variables over explicit AK/SK parameters

# # Command Format Standard

CCE upgrade follows standard hcloud format:

```bash
hcloud CCE <Operation> --param=value --cli-region=<region> --cli-output=json
```

## # Upgrade-specific Parameter Rules1. **Cluster ID required**: all upgrade operations need `--cluster_id`
2. **Target version required**: upgrade operations need `--spec.clusterUpgradeAction.targetVersion=v1.XX`
3. **Addon upgrade uses array format**: `--spec.clusterUpgradeAction.addons.1.addonTemplateName=<name> --spec.clusterUpgradeAction.addons.1.version=<ver>`
4. **Node pool priority uses key-value format**: `--spec.clusterUpgradeAction.nodePoolOrder.key1=value1`
5. **Node selector uses nested format**: `--spec.clusterUpgradeAction.nodeOrder.key1.1.nodeSelector.key=<label-key> --spec.clusterUpgradeAction.nodeOrder.key1.1.nodeSelector.operator=In --spec.clusterUpgradeAction.nodeOrder.key1.1.nodeSelector.value.1=<val>`
6. **Upgrade strategy**: `--spec.clusterUpgradeAction.strategy.type=inPlaceRollingUpdate` (only in-place supported)
7. **Batch size**: `--spec.clusterUpgradeAction.strategy.inPlaceRollingUpdate.userDefinedStep=<1-40>` (default 20, recommended)
8. **Batch scope**: `--spec.clusterUpgradeAction.strategy.inPlaceRollingUpdate.scope=Cluster` or `NodePool`

> **⚠️ Critical**: Before constructing any upgrade command, always run `hcloud CCE <Operation> --help` to verify exact parameter names. CCE upgrade APIs have hundreds of parameters; the help output is the authoritative source.

# # Scenario Routing

| User Intent | Reference Document |
|---|---|
| Full upgrade assessment (7-step workflow) | [references/upgrade-workflow.md](references/upgrade-workflow.md) |
| Pre-upgrade checklist (76 items) | [references/pre-upgrade-checklist.md](references/pre-upgrade-checklist.md) |
| Addon compatibility matrix & upgrade order | [references/addon-compatibility.md](references/addon-compatibility.md) |
| K8s version upgrade path rules | [references/k8s-version-matrix.md](references/k8s-version-matrix.md) |
| Upgrade window time estimation | [references/upgrade-window-estimation.md](references/upgrade-window-estimation.md) |
| Version-specific breaking changes | [references/pre-upgrade-checklist.md](references/pre-upgrade-checklist.md) |
| Deprecated API migration | [references/pre-upgrade-checklist.md](references/pre-upgrade-checklist.md) |
| Risk constraints & rollback | [references/risk-rules.md](references/risk-rules.md) |
| Output schema | [references/output-schema.md](references/output-schema.md) |

# # Core Commands

## # Step 1: Collect Cluster Current State

```bash
# Get cluster details (version, node count, addons)
hcloud CCE ShowCluster --cluster_id=<cluster-id> --detail=true --cli-region=<region> --cli-output=json

# List installed addons
hcloud CCE ListAddonInstances --cluster_id=<cluster-id> --cli-region=<region> --cli-output=json

# List node pools
hcloud CCE ListNodePools --cluster_id=<cluster-id> --cli-region=<region> --cli-output=json

# List nodes
hcloud CCE ListNodes --cluster_id=<cluster-id> --cli-region=<region> --cli-output=json
```

## # Step 2: Query Upgrade Paths

```bash
# Get all available upgrade paths for the cluster
hcloud CCE ListClusterUpgradePaths --cli-region=<region> --cli-output=json
```

## # Step 3: Pre-Upgrade Check

```bash
# Get upgrade info (includes pre-check status)
hcloud CCE ShowClusterUpgradeInfo --cluster_id=<cluster-id> --cli-region=<region> --cli-output=json

# Create upgrade workflow (triggers pre-check automatically)
hcloud CCE CreateUpgradeWorkFlow \
  --cluster_id=<cluster-id> \
  --apiVersion=v3 \
  --kind=WorkFlowTask \
  --spec.targetVersion=<target-version> \
  --spec.clusterVersion=<current-version> \
  --cli-region=<region> \
  --cli-output=json
```

## # Step 4: Addon Compatibility Check

```bash
# Get addon details (check version compatibility)
hcloud CCE ListAddonInstances --cluster_id=<cluster-id> --cli-region=<region> --cli-output=json

# List addon template versions (check available versions for target K8s)
hcloud CCE ListAddonTemplates --cluster_id=<cluster-id> --addon_template_name=<addon-name> --cli-region=<region> --cli-output=json
```

## # Step 5: Upgrade Execution Preview

```bash
# Preview cluster upgrade (without confirm=true, no execution)
hcloud CCE UpgradeCluster \
  --cluster_id=<cluster-id> \
  --metadata.apiVersion=v3 \
  --metadata.kind=UpgradeTask \
  --spec.clusterUpgradeAction.targetVersion=<target-version> \
  --spec.clusterUpgradeAction.strategy.type=inPlaceRollingUpdate \
  --spec.clusterUpgradeAction.strategy.inPlaceRollingUpdate.userDefinedStep=20 \
  --spec.clusterUpgradeAction.strategy.inPlaceRollingUpdate.scope=Cluster \
  --cli-region=<region> \
  --cli-output=json
```

**With addons** (specify addon upgrade during cluster upgrade):
```bash
hcloud CCE UpgradeCluster \
  --cluster_id=<cluster-id> \
  --metadata.apiVersion=v3 \
  --metadata.kind=UpgradeTask \
  --spec.clusterUpgradeAction.targetVersion=<target-version> \
  --spec.clusterUpgradeAction.strategy.type=inPlaceRollingUpdate \
  --spec.clusterUpgradeAction.strategy.inPlaceRollingUpdate.userDefinedStep=20 \
  --spec.clusterUpgradeAction.addons.1.addonTemplateName=coredns \
  --spec.clusterUpgradeAction.addons.1.operation=patch \
  --spec.clusterUpgradeAction.addons.1.version=<target-addon-version> \
  --cli-region=<region> \
  --cli-output=json
```

**With node pool priority** (control upgrade order):
```bash
hcloud CCE UpgradeCluster \
  --cluster_id=<cluster-id> \
  --metadata.apiVersion=v3 \
  --metadata.kind=UpgradeTask \
  --spec.clusterUpgradeAction.targetVersion=<target-version> \
  --spec.clusterUpgradeAction.nodePoolOrder.<nodepool-id>=<priority> \
  --cli-region=<region> \
  --cli-output=json
```

## # Step 6: Monitor Upgrade Progress

```bash
# Check upgrade workflow status
hcloud CCE ShowUpgradeWorkFlow \
  --cluster_id=<cluster-id> \
  --upgrade_workflow_id=<workflow-id> \
  --cli-region=<region> \
  --cli-output=json

# List upgrade tasks
hcloud CCE ListUpgradeClusterTasks --cluster_id=<cluster-id> --cli-region=<region> --cli-output=json

# Pause upgrade (if issues found)
hcloud CCE PauseUpgradeClusterTask --cluster_id=<cluster-id> --cli-region=<region> --cli-output=json

# Continue paused upgrade
hcloud CCE ContinueUpgradeClusterTask --cluster_id=<cluster-id> --cli-region=<region> --cli-output=json

# Retry failed upgrade
hcloud CCE RetryUpgradeClusterTask --cluster_id=<cluster-id> --cli-region=<region> --cli-output=json
```

## # Step 7: Cancel Upgrade Workflow

```bash
# Cancel upgrade workflow (status must not be Running/Success/Cancel)
hcloud CCE UpgradeWorkFlowUpdate \
  --cluster_id=<cluster-id> \
  --upgrade_workflow_id=<workflow-id> \
  --status.phase=Cancel \
  --cli-region=<region> \
  --cli-output=json
```

# # Upgrade Window Estimation Formula

See [references/upgrade-window-estimation.md](references/upgrade-window-estimation.md) for detailed formula and examples.

**Quick estimation**:

```
T_total = T_control_plane + T_node_batch + T_addon + T_verify + T_buffer

T_control_plane = 10-30 minutes
T_node_batch = N_nodes / batch_size * (5-15 min/node)
T_addon = count(addons) * (5-15 min/addon)
T_verify = 30 minutes
T_buffer = 20% * (T_control_plane + T_node_batch + T_addon)
```

**Example**: 3-node-pool cluster (10 nodes, 5 addons) upgrading v1.23→v1.25:
- Control plane: 15 min
- Node batches: 10/4 = 3 batches (1+4+5 nodes), ~9 min each = 9 min total (first batch 1 node at 5 min, second 4 nodes at 8 min, third 5 nodes at 10 min)
- Addon upgrade: 5 * 10 min = 50 min
- Verification: 30 min
- Buffer (20%): ~19 min
- **Total: ~123 min (2h 3min)**

# # Upgrade Methods

| Method | Advantages | Constraints | Recommended |
|--------|------------|------------|------------|
| **In-place upgrade** | Business pods not interrupted during control plane upgrade; nodes upgraded in batches; addons auto-upgraded | Nodes temporarily unschedulable during upgrade; Docker→Containerd runtime switch needed for v1.27+ | Most scenarios (default) |
| **Migration** | Clean slate; no compatibility risk accumulation; skip multiple intermediate upgrades | Full workload redeployment; requires double resources; longer downtime | Cross-version jumps (e.g. v1.15→v1.28); incompatible runtime |

# # Key Constraints

- **No skip-version upgrades**: must follow upgrade path step by step (e.g., v1.21→v1.23→v1.25→v1.27→v1.28)
- **Patch version first**: upgrade to latest patch before major version upgrade
- **Control plane before nodes**: upgrade control plane first, then node pools
- **Addons after cluster**: upgrade addons after cluster reaches target version
- **v1.28+ control node IP change**: upgrading to v1.28+ creates new control nodes, IP addresses change
- **Autoscaling paused**: during control plane upgrade, autoscaling is paused; resumes after control plane done, but shrink waits until full completion

# # Best Practices

1. **Always run pre-check first** — use CreateUpgradeWorkFlow or ShowClusterUpgradeInfo to validate readiness
2. **Upgrade patch version first** — ensure current patch is latest before major version upgrade
3. **Business low-traffic window** — schedule upgrades during low-traffic periods
4. **Keep ≥2 nodes** per node pool for redundancy during upgrade
5. **Monitor upgrade progress** — check ShowUpgradeWorkFlow status after each phase
6. **Verify after each phase** — run post-upgrade verification after control plane and node upgrades
7. **Rollback plan** — use backup data and PauseUpgradeClusterTask if issues arise

# # References

| Document | Description |
|----------|-------------|
| [upgrade-workflow.md](references/upgrade-workflow.md) | Full 7-step upgrade workflow detail |
| [pre-upgrade-checklist.md](references/pre-upgrade-checklist.md) | 76-item pre-check checklist and version-specific breaking changes |
| [addon-compatibility.md](references/addon-compatibility.md) | Addon compatibility matrix, DaemonSet plugins, upgrade order |
| [k8s-version-matrix.md](references/k8s-version-matrix.md) | Official CCE upgrade path table and patch version rules |
| [upgrade-window-estimation.md](references/upgrade-window-estimation.md) | Upgrade window estimation formula, batch strategy, examples |
| [risk-rules.md](references/risk-rules.md) | Risk constraints, rollback strategies, guardrails |
| [output-schema.md](references/output-schema.md) | Assessment report and execution preview JSON schema |