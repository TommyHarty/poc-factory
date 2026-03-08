"""Run-level graph orchestrating the full POC Factory flow."""

from datetime import datetime, timezone
from typing import Any

from langgraph.graph import END, START, StateGraph  # type: ignore[import-untyped]

from app.domain.models.run import ArtifactMetadata, BuildStatus, PocExecution, RunStatus, ValidationSuite
from app.graph.nodes.run_nodes import (
    aggregate_run_results,
    create_run_plan,
    expand_poc_candidates,
    finalize_run,
    ingest_request,
    normalize_phrase_node,
    rank_and_select_pocs,
)
from app.graph.state import PocGraphState, RunGraphState
from app.logging_config import get_logger

logger = get_logger(__name__)


def _run_poc_subgraph(poc_state_dict: dict) -> dict:
    """Execute the POC subgraph for a single POC."""
    from app.graph.poc_graph.graph import compile_poc_graph

    try:
        compiled = compile_poc_graph()
        result = compiled.invoke(poc_state_dict)
        return result
    except Exception as e:
        logger.error("poc_subgraph_failed", error=str(e), poc_slug=poc_state_dict.get("poc_slug"))
        # Return a failed state
        poc_state_dict["build_status"] = BuildStatus.FAILED
        poc_state_dict["error_message"] = str(e)
        poc_state_dict["completed_at"] = datetime.now(timezone.utc).isoformat()
        return poc_state_dict


def fan_out_poc_jobs(state: RunGraphState) -> RunGraphState:
    """Fan out POC execution across all selected POCs."""
    logger.info("fan_out_poc_jobs", poc_count=len(state.selected_pocs))

    if not state.selected_pocs:
        state.errors.append("No POCs to execute")
        return state

    from app.config import get_settings
    settings = get_settings()

    poc_executions = []

    for poc in state.selected_pocs:
        # Build per-POC state
        poc_state = PocGraphState(
            run_id=state.run_id,
            phrase=state.phrase,
            slug=state.slug,
            technologies=state.technologies,
            optional_packages=state.optional_packages,
            preferences=state.preferences,
            starter_repo=state.starter_repo,
            starter_repo_local_path=state.starter_repo_local_path,
            output_root=state.output_root,
            dry_run=state.dry_run,
            max_repair_attempts=settings.claude_code_max_repair_attempts,
            poc_index=poc.index,
            poc_title=poc.title,
            poc_slug=poc.slug,
            poc_goal=poc.goal,
            why_it_matters=poc.why_it_matters,
            scope_boundaries=poc.scope_boundaries,
            required_packages=poc.required_packages,
        )

        logger.info("executing_poc", poc_slug=poc.slug, index=poc.index)

        try:
            result_dict = _run_poc_subgraph(poc_state.model_dump())
            result_state = PocGraphState(**result_dict)

            poc_exec = PocExecution(
                poc_index=result_state.poc_index,
                poc_title=result_state.poc_title,
                poc_slug=result_state.poc_slug,
                poc_goal=result_state.poc_goal,
                why_it_matters=result_state.why_it_matters,
                scope_boundaries=result_state.scope_boundaries,
                required_packages=result_state.required_packages,
                folder_path=result_state.folder_path,
                claude_md_path=result_state.claude_md_path,
                build_status=result_state.build_status,
                validation_status=result_state.validation_status,
                # graph state tracks repair count as int; domain model stores RepairAttempt objects
                repair_attempts=[],
                artifacts=[
                    ArtifactMetadata.model_validate(a)
                    for a in result_state.artifacts
                ],
                logs=result_state.logs,
                test_results=(
                    ValidationSuite.model_validate({
                        "results": result_state.test_results,
                        "overall_passed": all(r.get("success", False) for r in result_state.test_results),
                    })
                    if result_state.test_results else None
                ),
                static_check_results=(
                    ValidationSuite.model_validate({
                        "results": result_state.static_check_results,
                        "overall_passed": all(r.get("success", False) for r in result_state.static_check_results),
                    })
                    if result_state.static_check_results else None
                ),
                markdown_status=result_state.markdown_status,
                readme_status=result_state.readme_status,
                docker_status=result_state.docker_status,
                env_example_status=result_state.env_example_status,
                error_message=result_state.error_message,
                started_at=result_state.started_at,
                completed_at=result_state.completed_at,
                notes=result_state.notes,
            )
            poc_executions.append(poc_exec)

        except Exception as e:
            logger.error("poc_execution_error", poc_slug=poc.slug, error=str(e))
            poc_exec = PocExecution(
                poc_index=poc.index,
                poc_title=poc.title,
                poc_slug=poc.slug,
                poc_goal=poc.goal,
                why_it_matters=poc.why_it_matters,
                scope_boundaries=poc.scope_boundaries,
                required_packages=poc.required_packages,
                build_status=BuildStatus.FAILED,
                error_message=str(e),
            )
            poc_executions.append(poc_exec)

    state.poc_executions = poc_executions
    state.updated_at = datetime.now(timezone.utc)

    logger.info(
        "fan_out_complete",
        total=len(poc_executions),
        succeeded=sum(1 for p in poc_executions if p.build_status == BuildStatus.SUCCEEDED),
        failed=sum(1 for p in poc_executions if p.build_status == BuildStatus.FAILED),
    )

    return state


def _wrap_node(node_fn: Any):
    """Wrap a node function to work with dict state."""
    def wrapper(state_dict: dict) -> dict:
        state = RunGraphState(**state_dict)
        updated = node_fn(state)
        return updated.model_dump()
    return wrapper


def build_run_graph() -> StateGraph:
    """Build the run-level LangGraph graph."""
    graph = StateGraph(dict)

    graph.add_node("ingest_request", _wrap_node(ingest_request))
    graph.add_node("normalize_phrase", _wrap_node(normalize_phrase_node))
    graph.add_node("expand_poc_candidates", _wrap_node(expand_poc_candidates))
    graph.add_node("rank_and_select_pocs", _wrap_node(rank_and_select_pocs))
    graph.add_node("create_run_plan", _wrap_node(create_run_plan))
    graph.add_node("fan_out_poc_jobs", _wrap_node(fan_out_poc_jobs))
    graph.add_node("aggregate_run_results", _wrap_node(aggregate_run_results))
    graph.add_node("finalize_run", _wrap_node(finalize_run))

    # Define the flow
    graph.add_edge(START, "ingest_request")
    graph.add_edge("ingest_request", "normalize_phrase")
    graph.add_edge("normalize_phrase", "expand_poc_candidates")
    graph.add_edge("expand_poc_candidates", "rank_and_select_pocs")

    # Conditional after ranking: proceed or fail
    graph.add_conditional_edges(
        "rank_and_select_pocs",
        lambda s: "failed" if s.get("run_status") == RunStatus.FAILED else "proceed",
        {
            "failed": "finalize_run",
            "proceed": "create_run_plan",
        },
    )

    graph.add_edge("create_run_plan", "fan_out_poc_jobs")
    graph.add_edge("fan_out_poc_jobs", "aggregate_run_results")
    graph.add_edge("aggregate_run_results", "finalize_run")
    graph.add_edge("finalize_run", END)

    return graph


def compile_run_graph():
    """Compile the run graph for execution."""
    graph = build_run_graph()
    return graph.compile()
