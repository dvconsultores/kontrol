"""Servicio de negocio para hallazgos de control gubernamental (CTL-06)."""
import csv
import io
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext
from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.documents.models import Document, DocumentLink
from app.modules.documents.service import freeze_links
from app.modules.government.models import (
    GovernmentAuditSample,
    GovernmentAuditSampleItem,
    GovernmentCorrectiveAction,
    GovernmentCorrectiveActionProgress,
    GovernmentFinding,
    GovernmentFindingEvent,
    GovernmentFindingHistory,
    GovernmentFindingRecommendation,
    GovernmentPosition,
    GovernmentStructure,
    GovernmentUnit,
)
from app.modules.government.schemas_hallazgos import (
    AccionIn,
    AvanceIn,
    DevolucionIn,
    HallazgoIn,
    HallazgosFiltros,
    RecomendacionIn,
    VerificacionIn,
)
from app.modules.government.service_sod import evaluar_antes_de_actuar
from app.modules.identity_access.models import User
from app.shared.audit import record_audit
from app.shared.clock import hoy_de_negocio

ESTADO_ABIERTO = "ABIERTO"
ESTADO_PLAN = "PLAN_DE_ACCION"
ESTADO_REMEDIACION = "EN_REMEDIACION"
ESTADO_EVIDENCIA = "EVIDENCIA_PRESENTADA"
ESTADO_CERRADO = "CERRADO"


def _usuarios_por_ids(db: Session, ids: Iterable[str | None], tenant_id: str | None) -> dict[str, str]:
    """Devuelve usernames por id en una sola consulta."""
    id_list = [i for i in set(ids) if i is not None]
    if not id_list:
        return {}
    filas = db.scalars(select(User).where(User.id.in_(id_list), User.tenant_id == tenant_id)).all()
    return {str(usuario.id): usuario.username for usuario in filas}


def _exigir_estado(hallazgo: GovernmentFinding, *estados: str) -> None:
    """Lanza ConflictError si el hallazgo no está en alguno de los estados permitidos."""
    if hallazgo.estado not in estados:
        raise ConflictError(
            "GOV_FINDING_INVALID_STATE",
            "La operación no es válida en el estado actual del hallazgo",
            details={"estado": hallazgo.estado},
        )


def _para_escribir(db: Session, ctx: CompanyContext, hallazgo_id: str, version: int | None) -> GovernmentFinding:
    """Obtiene un hallazgo para escritura, validando versión y empresa."""
    if version is None:
        raise KontrolError(
            code="GOV_FINDING_IF_MATCH_REQUIRED",
            message="Se requiere la versión actual del hallazgo para poder modificarlo",
            status_code=428,
        )

    hallazgo = db.scalars(
        select(GovernmentFinding)
        .where(
            GovernmentFinding.id == hallazgo_id,
            GovernmentFinding.tenant_id == ctx.tenant_id,
            GovernmentFinding.company_id == ctx.company_id,
        )
        .with_for_update()
    ).first()

    if hallazgo is None:
        raise NotFoundError("GOV_FINDING_NOT_FOUND", "El hallazgo no existe en esta empresa")

    if hallazgo.version != version:
        raise ConflictError(
            "GOV_FINDING_STALE",
            "El hallazgo cambió desde que lo abrió; recárguelo",
            details={"version_actual": hallazgo.version},
        )

    return hallazgo


def _obtener_hallazgo(db: Session, ctx: CompanyContext, hallazgo_id: str) -> GovernmentFinding:
    """Obtiene un hallazgo de la empresa o lanza NotFoundError."""
    hallazgo = db.scalars(
        select(GovernmentFinding).where(
            GovernmentFinding.id == hallazgo_id,
            GovernmentFinding.tenant_id == ctx.tenant_id,
            GovernmentFinding.company_id == ctx.company_id,
        )
    ).first()

    if hallazgo is None:
        raise NotFoundError("GOV_FINDING_NOT_FOUND", "El hallazgo no existe en esta empresa")

    return hallazgo


def _cargo_responsable(db: Session, ctx: CompanyContext, cargo_id: str) -> GovernmentPosition | None:
    """Devuelve el cargo responsable si es vigente y pertenece a la estructura actual."""
    hoy = hoy_de_negocio()
    return db.scalars(
        select(GovernmentPosition)
        .join(GovernmentStructure, GovernmentPosition.structure_id == GovernmentStructure.id)
        .where(
            GovernmentPosition.id == cargo_id,
            GovernmentPosition.company_id == ctx.company_id,
            GovernmentPosition.status == "VIGENTE",
            GovernmentPosition.valid_from <= hoy,
            (GovernmentPosition.valid_to.is_(None)) | (GovernmentPosition.valid_to >= hoy),
            GovernmentStructure.company_id == ctx.company_id,
            GovernmentStructure.status == "VIGENTE",
            GovernmentStructure.exercise == hoy.year,
        )
        .limit(1)
    ).first()


def _accion_vencida(accion: GovernmentCorrectiveAction) -> bool:
    """Indica si una acción está vencida según la regla R14."""
    return accion.fecha_objetivo < hoy_de_negocio() and accion.estado != "COMPLETADA"


def _exigir_otro_verificador(db: Session, hallazgo: GovernmentFinding, ctx: CompanyContext) -> None:
    """Impide que quien presentó o registró avances verifique o devuelva el hallazgo."""
    if ctx.user_id == hallazgo.presentado_por:
        raise ConflictError(
            "GOV_FINDING_SELF_VERIFICATION",
            "Quien registró la evidencia o presentó el hallazgo no puede verificarlo",
        )

    acciones = db.scalars(
        select(GovernmentCorrectiveAction).where(GovernmentCorrectiveAction.finding_id == hallazgo.id)
    ).all()
    for accion in acciones:
        avances = db.scalars(
            select(GovernmentCorrectiveActionProgress).where(
                GovernmentCorrectiveActionProgress.action_id == accion.id,
                GovernmentCorrectiveActionProgress.company_id == ctx.company_id,
            )
        ).all()
        for avance in avances:
            if str(avance.created_by) == str(ctx.user_id):
                raise ConflictError(
                    "GOV_FINDING_SELF_VERIFICATION",
                    "Quien registró la evidencia o presentó el hallazgo no puede verificarlo",
                )


def _documento_vinculado_a_accion(db: Session, ctx: CompanyContext, accion: GovernmentCorrectiveAction, documento_id: str) -> bool:
    """Indica si un documento está activo y vinculado a una acción correctiva."""
    fila = db.execute(
        select(Document, DocumentLink.id)
        .join(DocumentLink, DocumentLink.document_id == Document.id)
        .where(
            Document.id == documento_id,
            Document.company_id == ctx.company_id,
            DocumentLink.resource_type == "GovernmentCorrectiveAction",
            DocumentLink.resource_id == accion.id,
            DocumentLink.company_id == ctx.company_id,
            Document.status == "ACTIVE",
        )
        .limit(1)
    ).first()
    return fila is not None


def _documentos_de_accion(db: Session, accion: GovernmentCorrectiveAction) -> list[str]:
    """Devuelve ids de documentos ACTIVOS vinculados a una acción."""
    filas = db.execute(
        select(Document.id)
        .join(DocumentLink, DocumentLink.document_id == Document.id)
        .where(
            DocumentLink.resource_type == "GovernmentCorrectiveAction",
            DocumentLink.resource_id == accion.id,
            DocumentLink.company_id == accion.company_id,
            Document.status == "ACTIVE",
        )
    ).all()
    return [str(fila[0]) for fila in filas]


def _partidas_de_hallazgo(db: Session, hallazgo: GovernmentFinding) -> list[str]:
    """Devuelve los audit_event_id de las partidas en orden de inserción."""
    filas = db.scalars(
        select(GovernmentFindingEvent)
        .where(GovernmentFindingEvent.finding_id == hallazgo.id)
        .order_by(GovernmentFindingEvent.created_at, GovernmentFindingEvent.id)
    ).all()
    return [fila.audit_event_id for fila in filas]


def _serializar_detalle(db: Session, ctx: CompanyContext, hallazgo: GovernmentFinding) -> dict[str, Any]:
    """Construye el diccionario de detalle de un hallazgo."""
    usuarios = _usuarios_por_ids(
        db,
        [
            hallazgo.created_by,
            hallazgo.presentado_por,
            hallazgo.verificado_por,
        ],
        ctx.tenant_id,
    )

    recomendaciones = db.scalars(
        select(GovernmentFindingRecommendation)
        .where(GovernmentFindingRecommendation.finding_id == hallazgo.id)
        .order_by(GovernmentFindingRecommendation.orden)
    ).all()
    recomendaciones_out = []
    usuarios_recomendacion = _usuarios_por_ids(db, [r.created_by for r in recomendaciones], ctx.tenant_id)
    for r in recomendaciones:
        recomendaciones_out.append(
            {
                "id": str(r.id),
                "orden": r.orden,
                "texto": r.texto,
                "created_by": usuarios_recomendacion.get(str(r.created_by)),
                "created_at": r.created_at,
            }
        )

    acciones = db.scalars(
        select(GovernmentCorrectiveAction)
        .where(GovernmentCorrectiveAction.finding_id == hallazgo.id)
        .order_by(GovernmentCorrectiveAction.orden)
    ).all()
    acciones_out = []
    for a in acciones:
        avances = db.scalars(
            select(GovernmentCorrectiveActionProgress)
            .where(GovernmentCorrectiveActionProgress.action_id == a.id)
            .order_by(GovernmentCorrectiveActionProgress.created_at)
        ).all()
        usuarios_avances = _usuarios_por_ids(db, [p.created_by for p in avances], ctx.tenant_id)
        avances_out = [
            {
                "id": str(p.id),
                "nota": p.nota,
                "porcentaje": p.porcentaje,
                "documento_id": str(p.document_id) if p.document_id else None,
                "created_by": usuarios_avances.get(str(p.created_by)),
                "created_at": p.created_at,
            }
            for p in avances
        ]
        acciones_out.append(
            {
                "id": str(a.id),
                "recomendacion_id": str(a.recommendation_id),
                "orden": a.orden,
                "descripcion": a.descripcion,
                "cargo_id": str(a.position_id),
                "cargo_codigo": a.cargo_codigo,
                "cargo_denominacion": a.cargo_denominacion,
                "unidad_id": str(a.unidad_id),
                "unidad_nombre": a.unidad_nombre,
                "ejercicio": a.ejercicio,
                "fecha_objetivo": a.fecha_objetivo,
                "porcentaje": a.porcentaje,
                "estado": a.estado,
                "vencida": _accion_vencida(a),
                "documentos": _documentos_de_accion(db, a),
                "avances": avances_out,
            }
        )

    historia = db.scalars(
        select(GovernmentFindingHistory)
        .where(GovernmentFindingHistory.finding_id == hallazgo.id)
        .order_by(GovernmentFindingHistory.created_at, GovernmentFindingHistory.id)
    ).all()
    usuarios_historia = _usuarios_por_ids(db, [h.created_by for h in historia], ctx.tenant_id)
    historia_out = [
        {
            "id": str(h.id),
            "tipo": h.tipo,
            "estado_desde": h.estado_desde,
            "estado_hasta": h.estado_hasta,
            "detalle": h.detalle,
            "created_by": usuarios_historia.get(str(h.created_by)),
            "created_at": h.created_at,
        }
        for h in historia
    ]

    muestra = None
    if hallazgo.sample_id:
        muestra_obj = db.scalars(
            select(GovernmentAuditSample).where(GovernmentAuditSample.id == hallazgo.sample_id)
        ).first()
        if muestra_obj:
            muestra = {
                "id": str(muestra_obj.id),
                "codigo": muestra_obj.codigo,
                "titulo": muestra_obj.titulo,
            }

    return {
        "id": str(hallazgo.id),
        "codigo": hallazgo.codigo,
        "titulo": hallazgo.titulo,
        "condicion": hallazgo.condicion,
        "criterio": hallazgo.criterio,
        "causa": hallazgo.causa,
        "efecto": hallazgo.efecto,
        "riesgo": hallazgo.riesgo,
        "origen": hallazgo.origen,
        "origen_descripcion": hallazgo.origen_descripcion,
        "muestra": muestra,
        "partidas": _partidas_de_hallazgo(db, hallazgo),
        "estado": hallazgo.estado,
        "version": hallazgo.version,
        "presentado_por": usuarios.get(str(hallazgo.presentado_por)) if hallazgo.presentado_por else None,
        "presentado_en": hallazgo.presentado_en,
        "verificado_por": usuarios.get(str(hallazgo.verificado_por)) if hallazgo.verificado_por else None,
        "verificado_en": hallazgo.verificado_en,
        "nota_verificacion": hallazgo.nota_verificacion,
        "created_by": usuarios.get(str(hallazgo.created_by)) if hallazgo.created_by else None,
        "created_at": hallazgo.created_at,
        "recomendaciones": recomendaciones_out,
        "acciones": acciones_out,
        "historia": historia_out,
    }


def _registrar_historia(
    db: Session,
    hallazgo: GovernmentFinding,
    tipo: str,
    estado_desde: str | None,
    estado_hasta: str | None,
    detalle: dict | None,
    created_by: str,
) -> None:
    """Crea una fila de historia para un hallazgo (solo add)."""
    db.add(
        GovernmentFindingHistory(
            finding_id=hallazgo.id,
            company_id=hallazgo.company_id,
            tipo=tipo,
            estado_desde=estado_desde,
            estado_hasta=estado_hasta,
            detalle=detalle,
            created_by=created_by,
        )
    )


def _finalizar_escritura(
    db: Session,
    ctx: CompanyContext,
    hallazgo: GovernmentFinding,
    tipo_historia: str,
    estado_desde: str | None,
    estado_hasta: str | None,
    detalle: dict | None,
    action_audit: str,
    after_audit: dict[str, Any],
) -> dict[str, Any]:
    """Incrementa versión, registra historia y auditoría, y devuelve el detalle."""
    hallazgo.version += 1
    hallazgo.updated_at = datetime.now(UTC)
    _registrar_historia(db, hallazgo, tipo_historia, estado_desde, estado_hasta, detalle, ctx.user_id)
    db.flush()
    record_audit(
        db,
        action=action_audit,
        entity_type="GovernmentFinding",
        entity_id=str(hallazgo.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after=after_audit,
    )
    return _serializar_detalle(db, ctx, hallazgo)


def listar(db: Session, ctx: CompanyContext, filtros: HallazgosFiltros, pagina: int, por_pagina: int) -> dict[str, Any]:
    """Lista hallazgos paginados con filtros y resumen global."""
    condicion = [
        GovernmentFinding.tenant_id == ctx.tenant_id,
        GovernmentFinding.company_id == ctx.company_id,
    ]

    if filtros.estado:
        condicion.append(GovernmentFinding.estado == filtros.estado)
    if filtros.riesgo:
        condicion.append(GovernmentFinding.riesgo == filtros.riesgo)
    if filtros.origen:
        condicion.append(GovernmentFinding.origen == filtros.origen)
    if filtros.texto:
        texto = f"%{filtros.texto}%"
        condicion.append(
            (GovernmentFinding.codigo.ilike(texto)) | (GovernmentFinding.titulo.ilike(texto))
        )

    query = select(GovernmentFinding).where(*condicion)

    if filtros.vencidas:
        sub_acciones_vencidas = (
            select(GovernmentCorrectiveAction.finding_id)
            .where(
                GovernmentCorrectiveAction.fecha_objetivo < hoy_de_negocio(),
                GovernmentCorrectiveAction.estado != "COMPLETADA",
            )
            .distinct()
        )
        query = query.where(GovernmentFinding.id.in_(sub_acciones_vencidas))

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0

    hallazgos = db.scalars(
        query.order_by(GovernmentFinding.created_at.desc(), GovernmentFinding.id.desc())
        .offset((pagina - 1) * por_pagina)
        .limit(por_pagina)
    ).all()

    items = []
    for h in hallazgos:
        acciones = db.scalars(
            select(GovernmentCorrectiveAction).where(GovernmentCorrectiveAction.finding_id == h.id)
        ).all()
        acciones_total = len(acciones)
        acciones_vencidas = sum(1 for a in acciones if _accion_vencida(a))
        items.append(
            {
                "id": str(h.id),
                "codigo": h.codigo,
                "titulo": h.titulo,
                "riesgo": h.riesgo,
                "estado": h.estado,
                "origen": h.origen,
                "acciones_total": acciones_total,
                "acciones_vencidas": acciones_vencidas,
                "created_at": h.created_at,
            }
        )

    abiertos = db.scalar(
        select(func.count())
        .select_from(GovernmentFinding)
        .where(
            GovernmentFinding.tenant_id == ctx.tenant_id,
            GovernmentFinding.company_id == ctx.company_id,
            GovernmentFinding.estado != ESTADO_CERRADO,
        )
    ) or 0
    pendientes_verificacion = db.scalar(
        select(func.count())
        .select_from(GovernmentFinding)
        .where(
            GovernmentFinding.tenant_id == ctx.tenant_id,
            GovernmentFinding.company_id == ctx.company_id,
            GovernmentFinding.estado == ESTADO_EVIDENCIA,
        )
    ) or 0
    acciones_vencidas = db.scalar(
        select(func.count())
        .select_from(GovernmentCorrectiveAction)
        .join(
            GovernmentFinding,
            GovernmentCorrectiveAction.finding_id == GovernmentFinding.id,
        )
        .where(
            GovernmentFinding.tenant_id == ctx.tenant_id,
            GovernmentFinding.company_id == ctx.company_id,
            GovernmentCorrectiveAction.fecha_objetivo < hoy_de_negocio(),
            GovernmentCorrectiveAction.estado != "COMPLETADA",
        )
    ) or 0
    cerrados = db.scalar(
        select(func.count())
        .select_from(GovernmentFinding)
        .where(
            GovernmentFinding.tenant_id == ctx.tenant_id,
            GovernmentFinding.company_id == ctx.company_id,
            GovernmentFinding.estado == ESTADO_CERRADO,
        )
    ) or 0

    return {
        "items": items,
        "total": total,
        "pagina": pagina,
        "por_pagina": por_pagina,
        "resumen": {
            "abiertos": abiertos,
            "pendientes_verificacion": pendientes_verificacion,
            "acciones_vencidas": acciones_vencidas,
            "cerrados": cerrados,
        },
    }


def cargos_responsables(db: Session, ctx: CompanyContext) -> dict[str, Any]:
    """Lista cargos responsables vigentes de la empresa."""
    hoy = hoy_de_negocio()
    filas = db.execute(
        select(GovernmentPosition, GovernmentUnit.name, GovernmentStructure.exercise)
        .join(GovernmentStructure, GovernmentPosition.structure_id == GovernmentStructure.id)
        .join(GovernmentUnit, GovernmentPosition.unit_id == GovernmentUnit.id)
        .where(
            GovernmentPosition.company_id == ctx.company_id,
            GovernmentPosition.status == "VIGENTE",
            GovernmentPosition.valid_from <= hoy,
            (GovernmentPosition.valid_to.is_(None)) | (GovernmentPosition.valid_to >= hoy),
            GovernmentStructure.company_id == ctx.company_id,
            GovernmentStructure.status == "VIGENTE",
            GovernmentStructure.exercise == hoy.year,
        )
        .order_by(GovernmentPosition.code)
    ).all()

    return {
        "items": [
            {
                "id": str(c.id),
                "codigo": c.code,
                "denominacion": c.name,
                "unidad_nombre": unidad_nombre,
                "ejercicio": ejercicio,
            }
            for c, unidad_nombre, ejercicio in filas
        ]
    }


def registrar(db: Session, ctx: CompanyContext, datos: HallazgoIn) -> dict[str, Any]:
    """Registra un nuevo hallazgo."""
    if datos.origen == "MUESTRA":
        muestra = db.scalars(
            select(GovernmentAuditSample).where(
                GovernmentAuditSample.id == datos.muestra_id,
                GovernmentAuditSample.tenant_id == ctx.tenant_id,
                GovernmentAuditSample.company_id == ctx.company_id,
            )
        ).first()
        if muestra is None:
            raise KontrolError(
                code="GOV_FINDING_SOURCE_INVALID",
                message="El origen no pertenece a esta empresa",
                field_errors={"muestra_id": ["La muestra no existe en esta empresa"]},
                status_code=422,
            )

        partidas_invalidas = []
        for partida in datos.partidas:
            item = db.scalars(
                select(GovernmentAuditSampleItem).where(
                    GovernmentAuditSampleItem.sample_id == muestra.id,
                    GovernmentAuditSampleItem.audit_event_id == partida,
                )
            ).first()
            if item is None:
                partidas_invalidas.append(partida)
        if partidas_invalidas:
            raise KontrolError(
                code="GOV_FINDING_SOURCE_INVALID",
                message="El origen no pertenece a esta empresa",
                field_errors={"partidas": [f"Partida inválida: {p}" for p in partidas_invalidas]},
                status_code=422,
            )

    anio = hoy_de_negocio().year
    prefijo = f"HA-{anio}-"
    n = db.scalar(
        select(func.count())
        .select_from(GovernmentFinding)
        .where(
            GovernmentFinding.company_id == ctx.company_id,
            GovernmentFinding.codigo.like(f"{prefijo}%"),
        )
    ) or 0

    hallazgo = GovernmentFinding(
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        codigo=f"{prefijo}{n + 1:04d}",
        titulo=datos.titulo,
        condicion=datos.condicion,
        criterio=datos.criterio,
        causa=datos.causa,
        efecto=datos.efecto,
        riesgo=datos.riesgo,
        origen=datos.origen,
        sample_id=datos.muestra_id,
        origen_descripcion=datos.origen_descripcion,
        estado=ESTADO_ABIERTO,
        version=1,
        created_by=ctx.user_id,
    )
    db.add(hallazgo)
    db.flush()

    for partida in datos.partidas:
        db.add(
            GovernmentFindingEvent(
                finding_id=hallazgo.id,
                company_id=ctx.company_id,
                audit_event_id=partida,
            )
        )

    _registrar_historia(db, hallazgo, "CREADO", None, ESTADO_ABIERTO, None, ctx.user_id)
    db.flush()

    record_audit(
        db,
        action="GOV_FINDING_CREATED",
        entity_type="GovernmentFinding",
        entity_id=str(hallazgo.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={
            "codigo": hallazgo.codigo,
            "riesgo": hallazgo.riesgo,
            "origen": hallazgo.origen,
            "muestra_id": hallazgo.sample_id,
            "partidas": len(datos.partidas),
        },
    )

    return _serializar_detalle(db, ctx, hallazgo)


def detalle(db: Session, ctx: CompanyContext, hallazgo_id: str) -> dict[str, Any]:
    """Obtiene el detalle de un hallazgo."""
    hallazgo = _obtener_hallazgo(db, ctx, hallazgo_id)
    return _serializar_detalle(db, ctx, hallazgo)


def agregar_recomendacion(
    db: Session, ctx: CompanyContext, hallazgo_id: str, datos: RecomendacionIn, version: int | None
) -> dict[str, Any]:
    """Agrega una recomendación a un hallazgo abierto."""
    hallazgo = _para_escribir(db, ctx, hallazgo_id, version)
    _exigir_estado(hallazgo, ESTADO_ABIERTO)

    orden = db.scalar(
        select(func.count())
        .select_from(GovernmentFindingRecommendation)
        .where(GovernmentFindingRecommendation.finding_id == hallazgo.id)
    ) or 0
    recomendacion = GovernmentFindingRecommendation(
        finding_id=hallazgo.id,
        company_id=ctx.company_id,
        orden=orden + 1,
        texto=datos.texto,
        created_by=ctx.user_id,
    )
    evaluar_antes_de_actuar(db, ctx, "CTL06_RECOMENDAR", "GovernmentFinding", str(hallazgo.id))

    db.add(recomendacion)
    db.flush()

    return _finalizar_escritura(
        db,
        ctx,
        hallazgo,
        "RECOMENDACION",
        None,
        None,
        {"recomendacion_id": str(recomendacion.id), "orden": recomendacion.orden},
        "GOV_FINDING_RECOMMENDATION_ADDED",
        {"codigo": hallazgo.codigo, "recomendacion_id": str(recomendacion.id), "orden": recomendacion.orden},
    )


def agregar_accion(
    db: Session, ctx: CompanyContext, hallazgo_id: str, datos: AccionIn, version: int | None
) -> dict[str, Any]:
    """Agrega una acción correctiva a un hallazgo abierto."""
    hallazgo = _para_escribir(db, ctx, hallazgo_id, version)
    _exigir_estado(hallazgo, ESTADO_ABIERTO)

    recomendacion = db.scalars(
        select(GovernmentFindingRecommendation).where(
            GovernmentFindingRecommendation.id == datos.recomendacion_id,
            GovernmentFindingRecommendation.finding_id == hallazgo.id,
        )
    ).first()
    if recomendacion is None:
        raise KontrolError(
            code="GOV_FINDING_RECOMMENDATION_INVALID",
            message="La recomendación no pertenece al hallazgo",
            field_errors={"recomendacion_id": ["La recomendación no existe en este hallazgo"]},
            status_code=422,
        )

    cargo = _cargo_responsable(db, ctx, datos.cargo_id)
    if cargo is None:
        raise KontrolError(
            code="GOV_FINDING_RESPONSIBLE_INVALID",
            message="El cargo responsable no es válido para esta empresa",
            field_errors={"cargo_id": ["El cargo no es vigente o no pertenece a la empresa"]},
            status_code=422,
        )

    hoy = hoy_de_negocio()
    if datos.fecha_objetivo < hoy:
        raise KontrolError(
            code="GOV_FINDING_TARGET_DATE_INVALID",
            message="La fecha objetivo no puede ser anterior a la fecha actual",
            field_errors={"fecha_objetivo": ["La fecha es anterior a hoy"]},
            status_code=422,
        )

    orden = db.scalar(
        select(func.count())
        .select_from(GovernmentCorrectiveAction)
        .where(GovernmentCorrectiveAction.finding_id == hallazgo.id)
    ) or 0

    unidad = db.get(GovernmentUnit, cargo.unit_id)
    estructura = db.get(GovernmentStructure, cargo.structure_id)
    if (
        unidad is None
        or estructura is None
        or unidad.company_id != ctx.company_id
        or estructura.company_id != ctx.company_id
    ):
        raise KontrolError(
            code="GOV_FINDING_RESPONSIBLE_INVALID",
            message="El cargo responsable no es válido para esta empresa",
            field_errors={"cargo_id": ["El cargo no es vigente o no pertenece a la empresa"]},
            status_code=422,
        )
    accion = GovernmentCorrectiveAction(
        finding_id=hallazgo.id,
        recommendation_id=recomendacion.id,
        company_id=ctx.company_id,
        orden=orden + 1,
        descripcion=datos.descripcion,
        position_id=cargo.id,
        cargo_codigo=cargo.code,
        cargo_denominacion=cargo.name,
        unidad_id=cargo.unit_id,
        unidad_nombre=unidad.name,
        ejercicio=estructura.exercise,
        fecha_objetivo=datos.fecha_objetivo,
        porcentaje=0,
        estado="PENDIENTE",
        created_by=ctx.user_id,
    )
    evaluar_antes_de_actuar(db, ctx, "CTL06_ACCION", "GovernmentFinding", str(hallazgo.id))

    db.add(accion)
    db.flush()

    return _finalizar_escritura(
        db,
        ctx,
        hallazgo,
        "ACCION",
        None,
        None,
        {
            "accion_id": str(accion.id),
            "cargo_codigo": accion.cargo_codigo,
            "fecha_objetivo": accion.fecha_objetivo.isoformat(),
        },
        "GOV_CORRECTIVE_ACTION_ADDED",
        {
            "codigo": hallazgo.codigo,
            "accion_id": str(accion.id),
            "cargo_id": str(datos.cargo_id),
            "fecha_objetivo": datos.fecha_objetivo.isoformat(),
        },
    )


def registrar_plan(db: Session, ctx: CompanyContext, hallazgo_id: str, version: int | None) -> dict[str, Any]:
    """Registra el plan de acción de un hallazgo abierto."""
    hallazgo = _para_escribir(db, ctx, hallazgo_id, version)
    _exigir_estado(hallazgo, ESTADO_ABIERTO)

    recomendaciones = db.scalars(
        select(GovernmentFindingRecommendation).where(
            GovernmentFindingRecommendation.finding_id == hallazgo.id
        )
    ).all()
    if not recomendaciones:
        raise ConflictError(
            "GOV_FINDING_PLAN_INCOMPLETE",
            "Cada recomendación necesita al menos una acción correctiva",
        )

    for r in recomendaciones:
        n_acciones = db.scalar(
            select(func.count())
            .select_from(GovernmentCorrectiveAction)
            .where(
                GovernmentCorrectiveAction.finding_id == hallazgo.id,
                GovernmentCorrectiveAction.recommendation_id == r.id,
            )
        ) or 0
        if n_acciones == 0:
            raise ConflictError(
                "GOV_FINDING_PLAN_INCOMPLETE",
                "Cada recomendación necesita al menos una acción correctiva",
            )

    evaluar_antes_de_actuar(db, ctx, "CTL06_PLAN", "GovernmentFinding", str(hallazgo.id))

    estado_anterior = hallazgo.estado
    hallazgo.estado = ESTADO_PLAN

    return _finalizar_escritura(
        db,
        ctx,
        hallazgo,
        "PLAN",
        estado_anterior,
        ESTADO_PLAN,
        None,
        "GOV_FINDING_PLAN_REGISTERED",
        {"codigo": hallazgo.codigo, "estado": ESTADO_PLAN},
    )


def iniciar_ejecucion(db: Session, ctx: CompanyContext, hallazgo_id: str, version: int | None) -> dict[str, Any]:
    """Inicia la ejecución de un hallazgo con plan de acción."""
    hallazgo = _para_escribir(db, ctx, hallazgo_id, version)
    _exigir_estado(hallazgo, ESTADO_PLAN)

    evaluar_antes_de_actuar(db, ctx, "CTL06_EJECUCION", "GovernmentFinding", str(hallazgo.id))

    estado_anterior = hallazgo.estado
    hallazgo.estado = ESTADO_REMEDIACION

    return _finalizar_escritura(
        db,
        ctx,
        hallazgo,
        "EJECUCION",
        estado_anterior,
        ESTADO_REMEDIACION,
        None,
        "GOV_FINDING_REMEDIATION_STARTED",
        {"codigo": hallazgo.codigo, "estado": ESTADO_REMEDIACION},
    )


def registrar_avance(
    db: Session,
    ctx: CompanyContext,
    hallazgo_id: str,
    accion_id: str,
    datos: AvanceIn,
    version: int | None,
) -> dict[str, Any]:
    """Registra un avance de una acción en remediación."""
    hallazgo = _para_escribir(db, ctx, hallazgo_id, version)
    _exigir_estado(hallazgo, ESTADO_REMEDIACION)

    accion = db.scalars(
        select(GovernmentCorrectiveAction).where(
            GovernmentCorrectiveAction.id == accion_id,
            GovernmentCorrectiveAction.finding_id == hallazgo.id,
            GovernmentCorrectiveAction.company_id == ctx.company_id,
        )
    ).first()
    if accion is None:
        raise NotFoundError(
            "GOV_FINDING_ACTION_NOT_FOUND",
            "La acción correctiva no existe en este hallazgo",
        )

    if datos.porcentaje < accion.porcentaje:
        raise KontrolError(
            code="GOV_FINDING_PROGRESS_INVALID",
            message="El porcentaje no puede ser menor al registrado previamente",
            field_errors={"porcentaje": ["El porcentaje no puede disminuir"]},
            status_code=422,
        )

    documento_id = None
    if datos.documento_id:
        if not _documento_vinculado_a_accion(db, ctx, accion, datos.documento_id):
            raise KontrolError(
                code="GOV_FINDING_EVIDENCE_INVALID",
                message="El documento no es una evidencia válida para esta acción",
                field_errors={"documento_id": ["El documento no está vinculado a esta acción"]},
                status_code=422,
            )
        documento_id = datos.documento_id

    if datos.porcentaje == 100 and not _documentos_de_accion(db, accion):
        raise KontrolError(
            code="GOV_FINDING_EVIDENCE_REQUIRED",
            message="Se requiere un documento de evidencia para completar la acción",
            field_errors={"documento_id": ["Documento de evidencia requerido"]},
            status_code=422,
        )

    avance = GovernmentCorrectiveActionProgress(
        action_id=accion.id,
        company_id=ctx.company_id,
        nota=datos.nota,
        porcentaje=datos.porcentaje,
        document_id=documento_id,
        created_by=ctx.user_id,
    )
    evaluar_antes_de_actuar(db, ctx, "CTL06_AVANCE", "GovernmentFinding", str(hallazgo.id))

    db.add(avance)

    accion.porcentaje = datos.porcentaje
    if datos.porcentaje == 0:
        accion.estado = "PENDIENTE"
    elif 1 <= datos.porcentaje <= 99:
        accion.estado = "EN_CURSO"
    else:
        accion.estado = "COMPLETADA"

    db.flush()

    return _finalizar_escritura(
        db,
        ctx,
        hallazgo,
        "AVANCE",
        None,
        None,
        {
            "accion_id": str(accion.id),
            "porcentaje": datos.porcentaje,
            "documento_id": str(documento_id) if documento_id else None,
        },
        "GOV_CORRECTIVE_ACTION_PROGRESS_RECORDED",
        {
            "codigo": hallazgo.codigo,
            "accion_id": str(accion.id),
            "porcentaje": datos.porcentaje,
            "documento_id": str(documento_id) if documento_id else None,
        },
    )


def presentar(db: Session, ctx: CompanyContext, hallazgo_id: str, version: int | None) -> dict[str, Any]:
    """Presenta evidencia de un hallazgo en remediación."""
    hallazgo = _para_escribir(db, ctx, hallazgo_id, version)
    _exigir_estado(hallazgo, ESTADO_REMEDIACION)

    acciones = db.scalars(
        select(GovernmentCorrectiveAction).where(GovernmentCorrectiveAction.finding_id == hallazgo.id)
    ).all()
    if any(a.estado != "COMPLETADA" for a in acciones):
        raise ConflictError(
            "GOV_FINDING_ACTIONS_INCOMPLETE",
            "Todas las acciones correctivas deben estar completadas antes de presentar el hallazgo",
        )

    evaluar_antes_de_actuar(db, ctx, "CTL06_PRESENTAR", "GovernmentFinding", str(hallazgo.id))

    estado_anterior = hallazgo.estado
    hallazgo.estado = ESTADO_EVIDENCIA
    hallazgo.presentado_por = ctx.user_id
    hallazgo.presentado_en = datetime.now(UTC)

    return _finalizar_escritura(
        db,
        ctx,
        hallazgo,
        "PRESENTADO",
        estado_anterior,
        ESTADO_EVIDENCIA,
        None,
        "GOV_FINDING_SUBMITTED",
        {"codigo": hallazgo.codigo, "estado": ESTADO_EVIDENCIA},
    )


def verificar(
    db: Session,
    ctx: CompanyContext,
    hallazgo_id: str,
    datos: VerificacionIn,
    version: int | None,
    actor: User,
) -> dict[str, Any]:
    """Verifica y cierra un hallazgo con evidencia presentada."""
    hallazgo = _para_escribir(db, ctx, hallazgo_id, version)
    _exigir_estado(hallazgo, ESTADO_EVIDENCIA)
    _exigir_otro_verificador(db, hallazgo, ctx)

    evaluar_antes_de_actuar(db, ctx, "CTL06_VERIFICAR", "GovernmentFinding", str(hallazgo.id))

    estado_anterior = hallazgo.estado
    hallazgo.estado = ESTADO_CERRADO
    hallazgo.verificado_por = ctx.user_id
    hallazgo.verificado_en = datetime.now(UTC)
    hallazgo.nota_verificacion = datos.nota

    acciones = db.scalars(
        select(GovernmentCorrectiveAction).where(GovernmentCorrectiveAction.finding_id == hallazgo.id)
    ).all()
    db.flush()
    for accion in acciones:
        freeze_links(
            db,
            resource_type="GovernmentCorrectiveAction",
            resource_id=str(accion.id),
            actor=actor,
        )

    return _finalizar_escritura(
        db,
        ctx,
        hallazgo,
        "VERIFICADO",
        estado_anterior,
        ESTADO_CERRADO,
        {"nota": datos.nota},
        "GOV_FINDING_VERIFIED",
        {"codigo": hallazgo.codigo, "estado": ESTADO_CERRADO},
    )


def devolver(
    db: Session,
    ctx: CompanyContext,
    hallazgo_id: str,
    datos: DevolucionIn,
    version: int | None,
) -> dict[str, Any]:
    """Devuelve un hallazgo con evidencia presentada a remediación."""
    hallazgo = _para_escribir(db, ctx, hallazgo_id, version)
    _exigir_estado(hallazgo, ESTADO_EVIDENCIA)
    _exigir_otro_verificador(db, hallazgo, ctx)

    evaluar_antes_de_actuar(db, ctx, "CTL06_DEVOLVER", "GovernmentFinding", str(hallazgo.id))

    estado_anterior = hallazgo.estado
    hallazgo.estado = ESTADO_REMEDIACION
    hallazgo.presentado_por = None
    hallazgo.presentado_en = None

    return _finalizar_escritura(
        db,
        ctx,
        hallazgo,
        "DEVUELTO",
        estado_anterior,
        ESTADO_REMEDIACION,
        {"motivo": datos.motivo},
        "GOV_FINDING_RETURNED",
        {"codigo": hallazgo.codigo, "estado": ESTADO_REMEDIACION},
    )


def exportar_csv(db: Session, ctx: CompanyContext, filtros: HallazgosFiltros) -> tuple[str, bytes]:
    """Exporta el plan de acciones a CSV."""
    condicion = [
        GovernmentFinding.tenant_id == ctx.tenant_id,
        GovernmentFinding.company_id == ctx.company_id,
    ]
    if filtros.estado:
        condicion.append(GovernmentFinding.estado == filtros.estado)
    if filtros.riesgo:
        condicion.append(GovernmentFinding.riesgo == filtros.riesgo)
    if filtros.origen:
        condicion.append(GovernmentFinding.origen == filtros.origen)
    if filtros.texto:
        texto = f"%{filtros.texto}%"
        condicion.append(
            (GovernmentFinding.codigo.ilike(texto)) | (GovernmentFinding.titulo.ilike(texto))
        )

    query = select(GovernmentFinding).where(*condicion)

    if filtros.vencidas:
        sub_acciones_vencidas = (
            select(GovernmentCorrectiveAction.finding_id)
            .where(
                GovernmentCorrectiveAction.fecha_objetivo < hoy_de_negocio(),
                GovernmentCorrectiveAction.estado != "COMPLETADA",
            )
            .distinct()
        )
        query = query.where(GovernmentFinding.id.in_(sub_acciones_vencidas))

    hallazgos = db.scalars(query.order_by(GovernmentFinding.created_at.desc(), GovernmentFinding.id.desc())).all()

    salida = io.StringIO()
    writer = csv.writer(salida)
    writer.writerow(
        [
            "codigo",
            "titulo",
            "riesgo",
            "estado",
            "recomendacion",
            "accion",
            "cargo_codigo",
            "cargo_denominacion",
            "unidad",
            "fecha_objetivo",
            "porcentaje",
            "estado_accion",
            "vencida",
        ]
    )

    filas_exportadas = 0
    for h in hallazgos:
        acciones = db.scalars(
            select(GovernmentCorrectiveAction)
            .where(GovernmentCorrectiveAction.finding_id == h.id)
            .order_by(GovernmentCorrectiveAction.orden)
        ).all()
        if not acciones:
            writer.writerow(
                [
                    h.codigo,
                    h.titulo,
                    h.riesgo,
                    h.estado,
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                ]
            )
            filas_exportadas += 1
        else:
            for a in acciones:
                recomendacion = db.scalars(
                    select(GovernmentFindingRecommendation).where(
                        GovernmentFindingRecommendation.id == a.recommendation_id
                    )
                ).first()
                writer.writerow(
                    [
                        h.codigo,
                        h.titulo,
                        h.riesgo,
                        h.estado,
                        recomendacion.texto if recomendacion else "",
                        a.descripcion,
                        a.cargo_codigo,
                        a.cargo_denominacion,
                        a.unidad_nombre,
                        a.fecha_objetivo.isoformat(),
                        a.porcentaje,
                        a.estado,
                        "SI" if _accion_vencida(a) else "NO",
                    ]
                )
                filas_exportadas += 1

    hoy = hoy_de_negocio()
    nombre = f"plan-acciones-{hoy.isoformat()}.csv"
    filtros_dict: dict[str, Any] = {
        "estado": filtros.estado,
        "riesgo": filtros.riesgo,
        "origen": filtros.origen,
        "texto": filtros.texto,
    }
    filtros_no_nulos = {k: v for k, v in filtros_dict.items() if v is not None}
    if filtros.vencidas:
        filtros_no_nulos["vencidas"] = True

    record_audit(
        db,
        action="GOV_FINDINGS_EXPORTED",
        entity_type="GovernmentFinding",
        entity_id=ctx.company_id,
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={"filas": filas_exportadas, "filtros": filtros_no_nulos},
    )

    return nombre, salida.getvalue().encode("utf-8")
