"""Initial database migration

Create initial tables for LLM Router.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers
revision = '001_init'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create initial tables."""

    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=True),
        sa.Column('role', sa.Enum('admin', 'user', name='userrole'), nullable=False),
        sa.Column('status', sa.Enum('active', 'suspended', 'deleted', name='userstatus'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username'),
        sa.UniqueConstraint('email'),
        comment='User accounts'
    )
    op.create_index('ix_user_email_status', 'users', ['email', 'status'])

    # Create api_keys table
    op.create_table(
        'api_keys',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('key_hash', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('request_count', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='api_keys_user_id_fkey'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key_hash'),
        comment='API keys for authentication'
    )
    op.create_index('ix_api_key_user_active', 'api_keys', ['user_id', 'is_active'])

    # Create providers table
    op.create_table(
        'providers',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('provider_type', sa.Enum('openai', 'anthropic', 'custom', name='providertype'), nullable=False),
        sa.Column('api_key_encrypted', sa.String(length=500), nullable=False),
        sa.Column('base_url', sa.String(length=255), nullable=False),
        sa.Column('region', sa.String(length=50), nullable=True),
        sa.Column('organization', sa.String(length=100), nullable=True),
        sa.Column('timeout', sa.Integer(), nullable=False),
        sa.Column('max_retries', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('active', 'inactive', 'unhealthy', name='providerstatus'), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False),
        sa.Column('weight', sa.Integer(), nullable=False),
        sa.Column('config', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        comment='LLM provider configurations'
    )

    # Create provider_models table
    op.create_table(
        'provider_models',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('provider_id', sa.Integer(), nullable=False),
        sa.Column('model_id', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('context_window', sa.Integer(), nullable=False),
        sa.Column('input_price_per_1k', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('output_price_per_1k', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['provider_id'], ['providers.id'], name='provider_models_provider_id_fkey'),
        sa.PrimaryKeyConstraint('id'),
        comment='Available models for each provider'
    )

    # Create provider_performance_history table
    op.create_table(
        'provider_performance_history',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('provider_id', sa.Integer(), nullable=False),
        sa.Column('model_id', sa.String(length=100), nullable=False),
        sa.Column('avg_latency_ms', sa.Integer(), nullable=False),
        sa.Column('success_rate', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('total_requests', sa.Integer(), nullable=False),
        sa.Column('failed_requests', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['provider_id'], ['providers.id'], name='perf_history_provider_id_fkey'),
        sa.PrimaryKeyConstraint('id'),
        comment='Provider performance history'
    )
    op.create_index('ix_perf_provider_time', 'provider_performance_history', ['provider_id', 'created_at'])

    # Create routing_rules table
    op.create_table(
        'routing_rules',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('condition_type', sa.String(length=50), nullable=False),
        sa.Column('condition_value', sa.String(length=500), nullable=False),
        sa.Column('min_complexity', sa.Integer(), nullable=True),
        sa.Column('max_complexity', sa.Integer(), nullable=True),
        sa.Column('action_type', sa.String(length=50), nullable=False),
        sa.Column('action_value', sa.String(length=100), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('hit_count', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        comment='Routing rule configurations'
    )

    # Create routing_decisions table
    op.create_table(
        'routing_decisions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('session_id', sa.String(length=64), nullable=False),
        sa.Column('request_id', sa.String(length=64), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('api_key_id', sa.Integer(), nullable=True),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('intent', sa.String(length=50), nullable=True),
        sa.Column('complexity_score', sa.Float(), nullable=True),
        sa.Column('provider_id', sa.Integer(), nullable=False),
        sa.Column('model_id', sa.String(length=100), nullable=False),
        sa.Column('routing_rule_id', sa.Integer(), nullable=True),
        sa.Column('routing_method', sa.String(length=50), nullable=False),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('latency_ms', sa.Integer(), nullable=False),
        sa.Column('input_tokens', sa.Integer(), nullable=False),
        sa.Column('output_tokens', sa.Integer(), nullable=False),
        sa.Column('cost', sa.Numeric(precision=12, scale=6), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='routing_decisions_user_id_fkey'),
        sa.ForeignKeyConstraint(['api_key_id'], ['api_keys.id'], name='routing_decisions_api_key_id_fkey'),
        sa.ForeignKeyConstraint(['provider_id'], ['providers.id'], name='routing_decisions_provider_id_fkey'),
        sa.ForeignKeyConstraint(['routing_rule_id'], ['routing_rules.id'], name='routing_decisions_routing_rule_id_fkey'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('request_id'),
        comment='Routing decision records'
    )
    op.create_index('ix_routing_decision_time', 'routing_decisions', ['created_at'])
    op.create_index('ix_routing_decision_user', 'routing_decisions', ['user_id', 'created_at'])

    # Create routing_switch_history table
    op.create_table(
        'routing_switch_history',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('old_enabled', sa.Boolean(), nullable=False),
        sa.Column('new_enabled', sa.Boolean(), nullable=False),
        sa.Column('trigger_reason', sa.String(length=200), nullable=False),
        sa.Column('triggered_by', sa.String(length=100), nullable=False),
        sa.Column('effective_at', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        comment='Routing switch history'
    )

    # Create routing_switch_state table
    op.create_table(
        'routing_switch_state',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('pending_switch', sa.Boolean(), nullable=False),
        sa.Column('pending_value', sa.Boolean(), nullable=False),
        sa.Column('scheduled_at', sa.Integer(), nullable=True),
        sa.Column('cooldown_until', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        comment='Routing switch state'
    )

    # Create cost_records table
    op.create_table(
        'cost_records',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('session_id', sa.String(length=64), nullable=False),
        sa.Column('request_id', sa.String(length=64), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('api_key_id', sa.Integer(), nullable=True),
        sa.Column('provider_id', sa.Integer(), nullable=False),
        sa.Column('model_id', sa.String(length=100), nullable=False),
        sa.Column('provider_type', sa.String(length=50), nullable=False),
        sa.Column('input_tokens', sa.Integer(), nullable=False),
        sa.Column('output_tokens', sa.Integer(), nullable=False),
        sa.Column('total_tokens', sa.Integer(), nullable=False),
        sa.Column('input_cost', sa.Numeric(precision=12, scale=6), nullable=False),
        sa.Column('output_cost', sa.Numeric(precision=12, scale=6), nullable=False),
        sa.Column('total_cost', sa.Numeric(precision=12, scale=6), nullable=False),
        sa.Column('extra_data', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='cost_records_user_id_fkey'),
        sa.ForeignKeyConstraint(['api_key_id'], ['api_keys.id'], name='cost_records_api_key_id_fkey'),
        sa.ForeignKeyConstraint(['provider_id'], ['providers.id'], name='cost_records_provider_id_fkey'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('request_id'),
        comment='Cost tracking records'
    )
    op.create_index('ix_cost_provider_time', 'cost_records', ['provider_id', 'created_at'])
    op.create_index('ix_cost_user_time', 'cost_records', ['user_id', 'created_at'])
    op.create_index('ix_cost_date', 'cost_records', ['created_at'])

    # Create cost_budgets table
    op.create_table(
        'cost_budgets',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('budget_type', sa.String(length=50), nullable=False),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('warning_threshold', sa.Integer(), nullable=False),
        sa.Column('critical_threshold', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('warning_sent', sa.Boolean(), nullable=False),
        sa.Column('critical_sent', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='cost_budgets_user_id_fkey'),
        sa.PrimaryKeyConstraint('id'),
        comment='Cost budget management'
    )

    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=False),
        sa.Column('resource_id', sa.String(length=100), nullable=True),
        sa.Column('details', sa.JSON(), nullable=False),
        sa.Column('ip_address', sa.String(length=50), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='audit_logs_user_id_fkey'),
        sa.PrimaryKeyConstraint('id'),
        comment='System audit log'
    )
    op.create_index('ix_audit_action_time', 'audit_logs', ['action', 'created_at'])


def downgrade() -> None:
    """Drop all tables in reverse order."""
    op.drop_table('audit_logs')
    op.drop_table('cost_budgets')
    op.drop_table('cost_records')
    op.drop_table('routing_switch_state')
    op.drop_table('routing_switch_history')
    op.drop_table('routing_decisions')
    op.drop_table('routing_rules')
    op.drop_table('provider_performance_history')
    op.drop_table('provider_models')
    op.drop_table('providers')
    op.drop_table('api_keys')
    op.drop_table('users')
