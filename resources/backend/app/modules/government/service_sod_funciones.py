"""Funciones incompatibles del procedimiento de contratación (PROC-11, GOV-PROC-017).

CTL-01 responde «¿este actor puede hacer B después de haber hecho A sobre este objeto?» y prueba A con la
bitácora. Aquí la pregunta es otra: «¿la misma persona ocupa dos funciones que la institución declara
incompatibles en este expediente?», y la prueba son los registros del expediente, no los eventos. Se reutiliza
la capacidad, la equivalencia de actor de ORG-06 y el patrón de ciclo de vida; no se duplica el motor de CTL-01.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext
from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.government.models import (
    GovernmentProcurementCommitteeMember,
    GovernmentProcurementDecision,
    GovernmentProcurementEvalResult,
    GovernmentProcurementFile,
    GovernmentProcurementFileResponsible,
    GovernmentProcurementOffer,
    GovernmentProcurementOpening,
    GovernmentProcurementOpeningAttendee,
    GovernmentProcurementRecommendation,
    GovernmentProcurementRecommendationSignatory,
    GovernmentSoDRoleRule,
    GovernmentSoDRoleRuleHistory,
    GovernmentUserOfficialLink,
)
from app.modules.government.service_sod import usuarios_equivalentes
from app.modules.identity_access.models import User
from app.shared.audit import record_audit, record_audit_after_rollback
from app.shared.clock import hoy_de_negocio

ENTIDAD_REGLA = "GovernmentSoDRoleRule"
ENTIDAD_EXPEDIENTE = "GovernmentProcurementFile"
CONFLICTO_ACCION = "GOV_SOD_ROLE_CONFLICT_BLOCKED"
PROCESO = "PROC-03"

#: Catálogo cerrado de funciones. `disponible=False` se publica con su requisito habilitante y no se puede usar
#: en la matriz: preferimos decir «no existe» a inventar una función que el producto no puede ejercer.
FUNCIONES: dict[str, dict[str, Any]] = {
    "SOLICITANTE": {
        "etiqueta": "Solicitante (registra el expediente y el requiriente)",
        "fuente": "Expediente y responsables REQUIRENTE (PROC-03)",
        "disponible": True,
        "requisito": None,
    },
    "RECEPTOR": {
        "etiqueta": "Receptor de ofertas",
        "fuente": "Recepción de ofertas: funcionario receptor y usuario que la registra (PROC-06)",
        "disponible": True,
        "requisito": None,
    },
    "EVALUADOR": {
        "etiqueta": "Evaluador (comisión, apertura, aportes y recomendación)",
        "fuente": "Comisión vinculada, apertura, aportes de evaluación y recomendación (PROC-02/07/08)",
        "disponible": True,
        "requisito": None,
    },
    "ADJUDICADOR": {
        "etiqueta": "Adjudicador (decide el resultado)",
        "fuente": "Decisiones del procedimiento (PROC-08)",
        "disponible": True,
        "requisito": None,
    },
    "PAGADOR": {
        "etiqueta": "Pagador",
        "fuente": "No disponible en Gobierno",
        "disponible": False,
        "requisito": "GOV-TRE-004 (TRE-04): el pago no existe en Gobierno",
    },
}

FUNCIONES_DISPONIBLES = tuple(clave for clave, datos in FUNCIONES.items() if datos["disponible"])


def _invalida(mensaje: str) -> KontrolError:
    return KontrolError(code="GOV_SOD_ROLE_RULE_INVALID", message=mensaje, status_code=422)


def etiqueta_de_funcion(rol: str | None) -> str | None:
    if rol is None:
        return None
    datos = FUNCIONES.get(rol)
    return datos["etiqueta"] if datos else rol


def catalogo() -> dict[str, Any]:
    return {
        "proceso": PROCESO,
        "funciones": [
            {
                "codigo": clave,
                "etiqueta": datos["etiqueta"],
                "fuente": datos["fuente"],
                "disponible": datos["disponible"],
                "requisito_habilitante": datos["requisito"],
            }
            for clave, datos in FUNCIONES.items()
        ],
    }


# --------------------------------------------------------------------------- #
# Matriz institucional: ciclo de vida
# --------------------------------------------------------------------------- #
def _regla_de_empresa(db: Session, ctx: CompanyContext, regla_id: str, bloquear: bool = False) -> GovernmentSoDRoleRule:
    consulta = select(GovernmentSoDRoleRule).where(
        GovernmentSoDRoleRule.id == regla_id,
        GovernmentSoDRoleRule.tenant_id == ctx.tenant_id,
        GovernmentSoDRoleRule.company_id == ctx.company_id,
    )
    if bloquear:
        consulta = consulta.with_for_update()
    regla = db.execute(consulta).scalar_one_or_none()
    if regla is None:
        raise NotFoundError("GOV_SOD_ROLE_RULE_NOT_FOUND", "La regla de funciones no existe en este ente")
    return regla


def _para_escribir(db: Session, ctx: CompanyContext, regla_id: str, version: int | None) -> GovernmentSoDRoleRule:
    if version is None:
        raise KontrolError(
            code="GOV_SOD_IF_MATCH_REQUIRED",
            message="Falta la cabecera If-Match con la versión de la regla",
            status_code=428,
        )
    regla = _regla_de_empresa(db, ctx, regla_id, bloquear=True)
    if regla.version != version:
        raise ConflictError(
            "GOV_SOD_ROLE_RULE_STALE",
            "La regla cambió desde que la abrió; recárguela",
            details={"version_actual": regla.version},
        )
    return regla


def _exigir_estado(regla: GovernmentSoDRoleRule, estado: str) -> None:
    if regla.estado != estado:
        raise ConflictError("GOV_SOD_ROLE_RULE_INVALID_STATE", f"La regla debe estar en estado {estado}")


def _historia(db: Session, ctx: CompanyContext, regla: GovernmentSoDRoleRule, tipo: str,
              detalle: dict | None = None) -> None:
    db.add(
        GovernmentSoDRoleRuleHistory(
            rule_id=str(regla.id),
            company_id=ctx.company_id,
            tipo=tipo,
            detalle=detalle,
            created_by=ctx.user_id,
        )
    )


def _auditar(db: Session, ctx: CompanyContext, regla: GovernmentSoDRoleRule, accion: str, after: dict) -> None:
    record_audit(
        db,
        action=accion,
        entity_type=ENTIDAD_REGLA,
        entity_id=str(regla.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after=after,
    )


def _validar_par(rol_a: str, rol_b: str) -> None:
    for rol in (rol_a, rol_b):
        datos = FUNCIONES.get(rol)
        if datos is None:
            raise _invalida("La función debe pertenecer al catálogo del procedimiento")
        if not datos["disponible"]:
            raise _invalida(
                f"La función {rol} no está disponible: {datos['requisito']}"
            )
    if rol_a == rol_b:
        raise _invalida("Las dos funciones de la regla deben ser distintas")


def _codigo_nuevo(db: Session, ctx: CompanyContext) -> str:
    ultimo = db.execute(
        select(func.max(GovernmentSoDRoleRule.codigo)).where(
            GovernmentSoDRoleRule.company_id == ctx.company_id,
            GovernmentSoDRoleRule.codigo.like("RF-%"),
        )
    ).scalar_one_or_none()
    numero = int(ultimo.removeprefix("RF-")) + 1 if ultimo else 1
    return f"RF-{numero:04d}"


def _par_de_funciones(rol_a: str, rol_b: str):
    """El par sin dirección: A≠B y B≠A son la misma incompatibilidad."""
    return or_(
        and_(GovernmentSoDRoleRule.rol_a == rol_a, GovernmentSoDRoleRule.rol_b == rol_b),
        and_(GovernmentSoDRoleRule.rol_a == rol_b, GovernmentSoDRoleRule.rol_b == rol_a),
    )


def _evitar_solapamiento(db: Session, ctx: CompanyContext, regla: GovernmentSoDRoleRule) -> None:
    """Dos reglas en vigor no pueden declarar el mismo par de funciones."""
    existente = db.execute(
        select(GovernmentSoDRoleRule).where(
            GovernmentSoDRoleRule.company_id == ctx.company_id,
            GovernmentSoDRoleRule.estado == "VIGENTE",
            GovernmentSoDRoleRule.id != regla.id,
            _par_de_funciones(regla.rol_a, regla.rol_b),
        )
    ).scalars().first()
    if existente is not None:
        raise ConflictError(
            "GOV_SOD_ROLE_RULE_OVERLAP",
            f"Ya hay una regla en vigor para ese par de funciones ({existente.codigo})",
        )


def _resumen(regla: GovernmentSoDRoleRule, hoy: date) -> dict:
    return {
        "id": str(regla.id),
        "codigo": regla.codigo,
        "nombre": regla.nombre,
        "proceso": regla.proceso,
        "rol_a": regla.rol_a,
        "rol_a_etiqueta": etiqueta_de_funcion(regla.rol_a),
        "rol_b": regla.rol_b,
        "rol_b_etiqueta": etiqueta_de_funcion(regla.rol_b),
        "vigente_desde": regla.vigente_desde,
        "vigente_hasta": regla.vigente_hasta,
        "estado": regla.estado,
        "en_vigor": en_vigor(regla, hoy),
        "version": regla.version,
    }


def en_vigor(regla: GovernmentSoDRoleRule, hoy: date | None = None) -> bool:
    hoy = hoy or hoy_de_negocio()
    return (
        regla.estado == "VIGENTE"
        and regla.vigente_desde <= hoy
        and (regla.vigente_hasta is None or hoy <= regla.vigente_hasta)
    )


def listar(db: Session, ctx: CompanyContext, estado: str | None = None) -> dict:
    consulta = select(GovernmentSoDRoleRule).where(
        GovernmentSoDRoleRule.tenant_id == ctx.tenant_id,
        GovernmentSoDRoleRule.company_id == ctx.company_id,
    )
    if estado:
        consulta = consulta.where(GovernmentSoDRoleRule.estado == estado)
    consulta = consulta.order_by(GovernmentSoDRoleRule.codigo)
    hoy = hoy_de_negocio()
    filas = db.execute(consulta).scalars().all()
    return {"items": [_resumen(regla, hoy) for regla in filas], "total": len(filas), "hoy": hoy}


def detalle(db: Session, ctx: CompanyContext, regla_id: str) -> dict:
    regla = _regla_de_empresa(db, ctx, regla_id)
    historia = db.execute(
        select(GovernmentSoDRoleRuleHistory)
        .where(
            GovernmentSoDRoleRuleHistory.rule_id == regla.id,
            GovernmentSoDRoleRuleHistory.company_id == ctx.company_id,
        )
        .order_by(GovernmentSoDRoleRuleHistory.created_at, GovernmentSoDRoleRuleHistory.id)
    ).scalars().all()
    return {
        **_resumen(regla, hoy_de_negocio()),
        "descripcion": regla.descripcion,
        "fundamento": regla.fundamento,
        "historia": [
            {
                "tipo": fila.tipo,
                "detalle": fila.detalle,
                "en": fila.created_at,
            }
            for fila in historia
        ],
    }


def crear(db: Session, ctx: CompanyContext, cuerpo: dict) -> dict:
    rol_a = str(cuerpo.get("rol_a") or "")
    rol_b = str(cuerpo.get("rol_b") or "")
    _validar_par(rol_a, rol_b)
    nombre = (cuerpo.get("nombre") or "").strip()
    descripcion = (cuerpo.get("descripcion") or "").strip()
    fundamento = (cuerpo.get("fundamento") or "").strip()
    if not nombre or not descripcion or not fundamento:
        raise _invalida("Nombre, descripción del riesgo y fundamento son obligatorios")
    vigente_desde = cuerpo.get("vigente_desde") or hoy_de_negocio()
    vigente_hasta = cuerpo.get("vigente_hasta")
    if vigente_hasta is not None and vigente_hasta < vigente_desde:
        raise _invalida("La vigencia hasta no puede ser anterior a la vigencia desde")
    regla = GovernmentSoDRoleRule(
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        codigo=_codigo_nuevo(db, ctx),
        nombre=nombre,
        descripcion=descripcion,
        proceso=PROCESO,
        rol_a=rol_a,
        rol_b=rol_b,
        fundamento=fundamento,
        vigente_desde=vigente_desde,
        vigente_hasta=vigente_hasta,
        estado="BORRADOR",
        created_by=ctx.user_id,
    )
    db.add(regla)
    db.flush()
    _historia(db, ctx, regla, "CREADA", {"rol_a": rol_a, "rol_b": rol_b})
    _auditar(
        db,
        ctx,
        regla,
        "GOV_SOD_ROLE_RULE_CREATED",
        {"codigo": regla.codigo, "rol_a": rol_a, "rol_b": rol_b, "proceso": PROCESO},
    )
    db.flush()
    return detalle(db, ctx, str(regla.id))


def activar(db: Session, ctx: CompanyContext, regla_id: str, version: int | None, cuerpo: dict) -> dict:
    regla = _para_escribir(db, ctx, regla_id, version)
    _exigir_estado(regla, "BORRADOR")
    vigente_desde = cuerpo.get("vigente_desde") or hoy_de_negocio()
    vigente_hasta = cuerpo.get("vigente_hasta", regla.vigente_hasta)
    if vigente_hasta is not None and vigente_hasta < vigente_desde:
        raise _invalida("La vigencia hasta no puede ser anterior a la vigencia desde")
    _evitar_solapamiento(db, ctx, regla)
    regla.vigente_desde = vigente_desde
    regla.vigente_hasta = vigente_hasta
    regla.estado = "VIGENTE"
    regla.activada_por = ctx.user_id
    regla.activada_en = datetime.now(UTC)
    regla.version += 1
    db.flush()
    _historia(db, ctx, regla, "ACTIVADA", {"vigente_desde": str(vigente_desde)})
    _auditar(
        db,
        ctx,
        regla,
        "GOV_SOD_ROLE_RULE_ACTIVATED",
        {"codigo": regla.codigo, "vigente_desde": str(vigente_desde), "vigente_hasta": str(vigente_hasta) if vigente_hasta else None},
    )
    db.flush()
    return detalle(db, ctx, str(regla.id))


def cerrar(db: Session, ctx: CompanyContext, regla_id: str, version: int | None, cuerpo: dict) -> dict:
    regla = _para_escribir(db, ctx, regla_id, version)
    _exigir_estado(regla, "VIGENTE")
    motivo = (cuerpo.get("motivo") or "").strip()
    if not motivo:
        raise _invalida("El motivo de cierre es obligatorio")
    regla.estado = "CERRADA"
    regla.cerrada_por = ctx.user_id
    regla.cerrada_en = datetime.now(UTC)
    regla.motivo_cierre = motivo[:500]
    regla.version += 1
    db.flush()
    _historia(db, ctx, regla, "CERRADA", {"motivo": motivo})
    _auditar(db, ctx, regla, "GOV_SOD_ROLE_RULE_CLOSED", {"codigo": regla.codigo, "motivo": motivo})
    db.flush()
    return detalle(db, ctx, str(regla.id))


# --------------------------------------------------------------------------- #
# Ocupación de funciones y detección de conflictos
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Ocupacion:
    """Una persona ejerciendo una función del expediente, con el registro que lo prueba."""

    rol: str
    clase: frozenset[str]
    usuario: str | None
    nombre: str
    registro: str
    registro_id: str
    fecha: date
    etiqueta: str | None


def _clase_de_usuario(db: Session, ctx: CompanyContext, user_ids: Iterable[str | None]) -> frozenset[str]:
    """La persona, no la cuenta: mismo funcionario, vínculos cerrados y delegaciones (ORG-06)."""
    clase: set[str] = set()
    for user_id in user_ids:
        if user_id:
            clase |= usuarios_equivalentes(db, ctx, str(user_id))
    return frozenset(clase)


def _usuarios_de_funcionarios(db: Session, ctx: CompanyContext, official_ids: Iterable[str | None]) -> set[str]:
    ids = {str(i) for i in official_ids if i}
    if not ids:
        return set()
    filas = db.execute(
        select(GovernmentUserOfficialLink.user_id).where(
            GovernmentUserOfficialLink.company_id == ctx.company_id,
            GovernmentUserOfficialLink.official_id.in_(ids),
            GovernmentUserOfficialLink.status.in_(("ACTIVO", "CERRADO", "REVOCADO")),
        )
    ).scalars().all()
    return {str(fila) for fila in filas}


def _fecha_de(valor: datetime | date | None, respaldo: date) -> date:
    if valor is None:
        return respaldo
    if isinstance(valor, datetime):
        if valor.tzinfo is None:
            valor = valor.replace(tzinfo=UTC)
        from zoneinfo import ZoneInfo

        return valor.astimezone(ZoneInfo("America/Caracas")).date()
    return valor


def ocupacion(db: Session, ctx: CompanyContext, expediente: GovernmentProcurementFile) -> list[Ocupacion]:
    """Personas que ejercen cada función del expediente, con el registro que lo prueba."""
    company_id = ctx.company_id
    file_id = expediente.id
    respaldo = expediente.fecha_inicio
    filas: list[Ocupacion] = []

    def agregar(rol: str, clase: frozenset[str], usuario: str | None, nombre: str, registro: str,
                registro_id: str, fecha: date, etiqueta: str | None = None) -> None:
        if not clase:
            return
        filas.append(Ocupacion(rol, clase, usuario, nombre, registro, registro_id, fecha, etiqueta))

    agregar(
        "SOLICITANTE",
        _clase_de_usuario(db, ctx, [expediente.created_by]),
        expediente.created_by,
        "—",
        "Expediente registrado",
        str(expediente.id),
        respaldo,
    )
    responsables = db.execute(
        select(GovernmentProcurementFileResponsible).where(
            GovernmentProcurementFileResponsible.company_id == company_id,
            GovernmentProcurementFileResponsible.file_id == file_id,
            GovernmentProcurementFileResponsible.rol == "REQUIRENTE",
        )
    ).scalars().all()
    for responsable in responsables:
        clase = _clase_de_usuario(
            db, ctx, _usuarios_de_funcionarios(db, ctx, [responsable.official_id])
        )
        agregar(
            "SOLICITANTE",
            clase,
            None,
            responsable.funcionario_nombre,
            "Requiriente del expediente",
            str(responsable.id),
            responsable.desde,
            responsable.cargo_nombre,
        )

    ofertas = db.execute(
        select(GovernmentProcurementOffer).where(
            GovernmentProcurementOffer.company_id == company_id,
            GovernmentProcurementOffer.file_id == file_id,
        )
    ).scalars().all()
    for oferta in ofertas:
        clase = _clase_de_usuario(
            db,
            ctx,
            [oferta.created_by, *_usuarios_de_funcionarios(db, ctx, [oferta.official_id])],
        )
        agregar(
            "RECEPTOR",
            clase,
            oferta.created_by,
            oferta.receptor_etiqueta,
            f"Recepción de la oferta R-{oferta.numero:04d}",
            str(oferta.id),
            _fecha_de(oferta.recibida_en, respaldo),
        )

    if expediente.committee_id:
        miembros = db.execute(
            select(GovernmentProcurementCommitteeMember).where(
                GovernmentProcurementCommitteeMember.company_id == company_id,
                GovernmentProcurementCommitteeMember.committee_id == expediente.committee_id,
            )
        ).scalars().all()
        for miembro in miembros:
            clase = _clase_de_usuario(
                db, ctx, _usuarios_de_funcionarios(db, ctx, [miembro.official_id])
            )
            agregar(
                "EVALUADOR",
                clase,
                None,
                "Miembro de la comisión",
                "Miembro de la comisión vinculada",
                str(miembro.id),
                miembro.desde,
            )

    asistentes = db.execute(
        select(GovernmentProcurementOpeningAttendee)
        .join(GovernmentProcurementOpening, GovernmentProcurementOpening.id == GovernmentProcurementOpeningAttendee.opening_id)
        .where(
            GovernmentProcurementOpening.company_id == company_id,
            GovernmentProcurementOpening.file_id == file_id,
            GovernmentProcurementOpeningAttendee.company_id == company_id,
        )
    ).scalars().all()
    aperturas = {
        str(apertura.id): apertura
        for apertura in db.execute(
            select(GovernmentProcurementOpening).where(
                GovernmentProcurementOpening.company_id == company_id,
                GovernmentProcurementOpening.file_id == file_id,
            )
        ).scalars().all()
    }
    for asistente in asistentes:
        apertura = aperturas.get(str(asistente.opening_id))
        clase = _clase_de_usuario(
            db, ctx, _usuarios_de_funcionarios(db, ctx, [asistente.official_id])
        )
        agregar(
            "EVALUADOR",
            clase,
            None,
            "Asistente a la apertura",
            f"Asistente a la apertura n.º {apertura.numero}" if apertura else "Asistente a la apertura",
            str(asistente.id),
            _fecha_de(apertura.abierta_en if apertura else None, respaldo),
        )

    aportes = db.execute(
        select(GovernmentProcurementEvalResult)
        .join(GovernmentProcurementOffer, GovernmentProcurementOffer.id == GovernmentProcurementEvalResult.offer_id)
        .where(
            GovernmentProcurementEvalResult.company_id == company_id,
            GovernmentProcurementOffer.file_id == file_id,
        )
    ).scalars().all()
    for aporte in aportes:
        clase = _clase_de_usuario(
            db,
            ctx,
            [aporte.created_by, *_usuarios_de_funcionarios(db, ctx, [aporte.official_id])],
        )
        agregar(
            "EVALUADOR",
            clase,
            aporte.created_by,
            "—",
            "Resultado de evaluación registrado",
            str(aporte.id),
            _fecha_de(aporte.created_at, respaldo),
        )

    recomendaciones = db.execute(
        select(GovernmentProcurementRecommendation).where(
            GovernmentProcurementRecommendation.company_id == company_id,
            GovernmentProcurementRecommendation.file_id == file_id,
        )
    ).scalars().all()
    for recomendacion in recomendaciones:
        agregar(
            "EVALUADOR",
            _clase_de_usuario(db, ctx, [recomendacion.emitida_por]),
            recomendacion.emitida_por,
            "—",
            f"Recomendación n.º {recomendacion.numero}",
            str(recomendacion.id),
            _fecha_de(recomendacion.emitida_en, respaldo),
        )
    firmantes = db.execute(
        select(GovernmentProcurementRecommendationSignatory)
        .where(
            GovernmentProcurementRecommendationSignatory.company_id == company_id,
            GovernmentProcurementRecommendationSignatory.recommendation_id.in_(
                [recomendacion.id for recomendacion in recomendaciones] or [None]
            ),
        )
    ).scalars().all()
    for firmante in firmantes:
        clase = _clase_de_usuario(
            db, ctx, _usuarios_de_funcionarios(db, ctx, [firmante.official_id])
        )
        agregar(
            "EVALUADOR",
            clase,
            None,
            "Firmante de la recomendación",
            "Firmante de la recomendación",
            str(firmante.id),
            respaldo,
        )

    decisiones = db.execute(
        select(GovernmentProcurementDecision).where(
            GovernmentProcurementDecision.company_id == company_id,
            GovernmentProcurementDecision.file_id == file_id,
        )
    ).scalars().all()
    for decision in decisiones:
        clase = _clase_de_usuario(
            db,
            ctx,
            [decision.decidida_por, *_usuarios_de_funcionarios(db, ctx, [decision.official_id])],
        )
        agregar(
            "ADJUDICADOR",
            clase,
            decision.decidida_por,
            "—",
            f"Decisión n.º {decision.numero} ({decision.resultado})",
            str(decision.id),
            _fecha_de(decision.decidida_en, respaldo),
        )

    return filas


def _reglas_vigentes(db: Session, ctx: CompanyContext, fecha: date) -> list[GovernmentSoDRoleRule]:
    return list(
        db.execute(
            select(GovernmentSoDRoleRule).where(
                GovernmentSoDRoleRule.company_id == ctx.company_id,
                GovernmentSoDRoleRule.estado == "VIGENTE",
                GovernmentSoDRoleRule.vigente_desde <= fecha,
                (GovernmentSoDRoleRule.vigente_hasta.is_(None)) | (GovernmentSoDRoleRule.vigente_hasta >= fecha),
            ).order_by(GovernmentSoDRoleRule.codigo)
        ).scalars().all()
    )


def conflictos_de_ocupaciones(mundo: list[Ocupacion], reglas: list[GovernmentSoDRoleRule],
                              usuarios: dict[str, str]) -> list[dict]:
    """Cruza la ocupación con la matriz. Una persona y un par de funciones = un conflicto."""
    conflictos: list[dict] = []
    for regla in reglas:
        izquierda = [o for o in mundo if o.rol == regla.rol_a]
        derecha = [o for o in mundo if o.rol == regla.rol_b]
        for a in izquierda:
            for b in derecha:
                comunes = a.clase & b.clase
                if not comunes:
                    continue
                actor = sorted(comunes)[0]
                conflictos.append(
                    {
                        "regla_id": str(regla.id),
                        "regla_codigo": regla.codigo,
                        "regla_nombre": regla.nombre,
                        "regla_version": regla.version,
                        "rol_a": regla.rol_a,
                        "rol_a_etiqueta": etiqueta_de_funcion(regla.rol_a),
                        "rol_b": regla.rol_b,
                        "rol_b_etiqueta": etiqueta_de_funcion(regla.rol_b),
                        "actor": actor,
                        "actor_nombre": usuarios.get(actor) or a.nombre or b.nombre,
                        "fecha": max(a.fecha, b.fecha),
                        "evidencia": [
                            {
                                "rol": a.rol,
                                "rol_etiqueta": etiqueta_de_funcion(a.rol),
                                "registro": a.registro,
                                "registro_id": a.registro_id,
                                "fecha": a.fecha,
                                "etiqueta": a.etiqueta,
                            },
                            {
                                "rol": b.rol,
                                "rol_etiqueta": etiqueta_de_funcion(b.rol),
                                "registro": b.registro,
                                "registro_id": b.registro_id,
                                "fecha": b.fecha,
                                "etiqueta": b.etiqueta,
                            },
                        ],
                    }
                )
    conflictos.sort(key=lambda c: (c["fecha"], c["regla_codigo"], c["actor_nombre"]), reverse=True)
    return conflictos


def _nombre_de_usuarios(db: Session, ctx: CompanyContext, ocupaciones: list[Ocupacion]) -> dict[str, str]:
    ids = {usuario for ocupacion in ocupaciones for usuario in ocupacion.clase}
    if not ids:
        return {}
    filas = db.execute(
        select(User).where(User.id.in_(ids), User.tenant_id == ctx.tenant_id)
    ).scalars().all()
    return {str(usuario.id): usuario.username for usuario in filas}


def conflictos_de_expediente(db: Session, ctx: CompanyContext, expediente: GovernmentProcurementFile,
                             fecha: date | None = None) -> list[dict]:
    hoy = fecha or hoy_de_negocio()
    reglas = _reglas_vigentes(db, ctx, hoy)
    if not reglas:
        return []
    mundo = ocupacion(db, ctx, expediente)
    usuarios = _nombre_de_usuarios(db, ctx, mundo)
    return [
        {**conflicto, "expediente_id": str(expediente.id), "expediente_numero": expediente.numero}
        for conflicto in conflictos_de_ocupaciones(mundo, reglas, usuarios)
    ]


def _expedientes_del_periodo(db: Session, ctx: CompanyContext, desde: date, hasta: date) -> list[GovernmentProcurementFile]:
    return list(
        db.execute(
            select(GovernmentProcurementFile)
            .where(
                GovernmentProcurementFile.company_id == ctx.company_id,
                GovernmentProcurementFile.fecha_inicio <= hasta,
            )
            .order_by(GovernmentProcurementFile.numero)
        ).scalars().all()
    )


def conflictos_por_periodo(db: Session, ctx: CompanyContext, desde: date, hasta: date,
                           rol: str | None = None, expediente_id: str | None = None) -> list[dict]:
    if desde > hasta:
        raise KontrolError(
            code="INVALID_DATE_RANGE",
            message="La fecha desde no puede ser posterior a la fecha hasta",
            status_code=422,
        )
    if rol is not None and rol not in FUNCIONES:
        raise _invalida("La función debe pertenecer al catálogo del procedimiento")
    reglas = []
    for dia in {desde, hasta}:
        reglas.extend(_reglas_vigentes(db, ctx, dia))
    if not reglas:
        return []
    reglas_por_codigo: dict[str, GovernmentSoDRoleRule] = {}
    for regla in reglas:
        reglas_por_codigo.setdefault(regla.codigo, regla)
    reglas = list(reglas_por_codigo.values())

    conflictos: list[dict] = []
    for expediente in _expedientes_del_periodo(db, ctx, desde, hasta):
        if expediente_id and str(expediente.id) != str(expediente_id):
            continue
        mundo = ocupacion(db, ctx, expediente)
        usuarios = _nombre_de_usuarios(db, ctx, mundo)
        for conflicto in conflictos_de_ocupaciones(mundo, reglas, usuarios):
            if not (desde <= conflicto["fecha"] <= hasta):
                continue
            if rol is not None and rol not in (conflicto["rol_a"], conflicto["rol_b"]):
                continue
            conflictos.append(
                {
                    **conflicto,
                    "expediente_id": str(expediente.id),
                    "expediente_numero": expediente.numero,
                    "expediente_objeto": expediente.objeto,
                }
            )
    conflictos.sort(key=lambda c: (c["fecha"], c["regla_codigo"], c["expediente_numero"]), reverse=True)
    return conflictos


# --------------------------------------------------------------------------- #
# Guarda preventiva
# --------------------------------------------------------------------------- #
def conflictos_del_expediente(db: Session, ctx: CompanyContext, expediente_id: str) -> list[dict]:
    expediente = db.execute(
        select(GovernmentProcurementFile).where(
            GovernmentProcurementFile.id == expediente_id,
            GovernmentProcurementFile.company_id == ctx.company_id,
        )
    ).scalar_one_or_none()
    if expediente is None:
        raise NotFoundError("GOV_PROCUREMENT_FILE_NOT_FOUND", "El expediente no existe en este ente")
    return conflictos_de_expediente(db, ctx, expediente)


def exportar_csv(db: Session, ctx: CompanyContext, desde: date, hasta: date,
                 rol: str | None = None, expediente_id: str | None = None) -> tuple[str, bytes]:
    """CSV del listado de conflictos del período; deja el evento con filas y filtros (FR-009)."""
    import csv
    import io

    conflictos = conflictos_por_periodo(db, ctx, desde, hasta, rol, expediente_id)
    salida = io.StringIO()
    writer = csv.writer(salida)
    writer.writerow([
        "Expediente", "Objeto", "Fecha", "Regla", "Funcion A", "Funcion B", "Persona",
        "Registro A", "Fecha A", "Registro B", "Fecha B",
    ])
    for conflicto in conflictos:
        evidencia = {item["rol"]: item for item in conflicto["evidencia"]}
        izquierda = evidencia.get(conflicto["rol_a"], {})
        derecha = evidencia.get(conflicto["rol_b"], {})
        writer.writerow([
            conflicto["expediente_numero"],
            conflicto.get("expediente_objeto") or "",
            conflicto["fecha"].isoformat(),
            conflicto["regla_codigo"],
            conflicto["rol_a_etiqueta"] or conflicto["rol_a"],
            conflicto["rol_b_etiqueta"] or conflicto["rol_b"],
            conflicto["actor_nombre"] or conflicto["actor"],
            izquierda.get("registro", ""),
            izquierda.get("fecha", "").isoformat() if izquierda.get("fecha") else "",
            derecha.get("registro", ""),
            derecha.get("fecha", "").isoformat() if derecha.get("fecha") else "",
        ])
    nombre = f"funciones-incompatibles-{desde.isoformat()}-{hasta.isoformat()}.csv"
    record_audit(
        db,
        action="GOV_SOD_ROLE_CONFLICTS_EXPORTED",
        entity_type="GovernmentEntity",
        entity_id=ctx.company_id,
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={
            "filas": len(conflictos),
            "filtros": {
                "desde": desde.isoformat(),
                "hasta": hasta.isoformat(),
                "rol": rol,
                "expediente_id": expediente_id,
            },
        },
    )
    return nombre, salida.getvalue().encode("utf-8")


def verificar_antes_de_asumir_funcion(
    db: Session,
    ctx: CompanyContext,
    expediente: GovernmentProcurementFile,
    rol: str,
    user_ids: Iterable[str | None] = (),
    official_ids: Iterable[str | None] = (),
) -> None:
    """Impide que una persona asuma una función incompatible con otra que ya ejerce (FR-006).

    Se llama antes de la mutación, con la fila del expediente bloqueada por el servicio que la invoca. Si hay
    conflicto, deshace la transacción, audita el intento como REJECTION y responde 409.
    """
    if rol not in FUNCIONES or not FUNCIONES[rol]["disponible"]:
        return
    hoy = hoy_de_negocio()
    reglas = [regla for regla in _reglas_vigentes(db, ctx, hoy) if rol in (regla.rol_a, regla.rol_b)]
    if not reglas:
        return
    clase = _clase_de_usuario(
        db,
        ctx,
        [*[u for u in user_ids if u], *_usuarios_de_funcionarios(db, ctx, official_ids)],
    )
    if not clase:
        return
    mundo = [ocupacion_fila for ocupacion_fila in ocupacion(db, ctx, expediente) if ocupacion_fila.rol != rol]
    usuarios = _nombre_de_usuarios(db, ctx, mundo)
    for regla in reglas:
        previa = regla.rol_a if regla.rol_b == rol else regla.rol_b
        for ocupacion_fila in mundo:
            if ocupacion_fila.rol != previa:
                continue
            comunes = clase & ocupacion_fila.clase
            if not comunes:
                continue
            actor = sorted(comunes)[0]
            detalles = {
                "regla_codigo": regla.codigo,
                "regla_version": regla.version,
                "funcion": rol,
                "funcion_previa": previa,
                "registro_previo": ocupacion_fila.registro,
                "registro_previo_id": ocupacion_fila.registro_id,
                "expediente_id": str(expediente.id),
                "expediente_numero": expediente.numero,
                "actor": actor,
            }
            record_audit_after_rollback(
                db,
                action=CONFLICTO_ACCION,
                entity_type=ENTIDAD_EXPEDIENTE,
                entity_id=str(expediente.id),
                tenant_id=ctx.tenant_id,
                company_id=ctx.company_id,
                user_id=ctx.user_id,
                after=detalles,
            )
            quien = usuarios.get(actor) or ocupacion_fila.nombre
            raise ConflictError(
                "GOV_SOD_ROLE_CONFLICT",
                (
                    f"{quien} no puede asumir la función «{etiqueta_de_funcion(rol)}» en el expediente "
                    f"{expediente.numero}: ya ejerce «{etiqueta_de_funcion(previa)}» "
                    f"({ocupacion_fila.registro}) y la regla {regla.codigo} lo prohíbe"
                ),
                details=detalles,
            )
