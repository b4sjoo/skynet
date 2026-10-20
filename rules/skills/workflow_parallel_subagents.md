# 并行 Subagent 工作流（Claude Code）

## 元数据

- **类型**: Workflow
- **适用场景**: 并行执行多个独立子任务（调研、分析、代码）
- **创建日期**: 2026-02-20
- **最后更新**: 2026-08-14（补入 `Workflow` 确定性编排、worktree 隔离、fork、结构化输出；删除残留的 OpenCode subagent 路由表）

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

1. **只能 Claude**：subagent 的 `model` 只能取 Claude 系（`opus` / `sonnet` / `haiku` / `fable`），省略则继承主对话。**无法派 Gemini、GPT 等非 Claude 的 subagent**。需要跨 provider（如用 Gemini 做创意并行），走 OpenCode 后端或直接调对应 provider，而不是 `Agent` 工具。
2. **嵌套只有一层**：subagent **不能再派 subagent**。fork 出来的 agent 尤其要注意——它继承了完整上下文，很容易反射性地再委派一次，规则是**直接执行**。需要「嵌套并行」时把那一层上移到主 agent 平铺派发；用 `Workflow` 编排时，脚本内的 `workflow()` 也只允许嵌套一层，子 workflow 里再调就会抛错。

## 反模式

以下情况默认不要用 subagent，除非用户明确要求或任务价值足以覆盖额外成本：

1. **单点小任务**：只需读 1-2 个文件、跑一个命令、改一个局部 bug。
2. **强顺序依赖**：下一步必须依赖上一步输出，拆出去只会制造等待和交接成本。
3. **共享状态写入**：多个 agent 同时改同一批文件、同一张表、同一份文案，冲突和隐含决策难以合并。
   *已有部分解药*：`isolation: "worktree"` 给每个 agent 独立的 git worktree，物理上不可能互相踩。代价是每个 agent 约 200-500ms 建立开销加磁盘占用，**只在 agent 确实会并行改文件时才用**，不要当默认值。隐含决策难合并这一条依然成立——worktree 解决的是冲突，不是「谁的判断对」。
4. **上下文必须完整共享**：每个 agent 都必须知道全量背景才能做对，拆分后只会丢条件。
   *已有部分解药*：`subagent_type: "fork"` 派出的 agent 继承主对话的完整上下文（且强制跟随主模型，`model` 参数被忽略）。适合「背景很长但要独立跑一段」的场景。注意 fork 不省 token——它复制的是上下文，省的是**你的**上下文（工具输出留在 fork 里不回灌主线程）。
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

**在同一条消息里发出所有 `Agent` 调用**——Claude Code 会并发执行它们。逐个调用就是串行，这是最常见的「以为并行了其实没有」。

`Agent` 的参数只有 `prompt` / `description` / `subagent_type` / `model` / `isolation`。**没有 `run_in_background` 这个参数**（那是 `Bash` 的）。前台/后台不由你的调用决定：普通 subagent 的结果在本轮作为 tool result 回来；fork 和「后台运行的 skill」则先返回一个名字，结果稍后以 task notification 送达——那种情况下**派出后就结束本轮回复，等通知，不要轮询**。

`model`：`opus`（最难的逻辑/架构）、`sonnet`（执行、调研、代码，默认性价比）、`haiku`（轻量/快速）、`fable`。**默认省略**，继承主对话模型通常就是对的；只在明确判断该换档时才写。

常用 `subagent_type`：

| subagent_type | 工具 | 适合 |
|---|---|---|
| `general-purpose` | 全工具（含 Edit/Write、联网） | 外部深度调研、需写中间产物、复杂多步任务 |
| `Explore` | 只读 fan-out（Read/Glob/Grep/Bash/Web，无 Edit/Write/Agent） | 广撒网检索、代码库探索、定位为主不改动 |
| `fork` | 同主对话 | 需要完整上下文才做得对，且想把工具噪音挡在主线程外 |
| `Plan` | 只读 | 设计实现方案、架构权衡 |
| `claude-code-guide` | Bash/Read/Web | Claude Code / Agent SDK / Claude API 的用法咨询 |
| `claude` | 全工具 | 不匹配上述任何一类时的兜底 |

**类型以运行时的工具说明为准**——项目可以在 `.claude/agents/*.md` 里定义自己的 agent，名字、模型、工具集都由那份 frontmatter 决定。不要背这张表。

**派出后可以续聊**：`ListAgents` 列出可寻址的 agent，`SendMessage` 按名字继续某个已派出的 agent，它的上下文还在。这比重新 `Agent` 一次（全新空白上下文）省得多，也避免重复交代背景。

每个 subagent 的 prompt 要包含：

- 具体负责的维度/范围（subagent **看不到主对话上下文**，prompt 必须自包含）
- 预期的 overlap 区域（让它知道别人也在看这块，便于后续交叉验证）
- 输出格式要求，以及「返回结论与证据，不要回贴整文件」

### 3. 等待与整合

- **前台**：结果本轮返回，直接交叉验证重叠区域、合成最终输出。
- **后台**：**派出后结束当前回复，等系统通知**。不要反复查任务状态来「等」它完成——后台 subagent 完成会自动把结果回传到主对话的下一条消息。轮询既无必要也浪费配额。

---

## 结果回传与共享上下文

- subagent 只返回**一段最终文本**作为 tool result；它的中间工具调用主 agent **看不到**（需要时可事后查 subagent transcript）。所以 prompt 里要明确要求它把关键证据写进最终输出。**这个「看不到」是特性不是缺陷**——把 500 个 grep 结果挡在主线程外，正是 subagent 的主要价值之一。
- **要结构化结果就别靠 prompt 求**。用 `Workflow` 时给 `agent()` 传 `schema`（JSON Schema），subagent 会被强制走结构化输出通道，返回的是**校验过的对象**，格式不符会自动重试。手写「请返回 JSON」再自己解析是上一代做法，脆且会静默失败。
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
├─ Agent 1（Explore）：代码行为和边界条件
├─ Agent 2（Explore）：测试覆盖、缺失 fixture、回归风险
├─ Agent 3（general-purpose）：架构一致性和隐含依赖
└─ Overlap：所有 agent 都看核心 diff，但外围文件按职责分开
```

### 不适合并行的任务

```
修复「一个函数里的 off-by-one」
└─ 主线程直接读文件、改代码、跑测试。subagent 的启动和整合成本高于任务本身。
```

---

## 进阶：用 `Workflow` 做确定性编排

平铺派 `Agent` 适合「一轮就够」。当编排逻辑本身需要循环、条件、扇出扇入时，用 `Workflow`——写一段 JS 脚本，控制流由代码决定而不是由模型即兴发挥。

可用原语：`agent(prompt, opts)`、`parallel(thunks)`、`pipeline(items, ...stages)`、`phase(title)`、`log(msg)`、`workflow(name, args)`，外加 `args` 和 `budget`。

### 最值得记住的一条：`pipeline` 默认，`parallel` 是屏障

- **`parallel()` 是屏障**：等所有 thunk 跑完才返回。
- **`pipeline()` 没有屏障**：每个 item 独立穿过所有 stage，item A 已经跑到 stage 3 时，item B 可能还在 stage 1。

差别是墙钟时间：pipeline 的耗时 = 最慢的**单条链**，parallel 分段的耗时 = 每段最慢者之**和**。5 个 finder 里最慢的比最快的慢 3 倍时，屏障会白白浪费掉快的那些的空闲时间。

**只有当 stage N 真的需要 stage N−1 的全部结果**才用屏障——跨 item 去重、总数为零就整体早退、prompt 里要引用「其他人的发现」。以下都**不是**理由：「我得先 flatten/filter 一下」（放进 pipeline 的一个 stage 里做就行）、「这两步概念上是分开的」（pipeline 本来就建模了分步，分步 ≠ 同步）、「这样代码更好看」。

判断口诀：如果你写出了 `parallel → 一个纯变换 → parallel`，中间那个变换不需要屏障。

### 值得复用的几个质量形态

| 形态 | 做法 | 解决什么 |
|---|---|---|
| **对抗式验证** | 每个结论派 N 个独立怀疑者，prompt 要求它们**证伪**，多数证伪就杀掉 | 「看着有道理但其实错」的结论 |
| **视角分化验证** | N 个验证者各给一个不同镜头（正确性/安全/性能/能否复现），而不是 N 个同质怀疑者 | 冗余检不出的失败模式 |
| **评审团** | 从不同角度生成 N 个方案，并行打分，从赢家合成并嫁接亚军的好点子 | 解空间宽时，胜过「一个方案反复改」 |
| **跑到干涸** | 连续 K 轮没有新发现才停，而不是「凑够 N 个」 | 未知规模的发现类任务，固定计数会漏尾巴 |
| **多模态扫描** | 并行 agent 各用一种检索方式（按容器/按内容/按实体/按时间） | 单一检索角度找不全 |
| **完备性批评者** | 最后派一个专问「还缺什么——哪个模态没跑、哪条断言没验、哪个来源没读」 | 它找出来的就是下一轮的工作 |

**别静默截断**：如果编排里有 top-N、不重试、抽样这类限制，用 `log()` 把丢掉的部分说出来。静默截断读起来像「全覆盖了」，但其实没有。

### 规模与成本

并发上限是 `min(16, CPU核数-2)`，超出的排队。所以「10 个并行 ≈ 10 倍速」只在上限之内成立。单次 `parallel`/`pipeline` 最多 4096 个 item，单个 workflow 生涯上限 1000 个 agent（防跑飞的兜底，不是设计目标）。

规模要匹配请求：「找找有没有 bug」→ 几个 finder、单票验证；「彻底审计一遍」→ 更大的 finder 池 + 3-5 票对抗验证 + 综合阶段。

### 可恢复

每次调用都会把脚本落盘并返回 `runId` 和路径。改脚本后用 `{scriptPath, resumeFromRunId}` 重跑，**未改动的那段前缀直接命中缓存秒回**，只有第一个改动点及其之后才真跑。调试编排逻辑时这个能省大量重复开销。脚本里**不能用** `Date.now()` / `Math.random()` / 无参 `new Date()`（会破坏 resume），时间戳从 `args` 传进去或等 workflow 返回后再打。

---

## 注意事项

- **不要过度并行**：2-3 个精心设计的 subagent 通常优于 5 个松散的。并行越多 token/配额烧得越快——在并发上限（`min(16, 核数-2)`）以内约等于线性倍增，超出后只是排队，不再更快但一样烧钱。
- **prompt 质量**：subagent 的 prompt 要具体且自包含，否则结果会很浅。
- **成本意识**：并行消耗更多 token，评估是否值得。
- **中间结果**：通常不必保存，在主 agent 中整合即可；需要共享则用文件。

---

## 两条实战教训（2026-08-14 现场踩出来的）

### 1. 并行调用之间共享可变状态，会静默串味

同一条消息里发出的多个 `Bash` 调用**共用同一个 shell 会话**，也就共用 cwd。当天一次诊断里，一条命令带了 `cd`，另一条没带——后者继承了前者的 cwd，于是**同一个仓库被当成两个仓库读了两遍**，输出完全一样却看不出异常，据此得出了「这两个仓库是同一个」的错误结论，绕了两轮才发现。

规则：**并行发出的调用必须对可变共享状态零依赖**。具体做法是把状态显式写进每次调用——`git -C <绝对路径>` 而不是 `cd`、绝对路径而不是相对路径、各自独立的输出文件名。这条同样适用于并行 subagent 写同一个 `tmp/` 文件、同一个环境变量、同一个默认分支。

顺带一个同源的坑：zsh 默认开 `MULTIOS`，`cmd 2>&1 >/dev/null | grep` **不会**丢弃 stdout（它是加一个目的地而不是替换），于是「只看 stderr」的意图静默落空。想只要 stderr 就老老实实 `2>file` 再读。

### 2. 「什么都没发现」必须配阳性对照

同一天两次差点栽在这上面：一次是断言「git 跟随 301 重定向时完全静默」，实际测法被上面那个 MULTIOS 坑污染了；一次是扫描仓库历史里的明文密钥，扫出来 0 条。

0 条有两种可能——**真没有**，或者**扫描器根本没读到内容**。二者输出完全一样。所以任何负向结论都要附一个必定命中的对照：密钥扫描顺带 grep 一个已知存在的字符串（命中 41 行 → 证明确实在读 blob），重定向静默性顺带测一个必然报错的仓库（吐出 121 字节 → 证明 stderr 捕获有效）。

这条在并行验证里权重更高：N 个 agent 一起报告「没发现问题」时，你无法区分「干净」和「N 个 agent 都没真的看」。**给验证 agent 的 prompt 里塞一个已知缺陷，看它报不报**，比再加一个 agent 有用得多。

---

## 机会扫描战役的四条教训（2026-08-16/17，71 agent、4 个 Workflow 踩出来的）

### 3. 结构化输出有 64k 上限：让 LLM 只输出决策，不搬运数据

去重 agent 接收 248 条候选记录、被要求完整返回合并后清单 → 超出 64k 输出 token 上限直接失败。正确拆法：**agent 只返回合并决策（索引组/映射表），确定性代码（Python）执行搬运**。推论：任何「接收 N 条 → 返回 N 条」形状的 agent 设计，写 prompt 前先算输出预算；改用「返回 O(变更量) 而非 O(数据量)」的输出契约。

### 4. Workflow args 必须传真实数据；大入参拆文件让 agent 自读

一次把 args 传成占位符对象，12-agent workflow 因 `args.length === undefined` 零 chunk 空转（幸运：51ms 完成、零消耗——空转本身无害，但等于没跑）。大数据入参的正确姿势不是塞 50KB 进 args（还要在 orchestrator 上下文里往返一遍），而是**拆成每 agent 一个 JSON 文件，args 只传名字清单，agent 第一步用 Read 自读**——orchestrator 上下文零负担。

### 5. 对抗性 brief + 收紧裁决定义，防止 verdict 通胀

尽调类 agent 的任务要写成「先尽全力找出它会失败的理由，再下裁决」，并且把最高档裁决的定义收紧到可验证（如 conditional-go = 「阻碍是单一可验证的外部门槛；『执行得好就行』不算条件」）。效果可检验：48 份尽调 0 个 strong-go、44 个 no-go/weak，且每份都带实测证据（curl/DNS/流量估计器读数）——说明约束生效，裁决没有被讨好倾向稀释。配套要求：关键论断必须附「你实际看到的依据」，evidence 字段禁止编造。

### 6. 批式 workflow 要做经验注入：上一批的发现是下一批的待检验假设

第二批 40 个尽调 agent 的 brief 里显式注入第一批的三条结构性发现（AI Overview 意图分层、高 CPC=SaaS 封锁嫌疑、活体对照优先）并附先例锚点，要求「逐条对照检验而不是重新发明」。这让第二批的证伪/证实都有明确对照物，且把第一批的判断（如「高 CPC 生成器是红海」）变成了被 40 个独立样本检验过的结论，而非一次性直觉。

---

## OpenCode → Claude Code 映射（旧文档迁移参考）

本工作流原为 OpenCode 编写。遇到旧调用按下表翻译：

upstream（`grapeot/context-infrastructure`）的文档仍按 OpenCode 写，同步时会带回这些名字，照抄会得到不存在的 API。

| 旧（OpenCode） | 新（Claude Code） |
|---|---|
| `mcp_task(...)` / `task(...)` | `Agent` 工具（早期叫 `Task`） |
| `multi_tool_use.parallel` 包多个 `functions.task` | **不存在**；并行 = 同一条消息里发多个 `Agent` 调用 |
| 手写编排循环 | `Workflow` 工具（`pipeline` / `parallel` / `agent`） |
| `subagent_type="explore"` | `subagent_type="Explore"`（只读 fan-out 检索） |
| `subagent_type="librarian"` / `category="deep"`（外部调研） | `subagent_type="general-purpose"`（全工具、能联网） |
| `subagent_type="oracle"` | `subagent_type="general-purpose"` |
| `load_skills=[...]` | 无直接等价；在 prompt 里说明，或用 Skills |
| `category="artistry"`（Gemini 创意并行） | **无等价**——CC 只能 Claude；跨 provider 走 OpenCode 后端 |
| `category="quick"` / `"ultrabrain"` | `model="haiku"` / `model="opus"` |
| `background_output(block=…, timeout=…)` 取结果 | 无需；后台 subagent 完成自动回传 tool result |
| 共享 scratchpad（运行时内建） | 自己用文件（`tmp/<session>/`） |
| subagent 内部再派 subagent | 不允许；嵌套层上移到主 agent 平铺派发 |
