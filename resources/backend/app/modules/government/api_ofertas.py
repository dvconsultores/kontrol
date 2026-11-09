from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import require_module, require_permission, require_write_allowed
from app.modules.government import service_ofertas
from app.modules.government.api import _version
from app.modules.government.schemas_ofertas import (
    ConcluirRecepcionEntrada,
    ConcluirRecepcionOut,
    OfertaDetalle,
    OfertaEntrada,
    OfertasLista,
)
from app.modules.identity_access.models import User

router = APIRouter(prefix="/gobierno/contrataciones/expedientes", tags=["gobierno"])


@router.get(
    "/{expediente_id}/ofertas",
    response_model=OfertasLista,
)
def get_ofertas(
    expediente_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_ofertas", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_ofertas.listar_ofertas(db, ctx, expediente_id)


@router.get(
    "/{expediente_id}/ofertas/{oferta_id}",
    response_model=OfertaDetalle,
)
def get_oferta_detalle(
    expediente_id: str,
    oferta_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_ofertas", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_ofertas.detalle_oferta(db, ctx, expediente_id, oferta_id)


@router.post(
    "/{expediente_id}/ofertas",
    response_model=OfertaDetalle,
    status_code=201,
    dependencies=[Depends(require_write_allowed)],
)
def post_oferta(
    expediente_id: str,
    entrada: OfertaEntrada,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_ofertas", "receive")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_ofertas.recibir_oferta(db, ctx, expediente_id, entrada, _version(if_match))
    db.commit()
    return resultado


@router.post(
    "/{expediente_id}/ofertas/concluir",
    response_model=ConcluirRecepcionOut,
    dependencies=[Depends(require_write_allowed)],
)
def post_concluir(
    expediente_id: str,
    datos: ConcluirRecepcionEntrada,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_ofertas", "receive")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_ofertas.concluir_recepcion(db, ctx, expediente_id, _version(if_match), datos.motivo)
    db.commit()
    return resultado
