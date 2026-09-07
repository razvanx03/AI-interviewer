"""add pgvector extension and cv_chunks table for semantic RAG search

Revision ID: 010_add_pgvector_and_cv_chunks
Revises: 009_add_finishing_status
Create Date: 2026-09-04 17:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = '010_add_pgvector_and_cv_chunks'
down_revision: Union[str, None] = '009_add_finishing_status'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # 2. Create cv_chunks table
    op.create_table(
        'cv_chunks',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('candidate_name', sa.String(length=255), nullable=False),
        sa.Column('cv_filename', sa.String(length=255), nullable=True),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('chunk_text', sa.Text(), nullable=False),
        sa.Column('embedding', Vector(768), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_cv_chunks_id'), 'cv_chunks', ['id'], unique=False)
    op.create_index(op.f('ix_cv_chunks_candidate_name'), 'cv_chunks', ['candidate_name'], unique=False)

    # 3. Create HNSW index for fast cosine similarity vector search
    op.execute("""
    DO $$
    BEGIN
        CREATE INDEX IF NOT EXISTS ix_cv_chunks_embedding 
        ON cv_chunks USING hnsw (embedding vector_cosine_ops);
    EXCEPTION WHEN OTHERS THEN
        NULL;
    END$$;
    """)


def downgrade() -> None:
    op.drop_index(op.f('ix_cv_chunks_candidate_name'), table_name='cv_chunks')
    op.drop_index(op.f('ix_cv_chunks_id'), table_name='cv_chunks')
    op.drop_table('cv_chunks')
