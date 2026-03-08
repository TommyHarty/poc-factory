#!/usr/bin/env bash
# Setup script for the POC Factory

set -e

echo "Setting up POC Factory..."

# Check Python version
python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
echo "Python version: $python_version"

# Install dependencies
echo "Installing dependencies..."
if command -v pip &> /dev/null; then
    pip install -e ".[dev]"
else
    pip3 install -e ".[dev]"
fi

# Create required directories
mkdir -p output work logs

# Copy .env if it doesn't exist
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "Created .env from .env.example. Please update with your API keys."
    fi
fi

echo "Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit .env with your API keys (ANTHROPIC_API_KEY, GITHUB_TOKEN)"
echo "  2. Run: bash scripts/run.sh"
echo "  3. Try: curl -X POST http://localhost:8000/runs -H 'Content-Type: application/json' -d '{\"phrase\": \"prompt injection guardrails\"}'"
