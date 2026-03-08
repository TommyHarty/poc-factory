"""Unit tests for report generation."""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pytest

from app.application.services.report_writer import ReportWriter
from app.domain.models.run import (
    BuildStatus,
    PocExecution,
    PocPlan,
    Run,
    RunStatus,
    ValidationStatus,
)


def make_run(pocs: list[PocExecution]) -> Run:
    return Run(
        run_id=uuid4(),
        phrase="test phrase",
        normalized_phrase="test phrase",
        slug="test-phrase",
        technologies=["fastapi"],
        poc_executions=pocs,
        selected_pocs=[],
        run_status=RunStatus.COMPLETED,
        started_at=datetime(2024, 1, 1, 12, 0, 0),
        completed_at=datetime(2024, 1, 1, 12, 30, 0),
    )


def make_poc(
    index: int = 1,
    title: str = "Test POC",
    status: BuildStatus = BuildStatus.SUCCEEDED,
) -> PocExecution:
    return PocExecution(
        poc_index=index,
        poc_title=title,
        poc_slug=f"{index:02d}-test-poc",
        poc_goal="Test goal",
        why_it_matters="Matters",
        build_status=status,
        validation_status=ValidationStatus.PASSED if status == BuildStatus.SUCCEEDED else ValidationStatus.FAILED,
        folder_path=f"/tmp/test/{index:02d}-test-poc",
    )


class TestReportWriter:
    @pytest.fixture
    def writer(self):
        return ReportWriter()

    @pytest.fixture
    def tmp_dir(self):
        with tempfile.TemporaryDirectory() as d:
            yield Path(d)

    def test_write_poc_build_report(self, writer, tmp_dir):
        poc = make_poc()
        report_path = writer.write_poc_build_report(poc, tmp_dir)
        assert report_path.exists()
        data = json.loads(report_path.read_text())
        assert data["poc_slug"] == "01-test-poc"
        assert data["status"] == BuildStatus.SUCCEEDED

    def test_poc_build_report_includes_repair_info(self, writer, tmp_dir):
        poc = make_poc()
        poc.repair_attempts = [{"attempt_number": 1, "succeeded": True}]
        report_path = writer.write_poc_build_report(poc, tmp_dir)
        data = json.loads(report_path.read_text())
        # repair_attempts is a list or count
        assert "repair_attempts" in data

    def test_write_run_report(self, writer, tmp_dir):
        pocs = [
            make_poc(1, "POC One", BuildStatus.SUCCEEDED),
            make_poc(2, "POC Two", BuildStatus.FAILED),
        ]
        run = make_run(pocs)
        report_path = writer.write_run_report(run, tmp_dir)
        assert report_path.exists()
        data = json.loads(report_path.read_text())
        assert data["total_pocs"] == 2
        assert data["completed_pocs"] == 1
        assert data["failed_pocs"] == 1

    def test_write_run_report_fields(self, writer, tmp_dir):
        run = make_run([make_poc()])
        report_path = writer.write_run_report(run, tmp_dir)
        data = json.loads(report_path.read_text())
        assert "run_id" in data
        assert "phrase" in data
        assert "started_at" in data
        assert "duration_seconds" in data

    def test_write_run_summary_markdown(self, writer, tmp_dir):
        pocs = [make_poc(1), make_poc(2)]
        run = make_run(pocs)
        summary_path = writer.write_run_summary(run, tmp_dir)
        assert summary_path.exists()
        content = summary_path.read_text()
        assert "# Run Summary" in content
        assert "test phrase" in content

    def test_run_summary_contains_poc_table(self, writer, tmp_dir):
        pocs = [make_poc(1), make_poc(2)]
        run = make_run(pocs)
        summary_path = writer.write_run_summary(run, tmp_dir)
        content = summary_path.read_text()
        assert "01-test-poc" in content

    def test_run_duration_calculated(self, writer, tmp_dir):
        run = make_run([make_poc()])
        report_path = writer.write_run_report(run, tmp_dir)
        data = json.loads(report_path.read_text())
        assert data["duration_seconds"] == 1800.0  # 30 minutes
