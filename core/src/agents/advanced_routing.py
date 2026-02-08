"""
Advanced Routing Strategies - Enhanced routing with intelligent decision making.

This module provides:
- Complexity-based dynamic routing
- Content-type aware routing
- Business priority routing
- Custom rule DSL parser and evaluator
"""
import re
import time
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum

try:
    from .content_analyzer import (
        ContentAnalysis,
        content_analyzer,
        IntentType,
        ScenarioType,
        ContentType,
    )
    from ..providers.base import ChatRequest
except ImportError:
    from src.agents.content_analyzer import (
        ContentAnalysis,
        content_analyzer,
        IntentType,
        ScenarioType,
        ContentType,
    )
    from src.providers.base import ChatRequest


class RoutingPriority(str, Enum):
    """Routing priority levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ModelTier(str, Enum):
    """Model capability tiers."""
    PREMIUM = "premium"  # Best quality, high cost (e.g., GPT-4, Claude Opus)
    STANDARD = "standard"  # Good quality, medium cost (e.g., GPT-3.5, Claude Sonnet)
    ECONOMY = "economy"  # Basic quality, low cost (e.g., Claude Haiku)


@dataclass
class RoutingStrategy:
    """Routing strategy configuration."""
    name: str
    priority: RoutingPriority
    model_tier: ModelTier
    max_latency_ms: int
    max_cost_per_1k: float
    required_features: List[str]
    exclude_scenarios: List[ScenarioType]


@dataclass
class DSLRule:
    """Parsed DSL rule."""
    name: str
    priority: int
    conditions: List[Dict[str, Any]]
    actions: Dict[str, Any]
    strategy: str


class DSLLexer:
    """Lexer for custom routing DSL."""

    # Token types
    TOKENS = {
        "IF", "THEN", "AND", "OR", "NOT",
        "INTENT", "SCENARIO", "COMPLEXITY", "LANGUAGE", "TYPE",
        "GREATER", "LESS", "EQUAL", "CONTAINS",
        "NUMBER", "STRING", "LPAREN", "RPAREN",
        "SELECT_MODEL", "SELECT_PROVIDER", "STRATEGY",
        "PRIORITY", "BUDGET",
    }

    def __init__(self, text: str):
        """Initialize lexer."""
        self.text = text
        self.pos = 0
        self.tokens = self._tokenize()

    def _tokenize(self) -> List[tuple]:
        """Tokenize the input text."""
        tokens = []
        while self.pos < len(self.text):
            self._skip_whitespace()

            if self.pos >= len(self.text):
                break

            # Skip comments
            if self.text[self.pos:self.pos + 2] == "//":
                self._skip_line()
                continue

            # Numbers
            if self.text[self.pos].isdigit():
                tokens.append(("NUMBER", self._read_number()))
                continue

            # Strings
            if self.text[self.pos] in ['"', "'"]:
                tokens.append(("STRING", self._read_string()))
                continue

            # Keywords and identifiers
            word = self._read_word()
            if word in self.TOKENS:
                tokens.append((word, word))
            elif word:
                tokens.append(("IDENTIFIER", word))

            # Symbols
            if self.pos < len(self.text):
                char = self.text[self.pos]
                if char == "(":
                    tokens.append(("LPAREN", char))
                    self.pos += 1
                elif char == ")":
                    tokens.append(("RPAREN", char))
                    self.pos += 1
                elif char == ">":
                    if self.pos + 1 < len(self.text) and self.text[self.pos + 1] == "=":
                        tokens.append(("GREATER", ">="))
                        self.pos += 2
                    else:
                        tokens.append(("GREATER", ">"))
                        self.pos += 1
                elif char == "<":
                    if self.pos + 1 < len(self.text) and self.text[self.pos + 1] == "=":
                        tokens.append(("LESS", "<="))
                        self.pos += 2
                    else:
                        tokens.append(("LESS", "<"))
                        self.pos += 1
                elif char == "=":
                    tokens.append(("EQUAL", "="))
                    self.pos += 1

        return tokens

    def _skip_whitespace(self):
        """Skip whitespace characters."""
        while self.pos < len(self.text) and self.text[self.pos].isspace():
            self.pos += 1

    def _skip_line(self):
        """Skip to end of line."""
        while self.pos < len(self.text) and self.text[self.pos] != "\n":
            self.pos += 1

    def _read_number(self) -> str:
        """Read a number."""
        start = self.pos
        while self.pos < len(self.text) and (
            self.text[self.pos].isdigit() or self.text[self.pos] == "."
        ):
            self.pos += 1
        return self.text[start:self.pos]

    def _read_string(self) -> str:
        """Read a string literal."""
        quote = self.text[self.pos]
        self.pos += 1
        start = self.pos
        while self.pos < len(self.text) and self.text[self.pos] != quote:
            if self.text[self.pos] == "\\":
                self.pos += 2
            else:
                self.pos += 1
        value = self.text[start:self.pos]
        self.pos += 1  # Skip closing quote
        return value

    def _read_word(self) -> str:
        """Read a word or keyword."""
        start = self.pos
        while self.pos < len(self.text) and (
            self.text[self.pos].isalnum() or self.text[self.pos] == "_"
        ):
            self.pos += 1
        return self.text[start:self.pos].lower()


class DSLParser:
    """Parser for custom routing DSL."""

    def parse(self, text: str) -> DSLRule:
        """Parse DSL text into a rule."""
        lexer = DSLLexer(text)
        tokens = lexer.tokens

        # Simple parsing (for demonstration)
        # In production, use proper parser (e.g., PLY, ANTLR)
        name = "dsl_rule"
        priority = 50
        conditions = []
        actions = {}
        strategy = "standard"

        i = 0
        while i < len(tokens):
            token_type, token_value = tokens[i]

            if token_type == "IF":
                # Parse condition
                i += 1
                condition = self._parse_condition(tokens, i)
                if condition:
                    conditions.append(condition)

            elif token_type == "THEN":
                # Parse action
                i += 1
                action = self._parse_action(tokens, i)
                if action:
                    actions.update(action)

            elif token_type == "STRATEGY":
                i += 1
                if i < len(tokens):
                    _, strategy = tokens[i]
                    i += 1

            i += 1

        return DSLRule(
            name=name,
            priority=priority,
            conditions=conditions,
            actions=actions,
            strategy=strategy,
        )

    def _parse_condition(self, tokens: List[tuple], pos: int) -> Optional[Dict]:
        """Parse a condition."""
        if pos >= len(tokens):
            return None

        token_type, token_value = tokens[pos]

        # Simple pattern matching for demo
        # INTENT EQUAL "code_generation"
        if token_type == "INTENT" and pos + 2 < len(tokens):
            if tokens[pos + 1][0] == "EQUAL":
                return {
                    "type": "intent",
                    "operator": "==",
                    "value": tokens[pos + 2][1],
                }

        # COMPLEXITY GREATER 70
        elif token_type == "COMPLEXITY" and pos + 1 < len(tokens):
            return {
                "type": "complexity",
                "operator": tokens[pos + 1][0],
                "value": tokens[pos + 2][1] if pos + 2 < len(tokens) else 0,
            }

        return None

    def _parse_action(self, tokens: List[tuple], pos: int) -> Optional[Dict]:
        """Parse an action."""
        if pos >= len(tokens):
            return None

        token_type, token_value = tokens[pos]

        # SELECT_MODEL "gpt-4"
        if token_type == "SELECT_MODEL" and pos + 1 < len(tokens):
            return {"model": tokens[pos + 1][1]}

        # SELECT_PROVIDER 1
        elif token_type == "SELECT_PROVIDER" and pos + 1 < len(tokens):
            return {"provider": int(tokens[pos + 1][1])}

        return None


class AdvancedRoutingEngine:
    """
    Advanced routing engine with intelligent strategies.

    Features:
    - Content analysis based routing
    - Complexity-aware model selection
    - Priority-based routing
    - Custom DSL rule evaluation
    """

    # Predefined routing strategies
    STRATEGIES = {
        "quality_first": RoutingStrategy(
            name="quality_first",
            priority=RoutingPriority.HIGH,
            model_tier=ModelTier.PREMIUM,
            max_latency_ms=5000,
            max_cost_per_1k=0.05,
            required_features=[],
            exclude_scenarios=[],
        ),
        "balanced": RoutingStrategy(
            name="balanced",
            priority=RoutingPriority.MEDIUM,
            model_tier=ModelTier.STANDARD,
            max_latency_ms=2000,
            max_cost_per_1k=0.01,
            required_features=[],
            exclude_scenarios=[],
        ),
        "cost_optimized": RoutingStrategy(
            name="cost_optimized",
            priority=RoutingPriority.LOW,
            model_tier=ModelTier.ECONOMY,
            max_latency_ms=3000,
            max_cost_per_1k=0.005,
            required_features=[],
            exclude_scenarios=[],
        ),
        "code_expert": RoutingStrategy(
            name="code_expert",
            priority=RoutingPriority.HIGH,
            model_tier=ModelTier.PREMIUM,
            max_latency_ms=5000,
            max_cost_per_1k=0.05,
            required_features=["code_generation"],
            exclude_scenarios=[],
        ),
        "rapid_response": RoutingStrategy(
            name="rapid_response",
            priority=RoutingPriority.MEDIUM,
            model_tier=ModelTier.ECONOMY,
            max_latency_ms=1000,
            max_cost_per_1k=0.005,
            required_features=[],
            exclude_scenarios=[ScenarioType.DEVELOPMENT],
        ),
    }

    def __init__(self):
        """Initialize the advanced routing engine."""
        self.dsl_parser = DSLParser()
        self._custom_dsl_rules: List[DSLRule] = []

    def add_dsl_rule(self, rule_text: str) -> DSLRule:
        """Add a custom DSL rule."""
        rule = self.dsl_parser.parse(rule_text)
        self._custom_dsl_rules.append(rule)
        return rule

    def analyze_and_route(
        self,
        request: ChatRequest,
        content_analysis: ContentAnalysis,
    ) -> Dict[str, Any]:
        """
        Analyze content and determine optimal routing strategy.

        Args:
            request: Chat request
            content_analysis: Pre-computed content analysis

        Returns:
            Dict with routing recommendations
        """
        # Determine strategy based on content analysis
        strategy = self._select_strategy(content_analysis)

        # Get model tier preferences
        model_tier = strategy.model_tier

        # Check DSL rules
        dsl_matches = self._evaluate_dsl_rules(content_analysis)

        if dsl_matches:
            # Use highest priority DSL rule match
            dsl_match = max(dsl_matches, key=lambda r: r.priority)
            return {
                "strategy": "dsl_custom",
                "model_tier": model_tier,
                "priority": RoutingPriority.HIGH,
                "matched_dsl_rule": dsl_match.name,
                "actions": dsl_match.actions,
                "reason": f"DSL rule matched: {dsl_match.name}",
            }

        # Complexity-based routing
        if content_analysis.complexity_score > 70:
            return {
                "strategy": "complexity_high",
                "model_tier": ModelTier.PREMIUM,
                "priority": RoutingPriority.HIGH,
                "reason": "High complexity request requires premium model",
            }
        elif content_analysis.complexity_score > 40:
            return {
                "strategy": "complexity_medium",
                "model_tier": ModelTier.STANDARD,
                "priority": RoutingPriority.MEDIUM,
                "reason": "Medium complexity request suitable for standard model",
            }

        # Intent-based routing
        if content_analysis.intent == IntentType.CODE_GENERATION:
            return {
                "strategy": "code_expert",
                "model_tier": ModelTier.PREMIUM,
                "priority": RoutingPriority.HIGH,
                "reason": "Code generation requires premium model",
            }

        # Scenario-based routing
        if content_analysis.scenario == ScenarioType.DEVELOPMENT:
            return {
                "strategy": "code_expert",
                "model_tier": ModelTier.STANDARD,
                "priority": RoutingPriority.HIGH,
                "reason": "Development scenario requires code-capable model",
            }

        # Default: use selected strategy
        return {
            "strategy": strategy.name,
            "model_tier": model_tier,
            "priority": strategy.priority,
            "max_latency_ms": strategy.max_latency_ms,
            "max_cost_per_1k": strategy.max_cost_per_1k,
            "reason": f"Using {strategy.name} strategy based on content analysis",
        }

    def _select_strategy(self, analysis: ContentAnalysis) -> RoutingStrategy:
        """Select appropriate routing strategy."""
        # Check if critical features are required
        if analysis.complexity_score > 70:
            return self.STRATEGIES["quality_first"]

        # Check content type
        if analysis.content_type == ContentType.CODE:
            return self.STRATEGIES["code_expert"]

        # Check scenario
        if analysis.scenario == ScenarioType.SUPPORT:
            return self.STRATEGIES["rapid_response"]

        # Default to balanced
        return self.STRATEGIES["balanced"]

    def _evaluate_dsl_rules(
        self,
        analysis: ContentAnalysis,
    ) -> List[DSLRule]:
        """Evaluate custom DSL rules against content analysis."""
        matches = []

        for rule in self._custom_dsl_rules:
            if self._evaluate_dsl_rule(rule, analysis):
                matches.append(rule)

        return matches

    def _evaluate_dsl_rule(
        self,
        rule: DSLRule,
        analysis: ContentAnalysis,
    ) -> bool:
        """Evaluate a single DSL rule."""
        for condition in rule.conditions:
            if not self._evaluate_condition(condition, analysis):
                return False
        return True

    def _evaluate_condition(
        self,
        condition: Dict,
        analysis: ContentAnalysis,
    ) -> bool:
        """Evaluate a single condition."""
        cond_type = condition["type"]
        operator = condition["operator"]
        value = condition["value"]

        if cond_type == "intent":
            if operator == "==":
                return analysis.intent.value == value
            elif operator == "!=":
                return analysis.intent.value != value

        elif cond_type == "complexity":
            if operator in (">", "GREATER"):
                return analysis.complexity_score > int(value)
            elif operator in ("<", "LESS"):
                return analysis.complexity_score < int(value)
            elif operator in (">=", "GREATER"):
                return analysis.complexity_score >= int(value)
            elif operator in ("<=", "LESS"):
                return analysis.complexity_score <= int(value)
            elif operator in ("==", "EQUAL"):
                return analysis.complexity_score == int(value)

        elif cond_type == "scenario":
            if operator == "==":
                return analysis.scenario.value == value

        elif cond_type == "language":
            if operator == "==":
                return analysis.language == value

        return False

    def get_routing_recommendations(
        self,
        analysis: ContentAnalysis,
    ) -> List[Dict[str, Any]]:
        """
        Get all routing recommendations ranked by priority.

        Returns:
            List of routing recommendations with scores
        """
        recommendations = []

        # Base recommendation
        base_rec = self.analyze_and_route(
            request=None,  # Not needed for analysis-based routing
            content_analysis=analysis,
        )
        recommendations.append(base_rec)

        # Add alternative strategies with scores
        for strategy_name, strategy in self.STRATEGIES.items():
            if strategy_name != base_rec.get("strategy"):
                score = self._calculate_strategy_score(strategy, analysis)
                recommendations.append({
                    "strategy": strategy_name,
                    "model_tier": strategy.model_tier.value,
                    "priority": strategy.priority.value,
                    "score": score,
                    "reason": f"Alternative strategy with score {score:.2f}",
                })

        # Sort by score
        recommendations.sort(key=lambda r: r.get("score", 0), reverse=True)

        return recommendations

    def _calculate_strategy_score(
        self,
        strategy: RoutingStrategy,
        analysis: ContentAnalysis,
    ) -> float:
        """Calculate a score for how well a strategy fits the analysis."""
        score = 0.0

        # Complexity match
        if analysis.complexity_score > 70 and strategy.model_tier == ModelTier.PREMIUM:
            score += 0.4
        elif analysis.complexity_score < 40 and strategy.model_tier == ModelTier.ECONOMY:
            score += 0.3

        # Priority match
        if strategy.priority == RoutingPriority.HIGH:
            score += 0.2

        # Feature requirements
        for feature in strategy.required_features:
            if feature == "code_generation" and analysis.intent == IntentType.CODE_GENERATION:
                score += 0.2

        # Scenario exclusions
        if analysis.scenario in strategy.exclude_scenarios:
            score -= 0.5

        return max(0.0, min(1.0, score))


# Global instance
advanced_routing_engine = AdvancedRoutingEngine()
