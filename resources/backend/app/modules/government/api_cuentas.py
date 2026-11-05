"""API de las cuentas bancarias públicas de Gobierno (TRE-01, GOV-TRE-001)."""
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
from app.modules.government import service_cuentas
from app.modules.government.api import _version
from app.modules.government.schemas_cuentas import (
    ActoCuentaIn,
    AutorizadoIn,
    BancoCambios,
    BancoIn,
    BancoOut,
    BancosListado,
    CierreCuentaIn,
    CuentaCambios,
    CuentaDetalle,
    CuentaIn,
    CuentasListado,
    CuentasOpciones,
    EstadoBanco,
    EstadoCuenta,
    FinAutorizacionIn,
    MonedaCuenta,
    MotivoCuentaIn,
    NumeroCuentaOut,
)
from app.modules.identity_access.models import User

router = APIRouter(prefix="/gobierno/tesoreria", tags=["gobierno"])


@router.get("/bancos", response_model=BancosListado)
def listar_bancos(
    estado: EstadoBanco | None = Query(None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_cuentas", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_cuentas.listar_bancos(db, ctx, estado)


@router.post(
    "/bancos",
    response_model=BancoOut,
    status_code=201,
    dependencies=[Depends(require_write_allowed)],
)
def crear_banco(
    datos: BancoIn,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_cuentas", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    banco = service_cuentas.crear_banco(db, ctx, datos)
    db.commit()
    return service_cuentas._banco_salida(banco)


@router.patch(
    "/bancos/{banco_id}",
    response_model=BancoOut,
    dependencies=[Depends(require_write_allowed)],
)
def editar_banco(
    banco_id: str,
    cambios: BancoCambios,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_cuentas", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    banco = service_cuentas.editar_banco(
        db, ctx, banco_id, _version(if_match), cambios
    )
    db.commit()
    return service_cuentas._banco_salida(banco)


@router.get("/cuentas", response_model=CuentasListado)
def listar_cuentas(
    estado: EstadoCuenta | None = Query(None),
    banco_id: str | None = Query(None, max_length=36),
    moneda: MonedaCuenta | None = Query(None),
    cargo_id: str | None = Query(None, max_length=36),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_cuentas", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_cuentas.listar(db, ctx, estado, banco_id, moneda, cargo_id)


@router.post(
    "/cuentas",
    response_model=CuentaDetalle,
    status_code=201,
    dependencies=[Depends(require_write_allowed)],
)
def crear_cuenta(
    datos: CuentaIn,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_cuentas", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    cuenta = service_cuentas.crear(db, ctx, datos)
    db.commit()
    return service_cuentas.detalle(db, ctx, str(cuenta.id))


@router.get("/cuentas/{cuenta_id}", response_model=CuentaDetalle)
def detalle_cuenta(
    cuenta_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_cuentas", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_cuentas.detalle(db, ctx, cuenta_id)


@router.patch(
    "/cuentas/{cuenta_id}",
    response_model=CuentaDetalle,
    dependencies=[Depends(require_write_allowed)],
)
def editar_cuenta(
    cuenta_id: str,
    cambios: CuentaCambios,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_cuentas", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    cuenta = service_cuentas.editar(db, ctx, cuenta_id, _version(if_match), cambios)
    db.commit()
    return service_cuentas.detalle(db, ctx, str(cuenta.id))


@router.get("/cuentas/{cuenta_id}/numero", response_model=NumeroCuentaOut)
def numero_cuenta(
    cuenta_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_cuentas", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_cuentas.numero_completo(db, ctx, cuenta_id)
    db.commit()
    return resultado


@router.post(
    "/cuentas/{cuenta_id}/acto",
    response_model=CuentaDetalle,
    dependencies=[Depends(require_write_allowed)],
)
def vincular_acto(
    cuenta_id: str,
    datos: ActoCuentaIn,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_cuentas", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    cuenta = service_cuentas.vincular_acto(
        db, ctx, cuenta_id, _version(if_match), datos
    )
    db.commit()
    return service_cuentas.detalle(db, ctx, str(cuenta.id))


@router.post(
    "/cuentas/{cuenta_id}/autorizados",
    response_model=CuentaDetalle,
    status_code=201,
    dependencies=[Depends(require_write_allowed)],
)
def autorizar(
    cuenta_id: str,
    datos: AutorizadoIn,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_cuentas", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    cuenta = service_cuentas.autorizar(db, ctx, cuenta_id, _version(if_match), datos)
    db.commit()
    return service_cuentas.detalle(db, ctx, str(cuenta.id))


@router.post(
    "/cuentas/{cuenta_id}/autorizados/{autorizacion_id}/fin",
    response_model=CuentaDetalle,
    dependencies=[Depends(require_write_allowed)],
)
def terminar_autorizacion(
    cuenta_id: str,
    autorizacion_id: str,
    datos: FinAutorizacionIn,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_cuentas", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    cuenta = service_cuentas.terminar_autorizacion(
        db, ctx, cuenta_id, autorizacion_id, _version(if_match), datos
    )
    db.commit()
    return service_cuentas.detalle(db, ctx, str(cuenta.id))


@router.post(
    "/cuentas/{cuenta_id}/activar",
    response_model=CuentaDetalle,
    dependencies=[Depends(require_write_allowed)],
)
def activar(
    cuenta_id: str,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_cuentas", "activate")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    cuenta = service_cuentas.activar(db, ctx, cuenta_id, _version(if_match))
    db.commit()
    return service_cuentas.detalle(db, ctx, str(cuenta.id))


@router.post(
    "/cuentas/{cuenta_id}/inactivar",
    response_model=CuentaDetalle,
    dependencies=[Depends(require_write_allowed)],
)
def inactivar(
    cuenta_id: str,
    datos: MotivoCuentaIn,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_cuentas", "activate")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    cuenta = service_cuentas.inactivar(db, ctx, cuenta_id, _version(if_match), datos)
    db.commit()
    return service_cuentas.detalle(db, ctx, str(cuenta.id))


@router.post(
    "/cuentas/{cuenta_id}/reactivar",
    response_model=CuentaDetalle,
    dependencies=[Depends(require_write_allowed)],
)
def reactivar(
    cuenta_id: str,
    datos: MotivoCuentaIn,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_cuentas", "activate")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    cuenta = service_cuentas.reactivar(db, ctx, cuenta_id, _version(if_match), datos)
    db.commit()
    return service_cuentas.detalle(db, ctx, str(cuenta.id))


@router.post(
    "/cuentas/{cuenta_id}/cerrar",
    response_model=CuentaDetalle,
    dependencies=[Depends(require_write_allowed)],
)
def cerrar(
    cuenta_id: str,
    datos: CierreCuentaIn,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_cuentas", "activate")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    cuenta = service_cuentas.cerrar(db, ctx, cuenta_id, _version(if_match), datos)
    db.commit()
    return service_cuentas.detalle(db, ctx, str(cuenta.id))


@router.get("/opciones", response_model=CuentasOpciones)
def opciones(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_cuentas", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_cuentas.opciones(db, ctx)
