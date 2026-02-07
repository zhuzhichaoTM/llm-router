"""
Configuration management for LLM Router.
Loads settings from environment variables with validation.
"""
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "LLM Router"
    app_env: str = "development"
    app_version: str = "0.1.0"
    debug: bool = True
    log_level: str = "INFO"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://llm_router:llm_router_password@localhost:5432/llm_router",
        description="PostgreSQL database connection URL",
    )
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_password: str = ""
    redis_db: int = 0
    redis_max_connections: int = 50

    # API Keys
    secret_key: str = Field(
        default="your-secret-key-change-this-in-production",
        description="Secret key for JWT token signing",
    )
    admin_api_key: str = Field(
        default="your-admin-api-key-change-this-in-production",
        description="Admin API key for management operations",
    )
    api_key_salt: str = Field(
        default="your-salt-change-this-in-production",
        description="Salt for API key hashing",
    )

    # OpenAI
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_organization: str = ""
    openai_timeout: int = 60

    # Anthropic
    anthropic_api_key: str = ""
    anthropic_base_url: str = "https://api.anthropic.com"
    anthropic_timeout: int = 60

    # Routing Configuration
    routing_switch_enabled: bool = True
    routing_switch_delay_seconds: int = 10
    routing_switch_cooldown_seconds: int = 300
    default_model: str = "gpt-3.5-turbo"

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_requests_per_minute: int = 60
    rate_limit_requests_per_hour: int = 1000

    # Cost Tracking
    cost_tracking_enabled: bool = True
    cost_budget_warning_threshold: int = 80
    cost_budget_critical_threshold: int = 95

    # Monitoring
    metrics_enabled: bool = True
    health_check_interval: int = 30

    # CORS
    cors_origins: List[str] = Field(
        default=[
            "http://localhost:5173",
            "http://localhost:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:3000",
        ],
        description="Allowed CORS origins",
    )

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.app_env.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.app_env.lower() == "development"


# Global settings instance
settings = Settings()
