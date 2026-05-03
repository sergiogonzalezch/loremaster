"""Add image_generations and image_records tables

Revision ID: aaaa0000_add_image_batch
Revises: 15aea2b540d3
Create Date: 2026-05-03

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


revision: str = "aaaa0000_add_image_batch"
down_revision: Union[str, Sequence[str], None] = "15aea2b540d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "image_generations",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(length=36), nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=False),
        sa.Column("collection_id", sa.String(length=36), nullable=False),
        sa.Column("content_id", sa.String(length=36), nullable=True),
        sa.Column(
            "category", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False
        ),
        sa.Column(
            "auto_prompt", sqlmodel.sql.sqltypes.AutoString(length=1000), nullable=False
        ),
        sa.Column(
            "final_prompt", sqlmodel.sql.sqltypes.AutoString(length=1000), nullable=False
        ),
        sa.Column("prompt_token_count", sa.Integer(), nullable=False),
        sa.Column(
            "prompt_source", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False
        ),
        sa.Column("truncated", sa.Boolean(), nullable=False),
        sa.Column("batch_size", sa.Integer(), nullable=False),
        sa.Column(
            "backend", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False
        ),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["collection_id"],
            ["collections.id"],
        ),
        sa.ForeignKeyConstraint(
            ["content_id"],
            ["entity_contents.id"],
        ),
        sa.ForeignKeyConstraint(
            ["entity_id"],
            ["entities.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("image_generations", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_image_generations_collection_id"),
            ["collection_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_image_generations_entity_id"),
            ["entity_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_image_generations_content_id"),
            ["content_id"],
            unique=False,
        )

    op.create_table(
        "image_records",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(length=36), nullable=False),
        sa.Column("generation_id", sa.String(length=36), nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=False),
        sa.Column("collection_id", sa.String(length=36), nullable=False),
        sa.Column("seed", sa.Integer(), nullable=False),
        sa.Column(
            "storage_path", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True
        ),
        sa.Column(
            "filename", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True
        ),
        sa.Column(
            "extension", sqlmodel.sql.sqltypes.AutoString(length=10), nullable=False
        ),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("generation_ms", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["collection_id"],
            ["collections.id"],
        ),
        sa.ForeignKeyConstraint(
            ["entity_id"],
            ["entities.id"],
        ),
        sa.ForeignKeyConstraint(
            ["generation_id"],
            ["image_generations.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("image_records", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_image_records_collection_id"),
            ["collection_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_image_records_entity_id"),
            ["entity_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_image_records_generation_id"),
            ["generation_id"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("image_records", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_image_records_generation_id"))
        batch_op.drop_index(batch_op.f("ix_image_records_entity_id"))
        batch_op.drop_index(batch_op.f("ix_image_records_collection_id"))

    op.drop_table("image_records")

    with op.batch_alter_table("image_generations", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_image_generations_content_id"))
        batch_op.drop_index(batch_op.f("ix_image_generations_entity_id"))
        batch_op.drop_index(batch_op.f("ix_image_generations_collection_id"))

    op.drop_table("image_generations")