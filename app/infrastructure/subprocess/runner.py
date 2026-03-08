"""Generic subprocess runner for validation commands."""

import asyncio
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class SubprocessResult:
    """Result of running a subprocess command."""

    command: list[str]
    exit_code: int
    stdout: str
    stderr: str
    started_at: datetime
    finished_at: datetime
    timed_out: bool = False
    working_dir: Optional[str] = None

    @property
    def succeeded(self) -> bool:
        return self.exit_code == 0

    @property
    def duration_seconds(self) -> float:
        return (self.finished_at - self.started_at).total_seconds()


class SubprocessRunner:
    """Runs external commands with timeout and error handling."""

    def __init__(self, default_timeout: int = 120) -> None:
        self.default_timeout = default_timeout

    def run(
        self,
        command: list[str],
        cwd: Optional[Path] = None,
        timeout: Optional[int] = None,
        env: Optional[dict] = None,
        capture_output: bool = True,
    ) -> SubprocessResult:
        """Run a command synchronously."""
        started_at = datetime.utcnow()
        effective_timeout = timeout or self.default_timeout

        logger.debug("running_command", command=command[0], cwd=str(cwd) if cwd else None)

        try:
            result = subprocess.run(
                command,
                cwd=str(cwd) if cwd else None,
                capture_output=capture_output,
                text=True,
                timeout=effective_timeout,
                env=env,
            )
            finished_at = datetime.utcnow()
            return SubprocessResult(
                command=command,
                exit_code=result.returncode,
                stdout=result.stdout or "",
                stderr=result.stderr or "",
                started_at=started_at,
                finished_at=finished_at,
                working_dir=str(cwd) if cwd else None,
            )
        except subprocess.TimeoutExpired:
            finished_at = datetime.utcnow()
            logger.warning("command_timed_out", command=command[0])
            return SubprocessResult(
                command=command,
                exit_code=-1,
                stdout="",
                stderr=f"Command timed out after {effective_timeout}s",
                started_at=started_at,
                finished_at=finished_at,
                timed_out=True,
            )
        except FileNotFoundError:
            finished_at = datetime.utcnow()
            return SubprocessResult(
                command=command,
                exit_code=127,
                stdout="",
                stderr=f"Command not found: {command[0]}",
                started_at=started_at,
                finished_at=finished_at,
            )

    async def run_async(
        self,
        command: list[str],
        cwd: Optional[Path] = None,
        timeout: Optional[int] = None,
        env: Optional[dict] = None,
    ) -> SubprocessResult:
        """Run a command asynchronously."""
        started_at = datetime.utcnow()
        effective_timeout = timeout or self.default_timeout

        logger.debug("running_command_async", command=command[0])

        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                cwd=str(cwd) if cwd else None,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(), timeout=effective_timeout
                )
                exit_code = process.returncode or 0
                timed_out = False
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                stdout_bytes = b""
                stderr_bytes = f"Command timed out after {effective_timeout}s".encode()
                exit_code = -1
                timed_out = True

            finished_at = datetime.utcnow()
            return SubprocessResult(
                command=command,
                exit_code=exit_code,
                stdout=stdout_bytes.decode("utf-8", errors="replace"),
                stderr=stderr_bytes.decode("utf-8", errors="replace"),
                started_at=started_at,
                finished_at=finished_at,
                timed_out=timed_out,
                working_dir=str(cwd) if cwd else None,
            )

        except FileNotFoundError:
            finished_at = datetime.utcnow()
            return SubprocessResult(
                command=command,
                exit_code=127,
                stdout="",
                stderr=f"Command not found: {command[0]}",
                started_at=started_at,
                finished_at=finished_at,
            )
