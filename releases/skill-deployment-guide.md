# 华为云原生 Skill 部署与使用指导

> 本文档指导如何将 `releases/devtools` 和 `releases/container` 下的华为云原生 skill 安装部署到 aicli、OpenClaw、Hermes 三个 agent 中，并以 WSL (Ubuntu) 环境为例给出具体操作步骤。

## 1. Skill 清单

### 1.1 devtools 目录

| Skill 名称 | 路径 | 描述 |
|---|---|---|
| `huawei-cloud-cli-guidance` | `releases/devtools/huawei-cloud-cli-guidance/` | KooCLI 命令行工具操作指导，覆盖安装、认证配置、命令构造和错误排查 |

### 1.2 container 目录

| 分类 | Skill 名称 | 路径 | 描述 |
|---|---|---|---|
| **CCE** | `huawei-cloud-cce-cluster-management` | `releases/container/cce/huawei-cloud-cce-cluster-management/` | CCE 集群生命周期管理 |
| **CCE** | `huawei-cloud-cce-workload-manager` | `releases/container/cce/huawei-cloud-cce-workload-manager/` | CCE 工作负载管理 |
| **CCE** | `huawei-cloud-cce-cluster-upgrade-planner` | `releases/container/cce/huawei-cloud-cce-cluster-upgrade-planner/` | CCE 集群升级规划 |
| **CCE** | `huawei-cloud-cce-workload-failure-diagnoser` | `releases/container/cce/huawei-cloud-cce-workload-failure-diagnoser/` | CCE 工作负载故障诊断 |
| **CCE** | `huawei-cloud-cce-storage-failure-diagnoser` | `releases/container/cce/huawei-cloud-cce-storage-failure-diagnoser/` | CCE 存储故障诊断 |
| **CCE** | `huawei-cloud-cce-root-cause-analyzer` | `releases/container/cce/huawei-cloud-cce-root-cause-analyzer/` | CCE 根因分析 |
| **CCE** | `huawei-cloud-cce-pod-failure-diagnoser` | `releases/container/cce/huawei-cloud-cce-pod-failure-diagnoser/` | CCE Pod 故障诊断 |
| **CCE** | `huawei-cloud-cce-ops-report-generator` | `releases/container/cce/huawei-cloud-cce-ops-report-generator/` | CCE 运维报告生成 |
| **CCE** | `huawei-cloud-cce-observability-context-builder` | `releases/container/cce/huawei-cloud-cce-observability-context-builder/` | CCE 可观测性上下文构建 |
| **CCE** | `huawei-cloud-cce-node-failure-diagnoser` | `releases/container/cce/huawei-cloud-cce-node-failure-diagnoser/` | CCE 节点故障诊断 |
| **CCE** | `huawei-cloud-cce-network-failure-diagnoser` | `releases/container/cce/huawei-cloud-cce-network-failure-diagnoser/` | CCE 网络故障诊断 |
| **CCE** | `huawei-cloud-cce-metric-analyzer` | `releases/container/cce/huawei-cloud-cce-metric-analyzer/` | CCE 指标分析 |
| **CCE** | `huawei-cloud-cce-log-analyzer` | `releases/container/cce/huawei-cloud-cce-log-analyzer/` | CCE 日志分析 |
| **CCE** | `huawei-cloud-cce-kubernetes-event-analyzer` | `releases/container/cce/huawei-cloud-cce-kubernetes-event-analyzer/` | CCE K8s 事件分析 |
| **CCE** | `huawei-cloud-cce-dependency-impact-analyzer` | `releases/container/cce/huawei-cloud-cce-dependency-impact-analyzer/` | CCE 依赖影响分析 |
| **CCE** | `huawei-cloud-cce-daily-cluster-inspector` | `releases/container/cce/huawei-cloud-cce-daily-cluster-inspector/` | CCE 每日巡检 |
| **CCE** | `huawei-cloud-cce-cost-optimization-advisor` | `releases/container/cce/huawei-cloud-cce-cost-optimization-advisor/` | CCE 成本优化建议 |
| **CCE** | `huawei-cloud-cce-container-migration-planner` | `releases/container/cce/huawei-cloud-cce-container-migration-planner/` | CCE 容器迁移规划 |
| **CCE** | `huawei-cloud-cce-change-impact-analyzer` | `releases/container/cce/huawei-cloud-cce-change-impact-analyzer/` | CCE 变更影响分析 |
| **CCE** | `huawei-cloud-cce-cci-bursting-deployer` | `releases/container/cce/huawei-cloud-cce-cci-bursting-deployer/` | CCE CCI 弹性调度部署 |
| **CCE** | `huawei-cloud-cce-capacity-trend-forecaster` | `releases/container/cce/huawei-cloud-cce-capacity-trend-forecaster/` | CCE 容量趋势预测 |
| **CCE** | `huawei-cloud-cce-availability-risk-scanner` | `releases/container/cce/huawei-cloud-cce-availability-risk-scanner/` | CCE 可用性风险扫描 |
| **CCE** | `huawei-cloud-cce-autoscaling-diagnoser` | `releases/container/cce/huawei-cloud-cce-autoscaling-diagnoser/` | CCE 弹性伸缩诊断 |
| **CCE** | `huawei-cloud-cce-auto-remediation-runner` | `releases/container/cce/huawei-cloud-cce-auto-remediation-runner/` | CCE 自动修复执行 |
| **CCE** | `huawei-cloud-cce-alarm-correlation-engine` | `releases/container/cce/huawei-cloud-cce-alarm-correlation-engine/` | CCE 告警关联引擎 |
| **CCI** | `huawei-cloud-cci-instance-management` | `releases/container/cci/huawei-cloud-cci-instance-management/` | CCI 实例管理 |
| **SWR** | `huawei-cloud-swr-enterprise-instance` | `releases/container/swr/huawei-cloud-swr-enterprise-instance/` | SWR 企业版实例管理 |
| **SWR** | `huawei-cloud-swr-image-automation` | `releases/container/swr/huawei-cloud-swr-image-automation/` | SWR 镜像自动化 |
| **SWR** | `huawei-cloud-swr-image-governance` | `releases/container/swr/huawei-cloud-swr-image-governance/` | SWR 镜像治理 |
| **SWR** | `huawei-cloud-swr-image-management` | `releases/container/swr/huawei-cloud-swr-image-management/` | SWR 镜像管理 |
| **UCS** | `ucs-cluster-onboarding-manager` | `releases/container/ucs/ucs-cluster-onboarding-manager/` | UCS 集群纳管 |
| **UCS** | `ucs-policy-governor` | `releases/container/ucs/ucs-policy-governor/` | UCS 策略治理 |

## 2. Skill 结构说明

每个 skill 目录包含以下核心文件：

```
<skill-name>/
├── SKILL.md              # 主指令文件（YAML frontmatter + Markdown 正文）
├── SKILL-CN.md           # 中文版指令（可选）
├── skill-profile.yaml    # skill 级别、域、工具列表、guardrails 等元数据
├── references/           # 参考文档（workflow、API guide、troubleshooting 等）
├── scripts/              # Python 脚本（部分 skill 包含 huawei-cloud.py dispatcher）
└── .gitignore
```

**SKILL.md frontmatter 格式**：

```yaml
---
id: huawei-cloud-cce-change-impact-analyzer
name: huawei-cloud-cce-change-impact-analyzer
description: |
  ...
tags: [cce, change-impact, risk-assessment]
version: 1.0.0
---
```

> **注意**：三个 agent 对 SKILL.md frontmatter 有细微差异，详见各 agent 章节。

## 3. aicli 部署

### 3.1 环境现状

- **WSL 用户**：`pan`（home: `/home/pan`）
- **aicli 二进制**：`/home/pan/.huawei/bin/aicli`
- **KooCLI (hcloud)**：`/home/pan/.huawei/bin/hcloud`
- **Skill 安装路径**：`/home/pan/.agents/skills/`（已存在多个 skill）

已安装的 skill：

```
~/.agents/skills/
├── gitcode-cli/
├── huawei-cloud-cce-cluster-management/
├── huawei-cloud-cci-instance-management/
├── huawei-cloud-swr-enterprise-instance/
├── huawei-cloud-swr-image-automation/
├── huawei-cloud-swr-image-governance/
├── huawei-cloud-swr-image-management/
├── skill-targeted-audit/
├── ucs-cluster-onboarding-manager/
├── ucs-policy-governor/
```

### 3.2 安装步骤

aicli 的 skill 安装方式是**直接复制 skill 目录到 `~/.agents/skills/`**。

```bash
# 设置源路径（Windows 侧 releases 目录在 WSL 中映射为）
SKILLS_SRC="/mnt/d/code/huawei-cloudnative-skills/releases"

# 安装 devtools skill
cp -r "$SKILLS_SRC/devtools/huawei-cloud-cli-guidance" ~/.agents/skills/

# 安装全部 CCE skill（一键批量）
for skill_dir in "$SKILLS_SRC/container/cce"/*/; do
  skill_name=$(basename "$skill_dir")
  cp -r "$skill_dir" ~/.agents/skills/
  echo "Installed: $skill_name"
done

# 安装 SWR skill
for skill_dir in "$SKILLS_SRC/container/swr"/*/; do
  skill_name=$(basename "$skill_dir")
  cp -r "$skill_dir" ~/.agents/skills/
  echo "Installed: $skill_name"
done

# 安装 UCS skill
for skill_dir in "$SKILLS_SRC/container/ucs"/*/; do
  skill_name=$(basename "$skill_dir")
  cp -r "$skill_dir" ~/.agents/skills/
  echo "Installed: $skill_name"
done

# 安装 CCI skill（如果存在）
for skill_dir in "$SKILLS_SRC/container/cci"/*/; do
  skill_name=$(basename "$skill_dir")
  cp -r "$skill_dir" ~/.agents/skills/
  echo "Installed: $skill_name"
done
```

### 3.3 验证安装

```bash
# 确认目录存在
ls ~/.agents/skills/

# 确认 SKILL.md 文件完整
find ~/.agents/skills/ -name "SKILL.md" | wc -l
```

### 3.4 模型配置

aicli 的配置文件位于 `~/.huawei/aicli/settings.json`。当前配置使用百炼 (bailian) 提供商：

```json
{
  "current_model": "glm-5.1",
  "current_provider": "bailian",
  "providers": {
    "bailian": {
      "api": "openai-completions",
      "apikey": "<your-api-key>",
      "baseurl": "https://dashscope.aliyuncs.com/compatible-mode/v1",
      "models": [
        { "id": "glm-5", "name": "GLM-5", "contextwindow": 204800, "maxtokens": 131072 },
        { "id": "glm-5.1", "name": "GLM-5.1", "contextwindow": 204800 }
      ]
    },
    "huawei-inner-provider": {
      "baseurl": "https://tokenhub.developer.huaweicloud.com/v2",
      "models": [
        { "id": "deepseek-v4-flash" },
        { "id": "deepseek-v4-pro" }
      ]
    }
  }
}
```

参考 opencode 配置，百炼提供商的模型配置可以扩展为：

```json
{
  "providers": {
    "bailian": {
      "api": "openai-completions",
      "apikey": "sk-xxx",
      "baseurl": "https://dashscope.aliyuncs.com/compatible-mode/v1",
      "models": [
        { "id": "qwen3.6-plus", "name": "qwen3.6-plus", "contextwindow": 204800 },
        { "id": "glm-5.1", "name": "GLM-5.1", "contextwindow": 204800 },
        { "id": "glm-5", "name": "GLM-5", "contextwindow": 204800 },
        { "id": "glm-4.7", "name": "GLM-4.7", "contextwindow": 204800 }
      ]
    }
  }
}
```

### 3.5 使用方式

在 aicli 中，skill 通过**对话触发**自动激活：

```bash
# 启动 aicli
aicli

# 对话中自然触发 skill
> "帮我分析 CCE 集群 c1 的变更影响"
# aicli 会根据关键词匹配到 huawei-cloud-cce-change-impact-analyzer

> "hcloud 命令怎么配置认证"
# aicli 会匹配到 huawei-cloud-cli-guidance
```

aicli 也会通过 `/.agents/skills/.huawei/aicli/` 下的元数据来管理 skill 与 aicli 的关联。

### 3.6 skill 更新

```bash
# 删除旧版本再重新复制
rm -rf ~/.agents/skills/huawei-cloud-cce-cluster-management
cp -r "$SKILLS_SRC/container/cce/huawei-cloud-cce-cluster-management" ~/.agents/skills/
```

## 4. OpenClaw 部署

### 4.1 环境现状

- **已安装**：`/home/pan/.npm-global/bin/openclaw`
- **配置路径**：`/home/pan/.openclaw/openclaw.json`
- **Workspace**：`/mnt/d/pan/.openclaw/`（当前配置指向 Windows 侧路径）

OpenClaw 的 skill 加载路径（按优先级从高到低）：

| 优先级 | 来源 | 路径 |
|---|---|---|
| 1 | Workspace skills | `<workspace>/skills` |
| 2 | Project agent skills | `<workspace>/.agents/skills` |
| 3 | Personal agent skills | `~/.agents/skills` |
| 4 | Managed/local skills | `~/.openclaw/skills` |
| 5 | Bundled skills | 安装包内置 |
| 6 | Extra skill folders | `skills.load.extraDirs` 配置 |

> **关键发现**：aicli 的 `~/.agents/skills/` 正好是 OpenClaw 优先级 3 的路径！这意味着 aicli 已安装的 skill 会被 OpenClaw 自动发现和加载，无需额外操作。

### 4.2 安装步骤

**方案 A：共享 `~/.agents/skills/`（推荐）**

由于 aicli 和 OpenClaw 共用 `~/.agents/skills/`，只需按 aicli 章节的步骤将 skill 复制到该目录，OpenClaw 会自动发现。

```bash
# 无需额外操作，OpenClaw 会自动加载 ~/.agents/skills/ 下的所有 SKILL.md
# 验证
openclaw gateway status
openclaw skills list
```

**方案 B：安装到 workspace skills（更高优先级）**

如果某个 skill 需要 workspace 级别的控制，可以安装到 workspace 目录：

```bash
# 修正 workspace 路径为 WSL 本地路径（当前配置指向 Windows 侧，建议修改）
# 编辑 ~/.openclaw/openclaw.json，将 workspace 改为：
# "workspace": "/home/pan/.openclaw/workspace"

mkdir -p /home/pan/.openclaw/workspace/skills
cp -r "$SKILLS_SRC/devtools/huawei-cloud-cli-guidance" /home/pan/.openclaw/workspace/skills/
```

**方案 C：安装到 managed skills（全局共享）**

```bash
mkdir -p ~/.openclaw/skills
cp -r "$SKILLS_SRC/container/cce/huawei-cloud-cce-cluster-management" ~/.openclaw/skills/
```

**方案 D：使用 `extraDirs` 配置外部 skill 目录**

在 `~/.openclaw/openclaw.json` 中添加：

```json5
{
  skills: {
    load: {
      extraDirs: ["~/agents/skills"]
    }
  }
}
```

### 4.3 SKILL.md frontmatter 适配

OpenClaw 支持 [AgentSkills](https://agentskills.io) 规范，SKILL.md frontmatter 格式为：

```yaml
---
name: huawei-cloud-cce-change-impact-analyzer
description: CCE 变更影响分析
metadata: {"openclaw": {"requires": {"bins": ["hcloud"]}}}
---
```

华为云原生 skill 的 frontmatter 已包含 `name`、`description`、`tags`、`version` 字段，**兼容 OpenClaw 规范**。但 `id` 字段是华为自定义字段，OpenClaw 使用 `name` 作为标识。当前 skill 的 `id` 和 `name` 值一致，不会产生冲突。

对于含 Python 脚本的 skill（如 `scripts/huawei-cloud.py` dispatcher），需要在 frontmatter 中添加依赖声明：

```yaml
---
name: huawei-cloud-cce-change-impact-analyzer
description: CCE 变更影响分析
metadata: {"openclaw": {"requires": {"bins": ["python3", "hcloud"]}, "primaryEnv": "HCLOUD_ACCESS_KEY"}}
---
```

### 4.4 Agent skill allowlist

如果使用多 agent 配置，需要通过 allowlist 控制哪些 skill 对哪个 agent 可见：

```json5
{
  agents: {
    defaults: {
      skills: ["huawei-cloud-cli-guidance", "huawei-cloud-cce-cluster-management"]
    },
    list: [
      { id: "ops-agent", skills: ["huawei-cloud-cce-workload-failure-diagnoser", "huawei-cloud-cce-change-impact-analyzer"] }
    ]
  }
}
```

### 4.5 使用方式

OpenClaw 支持两种 skill 调用方式：

**1. Slash 命令**

```bash
# 在 OpenClaw TUI 或 WebChat 中
/huawei-cloud-cli-guidance
/huawei-cloud-cce-change-impact-analyzer 分析集群 c1 的近期变更
```

**2. 自然对话触发**

```bash
openclaw agent --message "帮我诊断 CCE 集群的工作负载故障" --thinking high
```

### 4.6 ClawHub 发布（可选）

如果希望将 skill 发布到 ClawHub 供其他 OpenClaw 用户安装：

```bash
openclaw skills install ./path/to/skill --as huawei-cloud-cce-cluster-management
```

或通过 ClawHub CLI：

```bash
clawhub sync --all
```

## 5. Hermes 部署

### 5.1 安装 Hermes（尚未安装）

> 详细安装过程见 `agent-installation-guide.md`。

快速安装（WSL）：

```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
source ~/.bashrc
hermes setup
```

### 5.2 Skill 加载机制

Hermes 的 skill 系统兼容 [agentskills.io](https://agentskills.io) 规范。skill 存储路径：

| 类型 | 路径 | 说明 |
|---|---|---|
| 本地 skill | `~/.hermes/skills/` | 主要存储位置，agent 可读写 |
| 外部 skill | 通过 `skills.external_dirs` 配置 | 扫描外部目录，本地优先 |

**关键发现**：Hermes 支持将 `~/.agents/skills/` 配置为外部目录，这意味着可以与 aicli/OpenClaw 共享 skill！

### 5.3 安装步骤

**方案 A：配置 `~/.agents/skills/` 为外部目录（推荐，共享 skill）**

在 `~/.hermes/config.yaml` 中添加：

```yaml
skills:
  external_dirs:
    - ~/.agents/skills
```

这样 Hermes 会自动发现 aicli/OpenClaw 已安装的所有 skill。

```bash
# 确认配置生效
hermes skills list
```

**方案 B：安装到 `~/.hermes/skills/`（独立管理）**

```bash
SKILLS_SRC="/mnt/d/code/huawei-cloudnative-skills/releases"

# 安装 devtools skill
cp -r "$SKILLS_SRC/devtools/huawei-cloud-cli-guidance" ~/.hermes/skills/

# 批量安装所有 container skill
for category in cce cci swr ucs; do
  if [ -d "$SKILLS_SRC/container/$category" ]; then
    for skill_dir in "$SKILLS_SRC/container/$category"/*/; do
      skill_name=$(basename "$skill_dir")
      cp -r "$skill_dir" ~/.hermes/skills/
      echo "Installed: $skill_name"
    done
  fi
done
```

**方案 C：通过 Skills Hub 安装（如果 skill 已发布到 hub）**

```bash
hermes skills install openai/skills/huawei-cloud-cce-cluster-management
# 或从 GitHub 仓库安装
hermes skills install git:owner/repo@ref
```

### 5.4 SKILL.md frontmatter 适配

Hermes 的 SKILL.md frontmatter 格式：

```yaml
---
name: huawei-cloud-cce-change-impact-analyzer
description: CCE 变更影响分析
version: 1.0.0
platforms: [linux]
metadata:
  hermes:
    tags: [cce, change-impact, risk-assessment]
    category: devops
    requires_toolsets: [terminal]
---
```

华为云原生 skill 的 `id`/`name`/`description`/`tags`/`version` 字段已兼容 Hermes 规范。需要适配的部分：

1. **`id` 字段** → Hermes 使用 `name` 作为标识，确保 `id` 和 `name` 值一致即可
2. **`platforms`** → 建议添加 `platforms: [linux]`（WSL 环境为 Linux）
3. **`metadata.hermes`** → 可选添加 `requires_toolsets: [terminal]`（含 Python 脚本的 skill 需终端执行）

对于含脚本的 skill，可添加环境变量声明：

```yaml
required_environment_variables:
  - name: HCLOUD_ACCESS_KEY
    prompt: Huawei Cloud Access Key
    help: 从华为云 IAM 控制台获取
    required_for: full functionality
```

### 5.5 Skill 分组

Hermes 支持 skill 按目录分组：

```
~/.hermes/skills/
├── huawei-cloud/                     # 分类目录
│   ├── huawei-cloud-cli-guidance/
│   │   └── SKILL.md
│   ├── huawei-cloud-cce-cluster-management/
│   │   └── SKILL.md
│   └── huawei-cloud-cce-workload-manager/
│   │   └── SKILL.md
│   └── ... (更多 CCE skill)
├── swr/
│   ├── huawei-cloud-swr-image-management/
│   └── ... (更多 SWR skill)
├── ucs/
│   ├── ucs-cluster-onboarding-manager/
│   └── ucs-policy-governor/
└── ...
```

分组只是组织方式，skill 的可见名称和 slash 命令仍由 `name` 字段决定。

### 5.6 Skill Bundle（组合调用）

可以将多个华为云 skill 组合成 bundle，一次加载多个 skill：

```bash
# 创建 CCE 诊断 bundle
hermes bundles create cce-diagnosis \
  --skill huawei-cloud-cce-workload-failure-diagnoser \
  --skill huawei-cloud-cce-pod-failure-diagnoser \
  --skill huawei-cloud-cce-node-failure-diagnoser \
  -d "CCE 集群故障诊断组合"
```

在对话中：

```
/cce-diagnosis 诊断集群 c1 的 Pod 故障
```

### 5.7 使用方式

**1. Slash 命令**

```
/huawei-cloud-cli-guidance
/huawei-cloud-cce-change-impact-analyzer 分析集群变更影响
/cce-diagnosis 诊断集群故障
```

**2. 自然对话触发**

```bash
hermes chat --toolsets skills -q "帮我分析 CCE 集群的变更影响"
```

**3. CLI 直接调用**

```bash
hermes chat -q "/huawei-cloud-cli-guidance 如何配置 hcloud 认证"
```

### 5.8 模型配置

Hermes 支持多种模型提供商。参考 opencode 配置，配置百炼提供商：

```bash
hermes model  # 交互式选择模型
```

或在 `~/.hermes/config.yaml` 中配置：

```yaml
provider: openai-compatible
model: glm-5.1
base_url: https://dashscope.aliyuncs.com/compatible-mode/v1
api_key: sk-xxx
```

使用 Nous Portal（一站式方案）：

```bash
hermes setup --portal
```

## 6. 三 Agent Skill 共享策略

### 6.1 共享架构图

```
~/.agents/skills/                        # aicli skill 路径 (优先级最高)
├── huawei-cloud-cli-guidance/
├── huawei-cloud-cce-cluster-management/
├── ... (所有华为云 skill)
│
│  ← OpenClaw 自动发现 (优先级 3)
│  ← Hermes 通过 external_dirs 配置发现
│
~/.openclaw/skills/                      # OpenClaw managed skills (优先级 4)
~/.hermes/skills/                        # Hermes 本地 skills (独立管理)
```

### 6.2 推荐方案

| 场景 | 推荐路径 | 说明 |
|---|---|---|
| 三个 agent 共享 skill | `~/.agents/skills/` | 最简方案，一份 skill 三处使用 |
| OpenClaw 需要覆盖某个 skill | `<workspace>/skills/` | workspace 级优先级最高 |
| Hermes 需要独立管理 skill | `~/.hermes/skills/` | 本地优先，覆盖外部目录同名 skill |
| 仅 aicli 使用 | `~/.agents/skills/` | 默认路径 |

### 6.3 注意事项

1. **同名 skill 冲突**：各 agent 按优先级加载，高优先级覆盖低优先级
2. **Python 脚本依赖**：含 `scripts/` 的 skill 需确保环境中有 `python3` 和相关依赖
3. **KooCLI 依赖**：多数华为云 skill 需要 `hcloud` CLI，确保已安装并配置认证
4. **skill 更新**：更新 `~/.agents/skills/` 中的 skill 后，需要重启 agent 或等待 skill watcher 热加载

## 7. 前置依赖安装

### 7.1 KooCLI

```bash
curl -sSL https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/hcloud_install.sh -o ./hcloud_install.sh && bash ./hcloud_install.sh -y
hcloud version  # 验证版本 >= 7.2.2
```

### 7.2 Python3

```bash
# WSL Ubuntu 通常自带 python3
python3 --version  # 需要 3.10+
pip3 install --user requests  # 部分 skill 脚本依赖
```

### 7.3 Node.js（OpenClaw 需要）

```bash
# 推荐 Node 24
node --version
# 如果缺失，安装
curl -fsSL https://deb.nodesource.com/setup_24.x | sudo -E bash -
sudo apt-get install -y nodejs
```

## 8. 故障排查

| 问题 | Agent | 解决方案 |
|---|---|---|
| Skill 未被识别 | aicli | 检查 `~/.agents/skills/<name>/SKILL.md` 文件存在且 frontmatter 正确 |
| Skill 未被识别 | OpenClaw | `openclaw skills list` 检查；确认路径在 skill root 中；重启 gateway |
| Skill 未被识别 | Hermes | `hermes skills list` 检查；确认 `external_dirs` 配置正确；重启 |
| Python 脚本执行失败 | 通用 | 检查 `python3 --version`；检查 `pip3` 依赖；检查 `scripts/huawei-cloud.py` 路径 |
| hcloud 命令失败 | 通用 | 检查 `hcloud version`；检查认证配置 `hcloud configure list` |
| 多 agent skill 冲突 | 通用 | 检查同名 skill 的优先级规则，确保使用正确的 skill root |

## 9. 批量安装脚本

以下一键脚本将所有 skill 安装到 `~/.agents/skills/` 并同时配置 Hermes 外部目录：

```bash
#!/bin/bash
SKILLS_SRC="/mnt/d/code/huawei-cloudnative-skills/releases"
SKILL_DIR="$HOME/.agents/skills"

echo "=== Installing Huawei Cloud Native Skills ==="

# Install all skills from devtools and container
for category in devtools; do
  for skill_dir in "$SKILLS_SRC/$category"/*/; do
    [ -d "$skill_dir" ] || continue
    skill_name=$(basename "$skill_dir")
    cp -r "$skill_dir" "$SKILL_DIR/"
    echo "  [OK] $skill_name"
  done
done

for category in cce cci swr ucs; do
  for skill_dir in "$SKILLS_SRC/container/$category"/*/; do
    [ -d "$skill_dir" ] || continue
    skill_name=$(basename "$skill_dir")
    cp -r "$skill_dir" "$SKILL_DIR/"
    echo "  [OK] $skill_name"
  done
done

echo ""
echo "=== Installed skills ==="
find "$SKILL_DIR" -name "SKILL.md" | sort

echo ""
echo "=== Configuring Hermes external_dirs ==="
HERMES_CONFIG="$HOME/.hermes/config.yaml"
if [ -f "$HERMES_CONFIG" ]; then
  echo "Hermes config exists, please manually add:"
  echo "  skills:"
  echo "    external_dirs:"
  echo "      - ~/.agents/skills"
else
  echo "Hermes not yet installed. After installation, add external_dirs to config.yaml."
fi

echo ""
echo "=== Done ==="
```

保存为 `install-skills.sh` 后执行：

```bash
chmod +x install-skills.sh
bash install-skills.sh
```