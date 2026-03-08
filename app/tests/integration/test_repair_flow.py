"""Integration tests for the repair flow."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.domain.models.run import BuildStatus, GenerationPreferences, ValidationStatus
from app.graph.state import PocGraphState


class TestRepairFlow:
    @pytest.fixture
    def tmp_output(self):
        with tempfile.TemporaryDirectory() as d:
            yield Path(d)

    @pytest.fixture
    def failed_poc_state(self, tmp_output) -> PocGraphState:
        """Create a POC state that has failed initial build."""
        # Set up a minimal POC folder
        poc_folder = tmp_output / "prompt-injection-guardrails" / "01-test-poc"
        poc_folder.mkdir(parents=True)
        (poc_folder / "CLAUDE.md").write_text("# Test POC\n\nBuild this.")

        state = PocGraphState(
            run_id="test-001",
            phrase="prompt injection guardrails",
            slug="prompt-injection-guardrails",
            output_root=str(tmp_output),
            poc_index=1,
            poc_title="Test POC",
            poc_slug="01-test-poc",
            poc_goal="Test goal",
            folder_path=str(poc_folder),
            claude_md_path=str(poc_folder / "CLAUDE.md"),
            build_status=BuildStatus.FAILED,
            validation_status=ValidationStatus.FAILED,
            repair_attempts=0,
            max_repair_attempts=2,
            dry_run=True,  # Skip actual Claude Code
            static_check_results=[
                {"tool": "required_files", "success": False, "notes": ["Missing README.md"], "stdout": "", "stderr": ""}
            ],
            test_results=[
                {"tool": "pytest", "success": False, "stdout": "FAILED test_main.py", "stderr": ""}
            ],
        )
        return state

    def test_should_repair_when_failed(self, failed_poc_state):
        """Test that repair is triggered when validation fails."""
        from app.graph.edges.poc_edges import should_repair_or_continue

        result = should_repair_or_continue(failed_poc_state)
        assert result == "repair"

    def test_should_not_repair_after_max_attempts(self, failed_poc_state):
        """Test that repair is not triggered after max attempts."""
        from app.graph.edges.poc_edges import should_repair_or_continue

        failed_poc_state.repair_attempts = 2  # At max
        result = should_repair_or_continue(failed_poc_state)
        assert result == "continue"

    def test_repair_increments_attempt_count(self, tmp_output, failed_poc_state):
        """Test that repair increments the attempt counter."""
        from app.graph.nodes.poc_nodes import invoke_claude_code_repair

        with patch("app.config.get_settings") as mock_settings:
            settings = MagicMock()
            settings.claude_code_command = "claude"
            settings.claude_code_timeout_seconds = 60
            mock_settings.return_value = settings

            result = invoke_claude_code_repair(failed_poc_state)

        assert result.repair_attempts == 1

    def test_should_continue_after_passed_validation(self, failed_poc_state):
        """Test that we continue to markdown if validation passes."""
        from app.graph.edges.poc_edges import should_repair_or_continue

        failed_poc_state.validation_status = ValidationStatus.PASSED
        result = should_repair_or_continue(failed_poc_state)
        assert result == "continue"

    def test_assess_build_result_passed(self, failed_poc_state):
        """Test assessment when all checks pass."""
        from app.graph.nodes.poc_nodes import assess_build_result

        failed_poc_state.static_check_results = [
            {"tool": "required_files", "success": True, "notes": []},
            {"tool": "python_syntax", "success": True, "notes": []},
        ]
        failed_poc_state.test_results = [
            {"tool": "pytest", "success": True, "stdout": "passed"},
        ]

        result = assess_build_result(failed_poc_state)
        assert result.validation_status == ValidationStatus.PASSED

    def test_assess_build_result_failed(self, failed_poc_state):
        """Test assessment when checks fail."""
        from app.graph.nodes.poc_nodes import assess_build_result

        failed_poc_state.static_check_results = [
            {"tool": "required_files", "success": False, "notes": ["Missing README"]}
        ]
        failed_poc_state.test_results = [
            {"tool": "pytest", "success": False, "stdout": "FAILED"}
        ]

        result = assess_build_result(failed_poc_state)
        assert result.validation_status == ValidationStatus.FAILED
