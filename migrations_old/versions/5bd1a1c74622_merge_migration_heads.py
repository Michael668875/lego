"""merge migration heads

Revision ID: 5bd1a1c74622
Revises: 6ac2dc32c8ef, ea6f9c577e73
Create Date: 2026-10-14 12:15:26.401274

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5bd1a1c74622'
down_revision = ('6ac2dc32c8ef', 'ea6f9c577e73')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
