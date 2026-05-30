# Risk Rules

- 允许自动执行节点只读查询、Lease 查询、Event 查询、Pod 查询、指标查询、巡检和 HSS 查询。
- `huawei_node_failure_diagnose` 是只读诊断工具，只生成结构化证据和 Markdown 报告，不执行恢复动作。
- 禁止本 skill 直接调用 cordon、uncordon、drain、reboot、漏洞状态修改。
- 建议重启或 drain 前必须说明业务影响、节点上 Pod、回滚方式和验证步骤。
- HSS 修复类动作必须说明 `confirm=true` 只可在用户明确确认后传入。
