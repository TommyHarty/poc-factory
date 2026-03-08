"""Filesystem adapter with safe file operations."""

import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Optional

import aiofiles
import aiofiles.os

from app.logging_config import get_logger

logger = get_logger(__name__)


class FileSystemAdapter:
    """Safe filesystem operations for POC Factory."""

    def __init__(self, work_root: Path, output_root: Path) -> None:
        self.work_root = work_root
        self.output_root = output_root

    def ensure_directory(self, path: Path) -> None:
        """Create directory and all parents if they don't exist."""
        path.mkdir(parents=True, exist_ok=True)
        logger.debug("ensured_directory", path=str(path))

    async def ensure_directory_async(self, path: Path) -> None:
        """Async version of ensure_directory."""
        await aiofiles.os.makedirs(str(path), exist_ok=True)

    def write_text(self, path: Path, content: str, encoding: str = "utf-8") -> None:
        """Write text to a file atomically."""
        self.ensure_directory(path.parent)
        # Write to temp file first, then rename (atomic on same filesystem)
        tmp_fd, tmp_path = tempfile.mkstemp(dir=path.parent, prefix=".tmp_")
        try:
            with os.fdopen(tmp_fd, "w", encoding=encoding) as f:
                f.write(content)
            os.replace(tmp_path, path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
        logger.debug("wrote_file", path=str(path), size=len(content))

    async def write_text_async(self, path: Path, content: str, encoding: str = "utf-8") -> None:
        """Write text to a file asynchronously."""
        await self.ensure_directory_async(path.parent)
        async with aiofiles.open(str(path), "w", encoding=encoding) as f:
            await f.write(content)

    def write_json(self, path: Path, data: Any, indent: int = 2) -> None:
        """Write JSON data to a file atomically."""
        content = json.dumps(data, indent=indent, default=str)
        self.write_text(path, content)

    async def write_json_async(self, path: Path, data: Any, indent: int = 2) -> None:
        """Write JSON data async."""
        content = json.dumps(data, indent=indent, default=str)
        await self.write_text_async(path, content)

    def read_text(self, path: Path, encoding: str = "utf-8") -> Optional[str]:
        """Read text from a file, returning None if not found."""
        try:
            return path.read_text(encoding=encoding)
        except FileNotFoundError:
            return None

    def read_json(self, path: Path) -> Optional[Any]:
        """Read JSON from a file, returning None if not found."""
        content = self.read_text(path)
        if content is None:
            return None
        return json.loads(content)

    def copy_directory(
        self,
        src: Path,
        dst: Path,
        exclude: Optional[list[str]] = None,
        ignore_git: bool = True,
    ) -> None:
        """Copy a directory tree, excluding specified patterns."""
        exclude = exclude or []
        if ignore_git:
            exclude.append(".git")

        def ignore_fn(directory: str, contents: list[str]) -> list[str]:
            ignored = []
            for item in contents:
                if item in exclude:
                    ignored.append(item)
            return ignored

        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(str(src), str(dst), ignore=ignore_fn)
        logger.info("copied_directory", src=str(src), dst=str(dst))

    def file_sha256(self, path: Path) -> Optional[str]:
        """Compute SHA-256 hash of a file."""
        if not path.exists():
            return None
        sha = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha.update(chunk)
        return sha.hexdigest()

    def file_size(self, path: Path) -> Optional[int]:
        """Return file size in bytes."""
        try:
            return path.stat().st_size
        except FileNotFoundError:
            return None

    def list_files(self, path: Path, recursive: bool = True) -> list[Path]:
        """List all files in a directory."""
        if not path.exists():
            return []
        if recursive:
            return [p for p in path.rglob("*") if p.is_file()]
        return [p for p in path.iterdir() if p.is_file()]

    def delete_directory(self, path: Path) -> None:
        """Delete a directory tree safely."""
        if path.exists() and path.is_dir():
            shutil.rmtree(str(path))

    def safe_path(self, base: Path, *parts: str) -> Path:
        """Build a path that is guaranteed to be within base."""
        candidate = base
        for part in parts:
            # Remove any path traversal attempts
            clean = part.replace("..", "").replace("/", "-").replace("\\", "-")
            candidate = candidate / clean
        return candidate

    def create_poc_folder(self, run_output_path: Path, poc_slug: str) -> Path:
        """Create a dedicated folder for a POC under the run output path."""
        poc_path = run_output_path / poc_slug
        self.ensure_directory(poc_path)
        return poc_path
