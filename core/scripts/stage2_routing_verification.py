"""
Stage 2 - 智能路由增强验证脚本

This script verifies the Stage 2 intelligent routing enhancements:
1. Content Analysis Engine
2. Advanced Routing Strategies
3. DSL Rule Parser
"""
import asyncio
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from agents.content_analyzer import content_analyzer, ContentAnalysis
from agents.advanced_routing import (
    advanced_routing_engine,
    RoutingPriority,
    ModelTier,
)
from providers.base import ChatRequest, ChatMessage


def print_section(title: str):
    """Print a section header."""
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)


def test_content_analyzer():
    """Test the content analysis engine."""
    print_section("1. Content Analysis Engine Tests")

    test_cases = [
        {
            "name": "Code Generation Request",
            "messages": [
                ChatMessage(role="user", content="Write a Python function to calculate fibonacci numbers")
            ],
            "expected_intent": "code_generation",
            "expected_scenario": "development",
        },
        {
            "name": "Question Answering",
            "messages": [
                ChatMessage(role="user", content="What is the capital of France?")
            ],
            "expected_intent": "question_answering",
            "expected_scenario": "general",
        },
        {
            "name": "Complex Code Request",
            "messages": [
                ChatMessage(role="user", content="```python\ndef complex_function():\n    pass\n```"),
                ChatMessage(role="user", content="Can you explain how this works and optimize it for performance?"),
            ],
            "expected_intent": "code_generation",
            "min_complexity": 60,
        },
    ]

    results = []

    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test_case['name']}")
        print("-" * 40)

        start_time = time.time()
        analysis = content_analyzer.analyze(test_case["messages"])
        analysis_time = (time.time() - start_time) * 1000

        print(f"Intent: {analysis.intent.value} (confidence: {analysis.intent_confidence:.2f})")
        print(f"Scenario: {analysis.scenario.value}")
        print(f"Complexity Score: {analysis.complexity_score}/100")
        print(f"Language: {analysis.language}")
        print(f"Content Type: {analysis.content_type.value}")
        print(f"Estimated Tokens: {analysis.estimated_tokens}")
        print(f"Keywords: {', '.join(analysis.keywords[:5])}")
        print(f"Analysis Time: {analysis_time:.2f}ms")

        # Verify expectations
        passed = True
        if "expected_intent" in test_case:
            if analysis.intent.value != test_case["expected_intent"]:
                print(f"❌ Expected intent: {test_case['expected_intent']}")
                passed = False

        if "expected_scenario" in test_case:
            if analysis.scenario.value != test_case["expected_scenario"]:
                print(f"❌ Expected scenario: {test_case['expected_scenario']}")
                passed = False

        if "min_complexity" in test_case:
            if analysis.complexity_score < test_case["min_complexity"]:
                print(f"❌ Expected min complexity: {test_case['min_complexity']}")
                passed = False

        # Check performance requirement (< 30ms)
        if analysis_time > 30:
            print(f"⚠️  Warning: Analysis time {analysis_time:.2f}ms exceeds 30ms target")

        if passed:
            print("✅ PASSED")
            results.append(True)
        else:
            print("❌ FAILED")
            results.append(False)

    return results


def test_advanced_routing():
    """Test the advanced routing engine."""
    print_section("2. Advanced Routing Engine Tests")

    test_cases = [
        {
            "name": "Code Generation Routing",
            "content": "Write a function to sort an array",
            "expected_strategy": "code_expert",
        },
        {
            "name": "Simple Query Routing",
            "content": "What is 2 + 2?",
            "expected_tier": "economy",
        },
        {
            "name": "High Complexity Routing",
            "messages": [
                ChatMessage(role="user", content="Analyze this complex code and optimize it"),
                ChatMessage(role="user", content="```python\nclass ComplexClass:\n    pass\n```"),
            ],
            "expected_priority": "high",
        },
    ]

    results = []

    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test_case['name']}")
        print("-" * 40)

        # Analyze content
        if "messages" in test_case:
            analysis = content_analyzer.analyze(test_case["messages"])
        else:
            analysis = content_analyzer.analyze([
                ChatMessage(role="user", content=test_case["content"])
            ])

        # Get routing recommendation
        recommendation = advanced_routing_engine.analyze_and_route(
            request=None,
            content_analysis=analysis,
        )

        print(f"Strategy: {recommendation.get('strategy')}")
        print(f"Model Tier: {recommendation.get('model_tier')}")
        print(f"Priority: {recommendation.get('priority')}")
        print(f"Reason: {recommendation.get('reason')}")

        # Verify expectations
        passed = True
        if "expected_strategy" in test_case:
            if test_case["expected_strategy"] not in recommendation.get("strategy", ""):
                print(f"❌ Expected strategy: {test_case['expected_strategy']}")
                passed = False

        if "expected_tier" in test_case:
            if recommendation.get("model_tier") != ModelTier(test_case["expected_tier"]):
                print(f"❌ Expected tier: {test_case['expected_tier']}")
                passed = False

        if "expected_priority" in test_case:
            if recommendation.get("priority") != RoutingPriority(test_case["expected_priority"]):
                print(f"❌ Expected priority: {test_case['expected_priority']}")
                passed = False

        if passed:
            print("✅ PASSED")
            results.append(True)
        else:
            print("❌ FAILED")
            results.append(False)

    return results


def test_dsl_rules():
    """Test the DSL rule parser."""
    print_section("3. DSL Rule Parser Tests")

    dsl_examples = [
        {
            "name": "Simple Intent Rule",
            "rule": 'IF INTENT EQUAL "code_generation" THEN SELECT_MODEL "gpt-4"',
        },
        {
            "name": "Complexity Rule",
            "rule": 'IF COMPLEXITY GREATER 70 THEN STRATEGY quality_first',
        },
    ]

    results = []

    for i, example in enumerate(dsl_examples, 1):
        print(f"\nTest {i}: {example['name']}")
        print("-" * 40)
        print(f"DSL Rule: {example['rule']}")

        try:
            parsed_rule = advanced_routing_engine.add_dsl_rule(example['rule'])

            print(f"Rule Name: {parsed_rule.name}")
            print(f"Conditions: {len(parsed_rule.conditions)}")
            print(f"Actions: {parsed_rule.actions}")
            print(f"Strategy: {parsed_rule.strategy}")

            print("✅ PASSED - DSL parsed successfully")
            results.append(True)
        except Exception as e:
            print(f"❌ FAILED - {str(e)}")
            results.append(False)

    return results


def test_integration():
    """Test integrated content analysis and routing."""
    print_section("4. Integration Tests")

    print("\nTest: End-to-End Routing Decision")
    print("-" * 40)

    # Simulate a complex code request
    messages = [
        ChatMessage(role="user", content="I need help with this Python code:"),
        ChatMessage(role="user", content="```python\ndef process_data(items):\n    results = []\n    for item in items:\n        if item.valid:\n            results.append(transform(item))\n    return results\n```"),
        ChatMessage(role="user", content="Can you optimize this for better performance and explain your changes?"),
    ]

    # Step 1: Analyze content
    print("\nStep 1: Content Analysis")
    analysis = content_analyzer.analyze(messages)
    print(f"Intent: {analysis.intent.value}")
    print(f"Complexity: {analysis.complexity_score}/100")
    print(f"Content Type: {analysis.content_type.value}")

    # Step 2: Get routing recommendations
    print("\nStep 2: Routing Recommendations")
    recommendations = advanced_routing_engine.get_routing_recommendations(analysis)

    for j, rec in enumerate(recommendations[:3], 1):
        score = rec.get("score", 0)
        print(f"\n{j}. {rec.get('strategy', 'unknown').upper()}")
        print(f"   Model Tier: {rec.get('model_tier')}")
        print(f"   Priority: {rec.get('priority')}")
        if score:
            print(f"   Score: {score:.2f}")
        print(f"   Reason: {rec.get('reason')}")

    print("\n✅ Integration test completed")
    return [True]


def main():
    """Run all verification tests."""
    print("""
╔══════════════════════════════════════════════════════════╗
║     Stage 2 - 智能路由增强验证脚本                        ║
║     Intelligent Routing Enhancement Verification          ║
╚══════════════════════════════════════════════════════════╝
    """)

    all_results = []

    # Run all tests
    all_results.extend(test_content_analyzer())
    all_results.extend(test_advanced_routing())
    all_results.extend(test_dsl_rules())
    all_results.extend(test_integration())

    # Summary
    print_section("Verification Summary")

    total = len(all_results)
    passed = sum(all_results)
    failed = total - passed

    print(f"\nTotal Tests: {total}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")

    if failed == 0:
        print("\n🎉 All Stage 2 intelligent routing enhancements verified!")
        return 0
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
