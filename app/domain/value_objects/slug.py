"""Slug value object and normalization logic."""

import re
import unicodedata


def slugify(text: str) -> str:
    """Convert text to a URL-safe, hyphen-separated slug.

    - Lowercase
    - Replace spaces and underscores with hyphens
    - Remove non-alphanumeric characters (except hyphens)
    - Collapse multiple hyphens
    - Strip leading/trailing hyphens
    """
    # Normalize unicode characters
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")

    # Lowercase
    text = text.lower()

    # Replace spaces, underscores, slashes with hyphens
    text = re.sub(r"[\s_/\\]+", "-", text)

    # Remove characters that aren't alphanumeric or hyphens
    text = re.sub(r"[^a-z0-9-]", "", text)

    # Collapse multiple hyphens
    text = re.sub(r"-{2,}", "-", text)

    # Strip leading/trailing hyphens
    text = text.strip("-")

    return text


def poc_slug(index: int, title: str) -> str:
    """Create a deterministic POC slug with a two-digit index prefix.

    Example: (1, "Untrusted Data Boundary") -> "01-untrusted-data-boundary"
    """
    base = slugify(title)
    return f"{index:02d}-{base}"


def normalize_phrase(phrase: str) -> str:
    """Normalize a user-provided phrase.

    - Strip whitespace
    - Collapse multiple spaces
    - Lowercase
    - Fix common typos (simple approach)
    """
    phrase = phrase.strip()
    phrase = re.sub(r"\s+", " ", phrase)
    phrase = phrase.lower()
    return phrase


def phrase_to_slug(phrase: str) -> str:
    """Convert a phrase to a folder-safe slug."""
    return slugify(phrase)


def normalize_package_name(name: str) -> str:
    """Normalize a Python package name to its canonical form."""
    return name.strip().lower().replace("_", "-")


def deduplicate_packages(packages: list[str]) -> list[str]:
    """Deduplicate package list while preserving order."""
    seen: set[str] = set()
    result: list[str] = []
    for pkg in packages:
        normalized = normalize_package_name(pkg)
        if normalized not in seen:
            seen.add(normalized)
            result.append(pkg.strip().lower())
    return result
