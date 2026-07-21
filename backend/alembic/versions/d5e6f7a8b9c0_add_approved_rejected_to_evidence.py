"""add approved and rejected to evidence_item

Revision ID: d5e6f7a8b9c0
Revises: c3d4e5f6a7b8
Create Date: 2026-07-21 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd5e6f7a8b9c0'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'evidence_item',
        sa.Column('approved', sa.Boolean(), nullable=False, server_default=sa.text('false')),
    )
    op.add_column(
        'evidence_item',
        sa.Column('rejected', sa.Boolean(), nullable=False, server_default=sa.text('false')),
    )


def downgrade() -> None:
    op.drop_column('evidence_item', 'rejected')
    op.drop_column('evidence_item', 'approved')
