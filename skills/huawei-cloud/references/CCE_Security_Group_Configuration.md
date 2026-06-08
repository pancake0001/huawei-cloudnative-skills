# CCE cluster security group rule configuration instructions

> Reference document: https://support.huaweicloud.com/cce_faq/cce_faq_00265.html

# # Overview

CCE is a universal container platform, and the setting of security group rules is suitable for common scenarios. When the cluster is created, a security group will be automatically created for the Master node and the Node node:

| Security group type | Naming rules |
|-----------|----------|
| Master node security group | `{cluster name}-cce-control-{random ID}` |
| Node node security group | `{cluster name}-cce-node-{random ID}` |
| ENI Security Group (CCE Turbo) | `{cluster name}-cce-eni-{random ID}` |

# # ⚠️ IMPORTANT WARNING

- **Modifying security group rules is a high-risk operation** and may affect the normal operation of the cluster.
- Please operate with caution and choose to do it during low business hours
- If you need to modify the security group rules, please try to avoid modifying the port rules that CCE depends on.
- Some ports may still be dependent on the user's own business. It is recommended to fully verify it in the test environment first.
- Recommendations for the verification process include: port connectivity, cluster component availability, business full-link availability and other dimensions

---

# # 1. VPC network model security group rules

# # # 1.1 Node node security group

**Security group name**:`{cluster name}-cce-node-{random ID}`

## # # Inbound direction rules

| Direction | Port | Default source address | Description | Modification suggestions | Impact after modification |
|------|------|-----------|------|----------|-----------|
| Inbound direction | UDP: All | VPC network segment | Mutual access between Node nodes, Node node and Master node | ❌ Modification is not recommended | Affects the normal operation of the cluster |
| Inbound direction | TCP: All | Master node security group | Master node accesses Node nodes | ❌ Modification is not recommended | Affects the normal operation of the cluster || Inbound direction | ICMP: All | Master node security group | Master node accesses Node nodes | ❌ Modification is not recommended | Affects the normal operation of the cluster |
| Inbound direction | TCP:30000-32767 | All IPs (0.0.0.0/0) | NodePort service default access port range | ✅ Can be modified | VPC network segment, container network segment and ELB network segment need to be allowed |
| Inbound direction | UDP:30000-32767 | All IPs (0.0.0.0/0) | NodePort service default access port range | ✅ Can be modified | VPC network segment, container network segment and ELB network segment need to be allowed |
| Inbound direction | All | Container network segment | Allow containers in the cluster to access nodes | ❌ Modification is not recommended | Affects the normal operation of the cluster |
| Inbound direction | All | Node node security group | Instances in the Node node security group can access each other | ❌ Modification is not recommended | Affects the normal operation of the cluster |
| Inbound direction | TCP:22 | All IPs (0.0.0.0/0) | SSH remote connection | ✅ Suggested changes | It is recommended to only allow fixed IP access |

## # # Outbound direction rules

| Port | Default source address | Description | Modification suggestions |
|------|-----------|------|----------|
| All | All IPs (0.0.0.0/0) | Allow all by default | ✅ Can be modified, refer to outbound rule reinforcement suggestions |

# # # 1.2 Master node security group

**Security group name**:`{cluster name}-cce-control-{random ID}`

## # # Inbound direction rules

| Port | Default source address | Description | Modification suggestions | Impact after modification |
|------|-----------|------|----------|-----------|
| TCP:5444 | VPC network segment | kube-apiserver service port | ❌ Modification is not recommended | Affects the normal operation of the cluster |
| TCP:5444 | Container network segment | kube-apiserver service port | ❌ Modification is not recommended | Affects the normal operation of the cluster || TCP:9443 | VPC network segment | Node node network plug-in accesses the Master node | ❌ Modification is not recommended | Affects the normal operation of the cluster |
| TCP:5443 | All IPs (0.0.0.0/0) | HAProxy load balancing port of kube-apiserver | ✅ Suggested changes | VPC network segments and container network segments need to be reserved |
| TCP:8445 | VPC network segment | Node node storage plug-in accesses the Master node | ❌ Modification is not recommended | Affects the normal operation of the cluster |
| All | Master node security group | Instances in the Master node security group can access each other | ❌ Modification is not recommended | Affects the normal operation of the cluster |

> **CloudShell Function Description**: If you need to use the CloudShell function, please reserve port 5443 and open the `198.19.0.0/16` network segment, otherwise you will not be able to access the cluster.

## # # Outbound direction rules

| Port | Default source address | Description | Modification suggestions |
|------|-----------|------|----------|
| All | All IPs (0.0.0.0/0) | All are allowed by default | ❌ Modification is not recommended |

---

# # 2. Container tunnel network model security group rules

# # # 2.1 Node node security group

**Security group name**:`{cluster name}-cce-node-{random ID}`

## # # Inbound direction rules

| Port | Default source address | Description | Modification suggestions | Impact after modification |
|------|-----------|------|----------|-----------|
| UDP:4789 | All IPs (0.0.0.0/0) | Network access between containers | ❌ Modification is not recommended | Affects the normal operation of the cluster |
| TCP:10250 | Master node network segment | Master node accesses Node node kubelet | ❌ Modification is not recommended | Affects the normal operation of the cluster |
| TCP:30000-32767 | All IPs (0.0.0.0/0) | NodePort service port range | ✅ Modifiable | VPC network segment, container network segment and ELB network segment need to be opened || UDP:30000-32767 | All IPs (0.0.0.0/0) | NodePort service port range | ✅ Modifiable | VPC network segment, container network segment and ELB network segment need to be opened |
| TCP:22 | All IPs (0.0.0.0/0) | SSH remote connection | ✅ Suggested changes | It is recommended to only allow fixed IP access |
| All | Node node security group | Instances in the Node node security group can access each other | ❌ Modification is not recommended | Affects the normal operation of the cluster |

# # # 2.2 Master node security group

**Security group name**:`{cluster name}-cce-control-{random ID}`

## # # Inbound direction rules

| Port | Default source address | Description | Modification suggestions | Impact after modification |
|------|-----------|------|----------|-----------|
| UDP:4789 | All IPs (0.0.0.0/0) | Network access between containers | ❌ Modification is not recommended | Affects the normal operation of the cluster |
| TCP:5444 | VPC network segment | kube-apiserver service port | ❌ Modification is not recommended | Affects the normal operation of the cluster |
| TCP:5444 | Container network segment | kube-apiserver service port | ❌ Modification is not recommended | Affects the normal operation of the cluster |
| TCP:9443 | VPC network segment | Node node network plug-in accesses the Master node | ❌ Modification is not recommended | Affects the normal operation of the cluster |
| TCP:5443 | All IPs (0.0.0.0/0) | HAProxy load balancing port of kube-apiserver | ✅ Suggested changes | VPC network segments and container network segments need to be reserved |
| TCP:8445 | VPC network segment | Node node storage plug-in accesses the Master node | ❌ Modification is not recommended | Affects the normal operation of the cluster |
| All | Master node security group | Instances in the Master node security group can access each other | ❌ Modification is not recommended | Affects the normal operation of the cluster |

---

# # 3. Cloud native network 2.0 (CCE Turbo cluster) security group rules

# # # 3.1 Node node security group**Security group name**:`{cluster name}-cce-node-{random ID}`

## # # Inbound direction rules

| Port | Default source address | Description | Modification suggestions | Impact after modification |
|------|-----------|------|----------|-----------|
| TCP:10250 | Master node network segment | Master node accesses Node node kubelet | ❌ Modification is not recommended | Affects the normal operation of the cluster |
| TCP:30000-32767 | All IPs (0.0.0.0/0) | NodePort service port range | ✅ Modifiable | VPC network segment, container network segment and ELB network segment need to be opened |
| UDP:30000-32767 | All IPs (0.0.0.0/0) | NodePort service port range | ✅ Modifiable | VPC network segment, container network segment and ELB network segment need to be opened |
| TCP:22 | All IPs (0.0.0.0/0) | SSH remote connection | ✅ Suggested changes | It is recommended to only allow fixed IP access |
| All | Node node security group | Instances in the Node node security group can access each other | ❌ Modification is not recommended | Affects the normal operation of the cluster |
| All | Container subnet segment | Allow containers in the cluster to access nodes | ❌ Modification is not recommended | Affects the normal operation of the cluster |

# # # 3.2 Master node security group

**Security group name**:`{cluster name}-cce-control-{random ID}`

## # # Inbound direction rules

| Port | Default source address | Description | Modification suggestions | Impact after modification |
|------|-----------|------|----------|-----------|
| TCP:5444 | All IPs (0.0.0.0/0) | kube-apiserver service port | ❌ Modification is not recommended | Affects the normal operation of the cluster |
| TCP:5444 | VPC network segment | kube-apiserver service port | ❌ Modification is not recommended | Affects the normal operation of the cluster || TCP:9443 | VPC network segment | Node node network plug-in accesses the Master node | ❌ Modification is not recommended | Affects the normal operation of the cluster |
| TCP:5443 | All IPs (0.0.0.0/0) | HAProxy load balancing port of kube-apiserver | ✅ Suggested changes | VPC network segments and container network segments need to be reserved |
| TCP:8445 | VPC network segment | Node node storage plug-in accesses the Master node | ❌ Modification is not recommended | Affects the normal operation of the cluster |
| All | Master node security group | Instances in the Master node security group can access each other | ❌ Modification is not recommended | Affects the normal operation of the cluster |
| All | Container subnet segment | All source addresses of the container subnet segment must be allowed | ❌ Modification is not recommended | It will affect the normal operation of the cluster |

# # # 3.3 ENI security group (for CCE Turbo only)

**Security group name**:`{cluster name}-cce-eni-{random ID}`

## # # Inbound direction rules

| Port | Default source address | Description | Modification suggestions | Impact after modification |
|------|-----------|------|----------|-----------|
| All | ENI security group | Allow containers in the cluster to access each other | ❌ Modification is not recommended | Affects the normal operation of the cluster |
| All | VPC network segment | Allow instances in the cluster VPC to access the container | ❌ Modification is not recommended | Affects the normal operation of the cluster |

---

# # 4. Recommendations for strengthening security group outbound rules

For outbound rules, all security groups created by CCE are allowed by default, and it is generally not recommended to modify them. If you need to strengthen outbound rules, please note that the following ports need to be allowed:

# # # Minimum range of Node node security group outbound rules

| Port | Allow address segment | Description |
|------|-----------|------|
| TCP:53 | Subnet's DNS server | Used for domain name resolution |
| UDP:53 | Subnet's DNS server | Used for domain name resolution |
| TCP:5353 | Container network segment | Used for CoreDNS domain name resolution || UDP:5353 | Container network segment | Used for CoreDNS domain name resolution |
| UDP:4789 | All IPs | Inter-container network access (only container tunnel network model) |
| TCP:5443 | Master node network segment | HAProxy load balancing port of kube-apiserver |
| TCP:5444 | VPC network segment, container network segment | kube-apiserver service port |
| TCP:6443 | Master node network segment | kube-apiserver service port |
| TCP:8445 | VPC network segment | Node node storage plug-in accesses Master node |
| TCP:9443 | VPC network segment | Node node network plug-in accesses Master node |
| All ports | 198.19.128.0/17 network segment | Access VPCEP service |
| UDP:123 | 100.125.0.0/16 network segment | Node node accesses the intranet NTP server port |
| TCP:443 | 100.125.0.0/16 network segment | Node node accesses the intranet OBS port to pull the installation package |
| TCP:6443 | 100.125.0.0/16 network segment | Node node reports node installation successful |
| TCP:8102 | 100.125.0.0/16 network segment | Node node log plug-in access LTS |

---

# # 5. Common port descriptions

| Port | Protocol | Purpose |
|------|------|------|
| 22 | TCP | SSH remote connection |
| 5443 | TCP | HAProxy load balancing port of kube-apiserver |
| 5444 | TCP | kube-apiserver service port |
| 6443 | TCP | kube-apiserver service port |
| 8445 | TCP | Node node storage plug-in accesses Master node |
| 9443 | TCP | Node node network plug-in accesses Master node |
| 10250 | TCP | kubelet port || 30000-32767 | TCP/UDP | NodePort service port range |
| 4789 | UDP | Network communication between VXLAN containers (tunnel network) |
| 53 | TCP/UDP | DNS domain name resolution |
| 5353 | TCP/UDP | CoreDNS domain name resolution |

---

# # 6. Steps to modify security group rules

1. Log in to [VPC console](https://console.huaweicloud.com/vpc/#/vpc/vpcs/list)
2. Click "Access Control > Security Group" in the left navigation bar
3. Find the security group corresponding to the cluster (identified according to naming rules)
4. Click the security group name to enter the details page
5. Make modifications on the "Inbound Rules" or "Outbound Rules" tab

---

# # Related documents

- [CCE Network Planning](https://support.huaweicloud.com/cce_faq/cce_faq_00265.html)
- [VPC Security Group Configuration](https://support.huaweicloud.com/usermanual-vpc/vpc_SG_001.html)
- [CCE Cluster Access Control](https://support.huaweicloud.com/cce_faq/cce_faq_00265.html)