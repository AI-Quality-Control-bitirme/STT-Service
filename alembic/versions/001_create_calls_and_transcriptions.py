"""create calls and transcriptions tables

Revision ID: 001
Revises:
Create Date: 2026-11-20

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

processing_status = sa.Enum(
    "pending",
    "processing",
    "completed",
    "failed",
    name="processing_status",
    native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "calls",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_call_id", sa.String(length=255), nullable=True),
        sa.Column("caller_number", sa.String(length=64), nullable=True),
        sa.Column("callee_number", sa.String(length=64), nullable=True),
        sa.Column("audio_file_ref", sa.Text(), nullable=False),
        sa.Column("processing_status", processing_status, nullable=False),
        sa.Column("call_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("call_ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "transcriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("call_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("transcript_text", sa.Text(), nullable=True),
        sa.Column("language", sa.String(), nullable=True),
        sa.Column("processing_status", processing_status, nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["call_id"], ["calls.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_transcriptions_call_id"), "transcriptions", ["call_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_transcriptions_call_id"), table_name="transcriptions")
    op.drop_table("transcriptions")
    op.drop_table("calls")