"""Add tamper_alerted_at to negotiation_sessions

Revision ID: d921b714fa3f
Revises: 677b6e36ce2e
Create Date: 2026-07-22 11:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd921b714fa3f'
down_revision: Union[str, Sequence[str], None] = '677b6e36ce2e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('negotiation_sessions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('tamper_alerted_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('negotiation_sessions', schema=None) as batch_op:
        batch_op.drop_column('tamper_alerted_at')
