# Huawei Cloud CCE Workload Troubleshooting Guide / CCE Workload Troubleshooting Guide

**Update time: 2026-04-02 GMT+8**

**Source: Huawei Cloud official document https://support.huaweicloud.com/cce_faq/cce_faq_00134.html**

---

# # Document overview

This document organizes the complete troubleshooting path when the workload status of Huawei Cloud CCE (Cloud Container Engine) is abnormal, including all relevant links and troubleshooting directions. It can be used as a problem location guide for daily operation and maintenance.

---

# # Positioning process

```
Abnormal workload status
       │
       ▼
   View Pod status + events
       │
       ├─ Pending ──→ Scheduling failed/volume mounting failed/adding storage failed
       ├─ ImagePullBackOff ──→ Failed to pull the image
       ├─ CrashLoopBackOff ──→ Failed to start container
       ├─ Evicted ──→ Pod was evicted
       ├─ Creating ──→ Always creating
       ├─ Terminating ──→ Always terminating
       ├─ Stopped ──→ Stopped
       └─ Running but not working → Configuration problem
```

---

# # Abnormal status and troubleshooting links

| Status | Description | Troubleshooting Documents |
|------|------|----------|
| **Pending** | Instance scheduling failed | [Instance scheduling failed](https://support.huaweicloud.com/cce_faq/cce_faq_00098.html) |
| **Pending** | The storage volume cannot be mounted | [The storage volume cannot be mounted](https://support.huaweicloud.com/cce_faq/cce_faq_00200.html) |
| **Pending** | Failed to add storage | [Failed to add storage](https://support.huaweicloud.com/cce_faq/cce_faq_00433.html) |
| **ImagePullBackOff** | Failed to pull the image | [Failed to pull the image from the instance](https://support.huaweicloud.com/cce_faq/cce_faq_00015.html) |
| **CrashLoopBackOff** | Failed to start the container | [Failed to start the container](https://support.huaweicloud.com/cce_faq/cce_faq_00018.html) |
| **Evicted** | Pod was evicted | [Instance eviction exception](https://support.huaweicloud.com/cce_faq/cce_faq_00209.html) |
| **Creating** | Always being created | [Always being created](https://support.huaweicloud.com/cce_faq/cce_faq_00140.html) |
| **Terminating** | Still being terminated | [Pod Terminating](https://support.huaweicloud.com/cce_faq/cce_faq_00210.html) |
| **Stopped** | Stopped | [Stopped](https://support.huaweicloud.com/cce_faq/cce_faq_00012.html) |
| **Running** | Running but not working | [Status normal but not working properly](https://support.huaweicloud.com/cce_faq/cce_faq_00471.html) |
| **Init:Error** | Init container failed to start | [Init container failed to start](https://support.huaweicloud.com/cce_faq/cce_faq_00469.html) |

---

# # Detailed troubleshooting items

## # 1. Instance scheduling failed

**Link**: https://support.huaweicloud.com/cce_faq/cce_faq_00098.html

**Common error messages**:

| Error message | Cause of the problem |
|---------|----------|
| `no nodes available` | There are no nodes available in the cluster |
| `Insufficient cpu/memory` | CPU/memory is insufficient |
| `volume node affinity conflict` | The storage volume and the node are not in the same availability zone |
| `node(s) had taints` | Pod does not meet taint tolerance |
| `Too many pods` | The number of node Pods exceeds the limit |
| `everest driver not found` | everest plug-in exception |
| `Thin Pool has xxxx free data blocks` | Insufficient node storage space |

**Troubleshooting sub-items**:

-Troubleshooting item 1: Whether there are no available nodes in the cluster
-Troubleshooting item 2: Whether node resources (CPU, memory, etc.) are sufficient
- Troubleshooting item three: Check the affinity configuration of the workload
- Check item 4: Whether the mounted storage volume and the node are in the same availability zone
- Troubleshooting Item 5: Check Pod Taint Tolerance
- Troubleshooting item six: Check temporary volume usage
- Troubleshooting item 7: Check whether the everest plug-in is working properly
- Troubleshooting item eight: Check whether the node thinpool space is sufficient
- Troubleshooting item nine: Check whether there are too many Pods scheduled on the node
- Troubleshooting item 10: kubelet static binding core exception

---

## # 2. The storage volume cannot be mounted.

**Link**: https://support.huaweicloud.com/cce_faq/cce_faq_00200.html

| Storage Types | Frequently Asked Questions | Solutions |
|---------|----------|----------|
| **EVS cloud disk** | Availability zone is inconsistent | Make sure the disk and node are in the same availability zone |
| **EVS cloud disk** | Multiple instances mount the same volume | The number of copies can only be 1 |
| **EVS cloud disk** | File system damage | Use fsck to repair |
| **SFS Turbo** | Shared address error | Check everest.io/share-export-location in PV |
| **SFS Turbo** | Network failure | Test node to SFS Turbo network |
| **SFS Universal Edition** | VPCEP is not created | Create VPC endpoint in cluster VPC |

---

## # 3. Failed to pull the image

**Link**: https://support.huaweicloud.com/cce_faq/cce_faq_00015.html

| Error Message | Cause of Problem | Solution |
|---------|----------|----------|
| `denied: You may not login yet` | imagePullSecret not configured | Configure SWR key |
| `no such host` | Mirror address error | Check mirror address |
| `no space left on device` | Insufficient node disk | Clear disk space |
| `certificate signed by unknown authority` | Warehouse certificate issues | Use trusted certificates or self-signed |
| `context canceled` | Image is too large | Optimize image size |
| `request canceled` | Network failure | Check network/mirror warehouse connectivity |
| `Too Many Requests` | Docker Hub rate limit | Log in to Docker Hub or use SWR |

---

## # 4. Failed to start container

**Link**: https://support.huaweicloud.com/cce_faq/cce_faq_00018.html

| Exit code | Cause of problem | Solution |
|-------|----------|----------|
| exit(0) | The container has no ongoing process | Keep the foreground process running |
| exit(137) | Health check failed | Check Liveness Probe configuration |
| - | Insufficient disk space | Clean up thinpool space |
| - | Insufficient OOM memory | Increase Pod memory limit |
| - | Port conflict | Check container port configuration |
| - | Secret is not Base64 encoded | Encode the Secret value |
| - | Architecture mismatch (ARM/x86) | Use image with matching architecture |
| exit(141) | tail -f is incompatible | Replace the startup command |
| - | Java probe version is incompatible | Upgrade/downgrade probe version |

---

## # 5. Pod was evicted (Evicted)

**Link**: https://support.huaweicloud.com/cce_faq/cce_faq_00209.html

Common reasons: Node resources exceed limit (memory/CPU/disk)

---

## # 6. Pod is always in Terminating

**Link**: https://support.huaweicloud.com/cce_faq/cce_faq_00210.html

---

## # 7. The status is normal but inaccessible

**Link**: https://support.huaweicloud.com/cce_faq/cce_faq_00471.html

---

## # 8. Init container failed to start**Link**: https://support.huaweicloud.com/cce_faq/cce_faq_00469.html

---

# # Common troubleshooting commands

```bash
# Check Pod status
kubectl get pod -n {namespace}

# View Pod detailed events
kubectl describe pod {pod-name} -n {namespace}

# View Pod logs
kubectl logs {pod-name} -n {namespace}

# View the previous log (after the container is restarted)
kubectl logs {pod-name} -n {namespace} --previous

# Check node status
kubectl get node

# Check node taint
kubectl describe node {node-name}

# Check node resource status
kubectl describe node {node-name} | grep -A 5 "Allocated resources"

# Check disk usage
df-h

# Check the number of Pods on the node
kubectl get pods -o wide | grep {node-ip}

# View OOM log
grep -i oom /var/log/messages

# Enter container debugging
kubectl exec -it {pod-name} -n {namespace} -- /bin/sh
```

---

# # Pod event viewing method

## # Method 1: View on the console

1. Log in to the CCE console
2. Enter the cluster → Workload
3. Click the workload name
4. Find the exception instance → More → Events

## # Method 2: Command line view

```bash
kubectl describe pod {pod-name} -n {namespace}
```

Focus on the Events section, common event types:

| Event | Meaning |
|------|------|
| FailedScheduling | Scheduling failed |
| SuccessfulCreatePod | Pod created successfully |
| Pulling | Pulling the image |
| Pulled | Image pulled successfully |
| Created | Container created successfully |
| Started | The container started successfully |
| Killing | Terminating container |
| BackOff | Container startup failed, retrying |
| Unhealthy | Health check failed |

---

# # Related documents

| Documentation | Links |
|------|------|
| Workload status abnormality locating method (main document) | https://support.huaweicloud.com/cce_faq/cce_faq_00134.html |
| How to log in to the container | https://support.huaweicloud.com/usermanual-cce/cce_10_00356.html |
| The cluster is available but the node is unavailable | https://support.huaweicloud.com/cce_faq/cce_faq_00120.html |
| Reset node | https://support.huaweicloud.com/usermanual-cce/cce_10_0003.html |