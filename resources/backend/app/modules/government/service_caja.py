"""Servicio de la programación financiera de caja (TRE-02, GOV-TRE-002)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext
from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.government.models import (
    GovernmentBank,
    GovernmentBankAccount,
    GovernmentCashItem,
    GovernmentCashProgram,
    GovernmentCashProgramDeclaration,
    GovernmentCashProgramHistory,
    GovernmentCashProgramLine,
    GovernmentCashProgramVersion,
)
from app.modules.government.service_auditoria import _instante, _usuarios_por_ids
from app.modules.government.service_cierres import evaluar_cierre
from app.modules.government.service_sod import evaluar_antes_de_actuar
from app.shared.audit import record_audit
from app.shared.clock import hoy_de_negocio

ENTIDAD_PROGRAMA = "GovernmentCashProgram"
ENTIDAD_RUBRO = "GovernmentCashItem"


def _instante_o_nulo(valor: datetime | None) -> datetime | None:
    return None if valor is None else _instante(valor)


def _invalida(mensaje: str) -> KontrolError:
    return KontrolError(
        code="GOV_CASH_PROGRAM_INVALID",
        message=mensaje,
        status_code=422,
    )


def _auditar(
    db: Session,
    ctx: CompanyContext,
    entidad_tipo: str,
    entidad_id: str,
    accion: str,
    after: dict[str, Any],
) -> None:
    record_audit(
        db,
        action=accion,
        entity_type=entidad_tipo,
        entity_id=entidad_id,
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after=after,
    )


def _historia(
    db: Session,
    ctx: CompanyContext,
    programa: GovernmentCashProgram,
    numero: int,
    tipo: str,
    detalle: dict[str, Any] | None,
) -> None:
    db.add(
        GovernmentCashProgramHistory(
            program_id=str(programa.id),
            company_id=ctx.company_id,
            version_numero=numero,
            tipo=tipo,
            detalle=detalle,
            created_by=ctx.user_id,
        )
    )


def _guardar(db: Session, duplicado: tuple[str, str]) -> None:
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ConflictError(*duplicado) from None


def _programa_de_empresa(
    db: Session,
    ctx: CompanyContext,
    programa_id: Any,
    bloquear: bool = False,
) -> GovernmentCashProgram:
    query = select(GovernmentCashProgram).where(
        GovernmentCashProgram.id == programa_id,
        GovernmentCashProgram.tenant_id == ctx.tenant_id,
        GovernmentCashProgram.company_id == ctx.company_id,
    )
    if bloquear:
        query = query.with_for_update()
    programa = db.scalar(query)
    if programa is None:
        raise NotFoundError(
            "GOV_CASH_PROGRAM_NOT_FOUND",
            "El programa no existe en este ente",
        )
    return programa


def _para_escribir_programa(
    db: Session,
    ctx: CompanyContext,
    programa_id: Any,
    version: Any,
) -> GovernmentCashProgram:
    if version is None:
        raise KontrolError(
            code="GOV_CASH_PROGRAM_IF_MATCH_REQUIRED",
            message="Falta la cabecera If-Match con la versión",
            status_code=428,
        )
    programa = _programa_de_empresa(db, ctx, programa_id, bloquear=True)
    if programa.version != version:
        raise ConflictError(
            "GOV_CASH_PROGRAM_STALE",
            "El dato cambió desde que lo abrió; recárguelo",
            details={"version_actual": programa.version},
        )
    return programa


def _rubro_de_empresa(
    db: Session,
    ctx: CompanyContext,
    rubro_id: Any,
    bloquear: bool = False,
) -> GovernmentCashItem:
    query = select(GovernmentCashItem).where(
        GovernmentCashItem.id == rubro_id,
        GovernmentCashItem.tenant_id == ctx.tenant_id,
        GovernmentCashItem.company_id == ctx.company_id,
    )
    if bloquear:
        query = query.with_for_update()
    rubro = db.scalar(query)
    if rubro is None:
        raise NotFoundError(
            "GOV_CASH_ITEM_NOT_FOUND",
            "El rubro no existe en este ente",
        )
    return rubro


def _para_escribir_rubro(
    db: Session,
    ctx: CompanyContext,
    rubro_id: Any,
    version: Any,
) -> GovernmentCashItem:
    if version is None:
        raise KontrolError(
            code="GOV_CASH_PROGRAM_IF_MATCH_REQUIRED",
            message="Falta la cabecera If-Match con la versión",
            status_code=428,
        )
    rubro = _rubro_de_empresa(db, ctx, rubro_id, bloquear=True)
    if rubro.version != version:
        raise ConflictError(
            "GOV_CASH_PROGRAM_STALE",
            "El dato cambió desde que lo abrió; recárguelo",
            details={"version_actual": rubro.version},
        )
    return rubro


def _versiones(
    db: Session,
    programa: GovernmentCashProgram,
) -> list[GovernmentCashProgramVersion]:
    return list(
        db.scalars(
            select(GovernmentCashProgramVersion)
            .where(GovernmentCashProgramVersion.program_id == str(programa.id))
            .order_by(GovernmentCashProgramVersion.numero)
        )
    )


def _version_en(
    versiones: list[GovernmentCashProgramVersion],
    estado: str,
) -> GovernmentCashProgramVersion | None:
    return next(
        (version for version in versiones if version.estado == estado),
        None,
    )


def _borrador_o_error(
    db: Session,
    programa: GovernmentCashProgram,
) -> GovernmentCashProgramVersion:
    versiones = _versiones(db, programa)
    borrador = _version_en(versiones, "BORRADOR")
    if borrador is None:
        raise ConflictError(
            "GOV_CASH_PROGRAM_INVALID_STATE",
            "El programa no tiene una versión en borrador",
        )
    return borrador


def _vigente_o_error(
    versiones: list[GovernmentCashProgramVersion],
) -> GovernmentCashProgramVersion:
    vigente = _version_en(versiones, "VIGENTE")
    if vigente is None:
        raise ConflictError(
            "GOV_CASH_PROGRAM_INVALID_STATE",
            "El programa no tiene una versión vigente",
        )
    return vigente


def _validar_mes(
    programa: GovernmentCashProgram,
    version: GovernmentCashProgramVersion,
    mes: int,
) -> None:
    if mes < programa.mes_inicial:
        raise _invalida("El mes está fuera del programa")
    if (
        version.numero > 1
        and programa.ejercicio == hoy_de_negocio().year
        and mes < hoy_de_negocio().month
    ):
        raise ConflictError(
            "GOV_CASH_PROGRAM_PAST_MONTH",
            "El mes ya pasó y no se puede modificar",
        )


def _cuenta_declarable(
    db: Session,
    ctx: CompanyContext,
    cuenta_id: Any,
    moneda: str,
) -> GovernmentBankAccount:
    cuenta = db.scalar(
        select(GovernmentBankAccount).where(
            GovernmentBankAccount.id == cuenta_id,
            GovernmentBankAccount.tenant_id == ctx.tenant_id,
            GovernmentBankAccount.company_id == ctx.company_id,
            GovernmentBankAccount.moneda == moneda,
            GovernmentBankAccount.estado == "VIGENTE",
        )
    )
    if cuenta is None:
        raise _invalida("La cuenta no es utilizable en este programa")
    return cuenta


def _rubro_utilizable(
    db: Session,
    ctx: CompanyContext,
    rubro_id: Any,
) -> GovernmentCashItem:
    rubro = db.scalar(
        select(GovernmentCashItem).where(
            GovernmentCashItem.id == rubro_id,
            GovernmentCashItem.tenant_id == ctx.tenant_id,
            GovernmentCashItem.company_id == ctx.company_id,
            GovernmentCashItem.estado == "ACTIVO",
        )
    )
    if rubro is None:
        raise _invalida("El rubro no es utilizable en este programa")
    return rubro


def listar_rubros(
    db: Session,
    ctx: CompanyContext,
    estado: str | None,
    tipo: str | None,
) -> list[GovernmentCashItem]:
    query = (
        select(GovernmentCashItem)
        .where(
            GovernmentCashItem.tenant_id == ctx.tenant_id,
            GovernmentCashItem.company_id == ctx.company_id,
        )
        .order_by(GovernmentCashItem.codigo)
    )
    if estado is not None:
        query = query.where(GovernmentCashItem.estado == estado)
    if tipo is not None:
        query = query.where(GovernmentCashItem.tipo == tipo)
    return list(db.scalars(query))


def crear_rubro(
    db: Session,
    ctx: CompanyContext,
    datos: Any,
) -> GovernmentCashItem:
    rubro = GovernmentCashItem(
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        codigo=datos.codigo,
        nombre=datos.nombre,
        tipo=datos.tipo,
        estado="ACTIVO",
        version=1,
        created_by=ctx.user_id,
    )
    db.add(rubro)
    _guardar(db, ("GOV_CASH_ITEM_DUPLICATE", "Ya hay un rubro con ese código"))
    _auditar(
        db,
        ctx,
        ENTIDAD_RUBRO,
        str(rubro.id),
        "GOV_CASH_ITEM_CREATED",
        {
            "codigo": rubro.codigo,
            "nombre": rubro.nombre,
            "tipo": rubro.tipo,
        },
    )
    return rubro


def editar_rubro(
    db: Session,
    ctx: CompanyContext,
    rubro_id: Any,
    version: Any,
    cambios: Any,
) -> GovernmentCashItem:
    rubro = _para_escribir_rubro(db, ctx, rubro_id, version)
    campos: list[str] = []
    if cambios.nombre is not None and cambios.nombre != rubro.nombre:
        rubro.nombre = cambios.nombre
        campos.append("nombre")
    if cambios.estado is not None and cambios.estado != rubro.estado:
        rubro.estado = cambios.estado
        campos.append("estado")
    if campos:
        rubro.version += 1
        _auditar(
            db,
            ctx,
            ENTIDAD_RUBRO,
            str(rubro.id),
            "GOV_CASH_ITEM_UPDATED",
            {
                "campos": campos,
                "codigo": rubro.codigo,
            },
        )
    return rubro


def rubro_salida(rubro: GovernmentCashItem) -> dict[str, Any]:
    return {
        "id": str(rubro.id),
        "codigo": rubro.codigo,
        "nombre": rubro.nombre,
        "tipo": rubro.tipo,
        "estado": rubro.estado,
        "version": rubro.version,
    }


def listar(db: Session, ctx: CompanyContext, ejercicio: int | None, moneda: str | None, estado: str | None) -> dict:
    filtros = []
    filtros.append(GovernmentCashProgram.tenant_id == ctx.tenant_id)
    filtros.append(GovernmentCashProgram.company_id == ctx.company_id)
    if ejercicio is not None:
        filtros.append(GovernmentCashProgram.ejercicio == ejercicio)
    if moneda is not None:
        filtros.append(GovernmentCashProgram.moneda == moneda)
    if estado is not None:
        filtros.append(GovernmentCashProgram.estado == estado)
    programas = (
        db.scalars(
            select(GovernmentCashProgram)
            .filter(*filtros)
            .order_by(GovernmentCashProgram.ejercicio.desc(), GovernmentCashProgram.moneda)
        )
        .all()
    )
    programa_ids = [str(programa.id) for programa in programas]
    versiones_por_programa: dict[str, list[GovernmentCashProgramVersion]] = {}
    declaraciones_por_programa: dict[str, list[GovernmentCashProgramDeclaration]] = {}
    if programa_ids:
        versiones = (
            db.scalars(
                select(GovernmentCashProgramVersion)
                .filter(GovernmentCashProgramVersion.program_id.in_(programa_ids))
                .order_by(GovernmentCashProgramVersion.numero)
            )
            .all()
        )
        for version in versiones:
            versiones_por_programa.setdefault(str(version.program_id), []).append(version)
        declaraciones = (
            db.scalars(
                select(GovernmentCashProgramDeclaration)
                .filter(GovernmentCashProgramDeclaration.program_id.in_(programa_ids))
            )
            .all()
        )
        for declaracion in declaraciones:
            declaraciones_por_programa.setdefault(str(declaracion.program_id), []).append(declaracion)
    items = []
    for programa in programas:
        versiones_programa = versiones_por_programa.get(str(programa.id), [])
        version_vigente = next(
            (version.numero for version in versiones_programa if version.estado == "VIGENTE"),
            None,
        )
        disponibilidad_inicial = sum(
            (declaracion.monto for declaracion in declaraciones_por_programa.get(str(programa.id), [])),
            Decimal("0.00"),
        )
        items.append(
            {
                "id": str(programa.id),
                "codigo": programa.codigo,
                "ejercicio": programa.ejercicio,
                "moneda": programa.moneda,
                "mes_inicial": programa.mes_inicial,
                "estado": programa.estado,
                "version": programa.version,
                "version_vigente": version_vigente,
                "disponibilidad_inicial": disponibilidad_inicial,
            }
        )
    resumen = {
        "borradores": db.scalar(
            select(func.count())
            .select_from(GovernmentCashProgram)
            .filter(
                GovernmentCashProgram.tenant_id == ctx.tenant_id,
                GovernmentCashProgram.company_id == ctx.company_id,
                GovernmentCashProgram.estado == "BORRADOR",
            )
        ),
        "vigentes": db.scalar(
            select(func.count())
            .select_from(GovernmentCashProgram)
            .filter(
                GovernmentCashProgram.tenant_id == ctx.tenant_id,
                GovernmentCashProgram.company_id == ctx.company_id,
                GovernmentCashProgram.estado == "VIGENTE",
            )
        ),
        "cerrados": db.scalar(
            select(func.count())
            .select_from(GovernmentCashProgram)
            .filter(
                GovernmentCashProgram.tenant_id == ctx.tenant_id,
                GovernmentCashProgram.company_id == ctx.company_id,
                GovernmentCashProgram.estado == "CERRADO",
            )
        ),
    }
    return {"items": items, "resumen": resumen}


def detalle(db: Session, ctx: CompanyContext, programa_id: Any, numero_version: int | None = None) -> dict:
    programa = _programa_de_empresa(db, ctx, programa_id)
    versiones = _versiones(db, programa)
    if numero_version is not None:
        version_mostrada = next(
            (version for version in versiones if version.numero == numero_version),
            None,
        )
        if version_mostrada is None:
            raise NotFoundError(
                "GOV_CASH_PROGRAM_NOT_FOUND",
                "No existe la versión solicitada del programa",
            )
    else:
        version_mostrada = (
            _version_en(versiones, "VIGENTE")
            or _version_en(versiones, "BORRADOR")
            or (versiones[-1] if versiones else None)
        )
        if version_mostrada is None:
            raise NotFoundError(
                "GOV_CASH_PROGRAM_NOT_FOUND",
                "No existe el programa solicitado",
            )
    version_vigente = next(
        (version.numero for version in versiones if version.estado == "VIGENTE"),
        None,
    )
    borrador_numero = next(
        (version.numero for version in versiones if version.estado == "BORRADOR"),
        None,
    )
    declaraciones = (
        db.scalars(
            select(GovernmentCashProgramDeclaration)
            .filter(GovernmentCashProgramDeclaration.program_id == str(programa.id))
            .order_by(GovernmentCashProgramDeclaration.created_at)
        )
        .all()
    )
    lineas = (
        db.scalars(
            select(GovernmentCashProgramLine)
            .filter(GovernmentCashProgramLine.version_id == str(version_mostrada.id))
            .order_by(GovernmentCashProgramLine.mes)
        )
        .all()
    )
    cuenta_ids = {str(declaracion.account_id) for declaracion in declaraciones}
    cuentas_por_id: dict[str, tuple[str, str, str]] = {}
    if cuenta_ids:
        cuentas = (
            db.execute(
                select(GovernmentBankAccount, GovernmentBank.nombre)
                .join(GovernmentBank, GovernmentBankAccount.bank_id == GovernmentBank.id)
                .filter(GovernmentBankAccount.id.in_(cuenta_ids))
            )
            .all()
        )
        for cuenta, banco_nombre in cuentas:
            cuentas_por_id[str(cuenta.id)] = (
                cuenta.codigo,
                cuenta.denominacion,
                banco_nombre,
            )
    rubro_ids = {str(linea.item_id) for linea in lineas}
    rubros_por_id: dict[str, tuple[str, str, str]] = {}
    if rubro_ids:
        rubros = (
            db.scalars(
                select(GovernmentCashItem)
                .filter(GovernmentCashItem.id.in_(rubro_ids))
            )
            .all()
        )
        for rubro in rubros:
            rubros_por_id[str(rubro.id)] = (rubro.codigo, rubro.nombre, rubro.tipo)
    historia = (
        db.scalars(
            select(GovernmentCashProgramHistory)
            .filter(GovernmentCashProgramHistory.program_id == str(programa.id))
            .order_by(GovernmentCashProgramHistory.created_at)
        )
        .all()
    )
    autor_ids: set[str | None] = set()
    autor_ids.add(programa.created_by)
    if programa.cerrado_por is not None:
        autor_ids.add(programa.cerrado_por)
    for version in versiones:
        autor_ids.add(version.created_by)
        if version.activada_por is not None:
            autor_ids.add(version.activada_por)
    for declaracion in declaraciones:
        autor_ids.add(declaracion.created_by)
    for registro in historia:
        autor_ids.add(registro.created_by)
    nombres = _usuarios_por_ids(db, autor_ids, ctx.tenant_id)

    def nombre_usuario(user_id: str | None) -> str | None:
        if user_id is None:
            return None
        return nombres.get(str(user_id))

    disponibilidad_inicial = sum(
        (declaracion.monto for declaracion in declaraciones),
        Decimal("0.00"),
    )
    meses_payload = []
    inicial = disponibilidad_inicial
    hay_deficit = False
    lineas_por_mes: dict[int, list[GovernmentCashProgramLine]] = {}
    for linea in lineas:
        lineas_por_mes.setdefault(linea.mes, []).append(linea)
    for mes in range(programa.mes_inicial, 13):
        ingresos = sum(
            (
                linea.monto
                for linea in lineas_por_mes.get(mes, [])
                if rubros_por_id.get(str(linea.item_id), ("", "", ""))[2] == "INGRESO"
            ),
            Decimal("0.00"),
        )
        desembolsos = sum(
            (
                linea.monto
                for linea in lineas_por_mes.get(mes, [])
                if rubros_por_id.get(str(linea.item_id), ("", "", ""))[2] == "DESEMBOLSO"
            ),
            Decimal("0.00"),
        )
        final = inicial + ingresos - desembolsos
        deficit = final < 0
        if deficit:
            hay_deficit = True
        meses_payload.append(
            {
                "mes": mes,
                "inicial": inicial,
                "ingresos": ingresos,
                "desembolsos": desembolsos,
                "final": final,
                "deficit": deficit,
            }
        )
        inicial = final
    return {
        "id": str(programa.id),
        "codigo": programa.codigo,
        "ejercicio": programa.ejercicio,
        "moneda": programa.moneda,
        "mes_inicial": programa.mes_inicial,
        "estado": programa.estado,
        "version": programa.version,
        "version_vista": version_mostrada.numero,
        "version_vigente": version_vigente,
        "borrador_numero": borrador_numero,
        "cerrado_por": nombre_usuario(programa.cerrado_por),
        "cerrado_en": _instante_o_nulo(programa.cerrado_en),
        "motivo_cierre": programa.motivo_cierre,
        "registrado_por": nombres.get(str(programa.created_by)),
        "registrado_en": _instante(programa.created_at),
        "declaraciones": [
            {
                "id": str(declaracion.id),
                "cuenta_id": str(declaracion.account_id),
                "cuenta_codigo": cuentas_por_id.get(str(declaracion.account_id), ("", "", ""))[0],
                "cuenta_denominacion": cuentas_por_id.get(str(declaracion.account_id), ("", "", ""))[1],
                "banco_nombre": cuentas_por_id.get(str(declaracion.account_id), ("", "", ""))[2],
                "monto": declaracion.monto,
                "fecha_corte": declaracion.fecha_corte,
                "fundamento": declaracion.fundamento,
                "declarado_por": nombres.get(str(declaracion.created_by)),
                "declarado_en": _instante(declaracion.created_at),
            }
            for declaracion in declaraciones
        ],
        "disponibilidad_inicial": disponibilidad_inicial,
        "lineas": [
            {
                "id": str(linea.id),
                "rubro_id": str(linea.item_id),
                "rubro_codigo": rubros_por_id.get(str(linea.item_id), ("", "", ""))[0],
                "rubro_nombre": rubros_por_id.get(str(linea.item_id), ("", "", ""))[1],
                "tipo": rubros_por_id.get(str(linea.item_id), ("", "", ""))[2],
                "mes": linea.mes,
                "monto": linea.monto,
            }
            for linea in sorted(
                lineas,
                key=lambda linea: (
                    linea.mes,
                    rubros_por_id.get(str(linea.item_id), ("", "", ""))[0],
                ),
            )
        ],
        "meses": meses_payload,
        "hay_deficit": hay_deficit,
        "versiones": [
            {
                "numero": version.numero,
                "estado": version.estado,
                "motivo": version.motivo,
                "activada_por": nombre_usuario(version.activada_por),
                "activada_en": _instante_o_nulo(version.activada_en),
                "registrado_por": nombres.get(str(version.created_by)),
                "registrado_en": _instante(version.created_at),
            }
            for version in versiones
        ],
        "historia": [
            {
                "version_numero": registro.version_numero,
                "tipo": registro.tipo,
                "detalle": registro.detalle,
                "registrado_por": nombres.get(str(registro.created_by)),
                "registrado_en": _instante(registro.created_at),
            }
            for registro in historia
        ],
    }


def detalle_tras_escribir(db: Session, ctx: CompanyContext, programa_id: Any) -> dict:
    programa = _programa_de_empresa(db, ctx, programa_id)
    versiones = _versiones(db, programa)
    borrador = _version_en(versiones, "BORRADOR")
    if borrador is not None:
        return detalle(db, ctx, programa_id, borrador.numero)
    return detalle(db, ctx, programa_id)


def opciones(db: Session, ctx: CompanyContext, programa_id: Any) -> dict:
    programa = _programa_de_empresa(db, ctx, programa_id)
    cuentas = (
        db.execute(
            select(GovernmentBankAccount, GovernmentBank.nombre)
            .join(GovernmentBank, GovernmentBankAccount.bank_id == GovernmentBank.id)
            .filter(
                GovernmentBankAccount.tenant_id == ctx.tenant_id,
                GovernmentBankAccount.company_id == ctx.company_id,
                GovernmentBankAccount.moneda == programa.moneda,
                GovernmentBankAccount.estado == "VIGENTE",
            )
            .order_by(GovernmentBankAccount.codigo)
        )
        .all()
    )
    rubros = (
        db.scalars(
            select(GovernmentCashItem)
            .filter(
                GovernmentCashItem.tenant_id == ctx.tenant_id,
                GovernmentCashItem.company_id == ctx.company_id,
                GovernmentCashItem.estado == "ACTIVO",
            )
            .order_by(GovernmentCashItem.codigo)
        )
        .all()
    )
    return {
        "cuentas": [
            {
                "id": str(cuenta.id),
                "codigo": cuenta.codigo,
                "denominacion": cuenta.denominacion,
                "banco_nombre": banco_nombre,
            }
            for cuenta, banco_nombre in cuentas
        ],
        "rubros": [
            {
                "id": str(rubro.id),
                "codigo": rubro.codigo,
                "nombre": rubro.nombre,
                "tipo": rubro.tipo,
            }
            for rubro in rubros
        ],
    }


def crear(db: Session, ctx: CompanyContext, datos: Any) -> GovernmentCashProgram:
    """Crea un programa financiero de caja BORRADOR con versión 1."""
    if datos.ejercicio < hoy_de_negocio().year - 1:
        raise _invalida("El ejercicio es anterior al permitido")

    codigo = f"PF-{datos.ejercicio}-{datos.moneda}"
    programa = GovernmentCashProgram(
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        codigo=codigo,
        ejercicio=datos.ejercicio,
        moneda=datos.moneda,
        mes_inicial=datos.mes_inicial,
        estado="BORRADOR",
        version=1,
        created_by=ctx.user_id,
    )
    db.add(programa)
    _guardar(db, ("GOV_CASH_PROGRAM_DUPLICATE", "Ya hay un programa de ese ejercicio y moneda"))

    version = GovernmentCashProgramVersion(
        program_id=str(programa.id),
        company_id=ctx.company_id,
        numero=1,
        estado="BORRADOR",
        motivo=None,
        created_by=ctx.user_id,
    )
    db.add(version)
    db.flush()

    _historia(db, ctx, programa, 1, "CREADO", detalle=None)
    _auditar(
        db,
        ctx,
        entidad_tipo=ENTIDAD_PROGRAMA,
        entidad_id=str(programa.id),
        accion="GOV_CASH_PROGRAM_CREATED",
        after={"codigo": programa.codigo, "ejercicio": programa.ejercicio, "moneda": programa.moneda},
    )
    return programa


def _tras_cambiar(db: Session, ctx: CompanyContext, programa: GovernmentCashProgram, numero: int, cambio: str) -> None:
    """Registra historia, auditoría y sube versión tras modificar declaraciones o líneas."""
    _historia(db, ctx, programa, numero, cambio, detalle=None)
    _auditar(
        db,
        ctx,
        entidad_tipo=ENTIDAD_PROGRAMA,
        entidad_id=str(programa.id),
        accion="GOV_CASH_PROGRAM_UPDATED",
        after={"codigo": programa.codigo, "cambio": cambio.lower(), "version_numero": numero},
    )
    programa.version += 1
    db.flush()


def declarar(db: Session, ctx: CompanyContext, programa_id: Any, version: Any, datos: Any) -> GovernmentCashProgram:
    """Declara una cuenta bancaria para la fecha de corte indicada."""
    programa = _para_escribir_programa(db, ctx, programa_id, version)
    if programa.estado != "BORRADOR":
        raise ConflictError(
            "GOV_CASH_PROGRAM_INVALID_STATE",
            "La operación solo está permitida en un programa BORRADOR",
        )

    if datos.fecha_corte > hoy_de_negocio():
        raise _invalida("La fecha de corte no puede ser futura")

    borrador = _borrador_o_error(db, programa)
    cuenta = _cuenta_declarable(db, ctx, datos.cuenta_id, programa.moneda)
    declaracion = GovernmentCashProgramDeclaration(
        program_id=str(programa.id),
        company_id=ctx.company_id,
        account_id=str(cuenta.id),
        monto=datos.monto,
        fecha_corte=datos.fecha_corte,
        fundamento=datos.fundamento,
        created_by=ctx.user_id,
    )
    db.add(declaracion)
    _guardar(db, ("GOV_CASH_DECLARATION_DUPLICATE", "Esa cuenta ya está declarada"))

    _tras_cambiar(db, ctx, programa, borrador.numero, "DECLARACION")
    return programa


def quitar_declaracion(db: Session, ctx: CompanyContext, programa_id: Any, declaracion_id: Any, version: Any) -> GovernmentCashProgram:
    """Elimina la declaración indicada del programa."""
    programa = _para_escribir_programa(db, ctx, programa_id, version)
    if programa.estado != "BORRADOR":
        raise ConflictError(
            "GOV_CASH_PROGRAM_INVALID_STATE",
            "La operación solo está permitida en un programa BORRADOR",
        )

    borrador = _borrador_o_error(db, programa)
    declaracion = db.scalar(
        select(GovernmentCashProgramDeclaration).where(
            GovernmentCashProgramDeclaration.id == declaracion_id,
            GovernmentCashProgramDeclaration.program_id == str(programa.id),
            GovernmentCashProgramDeclaration.company_id == ctx.company_id,
        )
    )
    if declaracion is None:
        raise NotFoundError("GOV_CASH_DECLARATION_NOT_FOUND", "La declaración no existe en este programa")

    db.delete(declaracion)
    _tras_cambiar(db, ctx, programa, borrador.numero, "DECLARACION")
    return programa


def agregar_linea(db: Session, ctx: CompanyContext, programa_id: Any, version: Any, datos: Any) -> GovernmentCashProgram:
    """Agrega una línea de rubro a la versión borrador."""
    programa = _para_escribir_programa(db, ctx, programa_id, version)
    borrador = _borrador_o_error(db, programa)
    _validar_mes(programa, borrador, datos.mes)
    rubro = _rubro_utilizable(db, ctx, datos.rubro_id)

    linea = GovernmentCashProgramLine(
        version_id=str(borrador.id),
        company_id=ctx.company_id,
        item_id=str(rubro.id),
        mes=datos.mes,
        monto=datos.monto,
        created_by=ctx.user_id,
    )
    db.add(linea)
    _guardar(db, ("GOV_CASH_LINE_DUPLICATE", "Ya hay una línea de ese rubro en ese mes"))

    _tras_cambiar(db, ctx, programa, borrador.numero, "LINEA")
    return programa


def _linea_del_borrador(db: Session, ctx: CompanyContext, version: GovernmentCashProgramVersion, linea_id: Any) -> GovernmentCashProgramLine:
    """Obtiene una línea de la versión borrador actual."""
    linea = db.scalar(
        select(GovernmentCashProgramLine).where(
            GovernmentCashProgramLine.id == linea_id,
            GovernmentCashProgramLine.version_id == str(version.id),
            GovernmentCashProgramLine.company_id == ctx.company_id,
        )
    )
    if linea is None:
        raise NotFoundError("GOV_CASH_LINE_NOT_FOUND", "La línea no existe en este programa")
    return linea


def cambiar_linea(db: Session, ctx: CompanyContext, programa_id: Any, linea_id: Any, version: Any, datos: Any) -> GovernmentCashProgram:
    """Actualiza el monto de una línea existente."""
    programa = _para_escribir_programa(db, ctx, programa_id, version)
    borrador = _borrador_o_error(db, programa)
    linea = _linea_del_borrador(db, ctx, borrador, linea_id)
    _validar_mes(programa, borrador, linea.mes)
    linea.monto = datos.monto
    _tras_cambiar(db, ctx, programa, borrador.numero, "LINEA")
    return programa


def quitar_linea(db: Session, ctx: CompanyContext, programa_id: Any, linea_id: Any, version: Any) -> GovernmentCashProgram:
    """Elimina una línea de la versión borrador."""
    programa = _para_escribir_programa(db, ctx, programa_id, version)
    borrador = _borrador_o_error(db, programa)
    linea = _linea_del_borrador(db, ctx, borrador, linea_id)
    _validar_mes(programa, borrador, linea.mes)
    db.delete(linea)
    _tras_cambiar(db, ctx, programa, borrador.numero, "LINEA")
    return programa


def activar(db: Session, ctx: CompanyContext, programa_id: Any, version: Any) -> GovernmentCashProgram:
    programa = _para_escribir_programa(db, ctx, programa_id, version)
    versiones = _versiones(db, programa)
    borrador = _borrador_o_error(db, programa)
    declaraciones_count = db.scalar(
        select(func.count())
        .select_from(GovernmentCashProgramDeclaration)
        .where(GovernmentCashProgramDeclaration.program_id == str(programa.id))
    )
    lineas_count = db.scalar(
        select(func.count())
        .select_from(GovernmentCashProgramLine)
        .where(GovernmentCashProgramLine.version_id == str(borrador.id))
    )
    faltan = []
    if not declaraciones_count:
        faltan.append("declaracion")
    if not lineas_count:
        faltan.append("linea")
    if faltan:
        raise ConflictError(
            "GOV_CASH_PROGRAM_NOT_READY",
            "El programa no está listo para activarse",
            details={"faltan": faltan},
        )
    evaluar_antes_de_actuar(db, ctx, "TRE02_ACTIVAR", ENTIDAD_PROGRAMA, str(programa.id))
    version_vigente = _version_en(versiones, "VIGENTE")
    if version_vigente is not None:
        version_vigente.estado = "SUPERADA"
        db.flush()
    borrador.estado = "VIGENTE"
    borrador.activada_por = ctx.user_id
    borrador.activada_en = datetime.now(UTC)
    programa.estado = "VIGENTE"
    programa.version += 1
    _historia(db, ctx, programa, borrador.numero, "ACTIVADO", None)
    db.flush()
    _auditar(
        db,
        ctx,
        ENTIDAD_PROGRAMA,
        str(programa.id),
        "GOV_CASH_PROGRAM_ACTIVATED",
        {"codigo": programa.codigo, "version_numero": borrador.numero},
    )
    return programa


def reprogramar(
    db: Session,
    ctx: CompanyContext,
    programa_id: Any,
    version: Any,
    datos: Any,
) -> GovernmentCashProgram:
    programa = _para_escribir_programa(db, ctx, programa_id, version)
    if programa.estado != "VIGENTE":
        raise ConflictError(
            "GOV_CASH_PROGRAM_INVALID_STATE",
            "El programa no está vigente",
        )
    versiones = _versiones(db, programa)
    if _version_en(versiones, "BORRADOR") is not None:
        raise ConflictError(
            "GOV_CASH_PROGRAM_DRAFT_OPEN",
            "Ya hay una reprogramación abierta",
        )
    version_vigente = _vigente_o_error(versiones)
    if programa.ejercicio < hoy_de_negocio().year:
        raise ConflictError(
            "GOV_CASH_PROGRAM_EXERCISE_ENDED",
            "El ejercicio del programa ya terminó",
        )
    evaluar_antes_de_actuar(db, ctx, "TRE02_REPROGRAMAR", ENTIDAD_PROGRAMA, str(programa.id))
    numero_nuevo = max(version_.numero for version_ in versiones) + 1
    version_nueva = GovernmentCashProgramVersion(
        program_id=str(programa.id),
        company_id=ctx.company_id,
        numero=numero_nuevo,
        estado="BORRADOR",
        motivo=datos.motivo,
        created_by=ctx.user_id,
    )
    db.add(version_nueva)
    _guardar(db, ("GOV_CASH_PROGRAM_DRAFT_OPEN", "Ya hay una reprogramación abierta"))
    for linea in db.scalars(
        select(GovernmentCashProgramLine).where(
            GovernmentCashProgramLine.version_id == str(version_vigente.id)
        )
    ).all():
        db.add(
            GovernmentCashProgramLine(
                version_id=str(version_nueva.id),
                company_id=ctx.company_id,
                item_id=str(linea.item_id),
                mes=linea.mes,
                monto=linea.monto,
                created_by=ctx.user_id,
            )
        )
    programa.version += 1
    _historia(
        db,
        ctx,
        programa,
        numero_nuevo,
        "REPROGRAMADO",
        {"motivo": datos.motivo},
    )
    db.flush()
    _auditar(
        db,
        ctx,
        ENTIDAD_PROGRAMA,
        str(programa.id),
        "GOV_CASH_PROGRAM_REVISED",
        {
            "codigo": programa.codigo,
            "motivo": datos.motivo,
            "version_numero": numero_nuevo,
        },
    )
    return programa


def descartar(db: Session, ctx: CompanyContext, programa_id: Any, version: Any) -> GovernmentCashProgram:
    programa = _para_escribir_programa(db, ctx, programa_id, version)
    borrador = _borrador_o_error(db, programa)
    borrador.estado = "DESCARTADA"
    if borrador.numero == 1:
        programa.estado = "DESCARTADO"
    programa.version += 1
    _historia(db, ctx, programa, borrador.numero, "DESCARTADO", None)
    db.flush()
    _auditar(
        db,
        ctx,
        ENTIDAD_PROGRAMA,
        str(programa.id),
        "GOV_CASH_PROGRAM_DISCARDED",
        {"codigo": programa.codigo, "version_numero": borrador.numero},
    )
    return programa


def cerrar(
    db: Session,
    ctx: CompanyContext,
    programa_id: Any,
    version: Any,
    datos: Any,
) -> GovernmentCashProgram:
    programa = _para_escribir_programa(db, ctx, programa_id, version)
    if programa.estado != "VIGENTE":
        raise ConflictError(
            "GOV_CASH_PROGRAM_INVALID_STATE",
            "El programa no está vigente",
        )
    versiones = _versiones(db, programa)
    if _version_en(versiones, "BORRADOR") is not None:
        raise ConflictError(
            "GOV_CASH_PROGRAM_DRAFT_OPEN",
            "Ya hay una reprogramación abierta",
        )
    evaluar_antes_de_actuar(db, ctx, "TRE02_CERRAR", ENTIDAD_PROGRAMA, str(programa.id))
    evaluar_cierre(db, ctx, "TRE02_CERRAR_PROGRAMA", ENTIDAD_PROGRAMA, str(programa.id), programa.codigo, programa.ejercicio)
    version_vigente = _vigente_o_error(versiones)
    version_vigente.estado = "CERRADA"
    programa.estado = "CERRADO"
    programa.cerrado_por = ctx.user_id
    programa.cerrado_en = datetime.now(UTC)
    programa.motivo_cierre = datos.motivo
    programa.version += 1
    _historia(
        db,
        ctx,
        programa,
        version_vigente.numero,
        "CERRADO",
        {"motivo": datos.motivo},
    )
    db.flush()
    _auditar(
        db,
        ctx,
        ENTIDAD_PROGRAMA,
        str(programa.id),
        "GOV_CASH_PROGRAM_CLOSED",
        {"codigo": programa.codigo, "motivo": datos.motivo},
    )
    return programa
