"""Restore generated_texts table

Revision ID: b1f3c9d2e4a5
Revises: ae9ee92df7ea
Create Date: 2026-04-28 18:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = "b1f3c9d2e4a5"
down_revision: Union[str, Sequence[str], None] = "ae9ee92df7ea"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # a) Crear tabla generated_texts
    op.create_table(
        "generated_texts",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(length=36), nullable=False),
        sa.Column("entity_id", sa.String(36), nullable=False),
        sa.Column("collection_id", sa.String(36), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column(
            "query", sqlmodel.sql.sqltypes.AutoString(length=2000), nullable=False
        ),
        sa.Column(
            "raw_content",
            sqlmodel.sql.sqltypes.AutoString(length=10000),
            nullable=False,
        ),
        sa.Column("sources_count", sa.Integer(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["collection_id"], ["collections.id"]),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("generated_texts") as batch_op:
        batch_op.create_index("ix_generated_texts_entity_id", ["entity_id"])
        batch_op.create_index("ix_generated_texts_collection_id", ["collection_id"])

    # b) Poblar generated_texts desde entity_contents existentes
    op.execute("""
        INSERT INTO generated_texts
            (id, entity_id, collection_id, category, query,
             raw_content, sources_count, token_count, created_at)
        SELECT
            lower(hex(randomblob(4))) || '-' ||
            lower(hex(randomblob(2))) || '-4' ||
            substr(lower(hex(randomblob(2))),2) || '-' ||
            substr('89ab', abs(random()) % 4 + 1, 1) ||
            substr(lower(hex(randomblob(2))),2) || '-' ||
            lower(hex(randomblob(6))),
            entity_id, collection_id, category, query,
            content, sources_count, token_count, created_at
        FROM entity_contents
        WHERE is_deleted = 0
    """)

    # c) Agregar columna generated_text_id (nullable primero)
    with op.batch_alter_table("entity_contents") as batch_op:
        batch_op.add_column(
            sa.Column(
                "generated_text_id",
                sqlmodel.sql.sqltypes.AutoString(length=36),
                nullable=True,
            )
        )

    # d) Vincular registros existentes
    op.execute("""
        UPDATE entity_contents
        SET generated_text_id = (
            SELECT gt.id FROM generated_texts gt
            WHERE gt.entity_id = entity_contents.entity_id
              AND gt.collection_id = entity_contents.collection_id
              AND gt.category = entity_contents.category
              AND gt.created_at = entity_contents.created_at
        )
        WHERE is_deleted = 0
    """)

    # e) Hacer NOT NULL y crear FK
    with op.batch_alter_table("entity_contents") as batch_op:
        batch_op.alter_column("generated_text_id", nullable=False)
        batch_op.create_foreign_key(
            "fk_entity_contents_generated_text_id",
            "generated_texts",
            ["generated_text_id"],
            ["id"],
        )
        batch_op.create_index(
            "ix_entity_contents_generated_text_id", ["generated_text_id"]
        )

    # f) Quitar columnas que se movieron a generated_texts
    with op.batch_alter_table("entity_contents") as batch_op:
        batch_op.drop_column("query")
        batch_op.drop_column("sources_count")
        batch_op.drop_column("token_count")


def downgrade() -> None:
    # Restaurar columnas en entity_contents
    with op.batch_alter_table("entity_contents") as batch_op:
        batch_op.add_column(
            sa.Column("query", sa.String(2000), nullable=False, server_default="")
        )
        batch_op.add_column(
            sa.Column("sources_count", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("token_count", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.drop_index("ix_entity_contents_generated_text_id")
        batch_op.drop_constraint(
            "fk_entity_contents_generated_text_id", type_="foreignkey"
        )
        batch_op.drop_column("generated_text_id")

    op.drop_table("generated_texts")
