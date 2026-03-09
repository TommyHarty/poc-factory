"""Per-POC graph nodes for the POC Factory orchestration."""

from datetime import datetime, timezone
from pathlib import Path

from app.domain.models.run import (
    ArtifactMetadata,
    ArtifactType,
    BuildStatus,
    ValidationStatus,
)
from app.graph.state import PocGraphState
from app.logging_config import get_logger

logger = get_logger(__name__)


def _poc_folder(state: PocGraphState) -> Path:
    """Return the POC folder path, asserting it has been set."""
    assert state.folder_path is not None, f"folder_path not set for POC {state.poc_slug}"
    return Path(state.folder_path)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _cleanup_poc_folder(poc_folder: Path) -> None:
    """Remove artifacts that Claude Code should not have created inside the POC folder."""
    import shutil

    # Directories to always remove from the POC output
    unwanted_dirs = [
        "src",               # Claude Code sometimes creates an empty src/ despite instructions
        ".venv",             # Created if Claude Code ran setup.sh or pip install
        "logs",              # Moved to work/logs/ — remove if Claude Code created one here
        ".pytest_cache",     # Test runner cache — not part of deliverable
        ".mypy_cache",
    ]
    # Any directory matching *.egg-info pattern
    for item in list(poc_folder.iterdir()):
        if item.is_dir():
            if item.name in unwanted_dirs:
                shutil.rmtree(item, ignore_errors=True)
                logger.info("cleaned_unwanted_dir", path=str(item))
            elif item.name.endswith(".egg-info"):
                shutil.rmtree(item, ignore_errors=True)
                logger.info("cleaned_egg_info", path=str(item))


def prepare_poc_folder(state: PocGraphState) -> PocGraphState:
    """Create the POC folder and write initial poc-plan.json."""
    import json

    logger.info("prepare_poc_folder", poc_slug=state.poc_slug)

    run_output_path = Path(state.output_root) / state.slug
    poc_folder = run_output_path / state.poc_slug
    poc_folder.mkdir(parents=True, exist_ok=True)

    state.folder_path = str(poc_folder)
    state.started_at = _now()

    # Write initial plan metadata
    plan_data = {
        "poc_index": state.poc_index,
        "poc_title": state.poc_title,
        "poc_slug": state.poc_slug,
        "poc_goal": state.poc_goal,
        "why_it_matters": state.why_it_matters,
        "scope_boundaries": state.scope_boundaries,
        "required_packages": state.required_packages,
        "run_id": state.run_id,
        "created_at": state.started_at.isoformat(),
    }
    plan_file = poc_folder / "poc-plan.json"
    plan_file.write_text(json.dumps(plan_data, indent=2))

    logger.info("poc_folder_prepared", path=str(poc_folder))
    return state


def acquire_starter_repo(state: PocGraphState) -> PocGraphState:
    """Copy or clone the starter repo into the POC folder."""
    from app.config import get_settings
    from app.infrastructure.git.adapter import GitAdapter

    settings = get_settings()
    logger.info("acquire_starter_repo", poc_slug=state.poc_slug)

    poc_folder = _poc_folder(state)
    assert state.starter_repo is not None, "starter_repo must be configured before acquiring"

    adapter = GitAdapter(
        cache_dir=settings.starter_repo_cache_dir or settings.work_root / "starter-cache",
        github_token=settings.github_token,
    )

    # If we have a cached local path from a prior run-level clone, copy from it directly
    if state.starter_repo_local_path:
        from app.infrastructure.filesystem.adapter import FileSystemAdapter
        cached = Path(state.starter_repo_local_path)
        fs = FileSystemAdapter(settings.work_root, Path(state.output_root))
        try:
            fs.copy_directory(cached, poc_folder, ignore_git=True)
            logger.info("copied_from_cached_starter", poc_slug=state.poc_slug)
            return state
        except Exception as e:
            logger.warning("copy_from_cache_failed_falling_back_to_clone", error=str(e))

    adapter.copy_starter_to_poc_folder(state.starter_repo, poc_folder)
    logger.info("starter_repo_acquired", poc_slug=state.poc_slug)

    return state


def generate_poc_claude_md(state: PocGraphState) -> PocGraphState:
    """Generate the CLAUDE.md instruction file for this POC."""
    from app.application.services.claude_md_generator import ClaudeMdGenerator
    from app.application.services.prompt_loader import PromptLoader
    from app.config import get_settings
    from app.infrastructure.llm.adapter import LLMError, create_llm_adapter

    settings = get_settings()
    logger.info("generate_poc_claude_md", poc_slug=state.poc_slug)

    poc_folder = _poc_folder(state)

    from app.domain.models.run import PocPlan

    poc = PocPlan(
        index=state.poc_index,
        title=state.poc_title,
        slug=state.poc_slug,
        goal=state.poc_goal,
        why_it_matters=state.why_it_matters,
        scope_boundaries=state.scope_boundaries,
        required_packages=state.required_packages,
    )

    prompt_loader = PromptLoader()
    try:
        llm = create_llm_adapter(settings)
        generator = ClaudeMdGenerator(llm=llm, prompt_loader=prompt_loader)
        content = generator.generate(
            poc=poc,
            phrase=state.phrase,
            technologies=state.technologies,
            optional_packages=state.optional_packages,
            preferences=state.preferences,
        )
    except LLMError:
        content = ClaudeMdGenerator.generate_fallback(
            poc=poc,
            phrase=state.phrase,
            technologies=state.technologies,
            preferences=state.preferences,
            prompt_loader=prompt_loader,
        )

    claude_md_path = poc_folder / "CLAUDE.md"
    claude_md_path.write_text(content, encoding="utf-8")
    state.claude_md_path = str(claude_md_path)

    # Record artifact
    state.artifacts.append(
        {
            "type": ArtifactType.CLAUDE_MD,
            "path": str(claude_md_path),
            "created_at": _now().isoformat(),
        }
    )

    logger.info("claude_md_generated", path=str(claude_md_path))
    return state


def invoke_claude_code_build(state: PocGraphState) -> PocGraphState:
    """Invoke Claude Code to build the POC from the CLAUDE.md."""
    from app.config import get_settings
    from app.infrastructure.claude_code.runner import ClaudeCodeRunner

    settings = get_settings()
    logger.info("invoke_claude_code_build", poc_slug=state.poc_slug)

    poc_folder = _poc_folder(state)
    state.build_status = BuildStatus.IN_PROGRESS

    if state.dry_run:
        logger.info("dry_run_skipping_claude_code", poc_slug=state.poc_slug)
        state.build_status = BuildStatus.SUCCEEDED
        state.notes.append("Dry run: Claude Code invocation skipped")
        return state

    # Read the CLAUDE.md as the prompt
    claude_md_path = Path(state.claude_md_path) if state.claude_md_path else poc_folder / "CLAUDE.md"
    if not claude_md_path.exists():
        state.build_status = BuildStatus.FAILED
        state.error_message = "CLAUDE.md not found"
        return state

    prompt = claude_md_path.read_text(encoding="utf-8")

    runner = ClaudeCodeRunner(
        command=settings.claude_code_command,
        timeout_seconds=settings.claude_code_timeout_seconds,
    )

    import asyncio
    try:
        result = asyncio.get_event_loop().run_until_complete(
            runner.run(poc_folder=poc_folder, prompt=prompt, prompt_file=claude_md_path)
        )
    except RuntimeError:
        # No event loop - run synchronously
        result = runner.run_sync(poc_folder=poc_folder, prompt=prompt, prompt_file=claude_md_path)

    state.build_stdout = result.stdout
    state.build_stderr = result.stderr
    state.build_exit_code = result.exit_code

    if result.succeeded:
        state.build_status = BuildStatus.SUCCEEDED
        state.notes.append("Claude Code build succeeded")
    else:
        state.build_status = BuildStatus.FAILED
        state.error_message = f"Claude Code exited with code {result.exit_code}"
        if result.timed_out:
            state.error_message = "Claude Code timed out"
        state.notes.append(f"Claude Code build failed: exit_code={result.exit_code}")

    _cleanup_poc_folder(poc_folder)
    logger.info(
        "claude_code_build_complete",
        poc_slug=state.poc_slug,
        status=state.build_status,
        exit_code=result.exit_code,
    )
    return state


def run_static_checks(state: PocGraphState) -> PocGraphState:
    """Run static checks (syntax, imports) on the generated POC."""
    from app.application.services.validator import PocValidator
    from app.infrastructure.subprocess.runner import SubprocessRunner

    logger.info("run_static_checks", poc_slug=state.poc_slug)

    poc_folder = _poc_folder(state)
    validator = PocValidator(SubprocessRunner())

    # Run only file + syntax checks (not tests)
    file_result = validator._check_required_files(poc_folder)
    syntax_result = validator._check_python_syntax(poc_folder)

    state.static_check_results = [
        {
            "tool": file_result.tool,
            "success": file_result.success,
            "stdout": file_result.stdout,
            "stderr": file_result.stderr,
            "exit_code": file_result.exit_code,
            "notes": file_result.notes,
        },
        {
            "tool": syntax_result.tool,
            "success": syntax_result.success,
            "stdout": syntax_result.stdout,
            "stderr": syntax_result.stderr,
            "exit_code": syntax_result.exit_code,
            "notes": syntax_result.notes,
        },
    ]

    all_passed = file_result.success and syntax_result.success
    logger.info("static_checks_complete", poc_slug=state.poc_slug, passed=all_passed)
    return state


def run_tests(state: PocGraphState) -> PocGraphState:
    """Run the test suite for the POC."""
    from app.application.services.validator import PocValidator
    from app.infrastructure.subprocess.runner import SubprocessRunner

    logger.info("run_tests", poc_slug=state.poc_slug)

    poc_folder = _poc_folder(state)
    validator = PocValidator(SubprocessRunner())

    test_result = validator._run_tests(poc_folder)

    state.test_results = [
        {
            "tool": test_result.tool,
            "success": test_result.success,
            "stdout": test_result.stdout,
            "stderr": test_result.stderr,
            "exit_code": test_result.exit_code,
        }
    ]

    logger.info(
        "tests_complete",
        poc_slug=state.poc_slug,
        passed=test_result.success,
    )
    return state


def assess_build_result(state: PocGraphState) -> PocGraphState:
    """Assess whether the build passed validation."""
    logger.info("assess_build_result", poc_slug=state.poc_slug)

    static_passed = all(r.get("success", False) for r in state.static_check_results)
    tests_passed = all(r.get("success", False) for r in state.test_results)

    if static_passed and tests_passed:
        state.validation_status = ValidationStatus.PASSED
        logger.info("build_assessment_passed", poc_slug=state.poc_slug)
    elif static_passed or tests_passed:
        state.validation_status = ValidationStatus.PARTIAL
        logger.info("build_assessment_partial", poc_slug=state.poc_slug)
    else:
        state.validation_status = ValidationStatus.FAILED
        logger.info("build_assessment_failed", poc_slug=state.poc_slug)

    return state


def invoke_claude_code_repair(state: PocGraphState) -> PocGraphState:
    """Invoke Claude Code to repair a failed build."""
    from app.config import get_settings
    from app.infrastructure.claude_code.runner import ClaudeCodePromptBuilder, ClaudeCodeRunner

    settings = get_settings()
    logger.info(
        "invoke_claude_code_repair",
        poc_slug=state.poc_slug,
        attempt=state.repair_attempts + 1,
    )

    poc_folder = _poc_folder(state)

    if state.dry_run:
        logger.info("dry_run_skipping_repair", poc_slug=state.poc_slug)
        state.repair_attempts += 1
        return state

    # Collect errors from previous validation
    validation_errors = []
    static_errors = []
    test_errors = []

    for result in state.static_check_results:
        if not result.get("success"):
            if result.get("notes"):
                if result["tool"] == "required_files":
                    validation_errors.extend(result["notes"])
                else:
                    static_errors.extend(result["notes"])
            elif result.get("stderr"):
                static_errors.append(result["stderr"][:300])

    for result in state.test_results:
        if not result.get("success"):
            if result.get("stdout"):
                lines = result["stdout"].split("\n")
                test_errors.extend(
                    l for l in lines if "FAILED" in l or "ERROR" in l or "error" in l.lower()
                )
    test_errors = test_errors[:20]

    repair_prompt = ClaudeCodePromptBuilder.build_repair_prompt(
        poc_slug=state.poc_slug,
        validation_errors=validation_errors,
        static_check_errors=static_errors,
        test_errors=test_errors,
    )

    runner = ClaudeCodeRunner(
        command=settings.claude_code_command,
        timeout_seconds=settings.claude_code_timeout_seconds,
    )

    import asyncio
    try:
        result = asyncio.get_event_loop().run_until_complete(
            runner.run(poc_folder=poc_folder, prompt=repair_prompt)
        )
    except RuntimeError:
        result = runner.run_sync(poc_folder=poc_folder, prompt=repair_prompt)

    state.repair_attempts += 1

    if result.succeeded:
        state.notes.append(f"Repair attempt {state.repair_attempts} succeeded")
        state.build_status = BuildStatus.SUCCEEDED
    else:
        state.notes.append(f"Repair attempt {state.repair_attempts} failed: exit_code={result.exit_code}")

    _cleanup_poc_folder(poc_folder)
    logger.info(
        "repair_attempt_complete",
        poc_slug=state.poc_slug,
        attempt=state.repair_attempts,
        succeeded=result.succeeded,
    )
    return state


def generate_prose_markdown(state: PocGraphState) -> PocGraphState:
    """Generate the prose teaching chapter for this POC."""
    from app.application.services.markdown_generator import MarkdownGenerator
    from app.application.services.prompt_loader import PromptLoader
    from app.config import get_settings
    from app.domain.models.run import PocPlan
    from app.infrastructure.llm.adapter import LLMError, create_llm_adapter

    settings = get_settings()
    logger.info("generate_prose_markdown", poc_slug=state.poc_slug)

    poc_folder = _poc_folder(state)

    poc = PocPlan(
        index=state.poc_index,
        title=state.poc_title,
        slug=state.poc_slug,
        goal=state.poc_goal,
        why_it_matters=state.why_it_matters,
        scope_boundaries=state.scope_boundaries,
        required_packages=state.required_packages,
    )

    try:
        llm = create_llm_adapter(settings)
        prompt_loader = PromptLoader()
        generator = MarkdownGenerator(llm=llm, prompt_loader=prompt_loader)
        content = generator.generate_prose_chapter(poc, state.phrase, poc_folder)
    except (LLMError, Exception) as e:
        logger.error("prose_markdown_error", error=str(e))
        content = f"# {poc.title}\n\n{poc.goal}\n\n{poc.why_it_matters}\n"

    docs_dir = poc_folder / "_docs"
    docs_dir.mkdir(exist_ok=True)
    prose_path = docs_dir / f"{state.poc_slug}.md"
    prose_path.write_text(content, encoding="utf-8")

    state.artifacts.append(
        {
            "type": ArtifactType.PROSE_MARKDOWN,
            "path": str(prose_path),
            "created_at": _now().isoformat(),
        }
    )

    state.markdown_status = BuildStatus.IN_PROGRESS
    logger.info("prose_markdown_generated", path=str(prose_path))
    return state


def generate_code_walkthrough_markdown(state: PocGraphState) -> PocGraphState:
    """Generate the code walkthrough markdown for this POC."""
    from app.application.services.markdown_generator import MarkdownGenerator
    from app.application.services.prompt_loader import PromptLoader
    from app.config import get_settings
    from app.domain.models.run import PocPlan
    from app.infrastructure.llm.adapter import LLMError, create_llm_adapter

    settings = get_settings()
    logger.info("generate_code_walkthrough_markdown", poc_slug=state.poc_slug)

    poc_folder = _poc_folder(state)

    poc = PocPlan(
        index=state.poc_index,
        title=state.poc_title,
        slug=state.poc_slug,
        goal=state.poc_goal,
        why_it_matters=state.why_it_matters,
        scope_boundaries=state.scope_boundaries,
        required_packages=state.required_packages,
    )

    try:
        llm = create_llm_adapter(settings)
        prompt_loader = PromptLoader()
        generator = MarkdownGenerator(llm=llm, prompt_loader=prompt_loader)
        content = generator.generate_code_walkthrough(poc, state.phrase, poc_folder)
    except (LLMError, Exception) as e:
        logger.error("walkthrough_markdown_error", error=str(e))
        content = f"# Code Implementation: {poc.title}\n\nSee the source code for implementation details.\n"

    docs_dir = poc_folder / "_docs"
    docs_dir.mkdir(exist_ok=True)
    walkthrough_path = docs_dir / f"code-implementation-{state.poc_slug}.md"
    walkthrough_path.write_text(content, encoding="utf-8")

    state.artifacts.append(
        {
            "type": ArtifactType.CODE_WALKTHROUGH_MARKDOWN,
            "path": str(walkthrough_path),
            "created_at": _now().isoformat(),
        }
    )

    state.markdown_status = BuildStatus.SUCCEEDED
    logger.info("walkthrough_markdown_generated", path=str(walkthrough_path))
    return state


def update_readme(state: PocGraphState) -> PocGraphState:
    """Ensure the README.md is present and meaningful."""
    logger.info("update_readme", poc_slug=state.poc_slug)

    poc_folder = _poc_folder(state)
    readme_path = poc_folder / "README.md"

    if not readme_path.exists() or readme_path.stat().st_size < 100:
        # Write a basic README
        content = f"""# {state.poc_title}

## What it demonstrates

{state.poc_goal}

## Why it matters

{state.why_it_matters}

## How to run

```bash
bash scripts/setup.sh
bash scripts/run.sh
```

## How to test

```bash
bash scripts/test.sh
```

## Key files

- `src/` - Main implementation
- `tests/` - Test suite
- `CLAUDE.md` - Build instructions

## Environment variables

See `.env.example` for required environment variables.

## Scope

This POC implements: {state.poc_goal}

Intentionally excluded:
{chr(10).join(f"- {b}" for b in state.scope_boundaries) or "- See CLAUDE.md for boundaries"}
"""
        readme_path.write_text(content, encoding="utf-8")
        state.notes.append("README.md created (was missing or too small)")

    state.readme_status = BuildStatus.SUCCEEDED
    logger.info("readme_updated", path=str(readme_path))
    return state


def update_env_example(state: PocGraphState) -> PocGraphState:
    """Ensure .env.example is present."""
    logger.info("update_env_example", poc_slug=state.poc_slug)

    poc_folder = _poc_folder(state)
    env_path = poc_folder / ".env.example"

    if not env_path.exists():
        content = "# Environment variables for this POC\n# Copy to .env and fill in values\n\n"
        env_path.write_text(content, encoding="utf-8")
        state.notes.append(".env.example created (was missing)")

    state.env_example_status = BuildStatus.SUCCEEDED
    return state


def update_docker_assets(state: PocGraphState) -> PocGraphState:
    """Update Docker assets if configured."""
    logger.info("update_docker_assets", poc_slug=state.poc_slug)

    if not state.preferences.use_docker:
        state.docker_status = BuildStatus.SKIPPED
        return state

    poc_folder = _poc_folder(state)
    dockerfile_path = poc_folder / "Dockerfile"

    if not dockerfile_path.exists():
        content = """FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
"""
        dockerfile_path.write_text(content, encoding="utf-8")
        state.notes.append("Dockerfile created")

    state.docker_status = BuildStatus.SUCCEEDED
    return state


def write_build_report(state: PocGraphState) -> PocGraphState:
    """Write the build-report.json for this POC."""
    import json

    logger.info("write_build_report", poc_slug=state.poc_slug)

    poc_folder = _poc_folder(state)

    report = {
        "poc_slug": state.poc_slug,
        "poc_title": state.poc_title,
        "poc_goal": state.poc_goal,
        "status": state.build_status,
        "packages_used": state.required_packages,
        "artifacts": state.artifacts,
        "validation": {
            "static_checks_passed": all(r.get("success", False) for r in state.static_check_results),
            "tests_passed": all(r.get("success", False) for r in state.test_results),
        },
        "repair_attempts": state.repair_attempts,
        "error_message": state.error_message,
        "notes": state.notes,
        "started_at": state.started_at.isoformat() if state.started_at else None,
        "completed_at": _now().isoformat(),
    }

    report_path = poc_folder / "build-report.json"
    report_path.write_text(json.dumps(report, indent=2, default=str))

    state.artifacts.append(
        {
            "type": ArtifactType.BUILD_REPORT,
            "path": str(report_path),
            "created_at": _now().isoformat(),
        }
    )

    logger.info("build_report_written", path=str(report_path))
    return state


def mark_poc_complete(state: PocGraphState) -> PocGraphState:
    """Mark the POC as complete."""
    logger.info("mark_poc_complete", poc_slug=state.poc_slug)

    state.completed_at = _now()

    if state.build_status not in (BuildStatus.FAILED,):
        state.build_status = BuildStatus.SUCCEEDED

    logger.info(
        "poc_marked_complete",
        poc_slug=state.poc_slug,
        status=state.build_status,
        repair_attempts=state.repair_attempts,
    )
    return state
