# Code Walkthrough Generation Prompt

You are writing a code-along implementation guide for a developer who wants to understand and replicate this POC step by step.

## Context
- Topic Area: {phrase}
- POC Title: {poc_title}
- POC Slug: {poc_slug}
- POC Goal: {poc_goal}
- Required Packages: {required_packages}

## Repo Structure
{repo_structure}

## Implementation Files
{key_files}

## Instructions

Write a step-by-step code walkthrough that covers **every piece of implementation code** in the repo above. The reader should be able to code along and end up with a working replica of this POC.

Rules:
- Cover ALL files shown in the Implementation Files section. Do not skip any file.
- Ignore `scripts/` and `core/` — those are boilerplate.
- Every piece of code must appear in a fenced code block with the correct language tag (e.g. ` ```python `, ` ```toml `).
- Each step has a short prose explanation (2-5 sentences) followed immediately by the full code for that file or logical chunk.
- Do not summarise or paraphrase code — show it in full.
- Do not include the health check endpoint from `app/main.py` unless the POC extends it.

## Required Structure

### Title (H1)
`Code Implementation: {poc_title}`

### Overview
2-3 sentences: what was built, what the reader will have at the end of this guide.

### Prerequisites
- Python version, key packages, any external services needed.

### Implementation Steps

Number each step. One step = one file or one tightly related group of additions. Format:

```
## Step N: [Descriptive title]

**File**: `path/to/file.py`

[2-5 sentence explanation of what this file does, why it is structured this way, and any non-obvious decisions.]

```python
[complete file contents]
```
```

Work through files in this order:
1. Any new configuration additions (`core/config.py` extensions or new env vars)
2. Domain models / schemas (`app/models.py`, `app/schemas.py`, etc.)
3. Core business logic / services (`app/services/`, `app/guards.py`, etc.)
4. API routes / endpoints (`app/main.py` additions or `app/routers/`)
5. Tests (`tests/`)
6. `pyproject.toml` (show the dependencies block)
7. `README.md`

### Verification

How to confirm the POC is working:
- How to run: `./scripts/run.sh`
- How to test: `./scripts/test.sh`
- What endpoints to call and what response to expect

### Key Takeaway
One paragraph: the single most important implementation insight from this POC.

## Output
Output the complete markdown guide. Start with the H1 title. Ensure every code file is in a fenced code block.
