"""Add credits to users; add style_critiques and credit_transactions tables

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-05-30 12:00:00.000000

Changes:
- Add `credits` column (INTEGER, default 100) to users table
- Create `style_critiques` table for Ollama/qwen3.5:9b critique results
- Create `credit_transactions` table for full audit trail of credit changes
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # 1. Add credits column to users
    # -----------------------------------------------------------------------
    op.add_column(
        'users',
        sa.Column('credits', sa.Integer(), nullable=False, server_default='100'),
    )
    # Remove server default so it only applies during backfill
    op.alter_column('users', 'credits', server_default=None)

    # -----------------------------------------------------------------------
    # 2. Create style_critiques table
    # -----------------------------------------------------------------------
    op.create_table(
        'style_critiques',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('image_path', sa.String(), nullable=False),
        sa.Column('markdown_response', sa.Text(), nullable=False),
        sa.Column('credits_used', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('model_used', sa.String(), nullable=False, server_default='qwen3.5:9b'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_style_critiques_id'), 'style_critiques', ['id'], unique=False)
    op.create_index(op.f('ix_style_critiques_user_id'), 'style_critiques', ['user_id'], unique=False)

    # -----------------------------------------------------------------------
    # 3. Create credit_transactions table
    # -----------------------------------------------------------------------
    op.create_table(
        'credit_transactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False),          # negative = deduction
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('service', sa.String(), nullable=False),
        sa.Column('balance_after', sa.Integer(), nullable=False),   # snapshot post-transaction
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_credit_transactions_id'), 'credit_transactions', ['id'], unique=False)
    op.create_index(op.f('ix_credit_transactions_user_id'), 'credit_transactions', ['user_id'], unique=False)


def downgrade() -> None:
    # -----------------------------------------------------------------------
    # Reverse: drop credit_transactions
    # -----------------------------------------------------------------------
    op.drop_index('ix_credit_transactions_user_id', table_name='credit_transactions')
    op.drop_index('ix_credit_transactions_id', table_name='credit_transactions')
    op.drop_table('credit_transactions')

    # -----------------------------------------------------------------------
    # Reverse: drop style_critiques
    # -----------------------------------------------------------------------
    op.drop_index('ix_style_critiques_user_id', table_name='style_critiques')
    op.drop_index('ix_style_critiques_id', table_name='style_critiques')
    op.drop_table('style_critiques')

    # -----------------------------------------------------------------------
    # Reverse: remove credits from users
    # -----------------------------------------------------------------------
    op.drop_column('users', 'credits')
