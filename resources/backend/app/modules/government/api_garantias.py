"""API de garantías y cauciones (PROC-10)."""

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import require_module, require_permission, require_write_allowed
from app.modules.government.api import _version
from app.modules.government.schemas_garantias import (
    EjecucionCreate,
    EmisorCreate,
    GarantiaCreate,
    LiberacionCreate,
    RenovacionCreate,
    RequisitoCreate,
    SustitucionCreate,
)
from app.modules.government.service_garantias import (
    ejecutar_garantia,
    liberar_garantia,
    listar_emisores,
    obtener_estado_garantias,
    registrar_emisor,
    registrar_garantia,
    registrar_requisito,
    renovar_garantia,
    sustituir_garantia,
)
from app.modules.identity_access.models import User

router = APIRouter(prefix="/gobierno/contrataciones", tags=["gobierno"])


@router.get("/garantias/emisores")
def get_emisores(
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_garantias", "view")),
    _modulo: None = Depends(require_module("gobierno")),
):
    return listar_emisores(db, ctx)


@router.post("/garantias/emisores", status_code=status.HTTP_201_CREATED)
def post_emisor(
    cuerpo: EmisorCreate,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_garantias", "manage")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
):
    resultado = registrar_emisor(db, ctx, user, cuerpo.model_dump())
    db.commit()
    return resultado


@router.get("/expedientes/{expediente_id}/garantias")
def get_garantias(
    expediente_id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_garantias", "view")),
    _modulo: None = Depends(require_module("gobierno")),
):
    return obtener_estado_garantias(db, ctx, user, expediente_id)


@router.post("/expedientes/{expediente_id}/garantias/requisitos", status_code=status.HTTP_201_CREATED)
def post_requisito(
    expediente_id: str,
    cuerpo: RequisitoCreate,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_garantias", "manage")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
):
    version = _version(if_match)
    resultado = registrar_requisito(db, ctx, user, expediente_id, version, cuerpo.model_dump())
    db.commit()
    return resultado


@router.post("/expedientes/{expediente_id}/garantias", status_code=status.HTTP_201_CREATED)
def post_garantia(
    expediente_id: str,
    cuerpo: GarantiaCreate,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_garantias", "manage")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
):
    version = _version(if_match)
    resultado = registrar_garantia(db, ctx, user, expediente_id, version, cuerpo.model_dump())
    db.commit()
    return resultado


@router.post("/expedientes/{expediente_id}/garantias/{garantia_id}/renovar", status_code=status.HTTP_201_CREATED)
def post_renovar(
    expediente_id: str,
    garantia_id: str,
    cuerpo: RenovacionCreate,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_garantias", "manage")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
):
    version = _version(if_match)
    resultado = renovar_garantia(db, ctx, user, expediente_id, garantia_id, version, cuerpo.model_dump())
    db.commit()
    return resultado


@router.post("/expedientes/{expediente_id}/garantias/{garantia_id}/sustituir", status_code=status.HTTP_201_CREATED)
def post_sustituir(
    expediente_id: str,
    garantia_id: str,
    cuerpo: SustitucionCreate,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_garantias", "manage")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
):
    version = _version(if_match)
    resultado = sustituir_garantia(db, ctx, user, expediente_id, garantia_id, version, cuerpo.model_dump())
    db.commit()
    return resultado


@router.post("/expedientes/{expediente_id}/garantias/{garantia_id}/liberar", status_code=status.HTTP_201_CREATED)
def post_liberar(
    expediente_id: str,
    garantia_id: str,
    cuerpo: LiberacionCreate,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_garantias", "release")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
):
    version = _version(if_match)
    resultado = liberar_garantia(db, ctx, user, expediente_id, garantia_id, version, cuerpo.model_dump())
    db.commit()
    return resultado


@router.post("/expedientes/{expediente_id}/garantias/{garantia_id}/ejecutar", status_code=status.HTTP_201_CREATED)
def post_ejecutar(
    expediente_id: str,
    garantia_id: str,
    cuerpo: EjecucionCreate,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_garantias", "execute")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
):
    version = _version(if_match)
    resultado = ejecutar_garantia(db, ctx, user, expediente_id, garantia_id, version, cuerpo.model_dump())
    db.commit()
    return resultado
