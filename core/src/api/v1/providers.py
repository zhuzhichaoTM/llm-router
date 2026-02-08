"""
Provider management API endpoints.
"""
from typing import List, Optional
from fastapi import APIRouter, Request, HTTPException, status

from src.api.middleware import require_admin
from src.schemas.provider import (
    ProviderCreate,
    ProviderUpdate,
    ProviderResponse,
    ProviderModelCreate,
    ProviderModelResponse,
    ProviderModelUpdate,
    HealthCheckResponse,
    ProviderHealth,
)
from src.models.provider import Provider, ProviderModel, ProviderStatus
from src.agents.routing_agent import routing_agent
from src.agents.provider_agent import provider_agent
from src.utils.logging import logger
from src.utils.encryption import EncryptionManager


router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("", response_model=list[ProviderResponse])
async def list_providers(request: Request):
    """
    List all configured providers.

    Returns all providers with their configuration status.
    """
    # Verify admin access
    from src.api.middleware import APIKeyAuth

    result = await APIKeyAuth.verify_api_key(request)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
        )
    user, api_key = result

    if not user or user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    try:
        from sqlalchemy import select
        from src.db.session import SessionManager

        providers = await SessionManager.execute_select(select(Provider))

        return [
            ProviderResponse(
                id=p.id,
                name=p.name,
                provider_type=p.provider_type.value,
                api_key="*****",  # Never return API key
                base_url=p.base_url,
                region=p.region,
                organization=p.organization,
                timeout=p.timeout,
                max_retries=p.max_retries,
                status=p.status.value,
                priority=p.priority,
                weight=p.weight,
                created_at=p.created_at.isoformat(),
                updated_at=p.updated_at.isoformat(),
            )
            for p in providers
        ]
    except Exception as e:
        logger.error(f"List providers error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("", response_model=ProviderResponse, status_code=status.HTTP_201_CREATED)
async def create_provider(
    request: ProviderCreate,
    http_request: Request,
):
    """
    Create a new provider.

    Creates a new LLM provider configuration.
    """
    # Verify admin access
    from src.api.middleware import APIKeyAuth

    result = await APIKeyAuth.verify_api_key(http_request)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
        )
    user, api_key = result

    if not user or user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    try:
        from src.models.provider import ProviderType, ProviderStatus
        from src.db.session import SessionManager

        # Encrypt API key
        encrypted_key = EncryptionManager.encrypt(request.api_key)

        provider = Provider(
            name=request.name,
            provider_type=ProviderType(request.provider_type.value),
            api_key_encrypted=encrypted_key,
            base_url=request.base_url,
            region=request.region,
            organization=request.organization,
            timeout=request.timeout,
            max_retries=request.max_retries,
            status=ProviderStatus(request.status.value),
            priority=request.priority,
            weight=request.weight,
        )

        result = await SessionManager.execute_insert(provider)

        return ProviderResponse(
            id=result.id,
            name=result.name,
            provider_type=result.provider_type.value,
            api_key="*****",
            base_url=result.base_url,
            region=result.region,
            organization=result.organization,
            timeout=result.timeout,
            max_retries=result.max_retries,
            status=result.status.value,
            priority=result.priority,
            weight=result.weight,
            created_at=result.created_at.isoformat(),
            updated_at=result.updated_at.isoformat(),
        )
    except Exception as e:
        logger.error(f"Create provider error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/{provider_id}", response_model=ProviderResponse)
async def get_provider(provider_id: int, request: Request):
    """
    Get provider details.

    Returns detailed information about a specific provider.
    """
    # Verify admin access
    from src.api.middleware import APIKeyAuth

    result = await APIKeyAuth.verify_api_key(request)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
        )
    user, api_key = result

    if not user or user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    try:
        from sqlalchemy import select
        from src.db.session import SessionManager

        provider = await SessionManager.execute_get_one(
            select(Provider).where(Provider.id == provider_id)
        )

        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Provider not found",
            )

        return ProviderResponse(
            id=provider.id,
            name=provider.name,
            provider_type=provider.provider_type.value,
            api_key="*****",
            base_url=provider.base_url,
            region=provider.region,
            organization=provider.organization,
            timeout=provider.timeout,
            max_retries=provider.max_retries,
            status=provider.status.value,
            priority=provider.priority,
            weight=provider.weight,
            created_at=provider.created_at.isoformat(),
            updated_at=provider.updated_at.isoformat(),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get provider error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/{provider_id}/health", response_model=HealthCheckResponse)
async def health_check(provider_id: int, request: Request):
    """
    Perform health check on a provider.

    Checks if the provider is reachable and responsive.
    """
    # Verify admin access
    from src.api.middleware import APIKeyAuth

    result = await APIKeyAuth.verify_api_key(request)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
        )
    user, api_key = result

    if not user or user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    try:
        from sqlalchemy import select
        from src.db.session import SessionManager

        provider = await SessionManager.execute_get_one(
            select(Provider).where(Provider.id == provider_id)
        )

        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Provider not found",
            )

        # Get provider instance from routing agent
        provider_instance = routing_agent._providers_cache.get(provider_id)

        if not provider_instance:
            return HealthCheckResponse(
                healthy=False,
                providers=[],
            )

        health = await provider_instance.health_check()

        return HealthCheckResponse(
            healthy=health.is_healthy,
            providers=[
                ProviderHealth(
                    provider_id=provider_id,
                    provider_name=provider.name,
                    is_healthy=health.is_healthy,
                    latency_ms=health.latency_ms,
                    error_message=health.error_message,
                )
            ],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/{provider_id}/models", response_model=list[ProviderModelResponse])
async def list_provider_models(provider_id: int, request: Request):
    """
    List models for a provider.

    Returns all configured models for a specific provider.
    """
    # Verify admin access
    from src.api.middleware import APIKeyAuth

    result = await APIKeyAuth.verify_api_key(request)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
        )
    user, api_key = result

    if not user or user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    try:
        from sqlalchemy import select
        from src.db.session import SessionManager

        models = await SessionManager.execute_select(
            select(ProviderModel).where(ProviderModel.provider_id == provider_id)
        )

        return [
            ProviderModelResponse(
                id=m.id,
                provider_id=m.provider_id,
                model_id=m.model_id,
                name=m.name,
                context_window=m.context_window,
                input_price_per_1k=float(m.input_price_per_1k),
                output_price_per_1k=float(m.output_price_per_1k),
                is_active=m.is_active,
                created_at=m.created_at.isoformat(),
                updated_at=m.updated_at.isoformat(),
            )
            for m in models
        ]
    except Exception as e:
        logger.error(f"List provider models error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/{provider_id}/models", response_model=ProviderModelResponse, status_code=status.HTTP_201_CREATED)
async def create_provider_model(
    provider_id: int,
    request: ProviderModelCreate,
    http_request: Request,
):
    """
    Create a new model for a provider.

    Creates a new model configuration for a provider.
    """
    # Verify admin access
    from src.api.middleware import APIKeyAuth

    result = await APIKeyAuth.verify_api_key(http_request)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
        )
    user, api_key = result

    if not user or user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    try:
        from src.db.session import SessionManager
        from decimal import Decimal

        model = ProviderModel(
            provider_id=provider_id,
            model_id=request.model_id,
            name=request.name,
            context_window=request.context_window,
            input_price_per_1k=Decimal(str(request.input_price_per_1k)),
            output_price_per_1k=Decimal(str(request.output_price_per_1k)),
            is_active=request.is_active,
        )

        result = await SessionManager.execute_insert(model)

        return ProviderModelResponse(
            id=result.id,
            provider_id=result.provider_id,
            model_id=result.model_id,
            name=result.name,
            context_window=result.context_window,
            input_price_per_1k=float(result.input_price_per_1k),
            output_price_per_1k=float(result.output_price_per_1k),
            is_active=result.is_active,
            created_at=result.created_at.isoformat(),
            updated_at=result.updated_at.isoformat(),
        )
    except Exception as e:
        logger.error(f"Create provider model error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.put("/{provider_id}", response_model=ProviderResponse)
async def update_provider(
    provider_id: int,
    request: ProviderUpdate,
    http_request: Request,
):
    """
    Update an existing provider.

    Updates provider configuration (excluding API key which requires separate endpoint).
    """
    # Verify admin access
    from src.api.middleware import APIKeyAuth

    result = await APIKeyAuth.verify_api_key(http_request)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
        )
    user, api_key = result

    if not user or user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    try:
        from sqlalchemy import update
        from src.db.session import SessionManager
        from src.models.provider import ProviderType

        # Build update values
        update_values = {}
        if request.name is not None:
            update_values["name"] = request.name
        if request.base_url is not None:
            update_values["base_url"] = request.base_url
        if request.region is not None:
            update_values["region"] = request.region
        if request.organization is not None:
            update_values["organization"] = request.organization
        if request.timeout is not None:
            update_values["timeout"] = request.timeout
        if request.max_retries is not None:
            update_values["max_retries"] = request.max_retries
        if request.status is not None:
            update_values["status"] = ProviderStatus(request.status.value)
        if request.priority is not None:
            update_values["priority"] = request.priority
        if request.weight is not None:
            update_values["weight"] = request.weight

        if request.api_key is not None:
            # Update API key (encrypt it)
            update_values["api_key_encrypted"] = EncryptionManager.encrypt(request.api_key)

        # Update provider
        await SessionManager.execute_update(
            update(Provider).where(Provider.id == provider_id).values(**update_values)
        )

        # Get updated provider
        provider = await SessionManager.execute_get_one(
            select(Provider).where(Provider.id == provider_id)
        )

        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Provider not found",
            )

        # Refresh provider instance in routing agent
        if provider.status == ProviderStatus.ACTIVE:
            await provider_agent.refresh_providers()

        return ProviderResponse(
            id=provider.id,
            name=provider.name,
            provider_type=provider.provider_type.value,
            api_key="*****",
            base_url=provider.base_url,
            region=provider.region,
            organization=provider.organization,
            timeout=provider.timeout,
            max_retries=provider.max_retries,
            status=provider.status.value,
            priority=provider.priority,
            weight=provider.weight,
            created_at=provider.created_at.isoformat(),
            updated_at=provider.updated_at.isoformat(),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update provider error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.delete("/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_provider(
    provider_id: int,
    http_request: Request,
):
    """
    Delete a provider.

    Permanently removes a provider and all its models.
    """
    # Verify admin access
    from src.api.middleware import APIKeyAuth

    result = await APIKeyAuth.verify_api_key(http_request)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
        )
    user, api_key = result

    if not user or user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    try:
        from sqlalchemy import delete
        from src.db.session import SessionManager

        # Check if provider exists
        provider = await SessionManager.execute_get_one(
            select(Provider).where(Provider.id == provider_id)
        )

        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Provider not found",
            )

        # Delete provider (cascade will delete models)
        await SessionManager.execute_delete(
            delete(Provider).where(Provider.id == provider_id)
        )

        # Remove from provider agent cache
        if provider_id in provider_agent._providers:
            del provider_agent._providers[provider_id]

        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete provider error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.put("/{provider_id}/models/{model_id}", response_model=ProviderModelResponse)
async def update_provider_model(
    provider_id: int,
    model_id: str,
    request: ProviderModelUpdate,
    http_request: Request,
):
    """
    Update an existing provider model.

    Updates model configuration.
    """
    # Verify admin access
    from src.api.middleware import APIKeyAuth

    result = await APIKeyAuth.verify_api_key(http_request)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
        )
    user, api_key = result

    if not user or user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    try:
        from sqlalchemy import update
        from src.db.session import SessionManager
        from decimal import Decimal

        # Build update values
        update_values = {}
        if request.name is not None:
            update_values["name"] = request.name
        if request.context_window is not None:
            update_values["context_window"] = request.context_window
        if request.input_price_per_1k is not None:
            update_values["input_price_per_1k"] = Decimal(str(request.input_price_per_1k))
        if request.output_price_per_1k is not None:
            update_values["output_price_per_1k"] = Decimal(str(request.output_price_per_1k))
        if request.is_active is not None:
            update_values["is_active"] = request.is_active

        # Update model
        await SessionManager.execute_update(
            update(ProviderModel)
            .where(ProviderModel.id == model_id, ProviderModel.provider_id == provider_id)
            .values(**update_values)
        )

        # Get updated model
        model = await SessionManager.execute_get_one(
            select(ProviderModel).where(
                ProviderModel.id == model_id,
                ProviderModel.provider_id == provider_id
            )
        )

        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Model not found",
            )

        return ProviderModelResponse(
            id=model.id,
            provider_id=model.provider_id,
            model_id=model.model_id,
            name=model.name,
            context_window=model.context_window,
            input_price_per_1k=float(model.input_price_per_1k),
            output_price_per_1k=float(model.output_price_per_1k),
            is_active=model.is_active,
            created_at=model.created_at.isoformat(),
            updated_at=model.updated_at.isoformat(),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update provider model error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.delete("/{provider_id}/models/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_provider_model(
    provider_id: int,
    model_id: str,
    http_request: Request,
):
    """
    Delete a provider model.

    Removes a model from a provider.
    """
    # Verify admin access
    from src.api.middleware import APIKeyAuth

    result = await APIKeyAuth.verify_api_key(http_request)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
        )
    user, api_key = result

    if not user or user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    try:
        from sqlalchemy import delete
        from src.db.session import SessionManager

        # Check if model exists
        model = await SessionManager.execute_get_one(
            select(ProviderModel).where(
                ProviderModel.id == model_id,
                ProviderModel.provider_id == provider_id
            )
        )

        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Model not found",
            )

        # Delete model
        await SessionManager.execute_delete(
            delete(ProviderModel).where(
                ProviderModel.id == model_id,
                ProviderModel.provider_id == provider_id
            )
        )

        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete provider model error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
