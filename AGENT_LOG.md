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
- 推送至 GitHub：`JianingZhangnan/AISE-copy`（自动认证通过，无需手动 PAT）

**Commit Hash 序列**：
- `9db1c04` — Initial: SPEC, PLAN, process docs and course resources
- `2ce2719` — docs: log git init and CI/CD plan

**推送结果**：✅ 成功

---

### [2026-07-08 11:35] 修正文档中错误的 CI / 仓库策略信息

**触发原因**：用户指出仓库中存在错误信息；我随后查阅 `course_resource\AI4SE_Final_Project_通用要求.md` 发现三处关键错误：

1. **CI 平台错误**：CLAUDE.md 和 SPEC.md 写"`.gitlab-ci.yml` 必须包含 `unit-test` job"，但课程 §4.8 / §五明确要求 **GitHub Actions**（每次 push 自动运行测试）。
2. **提交平台错误**：CLAUDE.md 写"最终平台待定"，但课程 §五明确 NJU Git 是最终提交平台。
3. **GitHub 仓库名错误**：CLAUDE.md 残留旧仓库名 `JianingZhangnan/AISE`（另一个 agent 的实验），正确名应为 `JianingZhangnan/AISE-copy`（用户创建用于对比实验）。

**Subagent ID**：`6698fd40-11b1-4597-91d1-2f653e08351d`

**修改文件**：
- `CLAUDE.md` — 改写"当前仓库策略"和新增"CI / CD 要求（重要更正）"小节
- `SPEC.md` §5.10 — 明确 GitHub Actions 必需 + `.gitlab-ci.yml` 必需（用于 NJU Git 校验）；改写"仓库平台"为 NJU Git + AISE-copy
- `SPEC.md` §12 风险与应对 — 更新"最终仓库平台"
- `SPEC.md` §14 未决事项 — 更新"最终提交平台"
- `docs/superpowers/specs/...design.md` — 同步英文版的提交平台与 CI 说明
- `PLAN.md` §T15 — 标题改为"CI（GitHub Actions 必需 + GitLab CI 必需）"，把 GitHub Actions 配置从可选升为必需，并补充完整 steps

**修正后的核心事实**：
- **CI 必须同时配置**：`.github/workflows/ci.yml`（必需）+ `.gitlab-ci.yml`（必需，含 `unit-test` job）
- **最终提交平台**：NJU Git（以本地仓库为源镜像迁移）
- **CI/CD 最后一次执行必须 pass**（课程硬性要求）

**Commit Hash**：（待提交）

**教训与备注**：
- **课程原始资料必须在做任何架构决策前通读**——CLAUDE.md / SPEC.md 都基于"通用要求"和"A 题要求"，但本次发现 CLAUDE.md 对 CI 的理解是错的（写成 GitLab CI 而不是 GitHub Actions）。
- **冷启动验证时让 subagent 重读 `course_resource/`** 是有价值的；可让 subagent 在冷启动阶段就把项目要求与课程要求做一次交叉对照。
- **仓库命名**：本仓库 `AISE-copy` 是用户为对比实验特意创建；与 `AISE`（另一个 agent 的实现）是平行分支，文档里以后都应区分清楚。

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

### [2026-07-08 11:50] T00 — 项目脚手架与 uv 配置

**任务编号**：T00
**Superpowers 技能**：`test-driven-development`、`executing-plans`
**Subagent ID**：`t00-scaffolding-subagent-2026-07-08-1150`

**关键 Prompt**：
> 建立可分发的 Python 包骨架，使后续任务可立刻 `uv sync && uv run pytest` 运行。严格遵循 TDD：先写失败测试，看到红色，再写最少实现变绿，最后重构。

**主要输出**：
- 新建 `pyproject.toml`：声明 `name = "phycode"`、`version = "0.1.0"`、`requires-python = ">=3.11"`；依赖 `typer>=0.12, rich>=13, pydantic>=2, httpx>=0.27, keyring>=24, platformdirs>=4`；dev 依赖 `pytest>=8, pytest-cov, ruff, mypy`；`project.scripts` 暴露 `phycode = "phycode.cli.app:app"`；`[tool.pytest.ini_options]` 设 `testpaths = ["tests"]`、`addopts = "-ra -q"`、`pythonpath = ["src"]`
- 新建 `src/phycode/__init__.py`：仅暴露 `__version__ = "0.1.0"`
- 新建 `tests/__init__.py` 和 `tests/test_scaffolding.py`：包含 2 个失败用例（导入 `phycode` 验证版本号、`entry_points` 注册到 `phycode.cli.app`）
- 新建 `README.md`：占位说明（项目简介、安装命令、`make test`、待补充章节）
- 新建 `Makefile`：`test` / `lint` / `fmt` 三个 target，均通过 `uv run` 调用 pytest / ruff
- 新建 `.python-version`：固定为 `3.11`

**TDD 流程（红 → 绿）**：

**第 1 步（RED）**：
```
tests/test_scaffolding.py::test_package_importable FAILED
  ModuleNotFoundError: No module named 'phycode'
tests/test_scaffolding.py::test_cli_entrypoint_registered FAILED
  AssertionError: phycode console_scripts entry point not registered
============================== 2 failed in 0.69s ==============================
```

**第 2 步（GREEN）**：实现 scaffold 文件后
```
collected 2 items
tests\test_scaffolding.py ..                                             [100%]
============================== 2 passed in 0.04s ==============================
```

**第 3 步（REFACTOR）**：
- `ruff check .` → `All checks passed!`
- `ruff format .` → 重新格式化 1 个文件（test_scaffolding.py）
- `gmake test` → `uv run pytest → 2 passed`
- `gmake lint` → `All checks passed!`

**Commit Hash**：`488cf37`

**人工干预**：本次任务无需人工干预

**教训与备注**：
- **TDD 流程顺利**：先写测试、执行看到红色；再写 `pyproject.toml` 和 `src/phycode/__init__.py` 变绿。两个测试一开始就 FAILED（`import phycode` 模块未注册、`entry_points` 未注册），符合预期。
- **entry_points 的特殊处理**：测试通过 `ep.value.startswith("phycode.cli.app")` 校验 entry point 路径正确性，而不是 `ep.load()`，因为 `phycode.cli.app` 模块还不存在（T13 才创建）。这避免了测试对未实现模块的耦合。
- **Windows 环境注意**：
  - 系统默认 Python 是 3.12.7（Anaconda），但 `uv sync` 创建 `.venv` 使用 Python 3.11.12。需要用 `uv run pytest`（自动使用 `.venv`）才能正确运行测试。
  - dev 依赖通过 `uv sync --extra dev` 安装（`pytest`, `ruff`, `mypy`, `pytest-cov` 在 `[project.optional-dependencies]` 的 `dev` 分组下）。
  - `make` 在 Windows PowerShell 中不存在；用户机器上 `gmake.exe` 在 `D:\strawberry\c\bin\`，可用 `gmake test` 调用。后续 CI 使用 GitHub Actions 标准 `make` 即可。
  - git 自动 LF→CRLF 警告是 Windows 上的正常现象，可忽略。
- **项目命名澄清**：本地目录为 `AISE - Copy`，但 PyPI 包名为 `phycode`（符合课程要求）。后续发布到 PyPI 时包名为 `phycode`，用户通过 `uvx phycode` 或 `pip install phycode` 安装。
- **CI 兼容性**：pyproject.toml 使用 `hatchling` 作为 build backend（hatch 是 uv 默认推荐），与 uv 兼容性最好。
- **下个任务**：T01（核心数据模型 Pydantic），由独立 subagent 在 worktree 中执行。

---

### [2026-07-08 13:20] T01 — 核心 Pydantic 数据模型

**任务编号**：T01
**Superpowers 技能**：`test-driven-development`、`executing-plans`

**关键 Prompt**：
> 实现 `src/phycode/events/__init__.py` 和 `models.py`，包含 AgentEvent、ToolSpec、ToolCall、PolicyDecision、ToolResult、FeedbackSignal、MemoryEntry、Session 等 Pydantic 模型。先确认 RED（测试失败），再写最少实现变绿，最后重构。

**主要输出**：
- 新建 `src/phycode/events/__init__.py`：导出全部 14 个公开符号（AgentEvent、EventType、FeedbackKind 等）
- 新建 `src/phycode/events/models.py`：236 行，包含：
  - 6 个枚举类（EventType、RiskLevel、PolicyDecisionEnum、FeedbackKind、MemoryCategory、SessionMode），均使用 `StrEnum`
  - 9 个 Pydantic 模型（ToolSpec、ToolCall、ToolResult、PolicyDecision、FeedbackSignal、MemoryEntry、AgentEvent、Session）+ SCHEMA_VERSION
  - `FeedbackSignal` 带 `@model_validator` 实现动态 `retryable` 默认值（`command_failed`/`test_failed`/`tool_error`/`timeout` → `True`；其余 → `False`）

**TDD 流程（红 → 绿）**：

**第 1 步（RED）**：
```
ModuleNotFoundError: No module named 'phycode.events'
```
确认测试收集失败，红色状态正确。

**第 2 步（GREEN）**：创建 `__init__.py` + `models.py` 后
```
tests/test_events_models.py ...............................  [100%]
============================== 31 passed in 0.67s ==============================
```
全部 31 个测试通过。

**第 3 步（REFACTOR）**：
- `ruff check --fix --unsafe-fixes src/phycode/events/` → 全部自动修复（StrEnum 迁移、`Dict`→`dict` 等）
- `ruff format src/phycode/events/` → 2 个文件格式化
- `uv run ruff check src/phycode/events/` → `All checks passed!`

**Commit Hash**：`24558fd`

**人工干预**：无

**教训与备注**：
- **FeedbackSignal.retryable 动态默认值**：测试 `test_feedback_signal_retryable_true_on_failure` 不传 `retryable` 参数但断言 `fs.retryable is True`（对特定 `FeedbackKind`）。这要求在 Pydantic `model_validator` 中根据 `kind` 字段动态设置 `retryable`，而不是简单的 `bool = False` 默认值。
- **StrEnum 迁移**：Python 3.11+ 推荐使用 `enum.StrEnum` 替代 `str, Enum` 继承方式；ruff `--unsafe-fixes` 自动处理了全部 6 个枚举类。
- **Windows 兼容性**：`make` 命令不可用，用 `gmake` 或直接 `uv run`；git 自动 CRLF 转换是正常现象。
- **frozen=True + extra="forbid"**：所有模型使用 `frozen=True` 保证不可变性，`extra="forbid"` 拒绝未知字段，与测试期望一致。

---

### [2026-07-08 14:13] T02 — 文件系统与工作区解析工具函数

**任务编号**：T02
**Superpowers 技能**：`test-driven-development`、`executing-plans`

**主要输出**：
- 新建 `src/phycode/errors.py`：`PhyCodeError` 基类 + `PathEscapeError` 子类
- 新建 `src/phycode/paths.py`：实现路径安全操作的 4 个核心函数：
  - `resolve_workspace_path(root, requested)`：解析相对/绝对路径，处理 `..`/`.`，标准化分隔符
  - `is_within_allowed(root, candidate, allowlist)`：检查路径是否在根目录或白名单内
  - `symlink_escape(root, candidate)`：检测符号链接是否逃逸到根目录外
  - `safe_join(root, *parts)`：安全拼接路径，拒绝绝对路径和逃逸路径
- 新建 `tests/test_paths.py`：14 个测试用例

**Commit Hash**：`d0cc83d`

**教训与备注**：
- **Windows symlink 限制**：Windows 上创建 symlink 需要管理员或开发者模式，测试用 `pytest.skip` 优雅降级。
- **resolve(strict=False)**：Windows 上某些路径的 `resolve()` 会抛 OSError，用 `strict=False` 保证健壮性。
- **ruff UP035**：`Iterable` 从 `collections.abc` 导入（Python 3.9+）。

---

### [2026-07-08 14:22] T03 — 配置加载（`phycode.toml` + 用户配置目录）

**任务编号**：T03
**Superpowers 技能**：`test-driven-development`、`executing-plans`

**主要输出**：
- 新建 `src/phycode/config/__init__.py`：导出全部 6 个公开符号
- 新建 `src/phycode/config/models.py`：`UserConfig` 和 `ProjectConfig` Pydantic 模型
- 新建 `src/phycode/config/loader.py`：`load_project_config()` 和 `load_user_config()`，支持 TOML 解析、未知字段警告、Pydantic 校验
- 新建 `tests/test_config_loader.py`：8 个测试用例
- 新建 `tests/fixtures/phycode_minimal.toml`：测试固件

**Commit Hash**：`5fcfc9d`

**教训与备注**：
- **Pydantic v2 API**：使用 `model_fields.keys()` 获取字段名集合（v2 FieldInfo 对象没有 `.name` 属性）
- **Python 3.11+ 内置 tomllib**：无需 tomli 回退
- **frozen=True + extra="allow"**：不可变配置 + 接受扩展字段
- **未知字段警告机制**：不在 model_fields 中的键记录 warning 但不抛异常

---

## 2026-07-09 — 核心机制实现阶段

### [2026-07-09 13:54] T04 — 策略引擎（深度维度核心）

**任务编号**：T04
**Superpowers 技能**：`test-driven-development`、`executing-plans`

**主要输出**：
- 新建 `src/phycode/policy/__init__.py`：导出 `PolicyEngine`、`PolicyContext`、`ApprovalMachine` 等
- 新建 `src/phycode/policy/engine.py`：`PolicyEngine.evaluate()` 方法，支持运行时覆盖、项目覆盖、默认规则三层决策
- 新建 `src/phycode/policy/rules.py`：`DEFAULT_RULES` 列表，包含 8 条规则：
  - `shell_dangerous_block`：危险命令黑名单
  - `credential_files_blocked`：凭据文件保护
  - `symlink_safe`：符号链接逃逸检测
  - `write_outside_workspace`：工作区外写入阻止
  - `path_in_workspace`：路径工具边界检查
  - `shell_safe`：安全 shell 命令放行
  - `safe_allow`：安全工具默认放行
  - `risky_action`：风险操作需审批
- 新建 `src/phycode/policy/dangerous_patterns.py`：跨平台危险命令模式库（rm -rf、SQL DROP、curl|wget|sh 等）
- 新建 `src/phycode/policy/approval.py`：`ApprovalMachine` 状态机（pending → user_prompted → approved|blocked）
- 新建测试：`test_policy_engine.py`（9 测试）、`test_policy_approval.py`（6 测试）、`test_dangerous_patterns.py`（28 测试）

**修复的问题**：
1. **规则顺序修复**：`shell_dangerous_block` 必须在 `safe_allow` 之前，避免危险命令被误判为安全
2. **凭据规则修复**：凭据文件规则必须在 `safe_allow` 之前
3. **ApprovalMachine KeyError vs ValueError**：区分"从未请求过审批"（KeyError）和"状态不对"（ValueError）
4. **Windows 危险命令模式**：添加 `rm -rf \Windows\System32` 等反斜杠路径检测

**TDD 流程（红 → 绿）**：

第 1 步（RED）：worktree 中有部分实现但 3 个测试失败
```
FAILED tests/test_policy_engine.py::test_project_override_beats_default
FAILED tests/test_policy_approval.py::test_unknown_tool_call_id_raises
FAILED tests/test_dangerous_patterns.py::test_dangerous_command_blocked[rm -rf \\Windows\\System32]
```

第 2 步（GREEN）：修复后
```
======================== 44 passed, 1 skipped in 0.36s ========================
```

**Commit Hash**：`d7ac0ed`

**人工干预**：修复了以下问题：
- 重排 `DEFAULT_RULES` 顺序
- 修复 `ApprovalMachine._pending_ids` 区分 KeyError 和 ValueError
- 添加 Windows 反斜杠危险命令模式
- 修复 `test_policy_approval.py::_pending()` 辅助函数

**教训与备注**：
- **规则顺序至关重要**：`PolicyEngine.evaluate()` 按顺序遍历 `DEFAULT_RULES`，更具体/危险的规则必须在前
- **ApprovalMachine 状态机设计**：用 `_pending_ids` set 区分"从未进入审批流程"和"正在等待用户输入"
- **跨平台危险模式**：`rm -rf \Windows\System32` 使用反斜杠，需要单独的 regex 模式
- **Windows git warning**：LF→CRLF 转换警告是正常现象，测试不受影响

---

## 阶段门禁检查

根据 CLAUDE.md 的七步工作流，当前已完成：
1. ✅ `brainstorming`
2. ✅ `writing-plans`
3. ✅ `cold-start-validation`（冷启动验证）
4. ✅ `P0-fixes`（修复关键文档问题）
5. ✅ `T00` — 项目脚手架与 uv 配置（`488cf37`）
6. ✅ `T01` — 核心数据模型（`24558fd`）
7. ✅ `T02` — 文件系统与工作区工具（`d0cc83d`）
8. ✅ `T03` — 配置加载器（`5fcfc9d`）
9. ✅ `T04` — 策略引擎（`d7ac0ed`）

---

## 待办事项

1. ✅ 执行 T04：策略引擎（深度维度核心）（`d7ac0ed`）
2. ⏭ 执行 T05：反馈分类器
3. ⏭ 执行 T06：工具注册表与运行时
4. ⏭ 执行 T07：内置工具实现
5. ⏭ 执行 T08：LLM 适配器
6. ⏭ 执行 T09：上下文构建器与记忆
7. ⏭ 执行 T10：Agent 主循环
8. ⏭ 执行 T11：Trace 存储与脱敏
9. ⏭ 执行 T12：凭据管理
10. ⏭ 执行 T13：CLI 接口
11. ⏭ 执行 T14：确定性演示
12. ⏭ 执行 T15：CI 与打包
13. ⏭ 执行 T16：文档与分发说明
