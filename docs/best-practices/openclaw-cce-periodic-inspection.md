# 最佳实践：使用OpenClaw进行CCE集群定期巡检

## 应用场景

企业生产环境中，CCE集群需要每日进行健康检查，及时发现节点异常、Pod故障、资源瓶颈等问题。通过OpenClaw Agent对接 `daily-cluster-inspector` Skill，可以实现：

- 定时自动执行集群巡检
- 自动生成巡检报告（Markdown/HTML格式）
- 通过邮件将巡检结果推送给运维团队
- 历史巡检数据持久化存储

## 前提条件

- 已创建CCE集群且状态为"运行中"。
- 已开通OpenClaw服务并完成Agent初始化。
- Agent已完成华为云云原生Skill的注册（详见[Skill参考](../skill-reference.md)）。
- 已配置华为云AK/SK凭证（通过OpenClaw密钥管理或环境变量）。
- 已配置邮件服务（SMTP或华为云邮件推送服务SES）。

## 涉及的Skill

| Skill名称 | 功能说明 |
|-----------|---------|
| `daily-cluster-inspector` | 执行每日集群巡检，支持快速、并行、深度三种模式 |
| `observability-context-builder` | 汇聚AOM告警、LTS日志、K8s事件、Pod/Node指标 |
| `ops-report-generator` | 生成运维报告（Markdown/HTML格式） |

## 操作步骤

### 步骤1：配置定时巡检任务

1. 登录OpenClaw控制台，进入 **Agent管理** > **任务编排**。

2. 点击 **创建定时任务**，填写任务基本信息：

   | 参数 | 说明 | 示例值 |
   |------|------|--------|
   | 任务名称 | 定时任务的标识 | `daily-cluster-inspection` |
   | 执行方式 | 触发方式 | `定时触发` |
   | Cron表达式 | 定时规则 | `0 9 * * *`（每天上午9点） |
   | 时区 | 执行时区 | `Asia/Shanghai` |

3. 配置执行内容：

   ```yaml
   skill: daily-cluster-inspector
   参数:
     region: "cn-north-4"
     cluster_id: "your-cluster-id"
     inspection_mode: "parallel"    # 并行巡检模式
     depth: "standard"              # 巡检深度：quick/standard/deep
   ```

4. 配置输出和通知：

   ```yaml
   输出配置:
     报告格式: ["markdown", "html"]
     存储位置: obs://your-bucket/reports/
   
   邮件通知:
     启用: true
     收件人: 
       - ops-team@company.com
       - sre-lead@company.com
     邮件标题模板: "[巡检报告] CCE集群每日巡检 - {{date}}"
   ```

5. 点击 **保存并启用**。

### 步骤2：查看巡检报告

#### 方式一：通过OpenClaw控制台查看

1. 进入 **任务编排** > **历史记录**。

2. 找到对应的巡检任务执行记录，点击 **查看报告**。

3. 报告页面展示以下内容：

   **巡检摘要**

   | 检查项 | 状态 | 详情 |
   |--------|------|------|
   | 节点健康 | 通过 | 3/3 节点正常 |
   | Pod状态 | 警告 | 2个Pod异常 |
   | 活跃告警 | 警告 | 1条未清除告警 |
   | 资源利用率 | 正常 | CPU 45%, 内存 62% |
   | 核心插件 | 通过 | 所有插件运行正常 |
   | 存储状态 | 通过 | 无异常PVC |

   **异常详情**

   | Pod名称 | 命名空间 | 状态 | 原因 |
   |---------|----------|------|------|
   | nginx-7d9f4b8c5-x2 | default | CrashLoopBackOff | OOMKilled |
   | redis-5c8a2f1d9-p9 | cache | Pending | 调度失败 |

#### 方式二：通过API查询报告

调用OpenClaw API获取最近一次巡检报告：

```bash
curl -X GET "https://openclaw.huaweicloud.com/api/v1/agents/{agent_id}/reports/latest" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json"
```

返回示例：

```json
{
  "report_id": "rpt-20260531-001",
  "agent_id": "cce-ops-agent",
  "task_name": "daily-cluster-inspection",
  "cluster_info": {
    "region": "cn-north-4",
    "cluster_id": "your-cluster-id",
    "cluster_name": "prod-web-cluster"
  },
  "inspection_time": {
    "start": "2026-05-31T09:00:05Z",
    "end": "2026-05-31T09:00:28Z",
    "duration_seconds": 23
  },
  "summary": {
    "total_checks": 12,
    "passed": 9,
    "warning": 2,
    "critical": 0,
    "failed": 1
  },
  "findings": [
    {
      "severity": "warning",
      "category": "pod_health",
      "resource": "nginx-7d9f4b8c5-x2",
      "namespace": "default",
      "issue": "CrashLoopBackOff",
      "root_cause": "OOMKilled - 内存limit不足",
      "recommendation": "增加内存limit或排查内存泄漏"
    }
  ],
  "artifacts": {
    "markdown_url": "obs://your-bucket/reports/2026-05-31/report.md",
    "html_url": "obs://your-bucket/reports/2026-05-31/report.html",
    "pdf_url": "obs://your-bucket/reports/2026-05-31/report.pdf"
  }
}
```

#### 方式三：通过OBS直接访问

巡检报告会自动上传至配置的OBS桶，可以直接下载：

```bash
# 下载HTML报告
obsutil cp obs://your-bucket/reports/2026-05-31/report.html ./

# 下载PDF报告
obsutil cp obs://your-bucket/reports/2026-05-31/report.pdf ./
```

### 步骤3：配置邮件发送

1. 进入OpenClaw控制台 **通知管理** > **邮件模板**。

2. 创建邮件模板：

   **模板名称**：`cluster-inspection-report`

   **邮件主题**：`[巡检报告] {{cluster_name}} 每日巡检 - {{date}}`

   **邮件正文**：

   ```
   您好，
   
   {{cluster_name}} 集群每日巡检已完成，以下是巡检摘要：
   
   - 巡检时间: {{inspection_time}}
   - 总检查项: {{total_checks}}
   - 通过: {{passed}}
   - 警告: {{warning}}
   - 严重: {{critical}}
   
   {{#if findings}}
   发现以下异常，请关注：
   {{#each findings}}
   - [{{severity}}] {{resource}}: {{issue}}
     建议: {{recommendation}}
   {{/each}}
   {{else}}
   本次巡检未发现异常，集群状态良好。
   {{/if}}
   
   详细报告请查看附件或访问：{{report_url}}
   
   此邮件由 OpenClaw 自动发送，请勿回复。
   ```

3. 配置邮件服务：

   | 参数 | 说明 | 示例值 |
   |------|------|--------|
   | 服务类型 | 邮件服务类型 | `SMTP` 或 `HUAWEI_CLOUD_SES` |
   | 服务器地址 | SMTP服务器地址 | `smtp.company.com` |
   | 端口 | SMTP端口 | `587` |
   | 加密方式 | 传输加密 | `STARTTLS` |
   | 发件人 | 发件人地址 | `openclaw@company.com` |

   > **说明**
   > 如果使用华为云邮件推送服务（SES），需要配置AK/SK和Region参数。

4. 测试邮件发送：

   手动触发一次巡检任务，检查邮件是否成功发送。可以在 **通知管理** > **发送记录** 中查看发送状态。

   收到的邮件示例：

   ```
   From: openclaw@company.com
   To: ops-team@company.com, sre-lead@company.com
   Subject: [巡检报告] prod-web-cluster 每日巡检 - 2026-05-31
   
   您好，
   
   prod-web-cluster 集群每日巡检已完成，以下是巡检摘要：
   
   - 巡检时间: 2026-05-31 09:00:05 - 09:00:28
   - 总检查项: 12
   - 通过: 9
   - 警告: 2
   - 严重: 0
   
   发现以下异常，请关注：
   - [warning] nginx-7d9f4b8c5-x2: CrashLoopBackOff
     建议: 增加内存limit或排查内存泄漏
   - [warning] node-02: NodeMemoryPressure
     建议: 考虑扩容节点或优化工作负载
   
   详细报告请查看附件或访问：
   https://openclaw.huaweicloud.com/reports/rpt-20260531-001
   
   此邮件由 OpenClaw 自动发送，请勿回复。
   ```

## 预期结果

完成上述配置后，系统将按照以下流程运行：

1. **每日定时巡检**：每天上午9点自动执行集群巡检。
2. **自动生成报告**：巡检完成后自动生成Markdown和HTML格式的报告。
3. **邮件自动推送**：报告生成后自动发送邮件给运维团队。
4. **历史数据留存**：所有报告保存至OBS，支持历史查询和对比分析。

巡检效果统计示例（最近7天）：

| 日期 | 执行状态 | 耗时 | 警告 | 严重 | 新发现问题 |
|------|---------|------|------|------|-----------|
| 2026-05-31 | 成功 | 23秒 | 2 | 0 | 1 |
| 2026-05-30 | 成功 | 21秒 | 1 | 0 | 0 |
| 2026-05-29 | 成功 | 25秒 | 3 | 1 | 2 |
| 2026-05-28 | 成功 | 20秒 | 0 | 0 | 0 |
| 2026-05-27 | 成功 | 22秒 | 1 | 0 | 1 |

## 约束与限制

- 巡检任务执行期间会调用CCE、AOM等云服务的API，会产生少量API调用费用。
- 报告存储在OBS中，会产生相应的存储费用。
- 邮件发送频率受邮件服务配额限制，建议合理设置巡检频率。
- 深度巡检（`depth: deep`）会采集更多指标，执行时间可能超过5分钟。

## 后续操作

- **告警升级**：对于严重级别的问题，建议配置短信或企业微信通知。
- **自定义检查项**：可以在 `daily-cluster-inspector` Skill的 `references/workflow.md` 中扩展自定义检查规则。
- **报告归档**：建议配置OBS生命周期策略，自动删除30天前的历史报告。

## 相关文档

- [Skill参考 - daily-cluster-inspector](../skill-reference.md#351-daily-cluster-inspector)
- [Skill参考 - ops-report-generator](../skill-reference.md#353-ops-report-generator)
- 华为云CCE用户指南
- 华为云AOM用户指南
