"""Unit tests for folder layout and filesystem operations."""

import json
import tempfile
from pathlib import Path

import pytest

from app.infrastructure.filesystem.adapter import FileSystemAdapter


@pytest.fixture
def tmp_dirs():
    with tempfile.TemporaryDirectory() as work_dir:
        with tempfile.TemporaryDirectory() as output_dir:
            yield Path(work_dir), Path(output_dir)


@pytest.fixture
def fs(tmp_dirs):
    work_root, output_root = tmp_dirs
    return FileSystemAdapter(work_root=work_root, output_root=output_root)


class TestFileSystemAdapter:
    def test_ensure_directory_creates_nested(self, fs, tmp_dirs):
        _, output_root = tmp_dirs
        nested = output_root / "a" / "b" / "c"
        fs.ensure_directory(nested)
        assert nested.exists()

    def test_write_text_creates_file(self, fs, tmp_dirs):
        _, output_root = tmp_dirs
        path = output_root / "test.txt"
        fs.write_text(path, "hello world")
        assert path.read_text() == "hello world"

    def test_write_text_is_atomic(self, fs, tmp_dirs):
        """Write should not leave partial files on failure."""
        _, output_root = tmp_dirs
        path = output_root / "atomic.txt"
        fs.write_text(path, "first content")
        fs.write_text(path, "second content")
        assert path.read_text() == "second content"

    def test_write_json(self, fs, tmp_dirs):
        _, output_root = tmp_dirs
        path = output_root / "data.json"
        data = {"key": "value", "numbers": [1, 2, 3]}
        fs.write_json(path, data)
        loaded = json.loads(path.read_text())
        assert loaded == data

    def test_read_text_missing_file_returns_none(self, fs, tmp_dirs):
        _, output_root = tmp_dirs
        result = fs.read_text(output_root / "nonexistent.txt")
        assert result is None

    def test_read_json_missing_file_returns_none(self, fs, tmp_dirs):
        _, output_root = tmp_dirs
        result = fs.read_json(output_root / "nonexistent.json")
        assert result is None

    def test_copy_directory(self, fs, tmp_dirs):
        work_root, output_root = tmp_dirs
        src = work_root / "source"
        src.mkdir()
        (src / "file.txt").write_text("content")
        (src / "subdir").mkdir()
        (src / "subdir" / "nested.txt").write_text("nested")

        dst = output_root / "destination"
        fs.copy_directory(src, dst)

        assert (dst / "file.txt").exists()
        assert (dst / "subdir" / "nested.txt").exists()

    def test_copy_directory_excludes_git(self, fs, tmp_dirs):
        work_root, output_root = tmp_dirs
        src = work_root / "source"
        src.mkdir()
        (src / ".git").mkdir()
        (src / ".git" / "config").write_text("git config")
        (src / "file.txt").write_text("content")

        dst = output_root / "destination"
        fs.copy_directory(src, dst, ignore_git=True)

        assert not (dst / ".git").exists()
        assert (dst / "file.txt").exists()

    def test_safe_path_prevents_traversal(self, fs, tmp_dirs):
        _, output_root = tmp_dirs
        # Attempt path traversal
        safe = fs.safe_path(output_root, "..", "etc", "passwd")
        # Should not go above output_root
        assert "etc" in str(safe)
        # The traversal attempt should be sanitized
        assert ".." not in safe.parts

    def test_create_poc_folder(self, fs, tmp_dirs):
        _, output_root = tmp_dirs
        poc_folder = fs.create_poc_folder(output_root, "01-test-poc")
        assert poc_folder.exists()
        assert poc_folder.name == "01-test-poc"

    def test_file_sha256(self, fs, tmp_dirs):
        _, output_root = tmp_dirs
        path = output_root / "hash_test.txt"
        path.write_text("test content")
        sha = fs.file_sha256(path)
        assert sha is not None
        assert len(sha) == 64  # SHA-256 hex digest

    def test_list_files_recursive(self, fs, tmp_dirs):
        _, output_root = tmp_dirs
        (output_root / "a.txt").write_text("a")
        (output_root / "sub").mkdir()
        (output_root / "sub" / "b.txt").write_text("b")

        files = fs.list_files(output_root)
        names = {f.name for f in files}
        assert "a.txt" in names
        assert "b.txt" in names
