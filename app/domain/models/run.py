"""Core domain models for Run and related entities."""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"
    CANCELLED = "cancelled"


class BuildStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class ValidationStatus(str, Enum):
    NOT_RUN = "not_run"
    PASSED = "passed"
    FAILED = "failed"
    PARTIAL = "partial"


class ArtifactType(str, Enum):
    CLAUDE_MD = "claude_md"
    REPO = "repo"
    PROSE_MARKDOWN = "prose_markdown"
    CODE_WALKTHROUGH_MARKDOWN = "code_walkthrough_markdown"
    BUILD_REPORT = "build_report"
    POC_PLAN = "poc_plan"
    LOG = "log"
    README = "readme"
    ENV_EXAMPLE = "env_example"
    DOCKERFILE = "dockerfile"
    DOCKER_COMPOSE = "docker_compose"
    REQUIREMENTS = "requirements"


class StarterRepoSource(BaseModel):
    """Source configuration for the starter repository."""

    provider: str = Field(default="github")
    repo_url: str
    branch: str = Field(default="main")
    commit: Optional[str] = Field(default=None)
    tag: Optional[str] = Field(default=None)

    @property
    def safe_url(self) -> str:
        """Return URL with token masked for logging."""
        import re
        return re.sub(r"://[^@]+@", "://***@", self.repo_url)


class GenerationPreferences(BaseModel):
    """User preferences for POC generation."""

    use_docker: bool = Field(default=False)
    use_pytest: bool = Field(default=True)
    prefer_mocks: bool = Field(default=True)
    include_mermaid: bool = Field(default=False)
    use_uv: bool = Field(default=False)
    favor_deterministic: bool = Field(default=False)
    prefer_local_mocks: bool = Field(default=True)


class TechnologySelection(BaseModel):
    """Selected technologies for a run."""

    required: list[str] = Field(default_factory=list)
    optional: list[str] = Field(default_factory=list)

    @property
    def all_packages(self) -> list[str]:
        return list(dict.fromkeys(self.required + self.optional))


class ArtifactMetadata(BaseModel):
    """Metadata for a generated artifact."""

    path: str
    type: ArtifactType
    created_at: datetime = Field(default_factory=datetime.utcnow)
    sha256: Optional[str] = Field(default=None)
    size_bytes: Optional[int] = Field(default=None)
    status: str = Field(default="created")


class ValidationResult(BaseModel):
    """Result of a single validation check."""

    tool: str
    success: bool
    stdout: str = Field(default="")
    stderr: str = Field(default="")
    exit_code: int = Field(default=0)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = Field(default=None)
    notes: list[str] = Field(default_factory=list)


class ValidationSuite(BaseModel):
    """Collection of validation results for a POC."""

    results: list[ValidationResult] = Field(default_factory=list)
    overall_passed: bool = Field(default=False)
    missing_files: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

    def add_result(self, result: ValidationResult) -> None:
        self.results.append(result)
        self.overall_passed = all(r.success for r in self.results)


class RepairAttempt(BaseModel):
    """Record of a repair attempt for a failed POC build."""

    attempt_number: int
    prompt_used: str
    command: str
    exit_code: int
    stdout: str = Field(default="")
    stderr: str = Field(default="")
    started_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = Field(default=None)
    succeeded: bool = Field(default=False)
    validation_after: Optional[ValidationSuite] = Field(default=None)


class PocPlan(BaseModel):
    """Plan for a single POC before execution."""

    index: int
    title: str
    slug: str
    goal: str
    why_it_matters: str = Field(default="")
    scope_boundaries: list[str] = Field(default_factory=list)
    required_packages: list[str] = Field(default_factory=list)
    rank_justification: str = Field(default="")
    excludes: list[str] = Field(default_factory=list)


class MarkdownArtifact(BaseModel):
    """A generated markdown file."""

    path: str
    type: str  # "prose" or "walkthrough"
    poc_slug: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    word_count: Optional[int] = Field(default=None)
    status: str = Field(default="pending")


class PocExecution(BaseModel):
    """Full execution record for a single POC."""

    poc_index: int
    poc_title: str
    poc_slug: str
    poc_goal: str
    why_it_matters: str = Field(default="")
    scope_boundaries: list[str] = Field(default_factory=list)
    required_packages: list[str] = Field(default_factory=list)
    folder_path: Optional[str] = Field(default=None)
    claude_md_path: Optional[str] = Field(default=None)
    build_status: BuildStatus = Field(default=BuildStatus.PENDING)
    validation_status: ValidationStatus = Field(default=ValidationStatus.NOT_RUN)
    repair_attempts: list[RepairAttempt] = Field(default_factory=list)
    artifacts: list[ArtifactMetadata] = Field(default_factory=list)
    logs: list[str] = Field(default_factory=list)
    test_results: Optional[ValidationSuite] = Field(default=None)
    static_check_results: Optional[ValidationSuite] = Field(default=None)
    markdown_status: BuildStatus = Field(default=BuildStatus.PENDING)
    readme_status: BuildStatus = Field(default=BuildStatus.PENDING)
    docker_status: BuildStatus = Field(default=BuildStatus.SKIPPED)
    env_example_status: BuildStatus = Field(default=BuildStatus.PENDING)
    error_message: Optional[str] = Field(default=None)
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    notes: list[str] = Field(default_factory=list)

    @property
    def repair_count(self) -> int:
        return len(self.repair_attempts)

    @property
    def is_complete(self) -> bool:
        return self.build_status in (BuildStatus.SUCCEEDED, BuildStatus.FAILED)


class Run(BaseModel):
    """Top-level domain model for a generation run."""

    run_id: UUID = Field(default_factory=uuid4)
    phrase: str
    normalized_phrase: str = Field(default="")
    slug: str = Field(default="")
    technologies: list[str] = Field(default_factory=list)
    optional_packages: list[str] = Field(default_factory=list)
    target_poc_count: int = Field(default=10)
    preferences: GenerationPreferences = Field(default_factory=GenerationPreferences)
    starter_repo: Optional[StarterRepoSource] = Field(default=None)
    output_root: str = Field(default="./output")
    candidate_pocs: list[PocPlan] = Field(default_factory=list)
    selected_pocs: list[PocPlan] = Field(default_factory=list)
    poc_executions: list[PocExecution] = Field(default_factory=list)
    run_status: RunStatus = Field(default=RunStatus.PENDING)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(default=None)

    @property
    def run_output_path(self) -> Path:
        return Path(self.output_root) / self.slug

    @property
    def completed_pocs(self) -> list[PocExecution]:
        return [p for p in self.poc_executions if p.build_status == BuildStatus.SUCCEEDED]

    @property
    def failed_pocs(self) -> list[PocExecution]:
        return [p for p in self.poc_executions if p.build_status == BuildStatus.FAILED]


class RunReport(BaseModel):
    """Final report for a completed run."""

    run_id: str
    phrase: str
    normalized_phrase: str
    slug: str
    status: RunStatus
    total_pocs: int
    completed_pocs: int
    failed_pocs: int
    poc_summaries: list[dict] = Field(default_factory=list)
    artifact_root: str
    started_at: datetime
    completed_at: Optional[datetime]
    duration_seconds: Optional[float] = Field(default=None)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
