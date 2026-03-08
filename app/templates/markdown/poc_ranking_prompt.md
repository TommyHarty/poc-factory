# POC Ranking Prompt

You are an expert in agentic systems. You have a list of POC candidates that need to be ranked and refined.

## Topic
{phrase}

## Required Technologies
{technologies}

## Target POC Count
{target_count}

## Candidate POCs
{candidates_json}

## Instructions

Review the candidate POCs above and select the best {target_count} for implementation.

Ranking criteria (in order of importance):
1. **Practical importance**: How often does this pattern appear in real production systems?
2. **Foundational dependency**: Do later POCs depend on understanding this one first?
3. **Implementation clarity**: Can this be cleanly implemented in a small, focused repo?
4. **Teaching value**: Does this clearly demonstrate a distinct concept?
5. **Distinctiveness**: Is this sufficiently different from the other selected POCs?

Rules:
- No two selected POCs should overlap significantly in scope
- Foundational patterns should come before advanced/derived ones
- The ordering should represent a natural learning progression
- If two POCs are very similar, keep only the more focused one

## Output Format

Respond with a JSON object:

```json
{
  "selected": [
    {
      "index": 1,
      "title": "Untrusted Data Boundary",
      "slug": "01-untrusted-data-boundary",
      "slug_base": "untrusted-data-boundary",
      "goal": "...",
      "why_it_matters": "...",
      "scope_boundaries": ["Only covers input validation", "Does not implement output filtering"],
      "required_packages": ["fastapi", "pydantic"],
      "rank_justification": "..."
    }
  ],
  "rejected": ["slug-base-1", "slug-base-2"],
  "selection_rationale": "Brief explanation of selection decisions"
}
```

Select exactly {target_count} POCs.
