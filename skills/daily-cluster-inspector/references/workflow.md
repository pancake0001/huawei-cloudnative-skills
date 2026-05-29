# Workflow

1. 默认先运行快检，正常时直接输出 heartbeat summary。
2. 快检异常时运行深度诊断或并行巡检。
3. 按 Pod、Node、Event、AOM、ELB、Resource 分类汇总问题。
4. 标记 P0/P1/P2 风险和建议负责人。
5. 只读输出报告，不自动修复。
6. 对需要动作的项提供转交 `auto-remediation-runner` 的确认清单。

