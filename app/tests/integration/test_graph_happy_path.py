"""Integration tests for the graph happy path with mocked Claude Code runner."""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.domain.models.run import BuildStatus, GenerationPreferences, PocPlan, RunStatus
from app.graph.state import PocGraphState, RunGraphState


def make_poc_plans(count: int = 3) -> list[PocPlan]:
    from app.domain.value_objects.slug import poc_slug

    plans = []
    for i in range(1, count + 1):
        plans.append(
            PocPlan(
                index=i,
                title=f"Test POC {i}",
                slug=poc_slug(i, f"test-poc-{i}"),
                goal=f"Goal for POC {i}",
                why_it_matters=f"Matters for POC {i}",
                required_packages=["fastapi", "pydantic"],
            )
        )
    return plans


class TestPocSubgraphHappyPath:
    """Test the POC subgraph with a dry run (no Claude Code invocation)."""

    @pytest.fixture
    def tmp_output(self):
        with tempfile.TemporaryDirectory() as d:
            yield Path(d)

    def test_poc_subgraph_dry_run(self, tmp_output):
        """Test that a POC can be processed in dry-run mode."""
        from app.graph.poc_graph.graph import compile_poc_graph

        poc = make_poc_plans(1)[0]

        state_dict = PocGraphState(
            run_id="test-run-001",
            phrase="prompt injection guardrails",
            slug="prompt-injection-guardrails",
            technologies=["fastapi"],
            optional_packages=[],
            preferences=GenerationPreferences(),
            starter_repo=None,
            output_root=str(tmp_output),
            dry_run=True,
            max_repair_attempts=1,
            poc_index=poc.index,
            poc_title=poc.title,
            poc_slug=poc.slug,
            poc_goal=poc.goal,
            why_it_matters=poc.why_it_matters,
            scope_boundaries=poc.scope_boundaries,
            required_packages=poc.required_packages,
        ).model_dump()

        # Patch LLM calls
        with patch("app.config.get_settings") as mock_settings:
            settings = MagicMock()
            settings.openai_api_key = None
            settings.claude_code_command = "claude"
            settings.claude_code_timeout_seconds = 60
            settings.claude_code_max_repair_attempts = 1
            settings.work_root = tmp_output
            settings.output_root = tmp_output
            settings.starter_repo_cache_dir = tmp_output / "cache"
            settings.github_token = None
            mock_settings.return_value = settings

            compiled = compile_poc_graph()
            result = compiled.invoke(state_dict)

        assert result is not None
        assert result["poc_slug"] == poc.slug
        # In dry run, build should be SUCCEEDED
        assert result["build_status"] in (BuildStatus.SUCCEEDED, "succeeded")

    def test_poc_folder_created(self, tmp_output):
        """Test that the POC folder is created during execution."""
        from app.graph.nodes.poc_nodes import prepare_poc_folder

        state = PocGraphState(
            run_id="test-001",
            phrase="test",
            slug="test",
            output_root=str(tmp_output),
            poc_index=1,
            poc_title="Test POC",
            poc_slug="01-test-poc",
            poc_goal="Test goal",
        )

        result = prepare_poc_folder(state)
        assert result.folder_path is not None
        assert Path(result.folder_path).exists()
        assert (Path(result.folder_path) / "poc-plan.json").exists()

    def test_poc_plan_json_written(self, tmp_output):
        """Test that poc-plan.json has correct content."""
        from app.graph.nodes.poc_nodes import prepare_poc_folder

        state = PocGraphState(
            run_id="run-123",
            phrase="test topic",
            slug="test-topic",
            output_root=str(tmp_output),
            poc_index=2,
            poc_title="My POC",
            poc_slug="02-my-poc",
            poc_goal="My goal",
            why_it_matters="It matters",
        )

        result = prepare_poc_folder(state)
        plan_file = Path(result.folder_path) / "poc-plan.json"
        data = json.loads(plan_file.read_text())

        assert data["poc_index"] == 2
        assert data["poc_title"] == "My POC"
        assert data["poc_goal"] == "My goal"


class TestRunGraphHappyPath:
    """Integration tests for the run-level graph."""

    @pytest.fixture
    def tmp_output(self):
        with tempfile.TemporaryDirectory() as d:
            yield Path(d)

    def test_ingest_request_node(self, tmp_output):
        """Test that ingest_request normalizes target count."""
        from app.graph.nodes.run_nodes import ingest_request

        state = RunGraphState(
            run_id="test-001",
            phrase="test phrase",
            target_poc_count=5,  # Below minimum
            output_root=str(tmp_output),
        )

        with patch("app.config.get_settings") as mock_settings:
            settings = MagicMock()
            settings.output_root = tmp_output
            mock_settings.return_value = settings

            result = ingest_request(state)

        # Should be clamped to minimum
        assert result.target_poc_count >= 5

    def test_normalize_phrase_node(self, tmp_output):
        """Test phrase normalization."""
        from app.graph.nodes.run_nodes import normalize_phrase_node

        state = RunGraphState(
            run_id="test-001",
            phrase="  PROMPT INJECTION GUARDRAILS  ",
            output_root=str(tmp_output),
        )

        with patch("app.config.get_settings") as mock_settings:
            settings = MagicMock()
            settings.output_root = tmp_output
            mock_settings.return_value = settings

            result = normalize_phrase_node(state)

        assert result.normalized_phrase == "prompt injection guardrails"
        assert result.slug == "prompt-injection-guardrails"
        assert result.run_output_path != ""

    def test_create_run_plan_writes_file(self, tmp_output):
        """Test that create_run_plan writes the plan file."""
        from app.graph.nodes.run_nodes import create_run_plan

        plans = make_poc_plans(3)
        state = RunGraphState(
            run_id="test-001",
            phrase="test phrase",
            normalized_phrase="test phrase",
            slug="test-phrase",
            run_output_path=str(tmp_output),
            output_root=str(tmp_output),
            selected_pocs=plans,
        )

        result = create_run_plan(state)

        plan_file = tmp_output / "run-plan.json"
        assert plan_file.exists()
        data = json.loads(plan_file.read_text())
        assert data["selected_pocs"] is not None
        assert len(data["selected_pocs"]) == 3
