# Workflow

1. 将用户意图或根因结论转换成动作、对象、参数和验证标准。
2. 如果根因是 Deployment 新版本启动命令/镜像/探针/CrashLoop 导致不可用，优先选择 `rollback_previous_revision`。
3. 检查动作风险等级。Deployment rollback、scale、resize、cordon、uncordon 属于 R2；delete、drain、reboot、HSS 状态变更属于 R3。
4. 第一次调用必须不带 `confirm=true`，获取预览或风险提示。
5. 输出预览结果、影响范围、回滚方式、执行后验证计划。
6. 等待用户明确确认，确认内容至少包含动作、对象、region、cluster_id。
7. 用户确认后才允许携带 `confirm=true`。
8. 执行后调用只读工具验证 Pod、Node、Workload、Events 或漏洞状态。
9. 对自动恢复编排，输出完整 Markdown 执行报告，包含诊断依据、动作结果和验证结果。
