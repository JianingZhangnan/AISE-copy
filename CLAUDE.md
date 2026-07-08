# CLAUDE.md

本项目是《智能化软件工程师》课程期末大作业，选题为 **A · Coding Agent Harness**。

> **必读文档**（所有实现、文档、测试、分发与过程记录都必须对齐）：
> - `course_resource\AI4SE_Final_Project_通用要求.md`
> - `course_resource\AI4SE_Final_Project_A_Coding_Agent_Harness.md`
> - `SPEC.md`、`PLAN.md`、`SPEC_PROCESS.md`、`AGENT_LOG.md`（项目核心文档）

Superpowers 本地资源在 `.local\superpowers`；使用前先阅读 `.local\superpowers\skills\using-superpowers\SKILL.md`。

---

## 快速参考

| 项目 | 值 |
|------|-----|
| 仓库 | `JianingZhangnan/AISE-copy`（GitHub）；最终提交 **NJU Git** |
| CI | `.github/workflows/ci.yml`（必需）+ `.gitlab-ci.yml` 含 `unit-test`（必需） |
| 包管理器 | `uv`（禁用 pip/conda） |
| 分发 | PyPI 包（`uv publish`）|
| 语言 | 文档中文；代码/注释/Commit 英文 |

---

## TDD 工作流

**硬性要求**：先写失败测试（RED）→ subagent 写最少实现变绿（GREEN）→ 重构（REFACTOR）。不得先写实现再补测试。

**分工**：
- **父 agent** 负责编写失败测试（`tests/test_*.py`），确保测试先红。
- **subagent** 负责实现功能让测试变绿，再重构。
- subagent 完成后父 agent 做 spec 合规检查与代码质量检查。

---

## 核心原则

### Harness 实现边界（硬性）

必须自己实现：agent 主循环、mock/stub LLM 抽象层、工具分发、治理护栏、反馈回灌、记忆读写、停机。

**不允许**：直接使用 LangChain AgentExecutor、AutoGen、CrewAI 等现成高层 agent loop；用提示词代替代码机制；配置文件/提示词文件冒充 harness 内核。

**判定标准**：移除真实 LLM 后，核心机制仍能用确定性单元测试验证。

### 深度维度

**策略感知工具运行时（Policy-Aware Tool Runtime）**，融合治理护栏、反馈闭环和工具分发三个机制族。

---

## 过程纪律

- **工作流**：`brainstorming` → `writing-plans` → `using-git-worktrees` → `subagent-driven-development` → `test-driven-development` → `requesting-code-review` → `finishing-a-development-branch`。
- **worktree 约定**：每个可并行任务拉独立 worktree，分支名 `feat/Txx-<short-name>`。
- **task 完成标准**：`uv run pytest <path>` 全通过 → commit → 更新 `AGENT_LOG.md`（task 编号、commit hash、人工干预、教训）。
- **commit 格式**：`[Txx] <title>`，标注 subagent 和人工修改。
- **SPEC / PLAN / SPEC_PROCESS / AGENT_LOG** 为规约与过程文档，TDD 实现代码不得改动；如有合理偏离必须记录。

---

## 安全与凭据

- API key/token **绝不**硬编码、提交 Git、写日志/明文配置。
- 至少实现一种安全存储（OS 钥匙串 / KMS / 加密文件）。
- `.env` 仅作来源之一（明文风险需说明），**不得提交**。
- 首次运行引导用户安全录入 key；查看状态不回显明文。

---

## 仓库与 CI

- **GitHub 仓库**：`JianingZhangnan/AISE-copy`（当前开发平台）
- **最终提交**：NJU Git（镜像迁移，保留完整历史）
- **GitHub Actions**：`.github/workflows/ci.yml`，每次 push 自动运行测试
- **GitLab CI**（NJU Git 校验）：`.gitlab-ci.yml`，必须含 `unit-test` job
- CI/CD 最后一次执行**必须 pass**（课程硬性要求）

---

## 分发

- **形态**：PyPI 包（`uv publish`），用户通过 `uvx phycode` 或 `pip install phycode` 安装
- **README 必须包含**：项目简介、安装、运行、分发命令、目录结构、安全边界说明
- 本项目为纯 CLI，无 WebUI

---

## 文档语言

- 项目文档（SPEC.md、PLAN.md、SPEC_PROCESS.md、AGENT_LOG.md、README.md 等）：**中文**
- 代码注释和 commit message：**英文**
