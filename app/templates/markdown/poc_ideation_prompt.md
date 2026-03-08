# POC Ideation Prompt

You are an expert in agentic systems and software engineering. Your task is to generate a comprehensive list of highly focused POC (Proof of Concept) ideas for the following topic.

## Topic
{phrase}

## Required Technologies
{technologies}

## Optional Packages
{optional_packages}

## Preferences
{preferences}

## Instructions

Generate exactly {candidate_count} distinct, focused POC ideas for this topic.

Each POC must:
1. Address exactly ONE specific approach, pattern, or technique
2. Be implementable as a small, focused Python/FastAPI project
3. Be pedagogically valuable (teaches a clear concept)
4. Be distinct from all other POCs (no overlap)
5. Be practically relevant (something that would appear in real systems)

For each POC, provide:
- `title`: A clear, concise title (3-6 words)
- `slug_base`: The base slug without index prefix (lowercase, hyphen-separated)
- `goal`: One sentence describing what this POC implements
- `why_it_matters`: One sentence explaining its practical importance
- `excludes`: 2-3 things this POC deliberately does NOT include
- `required_packages`: List of Python packages needed
- `rank_justification`: One sentence explaining why this is at this rank position

Order the POCs from most fundamental/important to most advanced/derived.

## Output Format

Respond with a JSON array:

```json
[
  {
    "title": "Untrusted Data Boundary",
    "slug_base": "untrusted-data-boundary",
    "goal": "Implement strict input validation and sanitization at the boundary between user-supplied data and agent instructions.",
    "why_it_matters": "Without clear trust boundaries, user input can manipulate agent behavior in unintended ways.",
    "excludes": ["multi-layer defense in depth", "output validation", "tool execution controls"],
    "required_packages": ["fastapi", "pydantic"],
    "rank_justification": "Foundational - must be understood before any other injection defense."
  }
]
```

Generate exactly {candidate_count} entries, ordered from most fundamental to most advanced.
