"""API del expediente contractual (CNT-08, GOV-CNT-009)."""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

from fastapi import APIRouter, Depends, File, Header, Query, Response, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import require_module, require_permission, require_write_allowed
from app.modules.government import service_expediente_contractual, service_expediente_paquetes
from app.modules.government.api_paquetes import CABECERAS_DESCARGA
from app.modules.government.schemas_paquetes import PaqueteIn
from app.modules.identity_access.models import User

router = APIRouter(tags=["gobierno"])


@router.get("/gobierno/expedientes-contractuales")
def listar_expedientes(
    codigo: str | None = Query(None, max_length=40),
    expediente: str | None = Query(None, max_length=40),
    contratista: str | None = Query(None, max_length=100),
    tipo: str | None = Query(None),
    vigencia: Literal["POR_INICIAR", "EN_PLAZO", "VENCIDO"] | None = Query(None),
    supervisor: str | None = Query(None, max_length=100),
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_contratos", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> dict[str, Any]:
    return service_expediente_contractual.listar(
        db,
        ctx,
        codigo=codigo,
        expediente_numero=expediente,
        contratista=contratista,
        tipo=tipo,
        vigencia_filtro=vigencia,
        supervisor=supervisor,
        desde=desde,
        hasta=hasta,
        limit=limit,
        offset=offset,
    )


@router.get("/gobierno/contratos/{contrato_id}/expediente")
def get_expediente(
    contrato_id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_contratos", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> dict[str, Any]:
    return service_expediente_contractual.expediente(db, ctx, contrato_id)


@router.get("/gobierno/contratos/{contrato_id}/expediente/cronologia")
def get_cronologia(
    contrato_id: str,
    proceso: str | None = Query(None, max_length=10),
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_contratos", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> dict[str, Any]:
    return service_expediente_contractual.cronologia(
        db, ctx, contrato_id, proceso=proceso, desde=desde, hasta=hasta, limit=limit, offset=offset
    )


@router.get("/gobierno/contratos/{contrato_id}/expediente/auditoria")
def get_auditoria(
    contrato_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_contratos", "view")),
    _auditoria: User = Depends(require_permission("gobierno_auditoria", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> dict[str, Any]:
    return service_expediente_contractual.auditoria(db, ctx, contrato_id, limit=limit, offset=offset)


@router.get("/gobierno/contratos/{contrato_id}/expediente/integridad")
def get_integridad(
    contrato_id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_contratos", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> dict[str, Any]:
    return service_expediente_contractual.integridad(db, ctx, contrato_id)


@router.post(
    "/gobierno/contratos/{contrato_id}/expediente/paquetes",
    status_code=201,
    dependencies=[Depends(require_write_allowed)],
)
def crear_paquete(
    contrato_id: str,
    cuerpo: PaqueteIn,
    response: Response,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_paquetes", "generate")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
) -> dict[str, Any]:
    paquete, creado = service_expediente_paquetes.generar(db, ctx, contrato_id, cuerpo.proposito, idempotency_key)
    db.commit()
    if not creado:
        response.status_code = 200
    return service_expediente_paquetes.detalle(db, ctx, paquete)


@router.get("/gobierno/contratos/{contrato_id}/expediente/paquetes")
def listar_paquetes(
    contrato_id: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_paquetes", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> dict[str, Any]:
    return service_expediente_paquetes.listar(db, ctx, contrato_id, limit=limit, offset=offset)


@router.get("/gobierno/expedientes-contractuales/paquetes/{paquete_id}/descargar")
def descargar_paquete(
    paquete_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_paquetes", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    nombre, flujo, tamano = service_expediente_paquetes.descargar(db, ctx, paquete_id)
    db.commit()
    return StreamingResponse(
        flujo,
        media_type="application/zip",
        headers={
            **CABECERAS_DESCARGA,
            "Content-Disposition": f'attachment; filename="{nombre}"',
            "Content-Length": str(tamano),
        },
    )


@router.post(
    "/gobierno/expedientes-contractuales/paquetes/verificar",
    dependencies=[Depends(require_write_allowed)],
)
def verificar_paquete(
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_paquetes", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_expediente_paquetes.verificar(db, ctx, archivo.file)
    db.commit()
    return resultado
