"""Add per-tenant org binding to agent_identities

Adds org_id, owner_user_id, and public_key to agent_identities so an agent's
signing identity can be scoped to the Clerk org/user that owns it and the DB row
can serve as the verification authority for its Ed25519 public key.

See docs/agent_card_design.md "Current State & Identity Hardening" and the
corrected Phase 1 item #1 in docs/TrustMesh_Master_Roadmap.md.

Revision ID: a1b2c3d4e5f6
Revises: d921b714fa3f
Create Date: 2026-07-23 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'd921b714fa3f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('agent_identities', schema=None) as batch_op:
        batch_op.add_column(sa.Column('org_id', sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column('owner_user_id', sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column('public_key', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('agent_identities', schema=None) as batch_op:
        batch_op.drop_column('public_key')
        batch_op.drop_column('owner_user_id')
        batch_op.drop_column('org_id')
