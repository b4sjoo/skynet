# 并行 Subagent 工作流（Claude Code）

## 元数据

- **类型**: Workflow
- **适用场景**: 并行执行多个独立子任务（调研、分析、代码）
- **创建日期**: 2026-02-20
- **最后更新**: 2026-05-27（按 Claude Code 现实重写；OpenCode 旧版见文末映射）

---

## 核心判断

Subagent 的主要价值不是模拟人类团队，也不是把一个普通任务包装得更复杂。它解决的是三类具体问题：

1. **上下文窗口隔离**：让不同 agent 各自持有一段可控上下文，避免主线程同时塞入大量文件、网页、日志和中间判断。
2. **并行读与独立探索**：让多个 agent 同时搜索、阅读、定位、复核，减少单一路径依赖。
3. **交叉验证**：让不同 agent 在有意重叠的范围内独立得出结论，用一致和分歧暴露遗漏、误读和假设冲突。

外部经验也指向同一个结论：multi-agent 在 research-heavy、read-heavy、高价值任务上更容易成立；在需要多个 agent 共享大量状态、连续协调写入、实时互相修正的任务上成本高且脆弱。Anthropic 的 multi-agent research system 把它定位为用更多 token 换更强的并行探索和压缩能力，并明确提到 multi-agent 可能消耗约 15 倍于普通 chat 的 token；LangChain 的经验则强调 read-heavy 比 write-heavy 更适合并行，因为写操作会携带隐含决策，合并冲突代价高。

调研依据：Anthropic Engineering《How we built our multi-agent research system》（https://www.anthropic.com/engineering/multi-agent-research-system）、LangChain《How and when to build multi-agent systems》（https://www.langchain.com/blog/how-and-when-to-build-multi-agent-systems）、Cemri et al.《Why Do Multi-Agent LLM Systems Fail?》（https://arxiv.org/abs/2503.13657）。

## 何时使用并行模式

满足以下条件中的至少 2 条，并且没有命中下方反模式时，优先考虑 subagent：

1. **信息面宽**：需要查多个文件、多个网页、多个数据源、多个时间段，主线程一次性读完会污染上下文。
2. **可拆分为独立读任务**：能分成至少 2 个相对独立的探索方向，每个方向预期需要 ≥5 个 tool call。
3. **需要独立判断**：需要反方审稿、事实核查、竞品对照、代码审查、方案对比，单一路径容易自我确认。
4. **存在高价值不确定性**：任务结果会影响后续决策、公开输出、代码改动或成本较高的行动，多花 token 值得。
5. **主线程需要保留设计/整合能力**：主 agent 应把注意力用在拆分问题、设定标准、整合证据和最终判断，而不是埋在低层搜索或重复读取里。

不满足时直接串行，不要为并行而并行。

---

## Claude Code 的两条硬约束（先记住）

1. **只能 Claude**：subagent 的 `model` 只能取 `opus` / `sonnet` / `haiku` / Claude 全名 / `inherit`。**无法派 Gemini、GPT 等非 Claude 的 subagent**。需要跨 provider（如用 Gemini 做创意并行），走 OpenCode 后端或直接调对应 provider，而不是 `Agent` 工具。
2. **子不能再生子**：subagent **不能再派 subagent**（防无限嵌套）。需要「嵌套并行」时，把那一层上移到主 agent——由主 agent 一次性平铺派出所有 subagent，而不是让某个 subagent 内部再分裂。深层链式委派改用 Skills 或主 agent 串接。

## 反模式

以下情况默认不要用 subagent，除非用户明确要求或任务价值足以覆盖额外成本：

1. **单点小任务**：只需读 1-2 个文件、跑一个命令、改一个局部 bug。
2. **强顺序依赖**：下一步必须依赖上一步输出，拆出去只会制造等待和交接成本。
3. **共享状态写入**：多个 agent 同时改同一批文件、同一张表、同一份文案，冲突和隐含决策难以合并。
4. **上下文必须完整共享**：每个 agent 都必须知道全量背景才能做对，拆分后只会丢条件。
5. **验证标准不清**：没有可核对的输出格式、证据要求或验收条件，多个 agent 只会产出多份模糊总结。

## 任务类型参考

| 任务类型 | 是否适合 | 推荐方式 |
|---|---|---|
| 外部调研、论文/产品/市场 survey | 高 | 3-5 个 agent，按证据功能切分，30-50% overlap |
| 大型代码库理解、文件定位、架构梳理 | 高 | `explore` 并行按模块或问题切分，主线程整合 |
| 代码 review、方案审稿、事实核查 | 高 | 2-3 个 agent 独立审查，同一关键区域保留 overlap |
| Brainstorm、反方观点、thesis 压力测试 | 中高 | 不同 agent 指定不同判断视角，输出必须回答同一组问题 |
| 多文件实现 | 中 | 只在模块边界清楚时并行；主线程保留最终合并和测试责任 |
| 单 bug 修复、局部编辑、格式调整 | 低 | 主线程直接做 |
| 多 agent 同时写同一文件或同一状态 | 低 | 避免；改成先并行读/评审，再由主线程或单一 agent 写 |

---

## 并行执行流程

### 1. 评估与分割

识别 3-5 个关键维度后，按任务类型确定 overlap：

| 任务类型 | Overlap 范围 | 原因 |
|---------|-------------|------|
| 调研/创造性任务 | 30% - 50% | 交叉验证、查漏补缺 |
| 代码/执行任务 | 0% - 20% | 效率优先，减少重复 |

不要把 overlap 理解成重复劳动。好的 overlap 是让相邻 agent 在最容易出错的边界区域共同覆盖，例如官方 claim 和独立证据的交界、模块接口、数据口径、反对意见。

### 2. 并行启动

**在同一条消息里发出所有 `Agent` 调用**——Claude Code 会并发执行它们。用 `subagent_type` 选角色、`model` 选模型、`run_in_background` 决定前台还是后台：

- **前台并发**（默认，多数场景）：同一条消息发多个 `Agent`，并发跑，结果在本轮作为 tool result 一起回来，主 agent 直接综合。
- **后台并发**（`run_in_background: true`）：派出后不阻塞，可以接着干别的；每个 subagent 完成时结果**自动**作为 tool result 回到主对话——系统会通知，**无需轮询**。

`model`：`opus`（最难的逻辑/架构）、`sonnet`（执行、调研、代码，默认性价比）、`haiku`（轻量/快速）、`inherit`（随主对话）。

常用 `subagent_type`：

| subagent_type | 工具 | 适合 |
|---|---|---|
| `general-purpose` | 全工具（含 Edit/Write、联网） | 外部深度调研、需写中间产物、复杂多步任务 |
| `Explore` | 只读 fan-out（Read/Glob/Grep/Bash/Web，无 Edit/Write/Agent） | 广撒网检索、代码库探索、定位为主不改动 |
| `Plan` | 只读 | plan 模式下的研究 |
| `claude-code-guide` | Bash/Read/Web | Claude Code 功能咨询 |

每个 subagent 的 prompt 要包含：

- 具体负责的维度/范围（subagent **看不到主对话上下文**，prompt 必须自包含）
- 预期的 overlap 区域（让它知道别人也在看这块，便于后续交叉验证）
- 输出格式要求，以及「返回结论与证据，不要回贴整文件」

### 3. 等待与整合

- **前台**：结果本轮返回，直接交叉验证重叠区域、合成最终输出。
- **后台**：**派出后结束当前回复，等系统通知**。不要反复查任务状态来「等」它完成——后台 subagent 完成会自动把结果回传到主对话的下一条消息。轮询既无必要也浪费配额。

---

## 结果回传与共享上下文

- subagent 只返回**一段最终文本**作为 tool result；它的中间工具调用主 agent **看不到**（需要时可事后查 subagent transcript）。所以 prompt 里要明确要求它把关键证据写进最终输出。
- Claude Code **没有内建的 agent 间共享 scratchpad**。需要多 agent 共享一份「活文档」（single source of truth）时用**文件**：主 agent 建 `tmp/<session>/scratchpad.md`，在 prompt 里告诉 subagent 去读/写这个文件。结构化 JSON 输出格式见 `bestpractice_multi_agent_analysis.md`。

---

## 示例

### 调研任务（30-50% overlap，前台并发，同一条消息发 3 个 Agent）

```
调研「某技术框架的采用情况」
├─ Agent 1（general-purpose）：核心特性 + 社区活跃度
├─ Agent 2（general-purpose）：社区活跃度 + 企业案例
├─ Agent 3（general-purpose）：企业案例 + 竞品对比
└─ Overlap：社区和企业案例都有覆盖，主 agent 交叉验证
```

### 代码任务（0-20% overlap）

```
实现「用户认证系统」
├─ Agent 1：认证核心逻辑 + Token 管理
├─ Agent 2：数据库模型 + 迁移脚本
├─ Agent 3：API 端点 + 测试用例
└─ Overlap：接口定义处少量重叠，确保对接正确
```

### 审查任务（30% overlap）

```
审查「一个 PR 是否可靠」
├─ Agent 1（explore/reasoning_gpt）：代码行为和边界条件
├─ Agent 2（explore）：测试覆盖、缺失 fixture、回归风险
├─ Agent 3（reasoning_gpt）：架构一致性和隐含依赖
└─ Overlap：所有 agent 都看核心 diff，但外围文件按职责分开
```

### 不适合并行的任务

```
修复「一个函数里的 off-by-one」
└─ 主线程直接读文件、改代码、跑测试。subagent 的启动和整合成本高于任务本身。
```

---

## 模型路由与指定模型

当前工具 schema 只暴露 `task(subagent_type=...)`，不暴露 `category` 或 `load_skills`。不要把旧环境的 category 路由照搬到当前 OpenCode 工具调用里。

当前可用 subagent 类型以系统工具说明为准。常见值：

| subagent_type | 用途 |
|---|---|
| `general` | 通用研究、复杂问题拆解、外部资料调研、事实核查；通常继承主会话模型 |
| `explore` | 快速探索代码库、搜索文件和符号、回答内部代码结构问题 |
| `reasoning_gpt` | GPT 路线高可靠推理和工程判断 |
| `writer_deepseek` | DeepSeek Pro 路线中文写作与改稿 |
| `cheap_glm` | GLM 路线低成本初筛和轻量整理 |
| `private_ds4` | 本地 ds4 路线，隐私敏感优先 |
| `ollama_kimi` | Ollama Cloud Kimi K2.6，zero-data-retention、低成本 |
| `ollama_deepseek_pro` | Ollama Cloud DeepSeek V4 Pro，zero-data-retention、高质量但更贵 |

如果未来工具 schema 更新，以运行时 tool schema 为准，不要沿用过期的 `category` / `run_in_background` 写法。

---

## 注意事项

- **不要过度并行**：2-3 个精心设计的 subagent 通常优于 5 个松散的。并行越多 token/配额烧得越快（10 个并行 ≈ 10 倍速）。
- **prompt 质量**：subagent 的 prompt 要具体且自包含，否则结果会很浅。
- **成本意识**：并行消耗更多 token，评估是否值得。
- **中间结果**：通常不必保存，在主 agent 中整合即可；需要共享则用文件。

---

## OpenCode → Claude Code 映射（旧文档迁移参考）

本工作流原为 OpenCode 编写。遇到旧调用按下表翻译：

| 旧（OpenCode） | 新（Claude Code） |
|---|---|
| `mcp_task(...)` / `task(...)` | `Agent` 工具（早期叫 `Task`） |
| `subagent_type="explore"` | `subagent_type="Explore"`（只读 fan-out 检索） |
| `subagent_type="librarian"` / `category="deep"`（外部调研） | `subagent_type="general-purpose"`（全工具、能联网） |
| `subagent_type="oracle"` | `subagent_type="general-purpose"` |
| `load_skills=[...]` | 无直接等价；在 prompt 里说明，或用 Skills |
| `category="artistry"`（Gemini 创意并行） | **无等价**——CC 只能 Claude；跨 provider 走 OpenCode 后端 |
| `category="quick"` / `"ultrabrain"` | `model="haiku"` / `model="opus"` |
| `background_output(block=…, timeout=…)` 取结果 | 无需；后台 subagent 完成自动回传 tool result |
| 共享 scratchpad（运行时内建） | 自己用文件（`tmp/<session>/`） |
| subagent 内部再派 subagent | 不允许；嵌套层上移到主 agent 平铺派发 |
