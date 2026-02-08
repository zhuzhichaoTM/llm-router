"""
Chat completion API endpoints.
"""
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, status

from src.api.middleware import APIKeyAuth, RateLimiter
from src.schemas.chat import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionErrorResponse,
    ModelInfo,
)
from src.agents.routing_agent import routing_agent
from src.agents.cost_agent import cost_agent
from src.config.settings import settings
from src.utils.logging import logger


router = APIRouter(prefix="/chat", tags=["chat"])


@router.post(
    "/completions",
    response_model=ChatCompletionResponse,
    responses={
        401: {"model": ChatCompletionErrorResponse},
        429: {"model": ChatCompletionErrorResponse},
        500: {"model": ChatCompletionErrorResponse},
    },
)
async def chat_completions(
    request: ChatCompletionRequest,
    http_request: Request,
):
    """
    Chat completion endpoint.

    This endpoint routes the chat request to the appropriate provider
    based on routing rules and configuration.
    """
    from src.providers.base import ChatRequest, ChatMessage

    # Verify API key
    result = await APIKeyAuth.verify_api_key(http_request)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
        )
    user, api_key = result

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
        )

    # Check rate limit
    await RateLimiter.check_rate_limit(http_request, user, api_key)

    try:
        # Convert request
        chat_request = ChatRequest(
            messages=[
                ChatMessage(role=msg.role, content=msg.content)
                for msg in request.messages
            ],
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=request.stream,
            stop=request.stop,
        )

        # Make routing decision
        route_decision = await routing_agent.route(
            chat_request,
            preferred_model=request.model,
        )

        logger.info(
            f"Routing request to provider {route_decision.provider_id}, "
            f"model {route_decision.model_id} "
            f"(method: {route_decision.method})"
        )

        # Execute request
        result = await routing_agent.execute(
            chat_request,
            route_decision,
            user_id=user.id if user.id else None,
            api_key_id=api_key.id if api_key else None,
        )

        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.error_message or "Request failed",
            )

        # Record cost
        await cost_agent.record_cost(
            session_id="",  # Already recorded by routing_agent
            request_id="",  # Already recorded by routing_agent
            user_id=user.id if user.id else None,
            api_key_id=api_key.id if api_key else None,
            provider_id=result.provider_id,
            model_id=result.model_id,
            provider_type="",  # Get from provider
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            input_cost=0,  # Calculated by routing_agent
            output_cost=0,  # Calculated by routing_agent
        )

        # Return response
        return ChatCompletionResponse(
            id=f"chatcmpl-{result.provider_id}-{int(http_request.state.get('start', 0))}",
            object="chat.completion",
            created=int(http_request.state.get('start', 0)),
            model=result.model_id,
            choices=[
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": result.response.choices[0].message.content,
                    },
                    "finish_reason": result.response.choices[0].finish_reason,
                }
            ],
            usage={
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "total_tokens": result.input_tokens + result.output_tokens,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat completion error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


@router.get("/models", response_model=list[ModelInfo])
async def list_models(
    http_request: Request,
):
    """
    List available models.

    Returns all available models from all configured providers.
    """
    # Verify API key
    result = await APIKeyAuth.verify_api_key(http_request)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
        )
    user, api_key = result

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
        )

    try:
        models = await routing_agent.get_available_models()
        return [
            ModelInfo(**model) for model in models
        ]
    except Exception as e:
        logger.error(f"List models error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list models: {str(e)}",
        )
