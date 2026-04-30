"""uuid_primary_keys

Revision ID: c3f1a9e7b4d2
Revises: a4f8c2d1e9b7
Create Date: 2026-04-30 00:00:00.000000

Changes:
  - Users.id:                  integer -> UUID  (all FK columns updated)
  - Ideas.id:                  integer -> UUID  (all FK columns updated)
  - User_Token:                remove id column, make uuid the PK
  - Reset_Email_Validation:    remove id column, make user_id the PK
  - Reset_Password:            remove id column, make code the PK

All existing data is preserved.
"""
from typing import Sequence, Union
from alembic import op


revision: str = 'c3f1a9e7b4d2'
down_revision: Union[str, None] = 'a4f8c2d1e9b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _drop_pks(table: str) -> str:
    """PL/pgSQL block that drops all PK constraints on a table by name."""
    return f'''
        DO $$ DECLARE r RECORD; BEGIN
            FOR r IN SELECT conname FROM pg_constraint
                     WHERE conrelid = '"{table}"'::regclass AND contype = 'p'
            LOOP
                EXECUTE 'ALTER TABLE "{table}" DROP CONSTRAINT ' || quote_ident(r.conname);
            END LOOP;
        END $$
    '''


def _drop_fks_referencing(table: str) -> str:
    """PL/pgSQL block that drops all FK constraints whose target is *table*."""
    return f'''
        DO $$ DECLARE r RECORD; BEGIN
            FOR r IN SELECT c.conname, c.conrelid::regclass AS tbl
                     FROM pg_constraint c
                     WHERE c.confrelid = '"{table}"'::regclass AND c.contype = 'f'
            LOOP
                EXECUTE 'ALTER TABLE ' || r.tbl || ' DROP CONSTRAINT ' || quote_ident(r.conname);
            END LOOP;
        END $$
    '''


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    # ===========================================================
    # Phase 1 — Users.id: integer → UUID
    # ===========================================================

    # 1.1  Add the new UUID column; auto-generate a UUID for every existing row
    op.execute('ALTER TABLE "Users" ADD COLUMN "id_uuid" UUID NOT NULL DEFAULT gen_random_uuid()')

    # 1.2  Add a parallel UUID FK column in every table that references Users.id
    op.execute('ALTER TABLE "Ideas"                  ADD COLUMN "owner_id_new"  UUID')
    op.execute('ALTER TABLE "Idea_Images"            ADD COLUMN "user_id_new"   UUID')
    op.execute('ALTER TABLE "Idea_Likes"             ADD COLUMN "user_id_new"   UUID')
    op.execute('ALTER TABLE "User_Token"             ADD COLUMN "user_id_new"   UUID')
    op.execute('ALTER TABLE "User_Activation"        ADD COLUMN "user_id_new"   UUID')
    op.execute('ALTER TABLE "User_Feedback"          ADD COLUMN "user_id_new"   UUID')
    op.execute('ALTER TABLE "Reset_Email_Validation" ADD COLUMN "user_id_new"   UUID')
    op.execute('ALTER TABLE "Reset_Password"         ADD COLUMN "user_id_new"   UUID')

    # 1.3  Populate the parallel columns via the int -> UUID mapping in Users
    op.execute('UPDATE "Ideas"                  SET "owner_id_new"  = u."id_uuid" FROM "Users" u WHERE u."id" = "Ideas"."owner_id"')
    op.execute('UPDATE "Idea_Images"            SET "user_id_new"   = u."id_uuid" FROM "Users" u WHERE u."id" = "Idea_Images"."user_id"')
    op.execute('UPDATE "Idea_Likes"             SET "user_id_new"   = u."id_uuid" FROM "Users" u WHERE u."id" = "Idea_Likes"."user_id"')
    op.execute('UPDATE "User_Token"             SET "user_id_new"   = u."id_uuid" FROM "Users" u WHERE u."id" = "User_Token"."user_id"')
    op.execute('UPDATE "User_Activation"        SET "user_id_new"   = u."id_uuid" FROM "Users" u WHERE u."id" = "User_Activation"."user_id"')
    op.execute('UPDATE "User_Feedback"          SET "user_id_new"   = u."id_uuid" FROM "Users" u WHERE u."id" = "User_Feedback"."user_id"')
    op.execute('UPDATE "Reset_Email_Validation" SET "user_id_new"   = u."id_uuid" FROM "Users" u WHERE u."id" = "Reset_Email_Validation"."user_id"')
    op.execute('UPDATE "Reset_Password"         SET "user_id_new"   = u."id_uuid" FROM "Users" u WHERE u."id" = "Reset_Password"."user_id"')

    # 1.4  Idea_Likes has a composite PK (idea_id, user_id).
    #      Drop it now so we can replace the user_id column.
    op.execute(_drop_pks('Idea_Likes'))

    # 1.5  Drop every FK that points at Users.id
    op.execute(_drop_fks_referencing('Users'))

    # 1.6  Swap Users PK column: drop integer id, promote id_uuid -> id
    op.execute(_drop_pks('Users'))
    op.execute('ALTER TABLE "Users" DROP COLUMN "id"')
    op.execute('ALTER TABLE "Users" RENAME COLUMN "id_uuid" TO "id"')
    op.execute('ALTER TABLE "Users" ADD PRIMARY KEY ("id")')

    # 1.7  Swap old integer FK columns with the new UUID columns
    for table, col in [
        ('Ideas',                  'owner_id'),
        ('Idea_Images',            'user_id'),
        ('Idea_Likes',             'user_id'),
        ('User_Token',             'user_id'),
        ('User_Activation',        'user_id'),
        ('User_Feedback',          'user_id'),
        ('Reset_Email_Validation', 'user_id'),
        ('Reset_Password',         'user_id'),
    ]:
        op.execute(f'ALTER TABLE "{table}" DROP COLUMN "{col}"')
        op.execute(f'ALTER TABLE "{table}" RENAME COLUMN "{col}_new" TO "{col}"')

    # 1.8  Recreate FK constraints (user_id / owner_id -> Users.id)
    #      Idea_Likes PK is NOT yet recreated — idea_id is still integer (Phase 2).
    op.execute('ALTER TABLE "Ideas"                  ADD CONSTRAINT "Ideas_owner_id_fkey"                  FOREIGN KEY ("owner_id")  REFERENCES "Users" ("id") ON DELETE SET NULL')
    op.execute('ALTER TABLE "Idea_Images"            ADD CONSTRAINT "Idea_Images_user_id_fkey"             FOREIGN KEY ("user_id")   REFERENCES "Users" ("id") ON DELETE SET NULL')
    op.execute('ALTER TABLE "Idea_Likes"             ADD CONSTRAINT "Idea_Likes_user_id_fkey"              FOREIGN KEY ("user_id")   REFERENCES "Users" ("id") ON DELETE CASCADE')
    op.execute('ALTER TABLE "User_Token"             ADD CONSTRAINT "User_Token_user_id_fkey"              FOREIGN KEY ("user_id")   REFERENCES "Users" ("id") ON DELETE CASCADE')
    op.execute('ALTER TABLE "User_Activation"        ADD CONSTRAINT "User_Activation_user_id_fkey"         FOREIGN KEY ("user_id")   REFERENCES "Users" ("id") ON DELETE CASCADE')
    op.execute('ALTER TABLE "User_Feedback"          ADD CONSTRAINT "User_Feedback_user_id_fkey"           FOREIGN KEY ("user_id")   REFERENCES "Users" ("id") ON DELETE SET NULL')
    op.execute('ALTER TABLE "Reset_Email_Validation" ADD CONSTRAINT "ResetEmailValidation_user_id_fkey"    FOREIGN KEY ("user_id")   REFERENCES "Users" ("id") ON DELETE CASCADE')
    op.execute('ALTER TABLE "Reset_Password"         ADD CONSTRAINT "Reset_Password_user_id_fkey"          FOREIGN KEY ("user_id")   REFERENCES "Users" ("id") ON DELETE CASCADE')

    # ===========================================================
    # Phase 2 — Ideas.id: integer → UUID
    # ===========================================================

    # 2.1  Add UUID column to Ideas
    op.execute('ALTER TABLE "Ideas" ADD COLUMN "id_uuid" UUID NOT NULL DEFAULT gen_random_uuid()')

    # 2.2  Add parallel UUID FK columns in tables that reference Ideas.id
    op.execute('ALTER TABLE "Idea_Likes"    ADD COLUMN "idea_id_new" UUID')
    op.execute('ALTER TABLE "Image_To_Idea" ADD COLUMN "idea_id_new" UUID')

    # 2.3  Populate
    op.execute('UPDATE "Idea_Likes"    SET "idea_id_new" = i."id_uuid" FROM "Ideas" i WHERE i."id" = "Idea_Likes"."idea_id"')
    op.execute('UPDATE "Image_To_Idea" SET "idea_id_new" = i."id_uuid" FROM "Ideas" i WHERE i."id" = "Image_To_Idea"."idea_id"')

    # 2.4  Image_To_Idea has a composite PK (idea_id, image_id) — drop it first
    op.execute(_drop_pks('Image_To_Idea'))

    # 2.5  Drop every FK that points at Ideas.id
    op.execute(_drop_fks_referencing('Ideas'))

    # 2.6  Swap Ideas PK column
    op.execute(_drop_pks('Ideas'))
    op.execute('ALTER TABLE "Ideas" DROP COLUMN "id"')
    op.execute('ALTER TABLE "Ideas" RENAME COLUMN "id_uuid" TO "id"')
    op.execute('ALTER TABLE "Ideas" ADD PRIMARY KEY ("id")')

    # 2.7  Swap idea_id columns in both dependent tables
    for table in ['Idea_Likes', 'Image_To_Idea']:
        op.execute(f'ALTER TABLE "{table}" DROP COLUMN "idea_id"')
        op.execute(f'ALTER TABLE "{table}" RENAME COLUMN "idea_id_new" TO "idea_id"')

    # 2.8  Recreate composite PKs (both columns are now UUID)
    op.execute('ALTER TABLE "Idea_Likes"    ADD PRIMARY KEY ("idea_id", "user_id")')
    op.execute('ALTER TABLE "Image_To_Idea" ADD PRIMARY KEY ("idea_id", "image_id")')

    # 2.9  Recreate FK constraints for idea_id
    #      Image_To_Idea.image_id FK was never dropped and remains intact.
    op.execute('ALTER TABLE "Idea_Likes"    ADD CONSTRAINT "Idea_Likes_idea_id_fkey"    FOREIGN KEY ("idea_id") REFERENCES "Ideas" ("id") ON DELETE CASCADE')
    op.execute('ALTER TABLE "Image_To_Idea" ADD CONSTRAINT "Image_To_Idea_idea_id_fkey" FOREIGN KEY ("idea_id") REFERENCES "Ideas" ("id") ON DELETE CASCADE')

    # ===========================================================
    # Phase 3 — User_Token: remove id, make uuid the PK
    # ===========================================================

    op.execute(_drop_pks('User_Token'))
    op.execute('DROP INDEX IF EXISTS "ix_user_token_uuid"')
    op.execute('ALTER TABLE "User_Token" DROP COLUMN "id"')
    op.execute('ALTER TABLE "User_Token" ADD PRIMARY KEY ("uuid")')

    # ===========================================================
    # Phase 4 — Reset_Email_Validation: remove id, make user_id the PK
    #           user_id must be unique → keep only the newest row per user
    # ===========================================================

    op.execute('''
        DELETE FROM "Reset_Email_Validation"
        WHERE id NOT IN (
            SELECT MAX(id) FROM "Reset_Email_Validation" GROUP BY user_id
        )
    ''')
    op.execute(_drop_pks('Reset_Email_Validation'))
    op.execute('ALTER TABLE "Reset_Email_Validation" DROP COLUMN "id"')
    op.execute('ALTER TABLE "Reset_Email_Validation" ADD PRIMARY KEY ("user_id")')

    # ===========================================================
    # Phase 5 — Reset_Password: remove id, make code the PK
    # ===========================================================

    op.execute(_drop_pks('Reset_Password'))
    op.execute('ALTER TABLE "Reset_Password" DROP COLUMN "id"')
    op.execute('ALTER TABLE "Reset_Password" ADD PRIMARY KEY ("code")')


def downgrade() -> None:
    raise NotImplementedError(
        "Downgrade not supported: reversing a UUID PK migration would require "
        "re-generating integer sequences and remapping all FK values."
    )
