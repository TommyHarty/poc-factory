"""Service for writing build reports and run summaries."""

import json
from datetime import datetime, timezone
from pathlib import Path

from app.domain.models.run import PocExecution, Run
from app.logging_config import get_logger

logger = get_logger(__name__)


class ReportWriter:
    """Writes JSON and markdown reports for runs and POCs."""

    def write_poc_build_report(
        self, poc: PocExecution, poc_folder: Path
    ) -> Path:
        """Write build-report.json for a single POC."""
        report = {
            "poc_slug": poc.poc_slug,
            "poc_title": poc.poc_title,
            "poc_goal": poc.poc_goal,
            "status": poc.build_status,
            "packages_used": poc.required_packages,
            "artifacts": [
                {
                    "type": a["type"] if isinstance(a, dict) else a.type,
                    "path": a["path"] if isinstance(a, dict) else a.path,
                }
                for a in poc.artifacts
            ],
            "validation": {
                "static_checks_passed": (
                    poc.static_check_results.overall_passed
                    if poc.static_check_results
                    else None
                ),
                "tests_passed": (
                    poc.test_results.overall_passed
                    if poc.test_results
                    else None
                ),
            },
            "repair_attempts": poc.repair_attempts,
            "error_message": poc.error_message,
            "notes": poc.notes,
            "started_at": poc.started_at.isoformat() if poc.started_at else None,
            "completed_at": poc.completed_at.isoformat() if poc.completed_at else None,
        }

        report_path = poc_folder / "build-report.json"
        report_path.write_text(json.dumps(report, indent=2, default=str))
        logger.info("wrote_build_report", path=str(report_path))
        return report_path

    def write_run_report(
        self, run: Run, run_output_path: Path
    ) -> Path:
        """Write run-report.json."""
        poc_summaries = []
        for poc in run.poc_executions:
            poc_summaries.append(
                {
                    "poc_slug": poc.poc_slug,
                    "poc_title": poc.poc_title,
                    "status": poc.build_status,
                    "validation_status": poc.validation_status,
                    "repair_attempts": poc.repair_attempts,
                    "markdown_status": poc.markdown_status,
                    "error_message": poc.error_message,
                }
            )

        completed_at = run.completed_at or datetime.now(timezone.utc)
        duration = (completed_at - run.started_at).total_seconds()

        report = {
            "run_id": str(run.run_id),
            "phrase": run.phrase,
            "normalized_phrase": run.normalized_phrase,
            "slug": run.slug,
            "status": run.run_status,
            "total_pocs": len(run.poc_executions),
            "completed_pocs": len(run.completed_pocs),
            "failed_pocs": len(run.failed_pocs),
            "poc_summaries": poc_summaries,
            "artifact_root": str(run.run_output_path),
            "started_at": run.started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "duration_seconds": duration,
            "errors": run.errors,
            "warnings": run.warnings,
        }

        report_path = run_output_path / "run-report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2, default=str))
        logger.info("wrote_run_report", path=str(report_path))
        return report_path

    def write_run_summary(
        self, run: Run, run_output_path: Path
    ) -> Path:
        """Write run-summary.md."""
        completed_at = run.completed_at or datetime.now(timezone.utc)
        duration = (completed_at - run.started_at).total_seconds()

        lines = [
            f"# Run Summary: {run.normalized_phrase}",
            "",
            f"**Run ID**: `{run.run_id}`",
            f"**Status**: {run.run_status}",
            f"**Started**: {run.started_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"**Duration**: {duration:.1f}s",
            "",
            "## Original Request",
            "",
            f"- **Phrase**: {run.phrase}",
            f"- **Normalized**: {run.normalized_phrase}",
            f"- **Technologies**: {', '.join(run.technologies) or 'none specified'}",
            f"- **Optional Packages**: {', '.join(run.optional_packages) or 'none'}",
            f"- **Target POC Count**: {run.target_poc_count}",
            "",
            "## Selected POCs",
            "",
        ]

        for poc in run.selected_pocs:
            lines.append(f"### {poc.index}. {poc.title}")
            lines.append(f"- **Slug**: `{poc.slug}`")
            lines.append(f"- **Goal**: {poc.goal}")
            lines.append("")

        lines += [
            "## POC Build Results",
            "",
            "| POC | Status | Validation | Repairs | Markdown |",
            "| --- | ------ | ---------- | ------- | -------- |",
        ]

        for poc in run.poc_executions:
            lines.append(
                f"| {poc.poc_slug} | {poc.build_status} | {poc.validation_status} "
                f"| {poc.repair_attempts} | {poc.markdown_status} |"
            )

        lines += [
            "",
            "## Summary",
            "",
            f"- **Total POCs**: {len(run.poc_executions)}",
            f"- **Completed**: {len(run.completed_pocs)}",
            f"- **Failed**: {len(run.failed_pocs)}",
            f"- **Artifact Root**: `{run.run_output_path}`",
            "",
        ]

        if run.errors:
            lines += ["## Errors", ""]
            for err in run.errors:
                lines.append(f"- {err}")
            lines.append("")

        if run.warnings:
            lines += ["## Warnings", ""]
            for warn in run.warnings:
                lines.append(f"- {warn}")
            lines.append("")

        content = "\n".join(lines)
        summary_path = run_output_path / "run-summary.md"
        summary_path.write_text(content, encoding="utf-8")
        logger.info("wrote_run_summary", path=str(summary_path))
        return summary_path
