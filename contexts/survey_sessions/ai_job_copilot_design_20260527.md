# AI Job Copilot — Design Doc

- **日期**：2026-05-27（v2：按 project_scaffold 内部分节 + 跨设计交叉验证）
- **方法**：`rules/skills/workflow_deep_research_survey.md`（3 个并行 Explore agent + 主线交叉验证）+ `rules/skills/bestpractice_multi_agent_analysis.md` + `rules/skills/project_scaffold.md` 量尺。
- **本文档形态**：单 markdown，但按 PRD / RFC / Test 内部分节，**便于 scaffold 项目时 1:1 切分到 `adhoc_jobs/ai_job_copilot/docs/{prd,rfc,test,working}.md`**。
- **平行报告**（同目录交叉验证来源）：`ai_job_copilot_design_202605271.md`（技术深潜）、`...272.html`（战略市场定位）、`...273.md`（产品化合规）。
- **远端**：https://github.com/b4sjoo/skynet.git

---

## 核心三原则

1. **official-first** —— 数据只来自公开 ATS 官方接口、官方合作 API 或用户主动导入；不 scrape LinkedIn / Indeed / Glassdoor / 未授权页面。
2. **retrieval-before-generation** —— master profile + JD 都先经检索 + 受约束生成；LLM 只在「解释 + tailoring」两个环节出现，不在「打每个岗位的分」环节。
3. **human-in-the-loop** —— 我们生成简历 + 评分，用户审核后**手动**投。坚决不做 auto-apply。

**为什么**：Wonsulting 2025-08 post-mortem 显示海投平均 50 申请 1 面试（2% hit rate）；Glassdoor 平均每岗位 250 申请人；Scale.jobs 数据 LazyApply 海投 callback 2-5% vs 人工定制 22%。低量高精是个人候选人在 2026 市场唯一可行的策略。

---

## §1 PRD —— 未来 `docs/prd.md`

### 目标

把一份 working summary（个人职业经历）+ 目标公司 AI 岗位池，自动产出**高匹配度排序** + **JD 定制、可溯源、ATS-friendly** 的简历，帮个人候选人在 AI 岗位竞争中提高 callback 率。

### 用户

- **MVP**：鸭哥本人（个人工具）。
- **Phase 3 generalize**：任何能提供 working summary + 申请 AI/IT 岗的候选人。

### 核心需求

1. **定期搜索**各目标公司 AI 相关岗位空缺（Mag7 + AI 独角兽起步，全美/remote/海外）。
2. **匹配打分**：根据 master profile 给岗位 fit_score，surface 高匹配的。
3. **简历定制**：master profile + 选中岗位 → 真实可溯源、ATS-friendly `.docx`。
4. **追踪**：申请状态（applied / screened / interview / offer / rejected / withdrawn）。
5. **可观测**：每份简历 → 哪些 master profile fact 被选中、JD 关键词覆盖率、gap 在哪里。

### 成功标准

**主指标**：14-30 天 callback / interview rate。海投基线 2-5%，定制目标 ≥ 15%。

**次指标**：
- 简历导出率（生成后用户实际使用）
- 岗位保存率（surface 出来后用户标 interested 的比例）
- 人工编辑幅度（生成版本 vs 用户最终投出去的版本 diff 行数，越小越好）
- 首轮响应时间（投出去到收到回复的中位数）
- 投诉率 / 误投率 / 虚假陈述率（负向；目标 0）

### 范围（目标公司，phase 化）

| 公司 | ATS | Phase |
|---|---|---|
| OpenAI、Anthropic | Ashby（Anthropic 备 Greenhouse） | 1 |
| Mistral | Lever | 1 |
| Scale AI、Databricks | Greenhouse | 1 |
| Nvidia、Tesla | Workday CXS | 1 |
| Apple、Google、Meta | 自研 ATS（站内 JSON / tavily-skill 兜底 / 聚合 API fallback） | 2 |

地理范围：全美、remote、海外均含；用户在 UI 自行过滤。

### 产品定位（参考 File 2 的 4 分类）

| 类型 | 例子 | 我们 |
|---|---|---|
| 被动聚合器 | Google for Jobs、SimplyHired | 不做 |
| 模板生成器 | Kickresume、Resume.io | 不做 |
| **ATS 优化器 + 检索定向** | Teal、Jobscan、Rezi | **这里**——差异化：dogfood workspace 资产（heartbeat / tavily-skill / Claude 大窗口）、CC-native、强 traceability |
| 端到端代理 | LazyApply、Sonara | **坚决不做** |

### 明确不做

- ❌ Auto-apply / Easy Apply 批量 / 浏览器机器人代投
- ❌ Scrape LinkedIn / Indeed / Glassdoor / Levels.fyi
- ❌ 编造任何不在 master profile facts 里的经历、头衔、技能、量化数据
- ❌ 隐藏白字 / 字体技巧 / 关键词堆砌
- ❌ 把 working summary / 真实简历 commit 进 public repo

### 实证锚

- **Glassdoor**：每个开放岗位平均 250 申请人 → 招聘官 throughput 是瓶颈。
- **Wonsulting 2025-08 post-mortem**：海投 hit rate 2%（50 申请 1 面试）。
- **Scale.jobs**：人工定制 22% callback vs LazyApply 2-5%。
- **Indeed Hiring Lab 2026 初**：AI mention share 4.2%（较 2020 +134%），LinkedIn 2030 前 70% 技能改变 → AI 岗位市场只会扩大。

---

## §2 RFC —— 未来 `docs/rfc.md`

### 架构图

```
[Cron / Heartbeat] ──► [Source adapters]
                         │
            Greenhouse / Lever / Ashby / Workday CXS / Custom
                         │
                         ▼
                   [Normalize] ──► [Taxonomy 分类] ──► [SQLite postings]
                                                          │
[Master profile JSON] ──► [Fact extraction] ──► [facts 表 + embeddings]
                                                          │
                                                          ▼
                                       [混合检索 pipeline]
              硬过滤 → BM25 召回 → 语义召回 → RRF 重排 → LLM 解释层
                                                          │
                                                          ▼
                                       [matches + gap 报告]
                                                          │ 用户选一个岗位
                                                          ▼
                  [简历定制：2 阶段 + 3 约束 + Source-ID guard]
                                                          │
                                                          ▼
                                  [docxtpl ATS-friendly .docx]
                                                          │
                                                          ▼
                          [React UI：预览 / 下载 / 申请追踪]
```

### 数据获取

#### Source adapter 公共契约

```python
@dataclass
class JobPosting:
    company: str
    ats: Literal["greenhouse", "lever", "ashby", "workday", "custom"]
    external_id: str
    title: str
    location: str
    remote: bool
    department: Optional[str]
    jd_text: str         # JD 全文（检索 + tailoring 用）
    jd_html: Optional[str]
    url: str             # 招聘页 URL
    apply_url: str       # 申请入口 URL
    posted_at: datetime
    last_seen_at: datetime
    raw: dict            # 原始响应（traceability）
```

#### 公司 → ATS 映射（`companies.yaml`）

```yaml
- name: OpenAI
  ats: ashby
  token: openai
  phase: 1
- name: Anthropic
  ats: ashby
  token: anthropic
  fallback: { ats: greenhouse, token: anthropic }
  phase: 1
- name: Mistral
  ats: lever
  token: mistral
  phase: 1
- name: Scale AI
  ats: greenhouse
  token: scaleai
  phase: 1
- name: Databricks
  ats: greenhouse
  token: databricks
  phase: 1
- name: Nvidia
  ats: workday
  tenant: nvidia
  site: NVIDIAExternalCareerSite
  phase: 1
- name: Apple
  ats: custom
  config:
    strategy: ["jobs_apple_json", "tavily_career_crawl", "theirstack_fallback"]
  phase: 2
# Google、Meta 同 custom，phase 2
```

#### RFC 9309 合规四层

robots.txt **不是授权形式**（per RFC 9309）。合规检查同时看 4 层：

1. **Site ToS** —— Greenhouse / Lever / Ashby 公开 API 明确允许 indexing；LinkedIn / Indeed 明确禁止。
2. **官方开发者文档** —— ATS 文档说"这个 endpoint 公开"才能用。
3. **robots.txt** —— 礼貌遵守 + 限速。
4. **请求频率** —— 即使在公开 API 上也限速；不超过 ATS 暴露的 rate limit（Lever 10 req/s）。

具体清单：

- ✅ **允许**：Greenhouse / Lever / Ashby 公开 board API；Workday CXS；公司站内 JSON-LD；用户主动导入。
- ❌ **禁止**：scrape LinkedIn 任何页面；scrape Indeed Easy Apply / 搜索结果；scrape 任何需登录后才看的内容。
- ⚠️ **灰区（避免）**：Glassdoor 详情、Levels.fyi、Salary.com —— 都有 ToS 限制。

### 数据模型（SQLite v0；Postgres 升级路径）

```sql
-- 公司
companies (id, name, ats, token, config_json, phase, created_at, updated_at)

-- 岗位（归一化 + taxonomy）
postings (
  id, company_id, external_id, title, location, remote, department,
  jd_text, jd_html, url, apply_url,
  posted_at, first_seen_at, last_seen_at, closed_at,
  taxonomy_family, taxonomy_subdomain, taxonomy_evidence_json,
  raw_json,
  UNIQUE(company_id, external_id)
)

-- 用户事实库（master profile 展开）
master_profile (id, version, profile_json, created_at)
facts (
  id, profile_id, fact_type, content, tags_json, metrics_json,
  employer, role, time_range_start, time_range_end,
  source_evidence,            -- 用户原始上下文，审计用
  created_at
)
-- fact_type: experience_bullet | skill | project | education | certification

-- 匹配
matches (id, posting_id, profile_id, fit_score, matched_reqs_json,
         missing_reqs_json, rationale, ranking_features_json, created_at)

-- 简历版本（一等公民，from day 1）
resume_versions (
  id, posting_id, profile_id, profile_version_hash,
  tailored_json,           -- 受约束的 JSON schema
  rendered_docx_path,
  rendered_pdf_path,
  fact_id_mapping_json,    -- {"experience.0.bullets.2": "fact_uuid", ...}
  gap_report,
  generated_at
)

-- 申请追踪
applications (
  id, posting_id, profile_id, resume_version_id,
  status,                  -- queued | applied | screened | interview | offer | rejected | withdrawn
  applied_at, status_history_json, notes
)

-- 审计（Phase 3 ready）
audit_logs (id, event_type, payload_json, user_id, timestamp)
```

### 匹配 pipeline（关键改进：**不是** LLM 打每个岗位）

```
[硬过滤]   地理 / remote / authorization / 资历 / 薪资
   │
   ▼
[BM25 召回]   从 facts 提技能/角色关键词 → 在 postings.jd_text BM25 召回 top 200
   │
   ▼
[语义召回]   facts embedding（per fact）vs jd embedding（per chunk）→ top 200
   │
   ▼
[RRF 重排]   Reciprocal Rank Fusion 合并两路 → top 50
   │
   ▼
[LLM 解释 + 打分]   对 top 50 用 Claude Sonnet 给 fit_score + matched/missing + 一句话理由
   │
   ▼
[matches 表 → UI]
```

**Why**：假设 MVP 规模 50 公司 × 30 新岗位/天 = 1500 新岗位/天。如果每个都过 Claude（5K input + 500 output），按 Sonnet $3/$15 per MTok ≈ $0.02/岗位 × 1500 = $30/天 = **$900/月**，超 MVP 预算 100×。混合检索把 LLM 调用收敛到 top 50 → 约 **$1/天**。

### 职位 taxonomy 分层

```yaml
families:
  - name: ml_engineering
    keywords: [machine learning engineer, ml engineer, mle, ai engineer]
    subdomains:
      - name: llm_infra
        keywords: [llm, large language model, inference, vllm, sglang, finetuning]
        skill_evidence: [pytorch, transformers, vllm, deepspeed, ray]
      - name: ml_platform
        keywords: [feature store, mlops, mlflow, model serving]
        skill_evidence: [kubeflow, airflow, sagemaker, vertex ai]
    common_ambiguity:
      - rule: "Data Scientist title with heavy MLOps content → ml_engineering not data_science"
  - name: applied_research
    keywords: [research engineer, research scientist, applied scientist]
    subdomains:
      - name: foundation_models
        keywords: [pretraining, alignment, rlhf, agent]
      - name: applied_nlp
        keywords: [nlp, semantic search, llm applications]
  - name: data_science
  - name: platform_engineering  # ml infra adjacent
  - name: product_engineering   # AI features in product
```

岗位入库时跑一遍 taxonomy 分类，写 `postings.taxonomy_*`；匹配时硬过滤"用户感兴趣的 family"，提升 precision。

### 简历定制：两阶段 + 三约束 + Source-ID guard

#### 阶段 1：事实抽取（一次性，profile 创建时）

用户输入：自由文本 / LinkedIn 导出 JSON / 已有 PDF 简历。

Claude 抽成结构化 facts：

```python
class Fact(BaseModel):
    id: str                       # uuid，永久 fact_id（Source-ID guard 锚点）
    type: Literal["experience_bullet", "skill", "project", "education", "certification"]
    content: str                  # 用户原话（不改写）
    tags: list[str]               # ["python", "kubernetes", "team-lead"]
    metrics: list[Metric]         # [{"name": "users", "value": 1_000_000}]
    employer: Optional[str]
    role: Optional[str]
    time_range: Optional[DateRange]
    source_evidence: str          # "来自我的 LinkedIn 导出 - Experience #3"
```

**用户必须人工 review + 校真所有抽取出的 facts**。校真后写入 `facts` 表。

#### 阶段 2：定制（每次申请触发）

输入：所有 facts + 目标 JD + taxonomy 分类。

Claude 输出**强约束 JSON Schema**：

```python
class TailoredResume(BaseModel):
    summary: BulletWithSource
    experience: list[ExperienceBlock]
    skills: list[SkillWithSource]
    education: list[EducationBlock]
    unsupported_claims: list[str] # 模型想说但 facts 没有的 → 拒绝并 regen
    gap_report: str               # 招聘要求里 facts 满足不了的部分（诚实暴露）

class BulletWithSource(BaseModel):
    text: str
    source_fact_ids: list[str]    # 必填，至少 1 个；每个 ID 必须存在于 facts 表
```

**三约束**：

1. **Template 约束** —— 生成的 sections 必须匹配 `constraints.sections`。
2. **JSON Schema 约束** —— Anthropic structured output（或本地 pydantic 校验）保证 schema 严格。
3. **Fact 校验约束** —— 后处理验证每个 `source_fact_ids` 都在 `facts` 表存在；任何 unsupported = 拒绝、regen 一次、再拒绝 → 报错给用户（让用户决定补 fact 还是放弃）。

#### Source-ID 防幻觉单测

```python
def test_no_hallucination(tailored: TailoredResume, facts: dict[str, Fact]):
    for bullet in walk_all_bullets(tailored):
        assert bullet.source_fact_ids, "every bullet must have ≥1 source_fact_id"
        for fid in bullet.source_fact_ids:
            assert fid in facts, f"fact {fid} not in master profile"
    assert not tailored.unsupported_claims, "model attempted unsupported claims"
```

CI 必须跑这条，集合若干 `(profile, jd)` fixture。

### 渲染：docxtpl ATS-friendly

- 模板：`templates/resume_ats.docx`，**单列** + Arial 11pt + 0.75-inch 边距 + 无表格 / 图形 / 页眉脚。
- 用 docxtpl 填充 `TailoredResume` JSON → 输出 `{company}_{title}_{date}.docx`。
- Phase 2 加 RenderCV 出 PDF（可选高质量分支）。

### Web UI（React + Vite + TS）

5 个主页面：

1. **Dashboard** —— 新高匹配岗位列表（fit_score 排序；按 company / remote / date / taxonomy 过滤）。
2. **Posting detail** —— JD 全文、matched/missing requirements、gap report、「生成定制简历」按钮。
3. **Resume preview** —— 定制简历预览（标红 source_fact_id 高亮显示溯源）+ 下载 `.docx` / `.pdf`。
4. **Application tracker** —— 状态看板（applied / screened / interview / offer / rejected）。
5. **Master profile editor** —— facts 表浏览 + 增删改（每个 fact 必须有 `source_evidence` 才能保存）。

### Cron / Ingest

复用 heartbeat 模式：`scripts/ingest.sh` 每日 08:00（本地时间）→ `python -m ai_job_copilot.ingest`：

1. 对 `companies.yaml` 每家公司 → 调对应 Source adapter。
2. 归一化 + taxonomy 分类 → upsert 到 `postings`。
3. 对新岗位（first_seen_at = 今天）→ 跑混合检索 pipeline → 写 `matches`。
4. 生成每日 digest（高匹配新岗位列表）→ UI 通知（Phase 2 加邮件）。

### Switch / Kill conditions（明确的升级 gate）

| 维度 | 现在 | Switch 触发 | 切换目标 |
|---|---|---|---|
| LLM | Sonnet 4.5 | 单次定制 fact_id 校验 > 2 次 regen | Opus 4.7 |
| Storage | SQLite | postings > 100k 行 OR p95 查询 > 500ms | Postgres |
| Embedding | 本地 voyage-3-lite | top-50 召回 P@10 < 0.6 | OpenAI text-embedding-3-large |
| Custom scrape | tavily-skill | Apple/Google/Meta 站内 JSON 改版且 tavily 拿不到 | Playwright + Browserbase |
| Frontend | 本地 dev | 多设备 / 外网用 | Fly.io / Render 部署 |
| Backend hosting | 本地 | 同上 + 接收 webhook | 同上 |

### Cost model（按 phase 量级）

基于 Sonnet 4.5 $3/$15 per MTok、Haiku 4.5 $0.80/$4 per MTok、voyage-3-lite $0.02/MTok：

| Phase | 规模 | 主要成本项 | 估算 |
|---|---|---|---|
| 0-1（个人 MVP） | 1 用户、50 申请/月 | Claude 定制 50 × $0.05 = $2.5；taxonomy/match Haiku $1；embedding $0.5 | **$5-10/月** |
| 2（个人 + 优化） | 1 用户、200 申请/月 | 同上 ×4 + Browserbase $20 | **$30-50/月** |
| 3（产品化） | 100 用户、平均 50 申请/月 | LLM $500 + infra $50 + embedding $50 + hosting $50 | **$650/月**（≈$6.50/用户/月） |

参考定价：Teal $19/月、Careerflow $23.99/月 → Phase 3 至少 $19/月，毛利 65%+。

---

## §3 Test 策略 —— 未来 `docs/test.md`

### L1 离线召回（matching pipeline）

构建 golden set：50 (profile, posting) 配对，双标注（鸭哥 + 模型）打 strong-match / weak-match / no-match。

| 指标 | 目标 |
|---|---|
| P@10 | top-10 中 strong-match 比例 ≥ 0.7 |
| R@50 | 所有 strong-match 中 top-50 召回到的比例 ≥ 0.9 |
| F1 | 综合 |

边界角色重点：ML Engineer vs Data Scientist 这种常混淆的。

### L2 生成质量（每份 tailored resume 必跑）

| 指标 | 目标 |
|---|---|
| Schema 有效率 | 100%（不达标 = 系统 bug） |
| **Source-ID 校验（事实一致率）** | **100%**（任何 unsupported = 拒绝 + regen + 报错） |
| 量化指标保真率 | 100%（resume 中的数字必须能在 facts 找到） |
| ATS 关键词覆盖率 | JD top-10 必填技能 → resume 出现 ≥ 8 个 |
| 人工编辑幅度 | 用户最终投出去的版本 vs 生成版本 diff 行数 < 10 |

### L3 在线 A/B（Phase 3）

- 实验单元 = user-posting 配对
- 主指标：14-30 天 callback / interview rate
- 先跑 A/A 验证无偏（同策略两组）
- A/B 对照：手写简历 vs 我们的工具
- 次指标：导出率 / 保存率 / 投诉率 / 误投率

### 离线 + 集成测试

- **Adapter fixture 单测** —— 每个 ATS 录一份真实 JSON 到 `tests/fixtures/`，断言归一化正确；离线可跑。
- **Live smoke** —— 每个 ATS 调一个真实公司的真实 endpoint，断言能拉到 ≥ 1 个岗位。
- **Resume 真实性单测** —— 合成 profile + 假 JD → 生成 resume → 跑 Source-ID 单测。
- **Schema 单测** —— 所有 SQLModel 表 round-trip（insert + read back）。

### 隐私 / 合规测试

- `.env` 不在 `git ls-files`（断言）。
- master profile 数据目录被 gitignore（断言 `.gitignore` 含 `data/`）。
- logger 不会把 `master_profile.profile_json` 或 `facts.content` 写到 stdout / log（断言：跑 ingest，grep log，敏感字段命中 = fail）。

---

## §4 合规 / 隐私（贯穿）

- **official-first** —— 所有数据来源符合 RFC 9309 四层检查。
- **不 scrape** —— LinkedIn / Indeed / Glassdoor / Levels.fyi。
- **限速** —— 所有 ATS 调用 ≤ 1 req/sec/host；按官方文档限速更严的从严。
- **PII 隔离** —— master profile + facts 表只在本地 SQLite；不上传到第三方分析服务；LLM 调用只传需要的 fact 字段（content + tags + metrics），不传整个用户对象。
- **可删除** —— 用户在 UI 一键 delete 自己的 master profile + 所有 facts + 所有 tailored_resumes（CASCADE）。
- **GDPR / CCPA / EEOC 锚点（Phase 3）** ——
  - GDPR Art. 22：完全自动化决策需谨慎；我们坚持人工最终编辑权（天然合规）。
  - CCPA delete right：见上。
  - EEOC：taxonomy 不含 protected class（race / gender / age）。

---

## §5 分阶段

### Phase 0：scaffold（本轮）

按 `project_scaffold` 在 `adhoc_jobs/ai_job_copilot/` Phase 0-2：private repo → 骨架 + docs/{prd,rfc,test,working}.md → AGENTS.md → 空的 src/。

**Switch gate**：用户 working summary 实际形态（自由文本 / LinkedIn 导出 / PDF）决定 Phase 1 第一周做哪个 fact extraction 入口。

### Phase 1：核心闭环（易源）

实现：

- Greenhouse / Lever / Ashby / Workday adapters（独角兽 + Nvidia/Tesla）
- 归一化 + taxonomy 分类（v1 keyword + Claude 二分类；先不上学习排序）
- 混合检索 pipeline（BM25 + 语义 + RRF + LLM 解释）
- master profile 抽取（一次性，Claude + 人工 review）
- 简历定制：两阶段 + 三约束 + Source-ID guard
- docxtpl 渲染 `.docx`
- 最小 React UI（Dashboard + Posting detail + Resume preview）
- 申请追踪
- 本地 cron 每日 ingest

**Switch gate**：单次定制 fact_id regen > 2 次 → 升 Opus。

### Phase 2：难源 + 打磨

- Apple / Google / Meta adapters（站内 JSON / tavily-skill / 聚合 API fallback）
- 增量 ingest + 变更检测
- 每日 digest（UI + 可选邮件）
- PDF 输出（RenderCV）
- L2 离线评估 dashboard
- 简历版本 diff 视图
- 浏览器扩展（一键从 LinkedIn 岗位详情 → 我们的系统，**read-only**）

**Switch gate**：postings > 100k 行 OR p95 查询 > 500ms → Postgres。

### Phase 3：产品化

- 多租户（auth、租户隔离）
- 把「master profile + JD → 定制简历」引擎抽成 public skill（ecosystem 模型）
- 部署到 Fly.io / Render
- Stripe 订阅
- L3 在线 A/B
- GDPR / CCPA / EEOC 全面合规
- 与 ATS 官方合作集成（Greenhouse Harvest API、Indeed Partner API）

**Switch gate**：自己用 ≥ 3 个月 + ≥ 5 个非鸭哥的人主动想用 → Phase 3。

---

## §6 复用 workspace 资产（dogfood）

- `periodic_jobs/` + `claude_runner.py` cron 模式 → 定期 ingest 入口。
- `adhoc_jobs/tavily-skill/`（`python -m tavily_skill`）→ Custom adapter 兜底（Apple/Google/Meta 站内抓 + JD 富化）。
- `claude-api` skill → 匹配 LLM 解释层 + 简历定制（prompt caching：缓存 master profile facts，变 JD）。
- `project_scaffold` skill → 项目结构 + 三脚本 contract + `APP_ROOT_PATH`。
- 本设计本身用 `workflow_deep_research_survey` + `bestpractice_multi_agent_analysis` + `bestpractice_product_decision_analysis` 产出。

---

## §7 项目结构（落 `adhoc_jobs/ai_job_copilot/`）

```
adhoc_jobs/ai_job_copilot/
├── AGENTS.md                           # 项目本地规则
├── .gitignore  .env.example
├── pyproject.toml
├── companies.yaml                      # 公司 → ATS 注册表
├── docs/
│   ├── prd.md                          # §1
│   ├── rfc.md                          # §2
│   ├── test.md                         # §3
│   └── working.md                      # changelog + lessons
├── src/ai_job_copilot/
│   ├── __init__.py
│   ├── main.py                         # FastAPI app
│   ├── models.py                       # SQLModel schema
│   ├── sources/{base,greenhouse,lever,ashby,workday,custom}.py
│   ├── ingest.py
│   ├── taxonomy.py
│   ├── match/{retrieve,explain}.py
│   ├── tailor/{extract_facts,generate,render_docx}.py
│   └── templates/resume_ats.docx       # ATS-friendly Word 模板
├── frontend/                           # React+Vite+TS
│   ├── src/  package.json  vite.config.ts
├── scripts/
│   ├── start_backend.sh  start_frontend.sh  build_frontend.sh
│   └── ingest.sh
├── tests/
│   ├── fixtures/                       # 各 ATS 录制 JSON
│   ├── test_sources.py
│   ├── test_tailor_source_id.py        # Source-ID 防幻觉单测
│   └── ...
└── data/                               # gitignored，本地 SQLite + master profile
```

### `.env.example`（private repo，placeholder）

```bash
ANTHROPIC_API_KEY=
# Embeddings (Phase 1 voyage-3-lite 本地，无需 key；Phase 2 可换 OpenAI)
# OPENAI_API_KEY=
# 部署
APP_ROOT_PATH=
APP_PORT=8000
```

### `AGENTS.md`（项目本地）

最少覆盖：

1. 项目结构说明（→ 上面的目录树）
2. `working.md` 更新要求（每个 commit 一条 atomic bullet）
3. 频繁 commit 要求（每完成一个 logical unit 就 commit）
4. Python 3.12 + uv pip + `.venv/`
5. 不能破坏的兼容约束：
   - master profile schema 必须向前兼容（升级要带 migration）
   - resume JSON schema 必须强约束（Source-ID guard 不能跳过）
   - ATS adapter 公共契约不能 break（新增字段 only，不删/改）

---

## §8 开放问题 + Prior Art

### 开放问题（实施时确认）

1. **Working summary 当前形态**：自由文本 / LinkedIn 导出 JSON / 已有 PDF？决定 Phase 1 fact extraction 入口优先级。
2. **目标地区**：MVP 默认全美 + remote；要不要加海外（欧洲 / 亚洲）？影响 location 过滤 + 时区。
3. **申请回传链路**：用户投了之后怎么把"已投"状态打回我们的系统？手动 / 邮件转发 / 浏览器扩展？决定 application tracker 的 UX。
4. **成本依赖参数**：50 申请/月只是 MVP 假设；用户实际频率影响 LLM 成本估算。
5. **GitHub Jobs 状态**：已停服；要不要支持已有开源 mirror？

### Prior Art

| Repo | 角度 | 借鉴点 |
|---|---|---|
| [career-ops](https://github.com/santifer/career-ops) | Claude Code + Playwright + 按 JD 评分 + 生成 CV | A-F 评分 / 10 维度 / per-listing CV |
| [kalil0321/ats-scrapers](https://github.com/kalil0321/ats-scrapers) | 多 ATS scraper 集合 | Adapter 实现参考 |
| [lever/postings-api](https://github.com/lever/postings-api) | Lever 官方 | 端点 + 参数 reference |
| [plibither8/jobber](https://github.com/plibither8/jobber) | 个人 job tracker | UI / 状态机参考 |
| [jsonresume/resume-cli](https://github.com/jsonresume/resume-cli) | JSON Resume + 多 theme 渲染 | 主 schema 参考 |

---

## v2 升级 changelog（vs 27 号 v1）

| 改动 | 来源 |
|---|---|
| 加核心三原则（official-first / retrieval-before-generation / human-in-the-loop） | File 3 |
| 整体重组成 PRD/RFC/Test 内部分节（对齐 project_scaffold 切分） | project_scaffold guideline |
| 数据获取加 RFC 9309 四层合规 | File 3 |
| 数据模型加 facts 表（事实库）+ resume_versions（一等公民）+ audit_logs | File 1 + File 3 |
| 匹配从「LLM 打每个岗位」改成混合检索 pipeline（BM25 + 语义 + RRF + LLM 仅在解释） | File 3 |
| 加职位 taxonomy 分层 | File 3 |
| 简历定制：两阶段 + 三约束 + **Source-ID 防幻觉**（source_fact_ids 字段 + 单测） | File 1 + File 3 |
| 加 Cost model（按 phase + 真实 LLM 单价） | File 1 |
| 加 Switch / Kill conditions（每个维度的升级 gate） | File 1 |
| Test 替换：3 层评估（L1 召回 / L2 生成质量 / L3 在线 A/B） | File 3 |
| 加实证锚（Wonsulting 2% + Glassdoor 250） | File 1 + File 2 |
| 产品定位 4 分类（我们 = ATS 优化器 + 检索定向，**不**做端到端代理） | File 2 |
| 开放问题扩到 5 + Prior Art 列 5 个 repo | File 1 |
