# CCE Node Kernel Baseline

This reference summarizes the recommended Linux kernel parameter values in the Huawei Cloud CCE node operating-system guidance. It is a comparison
baseline only: it is not an automatic remediation policy and does not prove that a node is unhealthy when its value differs.

## Baseline Values

| Parameter | Recommended value | Comparison | Purpose and applicability |
| --- | --- | --- | --- |
| `baseResourceConfiguration.cpu.usageRatio` | Less than `80%` | `>= 80%` is abnormal; `>= 90%` is critical | Current node CPU usage. |
| `baseResourceConfiguration.memory.usageRatio` | Less than `80%` | `>= 80%` is abnormal; `>= 90%` is critical | Current node memory usage. |
| `baseResourceConfiguration.disk[*].usageRatio` | Less than `80%` | `>= 80%` is abnormal; `>= 90%` is critical | Current usage for each collected node filesystem. |
| `systemConfiguration.fileDescriptor.usageRatio` | Less than `80%` | `>= 80%` is abnormal; `>= 90%` is critical | Current node file-descriptor usage. |
| `systemConfiguration.pid.usageRatio` | Less than `80%` | `>= 80%` is abnormal; `>= 90%` is critical | Current node PID usage. |
| `agentConfiguration.componentStatus[*].healthy` | `true` for every component | Any non-`true` or missing health state is abnormal | Health of collected node components. |
| `agentConfiguration.configurationConsistent` | Empty list | Any returned item is a configuration inconsistency | Reported node component configuration differences. |
| `agentConfiguration.criticalDependency` | No reported check errors | Any returned error, failure, unavailable, or non-zero-exit indication is abnormal | Critical runtime and node dependency checks. |
| `status.phase` | `Succeeded` | `Failed`, `Error`, timeout, or unavailable result is abnormal | Completion state of the CCE configuration collector. |
| `nf_conntrack_count / nf_conntrack_max` | Less than `80%` | `>= 80%` is abnormal; `>= 90%` is critical | Connection-tracking table utilization. |
| `net.netfilter.nf_conntrack_tcp_be_liberal` | `1` | Exact value | Enables more tolerant TCP window handling for NAT traffic. |
| `net.ipv4.tcp_max_tw_buckets` | `5000` | Exact value | Maximum number of `TIME_WAIT` sockets; values above the limit can increase node resource consumption. |
| `net.ipv4.tcp_tw_reuse` | `2` | Exact value | CCE node TCP `TIME_WAIT` socket reuse setting. |
| `net.ipv4.ip_local_port_range` | `32768-60999` | Exact value | CCE node ephemeral local port range. |
| `net.ipv4.ip_local_reserved_ports` | `3125-3126,3225-3226,4789,5137,8080,9253,9353,10248-10250,10255-10256,20101,20104,20202,20256-20257,28001-28002` | Exact value | Reserved ports for CCE node, CNI, and component traffic. |
| `net.ipv4.conf.eth0.arp_ignore` | `0` | Exact value | CCE node ARP reply behavior for the primary interface. |
| `net.ipv4.ip_forward` | `1` | Exact value | IPv4 forwarding must remain enabled for CCE node networking. |
| `DNS` nameservers | `100.125.0.0/16` | Every reported nameserver must be in this range | CCE node DNS resolver addresses. |
| `net.core.somaxconn` | `32768` | `actual >= baseline` | Maximum established connection queue size. |
| `net.ipv4.neigh.default.gc_thresh1` | `0` | Informational | ARP/neighbor-table garbage-collection threshold. Do not change without a specific need. |
| `net.ipv4.neigh.default.gc_thresh2` | `4096` | Informational | ARP/neighbor-table garbage-collection threshold. Do not change without a specific need. |
| `net.ipv4.neigh.default.gc_thresh3` | `163790` | `actual >= baseline` when applicable | Maximum non-permanent neighbor entries; increase only for many interfaces or directly connected devices. |

## Comparison Rules

- The list intentionally includes only values currently reported by `NodeConfigurationCollection`; do not claim a comparison for a parameter that the
  collector does not return.
- For capacity, count, queue, limit, and buffer parameters, an actual value greater than or equal to the baseline is normal. Do not flag it merely for being
  larger than the recommendation.
- For conntrack utilization, use `nf_conntrack_count / nf_conntrack_max`, not the absolute count: below `80%` is normal, `80%` to below `90%` is a
  warning, and `90%` or higher is critical.
- Treat workload intent, node operating system, CCE version, node size, and kube-proxy configuration as context before recommending a change.
- Changing kernel parameters is outside this diagnostic skill. Follow the CCE node-change procedure and confirm the change separately.

## Source

Huawei Cloud CCE: [Modify Node Kernel Parameters](https://support.huaweicloud.com/usermanual-cce/cce_10_0412.html).
