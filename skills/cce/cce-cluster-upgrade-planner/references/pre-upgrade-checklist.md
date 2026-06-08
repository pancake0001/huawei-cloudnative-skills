# Pre-Upgrade Checklist (76 Items)

Source: [Check items before upgrading](https://support.huaweicloud.com/usermanual-cce/cce_10_0549.html)

CCE automatically runs these 76 pre-check items before allowing upgrade. If any item fails, upgrade is blocked until fixed.

# # Checklist Categories

## # Node Health (Items 1, 21, 22, 25, 41, 44, 51, 52)

| # | Check Item | Description | Fix |
|---|------------|-------------|-----|
| 1 | Node limit check | Node availability, OS compatibility, unexpected node pool labels, K8s node name consistency with ECS | Fix node state, remove unexpected labels |
| 21 | Node Ready check | All cluster nodes must be Ready | Drain/fix NotReady nodes before upgrade |
| 22 | Node journald check | journald service must be running normally | Restart journald: `systemctl restart systemd-journald` |
| 25 | Check node mount points | No inaccessible mount points on nodes | Remove stale mount points |
| 41 | Node sock file mounting check | Pods mounting docker/containerd.sock directly will break during runtime restart | Remove sock mounts from Pod specs, or accept Pod restart |
| 44 | Node paas user login permission check | paas user must have login permission | Restore paas user permissions |
| 51 | Node command line check | Upgrade-required commands must exist on node | Ensure standard system tools available |
| 52 | Node swap area check | Swap must be disabled on nodes | Disable swap: `swapoff -a` |

## # Node Resources (Items 11, 12, 16, 19, 49, 62, 67, 69)

| # | Check Item | Description | Fix |
|---|------------|-------------|-----|
| 11 | Node CPU usage check | Node CPU usage must be < 90% | Reduce workload or add nodes |
| 12 | Node disk check | Key data disk usage meets requirements; /tmp has ≥500MB free | Clean disk space, remove unused images |
| 16 | Node memory check | Node memory usage must be < 90% | Reduce workload or add nodes |
| 19 | Node CPU number check | Control node CPU cores must be > 2 | Upgrade control node flavor |
| 49 | Node Sudo check | sudo command and related files must be normal | Fix sudo configuration |
| 62 | Check the number of cluster images | Node image count should not exceed 1000 (Docker slow start risk) | Clean unused images: `docker image prune` |
| 67 | Check the number of node image layers | Image layers should not exceed 5000 | Clean unused images |
| 69 | Check the number of rotating certificate files | Certificate files on node should not exceed 1000 (slow upgrade risk) | Remove unnecessary certificates |

## # Node Configuration (Items 15, 17, 34, 35, 36, 37, 39, 40, 50)

| # | Check Item | Description | Fix |
|---|------------|-------------|-----|
| 15 | Node Kubelet check | kubelet service must be running normally | Restart kubelet if needed |
| 17 | Node clock synchronization check | ntpd or chronyd must be running normally | Install/configure chronyd |
| 34 | Node NetworkManager check | NetworkManager must be running normally | Restart NetworkManager |
| 35 | Node ID file check | Node ID file content must match expected format | Fix ID file |
| 36 | Node configuration consistency check (v1.19+) | K8s component config files should not be manually modified (v1.19+ upgrade) | Use CCE config management instead of direct file edits |
| 37 | Node configuration file check | Key component config files must exist | Restore missing config files |
| 39 | Node key directory file permissions check | Root directory permissions must be correct | Fix permissions: `chmod 755 /` |
| 40 | Node key command check | Upgrade-required commands must execute normally | Ensure standard system commands work |
| 50 | Node system parameter check | Node sysctl parameters must match expected values | Reset sysctl to CCE defaults |

## # Node Network & DNS (Items 13, 14)

| # | Check Item | Description | Fix |
|---|------------|-------------|-----|
| 13 | Node DNS check | Node DNS must resolve OBS addresses | Fix DNS configuration |
| 14 | Node OBS access check | Node must access OBS (upgrade package storage) | Fix network/firewall rules |

## # Upgrade Control (Items 2, 46, 68)

| # | Check Item | Description | Fix |
|---|------------|-------------|-----|
| 2 | Upgrade control check | Cluster must not be under upgrade control | Wait for current control period to end |
| 46 | Historical upgrade record check | Original cluster version must meet upgrade path conditions | Follow correct upgrade path sequence |
| 68 | Cluster rolling upgrade condition check | Cluster must satisfy rolling upgrade conditions | Fix blocking conditions |

## # Addon & Plugin (Items 3, 27, 28, 47, 48, 53, 54, 63)| # | Check Item | Description | Fix |
|---|------------|-------------|-----|
| 3 | Addon Check | Addon status must be normal; addon must support target K8s version | Fix addon status; upgrade incompatible addons |
| 27 | Everest Addon Version Restriction Check | Everest plugin version compatibility | Upgrade Everest to compatible version |
| 28 | cce-hpa-controller Addon Restriction Check | HPA controller target version compatibility | Upgrade HPA controller |
| 47 | CCE AI Suite (NVIDIA GPU) Addon Check | GPU plugin may affect new GPU node driver installation | Verify GPU plugin compatibility |
| 48 | Enhanced CPU Management Policy Check | Source and target version must support enhanced CPU management | Disable if target version doesn't support |
| 53 | NGINX Ingress Controller Addon Upgrade Check | Ingress controller upgrade path compatibility | Upgrade Ingress controller version |
| 54 | Cloud Native Monitoring Addon Upgrade Check | Prometheus plugin 3.9.0 migration: grafana switch must be enabled | Enable grafana switch before upgrade |
| 63 | OpenKruise Addon Compatibility Check | OpenKruise plugin compatibility with target K8s | Upgrade OpenKruise to compatible version |

## # K8s Resources & API (Items 4, 8, 9, 33, 75)

| # | Check Item | Description | Fix |
|---|------------|-------------|-----|
| 4 | Helm Template Check | HelmRelease must not contain target-version deprecated APIs | Update Helm templates to use non-deprecated APIs |
| 8 | K8s Deprecated Resource Check | Cluster must not have resources from deprecated API versions | Migrate resources to new API versions |
| 9 | Compatibility Risk Check | Version compatibility differences (not applicable for patch upgrades) | Review version-specific changes in this document |
| 33 | K8s Deprecated API Check | Audit logs (past 24h) must not show calls to deprecated APIs | Migrate API calls to non-deprecated versions |
| 75 | Addon Configuration Consistency Check | Addon ConfigMap must match Helm Release records (manual edits will be overwritten) | Use CCE addon management API instead of direct ConfigMap edits |

## # Node Pool & Scheduling (Items 5, 26, 72)

| # | Check Item | Description | Fix |
|---|------------|-------------|-----|
| 5 | Node Pool Check | Node pool status must be normal | Fix node pool issues |
| 26 | K8s Node Taint Check | Nodes must not have taints needed by upgrade process | Remove conflicting taints |
| 72 | Cluster and Node Pool Configuration Management Check | ENI network component nic-max-above-warm-target must not exceed maximum | Adjust ENI warm target configuration |

## # Security & Network (Items 6, 42, 58, 70, 71, 74, 76)

| # | Check Item | Description | Fix |
|---|------------|-------------|-----|
| 6 | Security Group Check | ICMP rule from control node security group must not be deleted | Restore ICMP security group rule |
| 42 | HTTPS ELB Certificate Consistency Check | HTTPS ELB certificate must not be modified outside CCE | Manage certificates through CCE only |
| 58 | ELB Listener Access Control Check | ELB listener access control configuration must be correct | Fix ELB access control configuration |
| 70 | Ingress and ELB Configuration Consistency Check | Ingress config must match ELB config (no manual ELB edits) | Manage ELB through CCE Ingress only |
| 71 | Cluster Network Component NetworkPolicy Switch Check | NetworkPolicy switch must match default (manual changes will be reset) | Use CCE network management API |
| 74 | VPC Container Reserved CIDR Upgrade Check | VPC container CIDR reservation switch should be enabled | Enable VPC container CIDR reservation |
| 76 | Secret Encryption-at-Rest Compatibility Check | Target version must support Secret encryption-at-rest if enabled | Disable Secret encryption if target version doesn't support |

## # Control Plane (Items 31, 32, 59, 73)

| # | Check Item | Description | Fix |
|---|------------|-------------|-----|
| 31 | User Node Component Health Check | Container runtime and network components must be healthy | Fix component issues |
| 32 | Control Node Component Health Check | K8s, runtime, network components on control nodes must be healthy | Fix control plane component issues |
| 59 | Control Node Subnet Quota Check | Subnet must have enough remaining IPs for rolling upgrade | Request subnet IP quota increase |
| 73 | Control Node Time Zone Check | Control node timezone must match cluster timezone | Align timezone settings |

## # Special Checks (Items 7, 10, 23, 24, 29, 30, 38, 43, 45, 55, 56, 57, 60, 61, 64, 65, 66)

| # | Check Item | Description | Fix |
|---|------------|-------------|-----|
| 7 | Remaining Nodes Pending Migration Check | Nodes requiring migration must be handled first | Complete node migration before upgrade |
| 10 | Node CCE Agent Version Check | cce-agent must be latest version | Upgrade cce-agent |
| 23 | Node Interfering ContainerdSock Check | Interfering containerd.sock file exists (affects EulerOS runtime startup) | Remove interfering sock file |
| 24 | Internal Error Check | Internal error in pre-check process | Contact support |
| 29 | Enhanced CPU Management Policy Check | Current and target version must support enhanced CPU management | Adjust CPU management policy |
| 30 | User Node Component Health Check | User node runtime and network components healthy | Fix unhealthy components |
| 38 | CoreDNS Configuration Consistency Check | CoreDNS Corefile must match Helm Release (manual edits overwritten during addon upgrade) | Manage CoreDNS through CCE addon API |
| 43 | Node Mount Check | Node mount configuration issues | Fix mount issues |
| 45 | ELB IPv4 Private IP Check | LoadBalancer Service ELB must have IPv4 private IP | Fix ELB IP configuration |
| 55 | Containerd Pod Restart Risk Check | Containerd upgrade may restart business Pods on containerd nodes | Accept Pod restart risk or plan for it |
| 56 | CCE AI Suite (NVIDIA GPU) Key Parameter Check | GPU plugin parameters must not be invasively modified | Restore GPU plugin default parameters |
| 57 | GPU/NPU Pod Rebuild Risk Check | kubelet restart during upgrade may rebuild GPU/NPU Pods | Plan for GPU/NPU Pod rebuild |
| 60 | Node Runtime Check | Docker runtime warning for v1.27+ upgrade (CCE plans to remove Docker support) | Plan Containerd migration |
| 61 | Node Pool Runtime Check | Node pool Docker runtime warning for v1.27+ | Migrate to Containerd |
| 64 | Secret Encryption-at-Rest Compatibility Check | Secret encryption-at-rest compatibility with target version | Disable if target doesn't support |
| 65 | Ubuntu Kernel and GPU Driver Compatibility Reminder | Ubuntu kernel 5.15.0-113-generic requires NVIDIA driver ≥535.161.08 | Upgrade GPU driver or change kernel |
| 66 | Drain Task Check | Unfinished drain tasks will trigger Pod eviction after upgrade | Complete all pending drain tasks |

# # Version-Specific Breaking Changes

## # All Upgrade Paths

- Check for **deprecated APIs** across all versions (see Deprecated API tables in official docs)
- Verify Helm templates don't use deprecated API versions

## # v1.28 → v1.29/v1.31

- **nf_conntrack_max override**: kube-proxy may set nf_conntrack_max lower than node sysctl. High-traffic nodes (gateways) may be affected.
- **Fix**: Use node pool kube-proxy config `conntrack-min` instead of direct sysctl modification.

## # v1.23/v1.25 → v1.27

- **Docker runtime deprecated**: Recommend Containerd migration for v1.27+ clusters.
- **CCE warning**: Docker runtime will be removed in future versions.

## # v1.23 → v1.25

- **PodSecurityPolicy removed**: Must migrate PSP → Pod Security Admission before v1.25 upgrade.
- **Migration**: (1) Confirm v1.23 latest patch; (2) Migrate PSP to PSA; (3) Verify migration works; (4) Upgrade to v1.25.

## # v1.21/v1.19 → v1.23

- **NGINX Ingress class annotation**: Ingress without `kubernetes.io/ingress.class: nginx` annotation ignored by v2.x controller.
- **Fix**: Add class annotation to all Ingress resources, or verify auto-detection.

## # v1.19 → v1.21

- **exec probe timeoutSeconds enforced**: Previously ignored, now enforced. Default 1s. Pods with >1s exec probe may fail.
- **Webhook SAN required**: v1.19+ apiserver requires SAN in webhook certificates. CommonName-only certificates fail.

## # v1.15 → v1.19

- **Kubelet label incompatibility**: v1.19 apiserver rejects v1.15 kubelet labels (`failure-domain.beta.kubernetes.io/is-baremetal`, `kubernetes.io/availablezone`). Nodes may become NotReady.
- **Docker fs change**: v1.19 switches Docker storage driver fs from xfs to ext4. Java apps may have import order changes.
- **Webhook SAN**: Same as v1.21 — webhook certificates need SAN.
- **PSP auto-creation**: v1.17.17+ auto-creates PSP restricting insecure configs (sysctl net.core.somaxconn). Need to reference PSP for access.
- **QosClass change**: v1.16+ kubelet counts initContainers in QosClass calculation. Pods may change QosClass after upgrade.