"""add dynamic topics_plan and topic tracking to interviews table

Revision ID: 006_add_dynamic_topics_plan
Revises: 005_add_cvs_table
Create Date: 2026-08-23 22:10:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '006_add_dynamic_topics_plan'
down_revision: Union[str, None] = '005_add_cvs_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column('interviews', sa.Column('topics_plan', sa.JSON(), nullable=True, server_default='[]'))
    op.add_column('interviews', sa.Column('current_topic_index', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('interviews', sa.Column('topic_follow_up_count', sa.Integer(), nullable=False, server_default='0'))

def downgrade() -> None:
    op.drop_column('interviews', 'topic_follow_up_count')
    op.drop_column('interviews', 'current_topic_index')
    op.drop_column('interviews', 'topics_plan')
