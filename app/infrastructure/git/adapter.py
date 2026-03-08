"""Git adapter for cloning and managing starter repositories."""

import shutil
from pathlib import Path
from typing import Optional

from git import Repo  # type: ignore[import-untyped]
from git.exc import GitCommandError  # type: ignore[import-untyped]

from app.domain.models.run import StarterRepoSource
from app.logging_config import get_logger

logger = get_logger(__name__)


class GitError(Exception):
    """Raised when a git operation fails."""


class GitAdapter:
    """Handles git operations for starter repo acquisition."""

    def __init__(self, cache_dir: Path, github_token: Optional[str] = None) -> None:
        self.cache_dir = cache_dir
        self.github_token = github_token
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _inject_token_into_url(self, url: str) -> str:
        """Inject GitHub token into HTTPS URL if available.

        Uses the x-access-token format which works for both classic PATs
        and fine-grained personal access tokens.
        """
        if self.github_token and "github.com" in url and "://" in url:
            protocol, rest = url.split("://", 1)
            if "@" not in rest:
                return f"{protocol}://x-access-token:{self.github_token}@{rest}"
        return url

    def _cache_key(self, source: StarterRepoSource) -> str:
        """Generate a deterministic cache key for a repo source."""
        import hashlib
        key = f"{source.repo_url}:{source.branch}:{source.commit or ''}"
        return hashlib.md5(key.encode()).hexdigest()[:12]

    def get_cached_path(self, source: StarterRepoSource) -> Path:
        """Return path where this source would be cached."""
        key = self._cache_key(source)
        return self.cache_dir / key

    def clone_to_cache(self, source: StarterRepoSource) -> Path:
        """Clone the starter repo to cache if not already present."""
        cache_path = self.get_cached_path(source)

        if cache_path.exists() and (cache_path / ".git").exists():
            logger.info(
                "using_cached_starter_repo",
                path=str(cache_path),
                repo=source.safe_url,
            )
            # Pull latest if not pinned to specific commit
            if not source.commit and not source.tag:
                try:
                    repo = Repo(str(cache_path))
                    origin = repo.remotes.origin
                    origin.fetch()
                    repo.git.checkout(source.branch)
                    repo.git.pull("origin", source.branch)
                    logger.info("pulled_latest", branch=source.branch)
                except Exception as e:
                    logger.warning("pull_failed_using_cache", error=str(e))
            return cache_path

        authenticated_url = self._inject_token_into_url(source.repo_url)

        try:
            logger.info(
                "cloning_starter_repo",
                repo=source.safe_url,
                branch=source.branch,
                cache_path=str(cache_path),
            )

            repo = Repo.clone_from(
                authenticated_url,
                str(cache_path),
                branch=source.branch,
                depth=1 if not source.commit else None,
            )

            if source.commit:
                repo.git.checkout(source.commit)
            elif source.tag:
                repo.git.checkout(source.tag)

            logger.info("clone_succeeded", path=str(cache_path))
            return cache_path

        except GitCommandError as e:
            error_msg = str(e).replace(
                self.github_token or "", "***"
            ) if self.github_token else str(e)
            raise GitError(f"Failed to clone starter repo: {error_msg}") from e

    def copy_starter_to_poc_folder(
        self,
        source: StarterRepoSource,
        poc_folder: Path,
        exclude_git: bool = True,
    ) -> None:
        """Copy the cached starter repo into a POC folder."""
        cached = self.clone_to_cache(source)

        if poc_folder.exists():
            # Remove existing contents but keep the folder itself
            for item in poc_folder.iterdir():
                if item.name == ".git" and exclude_git:
                    continue
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(str(item))

        def ignore_fn(_: str, contents: list[str]) -> list[str]:
            ignored = []
            if exclude_git:
                if ".git" in contents:
                    ignored.append(".git")
            return ignored

        shutil.copytree(str(cached), str(poc_folder), dirs_exist_ok=True, ignore=ignore_fn)
        logger.info(
            "copied_starter_to_poc",
            source=str(cached),
            destination=str(poc_folder),
        )

