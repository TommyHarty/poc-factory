"""Shared pytest configuration and fixtures."""

import os
import tempfile
from pathlib import Path

import pytest

# Set test environment variables before importing anything
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("OUTPUT_ROOT", "/tmp/poc-factory-test-output")
os.environ.setdefault("WORK_ROOT", "/tmp/poc-factory-test-work")
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_poc_factory.db")


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture
def tmp_output_dir():
    """Provide a temporary output directory."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def tmp_work_dir():
    """Provide a temporary work directory."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)
