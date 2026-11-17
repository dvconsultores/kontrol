"""Supervisor o responsable del contrato (CNT-04, GOV-CNT-004)."""
from datetime import date, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext
from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.core.integrity import es_violacion_unica
from app.modules.government.models import (
    GovernmentAct,
    GovernmentContract,
    GovernmentContractSupervisorAssignment,
    GovernmentOfficial,
    GovernmentPosition,
    GovernmentProcurementFile,
    GovernmentUnit,
)
from app.modules.government.service_actos import _autoridad_valida
from app.modules.government.service_contratos_terminos import terminos_efectivos
from app.modules.government.service_expedientes import _evento
from app.modules.government.service_identidad import exigir_autoridad_funcional
from app.modules.government.service_ocupacion import FIGURAS, enmascarar_documento, ocupaciones_de_funcionario
from app.modules.government.service_sod import evaluar_antes_de_actuar
from app.modules.government.situacion_contractual import exigir_vigente_en
from app.shared.audit import record_audit, record_audit_after_rollback
from app.shared.clock import hoy_de_negocio, instante_actual

ENTIDAD = "GovernmentProcurementFile"
ETIQUETA_ESTADO = {"VIGENTE": "Vigente", "SUSTITUIDA": "Sustituida"}
ETIQUETA_TIPO_ACTO = {
    "DECRETO": "Decreto",
    "RESOLUCION": "Resolución",
    "ORDEN": "Orden",
    "PROVIDENCIA": "Providencia",
    "INSTRUCCION": "Instrucción",
    "CIRCULAR": "Circular",
}


def _inv(campo: str, mensaje: str, code: str) -> KontrolError:
    return KontrolError(code, "Datos de la designación inválidos", field_errors={campo: [mensaje]}, status_code=422)


def _etiqueta_acto(acto: GovernmentAct) -> str:
    tipo = ETIQUETA_TIPO_ACTO.get(acto.tipo)
    if tipo is None:
        tipo = acto.denominacion_tipo or "Decisión"
    return f"{tipo} N.º {acto.numero} del {acto.fecha:%d/%m/%Y}"


def _contrato(db: Session, ctx: CompanyContext, contrato_id: str, bloquear: bool) -> GovernmentContract:
    consulta = select(GovernmentContract).where(
        GovernmentContract.id == contrato_id,
        GovernmentContract.company_id == ctx.company_id,
    )
    if bloquear:
        consulta = consulta.with_for_update()
    contrato = db.execute(consulta).scalar_one_or_none()
    if contrato is None:
        raise NotFoundError("GOV_CONTRACT_NOT_FOUND", "Contrato u orden no encontrado")
    return contrato


def _vigente(db: Session, contrato_id: str, bloquear: bool) -> GovernmentContractSupervisorAssignment | None:
    consulta = select(GovernmentContractSupervisorAssignment).where(
        GovernmentContractSupervisorAssignment.contract_id == contrato_id,
        GovernmentContractSupervisorAssignment.estado == "VIGENTE",
    )
    if bloquear:
        consulta = consulta.with_for_update()
    return db.execute(consulta).scalar_one_or_none()


def _ocupacion_valida(db: Session, ctx: CompanyContext, official_id: str, asignacion_id: str, fecha: date) -> dict[str, Any] | None:
    for ocupacion in ocupaciones_de_funcionario(db, ctx, official_id, fecha):
        if ocupacion["id"] != asignacion_id:
            continue
        if ocupacion["situacion"] != "VIGENTE":
            return None
        figura = ocupacion.get("figura")
        if not figura or FIGURAS.get(figura, {}).get("grupo") == "DELEGACION":
            return None
        if not ocupacion.get("cargo"):
            return None
        return ocupacion
    return None


def _acto_valido(db: Session, acto: GovernmentAct, desde: date) -> bool:
    return acto.status == "EFICAZ" and acto.fecha_eficacia is not None and acto.fecha_eficacia <= desde


def _bloqueo(db: Session, ctx: CompanyContext, contrato: GovernmentContract, causal: str, campos: dict[str, Any]) -> None:
    after = {"contrato": contrato.codigo, "causal": causal}
    after.update({clave: valor for clave, valor in campos.items() if valor is not None})
    record_audit_after_rollback(
        db,
        action="GOV_CONTRACT_SUPERVISOR_BLOCKED",
        entity_type=ENTIDAD,
        entity_id=contrato.file_id,
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after=after,
    )


def _referencia(db: Session, designacion_id: str | None) -> str | None:
    if designacion_id is None:
        return None
    numero = db.scalar(
        select(GovernmentContractSupervisorAssignment.numero).where(
            GovernmentContractSupervisorAssignment.id == designacion_id
        )
    )
    return f"SUP-{numero:02d}" if numero is not None else None


def _item(db: Session, asignacion: GovernmentContractSupervisorAssignment, hoy: date) -> dict[str, Any]:
    situacion = "PROGRAMADA" if asignacion.desde > hoy else "CONCLUIDA" if asignacion.hasta is not None and asignacion.hasta < hoy else "EN_EJERCICIO"
    return {
        "id": asignacion.id,
        "situacion": situacion,
        "situacion_etiqueta": {"EN_EJERCICIO": "En ejercicio", "PROGRAMADA": "Programada", "CONCLUIDA": "Concluida"}[situacion],
        "referencia": f"SUP-{asignacion.numero:02d}",
        "numero": asignacion.numero,
        "estado": asignacion.estado,
        "estado_etiqueta": ETIQUETA_ESTADO.get(asignacion.estado, asignacion.estado),
        "funcionario": {
            "id": asignacion.official_id,
            "nombre": asignacion.funcionario_nombre,
            "documento": asignacion.funcionario_documento,
        },
        "asignacion_id": asignacion.assignment_id,
        "figura": asignacion.figura,
        "figura_etiqueta": FIGURAS.get(asignacion.figura, {}).get("etiqueta", asignacion.figura),
        "cargo": {
            "id": asignacion.position_id,
            "codigo": asignacion.cargo_codigo,
            "nombre": asignacion.cargo_nombre,
        },
        "unidad": {
            "id": asignacion.unit_id,
            "nombre": asignacion.unidad_nombre,
        },
        "acto": {
            "id": asignacion.act_id,
            "etiqueta": asignacion.acto_etiqueta,
            "emisor_cargo": asignacion.acto_emisor_cargo,
        },
        "desde": asignacion.desde.isoformat(),
        "hasta": asignacion.hasta.isoformat() if asignacion.hasta else None,
        "motivo": asignacion.motivo,
        "sustituye": _referencia(db, asignacion.sustituye_id),
        "registrado_en": asignacion.registrado_en.isoformat(),
    }


def supervisor_en(db: Session, ctx: CompanyContext, contrato_id: str, fecha: date) -> dict[str, Any] | None:
    _contrato(db, ctx, contrato_id, bloquear=False)
    consulta = select(GovernmentContractSupervisorAssignment).where(
        GovernmentContractSupervisorAssignment.contract_id == contrato_id,
        GovernmentContractSupervisorAssignment.desde <= fecha,
        (
            (GovernmentContractSupervisorAssignment.hasta.is_(None))
            | (GovernmentContractSupervisorAssignment.hasta >= fecha)
        ),
    ).order_by(GovernmentContractSupervisorAssignment.numero.desc())
    asignacion = db.execute(consulta).scalars().first()
    return _item(db, asignacion, hoy_de_negocio()) if asignacion else None


def supervisor_vigente(db: Session, ctx: CompanyContext, contrato_id: str) -> dict[str, Any] | None:
    return supervisor_en(db, ctx, contrato_id, hoy_de_negocio())


def supervision(db: Session, ctx: CompanyContext, contrato_id: str) -> dict[str, Any]:
    contrato = _contrato(db, ctx, contrato_id, bloquear=False)
    historia = db.execute(
        select(GovernmentContractSupervisorAssignment)
        .where(GovernmentContractSupervisorAssignment.contract_id == contrato_id)
        .order_by(GovernmentContractSupervisorAssignment.numero.desc())
    ).scalars().all()
    hoy = hoy_de_negocio()
    plazo = terminos_efectivos(db, contrato, hoy)
    return {
        "contrato": {
            "id": str(contrato.id),
            "codigo": contrato.codigo,
            "estado": contrato.estado,
            "fecha_formalizacion": contrato.fecha_formalizacion.isoformat() if contrato.fecha_formalizacion else None,
            "fecha_fin_original": contrato.fecha_fin.isoformat() if contrato.fecha_fin else None,
            "fecha_fin_vigente": plazo["fecha_fin"].isoformat() if plazo["fecha_fin"] else None,
            "fuente_plazo": plazo["fuente"],
            "modificacion_plazo": plazo["modificacion"],
        },
        "vigente": supervisor_vigente(db, ctx, str(contrato.id)),
        "programada": next((_item(db, item, hoy) for item in historia if item.estado == "VIGENTE" and item.desde > hoy), None),
        "ultima_id": next((item.id for item in historia if item.estado == "VIGENTE"), None),
        "historia": [_item(db, item, hoy) for item in historia],
        "puede_designar": contrato.estado == "FORMALIZADO",
    }


def opciones(db: Session, ctx: CompanyContext, contrato_id: str, fecha: date) -> dict[str, Any]:
    _contrato(db, ctx, contrato_id, bloquear=False)
    vigente = _vigente(db, contrato_id, bloquear=False)
    hoy = hoy_de_negocio()

    funcionarios = db.execute(
        select(GovernmentOfficial)
        .where(
            GovernmentOfficial.company_id == ctx.company_id,
            GovernmentOfficial.estado == "ACTIVO",
        )
        .order_by(GovernmentOfficial.nombre)
    ).scalars().all()

    funcionarios_validos: list[dict[str, Any]] = []
    for funcionario in funcionarios:
        ocupaciones_fecha = ocupaciones_de_funcionario(db, ctx, str(funcionario.id), fecha)
        ocupaciones_hoy = ocupaciones_de_funcionario(db, ctx, str(funcionario.id), hoy)
        ocupaciones_validas: list[dict[str, Any]] = []
        ids_hoy = {ocupacion["id"] for ocupacion in ocupaciones_hoy if ocupacion["situacion"] == "VIGENTE"}
        for ocupacion in ocupaciones_fecha:
            if ocupacion["id"] not in ids_hoy:
                continue
            if ocupacion["situacion"] != "VIGENTE":
                continue
            figura = ocupacion.get("figura")
            if not figura or FIGURAS.get(figura, {}).get("grupo") == "DELEGACION":
                continue
            cargo_info = ocupacion.get("cargo")
            if not cargo_info:
                continue
            ocupaciones_validas.append(
                {
                    "asignacion_id": ocupacion["id"],
                    "figura_etiqueta": ocupacion.get("figura_etiqueta", figura),
                    "cargo_id": cargo_info["id"],
                    "cargo": cargo_info["nombre"],
                    "unidad_id": cargo_info.get("unidad_id"),
                    "unidad": cargo_info.get("unidad"),
                }
            )
        if ocupaciones_validas:
            funcionarios_validos.append(
                {
                    "id": str(funcionario.id),
                    "nombre": funcionario.nombre,
                    "documento": enmascarar_documento(funcionario.tipo_documento, funcionario.numero_documento),
                    "ocupaciones": ocupaciones_validas,
                }
            )

    actos_query = select(GovernmentAct).where(
        GovernmentAct.company_id == ctx.company_id,
        GovernmentAct.status == "EFICAZ",
        GovernmentAct.fecha_eficacia.is_not(None),
        GovernmentAct.fecha_eficacia <= fecha,
    )
    actos = db.execute(actos_query.order_by(GovernmentAct.fecha.desc())).scalars().all()
    actos_validos: list[dict[str, Any]] = []
    for acto in actos:
        if not _autoridad_valida(db, ctx.company_id, str(acto.cargo_id), acto.fecha, "APROBAR", "CONTRATACIONES"):
            continue
        actos_validos.append(
            {
                "id": str(acto.id),
                "etiqueta": _etiqueta_acto(acto),
                "emisor_cargo": db.execute(
                    select(GovernmentPosition.name).where(GovernmentPosition.id == acto.cargo_id)
                ).scalar_one_or_none()
                or "",
                "fecha": acto.fecha.isoformat(),
                "fecha_eficacia": acto.fecha_eficacia.isoformat() if acto.fecha_eficacia else None,
            }
        )

    return {
        "fecha": fecha.isoformat(),
        "vigente_id": str(vigente.id) if vigente else None,
        "funcionarios": funcionarios_validos,
        "actos": actos_validos,
    }


def designar(db: Session, ctx: CompanyContext, contrato_id: str, cuerpo: dict[str, Any]) -> dict[str, Any]:
    contrato = _contrato(db, ctx, contrato_id, bloquear=True)
    if contrato.estado != "FORMALIZADO":
        raise ConflictError("GOV_CONTRACT_SUPERVISOR_CONTRACT_NOT_FORMALIZED", "Solo un contrato formalizado admite supervisor")

    vigente = _vigente(db, str(contrato.id), bloquear=True)
    sustituye_id = cuerpo.get("sustituye_id")
    if (sustituye_id or None) != (str(vigente.id) if vigente else None):
        raise ConflictError(
            "GOV_CONTRACT_SUPERVISOR_STALE",
            "La supervisión del contrato cambió: recargue la ficha",
            details={"vigente_id": str(vigente.id) if vigente else None},
        )

    if contrato.fecha_formalizacion is None or contrato.fecha_inicio is None:
        raise ConflictError(
            "GOV_CONTRACT_SUPERVISOR_CONTRACT_NOT_FORMALIZED",
            "Solo un contrato formalizado admite supervisor",
        )
    hoy = hoy_de_negocio()
    minimo: date = min(contrato.fecha_inicio, contrato.fecha_formalizacion)
    if vigente:
        minimo = max(minimo, vigente.desde + timedelta(days=1))
    desde = cuerpo["desde"]
    fin_vigente = terminos_efectivos(db, contrato, desde)["fecha_fin"]
    maximo: date = fin_vigente if fin_vigente else hoy
    if desde < minimo or desde > maximo:
        raise _inv("desde", f"La fecha efectiva debe estar entre el {minimo:%d/%m/%Y} y el {maximo:%d/%m/%Y}", "GOV_CONTRACT_SUPERVISOR_DATE_INVALID")
    exigir_vigente_en(db, ctx.company_id, str(contrato.id), desde)

    motivo = cuerpo.get("motivo")
    if vigente:
        if not motivo or not motivo.strip():
            raise _inv("motivo", "Indique el motivo del cambio", "GOV_CONTRACT_SUPERVISOR_REASON_REQUIRED")
        motivo = motivo.strip()
    else:
        motivo = None

    funcionario = db.execute(
        select(GovernmentOfficial).where(
            GovernmentOfficial.id == cuerpo["funcionario_id"],
            GovernmentOfficial.company_id == ctx.company_id,
            GovernmentOfficial.estado == "ACTIVO",
        )
    ).scalar_one_or_none()
    if funcionario is None:
        raise _inv("funcionario_id", "Elija un funcionario activo del ente", "GOV_CONTRACT_SUPERVISOR_OFFICIAL_INVALID")

    ocupacion = _ocupacion_valida(db, ctx, str(funcionario.id), cuerpo["asignacion_id"], desde)
    ocupacion_hoy = _ocupacion_valida(db, ctx, str(funcionario.id), cuerpo["asignacion_id"], hoy)
    if ocupacion is None or ocupacion_hoy is None:
        _bloqueo(db, ctx, contrato, "GOV_CONTRACT_SUPERVISOR_OCCUPATION_INVALID", {"supervisor": funcionario.nombre})
        raise _inv("asignacion_id", "El funcionario no ejerce esa ocupación en la fecha efectiva", "GOV_CONTRACT_SUPERVISOR_OCCUPATION_INVALID")

    acto = db.execute(
        select(GovernmentAct).where(
            GovernmentAct.id == cuerpo["acto_id"],
            GovernmentAct.company_id == ctx.company_id,
        )
    ).scalar_one_or_none()
    if acto is None or not _acto_valido(db, acto, desde):
        _bloqueo(db, ctx, contrato, "GOV_CONTRACT_SUPERVISOR_ACT_INVALID", {})
        raise _inv("acto_id", "El acto de designación debe estar eficaz en la fecha efectiva", "GOV_CONTRACT_SUPERVISOR_ACT_INVALID")

    if vigente and acto.id == vigente.act_id:
        raise _inv("acto_id", "La sustitución requiere un acto de designación nuevo", "GOV_CONTRACT_SUPERVISOR_ACT_REUSED")

    if not _autoridad_valida(db, ctx.company_id, str(acto.cargo_id), acto.fecha, "APROBAR", "CONTRATACIONES"):
        _bloqueo(db, ctx, contrato, "GOV_CONTRACT_SUPERVISOR_ACT_AUTHORITY_INVALID", {"acto": _etiqueta_acto(acto)})
        raise _inv(
            "acto_id",
            "El cargo que emitió el acto no tenía la competencia Aprobar sobre Contrataciones",
            "GOV_CONTRACT_SUPERVISOR_ACT_AUTHORITY_INVALID",
        )

    exigir_autoridad_funcional(db, ctx, str(acto.cargo_id), "APROBAR", "CONTRATACIONES")

    accion_sod = "PROC03_SUPERVISOR_SUSTITUIR" if vigente else "PROC03_SUPERVISOR_DESIGNAR"
    evaluar_antes_de_actuar(db, ctx, accion_sod, ENTIDAD, str(contrato.file_id))

    cargo = db.execute(select(GovernmentPosition).where(GovernmentPosition.id == ocupacion["cargo"]["id"])).scalar_one()
    unidad = db.execute(select(GovernmentUnit).where(GovernmentUnit.id == cargo.unit_id)).scalar_one_or_none()
    emisor = db.execute(select(GovernmentPosition).where(GovernmentPosition.id == acto.cargo_id)).scalar_one_or_none()

    numero = db.execute(
        select(func.max(GovernmentContractSupervisorAssignment.numero)).where(
            GovernmentContractSupervisorAssignment.contract_id == str(contrato.id)
        )
    ).scalar_one()
    numero = (numero or 0) + 1

    nuevo_id = str(uuid4())

    if vigente:
        vigente.estado = "SUSTITUIDA"
        vigente.hasta = desde - timedelta(days=1)
        vigente.sustituida_por_id = nuevo_id
        vigente.version += 1
        db.flush()

    nuevo = GovernmentContractSupervisorAssignment(
        id=nuevo_id,
        company_id=ctx.company_id,
        contract_id=str(contrato.id),
        numero=numero,
        estado="VIGENTE",
        official_id=str(funcionario.id),
        assignment_id=cuerpo["asignacion_id"],
        position_id=str(cargo.id),
        unit_id=str(cargo.unit_id),
        act_id=str(acto.id),
        funcionario_nombre=funcionario.nombre,
        funcionario_documento=enmascarar_documento(funcionario.tipo_documento, funcionario.numero_documento),
        figura=ocupacion["figura"],
        cargo_codigo=cargo.code,
        cargo_nombre=cargo.name,
        unidad_nombre=unidad.name if unidad else "",
        acto_etiqueta=_etiqueta_acto(acto),
        acto_emisor_cargo=emisor.name if emisor else "",
        desde=desde,
        hasta=None,
        motivo=motivo,
        sustituye_id=str(vigente.id) if vigente else None,
        registrado_en=instante_actual(),
        registrado_por=ctx.user_id,
        created_by=ctx.user_id,
    )
    db.add(nuevo)
    try:
        db.flush()
    except IntegrityError as error:
        if es_violacion_unica(error, "uq_gov_contract_supervisors_vigente") or es_violacion_unica(
            error, "uq_gov_contract_supervisors_numero"
        ):
            db.rollback()
            raise ConflictError(
                "GOV_CONTRACT_SUPERVISOR_CONFLICT", "Otra designación se registró al mismo tiempo: recargue la ficha"
            ) from error
        raise

    expediente = db.execute(
        select(GovernmentProcurementFile)
        .where(
            GovernmentProcurementFile.id == contrato.file_id,
            GovernmentProcurementFile.company_id == ctx.company_id,
        )
        .with_for_update()
    ).scalar_one()
    expediente.version += 1
    _evento(
        db,
        ctx,
        expediente,
        "CONTRATO",
        desde,
        f"Supervisor de {contrato.codigo}: {funcionario.nombre}",
        detalle=f"{cargo.name} · {unidad.name if unidad else ''} · {nuevo.acto_etiqueta}",
    )

    after = {
        "contrato": contrato.codigo,
        "designacion": f"SUP-{numero:02d}",
        "supervisor": funcionario.nombre,
        "cargo": cargo.name,
        "unidad": unidad.name if unidad else "",
        "acto": nuevo.acto_etiqueta,
        "desde": desde.isoformat(),
        "sustituye": f"SUP-{vigente.numero:02d}" if vigente else None,
        "motivo": motivo,
    }
    record_audit(
        db,
        action="GOV_CONTRACT_SUPERVISOR_REPLACED" if vigente else "GOV_CONTRACT_SUPERVISOR_ASSIGNED",
        entity_type=ENTIDAD,
        entity_id=str(contrato.file_id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={clave: valor for clave, valor in after.items() if valor is not None},
    )

    return supervision(db, ctx, str(contrato.id))
