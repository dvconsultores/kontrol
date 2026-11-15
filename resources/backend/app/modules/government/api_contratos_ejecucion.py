from __future__ import annotations

import io
from typing import Any

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import require_module, require_permission, require_write_allowed
from app.modules.government import service_contratos_ejecucion
from app.modules.government.schemas_contratos_ejecucion import (
    Anulacion,
    CierreCreate,
    EntregableCreate,
    EntregaCreate,
    FacturaCreate,
    HitoCreate,
    InicioCreate,
    RecepcionCreate,
    ResolucionValuacion,
    RevisionCreate,
    TerminacionCreate,
    ValuacionCreate,
)
from app.modules.identity_access.models import User

router = APIRouter(prefix="/gobierno/contratos/{contrato_id}/ejecucion", tags=["gobierno"])


@router.get("")
def get_ejecucion(
    contrato_id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_contratos", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> dict[str, Any]:
    return service_contratos_ejecucion.ejecucion(db, ctx, contrato_id)


@router.get("/opciones")
def get_opciones(
    contrato_id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_contratos", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> dict[str, Any]:
    return service_contratos_ejecucion.opciones(db, ctx, contrato_id)


@router.get("/reporte.csv")
def get_reporte_csv(
    contrato_id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_contratos", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> StreamingResponse:
    nombre, contenido = service_contratos_ejecucion.reporte_csv(db, ctx, contrato_id)
    return StreamingResponse(
        io.BytesIO(contenido),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@router.post("/inicio", status_code=status.HTTP_201_CREATED)
def post_inicio(
    contrato_id: str,
    cuerpo: InicioCreate,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_contratos", "execute")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
) -> dict[str, Any]:
    resultado = service_contratos_ejecucion.iniciar(db, ctx, contrato_id, cuerpo.model_dump())
    db.commit()
    return resultado


@router.post("/hitos", status_code=status.HTTP_201_CREATED)
def post_hito(
    contrato_id: str,
    cuerpo: HitoCreate,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_contratos", "execute")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
) -> dict[str, Any]:
    resultado = service_contratos_ejecucion.crear_hito(db, ctx, contrato_id, cuerpo.model_dump())
    db.commit()
    return resultado


@router.post("/hitos/{hito_id}/anular", status_code=status.HTTP_201_CREATED)
def post_anular_hito(
    contrato_id: str,
    hito_id: str,
    cuerpo: Anulacion,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_contratos", "execute")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
) -> dict[str, Any]:
    resultado = service_contratos_ejecucion.anular_hito(db, ctx, contrato_id, hito_id, cuerpo.model_dump())
    db.commit()
    return resultado


@router.post("/entregables", status_code=status.HTTP_201_CREATED)
def post_entregable(
    contrato_id: str,
    cuerpo: EntregableCreate,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_contratos", "execute")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
) -> dict[str, Any]:
    resultado = service_contratos_ejecucion.crear_entregable(db, ctx, contrato_id, cuerpo.model_dump())
    db.commit()
    return resultado


@router.post("/entregables/{entregable_id}/anular", status_code=status.HTTP_201_CREATED)
def post_anular_entregable(
    contrato_id: str,
    entregable_id: str,
    cuerpo: Anulacion,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_contratos", "execute")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
) -> dict[str, Any]:
    resultado = service_contratos_ejecucion.anular_entregable(db, ctx, contrato_id, entregable_id, cuerpo.model_dump())
    db.commit()
    return resultado


@router.post("/entregables/{entregable_id}/entregas", status_code=status.HTTP_201_CREATED)
def post_entrega(
    contrato_id: str,
    entregable_id: str,
    cuerpo: EntregaCreate,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_contratos", "execute")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
) -> dict[str, Any]:
    resultado = service_contratos_ejecucion.entregar(db, ctx, contrato_id, entregable_id, cuerpo.model_dump())
    db.commit()
    return resultado


@router.post("/entregas/{entrega_id}/revision", status_code=status.HTTP_201_CREATED)
def post_revision_entrega(
    contrato_id: str,
    entrega_id: str,
    cuerpo: RevisionCreate,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_contratos", "execute")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
) -> dict[str, Any]:
    resultado = service_contratos_ejecucion.revisar_entrega(db, ctx, contrato_id, entrega_id, cuerpo.model_dump())
    db.commit()
    return resultado


@router.post("/valuaciones", status_code=status.HTTP_201_CREATED)
def post_valuacion(
    contrato_id: str,
    cuerpo: ValuacionCreate,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_contratos", "execute")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
) -> dict[str, Any]:
    resultado = service_contratos_ejecucion.presentar_valuacion(db, ctx, contrato_id, cuerpo.model_dump())
    db.commit()
    return resultado


@router.post("/valuaciones/{valuacion_id}/resolucion", status_code=status.HTTP_201_CREATED)
def post_resolucion_valuacion(
    contrato_id: str,
    valuacion_id: str,
    cuerpo: ResolucionValuacion,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_contratos", "execute")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
) -> dict[str, Any]:
    resultado = service_contratos_ejecucion.resolver_valuacion(db, ctx, contrato_id, valuacion_id, cuerpo.model_dump())
    db.commit()
    return resultado


@router.post("/valuaciones/{valuacion_id}/anular", status_code=status.HTTP_201_CREATED)
def post_anular_valuacion(
    contrato_id: str,
    valuacion_id: str,
    cuerpo: Anulacion,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_contratos", "execute")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
) -> dict[str, Any]:
    resultado = service_contratos_ejecucion.anular_valuacion(db, ctx, contrato_id, valuacion_id, cuerpo.model_dump())
    db.commit()
    return resultado


@router.post("/terminacion", status_code=status.HTTP_201_CREATED)
def post_terminacion(
    contrato_id: str,
    cuerpo: TerminacionCreate,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_contratos", "execute")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
) -> dict[str, Any]:
    resultado = service_contratos_ejecucion.terminar_obra(db, ctx, contrato_id, cuerpo.model_dump())
    db.commit()
    return resultado


@router.post("/recepciones", status_code=status.HTTP_201_CREATED)
def post_recepcion(
    contrato_id: str,
    cuerpo: RecepcionCreate,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_contratos", "execute")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
) -> dict[str, Any]:
    resultado = service_contratos_ejecucion.registrar_recepcion(db, ctx, contrato_id, cuerpo.model_dump())
    db.commit()
    return resultado


@router.post("/recepciones/{recepcion_id}/anular", status_code=status.HTTP_201_CREATED)
def post_anular_recepcion(
    contrato_id: str,
    recepcion_id: str,
    cuerpo: Anulacion,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_contratos", "execute")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
) -> dict[str, Any]:
    resultado = service_contratos_ejecucion.anular_recepcion(db, ctx, contrato_id, recepcion_id, cuerpo.model_dump())
    db.commit()
    return resultado


@router.post("/facturas", status_code=status.HTTP_201_CREATED)
def post_factura(
    contrato_id: str,
    cuerpo: FacturaCreate,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_contratos", "execute")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
) -> dict[str, Any]:
    resultado = service_contratos_ejecucion.vincular_factura(db, ctx, contrato_id, cuerpo.model_dump())
    db.commit()
    return resultado


@router.post("/facturas/{factura_id}/anular", status_code=status.HTTP_201_CREATED)
def post_anular_factura(
    contrato_id: str,
    factura_id: str,
    cuerpo: Anulacion,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_contratos", "execute")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
) -> dict[str, Any]:
    resultado = service_contratos_ejecucion.anular_factura(db, ctx, contrato_id, factura_id, cuerpo.model_dump())
    db.commit()
    return resultado


@router.post("/cierre", status_code=status.HTTP_201_CREATED)
def post_cierre(
    contrato_id: str,
    cuerpo: CierreCreate,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_contratos", "execute")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
) -> dict[str, Any]:
    resultado = service_contratos_ejecucion.cerrar(db, ctx, contrato_id, cuerpo.model_dump())
    db.commit()
    return resultado
