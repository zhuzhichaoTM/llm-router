#!/bin/bash
# Run all tests and generate coverage report

set -e

echo "========================================"
echo "LLM Router Test Suite"
echo "========================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Install test dependencies if needed
echo -e "${YELLOW}Checking test dependencies...${NC}"
if ! uv run python -c "import pytest" 2>/dev/null; echo 'installed'; then
    echo -e "${YELLOW}Installing test dependencies...${NC}"
    uv pip install pytest pytest-cov pytest-asyncio httpx-mock
fi

# Run unit tests
echo -e "${YELLOW}Running unit tests...${NC}"
uv run python -m pytest tests/unit -v --cov=src --cov-report=html --cov-report=term-missing --cov-fail-under=60
unit_result=$?

echo ""
echo -e "${YELLOW}Running integration tests...${NC}"
uv run python -m pytest tests/integration -v --cov=src --cov-append --cov-report=html --cov-report=term-missing --cov-fail-under=60
integration_result=$?

# Summary
echo ""
echo "========================================"
echo "Test Summary"
echo "========================================"
echo ""

if [ $unit_result -eq 0 ]; then
    echo -e "${GREEN}Unit tests: PASSED${NC}"
else
    echo -e "${YELLOW}Unit tests: FAILED (exit code: $unit_result)${NC}"
fi

if [ $integration_result -eq 0 ]; then
    echo -e "${GREEN}Integration tests: PASSED${NC}"
else
    echo -e "${YELLOW}Integration tests: FAILED (exit code: $integration_result)${NC}"
fi

echo ""
echo "Coverage report generated: htmlcov/index.html"
echo "Open in browser: file://$(pwd)/htmlcov/index.html"
echo ""
echo "View coverage summary: cat htmlcov/index.html | grep -A 5 'Coverage Summary'"
