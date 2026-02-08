#!/bin/bash
# LLM Router Local Development Script

set -e

echo "========================================"
echo "LLM Router Local Development"
echo "========================================"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "Warning: .env file not found. Creating from .env.example..."
    cp .env.example .env
    echo ".env file created. Please update it with your configuration."
    echo ""
fi

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check if Python 3.11+ is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1)
if [ "$PYTHON_VERSION" -lt 3 ]; then
    echo "Error: Python 3.11+ is required (found $(python3 --version))"
    exit 1
fi

echo -e "${GREEN}Python version: $(python3 --version)${NC}"

# Create virtual environment if not exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo ""
echo "Installing/updating dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Check if PostgreSQL is running
echo ""
echo "Checking PostgreSQL connection..."
if ! pg_isready -h localhost -p 5432 > /dev/null 2>&1; then
    echo -e "${YELLOW}PostgreSQL is not running. Please start PostgreSQL or use Docker Compose:${NC}"
    echo "  docker-compose up -d postgres redis"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if Redis is running
echo "Checking Redis connection..."
if ! redis-cli ping > /dev/null 2>&1; then
    echo -e "${YELLOW}Redis is not running. Please start Redis or use Docker Compose:${NC}"
    echo "  docker-compose up -d redis"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Initialize database
echo ""
echo "Initializing database..."
python scripts/init_db.py

# Start backend in background
echo ""
echo -e "${GREEN}Starting backend server...${NC}"
echo "Backend will be available at: http://localhost:8000"
echo "API Docs available at: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop"
echo ""

python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
