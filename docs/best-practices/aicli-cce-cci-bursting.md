# 基于 AICLI + Skill 实现 CCE 到 CCI 2.0 Bursting 的最佳实践

> 参考文档：[CCE 集群使用 CCI 2.0 实现弹性扩缩容](https://support.huaweicloud.com/bestpractice-cce/cce_bestpractice_0133.html#cce_bestpractice_0133__section12422713464)

## 1 场景概述

当 CCE 集群面临突发流量、资源临时不足时，可通过 CCI 2.0 Bursting 机制将 Pod 弹性调度到 CCI（云容器实例）的虚拟节点上运行，实现秒级扩容、无需预购节点。负载回落后 Pod 自动缩回 CCE 物理节点，CCI 资源释放，成本最优。

<!-- 图片位置：整体架构图 -->
**[图 1-1：CCE→CCI Bursting 架构示意图]**

核心流程：
1. CCE 集群安装 `virtual-kubelet` addon → 产生虚拟节点 `bursting-node`
2. Pod 携带 `bursting.cci.io/burst-to-cci: enforce` 标签 → 调度到虚拟节点 → 实际在 CCI 运行
3. CCI Pod 共享 CCE VPC 网络，通过 VPCEP 拉取 SWR 镜像

## 2 前置条件

### 2.1 集群要求

| 条件 | 说明 |
|---|---|
| 集群类型 | 支持 **CCE Standard VPC网络模式集群** 和 **CCE Turbo集群**。非VPC网络模式的集群不适用于该方案。 |
| 集群版本 | Kubernetes ≥ 1.19 |
| 节点余量 | VK addon 自身需 ~2C/4GB，建议集群有 ≥ 2 个物理节点，单节点可用 CPU ≥ 2C、内存 ≥ 4GB |
| VPC | 需有可用子网（ENI 子网 + VPCEP 子网） |

<!-- 图片位置：CCE Turbo 集群创建界面 -->
**[图 2-1：创建 Turbo/ENI 类型 CCE 集群]**

### 2.2 IAM 权限

| 权限 | 用途 |
|---|---|
| `cce:cluster:get` | 获取集群网络信息 |
| `cce:addon:create/update` | 安装/配置 virtual-kubelet |
| `vpcep:endpoint:create/list` | 创建 VPCEP 终端节点 |
| `vpc:subnet:list/routetable:list` | 查询子网和路由表 |
| `cci:*` | CCI 资源操作 |

### 2.3 IAM 委托

CCI bursting 需要以下委托：

| 委托 | 用途 | 说明 |
|---|---|---|
| `CCEAutoClusterAgency` | CCE 集群基础委托 | 集群创建时自动生成 |
| `CCEBurstingAgency` | CCI bursting 专用委托 | 需授权 CCI、VPC、SWR 相关权限，通常由 CCE 自动创建 |

<!-- 图片位置：IAM 委托配置界面 -->
**[图 2-2：IAM 委托 CCEBurstingAgency 配置]**

### 2.4 环境准备

```bash
# 安装 hcloud CLI
# 参考：https://support.huaweicloud.com/cli/index.html

# 配置 AK/SK 环境变量（不要明文写在代码或配置文件中）
export HUAWEI_AK=<your-ak>
export HUAWEI_SK=<your-sk>
export HUAWEI_PROJECT_ID=<your-project-id>   # 重要！addon 需要此参数

# 安装 AICLI 和 huawei-cloud-cce-cci-bursting-deployer skill
# 参考 skill 安装文档
```

<!-- 图片位置：AICLI skill 安装界面 -->
**[图 2-3：AICLI 安装 bursting skill]**

## 3 操作步骤

### 步骤 1：Precheck——检查集群和网络状态

使用 AICLI 告诉 skill 你的集群信息，skill 会自动执行预检：

```
用户：帮我在 cn-north-4 的 turbo-cluster 上配置 CCI bursting

AICLI 自动执行：
  huawei_precheck_cce_cci_bursting region=cn-north-4 cluster_id=<cluster-id>
```

Precheck 会检查：
- ✅ 集群是否 Turbo/ENI 类型
- ✅ VPC 和子网信息（自动识别 ENI 子网和 VPCEP 子网）
- ✅ addon 是否已安装
- ✅ 节点资源余量
- ⚠️ 如有 blocking issues，会列出并给出修复建议

<!-- 图片位置：precheck 输出结果 -->
**[图 3-1：Precheck 输出结果——集群网络信息与问题列表]**

> **⚠️ 重要：子网 ID 类型区分**
>
> CCI subnet ID（Neutron UUID）和 VPCEP subnet ID（VPC UUID）是**不同类型**的 ID，千万不要互换！
> - `cci_subnet_id`：从 `spec.eni_network` 获取，用于 addon 的 `networkID/subnet_id` 参数
> - `vpcep_subnet_id`：VPC 子网 UUID，用于 VPCEP 终端节点的 `subnet_id` 参数

<!-- 图片位置：两种 subnet ID 的区别 -->
**[图 3-2：CCI subnet 与 VPCEP subnet ID 类型区别]**

### 步骤 2：确保节点资源充足

如果 precheck 发现节点资源不足，**必须先扩容节点**，否则 VK addon 无法启动。

```
用户：当前节点只有 2C/4GB，不够用

AICLI 自动执行节点池扩容：
  创建节点池：c6ne.xlarge.2 (4C/8GB) × 2，SSH keypair 认证
```

> **💡 经验：优先使用 SSH keypair 而不是密码认证**
>
> CCE API 对密码有 SHA-512 加密要求，通过 hcloud CLI 传明文密码可能被拒绝。
> 建议先在 ECS 创建 SSH keypair，然后用 keypair 创建节点池。

<!-- 图片位置：节点池创建界面 -->
**[图 3-3：创建 SSH keypair 和节点池]**

### 步骤 3：创建 VPCEP 终端节点

CCI Pod 需要通过 VPCEP（VPC Endpoint）访问 SWR 拉取镜像、访问 OBS 拉取镜像层。必须创建以下 VPCEP：

| VPCEP | 类型 | 用途 | 是否必须 |
|---|---|---|---|
| SWR（容器镜像仓库） | interface | CCI Pod 拉取 SWR 镜像 | ✅ 必须 |
| SWR-API（镜像仓库 API） | interface | CCI 认证/获取镜像元数据 | ✅ 必须 |
| OBS（对象存储） | gateway / cvs_gateway | CCI 拉取镜像层（blob） | ✅ 必须 |

```
用户：创建 VPCEP 终端节点

AICLI 先 preview，用户确认后再 apply：
  huawei_ensure_cce_cci_vpcep region=cn-north-4 cluster_id=<cluster-id> confirm=true
```

<!-- 图片位置：VPCEP 创建结果 -->
**[图 3-4：VPCEP 终端节点创建——SWR + SWR-API + OBS]**

> **⚠️ OBS VPCEP service name 不要猜**
>
> OBS gateway VPCEP 的 `endpoint_service_name` 是租户+区域专属的（如 `cn-north-4.com.myhuaweicloud.v4.obsv2.lz11`），**不要从其他区域或公共 service name 推断**。
> 如果 precheck 报 OBS 信息缺失，需要通过华为云服务工单获取准确的 service name。
> 
> 替代方案：部分区域支持 `cvs_gateway` 类型 OBS VPCEP，service name 更稳定，优先尝试。

<!-- 图片位置：OBS VPCEP endpoint service name -->
**[图 3-5：OBS VPCEP endpoint service name 获取方式]**

### 步骤 4：安装并配置 virtual-kubelet addon

```
用户：安装 VK addon

AICLI 先 preview，用户确认后 apply：
  huawei_setup_cce_cci_bursting region=cn-north-4 cluster_id=<cluster-id> confirm=true
```

Skill 会自动：
1. 确保 VPCEP 已创建
2. 安装 `virtual-kubelet` addon（如已存在则更新配置）
3. 配置 CCI 网络参数（`cci_subnet_id`、`region`、`PROJECT_ID`）

<!-- 图片位置：addon 安装界面 -->
**[图 3-6：virtual-kubelet addon 安装配置]**

> **⚠️ 关键配置参数**
>
> | 参数 | 正确值 | 易错值 | 说明 |
> |---|---|---|---|
> | `region` | `northchina`（cn-north-4） | `southchina` | region 到 addon region 的映射必须正确 |
> | `PROJECT_ID` | 项目 ID（32位 hex） | 空/默认值 | 必须填写，否则 CCI IAM 认证失败 |
> | `enableBurstingNode` | `"true"` | `"false"`（默认） | addon 默认 false，必须改为 true 才会出现 virtual node |
>
> **Region 映射表**：
> | 华为云区域 | addon region 参数 |
> |---|---|
> | cn-north-1 / cn-north-4 | `northchina` |
> | cn-east-2 / cn-east-3 | `eastchina` |
> | cn-south-1 / cn-south-2 | `southchina` |
> | cn-north-9 | `northeastchina` |
> | cn-southwest-2 | `southwestchina` |

<!-- 图片位置：addon 配置参数 -->
**[图 3-7：virtual-kubelet addon 关键参数配置]**

### 步骤 5：验证 virtual node 就绪

```
用户：验证 bursting 是否就绪

AICLI 自动执行：
  huawei_verify_cce_cci_bursting region=cn-north-4 cluster_id=<cluster-id>
```

期望结果：
- addon 状态：`running`
- virtual node `bursting-node` 状态：`Ready`
- allocatable：CPU ~200k, memory ~1600000Gi, pods ~200k（虚拟节点资源不受物理限制）

<!-- 图片位置：virtual node Ready 状态 -->
**[图 3-8：bursting-node Ready——virtual-kubelet 就绪]**

> **排查清单（如果 virtual node NotReady）**：
>
> | 症状 | 可能原因 | 修复 |
> |---|---|---|
> | addon pod Pending | 节点资源不足 | 扩容节点池 |
> | addon pod Running 但 node NotReady | region 配置错误 | 对照映射表修正 region |
> | addon 日志报 IAM/project denied | PROJECT_ID 缺失 | 设置 HUAWEI_PROJECT_ID |
> | 没有 virtual node 出现 | enableBurstingNode=false | patch ConfigMap 改为 true |
> | duplicate deployment | addon 多次重装残留 | 清理旧 ReplicaSet |

### 步骤 6：冒烟测试——部署 Pod 到 CCI

```
用户：部署冒烟测试到 CCI

AICLI 先 preview，用户确认后 apply：
  huawei_deploy_cce_cci_smoke_workload region=cn-north-4 cluster_id=<cluster-id> confirm=true
```

Skill 会自动创建 Deployment，携带 `bursting.cci.io/burst-to-cci: enforce` 标签，强制调度到 bursting-node。

<!-- 图片位置：冒烟 Deployment YAML -->
**[图 3-9：冒烟测试 Deployment 配置]**

> **⚠️ 镜像选择——最容易踩坑的环节**
>
> CCI Pod 通过 VPCEP 从 SWR 拉取镜像，**必须使用区域 SWR 镜像**，不要用 Docker Hub 镜像。
>
> 更重要：**优先使用你自有 SWR namespace 的镜像**！公共 namespace（如 `library`、`hwofficial`）的镜像在通过 VPCEP 拉取时可能认证不通。
>
> 推荐做法：
> 1. Skill 自动通过 `ListNamespaces` → `ListReposDetails` 发现用户 SWR 仓库
> 2. 选择用户 namespace 下有长期运行进程的镜像（如 `openclaw-sandbox`）
> 3. 不要用一次性进程镜像（如 `aicli`，跑完退出会 CrashLoopBackOff）
>
> ```yaml
> # ✅ 正确——用户自有 namespace 镜像
> image: swr.cn-north-4.myhuaweicloud.com/pancake/openclaw-sandbox:latest
> 
> # ✅ 正确——hwofficial addon 镜像（物理节点上可用）
> image: swr.cn-north-4.myhuaweicloud.com/hwofficial/coredns:1.30.67
> 
> # ❌ 可能失败——公共 library 镜像（CCI VPCEP 认证可能不通）
> image: swr.cn-north-4.myhuaweicloud.com/library/nginx:stable-alpine
> 
> # ❌ 超时——Docker Hub 镜像（CCI 没有公网出口）
> image: nginx:latest
> ```

<!-- 图片位置：镜像拉取成功/失败对比 -->
**[图 3-10：用户自有 SWR 镜像 vs 公共 SWR 镜像拉取对比]**

### 步骤 7：最终验证

```
用户：确认冒烟测试 Pod Running

AICLI 执行：
  huawei_verify_cce_cci_bursting region=cn-north-4 cluster_id=<cluster-id> \
    namespace=cci2-burst-lab workload_name=cci2-burst-demo
```

期望结果：
- Pod 状态：`Running (1/1)`
- Pod 节点：`bursting-node`
- Pod IP：CCE VPC 子网内 IP（如 `192.168.0.84`）

<!-- 图片位置：最终验证 Pod Running -->
**[图 3-11：冒烟测试 Pod Running 在 bursting-node 上]**

## 4 生产环境工作负载配置

冒烟测试通过后，将生产工作负载配置为弹性调度到 CCI：

### 4.1 强制调度模式（enforce）

Pod 始终运行在 CCI，适合低延迟、短周期任务：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: burst-workload
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: burst-workload
  template:
    metadata:
      labels:
        app: burst-workload
        bursting.cci.io/burst-to-cci: enforce    # 关键标签！
    spec:
      containers:
        - name: app
          image: swr.cn-north-4.myhuaweicloud.com/pancake/openclaw-sandbox:latest
          resources:
            requests:
              cpu: "1"
              memory: "2Gi"
            limits:
              cpu: "2"
              memory: "4Gi"
```

### 4.2 弹性调度模式（优先 CCE，资源不足时弹到 CCI）

结合 HPA + bursting，实现真正的弹性伸缩：

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: burst-workload-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: burst-workload
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

> CCE 物理节点资源不足时，HPA 扩出的新副本会自动调度到 bursting-node（CCI），无需 enforce 标签。

<!-- 图片位置：HPA + bursting 弹性伸缩流程 -->
**[图 4-1：HPA + CCI Bursting 弹性伸缩流程]**

### 4.3 CCI Bursting 资源限制

| 限制项 | 值 | 说明 |
|---|---|---|
| 单 Pod CPU | ≤ 32C | CCI 单实例最大规格 |
| 单 Pod 内存 | ≤ 256Gi | CCI 单实例最大规格 |
| Pod 存储 | ephemeral disk 最多 10Gi | CCI 临时存储，Pod 重建后丢失 |
| Pod 网络 | 共享 CCE VPC 子网 | CCI Pod IP 与 CCE Pod 在同一子网 |
| 支持的工作负载 | Deployment、StatefulSet、Job、CronJob | 适用于短时高负载或弹性任务类场景 |
| 暂不支持 | DaemonSet | 守护进程类工作负载不适合弹性到 CCI |
| 存储约束 | 云存储卷能力受 Kubernetes、CCI、调度器版本约束 | 使用 PVC、VolumeAttributesClass 等能力前，请先在测试环境验证并参考官方约束 |

## 5 故障排查速查表

| 症状 | 可能原因 | 修复方法 |
|---|---|---|
| addon pod Pending | 节点资源不足 | 扩容节点池（≥ 2C/4GB 余量） |
| addon pod CrashLoopBackOff | region/PROJECT_ID 配置错误 | 检查 addon 参数：region 对应映射表，PROJECT_ID 非空 |
| virtual node NotReady | enableBurstingNode=false | `kubectl patch cm bursting-status -n kube-system -p '{"data":{"enableBurstingNode":"true"}}'` |
| virtual node NotReady | CCEBurstingAgency 缺失 | 在 IAM 控制台创建/检查委托 |
| 没有 virtual node 出现 | addon 未安装或异常 | 检查 addon 状态：`kubectl get pods -n kube-system -l app=bursting-cceaddon-vk` |
| CCI Pod ImagePullBackOff | SWR/SWR-API VPCEP 未创建 | 创建 interface VPCEP for SWR + SWR-API |
| CCI Pod ImagePullBackOff | OBS VPCEP 未创建/失败 | 创建 gateway/cvs_gateway VPCEP for OBS |
| CCI Pod ImagePullBackOff | 使用了公共 namespace 镜像 | 换成用户自有 SWR namespace 镜像 |
| CCI Pod ImagePullBackOff | 使用了 Docker Hub 镜像 | 换成区域 SWR 镜像 |
| duplicate deployment | addon 多次重装残留 | 清理旧 ReplicaSet |
| 节点池创建密码被拒 | CCE SHA-512 密码加密要求 | 使用 SSH keypair 认证 |
| OBS gateway VPCEP 创建失败 | service name 不匹配 | 获取租户专属 service name（提工单），或改用 cvs_gateway 类型 |

<!-- 图片位置：故障排查流程图 -->
**[图 5-1：CCI Bursting 故障排查流程图]**

## 6 AICLI + Skill 一键部署命令参考

以下为完整的 AICLI 交互流程（用户只需确认即可）：

```
# Step 1: 预检
> 帮我在 cn-north-4 的 turbo-cluster 上配置 CCI bursting

# Step 2: 扩容节点（如需要）
> 当前节点资源不足，先扩容到 4C/8GB × 2 节点

# Step 3: 创建 VPCEP（preview → confirm）
> 创建 SWR 和 OBS 的 VPCEP 终端节点，确认执行

# Step 4: 安装 VK addon（preview → confirm）
> 安装 virtual-kubelet addon，确认执行

# Step 5: 验证就绪
> 验证 bursting 是否就绪

# Step 6: 冒烟测试（preview → confirm）
> 用我 SWR 上的镜像部署冒烟测试到 CCI，确认执行

# Step 7: 最终验证
> 确认冒烟 Pod Running
```

Skill 在每一步 mutation 操作前都会 preview，用户确认后才 apply，确保安全可控。

## 7 成本与计费说明

| 计费项 | 说明 |
|---|---|
| CCI Pod 运行 | 按 Pod 规格（CPU/内存）和运行时长计费，秒级计费 |
| VPCEP 终端节点 | interface VPCEP 按小时计费，gateway VPCEP 按流量计费 |
| CCE 集群/节点 | 按节点规格和时长计费（不变） |
| SWR 镜像存储 | 公共镜像免费，私有镜像按存储量计费 |

**成本优化建议**：
- 突发流量用 enforce 模式弹到 CCI，流量回落自动释放，无需预留节点
- VPCEP 终端节点常驻费用较低（~0.1 元/小时/节点），长期保留不影响成本
- HPA minReplicas 设为 CCE 物理节点可承载的值，超出部分才弹到 CCI

## 8 参考链接

- [CCE 集群使用 CCI 2.0 实现弹性扩缩容（最佳实践）](https://support.huaweicloud.com/bestpractice-cce/cce_bestpractice_0133.html)
- [CCI 2.0 用户指南——网络配置](https://support.huaweicloud.com/usermanual-cci2/cci_01_0005.html)
- [CCI 镜像拉取 FAQ](https://support.huaweicloud.com/cci_faq/cci_faq_0095.html)
- [VPC Endpoint 用户指南](https://support.huaweicloud.com/vpcep/index.html)
- [CCE 集群管理——Addon 管理](https://support.huaweicloud.com/usermanual-cce/cce_01_0133.html)
