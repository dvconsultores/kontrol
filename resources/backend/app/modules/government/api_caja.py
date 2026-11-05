"""API de la programación financiera de caja de Gobierno (TRE-02, GOV-TRE-002)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import (
    require_module,
    require_permission,
    require_write_allowed,
)
from app.modules.government import service_caja
from app.modules.government.api import _version
from app.modules.government.schemas_caja import (
    DeclaracionIn,
    EstadoPrograma,
    EstadoRubro,
    LineaCambios,
    LineaIn,
    MonedaPrograma,
    MotivoProgramaIn,
    OpcionesPrograma,
    ProgramaDetalle,
    ProgramaIn,
    ProgramasListado,
    RubroCambios,
    RubroIn,
    RubroOut,
    RubrosListado,
    TipoRubro,
)
from app.modules.identity_access.models import User

router = APIRouter(prefix="/gobierno/tesoreria", tags=["gobierno"])


@router.get("/rubros", response_model=RubrosListado)
def listar_rubros(
    estado: EstadoRubro | None = Query(None),
    tipo: TipoRubro | None = Query(None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_caja", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    rubros = service_caja.listar_rubros(db, ctx, estado, tipo)
    return RubrosListado(items=[RubroOut(**service_caja.rubro_salida(r)) for r in rubros])


@router.post(
    "/rubros",
    response_model=RubroOut,
    status_code=201,
    dependencies=[Depends(require_write_allowed)],
)
def crear_rubro(
    datos: RubroIn,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_caja", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    rubro = service_caja.crear_rubro(db, ctx, datos)
    db.commit()
    return service_caja.rubro_salida(rubro)


@router.patch(
    "/rubros/{rubro_id}",
    response_model=RubroOut,
    dependencies=[Depends(require_write_allowed)],
)
def editar_rubro(
    rubro_id: str,
    cambios: RubroCambios,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_caja", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    rubro = service_caja.editar_rubro(
        db, ctx, rubro_id, _version(if_match), cambios
    )
    db.commit()
    return service_caja.rubro_salida(rubro)


@router.get("/programas", response_model=ProgramasListado)
def listar_programas(
    ejercicio: int | None = Query(None, ge=1900, le=9999),
    moneda: MonedaPrograma | None = Query(None),
    estado: EstadoPrograma | None = Query(None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_caja", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_caja.listar(db, ctx, ejercicio, moneda, estado)


@router.post(
    "/programas",
    response_model=ProgramaDetalle,
    status_code=201,
    dependencies=[Depends(require_write_allowed)],
)
def crear_programa(
    datos: ProgramaIn,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_caja", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    programa = service_caja.crear(db, ctx, datos)
    db.commit()
    return service_caja.detalle_tras_escribir(db, ctx, str(programa.id))


@router.get("/programas/{programa_id}", response_model=ProgramaDetalle)
def ver_programa(
    programa_id: str,
    version: int | None = Query(None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_caja", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_caja.detalle(db, ctx, programa_id, version)


@router.get("/programas/{programa_id}/opciones", response_model=OpcionesPrograma)
def ver_opciones(
    programa_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_caja", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_caja.opciones(db, ctx, programa_id)


@router.post(
    "/programas/{programa_id}/declaraciones",
    response_model=ProgramaDetalle,
    status_code=201,
    dependencies=[Depends(require_write_allowed)],
)
def declarar_disponibilidad(
    programa_id: str,
    datos: DeclaracionIn,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_caja", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    service_caja.declarar(db, ctx, programa_id, _version(if_match), datos)
    db.commit()
    return service_caja.detalle_tras_escribir(db, ctx, programa_id)


@router.delete(
    "/programas/{programa_id}/declaraciones/{declaracion_id}",
    response_model=ProgramaDetalle,
    dependencies=[Depends(require_write_allowed)],
)
def quitar_declaracion(
    programa_id: str,
    declaracion_id: str,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_caja", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    service_caja.quitar_declaracion(
        db, ctx, programa_id, declaracion_id, _version(if_match)
    )
    db.commit()
    return service_caja.detalle_tras_escribir(db, ctx, programa_id)


@router.post(
    "/programas/{programa_id}/lineas",
    response_model=ProgramaDetalle,
    status_code=201,
    dependencies=[Depends(require_write_allowed)],
)
def agregar_linea(
    programa_id: str,
    datos: LineaIn,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_caja", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    service_caja.agregar_linea(db, ctx, programa_id, _version(if_match), datos)
    db.commit()
    return service_caja.detalle_tras_escribir(db, ctx, programa_id)


@router.patch(
    "/programas/{programa_id}/lineas/{linea_id}",
    response_model=ProgramaDetalle,
    dependencies=[Depends(require_write_allowed)],
)
def cambiar_linea(
    programa_id: str,
    linea_id: str,
    datos: LineaCambios,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_caja", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    service_caja.cambiar_linea(
        db, ctx, programa_id, linea_id, _version(if_match), datos
    )
    db.commit()
    return service_caja.detalle_tras_escribir(db, ctx, programa_id)


@router.delete(
    "/programas/{programa_id}/lineas/{linea_id}",
    response_model=ProgramaDetalle,
    dependencies=[Depends(require_write_allowed)],
)
def quitar_linea(
    programa_id: str,
    linea_id: str,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_caja", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    service_caja.quitar_linea(
        db, ctx, programa_id, linea_id, _version(if_match)
    )
    db.commit()
    return service_caja.detalle_tras_escribir(db, ctx, programa_id)


@router.post(
    "/programas/{programa_id}/activar",
    response_model=ProgramaDetalle,
    dependencies=[Depends(require_write_allowed)],
)
def activar_programa(
    programa_id: str,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_caja", "activate")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    service_caja.activar(db, ctx, programa_id, _version(if_match))
    db.commit()
    return service_caja.detalle_tras_escribir(db, ctx, programa_id)


@router.post(
    "/programas/{programa_id}/reprogramar",
    response_model=ProgramaDetalle,
    status_code=201,
    dependencies=[Depends(require_write_allowed)],
)
def reprogramar_programa(
    programa_id: str,
    datos: MotivoProgramaIn,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_caja", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    service_caja.reprogramar(
        db, ctx, programa_id, _version(if_match), datos
    )
    db.commit()
    return service_caja.detalle_tras_escribir(db, ctx, programa_id)


@router.post(
    "/programas/{programa_id}/descartar",
    response_model=ProgramaDetalle,
    dependencies=[Depends(require_write_allowed)],
)
def descartar_programa(
    programa_id: str,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_caja", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    service_caja.descartar(db, ctx, programa_id, _version(if_match))
    db.commit()
    return service_caja.detalle_tras_escribir(db, ctx, programa_id)


@router.post(
    "/programas/{programa_id}/cerrar",
    response_model=ProgramaDetalle,
    dependencies=[Depends(require_write_allowed)],
)
def cerrar_programa(
    programa_id: str,
    datos: MotivoProgramaIn,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_caja", "activate")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    service_caja.cerrar(db, ctx, programa_id, _version(if_match), datos)
    db.commit()
    return service_caja.detalle_tras_escribir(db, ctx, programa_id)
