"""idea_images_uuid_pk

Revision ID: e7b2d4f9a1c6
Revises: c3f1a9e7b4d2
Create Date: 2026-08-17 00:00:00.000000

Changes:
  - Idea_Images.id:        integer -> UUID  (Image_To_Idea.image_id FK updated)
  - Idea_Images.image_path: column dropped (filename on disk is now `{id}.webp`)

For existing rows, the new id is parsed out of the old image_path
(`"<uuid4>.webp"` -> that same uuid4) so already-uploaded files on disk keep
working without being renamed. Only if a row's image_path doesn't look like
a `<uuid>.webp` name does it fall back to a freshly generated UUID, in which
case that file would need a manual rename to match.
"""
from typing import Sequence, Union
from alembic import op


revision: str = 'e7b2d4f9a1c6'
down_revision: Union[str, None] = 'c3f1a9e7b4d2'
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

    # 1  Add the new UUID column, then populate it from the old image_path
    #    (`"<uuid4>.webp"` -> that same uuid4) so existing files keep matching
    #    their row without needing to be renamed on disk. Rows whose
    #    image_path isn't a valid uuid filename fall back to a fresh UUID.
    op.execute('ALTER TABLE "Idea_Images" ADD COLUMN "id_uuid" UUID')
    op.execute('''
        DO $$ DECLARE r RECORD; BEGIN
            FOR r IN SELECT id, image_path FROM "Idea_Images" LOOP
                BEGIN
                    UPDATE "Idea_Images" SET id_uuid = regexp_replace(r.image_path, '\\.webp$', '')::uuid WHERE id = r.id;
                EXCEPTION WHEN invalid_text_representation THEN
                    UPDATE "Idea_Images" SET id_uuid = gen_random_uuid() WHERE id = r.id;
                END;
            END LOOP;
        END $$
    ''')
    op.execute('ALTER TABLE "Idea_Images" ALTER COLUMN "id_uuid" SET NOT NULL')

    # 2  Add a parallel UUID FK column on Image_To_Idea
    op.execute('ALTER TABLE "Image_To_Idea" ADD COLUMN "image_id_new" UUID')

    # 3  Populate it via the int -> UUID mapping in Idea_Images
    op.execute('UPDATE "Image_To_Idea" SET "image_id_new" = img."id_uuid" FROM "Idea_Images" img WHERE img."id" = "Image_To_Idea"."image_id"')

    # 4  Image_To_Idea has a composite PK (idea_id, image_id) — drop it first
    op.execute(_drop_pks('Image_To_Idea'))

    # 5  Drop every FK that points at Idea_Images.id
    op.execute(_drop_fks_referencing('Idea_Images'))

    # 6  Swap Idea_Images PK column: drop integer id, promote id_uuid -> id
    op.execute(_drop_pks('Idea_Images'))
    op.execute('ALTER TABLE "Idea_Images" DROP COLUMN "id"')
    op.execute('ALTER TABLE "Idea_Images" RENAME COLUMN "id_uuid" TO "id"')
    op.execute('ALTER TABLE "Idea_Images" ADD PRIMARY KEY ("id")')

    # 7  Swap image_id column on Image_To_Idea
    op.execute('ALTER TABLE "Image_To_Idea" DROP COLUMN "image_id"')
    op.execute('ALTER TABLE "Image_To_Idea" RENAME COLUMN "image_id_new" TO "image_id"')

    # 8  Recreate composite PK (both columns are now UUID)
    op.execute('ALTER TABLE "Image_To_Idea" ADD PRIMARY KEY ("idea_id", "image_id")')

    # 9  Recreate FK constraint for image_id
    op.execute('ALTER TABLE "Image_To_Idea" ADD CONSTRAINT "Image_To_Idea_image_id_fkey" FOREIGN KEY ("image_id") REFERENCES "Idea_Images" ("id") ON DELETE CASCADE')

    # 10  image_path is no longer used — filename on disk is now `{id}.webp`
    op.execute('ALTER TABLE "Idea_Images" DROP COLUMN "image_path"')


def downgrade() -> None:
    raise NotImplementedError(
        "Downgrade not supported: reversing a UUID PK migration would require "
        "re-generating integer sequences and remapping all FK values, and the "
        "dropped image_path values cannot be recovered."
    )
