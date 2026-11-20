"""Autoridad única de bloqueos SoD (GOV-SOD-COVERAGE-01).

Taxonomía de plataforma; la regla la define cada dominio.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext
from app.modules.audit.models import AuditEvent
from app.modules.government import procesos as autoridad_procesos
from app.modules.government.models import GovernmentSoDRoleRule, GovernmentSoDRule
from app.modules.government.service_auditoria import _instante, _usuarios_por_ids
from app.modules.government.service_sod import CONFLICTO_ACCION as CTL01_ACCION
from app.modules.government.service_sod import etiqueta_de
from app.modules.government.service_sod_funciones import CONFLICTO_ACCION as PROC11_ACCION
from app.modules.government.service_sod_funciones import etiqueta_de_funcion

BUD08_ACCION = "GOV_BUDGET_COMMITMENT_SOD_BLOCKED"


def _etiqueta_proceso(codigo: str, respaldo: str) -> str:
    """Devuelve la etiqueta de un código de proceso según la taxonomía.

    Si el código es un proceso de la autoridad de procesos devuelve su nombre. Si el código es
    vacío devuelve "Proceso no especificado". En otro caso devuelve el respaldo.
    """
    nombre = autoridad_procesos.nombre_de(codigo)
    if nombre is not None:
        return nombre
    if not codigo:
        return "Proceso no especificado"
    return respaldo


@dataclass(frozen=True)
class AdaptadorSoD:
    accion: str
    proceso: str | None
    proceso_etiqueta: str
    tipo_conflicto: str
    tipo_conflicto_etiqueta: str
    titulo: str
    normalizar: Callable[[AdaptadorSoD, AuditEvent, Any, dict[str, str]], dict[str, Any]]
    resolver: (
        Callable[[Session, CompanyContext, list[AuditEvent]], dict[str, Any]] | None
    ) = None


def _resolver_ctl01(
    db: Session, ctx: CompanyContext, eventos: list[AuditEvent]
) -> dict[str, Any]:
    """Resuelve las reglas GovernmentSoDRule por `entity_id` de cada evento."""
    ids: set[str] = set()
    for evento in eventos:
        if evento.entity_id is not None:
            ids.add(str(evento.entity_id))
    if not ids:
        return {}
    filas = db.execute(
        select(GovernmentSoDRule).where(
            GovernmentSoDRule.company_id == ctx.company_id,
            GovernmentSoDRule.id.in_(ids),
        )
    ).scalars().all()
    reglas_por_id = {str(regla.id): regla for regla in filas}
    return {
        str(evento.id): (
            reglas_por_id.get(str(evento.entity_id))
            if evento.entity_id is not None
            else None
        )
        for evento in eventos
    }


def _resolver_proc11(
    db: Session, ctx: CompanyContext, eventos: list[AuditEvent]
) -> dict[str, Any]:
    """Resuelve las GovernmentSoDRoleRule por `after.regla_codigo`."""
    codigos: set[str] = set()
    for evento in eventos:
        after = evento.after or {}
        codigo = after.get("regla_codigo")
        if codigo:
            codigos.add(str(codigo))
    if not codigos:
        return {}
    filas = db.execute(
        select(GovernmentSoDRoleRule).where(
            GovernmentSoDRoleRule.company_id == ctx.company_id,
            GovernmentSoDRoleRule.codigo.in_(codigos),
        )
    ).scalars().all()
    reglas_por_codigo = {regla.codigo: regla for regla in filas}
    resueltas: dict[str, Any] = {}
    for evento in eventos:
        after = evento.after or {}
        codigo = after.get("regla_codigo")
        resueltas[str(evento.id)] = reglas_por_codigo.get(str(codigo)) if codigo else None
    return resueltas


def _normalizar_ctl01(
    adaptador: AdaptadorSoD,
    evento: AuditEvent,
    regla: GovernmentSoDRule | None,
    usuarios: dict[str, str],
) -> dict[str, Any]:
    after = evento.after or {}
    regla_codigo = after.get("regla_codigo") or (regla.codigo if regla else None)
    regla_nombre = regla.nombre if regla else (regla_codigo or "Regla no identificada")
    regla_version = after.get("regla_version")
    proceso = after.get("proceso") or (regla.proceso if regla else "") or ""
    proceso_etiqueta = _etiqueta_proceso(str(proceso), str(proceso))
    usuario_id = str(evento.user_id) if evento.user_id else None
    usuario = usuarios.get(usuario_id) if usuario_id else None
    recurso_tipo = after.get("objeto_tipo")
    recurso_id = after.get("objeto_id")
    recurso_etiqueta = None
    op = etiqueta_de(after.get("accion")) or "una operación"
    previa = etiqueta_de(after.get("accion_previa")) or "una operación previa"
    operacion_etiqueta = etiqueta_de(after.get("accion")) or f"Operación de {proceso_etiqueta}"
    operacion_previa_etiqueta = etiqueta_de(after.get("accion_previa")) or f"Operación de {proceso_etiqueta}"
    r = regla_codigo or "sin código"
    u = usuario or "Usuario no identificado"
    detalle = f"{u} intentó «{op}» después de «{previa}» sobre el mismo objeto. La regla {r} lo bloqueó."
    sujetos = [
        {"etiqueta": "Usuario", "valor": u},
        {"etiqueta": "Regla", "valor": r},
    ]
    evidencia = {
        "accion": after.get("accion"),
        "accion_previa": after.get("accion_previa"),
        "objeto_tipo": recurso_tipo,
        "objeto_id": recurso_id,
    }
    return {
        "evento_id": str(evento.id),
        "fecha": _instante(evento.event_time),
        "accion_auditoria": evento.action,
        "proceso": proceso,
        "proceso_etiqueta": proceso_etiqueta,
        "regla_codigo": regla_codigo,
        "regla_nombre": regla_nombre,
        "regla_version": regla_version,
        "tipo_conflicto": adaptador.tipo_conflicto,
        "tipo_conflicto_etiqueta": adaptador.tipo_conflicto_etiqueta,
        "usuario_id": usuario_id,
        "usuario": usuario,
        "recurso_tipo": recurso_tipo,
        "recurso_id": recurso_id,
        "recurso_etiqueta": recurso_etiqueta,
        "operacion_etiqueta": operacion_etiqueta,
        "operacion_previa_etiqueta": operacion_previa_etiqueta,
        "titulo": adaptador.titulo,
        "detalle": detalle,
        "sujetos": sujetos,
        "evidencia": evidencia,
    }


def _normalizar_proc11(
    adaptador: AdaptadorSoD,
    evento: AuditEvent,
    regla: GovernmentSoDRoleRule | None,
    usuarios: dict[str, str],
) -> dict[str, Any]:
    after = evento.after or {}
    regla_codigo = after.get("regla_codigo")
    regla_nombre = (
        regla.nombre
        if regla
        else (str(regla_codigo) if regla_codigo else "Regla no identificada")
    )
    regla_version = after.get("regla_version")
    proceso = adaptador.proceso or ""
    proceso_etiqueta = _etiqueta_proceso(proceso, adaptador.proceso_etiqueta)
    usuario_id = str(evento.user_id) if evento.user_id else None
    usuario = usuarios.get(usuario_id) if usuario_id else None
    recurso_tipo = "EXPEDIENTE"
    recurso_id = after.get("expediente_id") or evento.entity_id
    recurso_id = str(recurso_id) if recurso_id is not None else None
    recurso_etiqueta = after.get("expediente_numero")
    funcion = after.get("funcion")
    funcion_previa = after.get("funcion_previa")
    f = etiqueta_de_funcion(funcion) or "una función"
    fp = etiqueta_de_funcion(funcion_previa) or "otra función"
    operacion_etiqueta = f"Actuar como {f}"
    operacion_previa_etiqueta = f"Actuar como {fp}"
    expediente = after.get("expediente_numero") or "sin número"
    r = str(regla_codigo) if regla_codigo else "sin código"
    u = usuario or "Usuario no identificado"
    detalle = (
        f"{u} intentó actuar como {f} en el expediente {expediente} "
        f"después de actuar como {fp}. La regla {r} lo bloqueó."
    )
    sujetos = [
        {"etiqueta": "Usuario", "valor": u},
        {"etiqueta": "Regla", "valor": r},
        {"etiqueta": "Expediente", "valor": str(expediente)},
    ]
    evidencia = {
        "funcion": funcion,
        "funcion_previa": funcion_previa,
        "expediente_id": after.get("expediente_id"),
        "expediente_numero": after.get("expediente_numero"),
        "actor": after.get("actor"),
    }
    return {
        "evento_id": str(evento.id),
        "fecha": _instante(evento.event_time),
        "accion_auditoria": evento.action,
        "proceso": proceso,
        "proceso_etiqueta": proceso_etiqueta,
        "regla_codigo": regla_codigo,
        "regla_nombre": regla_nombre,
        "regla_version": regla_version,
        "tipo_conflicto": adaptador.tipo_conflicto,
        "tipo_conflicto_etiqueta": adaptador.tipo_conflicto_etiqueta,
        "usuario_id": usuario_id,
        "usuario": usuario,
        "recurso_tipo": recurso_tipo,
        "recurso_id": recurso_id,
        "recurso_etiqueta": recurso_etiqueta,
        "operacion_etiqueta": operacion_etiqueta,
        "operacion_previa_etiqueta": operacion_previa_etiqueta,
        "titulo": adaptador.titulo,
        "detalle": detalle,
        "sujetos": sujetos,
        "evidencia": evidencia,
    }


def _normalizar_bud08(
    adaptador: AdaptadorSoD,
    evento: AuditEvent,
    regla: None,
    usuarios: dict[str, str],
) -> dict[str, Any]:
    after = evento.after or {}
    regla_nombre = after.get("regla") or "Quien certifica no compromete"
    proceso = adaptador.proceso or ""
    proceso_etiqueta = _etiqueta_proceso(proceso, adaptador.proceso_etiqueta)
    usuario_id = str(evento.user_id) if evento.user_id else None
    usuario = usuarios.get(usuario_id) if usuario_id else None
    recurso_tipo = "BUDGET_YEAR"
    recurso_id = str(evento.entity_id) if evento.entity_id is not None else None
    anio = after.get("anio")
    recurso_etiqueta = f"Ejercicio {anio}" if anio else None
    certificados = after.get("certificados") or []
    certs = ", ".join(str(c) for c in certificados) or "sin código"
    operacion_etiqueta = "Registrar un compromiso"
    operacion_previa_etiqueta = f"Emitir o firmar la certificación {certs}"
    u = usuario or "Usuario no identificado"
    detalle = (
        f"{u} intentó registrar un compromiso después de haber emitido o firmado "
        f"la certificación {certs}"
    )
    if anio:
        detalle += f" del ejercicio {anio}"
    detalle += f". La regla «{regla_nombre}» lo bloqueó."
    sujetos = [
        {"etiqueta": "Usuario", "valor": u},
        {"etiqueta": "Regla", "valor": str(regla_nombre)},
    ]
    if anio:
        sujetos.append({"etiqueta": "Ejercicio", "valor": str(anio)})
    sujetos.append({"etiqueta": "Certificaciones", "valor": certs})
    evidencia = {
        "anio": anio,
        "certificados": after.get("certificados"),
    }
    return {
        "evento_id": str(evento.id),
        "fecha": _instante(evento.event_time),
        "accion_auditoria": evento.action,
        "proceso": proceso,
        "proceso_etiqueta": proceso_etiqueta,
        "regla_codigo": None,
        "regla_nombre": regla_nombre,
        "regla_version": None,
        "tipo_conflicto": adaptador.tipo_conflicto,
        "tipo_conflicto_etiqueta": adaptador.tipo_conflicto_etiqueta,
        "usuario_id": usuario_id,
        "usuario": usuario,
        "recurso_tipo": recurso_tipo,
        "recurso_id": recurso_id,
        "recurso_etiqueta": recurso_etiqueta,
        "operacion_etiqueta": operacion_etiqueta,
        "operacion_previa_etiqueta": operacion_previa_etiqueta,
        "titulo": adaptador.titulo,
        "detalle": detalle,
        "sujetos": sujetos,
        "evidencia": evidencia,
    }


PRODUCTORES: dict[str, AdaptadorSoD] = {
    adaptador.accion: adaptador
    for adaptador in (
        AdaptadorSoD(
            accion=CTL01_ACCION,
            proceso=None,
            proceso_etiqueta="Proceso no especificado",
            tipo_conflicto="INCOMPATIBLE_ACTIONS",
            tipo_conflicto_etiqueta="Acciones incompatibles",
            titulo="Intento bloqueado por segregación de funciones",
            normalizar=_normalizar_ctl01,
            resolver=_resolver_ctl01,
        ),
        AdaptadorSoD(
            accion=PROC11_ACCION,
            proceso="PROC-11",
            proceso_etiqueta="Funciones incompatibles en contrataciones",
            tipo_conflicto="INCOMPATIBLE_FUNCTIONS",
            tipo_conflicto_etiqueta="Funciones incompatibles",
            titulo="Intento bloqueado por funciones incompatibles",
            normalizar=_normalizar_proc11,
            resolver=_resolver_proc11,
        ),
        AdaptadorSoD(
            accion=BUD08_ACCION,
            proceso="BUD-08",
            proceso_etiqueta="Compromiso presupuestario",
            tipo_conflicto="SEGREGATION_OF_DUTIES",
            tipo_conflicto_etiqueta="Segregación de funciones",
            titulo="Intento bloqueado por segregación de funciones",
            normalizar=_normalizar_bud08,
            resolver=None,
        ),
    )
}

ACCIONES_SOD: tuple[str, ...] = tuple(PRODUCTORES)


def es_bloqueo_sod(accion: str | None) -> bool:
    return accion in ACCIONES_SOD


def consultar(
    db: Session,
    ctx: CompanyContext,
    *,
    inicio: datetime | None = None,
    fin: datetime | None = None,
) -> list[AuditEvent]:
    consulta = select(AuditEvent).where(
        AuditEvent.tenant_id == ctx.tenant_id,
        AuditEvent.company_id == ctx.company_id,
        AuditEvent.action.in_(ACCIONES_SOD),
    )
    if inicio is not None:
        consulta = consulta.where(AuditEvent.event_time >= inicio)
    if fin is not None:
        consulta = consulta.where(AuditEvent.event_time < fin)
    consulta = consulta.order_by(AuditEvent.event_time.desc())
    return list(db.execute(consulta).scalars().all())


def normalizar(
    db: Session, ctx: CompanyContext, eventos: list[AuditEvent]
) -> list[dict[str, Any]]:
    if not eventos:
        return []

    user_ids = {str(evento.user_id) for evento in eventos if evento.user_id is not None}
    usuarios = _usuarios_por_ids(db, user_ids, ctx.tenant_id)

    eventos_por_accion: dict[str, list[AuditEvent]] = {}
    for evento in eventos:
        eventos_por_accion.setdefault(evento.action, []).append(evento)

    reglas_resueltas: dict[str, Any] = {}
    for accion, grupo in eventos_por_accion.items():
        adaptador = PRODUCTORES.get(accion)
        if adaptador is None or adaptador.resolver is None:
            continue
        reglas_resueltas.update(adaptador.resolver(db, ctx, grupo))

    normalizados: list[dict[str, Any]] = []
    for evento in eventos:
        adaptador = PRODUCTORES.get(evento.action)
        if adaptador is None:
            continue
        regla = reglas_resueltas.get(str(evento.id))
        normalizados.append(
            adaptador.normalizar(adaptador, evento, regla, usuarios)
        )
    return normalizados
