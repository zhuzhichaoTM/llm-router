"""
Content Analysis Engine - Analyzes LLM requests for intelligent routing.

This module provides:
- Intent recognition
- Complexity scoring
- Scenario classification
- Multi-language detection
- Content type detection
"""
import re
import time
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum
from collections import Counter


class IntentType(str, Enum):
    """Intent types for classification."""
    CODE_GENERATION = "code_generation"
    QUESTION_ANSWERING = "question_answering"
    CONTENT_CREATION = "content_creation"
    TRANSLATION = "translation"
    SUMMARIZATION = "summarization"
    ANALYSIS = "analysis"
    CONVERSATION = "conversation"
    GENERAL = "general"


class ScenarioType(str, Enum):
    """Scenario types for classification."""
    DEVELOPMENT = "development"
    BUSINESS = "business"
    EDUCATION = "education"
    CREATIVE = "creative"
    RESEARCH = "research"
    SUPPORT = "support"
    GENERAL = "general"


class ContentType(str, Enum):
    """Content types."""
    CODE = "code"
    TEXT = "text"
    DATA = "data"
    MIXED = "mixed"


@dataclass
class ContentAnalysis:
    """Result of content analysis."""
    intent: IntentType
    intent_confidence: float
    scenario: ScenarioType
    complexity_score: int  # 0-100
    language: str
    content_type: ContentType
    keywords: List[str]
    estimated_tokens: int
    features: Dict[str, Any]


class ContentAnalyzer:
    """
    Content Analysis Engine for intelligent routing.

    Uses heuristic-based analysis for fast, accurate routing decisions.
    Performance target: < 30ms analysis time.
    """

    # Intent detection patterns
    INTENT_PATTERNS = {
        IntentType.CODE_GENERATION: [
            r"\b(write|create|generate|implement|develop|code|function|class|method)\s+(code|function|class|method|script|program)\b",
            r"\b(def |class |import |from |func |const |let |var |return |if |for |while )",
            r"```[\w]*\n[\s\S]*?```",
            r"<code>[\s\S]*?</code>",
        ],
        IntentType.QUESTION_ANSWERING: [
            r"\?+\s*$",
            r"\b(what|how|why|when|where|who|which|explain|describe|tell me)\b",
        ],
        IntentType.CONTENT_CREATION: [
            r"\b(write|create|generate|compose|draft)\s+(article|blog|story|essay|content|post|text)\b",
            r"\b(writing|content|story|article|blog|essay)\b",
        ],
        IntentType.TRANSLATION: [
            r"\b(translate|translation|translate to|in \w+\b)\s*(to|into|from)\b",
            r"\b翻译|翻译成|把.*翻译",
        ],
        IntentType.SUMMARIZATION: [
            r"\b(summarize|summary|summar|brief|outline|recap|tldr)\b",
            r"\b(总结|摘要|概述|简述)\b",
        ],
        IntentType.ANALYSIS: [
            r"\b(analyze|analysis|compare|contrast|evaluate|assess)\b",
            r"\b(分析|对比|评估)\b",
        ],
    }

    # Scenario detection patterns
    SCENARIO_PATTERNS = {
        ScenarioType.DEVELOPMENT: [
            r"\b(bug|debug|api|database|server|client|frontend|backend|deployment|test|testing)\b",
            r"\b(function|class|method|variable|algorithm|data structure)\b",
            r"\b(错误|调试|部署|测试|开发)\b",
        ],
        ScenarioType.BUSINESS: [
            r"\b(report|presentation|meeting|proposal|strategy|marketing|sales)\b",
            r"\b(报告|会议|提案|策略|营销|销售)\b",
        ],
        ScenarioType.EDUCATION: [
            r"\b(learn|study|teach|explain|understand|homework|assignment|course)\b",
            r"\b(学习|教学|作业|课程)\b",
        ],
        ScenarioType.CREATIVE: [
            r"\b(story|poem|creative|imagine|fiction|character|plot)\b",
            r"\b(故事|诗歌|创意|小说)\b",
        ],
        ScenarioType.RESEARCH: [
            r"\b(research|paper|study|experiment|hypothesis|data|statistics)\b",
            r"\b(研究|论文|实验|假设)\b",
        ],
        ScenarioType.SUPPORT: [
            r"\b(help|support|issue|problem|error|troubleshoot|fix)\b",
            r"\b(帮助|支持|问题|故障)\b",
        ],
    }

    # Language detection patterns
    LANGUAGE_PATTERNS = {
        "python": r"\b(def |import |from |print|class |if __name__)\b",
        "javascript": r"\b(function|const|let|var|=>|console\.|async|await)\b",
        "java": r"\b(public|private|class |void|int|String|System\.out)\b",
        "cpp": r"\b(#include|using namespace|std::|cout|cin|vector)\b",
        "go": r"\b(func |package|import|fmt\.|var |const |:=)\b",
        "rust": r"\b(fn |let |mut|pub |use |impl |struct )\b",
        "sql": r"\b(SELECT|INSERT|UPDATE|DELETE|FROM|WHERE|JOIN|GROUP BY)\b",
        "html": r"<(html|head|body|div|span|a|p|img)\b",
        "css": r"[\.\#][\w-]+\s*\{[\s\S]*?\}",
    }

    # Complexity indicators
    COMPLEXITY_INDICATORS = {
        "code_block": 30,
        "multiple_questions": 20,
        "technical_terms": 15,
        "foreign_language": 10,
        "long_request": 25,
        "structured_data": 20,
        "math_formula": 15,
    }

    def __init__(self):
        """Initialize the content analyzer."""
        # Compile regex patterns for performance
        self._compiled_intent_patterns = {}
        for intent, patterns in self.INTENT_PATTERNS.items():
            self._compiled_intent_patterns[intent] = [
                re.compile(pattern, re.IGNORECASE)
                for pattern in patterns
            ]

        self._compiled_scenario_patterns = {}
        for scenario, patterns in self.SCENARIO_PATTERNS.items():
            self._compiled_scenario_patterns[scenario] = [
                re.compile(pattern, re.IGNORECASE)
                for pattern in patterns
            ]

        self._compiled_language_patterns = {
            lang: re.compile(pattern, re.IGNORECASE)
            for lang, pattern in self.LANGUAGE_PATTERNS.items()
        }

    def analyze(
        self,
        messages: List[Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> ContentAnalysis:
        """
        Analyze chat request content for routing decisions.

        Args:
            messages: List of chat messages
            context: Optional context information

        Returns:
            ContentAnalysis: Analysis result
        """
        start_time = time.time()

        # Extract content
        content = self._extract_content(messages)

        # Detect intent
        intent, intent_confidence = self._detect_intent(content)

        # Detect scenario
        scenario = self._detect_scenario(content)

        # Calculate complexity
        complexity_score = self._calculate_complexity(content)

        # Detect language
        language = self._detect_language(content)

        # Detect content type
        content_type = self._detect_content_type(content)

        # Extract keywords
        keywords = self._extract_keywords(content)

        # Estimate tokens
        estimated_tokens = self._estimate_tokens(content)

        # Extract features
        features = self._extract_features(content, context)

        analysis_time = (time.time() - start_time) * 1000  # ms

        return ContentAnalysis(
            intent=intent,
            intent_confidence=intent_confidence,
            scenario=scenario,
            complexity_score=complexity_score,
            language=language,
            content_type=content_type,
            keywords=keywords,
            estimated_tokens=estimated_tokens,
            features={
                **features,
                "analysis_time_ms": round(analysis_time, 2),
            },
        )

    def _extract_content(self, messages: List[Any]) -> str:
        """Extract and combine content from messages."""
        return " ".join(
            msg.content if hasattr(msg, "content") else str(msg)
            for msg in messages
        )

    def _detect_intent(self, content: str) -> tuple[IntentType, float]:
        """Detect the primary intent of the request."""
        intent_scores = {}

        for intent, patterns in self._compiled_intent_patterns.items():
            matches = 0
            for pattern in patterns:
                if pattern.search(content):
                    matches += 1

            if matches > 0:
                # Normalize score based on number of patterns
                intent_scores[intent] = matches / len(patterns)

        if not intent_scores:
            return IntentType.GENERAL, 0.5

        # Get best intent
        best_intent = max(intent_scores, key=intent_scores.get)
        confidence = min(intent_scores[best_intent] * 1.5, 1.0)  # Boost confidence

        return best_intent, confidence

    def _detect_scenario(self, content: str) -> ScenarioType:
        """Detect the scenario/use case."""
        scenario_scores = {}

        for scenario, patterns in self._compiled_scenario_patterns.items():
            matches = sum(1 for pattern in patterns if pattern.search(content))
            if matches > 0:
                scenario_scores[scenario] = matches

        if not scenario_scores:
            return ScenarioType.GENERAL

        return max(scenario_scores, key=scenario_scores.get)

    def _calculate_complexity(self, content: str) -> int:
        """Calculate complexity score (0-100)."""
        score = 0

        # Base complexity from length
        length = len(content)
        if length > 500:
            score += self.COMPLEXITY_INDICATORS["long_request"]
        elif length > 200:
            score += 10

        # Code blocks
        if "```" in content or "<code>" in content:
            score += self.COMPLEXITY_INDICATORS["code_block"]

        # Multiple questions
        question_marks = content.count("?")
        if question_marks > 1:
            score += self.COMPLEXITY_INDICATORS["multiple_questions"]

        # Technical terms
        technical_count = sum(
            1 for term in ["api", "database", "algorithm", "function", "class"]
            if term.lower() in content.lower()
        )
        if technical_count > 2:
            score += self.COMPLEXITY_INDICATORS["technical_terms"]

        # Structured data (JSON, XML, etc.)
        if any(marker in content for marker in ["{", "}", "[", "]", "<", ">"]):
            score += self.COMPLEXITY_INDICATORS["structured_data"]

        # Math formulas
        if re.search(r'[=\+\-\*\/\^]+', content) and any(
            c in content for c in ["x", "y", "z", "∫", "∑", "√"]
        ):
            score += self.COMPLEXITY_INDICATORS["math_formula"]

        # Foreign language characters (non-ASCII)
        non_ascii = sum(1 for c in content if ord(c) > 127)
        if non_ascii > len(content) * 0.3:
            score += self.COMPLEXITY_INDICATORS["foreign_language"]

        return min(score, 100)

    def _detect_language(self, content: str) -> str:
        """Detect programming language or natural language."""
        # Check for code patterns first
        for lang, pattern in self._compiled_language_patterns.items():
            if pattern.search(content):
                return lang

        # Simple natural language detection
        if any(ord(c) > 127 for c in content):
            # Check for Chinese
            if any("\u4e00" <= c <= "\u9fff" for c in content):
                return "zh"
            # Check for Japanese
            if any("\u3040" <= c <= "\u309f" or "\u30a0" <= c <= "\u30ff" for c in content):
                return "ja"

        return "en"

    def _detect_content_type(self, content: str) -> ContentType:
        """Detect the type of content."""
        has_code = any(
            pattern.search(content)
            for pattern in self._compiled_language_patterns.values()
        )
        has_data = any(marker in content for marker in ["{", "[", "<", ">"])

        if has_code and has_data:
            return ContentType.MIXED
        elif has_code:
            return ContentType.CODE
        elif has_data:
            return ContentType.DATA
        else:
            return ContentType.TEXT

    def _extract_keywords(self, content: str) -> List[str]:
        """Extract important keywords from content."""
        # Simple keyword extraction
        words = re.findall(r'\b[a-zA-Z]{4,}\b', content.lower())

        # Filter common words
        stop_words = {
            "this", "that", "with", "from", "have", "will", "would", "could",
            "should", "what", "when", "where", "which", "their", "about",
        }

        keywords = [w for w in words if w not in stop_words]

        # Return top keywords by frequency
        counter = Counter(keywords)
        return [word for word, _ in counter.most_common(10)]

    def _estimate_tokens(self, content: str) -> int:
        """Estimate token count (rough approximation)."""
        # Rough estimate: ~4 characters per token for English
        # For code, it's less efficient
        if self._detect_content_type(content) == ContentType.CODE:
            return len(content) // 3
        else:
            return len(content) // 4

    def _extract_features(
        self,
        content: str,
        context: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Extract additional features for routing."""
        features = {}

        # Message count
        features["message_count"] = content.count(".") + content.count("?") + content.count("!")

        # Has code block
        features["has_code_block"] = "```" in content or "<code>" in content

        # Has structured data
        features["has_structured_data"] = any(
            marker in content for marker in ["{", "[", "]", "}"]
        )

        # Urgency indicators
        urgent_words = ["urgent", "asap", "immediately", "紧急", "立即"]
        features["is_urgent"] = any(word in content.lower() for word in urgent_words)

        # Context features
        if context:
            features["context_keys"] = list(context.keys())
            if "user_id" in context:
                features["has_user_context"] = True
            if "history" in context:
                features["has_history"] = True

        return features


# Global instance
content_analyzer = ContentAnalyzer()
