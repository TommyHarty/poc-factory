#!/usr/bin/env bash
# Example script to create a POC Factory run

set -e

BASE_URL="${BASE_URL:-http://localhost:8000}"

echo "Creating a new POC Factory run..."

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${BASE_URL}/runs" \
  -H "Content-Type: application/json" \
  -d '{
    "phrase": "prompt injection guardrails",
    "technologies": ["fastapi", "pydantic"],
    "optional_packages": [],
    "target_poc_count": 8,
    "preferences": {
      "use_docker": true,
      "use_pytest": true,
      "prefer_mocks": true,
      "include_mermaid": false
    },
    "dry_run": false
  }')

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

echo "HTTP $HTTP_CODE"
echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
