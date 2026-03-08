"""Service for generating and ranking POC ideas using the LLM."""

import json
from typing import Optional

from app.application.services.prompt_loader import PromptLoader
from app.domain.models.run import PocPlan
from app.domain.services.poc_ranking import assign_poc_slugs, select_top_pocs
from app.domain.value_objects.slug import poc_slug, slugify
from app.infrastructure.llm.adapter import LLMAdapter
from app.logging_config import get_logger

logger = get_logger(__name__)


class PocIdeationService:
    """Orchestrates POC idea generation and ranking via LLM."""

    def __init__(self, llm: LLMAdapter, prompt_loader: PromptLoader) -> None:
        self.llm = llm
        self.prompt_loader = prompt_loader

    def generate_candidates(
        self,
        phrase: str,
        technologies: list[str],
        optional_packages: list[str],
        preferences: dict,
        candidate_count: int = 18,
    ) -> list[PocPlan]:
        """Generate a list of POC candidate ideas."""
        prompt = self.prompt_loader.render(
            "poc_ideation_prompt.md",
            {
                "phrase": phrase,
                "technologies": technologies,
                "optional_packages": optional_packages,
                "preferences": json.dumps(preferences, indent=2),
                "candidate_count": candidate_count,
            },
        )

        logger.info("generating_poc_candidates", phrase=phrase, count=candidate_count)

        try:
            raw = self.llm.complete_json(
                prompt,
                system="You are an expert agentic systems architect. Respond only with valid JSON.",
                max_tokens=8000,
            )
        except Exception as e:
            logger.error("ideation_llm_error", error=str(e))
            raise

        candidates = self._parse_candidates(raw)
        logger.info("generated_candidates", count=len(candidates))
        return candidates

    def rank_and_select(
        self,
        phrase: str,
        technologies: list[str],
        candidates: list[PocPlan],
        target_count: int,
    ) -> list[PocPlan]:
        """Rank candidates and select the top N."""
        candidates_json = json.dumps(
            [c.model_dump() for c in candidates], indent=2
        )

        prompt = self.prompt_loader.render(
            "poc_ranking_prompt.md",
            {
                "phrase": phrase,
                "technologies": technologies,
                "candidates_json": candidates_json,
                "target_count": target_count,
            },
        )

        logger.info("ranking_poc_candidates", target_count=target_count)

        try:
            raw = self.llm.complete_json(
                prompt,
                system="You are an expert agentic systems architect. Respond only with valid JSON.",
                max_tokens=6000,
            )
        except Exception as e:
            logger.error("ranking_llm_error", error=str(e))
            # Fallback: just take the top N from the existing list
            logger.warning("using_fallback_ranking")
            return select_top_pocs(candidates, target_count)

        selected = self._parse_ranked_selection(raw, target_count)
        logger.info("selected_pocs", count=len(selected))
        return selected

    def _parse_candidates(self, raw: object) -> list[PocPlan]:
        """Parse raw LLM output into PocPlan objects."""
        if isinstance(raw, dict) and "candidates" in raw:
            items = raw["candidates"]
        elif isinstance(raw, list):
            items = raw
        else:
            logger.warning("unexpected_ideation_response_format")
            return []

        plans = []
        for i, item in enumerate(items):
            try:
                plan = PocPlan(
                    index=i + 1,
                    title=item.get("title", f"POC {i+1}"),
                    slug=poc_slug(i + 1, item.get("slug_base") or item.get("title", f"poc-{i+1}")),
                    goal=item.get("goal", ""),
                    why_it_matters=item.get("why_it_matters", ""),
                    scope_boundaries=item.get("excludes", []) or item.get("scope_boundaries", []),
                    required_packages=item.get("required_packages", []),
                    rank_justification=item.get("rank_justification", ""),
                    excludes=item.get("excludes", []),
                )
                plans.append(plan)
            except Exception as e:
                logger.warning("failed_to_parse_candidate", index=i, error=str(e))

        return plans

    def _parse_ranked_selection(self, raw: object, target_count: int) -> list[PocPlan]:
        """Parse the ranked selection response."""
        if isinstance(raw, dict):
            selected_items = raw.get("selected", [])
        elif isinstance(raw, list):
            selected_items = raw
        else:
            return []

        plans = []
        for item in selected_items:
            try:
                index = item.get("index", len(plans) + 1)
                title = item.get("title", f"POC {index}")
                slug_base = item.get("slug_base") or slugify(title)
                plan = PocPlan(
                    index=index,
                    title=title,
                    slug=poc_slug(index, slug_base),
                    goal=item.get("goal", ""),
                    why_it_matters=item.get("why_it_matters", ""),
                    scope_boundaries=item.get("scope_boundaries", []),
                    required_packages=item.get("required_packages", []),
                    rank_justification=item.get("rank_justification", ""),
                    excludes=item.get("excludes", []),
                )
                plans.append(plan)
            except Exception as e:
                logger.warning("failed_to_parse_selected", error=str(e))

        # Ensure correct indexing
        final = []
        for i, plan in enumerate(plans[:target_count], start=1):
            final.append(plan.model_copy(update={"index": i, "slug": poc_slug(i, slugify(plan.title))}))

        return final
