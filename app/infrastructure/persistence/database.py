"""SQLite persistence layer using aiosqlite."""

import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator, Optional

import aiosqlite  # type: ignore[import-untyped]

from app.logging_config import get_logger

logger = get_logger(__name__)

DB_PATH = Path("./poc_factory.db")


def _json_default(obj: object) -> str:
    """JSON serializer for types not handled by default encoder."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)


@asynccontextmanager
async def get_db_connection(
    db_path: str = str(DB_PATH),
) -> AsyncGenerator[aiosqlite.Connection, None]:
    """Async context manager yielding a configured database connection."""
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA journal_mode=WAL")
        await conn.execute("PRAGMA foreign_keys=ON")
        yield conn


async def init_db(db_path: str = str(DB_PATH)) -> None:
    """Initialize the database schema."""
    async with get_db_connection(db_path) as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                phrase TEXT NOT NULL,
                normalized_phrase TEXT NOT NULL,
                slug TEXT NOT NULL,
                technologies TEXT NOT NULL DEFAULT '[]',
                optional_packages TEXT NOT NULL DEFAULT '[]',
                target_poc_count INTEGER NOT NULL DEFAULT 10,
                preferences TEXT NOT NULL DEFAULT '{}',
                starter_repo TEXT,
                output_root TEXT NOT NULL,
                run_status TEXT NOT NULL DEFAULT 'pending',
                errors TEXT NOT NULL DEFAULT '[]',
                warnings TEXT NOT NULL DEFAULT '[]',
                started_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                completed_at TEXT,
                dry_run INTEGER NOT NULL DEFAULT 0,
                full_state TEXT
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS poc_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                poc_index INTEGER NOT NULL,
                poc_slug TEXT NOT NULL,
                poc_title TEXT NOT NULL,
                poc_goal TEXT NOT NULL,
                folder_path TEXT,
                build_status TEXT NOT NULL DEFAULT 'pending',
                validation_status TEXT NOT NULL DEFAULT 'not_run',
                markdown_status TEXT NOT NULL DEFAULT 'pending',
                repair_attempts INTEGER NOT NULL DEFAULT 0,
                error_message TEXT,
                notes TEXT NOT NULL DEFAULT '[]',
                started_at TEXT,
                completed_at TEXT,
                full_state TEXT,
                FOREIGN KEY (run_id) REFERENCES runs(run_id)
            )
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_poc_executions_run_id
            ON poc_executions(run_id)
        """)

        await conn.commit()
        logger.info("database_initialized", path=db_path)


class RunRepository:
    """Repository for Run persistence."""

    def __init__(self, db_path: str = str(DB_PATH)) -> None:
        self.db_path = db_path

    async def save_run(self, run_data: dict) -> None:
        """Insert or update a run record."""
        async with get_db_connection(self.db_path) as conn:
            await conn.execute(
                """
                INSERT INTO runs (
                    run_id, phrase, normalized_phrase, slug,
                    technologies, optional_packages, target_poc_count,
                    preferences, starter_repo, output_root, run_status,
                    errors, warnings, started_at, updated_at, completed_at,
                    dry_run, full_state
                ) VALUES (
                    :run_id, :phrase, :normalized_phrase, :slug,
                    :technologies, :optional_packages, :target_poc_count,
                    :preferences, :starter_repo, :output_root, :run_status,
                    :errors, :warnings, :started_at, :updated_at, :completed_at,
                    :dry_run, :full_state
                )
                ON CONFLICT(run_id) DO UPDATE SET
                    run_status = excluded.run_status,
                    errors = excluded.errors,
                    warnings = excluded.warnings,
                    updated_at = excluded.updated_at,
                    completed_at = excluded.completed_at,
                    full_state = excluded.full_state
                """,
                {
                    "run_id": run_data["run_id"],
                    "phrase": run_data["phrase"],
                    "normalized_phrase": run_data.get("normalized_phrase", ""),
                    "slug": run_data.get("slug", ""),
                    "technologies": json.dumps(run_data.get("technologies", []), default=_json_default),
                    "optional_packages": json.dumps(run_data.get("optional_packages", []), default=_json_default),
                    "target_poc_count": run_data.get("target_poc_count", 10),
                    "preferences": json.dumps(run_data.get("preferences", {}), default=_json_default),
                    "starter_repo": json.dumps(run_data.get("starter_repo"), default=_json_default) if run_data.get("starter_repo") else None,
                    "output_root": run_data.get("output_root", "./output"),
                    "run_status": run_data.get("run_status", "pending"),
                    "errors": json.dumps(run_data.get("errors", []), default=_json_default),
                    "warnings": json.dumps(run_data.get("warnings", []), default=_json_default),
                    "started_at": run_data.get("started_at", datetime.now(timezone.utc).isoformat()),
                    "updated_at": run_data.get("updated_at", datetime.now(timezone.utc).isoformat()),
                    "completed_at": run_data.get("completed_at"),
                    "dry_run": 1 if run_data.get("dry_run") else 0,
                    "full_state": json.dumps(run_data, default=_json_default),
                },
            )
            await conn.commit()

    async def get_run(self, run_id: str) -> Optional[dict]:
        """Retrieve a run by ID."""
        async with get_db_connection(self.db_path) as conn:
            async with conn.execute(
                "SELECT * FROM runs WHERE run_id = ?", (run_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row is None:
                    return None
                data = dict(row)
                # Parse JSON fields
                for field in ["technologies", "optional_packages", "preferences", "errors", "warnings"]:
                    if data.get(field):
                        data[field] = json.loads(data[field])
                if data.get("starter_repo"):
                    data["starter_repo"] = json.loads(data["starter_repo"])
                if data.get("full_state"):
                    return json.loads(data["full_state"])
                return data

    async def list_runs(self, limit: int = 50, offset: int = 0) -> list[dict]:
        """List recent runs."""
        async with get_db_connection(self.db_path) as conn:
            async with conn.execute(
                "SELECT run_id, phrase, normalized_phrase, slug, run_status, started_at, completed_at "
                "FROM runs ORDER BY started_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def update_run_status(
        self,
        run_id: str,
        status: str,
        full_state: Optional[dict] = None,
    ) -> None:
        """Update run status."""
        async with get_db_connection(self.db_path) as conn:
            updated_at = datetime.now(timezone.utc).isoformat()
            completed_at = updated_at if status in ("completed", "failed", "partial") else None

            await conn.execute(
                """
                UPDATE runs SET run_status = ?, updated_at = ?, completed_at = ?,
                full_state = COALESCE(?, full_state)
                WHERE run_id = ?
                """,
                (status, updated_at, completed_at, json.dumps(full_state, default=_json_default) if full_state else None, run_id),
            )
            await conn.commit()

    async def save_poc_execution(self, run_id: str, poc_data: dict) -> None:
        """Insert or update a POC execution record."""
        async with get_db_connection(self.db_path) as conn:
            await conn.execute(
                """
                INSERT INTO poc_executions (
                    run_id, poc_index, poc_slug, poc_title, poc_goal,
                    folder_path, build_status, validation_status, markdown_status,
                    repair_attempts, error_message, notes, started_at, completed_at, full_state
                ) VALUES (
                    :run_id, :poc_index, :poc_slug, :poc_title, :poc_goal,
                    :folder_path, :build_status, :validation_status, :markdown_status,
                    :repair_attempts, :error_message, :notes, :started_at, :completed_at, :full_state
                )
                ON CONFLICT DO NOTHING
                """,
                {
                    "run_id": run_id,
                    "poc_index": poc_data.get("poc_index", 0),
                    "poc_slug": poc_data.get("poc_slug", ""),
                    "poc_title": poc_data.get("poc_title", ""),
                    "poc_goal": poc_data.get("poc_goal", ""),
                    "folder_path": poc_data.get("folder_path"),
                    "build_status": poc_data.get("build_status", "pending"),
                    "validation_status": poc_data.get("validation_status", "not_run"),
                    "markdown_status": poc_data.get("markdown_status", "pending"),
                    "repair_attempts": poc_data.get("repair_attempts", 0),
                    "error_message": poc_data.get("error_message"),
                    "notes": json.dumps(poc_data.get("notes", []), default=_json_default),
                    "started_at": poc_data.get("started_at"),
                    "completed_at": poc_data.get("completed_at"),
                    "full_state": json.dumps(poc_data, default=_json_default),
                },
            )
            await conn.commit()

    async def get_poc_executions(self, run_id: str) -> list[dict]:
        """Get all POC executions for a run."""
        async with get_db_connection(self.db_path) as conn:
            async with conn.execute(
                "SELECT * FROM poc_executions WHERE run_id = ? ORDER BY poc_index",
                (run_id,),
            ) as cursor:
                rows = await cursor.fetchall()
                result = []
                for row in rows:
                    data = dict(row)
                    if data.get("full_state"):
                        result.append(json.loads(data["full_state"]))
                    else:
                        result.append(data)
                return result
