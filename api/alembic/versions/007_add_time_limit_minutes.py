"""add time_limit_minutes to interviews table

Revision ID: 007_add_time_limit_minutes
Revises: 006_add_dynamic_topics_plan
Create Date: 2026-08-29 15:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '007_add_time_limit_minutes'
down_revision: Union[str, None] = '006_add_dynamic_topics_plan'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column('interviews', sa.Column('time_limit_minutes', sa.Integer(), nullable=True))

def downgrade() -> None:
    op.drop_column('interviews', 'time_limit_minutes')
