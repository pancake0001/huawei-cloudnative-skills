# Workflow

# # Reuse priority

Existing capabilities must be reused first:

- K8s objects: `huawei_get_cce_services`, `huawei_get_cce_ingresses`, `huawei_get_cce_pods`, `huawei_get_kubernetes_nodes`, `huawei_get_cce_events`, `huawei_get_pod_logs`.
- Cloud network: `huawei_list_elb`, `huawei_list_elb_listeners`, `huawei_get_elb_metrics`, `huawei_list_eip`, `huawei_get_eip_me trics`, `huawei_list_nat`, `huawei_get_nat_gateway_metrics`, `huawei_list_security_groups`, `huawei_list_vpc_acls`.
- Old versions of comprehensive diagnostics: `huawei_network_diagnose` and `huawei_network_diagnose_by_alarm` can continue to be used for rough diagnosis of links and monitoring in the workload dimension.
- Logging and observation: LTS/AOM logs, Pod logs, and AOM indicator capabilities already exist, and the log platform or indicator platform will not be re-implemented.

The newly added thin layer capabilities of this skill:

- `huawei_network_failure_diagnose`: Collect Service, Ingress, EndpointSlice, NetworkPolicy, Node, Pod, Events, CoreDNS/Ingress logs and cloud ELB backend health at one time, and directly generate Markdown reports.
- `huawei_get_elb_backend_status`: Read ELB pool/member/health monitor/load balancer status, and fix the problem that only looking at ELB indicators cannot confirm the specific backend health.

Things still not done:

- Do not execute `kubectl exec` active detection, and do not modify the security group/ACL/ELB/Ingress/Service.
- Does not replace `pod-failure-diagnoser`, `node-failure-diagnoser`, `workload-failure-diagnoser`; only cross-references when encountering Pod/Node/release roots.

# # Input and collection

Minimum input is `region`, `cluster_id`, `namespace`. Please complete the following fields as much as possible:

- `failure_symptom`: `Domain name cannot be resolved`, `Service unavailable within the cluster`, `Service jitters occasionally`, `External domain name/IP cannot be accessed`, `Ingress 502/504`.
- `target_kind` + `target_name`: Pod, Service, Ingress, etc.
- `service_name`, `ingress_name`, `source_pod`, `destination_pod`, `domain`, `elb_id`.

By default, `huawei_network_failure_diagnose` is called first. It forms a read-only context snapshot around the same moment in time and returns:

- `snapshot`: original object and cloud-side context.
- `findings` / `top_causes`: Structured diagnostic hits.
- `report_markdown`: The complete Markdown report finally delivered to the customer.

# # Hierarchical diagnostic pipeline

## # 1. Infrastructure and node layer

First check the nodes where the target source/destination Pod, backend Pod, and CoreDNS/Ingress Controller are located:

- `Ready=False` or `Ready=Unknown`: Directly output node base faults and prune to skip upper-layer application diagnosis.
- `MemoryPressure`, `DiskPressure`, `PIDPressure`, `NetworkUnavailable=True`: associated with `OOMKilled`, `KubeletNotReady`, `Evicted`, `FailedCreatePodSandBox` and other events. If it coincides with the fault window, it can be pruned.

## # 2. DNS link

Trigger condition: `failure_symptom` includes DNS, domain name, resolution, NXDOMAIN, etc.

Path: Client Pod -> `kube-dns` Service -> CoreDNS Pods -> Upstream DNS / Cluster Service DNS.

Assert:

- Client Pod `dnsPolicy=None` and no `dnsConfig`: Output Pod DNS configuration is missing.
- `kube-dns` EndpointSlice ready endpoint is 0: Output CoreDNS backend is unavailable.
- There are `OOMKilled`, `Liveness probe failed`, `Unhealthy`, `BackOff` in CoreDNS Events: output CoreDNS restart/probe failure causes resolution jitter.
- `NXDOMAIN` in CoreDNS logs: output service name spelling, namespace suffix or service does not exist.
- `i/o timeout` / timeout in CoreDNS logs: Output upstream DNS or out-of-cluster network failure candidates.

## # 3. East-West Service and Strategy

Trigger conditions: Service failure within the cluster, occasional failure, service jitter, or default check when no external link is specified.

Path: Source Pod -> NetworkPolicy -> Service -> EndpointSlice -> Destination Pod.

Assert:

- The target Pod is selected by NetworkPolicy, but the rule does not allow the source Pod label, namespace label, or port: Output NetworkPolicy interception with 100% confidence.
- There is no matching Pod in the Service selector, or the EndpointSlice ready endpoint is 0: the output Service selector/backend topology is broken.
- Backend Pod Events have intensive `Readiness probe failed` or `Unhealthy`: output readiness jitter causes the backend to be removed.
- Backend application logs include OOM, connection pool exhaustion, and connection refused: output application overload/denial of service candidates.

## # 4. North-south Ingress/ELB

Trigger conditions: External domain name/IP access failure, Ingress 502/504, ELB backend exception.

Path: External Request -> Cloud ELB/EIP -> Ingress Controller -> Service -> EndpointSlice -> Pod.

Assert:

- Empty `status.loadBalancer.ingress` for Ingress or LoadBalancer Service: Failed to create ELB in associated CCM/CCE Events, insufficient quota, insufficient permissions, wrong security group/subnet.
- ELB member/pool status is not healthy, K8s backend Pod Ready: Output cloud security group does not release NodePort, health check port error, node IPVS/Iptables/kube-proxy synchronization exception candidate.
- There are `502 Bad Gateway` and `504 Gateway Timeout` in Ingress Controller logs: Output Ingress to the backend or the backend application responds abnormally. Continue to check the Service/Endpoint and application timeout.

# # Reporting requirements

Markdown reports must contain:

1. Diagnosis overview: target, fault phenomenon, conclusion, confidence, collection time, and whether to prune.
2. Troubleshooting process: four-stage item-by-item status, indicating checked, abnormal, or pruning skipped.
3. Link topology: Outputs DNS, east-west, or north-south links by failure type.
4. Key object snapshots: Service, EndpointSlice, Backend Pods, Ingress, NetworkPolicy, Cloud ELB.
5. Evidence matrix: stage, type, confidence level, evidence summary.
6. Top root causes: up to 3, must be supported by evidence.
7. Recommended actions and verification standards: read-only verification or forwarding of change recommendations for recovery skills.