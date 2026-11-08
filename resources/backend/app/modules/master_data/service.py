"""Servicios de maestros (002-maestros).

- Validación de RIF (formato) y texto de identificadores.
- Control de duplicidad de RIF por empresa/rol (FR-002-002).
- `allowed_actions` calculadas en backend (FR-002-042).
- Perfiles: validación de versiones (sin solape de vigencia).
"""

from __future__ import annotations

import re

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.master_data.models import Party

# --------------------------------------------------------------------------- #
# Validadores
# --------------------------------------------------------------------------- #
# RIF: J/V/E/G/C-8 dígitos-1 dígito (ej. J-12345678-9)
_RIF_RE = re.compile(r"^[JVE GCPjvegcp][-]?\d{8}[-]?\d$")
# Cédula: V/E-6 a 8 dígitos
_ID_RE = re.compile(r"^[VEve][-]?\d{6,8}$")


def normalize_rif(value: str) -> str:
    """Normaliza un RIF a formato canónico (J-XXXXXXXX-X)."""
    cleaned = value.strip().upper().replace("-", "")
    if not _RIF_RE.match(cleaned.replace(" ", "")) and not _RIF_RE.match(value.strip().upper()):
        # Permitir el formato canónico
        if not re.match(r"^[JVEGCP]\d{8}\d$", cleaned):
            raise KontrolError(code="INVALID_RIF", message="El RIF no tiene un formato válido", status_code=422)
    if len(cleaned) == 10 and cleaned[:1] in "JVEGCP":
        return f"{cleaned[0]}-{cleaned[1:9]}-{cleaned[9]}"
    return value.strip().upper()


def validate_tax_id(value: str, person_type: str = "JURIDICA") -> str:
    """Valida y normaliza el identificador fiscal (RIF) o cédula."""
    if person_type in ("JURIDICA", "PUBLICA", "EXTRANJERA", "GUBERNAMENTAL"):
        return normalize_rif(value)
    # Persona natural: cédula o RIF
    v = value.strip().upper()
    if _ID_RE.match(v) or _RIF_RE.match(v):
        return v.replace("-", "")
    raise KontrolError(code="INVALID_TAX_ID", message="El identificador fiscal no es válido", status_code=422)


def is_duplicate_party(
    db: Session,
    *,
    company_id: str,
    tax_id: str,
    role: str,
    exclude_party_id: str | None = None,
) -> bool:
    """Controla duplicidad de RIF por empresa y rol (FR-002-002).

    Un mismo tercero puede tener varios roles; se evita duplicar el RIF en el
    mismo rol dentro de la misma empresa.
    """
    query = select(Party).where(Party.company_id == company_id, Party.tax_id == tax_id)
    if exclude_party_id:
        query = query.where(Party.id != exclude_party_id)
    party = db.execute(query).scalars().first()
    if party is None:
        return False
    return role in (party.roles or [])


def ensure_no_duplicate(
    db: Session,
    *,
    company_id: str,
    tax_id: str,
    role: str,
    exclude_party_id: str | None = None,
) -> None:
    if is_duplicate_party(db, company_id=company_id, tax_id=tax_id, role=role, exclude_party_id=exclude_party_id):
        raise ConflictError(
            code="PARTY_DUPLICATE_TAX_ID",
            message=f"Ya existe un tercero con este RIF en el rol '{role}' para esta empresa.",
        )


def require_eligible_party(db: Session, *, company_id: str, party_id: str, role: str | None, require_active: bool) -> Party:
    """Autoridad única de elegibilidad del tercero para operaciones nuevas (delta terceros, Spec 002)."""
    party = db.get(Party, party_id)
    if party is None or party.company_id != company_id:
        raise NotFoundError(code="PARTY_NOT_FOUND", message="Tercero no encontrado")
    if role is not None and role.upper() not in {r.upper() for r in (party.roles or [])}:
        raise ConflictError(code="PARTY_ROLE_REQUIRED", message=f"El tercero no tiene el rol {role.upper()}.")
    if require_active and party.status != "ACTIVE":
        raise ConflictError(code="PARTY_INACTIVE", message="El tercero no está activo.")
    return party


# --------------------------------------------------------------------------- #
# allowed_actions
# --------------------------------------------------------------------------- #
def party_allowed_actions(party: Party) -> dict[str, bool]:
    active = party.status == "ACTIVE"
    return {
        "view": True,
        "edit": True,
        "activate": not active,
        "deactivate": active,
        "delete": False,  # los terceros con historia no se eliminan
        "approve": True,
        "audit": True,
    }


def item_allowed_actions(status: str) -> dict[str, bool]:
    active = status == "ACTIVE"
    return {
        "view": True,
        "edit": True,
        "activate": not active,
        "deactivate": active,
        "delete": False,
        "print": True,
        "export": True,
    }


# --------------------------------------------------------------------------- #
# Perfiles: validación de vigencia (sin solape)
# --------------------------------------------------------------------------- #
def assert_no_overlap(
    db: Session,
    *,
    profile_type: str,
    code: str,
    effective_from,
    effective_to,
    exclude_id: str | None = None,
) -> None:
    from app.modules.master_data.models import ProfileVersion

    if effective_from is None or effective_to is None:
        return
    if effective_from >= effective_to:
        raise KontrolError(code="PROFILE_INVALID_VIGENCIA", message="La vigencia del perfil es inválida", status_code=422)

    query = (
        select(func.count())
        .select_from(ProfileVersion)
        .where(
            ProfileVersion.profile_type == profile_type,
            ProfileVersion.code == code,
            ProfileVersion.status == "ACTIVE",
            ProfileVersion.effective_from < effective_to,
            ProfileVersion.effective_to > effective_from,
        )
    )
    if exclude_id:
        from app.modules.master_data.models import ProfileVersion as PV

        query = (
            select(func.count())
            .select_from(PV)
            .where(
                PV.profile_type == profile_type,
                PV.code == code,
                PV.status == "ACTIVE",
                PV.effective_from < effective_to,
                PV.effective_to > effective_from,
                PV.id != exclude_id,
            )
        )
    count = db.execute(query).scalar() or 0
    if count > 0:
        raise ConflictError(
            code="PROFILE_VIGENCIA_OVERLAP",
            message="Ya existe una versión de perfil activa con vigencia que se solapa para el mismo código.",
        )
