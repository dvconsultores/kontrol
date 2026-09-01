"""Regulación y traslados (008).

Revision ID: 0008_regulacion
Revises: 0007_nucleo_fiscal
Create Date: 2026-08-04
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0008_regulacion"
down_revision = "0007_nucleo_fiscal"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---------------- Maestros regulatorios ----------------
    op.create_table(
        "regulatory_authorities",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("validation_method", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_regulatory_authorities_company_id", "regulatory_authorities", ["company_id"])

    op.create_table(
        "permit_types",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("authority_id", sa.String(length=36), sa.ForeignKey("regulatory_authorities.id"), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("scope", sa.String(length=120), nullable=True),
        sa.Column("validation_method", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_permit_types_company_id", "permit_types", ["company_id"])
    op.create_index("ix_permit_types_authority_id", "permit_types", ["authority_id"])

    op.create_table(
        "official_registrations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("authority_id", sa.String(length=36), sa.ForeignKey("regulatory_authorities.id"), nullable=False),
        sa.Column("scope", sa.String(length=16), nullable=False),
        sa.Column("ref_number", sa.String(length=120), nullable=False),
        sa.Column("issued_at", sa.Date(), nullable=True),
        sa.Column("expires_at", sa.Date(), nullable=True),
        sa.Column("file_ref", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_official_registrations_company_id", "official_registrations", ["company_id"])
    op.create_index("ix_official_registrations_authority_id", "official_registrations", ["authority_id"])

    op.create_table(
        "regulatory_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("rubric_id", sa.String(length=36), nullable=True),
        sa.Column("product_id", sa.String(length=36), nullable=True),
        sa.Column("operation", sa.String(length=64), nullable=False, server_default="DESPACHO"),
        sa.Column("origin", sa.String(length=120), nullable=True),
        sa.Column("destination", sa.String(length=120), nullable=True),
        sa.Column("required_documents", sa.Text(), nullable=True),
        sa.Column("validity", sa.Text(), nullable=True),
        sa.Column("version", sa.String(length=32), nullable=False, server_default="1.0"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_regulatory_profiles_company_id", "regulatory_profiles", ["company_id"])

    op.create_table(
        "transport_vehicles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("plate", sa.String(length=32), nullable=False),
        sa.Column("vehicle_type", sa.String(length=64), nullable=True),
        sa.Column("capacity", sa.Float(), nullable=True),
        sa.Column("owner_party_id", sa.String(length=36), sa.ForeignKey("parties.id"), nullable=True),
        sa.Column("documents", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_transport_vehicles_company_id", "transport_vehicles", ["company_id"])

    op.create_table(
        "transport_drivers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("party_id", sa.String(length=36), sa.ForeignKey("parties.id"), nullable=False),
        sa.Column("license", sa.String(length=64), nullable=True),
        sa.Column("documents", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_transport_drivers_company_id", "transport_drivers", ["company_id"])
    op.create_index("ix_transport_drivers_party_id", "transport_drivers", ["party_id"])

    # ---------------- Permisos y guías ----------------
    op.create_table(
        "permit_instances",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("permit_type_id", sa.String(length=36), sa.ForeignKey("permit_types.id"), nullable=False),
        sa.Column("number", sa.String(length=120), nullable=False),
        sa.Column("issued_at", sa.Date(), nullable=True),
        sa.Column("expires_at", sa.Date(), nullable=True),
        sa.Column("origin", sa.String(length=120), nullable=True),
        sa.Column("destination", sa.String(length=120), nullable=True),
        sa.Column("products", sa.Text(), nullable=True),
        sa.Column("lots", sa.Text(), nullable=True),
        sa.Column("quantity", sa.Float(), nullable=True),
        sa.Column("vehicle_id", sa.String(length=36), sa.ForeignKey("transport_vehicles.id"), nullable=True),
        sa.Column("file_ref", sa.String(length=255), nullable=True),
        sa.Column("hash", sa.String(length=64), nullable=True),
        sa.Column("verification", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="DRAFT"),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_permit_instances_company_id", "permit_instances", ["company_id"])
    op.create_index("ix_permit_instances_permit_type_id", "permit_instances", ["permit_type_id"])

    op.create_table(
        "official_documents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("authority_id", sa.String(length=36), sa.ForeignKey("regulatory_authorities.id"), nullable=True),
        sa.Column("number", sa.String(length=120), nullable=False),
        sa.Column("organism", sa.String(length=120), nullable=True),
        sa.Column("issued_at", sa.Date(), nullable=True),
        sa.Column("expires_at", sa.Date(), nullable=True),
        sa.Column("file_ref", sa.String(length=255), nullable=True),
        sa.Column("hash", sa.String(length=64), nullable=True),
        sa.Column("verification", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="VALID"),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_official_documents_company_id", "official_documents", ["company_id"])

    # ---------------- Evaluación y bloqueo ----------------
    op.create_table(
        "regulatory_evaluations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("shipment_id", sa.String(length=36), nullable=False),
        sa.Column("shipment_line_ref", sa.String(length=120), nullable=True),
        sa.Column("profile_version_id", sa.String(length=36), nullable=True),
        sa.Column("required", sa.Text(), nullable=True),
        sa.Column("results", sa.Text(), nullable=True),
        sa.Column("blockers", sa.Text(), nullable=True),
        sa.Column("override", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="CLEARED"),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_regulatory_evaluations_company_id", "regulatory_evaluations", ["company_id"])
    op.create_index("ix_regulatory_evaluations_shipment_id", "regulatory_evaluations", ["shipment_id"])

    op.create_table(
        "approval_requests",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("object_ref", sa.String(length=200), nullable=False),
        sa.Column("rule_ref", sa.String(length=120), nullable=True),
        sa.Column("requester_id", sa.String(length=36), nullable=True),
        sa.Column("approvers", sa.Text(), nullable=True),
        sa.Column("risk", sa.String(length=32), nullable=True),
        sa.Column("amount", sa.Float(), nullable=True),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column("decision", sa.String(length=32), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_approval_requests_company_id", "approval_requests", ["company_id"])

    # ---------------- Contingencias ----------------
    op.create_table(
        "regulatory_contingencies",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("rule_ref", sa.String(length=120), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=False),
        sa.Column("allowed_by", sa.String(length=36), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_regulatory_contingencies_company_id", "regulatory_contingencies", ["company_id"])


def downgrade() -> None:
    op.drop_table("regulatory_contingencies")
    op.drop_table("approval_requests")
    op.drop_table("regulatory_evaluations")
    op.drop_table("official_documents")
    op.drop_table("permit_instances")
    op.drop_table("transport_drivers")
    op.drop_table("transport_vehicles")
    op.drop_table("regulatory_profiles")
    op.drop_table("official_registrations")
    op.drop_table("permit_types")
    op.drop_table("regulatory_authorities")
