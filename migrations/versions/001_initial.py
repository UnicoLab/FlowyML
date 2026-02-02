"""Initial schema migration.

Revision ID: 001_initial
Revises: None
Create Date: 2026-02-02

This migration creates the initial FlowyML database schema.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create initial FlowyML tables."""

    # Runs table
    op.create_table(
        "runs",
        sa.Column("run_id", sa.String(), primary_key=True),
        sa.Column("pipeline_name", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("started_at", sa.String()),
        sa.Column("ended_at", sa.String()),
        sa.Column("parameters", sa.Text()),
        sa.Column("metadata", sa.Text()),
        sa.Column("parent_run_id", sa.String()),
        sa.Column("experiment_id", sa.String()),
        sa.Column("project", sa.String()),
    )

    # Artifacts table
    op.create_table(
        "artifacts",
        sa.Column("artifact_id", sa.String(), primary_key=True),
        sa.Column("run_id", sa.String()),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("artifact_type", sa.String()),
        sa.Column("path", sa.String()),
        sa.Column("uri", sa.String()),
        sa.Column("metadata", sa.Text()),
        sa.Column("created_at", sa.String()),
        sa.Column("project", sa.String()),
    )

    # Step results table
    op.create_table(
        "step_results",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.String(), nullable=False),
        sa.Column("step_name", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("started_at", sa.String()),
        sa.Column("ended_at", sa.String()),
        sa.Column("error", sa.Text()),
        sa.Column("outputs", sa.Text()),
    )

    # Metrics table
    op.create_table(
        "metrics",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("step", sa.Integer()),
        sa.Column("timestamp", sa.String()),
    )

    # Experiments table
    op.create_table(
        "experiments",
        sa.Column("experiment_id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("tags", sa.Text()),
        sa.Column("created_at", sa.String()),
        sa.Column("project", sa.String()),
    )

    # Traces table
    op.create_table(
        "traces",
        sa.Column("trace_id", sa.String(), primary_key=True),
        sa.Column("run_id", sa.String()),
        sa.Column("parent_trace_id", sa.String()),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("trace_type", sa.String()),
        sa.Column("inputs", sa.Text()),
        sa.Column("outputs", sa.Text()),
        sa.Column("metadata", sa.Text()),
        sa.Column("started_at", sa.String()),
        sa.Column("ended_at", sa.String()),
        sa.Column("status", sa.String()),
        sa.Column("error", sa.Text()),
        sa.Column("prompt_tokens", sa.Integer()),
        sa.Column("completion_tokens", sa.Integer()),
        sa.Column("total_tokens", sa.Integer()),
        sa.Column("cost", sa.Float()),
        sa.Column("model", sa.String()),
        sa.Column("project", sa.String()),
        sa.Column("created_at", sa.String()),
    )

    # Pipeline definitions table
    op.create_table(
        "pipeline_definitions",
        sa.Column("pipeline_name", sa.String(), primary_key=True),
        sa.Column("definition", sa.Text(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("updated_at", sa.String(), nullable=False),
    )

    # Projects table
    op.create_table(
        "projects",
        sa.Column("name", sa.String(), primary_key=True),
        sa.Column("description", sa.Text()),
        sa.Column("tags", sa.Text()),
        sa.Column("created_at", sa.String()),
        sa.Column("updated_at", sa.String()),
    )

    # Model versions table
    op.create_table(
        "model_versions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("version", sa.String(), nullable=False),
        sa.Column("stage", sa.String(), nullable=False),
        sa.Column("framework", sa.String(), nullable=False),
        sa.Column("model_path", sa.String(), nullable=False),
        sa.Column("metrics", sa.Text()),
        sa.Column("tags", sa.Text()),
        sa.Column("schema", sa.Text()),
        sa.Column("description", sa.Text()),
        sa.Column("author", sa.String()),
        sa.Column("parent_version", sa.String()),
        sa.Column("created_at", sa.String()),
        sa.Column("updated_at", sa.String()),
    )

    # Pipeline templates table
    op.create_table(
        "pipeline_templates",
        sa.Column("template_id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("definition", sa.Text(), nullable=False),
        sa.Column("tags", sa.Text()),
        sa.Column("author", sa.String()),
        sa.Column("category", sa.String()),
        sa.Column("is_public", sa.Integer(), default=0),
        sa.Column("created_at", sa.String()),
        sa.Column("updated_at", sa.String()),
    )


def downgrade() -> None:
    """Drop all tables."""
    op.drop_table("pipeline_templates")
    op.drop_table("model_versions")
    op.drop_table("projects")
    op.drop_table("pipeline_definitions")
    op.drop_table("traces")
    op.drop_table("experiments")
    op.drop_table("metrics")
    op.drop_table("step_results")
    op.drop_table("artifacts")
    op.drop_table("runs")
