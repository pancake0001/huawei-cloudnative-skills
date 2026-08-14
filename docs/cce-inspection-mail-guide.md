# CCE 集群巡检与邮件告警指南

本文档介绍如何在 opencode 中使用华为云 CCE 巡检工具，对集群进行健康检查，并将巡检结果通过邮件发送。

## 目录

- [环境准备](#环境准备)
- [巡检工具概览](#巡检工具概览)
- [执行巡检](#执行巡检)
- [查看巡检结果](#查看巡检结果)
- [发送邮件告警](#发送邮件告警)

---

## 环境准备

### 1. 配置凭证

巡检工具需要华为云 AK/SK 凭证。凭证文件位于 `~/qiujiansong/secure`：

```bash
export HUAWEI_AK="your_access_key"
export HUAWEI_SK="your_secret_key"
```

### 2. 确认集群信息

集群 `cce-ai-diagnoses` 位于 `cn-north-4`（华北-北京四）区域：

| 参数 | 值 |
|------|-----|
| Region | `cn-north-4` |
| Cluster ID | `1d450236-5b28-11f1-a7f6-0255ac10026a` |
| Cluster Name | `cce-ai-diagnoses` |

### 3. 确认工具可用性

```bash
cd /Users/qiujiansong/Codes/huawei-cloudnative-skills
python3 -c "
import sys
sys.path.insert(0, '.')
from scripts.huawei_cloud.dispatcher import ACTION_SPECS
print(f'共 {len(ACTION_SPECS)} 个工具已注册')
inspection = [k for k in ACTION_SPECS.keys() if 'inspect' in k.lower() or 'check' in k.lower()]
print(f'巡检相关工具: {len(inspection)} 个')
for t in sorted(inspection):
    print(f'  - {t}')
"
```

---

## 巡检工具概览

### 工具层级

| 层级 | 工具 | 说明 |
|------|------|------|
| **快检** | `huawei_cce_quick_check` | 3 个 API，< 30s，判断是否有异常 |
| **全量巡检** | `huawei_cce_auto_inspection` | 并行执行节点/Pod/事件/AOM/ELB 检查 |
| **深度诊断** | `huawei_cce_deep_diagnosis` | 异常时深度分析 |
| **节点巡检** | `huawei_node_status_inspection` | 节点状态专项 |
| **Pod 巡检** | `huawei_pod_status_inspection` | Pod 状态专项 |
| **事件巡检** | `huawei_event_inspection` | K8s 事件分析 |
| **AOM 告警巡检** | `huawei_aom_alarm_inspection` | 云监控告警分析 |
| **报告导出** | `huawei_export_inspection_report` | 导出巡检报告 |

### Skill 对应关系

| Skill | 负责工具 |
|-------|----------|
| `daily-cluster-inspector` | `huawei_cce_quick_check`, `huawei_cce_auto_inspection`, `huawei_export_inspection_report` |
| `ops-report-generator` | `huawei_generate_ops_report` (周报/月报/SLA) |

---

## 执行巡检

### 方式一：快检（推荐日常巡检）

快检快速判断集群是否有异常，适合每日例行检查：

```bash
cd /Users/qiujiansong/Codes/huawei-cloudnative-skills
source ~/qiujiansong/secure

python3 -c "
import sys
sys.path.insert(0, '.')
from scripts.huawei_cloud.dispatcher import dispatch_action

result = dispatch_action('huawei_cce_quick_check', {
    'region': 'cn-north-4',
    'cluster_id': '1d450236-5b28-11f1-a7f6-0255ac10026a',
    'ak': '$HUAWEI_AK',
    'sk': '$HUAWEI_SK',
})

import json
print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
"
```

**正常输出示例**：
```json
{
  "success": true,
  "has_anomaly": false,
  "anomaly_details": [],
  "normal_details": [
    "AOM 告警正常：0 firing, 0 resolved，无资源类严重告警",
    "ELB 正常：3 个 ELB 最近 5分钟内无异常"
  ],
  "check_time": "2026-05-31 20:57:51 CST",
  "duration_seconds": 8.22
}
```

**发现异常时的输出示例**：
```json
{
  "success": true,
  "has_anomaly": true,
  "anomaly_details": [
    {
      "type": "replica_mismatch",
      "deployments": [
        {"name": "abclient", "ready": 18, "desired": 20},
        {"name": "cceaddon-virtual-kubelet-virtual-kubelet", "ready": 1, "desired": 2}
      ],
      "message": "3 个 Deployment 副本不匹配: abclient(18/20), ..."
    }
  ],
  "normal_details": [...],
  "check_time": "2026-05-31 20:57:51 CST"
}
```

### 方式二：全量自动巡检

全量巡检并行执行所有检查项，生成完整的诊断报告：

```bash
cd /Users/qiujiansong/Codes/huawei-cloudnative-skills
source ~/qiujiansong/secure

python3 -c "
import sys
sys.path.insert(0, '.')
from scripts.huawei_cloud.dispatcher import dispatch_action

result = dispatch_action('huawei_cce_auto_inspection', {
    'region': 'cn-north-4',
    'cluster_id': '1d450236-5b28-11f1-a7f6-0255ac10026a',
    'ak': '\$HUAWEI_AK',
    'sk': '\$HUAWEI_SK',
})

import json
print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
"
```

**输出结构**：
```json
{
  "success": true,
  "cluster_id": "1d450236-5b28-11f1-a7f6-0255ac10026a",
  "region": "cn-north-4",
  "check_time": "2026-05-31 20:56:06 CST",
  "has_anomaly": true,
  "quick_check_anomalies": [
    {
      "type": "replica_mismatch",
      "deployments": [
        {"name": "abclient", "ready": 14, "desired": 20}
      ],
      "message": "3 个 Deployment 副本不匹配"
    }
  ],
  "diagnosis": {
    "alarm_analysis": {
      "summary": {
        "total_raw_alarms": 401,
        "unique_alarm_groups": 9,
        "chronic_count": 4,
        "attention_count": 4,
        "sudden_count": 1,
        "noise_reduction_pct": 78.8
      },
      "sudden_alarms": [...],
      "attention_alarms": [...],
      "chronic_alarms": [...]
    },
    "pod_status": {...},
    "node_status": {...},
    "event_analysis": {...}
  }
}
```

### 方式三：深度诊断

当快检发现异常时，进行深度诊断：

```bash
python3 -c "
import sys
sys.path.insert(0, '.')
from scripts.huawei_cloud.dispatcher import dispatch_action

result = dispatch_action('huawei_cce_deep_diagnosis', {
    'region': 'cn-north-4',
    'cluster_id': '1d450236-5b28-11f1-a7f6-0255ac10026a',
    'ak': '$HUAWEI_AK',
    'sk': '$HUAWEI_SK',
    'thresholds': '{\"pod_anomaly_threshold\": 0.5}'
})

import json
print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
"
```

### 方式四：单专项巡检

针对特定维度进行巡检：

```bash
# 节点状态巡检
huawei_node_status_inspection region=cn-north-4 cluster_id=1d450236-5b28-11f1-a7f6-0255ac10026a

# Pod 状态巡检
huawei_pod_status_inspection region=cn-north-4 cluster_id=1d450236-5b28-11f1-a7f6-0255ac10026a

# AOM 告警巡检
huawei_aom_alarm_inspection region=cn-north-4 cluster_id=1d450236-5b28-11f1-a7f6-0255ac10026a
```

---

## 查看巡检结果

### 巡检结果结构

巡检结果包含以下核心字段：

| 字段 | 说明 |
|------|------|
| `success` | 请求是否成功 |
| `summary` | 总体状态：`HEALTHY` / `WARNING` / `CRITICAL` |
| `quick_check_anomalies` | 快检发现的异常列表 |
| `diagnosis.*` | 详细诊断结果 |
| `diagnosis_time` | 巡检时间 |

### 关键异常类型

| 异常类型 | 说明 | 关联分析 |
|----------|------|----------|
| `replica_mismatch` | 副本数不匹配 | Deployment 副本数与期望不符 |
| `pod_restart_loop` | Pod 重启循环 | CrashLoopBackOff |
| `node_not_ready` | 节点 NotReady | 节点故障 |
| `pod_pending` | Pod Pending | 调度失败/资源不足 |
| `oom_killed` | OOM 被杀 | 内存超限 |
| `image_pull_backoff` | 镜像拉取失败 | 镜像不存在或拉取超时 |

### 巡检结果判读

**快速判读规则**：

1. `summary == "HEALTHY"` → 集群健康，无需操作
2. `summary == "WARNING"` → 存在关注项，查看 `quick_check_anomalies`
3. `summary == "CRITICAL"` → 需立即处理，查看深度诊断结果

**当前集群典型异常**（`cce-ai-diagnoses`）：

- `abclient` Deployment 副本不匹配（14/20）
- 67 个 Warning 事件（大部分为 `abclient` 容器退出码 104/110）
- 4 个慢性告警（Pod CPU 超限）
- 1 个突发告警（nginx-bd96c8c7d-gms8z CPU 超 80%）

---

## 发送邮件告警

当前工具集未内置邮件发送功能。以下提供两种邮件发送方案。

### 方案一：Python 脚本发送邮件（推荐）

将巡检结果生成为 HTML 报告后发送邮件：

```python
#!/usr/bin/env python3
"""
CCE 巡检报告邮件发送脚本
用法: python3 send_inspection_report.py [--report-file <path>] [--to <email>]
"""

import sys
import json
import smtplib
import argparse
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header

# 邮件配置（请根据实际情况修改）
SMTP_SERVER = "smtp.example.com"      # SMTP 服务器地址
SMTP_PORT = 465                       # SMTP 端口（SSL）
SMTP_USER = "your_email@example.com"  # 发件人邮箱
SMTP_PASSWORD = "your_password"       # 邮箱密码或授权码
FROM_NAME = "CCE 巡检系统"            # 发件人显示名


def load_inspection_report(report_path: str) -> dict:
    """从 JSON 文件加载巡检结果"""
    with open(report_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def format_html_report(result: dict) -> str:
    """将巡检结果格式化为 HTML 邮件正文"""
    cluster_id = result.get("cluster_id", "N/A")
    region = result.get("region", "N/A")

    # 兼容不同 API 的时间字段名
    diagnosis_time = result.get("check_time") or result.get("diagnosis_time") or "N/A"

    # 兼容 quick_check 和 auto_inspection 的异常字段
    # quick_check: anomaly_details
    # auto_inspection: quick_check_anomalies
    anomaly_list = result.get("anomaly_details") or result.get("quick_check_anomalies") or []
    has_anomaly = result.get("has_anomaly", bool(anomaly_list))
    summary = "WARNING" if has_anomaly else "HEALTHY"

    # 状态颜色
    status_colors = {
        "HEALTHY": "#28a745",
        "WARNING": "#ffc107",
        "CRITICAL": "#dc3545"
    }
    status_color = status_colors.get(summary, "#6c757d")

    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto;">
    <div style="background: {status_color}; color: white; padding: 20px; text-align: center;">
        <h1 style="margin: 0;">CCE 集群巡检报告</h1>
        <p style="margin: 10px 0 0;">状态: {summary}</p>
    </div>

    <div style="padding: 20px; background: #f8f9fa;">
        <h2 style="color: #333;">基本信息</h2>
        <table style="width: 100%; border-collapse: collapse;">
        <tr>
            <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>集群 ID</strong></td>
            <td style="padding: 8px; border-bottom: 1px solid #ddd;">{cluster_id}</td>
        </tr>
        <tr>
            <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Region</strong></td>
            <td style="padding: 8px; border-bottom: 1px solid #ddd;">{region}</td>
        </tr>
        <tr>
            <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>巡检时间</strong></td>
            <td style="padding: 8px; border-bottom: 1px solid #ddd;">{diagnosis_time}</td>
        </tr>
        </table>
    </div>
    """

    # 异常信息
    if anomaly_list:
        html += """
        <div style="padding: 20px;">
            <h2 style="color: #dc3545;">异常告警</h2>
        """
        for anomaly in anomaly_list:
            anomaly_type = anomaly.get("type", "unknown")
            message = anomaly.get("message", "N/A")
            deployments = anomaly.get("deployments", [])

            html += f"""
            <div style="background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin-bottom: 15px;">
                <h3 style="margin: 0 0 10px; color: #856404;">类型: {anomaly_type}</h3>
                <p style="margin: 0; color: #333;">{message}</p>
            """

            if deployments:
                html += """
                <table style="width: 100%; margin-top: 10px; border-collapse: collapse;">
                <thead>
                    <tr style="background: #ffeeba;">
                        <th style="padding: 8px; text-align: left;">Deployment</th>
                        <th style="padding: 8px; text-align: center;">就绪/期望</th>
                    </tr>
                </thead>
                <tbody>
                """
                for dep in deployments:
                    name = dep.get("name", "N/A")
                    ready = dep.get("ready", "N/A")
                    desired = dep.get("desired", "N/A")
                    html += f"""
                    <tr>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd;">{name}</td>
                        <td style="padding: 8px; text-align: center; border-bottom: 1px solid #ddd;">{ready} / {desired}</td>
                    </tr>
                    """
                html += "</tbody></table>"

            html += "</div>"

        html += "</div>"

    # AOM 告警摘要
    diagnosis = result.get("diagnosis", {})
    alarm = diagnosis.get("alarm_analysis", {})
    summary_data = alarm.get("summary", {})

    if summary_data:
        html += f"""
        <div style="padding: 20px; border-top: 1px solid #ddd;">
            <h2 style="color: #333;">AOM 告警摘要</h2>
            <table style="width: 100%; border-collapse: collapse;">
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>总告警数</strong></td>
                <td style="padding: 8px; border-bottom: 1px solid #ddd;">{summary_data.get('total_raw_alarms', 0)}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>去重后告警组</strong></td>
                <td style="padding: 8px; border-bottom: 1px solid #ddd;">{summary_data.get('unique_alarm_groups', 0)}</td>
            </tr>
            <tr style="background: #f8d7da;">
                <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>慢性告警 (≥5次)</strong></td>
                <td style="padding: 8px; border-bottom: 1px solid #ddd;">{summary_data.get('chronic_count', 0)}</td>
            </tr>
            <tr style="background: #fff3cd;">
                <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>关注告警</strong></td>
                <td style="padding: 8px; border-bottom: 1px solid #ddd;">{summary_data.get('attention_count', 0)}</td>
            </tr>
            <tr style="background: #d4edda;">
                <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>突发告警</strong></td>
                <td style="padding: 8px; border-bottom: 1px solid #ddd;">{summary_data.get('sudden_count', 0)}</td>
            </tr>
            </table>
        </div>
        """

    html += """
    <div style="padding: 20px; background: #e9ecef; text-align: center; color: #6c757d; font-size: 12px;">
        <p>此报告由 CCE 智能巡检系统自动生成</p>
        <p>如需进一步诊断，请联系运维团队</p>
    </div>
    </body>
    </html>
    """
    return html


def send_email(to: str, subject: str, html_content: str, text_content: str = ""):
    """发送邮件"""
    msg = MIMEMultipart('alternative')
    msg['Subject'] = Header(subject, 'utf-8')
    msg['From'] = f"{FROM_NAME} <{SMTP_USER}>"
    msg['To'] = to

    # Plain text 版本（兼容邮件客户端）
    if text_content:
        msg.attach(MIMEText(text_content, 'plain', 'utf-8'))

    # HTML 版本
    msg.attach(MIMEText(html_content, 'html', 'utf-8'))

    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, [to], msg.as_string())
        print(f"邮件已发送至: {to}")
        return True
    except Exception as e:
        print(f"邮件发送失败: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='CCE 巡检报告邮件发送工具')
    parser.add_argument('--report-file', '-f', default='/tmp/inspection_report.json',
                        help='巡检结果 JSON 文件路径')
    parser.add_argument('--to', '-t', required=True, help='收件人邮箱地址')
    parser.add_argument('--subject', '-s', default='[CCE巡检] 集群健康状态报告',
                        help='邮件主题')
    args = parser.parse_args()

    # 加载报告
    result = load_inspection_report(args.report_file)

    # 生成 HTML
    html_content = format_html_report(result)

    # 生成纯文本摘要（用于不支持 HTML 的邮件客户端）
    anomaly_list = result.get("anomaly_details") or result.get("quick_check_anomalies") or []
    has_anomaly = result.get("has_anomaly", bool(anomaly_list))
    check_time = result.get("check_time") or result.get("diagnosis_time") or "N/A"
    text_content = f"""CCE 集群巡检报告

集群: {result.get('cluster_id')}
Region: {result.get('region')}
时间: {check_time}

状态: {'WARNING' if has_anomaly else 'HEALTHY'}

{'发现 ' + str(len(anomaly_list)) + ' 个异常:' if anomaly_list else '未发现异常'}

"""
    for a in anomaly_list:
        text_content += f"\n- [{a.get('type')}] {a.get('message')}"

    # 发送邮件
    send_email(args.to, args.subject, html_content, text_content)


if __name__ == "__main__":
    main()
```

### 方案二：一键执行巡检并发送邮件

```bash
#!/bin/bash
#巡检并发送邮件脚本
#用法: ./inspection_mail.sh <收件人邮箱>

set -e

SCRIPT_DIR="/Users/qiujiansong/Codes/huawei-cloudnative-skills"
source ~/qiujiansong/secure
REPORT_FILE="/tmp/inspection_report_$(date +%Y%m%d_%H%M%S).json"
TO_EMAIL="$1"

if [ -z "$TO_EMAIL" ]; then
    echo "用法: $0 <收件人邮箱>"
    exit 1
fi

cd "$SCRIPT_DIR"

echo "=== 执行 CCE 全量巡检 ==="
python3 << EOF
import sys
import json
import os
sys.path.insert(0, '.')
from scripts.huawei_cloud.dispatcher import dispatch_action

result = dispatch_action('huawei_cce_auto_inspection', {
    'region': 'cn-north-4',
    'cluster_id': '1d450236-5b28-11f1-a7f6-0255ac10026a',
    'ak': os.environ.get('HUAWEI_AK'),
    'sk': os.environ.get('HUAWEI_SK'),
})

with open('$REPORT_FILE', 'w', encoding='utf-8') as f:
    json.dump(result, f, indent=2, ensure_ascii=False, default=str)

print(f"报告已保存: $REPORT_FILE")
EOF

echo "=== 发送邮件 ==="
python3 "$SCRIPT_DIR/send_inspection_report.py" \
    --report-file "$REPORT_FILE" \
    --to "$TO_EMAIL" \
    --subject "[CCE巡检] cce-ai-diagnoses $(date +%Y-%m-%d) 巡检报告"

echo "=== 完成 ==="
```

### 方案三：通过企业微信/钉钉机器人转发邮件

如果企业使用内部通讯工具，可通过 webhook 机器人将巡检摘要转发，再由机器人触发邮件。

---

## 邮件主题参考

| 场景 | 邮件主题 |
|------|----------|
| 日常巡检 | `[CCE巡检] cce-ai-diagnoses 2026-05-31 巡检报告` |
| 发现异常 | `[CCE告警] cce-ai-diagnoses 发现 {N} 个异常需关注` |
| 严重告警 | `[CCE紧急] cce-ai-diagnoses 集群状态: CRITICAL` |

---

## 附录：完整巡检结果 JSON 结构

```json
{
  "success": true,
  "cluster_id": "集群ID",
  "region": "区域",
  "diagnosis_time": "YYYY-MM-DD HH:MM:SS",
  "quick_check_anomalies": [
    {
      "type": "replica_mismatch | pod_restart_loop | ...",
      "deployments": [],
      "message": "异常描述"
    }
  ],
  "diagnosis": {
    "alarm_analysis": {
      "summary": {
        "total_raw_alarms": 0,
        "unique_alarm_groups": 0,
        "chronic_count": 0,
        "attention_count": 0,
        "sudden_count": 0,
        "noise_reduction_pct": 0.0
      },
      "sudden_alarms": [],
      "attention_alarms": [],
      "chronic_alarms": []
    },
    "pod_status": { "issues": [], "summary": {} },
    "node_status": { "issues": [], "summary": {} },
    "event_analysis": { "warning_count": 0, "recent_warnings": [] }
  }
}
```
