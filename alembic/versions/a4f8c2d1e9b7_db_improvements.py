"""db_improvements

Revision ID: a4f8c2d1e9b7
Revises: 5ac67de54573
Create Date: 2026-04-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a4f8c2d1e9b7'
down_revision: Union[str, None] = '5ac67de54573'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Fix 5: Merge User_Token_Blacklist into User_Token
    op.add_column('User_Token', sa.Column('is_blacklisted', sa.Boolean(), nullable=False, server_default='false'))
    op.drop_table('User_Token_Blacklist')

    # Fix 9: Unique constraints on Users
    op.create_unique_constraint('uq_users_email', 'Users', ['email'])

    # Fix 10: Indexes on frequently queried columns
    op.create_index('ix_user_token_uuid', 'User_Token', ['uuid'])
    op.create_index('ix_ideas_owner_id', 'Ideas', ['owner_id'])
    op.create_index('ix_ideas_status_id', 'Ideas', ['status_id'])
    op.create_index('ix_ideas_category_id', 'Ideas', ['category_id'])

    # Fix 11: Rename Idea_Categorys -> Idea_Categories
    op.rename_table('Idea_Categorys', 'Idea_Categories')

    # Fix 12: Rename user_group -> user_group_id
    op.alter_column('Users', 'user_group', new_column_name='user_group_id')


def downgrade() -> None:
    op.alter_column('Users', 'user_group_id', new_column_name='user_group')

    op.rename_table('Idea_Categories', 'Idea_Categorys')

    op.drop_index('ix_ideas_category_id', table_name='Ideas')
    op.drop_index('ix_ideas_status_id', table_name='Ideas')
    op.drop_index('ix_ideas_owner_id', table_name='Ideas')
    op.drop_index('ix_user_token_uuid', table_name='User_Token')

    op.drop_constraint('uq_users_email', 'Users', type_='unique')

    op.drop_column('User_Token', 'is_blacklisted')
    op.create_table('User_Token_Blacklist',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('token_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['token_id'], ['User_Token.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
