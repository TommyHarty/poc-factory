"""Edge routing logic for the POC subgraph."""

from app.domain.models.run import BuildStatus, ValidationStatus
from app.graph.state import PocGraphState


def should_repair_or_continue(state: PocGraphState) -> str:
    """Decide whether to attempt repair or continue to markdown generation."""
    from app.config import get_settings
    settings = get_settings()

    max_attempts = state.max_repair_attempts

    validation_failed = state.validation_status in (
        ValidationStatus.FAILED,
        ValidationStatus.PARTIAL,
    )

    if validation_failed and state.repair_attempts < max_attempts:
        return "repair"

    return "continue"


def should_continue_after_repair(state: PocGraphState) -> str:
    """After a repair attempt, decide whether to re-validate or give up."""
    from app.config import get_settings
    settings = get_settings()

    max_attempts = state.max_repair_attempts

    if state.repair_attempts < max_attempts:
        return "revalidate"

    return "finalize"


def build_succeeded_or_failed(state: PocGraphState) -> str:
    """Route based on initial Claude Code build result."""
    if state.build_status == BuildStatus.FAILED:
        return "failed"
    return "succeeded"
