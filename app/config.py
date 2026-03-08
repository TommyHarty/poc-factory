"""Application configuration using pydantic-settings."""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_env: str = Field(default="development")
    log_level: str = Field(default="INFO")
    app_name: str = Field(default="poc-factory")
    app_version: str = Field(default="0.1.0")

    # Output paths
    output_root: Path = Field(default=Path("./output"))
    work_root: Path = Field(default=Path("./work"))
    starter_repo_cache_dir: Optional[Path] = Field(default=None)

    # GitHub
    github_token: Optional[str] = Field(default=None)
    starter_repo_url: str = Field(default="")
    starter_repo_branch: str = Field(default="main")

    # Claude Code
    claude_code_command: str = Field(default="claude")
    claude_code_timeout_seconds: int = Field(default=300)
    claude_code_max_repair_attempts: int = Field(default=2)

    # OpenAI
    openai_api_key: Optional[str] = Field(default=None)
    openai_model: str = Field(default="gpt-4o")

    # Langfuse
    enable_langfuse: bool = Field(default=False)
    langfuse_public_key: Optional[str] = Field(default=None)
    langfuse_secret_key: Optional[str] = Field(default=None)
    langfuse_host: str = Field(default="https://cloud.langfuse.com")

    # Persistence
    database_url: str = Field(default="sqlite+aiosqlite:///./poc_factory.db")

    # Defaults
    default_target_poc_count: int = Field(default=10)
    max_concurrent_pocs: int = Field(default=3)

    def model_post_init(self, __context: object) -> None:
        """Set derived defaults after init."""
        if self.starter_repo_cache_dir is None:
            self.starter_repo_cache_dir = self.work_root / "starter-cache"
        # Ensure paths are absolute relative to cwd if relative
        self.output_root = self.output_root.resolve()
        self.work_root = self.work_root.resolve()
        if self.starter_repo_cache_dir:
            self.starter_repo_cache_dir = self.starter_repo_cache_dir.resolve()

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
