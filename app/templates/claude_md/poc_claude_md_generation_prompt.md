# POC CLAUDE.md Generation Prompt

You are generating a CLAUDE.md file that will be used to instruct Claude Code to build a specific POC.

## Run Context
- Topic: {phrase}
- All Technologies: {technologies}
- Preferences: {preferences}

## This POC
- Index: {poc_index}
- Title: {poc_title}
- Slug: {poc_slug}
- Goal: {poc_goal}
- Why It Matters: {why_it_matters}
- Scope Boundaries: {scope_boundaries}
- Required Packages: {required_packages}

## Instructions

Generate a complete CLAUDE.md file for this POC. The CLAUDE.md must instruct Claude Code to build exactly this POC from the starter repo — with a clean, intelligent implementation that properly demonstrates the concept.

The file must include these sections:
1. Mission header
2. POC Goal
3. Starter Assumptions (use the standard section below EXACTLY)
4. Required Packages
5. Implementation Approach (specific guidance for THIS concept)
6. Required File Structure
7. Implementation Boundaries (what to include AND what NOT to include)
8. Acceptance Criteria (specific, testable criteria)
9. Testing Requirements
10. Repo Hygiene Requirements
11. Documentation Requirements — README must be self-contained. Do NOT reference other POCs, other patterns, or "related approaches" sections. Do not mention any other numbered POC.
12. Global Implementation Rules (use the standard section below EXACTLY)

## Standard Starter Assumptions Section

Use this EXACTLY:

```
## Starter assumptions

This POC starts from an existing FastAPI starter repo that already has Docker configured.

The starter already contains:
- `app/` — the FastAPI application package. `app/main.py` is the entry point.
- `core/` — configuration only. `core/config.py` contains a pydantic-settings `Settings` class that reads from `.env`. It already has `openai_api_key: SecretStr | None`.
- `tests/` — pytest test suite.
- `scripts/` — shell scripts: `setup.sh`, `run.sh`, `test.sh`, `down.sh`.
- `pyproject.toml` — package config and dependencies. Add new packages here. Do NOT create a `requirements.txt`.
- `Dockerfile` and `docker-compose.yml` — already configured.

Do NOT create a `src/` directory. All implementation code goes inside `app/`.
Do NOT run `pip install -e .` locally — this creates unwanted `.egg-info` artifacts.
```

## Standard Required File Structure Section

Use this EXACTLY, tailored to the POC concept:

```
## Required file structure

Do NOT pile routes or business logic into `app/main.py`. Use clean separation of concerns:

app/
  main.py              ← thin: only imports router, configures middleware, registers routes
  api/
    routes.py          ← APIRouter with all endpoint handlers
  models/
    schemas.py         ← Pydantic request/response models
  services/
    <concept>.py       ← core business logic for this POC
    openai_service.py  ← OpenAI API calls (if the POC uses the model)
tests/
  test_<concept>.py    ← unit tests for business logic
  test_api.py          ← API-level tests using httpx AsyncClient

`app/main.py` must only:
- Import and include the router from `app/api/routes.py`
- Register middleware if needed
- Expose the `/health` endpoint

All domain logic belongs in `app/services/`. All schemas belong in `app/models/schemas.py`.
All route handlers belong in `app/api/routes.py` using `APIRouter`.
```

## Implementation Approach Guidance

When writing the Implementation Approach section for this POC, be specific about:

1. **What the core logic actually does** — describe the algorithm, data flow, or decision tree concisely
2. **What modules to create** — name them specifically (e.g. `app/services/validator.py`, `app/services/prompt_builder.py`)
3. **What the API surface looks like** — name the endpoints, their inputs, and their outputs
4. **How OpenAI is used** — every POC must make real OpenAI API calls. Describe the prompt structure, the model role, and what the model should return. The API key comes from `core/config.py` via `settings.openai_api_key.get_secret_value()`. All model calls go in `app/services/openai_service.py`.
5. **What the tests must prove** — describe the specific behaviors that must be verified. Tests mock the OpenAI client, not the business logic.

Make the implementation approach intelligent and specific to THIS concept. Do not give generic instructions. A developer reading the CLAUDE.md should understand exactly what to build before writing a single line of code.

## Standard Global Implementation Rules

Use this EXACTLY:

```
## Global implementation rules

- Use Python.
- Use FastAPI for the API surface. All routes go in `app/api/routes.py` via `APIRouter`. `app/main.py` only wires things together.
- Keep the POC lightweight and focused on one concept.
- **Use the real OpenAI API for all LLM calls.** Do NOT simulate or stub model responses. The starter repo's `core/config.py` already exposes `settings.openai_api_key` (a `SecretStr`). Access it with `settings.openai_api_key.get_secret_value()`. Isolate all OpenAI calls in `app/services/openai_service.py`.
- Mock only infrastructure side effects that are genuinely external and irrelevant to the concept being demonstrated (e.g. email sending, browser automation, secret manager calls). Do NOT mock OpenAI.
- Organize the code cleanly into `app/models/`, `app/services/`, `app/api/`.
- Add tests in `tests/`. Use `httpx.AsyncClient` with `ASGITransport` for API tests. Mock the OpenAI client in tests using `unittest.mock.patch` or `pytest-mock` so tests do not make real API calls.
- Ensure imports and typing are correct. Use `from __future__ import annotations`.
- Update `README.md` so the POC is easy to understand and run.
- Update `.env.example` with any new environment variables. `OPENAI_API_KEY` is already present.
- Add new packages to `pyproject.toml` under `[project] dependencies`. Do NOT create or modify a `requirements.txt`.

## Docker requirements

The starter repo already has a `Dockerfile` and `docker-compose.yml`. You must work with these existing files, not replace them.

- Always update `docker-compose.yml` to add any infrastructure services the POC needs.
- If the POC requires a service such as ChromaDB, Postgres, Redis, Qdrant, or any other external dependency, add it as a named service in `docker-compose.yml` with the correct image, ports, volumes, and environment variables.
- Add a `depends_on` entry to the app service for any infrastructure services you add.
- Expose the correct ports and set the correct environment variables in `.env.example` so the POC connects to those services.
- Do not remove or replace the existing app service definition — only extend it.
- If no infrastructure services are needed, leave `docker-compose.yml` unchanged.
```

## Output

Output the complete CLAUDE.md file content (not wrapped in code fences, just the raw markdown).
