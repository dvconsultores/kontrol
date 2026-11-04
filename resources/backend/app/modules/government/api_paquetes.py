"""API del paquete de auditoría exportable de Gobierno (DOC-08, GOV-DOC-010).

Expone la vista previa y la generación de paquetes desde una muestra de CTL-04, además de la consulta, la descarga y la
verificación de integridad de paquetes generados. La huella no es una firma electrónica.
"""

from __future__ import annotations

import io

from fastapi import APIRouter, Depends, File, Header, Query, Response, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import (
    require_module,
    require_permission,
    require_write_allowed,
)
from app.modules.government import service_paquetes
from app.modules.government.schemas_paquetes import (
    PaqueteDetalle,
    PaqueteIn,
    PaquetesListado,
    ResultadoDeVerificacion,
    VistaPrevia,
)
from app.modules.identity_access.models import User

router = APIRouter(prefix="/gobierno", tags=["gobierno"])

CABECERAS_DESCARGA = {
    "Cache-Control": "private, no-store",
    "X-Content-Type-Options": "nosniff",
    "Content-Security-Policy": "default-src 'none'; sandbox",
}


@router.get(
    "/auditoria/muestras/{muestra_id}/paquete/vista-previa",
    response_model=VistaPrevia,
)
def vista_previa(
    muestra_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_paquetes", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_paquetes.vista_previa(db, ctx, muestra_id)


@router.post(
    "/auditoria/muestras/{muestra_id}/paquetes",
    response_model=PaqueteDetalle,
    status_code=201,
    dependencies=[Depends(require_write_allowed)],
)
def generar(
    muestra_id: str,
    datos: PaqueteIn,
    response: Response,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_paquetes", "generate")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    paquete, creado = service_paquetes.generar(
        db, ctx, muestra_id, datos.proposito, idempotency_key
    )
    db.commit()
    if not creado:
        response.status_code = 200
    return service_paquetes.detalle(db, ctx, str(paquete.id))


@router.get("/paquetes", response_model=PaquetesListado)
def listar(
    muestra_id: str | None = Query(None, min_length=1, max_length=36),
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(20, ge=10, le=100),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_paquetes", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_paquetes.listar(db, ctx, muestra_id, pagina, por_pagina)


@router.post(
    "/paquetes/verificar",
    response_model=ResultadoDeVerificacion,
    dependencies=[Depends(require_write_allowed)],
)
def verificar(
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_paquetes", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_paquetes.verificar(db, ctx, archivo.file)
    db.commit()
    return resultado


@router.get("/paquetes/{paquete_id}", response_model=PaqueteDetalle)
def detalle(
    paquete_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_paquetes", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_paquetes.detalle(db, ctx, paquete_id)


@router.get("/paquetes/{paquete_id}/descargar")
def descargar(
    paquete_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_paquetes", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    nombre, flujo, tamano = service_paquetes.descargar(db, ctx, paquete_id)
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


@router.get("/paquetes/{paquete_id}/manifiesto")
def manifiesto(
    paquete_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_paquetes", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    nombre, datos = service_paquetes.manifiesto(db, ctx, paquete_id)
    db.commit()
    return StreamingResponse(
        io.BytesIO(datos),
        media_type="application/json",
        headers={
            **CABECERAS_DESCARGA,
            "Content-Disposition": f'attachment; filename="{nombre}"',
        },
    )
