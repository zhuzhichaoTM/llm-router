#!/bin/bash
# Install test dependencies

set -e

echo "Installing test dependencies..."

# Using uv
uv pip install pytest pytest-cov pytest-asyncio httpx-mock

echo "Test dependencies installed successfully!"
