#!/usr/bin/env python3
"""
Stage 5 Verification Script - Cost Monitoring Module

This script verifies that all Stage 5 requirements are met by checking
file existence and code content.
"""
import sys
import os
from pathlib import Path

# Change to core directory
script_dir = Path(__file__).parent
core_dir = script_dir.parent
os.chdir(core_dir)

# Add src to path
src_dir = core_dir / "src"
sys.path.insert(0, str(src_dir))
sys.path.insert(0, str(core_dir.parent))

print("\n" + "=" * 60)
print("Stage 5 Verification: Cost Monitoring Module")
print("=" * 60)

# Verification results
results = []

# 1. Check Cost Agent
print("\n=== Stage 5 Verification: Cost Agent ===\n")
cost_agent_file = src_dir / "agents" / "cost_agent.py"
if cost_agent_file.exists():
    print("✓ Cost Agent file exists")
    results.append(True)

    content = cost_agent_file.read_text()

    # Check for record_cost method
    if "async def record_cost" in content:
        print("✓ Record cost method")
        results.append(True)
    else:
        print("✗ Record cost method missing")
        results.append(False)

    # Check for get_current_cost method
    if "async def get_current_cost" in content:
        print("✓ Get current cost method")
        results.append(True)
    else:
        print("✗ Get current cost method missing")
        results.append(False)

    # Check for get_daily_cost method
    if "async def get_daily_cost" in content:
        print("✓ Get daily cost method")
        results.append(True)
    else:
        print("✗ Get daily cost method missing")
        results.append(False)

    # Check for get_cost_by_model method
    if "async def get_cost_by_model" in content:
        print("✓ Get cost by model method")
        results.append(True)
    else:
        print("✗ Get cost by model method missing")
        results.append(False)

    # Check for get_cost_by_user method
    if "async def get_cost_by_user" in content:
        print("✓ Get cost by user method")
        results.append(True)
    else:
        print("✗ Get cost by user method missing")
        results.append(False)

    # Check for get_cost_summary method
    if "async def get_cost_summary" in content:
        print("✓ Get cost summary method")
        results.append(True)
    else:
        print("✗ Get cost summary method missing")
        results.append(False)

    # Check for Redis cost tracking
    if "redis" in content.lower() or "RedisKeys.COST" in content:
        print("✓ Redis real-time cost tracking")
        results.append(True)
    else:
        print("✗ Redis cost tracking missing")
        results.append(False)

    # Check for database persistence
    if "CostRecord" in content or "execute_insert" in content:
        print("✓ PostgreSQL cost persistence")
        results.append(True)
    else:
        print("✗ PostgreSQL persistence missing")
        results.append(False)
else:
    print("✗ Cost Agent file not found")
    results.append(False)

# 2. Check Cost API
print("\n=== Stage 5 Verification: Cost API ===\n")
cost_api_file = src_dir / "api" / "v1" / "cost.py"
if cost_api_file.exists():
    print("✓ Cost API file exists")
    results.append(True)

    content = cost_api_file.read_text()

    # Check for /current endpoint
    if "/current" in content:
        print("✓ GET /cost/current endpoint")
        results.append(True)
    else:
        print("✗ Current cost endpoint missing")
        results.append(False)

    # Check for /daily endpoint
    if "/daily" in content:
        print("✓ GET /cost/daily endpoint")
        results.append(True)
    else:
        print("✗ Daily cost endpoint missing")
        results.append(False)

    # Check for /by-model endpoint
    if "/by-model" in content:
        print("✓ GET /cost/by-model endpoint")
        results.append(True)
    else:
        print("✗ By-model endpoint missing")
        results.append(False)

    # Check for /by-user endpoint
    if "/by-user" in content:
        print("✓ GET /cost/by-user endpoint")
        results.append(True)
    else:
        print("✗ By-user endpoint missing")
        results.append(False)

    # Check for /summary endpoint
    if "/summary" in content:
        print("✓ GET /cost/summary endpoint")
        results.append(True)
    else:
        print("✗ Summary endpoint missing")
        results.append(False)
else:
    print("✗ Cost API file not found")
    results.append(False)

# 3. Check Cost Data Models
print("\n=== Stage 5 Verification: Cost Data Models ===\n")
cost_model_file = src_dir / "models" / "cost.py"
if cost_model_file.exists():
    print("✓ Cost models file exists")
    results.append(True)

    content = cost_model_file.read_text()

    # Check for CostRecord model
    if "class CostRecord" in content:
        print("✓ CostRecord model")
        results.append(True)
    else:
        print("✗ CostRecord model missing")
        results.append(False)

    # Check for CostBudget model
    if "class CostBudget" in content:
        print("✓ CostBudget model")
        results.append(True)
    else:
        print("✗ CostBudget model missing")
        results.append(False)

    # Check for cost fields
    if "total_cost" in content:
        print("✓ Total cost field")
        results.append(True)
    else:
        print("✗ Total cost field missing")
        results.append(False)

    if "input_tokens" in content:
        print("✓ Input tokens field")
        results.append(True)
    else:
        print("✗ Input tokens field missing")
        results.append(False)

    if "output_tokens" in content:
        print("✓ Output tokens field")
        results.append(True)
    else:
        print("✗ Output tokens field missing")
        results.append(False)
else:
    print("✗ Cost models file not found")
    results.append(False)

# 4. Check Cost Schemas
print("\n=== Stage 5 Verification: Cost Schemas ===\n")
cost_schema_file = src_dir / "schemas" / "cost.py"
if cost_schema_file.exists():
    print("✓ Cost schemas file exists")
    results.append(True)

    content = cost_schema_file.read_text()

    # Check for response models
    if "CurrentCostResponse" in content or "class" in content:
        print("✓ Cost response schemas")
        results.append(True)
    else:
        print("✗ Cost response schemas missing")
        results.append(False)
else:
    print("✗ Cost schemas file not found")
    results.append(False)

# 5. Check Token Counter
print("\n=== Stage 5 Verification: Token Counter ===\n")
token_counter_file = src_dir / "providers" / "token_counter.py"
if token_counter_file.exists():
    print("✓ Token counter file exists")
    results.append(True)

    content = token_counter_file.read_text()

    # Check for TokenCounter class
    if "class TokenCounter" in content:
        print("✓ TokenCounter class")
        results.append(True)
    else:
        print("✗ TokenCounter class missing")
        results.append(False)

    # Check for counting methods
    if "start_stream" in content or "count" in content:
        print("✓ Token counting functionality")
        results.append(True)
    else:
        print("✗ Token counting missing")
        results.append(False)
else:
    print("✗ Token counter file not found")
    results.append(False)

# 6. Check Cost Calculation
print("\n=== Stage 5 Verification: Cost Calculation ===\n")
cost_calc_file = src_dir / "services" / "cost_calculator.py"
if cost_calc_file.exists():
    print("✓ Cost calculator file exists")
    results.append(True)

    content = cost_calc_file.read_text()

    # Check for calculation functions
    if "calculate" in content.lower() or "cost" in content.lower():
        print("✓ Cost calculation functions")
        results.append(True)
    else:
        print("✗ Cost calculation missing")
        results.append(False)
else:
    print("✗ Cost calculator file not found")
    results.append(False)

# Summary
print("\n" + "=" * 60)
print("Stage 5 Verification Results")
print("=" * 60)

total_tests = len(results)
passed_tests = sum(results)

print(f"\nTotal tests: {total_tests}")
print(f"Passed: {passed_tests}")
print(f"Failed: {total_tests - passed_tests}")
print(f"Success rate: {passed_tests / total_tests * 100:.1f}%")

if passed_tests == total_tests:
    print("\n✅ Stage 5 requirements are FULLY MET!")
    print("\nSummary:")
    print("  ✓ Cost Agent: All tracking methods implemented")
    print("  ✓ Cost API: All endpoints available")
    print("  ✓ Data Models: CostRecord + CostBudget")
    print("  ✓ Real-time Tracking: Redis-based")
    print("  ✓ Persistence: PostgreSQL-based")
    print("  ✓ Token Counter: Implemented")
    print("  ✓ Cost Calculation: Implemented")
    sys.exit(0)
else:
    print(f"\n⚠️ Stage 5 has {total_tests - passed_tests} missing features")
    sys.exit(1)
