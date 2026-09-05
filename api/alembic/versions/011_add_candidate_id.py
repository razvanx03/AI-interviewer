"""add candidate_id to cv_chunks

Revision ID: 011_add_candidate_id
Revises: 010_add_pgvector_and_cv_chunks
Create Date: 2026-09-05 12:28:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '011_add_candidate_id'
down_revision: Union[str, None] = '010_add_pgvector_and_cv_chunks'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'cv_chunks',
        sa.Column('candidate_id', sa.String(length=36), nullable=True)
    )
    op.create_index(op.f('ix_cv_chunks_candidate_id'), 'cv_chunks', ['candidate_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_cv_chunks_candidate_id'), table_name='cv_chunks')
    op.drop_column('cv_chunks', 'candidate_id')
