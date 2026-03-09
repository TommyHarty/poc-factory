"""Validation service for generated POC repos."""

import ast
import sys
from datetime import datetime
from pathlib import Path

from app.domain.models.run import ValidationResult, ValidationSuite
from app.infrastructure.subprocess.runner import SubprocessRunner
from app.logging_config import get_logger

logger = get_logger(__name__)

REQUIRED_FILES = [
    "README.md",
    ".env.example",
]

# The starter repo uses pyproject.toml instead of requirements.txt,
# and app/ instead of src/ — so we check for those conventions.
REQUIRED_DIRS = [
    "tests",
    "app",
]


class PocValidator:
    """Runs validation checks on generated POC repos."""

    def __init__(self, subprocess_runner: SubprocessRunner) -> None:
        self.runner = subprocess_runner

    def validate(self, poc_folder: Path) -> ValidationSuite:
        """Run all validation checks and return a suite of results."""
        suite = ValidationSuite()

        # 1. Check required files
        file_result = self._check_required_files(poc_folder)
        suite.add_result(file_result)

        if file_result.notes:
            suite.missing_files = file_result.notes

        # 2. Python syntax check
        syntax_result = self._check_python_syntax(poc_folder)
        suite.add_result(syntax_result)

        # 3. Run tests
        test_result = self._run_tests(poc_folder)
        suite.add_result(test_result)

        suite.overall_passed = all(r.success for r in suite.results)
        suite.notes = self._collect_notes(suite)

        logger.info(
            "validation_complete",
            poc_folder=str(poc_folder),
            passed=suite.overall_passed,
            result_count=len(suite.results),
        )

        return suite

    def _check_required_files(self, poc_folder: Path) -> ValidationResult:
        """Check that required files and directories are present."""
        started_at = datetime.utcnow()
        missing = []

        for filename in REQUIRED_FILES:
            path = poc_folder / filename
            if not path.exists():
                missing.append(filename)

        for dirname in REQUIRED_DIRS:
            path = poc_folder / dirname
            if not path.exists():
                missing.append(f"{dirname}/")

        success = len(missing) == 0
        return ValidationResult(
            tool="required_files",
            success=success,
            stdout="All required files present" if success else f"Missing: {', '.join(missing)}",
            stderr="",
            exit_code=0 if success else 1,
            started_at=started_at,
            finished_at=datetime.utcnow(),
            notes=missing,
        )

    def _check_python_syntax(self, poc_folder: Path) -> ValidationResult:
        """Check Python files for syntax errors."""
        started_at = datetime.utcnow()
        errors = []

        python_files = list(poc_folder.rglob("*.py"))
        # Exclude hidden dirs and __pycache__
        python_files = [
            p for p in python_files
            if not any(part.startswith(".") or part == "__pycache__" for part in p.parts)
        ]

        for py_file in python_files:
            try:
                source = py_file.read_text(encoding="utf-8")
                ast.parse(source, filename=str(py_file))
            except SyntaxError as e:
                rel_path = py_file.relative_to(poc_folder)
                errors.append(f"{rel_path}: {e}")
            except Exception as e:
                rel_path = py_file.relative_to(poc_folder)
                errors.append(f"{rel_path}: {e}")

        success = len(errors) == 0
        return ValidationResult(
            tool="python_syntax",
            success=success,
            stdout=f"Checked {len(python_files)} Python files" if success else "",
            stderr="\n".join(errors),
            exit_code=0 if success else 1,
            started_at=started_at,
            finished_at=datetime.utcnow(),
            notes=errors,
        )

    def _run_tests(self, poc_folder: Path) -> ValidationResult:
        """Run pytest in the POC folder."""
        started_at = datetime.utcnow()

        tests_dir = poc_folder / "tests"
        if not tests_dir.exists():
            return ValidationResult(
                tool="pytest",
                success=False,
                stdout="",
                stderr="No tests directory found",
                exit_code=1,
                started_at=started_at,
                finished_at=datetime.utcnow(),
                notes=["Missing tests/ directory"],
            )

        # Check if there are any test files
        test_files = list(tests_dir.glob("test_*.py")) + list(tests_dir.glob("*_test.py"))
        if not test_files:
            return ValidationResult(
                tool="pytest",
                success=False,
                stdout="",
                stderr="No test files found in tests/",
                exit_code=1,
                started_at=started_at,
                finished_at=datetime.utcnow(),
                notes=["No test files found"],
            )

        result = self.runner.run(
            command=[sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short", "--no-header"],
            cwd=poc_folder,
            timeout=120,
        )

        return ValidationResult(
            tool="pytest",
            success=result.succeeded,
            stdout=result.stdout,
            stderr=result.stderr,
            exit_code=result.exit_code,
            started_at=started_at,
            finished_at=datetime.utcnow(),
        )

    def _check_imports(self, poc_folder: Path) -> ValidationResult:
        """Try to import key Python modules to detect missing dependencies."""
        started_at = datetime.utcnow()

        result = self.runner.run(
            command=[sys.executable, "-c", "import src; print('OK')"],
            cwd=poc_folder,
            timeout=30,
        )

        return ValidationResult(
            tool="import_check",
            success=result.succeeded,
            stdout=result.stdout,
            stderr=result.stderr,
            exit_code=result.exit_code,
            started_at=started_at,
            finished_at=datetime.utcnow(),
        )

    def _collect_notes(self, suite: ValidationSuite) -> list[str]:
        """Collect summary notes from validation results."""
        notes = []
        for result in suite.results:
            if not result.success:
                notes.append(f"{result.tool} failed: {result.stderr[:200]}")
        return notes

    def build_repair_context(self, suite: ValidationSuite) -> dict[str, list[str]]:
        """Extract actionable error info for repair prompts."""
        validation_errors = suite.missing_files

        static_errors = []
        for result in suite.results:
            if result.tool in ("python_syntax", "import_check") and not result.success:
                if result.notes:
                    static_errors.extend(result.notes)
                elif result.stderr:
                    static_errors.append(result.stderr[:500])

        test_errors = []
        for result in suite.results:
            if result.tool == "pytest" and not result.success:
                if result.stdout:
                    # Extract failure lines
                    lines = result.stdout.split("\n")
                    failure_lines = [l for l in lines if "FAILED" in l or "ERROR" in l or "error" in l.lower()]
                    test_errors.extend(failure_lines[:20])
                if result.stderr:
                    test_errors.append(result.stderr[:300])

        return {
            "validation_errors": validation_errors,
            "static_check_errors": static_errors,
            "test_errors": test_errors,
        }
