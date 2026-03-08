"""Unit tests for POC ranking and selection."""

import pytest

from app.domain.models.run import PocPlan
from app.domain.services.poc_ranking import assign_poc_slugs, select_top_pocs


def make_poc(index: int, title: str, slug: str = "") -> PocPlan:
    return PocPlan(
        index=index,
        title=title,
        slug=slug or f"{index:02d}-{title.lower().replace(' ', '-')}",
        goal=f"Goal for {title}",
        why_it_matters=f"Matters because of {title}",
    )


class TestSelectTopPocs:
    def test_selects_correct_count(self):
        candidates = [make_poc(i, f"POC {i}") for i in range(1, 16)]
        selected = select_top_pocs(candidates, 10)
        assert len(selected) == 10

    def test_respects_order(self):
        candidates = [make_poc(i, f"POC {i}") for i in range(1, 6)]
        selected = select_top_pocs(candidates, 3)
        assert [p.title for p in selected] == ["POC 1", "POC 2", "POC 3"]

    def test_deduplicates_by_slug(self):
        candidates = [
            make_poc(1, "Test", "01-test"),
            make_poc(2, "Test", "01-test"),  # duplicate slug
            make_poc(3, "Other", "03-other"),
        ]
        selected = select_top_pocs(candidates, 3)
        slugs = [p.slug for p in selected]
        assert len(set(slugs)) == len(slugs)

    def test_reindexes_from_one(self):
        candidates = [make_poc(i, f"POC {i}") for i in range(5, 10)]
        selected = select_top_pocs(candidates, 3)
        assert [p.index for p in selected] == [1, 2, 3]

    def test_empty_candidates(self):
        assert select_top_pocs([], 10) == []

    def test_fewer_candidates_than_target(self):
        candidates = [make_poc(i, f"POC {i}") for i in range(1, 4)]
        selected = select_top_pocs(candidates, 10)
        assert len(selected) == 3


class TestAssignPocSlugs:
    def test_assigns_correct_slugs(self):
        pocs = [
            PocPlan(index=1, title="Untrusted Data Boundary", slug="", goal="G"),
            PocPlan(index=2, title="Output Schema Validation", slug="", goal="G"),
        ]
        result = assign_poc_slugs(pocs)
        assert result[0].slug == "01-untrusted-data-boundary"
        assert result[1].slug == "02-output-schema-validation"

    def test_preserves_other_fields(self):
        poc = PocPlan(index=1, title="Test POC", slug="", goal="My goal")
        result = assign_poc_slugs([poc])
        assert result[0].goal == "My goal"
