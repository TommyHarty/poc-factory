# CLAUDE.md — Build the POC Factory Agentic System

You are building a **production-grade internal platform** that automatically generates a folder of small, focused POCs for a given agentic-systems concern.

The user will invoke the platform with:
- an **initial phrase** such as:
  - `prompt injection guardrails`
  - `monitoring and observability`
  - `tool calling reliability`
  - `evaluation and regression testing`
- a list of **required technologies/packages** to use where relevant, such as:
  - `langfuse`
  - `langgraph`
  - `chromadb`
  - `postgres`
  - `pydantic-ai`
  - `fastapi`
- an optional **POC count target** between **8 and 15**
- optional preferences such as:
  - favor deterministic workflows
  - prefer Dockerized infra
  - use pytest
  - use uv vs pip
  - prefer local mocks over paid APIs
  - include Mermaid diagrams in markdown

Your task is to create the **entire system** that automates the user's current workflow.

---

## Mission

Build an application that:

1. Accepts a request via a public API endpoint.
2. Expands the initial phrase into **8–15 highly relevant POC ideas**, ordered by importance/commonness/practicality.
3. Ensures **each POC is tightly scoped to one approach only**.
4. Clones or copies a **starter repo** from a private GitHub repository for each POC.
5. Creates a dedicated subfolder for each POC under a structured output directory.
6. Generates a **POC-specific `CLAUDE.md`** file inside each POC folder, based on a reusable starter template plus the specific POC requirements.
7. Invokes **Claude Code programmatically** for each POC so Claude Code builds the full POC repo from the starter.
8. Runs static/type/test validation.
9. If there are errors, invokes Claude Code again with a focused remediation prompt.
10. Generates two markdown deliverables for each POC:
    - a **full prose chapter**
    - a **step-by-step implementation guide**
11. Updates repo artifacts where needed:
    - `README.md`
    - `Dockerfile`
    - `requirements.txt`
    - `.env.example`
    - optional `docker-compose.yml`
12. Produces a final output structure like:

```text
output/
  prompt-injection-guardrails/
    01-untrusted-data-boundary/
      CLAUDE.md
      README.md
      Dockerfile
      requirements.txt
      .env.example
      src/...
      tests/...
      01-untrusted-data-boundary.md
      code-implementation-01-untrusted-data-boundary.md
      build-report.json
    02-minimise-model-authority/
      ...
    ...
  monitoring-and-observability/
    01-basic-request-tracing/
      ...
```

The system itself should also produce:
- a **run manifest**
- a **summary report**
- per-POC **status metadata**
- logs, traces, and structured outputs for auditing and retryability

---

## High-level product goals

This system is an **agentic POC factory**.

It should allow the user to go from a single topic phrase to:
- a ranked set of focused POC repos
- complete generated code
- prose teaching material
- implementation walkthroughs
- a consistent filesystem structure
- reproducible outputs

This platform is not a toy. Treat it as a serious internal engineering product.

---

## Core constraints

### 1) One POC = one approach
Every POC must teach and implement **exactly one focused approach**.

Good examples:
- `untrusted-data-boundary`
- `structured-tool-allowlist`
- `output-schema-validation`
- `basic-langfuse-tracing`
- `trace-linked-evals`
- `fallback-model-routing`

Bad examples:
- `security-everything`
- `observability-complete-platform`
- `guardrails-plus-monitoring-plus-routing`
- anything that bundles multiple distinct concerns into one POC

### 2) POCs must be ranked
Generated POCs must be ordered by:
1. practical importance
2. commonness in real systems
3. foundational dependency for later POCs
4. teaching value
5. implementation clarity

### 3) Consistent naming
All output must use deterministic naming conventions.

For a phrase like `prompt injection guardrails`, normalize to:
- root folder: `prompt-injection-guardrails`

For POCs:
- `01-untrusted-data-boundary`
- `02-minimise-model-authority`
- `03-structured-tool-allowlist`

Markdown files in each POC folder:
- `01-untrusted-data-boundary.md`
- `code-implementation-01-untrusted-data-boundary.md`

### 4) Starter-repo-first generation
Every POC must start from the same existing starter repo pulled from the user’s private GitHub repo.

Do not scaffold from scratch unless the starter retrieval fails and a fallback mode is explicitly enabled.

### 5) Default to lightweight implementations
Keep POCs minimal and focused.
Mock non-essential side effects unless the concept requires the real dependency.
Do not overbuild.

### 6) Fully auditable
Every important step must be logged in structured form.
Every LLM-produced artifact must be persisted.
Every retry must be visible.

---

## Required architecture choice

Build this system using:

- **Python**
- **FastAPI** for the public API
- **LangGraph** for orchestration
- **Pydantic** for request/response/state schemas
- **Structured logging**
- **Langfuse** for tracing / prompt versioning / observability when enabled
- **pytest** for tests
- **filesystem-based output persistence**
- optional persistence layer for job metadata:
  - start with SQLite or Postgres
  - choose the simplest robust option
- programmatic Claude Code invocation via CLI / headless execution

Use clean architecture principles with a strong bias toward:
- orchestration layer
- domain layer
- infrastructure/adapters
- explicit state transitions
- deterministic side-effect boundaries

---

## Important implementation guidance

### Why LangGraph
Use LangGraph as the orchestration backbone because this system is:
- stateful
- multi-step
- branch-heavy
- retryable
- suited to explicit node responsibilities
- able to benefit from checkpointing and resumability

### Why separate responsibilities into nodes
The workflow contains distinct responsibilities:
- request normalization
- POC ideation/ranking
- starter repo acquisition
- folder preparation
- CLAUDE.md generation
- Claude Code execution
- validation
- repair
- markdown generation
- final reporting

These should not be collapsed into one giant agent.

You must model them as explicit graph nodes with typed state.

---

## Deliver the following

Create a full project that includes at least:

### 1) API
Implement FastAPI endpoints such as:

#### `POST /runs`
Create a new generation run.

Example request:
```json
{
  "phrase": "prompt injection guardrails",
  "technologies": ["fastapi", "langgraph"],
  "optional_packages": ["langfuse"],
  "target_poc_count": 10,
  "starter_repo": {
    "provider": "github",
    "repo_url": "https://github.com/<org>/<private-starter-repo>.git",
    "branch": "main"
  },
  "preferences": {
    "use_docker": true,
    "use_pytest": true,
    "prefer_mocks": true,
    "include_mermaid": true
  }
}
```

#### `GET /runs/{run_id}`
Return current run status, summary, and per-POC statuses.

#### `GET /runs/{run_id}/artifacts`
Return artifact paths / metadata.

#### `POST /runs/{run_id}/resume`
Resume an interrupted run.

#### `POST /runs/{run_id}/retry-failures`
Retry only failed POCs or failed steps.

### 2) LangGraph orchestration
Implement a graph with clearly separated nodes.

### 3) Claude Code integration
The platform must create POC-specific `CLAUDE.md` files and invoke Claude Code programmatically for each POC.

### 4) Validation and repair
Run validation for each generated POC and selectively retry/fix when needed.

### 5) Markdown generation
Generate:
- one prose chapter markdown file
- one implementation walkthrough markdown file

### 6) Final reports
Create machine-readable and human-readable reports.

---

## Required graph design

Implement a graph roughly along these lines.

### Global run-level nodes

1. `ingest_request`
2. `normalize_phrase`
3. `expand_poc_candidates`
4. `rank_and_select_pocs`
5. `create_run_plan`
6. `fan_out_poc_jobs`
7. `aggregate_run_results`
8. `finalize_run`

### Per-POC subgraph nodes

1. `prepare_poc_folder`
2. `acquire_starter_repo`
3. `generate_poc_claude_md`
4. `invoke_claude_code_build`
5. `run_static_checks`
6. `run_tests`
7. `assess_build_result`
8. `invoke_claude_code_repair` (conditional)
9. `generate_prose_markdown`
10. `generate_code_walkthrough_markdown`
11. `update_readme`
12. `update_env_example`
13. `update_docker_assets`
14. `write_build_report`
15. `mark_poc_complete`

### Optional cross-cutting nodes

- `record_trace_metadata`
- `persist_checkpoint`
- `collect_metrics`
- `apply_rate_limit`
- `human_review_gate` (optional, disabled by default)

---

## Required state design

Create explicit Pydantic models for graph state.

At minimum include:

### Run state
- `run_id`
- `phrase`
- `normalized_phrase`
- `technologies`
- `optional_packages`
- `target_poc_count`
- `preferences`
- `starter_repo`
- `output_root`
- `candidate_pocs`
- `selected_pocs`
- `run_status`
- `errors`
- `warnings`
- `started_at`
- `updated_at`
- `completed_at`

### POC state
- `poc_index`
- `poc_title`
- `poc_slug`
- `poc_goal`
- `why_it_matters`
- `scope_boundaries`
- `required_packages`
- `folder_path`
- `claude_md_path`
- `build_status`
- `validation_status`
- `repair_attempts`
- `artifacts`
- `logs`
- `test_results`
- `static_check_results`
- `markdown_status`
- `readme_status`
- `docker_status`
- `env_example_status`

### Artifact metadata
- `path`
- `type`
- `created_at`
- `sha256`
- `size_bytes`
- `status`

### Validation result
- `tool`
- `success`
- `stdout`
- `stderr`
- `exit_code`
- `started_at`
- `finished_at`

---

## Domain modeling requirements

Design the internal domain around these concepts:

- **Run**
- **PocPlan**
- **PocExecution**
- **Artifact**
- **ValidationSuite**
- **RepairAttempt**
- **StarterRepoSource**
- **TechnologySelection**
- **GenerationPolicy**
- **MarkdownArtifact**
- **RunReport**

Avoid vague blobs like `data: dict[str, Any]` unless there is no better option.

Use explicit types.

---

## Required project structure

Use a clean, maintainable structure such as:

```text
poc-factory/
  app/
    api/
      routes/
      dependencies/
      schemas/
    application/
      services/
      orchestrators/
      prompts/
    domain/
      models/
      services/
      policies/
      value_objects/
    infrastructure/
      claude_code/
      git/
      filesystem/
      subprocess/
      persistence/
      observability/
      llm/
    graph/
      run_graph/
      poc_graph/
      state.py
      nodes/
      edges/
    templates/
      claude_md/
      markdown/
    tests/
      unit/
      integration/
      e2e/
  scripts/
  output/
  docs/
  pyproject.toml
  README.md
  .env.example
  Dockerfile
  docker-compose.yml
```

You may adapt this structure, but keep the separation strong and coherent.

---

## Behavior of the system

## Phase 1: Request ingestion and normalization

When the user submits a phrase:
- normalize spacing/casing
- create a slug
- infer likely sub-domain
- preserve the raw phrase
- validate target count is between 8 and 15
- normalize package names
- deduplicate technologies
- infer defaults if omitted

Example:
- input: `monitoring and observaibility`
- normalized phrase should correct obvious typo to `monitoring and observability`
- slug: `monitoring-and-observability`

Keep both:
- raw input
- normalized interpretation

---

## Phase 2: POC ideation and ranking

Generate candidate POC ideas for the phrase.

Requirements:
- generate more candidates than needed initially, e.g. 14–20
- then rank/select top N
- every POC must be:
  - implementable
  - focused
  - distinct from the others
  - pedagogically useful
  - relevant to the phrase
- avoid duplicate or near-duplicate POCs

Each candidate should include:
- title
- slug
- one-sentence goal
- why it matters
- what it excludes
- packages required
- rank justification

---

## Phase 3: Folder preparation

For each selected POC:
- create folder under:
  - `output/<normalized-phrase>/<NN-poc-slug>/`
- place initial metadata file:
  - `poc-plan.json`
- place generated POC-specific `CLAUDE.md`
- prepare workspace for starter repo copy/clone

---

## Phase 4: Starter repo acquisition

Use the user’s private GitHub starter repo as the base.

Implement one of:
- clone once to cache, then copy into each POC folder
- or archive download then extract
- or local mirror if configured

Prefer:
- clone once per run into a temp/cache directory
- copy the clean starter snapshot into each POC folder

Requirements:
- handle auth via env var / token
- never leak secrets to logs
- make clone deterministic
- support specific branch/tag/commit if provided

If the starter repo includes Git metadata, do not necessarily copy `.git` into each POC unless explicitly configured.

Default behavior:
- exclude `.git`
- copy working tree only

---

## Phase 5: Generating per-POC CLAUDE.md

For each POC, generate a **specific** `CLAUDE.md` file that instructs Claude Code to build that exact POC from the starter.

Each generated `CLAUDE.md` must:
- start from the user's reusable starter template
- embed the specific POC goal
- define exact constraints
- define acceptance criteria
- define required outputs
- define packages to use
- define what not to include
- require updates to `README.md`, `requirements.txt`, `.env.example`, Docker assets where relevant
- require tests
- require type correctness
- require concise implementation
- require a focused repo

Also include explicit guidance like:
- do not build multiple approaches in one repo
- do not overengineer
- mock non-essential side effects
- keep files well organized
- prefer clarity over abstraction
- add comments only where they materially help understanding

---

## Phase 6: Claude Code invocation

Programmatically invoke Claude Code against each POC folder.

Requirements:
- support headless/non-interactive execution
- pass the generated `CLAUDE.md` prompt
- capture stdout/stderr
- persist logs to files
- detect non-zero exit status
- enforce timeout
- allow per-POC retries
- ensure only one POC folder is modified by one build invocation

Design an adapter like:
- `ClaudeCodeRunner`
- `ClaudeCodePromptBuilder`
- `ClaudeCodeExecutionResult`

Persist:
- prompt used
- command executed
- timestamps
- exit code
- output text
- artifacts changed (if inferable)

---

## Phase 7: Validation

After Claude Code builds the POC:
- run type checks if appropriate
- run tests
- run setup/validation scripts if present
- inspect critical files

At minimum detect:
- missing `README.md`
- missing tests
- missing markdown files later in workflow
- failing test suite
- malformed `.env.example`
- broken imports
- syntax errors
- missing package declarations
- obvious mismatch between requested POC scope and generated repo

Create structured validation results.

---

## Phase 8: Repair loop

If build validation fails:
- generate a concise remediation prompt
- invoke Claude Code again only for the repair
- cap repair attempts, e.g. 2
- after repair, rerun validation

Repair prompts must be narrow and precise.
Do not regenerate the entire repo unless necessary.

---

## Phase 9: Markdown generation

For each successful POC, generate two markdown files.

### A) Prose chapter file
Filename:
- `<NN-poc-slug>.md`

Purpose:
- teach the approach as a chapter in an ebook

Structure:
1. title
2. problem it solves
3. when to use it
4. key design decisions
5. architecture walkthrough
6. code structure walkthrough
7. trade-offs
8. limitations
9. how it fits into larger production systems
10. final summary

Style:
- full prose
- clear and thoughtful
- technical but readable
- avoid fluff
- explain the approach in terms of the actual generated POC repo

### B) Code implementation walkthrough
Filename:
- `code-implementation-<NN-poc-slug>.md`

Purpose:
- concise guided build walkthrough

Structure:
- numbered steps
- each step explains what was added or changed
- reference files/folders
- brief reasoning beside each step
- concise prose

Both markdown files must be based on the **actual generated POC**, not generic theory.

---

## Phase 10: README / Docker / env updates

Each POC repo must contain:
- updated `README.md`
- updated `requirements.txt`
- updated `.env.example`
- updated `Dockerfile` when needed
- `docker-compose.yml` when infrastructure requires it and the POC benefits from it

Guidelines:
- only add Docker/database infra if relevant
- if ChromaDB/Postgres is needed, reflect that cleanly
- keep `.env.example` complete but safe
- never commit real secrets

---

## Phase 11: Reporting

For each POC write:
- `build-report.json`

This should include:
- POC metadata
- selected packages
- files created/modified
- validation results
- repair attempts
- artifact list
- completion status
- summary notes

For the whole run write:
- `run-report.json`
- `run-summary.md`

---

## Specific implementation requirements

## A. Public API design
Use FastAPI and expose endpoints with typed request/response schemas.
Return run IDs and status payloads.

Support:
- synchronous submission with async background processing model if needed inside the app
- or explicit worker execution mode

However, keep the code understandable.
Do not add Kafka/Celery/etc unless truly necessary.
A simpler internal job execution model is preferred first.

## B. Persistence
Persist run metadata and statuses.
Start simple.
SQLite is acceptable if implemented cleanly.
Postgres is also acceptable if you want stronger future production alignment.

## C. File operations
Implement safe filesystem utilities:
- atomic writes where practical
- path normalization
- no accidental deletion outside workspace
- temp folder hygiene

## D. Prompt management
Store prompt templates in files, not hardcoded giant strings scattered across the codebase.

At minimum have:
- run-level POC ideation prompt
- POC ranking prompt
- per-POC CLAUDE.md generation prompt
- prose markdown generation prompt
- code walkthrough markdown generation prompt
- repair prompt

## E. Observability
Instrument the workflow.
If Langfuse is enabled, trace:
- run creation
- ideation
- ranking
- per-POC build
- validation
- repair
- markdown generation
- finalization

Also ensure the app still works if Langfuse is disabled.

## F. Configuration
Support config via env vars and a config module.

Possible env vars:
- `APP_ENV`
- `LOG_LEVEL`
- `OUTPUT_ROOT`
- `WORK_ROOT`
- `GITHUB_TOKEN`
- `STARTER_REPO_CACHE_DIR`
- `CLAUDE_CODE_COMMAND`
- `CLAUDE_CODE_TIMEOUT_SECONDS`
- `ENABLE_LANGFUSE`
- `LANGFUSE_PUBLIC_KEY`
- `LANGFUSE_SECRET_KEY`
- `LANGFUSE_HOST`
- `OPENAI_API_KEY` or other LLM provider keys if needed for internal generation
- `DEFAULT_TARGET_POC_COUNT`

Reflect required vars in `.env.example`.

---

## Non-functional requirements

### Reliability
- retry transient failures selectively
- do not lose run state on restart if reasonable persistence/checkpointing is implemented

### Determinism
- naming should be deterministic
- ordering should be deterministic given same inputs, as much as practical

### Extensibility
This platform should later be able to support:
- other code generators
- other starter repos
- other artifact types
- optional human approval
- additional documentation formats

Design with that future in mind.

### Cost-awareness
- minimize unnecessary model calls
- avoid repeated cloning
- reuse cached starter repo snapshot where appropriate

### Security
- do not log secrets
- sanitize user-provided phrase before using it in shell commands or paths
- isolate subprocess execution
- validate repo paths carefully

---

## Strong recommendations for implementation approach

Use a **planner + deterministic worker graph** style.

That means:
- use LLMs where semantic judgment matters
- use deterministic code for file ops, validation, path building, ordering, subprocesses

Do **not** build one giant fully autonomous free-form agent.

Use explicit graph nodes for:
- judgment
- planning
- execution
- validation
- remediation

---

## Suggested graph flow in more detail

```text
ingest_request
  -> normalize_phrase
  -> expand_poc_candidates
  -> rank_and_select_pocs
  -> create_run_plan
  -> fan_out_poc_jobs

For each POC:
  prepare_poc_folder
    -> acquire_starter_repo
    -> generate_poc_claude_md
    -> invoke_claude_code_build
    -> run_static_checks
    -> run_tests
    -> assess_build_result
      -> if failed and repair attempts remain:
           invoke_claude_code_repair
           -> run_static_checks
           -> run_tests
           -> assess_build_result
      -> if passed:
           generate_prose_markdown
           -> generate_code_walkthrough_markdown
           -> update_readme
           -> update_env_example
           -> update_docker_assets
           -> write_build_report
           -> mark_poc_complete

After all POCs:
  aggregate_run_results
    -> finalize_run
```

If LangGraph map/fan-out patterns are helpful, use them.

---

## Required prompts/artifacts to implement

Create reusable templates for:

1. `poc_ideation_prompt.md`
2. `poc_ranking_prompt.md`
3. `poc_claude_md_generation_prompt.md`
4. `prose_markdown_generation_prompt.md`
5. `code_walkthrough_generation_prompt.md`
6. `repair_prompt.md`

Also create a reusable **starter template** for per-POC `CLAUDE.md` generation.

---

## The generated per-POC CLAUDE.md template must include sections like:

- mission
- POC goal
- starter assumptions
- required packages
- implementation boundaries
- acceptance criteria
- required output files
- testing requirements
- repo hygiene requirements
- documentation requirements
- what not to include

---

## Include this exact reusable starter section inside the generated per-POC CLAUDE.md template

Use the following as the foundation for all per-POC generated `CLAUDE.md` files:

```md
## Starter assumptions

This POC starts from an existing FastAPI starter.

The starter already contains:
- a `shared/` folder with config that handles environment variables, including the OpenAI API key
- a `shared/logging/` module that provides the project's logging functionality
- a `scripts/` folder with:
  - a setup script that installs Python dependencies
  - a test script that runs the test suite
  - a run script that starts the app

You may update files in `shared/` and `scripts/` if needed to support the generated POC.

## Global implementation rules

- Use Python.
- Use FastAPI for the API surface.
- Keep the POC lightweight and focused on one concept.
- Mock real side effects such as email sending, SQL execution, browser access, or secret manager calls unless the point of the POC is specifically to demonstrate that dependency.
- Organize the code cleanly.
- Add tests.
- Ensure imports and typing are correct.
- Update `README.md` so the POC is easy to understand and run.
- Update `.env.example` with any new environment variables.
- Update dependency files with any new packages.
- Update Docker assets only if relevant to the POC.
```

---

## Implementation detail expectations

You must produce real code, not a superficial scaffold.

The project must include:

### LangGraph graph code
- typed graph state
- node implementations
- edge routing
- checkpoint/resume strategy if used

### Claude Code adapter
- safe subprocess wrapper
- timeout handling
- result capture
- retry support

### Git/starter repo adapter
- clone/fetch/copy logic
- auth support
- cache support

### Markdown generators
- prompt + generation service
- file writer
- deterministic naming

### Validators
At minimum:
- syntax/import validation
- test execution
- required-file validation
- optional dependency sanity check

### Reporting
- JSON report writers
- summary markdown writer

### Tests
Include:
- unit tests for naming/normalization
- unit tests for ranking/output planning
- unit tests for folder layout
- unit tests for report generation
- integration tests for graph happy path with mocked Claude Code runner
- integration tests for repair flow
- API tests for run creation/status

---

## Output quality bar

The codebase must be:
- coherent
- navigable
- strongly typed where practical
- not overabstracted
- not underdesigned
- suitable as a serious internal project starter

Do not produce a fake implementation that only stubs the difficult parts unless clearly marked.
Where external tools cannot be run in tests, mock them properly behind adapters.

---

## Important design choices to follow

### Use deterministic slugs
Implement slugging carefully:
- lowercase
- hyphen-separated
- remove punctuation
- collapse spaces
- preserve order index with two digits

### Prefer copy-from-cache for starter repo
Do not clone the private repo separately for every POC unless unavoidable.

### Use per-POC work isolation
Each POC should run in its own folder and should not interfere with other POCs.

### Keep prompts versionable
Store prompts as files for later refinement.

### Separate planning from execution
The ideation/ranking stage should not directly perform filesystem or subprocess work.

---

## Guidance for ranking POCs

When ranking POCs for a phrase, prioritize:
- foundational patterns first
- simplest useful implementations first
- concepts most likely to appear in real systems first
- clear progression from basic to more advanced
- minimal overlap

For example, for `monitoring and observability`, more fundamental POCs likely come before advanced/derived ones.

---

## Guidance for markdown generation

The markdown must not read like vague AI filler.
It must map directly to the repo contents.

The prose chapter should:
- explain why the approach exists
- explain design trade-offs
- contextualize the POC in larger systems

The code walkthrough should:
- walk through the actual implementation in concise steps
- mention concrete files/modules
- help a reader reconstruct the architecture

---

## README requirements for each generated POC

Each README should include:
- POC title
- what it demonstrates
- why it matters
- architecture overview
- project structure
- how to run
- how to test
- env vars
- key limitations
- next logical POCs / related patterns

---

## Build-report requirements

Example structure:

```json
{
  "poc_slug": "01-untrusted-data-boundary",
  "status": "completed",
  "packages_used": ["fastapi"],
  "artifacts": [
    {"type": "claude_md", "path": "..."},
    {"type": "repo", "path": "..."},
    {"type": "prose_markdown", "path": "..."},
    {"type": "code_walkthrough_markdown", "path": "..."}
  ],
  "validation": {
    "static_checks_passed": true,
    "tests_passed": true
  },
  "repair_attempts": 1,
  "notes": [
    "Added request boundary validation",
    "Updated .env.example"
  ]
}
```

---

## Run-summary requirements

Produce `run-summary.md` containing:
- original request
- normalized phrase
- selected POCs in order
- completion status per POC
- failures and reasons
- artifact root path
- summary observations

---

## What to avoid

Do not:
- create a single monolithic agent that improvises everything
- bury core logic in one enormous file
- mix subprocess code directly into graph node logic without adapters
- skip structured state
- make every dependency mandatory
- overuse inheritance
- generate bloated POCs
- create overlapping POCs
- write weak placeholder markdown
- expose secrets in logs
- hardcode absolute machine-specific paths

---

## Nice-to-have features if feasible

Implement these if they fit cleanly:

1. **Dry-run mode**
   - generates plans and CLAUDE.md files without invoking Claude Code

2. **Selective phase execution**
   - e.g. generate only plans
   - build only failed POCs
   - regenerate only markdown

3. **Parallelism controls**
   - configurable concurrency for POC builds

4. **Manual review mode**
   - pause after plan generation for approval

5. **Artifact hash manifest**
   - to detect drift/regeneration

6. **Prompt snapshotting**
   - save exact prompts used per artifact

7. **Web UI later-ready API contracts**
   - clean responses that could support a frontend later

---

## Minimum acceptance criteria

The project is complete only if:

1. I can run the app.
2. I can call `POST /runs` with a phrase and technologies.
3. The system creates 8–15 ranked, focused POC folders.
4. Each POC folder starts from the starter repo.
5. Each POC folder gets a generated `CLAUDE.md`.
6. Claude Code is invoked to build each POC.
7. Validation runs for each POC.
8. Failed builds can be repaired with targeted retries.
9. Two markdown files are generated per successful POC.
10. README / requirements / env / docker assets are updated when relevant.
11. A run-level report and per-POC reports are written.
12. The codebase is clean and maintainable.

---

## Deliverables expected from you

You must generate the full project implementation.

At the end, ensure the repository contains at least:
- complete FastAPI app
- complete LangGraph orchestration
- complete domain and adapters
- prompt templates
- tests
- README
- `.env.example`
- Dockerfile
- optional docker-compose
- sample config
- clear setup instructions

---

## Final instruction

Build this as though it will become the user's long-term internal content-generation platform for producing focused, high-quality educational POCs around agentic-system concerns.

Optimize for:
- clarity
- maintainability
- repeatability
- scoped POCs
- strong artifact hygiene
- explicit orchestration

Do not cut corners on the architecture.
Do not overcomplicate the first version either.
Aim for the strongest practical v1.
