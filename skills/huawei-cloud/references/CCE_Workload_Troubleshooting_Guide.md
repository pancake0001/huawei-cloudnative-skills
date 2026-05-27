# 华为云 CCE 工作负载异常排查指南 / CCE Workload Troubleshooting Guide

**更新时间：2026-04-02 GMT+8**

**来源：华为云官方文档 https://support.huaweicloud.com/cce_faq/cce_faq_00134.html**

---

## 文档概述

本文档整理了华为云 CCE（云容器引擎）工作负载状态异常时的完整排查路径，包含所有相关链接和排查方向。可作为日常运维的问题定位指南。

---

## 定位流程

```
工作负载状态异常
       │
       ▼
   查看Pod状态 + 事件
       │
       ├─ Pending ──→ 调度失败 / 挂卷失败 / 添加存储失败
       ├─ ImagePullBackOff ──→ 拉取镜像失败
       ├─ CrashLoopBackOff ──→ 启动容器失败
       ├─ Evicted ──→ Pod被驱逐
       ├─ Creating ──→ 一直创建中
       ├─ Terminating ──→ 一直终止中
       ├─ Stopped ──→ 已停止
       └─ Running但不工作 → 配置问题
```

---

## 异常状态与排查链接

| 状态 | 说明 | 排查文档 |
|------|------|----------|
| **Pending** | 实例调度失败 | [实例调度失败](https://support.huaweicloud.com/cce_faq/cce_faq_00098.html) |
| **Pending** | 存储卷无法挂载 | [存储卷无法挂载](https://support.huaweicloud.com/cce_faq/cce_faq_00200.html) |
| **Pending** | 添加存储失败 | [添加存储失败](https://support.huaweicloud.com/cce_faq/cce_faq_00433.html) |
| **ImagePullBackOff** | 拉取镜像失败 | [实例拉取镜像失败](https://support.huaweicloud.com/cce_faq/cce_faq_00015.html) |
| **CrashLoopBackOff** | 启动容器失败 | [启动容器失败](https://support.huaweicloud.com/cce_faq/cce_faq_00018.html) |
| **Evicted** | Pod被驱逐 | [实例驱逐异常](https://support.huaweicloud.com/cce_faq/cce_faq_00209.html) |
| **Creating** | 一直创建中 | [一直处于创建中](https://support.huaweicloud.com/cce_faq/cce_faq_00140.html) |
| **Terminating** | 一直终止中 | [Pod Terminating](https://support.huaweicloud.com/cce_faq/cce_faq_00210.html) |
| **Stopped** | 已停止 | [已停止](https://support.huaweicloud.com/cce_faq/cce_faq_00012.html) |
| **Running** | 运行中但不工作 | [状态正常但未正常工作](https://support.huaweicloud.com/cce_faq/cce_faq_00471.html) |
| **Init:Error** | Init容器启动失败 | [Init容器启动失败](https://support.huaweicloud.com/cce_faq/cce_faq_00469.html) |

---

## 详细排查项

### 1. 实例调度失败

**链接**: https://support.huaweicloud.com/cce_faq/cce_faq_00098.html

**常见错误信息**:

| 错误信息 | 问题原因 |
|---------|----------|
| `no nodes available` | 集群无可用节点 |
| `Insufficient cpu/memory` | CPU/内存不足 |
| `volume node affinity conflict` | 存储卷与节点不在同一可用区 |
| `node(s) had taints` | Pod不满足污点容忍 |
| `Too many pods` | 节点Pod数量超限 |
| `everest driver not found` | everest插件异常 |
| `Thin Pool has xxxx free data blocks` | 节点存储空间不足 |

**排查子项**:

- 排查项一：集群内是否无可用节点
- 排查项二：节点资源（CPU、内存等）是否充足
- 排查项三：检查工作负载的亲和性配置
- 排查项四：挂载的存储卷与节点是否处于同一可用区
- 排查项五：检查Pod污点容忍情况
- 排查项六：检查临时卷使用量
- 排查项七：检查everest插件是否工作正常
- 排查项八：检查节点thinpool空间是否充足
- 排查项九：检查节点上调度的Pod是否过多
- 排查项十：kubelet静态绑核异常

---

### 2. 存储卷无法挂载

**链接**: https://support.huaweicloud.com/cce_faq/cce_faq_00200.html

| 存储类型 | 常见问题 | 解决方案 |
|---------|----------|----------|
| **EVS云硬盘** | 可用区不一致 | 确保磁盘与节点在同一可用区 |
| **EVS云硬盘** | 多实例挂载同一卷 | 副本数只能为1 |
| **EVS云硬盘** | 文件系统损坏 | 使用 fsck 修复 |
| **SFS Turbo** | 共享地址错误 | 检查PV中everest.io/share-export-location |
| **SFS Turbo** | 网络不通 | 测试节点到SFS Turbo网络 |
| **SFS通用版** | 未创建VPCEP | 在集群VPC创建VPC终端节点 |

---

### 3. 拉取镜像失败

**链接**: https://support.huaweicloud.com/cce_faq/cce_faq_00015.html

| 错误信息 | 问题原因 | 解决方案 |
|---------|----------|----------|
| `denied: You may not login yet` | 未配置imagePullSecret | 配置SWR密钥 |
| `no such host` | 镜像地址错误 | 检查镜像地址 |
| `no space left on device` | 节点磁盘不足 | 清理磁盘空间 |
| `certificate signed by unknown authority` | 仓库证书问题 | 使用可信证书或自签名 |
| `context canceled` | 镜像过大 | 优化镜像大小 |
| `request canceled` | 网络不通 | 检查网络/镜像仓库连通性 |
| `Too Many Requests` | Docker Hub限速 | 登录Docker Hub或使用SWR |

---

### 4. 启动容器失败

**链接**: https://support.huaweicloud.com/cce_faq/cce_faq_00018.html

| 退出码 | 问题原因 | 解决方案 |
|-------|----------|----------|
| exit(0) | 容器无持续进程 | 保持前台进程运行 |
| exit(137) | 健康检查失败 | 检查Liveness Probe配置 |
| - | 磁盘空间不足 | 清理thinpool空间 |
| - | OOM内存不足 | 增加Pod内存限制 |
| - | 端口冲突 | 检查容器端口配置 |
| - | Secret未Base64编码 | 对Secret值进行编码 |
| - | 架构不匹配(ARM/x86) | 使用匹配架构的镜像 |
| exit(141) | tail -f 不兼容 | 更换启动命令 |
| - | Java探针版本不兼容 | 升级/降级探针版本 |

---

### 5. Pod被驱逐 (Evicted)

**链接**: https://support.huaweicloud.com/cce_faq/cce_faq_00209.html

常见原因：节点资源超出限制（内存/CPU/磁盘）

---

### 6. Pod一直处于Terminating

**链接**: https://support.huaweicloud.com/cce_faq/cce_faq_00210.html

---

### 7. 状态正常但无法访问

**链接**: https://support.huaweicloud.com/cce_faq/cce_faq_00471.html

---

### 8. Init容器启动失败

**链接**: https://support.huaweicloud.com/cce_faq/cce_faq_00469.html

---

## 常用排查命令

```bash
# 查看Pod状态
kubectl get pod -n {namespace}

# 查看Pod详细事件
kubectl describe pod {pod-name} -n {namespace}

# 查看Pod日志
kubectl logs {pod-name} -n {namespace}

# 查看上一条日志（容器重启後）
kubectl logs {pod-name} -n {namespace} --previous

# 查看节点状态
kubectl get node

# 查看节点污点
kubectl describe node {node-name}

# 查看节点资源情况
kubectl describe node {node-name} | grep -A 5 "Allocated resources"

# 查看磁盘使用情况
df -h

# 查看节点上Pod数量
kubectl get pods -o wide | grep {node-ip}

# 查看OOM日志
grep -i oom /var/log/messages

# 进入容器调试
kubectl exec -it {pod-name} -n {namespace} -- /bin/sh
```

---

## Pod事件查看方法

### 方式一：控制台查看

1. 登录CCE控制台
2. 进入集群 → 工作负载
3. 点击工作负载名称
4. 找到异常实例 → 更多 → 事件

### 方式二：命令行查看

```bash
kubectl describe pod {pod-name} -n {namespace}
```

重点关注 Events 部分，常见事件类型：

| 事件 | 含义 |
|------|------|
| FailedScheduling | 调度失败 |
| SuccessfulCreatePod | Pod创建成功 |
| Pulling | 正在拉取镜像 |
| Pulled | 镜像拉取成功 |
| Created | 容器创建成功 |
| Started | 容器启动成功 |
| Killing | 正在终止容器 |
| BackOff | 容器启动失败，正在重试 |
| Unhealthy | 健康检查失败 |

---

## 相关文档

| 文档 | 链接 |
|------|------|
| 工作负载状态异常定位方法（主文档） | https://support.huaweicloud.com/cce_faq/cce_faq_00134.html |
| 登录容器方法 | https://support.huaweicloud.com/usermanual-cce/cce_10_00356.html |
| 集群可用但节点不可用 | https://support.huaweicloud.com/cce_faq/cce_faq_00120.html |
| 重置节点 | https://support.huaweicloud.com/usermanual-cce/cce_10_0003.html |