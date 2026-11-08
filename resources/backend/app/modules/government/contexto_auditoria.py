"""Proveedor de contexto institucional para auditoría de Gobierno."""

from typing import Any

from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext
from app.core.errors import NotFoundError
from app.modules.government.service_identidad import contexto_institucional
from app.modules.organization.models import Company
from app.shared.audit_catalog import catalog
from app.shared.clock import hoy_de_negocio


def contexto_de_evento(
    db: Session,
    *,
    action: str,
    entity_type: str,
    tenant_id: str | None,
    company_id: str | None,
    user_id: str | None,
) -> dict[str, Any] | None:
    spec = catalog().get((action, entity_type))
    if spec is None or spec.owner_module != "government":
        return None

    if tenant_id is None or company_id is None or user_id is None:
        return None

    empresa = db.get(Company, company_id)
    if empresa is None:
        return None

    ctx = CompanyContext(
        tenant_id=tenant_id, company_id=company_id, company=empresa, user_id=user_id
    )

    with db.no_autoflush:
        try:
            datos = contexto_institucional(db, ctx, str(user_id), None)
        except NotFoundError:
            return {
                "version": 1,
                "estado": "SIN_VINCULO",
                "fecha": hoy_de_negocio().isoformat(),
                "ente": None,
                "vinculo": None,
                "funcionario": None,
                "ocupaciones": [],
                "roles": [],
                "categorias": [],
                "tiene_autoridad": False,
                "motivo_sin_autoridad": "SIN_VINCULO",
            }

    return {
        "version": 1,
        "estado": "CON_IDENTIDAD" if datos["vinculo"] else "SIN_VINCULO",
        "fecha": datos["fecha"],
        "ente": datos["ente"],
        "vinculo": (
            {"id": datos["vinculo"]["id"], "codigo": datos["vinculo"]["codigo"]}
            if datos["vinculo"]
            else None
        ),
        "funcionario": (
            {
                "id": datos["funcionario"]["id"],
                "nombre": datos["funcionario"]["nombre"],
            }
            if datos["funcionario"]
            else None
        ),
        "ocupaciones": [
            {
                "cargo_id": ocupacion["cargo_id"],
                "cargo": ocupacion["cargo"],
                "cargo_codigo": ocupacion["cargo_codigo"],
                "unidad_id": ocupacion["unidad_id"],
                "unidad": ocupacion["unidad"],
                "figura": ocupacion["figura"],
                "figura_etiqueta": ocupacion["figura_etiqueta"],
                "ejerce": ocupacion["ejerce"],
                "autoridad": [
                    {"accion": item["accion"], "materia": item["materia"]}
                    for item in ocupacion["autoridad"]
                ],
            }
            for ocupacion in datos["ocupaciones"]
        ],
        "roles": datos["roles"],
        "categorias": datos["categorias"],
        "tiene_autoridad": datos["tiene_autoridad"],
        "motivo_sin_autoridad": datos["motivo_sin_autoridad"],
    }
