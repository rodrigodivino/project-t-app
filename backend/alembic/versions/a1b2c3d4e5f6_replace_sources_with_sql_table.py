"""replace sources with sql table

Revision ID: a1b2c3d4e5f6
Revises: 4ca671e03d32
Create Date: 2026-07-21 12:00:00.000000

"""
import csv
from pathlib import Path
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '4ca671e03d32'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CSV_PATH = Path(__file__).resolve().parents[3] / "materials" / "external_data_source" / "MC3" / "YInt.csv"


def upgrade() -> None:
    op.execute('DROP TABLE IF EXISTS shoebox_item')
    op.execute('DROP TABLE IF EXISTS source_document')

    op.create_table(
        'post_rede_social_himark',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('time', sa.DateTime(), nullable=False),
        sa.Column('location', sa.String(), nullable=False),
        sa.Column('account', sa.String(), nullable=False),
        sa.Column('message', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'shoebox_item',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('workspace_id', sa.Uuid(), nullable=False),
        sa.Column('query', sa.Text(), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=False),
        sa.Column('result', sa.JSON(), nullable=False),
        sa.Column('added_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspace.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    if CSV_PATH.is_file():
        table = sa.table(
            'post_rede_social_himark',
            sa.column('time', sa.DateTime),
            sa.column('location', sa.String),
            sa.column('account', sa.String),
            sa.column('message', sa.String),
        )
        with open(CSV_PATH, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            batch = []
            for row in reader:
                batch.append({
                    'time': row['time'],
                    'location': row['location'],
                    'account': row['account'],
                    'message': row['message'],
                })
                if len(batch) >= 1000:
                    op.bulk_insert(table, batch)
                    batch = []
            if batch:
                op.bulk_insert(table, batch)


def downgrade() -> None:
    op.drop_table('shoebox_item')
    op.drop_table('post_rede_social_himark')

    op.create_table(
        'source_document',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('workspace_id', sa.Uuid(), nullable=False),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('content', sa.LargeBinary(), nullable=False),
        sa.Column('content_type', sa.String(), nullable=False),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspace.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'shoebox_item',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('workspace_id', sa.Uuid(), nullable=False),
        sa.Column('source_document_id', sa.Uuid(), nullable=False),
        sa.Column('added_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['source_document_id'], ['source_document.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspace.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workspace_id', 'source_document_id'),
    )
