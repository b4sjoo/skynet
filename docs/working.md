# Working Log

## 2026-08-05

- Synced external/internal writing skills from private workspace: mandatory Round 4 CLI mechanical self-check (`external_prose_lint_cli`), genre-label writer lever, polarity diagnostics, updated internal concept-order hard rules. Stripped private paths/names; no secrets in CLI or skill text.

## 2026-07-29

- Added `m5stack-sticks3-skill` to the public ecosystem for source-backed M5StickS3 board bring-up and hardware acceptance checks; it contains no workspace-private overlay or device secrets.

## 2026-07-20

- Added `apple-photos-skill` for normalized Apple Photos metadata workflows and explicitly authorized, dry-run-first PhotoKit mutations; the public entry preserves its live-unverified alpha boundary.
- Added `bright-horizons-photo-sync-skill` for resumable My Bright Day backups with integrity verification; credentials and family data remain local.
- Updated the Antigravity CLI guide and quick reference for AGY 1.1.4: documented the top-level `agy --print` interface, rejected nonexistent `agy run` and JSON event flags, and added the new headless inheritance of persisted `settings.json` policies.
- Added `ai-session-profanity-rate` to the public ecosystem for cached sub-agent profanity-unit analysis over local AI-session user messages, with private local artifacts and redacted JSON/chart outputs.

## 2026-07-16

- Added `chat-gpt-oauth-skill` to the public ecosystem as an opt-in local ChatGPT Plus/Pro OAuth compatibility reference; documented that its private endpoint is unstable and not recommended for production.

## 2026-07-15

- Added a public AI Session Search & Archive workflow with source routing, lexical-first retrieval, fresh semantic-search file lists, freshness checks, and privacy-safe result rules.
- Added `ai_session_export` to the public ecosystem and documented a daily multi-source Session Sync covering OpenCode, Claude Code, Codex, Antigravity, and Second Mind.
- Added the private `contexts/ai_sessions/<source>/` route to the starter workspace map.

## 2026-07-12

- Added `genai_portrait_skill` to the public skill ecosystem for identity-preserving portrait, headshot, and ID-photo editing with photographic coherence.

## 2026-07-10

- Added `innovation-assistant-skill` to the public skill ecosystem as the Innovation capability for structured innovation pipelines (SIT + Think Bigger).

## 2026-06-06

- Added `google-maps-routing-skill` to the public skill ecosystem as the Maps / travel capability for Google Maps Routes + Geocoding CLI workflows.
- Updated README, setup guide, and starter skill index examples so Google Maps appears alongside other standalone public skill repos.

## 2026-05-25

- Moved image generation from built-in skill (`rules/skills/generate_image.md`, `tools/generate_image.py`) to independent public repo [`image-generation-skill`](https://github.com/grapeot/image-generation-skill). The starter repo now references it via `docs/SKILL_ECOSYSTEM.md` instead of shipping its own implementation.
- Removed `rules/skills/generate_image.md`, `tools/generate_image.py`, and `tools/tests/test_generate_image.py` from the starter set.
- Updated `rules/skills/INDEX.md` to point users to the ecosystem index for image generation.
- Added image-generation-skill row to `docs/SKILL_ECOSYSTEM.md`.

- Added three generic best-practice skills to the starter set: PDF-to-Markdown with Docling, GUI automation methodology, and product/technical decision reverse engineering.
- Redacted the PDF conversion skill's local report path so the public version stays workspace-neutral.

- Added a human- and agent-readable public skill ecosystem index at `docs/SKILL_ECOSYSTEM.md`.
- Linked the ecosystem index from `README.md`, `setup_guide.md`, and `rules/skills/INDEX.md` so users can discover standalone skill repos without loading every repo into the starter skill index.
- Kept the model as public repo + private workspace overlay: public repos hold generic CLI contracts and tests; local workspaces hold aliases, paths, endpoints, credentials, and business context.
- Updated `rules/skills/project_scaffold.md` with the public skill repo installation convention: loose Markdown-based install, one root/router skill per repo, and private overlays outside the public repo.

## 2026-05-27

- Adapted AI Heartbeat to a Claude Code backend: added `periodic_jobs/ai_heartbeat/src/v0/claude_runner.py` (`claude --print` agentic backend) plus a `HEARTBEAT_BACKEND` switch and portable `ROOT_DIR` in observer/reflector. (cfcd102)
- Added a Claude Code observer cron section to `docs/CRONTAB.md`; observer auto-runs daily, reflector stays manual. Ran the observer once, so `OBSERVATIONS.md` has its first entries. (4be3cf4)
- Rewrote `rules/skills/workflow_parallel_subagents.md` for Claude Code: Agent tool instead of mcp_task/category/background_output, Claude-only + no-nested-subagent constraints, file-based scratchpad, OpenCode->CC mapping appendix. Updated `AGENTS.md` routing, `bestpractice_multi_agent_analysis.md`, `INDEX.md`. (248d726)
- Aligned `workflow_deep_research_survey.md` and `bestpractice_temporal_info_verification.md` to Claude Code. (cb50960)
- Standardized those two skills' web search/extract on the public `tavily-skill` instead of the per-machine MCP tavily tools. (499b83d)
- Removed orphaned image-generation files that were still present locally despite the 2026-05-25 extraction note (`generate_image.md`, `tools/generate_image.py`, its test). (e218eca)
- Installed `tavily-skill` under `adhoc_jobs/tavily-skill/` (editable install into `.venv`), exposed one root skill in `rules/skills/INDEX.md`, added `TAVILY_API_KEY` to `.env.example`, and gitignored the vendored repo (re-clone via `docs/SKILL_ECOSYSTEM.md`).
- Smoke-tested the `tavily-skill` CLI end-to-end: `search` + `extract` both pass; key loaded from `.env`; the `raw_content=markdown` and `answer=off` agent defaults verified live.
- Researched and designed the **AI Job Copilot** MVP using `workflow_deep_research_survey` (3 parallel Explore agents on data acquisition / resume+ATS / competitors+legal, cross-validated). Saved the standalone design doc at `contexts/survey_sessions/ai_job_copilot_design_20260527.md`; implementation deferred to a later round.
- Initialized the workspace as a public GitHub repo at `https://github.com/b4sjoo/skynet.git` and pushed `main`. `.env` is not tracked; credential scan was zero-hit before pushing.
