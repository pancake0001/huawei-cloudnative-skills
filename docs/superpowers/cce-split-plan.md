# CCE Module Split Plan

**Source File:** `scripts/huawei_cloud/cce.py` (4545 lines)
**Analysis Date:** 2026-05-28

## Overview

This document maps the functions in `cce.py` to their target modules following the Single Responsibility Principle.

## Function Inventory

**Total Functions Found:** 38

| # | Function Name | Lines | Category |
|---|---------------|-------|----------|
| 1 | `get_cce_addon_detail` | 6-94 | Addon |
| 2 | `list_cce_clusters` | 95-162 | Cluster |
| 3 | `delete_cce_cluster` | 164-249 | Cluster |
| 4 | `list_cce_cluster_nodes` | 251-328 | Node |
| 5 | `get_cce_nodes` | 330-428 | Cluster (per task) |
| 6 | `delete_cce_node` | 430-518 | Node |
| 7 | `list_cce_node_pools` | 520-659 | Nodepool |
| 8 | `get_cce_kubeconfig` | 661-753 | Cluster |
| 9 | `list_cce_addons` | 755-831 | Addon |
| 10 | `resize_node_pool` | 833-991 | Nodepool |
| 11 | `get_kubernetes_pods` | 993-1137 | K8s |
| 12 | `get_kubernetes_namespaces` | 1139-1260 | K8s |
| 13 | `get_kubernetes_deployments` | 1262-1394 | K8s |
| 14 | `scale_cce_workload` | 1396-1602 | K8s (workload) |
| 15 | `resize_cce_workload` | 1604-1861 | K8s (workload) |
| 16 | `delete_cce_workload` | 1864-2049 | K8s (workload) |
| 17 | `get_kubernetes_nodes` | 2051-2217 | K8s |
| 18 | `get_kubernetes_events` | 2219-2370 | K8s |
| 19 | `get_kubernetes_pvcs` | 2372-2517 | K8s |
| 20 | `get_kubernetes_pvs` | 2519-2684 | K8s |
| 21 | `get_kubernetes_services` | 2686-2858 | K8s |
| 22 | `get_kubernetes_ingresses` | 2860-3048 | K8s |
| 23 | `list_cce_configmaps` | 3050-3180 | K8s |
| 24 | `list_cce_secrets` | 3182-3312 | K8s |
| 25 | `list_cce_daemonsets` | 3314-3453 | K8s |
| 26 | `list_cce_statefulsets` | 3455-3606 | K8s |
| 27 | `hibernate_cce_cluster` | 3609-3685 | Cluster |
| 28 | `awake_cce_cluster` | 3688-3764 | Cluster |
| 29 | `list_cce_cronjobs` | 3767-3914 | K8s |
| 30 | `get_pod_logs` | 3917-4094 | K8s |
| 31 | `_node_operation` | 4098-4282 | Shared Helper |
| 32 | `_extract_host` | 4285-4298 | Shared Utility |
| 33 | `cce_node_cordon` | 4301-4318 | Node |
| 34 | `cce_node_uncordon` | 4321-4338 | Node |
| 35 | `cce_node_drain` | 4341-4358 | Node |
| 36 | `cce_node_status` | 4361-4377 | Node |
| 37 | `bind_cce_cluster_eip` | 4380-4472 | Cluster |
| 38 | `unbind_cce_cluster_eip` | 4475-4545 | Cluster |

---

## Module Mapping

### 1. `cce_cluster.py` - Cluster Lifecycle

**Responsibility:** Cluster-level operations (create, delete, hibernate, awake, EIP, kubeconfig)

| Function | Lines | Action |
|----------|-------|--------|
| `list_cce_clusters` | 95-162 | Move |
| `get_cce_nodes` | 330-428 | Move (cluster context node info) |
| `get_cce_kubeconfig` | 661-753 | Move |
| `delete_cce_cluster` | 164-249 | Move |
| `hibernate_cce_cluster` | 3609-3685 | Move |
| `awake_cce_cluster` | 3688-3764 | Move |
| `bind_cce_cluster_eip` | 4380-4472 | Move |
| `unbind_cce_cluster_eip` | 4475-4545 | Move |
| `create_cluster` | N/A | Add later (Task requirement) |

**Total Lines:** ~850 (excluding create_cluster)
**Dependencies:** `create_cce_client`, `get_credentials` from common.py

---

### 2. `cce_nodepool.py` - Node Pool Operations

**Responsibility:** Node pool management (list, resize)

| Function | Lines | Action |
|----------|-------|--------|
| `list_cce_node_pools` | 520-659 | Move |
| `resize_node_pool` | 833-991 | Move |

**Total Lines:** ~280
**Dependencies:** `create_cce_client`, `get_credentials`, `list_cce_node_pools` (internal call in resize)

---

### 3. `cce_node.py` - Node Operations

**Responsibility:** Node management (list, delete, cordon, uncordon, drain, status)

| Function | Lines | Action |
|----------|-------|--------|
| `list_cce_cluster_nodes` | 251-328 | Move (rename to `list_nodes`) |
| `delete_cce_node` | 430-518 | Move |
| `cce_node_cordon` | 4301-4318 | Move (rename to `cordon`) |
| `cce_node_uncordon` | 4321-4338 | Move (rename to `uncordon`) |
| `cce_node_drain` | 4341-4358 | Move (rename to `drain`) |
| `cce_node_status` | 4361-4377 | Move (rename to `status`) |

**Total Lines:** ~470
**Dependencies:** `create_cce_client`, `get_credentials`, `_node_operation` from common.py

---

### 4. `cce_addon.py` - Addon Operations

**Responsibility:** CCE addon/plugin management (list, detail)

| Function | Lines | Action |
|----------|-------|--------|
| `get_cce_addon_detail` | 6-94 | Move (rename to `get_addon_detail`) |
| `list_cce_addons` | 755-831 | Move (rename to `list_addons`) |

**Total Lines:** ~170
**Dependencies:** `create_cce_client`, `get_credentials` from common.py

---

### 5. `cce_k8s.py` - Kubernetes Resource Operations

**Responsibility:** K8s API operations (read/write resources, workload management)

| Function | Lines | Action |
|----------|-------|--------|
| `get_kubernetes_pods` | 993-1137 | Move (rename to `get_pods`) |
| `get_kubernetes_namespaces` | 1139-1260 | Move (rename to `get_namespaces`) |
| `get_kubernetes_deployments` | 1262-1394 | Move (rename to `get_deployments`) |
| `scale_cce_workload` | 1396-1602 | Move (rename to `scale_workload`) |
| `resize_cce_workload` | 1604-1861 | Move (rename to `resize_workload`) |
| `delete_cce_workload` | 1864-2049 | Move (rename to `delete_workload`) |
| `get_kubernetes_nodes` | 2051-2217 | Move (rename to `get_nodes`) |
| `get_kubernetes_events` | 2219-2370 | Move (rename to `get_events`) |
| `get_kubernetes_pvcs` | 2372-2517 | Move (rename to `get_pvcs`) |
| `get_kubernetes_pvs` | 2519-2684 | Move (rename to `get_pvs`) |
| `get_kubernetes_services` | 2686-2858 | Move (rename to `get_services`) |
| `get_kubernetes_ingresses` | 2860-3048 | Move (rename to `get_ingresses`) |
| `list_cce_configmaps` | 3050-3180 | Move |
| `list_cce_secrets` | 3182-3312 | Move |
| `list_cce_daemonsets` | 3314-3453 | Move |
| `list_cce_statefulsets` | 3455-3606 | Move |
| `list_cce_cronjobs` | 3767-3914 | Move |
| `get_pod_logs` | 3917-4094 | Move |

**Total Lines:** ~2800
**Dependencies:** `create_cce_client`, `get_credentials`, K8s client setup pattern

---

### 6. `common.py` - Shared Utilities (Additions)

**Responsibility:** Shared helper functions and utilities

| Function | Lines | Action |
|----------|-------|--------|
| `_node_operation` | 4098-4282 | Move (internal helper) |
| `_extract_host` | 4285-4298 | Move (utility) |
| `_register_cert_file` | existing | Keep |
| `_safe_delete_file` | existing | Keep |

**Dependencies:** Existing common.py utilities

---

## Shared Dependencies Analysis

### From common.py (already exists):
- `get_credentials` - credential handling
- `get_credentials_with_region` - credential with region
- `create_cce_client` - CCE client factory
- `SDK_AVAILABLE`, `IMPORT_ERROR` - SDK availability checks
- `K8S_AVAILABLE`, `K8S_IMPORT_ERROR` - K8s SDK checks
- `k8s_client` - Kubernetes client import

### New additions to common.py:
- `_node_operation` - shared helper for node cordon/uncordon/drain/status
- `_extract_host` - utility for extracting host from kubeconfig

### Import patterns observed:
1. CCE SDK pattern: `from huaweicloudsdkcce.v3 import ...`
2. K8s client pattern: `k8s_client.Configuration`, `k8s_client.CoreV1Api`, etc.
3. Certificate handling: `_register_cert_file`, `_safe_delete_file`

---

## Function Distribution Summary

| Module | Functions | Lines | Percentage |
|--------|-----------|-------|------------|
| `cce_cluster.py` | 9 | ~850 | 19% |
| `cce_nodepool.py` | 2 | ~280 | 6% |
| `cce_node.py` | 6 | ~470 | 10% |
| `cce_addon.py` | 2 | ~170 | 4% |
| `cce_k8s.py` | 18 | ~2800 | 62% |
| `common.py` | 2 (new) | ~200 | 4% |

---

## Rename Mapping (Dispatcher Compatibility)

Functions will be renamed for dispatcher consistency:

| Old Name | New Name | Module |
|----------|----------|--------|
| `list_cce_clusters` | `list_clusters` | cce_cluster |
| `get_cce_nodes` | `get_cluster_nodes` | cce_cluster |
| `get_cce_kubeconfig` | `get_kubeconfig` | cce_cluster |
| `delete_cce_cluster` | `delete_cluster` | cce_cluster |
| `hibernate_cce_cluster` | `hibernate` | cce_cluster |
| `awake_cce_cluster` | `awake` | cce_cluster |
| `bind_cce_cluster_eip` | `bind_eip` | cce_cluster |
| `unbind_cce_cluster_eip` | `unbind_eip` | cce_cluster |
| `list_cce_cluster_nodes` | `list_nodes` | cce_node |
| `delete_cce_node` | `delete_node` | cce_node |
| `cce_node_cordon` | `cordon` | cce_node |
| `cce_node_uncordon` | `uncordon` | cce_node |
| `cce_node_drain` | `drain` | cce_node |
| `cce_node_status` | `status` | cce_node |
| `list_cce_node_pools` | `list_nodepools` | cce_nodepool |
| `resize_node_pool` | `resize_nodepool` | cce_nodepool |
| `get_cce_addon_detail` | `get_addon_detail` | cce_addon |
| `list_cce_addons` | `list_addons` | cce_addon |
| `get_kubernetes_*` | `get_*` | cce_k8s |
| `scale_cce_workload` | `scale_workload` | cce_k8s |
| `resize_cce_workload` | `resize_workload` | cce_k8s |
| `delete_cce_workload` | `delete_workload` | cce_k8s |
| `list_cce_*` | `list_*` | cce_k8s |

---

## K8s Client Setup Pattern (Shared Code)

All K8s functions use identical setup pattern (~50 lines each). This can be extracted:

```python
def _get_k8s_config(region: str, cluster_id: str, ak, sk, project_id) -> Tuple[Configuration, str, str]:
    """Shared K8s client configuration setup."""
    # Get credentials, kubeconfig, write certs, return config + cert paths
```

**Recommendation:** Create shared helper in common.py to reduce code duplication.

---

## Implementation Order

1. **Phase 1:** Move shared helpers to common.py
   - `_node_operation`, `_extract_host`
   - Create `_get_k8s_config` helper

2. **Phase 2:** Create small modules first
   - `cce_addon.py` (170 lines)
   - `cce_nodepool.py` (280 lines)

3. **Phase 3:** Create medium modules
   - `cce_node.py` (470 lines)
   - `cce_cluster.py` (850 lines)

4. **Phase 4:** Create large module
   - `cce_k8s.py` (2800 lines)

5. **Phase 5:** Update dispatcher
   - Update manifest.json with new function mappings
   - Add import statements for new modules

---

## Notes and Concerns

1. **`get_nodes` ambiguity:** Task says `get_nodes` goes to `cce_cluster.py`, but there are two candidates:
   - `get_cce_nodes` (CCE SDK, 330-428) - detailed node info via CCE
   - `get_kubernetes_nodes` (K8s API, 2051-2217) - node status via K8s
   
   **Decision:** Follow task mapping - `get_cce_nodes` to `cce_cluster.py`, `get_kubernetes_nodes` to `cce_k8s.py`

2. **Workload operations:** Functions `scale_cce_workload`, `resize_cce_workload`, `delete_cce_workload` are not in task requirements but logically belong to K8s operations.

3. **Certificate cleanup:** All K8s functions have similar certificate cleanup patterns. Consider centralizing.

4. **Pagination:** Some functions have pagination support (`limit`, `offset`), others don't. Standardize later.

5. **Error handling:** All functions use identical error response format. Keep consistency.

---

## Self-Review Checklist

- [ ] All 38 functions accounted for
- [ ] No orphan functions (all assigned to modules)
- [ ] Shared helpers identified for common.py
- [ ] Import dependencies documented
- [ ] Rename mapping complete
- [ ] Implementation order logical (small → large)
- [ ] Dispatcher update planned