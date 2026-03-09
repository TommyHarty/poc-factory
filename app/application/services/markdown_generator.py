"""Service for generating prose and code walkthrough markdown files."""

from pathlib import Path

from app.application.services.prompt_loader import PromptLoader
from app.domain.models.run import PocExecution, PocPlan
from app.infrastructure.llm.adapter import LLMAdapter
from app.logging_config import get_logger

logger = get_logger(__name__)

MAX_FILE_CONTENT_CHARS_PROSE = 2000    # For prose chapter (just for context)
MAX_FILE_CONTENT_CHARS_WALKTHROUGH = 6000  # For code walkthrough (needs full code)
MAX_FILES_PROSE = 5
MAX_FILES_WALKTHROUGH = 20


class MarkdownGenerator:
    """Generates prose and implementation walkthrough markdown for POCs."""

    def __init__(self, llm: LLMAdapter, prompt_loader: PromptLoader) -> None:
        self.llm = llm
        self.prompt_loader = prompt_loader

    def generate_prose_chapter(
        self,
        poc: PocPlan,
        phrase: str,
        poc_folder: Path,
    ) -> str:
        """Generate a prose teaching chapter for the POC."""
        repo_structure = self._get_repo_structure(poc_folder)
        key_files = self._get_key_files_content(
            poc_folder,
            max_files=MAX_FILES_PROSE,
            max_chars=MAX_FILE_CONTENT_CHARS_PROSE,
        )

        prompt = self.prompt_loader.render(
            "prose_markdown_generation_prompt.md",
            {
                "phrase": phrase,
                "poc_title": poc.title,
                "poc_slug": poc.slug,
                "poc_goal": poc.goal,
                "why_it_matters": poc.why_it_matters,
                "required_packages": poc.required_packages,
                "scope_boundaries": poc.scope_boundaries,
                "repo_structure": repo_structure,
                "key_files": key_files,
            },
        )

        logger.info("generating_prose_markdown", poc_slug=poc.slug)

        content = self.llm.complete(
            prompt,
            system="You are a technical writer creating a chapter for a book about agentic systems. Write clear, technical, and insightful prose.",
            max_tokens=3000,
        )

        return content

    def generate_code_walkthrough(
        self,
        poc: PocPlan,
        phrase: str,
        poc_folder: Path,
    ) -> str:
        """Generate a step-by-step code walkthrough for the POC."""
        repo_structure = self._get_repo_structure(poc_folder)
        all_files = self._get_key_files_content(
            poc_folder,
            max_files=MAX_FILES_WALKTHROUGH,
            max_chars=MAX_FILE_CONTENT_CHARS_WALKTHROUGH,
            exclude_readme=True,
        )

        prompt = self.prompt_loader.render(
            "code_walkthrough_generation_prompt.md",
            {
                "phrase": phrase,
                "poc_title": poc.title,
                "poc_slug": poc.slug,
                "poc_goal": poc.goal,
                "required_packages": poc.required_packages,
                "repo_structure": repo_structure,
                "key_files": all_files,
            },
        )

        logger.info("generating_walkthrough_markdown", poc_slug=poc.slug)

        content = self.llm.complete(
            prompt,
            system="You are a senior engineer writing a step-by-step implementation guide. Be precise and include all implementation code.",
            max_tokens=6000,
        )

        return content

    def generate_run_intro_chapter(
        self,
        phrase: str,
        normalized_phrase: str,
        selected_pocs: list,
        poc_executions: list | None = None,
    ) -> str:
        """Generate the opening intro chapter for the full run."""
        # Build a status lookup by slug so we can annotate each POC
        status_by_slug: dict[str, str] = {}
        if poc_executions:
            for exc in poc_executions:
                slug = exc.poc_slug if hasattr(exc, "poc_slug") else exc.get("poc_slug", "")
                status = exc.build_status if hasattr(exc, "build_status") else exc.get("build_status", "unknown")
                if slug:
                    status_by_slug[slug] = str(status)

        poc_detail_blocks: list[str] = []
        for poc in selected_pocs:
            status = status_by_slug.get(poc.slug, "unknown")
            packages = ", ".join(poc.required_packages) if poc.required_packages else "none specified"
            boundaries = "\n".join(f"  - {b}" for b in poc.scope_boundaries) if poc.scope_boundaries else "  - (not specified)"
            block = (
                f"### {poc.index:02d}. {poc.title} (`{poc.slug}`) — status: {status}\n"
                f"**Goal:** {poc.goal}\n"
                f"**Why it matters:** {poc.why_it_matters}\n"
                f"**Packages:** {packages}\n"
                f"**Scope boundaries:**\n{boundaries}"
            )
            poc_detail_blocks.append(block)

        poc_details = "\n\n".join(poc_detail_blocks)

        prompt = self.prompt_loader.render(
            "run_intro_chapter_prompt.md",
            {
                "phrase": phrase,
                "normalized_phrase": normalized_phrase,
                "poc_details": poc_details,
            },
        )

        logger.info("generating_run_intro_chapter", phrase=phrase)

        content = self.llm.complete(
            prompt,
            system="You are a technical writer creating the opening chapter of a book about agentic systems.",
            max_tokens=4000,
        )

        return content

    def write_prose_chapter(
        self, content: str, poc_folder: Path, poc_slug: str
    ) -> Path:
        """Write the prose chapter to file."""
        filename = f"{poc_slug}.md"
        path = poc_folder / filename
        path.write_text(content, encoding="utf-8")
        logger.info("wrote_prose_chapter", path=str(path))
        return path

    def write_code_walkthrough(
        self, content: str, poc_folder: Path, poc_slug: str
    ) -> Path:
        """Write the code walkthrough to file."""
        filename = f"code-implementation-{poc_slug}.md"
        path = poc_folder / filename
        path.write_text(content, encoding="utf-8")
        logger.info("wrote_code_walkthrough", path=str(path))
        return path

    def _get_repo_structure(self, poc_folder: Path) -> str:
        """Generate a tree-like structure of the repo."""
        if not poc_folder.exists():
            return "Repository not found"

        lines = [f"{poc_folder.name}/"]
        self._build_tree(poc_folder, lines, prefix="  ", depth=0, max_depth=4)
        return "\n".join(lines)

    def _build_tree(
        self,
        directory: Path,
        lines: list[str],
        prefix: str,
        depth: int,
        max_depth: int,
    ) -> None:
        """Recursively build directory tree."""
        if depth >= max_depth:
            return

        try:
            entries = sorted(directory.iterdir(), key=lambda p: (p.is_file(), p.name))
        except PermissionError:
            return

        skip_dirs = {".git", "__pycache__", ".pytest_cache", "node_modules", ".mypy_cache", "logs"}

        for entry in entries:
            if entry.name in skip_dirs:
                continue
            if entry.name.startswith(".") and entry.name not in {".env.example"}:
                continue

            if entry.is_dir():
                lines.append(f"{prefix}{entry.name}/")
                self._build_tree(entry, lines, prefix + "  ", depth + 1, max_depth)
            else:
                lines.append(f"{prefix}{entry.name}")

    def _get_key_files_content(
        self,
        poc_folder: Path,
        max_files: int = MAX_FILES_WALKTHROUGH,
        max_chars: int = MAX_FILE_CONTENT_CHARS_WALKTHROUGH,
        exclude_readme: bool = False,
    ) -> str:
        """Get content of implementation files to include in the prompt.

        Collects all .py files from app/ and tests/, plus README.md and pyproject.toml.
        Skips scripts/ and core/ (boilerplate). Skips __pycache__ and similar noise.
        """
        # Directories to skip entirely
        skip_dirs = {
            "scripts", "core", ".git", "__pycache__",
            ".pytest_cache", ".mypy_cache", "logs", ".venv",
        }
        # File names to skip
        skip_files = {"__init__.py"}

        collected: list[Path] = []

        # Walk app/ and tests/ for .py files
        for subdir in ["app", "tests"]:
            target = poc_folder / subdir
            if not target.exists():
                continue
            for path in sorted(target.rglob("*.py")):
                if any(part in skip_dirs for part in path.parts):
                    continue
                if path.name in skip_files:
                    continue
                collected.append(path)

        # Also include pyproject.toml and optionally README.md at root
        if not exclude_readme:
            readme = poc_folder / "README.md"
            if readme.exists():
                collected.append(readme)
        toml = poc_folder / "pyproject.toml"
        if toml.exists():
            collected.append(toml)

        files_content = []
        for path in collected[:max_files]:
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
                if len(content) > max_chars:
                    content = content[:max_chars] + "\n... [truncated]"
                rel_path = path.relative_to(poc_folder)
                lang = "python" if path.suffix == ".py" else "toml" if path.suffix == ".toml" else ""
                files_content.append(f"### {rel_path}\n\n```{lang}\n{content}\n```")
            except Exception:
                pass

        return "\n\n".join(files_content) if files_content else "No implementation files found"
