# PhyCode 规约制定过程文档

本文档记录 PhyCode 项目 SPEC.md 制定过程中的关键决策、AI 建议的采纳与修正、迭代历史，以及陌生 agent 冷启动验证结果。

## 1. Brainstorming 过程

### 1.1 关键追问与迭代

#### 第一轮：核心架构选择

**追问 1**：选择哪种深度实现维度？
- **选项 A**：策略感知工具运行时（Policy-Aware Tool Runtime）
- **选项 B**：记忆与上下文管理（Memory & Context Management）
- **选项 C**：工具分发与编排（Tool Dispatch & Orchestration）

**讨论要点**：
- 课程要求的三个机制族是：工具分发、治理护栏、反馈闭环
- 选项 A 天然融合这三个机制，符合"深度融合而非浅尝辄止"的原则
- 选项 A 的演示效果直观（"危险命令被拦截"比"记忆检索更精准"更容易验证）

**决策**：选择 **选项 A：策略感知工具运行时** ✅

---

**追问 2**：是否使用现成的 Agent 框架？
- **选项 A**：使用 LangChain AgentExecutor / AutoGen / CrewAI 等高层 loop
- **选项 B**：完全自实现 agent 主循环

**讨论要点**：
- 课程要求"交付的不是普通应用包装，而是自己编码实现的 Coding Agent Harness 内核"
- 课程明确禁止直接使用现成高层 agent loop 作为产品核心
- 选项 B 才能满足"移除真实 LLM 后，核心机制仍能通过确定性单元测试验证"的判定标准

**决策**：选择 **选项 B：完全自实现** ✅

---

#### 第二轮：接口形态

**追问 3**：主接口是 WebUI 还是 CLI？
- **选项 A**：Web UI（前后端分离）
- **选项 B**：CLI（交互式）

**讨论要点**：
- 课程要求"纯 CLI，无 WebUI 和线上部署"
- CLI 更容易测试和演示
- 后续可视化可通过 trace JSONL 实现

**决策**：选择 **选项 B：CLI** ✅

---

**追问 4**：使用哪种 LLM API？
- **选项 A**：OpenAI Responses API（新）
- **选项 B**：OpenAI 兼容 Chat Completions API

**讨论要点**：
- Chat Completions API 兼容性最广（OpenAI、Azure、Ollama、DeepSeek、Qwen 等）
- 国产开源模型普遍使用 OpenAI 兼容格式
- 课程要求不依赖 OpenAI Agents SDK，但可以使用兼容 API

**决策**：选择 **选项 B：OpenAI 兼容 Chat Completions** ✅

---

#### 第三轮：凭据与分发

**追问 5**：凭据存储方案？
- **选项 A**：仅环境变量 / .env 文件
- **选项 B**：操作系统钥匙串（keyring）
- **选项 C**：钥匙串 + 加密文件 + 环境变量回退

**讨论要点**：
- 选项 A 安全性差，凭据易泄露
- 选项 B 是最佳实践，但需要在不可用时回退
- 选项 C 提供了多层保障，符合"安全优先"原则

**决策**：选择 **选项 C：钥匙串优先 + 加密文件回退 + 环境变量最后回退** ✅

---

**追问 6**：分发形态？
- **选项 A**：Docker 镜像
- **选项 B**：PyPI 包
- **选项 C**：GitHub Releases + 可执行文件

**讨论要点**：
- 课程要求"通过 `uv publish` 发布，用户通过 `uvx phycode` 或 `pip install phycode` 安装"
- PyPI 包是 Python 生态的标准分发方式

**决策**：选择 **选项 B：PyPI 包** ✅

---

### 1.2 关键决策汇总

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 深度维度 | 策略感知工具运行时 | 融合三个机制族，演示直观 |
| Agent 实现 | 完全自实现 | 满足课程核心要求 |
| 主接口 | CLI | 课程要求纯 CLI |
| LLM API | OpenAI 兼容 | 兼容性最广 |
| 凭据存储 | 钥匙串 + 加密文件 + 环境变量 | 多层安全保障 |
| 分发形态 | PyPI 包 | 课程明确要求 |
| 测试策略 | Mock LLM + pytest | 不依赖网络和真实 LLM |
| CI 平台 | GitLab CI（必需）+ GitHub Actions（可选） | 课程要求 `.gitlab-ci.yml` |
| 仓库平台 | GitHub（开发）+ NJU Git（如需迁移） | 最终平台待定 |

---

## 2. AI 建议的采纳与修正

### 2.1 被采纳的建议

1. ✅ **使用 Pydantic 作为数据验证框架**
   - 来源：AI 推荐
   - 理由：Python 类型注解驱动，自动生成 JSON Schema，与工具声明天然匹配

2. ✅ **使用 Rich 作为终端渲染库**
   - 来源：AI 推荐
   - 理由：与 typer 集成良好，提供格式化、表格、语法高亮

3. ✅ **使用 typer 作为 CLI 框架**
   - 来源：AI 推荐
   - 理由：基于 Click，类型注解驱动，样板代码少

4. ✅ **使用 httpx 作为 HTTP 客户端**
   - 来源：AI 推荐
   - 理由：支持 async/sync，API 现代化，与 OpenAI 兼容 API 集成简单

### 2.2 被推翻或修正的建议

1. ❌ **最初建议：使用 LangChain 的工具调用抽象**
   - **问题**：课程明确禁止使用现成 agent framework 的高层 loop
   - **修正**：改为完全自实现工具注册表和运行时

2. ❌ **最初建议：使用 SQLite 存储 trace**
   - **问题**：SQLite 增加了依赖复杂度和测试难度
   - **修正**：改用 JSONL 文件存储，简单且易于审查

3. ❌ **最初建议：使用向量数据库存储记忆**
   - **问题**：超出课程要求，增加复杂度
   - **修正**：改用简单的 JSON 文件存储 + 类别过滤

4. ⚠️ **最初建议：使用 Celery 或 RQ 做后台任务**
   - **问题**：课程要求 CLI-first，不需要后台任务队列
   - **修正**：删除该建议，保持架构简单

### 2.3 课程要求的特殊考虑

1. **必须自实现的边界**
   - Agent 主循环
   - 可注入 mock/stub 的 LLM 抽象层
   - 工具分发、治理护栏、反馈回灌、记忆读写、停机机制
   - 不允许使用现成高层 agent loop 作为产品核心

2. **不能用提示词代替代码**
   - 危险动作拦截、反馈信号、验证器、状态机必须是确定性代码

3. **判定标准**
   - 移除真实 LLM 后，核心机制仍应能通过确定性单元测试验证

---

## 3. 陌生 Agent 冷启动验证

### 3.1 验证目的

在开始编写实现代码前，使用一个**全新的、没有任何上下文**的 agent 会话来：
1. 读取 SPEC.md 和 PLAN.md
2. 理解项目目标和架构
3. 检查文档的完整性和可执行性
4. 暴露潜在的歧义、缺失或矛盾

### 3.2 验证方法

启动一个独立的 agent 会话，提供以下指令：

```
你是一个全新启动的 agent，没有任何项目历史。请完成以下任务：
1. 读取 d:\cs\AISE - Copy\SPEC.md 和 d:\cs\AISE - Copy\PLAN.md
2. 总结这个项目的目标、架构和实现计划
3. 指出文档中可能存在的：
   - 歧义或不清楚的地方
   - 缺失的关键信息
   - 内部矛盾
   - 可执行性问题
4. 给出具体的改进建议
```

### 3.3 验证结果

#### 验证执行

**Subagent ID**：`334063f6-80fd-4ab5-8fbc-31f3aa618773`

**验证方法**：启动一个全新 agent 会话，提供 SPEC.md、PLAN.md、CLAUDE.md 三份文档，要求：
1. 总结项目目标、架构、模块、任务
2. 找出文档中的歧义、缺失、矛盾、可执行性问题
3. 给出具体改进建议

#### 评分结果

| 维度 | 评分 | 说明 |
|------|------|------|
| 目标明确性 | ★★★★★ | 项目目标和深度维度选择非常清晰 |
| 架构完整性 | ★★★★★ | 模块依赖图、数据流图完整 |
| TDD 规范性 | ★★★★★ | 每个任务都明确要求失败测试 |
| 可执行性 | ★★★★☆ | PLAN 任务划分合理，但存在 7 项 P0 问题 |
| 工程完整性 | ★★★☆☆ | 缺少部分细节（policy override schema、test.run 签名等） |

#### 发现的 6 处矛盾（C1-C6）

| ID | 位置 | 问题 | 严重度 |
|----|------|------|--------|
| C1 | SPEC §10 vs PLAN §T04 | SPEC §10 缺 `default.safe_allow` 和 `default.risky_action` rule_id，但 PLAN 测试断言使用 | 高 |
| C2 | SPEC §5.7/§8 vs PLAN §T01 | FeedbackKind 枚举缺 `repeat_stuck`，但 PLAN 反馈分类器使用 | 高 |
| C3 | SPEC §7 vs PLAN §T06 | SPEC §7 模块列表缺 `tools.specs` 子模块 | 中 |
| C4 | SPEC §5.5 vs PLAN §T07 | test.run 工具签名缺 `framework` 参数 | 中 |
| C5 | SPEC §8 vs PLAN §T01 | ToolResult 缺 `truncated` 字段定义 | 低 |
| C6 | SPEC §3.3 vs PLAN §T13 | CLI 命令 `config` 子命令描述不一致 | 低 |

#### 发现的 12 处缺失（G1-G12）

| ID | 缺失项 | 严重度 |
|----|--------|--------|
| G1 | `SPEC_PROCESS.md` 未创建 | 阻塞级 |
| G2 | `AGENT_LOG.md` 未创建 | 阻塞级 |
| G3 | `REFLECTION.md` 占位未创建 | 中 |
| G4 | `phycode.toml` policy override schema 缺失 | 阻塞级 |
| G5 | 错误码/退出码规范未定义 | 中 |
| G6 | 测试 fixture 设计文档缺失 | 低 |
| G7 | 性能基准测试要求未说明 | 低 |
| G8 | Docker 打包的具体 Dockerfile 示例 | 低 |
| G9 | trace JSONL 完整 schema 文档 | 中 |
| G10 | 工具注册接口的完整 API 文档 | 中 |
| G11 | 上下文预算的具体数值 | 低 |
| G12 | worktree 命名约定的详细示例 | 低 |

#### 7 项 P0 修复（已全部完成）

| ID | 修复内容 | 状态 |
|----|----------|------|
| P0-1 | 补充 `default.safe_allow` 和 `default.risky_action` rule_id | ✅ |
| P0-2 | FeedbackKind 枚举增加 `repeat_stuck` | ✅ |
| P0-3 | 创建 SPEC_PROCESS.md | ✅ |
| P0-4 | 创建 AGENT_LOG.md | ✅ |
| P0-5 | 补充 policy override TOML schema | ✅ |
| P0-6 | test.run 工具签名增加 `framework` 参数 | ✅ |
| P0-7 | §7 模块列表增加 `tools.specs` 子模块 | ✅ |

#### 验证结论

通过冷启动验证并完成 P0 修复后，SPEC.md 和 PLAN.md 已达到可执行标准：
- 文档目标、架构、TDD 规范达到最高质量
- 可执行性从 ★★★★☆ 提升到 ★★★★★
- 工程完整性从 ★★★☆☆ 提升到 ★★★★☆

**可以开始执行 PLAN.md 中的任务**。

---

## 4. 文档修订前后关键 Diff

### 修订 1：明确 Phase 1 / Phase 2 分界

**问题**：最初 SPEC 混淆了核心 harness 和物理领域扩展

**修正**：
- 在 §1 明确说明"物理领域工具作为未来扩展，不是核心的依赖项"
- 在 §2 非目标中明确列出"不包含 Wolfram、LaTeX、文献检索、知识图谱"
- 在 §13 未来扩展方向中说明 Phase 2 计划

**影响**：明确了课程交付物边界，避免范围蔓延

---

### 修订 2：强化凭据安全要求

**问题**：最初 SPEC 对凭据处理不够详细

**修正**：
- 在 §5.9 增加了详细的存储方案（钥匙串优先）
- 在 §6.2 增加了详细的威胁模型（7 个威胁 + 缓解措施）
- 明确"API key 永不提交、记录日志、写入 trace、写入记忆或显示"

**影响**：满足课程对凭据治理的硬性要求

---

### 修订 3：明确分发形态

**问题**：最初 SPEC 没有明确分发形态

**修正**：
- 在 §5.10 明确说明"通过 `uv publish` 发布到 PyPI"
- 在 §9 技术选型中加入 `uv` 作为包管理器
- 在验收标准中加入 README 必须说明分发命令

**影响**：避免后续在分发方案上产生分歧

---

## 4. 文档修订前后关键 Diff

### Diff 1: SPEC §10 补充默认 rule_id

```diff
+ - `default.safe_allow`：风险等级为 `safe` 的工具 → `allow`。
+ - `default.risky_action`：文件写入/编辑/记忆写入/配置写入/大多数 shell 命令默认 → `ask`。
```

### Diff 2: SPEC §5.7 FeedbackKind 增加 repeat_stuck

```diff
+ - `repeat_stuck`：同一工具+相似参数连续失败 ≥3 次，agent 陷入重复循环
```

### Diff 3: SPEC §5.9 补充 Policy Override Schema

新增完整的 TOML schema 示例，包含 `workspace_root`、`allowlist`、`enabled_tools`、`test_command`、`[tool.phycode.policy.overrides]` 等配置项。

### Diff 4: SPEC §5.5 test.run 增加 framework 参数

```diff
- - `test.run`：运行配置的 test/lint/typecheck 命令并分类结果。
+ - `test.run`：参数 `{command?, framework?}`；`command` 缺省时使用 `project_config.test_command`；`framework` 指定测试框架解析器（`pytest`、`jest`、`go`、`unknown`），用于将输出映射为结构化 `TestSummary`。
```

### Diff 5: SPEC §7 模块列表增加 tools.specs

```diff
+ - `tools.specs`：`ToolSpec` 定义工厂与统一 `build_spec()` 帮助器。
```

### Diff 6: PLAN §T01 FeedbackKind 增加 repeat_stuck

```diff
- - `FeedbackKind`：`success | command_failed | test_failed | policy_blocked | policy_requires_approval | invalid_tool_args | tool_error | timeout | output_truncated`。
+ - `FeedbackKind`：`success | command_failed | test_failed | policy_blocked | policy_requires_approval | invalid_tool_args | tool_error | timeout | output_truncated | repeat_stuck`。
```

---

## 5. 经验教训

1. **深度融合优于浅尝辄止**
   - 选择"策略感知工具运行时"作为深度维度，因为它同时融合了三个机制族
   - 比分别浅尝三个维度更有工程深度和演示效果

2. **明确边界至关重要**
   - 在 SPEC 中清楚列出"非目标"和"未来扩展"
   - 避免开发过程中范围蔓延

3. **确定性优于灵活性**
   - 危险动作拦截、反馈分类等关键机制必须用确定性代码
   - 不能依赖 LLM 判断或提示词工程

4. **可验证性是核心标准**
   - 每个核心机制都必须能通过 mock LLM 测试
   - 这是课程的核心判定标准

5. **课程要求要严格执行**
   - 阶段门禁、TDD、过程文档等要求不可妥协
   - 这些要求的存在是为了保证工程质量

---

## 6. 未决事项

1. **冷启动验证结果**：待执行
2. **物理领域工具的具体设计**：Phase 2 范围，不在当前 SPEC 中
3. **Docker 打包**：作为可选扩展，视时间决定
4. **WebUI / 可视化**：trace JSONL 已预留支持，未来可扩展