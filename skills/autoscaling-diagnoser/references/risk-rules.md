# Risk Rules

## 默认只读

本 skill 的默认行为只允许读取和报告，不允许直接改变集群状态。

禁止自动执行：

- 创建、替换或删除 HPA。
- 修改 Deployment/StatefulSet replicas、requests、limits。
- 修改节点池 min/max、手动扩缩节点池。
- 安装、升级、卸载 CCE 插件。
- cordon、drain、delete、reboot 节点。
- 扩容 VPC 子网、申请配额、修改 IAM 委托。

## 可输出的整改内容

允许输出：

- HPA YAML 建议或 `huawei_configure_cce_hpa` 的无 `confirm=true` 预览。
- 节点池 autoscaling min/max 建议。
- request/limit 调整建议。
- 亲和性、污点、tolerations、nodeSelector 的修复建议。
- 子网、配额、IAM 的人工核查清单。
- 变更前后验证步骤和回滚路径。

## 需要转交的动作

客户明确要求执行整改时，转交 `auto-remediation-runner` 或人工变更流程：

- HPA 配置：先预览 manifest，再由客户确认。
- 节点池扩缩容或 min/max 调整：必须确认业务影响、费用、AZ/规格、回滚方案。
- request/limit 调整：需要发布窗口或滚动更新计划。
- 插件安装/升级：需要确认插件版本、集群版本兼容性和回滚方案。
