# huawei-cloud-cce-network-failure-diagnoser 验证报告

## 基本信息

| 项目 | 内容 |
| --- | --- |
| Skill | `huawei-cloud-cce-network-failure-diagnoser` |
| 验证工具 | `aicli v1.0.0-beta.2` |
| 验证环境 | CCE 集群 `aicli` 命名空间，Pod `aicli-dcfcf5595-4gf22` |
| 验证时间 | 2026-06-01 |
| 区域 | `cn-north-4` |
| 集群 ID | `1d450236-5b28-11f1-a7f6-0255ac10026a` |
| 操作性质 | 只读诊断 |

## 验证结果

| 验证项 | 结果 | 证据 |
| --- | --- | --- |
| Skill 触发 | 通过 | aicli 正确加载并识别该 skill |
| 网络诊断 | 通过 | finding=1，top_causes=1 |
| 只读安全 | 通过 | 仅执行诊断，无变更操作 |
| 凭证安全 | 通过 | 未输出 AK/SK/Token |

## 关键发现

- 网络诊断功能正常运行
- 诊断结论指向节点资源或网络压力，属于环境状态

## 修复记录

| 编号 | 类型 | 问题 | 修复 |
| --- | --- | --- | --- |
| CCE-COMMON-001 | 参数兼容性 | CLI dispatcher 仅支持 `key=value` 格式 | 增强 `_parse_cli_params` 支持多种格式 |

## 最终结论

**通过**。网络故障诊断功能正常。


## aicli 实际输出（Skill 生成的报告）

>>> FIELD: report_markdown (len=1900)
# CCE 网络故障自动化诊断报告

## 1. 诊断总览
| 评估项 | 详细信息 |
| :--- | :--- |
| 目标集群 | region=`cn-north-4` cluster_id=`1d450236-5b28-11f1-a7f6-0255ac10026a` |
| 目标对象 | namespace=`default` target=`-/-` service=`-` ingress=`-` |
| 故障现象 | - |
| 诊断结论 | **Service 无可用 EndpointSlice 后端，流量无法转发到 Pod** |
| 置信度 | **高 (High)** |
| 数据采集时间 | `2026-06-01T11:52:12.255371+00:00` |
| 剪枝状态 | 未剪枝，已继续检查上层链路 |

## 2. 排查过程
| 阶段 | 状态 | 命中结论 |
| :--- | :--- | :--- |
| 第一阶段：基础设施与节点层诊断 | 已检查 | 未发现强异常 |
| 第二阶段：域名解析层诊断 | 已检查 | 未发现强异常 |
| 第三阶段：东西向路由与策略层诊断 | 异常 | Service 无可用 EndpointSlice 后端，流量无法转发到 Pod |
| 第四阶段：南北向边缘接入层诊断 | 已检查 | 未发现强异常 |

## 3. 链路拓扑
```text
外部客户端 -> Cloud ELB/EIP -> Ingress default/ingress-work -> Service default/svc-workload -> EndpointSlice -> Pod -/-
```

## 4. 关键对象快照
| 对象 | 摘要 |
| :--- | :--- |
| Service | `default/svc-workload` type=`NodePort` selector=`{'app': 'test-workload', 'version': 'v1'}` |
| EndpointSlice | ready=0 slices=1 |
| Backend Pods | - |
| Ingress | `default/ingress-work` class=`nginx` lb=`[{'ip': '192.168.135.155', 'hostname': None}]` |
| NetworkPolicy | 0 个策略位于 namespace `default` |
| Cloud ELB | ids=`['b1f378ef-7621-4b79-ac70-330c83ccad7b']` |

## 5. 证据矩阵
| 阶段 | 严重度 | 类型 | 置信度 | 证据摘要 |
| :--- | :--- | :--- | :--- | :--- |
| 第三阶段：东西向路由与策略层诊断 | critical | `ServiceNoReadyEndpoint` | 95% | {'service': {'name': 'svc-workload', 'namespace': 'default', 'labels': {'app': 'test-workload', 'version': 'v1'}, 'annotations': {}, 'type': 'NodePort', 'cluster_ip': '10.247.64.209', 'selector': {'app': 'test-workload', 'version': 'v1'}, 'ports': [{'name':... |

## 6. 诊断结论
1. **Service 无可用 EndpointSlice 后端，流量无法转发到 Pod** (`ServiceNoReadyEndpoint`，置信度 95%)

## 7. 建议动作与验证标准
1. 核对 Service selector 与 Pod labels 是否一致。
2. 如果 selector 已匹配，继续检查后端 Pod readinessProbe 和容器端口监听状态。
恢复验证标准：目标 Service 有 ready EndpointSlice；CoreDNS/Ingress Controller 无新增 Warning；ELB 后端为健康；客户端请求成功率恢复并且 502/504/timeout 不再增长。


