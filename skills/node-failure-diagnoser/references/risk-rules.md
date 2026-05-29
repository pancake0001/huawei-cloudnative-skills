# Risk Rules

- 允许自动执行节点只读查询、指标查询、巡检和 HSS 查询。
- 禁止本 skill 直接调用 cordon、uncordon、drain、reboot、漏洞状态修改。
- 建议重启或 drain 前必须说明业务影响、节点上 Pod、回滚方式和验证步骤。
- HSS 修复类动作必须说明 `confirm=true` 只可在用户明确确认后传入。

