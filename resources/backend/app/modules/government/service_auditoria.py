"""Servicio de consulta y muestreo del auditor de Gobierno (CTL-04 · GOV-CTL-005)."""

from __future__ import annotations

import csv
import io
import json
import random
import re
import secrets
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, false, func, or_, select, tuple_
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext
from app.core.errors import KontrolError, NotFoundError
from app.modules.audit.models import AuditEvent
from app.modules.government.models import (
    GovernmentAct,
    GovernmentAuditSample,
    GovernmentAuditSampleItem,
    GovernmentEntity,
    GovernmentFinding,
    GovernmentNotification,
    GovernmentPosition,
    GovernmentStructure,
    GovernmentUnit,
)
from app.modules.government.schemas_auditoria import (
    AuditoriaEventoResumen,
    AuditoriaFiltrosPoblacion,
    AuditoriaObjeto,
    MuestraIn,
)
from app.modules.identity_access.models import User
from app.shared.audit import record_audit
from app.shared.audit_catalog import catalog, safe_details
from app.shared.clock import hoy_de_negocio, limites_del_dia_utc

PROCESOS: list[tuple[str, str, str]] = [
    ("ORG-01", "Configuración del ente", "gov-0-01"),
    ("ORG-02", "Estructura organizativa", "gov-0-02"),
    ("ORG-03", "Cargos y competencias", "gov-0-03"),
    ("ORG-07", "Matriz de autoridad", "gov-org-07"),
    ("DOC-02", "Actos administrativos", "gov-doc-02"),
    ("DOC-04", "Notificaciones administrativas", "gov-doc-04"),
    ("CTL-04", "Auditoría institucional", "gov-ctl-04"),
    ("CTL-06", "Hallazgos y acciones correctivas", "gov-ctl-06"),
]
_PROCESO_POR_OWNER_SPEC = {owner_spec: (codigo, nombre) for codigo, nombre, owner_spec in PROCESOS}
_PROCESO_NOMBRE = {codigo: nombre for codigo, nombre, _ in PROCESOS}
_CODIGOS_PROCESO = {codigo for codigo, _, _ in PROCESOS}

_ACTION_ENTITY_TYPE = tuple[tuple[str, str], ...]


def _instante(dt: datetime) -> datetime:
    """Normaliza un datetime a UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _pares_gobierno() -> _ACTION_ENTITY_TYPE:
    """Devuelve los pares (action, entity_type) del catálogo de Gobierno."""
    pares: list[tuple[str, str]] = []
    for (action, entity_type), spec in catalog().items():
        if spec.owner_module == "government":
            pares.append((action, entity_type))
    return tuple(pares)


def _proceso_de(owner_spec: str) -> tuple[str, str]:
    """Traduce el owner_spec del catálogo al código y nombre del proceso."""
    return _PROCESO_POR_OWNER_SPEC.get(owner_spec, ("", owner_spec))


def _filtro_acciones_gobierno() -> tuple[dict[str, str], ...]:
    """Catálogo de acciones de Gobierno ordenado por proceso y código."""
    acciones: list[dict[str, str]] = []
    for (action, entity_type), spec in catalog().items():
        if spec.owner_module != "government":
            continue
        proceso_codigo, _ = _proceso_de(spec.owner_spec)
        acciones.append(
            {
                "codigo": action,
                "entidad": entity_type,
                "etiqueta": spec.label,
                "proceso": proceso_codigo,
            }
        )
    orden = {codigo: pos for pos, (codigo, _, _) in enumerate(PROCESOS)}
    acciones.sort(key=lambda a: (orden.get(a["proceso"], 999), a["codigo"]))
    return tuple(acciones)


def _condicion_proceso(proceso: str) -> Any:
    """Devuelve la condición OR de owner_spec del proceso indicado."""
    owner_specs = [owner_spec for codigo, _, owner_spec in PROCESOS if codigo == proceso]
    if not owner_specs:
        return false()
    pares: list[Any] = []
    for (action, entity_type), spec in catalog().items():
        if spec.owner_module == "government" and spec.owner_spec in owner_specs:
            pares.append(and_(AuditEvent.action == action, AuditEvent.entity_type == entity_type))
    return or_(*pares) if pares else false()


def _condiciones(ctx: CompanyContext, filtros: AuditoriaFiltrosPoblacion) -> list[Any]:
    """Construye las condiciones de población (alcance A + filtros B) con validaciones 422."""
    if filtros.desde and filtros.hasta and filtros.desde > filtros.hasta:
        raise KontrolError(
            code="INVALID_DATE_RANGE",
            message="La fecha inicial no puede ser posterior a la fecha final",
            field_errors={"desde": ["La fecha inicial no puede ser posterior a la fecha final"]},
            status_code=422,
        )

    condiciones: list[Any] = [
        AuditEvent.tenant_id == ctx.tenant_id,
        AuditEvent.company_id == ctx.company_id,
        tuple_(AuditEvent.action, AuditEvent.entity_type).in_(_pares_gobierno()),
    ]

    if filtros.desde:
        inicio, _ = limites_del_dia_utc(filtros.desde)
        condiciones.append(AuditEvent.event_time >= inicio)
    if filtros.hasta:
        _, inicio_siguiente = limites_del_dia_utc(filtros.hasta)
        condiciones.append(AuditEvent.event_time < inicio_siguiente)

    if filtros.proceso:
        if filtros.proceso not in _CODIGOS_PROCESO:
            raise KontrolError(
                code="GOV_AUDIT_INVALID_FILTER",
                message="El proceso indicado no pertenece a la auditoría de Gobierno",
                field_errors={"proceso": ["El proceso indicado no pertenece a la auditoría de Gobierno"]},
                status_code=422,
            )
        condiciones.append(_condicion_proceso(filtros.proceso))

    if filtros.accion:
        codigos = {item["codigo"] for item in _filtro_acciones_gobierno()}
        if filtros.accion not in codigos:
            raise KontrolError(
                code="GOV_AUDIT_INVALID_FILTER",
                message="La acción indicada no pertenece a la auditoría de Gobierno",
                field_errors={"accion": ["La acción indicada no pertenece a la auditoría de Gobierno"]},
                status_code=422,
            )
        condiciones.append(AuditEvent.action == filtros.accion)

    if filtros.usuario:
        condiciones.append(
            AuditEvent.user_id.in_(
                select(User.id).where(User.tenant_id == ctx.tenant_id, User.username == filtros.usuario)
            )
        )

    if filtros.texto:
        texto = filtros.texto.casefold()
        acciones_texto = [
            item["codigo"]
            for item in _filtro_acciones_gobierno()
            if texto in item["codigo"].casefold() or texto in item["etiqueta"].casefold()
        ]
        usuarios_texto = select(User.id).where(
            User.tenant_id == ctx.tenant_id,
            User.username.icontains(texto, autoescape=True),
        )
        condiciones_texto = [
            AuditEvent.reason.icontains(texto, autoescape=True),
            AuditEvent.user_id.in_(usuarios_texto),
        ]
        if acciones_texto:
            condiciones_texto.append(AuditEvent.action.in_(acciones_texto))
        condiciones.append(or_(*condiciones_texto))

    return condiciones


def _detalle_de_evento_para_catalogo(event: AuditEvent) -> tuple[dict[str, Any], list[str]]:
    """Calcula safe_details y documentos de un evento."""
    detalle = safe_details(event.action, event.entity_type, event.before, event.after, event.evidence)
    documentos: list[str] = []
    seen: set[str] = set()
    for valor in detalle.values():
        if not isinstance(valor, dict):
            continue
        for clave, contenido in valor.items():
            if isinstance(contenido, str) and contenido.strip() and (
                clave.endswith("documento_id") or re.match(r"^documento_\w+_id$", clave)
            ):
                doc_id = contenido.strip()
                if doc_id not in seen:
                    seen.add(doc_id)
                    documentos.append(doc_id)
    return detalle, documentos


def _objeto_desde_evento(db: Session, event: AuditEvent, ctx: CompanyContext) -> AuditoriaObjeto | None:
    """Resuelve el objeto de negocio asociado a un evento si existe y es de la empresa activa."""
    objeto_id = event.entity_id
    if objeto_id is None:
        return None

    empresa = ctx.company_id
    if event.entity_type == "GovernmentEntity":
        objeto = db.scalar(
            select(GovernmentEntity).where(
                GovernmentEntity.id == objeto_id,
                GovernmentEntity.company_id == empresa,
            )
        )
        return None if objeto is None else AuditoriaObjeto(
            tipo=event.entity_type, id=objeto_id, ruta="/gobierno/ente", capacidad="gobierno_ente:view"
        )
    if event.entity_type == "GovernmentStructure":
        estructura = db.scalar(
            select(GovernmentStructure).where(
                GovernmentStructure.id == objeto_id,
                GovernmentStructure.company_id == empresa,
            )
        )
        return None if estructura is None else AuditoriaObjeto(
            tipo=event.entity_type, id=objeto_id, ruta=f"/gobierno/estructura/{estructura.exercise}", capacidad="gobierno_estructura:view"
        )
    if event.entity_type == "GovernmentUnit":
        unidad = db.scalar(
            select(GovernmentUnit).where(
                GovernmentUnit.id == objeto_id,
                GovernmentUnit.company_id == empresa,
            )
        )
        if unidad is None:
            return None
        estructura = db.scalar(
            select(GovernmentStructure).where(
                GovernmentStructure.id == unidad.structure_id,
                GovernmentStructure.company_id == empresa,
            )
        )
        return None if estructura is None else AuditoriaObjeto(
            tipo=event.entity_type, id=objeto_id, ruta=f"/gobierno/estructura/{estructura.exercise}", capacidad="gobierno_estructura:view"
        )
    if event.entity_type == "GovernmentPosition":
        cargo = db.scalar(
            select(GovernmentPosition).where(
                GovernmentPosition.id == objeto_id,
                GovernmentPosition.company_id == empresa,
            )
        )
        if cargo is None:
            return None
        estructura = db.scalar(
            select(GovernmentStructure).where(
                GovernmentStructure.id == cargo.structure_id,
                GovernmentStructure.company_id == empresa,
            )
        )
        return None if estructura is None else AuditoriaObjeto(
            tipo=event.entity_type, id=objeto_id, ruta=f"/gobierno/cargos/{estructura.exercise}/{objeto_id}", capacidad="gobierno_cargos:view"
        )
    if event.entity_type == "GovernmentAct":
        acto = db.scalar(
            select(GovernmentAct).where(
                GovernmentAct.id == objeto_id,
                GovernmentAct.company_id == empresa,
            )
        )
        return None if acto is None else AuditoriaObjeto(
            tipo=event.entity_type, id=objeto_id, ruta=f"/gobierno/actos/{objeto_id}", capacidad="gobierno_actos:view"
        )
    if event.entity_type == "GovernmentNotification":
        notificacion = db.scalar(
            select(GovernmentNotification).where(
                GovernmentNotification.id == objeto_id,
                GovernmentNotification.company_id == empresa,
            )
        )
        return None if notificacion is None else AuditoriaObjeto(
            tipo=event.entity_type, id=objeto_id, ruta=f"/gobierno/notificaciones/{objeto_id}", capacidad="gobierno_notificaciones:view"
        )
    if event.entity_type == "GovernmentAuditSample":
        muestra = db.scalar(
            select(GovernmentAuditSample).where(
                GovernmentAuditSample.id == objeto_id,
                GovernmentAuditSample.company_id == empresa,
            )
        )
        return None if muestra is None else AuditoriaObjeto(
            tipo=event.entity_type, id=objeto_id, ruta=f"/gobierno/auditoria/muestras/{objeto_id}", capacidad="gobierno_auditoria:view"
        )
    if event.entity_type == "GovernmentFinding":
        hallazgo = db.scalar(
            select(GovernmentFinding).where(
                GovernmentFinding.id == objeto_id,
                GovernmentFinding.company_id == empresa,
            )
        )
        return None if hallazgo is None else AuditoriaObjeto(
            tipo=event.entity_type, id=objeto_id, ruta=f"/gobierno/hallazgos/{objeto_id}", capacidad="gobierno_hallazgos:view"
        )
    return None


def _usuarios_por_ids(
    db: Session, ids: Iterable[str | None], tenant_id: str | None
) -> dict[str, str]:
    """Resuelve usernames para un conjunto de ids con una consulta."""
    id_list = [i for i in set(ids) if i is not None]
    if not id_list:
        return {}
    filas = db.scalars(
        select(User).where(User.id.in_(id_list), User.tenant_id == tenant_id)
    ).all()
    return {str(usuario.id): usuario.username for usuario in filas}


def _resumenes(db: Session, events: Iterable[AuditEvent]) -> list[AuditoriaEventoResumen]:
    """Convierte eventos en resúmenes resolviendo usuarios con una sola consulta por página."""
    eventos = list(events)
    if not eventos:
        return []
    usuarios = _usuarios_por_ids(
        db,
        (event.user_id for event in eventos if event.user_id is not None),
        eventos[0].tenant_id if eventos else None,
    )
    resumenes: list[AuditoriaEventoResumen] = []
    for event in eventos:
        spec = catalog().get((event.action, event.entity_type))
        etiqueta = spec.label if spec else event.action
        owner_spec = spec.owner_spec if spec else ""
        proceso, proceso_nombre = _proceso_de(owner_spec)
        resumenes.append(
            AuditoriaEventoResumen(
                id=str(event.id),
                fecha=_instante(event.event_time),
                proceso=proceso,
                proceso_nombre=proceso_nombre,
                accion=event.action,
                accion_etiqueta=etiqueta,
                entidad=event.entity_type,
                entidad_id=event.entity_id,
                usuario=usuarios.get(event.user_id) if event.user_id is not None else None,
                motivo=event.reason,
                request_id=event.request_id,
            )
        )
    return resumenes


def _muestra_serializada(db: Session, muestra: GovernmentAuditSample, con_eventos: bool = False) -> dict[str, Any]:
    """Serializa una muestra y opcionalmente sus eventos en el orden de las partidas."""
    registrada_por = None
    if muestra.created_by is not None:
        usuario = db.scalar(select(User).where(User.id == muestra.created_by, User.tenant_id == muestra.tenant_id))
        registrada_por = usuario.username if usuario else None

    resultado: dict[str, Any] = {
        "id": str(muestra.id),
        "codigo": muestra.codigo,
        "titulo": muestra.titulo,
        "criterio": muestra.criterio,
        "justificacion": muestra.justificacion,
        "metodo": muestra.metodo,
        "semilla": muestra.semilla,
        "tamano": muestra.tamano,
        "poblacion": muestra.poblacion,
        "filtros": muestra.filtros or {},
        "registrada_por": registrada_por,
        "registrada_en": _instante(muestra.created_at),
    }
    if con_eventos:
        partidas = db.scalars(
            select(GovernmentAuditSampleItem)
            .where(
                GovernmentAuditSampleItem.sample_id == muestra.id,
                GovernmentAuditSampleItem.company_id == muestra.company_id,
            )
            .order_by(GovernmentAuditSampleItem.orden)
        ).all()
        ids = [partida.audit_event_id for partida in partidas]
        eventos: list[AuditoriaEventoResumen] = []
        if ids:
            filas = db.scalars(select(AuditEvent).where(AuditEvent.id.in_(ids))).all()
            por_id = {str(event.id): event for event in filas}
            eventos = _resumenes(db, (por_id[event_id] for event_id in ids if event_id in por_id))
        resultado["eventos"] = eventos
    return resultado


def filtros(db: Session, ctx: CompanyContext) -> dict[str, Any]:
    """Devuelve el catálogo de procesos y acciones de la auditoría de Gobierno."""
    del db, ctx
    return {
        "procesos": [{"codigo": codigo, "nombre": nombre} for codigo, nombre, _ in PROCESOS],
        "acciones": list(_filtro_acciones_gobierno()),
    }


def listar_eventos(
    db: Session,
    ctx: CompanyContext,
    filtros_poblacion: AuditoriaFiltrosPoblacion,
    *,
    pagina: int,
    por_pagina: int,
) -> dict[str, Any]:
    """Página de eventos de auditoría de Gobierno."""
    condiciones = _condiciones(ctx, filtros_poblacion)
    total = db.scalar(
        select(func.count()).select_from(AuditEvent).where(*condiciones)
    ) or 0
    eventos = db.scalars(
        select(AuditEvent)
        .where(*condiciones)
        .order_by(AuditEvent.event_time.desc(), AuditEvent.id.desc())
        .offset((pagina - 1) * por_pagina)
        .limit(por_pagina)
    ).all()
    return {
        "items": _resumenes(db, eventos),
        "total": total,
        "pagina": pagina,
        "por_pagina": por_pagina,
    }


def detalle_evento(db: Session, ctx: CompanyContext, evento_id: str) -> dict[str, Any]:
    """Devuelve el detalle de un evento de auditoría de Gobierno."""
    event = db.scalar(
        select(AuditEvent).where(
            AuditEvent.id == evento_id,
            AuditEvent.tenant_id == ctx.tenant_id,
            AuditEvent.company_id == ctx.company_id,
        )
    )
    if event is None or (event.action, event.entity_type) not in set(_pares_gobierno()):
        raise NotFoundError(
            code="GOV_AUDIT_EVENT_NOT_FOUND",
            message="El evento no existe en la auditoría de este ente",
        )

    resumen = _resumenes(db, [event])[0]
    detalle_seguro, documentos = _detalle_de_evento_para_catalogo(event)
    objeto = _objeto_desde_evento(db, event, ctx)
    return {
        **resumen.model_dump(),
        "detalle": detalle_seguro,
        "documentos": documentos,
        "objeto": objeto.model_dump() if objeto else None,
    }


def registrar_muestra(db: Session, ctx: CompanyContext, datos: MuestraIn) -> dict[str, Any]:
    """Registra una muestra inmutable de auditoría y su evento correspondiente."""
    condiciones = _condiciones(ctx, datos.filtros)
    ids_poblacion = [
        str(i)
        for i in db.scalars(
            select(AuditEvent.id)
            .where(*condiciones)
            .order_by(AuditEvent.event_time.asc(), AuditEvent.id.asc())
        ).all()
    ]
    n_poblacion = len(ids_poblacion)

    if n_poblacion == 0:
        raise KontrolError(
            code="GOV_AUDIT_EMPTY_POPULATION",
            message="La población de auditoría está vacía",
            status_code=422,
        )

    metodo = datos.metodo
    semilla: int | None = None
    ids_seleccionados: list[str] = []

    if metodo == "TODAS":
        if n_poblacion > 2000:
            raise KontrolError(
                code="GOV_AUDIT_POPULATION_TOO_LARGE",
                message="La población de auditoría supera el límite de 2000 eventos",
                status_code=422,
            )
        ids_seleccionados = ids_poblacion
    elif metodo == "ESPECIFICA":
        elegidos = set(datos.eventos or [])
        fuera = elegidos - set(ids_poblacion)
        if fuera:
            raise KontrolError(
                code="GOV_AUDIT_EVENT_OUTSIDE_POPULATION",
                message="Uno o más eventos no pertenecen a la población",
                field_errors={"eventos": ["Uno o más eventos no pertenecen a la población"]},
                status_code=422,
            )
        ids_seleccionados = [i for i in ids_poblacion if i in elegidos]
    else:
        tamano = datos.tamano or 0
        if tamano < 1 or tamano > min(500, n_poblacion):
            raise KontrolError(
                code="GOV_AUDIT_INVALID_SAMPLE_SIZE",
                message="El tamaño de la muestra aleatoria no es válido",
                field_errors={"tamano": ["El tamaño debe estar entre 1 y el mínimo de 500 y la población"]},
                status_code=422,
            )
        semilla = datos.semilla or (secrets.randbelow(999_999_999) + 1)
        posiciones = sorted(random.Random(semilla).sample(range(n_poblacion), tamano))
        ids_seleccionados = [ids_poblacion[p] for p in posiciones]

    hoy = hoy_de_negocio()
    año = hoy.year
    prefijo = f"MU-{año}-"
    numero = 1 + (
        db.scalar(
            select(func.count()).where(
                GovernmentAuditSample.tenant_id == ctx.tenant_id,
                GovernmentAuditSample.company_id == ctx.company_id,
                GovernmentAuditSample.codigo.like(f"{prefijo}%"),
            )
        )
        or 0
    )
    codigo = f"MU-{año}-{numero:04d}"

    filtros_serializados: dict[str, Any] = {}
    if datos.filtros.desde:
        filtros_serializados["desde"] = datos.filtros.desde.isoformat()
    if datos.filtros.hasta:
        filtros_serializados["hasta"] = datos.filtros.hasta.isoformat()
    if datos.filtros.proceso:
        filtros_serializados["proceso"] = datos.filtros.proceso
    if datos.filtros.accion:
        filtros_serializados["accion"] = datos.filtros.accion
    if datos.filtros.usuario:
        filtros_serializados["usuario"] = datos.filtros.usuario
    if datos.filtros.texto:
        filtros_serializados["texto"] = datos.filtros.texto

    muestra = GovernmentAuditSample(
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        codigo=codigo,
        titulo=datos.titulo,
        criterio=datos.criterio,
        justificacion=datos.justificacion,
        metodo=metodo,
        semilla=semilla if metodo == "ALEATORIA" else None,
        tamano=len(ids_seleccionados),
        poblacion=n_poblacion,
        filtros=filtros_serializados,
        created_by=ctx.user_id,
        created_at=datetime.now(UTC),
    )
    db.add(muestra)
    db.flush()

    for orden, event_id in enumerate(ids_seleccionados, start=1):
        db.add(
            GovernmentAuditSampleItem(
                sample_id=muestra.id,
                company_id=ctx.company_id,
                audit_event_id=event_id,
                orden=orden,
            )
        )
    db.flush()

    record_audit(
        db,
        action="GOV_AUDIT_SAMPLE_CREATED",
        entity_type="GovernmentAuditSample",
        entity_id=str(muestra.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={
            "codigo": muestra.codigo,
            "metodo": muestra.metodo,
            "tamano": muestra.tamano,
            "poblacion": muestra.poblacion,
            "semilla": muestra.semilla,
            "filtros": muestra.filtros,
        },
    )

    return obtener_muestra(db, ctx, str(muestra.id))


def listar_muestras(db: Session, ctx: CompanyContext) -> dict[str, Any]:
    """Lista las muestras de auditoría de la empresa activa, más recientes primero."""
    muestras = db.scalars(
        select(GovernmentAuditSample)
        .where(
            GovernmentAuditSample.tenant_id == ctx.tenant_id,
            GovernmentAuditSample.company_id == ctx.company_id,
        )
        .order_by(GovernmentAuditSample.created_at.desc(), GovernmentAuditSample.id.desc())
    ).all()
    return {"items": [_muestra_serializada(db, muestra) for muestra in muestras]}


def obtener_muestra(db: Session, ctx: CompanyContext, muestra_id: str) -> dict[str, Any]:
    """Devuelve una muestra de auditoría con sus eventos."""
    muestra = db.scalar(
        select(GovernmentAuditSample).where(
            GovernmentAuditSample.id == muestra_id,
            GovernmentAuditSample.tenant_id == ctx.tenant_id,
            GovernmentAuditSample.company_id == ctx.company_id,
        )
    )
    if muestra is None:
        raise NotFoundError(
            code="GOV_AUDIT_SAMPLE_NOT_FOUND",
            message="La muestra no existe en la auditoría de este ente",
        )
    return _muestra_serializada(db, muestra, con_eventos=True)


def exportar_muestra_csv(db: Session, ctx: CompanyContext, muestra_id: str) -> tuple[str, bytes]:
    """Exporta una muestra de auditoría en CSV y registra su exportación."""
    muestra = db.scalar(
        select(GovernmentAuditSample).where(
            GovernmentAuditSample.id == muestra_id,
            GovernmentAuditSample.tenant_id == ctx.tenant_id,
            GovernmentAuditSample.company_id == ctx.company_id,
        )
    )
    if muestra is None:
        raise NotFoundError(
            code="GOV_AUDIT_SAMPLE_NOT_FOUND",
            message="La muestra no existe en la auditoría de este ente",
        )

    salida = io.StringIO()
    escritor = csv.writer(salida, lineterminator="\n")
    encabezados = [
        ("titulo", muestra.titulo),
        ("codigo", muestra.codigo),
        ("metodo", muestra.metodo),
        ("semilla", muestra.semilla),
        ("poblacion", muestra.poblacion),
        ("tamano", muestra.tamano),
        ("criterio", muestra.criterio),
        ("justificacion", muestra.justificacion),
        ("filtros", json.dumps(muestra.filtros or {}, sort_keys=True, ensure_ascii=False)),
        ("registrada_por", _usuario_username(db, muestra) or ""),
        ("registrada_en", _instante(muestra.created_at).isoformat()),
    ]
    for clave, valor in encabezados:
        escritor.writerow([f"# {clave}: {valor}"])
    escritor.writerow([])
    escritor.writerow(
        [
            "orden",
            "fecha",
            "proceso",
            "accion",
            "accion_etiqueta",
            "entidad",
            "entidad_id",
            "usuario",
            "motivo",
            "request_id",
            "detalle",
        ]
    )

    partidas = db.scalars(
        select(GovernmentAuditSampleItem)
        .where(
            GovernmentAuditSampleItem.sample_id == muestra.id,
            GovernmentAuditSampleItem.company_id == muestra.company_id,
        )
        .order_by(GovernmentAuditSampleItem.orden)
    ).all()
    ids = [partida.audit_event_id for partida in partidas]
    por_id: dict[str, AuditEvent] = {}
    if ids:
        por_id = {str(event.id): event for event in db.scalars(select(AuditEvent).where(AuditEvent.id.in_(ids))).all()}
    usuarios = _usuarios_por_ids(
        db,
        (event.user_id for event in por_id.values() if event.user_id is not None),
        muestra.tenant_id,
    )

    for partida in partidas:
        event = por_id.get(partida.audit_event_id)
        if event is None:
            continue
        spec = catalog().get((event.action, event.entity_type))
        etiqueta = spec.label if spec else event.action
        owner_spec = spec.owner_spec if spec else ""
        proceso, _ = _proceso_de(owner_spec)
        detalle, _ = _detalle_de_evento_para_catalogo(event)
        escritor.writerow(
            [
                partida.orden,
                _instante(event.event_time).isoformat(),
                proceso,
                event.action,
                etiqueta,
                event.entity_type,
                event.entity_id,
                usuarios.get(event.user_id) if event.user_id is not None else "",
                event.reason or "",
                event.request_id or "",
                json.dumps(detalle, sort_keys=True, ensure_ascii=False),
            ]
        )

    record_audit(
        db,
        action="GOV_AUDIT_SAMPLE_EXPORTED",
        entity_type="GovernmentAuditSample",
        entity_id=str(muestra.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={"codigo": muestra.codigo, "tamano": muestra.tamano},
    )

    return (f"muestra-{muestra.codigo}.csv", salida.getvalue().encode("utf-8"))


def _usuario_username(db: Session, muestra: GovernmentAuditSample) -> str | None:
    """Devuelve el username del creador de la muestra."""
    if muestra.created_by is None:
        return None
    usuario = db.scalar(
        select(User).where(User.id == muestra.created_by, User.tenant_id == muestra.tenant_id)
    )
    return usuario.username if usuario else None
