"""create sentences table

Revision ID: 2b7a4444d04b
Revises: 
Create Date: 2025-06-01 21:49:32.058055

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2b7a4444d04b'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('sentences',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('case_id', sa.String(), nullable=False),
    sa.Column('offender_name', sa.String(), nullable=False),
    sa.Column('offence_code', sa.String(), nullable=False),
    sa.Column('offence_date', sa.Date(), nullable=True),
    sa.Column('sentence_imposed', sa.JSON(), nullable=True),
    sa.Column('citation', sa.JSON(), nullable=True),
    sa.Column('is_appeal', sa.Boolean(), nullable=True),
    sa.Column('dissent', sa.Boolean(), nullable=True),
    sa.Column('lower_court_sentence_varied', sa.Boolean(), nullable=True),
    sa.Column('higher_court_varied_sentence', sa.Boolean(), nullable=True),
    sa.Column('time_analysis_started', sa.TIMESTAMP(), nullable=True),
    sa.Column('time_analysis_stopped', sa.TIMESTAMP(), nullable=True),
    sa.Column('human_verified', sa.Boolean(), nullable=True),
    sa.Column('human_modified', sa.Boolean(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('sentences')
    # ### end Alembic commands ###
