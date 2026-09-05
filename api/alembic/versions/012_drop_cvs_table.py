"""drop cvs table and parsing_status_enum

Revision ID: 012_drop_cvs_table
Revises: 011_add_candidate_id
Create Date: 2026-09-05 16:55:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '012_drop_cvs_table'
down_revision: Union[str, None] = '011_add_candidate_id'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Drop cvs table
    op.drop_table('cvs')

    # 2. Drop the parsing_status_enum
    op.execute("DROP TYPE IF EXISTS parsing_status_enum;")


def downgrade() -> None:
    # 1. Recreate enum safely
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'parsing_status_enum') THEN
            CREATE TYPE parsing_status_enum AS ENUM ('pending', 'completed', 'failed');
        END IF;
    END$$;
    """)

    # 2. Recreate cvs table
    op.create_table(
        'cvs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=True),
        sa.Column('interview_id', sa.String(length=36), nullable=True),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('file_type', sa.String(length=10), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('storage_path', sa.String(length=500), nullable=False),
        sa.Column('raw_text', sa.Text(), nullable=False),
        sa.Column('parsed_data', sa.JSON(), nullable=True),
        sa.Column(
            'parsing_status',
            postgresql.ENUM('pending', 'completed', 'failed', name='parsing_status_enum', create_type=False),
            nullable=False,
            server_default='pending'
        ),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['interview_id'], ['interviews.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_cvs_id'), 'cvs', ['id'], unique=False)
    op.create_index(op.f('ix_cvs_user_id'), 'cvs', ['user_id'], unique=False)
    op.create_index(op.f('ix_cvs_interview_id'), 'cvs', ['interview_id'], unique=False)
