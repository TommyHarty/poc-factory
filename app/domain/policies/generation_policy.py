"""Generation policy governing run constraints and defaults."""

from pydantic import BaseModel, Field


class GenerationPolicy(BaseModel):
    """Policy governing how a run is executed."""

    min_poc_count: int = Field(default=8)
    max_poc_count: int = Field(default=15)
    default_poc_count: int = Field(default=10)

    max_repair_attempts: int = Field(default=2)
    max_concurrent_pocs: int = Field(default=3)

    ideation_candidate_count: int = Field(default=18)
    # Generate more than needed, then rank/select top N

    require_tests: bool = Field(default=True)
    require_readme: bool = Field(default=True)
    require_env_example: bool = Field(default=True)

    dry_run_mode: bool = Field(default=False)
    # If true, skip Claude Code invocation

    skip_validation: bool = Field(default=False)
    skip_markdown_generation: bool = Field(default=False)

    def validate_poc_count(self, count: int) -> int:
        """Clamp count to allowed range."""
        return max(self.min_poc_count, min(self.max_poc_count, count))

    def is_valid_poc_count(self, count: int) -> bool:
        return self.min_poc_count <= count <= self.max_poc_count


DEFAULT_POLICY = GenerationPolicy()
