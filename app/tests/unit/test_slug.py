"""Unit tests for slug generation and normalization."""

import pytest

from app.domain.value_objects.slug import (
    deduplicate_packages,
    normalize_package_name,
    normalize_phrase,
    phrase_to_slug,
    poc_slug,
    slugify,
)


class TestSlugify:
    def test_basic_lowercase(self):
        assert slugify("Hello World") == "hello-world"

    def test_underscores_become_hyphens(self):
        assert slugify("hello_world") == "hello-world"

    def test_multiple_spaces_collapse(self):
        assert slugify("hello   world") == "hello-world"

    def test_special_chars_removed(self):
        assert slugify("hello! @world#") == "hello-world"

    def test_leading_trailing_hyphens_stripped(self):
        assert slugify("-hello-world-") == "hello-world"

    def test_multiple_hyphens_collapse(self):
        assert slugify("hello--world") == "hello-world"

    def test_numbers_preserved(self):
        assert slugify("test123") == "test123"

    def test_empty_string(self):
        assert slugify("") == ""

    def test_unicode_normalized(self):
        result = slugify("café")
        assert "caf" in result

    def test_monitoring_and_observability(self):
        assert slugify("monitoring and observability") == "monitoring-and-observability"


class TestPocSlug:
    def test_single_digit_index_padded(self):
        assert poc_slug(1, "untrusted-data-boundary") == "01-untrusted-data-boundary"

    def test_double_digit_index(self):
        assert poc_slug(10, "some-poc") == "10-some-poc"

    def test_title_is_slugified(self):
        assert poc_slug(1, "Untrusted Data Boundary") == "01-untrusted-data-boundary"

    def test_index_preserves_order(self):
        slugs = [poc_slug(i, f"poc {i}") for i in range(1, 4)]
        assert slugs == ["01-poc-1", "02-poc-2", "03-poc-3"]


class TestNormalizePhrase:
    def test_strips_whitespace(self):
        assert normalize_phrase("  hello world  ") == "hello world"

    def test_lowercases(self):
        assert normalize_phrase("Hello World") == "hello world"

    def test_collapses_spaces(self):
        assert normalize_phrase("hello   world") == "hello world"

    def test_monitoring_typo(self):
        # Basic normalization (typo correction is done by LLM layer)
        result = normalize_phrase("Monitoring and Observaibility")
        assert result == "monitoring and observaibility"


class TestPhraseToSlug:
    def test_prompt_injection_guardrails(self):
        slug = phrase_to_slug("prompt injection guardrails")
        assert slug == "prompt-injection-guardrails"

    def test_monitoring_and_observability(self):
        slug = phrase_to_slug("monitoring and observability")
        assert slug == "monitoring-and-observability"


class TestNormalizePackageName:
    def test_lowercase(self):
        assert normalize_package_name("FastAPI") == "fastapi"

    def test_underscores_to_hyphens(self):
        assert normalize_package_name("pydantic_settings") == "pydantic-settings"

    def test_strips_whitespace(self):
        assert normalize_package_name("  langfuse  ") == "langfuse"


class TestDeduplicatePackages:
    def test_removes_duplicates(self):
        result = deduplicate_packages(["fastapi", "pydantic", "fastapi"])
        assert result == ["fastapi", "pydantic"]

    def test_preserves_order(self):
        result = deduplicate_packages(["b", "a", "c"])
        assert result == ["b", "a", "c"]

    def test_normalizes_case(self):
        result = deduplicate_packages(["FastAPI", "fastapi"])
        assert len(result) == 1

    def test_empty_list(self):
        assert deduplicate_packages([]) == []
