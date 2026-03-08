"""Claude Code runner adapter for programmatic invocation."""

import asyncio
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class ClaudeCodeExecutionResult:
    """Result of a Claude Code invocation."""

    command: str
    working_directory: str
    exit_code: int
    stdout: str
    stderr: str
    started_at: datetime
    finished_at: datetime
    timed_out: bool = False
    prompt_file: Optional[str] = None
    prompt_text: Optional[str] = None
    notes: list[str] = field(default_factory=list)

    @property
    def succeeded(self) -> bool:
        return self.exit_code == 0 and not self.timed_out

    @property
    def duration_seconds(self) -> float:
        return (self.finished_at - self.started_at).total_seconds()


class ClaudeCodeRunner:
    """Runs Claude Code programmatically against a POC folder.

    Claude Code is invoked as a subprocess, passing the CLAUDE.md file
    as the prompt. The runner captures all output and enforces timeouts.
    """

    def __init__(
        self,
        command: str = "claude",
        timeout_seconds: int = 300,
        max_retries: int = 2,
    ) -> None:
        self.command = command
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    def build_command(self, poc_folder: Path, prompt: Optional[str] = None) -> list[str]:
        """Build the command list for Claude Code invocation.

        Claude Code CLI: claude --print --no-sandbox -p <prompt>
        or with the CLAUDE.md as instructions, navigate to folder.
        """
        cmd = [
            self.command,
            "--print",                         # Non-interactive output mode
            "--dangerously-skip-permissions",  # Skip permission prompts
        ]
        if prompt:
            cmd += ["-p", prompt]
        return cmd

    async def run(
        self,
        poc_folder: Path,
        prompt: str,
        prompt_file: Optional[Path] = None,
    ) -> ClaudeCodeExecutionResult:
        """Execute Claude Code in the given folder with the given prompt."""
        started_at = datetime.utcnow()

        cmd = self.build_command(poc_folder, prompt=prompt)
        cmd_str = " ".join(cmd[:3]) + " ..."  # Safe truncated version for logging

        logger.info(
            "invoking_claude_code",
            poc_folder=str(poc_folder),
            command=cmd_str,
            timeout=self.timeout_seconds,
        )

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(poc_folder),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=self._build_env(),
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout_seconds,
                )
                exit_code = process.returncode or 0
                timed_out = False
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                stdout_bytes = b""
                stderr_bytes = b"Process timed out"
                exit_code = -1
                timed_out = True
                logger.warning("claude_code_timed_out", folder=str(poc_folder))

            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")
            finished_at = datetime.utcnow()

            result = ClaudeCodeExecutionResult(
                command=cmd_str,
                working_directory=str(poc_folder),
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                started_at=started_at,
                finished_at=finished_at,
                timed_out=timed_out,
                prompt_file=str(prompt_file) if prompt_file else None,
                prompt_text=prompt[:500] + "..." if len(prompt) > 500 else prompt,
            )

            # Persist logs
            self._persist_logs(poc_folder, result)

            if result.succeeded:
                logger.info(
                    "claude_code_succeeded",
                    folder=str(poc_folder),
                    duration=result.duration_seconds,
                )
            else:
                logger.warning(
                    "claude_code_failed",
                    folder=str(poc_folder),
                    exit_code=exit_code,
                    timed_out=timed_out,
                )

            return result

        except FileNotFoundError:
            # Claude Code not installed
            finished_at = datetime.utcnow()
            logger.error("claude_code_not_found", command=self.command)
            return ClaudeCodeExecutionResult(
                command=cmd_str,
                working_directory=str(poc_folder),
                exit_code=127,
                stdout="",
                stderr=f"Command not found: {self.command}. Is Claude Code installed?",
                started_at=started_at,
                finished_at=finished_at,
                timed_out=False,
                notes=["Claude Code binary not found"],
            )

    def run_sync(
        self,
        poc_folder: Path,
        prompt: str,
        prompt_file: Optional[Path] = None,
    ) -> ClaudeCodeExecutionResult:
        """Synchronous version of run() for use in non-async contexts."""
        started_at = datetime.utcnow()
        cmd = self.build_command(poc_folder, prompt=prompt)
        cmd_str = " ".join(cmd[:3]) + " ..."

        logger.info(
            "invoking_claude_code_sync",
            poc_folder=str(poc_folder),
            command=cmd_str,
        )

        try:
            result = subprocess.run(
                cmd,
                cwd=str(poc_folder),
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                env=self._build_env(),
            )
            finished_at = datetime.utcnow()

            exec_result = ClaudeCodeExecutionResult(
                command=cmd_str,
                working_directory=str(poc_folder),
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                started_at=started_at,
                finished_at=finished_at,
                timed_out=False,
                prompt_file=str(prompt_file) if prompt_file else None,
            )
            self._persist_logs(poc_folder, exec_result)
            return exec_result

        except subprocess.TimeoutExpired:
            finished_at = datetime.utcnow()
            return ClaudeCodeExecutionResult(
                command=cmd_str,
                working_directory=str(poc_folder),
                exit_code=-1,
                stdout="",
                stderr="Process timed out",
                started_at=started_at,
                finished_at=finished_at,
                timed_out=True,
            )

        except FileNotFoundError:
            finished_at = datetime.utcnow()
            return ClaudeCodeExecutionResult(
                command=cmd_str,
                working_directory=str(poc_folder),
                exit_code=127,
                stdout="",
                stderr=f"Command not found: {self.command}",
                started_at=started_at,
                finished_at=finished_at,
                timed_out=False,
            )

    def _build_env(self) -> dict:
        """Build the environment for subprocess execution."""
        import os
        env = os.environ.copy()
        return env

    def _persist_logs(self, poc_folder: Path, result: ClaudeCodeExecutionResult) -> None:
        """Write execution logs to work/logs/<poc_folder_name>/, outside the POC folder."""
        from app.config import get_settings
        settings = get_settings()
        logs_dir = settings.work_root / "logs" / poc_folder.name
        logs_dir.mkdir(parents=True, exist_ok=True)

        timestamp = result.started_at.strftime("%Y%m%d_%H%M%S")
        log_file = logs_dir / f"claude_code_{timestamp}.log"

        content = f"""=== Claude Code Execution Log ===
Command: {result.command}
Directory: {result.working_directory}
Exit Code: {result.exit_code}
Duration: {result.duration_seconds:.1f}s
Timed Out: {result.timed_out}
Started: {result.started_at.isoformat()}
Finished: {result.finished_at.isoformat()}

=== STDOUT ===
{result.stdout}

=== STDERR ===
{result.stderr}
"""
        try:
            log_file.write_text(content)
        except Exception as e:
            logger.warning("failed_to_persist_log", error=str(e))


class ClaudeCodePromptBuilder:
    """Builds prompts for Claude Code invocations."""

    @staticmethod
    def build_repair_prompt(
        poc_slug: str,
        validation_errors: list[str],
        static_check_errors: list[str],
        test_errors: list[str],
    ) -> str:
        """Build a focused repair prompt for failed validation."""
        lines = [
            f"# Repair Instructions for {poc_slug}",
            "",
            "The POC build has issues that need to be fixed. Please address the following specific problems:",
            "",
        ]

        if validation_errors:
            lines.append("## Validation Issues")
            for err in validation_errors:
                lines.append(f"- {err}")
            lines.append("")

        if static_check_errors:
            lines.append("## Static Check / Import Errors")
            for err in static_check_errors:
                lines.append(f"- {err}")
            lines.append("")

        if test_errors:
            lines.append("## Test Failures")
            for err in test_errors:
                lines.append(f"- {err}")
            lines.append("")

        lines += [
            "## Instructions",
            "- Fix ONLY the issues listed above",
            "- Do not regenerate the entire repo",
            "- Do not change the overall approach or architecture",
            "- Ensure all tests pass after your fix",
            "- Ensure all imports resolve",
            "- Keep changes minimal and targeted",
        ]

        return "\n".join(lines)
