#!/usr/bin/env bash
# Run the test suite

set -e

echo "Running POC Factory tests..."

# Unit tests
echo "=== Unit Tests ==="
python -m pytest app/tests/unit/ -v --tb=short

# Integration tests
echo ""
echo "=== Integration Tests ==="
python -m pytest app/tests/integration/ -v --tb=short

# E2E tests
echo ""
echo "=== E2E Tests ==="
python -m pytest app/tests/e2e/ -v --tb=short

echo ""
echo "All tests complete!"
