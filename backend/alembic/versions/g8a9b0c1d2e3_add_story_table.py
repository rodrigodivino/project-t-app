"""add story table

Revision ID: g8a9b0c1d2e3
Revises: f7a8b9c0d1e2
Create Date: 2026-07-23 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'g8a9b0c1d2e3'
down_revision: Union[str, Sequence[str], None] = 'a8b9c0d1e2f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'story',
        sa.Column('workspace_id', sa.Uuid(), sa.ForeignKey('workspace.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('content', sa.Text(), nullable=False, server_default=''),
    )


def downgrade() -> None:
    op.drop_table('story')
