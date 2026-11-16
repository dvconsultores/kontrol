"""API de la terminación del contrato (CNT-07)."""

from __future__ import annotations

import io
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Header, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import require_module, require_permission, require_write_allowed
from app.modules.government import service_contratos_terminacion
from app.modules.government.api import _version
from app.modules.government.schemas_contratos_terminacion import (
    TerminacionCreate,
    TerminacionUpdate,
)
from app.modules.identity_access.models import User

router = APIRouter(prefix="/gobierno/contratos", tags=["gobierno"])


def _dump(cuerpo: dict[str, Any]) -> dict[str, Any]:
    if isinstance(cuerpo.get("conclusion_hasta"), date):
        cuerpo = {**cuerpo, "conclusion_hasta": cuerpo["conclusion_hasta"].isoformat()}
    return cuerpo


@router.get("/terminaciones/reporte.csv")
def get_reporte_csv(
    figura: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_contratos", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> StreamingResponse:
    nombre, contenido = service_contratos_terminacion.reporte_csv(
        db, ctx, figura, desde, hasta
    )
    return StreamingResponse(
        io.BytesIO(contenido),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@router.get("/{contrato_id}/terminacion")
def get_terminacion(
    contrato_id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_contratos", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> dict[str, Any]:
    return service_contratos_terminacion.vista(db, ctx, contrato_id)


@router.post("/{contrato_id}/terminacion", status_code=status.HTTP_201_CREATED)
def post_terminacion(
    contrato_id: str,
    cuerpo: TerminacionCreate,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_contratos", "terminate")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
) -> dict[str, Any]:
    resultado = service_contratos_terminacion.crear_borrador(
        db, ctx, contrato_id, _dump(cuerpo.model_dump(exclude_unset=True))
    )
    db.commit()
    return resultado


@router.patch("/{contrato_id}/terminacion/borrador")
def patch_terminacion_borrador(
    contrato_id: str,
    cuerpo: TerminacionUpdate,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_contratos", "terminate")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> dict[str, Any]:
    version = _version(if_match)
    resultado = service_contratos_terminacion.actualizar_borrador(
        db, ctx, contrato_id, version, _dump(cuerpo.model_dump(exclude_unset=True))
    )
    db.commit()
    return resultado


@router.delete(
    "/{contrato_id}/terminacion/borrador",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_terminacion_borrador(
    contrato_id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_contratos", "terminate")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> Response:
    version = _version(if_match)
    service_contratos_terminacion.descartar_borrador(db, ctx, contrato_id, version)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{contrato_id}/terminacion/formalizar")
def post_terminacion_formalizar(
    contrato_id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_contratos", "terminate")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> dict[str, Any]:
    version = _version(if_match)
    resultado = service_contratos_terminacion.formalizar(
        db, ctx, user, contrato_id, version
    )
    db.commit()
    return resultado
