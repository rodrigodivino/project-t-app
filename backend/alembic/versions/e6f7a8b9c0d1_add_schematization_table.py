"""add schematization table

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-07-21 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'e6f7a8b9c0d1'
down_revision: Union[str, Sequence[str], None] = 'd5e6f7a8b9c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'schematization',
        sa.Column('workspace_id', sa.Uuid(), sa.ForeignKey('workspace.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('data', postgresql.JSON(), nullable=False, server_default='{}'),
    )


def downgrade() -> None:
    op.drop_table('schematization')
