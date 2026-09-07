"""add active_question_text, active_question_status, assessed_topics, language, conversation_summary to interviews

Revision ID: 013_add_conv_state
Revises: 012_drop_cvs_table
Create Date: 2026-09-07 20:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '013_add_conv_state'
down_revision: Union[str, None] = '012_drop_cvs_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('interviews', sa.Column('active_question_text', sa.Text(), nullable=True))
    op.add_column('interviews', sa.Column('active_question_status', sa.String(length=30), nullable=False, server_default='INTRO'))
    op.add_column('interviews', sa.Column('assessed_topics', sa.JSON(), nullable=True, server_default='[]'))
    op.add_column('interviews', sa.Column('language', sa.String(length=10), nullable=False, server_default='en'))
    op.add_column('interviews', sa.Column('conversation_summary', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('interviews', 'conversation_summary')
    op.drop_column('interviews', 'language')
    op.drop_column('interviews', 'assessed_topics')
    op.drop_column('interviews', 'active_question_status')
    op.drop_column('interviews', 'active_question_text')
