from fastapi import APIRouter, Depends, Header, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import require_module, require_permission, require_write_allowed
from app.modules.government.api import _version
from app.modules.government.schemas_decision import DecisionCreate, RecomendacionCreate
from app.modules.government.service_decision import (
    abrir_informe,
    emitir_recomendacion,
    obtener_estado_decision,
)
from app.modules.government.service_decision_resolver import registrar_decision
from app.modules.identity_access.models import User

router = APIRouter(prefix="/gobierno/contrataciones/expedientes", tags=["gobierno"])


@router.get("/{expediente_id}/decision")
def get_decision(
    expediente_id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_decision", "view")),
    _modulo: None = Depends(require_module("gobierno")),
):
    return obtener_estado_decision(db, ctx, user, expediente_id)


@router.post("/{expediente_id}/decision/recomendaciones", status_code=status.HTTP_201_CREATED)
def post_recomendacion(
    expediente_id: str,
    cuerpo: RecomendacionCreate,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_decision", "recommend")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
):
    version = _version(if_match)
    resultado = emitir_recomendacion(db, ctx, user, expediente_id, version, cuerpo.model_dump())
    db.commit()
    return resultado


@router.get("/{expediente_id}/decision/recomendaciones/{recomendacion_id}/informe")
def get_informe_recomendacion(
    expediente_id: str,
    recomendacion_id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_decision", "view")),
    _modulo: None = Depends(require_module("gobierno")),
):
    file_name, stream, file_size = abrir_informe(db, ctx, user, expediente_id, recomendacion_id)
    db.commit()
    disposition = f'attachment; filename="{file_name}"'
    return StreamingResponse(
        stream,
        media_type="application/pdf",
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": disposition,
            "Content-Length": str(file_size),
        },
    )


@router.post("/{expediente_id}/decision/decisiones", status_code=status.HTTP_201_CREATED)
def crear_decision(
    expediente_id: str,
    cuerpo: DecisionCreate,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_decision", "decide")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
):
    version = _version(if_match)
    estado = registrar_decision(db, ctx, user, expediente_id, version, cuerpo.model_dump())
    db.commit()
    return estado
