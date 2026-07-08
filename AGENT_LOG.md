# PhyCode Agent 工作日志

本文档记录 PhyCode 项目开发过程中所有 agent/subagent 的工作内容、关键决策、commit 记录和人工干预情况。

## 日志格式说明

每条记录包含：
- **日期时间**：任务执行时间
- **任务编号**：对应 PLAN.md 中的任务 ID
- **Superpowers 技能**：使用的 Superpowers skill
- **Subagent ID**：subagent 标识符（如适用）
- **关键 Prompt/Context**：传递给 agent 的核心指令或上下文
- **主要输出**：agent 完成的工作和产出
- **Commit Hash**：相关的 git commit（如已提交）
- **人工干预**：人工修改、决策或纠正
- **教训与备注**：经验总结或注意事项

---

## 2026-07-08 — 项目启动与规划阶段

### [2026-07-08 08:00] Brainstorming 阶段

**技能**：`superpowers:brainstorming`

**主要输出**：
- 完成 PhyCode 项目的架构设计和技术选型讨论
- 确定核心深度维度为"策略感知工具运行时（Policy-Aware Tool Runtime）"
- 输出设计文档：`docs/superpowers/specs/2026-07-08-phycode-phase1-agent-harness-design.md`
- 完成正式规约文档：`SPEC.md`

**关键决策**：
1. 采用两阶段策略：Phase 1 为通用 Coding Agent Harness，Phase 2 扩展物理领域功能
2. 选择 Policy-Aware Tool Runtime 作为深度实现维度，融合工具分发、治理护栏和反馈闭环
3. 主接口为 CLI，无 WebUI
4. 使用 OpenAI 兼容 API 以支持本地模型和国产开源模型
5. 凭据优先使用系统钥匙串，回退到加密文件
6. 分发形态为 PyPI 包（通过 `uv publish`）

**人工干预**：无

**教训与备注**：
- SPEC.md 严格遵循了课程要求，包含所有必需章节（问题陈述、INVEST 用户故事、功能规约、非功能需求、系统架构、数据模型、技术选型、领域与机制设计、验收标准、风险与未决问题）
- 威胁模型和缓解措施在 §6.2 中详细说明
- SPEC 明确了"非目标"，避免范围蔓延

---

### [2026-07-08 09:01] Writing Plans 阶段

**技能**：`superpowers:writing-plans`

**Subagent ID**：`0d5a7587-8d97-4403-8d22-3b36fb2f79ca`

**关键 Prompt**：
> 基于已完成的 SPEC.md 创建 PLAN.md，将实现分解为可由单个 subagent 在一次会话内完成的具体任务。每个任务必须包含：目标、涉及文件、实现要点、要先写的失败测试、验证步骤、依赖关系和并行化标记。

**主要输出**：
- 创建 `PLAN.md`（约 1020 行）
- 定义了 17 个任务（T00-T16），从项目脚手架到最终文档
- 明确了 4 个并行窗口和任务依赖关系
- 每个任务都包含具体的测试文件、测试函数名和 pytest 验证命令

**任务结构**：
- **T00**：项目脚手架与 uv 配置
- **T01**：核心数据模型（Pydantic）
- **T02**：文件系统与工作区工具
- **T03**：配置加载
- **T04**：策略引擎（深度维度核心）
- **T05**：反馈分类器
- **T06**：工具注册表与运行时
- **T07**：内置工具实现（14 个工具）
- **T08**：LLM 适配器（mock + 真实）
- **T09**：上下文构建器与记忆
- **T10**：Agent 主循环
- **T11**：Trace 存储与脱敏
- **T12**：凭据管理
- **T13**：CLI 接口
- **T14**：确定性演示
- **T15**：CI 与打包
- **T16**：文档与分发说明

**Commit Hash**：（待提交）

**人工干预**：无

**教训与备注**：
- PLAN 严格遵循 TDD：每个任务都明确了要先写的失败测试
- 并行化策略清晰，可利用 git worktrees 加速开发
- 每个任务都有具体的 `uv run pytest` 验证命令
- 任务粒度合适，单个 subagent 可在一次会话内完成

---

### [2026-07-08 09:41] 创建 SPEC_PROCESS.md

**主要输出**：
- 创建 `SPEC_PROCESS.md`
- 记录了 brainstorming 的关键追问与 3 轮关键迭代
- 总结了 AI 建议的采纳与修正（含 4 项被采纳、4 项被推翻/修正）
- 记录了 SPEC/PLAN 的 3 项重要修订历史

**人工干预**：无

**教训与备注**：
- SPEC_PROCESS.md 是课程要求的交付物，记录规约制定过程的可追溯证据
- 必须包含"哪些 AI 建议被采纳/推翻/修正及原因"

---

### [2026-07-08 09:50] 陌生 Agent 冷启动验证

**Subagent ID**：`334063f6-80fd-4ab5-8fbc-31f3aa618773`

**关键 Prompt**：
> 你是一个全新启动的 agent，没有任何项目历史。请读取 SPEC.md、PLAN.md、CLAUDE.md，回答项目核心问题，并找出文档中的歧义、缺失、矛盾和可执行性问题。

**主要输出**：
- 完成对 SPEC.md / PLAN.md / CLAUDE.md 的全面审查
- 发现 **6 处文档矛盾**（C1-C6）
- 发现 **12 处缺失**（G1-G12）
- 给出 **20 项改进建议**（7 项 P0 + 7 项 P1 + 6 项 P2）
- 评分：目标/架构/TDD ★★★★★，可执行性 ★★★★☆，工程完整性 ★★★☆☆

**关键发现**：
- C1：SPEC §10 缺 `default.safe_allow` 和 `default.risky_action` rule_id
- C2：FeedbackKind 枚举缺 `repeat_stuck`
- C3：§7 模块列表缺 `tools.specs` 子模块
- C4：test.run 工具签名缺 `framework` 参数
- C5/C6：次要矛盾
- G1-G3：SPEC_PROCESS.md / AGENT_LOG.md / REFLECTION.md 占位缺失

**关于分支问题**：
冷启动验证**不需要新开 git 分支**——它是一个文档质量验证步骤，不涉及实际开发工作。所有修复都在当前分支进行。

**Commit Hash**：（待提交）

**人工干预**：根据验证报告，决定修复 7 项 P0 问题

**教训与备注**：
- 冷启动验证非常有效，暴露了文档中的多个隐患
- P0 问题如果不修复，后续 T03/T04/T11 任务中的 subagent 容易返工
- 验证方法是让一个全新 agent 阅读文档，模拟"陌生开发者"视角

---

### [2026-07-08 11:17] Git 仓库初始化

**操作**：
- 在 `d:\cs\AISE - Copy` 目录初始化本地 git 仓库
- 配置本地用户：`PhyCode Developer <phycode@example.com>`
- 扩展 `.gitignore` 覆盖 Python、构建产物、本地状态、IDE 文件
- 提交初始文档：`9db1c04 Initial: SPEC, PLAN, process docs and course resources`

**Commit Hash**：`9db1c04`

**包含文件**：
- `SPEC.md`、`PLAN.md`、`SPEC_PROCESS.md`、`AGENT_LOG.md`、`CLAUDE.md`
- `.gitignore`
- `course_resource/`（课程原始资料）
- `docs/superpowers/specs/`（brainstorming 设计笔记）

**关于 GitHub 仓库**：
- 暂未推送到 GitHub，因为需要用户提供以下信息：
  - GitHub 用户名/组织名
  - Personal Access Token (PAT)
  - 目标仓库名（CLAUDE.md 提到 `JianingZhangnan/AISE`）
- 创建 GitHub 仓库的步骤：
  1. 用户在 GitHub 上创建空仓库（不要初始化 README/.gitignore）
  2. 提供 Personal Access Token（需要 `repo` 权限）
  3. 添加远程源：`git remote add origin https://github.com/<user>/<repo>.git`
  4. 推送：`git push -u origin master`

**关于 CI/CD**：
- 课程明确要求 `.gitlab-ci.yml` 必须包含名为 `unit-test` 的 job
- CLAUDE.md §5.10 允许添加 GitHub Actions 但不取代 GitLab CI
- 推荐设置：
  - **GitLab CI**（必需）：`.gitlab-ci.yml` — 课程作业提交平台（如果用 NJU Git）
  - **GitHub Actions**（推荐）：`.github/workflows/ci.yml` — 当前开发平台使用
- CI 配置文件将在 T15 任务中创建

**人工干预**：用户提供 GitHub 凭证后才能推送

**教训与备注**：
- 本地 git 仓库是 GitHub 仓库的源，迁移到 NJU Git 时只需镜像
- CI 配置文件必须在 T15 任务中创建，不能提前添加（避免在脚手架不完整时 CI 失败）

---

### [2026-07-08 10:15] 修复 P0 级别文档问题

**Subagent ID**：`044261f7-867b-4bf8-988a-4705a81f4abc`

**关键 Prompt**：
> 帮我修复 PhyCode 项目 SPEC.md 和 PLAN.md 中的 P0 级问题。请直接输出 diff。

**修复内容**：

| P0 | 文件 | 修复 |
|----|------|------|
| P0-1 | SPEC.md §10 | 补充 `default.safe_allow` 和 `default.risky_action` rule_id |
| P0-2 | SPEC.md §5.7/§8 | FeedbackKind 枚举增加 `repeat_stuck` |
| P0-3 | SPEC_PROCESS.md | 已创建 ✅ |
| P0-4 | AGENT_LOG.md | 已创建 ✅ |
| P0-5 | SPEC.md §5.9 | 补充 policy override TOML schema |
| P0-6 | SPEC.md §5.5 | test.run 工具签名增加 `framework` 参数 |
| P0-7 | SPEC.md §7 | 模块列表增加 `tools.specs` 子模块 |
| P0-1 | PLAN.md §T01 | FeedbackKind 增加 `repeat_stuck` |

**Commit Hash**：（待提交）

**人工干预**：直接应用 subagent 提供的 diff

**教训与备注**：
- 修复了所有 P0 级问题，文档质量显著提升
- P1/P2 级问题可在后续任务执行中逐步修复
- 冷启动验证 + 修复循环是确保文档可执行性的关键步骤

---

## 下一步行动

根据 CLAUDE.md 的七步工作流，当前已完成：
1. ✅ `brainstorming`
2. ✅ `writing-plans`
3. ✅ `cold-start-validation`（冷启动验证）
4. ✅ `P0-fixes`（修复关键文档问题）

接下来应该：
5. ⏭ `using-git-worktrees` — 为并行任务创建隔离的 worktrees
6. ⏭ `subagent-driven-development` 或 `executing-plans` — 开始执行 PLAN.md 中的任务
7. ⏭ `test-driven-development` — 每个任务严格遵循 TDD
8. ⏭ `requesting-code-review` — 每个任务完成后请求代码审查
9. ⏭ `finishing-a-development-branch` — 完成后合并分支

**阶段门禁检查**：
- ✅ SPEC.md 已完成
- ✅ PLAN.md 已完成
- ✅ SPEC_PROCESS.md 已完成
- ✅ AGENT_LOG.md 已完成
- ✅ 冷启动验证已通过（发现并修复 7 项 P0 问题）
- ⏭ 现在可以开始执行 T00（项目脚手架）

---

## 待办事项

1. ⏭ 为 T00 任务创建 git worktree（可选，因为 T00 无前置依赖）
2. ⏭ 执行 T00：项目脚手架与 uv 配置
3. ⏭ 后续按 PLAN.md 依次执行 T01-T16
