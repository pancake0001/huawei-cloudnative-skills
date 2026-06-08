# CCE node vulnerability repair guide

> 📅 **Update: 2026-04-08** — Updated based on real experience of repairing accidents in test-cce-ai-diagnose cluster

---

# # 1. Core Lessons (Must Read)

# # # ⚠️ `immediate_repair` is an asynchronous API — this is crucial

After calling `change_vul_status(operate_type=immediate_repair)`:

1. API **returns 200** immediately (request accepted)
2. The vulnerability status changes from `unfix` → `fixing` (fixing in progress)
3. HSS Agent **asynchronously downloads and installs patches** on the node
4. **For vulnerabilities that require restarting**, the status is still `fixing` after the patch installation is completed. **The node must be restarted** for the fix to take effect, and the status changes to `fixed`

**If skipped reboot_ecs:**
- Vulnerability status stuck at `fixing` (looks like "fixing")
- Users thought it was "under repair" → the actual system was not repaired at all.
- **This is the most dangerous situation: false sense of security**

# # # ⚠️ `change_vul_status` does not support safe idempotent retries

The repair trigger is a **write operation** and cannot be retried at will:
- First call: return 200, status → `fixing`
- Call again (status is still `fixing`): return **HSS.1105** (Unknown error)
- **Encountering HSS.1105 ≠ Failure** is a signal that the server rejects repeated requests; indicating that the first call has been successfully triggered and no further adjustments are needed.

**Therefore, you must first confirm that the vulnerability status is `unfix`** before triggering the fix, otherwise it may be idempotently intercepted or produce unexpected behavior.

# # # ⚠️ reboot_ecs must not be skipped

Kernel/bpftool/kernel-tools class vulnerabilities (HCE2-SA-2025-0327, etc.):
- Repair method: `yum update kernel && reboot`
- After the patch installation is completed, you must **restart the node** for the new kernel to take effect
- Restarting is a **required step** for vulnerability repair, not an optional step

---# # 2. Execution responsibilities and operating specifications

# # # Division of responsibilities: Business confirmation is the job of AI

When developing a remediation plan, **business impact assessment and validation is the responsibility of the AI, not the user**:

1. **Analysis Phase** (AI completes automatically, no need to notify the user):
   - Query node Pod distribution and identify the number of business copies
   - Identify high-risk nodes (coredns/Ingress/single-copy business nodes)
   - Evaluate whether repairs can be done in parallel

2. **Planning stage** (AI completed, provided to user for confirmation):
   - Output the complete repair plan (node sequence, batching strategy, business impact)
   - Provide options (if any)
   - **Clear the business impact in the plan**, don’t let users infer on their own

3. **Execution Phase** (AI automatically executes, providing real-time observability):
   - Report the results (success/failure/specific content) immediately after each step of operation is completed
   - Stop immediately when failure occurs, report an error, and do not automatically skip and continue
   - When restarting a node, wait for the node to be Ready before continuing.

**Time to notify the user**: Only notify the user when it is time to confirm the strategy, do not disturb the user at every step.

# # # Priority order of repair methods

**By default, HSS `change_vul_status` API is used for automatic repair** unless:
- Credential without permission (returns HSS.0013)
- API does not support this vulnerability type
- Vulnerability types require manual intervention (if manual compilation and installation are required)

Manually logging in to the node and executing the yum command is a **cover-in solution** and is not the first choice.

# # # The node name and tool name must be complete

**Truncation prohibited**:
- Node name: You must use the complete name (such as `test-cce-ai-diagnose-nodepool-43986-y6bwx`, you cannot just write `y6bwx`)
- server_id / instance_id: must be complete and cannot be omitted
- Tool name: You must use the complete tool name (such as `huawei_hss_change_vul_status`, you cannot just write `change_vul_status`)
- Vulnerability ID: must be complete (such as `HCE2-SA-2025-0327`, cannot just write `0327`)**Output format requirements**: Key operation output must contain complete identifiers to facilitate tracking and log retrieval.

# # # Enforce observability requirements

**Must report** after each step of operation is completed:
- The complete tool name and key parameters of the operation
- Return result (success/failure)
- On failure: complete error message (HSS error code + description)
- After reboot: Node Ready status confirmation

**Prohibited Behavior**:
- You cannot just report "success/failure" without saying the specific content
- Cannot continue uncordon while reboot is not complete
- Cannot report "Fix Completed" before verification
- Cannot skip reboot and enter the next node

---

# # 3. Vulnerability status (official definition)

| Status value | Meaning | Description |
|--------|------|------|
| `vul_status_unfix` | Not processed | The vulnerability exists and has not been fixed yet |
| `vul_status_ignored` | Ignored | Manually ignored |
| `vul_status_verified` | Verifying | Verifying vulnerability |
| `vul_status_fixing` | Repairing | ⚠️ **The patch is being installed and needs to be restarted to take effect** |
| `vul_status_fixed` | Fixed | ✅ **Fixed (the kernel vulnerability must be restarted before it can become this state)** |
| `vul_status_reboot` | Repair needs to be restarted | The patch has been installed and needs to be restarted to take effect |
| `vul_status_failed` | Repair failed | Repair execution failed |
| `vul_status_fix_after_reboot` | Please restart to repair | Need to restart to perform repair again |

> **`vul_status_unhandled` is not the official vulnerability status**, it is an alias for "all vulnerabilities", and the actual behavior is equivalent to not passing the status parameter. To filter unhandled vulnerabilities, `vul_status_unfix` should be used.

---

# # 4. Complete repair workflow (correct version)

```
Stage 1: Information collection
├── Cluster node list → huawei_list_cce_nodes (including server_id)├── Node vulnerability overview → huawei_hss_list_hosts (match server_id)
└── Single node vulnerability details → huawei_hss_list_host_vuls_all

Phase 2: Develop a remediation plan
├── Confirm the fix method of each vulnerability (yum update / reboot)
├── Confirm the existence of reboot vulnerability → reboot_ecs must be executed
└── Negotiate and confirm with the user before executing

Phase 3: Execution node by node (each node must complete all steps in order)
│
├── Step ① cordon (mark unschedulable)
│ confirm=true
│
├── Step ② drain (evict Pod)
│ confirm=true
│
├── Step ③ HSS trigger repair ← Must be executed
│ huawei_hss_change_vul_status(operate_type=immediate_repair, confirm=true)
│ ⚠️ API returns 200 ≠ Repair completed
│
├── Step ④ reboot_ecs ← Never skip
│ confirm=true
│ ⚠️ reboot is a necessary step to repair kernel vulnerabilities
│ ⚠️ K8s will automatically detect if the node is NotReady during restart
│
├── Step ⑤ Wait for node Ready
│ huawei_cce_node_status Confirm node status recovery
│ ⚠️ You must wait for the node to be Ready before proceeding to the next step.
│
├── Step ⑥ uncordon (restore scheduling)
│ confirm=true
│
└── Step ⑦ Verify vulnerability status
    huawei_hss_list_host_vuls_all
    ⚠️ Must be verified after reboot, not immediately after API call
    ⚠️ Kernel vulnerability: the status should be fixed after reboot
    ⚠️ If it is still fixing: It may be that the HSS Agent installation failed and you need to check the node log.

Stage 4: Business recovery confirmation
├── Confirm that the business Pod has been rebuilt and running└── If there is any abnormality → Enter the "Unexpected Impact Response" process
```

# # # Consequences of skipping each step

| Steps | Skip Consequences |
|------|---------|
| ① cordon | drain When new Pod is scheduled to this node, business will be interrupted when restarting |
| ② drain | The business Pod crashes when the node is restarted, and the service is interrupted |
| ③ HSS trigger | The vulnerability does not trigger the fix at all |
| ④ reboot_ecs | **The kernel vulnerability is stuck in fixing. The user thinks it is being fixed, but it is not actually fixed** |
| ⑤ Waiting for Ready | The node uncordoned before it was started, and Pod scheduling failed |
| ⑥ uncordon | The node is permanently unavailable |
| ⑦ Verification | I don’t know whether the repair was successful or not |

---

# # 5. Tool list

# # # CCE node operations

| Tools | Features | confirm |
|------|------|--------|
| `huawei_cce_node_cordon` | Mark the node as unschedulable | ✅ |
| `huawei_cce_node_uncordon` | The recovery node can be scheduled | ✅ |
| `huawei_cce_node_drain` | Evict node Pod (non-system) | ✅ |
| `huawei_cce_node_status` | Query node scheduling status | Query |

# # # HSS vulnerability operations

| Tools | Features | confirm |
|------|------|--------|
| `huawei_hss_list_host_vuls_all` | Query host vulnerabilities (full volume, automatic page turning) | Query |
| `huawei_hss_list_hosts` | Query an overview of all host vulnerabilities | Query || `huawei_hss_change_vul_status` | Modify vulnerability status (fix/ignore/verify) | ✅ |

# # # ECS operations

| Tools | Features | confirm |
|------|------|--------|
| `huawei_reboot_ecs` | Restart the ECS instance | ✅ |

---

# # 6. Key constraints

# # # data_list and host_data_list are mutually exclusive

| Scenario | Calling method |
|------|---------|
| All vulnerabilities of the host | `host_data_list=[HostVulOperateInfo(host_id=..., vul_id_list=None)]` |
| Specify vulnerability list | `data_list=[VulOperateInfo(vul_id=...) for ...]` |
| Simultaneous upload | ❌ HSS.0004 |

# # # confirm mechanism

All change operations (cordon/drain/uncordon/reboot/change_vul_status) require `confirm=true` before they are actually executed.

---

# # 7. Error code quick check

| Error code | Meaning | Actual meaning and processing |
|--------|------|--------------|
| HSS.0004 | Database operation failed | data_list and host_data_list cannot be transmitted at the same time |
| HSS.0013 | Insufficient permissions | AK/SK no HSS repair permissions, authorized in the console |
| HSS.0191 | Host protection is not enabled | Enable HSS protection first |
| HSS.1059 | Vulnerability status does not allow operation | Confirm that the vulnerability status is unfix to trigger repair |
| HSS.1060 | Repair failed | Check HSS Agent status and node system logs |
| HSS.1061 | The vulnerability is being repaired | Waiting for the repair to be completed (HSS.1105 may also appear at the same time, which is normal idempotence) |
| **HSS.1105** | **Unknown error** | ⚠️ **Not a failure! It is an idempotent callback signal. The first call is successful, and subsequent calls are intercepted** |

---

# # 8. Verification requirements

# # # Verification timing

- **Wrong practice**: Verify immediately after the API call returns 200 → the status may still be fixing at this time
- **Correct approach**: Wait 2-3 minutes after reboot and then verify → Only after the kernel patch takes effect can you see fixed

# # # Verification judgment criteria

| Vulnerability type | Status after successful repair |
|---------|--------------|
| Non-kernel vulnerabilities (bind/openssl/cups, etc.) | `fixed` or `unfix` (depending on whether the HSS Agent has been installed) |
| Kernel vulnerabilities (HCE2-SA-2025-0327, etc.) | `fixed` (can only be changed to fixed after reboot) |

---

# # 9. Response to Unintended Impacts

If the business is found to be affected during the repair process, proceed in the following order:

1. **cordon the abnormal node immediately** (prevent new Pod scheduling)
2. **Check node Pod status**: `huawei_get_cce_pods`
3. **Expand new nodes** to undertake current business
4. **Evict the Pod on the abnormal node** (drain)
5. **Root cause analysis**: Check HSS repair logs and node system status
6. **Decision**: Continue to repair other nodes or suspend this repair plan

---

# # 10. Other references

- [Node fault detection policy configuration](./CCE_Node_Fault_Detection_Configuration.md)
- [CCE Security Group Configuration Instructions](./CCE_Security_Group_Configuration.md)