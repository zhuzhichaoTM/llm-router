"""Add priority and weight to provider_models table

Revision ID: 002_add_model_priority_weight
Revises: 001_init
Create Date: 2025-02-09
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '002_add_model_priority_weight'
down_revision = '001_init'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add priority and weight columns to provider_models table."""

    # Add priority column with default value 100
    op.add_column(
        'provider_models',
        sa.Column('priority', sa.Integer(), nullable=False, server_default='100')
    )

    # Add weight column with default value 100
    op.add_column(
        'provider_models',
        sa.Column('weight', sa.Integer(), nullable=False, server_default='100')
    )


def downgrade() -> None:
    """Remove priority and weight columns from provider_models table."""

    op.drop_column('provider_models', 'weight')
    op.drop_column('provider_models', 'priority')
