#!/bin/bash
# LLM Router Development Startup Script

set -e

echo "========================================"
echo "LLM Router Development Environment"
echo "========================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}Warning: .env file not found. Creating from .env.example...${NC}"
    cp .env.example .env
    echo -e "${GREEN}.env file created. Please update it with your configuration.${NC}"
    echo ""
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker is not running. Please start Docker Desktop first.${NC}"
    exit 1
fi

# Function to check service health
check_health() {
    local service=$1
    local url=$2
    local max_attempts=30
    local attempt=1

    echo "Waiting for $service to be healthy..."

    while [ $attempt -le $max_attempts ]; do
        if curl -sf "$url" > /dev/null 2>&1; then
            echo -e "${GREEN}$service is healthy!${NC}"
            return 0
        fi
        echo "Attempt $attempt/$max_attempts: $service not ready yet..."
        sleep 2
        attempt=$((attempt + 1))
    done

    echo -e "${RED}Error: $service did not become healthy${NC}"
    return 1
}

# Start dependencies
echo "Starting PostgreSQL and Redis..."
docker-compose up -d postgres redis

# Wait for PostgreSQL
echo "Waiting for PostgreSQL to be ready..."
check_health "PostgreSQL" "http://localhost:5432"

# Wait for Redis
echo "Waiting for Redis to be ready..."
check_health "Redis" "http://localhost:6379"

# Initialize database
echo ""
echo "Initializing database..."
python scripts/init_db.py

# Start backend
echo ""
echo "Starting backend..."
docker-compose up -d backend

# Wait for backend
check_health "Backend" "http://localhost:8000/health"

# Start frontend (optional)
echo ""
read -p "Start frontend? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Starting frontend..."
    docker-compose up -d frontend
    check_health "Frontend" "http://localhost:3000"
fi

echo ""
echo "========================================"
echo -e "${GREEN}Startup complete!${NC}"
echo "========================================"
echo ""
echo "Service URLs:"
echo "  - Backend API:  http://localhost:8000"
echo "  - API Docs:     http://localhost:8000/docs"
echo "  - Frontend:     http://localhost:3000"
echo "  - PostgreSQL:    localhost:5432"
echo "  - Redis:        localhost:6379"
echo ""
echo "To stop all services, run: docker-compose down"
echo "To view logs, run: docker-compose logs -f"
echo ""
