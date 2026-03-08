"""POC subgraph definition using LangGraph."""

from typing import Any

from langgraph.graph import END, START, StateGraph # type: ignore[import-untyped]

from app.domain.models.run import BuildStatus, ValidationStatus
from app.graph.nodes.poc_nodes import (
    acquire_starter_repo,
    assess_build_result,
    generate_code_walkthrough_markdown,
    generate_poc_claude_md,
    generate_prose_markdown,
    invoke_claude_code_build,
    invoke_claude_code_repair,
    mark_poc_complete,
    prepare_poc_folder,
    run_static_checks,
    run_tests,
    update_docker_assets,
    update_env_example,
    update_readme,
    write_build_report,
)
from app.graph.state import PocGraphState


def _should_repair(state: PocGraphState) -> str:
    """Conditional edge: repair or proceed to markdown."""
    max_attempts = state.max_repair_attempts

    validation_failed = state.validation_status in (
        ValidationStatus.FAILED,
        ValidationStatus.PARTIAL,
    )

    if validation_failed and state.repair_attempts < max_attempts:
        return "repair"
    return "proceed"


def _should_skip_markdown(state: PocGraphState) -> str:
    """Conditional edge: skip markdown if build totally failed."""
    if state.build_status == BuildStatus.FAILED and state.validation_status == ValidationStatus.FAILED:
        return "skip_to_report"
    return "generate_markdown"


def build_poc_graph() -> StateGraph:
    """Build and return the POC subgraph."""

    # Use a dict-based state for LangGraph compatibility
    graph = StateGraph(dict)

    # Add all nodes
    graph.add_node("prepare_poc_folder", lambda s: _run_node(prepare_poc_folder, s))
    graph.add_node("acquire_starter_repo", lambda s: _run_node(acquire_starter_repo, s))
    graph.add_node("generate_poc_claude_md", lambda s: _run_node(generate_poc_claude_md, s))
    graph.add_node("invoke_claude_code_build", lambda s: _run_node(invoke_claude_code_build, s))
    graph.add_node("run_static_checks", lambda s: _run_node(run_static_checks, s))
    graph.add_node("run_tests", lambda s: _run_node(run_tests, s))
    graph.add_node("assess_build_result", lambda s: _run_node(assess_build_result, s))
    graph.add_node("invoke_claude_code_repair", lambda s: _run_node(invoke_claude_code_repair, s))
    graph.add_node("generate_prose_markdown", lambda s: _run_node(generate_prose_markdown, s))
    graph.add_node("generate_code_walkthrough_markdown", lambda s: _run_node(generate_code_walkthrough_markdown, s))
    graph.add_node("update_readme", lambda s: _run_node(update_readme, s))
    graph.add_node("update_env_example", lambda s: _run_node(update_env_example, s))
    graph.add_node("update_docker_assets", lambda s: _run_node(update_docker_assets, s))
    graph.add_node("write_build_report", lambda s: _run_node(write_build_report, s))
    graph.add_node("mark_poc_complete", lambda s: _run_node(mark_poc_complete, s))

    # Edges: start -> prepare
    graph.add_edge(START, "prepare_poc_folder")
    graph.add_edge("prepare_poc_folder", "acquire_starter_repo")
    graph.add_edge("acquire_starter_repo", "generate_poc_claude_md")
    graph.add_edge("generate_poc_claude_md", "invoke_claude_code_build")
    graph.add_edge("invoke_claude_code_build", "run_static_checks")
    graph.add_edge("run_static_checks", "run_tests")
    graph.add_edge("run_tests", "assess_build_result")

    # Conditional: repair or proceed
    graph.add_conditional_edges(
        "assess_build_result",
        lambda s: _should_repair(PocGraphState(**s)),
        {
            "repair": "invoke_claude_code_repair",
            "proceed": "generate_prose_markdown",
        },
    )

    # After repair: re-run checks
    graph.add_edge("invoke_claude_code_repair", "run_static_checks")

    # Markdown generation chain
    graph.add_edge("generate_prose_markdown", "generate_code_walkthrough_markdown")
    graph.add_edge("generate_code_walkthrough_markdown", "update_readme")
    graph.add_edge("update_readme", "update_env_example")
    graph.add_edge("update_env_example", "update_docker_assets")
    graph.add_edge("update_docker_assets", "write_build_report")
    graph.add_edge("write_build_report", "mark_poc_complete")
    graph.add_edge("mark_poc_complete", END)

    return graph


def _run_node(node_fn: Any, state_dict: dict) -> dict:
    """Convert dict state to PocGraphState, run node, convert back."""
    state = PocGraphState(**state_dict)
    updated = node_fn(state)
    return updated.model_dump()


def compile_poc_graph():
    """Compile the POC graph for execution."""
    graph = build_poc_graph()
    return graph.compile()
