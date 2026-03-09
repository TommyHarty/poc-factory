"""API routes for run management."""

from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from app.api.dependencies.orchestrator import OrchestratorDep
from app.api.schemas.runs import (
    ArtifactResponse,
    CreateRunRequest,
    CreateRunResponse,
    PocStatusResponse,
    ResumeRunResponse,
    RetryFailuresResponse,
    RunArtifactsResponse,
    RunStatusResponse,
)
from app.domain.models.run import GenerationPreferences
from app.domain.value_objects.slug import normalize_phrase, phrase_to_slug
from app.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/runs", tags=["runs"])


@router.post("", response_model=CreateRunResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_run(
    request: CreateRunRequest,
    background_tasks: BackgroundTasks,
    orchestrator: OrchestratorDep,
) -> CreateRunResponse:
    """Create a new POC generation run.

    The run starts in the background immediately.
    Use GET /runs/{run_id} to check progress.
    """
    logger.info("api_create_run", phrase=request.phrase)

    # Build domain objects from request
    preferences = GenerationPreferences(
        use_docker=request.preferences.use_docker,
        use_pytest=request.preferences.use_pytest,
        prefer_mocks=request.preferences.prefer_mocks,
        include_mermaid=request.preferences.include_mermaid,
        use_uv=request.preferences.use_uv,
        favor_deterministic=request.preferences.favor_deterministic,
        prefer_local_mocks=request.preferences.prefer_local_mocks,
    )

    run_id = await orchestrator.create_run(
        phrase=request.phrase,
        technologies=request.technologies,
        optional_packages=request.optional_packages,
        target_poc_count=request.target_poc_count,
        preferences=preferences,
        dry_run=request.dry_run,
    )

    # Start background execution
    background_tasks.add_task(orchestrator.start_run_background, run_id)

    normalized = normalize_phrase(request.phrase)
    slug = phrase_to_slug(normalized)

    return CreateRunResponse(
        run_id=run_id,
        status="running",
        message=f"Run started. Use GET /runs/{run_id} to check progress.",
        phrase=request.phrase,
        normalized_phrase=normalized,
        slug=slug,
    )


@router.get("/{run_id}", response_model=RunStatusResponse)
async def get_run_status(
    run_id: str,
    orchestrator: OrchestratorDep,
) -> RunStatusResponse:
    """Get current status of a run."""
    state = await orchestrator.get_run_status(run_id)
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run {run_id} not found",
        )

    poc_statuses = []
    for poc in state.get("poc_executions", []):
        if isinstance(poc, dict):
            poc_statuses.append(
                PocStatusResponse(
                    poc_slug=poc.get("poc_slug", ""),
                    poc_title=poc.get("poc_title", ""),
                    poc_goal=poc.get("poc_goal", ""),
                    build_status=poc.get("build_status", "pending"),
                    validation_status=poc.get("validation_status", "not_run"),
                    repair_attempts=(
                        ra if isinstance(ra := poc.get("repair_attempts", 0), int)
                        else len(ra)
                    ),
                    markdown_status=poc.get("markdown_status", "pending"),
                    folder_path=poc.get("folder_path"),
                    error_message=poc.get("error_message"),
                    notes=poc.get("notes", []),
                )
            )

    return RunStatusResponse(
        run_id=run_id,
        phrase=state.get("phrase", ""),
        normalized_phrase=state.get("normalized_phrase", ""),
        slug=state.get("slug", ""),
        run_status=state.get("run_status", "pending"),
        technologies=state.get("technologies", []),
        optional_packages=state.get("optional_packages", []),
        target_poc_count=state.get("target_poc_count", 10),
        selected_poc_count=len(state.get("selected_pocs", [])),
        poc_statuses=poc_statuses,
        errors=state.get("errors", []),
        warnings=state.get("warnings", []),
        started_at=state["started_at"].isoformat() if state.get("started_at") is not None else None,
        completed_at=state["completed_at"].isoformat() if state.get("completed_at") is not None else None,
        output_path=state.get("run_output_path"),
    )


@router.get("/{run_id}/artifacts", response_model=RunArtifactsResponse)
async def get_run_artifacts(
    run_id: str,
    orchestrator: OrchestratorDep,
) -> RunArtifactsResponse:
    """Get artifact metadata for a run."""
    state = await orchestrator.get_run_status(run_id)
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run {run_id} not found",
        )

    raw_artifacts = await orchestrator.get_run_artifacts(run_id)

    artifacts = [
        ArtifactResponse(
            poc_slug=a.get("poc_slug"),
            type=str(a.get("type", "unknown")),
            path=a.get("path", ""),
            created_at=str(a.get("created_at")) if a.get("created_at") else None,
            status=a.get("status", "created"),
        )
        for a in raw_artifacts
    ]

    return RunArtifactsResponse(
        run_id=run_id,
        artifacts=artifacts,
        total_count=len(artifacts),
    )


@router.post("/{run_id}/resume", response_model=ResumeRunResponse)
async def resume_run(
    run_id: str,
    background_tasks: BackgroundTasks,
    orchestrator: OrchestratorDep,
) -> ResumeRunResponse:
    """Resume an interrupted run."""
    state = await orchestrator.get_run_status(run_id)
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run {run_id} not found",
        )

    current_status = state.get("run_status", "pending")
    if current_status == "running":
        if orchestrator.is_run_active(run_id):
            return ResumeRunResponse(
                run_id=run_id,
                status="running",
                message="Run is already active",
            )

    if current_status in ("completed",):
        return ResumeRunResponse(
            run_id=run_id,
            status=current_status,
            message="Run is already completed",
        )

    # Restart the background execution
    background_tasks.add_task(orchestrator.start_run_background, run_id)

    return ResumeRunResponse(
        run_id=run_id,
        status="running",
        message="Run resumed",
    )


@router.post("/{run_id}/retry-failures", response_model=RetryFailuresResponse)
async def retry_failures(
    run_id: str,
    orchestrator: OrchestratorDep,
) -> RetryFailuresResponse:
    """Retry failed POCs in a run."""
    state = await orchestrator.get_run_status(run_id)
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run {run_id} not found",
        )

    failed_pocs = [
        p for p in state.get("poc_executions", [])
        if isinstance(p, dict) and p.get("build_status") == "failed"
    ]

    if not failed_pocs:
        return RetryFailuresResponse(
            run_id=run_id,
            retry_run_id=run_id,
            status="no_failures",
            message="No failed POCs found",
            failed_poc_count=0,
        )

    try:
        retry_run_id = await orchestrator.retry_failed_pocs(run_id)
        return RetryFailuresResponse(
            run_id=run_id,
            retry_run_id=retry_run_id,
            status="retrying",
            message=f"Retrying {len(failed_pocs)} failed POC(s)",
            failed_poc_count=len(failed_pocs),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
