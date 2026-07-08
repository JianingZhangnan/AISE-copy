# PhyCode 实现计划

本文档遵循 Superpowers `writing-plans` 流程，由已批准的 `SPEC.md` 沉淀而来。代码、测试、CI、分发与文档的工程取舍一律以 `SPEC.md` 为准；本计划仅负责把这些决策拆分成可由单个 subagent 在一次会话内完成的、可验证、可并行的具体任务。

## 0. 总体策略

- 任务编号 `Txx`；同一阶段可并行的任务标记 `[PARALLEL]`。
- 每个任务都遵守 TDD：先写失败测试并确认 pytest 报告红色，再写最少实现变绿，最后重构。
- 每个任务在完成时必须：
  - 执行 `uv run pytest <path>` 全部通过。
  - 在 `AGENT_LOG.md` 追加一条记录，包含 subagent 名称、commit hash、关键 prompt 与人工修改。
  - 对应 commit message 标注 `[Txx] <title>`。
- 工作流守则：`subagent-driven-development`（每任务一个新 subagent） + `test-driven-development` + `requesting-code-review`（每任务后由父 agent 检阅 spec 合规与代码质量）。
- worktree 使用约定：每个 `[PARALLEL]` 任务拉独立 worktree，从 `main` 分支派生，分支名 `feat/Txx-<short-name>`；完成后合并回 `main`。

## 1. 任务依赖总览

```
T00 -> T01 -> T02,T03,T04
              |       |
              |       +--> T05,T06 -> T07 -> T08 -> T10 -> T11 -> T12,T13,T14 -> T15 -> T16
              |
              +--> (T02,T03 已就绪后)
                   T08[PARALLEL with T07,T04 子部分]
                   T11[PARALLEL after T02]
```

层级一（基础设施）：T00, T01, T02, T03
层级二（核心机制）：T04 (policy), T05 (feedback), T06 (tool registry), T07 (built-in tools), T08 (LLM adapters), T09 (context/memory), T10 (agent loop), T11 (trace store), T12 (credentials)
层级三（产品外层）：T13 (CLI), T14 (demos), T15 (CI + packaging), T16 (docs + distribution)

并行窗口：
- 窗口 A（T03 完成后）：T04 / T05 / T11 可并行。
- 窗口 B（T04+T05+T06+T07+T08+T09+T10+T11 完成后）：T12 / T13 / T14 可并行。
- T15 / T16 在 T13 完成后并行。

---

## T00 — 项目脚手架、`uv` 与 `pyproject.toml`

**目标**：建立可分发的 Python 包骨架，使后续任务可立刻 `uv sync && uv run pytest` 运行。

**涉及文件**：

- 新建 `pyproject.toml`
- 新建 `README.md`（占位说明即可，详细文档由 T16 完成）
- 新建 `src/phycode/__init__.py`
- 新建 `tests/__init__.py`
- 新建 `.python-version`
- 修改 `.gitignore`（加入 `.phycode/`、`dist/`、`build/`、`*.egg-info`）
- 新建 `Makefile`（至少包含 `test`、`lint`、`fmt` 三个 target，最终 demo 命令在 T14 中追加）

**实现要点**：

- 在 `pyproject.toml` 中声明：
  - `name = "phycode"`, `version = "0.1.0"`, `requires-python = ">=3.11"`。
  - 依赖：`typer>=0.12`、`rich>=13`、`pydantic>=2`、`httpx>=0.27`、`keyring>=24`、`platformdirs>=4`。
  - dev 依赖：`pytest>=8`、`pytest-cov`、`ruff`、`mypy`。
  - `project.scripts` 暴露 `phycode = "phycode.cli.app:app"`。
- `[tool.pytest.ini_options]` 设 `testpaths = ["tests"]`、`addopts = "-ra -q"`。
- `src/phycode/__init__.py` 仅暴露 `__version__`。
- `Makefile` 中 `test` 目标调用 `uv run pytest`。

**先写的失败测试**（`tests/test_scaffolding.py`）：

- `test_package_importable`：导入 `phycode`，断言 `phycode.__version__` 是字符串且形如 `0.1.0`。
- `test_cli_entrypoint_registered`：调用 `importlib.metadata.entry_points(group="console_scripts")`，过滤 `name == "phycode"`，断言存在并能 `load()`。

**验证步骤**：

```bash
uv sync
uv run pytest tests/test_scaffolding.py -v
```

**依赖**：无（首任务）。

**并行**：否（前置任务）。

---

## T01 — 核心数据结构与 Pydantic 基础模型

**目标**：定义 `AgentEvent`、`ToolSpec`、`ToolCall`、`PolicyDecision`、`ToolResult`、`FeedbackSignal`、`MemoryEntry`、`Session`、`ProviderConfig` 等数据模型，作为整个 harness 的“总线”。

**涉及文件**：

- 新建 `src/phycode/events/__init__.py`
- 新建 `src/phycode/events/models.py`
- 新建 `tests/test_events_models.py`

**实现要点**：

- 使用 `pydantic.BaseModel`，开启 `model_config = ConfigDict(frozen=True, extra="forbid")`。
- 枚举定义：
  - `EventType`：与 SPEC §5.4 一一对应（`assistant_commentary`、`reasoning_summary`、`tool_call_requested`、`policy_decision`、`tool_call_running`、`tool_call_output`、`feedback_signal`、`assistant_final`、`error`、`incomplete`、`user_interrupt`）。
  - `RiskLevel`：`safe | risky | dangerous`。
  - `PolicyDecisionEnum`：`allow | ask | deny`。
  - `MemoryCategory`：`decision | preference | project_fact | test_command`。
  - `FeedbackKind`：`success | command_failed | test_failed | policy_blocked | policy_requires_approval | invalid_tool_args | tool_error | timeout | output_truncated | repeat_stuck`。
  - `FeedbackKind` 中追加 `repeat_stuck`：同一工具+相似参数连续失败 ≥3 次时触发。
  - `SessionMode`：`interactive | non_interactive`。
- 每个模型提供：
  - `id`：默认 `uuid4` 字符串字段；`Session` 与 `AgentEvent` 包含 `session_id`、`timestamp`（ISO 8601 字符串，UTC）。
  - `redaction_status`：可选枚举 `unknown | clean | redacted`。
- `PolicyDecision` 字段：`tool_call_id`、`decision`、`rule_id`、`reason`、`requires_user: bool`。
- `FeedbackSignal` 字段：`kind`、`summary`、`evidence: dict[str, Any]`、`retryable: bool`、`suggested_next_step: Optional[str]`。
- 模块级 `SCHEMA_VERSION = "1"` 常量，供 trace 文件头使用。

**先写的失败测试**（`tests/test_events_models.py`）：

- `test_agent_event_minimal_payload_round_trip`：构造一个 `AgentEvent(type="assistant_commentary", payload={"text": "hi"})`，序列化为 dict、再 `model_validate` 回去，断言等价。
- `test_policy_decision_enum_validation`：传入非法 `decision="maybe"`，断言抛 `ValidationError`。
- `test_feedback_signal_defaults_retryable_false`：构造 `FeedbackSignal(kind="success", summary="ok", evidence={})`，断言 `retryable is False`、`suggested_next_step is None`。
- `test_extra_fields_forbidden`：在 `ToolCall` 上塞入未声明字段，断言 `extra="forbid"` 生效。

**验证步骤**：

```bash
uv run pytest tests/test_events_models.py -v
```

**依赖**：`T00`。

**并行**：是，可与 `T02`、`T03` 在同一 worktree 阶段并行（不同文件）。

---

## T02 — 文件系统与工作区解析工具函数

**目标**：把所有“路径相关”的原子操作集中起来，供后续 policy / tool / config 模块共享：解析相对路径为绝对路径、检测符号链接逃逸、判断路径是否在工作区根或 allowlist 内、规范化路径分隔符（兼容 Windows 与 POSIX）。

**涉及文件**：

- 新建 `src/phycode/paths.py`
- 新建 `tests/test_paths.py`

**实现要点**：

- 函数清单：
  - `resolve_workspace_path(root: Path, requested: str) -> Path`：解析 `requested` 相对 `root`，对 `..` 与平台规范化。
  - `is_within_allowed(root: Path, candidate: Path, allowlist: Iterable[Path]) -> bool`：先 `resolve`，再对 `root` 与每个 allowlist 项做 `Path.is_relative_to`（Python 3.9+）；若不存在检测 `_parts` 关系。
  - `symlink_escape(root: Path, candidate: Path) -> bool`：使用 `os.path.realpath` 与 `os.lstat` 检查是否存在符号链接并指向允许根之外。
  - `safe_join(root: Path, *parts: str) -> Path`：禁止结果路径逃逸 `root`，否则抛 `PathEscapeError`。
- 全部 API 同步 + 异步安全（即纯 CPU，不发起 IO 假设）。
- 异常类型 `PathEscapeError(PhyCodeError)`；新建 `src/phycode/errors.py` 暴露基础异常 `PhyCodeError`。
- 逻辑不依赖文件系统实际存在；通过 `tmp_path` fixture 覆盖真实 IO 测试。

**先写的失败测试**（`tests/test_paths.py`）：

- `test_resolve_workspace_path_strips_relative_dots`：使用 `tmp_path`，在子目录建文件，请求 `"./sub/file"`，断言解析为 `root / "sub" / "file"`。
- `test_safe_join_blocks_parent_escape`：`safe_join(root, "..", "evil")` 必须抛 `PathEscapeError`。
- `test_symlink_escape_detected_outside_root`：用 `tmp_path` 创建符号链接到 `/tmp` 或 `%TEMP%` 之外，断言 `symlink_escape` 返回 `True`。
- `test_is_within_allowed_respects_extra_root`：root 与额外 allowlist，候选落在 allowlist 内仍返回 `True`。

**验证步骤**：

```bash
uv run pytest tests/test_paths.py -v
```

**依赖**：`T00`。

**并行**：是，与 `T01`、`T03` 并行。

---

## T03 — 配置加载（`phycode.toml` + 用户配置目录）

**目标**：提供项目级 `phycode.toml` 与用户级 `config.toml` 的加载、合并、校验。

**涉及文件**：

- 新建 `src/phycode/config/__init__.py`
- 新建 `src/phycode/config/loader.py`
- 新建 `src/phycode/config/models.py`
- 新建 `tests/test_config_loader.py`
- 新建 `tests/fixtures/phycode_minimal.toml`（最小可解析样例）

**实现要点**：

- 模型：`UserConfig`（默认供应商、`base_url`、`model`）、`ProjectConfig`（`workspace_root`、`allowlist`、`test_command`、`enabled_tools`、`policy_overrides`、`feedback_overrides`）。
- 加载流程：
  - 用户配置目录来自 `platformdirs.user_config_dir("phycode", appauthor=False)`，文件 `config.toml`，缺省安全 fallback。
  - 项目配置从 CWD 向上查找 `phycode.toml`，最多查到 `git` 边界或文件系统根。
  - 项目覆盖用户；重复字段：用户级 `default_provider` 仅在项目未设置时生效。
- 解析用 `tomllib`（3.11+ 内置）+ `pydantic` 校验；对未知字段报 warn 但不报错。
- 抛 `ConfigError(PhyCodeError)`。

**先写的失败测试**（`tests/test_config_loader.py`）：

- `test_load_project_config_minimal`：使用 `tmp_path` 放置 `tests/fixtures/phycode_minimal.toml` 的副本，调用 `load_project_config(tmp_path)`，断言 `test_command == "uv run pytest"`。
- `test_user_config_overlays_when_project_missing`：在 `tmp_path` 写入用户配置 `config.toml` 与项目根目录，断言 `UserConfig.default_provider` 生效。
- `test_project_overrides_user`：项目设置 `test_command = "make test"`，断言最终生效为项目值。
- `test_unknown_key_warns_does_not_raise`：TOML 中加入未知 `foo = 1`，断言不抛异常且被记录到 logger（`caplog`）。

**验证步骤**：

```bash
uv run pytest tests/test_config_loader.py -v
```

**依赖**：`T00`、`T01`（事件模型/枚举）。

**并行**：是，可与 `T04`、`T11` 在 T02 后并行。

---

## T04 — 策略引擎（核心深度维度）

**目标**：实现确定性策略引擎，对每次工具调用返回 `allow | ask | deny`，并附 `rule_id`、`reason`。

**涉及文件**：

- 新建 `src/phycode/policy/__init__.py`
- 新建 `src/phycode/policy/engine.py`
- 新建 `src/phycode/policy/rules.py`
- 新建 `src/phycode/policy/dangerous_patterns.py`
- 新建 `src/phycode/policy/approval.py`（审批状态机：`pending → user_prompted → approved|rejected → executed|blocked`）
- 新建 `tests/test_policy_engine.py`
- 新建 `tests/test_policy_approval.py`
- 新建 `tests/test_dangerous_patterns.py`

**实现要点**：

- `engine.evaluate(tool_call: ToolCall, tool_spec: ToolSpec, ctx: PolicyContext) -> PolicyDecision`。
- `PolicyContext` 字段：`workspace_root`、`allowlist: list[Path]`、`policy_overrides`、`dry_run: bool`、`approval_state`。
- 规则匹配顺序：
  1. 内置默认规则（`policy/rules.py` 中的有序列表，rule_id 前缀 `default.`）。
  2. 项目 `phycode.toml` 中的 `[tool.phycode.policy.overrides]`（rule_id 前缀 `project.`）。
  3. 运行时临时决议（仅 interactive 模式存在，rule_id 前缀 `runtime.`）。
- 规则条目结构：`name`、`match`（`tool_name` 全名或 `prefix.*` + 可选 `path_glob`）、`decision`、`reason`。
- 默认规则：
  - `default.path_in_workspace`：路径类工具必须落在 `workspace_root` 或 `allowlist`，否则 `deny`。
  - `default.symlink_safe`：符号链接逃逸 → `deny`。
  - `default.credential_files_blocked`：读取 `.env`、`*.pem`、`*.key`、`id_rsa` 等 → `deny`。
  - `default.shell_safe_commands`：`safe.risk_level` 工具在 `tool.risk_level == safe` 时 → `allow`。
  - `default.shell_risky_default`：文件写入/编辑/记忆写入/配置写入/大多数 shell → `ask`。
  - `default.shell_dangerous_block`：匹配 `dangerous_patterns` 的命令 → `deny`。
  - `default.write_outside_workspace`：写入超出 `workspace_root` → `deny`。
- `dangerous_patterns.py`：导出 `DANGEROUS_COMMAND_PATTERNS: list[CompiledRegex]`，覆盖：
  - `rm\s+-rf\s+/`、`rm\s+-rf\s+~`、`format\s+`、`mkfs`、`dd\s+if=.*of=/dev/`。
  - `DROP\s+TABLE`、`DELETE\s+FROM`、`TRUNCATE`。
  - `curl\s+.*\|\s*(sudo\s+)?sh`、`wget\s+.*\|\s*sh`。
  - `chmod\s+777`、`chown\s+-R`、`shutdown`、`reboot`、`poweroff`。
  - Windows：`del\s+/[s/q]\\.*`、`rd\s+/s\\.*`、`Remove-Item\s+-Recurse\s+.*\\\\`。
  - 跨平台通用：`:\(\)\{.*\|.*&\}\s*;:` 等 fork bomb。
- 引擎为纯函数：除 `approval_state`（由 CLI 注入）外，不发起 IO。
- `approval.py` 提供 `ApprovalMachine`，对外 API：
  - `decide(tool_call, decision) -> ApprovalAction`，其中 `decision in {"approved", "rejected"}`。
  - 状态转换日志记入 `events.AgentEvent(type="policy_decision", ...)`。
- 集成点：策略结果在 trace 中强制写入 `rule_id`、`reason`，便于审计与 demo。

**先写的失败测试**（按测试文件）：

`tests/test_dangerous_patterns.py`：

- `test_dangerous_rm_rf_root_blocked`：`rm -rf /` → 至少命中一条规则。
- `test_benign_command_not_matched`：`pytest -q` → 不命中。
- `test_fork_bomb_blocked`：bash fork bomb → 命中。

`tests/test_policy_engine.py`：

- `test_safe_read_inside_workspace_allows`：`file.read` 路径 `/workspace/README.md` → `decision == "allow"`、`rule_id == "default.safe_allow"`。
- `test_workspace_escape_denies`：`file.write` 路径 `../etc/passwd` → `deny`。
- `test_credential_read_denied`：`file.read` 路径 `.env` → `deny`，`rule_id == "default.credential_files_blocked"`。
- `test_file_write_requires_approval`：写入工作区内文件 → `ask`、`rule_id == "default.risky_action"`。
- `test_dangerous_shell_denied`：`shell.run` 命令 `rm -rf /` → `deny`、`rule_id == "default.shell_dangerous_block"`。
- `test_project_override_beats_default`：在 `phycode.toml` 中将 `default.safe_allow` 改为 `ask`，对应调用应得 `ask`。
- `test_symlink_escape_denied`：跨 worktree 创建 symlink 指向外部目录，读取它 → `deny`。

`tests/test_policy_approval.py`：

- `test_pending_to_user_prompted_to_approved`：`ApprovalMachine` 三步推进后状态为 `approved`。
- `test_rejected_blocks_tool_call`：拒绝后状态为 `blocked`。
- `test_reapprove_required_after_reject`：rejected 后同一 `tool_call_id` 再次请求必须重新发起审批。

**验证步骤**：

```bash
uv run pytest tests/test_policy_engine.py tests/test_policy_approval.py tests/test_dangerous_patterns.py -v
```

**依赖**：`T01`、`T02`、`T03`。

**并行**：与 `T05`、`T11` 并行（依赖交叉但文件不冲突）。

---

## T05 — 反馈分类器

**目标**：将 `ToolResult` 映射为 `FeedbackSignal`，提供确定性测试结果解析与重复失败检测。

**涉及文件**：

- 新建 `src/phycode/feedback/__init__.py`
- 新建 `src/phycode/feedback/classifier.py`
- 新建 `src/phycode/feedback/test_parsers.py`
- 新建 `src/phycode/feedback/repeat.py`
- 新建 `tests/test_feedback_classifier.py`
- 新建 `tests/test_test_parsers.py`
- 新建 `tests/test_repeat_detection.py`

**实现要点**：

- `classify(result: ToolResult, context: FeedbackContext) -> list[FeedbackSignal]`：可能返回多个信号（例如 `test_failed + output_truncated`）。
- 分类规则优先级：
  1. `timeout`（依据 `result.timed_out`） → 永远单独返回。
  2. `policy_blocked` / `policy_requires_approval` → 当 `result.status == "policy_denied"` 或 `policy_asked`。
  3. `invalid_tool_args` → 由上游 schema 校验器标 `args_invalid=True`。
  4. `command_failed` → `exit_code != 0` 且非测试命令。
  5. `test_failed` → 通过 `test_parsers` 解析输出；若解析不到按 `tool_error`。
  6. `output_truncated` → `truncated is True` 时追加。
  7. `success` → 其他情况。
- `test_parsers.py`：暴露 `parse_pytest(output: str) -> TestSummary`、`parse_jest(output: str)`、`parse_go_test(output: str)`，结构：
  ```python
  class TestSummary(BaseModel):
      framework: Literal["pytest", "jest", "go", "unknown"]
      passed: int
      failed: int
      skipped: int
      failures: list[TestFailure]  # name, message
  ```
- `repeat.py`：维护最近 N（默认 5）个工具调用的 `(tool_name, args_signature, feedback_kind)` 指纹；同一指纹连续出现 ≥3 次 → 返回 `kind="repeat_stuck"`、`suggested_next_step="ask_user_for_guidance"`、`retryable=False`。
- `args_signature`：对 args 中 path 类字段按 `paths.resolve_workspace_path` 规范化，对 shell 命令去除多余空白并归一化环境变量。

**先写的失败测试**：

`tests/test_feedback_classifier.py`：

- `test_success_when_exit_zero_and_clean`：exit 0、stdout 短、无 policy → `[success]`。
- `test_command_failed_when_nonzero_exit`：exit 1、stderr 非空 → `[command_failed]`。
- `test_policy_denied_returns_policy_blocked`：`status == "policy_denied"` → `[policy_blocked]`。
- `test_truncation_appends_secondary_signal`：长输出 + `truncated=True` → `[command_failed, output_truncated]` 或对应成功类别 + `output_truncated`。
- `test_invalid_tool_args_preempts_other_kinds`：`args_invalid=True` → `[invalid_tool_args]`。

`tests/test_test_parsers.py`：

- `test_pytest_parser_counts`：固定样例输出断言 `passed == 3`、`failed == 1`、`failures[0].name == "test_x"`。
- `test_unknown_output_marks_framework_unknown`：垃圾输出 → `framework == "unknown"`、`failed == 0`。
- `test_jest_parser_basic`。

`tests/test_repeat_detection.py`：

- `test_three_repeats_flag_repeat_stuck`：三次相同 `(tool_name, normalized_args, command_failed)` → 第四个返回 `repeat_stuck`。
- `test_distinct_args_not_counted`：变参 → 不触发。

**验证步骤**：

```bash
uv run pytest tests/test_feedback_classifier.py tests/test_test_parsers.py tests/test_repeat_detection.py -v
```

**依赖**：`T01`、`T02`。

**并行**：与 `T04`、`T11` 并行。

---

## T06 — 工具注册表与执行运行时

**目标**：实现工具注册中心 + 策略感知工具运行时（Policy-Aware Tool Runtime）的统一入口：`validate_args → check_policy → execute → map_feedback → record_trace`。

**涉及文件**：

- 新建 `src/phycode/tools/__init__.py`
- 新建 `src/phycode/tools/registry.py`
- 新建 `src/phycode/tools/runtime.py`
- 新建 `src/phycode/tools/specs.py`（统一 `ToolSpec` 定义与帮助器）
- 新建 `tests/test_tool_registry.py`
- 新建 `tests/test_tool_runtime.py`

**实现要点**：

- `registry.ToolRegistry`：
  - API：`register(spec: ToolSpec)`、`get(name) -> ToolSpec`、`names() -> list[str]`、`for_each(callable)`。
  - 内置工具构造在 `T07` 中完成；本任务负责容器而非内容。
- `runtime.ToolRuntime`：
  - 构造接受 `registry`、`policy_engine`、`feedback_classifier`、`trace_store`、`approval_machine`、`clock`。
  - `invoke(tool_call: ToolCall, ctx: RuntimeContext) -> RuntimeOutcome`：
    1. `validate_args`：基于 `ToolSpec.input_schema`（pydantic）校验；失败 → `ToolResult(status="args_invalid")` + 返回。
    2. `check_policy`：调用 `policy_engine.evaluate`；`deny` → 返回 `policy_denied` 结果；`ask` → 通过 `approval_machine` 决定。
    3. `execute`：调用 `tool_spec.executor(args, ctx)`，产出 `ToolResult`，含 `status`、`stdout/stderr`、`duration_ms`、`truncated`、`artifact_refs`。
    4. `map_feedback`：调用 `feedback_classifier.classify`；附加到结果上。
    5. `record_trace`：将 `tool_call_requested`、`policy_decision`、`tool_call_running`、`tool_call_output`、`feedback_signal` 全部 append 到 `trace_store`，且写入脱敏状态。
  - 关键不变量：**`record_trace` 在 `execute` 异常分支也必须被调用**，避免审计空洞。
- 输出截断：runtime 内置 `truncate(text, max_bytes=20000)`，超过则保留头尾，中间插入 `...truncated...` 标记。
- 执行器统一包装异常为 `ToolResult(status="tool_error", stderr=...)`；异常不外泄。

**先写的失败测试**：

`tests/test_tool_registry.py`：

- `test_register_and_lookup`：注册 2 个工具，`get` 返回正确对象，`names()` 排序稳定。
- `test_register_duplicate_raises`：重复名 → 抛 `RegistryError`。
- `test_input_schema_is_pydantic_model`：每个内置工具的 `input_schema` 必须是 `type[BaseModel]`。

`tests/test_tool_runtime.py`：

- `test_invoke_safe_tool_records_full_trace`：注册一个 `safe` 工具，正常调用 → runtime 返回 `RuntimeOutcome` 且 `trace_store` 至少有 `tool_call_requested`、`policy_decision`、`tool_call_running`、`tool_call_output`、`feedback_signal` 五条事件。
- `test_invalid_args_skips_policy_and_executor`：传非法 args → 不调用 executor（通过 mock 验证）、返回 `args_invalid` 反馈。
- `test_deny_short_circuits`：policy `deny` → executor 不被调用、`feedback == "policy_blocked"`、trace 中仍写入 `policy_decision`。
- `test_ask_triggers_approval_machine`：policy `ask` → 注入一个总是批准的 `approval_machine` 决策器，验证执行被放行；另一个总是拒绝的，验证 `policy_requires_approval` 反馈。
- `test_executor_exception_is_caught_and_recorded`：executor 抛 `RuntimeError` → `ToolResult.status == "tool_error"`、trace 仍写入 `tool_call_output`。
- `test_trace_redaction_status_set_when_args_look_like_secret`：args 中含 `sk-...` 模式时，关联事件的 `redaction_status == "redacted"`。

**验证步骤**：

```bash
uv run pytest tests/test_tool_registry.py tests/test_tool_runtime.py -v
```

**依赖**：`T01`、`T02`、`T04`、`T05`。

**并行**：否，T07 依赖此任务。

---

## T07 — 内置工具实现

**目标**：实现 SPEC §5.5 列出的 14 个内置工具；在 `tests/tools/` 提供 fake 执行器后端以便确定性测试。

**涉及文件**：

- 新建 `src/phycode/tools/builtin/__init__.py`
- 新建 `src/phycode/tools/builtin/file_read.py`
- 新建 `src/phycode/tools/builtin/file_list.py`
- 新建 `src/phycode/tools/builtin/file_write.py`
- 新建 `src/phycode/tools/builtin/file_edit.py`
- 新建 `src/phycode/tools/builtin/search_grep.py`
- 新建 `src/phycode/tools/builtin/search_glob.py`
- 新建 `src/phycode/tools/builtin/shell_run.py`
- 新建 `src/phycode/tools/builtin/test_run.py`
- 新建 `src/phycode/tools/builtin/workspace_status.py`
- 新建 `src/phycode/tools/builtin/memory_io.py`（封装 `memory.read/write`）
- 新建 `src/phycode/tools/builtin/config_io.py`（封装 `config.read/write`）
- 新建 `src/phycode/tools/builtin/keys_status.py`
- 新建 `tests/tools/__init__.py`
- 新建 `tests/tools/conftest.py`（提供 `fake_fs`、`fake_shell`、`fake_test_runner` fixture）
- 新建 `tests/tools/test_file_tools.py`
- 新建 `tests/tools/test_search_tools.py`
- 新建 `tests/tools/test_shell_and_test_tools.py`
- 新建 `tests/tools/test_meta_tools.py`

**实现要点**：

- 所有工具以「`ToolSpec` 工厂函数 + 执行器闭包」形式构造，注册到 `ToolRegistry`。注意 `tools.specs` 提供统一 `build_spec()` 帮助器以减少样板。
- `file.read`：参数 `{path, offset?, limit?}`，使用 `paths.resolve_workspace_path`，读取后调用 `runtime.truncate`，返回 `{content, total_bytes, returned_bytes, truncated}`。
- `file.list`：参数 `{path?, pattern?}`，glob 排序，限制 1000 条；超出截断。
- `file.write`：参数 `{path, content}`；必须在策略 `allow` 或通过审批后才写入；返回 `{bytes_written}`。
- `file.edit`：参数 `{path, old_text, new_text, replace_all=false}`；返回 unified diff；`old_text` 出现 0 次或 >1 次 → 报错。
- `search.grep`：使用 `rg` 时落 subprocess，固定 `cwd`、`timeout=5s`、输出截断；`rg` 不可用时回退 Python 实现。返回 `{matches: [{path, line, content}], total}`。
- `search.glob`：纯 Python `pathlib` 实现；与 `search.grep` 同样的截断策略。
- `shell.run`：参数 `{command, cwd?, timeout_ms?, env?}`；策略 `dangerous` 直接 deny；正常执行解析 `exit_code`、stdout、stderr、duration。
- `test.run`：参数 `{command?, framework?}`；优先用 `project_config.test_command`；解析器从 `feedback.test_parsers` 注入；返回结构化 `TestSummary`。
- `workspace.status`：报告 `{root, allowlist, git: {branch, dirty, last_commit}, diff_summary}`。
- `memory.read/write`：依赖 `T09` 的 `MemoryStore`；写入受策略管控，只接受 `MemoryCategory` 列出的四类。
- `config.read/write`：依赖 T03 的 `UserConfig`/`ProjectConfig`，**不**允许写入敏感字段。
- `keys.status`：仅返回 `{provider, present: bool, source, updated_at}`，绝不返回 key 本身。

**先写的失败测试**：

`tests/tools/test_file_tools.py`：

- `test_file_read_truncates_long_output`：写入 50KB 文件，offset/limit 缺省，验证 `returned_bytes < total_bytes`、`truncated is True`。
- `test_file_edit_returns_unified_diff`：写入两行文件、替换其中一行，验证返回的 diff 含 `-old` / `+new`。
- `test_file_edit_no_match_raises`：无匹配 → 抛 `EditError`，不应写入文件。
- `test_file_write_to_outside_workspace_denied`：利用 `tmp_path`，尝试写入 `..` 之外的路径，必须被 runtime 阶段 `deny`。

`tests/tools/test_search_tools.py`：

- `test_search_grep_uses_ripgrep_when_available`：在 `tmpdir` 写若干行，调用工具并断言 `rg` 被调用（通过注入 fake 后端）。
- `test_search_glob_sorts_results`。

`tests/tools/test_shell_and_test_tools.py`：

- `test_shell_run_captures_exit_code_and_output`：fake 执行器返回固定 `(0, "hello")`，验证结果结构。
- `test_shell_run_truncates_stdout`：长 stdout 触发 truncation 标志。
- `test_test_run_invokes_configured_test_command`：项目 `phycode.toml` 设置 `test_command = "echo passed"`，断言被调用并返回 `passed >= 1`。
- `test_shell_run_blocked_for_dangerous_command`：使用 `dangerous_patterns` 中条目，验证 runtime 阶段被策略 deny。

`tests/tools/test_meta_tools.py`：

- `test_workspace_status_reports_git_dirty`：在 fake git 仓库内修改文件，断言 `git.dirty is True`。
- `test_memory_write_requires_allowed_category`：写入 `category="secret"` → 策略 deny。
- `test_keys_status_never_returns_secret`：mock credentials store 返回固定 key；断言返回 dict 不含 key 字符串。

**验证步骤**：

```bash
uv run pytest tests/tools/ -v
```

**依赖**：`T02`、`T03`、`T04`、`T06`。

**并行**：是，但 T07 内部子模块可多人 worktree 并行；建议拆为：`feat/T07-files`、`feat/T07-search-shell-test`、`feat/T07-meta` 三个 worktree，最后合并。

---

## T08 — LLM 适配器（mock + OpenAI 兼容）

**目标**：实现 SPEC §5.3 中的 4 个 LLM 适配器，并把响应规范化为 `AgentEvent` 流。

**涉及文件**：

- 新建 `src/phycode/llm/__init__.py`
- 新建 `src/phycode/llm/base.py`（`LLMAdapter` 抽象接口）
- 新建 `src/phycode/llm/scripted.py`（`ScriptedLLM`）
- 新建 `src/phycode/llm/echo.py`（`EchoLLM`）
- 新建 `src/phycode/llm/failing.py`（`FailingLLM`）
- 新建 `src/phycode/llm/openai_compatible.py`（`OpenAICompatibleChatAdapter`）
- 新建 `src/phycode/llm/normalizer.py`（供应商响应 → `AgentEvent`）
- 新建 `tests/test_scripted_llm.py`
- 新建 `tests/test_llm_normalizer.py`
- 新建 `tests/test_openai_compatible_adapter.py`

**实现要点**：

- `LLMAdapter`：
  - 抽象方法 `async def complete(self, request: LLMRequest) -> LLMResponse` 与同步变体 `complete_sync`。
  - `LLMRequest` 字段：`messages: list[Message]`、`tools: list[ToolSchema]`、`temperature`、`max_tokens`、`model`、`extra`。
  - `LLMResponse` 字段：`raw: dict`、`events: list[AgentEvent]`、`usage: Usage`、`provider_call_id: Optional[str]`。
- `ScriptedLLM`：构造时传入 `script: list[Callable[[LLMRequest], list[AgentEvent]]]` 或事件序列；按调用顺序执行；耗尽后抛 `ScriptExhausted`，可由测试转化为 `assistant_final`。
- `EchoLLM`：把最后一条 `user` 内容回作为 `assistant_commentary`，再追加 `assistant_final`。
- `FailingLLM`：每次调用抛 `ProviderError`，并把 `kind="timeout"` 或 `kind="malformed"` 作为参数。
- `OpenAICompatibleChatAdapter`：
  - 依赖注入 `httpx.AsyncClient`、`credential_provider`（从 `T12` 而来）、`base_url`、`model`。
  - 支持 `tools` / `tool_calls`；若响应中无 `tool_calls`，尝试 fallback JSON-action 解析器：当 `extra.allow_json_fallback=True` 且响应文本包含孤立 JSON 块时尝试提取。
  - 调用完成后从 `adapter_state` 中清除 key（清空私有变量 + `gc.collect()` 仅作提醒，不强制）。
  - **CI 中不发起网络**：`OpenAICompatibleChatAdapter` 不在 `tests/test_openai_compatible_adapter.py` 默认用例中真实请求；只测试 payload 构造与 response normalization，使用 `respx` 拦截 `httpx` 调用。
- `normalizer.py`：
  - 将供应商响应解析为统一 `AgentEvent` 流；详细规则：
    - 文本 → `assistant_commentary`；若含 `<reasoning>` 标签（备用） → `reasoning_summary`。
    - `tool_calls[]` → 每个一条 `tool_call_requested`。
    - 终止条件：`finish_reason == "stop"` → `assistant_final`；`length` → `incomplete`；`error` → `error`。

**先写的失败测试**：

`tests/test_scripted_llm.py`：

- `test_scripted_llm_replays_events_in_order`：传入 3 个事件脚本，调用一次 `complete` 后断言返回事件顺序与脚本一致；再次调用抛 `ScriptExhausted`。
- `test_scripted_llm_passes_request_to_callback`：回调能读取 `request.messages[-1]` 做出决定。

`tests/test_llm_normalizer.py`：

- `test_normalize_tool_call_response_yields_requested_events`：构造 OpenAI 风格响应 dict，断言产生 `tool_call_requested` 事件、`tool_name` 与 `args` 解析正确。
- `test_normalize_text_only_response_yields_commentary_and_final`：纯文本响应 → `assistant_commentary` + `assistant_final`，无 `tool_call_requested`。
- `test_normalize_malformed_payload_yields_error`：缺字段、字段类型错误 → `error` 事件，含 `kind="malformed"`。
- `test_json_fallback_parses_isolated_tool_call`：响应文本为合法 JSON 工具描述 → 经 `allow_json_fallback=True` 后 → `tool_call_requested`。

`tests/test_openai_compatible_adapter.py`：

- `test_build_request_payload_omits_redacted_args`：使用 fake LLM 客户端（`respx` mock），断言发出请求的 JSON body 不包含明文凭据。
- `test_response_parsed_end_to_end_with_respx`：`respx` 拦截 POST，返回固定 fixture，断言 adaptor 输出 `AgentEvent` 流正确。
- `test_adapter_clears_key_after_call`：mock `credential_provider`，断言调用后 adapter 内不再持有 key。

**验证步骤**：

```bash
uv run pytest tests/test_scripted_llm.py tests/test_llm_normalizer.py tests/test_openai_compatible_adapter.py -v
```

**依赖**：`T01`、`T03`、`T11`（trace store，因为规范化的某些事件需要追溯）。

**并行**：与 `T09`、`T10` 中能在 mock 路径成立的子集并行；建议 `feat/T08-adapters` 单 worktree。

---

## T09 — 上下文构建器、会话存储、项目记忆

**目标**：实现 SPEC §5.8 的 ContextBuilder、SessionStore、MemoryStore，并在上下文预算下做截断 + 最近反馈优先。

**涉及文件**：

- 新建 `src/phycode/context/__init__.py`
- 新建 `src/phycode/context/session.py`（`SessionStore`）
- 新建 `src/phycode/context/builder.py`（`ContextBuilder`）
- 新建 `src/phycode/memory/__init__.py`
- 新建 `src/phycode/memory/store.py`（`MemoryStore`）
- 新建 `tests/test_context_builder.py`
- 新建 `tests/test_session_store.py`
- 新建 `tests/test_memory_store.py`

**实现要点**：

- `SessionStore`：
  - 内存实现 `InMemorySessionStore`，测试用；
  - 文件实现 `FileSessionStore`，写入 `.phycode/sessions/<id>.json`；
  - 提供 `append_event`、`events_within_window(n)`、`clear_for_test_only`。
- `MemoryStore`：
  - 文件位置 `.phycode/memory.jsonl`；
  - 提供 `append(entry)`、`list(category=None)`、`latest(n)`；
  - 不接受敏感字段（`denied_patterns` 在写入时检查）；content 不允许包含 `sk-...`、`-----BEGIN ... PRIVATE KEY-----` 等。
- `ContextBuilder`：
  - `build(*, session: Session, memory: MemoryStore, tools: list[ToolSpec], recent_feedback: list[FeedbackSignal], workspace_summary: str) -> ContextBundle`。
  - 组装顺序：system → tools → workspace_summary → memory_summary → recent_events（默认 20 条）→ recent_feedback → current_user_input。
  - 截断：估算 token（用 `len(text) // 4` 近似）；超出预算 → 优先压缩 `recent_events`，保留高价值（`tool_call_output` 含失败信息 > 旧 commentary）。
  - 提供 `stable_prefix` (`str`)：system + tools schema + workspace summary；要求对相同输入稳定，便于测试。
- `MemoryStore` 不允许 `keys.set` 等凭据信息写入。

**先写的失败测试**：

`tests/test_session_store.py`：

- `test_append_and_iterate_events`：顺序保留；
- `test_events_within_window`：传入 30 条事件 → `n=5` 返回最后 5 条；
- `test_file_session_persists`：写盘后重读一致。

`tests/test_memory_store.py`：

- `test_append_and_list_by_category`：四类各写一条 → `list(category="decision")` 只返回一类。
- `test_secret_pattern_rejected`：content 含 `sk-abcdef` → `append` 抛 `MemoryStoreError`。

`tests/test_context_builder.py`：

- `test_context_order_system_to_user`：`build(...)` 返回的 `messages` list 按规约顺序。
- `test_context_truncates_long_history`：构造 100 条 commentary → 截断后总额约预算 ± 5%。
- `test_recent_feedback_included_and_prioritized`：在长 history 后注入 `feedback_signal`（kind=command_failed） → 该消息排在被压缩的 commentary 之前。
- `test_stable_prefix_is_deterministic_for_same_inputs`：相同输入两次 `build` → `stable_prefix` 字节级一致。

**验证步骤**：

```bash
uv run pytest tests/test_context_builder.py tests/test_session_store.py tests/test_memory_store.py -v
```

**依赖**：`T01`、`T03`、`T11`。

**并行**：是（与 `T08`、`T10` mock 路径并行）。

---

## T10 — Agent 主循环

**目标**：实现 SPEC §5.2 的 8 步 agent 循环，并提供停机判断逻辑。

**涉及文件**：

- 新建 `src/phycode/agent/__init__.py`
- 新建 `src/phycode/agent/loop.py`
- 新建 `src/phycode/agent/shutdown.py`
- 新建 `tests/test_agent_loop.py`
- 新建 `tests/test_agent_shutdown.py`

**实现要点**：

- `loop.AgentLoop.run(initial_user_input, *, llm, tools, policy, context, memory, session, max_steps=50) -> RunResult`。
- 步骤严格对应 SPEC §5.2；每步完成后产生对应 `AgentEvent`。
- 消息流：内部维护 `messages: list[Message]`，由 `ContextBuilder.build` 产出初始 messages，每轮末尾追加工具结果与反馈。
- 调用 LLM 时将上一轮 `AgentEvent` 列表喂给 normalizer；返回值再喂给 `tools.invoke`。
- 反馈回灌：每轮最多回灌 3 个最新 `FeedbackSignal`（包含完整 evidence 截断）。
- 停机判断 `shutdown.ShutdownController.should_stop`：
  - 收到 `assistant_final` → 停。
  - 步数达 `max_steps` → 停，事件 `incomplete`。
  - 收到 `repeat_stuck` 反馈超过 1 次 → 停，事件 `error`（用户可继续）。
  - 收到 `policy_requires_approval` 且 `Session.mode == "non_interactive"` → 停，事件 `incomplete`，返回值含 reason。
  - 用户中断（`SIGINT`） → 写出 `user_interrupt` 事件并返回当前结果。
- `RunResult`：`final_answer: Optional[str]`、`events: list[AgentEvent]`、`stop_reason: Literal["final", "max_steps", "repeat_stuck", "policy_unresolved", "user_interrupt", "error"]`。

**先写的失败测试**：

`tests/test_agent_loop.py`：

- `test_single_step_with_scripted_llm`：mock LLM 返回 `assistant_final` → 1 轮后停机，`final_answer ==` script 内容。
- `test_tool_call_then_final`：脚本 `[tool_call_requested, assistant_final]`，runtime 注入 fake 安全工具 → 第二轮收 `assistant_final`，trace 中包含完整事件序列。
- `test_feedback_changes_next_action`：脚本 `[tool_call_requested, tool_call_requested, assistant_final]`；第一次 tool 注入 `command_failed` 反馈 → 第二次 tool 的 args 应与第一次不同（注入差异断言）。
- `test_dangerous_tool_denied_without_exec`：脚本 `tool_call_requested`（`shell.run` `rm -rf /`） → runtime 在策略阶段 deny，不再发起 fake executor（mock 验证）、agent 收到 `policy_blocked` 反馈。
- `test_max_steps_limit`：`max_steps=3`，mock 永不返回 `assistant_final` → 在第 3 步后停机，`stop_reason == "max_steps"`、`最后事件 == "incomplete"`。
- `test_noninteractive_ask_stops`：脚本发 `shell.run`，策略 `ask`、`Session.mode == "non_interactive"` → 停机 reason `policy_unresolved`、不再次调用 LLM。

`tests/test_agent_shutdown.py`：

- `test_user_interrupt_emits_event`：使用 `KeyboardInterrupt`-simulating harness；断言事件最后一条为 `user_interrupt`。
- `test_repeat_stuck_twice_stops`：`feedback.repeats == 2` → 停。

**验证步骤**：

```bash
uv run pytest tests/test_agent_loop.py tests/test_agent_shutdown.py -v
```

**依赖**：`T04`、`T05`、`T06`、`T07`（部分工具子集），`T08`，`T09`，`T11`。

**并行**：否，是核心集成点。

---

## T11 — Trace Store 与脱敏

**目标**：实现 `.phycode/traces/<session-id>.jsonl` 写入器，提供查询接口；保证脱敏。

**涉及文件**：

- 新建 `src/phycode/trace/__init__.py`
- 新建 `src/phycode/trace/store.py`
- 新建 `src/phycode/trace/redaction.py`
- 新建 `tests/test_trace_store.py`
- 新建 `tests/test_trace_redaction.py`

**实现要点**：

- `TraceStore.append(event)`：原子写一行 JSON；使用 `pathlib.Path.open("a")`，flush 后 fsync（每 N 条或 shutdown）。
- 每条事件按 SPEC §8 schema，包含 `id`、`session_id`、`type`、`timestamp`、`payload`、`redaction_status`、`schema_version`。
- `TraceStore.tail(n)`、`find_by_type(type_)`、`for_each(callable)`。
- `Redactor.scrub(text)`：
  - 匹配 `sk-[A-Za-z0-9]{20,}`、`[A-Za-z0-9]{32,}`、`-----BEGIN ... PRIVATE KEY-----`、`(?i)bearer\s+[A-Za-z0-9._-]{20,}`、`.env`、`AWS_SECRET_ACCESS_KEY=...` 等模式 → 替换为 `[REDACTED]`。
  - 命中即把事件的 `redaction_status` 置为 `redacted`。
- 写 trace 时调用 `Redactor.scrub` 重新清洗所有 payload 字符串字段（包括 args、stderr、stdout）；保证即使上游组件漏过也能在最后一道关上。

**先写的失败测试**：

`tests/test_trace_store.py`：

- `test_append_creates_line_per_event`：10 条事件 → 文件有 10 行 JSON。
- `test_tail_returns_last_n`。
- `test_load_round_trip_preserves_schema_fields`。
- `test_concurrent_append_is_safe_with_lock`：使用线程并发写 100 条事件 → 文件行数与断言一致。

`tests/test_trace_redaction.py`：

- `test_redactor_scrubs_openai_style_key`：原文含 `sk-abcdef...` → 替换为 `[REDACTED]`。
- `test_redactor_preserves_unrelated_text`。
- `test_redactor_handles_private_key_block`：PEM 内容 → 整块替换。
- `test_redaction_status_propagates_to_event`：`trace.append(event_with_secret)` → 再次读取时 `redaction_status == "redacted"`、payload 字符串已脱敏。

**验证步骤**：

```bash
uv run pytest tests/test_trace_store.py tests/test_trace_redaction.py -v
```

**依赖**：`T01`。

**并行**：是（与 `T04`、`T05` 并行）。

---

## T12 — 凭据存储与 `keys` CLI 子集

**目标**：实现 keyring + 加密文件双策略凭据存储，提供 `keys.set|status|clear` 后端 API。

**涉及文件**：

- 新建 `src/phycode/credentials/__init__.py`
- 新建 `src/phycode/credentials/backends/keyring_backend.py`
- 新建 `src/phycode/credentials/backends/encrypted_file_backend.py`
- 新建 `src/phycode/credentials/manager.py`
- 新建 `tests/test_credentials_manager.py`
- 新建 `tests/test_credentials_redaction.py`

**实现要点**：

- `CredentialsManager`：
  - 探测顺序：`keyring` → `encrypted_file` → `env_only`（fail-safe，仅文档警告）。
  - API：`set(provider, key) -> None`，`get(provider) -> Optional[str]`，`status(provider) -> CredentialStatus`，`clear(provider) -> None`，`available_backends()`。
- `keyring_backend`：
  - 使用 `keyring.set_password/get_password/delete_password`；`service_name = "phycode"`，`username = provider`。
  - 测试中通过 monkeypatch `keyring` 注入 fake backend。
- `encrypted_file_backend`：
  - 文件 `.phycode/credentials.bin`，使用 PBKDF2 + Fernet；首次使用要求交互式输入主密码（CLI 命令在 T13 完成）；非交互模式下抛 `MasterPasswordRequired`。
  - 提供 `unlock(master_pw)`、`lock()`。
- `status()` 返回 `CredentialStatus(provider, present, source, updated_at)`，绝不返回 key 字符串。
- 任何 `print/log/trace.write` 接触 key 时由 `Redactor.scrub` 兜底（与 `trace` 模块共享实现）。

**先写的失败测试**：

`tests/test_credentials_manager.py`：

- `test_keyring_backend_set_get_clear`：monkeypatch keyring → set/get 流程闭环。
- `test_encrypted_file_backend_round_trip_with_master_pw`：临时 home，写入、unlock、读出 key，再 lock。
- `test_env_only_fallback_when_no_backend`：移除所有 backends（monkeypatch）、断言 `available_backends() == ["env_only"]`、且 `get` 直接读环境变量。
- `test_status_does_not_return_key`：`status()` 字典中不允许出现 key 字符串（用检测模式扫描）。

`tests/test_credentials_redaction.py`：

- `test_logging_with_key_redacts`：使用 `caplog`，日志中包含 key → 重写为 `[REDACTED]`。
- `test_repr_of_manager_does_not_expose_key`：repr(manager) 内不含 key。

**验证步骤**：

```bash
uv run pytest tests/test_credentials_manager.py tests/test_credentials_redaction.py -v
```

**依赖**：`T01`、`T11`（共享 Redactor）。

**并行**：是，与 `T13`、`T14` 并行（在 T03、T11 完成后）。

---

## T13 — CLI（typer）与交互循环

**目标**：提供 `phycode`、`phycode chat`、`phycode run`、`phycode tools list`、`phycode demo ...`、`phycode config ...`、`phycode keys ...` 等 CLI 子命令。

**涉及文件**：

- 新建 `src/phycode/cli/__init__.py`
- 新建 `src/phycode/cli/app.py`
- 新建 `src/phycode/cli/chat.py`
- 新建 `src/phycode/cli/run.py`
- 新建 `src/phycode/cli/tools_cmd.py`
- 新建 `src/phycode/cli/config_cmd.py`
- 新建 `src/phycode/cli/keys_cmd.py`
- 新建 `src/phycode/cli/render.py`（Rich 渲染）
- 新建 `tests/test_cli_app.py`
- 新建 `tests/test_cli_chat.py`
- 新建 `tests/test_cli_keys.py`

**实现要点**：

- 使用 `typer.Typer()`、子应用：`phycode_app.add_typer(tools_app, name="tools")` 等。
- 默认 `phycode` 不带参数 → 进入 `chat` 子命令。
- `chat`：使用 `rich.prompt.Prompt` 实现 REPL；`/exit` 退出；首次启动若缺少凭据则提示运行 `phycode keys set`。
- `run "<task>"`：构造非交互 Session、单轮 agent loop、退码语义见 SPEC §5.1。
- `tools list`：表格列出 name、description、risk_level，着色按 risk。
- `config read|write`：基于 `phycode.config.loader`，对未知字段报错。
- `keys set|status|clear`：交互模式使用 `rich.prompt.Prompt(password=True)` 录入；非交互模式 `phycode keys set --provider openai-compatible --key-from-stdin`。
- 渲染：`render.py` 提供 `print_event(event, console)`、`print_policy_decision(decision)`、`print_feedback(signal)`。
- 退出码：0=成功、1=通用错误、2=policy_unresolved、3=config_invalid、4=credentials_missing。
- 输入解析异常 → `typer.echo(err=True)`。

**先写的失败测试**：

`tests/test_cli_app.py`：

- `test_help_lists_subcommands`：`phycode --help` 输出包含 `chat run tools demo config keys`。
- `test_run_returns_nonzero_on_policy_unresolved`：使用 monkeypatch 注入 `AgentLoop` 模拟返回 `stop_reason="policy_unresolved"` → 退码 2。
- `test_run_returns_zero_on_final_answer`：脚本 LLM 输出 `assistant_final` → 退码 0。

`tests/test_cli_chat.py`：

- `test_chat_starts_when_credentials_present`：monkeypatch `CredentialsManager.status` 返回 present，`stdin` 提供 `"hello"` 与 `"exit"` → 断言 `AgentLoop.run` 被调用一次、第二次因 `/exit` 退出。
- `test_chat_prompts_for_keys_when_missing`：`status().present == False` 时，CLI 打印引导信息并退码 4。

`tests/test_cli_keys.py`：

- `test_keys_set_writes_via_manager`：monkeypatch manager，`stdin` 提供 provider、password 值 → `set` 被以正确参数调用。
- `test_keys_status_never_prints_secret`：`status` 返回固定 key 时，CLI 输出不含 key 字符串。

**验证步骤**：

```bash
uv run pytest tests/test_cli_app.py tests/test_cli_chat.py tests/test_cli_keys.py -v
```

**依赖**：`T00`、`T03`、`T06`、`T07`、`T10`、`T12`。

**并行**：是（与 T14 并行）。

---

## T14 — 确定性演示命令 (`phycode demo`)

**目标**：实现 `phycode demo guardrail`、`feedback`、`policy` 三个确定性演示，复现 SPEC §11 验收条件。

**涉及文件**：

- 新建 `src/phycode/demos/__init__.py`
- 新建 `src/phycode/demos/guardrail.py`
- 新建 `src/phycode/demos/feedback.py`
- 新建 `src/phycode/demos/policy.py`
- 新建 `tests/test_demos.py`

**实现要点**：

- 命令在 `cli/app.py` 中注册为 `phycode demo <name>`。
- 每个 demo 构造：
  - 临时 `tmp` workspace；
  - 注入脚本化 LLM（指定工具调用序列）；
  - 注入 `InMemoryTraceStore`，事后 `cat` 关键事件；
  - 输出确定性 ASCII 报告 + 退出码 0。
- `guardrail`：脚本化 shell.run `rm -rf /`，断言 trace 中出现 `policy_decision(decision=deny, rule_id=default.shell_dangerous_block)`、无 `tool_call_running` 事件。
- `feedback`：脚本化 1) `shell.run pytest -q`（fake executor 返回非零退出）→ 反馈 `command_failed`；2) `assistant_final`。断言第二次 LLM 输入中含 `feedback_signal`。
- `policy`：脚本化 `file.write` → 策略 `ask` → 非交互模式 → 停机 `policy_unresolved`。

**先写的失败测试**（`tests/test_demos.py`）：

- `test_demo_guardrail_blocks_dangerous_shell`：`assert_tool_call_running_not_in_trace`、`assert_policy_decision_present`。
- `test_demo_feedback_propagates_to_next_step`：mock LLM 的第二次 `complete` 入参中存在 `feedback_signal` 消息。
- `test_demo_policy_stops_non_interactive_on_ask`：最终 `RunResult.stop_reason == "policy_unresolved"`、`exit_code == 2`。

**验证步骤**：

```bash
uv run phycode demo guardrail
uv run phycode demo feedback
uv run phycode demo policy
uv run pytest tests/test_demos.py -v
```

**依赖**：`T07`、`T10`、`T11`、`T13`。

**并行**：是（与 T13 并行 / 紧随其完成）。

---

## T15 — CI（`.gitlab-ci.yml` + GitHub Actions 可选）、一键测试、PyPI 发布

**目标**：让 `uv run pytest` 在 CI 中通过；提供 `make test`、`make publish-dry-run`；预备 `pyproject.toml` 的 `build-system` 与 metadata。

**涉及文件**：

- 新建 `.gitlab-ci.yml`
- 新建 `.github/workflows/ci.yml`（可选）
- 新建/更新 `Makefile`（追加 `make demo`、`make publish-dry-run`）
- 更新 `pyproject.toml`（补 `build-system = {requires = ["hatchling>=1.18"], build-backend = "hatchling.build"}`、`[project.urls]`、`[tool.hatch.build.targets.wheel]` 等）

**实现要点**：

- `.gitlab-ci.yml`：
  - `image: python:3.11-slim`
  - 安装 `pip install uv`。
  - 唯一 job：`unit-test`：`script: ["uv sync", "uv run pytest --maxfail=1 --disable-warnings -q"]`、`cache: {paths: [.cache/uv]}`。
  - 不需要任何 API key；不下载第三方模型。
- `Makefile`：
  - `test`：`uv run pytest`
  - `lint`：`uv run ruff check .`
  - `fmt`：`uv run ruff format .`
  - `demo`：`uv run phycode demo guardrail && uv run phycode demo feedback && uv run phycode demo policy`
  - `publish-dry-run`：`uv publish --dry-run`（实际发布会带 `--token` 由用户在本地输入）。
- `pyproject.toml` 元数据完整：
  - `description` 简短；
  - `readme = "README.md"`；
  - `[project.urls]`：`Homepage`、`Source`、`Issues`。
- 注：CI 中不要跑 `phycode demo`（避免依赖 `tmp_path` 表现差异），demo 由 PR 描述人工复现。

**先写的失败测试**（不需要新测试，但需要 CI 中验证）：

- 在本地复现 CI：
  ```bash
  uv sync
  uv run pytest --maxfail=1 -q
  ```
  期望所有测试通过。

**验证步骤**：

```bash
uv run pytest --maxfail=1 -q
uv run ruff check .
uv build
uv publish --dry-run
```

**依赖**：`T13`、`T14`。

**并行**：是（与 T16 并行）。

---

## T16 — README、CHANGELOG 与分发说明

**目标**：为最终用户与评审提供完整使用、测试、分发、安全说明。

**涉及文件**：

- 重写 `README.md`
- 新建 `CHANGELOG.md`
- 新建 `SECURITY.md`（凭据威胁模型与上报流程）
- 新建 `docs/USAGE.md`（命令大全与示例）
- 修改 `AGENT_LOG.md`（追加项目交付里程碑记录）

**实现要点**：

- `README.md`：
  - 简介（一句话 + 设计主张）。
  - 安装：`uv tool install phycode` 或 `pip install phycode`；列出 uv 与 PyPI 两种方式。
  - 运行：`phycode` 进入 REPL；`phycode run "..."`、`phycode tools list`、`phycode demo ...`。
  - 测试：`make test` 或 `uv run pytest`。
  - 分发：`make publish-dry-run`、`make publish`（说明 `UV_PUBLISH_TOKEN`）。
  - 安全：如何 `phycode keys set`；Windows / macOS / Linux 钥匙串差异；明文 `.env` 风险；不提交 `.env`。
  - 目录结构（src、tests、docs、course_resource）。
  - 链接到 `SPEC.md`、`PLAN.md`、`SPEC_PROCESS.md`、`AGENT_LOG.md`。
- `CHANGELOG.md`：`0.1.0` 初始版本记录。
- `SECURITY.md`：列出 SPEC §6.2 中的威胁与缓解措施；联系邮箱（占位）。
- `docs/USAGE.md`：长篇示例、配置项清单、常见报错。

**先写的失败测试**（`tests/test_docs_examples.py`）：

- `test_readme_quickstart_runs`：执行 README “Quickstart” 段落中命令片段到 tmpdir（除 install 命令），最后断言 trace 写出。
- `test_readme_does_not_contain_placeholder_url`：使用正则 `https?://example\.com/`，`README.md` 不允许出现。

**验证步骤**：

```bash
uv run pytest tests/test_docs_examples.py -v
```

**依赖**：`T13`、`T15`。

**并行**：是。

---

## 2. 跨任务约束与里程碑

### 2.1 阶段门禁

- **阶段 1（脚手架完成）**：`T00` 完成；之后任何 task 必须能跑 `uv run pytest` 才算合规。
- **阶段 2（核心机制完成）**：`T01`、`T02`、`T03`、`T04`、`T05`、`T06`、`T09`、`T10`、`T11` 完成；`phycode demo guardrail` 能确定性复现。
- **阶段 3（产品外层完成）**：`T07`、`T08`、`T12`、`T13`、`T14` 完成；`uv run pytest` 全绿；`.gitlab-ci.yml` 已配置。
- **阶段 4（分发与交付）**：`T15`、`T16` 完成；`uv publish --dry-run` 通过；`README.md`、`SECURITY.md` 无明文占位。

### 2.2 每任务执行守则（subagent 必读）

1. 从 `feat/Txx-<short>` 拉 worktree；任务完成合并回 `main` 后删除。
2. 严格 TDD：先 commit 失败的测试，再 commit 实现变绿；commit message 分别记录。
3. 任务结束前运行完整测试集：`uv run pytest` 必须全绿。
4. 在 `AGENT_LOG.md` 追加：`[Txx] <commit> <subagent> <一句话结论>`。
5. 不允许引入 SPEC §5.3 之外的 LLM 供应商运行时（OpenAI Agents SDK / LangChain AgentExecutor / AutoGen / CrewAI / LlamaIndex agent）。
6. 不允许把策略决策改为基于 prompt 而非代码。
7. 默认全部测试**不访问网络与真实凭据**；`httpx` 测试必须通过 `respx` mock。
8. 凭据相关测试只能使用 `monkeypatch` 注入的 fake backend，不允许真实 keyring 操作。
9. 任务完成的 PR 描述必须包含：所属 task 编号、对应 SPEC 章节、测试覆盖变化、人工干预说明。

### 2.3 风险跟踪

- 供应商 tool-call 差异：T08 已实现 fallback JSON 解析器；CI 不联网。
- 钥匙串不可用：T12 的 fail-safe `env_only` 提供兜底，但 README 必须警告。
- Worktree 合并冲突：建议工作日为单 subagent 单 task，避免同一文件多处修改。
- 演示命令在 CI 中差异：明确 demo 不进 CI，仅本地复现。

---

## 3. 验收清单（与 SPEC §11 一一对应）

- 启动：`T13` 完成。
- `phycode run`：`T13` + `T10`。
- `phycode tools list`：`T13`。
- `phycode demo guardrail`：`T14`。
- `phycode demo feedback`：`T14`。
- `phycode demo policy`：`T14`。
- `uv run pytest` 通过：`T00–T14` 收尾。
- `.gitlab-ci.yml` 含 `unit-test` job：`T15`。
- Mock LLM 测覆盖主循环：`T10`。
- 策略测覆盖安全读取/风险写入/危险 shell/路径逃逸/凭据不泄露：`T04` + `T12`。
- 上下文测覆盖截断和最近反馈：`T09`。
- 凭据测试验证 status/trace/memory 不出现明文 key：`T11`、`T12`、`T14`（demo policy 配合）。
- README 说明安装/运行/测试/分发/安全配置：`T16`。
- SPEC/PLAN/SPEC_PROCESS/AGENT_LOG 维护：本次 PLAN 即为 PLAN；SPEC 已完成；SPEC_PROCESS 与 AGENT_LOG 在任务进行中持续维护。
