#!/bin/bash
# Stage 1 测试执行脚本

set -e

echo "========================================"
echo "Stage 1 测试执行脚本"
echo "========================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 检查环境
echo "检查运行环境..."

# 检查 uv
if ! command -v uv >/dev/null 2>&1; then
    echo -e "${RED}uv 未安装${NC}"
    echo "请安装 uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# 检查测试依赖
echo "检查测试依赖..."

# 启动 Docker 服务
echo ""
echo "启动必要的服务..."

# 检查 Docker
if ! command -v docker >/dev/null 2>&1; then
    echo -e "${RED}Docker 未运行${NC}"
    echo "请启动 Docker 并运行: docker-compose up -d postgres redis backend"
    exit 1
fi

# 运行测试
echo ""
echo "========================================"
echo -e "${YELLOW}运行 Stage 1 测试...${NC}"
echo ""

# 测试配置
export PYTEST_ASYNCIO_MODE=auto
export PYTHONPATH=$(uv run python -c "from pathlib import Path; print(str(Path.cwd()))")

# 执行单元测试
echo -e "${YELLOW}1. 运行单元测试...${NC}"
echo ""
uv run pytest tests/unit/ -v --tb=short \
    --cov=core/src \
    --cov-report=html \
    --cov-report=term-missing \
    --cov-fail-under=60 \
    --junitxml=junit.xml \
    tests/unit/test_streaming.py \
    tests/unit/test_token_counter.py \
    tests/unit/test_rate_limiter.py \
    tests/unit/test_content_analyzer.py \
    tests/unit/test_load_balancer.py \
    tests/unit/test_cost_agent.py \
    tests/unit/test_routing_agent.py \
    tests/unit/test_providers.py
    tests/unit/test_models.py \
    tests/unit/test_api.py
    2>&1

unit_result=$?

echo ""
echo -e "${YELLOW}2. 运行集成测试...${NC}"
echo ""

# 只运行不依赖外部服务的集成测试
uv run pytest tests/integration/ -v --tb=short \
    --cov-append \
    tests/integration/test_streaming_api.py \
    2>&1

int_result=$?

# 总结
echo ""
echo "========================================"
echo "测试总结"
echo "========================================"
echo ""

if [ $unit_result -eq 0 ]; then
    echo -e "${GREEN}单元测试通过${NC}"
else
    echo -e "${RED}单元测试失败，退出码: $unit_result${NC}"
fi

if [ $int_result -eq 0 ]; then
    echo -e "${GREEN}集成测试通过${NC}"
else
    echo -e "${RED}集成测试失败，退出码: $int_result${NC}"
fi

# 生成覆盖率报告
echo ""
echo -e "${YELLOW}生成覆盖率报告...${NC}"
uv run pytest tests/ -v --cov=core/src --cov-report=html --cov-report=term-missing > pytest_coverage.txt 2>&1

# 显示覆盖率摘要
echo ""
echo -e "${YELLOW}覆盖率摘要:${NC}"
grep -A 2 "TOTAL" pytest_coverage.txt || echo "未找到覆盖率数据"

echo ""
echo "查看完整覆盖率报告："
echo "  open htmlcov/index.html"

echo ""
echo -e "${YELLOW}检查测试覆盖率要求...${NC}"
if grep -q "TOTAL.*100%" pytest_coverage.txt > /dev/null 2>&1; then
    echo -e "${GREEN}覆盖率 >= 100%${NC}"
else
    coverage = grep "TOTAL.*[0-9]+" pytest_coverage.txt | tail -1
    coverage_pct=${coverage##. 8}
    if [ "$coverage_pct" -gt "60" ]; then
        echo -e "${GREEN}覆盖率 $coverage_pct% >= 60%${NC}"
    else
        echo -e "${YELLOW}覆盖率 $coverage_pct% < 60%${NC}"
    fi
fi

echo ""
echo "========================================"
echo "Stage 1 测试执行完成"
echo "========================================"
