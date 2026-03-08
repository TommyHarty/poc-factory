"""FastAPI dependency injection for orchestrator."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from app.application.orchestrators.run_orchestrator import RunOrchestrator


@lru_cache
def _get_orchestrator() -> RunOrchestrator:
    return RunOrchestrator()


def get_orchestrator() -> RunOrchestrator:
    return _get_orchestrator()


OrchestratorDep = Annotated[RunOrchestrator, Depends(get_orchestrator)]
