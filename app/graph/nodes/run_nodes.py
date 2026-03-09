"""Run-level graph nodes for the POC Factory orchestration."""

from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from app.domain.models.run import PocPlan, RunStatus
from app.domain.value_objects.slug import (
    deduplicate_packages,
    normalize_phrase,
    phrase_to_slug,
)
from app.graph.state import RunGraphState
from app.logging_config import get_logger

logger = get_logger(__name__)


def ingest_request(state: RunGraphState) -> RunGraphState:
    """Validate and store the incoming request."""
    logger.info("ingest_request", run_id=state.run_id, phrase=state.phrase)

    now = datetime.now(timezone.utc)
    state.started_at = now
    state.updated_at = now
    state.run_status = RunStatus.RUNNING

    # Validate target count
    from app.domain.policies.generation_policy import DEFAULT_POLICY
    state.target_poc_count = DEFAULT_POLICY.validate_poc_count(state.target_poc_count)

    # Deduplicate packages
    state.technologies = deduplicate_packages(state.technologies)
    state.optional_packages = deduplicate_packages(state.optional_packages)

    # Ensure output root exists
    output_root = Path(state.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    logger.info(
        "request_ingested",
        run_id=state.run_id,
        technologies=state.technologies,
        target_poc_count=state.target_poc_count,
    )
    return state


def normalize_phrase_node(state: RunGraphState) -> RunGraphState:
    """Normalize the input phrase and create a slug."""
    logger.info("normalize_phrase", raw_phrase=state.phrase)

    normalized = normalize_phrase(state.phrase)
    slug = phrase_to_slug(normalized)

    state.normalized_phrase = normalized
    state.slug = slug
    state.run_output_path = str(Path(state.output_root) / slug)
    state.updated_at = datetime.now(timezone.utc)

    # Create run output directory
    Path(state.run_output_path).mkdir(parents=True, exist_ok=True)

    logger.info(
        "phrase_normalized",
        normalized=normalized,
        slug=slug,
        output_path=state.run_output_path,
    )
    return state


def expand_poc_candidates(state: RunGraphState) -> RunGraphState:
    """Expand the phrase into POC candidate ideas using the LLM."""
    from app.application.services.poc_ideation import PocIdeationService
    from app.application.services.prompt_loader import PromptLoader
    from app.config import get_settings
    from app.infrastructure.llm.adapter import LLMError, create_llm_adapter

    settings = get_settings()
    logger.info("expand_poc_candidates", phrase=state.normalized_phrase)

    try:
        llm = create_llm_adapter(settings)
    except LLMError:
        logger.warning("no_llm_key_using_mock_candidates")
        state.candidate_pocs = _generate_mock_candidates(state)
        state.updated_at = datetime.now(timezone.utc)
        return state
    prompt_loader = PromptLoader()
    service = PocIdeationService(llm=llm, prompt_loader=prompt_loader)

    from app.domain.policies.generation_policy import DEFAULT_POLICY
    candidate_count = DEFAULT_POLICY.ideation_candidate_count

    try:
        candidates = service.generate_candidates(
            phrase=state.normalized_phrase,
            technologies=state.technologies,
            optional_packages=state.optional_packages,
            preferences=state.preferences.model_dump(),
            candidate_count=candidate_count,
        )
        state.candidate_pocs = candidates
        logger.info("candidates_generated", count=len(candidates))
    except Exception as e:
        logger.error("candidate_generation_failed", error=str(e))
        state.errors.append(f"Candidate generation failed: {e}")
        state.candidate_pocs = _generate_mock_candidates(state)

    state.updated_at = datetime.now(timezone.utc)
    return state


def rank_and_select_pocs(state: RunGraphState) -> RunGraphState:
    """Rank candidates and select the top N POCs."""
    from app.application.services.poc_ideation import PocIdeationService
    from app.application.services.prompt_loader import PromptLoader
    from app.config import get_settings
    from app.domain.services.poc_ranking import select_top_pocs
    from app.infrastructure.llm.adapter import LLMError, create_llm_adapter

    settings = get_settings()
    logger.info("rank_and_select_pocs", candidate_count=len(state.candidate_pocs))

    if not state.candidate_pocs:
        state.errors.append("No candidate POCs to rank")
        state.run_status = RunStatus.FAILED
        return state

    try:
        llm = create_llm_adapter(settings)
    except LLMError:
        # No LLM available — just take the top N without ranking
        state.selected_pocs = select_top_pocs(state.candidate_pocs, state.target_poc_count)
        state.updated_at = datetime.now(timezone.utc)
        return state
    prompt_loader = PromptLoader()
    service = PocIdeationService(llm=llm, prompt_loader=prompt_loader)

    try:
        selected = service.rank_and_select(
            phrase=state.normalized_phrase,
            technologies=state.technologies,
            candidates=state.candidate_pocs,
            target_count=state.target_poc_count,
        )
        state.selected_pocs = selected
        logger.info("pocs_selected", count=len(selected))
    except Exception as e:
        logger.error("ranking_failed", error=str(e))
        state.errors.append(f"Ranking failed: {e}")
        state.selected_pocs = select_top_pocs(state.candidate_pocs, state.target_poc_count)

    state.updated_at = datetime.now(timezone.utc)
    return state


def create_run_plan(state: RunGraphState) -> RunGraphState:
    """Create the execution plan for the run."""
    logger.info("create_run_plan", selected_count=len(state.selected_pocs))

    if not state.selected_pocs:
        state.errors.append("No POCs selected - cannot create run plan")
        state.run_status = RunStatus.FAILED
        return state

    # Write the run plan to disk
    run_output_path = Path(state.run_output_path)
    plan_data = {
        "run_id": state.run_id,
        "phrase": state.phrase,
        "normalized_phrase": state.normalized_phrase,
        "slug": state.slug,
        "technologies": state.technologies,
        "optional_packages": state.optional_packages,
        "target_poc_count": state.target_poc_count,
        "selected_pocs": [p.model_dump() for p in state.selected_pocs],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    import json
    plan_file = run_output_path / "run-plan.json"
    plan_file.write_text(json.dumps(plan_data, indent=2, default=str))

    logger.info("run_plan_created", poc_count=len(state.selected_pocs))
    state.updated_at = datetime.now(timezone.utc)
    return state


def aggregate_run_results(state: RunGraphState) -> RunGraphState:
    """Aggregate results from all POC executions."""
    logger.info("aggregate_run_results", poc_execution_count=len(state.poc_executions))

    completed = [p for p in state.poc_executions if p.build_status == "succeeded"]
    failed = [p for p in state.poc_executions if p.build_status == "failed"]

    logger.info(
        "aggregation_complete",
        total=len(state.poc_executions),
        completed=len(completed),
        failed=len(failed),
    )

    state.updated_at = datetime.now(timezone.utc)
    return state


def finalize_run(state: RunGraphState) -> RunGraphState:
    """Write final reports and mark run as complete."""
    from app.application.services.report_writer import ReportWriter
    from app.domain.models.run import (
        PocExecution,
        Run,
        RunStatus,
    )

    logger.info("finalize_run", run_id=state.run_id)

    # Determine final status
    completed = [p for p in state.poc_executions if p.build_status == "succeeded"]
    failed = [p for p in state.poc_executions if p.build_status == "failed"]

    if len(failed) == 0:
        final_status = RunStatus.COMPLETED
    elif len(completed) == 0:
        final_status = RunStatus.FAILED
    else:
        final_status = RunStatus.PARTIAL

    state.run_status = final_status
    state.completed_at = datetime.now(timezone.utc)
    state.updated_at = datetime.now(timezone.utc)

    # Write reports
    try:
        run_output_path = Path(state.run_output_path)

        # Build a Run domain object for the report writer
        run = Run(
            run_id=UUID(state.run_id),
            phrase=state.phrase,
            normalized_phrase=state.normalized_phrase,
            slug=state.slug,
            technologies=state.technologies,
            optional_packages=state.optional_packages,
            target_poc_count=state.target_poc_count,
            preferences=state.preferences,
            output_root=state.output_root,
            selected_pocs=state.selected_pocs,
            poc_executions=[
                PocExecution(**p) if isinstance(p, dict) else p
                for p in state.poc_executions
            ],
            run_status=final_status,
            errors=state.errors,
            warnings=state.warnings,
            started_at=state.started_at or datetime.now(timezone.utc),
            updated_at=state.updated_at,
            completed_at=state.completed_at,
        )

        writer = ReportWriter()
        writer.write_run_report(run, run_output_path)
        writer.write_run_summary(run, run_output_path)

        # Generate the top-level intro chapter for the whole topic
        try:
            from app.application.services.markdown_generator import MarkdownGenerator
            from app.application.services.prompt_loader import PromptLoader
            from app.config import get_settings
            from app.infrastructure.llm.adapter import create_llm_adapter

            _settings = get_settings()
            llm = create_llm_adapter(_settings)
            generator = MarkdownGenerator(llm=llm, prompt_loader=PromptLoader())
            intro_content = generator.generate_run_intro_chapter(
                phrase=state.phrase,
                normalized_phrase=state.normalized_phrase,
                selected_pocs=state.selected_pocs,
                poc_executions=run.poc_executions,
            )
            intro_slug = state.slug or state.normalized_phrase.replace(" ", "-")
            intro_path = run_output_path / f"{intro_slug}.md"
            intro_path.write_text(intro_content, encoding="utf-8")
            logger.info("run_intro_chapter_written", path=str(intro_path))
        except Exception as e:
            logger.error("run_intro_chapter_error", error=str(e))

        logger.info(
            "run_finalized",
            run_id=state.run_id,
            status=final_status,
            completed=len(completed),
            failed=len(failed),
        )
    except Exception as e:
        logger.error("finalization_error", error=str(e))
        state.errors.append(f"Finalization error: {e}")

    return state


def _generate_mock_candidates(state: RunGraphState) -> list[PocPlan]:
    """Generate simple mock POC candidates without LLM (fallback)."""
    from app.domain.value_objects.slug import poc_slug

    base_candidates = [
        ("Input Validation Layer", "input-validation-layer", "Implement strict input validation at the API boundary"),
        ("Output Schema Enforcement", "output-schema-enforcement", "Enforce structured output schemas from LLM responses"),
        ("Context Window Management", "context-window-management", "Manage and trim context to prevent overflow"),
        ("Tool Call Validation", "tool-call-validation", "Validate tool calls before execution"),
        ("Prompt Template Safety", "prompt-template-safety", "Sanitize user inputs before injecting into prompts"),
        ("Rate Limiting Middleware", "rate-limiting-middleware", "Implement per-user rate limiting"),
        ("Audit Logging", "audit-logging", "Log all agent actions for audit trails"),
        ("Error Recovery", "error-recovery", "Implement graceful error recovery strategies"),
        ("Fallback Chain", "fallback-chain", "Build model fallback chains for reliability"),
        ("Cost Tracking", "cost-tracking", "Track and limit LLM API costs per request"),
    ]

    pocs = []
    for i, (title, slug_base, goal) in enumerate(base_candidates[:state.target_poc_count], start=1):
        pocs.append(
            PocPlan(
                index=i,
                title=title,
                slug=poc_slug(i, slug_base),
                goal=goal,
                why_it_matters=f"Essential for production {state.normalized_phrase} systems",
                required_packages=state.technologies[:3] if state.technologies else ["fastapi", "pydantic"],
                rank_justification=f"Rank {i}: fundamental pattern",
            )
        )

    return pocs
