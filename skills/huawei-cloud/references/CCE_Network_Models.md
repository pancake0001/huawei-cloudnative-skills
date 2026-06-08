# Detailed explanation of CCE cluster network mode

> Reference documents:
> - https://support.huaweicloud.com/usermanual-cce/cce_10_0282.html (VPC network)
> - https://support.huaweicloud.com/usermanual-cce/cce_10_0283.html (Cloud Native Network 2.0)
> - https://support.huaweicloud.com/usermanual-cce/cce_10_0284.html (container tunnel network)

---

# # Overview

CCE supports three network models, each model is suitable for different scenarios:

| Network model | Applicable scenarios | Performance | Complexity |
|---------|---------|------|--------|
| **VPC Network** | Traditional applications, small clusters | Medium | Low |
| **Container Tunnel Network** | Large-scale clusters, multi-tenancy | Higher | Medium |
| **Cloud Native Network 2.0** | High performance, low latency, large scale | Highest | Low |

---

# # 1. VPC network

# # # 1.1 Overview

The VPC network is the default network mode of CCE. The container network communicates with the VPC network, and the container directly uses the subnet IP of the VPC.

# # # 1.2 Architecture features

```
┌────────────────────────────────────────────
│ VPC Network │
│ ┌────────────────────────────────┐ │
│ │ Container subnet │ │
│ │ ┌─────┐ ┌─────┐ ┌─────┐ │ │
│ │ │Pod 1│ │Pod 2│ │Pod 3│ ... │ │
│ │ └─────┘ └─────┘ └─────┘ │ ││ └────────────────────────────────┘ │
│ Direct interoperability │
│ ┌────────────────────────────────┐ │
│ │ Node Subnet │ │
│ │ ┌─────┐ ┌─────┐ ┌─────┐ │ │
│ │ │Node1│ │Node2│ │Node3│ ... │ │
│ │ └─────┘ └─────┘ └─────┘ │ │
│ └────────────────────────────────┘ │
└──────────────────────────────────────────┘
```

# # # 1.3 Technical features

| Features | Description |
|------|------|
| **IP allocation** | Container IP is allocated directly from the VPC subnet |
| **Network Interoperability** | Direct interoperability between containers and other resources in the VPC |
| **Routing** | Cross-node communication through VPC routing table |
| **Security Group** | Support security group and network ACL |

# # # 1.4 Advantages and Disadvantages

**Advantages:**
- Simple configuration and easy to understand
- Seamless interoperability with VPC resources
- Simple network strategy

**Disadvantages:**
- Container IP consumes VPC subnet IP
- IP resources are tight in large-scale clusters
- Average cross-node communication performance

# # # 1.5 Applicable scenarios

- Small cluster (number of nodes < 50)
- Traditional application migration
- Common applications that do not require high-performance networking

---

# # 2. Container tunnel network

# # # 2.1 Overview

The container tunnel network is based on VXLAN technology and establishes tunnels between nodes. The containers use independent container network segments and are isolated from the VPC network.

# # # 2.2 Architecture features

```
┌────────────────────────────────────────────
│ VPC Network ││ ┌────────────────────────────────┐ │
│ │ Node Subnet │ │
│ │ ┌─────┐ ┌─────┐ ┌─────┐ │ │
│ │ │Node1│ │Node2│ │Node3│ ... │ │
│ │ └──┬──┘ └──┬──┘ └──┬──┘ │ │
│ │ │ │ │ │ │
│ │ VXLAN Tunnel (Overlay Network) │ │
│ │ │ │ │ │ │
│ │ ┌──┴──┐ ┌──┴──┐ ┌──┴──┐ │ │
│ │ │Pod 1│ │Pod 2│ │Pod 3│ ... │ │
│ │ └─────┘ └─────┘ └─────┘ │ │
│ │ Independent container network segment │ │
│ └────────────────────────────────┘ │
└──────────────────────────────────────────┘
```

# # # 2.3 Technical features

| Features | Description |
|------|------|
| **IP allocation** | The container uses an independent container network segment (such as 172.16.0.0/16) |
| **Tunnel Technology** | Based on VXLAN, UDP port 4789 |
| **Network Isolation** | Container network and VPC network isolation |
| **Routing** | Cross-node communication through tunnels |

# # # 2.4 Advantages and Disadvantages

**Advantages:**
- The container IP is separated from the VPC IP and does not consume the VPC subnet.
- Support large-scale clusters (number of nodes > 1000)
- Good network isolation

**Disadvantages:**
- Requires additional VXLAN encapsulation/decapsulation, which has a certain performance overhead
- Configuration is relatively complex
- Intercommunication between containers and VPC resources requires additional configuration

# # # 2.5 Applicable scenarios- Large-scale cluster (number of nodes > 50)
- Multi-tenant environment
- Scenarios that require network isolation

---

# # 3. Cloud Native Network 2.0 (CCE Turbo)

# # # 3.1 Overview

Cloud Native Network 2.0 is the network mode of CCE Turbo cluster. Based on Huawei Cloud's self-developed container network technology, it provides high-performance and low-latency network capabilities.

# # # 3.2 Architecture features

```
┌────────────────────────────────────────────
│ VPC Network │
│ ┌────────────────────────────────┐ │
│ │ Node Subnet │ │
│ │ ┌─────┐ ┌─────┐ ┌─────┐ │ │
│ │ │Node1│ │Node2│ │Node3│ ... │ │
│ │ └──┬──┘ └──┬──┘ └──┬──┘ │ │
│ │ │ │ │ │ │
│ │ High performance network (ENI pass-through) │ │
│ │ │ │ │ │ │
│ │ ┌──┴──┐ ┌──┴──┐ ┌──┴──┐ │ │
│ │ │Pod 1│ │Pod 2│ │Pod 3│ ... │ │
│ │ └─────┘ └─────┘ └─────┘ │ │
│ │ Independent container subnet │ │
│ └────────────────────────────────┘ │
└──────────────────────────────────────────┘
```

# # # 3.3 Technical features

| Features | Description |
|------|------|| **IP allocation** | Containers use independent container subnets (such as 192.168.0.0/16) |
| **Network Technology** | Based on ENI (Elastic Network Adapter) pass-through, no VXLAN encapsulation |
| **Performance** | Close to physical machine network performance, extremely low latency |
| **Routing** | Direct routing through the VPC routing table, no tunnel required |

# # # 3.4 Advantages and Disadvantages

**Advantages:**
- High performance, close to physical machine network
- Low latency, suitable for real-time applications
- Support large-scale clusters (number of nodes > 1000)
- Separate container IP and VPC IP
- Simple configuration

**Disadvantages:**
- Requires specific instance specification support (such as c6s, c6sn, etc.)
- Some old specifications are not supported

# # # 3.5 Applicable scenarios

- Applications with high performance requirements (such as AI training, big data)
- Applications with low latency requirements (such as financial transactions, real-time games)
- Large scale clusters
- CCE Turbo cluster (recommended)

---

# # 4. Comparison of three network modes

| Comparison items | VPC network | Container tunnel network | Cloud native network 2.0 |
|--------|---------|-------------|--------------|
| **Network Technology** | VPC Routing | VXLAN Tunnel | ENI Passthrough |
| **Container IP source** | VPC subnet | Independent container network segment | Independent container subnet |
| **Cross-node communication** | VPC routing | VXLAN tunnel | VPC routing |
| **Performance** | Medium | Higher | Highest |
| **Latency** | Medium | Lower | Lowest |
| **Throughput** | Medium | High | Highest |
| **Supported scale** | < 50 nodes | > 1000 nodes | > 1000 nodes |
| **Configuration Complexity** | Low | Medium | Low |
| **Applicable clusters** | CCE | CCE | CCE Turbo |
| **Example Requirements** | No special requirements | No special requirements | Specific specifications required |

---

# # 5. Selection suggestions

# # # 5.1 Select by scene

| Scenario | Recommended network model |
|------|-------------|| Small cluster (<50 nodes) | VPC network |
| Traditional application migration | VPC network |
| Large-scale clusters (>100 nodes) | Container tunnel network or cloud native network 2.0 |
| High performance requirements (AI/big data) | Cloud native network 2.0 |
| Low latency requirements (finance/games) | Cloud native network 2.0 |
| Multi-tenant isolation | Container tunnel network |

# # # 5.2 Select by cluster type

| Cluster Types | Available Network Models |
|---------|-------------|
| CCE standard cluster | VPC network, container tunnel network |
| CCE Turbo Cluster | Cloud Native Network 2.0 (recommended) |

---

# # 6. Network mode switching

# # # 6.1 Notes

⚠️ **Important**: The network mode **cannot be modified** after the cluster is created. Please choose carefully when creating the cluster.

# # # 6.2 Migration plan

If you need to change the network mode, you need:
1. Create a new cluster (using target network mode)
2. Migrate the application to the new cluster
3. Switch traffic to the new cluster
4. Delete the old cluster

---

# # 7. Related documents

- [VPC Network](https://support.huaweicloud.com/usermanual-cce/cce_10_0282.html)
- [Cloud Native Network 2.0](https://support.huaweicloud.com/usermanual-cce/cce_10_0283.html)
- [Container Tunnel Network](https://support.huaweicloud.com/usermanual-cce/cce_10_0284.html)
- [CCE Security Group Configuration](./CCE_Security_Group_Configuration.md)