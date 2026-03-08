"""Orchestrator that manages the lifecycle of a POC Factory run."""

import asyncio
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

from app.config import get_settings
from app.domain.models.run import (
    GenerationPreferences,
    RunStatus,
    StarterRepoSource,
)
from app.domain.policies.generation_policy import DEFAULT_POLICY
from app.domain.value_objects.slug import deduplicate_packages
from app.graph.run_graph.graph import compile_run_graph
from app.graph.state import RunGraphState
from app.infrastructure.persistence.database import RunRepository
from app.logging_config import get_logger

logger = get_logger(__name__)

# In-memory store for active run states (supplements DB)
_active_runs: dict[str, dict] = {}
_run_threads: dict[str, threading.Thread] = {}


class RunOrchestrator:
    """Manages run lifecycle: creation, execution, status tracking."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.settings = get_settings()
        db_path = db_path or str(Path(self.settings.work_root) / "poc_factory.db")
        self.repo = RunRepository(db_path=db_path)

    async def create_run(
        self,
        phrase: str,
        technologies: list[str],
        optional_packages: list[str],
        target_poc_count: int,
        preferences: GenerationPreferences,
        dry_run: bool = False,
    ) -> str:
        """Create a new run and return the run_id."""
        if not self.settings.starter_repo_url:
            raise ValueError(
                "STARTER_REPO_URL is not configured. "
                "Set it in your .env file before starting a run."
            )

        run_id = str(uuid4())
        now = datetime.utcnow()

        # Normalize inputs
        technologies = deduplicate_packages(technologies)
        optional_packages = deduplicate_packages(optional_packages)
        target_poc_count = DEFAULT_POLICY.validate_poc_count(target_poc_count)

        starter_repo = StarterRepoSource(
            provider="github",
            repo_url=self.settings.starter_repo_url,
            branch=self.settings.starter_repo_branch,
        )

        state = RunGraphState(
            run_id=run_id,
            phrase=phrase,
            technologies=technologies,
            optional_packages=optional_packages,
            target_poc_count=target_poc_count,
            preferences=preferences,
            starter_repo=starter_repo,
            output_root=str(self.settings.output_root),
            run_status=RunStatus.PENDING,
            started_at=now,
            updated_at=now,
            dry_run=dry_run,
        )

        # Persist initial state
        _active_runs[run_id] = state.model_dump()
        await self.repo.save_run(_active_runs[run_id])

        logger.info("run_created", run_id=run_id, phrase=phrase)
        return run_id

    def start_run_background(self, run_id: str) -> None:
        """Start executing a run in a background thread."""
        def execute():
            try:
                self._execute_run_sync(run_id)
            except Exception as e:
                logger.error("background_run_failed", run_id=run_id, error=str(e))
                if run_id in _active_runs:
                    _active_runs[run_id]["run_status"] = RunStatus.FAILED
                    _active_runs[run_id]["errors"] = _active_runs[run_id].get("errors", []) + [str(e)]

        thread = threading.Thread(target=execute, daemon=True, name=f"run-{run_id[:8]}")
        _run_threads[run_id] = thread
        thread.start()
        logger.info("run_started_in_background", run_id=run_id)

    def _execute_run_sync(self, run_id: str) -> None:
        """Execute the run graph synchronously."""
        if run_id not in _active_runs:
            raise ValueError(f"Run {run_id} not found in active runs")

        initial_state = _active_runs[run_id]

        try:
            compiled_graph = compile_run_graph()
            logger.info("executing_run_graph", run_id=run_id)

            final_state_dict = compiled_graph.invoke(initial_state)
            _active_runs[run_id] = final_state_dict

            # Persist final state
            asyncio.run(self.repo.save_run(final_state_dict))
            logger.info(
                "run_graph_complete",
                run_id=run_id,
                status=final_state_dict.get("run_status"),
            )

        except Exception as e:
            logger.error("run_execution_failed", run_id=run_id, error=str(e))
            if run_id in _active_runs:
                _active_runs[run_id]["run_status"] = RunStatus.FAILED
                _active_runs[run_id]["errors"] = _active_runs[run_id].get("errors", []) + [str(e)]
            raise

    async def get_run_status(self, run_id: str) -> Optional[dict]:
        """Get the current state of a run."""
        # Check in-memory first (more current)
        if run_id in _active_runs:
            return _active_runs[run_id]
        # Fall back to DB
        return await self.repo.get_run(run_id)

    async def get_run_artifacts(self, run_id: str) -> list[dict]:
        """Get artifact paths for a completed run."""
        state = await self.get_run_status(run_id)
        if not state:
            return []

        artifacts = []
        for poc in state.get("poc_executions", []):
            if isinstance(poc, dict):
                for art in poc.get("artifacts", []):
                    artifacts.append(
                        {
                            "poc_slug": poc.get("poc_slug"),
                            **art,
                        }
                    )
        return artifacts

    def is_run_active(self, run_id: str) -> bool:
        """Check if a run is currently executing."""
        thread = _run_threads.get(run_id)
        return thread is not None and thread.is_alive()

    async def retry_failed_pocs(self, run_id: str) -> str:
        """Create a new run targeting only failed POCs."""
        state = await self.get_run_status(run_id)
        if not state:
            raise ValueError(f"Run {run_id} not found")

        failed_pocs = [
            p for p in state.get("poc_executions", [])
            if isinstance(p, dict) and p.get("build_status") == "failed"
        ]

        if not failed_pocs:
            raise ValueError("No failed POCs to retry")

        # For a retry, we'd need to re-run just the failed POC subgraphs
        # This is a simplified implementation
        logger.info("retry_failed_pocs", run_id=run_id, failed_count=len(failed_pocs))

        # Return original run_id for now (in a full implementation, this would create a new run)
        return run_id


def get_orchestrator() -> RunOrchestrator:
    """Get a configured orchestrator instance."""
    return RunOrchestrator()
