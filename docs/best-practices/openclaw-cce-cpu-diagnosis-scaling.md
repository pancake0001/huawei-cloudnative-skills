# 最佳实践：使用OpenClaw诊断应用CPU上涨并扩容

## 应用场景

生产环境中，应用CPU使用率突然上涨是常见的问题。通过OpenClaw Agent对接 `observability-context-builder`、`pod-failure-diagnoser`、`root-cause-analyzer` 和 `auto-remediation-runner` Skill，可以实现：

- 自动汇聚多源可观测数据（告警、指标、日志、事件）
- 综合分析定位CPU上涨根因
- 一键执行扩容恢复（预览 + 确认机制）
- 验证扩容效果并输出诊断报告

本实践以 **order-service 应用CPU使用率从35%上涨至87%** 为例，演示完整的诊断和恢复流程。

## 前提条件

- CCE集群中已部署目标应用（本例为 `order-service`）。
- 已配置AOM告警规则（CPU使用率 > 80% 触发告警）。
- OpenClaw Agent已完成云原生Skill注册。
- Agent有权限执行工作负载扩缩容操作。
- 应用已配置Resource Limit（建议设置，便于诊断）。

## 涉及的Skill

| Skill名称 | 功能说明 |
|-----------|---------|
| `observability-context-builder` | 汇聚AOM告警、LTS日志、K8s Events、Pod/Node指标 |
| `pod-failure-diagnoser` | 分析Pod运行状态、容器日志、Events |
| `root-cause-analyzer` | 综合多源证据进行跨域根因分析 |
| `auto-remediation-runner` | 执行受控恢复动作（扩容、cordon等），默认预览模式 |

## 操作步骤

### 步骤1：向Agent描述问题

在OpenClaw对话中，输入自然语言描述问题：

```
我的order-service应用CPU使用率一直在涨，现在87%了，帮我看看是什么原因
```

Agent接收到问题后，会自动触发 `observability-context-builder` 和 `root-cause-analyzer` Skill，开始诊断流程。

### 步骤2：Agent自动收集可观测数据

Agent调用 `observability-context-builder` Skill，并行收集以下数据：

1. **AOM告警**：查询与该应用相关的活跃告警和历史告警。
2. **AOM指标**：查询CPU、内存、网络、磁盘等指标的时间序列数据。
3. **K8s Events**：查询该命名空间下的Warning和Normal事件。
4. **Pod指标**：查询TopN Pod的CPU和内存使用率。

收集到的上下文数据示例：

```json
{
  "timestamp": "2026-05-31T14:23:24Z",
  "scope": {
    "cluster": "prod-web-cluster",
    "namespace": "default",
    "deployment": "order-service"
  },
  "alarms": [
    {
      "name": "HighCPUUsage",
      "severity": "warning",
      "metric": "container_cpu_usage_seconds_total",
      "current_value": "87%",
      "threshold": "80%",
      "duration": "10m"
    }
  ],
  "metrics": {
    "cpu_usage": {
      "current": "87%",
      "1h_ago": "35%",
      "trend": "rising"
    },
    "memory_usage": {
      "current": "62%",
      "trend": "stable"
    },
    "network_in": {
      "current": "45MB/s",
      "1h_ago": "12MB/s",
      "trend": "rising"
    },
    "network_out": {
      "current": "38MB/s",
      "1h_ago": "10MB/s",
      "trend": "rising"
    }
  },
  "events": [
    {
      "time": "14:15:00",
      "type": "Warning",
      "reason": "HighCpuUsage",
      "message": "Pod order-service-7d9f4b8c5-x2 cpu usage high"
    }
  ],
  "logs": {
    "recent_errors": 0,
    "traffic_pattern": "increased_request_rate",
    "qps": {
      "current": 1250,
      "baseline": 400
    }
  }
}
```

### 步骤3：分析Pod运行状态

Agent调用 `pod-failure-diagnoser` Skill，分析Pod运行状态：

1. 查询Deployment的Pod列表和状态。
2. 查看容器日志（包括当前日志和previous日志）。
3. 查看Pod的Events。

Pod状态分析结果：

| Pod名称 | 状态 | CPU | 内存 | 重启次数 | 备注 |
|---------|------|-----|------|---------|------|
| order-service-7d9f4b8c5-x2 | Running | 92% | 55% | 0 | - |
| order-service-7d9f4b8c5-a1 | Running | 85% | 58% | 0 | - |
| order-service-7d9f4b8c5-b3 | Running | 84% | 60% | 0 | - |

容器日志关键信息：

```
[INFO] Request rate increased: 1250 req/s
[INFO] Processing checkout requests...
[INFO] No errors detected
```

### 步骤4：分析网络链路

Agent调用 `network-failure-diagnoser` Skill，检查网络链路：

1. 查询Service配置和后端状态。
2. 查询Ingress和ELB配置。
3. 查询ELB流量指标。

网络链路分析结果：

| 指标 | 当前值 | 基线值 | 变化 |
|------|--------|--------|------|
| 入流量(QPS) | 1250 | 400 | +212% |
| 出流量 | 38MB/s | 10MB/s | +280% |
| 连接数 | 850 | 300 | +183% |
| 响应时间(P99) | 450ms | 200ms | +125% |

ELB后端状态：3/3 健康。无网络异常，流量正常转发。

### 步骤5：根因分析

Agent调用 `root-cause-analyzer` Skill，综合以上数据进行根因分析：

**根因定位结果**：

| 根因 | 置信度 | 证据 |
|------|--------|------|
| **流量突增导致CPU上涨** | 95% | QPS从400升至1250，CPU同步从35%升至87% |
| 内存泄漏 | 已排除 | 内存使用率稳定62%，无增长趋势 |
| 应用异常 | 已排除 | 日志无错误，无异常重启 |
| 网络问题 | 已排除 | ELB后端健康，流量转发正常 |
| 版本问题 | 已排除 | 无近期发布记录 |

**证据链**：

1. `[14:10]` 流量开始上升，QPS从400升至800。
2. `[14:15]` CPU使用率突破60%，触发AOM告警。
3. `[14:20]` 流量继续攀升至1250 QPS。
4. `[14:23]` CPU使用率达到87%，告警升级。

### 步骤6：Agent输出诊断结论

Agent向用户呈现分析结果和建议操作：

**诊断结论**：

- **根因**：外部流量大幅增加，当前3个Pod的处理能力接近瓶颈。
- **关键数据**：
  - CPU使用率：87%（1小时前为35%）
  - 请求QPS：1250（基线400，上涨212%）
  - 网络入流量：45MB/s（上涨275%）

**建议操作**：

1. 扩容Pod副本数至6个，降低单Pod负载。
2. 检查流量来源，确认是否为正常业务流量。
3. 考虑配置HPA自动扩缩容，应对未来流量波动。

### 步骤7：执行扩容（预览 + 确认）

用户确认执行扩容后，Agent调用 `auto-remediation-runner` Skill，进入预览模式：

**变更预览**：

| 属性 | 当前值 | 目标值 | 变化 |
|------|--------|--------|------|
| 副本数 | 3 | 6 | +3 (+100%) |
| 单Pod CPU请求 | 500m | 500m | 不变 |
| 单Pod CPU限制 | 2000m | 2000m | 不变 |
| 总CPU请求 | 1500m | 3000m | +1500m |
| 总CPU限制 | 6000m | 12000m | +6000m |

**风险评估**：

- 风险等级：R3（低风险变更）
- 影响范围：order-service Deployment
- 回滚方式：可随时缩容回3个副本

用户确认后，Agent执行扩容：

```bash
# Agent内部调用
python scripts/huawei-cloud.py huawei_scale_cce_workload \
  region=cn-north-4 \
  cluster_id=your-cluster-id \
  workload_type=deployment \
  name=order-service \
  namespace=default \
  replicas=6
```

扩容执行日志：

```
[14:24:05] 开始执行扩容: order-service 3 -> 6
[14:24:06] 新Pod创建中...
[14:24:15] Pod order-service-xxx-c4 状态变为: Running
[14:24:16] Pod order-service-xxx-d5 状态变为: Running
[14:24:17] Pod order-service-xxx-e6 状态变为: Running
[14:24:18] 扩容完成，当前副本: 6/6 Ready
```

### 步骤8：验证扩容效果

Agent自动验证扩容效果：

扩容后Pod状态：

| Pod名称 | 状态 | CPU | 内存 | 类型 |
|---------|------|-----|------|------|
| order-service-7d9f4b8c5-x2 | Running | 42% | 55% | 旧 |
| order-service-7d9f4b8c5-a1 | Running | 41% | 58% | 旧 |
| order-service-7d9f4b8c5-b3 | Running | 40% | 60% | 旧 |
| order-service-xxx-c4 | Running | 39% | 52% | 新 |
| order-service-xxx-d5 | Running | 38% | 54% | 新 |
| order-service-xxx-e6 | Running | 38% | 53% | 新 |

效果对比：

| 指标 | 扩容前 | 扩容后 | 改善 |
|------|--------|--------|------|
| 平均CPU | 87% | 40% | -47% |
| 平均内存 | 58% | 55% | -3% |
| P99响应时间 | 450ms | 220ms | -51% |
| 单Pod QPS | 417 | 208 | -50% |

## 预期结果

完成上述操作后：

1. **CPU使用率下降**：从87%降至40%，恢复至安全范围。
2. **响应时间改善**：P99响应时间从450ms降至220ms。
3. **系统稳定性恢复**：单Pod负载降低，避免因CPU过高导致的请求超时或OOM。

完整诊断和恢复流程耗时统计：

| 阶段 | 耗时 | 关键操作 |
|------|------|---------|
| 问题描述 | 5秒 | 用户输入自然语言描述 |
| 数据收集 | 6秒 | 收集告警、指标、日志、事件 |
| Pod分析 | 3秒 | 分析Pod状态和容器日志 |
| 网络分析 | 3秒 | 检查Service/Ingress/ELB流量 |
| 根因定位 | 2秒 | 综合分析输出根因 |
| 扩容执行 | 13秒 | 预览 -> 确认 -> 执行 -> 验证 |
| **总计** | **32秒** | **从告警到恢复** |

## 约束与限制

- `auto-remediation-runner` 默认预览模式，不会自动执行变更，必须经过用户确认。
- 扩容操作受集群资源限制，如果节点资源不足，新Pod可能处于Pending状态。
- 建议在非高峰时段执行扩容操作，避免对业务造成影响。
- 如果根因不是流量上涨（如内存泄漏、代码异常），扩容只能临时缓解，需要进一步排查。

## 后续操作

- **配置HPA**：建议为应用配置HPA（Horizontal Pod Autoscaler），设置CPU目标利用率为70%，副本范围3-10，实现自动扩缩容。
- **优化应用性能**：如果单Pod处理能力不足，可以考虑优化代码热点、增加缓存层、优化数据库查询等。
- **监控流量来源**：持续监控流量来源，确认是否为正常业务流量，排除爬虫或异常请求。

## 相关文档

- [Skill参考 - observability-context-builder](../skill-reference.md#331-observability-context-builder)
- [Skill参考 - pod-failure-diagnoser](../skill-reference.md#341-pod-failure-diagnoser)
- [Skill参考 - root-cause-analyzer](../skill-reference.md#346-root-cause-analyzer)
- [Skill参考 - auto-remediation-runner](../skill-reference.md#347-auto-remediation-runner)
- 华为云CCE用户指南 - 工作负载伸缩
