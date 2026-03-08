"""Service for loading and rendering prompt templates."""

from pathlib import Path
from typing import Any

from app.logging_config import get_logger

logger = get_logger(__name__)

TEMPLATES_ROOT = Path(__file__).parent.parent.parent / "templates"


class PromptLoader:
    """Loads prompt templates from files and renders them with variables."""

    def __init__(self, templates_root: Path = TEMPLATES_ROOT) -> None:
        self.templates_root = templates_root

    def load(self, template_name: str) -> str:
        """Load a template file by name."""
        # Search in both markdown/ and claude_md/ subdirs
        for subdir in ["markdown", "claude_md"]:
            path = self.templates_root / subdir / template_name
            if path.exists():
                return path.read_text(encoding="utf-8")

        # Try direct path
        path = self.templates_root / template_name
        if path.exists():
            return path.read_text(encoding="utf-8")

        raise FileNotFoundError(f"Prompt template not found: {template_name}")

    def render(self, template_name: str, variables: dict[str, Any]) -> str:
        """Load and render a template with the given variables."""
        template = self.load(template_name)
        return self._render_template(template, variables)

    def _render_template(self, template: str, variables: dict[str, Any]) -> str:
        """Simple {variable} substitution in templates."""
        import json
        result = template
        for key, value in variables.items():
            placeholder = "{" + key + "}"
            if isinstance(value, (list, dict)):
                str_value = json.dumps(value, indent=2)
            else:
                str_value = str(value) if value is not None else ""
            result = result.replace(placeholder, str_value)
        return result


_default_loader = PromptLoader()


def get_prompt_loader() -> PromptLoader:
    return _default_loader
