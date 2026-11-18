"""Initial database schema.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-11-18 18:52:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tenants_email"), "tenants", ["email"], unique=True)

    op.create_table(
        "api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("key_prefix", sa.String(length=16), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_api_keys_key_hash"), "api_keys", ["key_hash"], unique=True)
    op.create_index(op.f("ix_api_keys_tenant_id"), "api_keys", ["tenant_id"], unique=False)

    op.create_table(
        "instances",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("instance_name", sa.String(length=100), nullable=False),
        sa.Column("evo_instance_id", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("webhook_url", sa.String(length=500), nullable=True),
        sa.Column("webhook_secret", sa.String(length=120), nullable=True),
        sa.Column(
            "webhook_events",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("ai_enabled", sa.Boolean(), nullable=False),
        sa.Column("ai_model", sa.String(length=80), nullable=True),
        sa.Column("ai_system_prompt", sa.String(length=2000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_instances_instance_name"), "instances", ["instance_name"], unique=True
    )
    op.create_index(op.f("ix_instances_tenant_id"), "instances", ["tenant_id"], unique=False)

    op.create_table(
        "message_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("instance_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("direction", sa.String(length=16), nullable=False),
        sa.Column("remote_jid", sa.String(length=120), nullable=False),
        sa.Column("message_type", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column(
            "payload_summary",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["instance_id"], ["instances.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_message_logs_instance_id"), "message_logs", ["instance_id"], unique=False
    )
    op.create_index(
        op.f("ix_message_logs_remote_jid"), "message_logs", ["remote_jid"], unique=False
    )

    op.create_table(
        "webhook_deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("instance_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("target_url", sa.String(length=500), nullable=False),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["instance_id"], ["instances.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_webhook_deliveries_event_type"),
        "webhook_deliveries",
        ["event_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_webhook_deliveries_instance_id"),
        "webhook_deliveries",
        ["instance_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_webhook_deliveries_instance_id"), table_name="webhook_deliveries")
    op.drop_index(op.f("ix_webhook_deliveries_event_type"), table_name="webhook_deliveries")
    op.drop_table("webhook_deliveries")

    op.drop_index(op.f("ix_message_logs_remote_jid"), table_name="message_logs")
    op.drop_index(op.f("ix_message_logs_instance_id"), table_name="message_logs")
    op.drop_table("message_logs")

    op.drop_index(op.f("ix_instances_tenant_id"), table_name="instances")
    op.drop_index(op.f("ix_instances_instance_name"), table_name="instances")
    op.drop_table("instances")

    op.drop_index(op.f("ix_api_keys_tenant_id"), table_name="api_keys")
    op.drop_index(op.f("ix_api_keys_key_hash"), table_name="api_keys")
    op.drop_table("api_keys")

    op.drop_index(op.f("ix_tenants_email"), table_name="tenants")
    op.drop_table("tenants")
