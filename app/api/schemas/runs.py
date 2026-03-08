"""API request and response schemas for run endpoints."""

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class GenerationPreferencesRequest(BaseModel):
    use_docker: bool = Field(default=False)
    use_pytest: bool = Field(default=True)
    prefer_mocks: bool = Field(default=True)
    include_mermaid: bool = Field(default=False)
    use_uv: bool = Field(default=False)
    favor_deterministic: bool = Field(default=False)
    prefer_local_mocks: bool = Field(default=True)


class CreateRunRequest(BaseModel):
    """Request body for POST /runs."""

    phrase: str = Field(
        ...,
        min_length=3,
        max_length=200,
        description="The agentic systems topic phrase",
    )
    technologies: list[str] = Field(
        default_factory=list,
        description="Required technologies/packages to use",
    )
    optional_packages: list[str] = Field(
        default_factory=list,
        description="Optional packages to incorporate where relevant",
    )
    target_poc_count: int = Field(
        default=10,
        ge=8,
        le=15,
        description="Number of POCs to generate (8-15)",
    )
    preferences: GenerationPreferencesRequest = Field(
        default_factory=GenerationPreferencesRequest
    )
    dry_run: bool = Field(
        default=False,
        description="If true, skip Claude Code invocation (plan only)",
    )

    @field_validator("phrase")
    @classmethod
    def validate_phrase(cls, v: str) -> str:
        return v.strip()


class PocStatusResponse(BaseModel):
    """Status of a single POC execution."""

    poc_slug: str
    poc_title: str
    poc_goal: str
    build_status: str
    validation_status: str
    repair_attempts: int
    markdown_status: str
    folder_path: Optional[str] = None
    error_message: Optional[str] = None
    notes: list[str] = Field(default_factory=list)


class RunStatusResponse(BaseModel):
    """Response for GET /runs/{run_id}."""

    run_id: str
    phrase: str
    normalized_phrase: str
    slug: str
    run_status: str
    technologies: list[str]
    optional_packages: list[str]
    target_poc_count: int
    selected_poc_count: int
    poc_statuses: list[PocStatusResponse] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    output_path: Optional[str] = None


class CreateRunResponse(BaseModel):
    """Response for POST /runs."""

    run_id: str
    status: str = "pending"
    message: str
    phrase: str
    normalized_phrase: str = ""
    slug: str = ""


class ArtifactResponse(BaseModel):
    """A single artifact metadata entry."""

    poc_slug: Optional[str] = None
    type: str
    path: str
    created_at: Optional[str] = None
    status: str = "created"


class RunArtifactsResponse(BaseModel):
    """Response for GET /runs/{run_id}/artifacts."""

    run_id: str
    artifacts: list[ArtifactResponse] = Field(default_factory=list)
    total_count: int = 0


class ResumeRunResponse(BaseModel):
    """Response for POST /runs/{run_id}/resume."""

    run_id: str
    status: str
    message: str


class RetryFailuresResponse(BaseModel):
    """Response for POST /runs/{run_id}/retry-failures."""

    run_id: str
    retry_run_id: str
    status: str
    message: str
    failed_poc_count: int = 0
