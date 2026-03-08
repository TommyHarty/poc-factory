"""Graph state definitions for the POC Factory LangGraph orchestration."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.domain.models.run import (
    BuildStatus,
    GenerationPreferences,
    PocExecution,
    PocPlan,
    RunStatus,
    StarterRepoSource,
    ValidationStatus,
)


def merge_list(left: list, right: list) -> list:
    """Merge two lists, preferring right (for LangGraph reducers)."""
    return right if right else left


def merge_dict(left: dict, right: dict) -> dict:
    """Merge two dicts."""
    return {**left, **right}


class RunGraphState(BaseModel):
    """Top-level state for the run-level LangGraph graph."""

    # Identity
    run_id: str = Field(default="")
    phrase: str = Field(default="")
    normalized_phrase: str = Field(default="")
    slug: str = Field(default="")

    # Input
    technologies: list[str] = Field(default_factory=list)
    optional_packages: list[str] = Field(default_factory=list)
    target_poc_count: int = Field(default=10)
    preferences: GenerationPreferences = Field(default_factory=GenerationPreferences)
    starter_repo: Optional[StarterRepoSource] = Field(default=None)
    generation_policy: dict[str, Any] = Field(default_factory=dict)

    # Paths
    output_root: str = Field(default="./output")
    run_output_path: str = Field(default="")
    starter_repo_local_path: Optional[str] = Field(default=None)

    # Planning
    candidate_pocs: list[PocPlan] = Field(default_factory=list)
    selected_pocs: list[PocPlan] = Field(default_factory=list)

    # Execution
    poc_executions: list[PocExecution] = Field(default_factory=list)

    # Status
    run_status: RunStatus = Field(default=RunStatus.PENDING)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    # Timestamps
    started_at: Optional[datetime] = Field(default=None)
    updated_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)

    # Dry-run
    dry_run: bool = Field(default=False)

    model_config = ConfigDict(arbitrary_types_allowed=True)


class PocGraphState(BaseModel):
    """State for a single POC's subgraph execution."""

    # Run context
    run_id: str = Field(default="")
    phrase: str = Field(default="")
    slug: str = Field(default="")
    technologies: list[str] = Field(default_factory=list)
    optional_packages: list[str] = Field(default_factory=list)
    preferences: GenerationPreferences = Field(default_factory=GenerationPreferences)
    starter_repo: Optional[StarterRepoSource] = Field(default=None)
    starter_repo_local_path: Optional[str] = Field(default=None)
    output_root: str = Field(default="./output")
    dry_run: bool = Field(default=False)
    max_repair_attempts: int = Field(default=2)

    # POC identity
    poc_index: int = Field(default=0)
    poc_title: str = Field(default="")
    poc_slug: str = Field(default="")
    poc_goal: str = Field(default="")
    why_it_matters: str = Field(default="")
    scope_boundaries: list[str] = Field(default_factory=list)
    required_packages: list[str] = Field(default_factory=list)

    # Paths
    folder_path: Optional[str] = Field(default=None)
    claude_md_path: Optional[str] = Field(default=None)

    # Status
    build_status: BuildStatus = Field(default=BuildStatus.PENDING)
    validation_status: ValidationStatus = Field(default=ValidationStatus.NOT_RUN)
    repair_attempts: int = Field(default=0)
    markdown_status: BuildStatus = Field(default=BuildStatus.PENDING)
    readme_status: BuildStatus = Field(default=BuildStatus.PENDING)
    docker_status: BuildStatus = Field(default=BuildStatus.SKIPPED)
    env_example_status: BuildStatus = Field(default=BuildStatus.PENDING)

    # Results
    build_stdout: str = Field(default="")
    build_stderr: str = Field(default="")
    build_exit_code: int = Field(default=0)
    static_check_results: list[dict] = Field(default_factory=list)
    test_results: list[dict] = Field(default_factory=list)
    artifacts: list[dict] = Field(default_factory=list)
    logs: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    error_message: Optional[str] = Field(default=None)

    # Timestamps
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)

    model_config = ConfigDict(arbitrary_types_allowed=True)
