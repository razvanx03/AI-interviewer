"""add active_question_number and consecutive_clarifications to interviews table

Revision ID: 004_add_active_question_tracking
Revises: 003_drop_cv_summary
Create Date: 2026-08-23 15:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '004_add_active_question_tracking'
down_revision: Union[str, None] = '003_drop_cv_summary'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column('interviews', sa.Column('active_question_number', sa.Integer(), nullable=True, server_default='1'))
    op.add_column('interviews', sa.Column('consecutive_clarifications', sa.Integer(), nullable=False, server_default='0'))

def downgrade() -> None:
    op.drop_column('interviews', 'consecutive_clarifications')
    op.drop_column('interviews', 'active_question_number')
