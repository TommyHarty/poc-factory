"""Unit tests for domain models."""

import pytest
from datetime import datetime
from uuid import uuid4

from app.domain.models.run import (
    ArtifactMetadata,
    ArtifactType,
    BuildStatus,
    GenerationPreferences,
    PocExecution,
    PocPlan,
    RepairAttempt,
    Run,
    RunStatus,
    StarterRepoSource,
    ValidationResult,
    ValidationSuite,
)


class TestStarRepoSource:
    def test_safe_url_masks_token(self):
        source = StarterRepoSource(
            repo_url="https://ghp_secret123@github.com/org/repo.git",
            branch="main",
        )
        assert "ghp_secret123" not in source.safe_url
        assert "github.com" in source.safe_url

    def test_safe_url_no_token(self):
        source = StarterRepoSource(
            repo_url="https://github.com/org/repo.git",
            branch="main",
        )
        assert source.safe_url == "https://github.com/org/repo.git"


class TestGenerationPreferences:
    def test_defaults(self):
        prefs = GenerationPreferences()
        assert prefs.use_pytest is True
        assert prefs.prefer_mocks is True
        assert prefs.use_docker is False


class TestValidationSuite:
    def test_add_result_updates_overall(self):
        suite = ValidationSuite()
        suite.add_result(ValidationResult(tool="test", success=True, exit_code=0))
        assert suite.overall_passed is True

    def test_one_failure_fails_suite(self):
        suite = ValidationSuite()
        suite.add_result(ValidationResult(tool="check1", success=True, exit_code=0))
        suite.add_result(ValidationResult(tool="check2", success=False, exit_code=1))
        assert suite.overall_passed is False

    def test_missing_files_tracked(self):
        suite = ValidationSuite(missing_files=["README.md", "tests/"])
        assert "README.md" in suite.missing_files


class TestPocPlan:
    def test_basic_creation(self):
        poc = PocPlan(
            index=1,
            title="Test POC",
            slug="01-test-poc",
            goal="Build something",
            why_it_matters="Because it matters",
        )
        assert poc.slug == "01-test-poc"

    def test_optional_fields_have_defaults(self):
        poc = PocPlan(index=1, title="T", slug="01-t", goal="G")
        assert poc.scope_boundaries == []
        assert poc.required_packages == []


class TestPocExecution:
    def test_repair_count_property(self):
        poc = PocExecution(
            poc_index=1,
            poc_title="T",
            poc_slug="01-t",
            poc_goal="G",
        )
        assert poc.repair_count == 0

    def test_is_complete_when_succeeded(self):
        poc = PocExecution(
            poc_index=1,
            poc_title="T",
            poc_slug="01-t",
            poc_goal="G",
            build_status=BuildStatus.SUCCEEDED,
        )
        assert poc.is_complete is True

    def test_is_not_complete_when_pending(self):
        poc = PocExecution(
            poc_index=1,
            poc_title="T",
            poc_slug="01-t",
            poc_goal="G",
            build_status=BuildStatus.PENDING,
        )
        assert poc.is_complete is False


class TestRun:
    def test_run_output_path(self):
        run = Run(
            phrase="test",
            normalized_phrase="test",
            slug="test",
            output_root="/output",
        )
        assert str(run.run_output_path) == "/output/test"

    def test_completed_pocs(self):
        run = Run(phrase="test", output_root="/output")
        run.poc_executions = [
            PocExecution(poc_index=1, poc_title="A", poc_slug="01-a", poc_goal="G",
                        build_status=BuildStatus.SUCCEEDED),
            PocExecution(poc_index=2, poc_title="B", poc_slug="02-b", poc_goal="G",
                        build_status=BuildStatus.FAILED),
        ]
        assert len(run.completed_pocs) == 1
        assert len(run.failed_pocs) == 1
