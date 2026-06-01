# huawei-cloud-cce-dependency-impact-analyzer 验证报告

## 基本信息

| 项目 | 内容 |
| --- | --- |
| Skill | `huawei-cloud-cce-dependency-impact-analyzer` |
| 验证工具 | `aicli v1.0.0-beta.2` |
| 验证环境 | CCE 集群 `aicli` 命名空间，Pod `aicli-dcfcf5595-4gf22` |
| 验证时间 | 2026-06-01 |
| 区域 | `cn-north-4` |
| 集群 ID | `1d450236-5b28-11f1-a7f6-0255ac10026a` |
| 操作性质 | 只读分析 |

## 验证结果

| 验证项 | 结果 | 证据 |
| --- | --- | --- |
| Skill 触发 | 通过 | aicli 正确加载并识别该 skill |
| 依赖影响分析 | 通过 | 风险等级 Medium，path_count=1 |
| 只读安全 | 通过 | 仅执行分析，无变更操作 |
| 凭证安全 | 通过 | 未输出 AK/SK/Token |

## 关键发现

- 依赖影响分析正常运行，正确识别了依赖链路
- 目标 workload 存在 Evicted 历史 Pod，属于环境状态

## 修复记录

| 编号 | 类型 | 问题 | 修复 |
| --- | --- | --- | --- |
| CCE-COMMON-001 | 参数兼容性 | CLI dispatcher 仅支持 `key=value` 格式 | 增强 `_parse_cli_params` 支持多种格式 |

## 最终结论

**通过**。依赖影响分析功能正常。


## aicli 实际输出（Skill 生成的报告）

>>> REPORT: report_markdown (len=3688)
# CCE 依赖影响面分析报告

## 1. 分析摘要

- Analysis-Trace-ID: `DIA-20260601115941-8deb8296`
- 集群: `1d450236-5b28-11f1-a7f6-0255ac10026a`
- 区域: `cn-north-4`
- 命名空间: `default`
- 目标对象: `abclient`
- 风险等级: `Medium`，评分 `55/100`
- 初步结论: 目标 Pod 部分不可用，影响范围取决于副本和流量分布。

## 2. 排查过程

1. 拉取 Pod、Service、Ingress、Node 当前快照，构建命名空间内服务拓扑。
2. 按目标名称或 label selector 定位目标 Pod，并识别 Ready/异常副本。
3. 用 Service selector 反查上游服务，再从 Ingress backend 反查外部入口。
4. 生成故障传播路径、上下游影响面、证据表和能力缺口。

## 3. 数据源与采集状态

| 数据源 | 状态 | 说明 |
| --- | --- | --- |
| Pod 快照 | 成功 | count=1019 |
| Service 快照 | 成功 | count=5 |
| Ingress 快照 | 成功 | count=1 |
| Node 快照 | 成功 | count=11 |

## 4. 目标健康证据

- Pod 总数: `1007`，Ready: `20`，Unready: `987`，可用性: `degraded`
| Pod | 状态 | Ready | Node | IP |
| --- | --- | --- | --- | --- |
| default/abclient-57c4fbb6f6-22ckc | Failed | False | 192.168.32.63 | - |
| default/abclient-57c4fbb6f6-22mgd | Failed | False | 192.168.32.53 | - |
| default/abclient-57c4fbb6f6-24ztf | Failed | False | 192.168.32.239 | - |
| default/abclient-57c4fbb6f6-252xw | Failed | False | 192.168.32.218 | - |
| default/abclient-57c4fbb6f6-256tb | Failed | False | 192.168.32.124 | - |
| default/abclient-57c4fbb6f6-25q2h | Failed | False | 192.168.32.239 | - |
| default/abclient-57c4fbb6f6-26lk5 | Failed | False | 192.168.32.226 | - |
| default/abclient-57c4fbb6f6-27dz8 | Failed | False | 192.168.32.53 | - |
| default/abclient-57c4fbb6f6-27gfz | Failed | False | 192.168.32.218 | - |
| default/abclient-57c4fbb6f6-288bg | Failed | False | 192.168.32.239 | - |
| default/abclient-57c4fbb6f6-289ns | Failed | False | 192.168.32.117 | - |
| default/abclient-57c4fbb6f6-28bsj | Failed | False | 192.168.32.218 | - |
| default/abclient-57c4fbb6f6-28vgm | Failed | False | 192.168.32.117 | - |
| default/abclient-57c4fbb6f6-292zg | Failed | False | 192.168.32.239 | - |
| default/abclient-57c4fbb6f6-2976r | Failed | False | 192.168.32.218 | - |
| default/abclient-57c4fbb6f6-29hdd | Failed | False | 192.168.32.239 | - |
| default/abclient-57c4fbb6f6-2btkh | Failed | False | 192.168.32.218 | - |
| default/abclient-57c4fbb6f6-2c6jx | Failed | False | 192.168.32.124 | - |
| default/abclient-57c4fbb6f6-2c9fc | Failed | False | 192.168.32.63 | - |
| default/abclient-57c4fbb6f6-2cbm4 | Failed | False | 192.168.32.239 | - |

## 5. 上游入口与服务暴露

| Service | Type | ClusterIP | Ports | Selector |
| --- | --- | --- | --- | --- |
| - | - | - | - | - |

| Ingress | Hosts | Backend Services | LB |
| --- | --- | --- | --- |
| - | - | - | - |

## 6. 故障传播路径

- **direct-pod**: Pods:default/abclient-57c4fbb6f6-22ckc, default/abclient-57c4fbb6f6-22mgd, default/abclient-57c4fbb6f6-24ztf, default/abclient-57c4fbb6f6-252xw, default/abclient-57c4fbb6f6-256tb, default/abclient-57c4fbb6f6-25q2h, default/abclient-57c4fbb6f6-26lk5, default/abclient-57c4fbb6f6-27dz8。影响: no Service/Ingress was found; blast radius appears limited to direct Pod consumers or batch execution

```mermaid
flowchart LR
  N1["Pods:default/abclient-57c4fbb6f6-22ckc, default/abclient-57c4fb
