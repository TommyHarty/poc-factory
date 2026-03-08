# Repair Prompt Template

You are repairing a POC that failed validation after the initial build.

## POC
- Slug: {poc_slug}
- Goal: {poc_goal}

## Validation Failures

{validation_failures}

## Static Check Errors

{static_check_errors}

## Test Failures

{test_failures}

## Instructions

Fix ONLY the issues listed above. Do not change the overall architecture or approach.

### Rules
1. Make the minimum changes needed to fix the listed errors
2. Do not refactor code that is working correctly
3. Do not add new features or change the POC scope
4. Ensure all tests pass after your fix
5. Ensure all imports resolve correctly
6. If a test was incorrectly written, fix the test rather than removing it
7. Keep the fix targeted and minimal

### What to check after fixing
- Run `pytest tests/ -v` to verify tests pass
- Ensure no new import errors are introduced
- Verify the API endpoints still work as documented in README.md

Fix the issues now.
