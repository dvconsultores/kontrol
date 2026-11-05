"""Servicio de las cuentas bancarias públicas de Gobierno (TRE-01, GOV-TRE-001)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext
from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.government.models import (
    GovernmentAct,
    GovernmentBank,
    GovernmentBankAccount,
    GovernmentBankAccountAuthorization,
    GovernmentBankAccountHistory,
    GovernmentPosition,
    GovernmentStructure,
    GovernmentUnit,
)
from app.modules.government.service_auditoria import _instante, _usuarios_por_ids
from app.modules.government.service_sod import evaluar_antes_de_actuar
from app.shared.audit import record_audit
from app.shared.clock import hoy_de_negocio

ENTIDAD_BANCO = "GovernmentBank"
ENTIDAD_CUENTA = "GovernmentBankAccount"
ESTADOS_ACTO_CON_EFECTO = ("EMITIDO", "EFICAZ")
ESTADOS_ACTO_SIN_EFECTO = ("REVOCADO", "NULO")
MOTIVO_CIERRE_AUTORIZACION = "Cierre de la cuenta"


def _instante_o_nulo(valor: datetime | None) -> datetime | None:
    return _instante(valor) if valor is not None else None


def _invalida(mensaje: str) -> KontrolError:
    return KontrolError(
        code="GOV_BANK_ACCOUNT_INVALID", message=mensaje, status_code=422
    )


def _enmascarar(numero: str) -> str:
    return "••••" + numero[-4:]


def _validar_codigo_banco(codigo: str) -> None:
    if not (len(codigo) == 4 and codigo.isascii() and codigo.isdigit()):
        raise _invalida("El código del banco debe tener 4 dígitos")


def _validar_numero(numero: str, banco: GovernmentBank) -> None:
    if not (len(numero) == 20 and numero.isascii() and numero.isdigit()):
        raise _invalida("El número de cuenta debe tener 20 dígitos")
    if not numero.startswith(banco.codigo):
        raise _invalida("El número de cuenta debe empezar por el código del banco")


def _banco_de_empresa(
    db: Session, ctx: CompanyContext, banco_id: Any, bloquear: bool = False
) -> GovernmentBank:
    consulta = select(GovernmentBank).where(
        GovernmentBank.id == banco_id,
        GovernmentBank.tenant_id == ctx.tenant_id,
        GovernmentBank.company_id == ctx.company_id,
    )
    if bloquear:
        consulta = consulta.with_for_update()
    banco = db.scalars(consulta).first()
    if banco is None:
        raise NotFoundError("GOV_BANK_NOT_FOUND", "El banco no existe en este ente")
    return banco


def _para_escribir_banco(
    db: Session, ctx: CompanyContext, banco_id: Any, version: Any
) -> GovernmentBank:
    if version is None:
        raise KontrolError(
            code="GOV_BANK_ACCOUNT_IF_MATCH_REQUIRED",
            message="Falta la cabecera If-Match con la versión",
            status_code=428,
        )
    banco = _banco_de_empresa(db, ctx, banco_id, bloquear=True)
    if banco.version != version:
        raise ConflictError(
            "GOV_BANK_ACCOUNT_STALE",
            "El dato cambió desde que lo abrió; recárguelo",
            details={"version_actual": banco.version},
        )
    return banco


def _cuenta_de_empresa(
    db: Session, ctx: CompanyContext, cuenta_id: Any, bloquear: bool = False
) -> GovernmentBankAccount:
    consulta = select(GovernmentBankAccount).where(
        GovernmentBankAccount.id == cuenta_id,
        GovernmentBankAccount.tenant_id == ctx.tenant_id,
        GovernmentBankAccount.company_id == ctx.company_id,
    )
    if bloquear:
        consulta = consulta.with_for_update()
    cuenta = db.scalars(consulta).first()
    if cuenta is None:
        raise NotFoundError("GOV_BANK_ACCOUNT_NOT_FOUND", "La cuenta no existe en este ente")
    return cuenta


def _para_escribir(
    db: Session, ctx: CompanyContext, cuenta_id: Any, version: Any
) -> GovernmentBankAccount:
    if version is None:
        raise KontrolError(
            code="GOV_BANK_ACCOUNT_IF_MATCH_REQUIRED",
            message="Falta la cabecera If-Match con la versión",
            status_code=428,
        )
    cuenta = _cuenta_de_empresa(db, ctx, cuenta_id, bloquear=True)
    if cuenta.version != version:
        raise ConflictError(
            "GOV_BANK_ACCOUNT_STALE",
            "El dato cambió desde que lo abrió; recárguelo",
            details={"version_actual": cuenta.version},
        )
    return cuenta


def _exigir_estado(cuenta: GovernmentBankAccount, *estados: str) -> None:
    if cuenta.estado not in estados:
        raise ConflictError(
            "GOV_BANK_ACCOUNT_INVALID_STATE",
            "La cuenta no admite esta acción en su estado actual",
        )


def _banco_utilizable(db: Session, ctx: CompanyContext, banco_id: Any) -> GovernmentBank:
    banco = db.scalars(
        select(GovernmentBank)
        .where(
            GovernmentBank.id == banco_id,
            GovernmentBank.tenant_id == ctx.tenant_id,
            GovernmentBank.company_id == ctx.company_id,
            GovernmentBank.estado == "ACTIVO",
        )
        .limit(1)
    ).first()
    if banco is None:
        raise _invalida("El banco no existe en este ente o no está activo")
    return banco


def _acto_con_efecto(db: Session, ctx: CompanyContext, acto_id: Any) -> GovernmentAct:
    acto = db.scalars(
        select(GovernmentAct)
        .where(
            GovernmentAct.id == acto_id,
            GovernmentAct.company_id == ctx.company_id,
            GovernmentAct.status.in_(ESTADOS_ACTO_CON_EFECTO),
            GovernmentAct.fecha <= hoy_de_negocio(),
        )
        .limit(1)
    ).first()
    if acto is None:
        raise _invalida("El acto no existe en este ente o no tiene efecto")
    return acto


def _condiciones_cargo(ctx: CompanyContext, hoy: date) -> list[Any]:
    return [
        GovernmentPosition.company_id == ctx.company_id,
        GovernmentPosition.status == "VIGENTE",
        GovernmentPosition.valid_from <= hoy,
        (GovernmentPosition.valid_to.is_(None))
        | (GovernmentPosition.valid_to >= hoy),
        GovernmentStructure.company_id == ctx.company_id,
        GovernmentStructure.status == "VIGENTE",
        GovernmentStructure.exercise == hoy.year,
    ]


def _cargo_autorizable(
    db: Session, ctx: CompanyContext, cargo_id: Any
) -> GovernmentPosition:
    hoy = hoy_de_negocio()
    cargo = db.scalars(
        select(GovernmentPosition)
        .join(GovernmentStructure, GovernmentPosition.structure_id == GovernmentStructure.id)
        .where(GovernmentPosition.id == cargo_id, *_condiciones_cargo(ctx, hoy))
        .limit(1)
    ).first()
    if cargo is None:
        raise _invalida("El cargo no existe en este ente o no está vigente")
    return cargo


def _cargos_autorizables(ctx: CompanyContext) -> Any:
    hoy = hoy_de_negocio()
    return select(GovernmentPosition).join(
        GovernmentStructure, GovernmentPosition.structure_id == GovernmentStructure.id
    ).where(*_condiciones_cargo(ctx, hoy)).order_by(GovernmentPosition.code)


def _autorizaciones(
    db: Session, ctx: CompanyContext, cuenta_id: Any
) -> list[GovernmentBankAccountAuthorization]:
    filas = db.scalars(
        select(GovernmentBankAccountAuthorization).where(
            GovernmentBankAccountAuthorization.account_id == cuenta_id,
            GovernmentBankAccountAuthorization.company_id == ctx.company_id,
        )
    ).all()
    filas = sorted(
        filas,
        key=lambda a: (a.vigente_desde, a.created_at),
        reverse=True,
    )
    filas.sort(key=lambda a: a.vigente_hasta is not None)
    return filas


def _autorizados_en_vigor(
    db: Session, ctx: CompanyContext, cuenta_id: Any
) -> list[GovernmentBankAccountAuthorization]:
    return list(
        db.scalars(
            select(GovernmentBankAccountAuthorization).where(
                GovernmentBankAccountAuthorization.account_id == cuenta_id,
                GovernmentBankAccountAuthorization.company_id == ctx.company_id,
                GovernmentBankAccountAuthorization.vigente_hasta.is_(None),
            )
        ).all()
    )


def _en_vigor(cuenta: GovernmentBankAccount, hoy: date) -> bool:
    if cuenta.estado != "VIGENTE":
        return False
    if cuenta.vigente_desde > hoy:
        return False
    if cuenta.vigente_hasta is not None and cuenta.vigente_hasta < hoy:
        return False
    return True


def _acto_sin_efecto(acto: GovernmentAct | None) -> bool:
    return acto is not None and acto.status in ESTADOS_ACTO_SIN_EFECTO


def _referencia_acto(acto: GovernmentAct | None) -> dict[str, Any] | None:
    if acto is None:
        return None
    return {
        "id": acto.id,
        "tipo": acto.tipo,
        "numero": acto.numero,
        "fecha": acto.fecha.isoformat() if acto.fecha is not None else None,
        "estado": acto.status,
        "asunto": acto.asunto,
    }


def _historia(
    db: Session,
    ctx: CompanyContext,
    cuenta: GovernmentBankAccount,
    tipo: str,
    detalle: dict[str, Any] | None,
) -> GovernmentBankAccountHistory:
    historia = GovernmentBankAccountHistory(
        account_id=cuenta.id,
        company_id=ctx.company_id,
        tipo=tipo,
        detalle=detalle,
        created_by=ctx.user_id,
    )
    db.add(historia)
    return historia


def _auditar(
    db: Session,
    ctx: CompanyContext,
    cuenta: GovernmentBankAccount,
    accion: str,
    after: dict[str, Any],
) -> None:
    record_audit(
        db,
        action=accion,
        entity_type=ENTIDAD_CUENTA,
        entity_id=str(cuenta.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after=after,
    )


def _auditar_banco(
    db: Session,
    ctx: CompanyContext,
    banco: GovernmentBank,
    accion: str,
    after: dict[str, Any],
) -> None:
    record_audit(
        db,
        action=accion,
        entity_type=ENTIDAD_BANCO,
        entity_id=str(banco.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after=after,
    )


def _guardar(db: Session, duplicado: tuple[str, str]) -> None:
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ConflictError(*duplicado) from None


def _siguiente_codigo(db: Session, ctx: CompanyContext) -> str:
    hoy = hoy_de_negocio()
    prefijo = f"CB-{hoy.year}-"
    total = db.scalar(
        select(func.count(GovernmentBankAccount.id)).where(
            GovernmentBankAccount.tenant_id == ctx.tenant_id,
            GovernmentBankAccount.company_id == ctx.company_id,
            GovernmentBankAccount.codigo.like(f"{prefijo}%"),
        )
    ) or 0
    return f"{prefijo}{total + 1:04d}"


def _resumen(
    cuenta: GovernmentBankAccount,
    banco: GovernmentBank,
    acto: GovernmentAct | None,
    autorizados_en_vigor: int,
    hoy: date,
) -> dict[str, Any]:
    return {
        "id": cuenta.id,
        "codigo": cuenta.codigo,
        "denominacion": cuenta.denominacion,
        "banco_id": banco.id,
        "banco_codigo": banco.codigo,
        "banco_nombre": banco.nombre,
        "tipo": cuenta.tipo,
        "moneda": cuenta.moneda,
        "numero_enmascarado": _enmascarar(cuenta.numero),
        "vigente_desde": cuenta.vigente_desde.isoformat()
        if cuenta.vigente_desde is not None
        else None,
        "vigente_hasta": cuenta.vigente_hasta.isoformat()
        if cuenta.vigente_hasta is not None
        else None,
        "estado": cuenta.estado,
        "en_vigor": _en_vigor(cuenta, hoy),
        "acto_sin_efecto": _acto_sin_efecto(acto),
        "autorizados_en_vigor": autorizados_en_vigor,
        "version": cuenta.version,
    }


def _faltantes(db: Session, ctx: CompanyContext, cuenta: GovernmentBankAccount) -> list[str]:
    faltantes: list[str] = []
    if cuenta.acto_id is None:
        faltantes.append("acto")
    if not _autorizados_en_vigor(db, ctx, cuenta.id):
        faltantes.append("autorizado")
    hoy = hoy_de_negocio()
    if cuenta.vigente_desde > hoy or (
        cuenta.vigente_hasta is not None and cuenta.vigente_hasta < hoy
    ):
        faltantes.append("vigencia")
    return faltantes


def _exigir_lista(
    db: Session, ctx: CompanyContext, cuenta: GovernmentBankAccount
) -> None:
    if cuenta.acto_id is not None:
        acto = db.get(GovernmentAct, cuenta.acto_id)
        if _acto_sin_efecto(acto):
            raise ConflictError(
                "GOV_BANK_ACCOUNT_ACT_WITHOUT_EFFECT",
                "El acto habilitante fue revocado o anulado; vincule un acto vigente",
            )
    faltantes = _faltantes(db, ctx, cuenta)
    if faltantes:
        raise ConflictError(
            "GOV_BANK_ACCOUNT_NOT_READY",
            "Faltan requisitos para activar la cuenta",
            details={"faltan": faltantes},
        )


def detalle(db: Session, ctx: CompanyContext, cuenta_id: Any) -> dict[str, Any]:
    cuenta = _cuenta_de_empresa(db, ctx, cuenta_id)
    banco = _banco_de_empresa(db, ctx, cuenta.bank_id)
    acto = db.get(GovernmentAct, cuenta.acto_id) if cuenta.acto_id is not None else None

    autorizaciones = _autorizaciones(db, ctx, cuenta.id)
    historia = db.scalars(
        select(GovernmentBankAccountHistory)
        .where(
            GovernmentBankAccountHistory.account_id == cuenta.id,
            GovernmentBankAccountHistory.company_id == ctx.company_id,
        )
        .order_by(
            GovernmentBankAccountHistory.created_at,
            GovernmentBankAccountHistory.id,
        )
    ).all()

    acto_ids: set[Any] = set()
    for autorizacion in autorizaciones:
        if autorizacion.acto_alta_id is not None:
            acto_ids.add(autorizacion.acto_alta_id)
        if autorizacion.acto_fin_id is not None:
            acto_ids.add(autorizacion.acto_fin_id)
    actos = (
        {
            str(acto_fila.id): acto_fila
            for acto_fila in db.scalars(
                select(GovernmentAct).where(GovernmentAct.id.in_(acto_ids))
            ).all()
        }
        if acto_ids
        else {}
    )

    posicion_ids = {a.position_id for a in autorizaciones}
    posiciones_vigentes: set[Any] = set()
    if posicion_ids:
        posiciones_vigentes = {
            cargo.id
            for cargo in db.scalars(_cargos_autorizables(ctx).where(GovernmentPosition.id.in_(posicion_ids)))
        }

    usuario_ids: set[Any] = {cuenta.created_by, cuenta.activada_por, cuenta.cerrada_por}
    for autorizacion in autorizaciones:
        usuario_ids.update((autorizacion.created_by, autorizacion.terminada_por))
    usuario_ids.update(entrada.created_by for entrada in historia)
    usuarios = _usuarios_por_ids(db, usuario_ids, ctx.tenant_id)

    def _nombre(usuario_id: Any) -> str | None:
        return usuarios.get(str(usuario_id)) if usuario_id is not None else None

    autorizados_salida: list[dict[str, Any]] = []
    for autorizacion in autorizaciones:
        autorizados_salida.append(
            {
                "id": autorizacion.id,
                "cargo_id": autorizacion.position_id,
                "cargo_codigo": autorizacion.cargo_codigo,
                "cargo_denominacion": autorizacion.cargo_denominacion,
                "cargo_unidad": autorizacion.cargo_unidad,
                "cargo_vigente": autorizacion.position_id in posiciones_vigentes,
                "acto_alta": _referencia_acto(actos.get(autorizacion.acto_alta_id))
                if autorizacion.acto_alta_id is not None
                else None,
                "vigente_desde": autorizacion.vigente_desde.isoformat()
                if autorizacion.vigente_desde is not None
                else None,
                "vigente_hasta": autorizacion.vigente_hasta.isoformat()
                if autorizacion.vigente_hasta is not None
                else None,
                "acto_fin": _referencia_acto(actos.get(autorizacion.acto_fin_id))
                if autorizacion.acto_fin_id is not None
                else None,
                "motivo_fin": autorizacion.motivo_fin,
                "en_vigor": autorizacion.vigente_hasta is None,
                "registrada_por": _nombre(autorizacion.created_by),
                "registrada_en": _instante(autorizacion.created_at),
                "terminada_por": _nombre(autorizacion.terminada_por),
                "terminada_en": _instante_o_nulo(autorizacion.terminada_en),
            }
        )

    historia_salida: list[dict[str, Any]] = []
    for entrada in historia:
        historia_salida.append(
            {
                "tipo": entrada.tipo,
                "detalle": entrada.detalle,
                "registrado_por": _nombre(entrada.created_by),
                "registrado_en": _instante(entrada.created_at),
            }
        )

    resumen = _resumen(
        cuenta,
        banco,
        acto,
        len([a for a in autorizaciones if a.vigente_hasta is None]),
        hoy_de_negocio(),
    )
    return {
        **resumen,
        "acto": _referencia_acto(acto),
        "registrada_por": _nombre(cuenta.created_by),
        "registrada_en": _instante(cuenta.created_at),
        "activada_por": _nombre(cuenta.activada_por),
        "activada_en": _instante_o_nulo(cuenta.activada_en),
        "cerrada_por": _nombre(cuenta.cerrada_por),
        "cerrada_en": _instante_o_nulo(cuenta.cerrada_en),
        "fecha_cierre": cuenta.fecha_cierre.isoformat()
        if cuenta.fecha_cierre is not None
        else None,
        "motivo_cierre": cuenta.motivo_cierre,
        "autorizados": autorizados_salida,
        "historia": historia_salida,
    }


def listar(
    db: Session,
    ctx: CompanyContext,
    estado: str | None,
    banco_id: Any | None,
    moneda: str | None,
    cargo_id: Any | None,
) -> dict[str, Any]:
    consulta = select(GovernmentBankAccount).where(
        GovernmentBankAccount.tenant_id == ctx.tenant_id,
        GovernmentBankAccount.company_id == ctx.company_id,
    )
    if estado is not None:
        consulta = consulta.where(GovernmentBankAccount.estado == estado)
    if banco_id is not None:
        consulta = consulta.where(GovernmentBankAccount.bank_id == banco_id)
    if moneda is not None:
        consulta = consulta.where(GovernmentBankAccount.moneda == moneda)
    if cargo_id is not None:
        consulta = consulta.where(
            GovernmentBankAccount.id.in_(
                select(GovernmentBankAccountAuthorization.account_id).where(
                    GovernmentBankAccountAuthorization.position_id == cargo_id,
                    GovernmentBankAccountAuthorization.company_id == ctx.company_id,
                    GovernmentBankAccountAuthorization.vigente_hasta.is_(None),
                )
            )
        )
    consulta = consulta.order_by(GovernmentBankAccount.codigo.desc())
    cuentas = db.scalars(consulta).all()

    todos_ids = {cuenta.bank_id for cuenta in cuentas}
    bancos = {
        str(banco.id): banco
        for banco in db.scalars(
            select(GovernmentBank).where(
                GovernmentBank.id.in_(todos_ids),
                GovernmentBank.tenant_id == ctx.tenant_id,
                GovernmentBank.company_id == ctx.company_id,
            )
        ).all()
    } if todos_ids else {}

    acto_ids = {cuenta.acto_id for cuenta in cuentas if cuenta.acto_id is not None}
    actos = {
        str(acto.id): acto
        for acto in db.scalars(
            select(GovernmentAct).where(GovernmentAct.id.in_(acto_ids))
        ).all()
    } if acto_ids else {}

    cuenta_ids = [cuenta.id for cuenta in cuentas]
    conteos: dict[Any, int] = {}
    if cuenta_ids:
        filas = db.execute(
            select(
                GovernmentBankAccountAuthorization.account_id,
                func.count(GovernmentBankAccountAuthorization.id),
            )
            .where(
                GovernmentBankAccountAuthorization.account_id.in_(cuenta_ids),
                GovernmentBankAccountAuthorization.company_id == ctx.company_id,
                GovernmentBankAccountAuthorization.vigente_hasta.is_(None),
            )
            .group_by(GovernmentBankAccountAuthorization.account_id)
        ).all()
        conteos = {cuenta_id: total for cuenta_id, total in filas}

    proyecto = (
        select(
            GovernmentBankAccount.estado,
            func.count(GovernmentBankAccount.id),
        )
        .where(
            GovernmentBankAccount.tenant_id == ctx.tenant_id,
            GovernmentBankAccount.company_id == ctx.company_id,
        )
        .group_by(GovernmentBankAccount.estado)
    )
    todos_conteos = {estado_fila: total for estado_fila, total in db.execute(proyecto).all()}
    resumen = {
        "borradores": todos_conteos.get("BORRADOR", 0),
        "vigentes": todos_conteos.get("VIGENTE", 0),
        "inactivas": todos_conteos.get("INACTIVA", 0),
        "cerradas": todos_conteos.get("CERRADA", 0),
    }

    hoy = hoy_de_negocio()
    items: list[dict[str, Any]] = []
    for cuenta in cuentas:
        acto = actos.get(cuenta.acto_id) if cuenta.acto_id is not None else None
        items.append(
            _resumen(
                cuenta,
                bancos[cuenta.bank_id],
                acto,
                conteos.get(cuenta.id, 0),
                hoy,
            )
        )
    return {"items": items, "resumen": resumen}


def _banco_salida(banco: GovernmentBank) -> dict[str, Any]:
    return {
        "id": banco.id,
        "codigo": banco.codigo,
        "nombre": banco.nombre,
        "estado": banco.estado,
        "version": banco.version,
    }


def listar_bancos(
    db: Session, ctx: CompanyContext, estado: str | None
) -> dict[str, Any]:
    consulta = select(GovernmentBank).where(
        GovernmentBank.tenant_id == ctx.tenant_id,
        GovernmentBank.company_id == ctx.company_id,
    )
    if estado is not None:
        consulta = consulta.where(GovernmentBank.estado == estado)
    consulta = consulta.order_by(GovernmentBank.codigo)
    return {"items": [_banco_salida(banco) for banco in db.scalars(consulta).all()]}


def opciones(db: Session, ctx: CompanyContext) -> dict[str, Any]:
    bancos = db.scalars(
        select(GovernmentBank)
        .where(
            GovernmentBank.tenant_id == ctx.tenant_id,
            GovernmentBank.company_id == ctx.company_id,
            GovernmentBank.estado == "ACTIVO",
        )
        .order_by(GovernmentBank.codigo)
    ).all()

    hoy = hoy_de_negocio()
    posiciones = db.scalars(_cargos_autorizables(ctx)).all()
    unit_ids = {posicion.unit_id for posicion in posiciones}
    unidades = {
        unidad.id: unidad
        for unidad in db.scalars(
            select(GovernmentUnit).where(GovernmentUnit.id.in_(unit_ids))
        ).all()
    } if unit_ids else {}

    actos = db.scalars(
        select(GovernmentAct)
        .where(
            GovernmentAct.company_id == ctx.company_id,
            GovernmentAct.status.in_(ESTADOS_ACTO_CON_EFECTO),
            GovernmentAct.fecha <= hoy,
        )
        .order_by(GovernmentAct.fecha.desc(), GovernmentAct.numero)
        .limit(500)
    ).all()

    return {
        "bancos": [
            {"id": banco.id, "codigo": banco.codigo, "nombre": banco.nombre}
            for banco in bancos
        ],
        "cargos": [
            {
                "id": str(posicion.id),
                "codigo": posicion.code,
                "denominacion": posicion.name,
                "unidad": unidades[posicion.unit_id].name,
            }
            for posicion in posiciones
        ],
        "actos": [_referencia_acto(acto) for acto in actos],
    }


def numero_completo(
    db: Session, ctx: CompanyContext, cuenta_id: Any
) -> dict[str, Any]:
    cuenta = _cuenta_de_empresa(db, ctx, cuenta_id)
    _auditar(
        db,
        ctx,
        cuenta,
        "GOV_BANK_ACCOUNT_NUMBER_VIEWED",
        {
            "codigo": cuenta.codigo,
            "numero_enmascarado": _enmascarar(cuenta.numero),
        },
    )
    return {"numero": cuenta.numero}


def crear_banco(db: Session, ctx: CompanyContext, datos: Any) -> GovernmentBank:
    _validar_codigo_banco(datos.codigo)
    existente = db.scalars(
        select(GovernmentBank)
        .where(
            GovernmentBank.tenant_id == ctx.tenant_id,
            GovernmentBank.company_id == ctx.company_id,
            GovernmentBank.codigo == datos.codigo,
        )
        .limit(1)
    ).first()
    if existente is not None:
        raise ConflictError(
            "GOV_BANK_CODE_DUPLICATE",
            "Ya hay un banco con ese código en este ente",
        )
    banco = GovernmentBank(
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        codigo=datos.codigo,
        nombre=datos.nombre,
        estado="ACTIVO",
        version=1,
        created_by=ctx.user_id,
    )
    db.add(banco)
    _guardar(db, ("GOV_BANK_CODE_DUPLICATE", "Ya hay un banco con ese código en este ente"))
    _auditar_banco(
        db,
        ctx,
        banco,
        "GOV_BANK_CREATED",
        {"codigo": banco.codigo, "nombre": banco.nombre},
    )
    return banco


def editar_banco(
    db: Session, ctx: CompanyContext, banco_id: Any, version: Any, cambios: Any
) -> GovernmentBank:
    banco = _para_escribir_banco(db, ctx, banco_id, version)
    valores = cambios.model_dump(exclude_unset=True)
    for campo, valor in valores.items():
        if valor is None:
            raise _invalida(f"El campo {campo} no puede ser nulo")
        setattr(banco, campo, valor)
    banco.version += 1
    _guardar(db, ("GOV_BANK_CODE_DUPLICATE", "Ya hay un banco con ese código en este ente"))
    _auditar_banco(
        db,
        ctx,
        banco,
        "GOV_BANK_UPDATED",
        {"codigo": banco.codigo, "campos": sorted(valores.keys())},
    )
    return banco


def crear(db: Session, ctx: CompanyContext, datos: Any) -> GovernmentBankAccount:
    banco = _banco_utilizable(db, ctx, datos.banco_id)
    _validar_numero(datos.numero, banco)
    if datos.vigente_hasta is not None and datos.vigente_hasta < datos.vigente_desde:
        raise _invalida("La vigencia hasta no puede ser anterior a la vigente desde")

    duplicado = db.scalars(
        select(GovernmentBankAccount)
        .where(
            GovernmentBankAccount.tenant_id == ctx.tenant_id,
            GovernmentBankAccount.company_id == ctx.company_id,
            GovernmentBankAccount.bank_id == banco.id,
            GovernmentBankAccount.numero == datos.numero,
        )
        .limit(1)
    ).first()
    if duplicado is not None:
        raise ConflictError(
            "GOV_BANK_ACCOUNT_DUPLICATE",
            "Ya hay una cuenta con ese número en este banco",
        )

    cuenta = GovernmentBankAccount(
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        codigo=_siguiente_codigo(db, ctx),
        denominacion=datos.denominacion,
        bank_id=banco.id,
        tipo=datos.tipo,
        numero=datos.numero,
        moneda=datos.moneda,
        vigente_desde=datos.vigente_desde,
        vigente_hasta=datos.vigente_hasta,
        estado="BORRADOR",
        version=1,
        created_by=ctx.user_id,
    )
    db.add(cuenta)
    try:
        db.flush()
    except IntegrityError as error:
        db.rollback()
        if "uq_gov_bank_accounts_numero" in str(error.orig):
            raise ConflictError(
                "GOV_BANK_ACCOUNT_DUPLICATE",
                "Ya hay una cuenta con ese número en este banco",
            ) from None
        raise ConflictError(
            "GOV_BANK_ACCOUNT_CONFLICT",
            "Otra cuenta se registró al mismo tiempo; vuelva a intentarlo",
        ) from None

    _historia(db, ctx, cuenta, "CREADA", None)
    _auditar(
        db,
        ctx,
        cuenta,
        "GOV_BANK_ACCOUNT_CREATED",
        {
            "codigo": cuenta.codigo,
            "banco_codigo": banco.codigo,
            "tipo": cuenta.tipo,
            "moneda": cuenta.moneda,
            "numero_enmascarado": _enmascarar(cuenta.numero),
        },
    )
    db.flush()
    return cuenta


def editar(
    db: Session,
    ctx: CompanyContext,
    cuenta_id: Any,
    version: Any,
    cambios: Any,
) -> GovernmentBankAccount:
    cuenta = _para_escribir(db, ctx, cuenta_id, version)
    _exigir_estado(cuenta, "BORRADOR")
    valores = cambios.model_dump(exclude_unset=True)
    for campo in ("denominacion", "banco_id", "tipo", "numero", "moneda", "vigente_desde"):
        if campo in valores and valores[campo] is None:
            raise _invalida("Un dato obligatorio de la cuenta no puede quedar vacío")
    nuevos: dict[str, Any] = {
        "denominacion": valores.get("denominacion", cuenta.denominacion),
        "bank_id": valores.get("banco_id", cuenta.bank_id),
        "tipo": valores.get("tipo", cuenta.tipo),
        "numero": valores.get("numero", cuenta.numero),
        "moneda": valores.get("moneda", cuenta.moneda),
        "vigente_desde": valores.get("vigente_desde", cuenta.vigente_desde),
        "vigente_hasta": valores.get("vigente_hasta", cuenta.vigente_hasta),
    }
    numero_cambio = nuevos["numero"] != cuenta.numero
    if numero_cambio or nuevos["bank_id"] != cuenta.bank_id:
        banco = _banco_utilizable(db, ctx, nuevos["bank_id"])
        _validar_numero(nuevos["numero"], banco)
        duplicado = db.scalars(
            select(GovernmentBankAccount)
            .where(
                GovernmentBankAccount.tenant_id == ctx.tenant_id,
                GovernmentBankAccount.company_id == ctx.company_id,
                GovernmentBankAccount.bank_id == banco.id,
                GovernmentBankAccount.numero == nuevos["numero"],
                GovernmentBankAccount.id != cuenta.id,
            )
            .limit(1)
        ).first()
        if duplicado is not None:
            raise ConflictError(
                "GOV_BANK_ACCOUNT_DUPLICATE",
                "Ya hay una cuenta con ese número en este banco",
            )
    if nuevos["vigente_hasta"] is not None and nuevos["vigente_hasta"] < nuevos["vigente_desde"]:
        raise _invalida("La vigencia hasta no puede ser anterior a la vigente desde")
    campos = sorted(
        "banco_id" if campo == "bank_id" else campo
        for campo, valor in nuevos.items()
        if valor != getattr(cuenta, campo)
    )
    for campo, valor in nuevos.items():
        setattr(cuenta, campo, valor)
    cuenta.version += 1
    try:
        db.flush()
    except IntegrityError as error:
        db.rollback()
        if "uq_gov_bank_accounts_numero" in str(error.orig):
            raise ConflictError(
                "GOV_BANK_ACCOUNT_DUPLICATE",
                "Ya hay una cuenta con ese número en este banco",
            ) from None
        raise ConflictError(
            "GOV_BANK_ACCOUNT_CONFLICT",
            "Otra cuenta se registró al mismo tiempo; vuelva a intentarlo",
        ) from None

    detalle_historia: dict[str, Any] = {"campos": campos}
    if numero_cambio:
        detalle_historia["numero_enmascarado"] = _enmascarar(cuenta.numero)
    _historia(db, ctx, cuenta, "EDITADA", detalle_historia)
    _auditar(
        db,
        ctx,
        cuenta,
        "GOV_BANK_ACCOUNT_UPDATED",
        {"codigo": cuenta.codigo, "campos": campos},
    )
    db.flush()
    return cuenta


def vincular_acto(
    db: Session,
    ctx: CompanyContext,
    cuenta_id: Any,
    version: Any,
    datos: Any,
) -> GovernmentBankAccount:
    cuenta = _para_escribir(db, ctx, cuenta_id, version)
    _exigir_estado(cuenta, "BORRADOR", "VIGENTE", "INACTIVA")
    acto = _acto_con_efecto(db, ctx, datos.acto_id)
    cuenta.acto_id = str(acto.id)
    cuenta.version += 1
    _historia(
        db,
        ctx,
        cuenta,
        "ACTO_VINCULADO",
        {"acto_id": acto.id, "acto_numero": acto.numero},
    )
    _auditar(
        db,
        ctx,
        cuenta,
        "GOV_BANK_ACCOUNT_ACT_LINKED",
        {"acto_id": acto.id, "acto_numero": acto.numero, "codigo": cuenta.codigo},
    )
    db.flush()
    return cuenta


def activar(
    db: Session, ctx: CompanyContext, cuenta_id: Any, version: Any
) -> GovernmentBankAccount:
    cuenta = _para_escribir(db, ctx, cuenta_id, version)
    _exigir_estado(cuenta, "BORRADOR")
    _exigir_lista(db, ctx, cuenta)
    evaluar_antes_de_actuar(db, ctx, "TRE01_ACTIVAR", ENTIDAD_CUENTA, str(cuenta.id))
    cuenta.estado = "VIGENTE"
    cuenta.activada_por = ctx.user_id
    cuenta.activada_en = datetime.now(UTC)
    cuenta.version += 1
    _historia(
        db,
        ctx,
        cuenta,
        "ACTIVADA",
        {"acto_id": cuenta.acto_id},
    )
    _auditar(
        db,
        ctx,
        cuenta,
        "GOV_BANK_ACCOUNT_ACTIVATED",
        {
            "acto_id": cuenta.acto_id,
            "codigo": cuenta.codigo,
            "vigente_desde": cuenta.vigente_desde.isoformat()
            if cuenta.vigente_desde is not None
            else None,
        },
    )
    db.flush()
    return cuenta


def inactivar(
    db: Session,
    ctx: CompanyContext,
    cuenta_id: Any,
    version: Any,
    datos: Any,
) -> GovernmentBankAccount:
    cuenta = _para_escribir(db, ctx, cuenta_id, version)
    _exigir_estado(cuenta, "VIGENTE")
    evaluar_antes_de_actuar(db, ctx, "TRE01_INACTIVAR", ENTIDAD_CUENTA, str(cuenta.id))
    cuenta.estado = "INACTIVA"
    cuenta.version += 1
    _historia(db, ctx, cuenta, "INACTIVADA", {"motivo": datos.motivo})
    _auditar(
        db,
        ctx,
        cuenta,
        "GOV_BANK_ACCOUNT_DEACTIVATED",
        {"codigo": cuenta.codigo, "motivo": datos.motivo},
    )
    db.flush()
    return cuenta


def reactivar(
    db: Session,
    ctx: CompanyContext,
    cuenta_id: Any,
    version: Any,
    datos: Any,
) -> GovernmentBankAccount:
    cuenta = _para_escribir(db, ctx, cuenta_id, version)
    _exigir_estado(cuenta, "INACTIVA")
    _exigir_lista(db, ctx, cuenta)
    cuenta.estado = "VIGENTE"
    cuenta.version += 1
    _historia(db, ctx, cuenta, "REACTIVADA", {"motivo": datos.motivo})
    _auditar(
        db,
        ctx,
        cuenta,
        "GOV_BANK_ACCOUNT_REACTIVATED",
        {"codigo": cuenta.codigo, "motivo": datos.motivo},
    )
    db.flush()
    return cuenta


def cerrar(
    db: Session,
    ctx: CompanyContext,
    cuenta_id: Any,
    version: Any,
    datos: Any,
) -> GovernmentBankAccount:
    cuenta = _para_escribir(db, ctx, cuenta_id, version)
    _exigir_estado(cuenta, "VIGENTE", "INACTIVA")
    hoy = hoy_de_negocio()
    if datos.fecha_cierre > hoy or datos.fecha_cierre < cuenta.vigente_desde:
        raise _invalida("La fecha de cierre no es válida")
    evaluar_antes_de_actuar(db, ctx, "TRE01_CERRAR", ENTIDAD_CUENTA, str(cuenta.id))

    for autorizacion in _autorizados_en_vigor(db, ctx, cuenta.id):
        autorizacion.vigente_hasta = max(datos.fecha_cierre, autorizacion.vigente_desde)
        autorizacion.motivo_fin = MOTIVO_CIERRE_AUTORIZACION
        autorizacion.terminada_por = ctx.user_id
        autorizacion.terminada_en = datetime.now(UTC)
        _historia(
            db,
            ctx,
            cuenta,
            "AUTORIZADO_FIN",
            {
                "autorizacion_id": autorizacion.id,
                "cargo_codigo": autorizacion.cargo_codigo,
                "motivo": autorizacion.motivo_fin,
            },
        )
        _auditar(
            db,
            ctx,
            cuenta,
            "GOV_BANK_AUTHORIZATION_ENDED",
            {
                "acto_id": None,
                "cargo_codigo": autorizacion.cargo_codigo,
                "codigo": cuenta.codigo,
                "motivo": autorizacion.motivo_fin,
                "vigente_hasta": autorizacion.vigente_hasta.isoformat()
                if autorizacion.vigente_hasta is not None
                else None,
            },
        )

    cuenta.estado = "CERRADA"
    cuenta.vigente_hasta = datos.fecha_cierre
    cuenta.cerrada_por = ctx.user_id
    cuenta.cerrada_en = datetime.now(UTC)
    cuenta.fecha_cierre = datos.fecha_cierre
    cuenta.motivo_cierre = datos.motivo
    cuenta.version += 1
    _historia(
        db,
        ctx,
        cuenta,
        "CERRADA",
        {"fecha_cierre": datos.fecha_cierre.isoformat(), "motivo": datos.motivo},
    )
    _auditar(
        db,
        ctx,
        cuenta,
        "GOV_BANK_ACCOUNT_CLOSED",
        {"codigo": cuenta.codigo, "fecha_cierre": datos.fecha_cierre.isoformat(), "motivo": datos.motivo},
    )
    db.flush()
    return cuenta


def autorizar(
    db: Session,
    ctx: CompanyContext,
    cuenta_id: Any,
    version: Any,
    datos: Any,
) -> GovernmentBankAccount:
    cuenta = _para_escribir(db, ctx, cuenta_id, version)
    _exigir_estado(cuenta, "BORRADOR", "VIGENTE", "INACTIVA")
    if cuenta.acto_id is not None:
        acto_cuenta = db.get(GovernmentAct, cuenta.acto_id)
        if _acto_sin_efecto(acto_cuenta):
            raise ConflictError(
                "GOV_BANK_ACCOUNT_ACT_WITHOUT_EFFECT",
                "El acto habilitante fue revocado o anulado; vincule un acto vigente",
            )
    cargo = _cargo_autorizable(db, ctx, datos.cargo_id)
    _acto_con_efecto(db, ctx, datos.acto_id)

    hoy = hoy_de_negocio()
    if datos.vigente_desde > hoy or datos.vigente_desde < cuenta.vigente_desde:
        raise _invalida("La fecha de la autorización no es válida")
    if cuenta.vigente_hasta is not None and datos.vigente_desde > cuenta.vigente_hasta:
        raise _invalida("La fecha de la autorización no es válida")

    en_vigor = _autorizados_en_vigor(db, ctx, cuenta.id)
    if any(a.position_id == cargo.id for a in en_vigor):
        raise ConflictError(
            "GOV_BANK_AUTHORIZATION_DUPLICATE",
            "Ese cargo ya está autorizado en esta cuenta",
        )

    evaluar_antes_de_actuar(db, ctx, "TRE01_AUTORIZAR", ENTIDAD_CUENTA, str(cuenta.id))

    unidad = db.scalars(select(GovernmentUnit).where(GovernmentUnit.id == cargo.unit_id)).one()
    autorizacion = GovernmentBankAccountAuthorization(
        account_id=cuenta.id,
        company_id=ctx.company_id,
        position_id=cargo.id,
        cargo_codigo=cargo.code,
        cargo_denominacion=cargo.name,
        cargo_unidad=unidad.name,
        acto_alta_id=datos.acto_id,
        vigente_desde=datos.vigente_desde,
        created_by=ctx.user_id,
    )
    db.add(autorizacion)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ConflictError(
            "GOV_BANK_AUTHORIZATION_DUPLICATE",
            "Ese cargo ya está autorizado en esta cuenta",
        ) from None

    cuenta.version += 1
    _historia(
        db,
        ctx,
        cuenta,
        "AUTORIZADO_ALTA",
        {
            "autorizacion_id": autorizacion.id,
            "cargo_codigo": autorizacion.cargo_codigo,
            "acto_id": autorizacion.acto_alta_id,
            "vigente_desde": autorizacion.vigente_desde.isoformat()
            if autorizacion.vigente_desde is not None
            else None,
        },
    )
    _auditar(
        db,
        ctx,
        cuenta,
        "GOV_BANK_AUTHORIZATION_ADDED",
        {
            "acto_id": autorizacion.acto_alta_id,
            "cargo_codigo": autorizacion.cargo_codigo,
            "codigo": cuenta.codigo,
            "vigente_desde": autorizacion.vigente_desde.isoformat()
            if autorizacion.vigente_desde is not None
            else None,
        },
    )
    db.flush()
    return cuenta


def terminar_autorizacion(
    db: Session,
    ctx: CompanyContext,
    cuenta_id: Any,
    autorizacion_id: Any,
    version: Any,
    datos: Any,
) -> GovernmentBankAccount:
    cuenta = _para_escribir(db, ctx, cuenta_id, version)
    _exigir_estado(cuenta, "BORRADOR", "VIGENTE", "INACTIVA")

    autorizacion = db.scalars(
        select(GovernmentBankAccountAuthorization)
        .where(
            GovernmentBankAccountAuthorization.id == autorizacion_id,
            GovernmentBankAccountAuthorization.account_id == cuenta.id,
            GovernmentBankAccountAuthorization.company_id == ctx.company_id,
        )
        .limit(1)
    ).first()
    if autorizacion is None:
        raise NotFoundError(
            "GOV_BANK_AUTHORIZATION_NOT_FOUND",
            "La autorización no existe en esta cuenta",
        )
    if autorizacion.vigente_hasta is not None:
        raise ConflictError(
            "GOV_BANK_ACCOUNT_INVALID_STATE",
            "La cuenta no admite esta acción en su estado actual",
        )

    _acto_con_efecto(db, ctx, datos.acto_id)
    hoy = hoy_de_negocio()
    if datos.vigente_hasta > hoy or datos.vigente_hasta < autorizacion.vigente_desde:
        raise _invalida("La fecha de fin de la autorización no es válida")

    evaluar_antes_de_actuar(
        db, ctx, "TRE01_FIN_AUTORIZACION", ENTIDAD_CUENTA, str(cuenta.id)
    )

    autorizacion.vigente_hasta = datos.vigente_hasta
    autorizacion.acto_fin_id = datos.acto_id
    autorizacion.motivo_fin = datos.motivo
    autorizacion.terminada_por = ctx.user_id
    autorizacion.terminada_en = datetime.now(UTC)
    cuenta.version += 1

    _historia(
        db,
        ctx,
        cuenta,
        "AUTORIZADO_FIN",
        {
            "autorizacion_id": autorizacion.id,
            "cargo_codigo": autorizacion.cargo_codigo,
            "acto_id": autorizacion.acto_fin_id,
            "motivo": autorizacion.motivo_fin,
            "vigente_hasta": autorizacion.vigente_hasta.isoformat()
            if autorizacion.vigente_hasta is not None
            else None,
        },
    )
    _auditar(
        db,
        ctx,
        cuenta,
        "GOV_BANK_AUTHORIZATION_ENDED",
        {
            "acto_id": autorizacion.acto_fin_id,
            "cargo_codigo": autorizacion.cargo_codigo,
            "codigo": cuenta.codigo,
            "motivo": autorizacion.motivo_fin,
            "vigente_hasta": autorizacion.vigente_hasta.isoformat()
            if autorizacion.vigente_hasta is not None
            else None,
        },
    )
    db.flush()
    return cuenta
