"""
Routing Agent - Handles routing decisions and load balancing.
"""
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.redis_config import RedisConfig, RedisKeys
from src.config.settings import settings
from src.providers.base import IProvider, ProviderError, ChatRequest, ChatResponse
from src.providers.factory import ProviderFactory
from src.models.provider import Provider, ProviderModel, ProviderStatus
from src.models.routing import RoutingRule, RoutingDecision
from src.db.session import SessionManager
from src.utils.encryption import hash_content, generate_session_id, sanitize_for_logging


class RoutingMethod(str, Enum):
    """Routing method types."""
    CONTENT_ANALYSIS = "content_analysis"
    RULE_BASED = "rule_based"
    ROUND_ROBIN = "round_robin"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    LEAST_LATENCY = "least_latency"
    FIXED = "fixed"


@dataclass
class RouteDecision:
    """Route decision data."""
    provider_id: int
    model_id: str
    rule_id: Optional[int]
    method: str
    reason: str


@dataclass
class RouteResult:
    """Route execution result."""
    success: bool
    response: Optional[ChatResponse]
    provider_id: int
    model_id: str
    latency_ms: int
    input_tokens: int
    output_tokens: int
    cost: float
    error_message: Optional[str]


class RoutingAgent:
    """
    Routing Agent handles intelligent routing decisions.

    Features:
    - Rule-based routing
    - Content analysis routing
    - Load balancing (round robin, weighted, least latency)
    - Simple retry logic
    """

    _instance: Optional["RoutingAgent"] = None

    def __new__(cls) -> "RoutingAgent":
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the routing agent."""
        if self._initialized:
            return

        self._initialized = True
        self._round_robin_index = 0
        self._providers_cache: Dict[int, IProvider] = {}
        self._provider_models_cache: Dict[int, Dict[str, str]] = {}

    async def initialize(self) -> None:
        """Initialize the routing agent."""
        # Load active providers
        await self._refresh_providers()

    async def _refresh_providers(self) -> None:
        """Refresh providers cache."""
        from sqlalchemy import select

        providers = await SessionManager.execute_select(
            select(Provider).where(Provider.status == ProviderStatus.ACTIVE),
        )

        for provider in providers:
            try:
                # Create provider instance
                provider_instance = self._create_provider_instance(provider)
                self._providers_cache[provider.id] = provider_instance

                # Cache models - fetch separately to avoid lazy loading
                models = await SessionManager.execute_select(
                    select(ProviderModel).where(
                        ProviderModel.provider_id == provider.id,
                        ProviderModel.is_active == True
                    )
                )
                self._provider_models_cache[provider.id] = {
                    model.model_id: model.id
                    for model in models
                }

            except Exception:
                # Skip providers that fail to initialize
                continue

    def _create_provider_instance(self, provider: Provider) -> IProvider:
        """Create provider instance from database record."""
        from src.utils.encryption import EncryptionManager

        # Decrypt API key
        api_key = EncryptionManager.decrypt(provider.api_key_encrypted)

        # Create provider based on type
        if provider.provider_type.value == "openai":
            return ProviderFactory.create_provider(
                "openai",
                api_key=api_key,
                base_url=provider.base_url,
                organization=provider.organization,
                timeout=provider.timeout,
            )
        elif provider.provider_type.value == "anthropic":
            return ProviderFactory.create_provider(
                "anthropic",
                api_key=api_key,
                base_url=provider.base_url,
                timeout=provider.timeout,
            )
        else:
            raise ValueError(f"Unknown provider type: {provider.provider_type}")

    async def route(
        self,
        request: ChatRequest,
        preferred_model: Optional[str] = None,
        preferred_provider: Optional[int] = None,
    ) -> RouteDecision:
        """
        Make a routing decision.

        Args:
            request: The chat request
            preferred_model: Preferred model ID
            preferred_provider: Preferred provider ID

        Returns:
            RouteDecision: The routing decision
        """
        from src.agents.gateway_orchestrator import orchestrator

        # Check if fixed provider/model is requested
        if preferred_provider and preferred_model:
            return RouteDecision(
                provider_id=preferred_provider,
                model_id=preferred_model,
                rule_id=None,
                method=RoutingMethod.FIXED.value,
                reason="Fixed provider/model requested",
            )

        # Check if router switch is enabled
        switch_status = await orchestrator.get_status()
        if switch_status.enabled:
            # Router is ON: try rule-based routing
            rules = await self._get_active_rules()
            decision = await self._rule_based_routing(request, rules)
            if decision:
                return decision

        # Router is OFF or no rules matched: use model priority and load balancing
        return await self._weighted_round_robin_routing()

    async def _rule_based_routing(
        self,
        request: ChatRequest,
        rules: list[RoutingRule],
    ) -> Optional[RouteDecision]:
        """
        Apply rule-based routing.

        Args:
            request: The chat request
            rules: List of active routing rules

        Returns:
            Optional[RouteDecision]: Routing decision if a rule matches
        """
        # Sort rules by priority (higher first)
        sorted_rules = sorted(rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            if await self._evaluate_rule(request, rule):
                # Update hit count in memory (will be persisted in background)
                rule.hit_count += 1

                return RouteDecision(
                    provider_id=int(rule.action_value) if rule.action_type == "use_provider" else None,
                    model_id=rule.action_value if rule.action_type == "use_model" else settings.default_model,
                    rule_id=rule.id,
                    method=RoutingMethod.RULE_BASED.value,
                    reason=f"Rule matched: {rule.name}",
                )

        return None

    async def _evaluate_rule(self, request: ChatRequest, rule: RoutingRule) -> bool:
        """
        Evaluate if a rule matches the request.

        Args:
            request: The chat request
            rule: The routing rule

        Returns:
            bool: True if rule matches
        """
        content = " ".join(msg.content for msg in request.messages)

        if rule.condition_type == "regex":
            try:
                pattern = re.compile(rule.condition_value)
                return pattern.search(content) is not None
            except re.error:
                return False

        elif rule.condition_type == "complexity":
            # Simple complexity check based on length
            complexity = len(content)
            if rule.min_complexity is not None and complexity < rule.min_complexity:
                return False
            if rule.max_complexity is not None and complexity > rule.max_complexity:
                return False
            return True

        return False

    async def _weighted_round_robin_routing(self) -> RouteDecision:
        """
        Perform weighted round robin routing using model-level priority and weight.

        Returns:
            RouteDecision: The routing decision
        """
        from sqlalchemy import select

        # Query providers and models separately to avoid tuple unpacking issues
        providers = await SessionManager.execute_select(
            select(Provider).where(Provider.status == ProviderStatus.ACTIVE)
        )

        models = await SessionManager.execute_select(
            select(ProviderModel).where(ProviderModel.is_active == True)
        )

        if not models:
            raise RuntimeError("No active models available")

        # Create a map of provider_id to provider
        provider_map = {p.id: p for p in providers}

        # Build list of (model, provider) tuples
        model_list = []
        for model in models:
            provider = provider_map.get(model.provider_id)
            if provider:
                model_list.append((model, provider))

        if not model_list:
            raise RuntimeError("No active models available")

        # Sort by priority (higher first), then by weight
        model_list.sort(key=lambda x: (x[0].priority, x[0].weight), reverse=True)

        # Group models by priority level
        priority_groups = {}
        for model, provider in model_list:
            if model.priority not in priority_groups:
                priority_groups[model.priority] = []
            priority_groups[model.priority].append((model, provider))

        # Use the highest priority group
        highest_priority = max(priority_groups.keys())
        candidate_models = priority_groups[highest_priority]

        # Calculate total weight for this priority level
        total_weight = sum(m.weight for m, _ in candidate_models)

        # Find model based on weighted round robin
        weighted_index = self._round_robin_index % total_weight
        current_weight = 0

        selected_model = None
        selected_provider = None
        for model, provider in candidate_models:
            current_weight += model.weight
            if weighted_index < current_weight:
                selected_model = model
                selected_provider = provider
                break

        if selected_model is None:
            selected_model, selected_provider = candidate_models[0]

        self._round_robin_index += 1

        return RouteDecision(
            provider_id=selected_provider.id,
            model_id=selected_model.model_id,
            rule_id=None,
            method=RoutingMethod.WEIGHTED_ROUND_ROBIN.value,
            reason=f"Weighted round robin (priority={selected_model.priority}, weight={selected_model.weight})",
        )

    async def execute(
        self,
        request: ChatRequest,
        decision: RouteDecision,
        user_id: Optional[int] = None,
        api_key_id: Optional[int] = None,
    ) -> RouteResult:
        """
        Execute the routed request.

        Args:
            request: The chat request
            decision: The routing decision
            user_id: Optional user ID
            api_key_id: Optional API key ID

        Returns:
            RouteResult: The execution result
        """
        from sqlalchemy import select
        from decimal import Decimal

        session_id = generate_session_id()
        request_id = generate_session_id()
        content = " ".join(msg.content for msg in request.messages)

        provider = await SessionManager.execute_get_one(
            select(Provider).where(Provider.id == decision.provider_id),
        )

        if not provider:
            return RouteResult(
                success=False,
                response=None,
                provider_id=decision.provider_id,
                model_id=decision.model_id,
                latency_ms=0,
                input_tokens=0,
                output_tokens=0,
                cost=0.0,
                error_message="Provider not found",
            )

        provider_instance = self._providers_cache.get(provider.id)
        if not provider_instance:
            return RouteResult(
                success=False,
                response=None,
                provider_id=decision.provider_id,
                model_id=decision.model_id,
                latency_ms=0,
                input_tokens=0,
                output_tokens=0,
                cost=0.0,
                error_message="Provider not initialized",
            )

        start_time = time.time()

        try:
            # Execute request with retry
            response = await self._execute_with_retry(
                provider_instance,
                request,
                max_retries=provider.max_retries,
            )

            latency_ms = int((time.time() - start_time) * 1000)

            # Calculate cost
            input_cost, output_cost = provider_instance.calculate_cost(
                response.usage.input_tokens,
                response.usage.output_tokens,
                decision.model_id,
            )
            total_cost = float(input_cost + output_cost)

            # Record routing decision
            await self._record_decision(
                session_id=session_id,
                request_id=request_id,
                user_id=user_id,
                api_key_id=api_key_id,
                content=content,
                decision=decision,
                provider=provider,
                response=response,
                latency_ms=latency_ms,
                cost=total_cost,
            )

            return RouteResult(
                success=True,
                response=response,
                provider_id=provider.id,
                model_id=decision.model_id,
                latency_ms=latency_ms,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                cost=total_cost,
                error_message=None,
            )

        except ProviderError as e:
            latency_ms = int((time.time() - start_time) * 1000)

            # Record failed decision
            await self._record_decision(
                session_id=session_id,
                request_id=request_id,
                user_id=user_id,
                api_key_id=api_key_id,
                content=content,
                decision=decision,
                provider=provider,
                response=None,
                latency_ms=latency_ms,
                cost=0.0,
                error=str(e),
            )

            return RouteResult(
                success=False,
                response=None,
                provider_id=provider.id,
                model_id=decision.model_id,
                latency_ms=latency_ms,
                input_tokens=0,
                output_tokens=0,
                cost=0.0,
                error_message=str(e),
            )

    async def _execute_with_retry(
        self,
        provider: IProvider,
        request: ChatRequest,
        max_retries: int = 3,
    ) -> ChatResponse:
        """
        Execute request with retry logic.

        Args:
            provider: Provider instance
            request: Chat request
            max_retries: Maximum number of retries

        Returns:
            ChatResponse: The response

        Raises:
            ProviderError: If all retries fail
        """
        last_error = None

        for attempt in range(max_retries):
            try:
                return await provider.chat_completion(request)
            except ProviderError as e:
                last_error = e
                if attempt < max_retries - 1:
                    # Wait before retry (exponential backoff)
                    import asyncio
                    await asyncio.sleep(2 ** attempt)
                continue

        raise last_error

    async def _record_decision(
        self,
        session_id: str,
        request_id: str,
        user_id: Optional[int],
        api_key_id: Optional[int],
        content: str,
        decision: RouteDecision,
        provider: Provider,
        response: Optional[ChatResponse],
        latency_ms: int,
        cost: float,
        error: Optional[str] = None,
    ) -> None:
        """Record routing decision to database."""
        from decimal import Decimal

        routing_decision = RoutingDecision(
            session_id=session_id,
            request_id=request_id,
            user_id=user_id,
            api_key_id=api_key_id,
            content_hash=hash_content(content),
            provider_id=provider.id,
            model_id=decision.model_id,
            routing_rule_id=decision.rule_id,
            routing_method=decision.method,
            success=error is None,
            latency_ms=latency_ms,
            input_tokens=response.usage.input_tokens if response else 0,
            output_tokens=response.usage.output_tokens if response else 0,
            cost=Decimal(str(cost)),
            error_message=error,
        )

        await SessionManager.execute_insert(routing_decision)

    async def _get_active_rules(self) -> list[RoutingRule]:
        """Get active routing rules."""
        from sqlalchemy import select

        return await SessionManager.execute_select(
            select(RoutingRule).where(RoutingRule.is_active == True)
        )

    async def get_available_providers(self) -> list[dict]:
        """Get list of available providers with their models."""
        result = []

        for provider_id, provider_instance in self._providers_cache.items():
            try:
                health = await provider_instance.health_check()
                models = await provider_instance.get_model_list()

                result.append({
                    "provider_id": provider_id,
                    "provider_name": provider_instance.get_provider_name(),
                    "is_healthy": health.is_healthy,
                    "latency_ms": health.latency_ms,
                    "models": [m.id for m in models],
                })
            except Exception:
                continue

        return result

    async def get_available_models(self) -> list[dict]:
        """Get list of all available models."""
        from sqlalchemy import select

        # Query providers and models separately to avoid lazy loading issues
        providers = await SessionManager.execute_select(
            select(Provider).where(Provider.status == ProviderStatus.ACTIVE)
        )

        models = await SessionManager.execute_select(
            select(ProviderModel).where(ProviderModel.is_active == True)
        )

        # Create a map of provider_id to provider
        provider_map = {p.id: p for p in providers}

        result = []
        for model in models:
            provider = provider_map.get(model.provider_id)
            if provider:
                result.append({
                    "id": model.model_id,
                    "model_id": model.model_id,
                    "name": model.name,
                    "provider": provider.provider_type.value,
                    "provider_id": provider.id,
                    "provider_type": provider.provider_type.value,
                    "context_window": model.context_window,
                    "input_price_per_1k": float(model.input_price_per_1k),
                    "output_price_per_1k": float(model.output_price_per_1k),
                    "priority": model.priority,
                    "weight": model.weight,
                })

        return result


# Global instance
routing_agent = RoutingAgent()
