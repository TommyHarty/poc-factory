"""Domain service for POC ranking and selection."""

from app.domain.models.run import PocPlan


def select_top_pocs(candidates: list[PocPlan], target_count: int) -> list[PocPlan]:
    """Select the top N POCs from ranked candidates.

    Candidates are expected to already be in ranked order from the LLM.
    This function applies additional deduplication and slice selection.
    """
    if not candidates:
        return []

    # Deduplicate by slug
    seen_slugs: set[str] = set()
    deduplicated: list[PocPlan] = []
    for poc in candidates:
        if poc.slug not in seen_slugs:
            seen_slugs.add(poc.slug)
            deduplicated.append(poc)

    # Select top N
    selected = deduplicated[:target_count]

    # Re-index from 1
    reindexed = []
    for i, poc in enumerate(selected, start=1):
        reindexed.append(
            poc.model_copy(update={"index": i})
        )

    return reindexed


def assign_poc_slugs(pocs: list[PocPlan]) -> list[PocPlan]:
    """Assign deterministic slugs to a list of POC plans."""
    from app.domain.value_objects.slug import poc_slug

    result = []
    for poc in pocs:
        slug = poc_slug(poc.index, poc.title)
        result.append(poc.model_copy(update={"slug": slug}))
    return result
