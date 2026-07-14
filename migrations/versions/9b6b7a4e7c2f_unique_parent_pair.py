"""unique parent pair

Revision ID: 9b6b7a4e7c2f
Revises: c2ba62408b75
Create Date: 2026-07-14 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "9b6b7a4e7c2f"
down_revision: Union[str, Sequence[str], None] = "c2ba62408b75"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_unique_constraint("uq_parent_first_second", "parent", ["first", "second"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("uq_parent_first_second", "parent", type_="unique")
