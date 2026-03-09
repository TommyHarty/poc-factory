# POC Factory

An agentic POC generation platform that automatically creates a folder of focused, production-quality POCs for any agentic systems topic.

## What it does

Submit a phrase like `"prompt injection guardrails"` and get back:
- 5-10 ranked, focused POC ideas
- Each POC built from your starter repo (public or private)
- Claude Code invoked to implement each POC
- Validation and auto-repair for failures
- Prose teaching chapter + code walkthrough per POC
- Complete file structure with README, tests, Docker assets

## Quick Start

### 1. Install

```bash
pip install -e ".[dev]"
# or
bash scripts/setup.sh
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env with:
#   OPENAI_API_KEY=sk-...         (for ideation, ranking, markdown)
#   STARTER_REPO_URL=https://...  (your FastAPI starter repo)
#   GITHUB_TOKEN=ghp_...          (only needed for private starter repos)
```

### 3. Run

```bash
bash scripts/run.sh
# Or directly:
uvicorn app.main:app --reload
```

### 4. Create a run

```bash
curl -X POST http://localhost:8000/runs \
  -H "Content-Type: application/json" \
  -d '{
    "phrase": "prompt injection guardrails",
    "technologies": ["fastapi", "pydantic"],
    "target_poc_count": 5,
    "dry_run": false
  }'
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/runs` | Create a new generation run |
| GET | `/runs/{run_id}` | Get run status and POC statuses |
| GET | `/runs/{run_id}/artifacts` | Get artifact paths/metadata |
| POST | `/runs/{run_id}/resume` | Resume an interrupted run |
| POST | `/runs/{run_id}/retry-failures` | Retry only failed POCs |

## Example Request

```json
{
  "phrase": "monitoring and observability",
  "technologies": ["langfuse", "fastapi"],
  "optional_packages": ["langgraph"],
  "target_poc_count": 8,
  "preferences": {
    "use_docker": true,
    "use_pytest": true,
    "prefer_mocks": true,
    "include_mermaid": false
  }
}
```

## Output Structure

```
output/
  prompt-injection-guardrails/
    prompt-injection-guardrails.md   ← intro chapter for the topic
    run-report.json
    run-summary.md
    01-untrusted-data-boundary/
      CLAUDE.md
      README.md
      pyproject.toml
      .env.example
      app/
      tests/
      _docs/
        01-untrusted-data-boundary.md
        code-implementation-01-untrusted-data-boundary.md
      build-report.json
    02-minimise-model-authority/
      ...
```

## Architecture

```
app/
  api/            - FastAPI endpoints and schemas
  application/    - Services and orchestrators
  domain/         - Business logic (no infrastructure deps)
  graph/          - LangGraph orchestration
  infrastructure/ - Adapters (LLM, Git, filesystem, DB)
  templates/      - Prompt templates (markdown files)
  tests/          - Unit, integration, and E2E tests
```

### Graph Flow

**Run level:**
```
ingest_request -> normalize_phrase -> expand_poc_candidates -> rank_and_select_pocs
  -> create_run_plan -> fan_out_poc_jobs -> aggregate_run_results -> finalize_run
```

**Per-POC level:**
```
prepare_poc_folder -> acquire_starter_repo -> generate_poc_claude_md
  -> invoke_claude_code_build -> run_static_checks -> run_tests
  -> assess_build_result -> [invoke_claude_code_repair if needed]
  -> generate_prose_markdown -> generate_code_walkthrough_markdown
  -> update_readme -> update_env_example -> update_docker_assets
  -> write_build_report -> mark_poc_complete
```

## Configuration

Key environment variables (see `.env.example` for full list):

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | For POC ideation, ranking, and markdown generation |
| `STARTER_REPO_URL` | URL of the FastAPI starter repo to clone for each POC |
| `STARTER_REPO_BRANCH` | Branch to use (default: `master`) |
| `GITHUB_TOKEN` | Only required for private starter repos |
| `CLAUDE_CODE_COMMAND` | Claude Code CLI command (default: `claude`) |
| `CLAUDE_CODE_TIMEOUT_SECONDS` | Timeout per POC build (default: 300) |
| `ENABLE_LANGFUSE` | Enable Langfuse tracing |
| `OUTPUT_ROOT` | Where to write generated POCs |
| `WORK_ROOT` | Working directory for caches and DB |

## Running Tests

```bash
bash scripts/test.sh
# Or:
pytest app/tests/ -v
```

## Dry Run Mode

Set `"dry_run": true` in the request to generate CLAUDE.md files and plans without invoking Claude Code. Useful for inspecting the plan before full execution.

## Langfuse Integration

Set `ENABLE_LANGFUSE=true` with valid keys to enable trace logging for:
- Run creation
- POC ideation and ranking
- Per-POC builds
- Validation and repair
- Markdown generation

The app works without Langfuse (all calls fall back to no-ops).
