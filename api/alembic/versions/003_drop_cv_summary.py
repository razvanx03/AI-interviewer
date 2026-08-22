"""drop cv_summary from interviews table

Revision ID: 003_drop_cv_summary
Revises: 002_enums_and_candidates
Create Date: 2026-08-22 17:33:40.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '003_drop_cv_summary'
down_revision: Union[str, None] = '002_enums_and_candidates'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.drop_column('interviews', 'cv_summary')

def downgrade() -> None:
    op.add_column('interviews', sa.Column('cv_summary', sa.Text(), nullable=True))
