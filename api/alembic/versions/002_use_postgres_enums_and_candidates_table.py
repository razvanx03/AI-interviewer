"""use postgres enums and relational candidates table

Revision ID: 002
Revises: 001
Create Date: 2026-08-22 15:27:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002_enums_and_candidates'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

experience_level_enum = postgresql.ENUM(
    'entry', 'mid', 'senior', 'lead', 'executive', name='experience_level_enum'
)
interview_status_enum = postgresql.ENUM(
    'draft', 'active', 'completed', name='interview_status_enum'
)
message_role_enum = postgresql.ENUM(
    'system', 'assistant', 'user', name='message_role_enum'
)

def upgrade() -> None:
    # 1. Create PostgreSQL native enum types
    experience_level_enum.create(op.get_bind(), checkfirst=True)
    interview_status_enum.create(op.get_bind(), checkfirst=True)
    message_role_enum.create(op.get_bind(), checkfirst=True)

    # 2. Alter interviews table to use native enums
    op.execute("ALTER TABLE interviews ALTER COLUMN experience_level DROP DEFAULT")
    op.execute(
        "ALTER TABLE interviews ALTER COLUMN experience_level TYPE experience_level_enum USING experience_level::experience_level_enum"
    )
    op.execute("ALTER TABLE interviews ALTER COLUMN experience_level SET DEFAULT 'mid'::experience_level_enum")

    op.execute("ALTER TABLE interviews ALTER COLUMN status DROP DEFAULT")
    op.execute(
        "ALTER TABLE interviews ALTER COLUMN status TYPE interview_status_enum USING status::interview_status_enum"
    )
    op.execute("ALTER TABLE interviews ALTER COLUMN status SET DEFAULT 'active'::interview_status_enum")

    # 3. Drop legacy JSON columns from interviews
    op.drop_column('interviews', 'candidates_pool')
    op.drop_column('interviews', 'screening_results')

    # 4. Alter messages table to use native role enum
    op.execute(
        "ALTER TABLE messages ALTER COLUMN role TYPE message_role_enum USING role::message_role_enum"
    )

    # 5. Create dedicated relational candidates table
    op.create_table(
        'candidates',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('interview_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('cv_filename', sa.String(length=255), nullable=True),
        sa.Column('cv_raw_text', sa.Text(), nullable=True),
        sa.Column('match_score', sa.Integer(), nullable=True),
        sa.Column('strengths', sa.JSON(), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('is_selected', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['interview_id'], ['interviews.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_candidates_id'), 'candidates', ['id'], unique=False)
    op.create_index(op.f('ix_candidates_interview_id'), 'candidates', ['interview_id'], unique=False)

def downgrade() -> None:
    # 1. Drop candidates table
    op.drop_index(op.f('ix_candidates_interview_id'), table_name='candidates')
    op.drop_index(op.f('ix_candidates_id'), table_name='candidates')
    op.drop_table('candidates')

    # 2. Revert messages.role to VARCHAR
    op.execute(
        "ALTER TABLE messages ALTER COLUMN role TYPE VARCHAR(50) USING role::text"
    )

    # 3. Add back JSON columns to interviews
    op.add_column('interviews', sa.Column('candidates_pool', sa.JSON(), nullable=True))
    op.add_column('interviews', sa.Column('screening_results', sa.JSON(), nullable=True))

    # 4. Revert interviews enums to VARCHAR
    op.execute(
        "ALTER TABLE interviews ALTER COLUMN experience_level TYPE VARCHAR(50) USING experience_level::text"
    )
    op.execute(
        "ALTER TABLE interviews ALTER COLUMN status TYPE VARCHAR(50) USING status::text"
    )

    # 5. Drop enum types
    message_role_enum.drop(op.get_bind(), checkfirst=True)
    interview_status_enum.drop(op.get_bind(), checkfirst=True)
    experience_level_enum.drop(op.get_bind(), checkfirst=True)
