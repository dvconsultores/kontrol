from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import require_module, require_permission, require_write_allowed
from app.modules.government.api import _version
from app.modules.government.schemas_evaluacion import AperturaCreate, AporteCreate, CriterioCreate, MatrizCreate, ResultadoCreate
from app.modules.government.service_evaluacion import (
    abrir_ofertas,
    anadir_criterio,
    bloquear_matriz,
    crear_matriz,
    obtener_evaluacion,
    quitar_criterio,
)
from app.modules.government.service_evaluacion_resultados import (
    concluir_evaluacion,
    registrar_aporte,
    registrar_resultado,
)
from app.modules.identity_access.models import User

router = APIRouter(prefix="/gobierno/contrataciones/expedientes", tags=["gobierno"])


@router.get("/{expediente_id}/evaluacion")
def get_evaluacion(
    expediente_id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_evaluacion", "view")),
    _modulo: None = Depends(require_module("gobierno")),
):
    return obtener_evaluacion(db, ctx, _user, expediente_id)


@router.post("/{expediente_id}/evaluacion/matriz", status_code=status.HTTP_201_CREATED)
def post_matriz(
    expediente_id: str,
    cuerpo: MatrizCreate,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_evaluacion", "criteria")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
):
    version = _version(if_match)
    resultado = crear_matriz(db, ctx, _user, expediente_id, version, cuerpo.model_dump())
    db.commit()
    return resultado


@router.post("/{expediente_id}/evaluacion/matriz/criterios", status_code=status.HTTP_201_CREATED)
def post_criterio(
    expediente_id: str,
    cuerpo: CriterioCreate,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_evaluacion", "criteria")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
):
    version = _version(if_match)
    resultado = anadir_criterio(db, ctx, _user, expediente_id, version, cuerpo.model_dump())
    db.commit()
    return resultado


@router.delete("/{expediente_id}/evaluacion/matriz/criterios/{criterio_id}")
def delete_criterio(
    expediente_id: str,
    criterio_id: str,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_evaluacion", "criteria")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
):
    version = _version(if_match)
    resultado = quitar_criterio(db, ctx, _user, expediente_id, version, criterio_id)
    db.commit()
    return resultado


@router.post("/{expediente_id}/evaluacion/matriz/bloquear")
def post_bloquear(
    expediente_id: str,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_evaluacion", "criteria")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
):
    version = _version(if_match)
    resultado = bloquear_matriz(db, ctx, _user, expediente_id, version)
    db.commit()
    return resultado


@router.post("/{expediente_id}/evaluacion/aperturas", status_code=status.HTTP_201_CREATED)
def post_apertura(
    expediente_id: str,
    cuerpo: AperturaCreate,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_evaluacion", "open")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
):
    version = _version(if_match)
    resultado = abrir_ofertas(db, ctx, _user, expediente_id, version, cuerpo.model_dump())
    db.commit()
    return resultado


@router.post("/{expediente_id}/evaluacion/aportes", status_code=status.HTTP_201_CREATED)
def post_aporte(
    expediente_id: str,
    cuerpo: AporteCreate,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_evaluacion", "evaluate")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
):
    resultado = registrar_aporte(db, ctx, _user, expediente_id, cuerpo.model_dump())
    db.commit()
    return resultado


@router.post("/{expediente_id}/evaluacion/resultados", status_code=status.HTTP_201_CREATED)
def post_resultado(
    expediente_id: str,
    cuerpo: ResultadoCreate,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_evaluacion", "evaluate")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
):
    resultado = registrar_resultado(db, ctx, _user, expediente_id, cuerpo.model_dump())
    db.commit()
    return resultado


@router.post("/{expediente_id}/evaluacion/concluir", status_code=status.HTTP_200_OK)
def post_concluir(
    expediente_id: str,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_evaluacion", "evaluate")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
):
    version = _version(if_match)
    resultado = concluir_evaluacion(db, ctx, _user, expediente_id, version)
    db.commit()
    return resultado
