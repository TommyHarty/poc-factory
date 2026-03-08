"""Service for generating per-POC CLAUDE.md files."""

from pathlib import Path

from app.application.services.prompt_loader import PromptLoader
from app.domain.models.run import GenerationPreferences, PocPlan
from app.infrastructure.llm.adapter import LLMAdapter
from app.logging_config import get_logger

logger = get_logger(__name__)


class ClaudeMdGenerator:
    """Generates CLAUDE.md files for individual POCs using the LLM."""

    def __init__(self, llm: LLMAdapter, prompt_loader: PromptLoader) -> None:
        self.llm = llm
        self.prompt_loader = prompt_loader

    def generate(
        self,
        poc: PocPlan,
        phrase: str,
        technologies: list[str],
        optional_packages: list[str],
        preferences: GenerationPreferences,
    ) -> str:
        """Generate a CLAUDE.md for the given POC."""
        import json

        all_packages = list(set(poc.required_packages + technologies + optional_packages))

        prompt = self.prompt_loader.render(
            "poc_claude_md_generation_prompt.md",
            {
                "phrase": phrase,
                "technologies": technologies,
                "optional_packages": optional_packages,
                "preferences": json.dumps(preferences.model_dump(), indent=2),
                "poc_index": poc.index,
                "poc_title": poc.title,
                "poc_slug": poc.slug,
                "poc_goal": poc.goal,
                "why_it_matters": poc.why_it_matters,
                "scope_boundaries": poc.scope_boundaries,
                "required_packages": all_packages,
            },
        )

        logger.info("generating_claude_md", poc_slug=poc.slug)

        try:
            content = self.llm.complete(
                prompt,
                system="You are an expert software architect creating precise build instructions for Claude Code.",
                max_tokens=4000,
                temperature=0.2,
            )
            return content
        except Exception as e:
            logger.error("claude_md_generation_error", poc_slug=poc.slug, error=str(e))
            # Fallback: generate a minimal CLAUDE.md
            return self._generate_fallback_claude_md(poc, phrase, technologies, preferences)

    def _generate_fallback_claude_md(
        self,
        poc: PocPlan,
        phrase: str,
        technologies: list[str],
        preferences: GenerationPreferences,
    ) -> str:
        """Generate a minimal CLAUDE.md without LLM."""
        newline = "\n"
        packages_str = newline.join(f"- {p}" for p in poc.required_packages)
        boundaries_str = newline.join(f"- {b}" for b in poc.scope_boundaries)
        default_packages = "- fastapi\n- pydantic"
        packages_section = packages_str if packages_str else default_packages
        default_boundaries = "- See scope boundaries"
        boundaries_section = boundaries_str if boundaries_str else default_boundaries

        return f"""# CLAUDE.md — {poc.title}

## Mission

Build the `{poc.slug}` POC from the starter repo.

## POC Goal

{poc.goal}

## Why It Matters

{poc.why_it_matters}

## Starter assumptions

This POC starts from an existing FastAPI starter repo that already has Docker configured.

The starter already contains:
- `app/` — the FastAPI application package. `app/main.py` is the entry point. Add all new routes, modules, and business logic here.
- `core/` — configuration only. `core/config.py` contains a pydantic-settings `Settings` class that reads from `.env`. Extend it if you need new env vars.
- `tests/` — pytest test suite. Add new test files here.
- `scripts/` — shell scripts: `setup.sh` (installs deps / builds Docker), `run.sh` (starts app), `test.sh` (runs tests), `down.sh` (stops Docker).
- `pyproject.toml` — package config and dependencies. Add new packages to the `[project] dependencies` list here. Do NOT create a `requirements.txt`.
- `Dockerfile` and `docker-compose.yml` — already configured for the app service.

Do NOT create a `src/` directory. All implementation code goes inside `app/`.
Do NOT run `pip install -e .` locally — this creates unwanted `.egg-info` artifacts.
You may update any of the above files as needed to support the POC.

## Required packages

{packages_section}

## Implementation boundaries

This POC implements ONLY:
- The core concept: {poc.goal}

This POC does NOT include:
{boundaries_section}

## Acceptance criteria

- [ ] The POC implements the stated goal
- [ ] All tests pass
- [ ] README.md is updated with clear instructions
- [ ] `.env.example` is complete
- [ ] The implementation is focused and does not implement other concerns

## Required output files

- `app/api/routes.py` — APIRouter with all endpoint handlers
- `app/models/schemas.py` — Pydantic request/response models
- `app/services/<concept>.py` — core business logic
- `app/main.py` — thin wiring only (import router, register routes)
- `tests/test_<concept>.py` — unit tests for business logic
- `tests/test_api.py` — API-level tests
- `README.md` — updated with POC documentation
- `pyproject.toml` — updated with any new packages
- `.env.example` — updated with any new env vars

## Testing requirements

- Write pytest tests that verify the core behavior
- Tests must be in `tests/`
- All tests must pass

## Repo hygiene requirements

- Clean, well-organized file structure
- No unused imports
- Type annotations on public functions

## Documentation requirements

- README.md must describe what this POC demonstrates
- README.md must include setup and run instructions

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

`app/main.py` must only import and include the router and register middleware.
All domain logic belongs in `app/services/`. All schemas belong in `app/models/schemas.py`.
All route handlers belong in `app/api/routes.py` using `APIRouter`.

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
"""

    @staticmethod
    def generate_fallback(
        poc: PocPlan,
        phrase: str,
        technologies: list[str],
        preferences: GenerationPreferences,
        prompt_loader: PromptLoader,
    ) -> str:
        """Generate a minimal CLAUDE.md without an LLM instance."""
        instance = ClaudeMdGenerator.__new__(ClaudeMdGenerator)
        instance.prompt_loader = prompt_loader
        return instance._generate_fallback_claude_md(poc, phrase, technologies, preferences)

    def write_to_folder(self, content: str, poc_folder: Path) -> Path:
        """Write the CLAUDE.md to the POC folder."""
        claude_md_path = poc_folder / "CLAUDE.md"
        claude_md_path.write_text(content, encoding="utf-8")
        logger.info("wrote_claude_md", path=str(claude_md_path))
        return claude_md_path
