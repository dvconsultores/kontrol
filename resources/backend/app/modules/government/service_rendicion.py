"""Servicio de rendición de cuentas (CTL-05)."""

from __future__ import annotations

import csv
import hashlib
import io
import json
from datetime import date, datetime, timedelta
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext
from app.core.errors import ConflictError, KontrolError
from app.modules.audit.models import AuditEvent
from app.modules.documents.models import DocumentVersion
from app.modules.documents.storage import generate_storage_key, get_storage
from app.modules.government.models import (
    GovernmentAssignment,
    GovernmentEntity,
    GovernmentOfficial,
    GovernmentPosition,
    GovernmentRenditionFile,
    GovernmentRenditionPiece,
    GovernmentUnit,
)
from app.modules.government.schemas_auditoria import AuditoriaFiltrosPoblacion
from app.modules.government.service_auditoria import (
    PROCESOS,
    AuditoriaEventoResumen,
    AuditoriaObjeto,
    _condiciones,
    _detalle_de_evento_para_catalogo,
    _objeto_desde_evento,
    _resumenes,
)
from app.modules.government.service_identidad import _funcionario_del_actor
from app.modules.government.service_paquetes import _documentos_vinculados
from app.shared.audit import record_audit
from app.shared.audit_catalog import catalog
from app.shared.clock import hoy_de_negocio, instante_actual, limites_del_dia_utc


def _catalog_label(accion: str, entidad: str) -> str | None:
    spec = catalog().get((accion, entidad))
    return spec.label if spec is not None else None

ESTADOS = ["EN_FORMACION", "FORMADA", "PARTICIPADA", "CALIFICADA", "FENECIDA", "SUSTITUIDA"]


def _ahora() -> datetime:
    return instante_actual()


def _a_iso(v: Any) -> str | None:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, date):
        return v.isoformat()
    return str(v)


def _json_nativo(d: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(d, default=_a_iso))


def _hash_canonico(d: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(d, sort_keys=True, separators=(",", ":"), default=_a_iso).encode("utf-8")
    ).hexdigest()


def _referencia_desde_accion(accion: str, detalle: dict[str, Any]) -> str:
    spec = catalog().get((accion, ""))
    etiqueta = spec.label if spec else accion
    for clave in ("codigo", "referencia", "numero", "denominacion", "nombre"):
        for valor in detalle.values():
            if isinstance(valor, dict):
                v = valor.get(clave)
            elif clave == "referencia" and isinstance(valor, str):
                v = valor
            else:
                v = None
            if isinstance(v, str) and v.strip():
                return f"{etiqueta} · {v.strip()}"[:300]
    return etiqueta[:300]


def _not_found() -> KontrolError:
    return KontrolError(code="GOV_RENDITION_NOT_FOUND", message="Expediente de rendición no encontrado.", status_code=404)


def _event_not_found() -> KontrolError:
    return KontrolError(code="GOV_RENDITION_EVENT_NOT_FOUND", message="Evento no encontrado como candidato.", status_code=404)


def _state_error(message: str = "No se permite la operación en el estado actual.") -> KontrolError:
    return KontrolError(code="GOV_RENDITION_STATE", message=message, status_code=409)


def _invalid_period(message: str = "Periodo inválido.") -> KontrolError:
    return KontrolError(code="GOV_RENDITION_INVALID_PERIOD", message=message, status_code=422)


def _responsible_invalid() -> KontrolError:
    return KontrolError(
        code="GOV_RENDITION_RESPONSIBLE_INVALID", message="La asignación del responsable no es válida.", status_code=422
    )


def _empty() -> KontrolError:
    return KontrolError(code="GOV_RENDITION_EMPTY", message="La cuenta requiere al menos una pieza.", status_code=422)


def _reason_required() -> KontrolError:
    return KontrolError(code="GOV_RENDITION_REASON_REQUIRED", message="El motivo/fundamento es obligatorio.", status_code=422)


def _not_formed() -> KontrolError:
    return KontrolError(code="GOV_RENDITION_NOT_FORMED", message="La cuenta no está formada.", status_code=409)


def _same_actor() -> KontrolError:
    return KontrolError(
        code="GOV_RENDITION_SAME_ACTOR",
        message="No puede registrar calificación o fenecimiento el mismo actor de la formación o el cuentadante.",
        status_code=403,
    )


def _invalid_page() -> KontrolError:
    return KontrolError(code="GOV_RENDITION_INVALID_PAGE", message="Página fuera de rango (1..50).", status_code=422)


def _event_out_of_period() -> KontrolError:
    return KontrolError(
        code="GOV_RENDITION_EVENT_OUT_OF_PERIOD", message="El evento no pertenece al periodo de la cuenta.", status_code=422
    )


def _obtener_asignacion(db: Session, ctx: CompanyContext, assignment_id: str) -> GovernmentAssignment:
    asignacion = db.scalar(
        select(GovernmentAssignment).where(
            GovernmentAssignment.id == assignment_id,
            GovernmentAssignment.company_id == ctx.company_id,
            GovernmentAssignment.status.notin_(["BORRADOR", "DESCARTADO"]),
        )
    )
    if not asignacion:
        raise _responsible_invalid()
    return asignacion


def _snapshot_responsable(db: Session, ctx: CompanyContext, assignment_id: str) -> dict[str, str]:
    asignacion = _obtener_asignacion(db, ctx, assignment_id)
    oficial = db.scalar(select(GovernmentOfficial).where(GovernmentOfficial.id == asignacion.official_id))
    posicion = db.scalar(select(GovernmentPosition).where(GovernmentPosition.id == asignacion.position_id))
    unidad = db.scalar(select(GovernmentUnit).where(GovernmentUnit.id == posicion.unit_id)) if posicion else None
    return {
        "funcionario": oficial.nombre if oficial else "",
        "funcionario_codigo": oficial.codigo if oficial else "",
        "cargo": posicion.name if posicion else "",
        "cargo_codigo": posicion.code if posicion else "",
        "unidad": unidad.name if unidad else "",
        "unidad_codigo": unidad.code if unidad else "",
        "figura": asignacion.figura or "",
        "asignacion_codigo": asignacion.codigo or "",
    }


def _validar_periodo(desde: date, hasta: date, corte: date) -> None:
    if desde > hasta:
        raise _invalid_period("Desde no puede ser posterior a hasta.")
    if not (desde <= corte <= hasta):
        raise _invalid_period("La fecha de corte debe estar dentro del periodo.")


def _validar_responsable(
    db: Session, ctx: CompanyContext, assignment_id: str, desde: date, hasta: date
) -> GovernmentAssignment:
    asignacion = _obtener_asignacion(db, ctx, assignment_id)
    fin_efectivo = asignacion.fin_efectivo or asignacion.hasta or hasta
    if asignacion.desde > hasta or fin_efectivo < desde:
        raise _responsible_invalid()
    return asignacion


def _siguiente_codigo(db: Session, ctx: CompanyContext, anio: int) -> str:
    prefijo = f"CTA-{anio}-"
    maximo = db.scalar(
        select(func.max(GovernmentRenditionFile.codigo)).where(
            GovernmentRenditionFile.company_id == ctx.company_id,
            GovernmentRenditionFile.codigo.like(f"{prefijo}%"),
        )
    )
    secuencia = 1
    if maximo:
        try:
            secuencia = int(maximo.split("-")[-1]) + 1
        except (ValueError, IndexError):
            secuencia = 1
    return f"{prefijo}{secuencia:04d}"


def _evento_resumen(evento: AuditEvent) -> AuditoriaEventoResumen:
    return AuditoriaEventoResumen(
        id=str(evento.id),
        fecha=evento.event_time,
        proceso=evento.entity_type,
        proceso_nombre=_catalog_label(evento.action, evento.entity_type) or evento.entity_type,
        accion=evento.action,
        accion_etiqueta=_catalog_label(evento.action, evento.entity_type) or evento.action,
        entidad=evento.entity_type,
        entidad_id=evento.entity_id,
        usuario=evento.user_id or "",
        motivo=None,
        request_id=evento.request_id or "",
    )


def _proceso_del_evento(evento: AuditEvent, resumen: AuditoriaEventoResumen) -> tuple[str, str, str]:
    proceso = resumen.proceso
    nombre = resumen.proceso_nombre
    accion = resumen.accion
    return proceso, nombre, accion


def _documentos_de_pieza(
    db: Session, ctx: CompanyContext, objeto: AuditoriaObjeto | None, detalle: dict[str, Any]
) -> list[dict[str, str]]:
    documento_ids = list(detalle.get("documento_ids", []) or [])
    if objeto:
        for vinculo in _documentos_vinculados(db, ctx, objeto.tipo, objeto.id):
            # _documentos_vinculados devuelve tuplas (documento_id, version_id | None)
            if isinstance(vinculo, tuple):
                documento_ids.append(vinculo[0])
            else:
                documento_ids.append(vinculo)

    # Preservar version_id preferida del vínculo congelado
    version_preferida: dict[str, str] = {}
    if objeto:
        for vinculo in _documentos_vinculados(db, ctx, objeto.tipo, objeto.id):
            if isinstance(vinculo, tuple) and len(vinculo) == 2 and vinculo[1] is not None:
                version_preferida[str(vinculo[0])] = str(vinculo[1])

    ids_unicos = list(dict.fromkeys(documento_ids))
    resultado: list[dict[str, str]] = []
    vistos: set[tuple[str, str]] = set()

    for doc_id in ids_unicos:
        doc_id_str = str(doc_id)
        preferida = version_preferida.get(doc_id_str)

        if preferida:
            version = db.scalar(
                select(DocumentVersion).where(
                    DocumentVersion.id == preferida,
                    DocumentVersion.document_id == doc_id_str,
                    DocumentVersion.company_id == ctx.company_id,
                )
            )
        else:
            version = db.scalar(
                select(DocumentVersion)
                .where(
                    DocumentVersion.document_id == doc_id_str,
                    DocumentVersion.company_id == ctx.company_id,
                )
                .order_by(DocumentVersion.version_number.desc())
                .limit(1)
            )

        if version:
            clave = (doc_id_str, str(version.id))
            if clave not in vistos:
                vistos.add(clave)
                resultado.append(
                    {
                        "documento_id": doc_id_str,
                        "version_id": str(version.id),
                        "sha256": version.sha256 or "",
                    }
                )

    return resultado


def _huella_evento(evento: AuditEvent, documento_ids: list[str]) -> str:
    payload = {
        "evento_id": str(evento.id),
        "action": evento.action,
        "entity_type": evento.entity_type,
        "entity_id": evento.entity_id,
        "event_time": evento.event_time.isoformat(),
        "user_id": evento.user_id,
        "request_id": evento.request_id,
        "documentos": sorted(documento_ids),
    }
    return _hash_canonico(payload)


def _pieza_desde_evento(
    db: Session,
    ctx: CompanyContext,
    expediente: GovernmentRenditionFile,
    evento: AuditEvent,
    ordinal: int | None,
    incorporada_por: str | None = None,
    incorporada_en: datetime | None = None,
) -> GovernmentRenditionPiece:
    detalle, documento_ids = _detalle_de_evento_para_catalogo(evento)
    objeto = _objeto_desde_evento(db, evento, ctx)
    resumen = next((r for r in _resumenes(db, [evento]) if r.id == str(evento.id)), None)
    proceso = resumen.proceso if resumen else "GOB"
    accion = resumen.accion if resumen else evento.action
    referencia = _referencia_desde_accion(accion, detalle)
    documentos = _documentos_de_pieza(db, ctx, objeto, {"documento_ids": documento_ids})
    huella = _huella_evento(evento, [d["documento_id"] for d in documentos])
    return GovernmentRenditionPiece(
        company_id=ctx.company_id,
        file_id=expediente.id,
        audit_event_id=evento.id,
        ordinal=ordinal,
        fecha=evento.event_time,
        proceso=proceso,
        accion=accion,
        entidad=evento.entity_type,
        entidad_id=evento.entity_id,
        referencia=referencia,
        objeto=objeto.model_dump() if objeto else None,
        documentos=documentos,
        huella=huella,
        incorporada_por=incorporada_por,
        incorporada_en=incorporada_en,
    )


def _cargar_expediente(db: Session, ctx: CompanyContext, expediente_id: str, bloqueo: bool = False) -> GovernmentRenditionFile:
    consulta = select(GovernmentRenditionFile).where(
        GovernmentRenditionFile.id == expediente_id,
        GovernmentRenditionFile.company_id == ctx.company_id,
    )
    if bloqueo:
        consulta = consulta.with_for_update()
    expediente = db.scalar(consulta)
    if not expediente:
        raise _not_found()
    return expediente


def _crear(
    db: Session, ctx: CompanyContext, datos: dict[str, Any]
) -> GovernmentRenditionFile:
    desde: date = datos["periodo_desde"]
    hasta: date = datos["periodo_hasta"]
    corte: date = datos["fecha_corte"]
    _validar_periodo(desde, hasta, corte)
    asignacion = _validar_responsable(db, ctx, datos["assignment_id"], desde, hasta)
    responsable = _snapshot_responsable(db, ctx, str(asignacion.id))
    codigo = _siguiente_codigo(db, ctx, desde.year)
    expediente = GovernmentRenditionFile(
        company_id=ctx.company_id,
        codigo=codigo,
        numero_version=1,
        denominacion=datos["denominacion"],
        ejercicio=datos.get("ejercicio"),
        periodo_desde=desde,
        periodo_hasta=hasta,
        fecha_corte=corte,
        observaciones=datos.get("observaciones"),
        assignment_id=asignacion.id,
        responsable=responsable,
        responsable_official_id=asignacion.official_id,
        estado="EN_FORMACION",
    )
    db.add(expediente)
    db.flush()
    record_audit(
        db,
        action="GOV_RENDITION_FILE_CREATED",
        entity_type="GovernmentRenditionFile",
        entity_id=str(expediente.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={"codigo": codigo, "denominacion": expediente.denominacion, "periodo_desde": _a_iso(desde), "periodo_hasta": _a_iso(hasta)},
    )
    return expediente


def _actualizar(
    db: Session, ctx: CompanyContext, expediente_id: str, datos: dict[str, Any], version: int | None = None
) -> GovernmentRenditionFile:
    expediente = _cargar_expediente(db, ctx, expediente_id, bloqueo=True)
    if expediente.estado != "EN_FORMACION":
        raise _state_error("Solo se puede editar una cuenta EN_FORMACION.")
    if version is not None and expediente.version != version:
        raise ConflictError(code="VERSION_CONFLICT", message="Conflicto de versión.")
    desde: date = datos["periodo_desde"]
    hasta: date = datos["periodo_hasta"]
    corte: date = datos["fecha_corte"]
    _validar_periodo(desde, hasta, corte)
    asignacion = _validar_responsable(db, ctx, datos["assignment_id"], desde, hasta)
    asignacion_id = str(asignacion.id)
    responsable = _snapshot_responsable(db, ctx, asignacion_id)
    expediente.denominacion = datos["denominacion"]
    expediente.periodo_desde = desde
    expediente.periodo_hasta = hasta
    expediente.fecha_corte = corte
    expediente.ejercicio = datos.get("ejercicio")
    expediente.observaciones = datos.get("observaciones")
    expediente.assignment_id = str(asignacion.id)
    expediente.responsable = responsable
    expediente.responsable_official_id = asignacion.official_id
    expediente.version += 1
    db.flush()
    record_audit(
        db,
        action="GOV_RENDITION_FILE_UPDATED",
        entity_type="GovernmentRenditionFile",
        entity_id=str(expediente.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={"codigo": expediente.codigo, "denominacion": expediente.denominacion},
    )
    return expediente


def _condiciones_candidatas(db: Session, ctx: CompanyContext, expediente: GovernmentRenditionFile):
    desde = limites_del_dia_utc(expediente.periodo_desde)[0]
    hasta = limites_del_dia_utc(expediente.periodo_hasta)[1]
    return and_(
        *_condiciones(ctx, AuditoriaFiltrosPoblacion(desde=expediente.periodo_desde, hasta=expediente.periodo_hasta)),
        AuditEvent.event_time >= desde,
        AuditEvent.event_time < hasta,
        AuditEvent.entity_type != "GovernmentRenditionFile",
    )


def _candidatas(
    db: Session,
    ctx: CompanyContext,
    expediente: GovernmentRenditionFile,
    proceso: str | None = None,
    accion: str | None = None,
    texto: str | None = None,
    pagina: int = 1,
    por_pagina: int = 20,
) -> tuple[list[AuditEvent], int]:
    if por_pagina < 1 or por_pagina > 50:
        raise _invalid_page()
    base = _condiciones_candidatas(db, ctx, expediente)
    filtros = [base]
    if proceso:
        filtros.append(AuditEvent.entity_type == proceso)
    if accion:
        filtros.append(AuditEvent.action == accion)
    if texto:
        patron = f"%{texto}%"
        filtros.append(or_(AuditEvent.action.ilike(patron), AuditEvent.entity_type.ilike(patron), AuditEvent.user_id.ilike(patron)))
    total = db.scalar(select(func.count()).select_from(AuditEvent).where(*filtros)) or 0
    eventos = list(
        db.scalars(
            select(AuditEvent)
            .where(*filtros)
            .order_by(AuditEvent.event_time, AuditEvent.id)
            .offset((pagina - 1) * por_pagina)
            .limit(por_pagina)
        )
    )
    return eventos, total


def _incluidas_ids(db: Session, expediente_id: str) -> set[str]:
    return set(
        db.scalars(
            select(GovernmentRenditionPiece.audit_event_id).where(GovernmentRenditionPiece.file_id == expediente_id)
        )
    )


def _incorporar(db: Session, ctx: CompanyContext, expediente_id: str, evento_id: str) -> GovernmentRenditionPiece:
    expediente = _cargar_expediente(db, ctx, expediente_id, bloqueo=True)
    if expediente.estado != "EN_FORMACION":
        raise _state_error("Solo se pueden incorporar piezas EN_FORMACION.")
    desde = limites_del_dia_utc(expediente.periodo_desde)[0]
    hasta = limites_del_dia_utc(expediente.fecha_corte)[1]
    try:
        evento_uuid = evento_id
        evento = db.scalar(
            select(AuditEvent).where(
                *_condiciones(ctx, AuditoriaFiltrosPoblacion()),
                AuditEvent.id == evento_uuid,
                AuditEvent.entity_type != "GovernmentRenditionFile",
            )
        )
    except Exception:
        evento = None
    if not evento:
        raise _event_not_found()
    if not (desde <= evento.event_time < hasta):
        raise _event_out_of_period()
    if db.scalar(
        select(GovernmentRenditionPiece).where(
            GovernmentRenditionPiece.file_id == expediente.id,
            GovernmentRenditionPiece.audit_event_id == evento.id,
        )
    ):
        raise KontrolError(code="GOV_RENDITION_PIECE_DUPLICATE", message="El evento ya está incorporado.", status_code=409)
    pieza = _pieza_desde_evento(
        db, ctx, expediente, evento, None, incorporada_por=str(ctx.user_id or ""), incorporada_en=_ahora()
    )
    db.add(pieza)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise KontrolError(code="GOV_RENDITION_PIECE_DUPLICATE", message="El evento ya está incorporado.", status_code=409) from None
    record_audit(
        db,
        action="GOV_RENDITION_FILE_PIECE_ADDED",
        entity_type="GovernmentRenditionFile",
        entity_id=str(expediente.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={"codigo": expediente.codigo, "evento_id": str(evento.id)},
    )
    return pieza


def _retirar_pieza(db: Session, ctx: CompanyContext, expediente_id: str, pieza_id: str) -> None:
    expediente = _cargar_expediente(db, ctx, expediente_id, bloqueo=True)
    if expediente.estado != "EN_FORMACION":
        raise _state_error("Solo se pueden retirar piezas EN_FORMACION.")
    pieza = db.scalar(
        select(GovernmentRenditionPiece).where(
            GovernmentRenditionPiece.id == pieza_id,
            GovernmentRenditionPiece.file_id == expediente.id,
        )
    )
    if not pieza:
        raise _not_found()
    evento_id = str(pieza.audit_event_id)
    db.delete(pieza)
    db.flush()
    record_audit(
        db,
        action="GOV_RENDITION_FILE_PIECE_REMOVED",
        entity_type="GovernmentRenditionFile",
        entity_id=str(expediente.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={"codigo": expediente.codigo, "evento_id": evento_id},
    )


def _ordinales_provisionales(db: Session, expediente_id: str) -> list[GovernmentRenditionPiece]:
    piezas = list(
        db.scalars(
            select(GovernmentRenditionPiece)
            .where(GovernmentRenditionPiece.file_id == expediente_id)
            .order_by(GovernmentRenditionPiece.fecha, GovernmentRenditionPiece.audit_event_id)
        )
    )
    return piezas


def _construir_snapshot(
    db: Session, ctx: CompanyContext, expediente: GovernmentRenditionFile, provisional: bool
) -> dict[str, Any]:
    piezas = _ordinales_provisionales(db, str(expediente.id))
    piezas_out = [_pieza_out(db, ctx, expediente, pieza, orden) for orden, pieza in enumerate(piezas, start=1)]
    generado_en = _ahora() if provisional else expediente.formado_en
    resumen = _resumen_reporte(db, ctx, expediente, generado_en)
    hallazgos = [
        {"ordinal": orden, "referencia": pieza.referencia, "objeto": pieza.objeto}
        for orden, pieza in enumerate(piezas, start=1)
        if pieza.entidad == "GovernmentFinding"
    ]
    snapshot = {
        "provisional": provisional,
        "generado_en": _a_iso(generado_en),
        "expediente": {
            "id": str(expediente.id),
            "codigo": expediente.codigo,
            "numero_version": expediente.numero_version,
            "version": expediente.version,
            "estado": "FORMADA" if not provisional else expediente.estado,
            "denominacion": expediente.denominacion,
            "ejercicio": expediente.ejercicio,
            "periodo_desde": _a_iso(expediente.periodo_desde),
            "periodo_hasta": _a_iso(expediente.periodo_hasta),
            "fecha_corte": _a_iso(expediente.fecha_corte),
        },
        "ente": "",
        "responsable": expediente.responsable or {},
        "piezas": [p.model_dump() if hasattr(p, "model_dump") else p for p in piezas_out],
        "resumen": resumen,
        "hallazgos": hallazgos,
        "snapshot_sha256": None,
    }
    ente = db.scalar(select(GovernmentEntity.denominacion).where(GovernmentEntity.company_id == ctx.company_id))
    snapshot["ente"] = ente or ""
    return _json_nativo(snapshot)


def _pdf_desde_snapshot(snapshot: dict[str, Any]) -> bytes:
    buffer = io.BytesIO()
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=20 * mm, leftMargin=20 * mm, topMargin=20 * mm, bottomMargin=20 * mm)
    elementos: list[Any] = []
    elementos.append(Paragraph(escape(snapshot.get("expediente", {}).get("codigo", "Rendición")), styles["Title"]))
    elementos.append(Spacer(1, 6 * mm))
    if snapshot.get("ente"):
        elementos.append(Paragraph(escape(str(snapshot["ente"])), styles["Normal"]))
    if snapshot.get("responsable", {}).get("funcionario"):
        elementos.append(Paragraph(escape(str(snapshot["responsable"]["funcionario"])), styles["Normal"]))
    elementos.append(Spacer(1, 6 * mm))
    piezas = snapshot.get("piezas", [])
    cabecera = ["Ordinal", "Fecha", "Proceso", "Acción", "Referencia", "Entidad", "Documentos", "Huella"]
    filas = [cabecera]
    for pieza in piezas:
        def _str(v: Any) -> str:
            if v is None:
                return ""
            if isinstance(v, list):
                return ", ".join(str(x) for x in v)
            if isinstance(v, dict):
                return str(v.get("tipo", "") or v.get("id", ""))
            return str(v)
        filas.append(
            [
                str(pieza.get("ordinal", "")),
                _str(pieza.get("fecha", "")),
                _str(pieza.get("proceso", "")),
                _str(pieza.get("accion", "")),
                _str(pieza.get("referencia", "")),
                _str(pieza.get("entidad", "")),
                str(len(pieza.get("documentos", []))),
                _str(pieza.get("huella", "")),
            ]
        )
    tabla = Table(filas, repeatRows=1)
    tabla.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    elementos.append(tabla)
    doc.build(elementos)
    return buffer.getvalue()


def _snapshot_out(db: Session, ctx: CompanyContext, expediente: GovernmentRenditionFile) -> dict[str, Any]:
    if expediente.estado == "EN_FORMACION":
        snapshot = _construir_snapshot(db, ctx, expediente, True)
        return {**snapshot, "provisional": True, "generado_en": _a_iso(_ahora()), "snapshot_sha256": None}
    snapshot = dict(expediente.snapshot or {})
    snapshot["snapshot_sha256"] = expediente.snapshot_sha256
    snapshot["provisional"] = False
    snapshot["generado_en"] = _a_iso(expediente.formado_en)
    return snapshot


def _resumen_reporte(
    db: Session, ctx: CompanyContext, expediente: GovernmentRenditionFile, generado_en: datetime | None
) -> list[dict[str, Any]]:
    filas: list[dict[str, Any]] = []
    corte = generado_en or _ahora()
    fecha_hechos = corte.isoformat()
    condiciones = _condiciones_candidatas(db, ctx, expediente)
    total_hechos = db.scalar(
        select(func.count()).select_from(AuditEvent).where(condiciones, AuditEvent.event_time < corte)
    ) or 0
    filas.append(
        {
            "concepto": "Hechos de Gobierno del período",
            "fuente": "Bitácora",
            "filtro": "entity_type != GovernmentRenditionFile",
            "periodo": f"{expediente.periodo_desde.isoformat()} / {expediente.periodo_hasta.isoformat()}",
            "conjunto": "Eventos de auditoría",
            "regla": f"event_time < {fecha_hechos}",
            "resultado": total_hechos,
        }
    )
    piezas = _ordinales_provisionales(db, str(expediente.id))
    filas.append(
        {
            "concepto": "Piezas incluidas",
            "fuente": "Rendición",
            "filtro": "file_id",
            "periodo": expediente.periodo_desde.isoformat(),
            "conjunto": "Piezas",
            "regla": "1-n",
            "resultado": len(piezas),
        }
    )
    por_proceso: dict[str, list[int]] = {}
    for orden, pieza in enumerate(piezas, start=1):
        por_proceso.setdefault(pieza.proceso, []).append(orden)
    for proceso, ordinales in por_proceso.items():
        filas.append(
            {
                "concepto": f"Proceso {proceso}",
                "fuente": "Rendición",
                "filtro": proceso,
                "periodo": expediente.periodo_desde.isoformat(),
                "conjunto": "Piezas",
                "regla": "Proceso con piezas",
                "resultado": ",".join(str(o) for o in ordinales),
            }
        )
    total_documentos = sum(len(pieza.documentos or []) for pieza in piezas)
    filas.append(
        {
            "concepto": "Soportes documentales",
            "fuente": "Rendición",
            "filtro": "documentos",
            "periodo": expediente.periodo_desde.isoformat(),
            "conjunto": "Documentos",
            "regla": "Suma",
            "resultado": total_documentos,
        }
    )
    ids_hallazgos = set(pieza.entidad_id for pieza in piezas if pieza.entidad == "GovernmentFinding" and pieza.entidad_id)
    filas.append(
        {
            "concepto": "Hallazgos asociados",
            "fuente": "Rendición",
            "filtro": "GovernmentFinding",
            "periodo": expediente.periodo_desde.isoformat(),
            "conjunto": "Hallazgos",
            "regla": "entidad_id distintos",
            "resultado": len(ids_hallazgos),
        }
    )
    return filas


def _formar(db: Session, ctx: CompanyContext, expediente_id: str) -> GovernmentRenditionFile:
    expediente = _cargar_expediente(db, ctx, expediente_id, bloqueo=True)
    if expediente.estado != "EN_FORMACION":
        raise _state_error("Solo se puede formar una cuenta EN_FORMACION.")
    piezas = _ordinales_provisionales(db, str(expediente.id))
    if not piezas:
        raise _empty()
    for orden, pieza in enumerate(piezas, start=1):
        pieza.ordinal = orden
    db.flush()
    expediente.formado_en = _ahora()
    expediente.formado_por = str(ctx.user_id or "")
    snapshot = _construir_snapshot(db, ctx, expediente, False)
    expediente.snapshot = snapshot
    expediente.snapshot_sha256 = _hash_canonico(snapshot)
    pdf_bytes = _pdf_desde_snapshot(snapshot)
    pdf_sha256 = hashlib.sha256(pdf_bytes).hexdigest()
    storage = get_storage()
    storage_key = generate_storage_key(ctx.company_id)
    size, sha = storage.put(storage_key, io.BytesIO(pdf_bytes))
    if sha != pdf_sha256 or not storage.verify(storage_key, sha):
        storage.delete(storage_key)
        raise KontrolError(code="STORAGE_HASH_MISMATCH", status_code=500, message="El informe almacenado no coincide con su huella")
    expediente.informe_storage_key = storage_key
    expediente.informe_sha256 = pdf_sha256
    expediente.informe_bytes = size
    expediente.estado = "FORMADA"
    db.flush()
    record_audit(
        db,
        action="GOV_RENDITION_FILE_FORMED",
        entity_type="GovernmentRenditionFile",
        entity_id=str(expediente.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={"codigo": expediente.codigo, "piezas": len(piezas), "snapshot_sha256": expediente.snapshot_sha256},
    )
    return expediente


def _validar_pieza_periodo(
    db: Session, ctx: CompanyContext, expediente: GovernmentRenditionFile, pieza: GovernmentRenditionPiece
) -> None:
    desde = limites_del_dia_utc(expediente.periodo_desde)[0]
    hasta = limites_del_dia_utc(expediente.fecha_corte)[1]
    if not (desde <= pieza.fecha < hasta):
        raise _event_out_of_period()


def _participar(
    db: Session, ctx: CompanyContext, expediente_id: str, fecha: date, oficio: str
) -> GovernmentRenditionFile:
    expediente = _cargar_expediente(db, ctx, expediente_id, bloqueo=True)
    if expediente.estado != "FORMADA":
        raise _state_error("La participación requiere una cuenta FORMADA.")
    if fecha < expediente.fecha_corte or fecha > hoy_de_negocio():
        raise _invalid_period("La fecha de participación debe estar entre la fecha de corte y hoy.")
    _vence = expediente.periodo_hasta + timedelta(days=90)
    expediente.participacion_fecha = fecha
    expediente.participacion_oficio = oficio
    expediente.participacion_registrada_por = str(ctx.user_id or "")
    expediente.participacion_registrada_en = _ahora()
    expediente.estado = "PARTICIPADA"
    db.flush()
    record_audit(
        db,
        action="GOV_RENDITION_FILE_PARTICIPATED",
        entity_type="GovernmentRenditionFile",
        entity_id=str(expediente.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={"codigo": expediente.codigo, "oficio": oficio},
    )
    return expediente


def _verificar_actor_calificacion(db: Session, ctx: CompanyContext, expediente: GovernmentRenditionFile) -> None:
    if str(ctx.user_id or "") == expediente.formado_por:
        raise _same_actor()
    if _funcionario_del_actor(db, ctx) == expediente.responsable_official_id:
        raise _same_actor()


def _calificar(db: Session, ctx: CompanyContext, expediente_id: str, datos: dict[str, Any]) -> GovernmentRenditionFile:
    expediente = _cargar_expediente(db, ctx, expediente_id, bloqueo=True)
    if expediente.estado != "PARTICIPADA":
        raise _state_error("La calificación requiere una cuenta PARTICIPADA.")
    _verificar_actor_calificacion(db, ctx, expediente)
    if datos["informe_fecha"] > hoy_de_negocio():
        raise _invalid_period("La fecha del informe no puede ser futura.")
    expediente.calificacion = datos["resultado"]
    expediente.calificacion_organo = datos["organo"]
    expediente.calificacion_informe_numero = datos["informe_numero"]
    expediente.calificacion_informe_fecha = datos["informe_fecha"]
    expediente.calificacion_fundamento = datos.get("fundamento")
    expediente.calificacion_registrada_por = str(ctx.user_id or "")
    expediente.calificacion_registrada_en = _ahora()
    expediente.estado = "CALIFICADA"
    db.flush()
    record_audit(
        db,
        action="GOV_RENDITION_FILE_QUALIFIED",
        entity_type="GovernmentRenditionFile",
        entity_id=str(expediente.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={"codigo": expediente.codigo, "resultado": datos["resultado"], "informe_numero": datos["informe_numero"]},
    )
    return expediente


def _fenecer(db: Session, ctx: CompanyContext, expediente_id: str, datos: dict[str, Any]) -> GovernmentRenditionFile:
    expediente = _cargar_expediente(db, ctx, expediente_id, bloqueo=True)
    if expediente.estado != "CALIFICADA":
        raise _state_error("El fenecimiento requiere una cuenta CALIFICADA.")
    _verificar_actor_calificacion(db, ctx, expediente)
    if datos["auto_fecha"] < expediente.calificacion_informe_fecha or datos["auto_fecha"] > hoy_de_negocio():
        raise _invalid_period("La fecha del auto debe estar entre el informe de calificación y hoy.")
    if expediente.calificacion == "OBJETADA" and not datos.get("fundamento"):
        raise _reason_required()
    expediente.fenecimiento_auto_numero = datos["auto_numero"]
    expediente.fenecimiento_auto_fecha = datos["auto_fecha"]
    expediente.fenecimiento_fundamento = datos.get("fundamento")
    expediente.fenecimiento_registrado_por = str(ctx.user_id or "")
    expediente.fenecimiento_registrado_en = _ahora()
    expediente.estado = "FENECIDA"
    db.flush()
    record_audit(
        db,
        action="GOV_RENDITION_FILE_DISCHARGED",
        entity_type="GovernmentRenditionFile",
        entity_id=str(expediente.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={"codigo": expediente.codigo, "auto_numero": datos["auto_numero"]},
    )
    return expediente


def _nueva_version(db: Session, ctx: CompanyContext, expediente_id: str, motivo: str) -> GovernmentRenditionFile:
    expediente = _cargar_expediente(db, ctx, expediente_id, bloqueo=True)
    if expediente.estado not in ("FORMADA", "PARTICIPADA"):
        raise _state_error("Solo se puede versionar una cuenta FORMADA o PARTICIPADA.")
    if len(motivo) < 10:
        raise _reason_required()
    nueva = GovernmentRenditionFile(
        company_id=ctx.company_id,
        codigo=expediente.codigo,
        numero_version=expediente.numero_version + 1,
        anterior_id=expediente.id,
        denominacion=expediente.denominacion,
        ejercicio=expediente.ejercicio,
        periodo_desde=expediente.periodo_desde,
        periodo_hasta=expediente.periodo_hasta,
        fecha_corte=expediente.fecha_corte,
        observaciones=expediente.observaciones,
        assignment_id=expediente.assignment_id,
        responsable=expediente.responsable,
        responsable_official_id=expediente.responsable_official_id,
        estado="EN_FORMACION",
        sustitucion_motivo=motivo,
    )
    db.add(nueva)
    db.flush()
    expediente_id = str(expediente.id)
    piezas_originales = _ordinales_provisionales(db, expediente_id)
    for pieza in piezas_originales:
        copia = GovernmentRenditionPiece(
            company_id=ctx.company_id,
            file_id=nueva.id,
            audit_event_id=pieza.audit_event_id,
            ordinal=None,
            fecha=pieza.fecha,
            proceso=pieza.proceso,
            accion=pieza.accion,
            entidad=pieza.entidad,
            entidad_id=pieza.entidad_id,
            referencia=pieza.referencia,
            objeto=pieza.objeto,
            documentos=pieza.documentos,
            huella=pieza.huella,
            incorporada_por=None,
            incorporada_en=None,
        )
        db.add(copia)
    expediente.estado = "SUSTITUIDA"
    expediente.sustitucion_motivo = motivo
    db.flush()
    record_audit(
        db,
        action="GOV_RENDITION_FILE_VERSIONED",
        entity_type="GovernmentRenditionFile",
        entity_id=str(expediente.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={"codigo": expediente.codigo, "numero_version": expediente.numero_version, "motivo": motivo},
    )
    record_audit(
        db,
        action="GOV_RENDITION_FILE_VERSIONED",
        entity_type="GovernmentRenditionFile",
        entity_id=str(nueva.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={"codigo": nueva.codigo, "numero_version": nueva.numero_version, "motivo": motivo},
    )
    return nueva


def _pieza_out(
    db: Session, ctx: CompanyContext, expediente: GovernmentRenditionFile, pieza: GovernmentRenditionPiece, ordinal: int | None
) -> dict[str, Any]:
    objeto = pieza.objeto or None
    if not objeto and pieza.entidad_id and pieza.entidad in ("documents", "packages"):
        objeto = {"tipo": pieza.entidad, "id": pieza.entidad_id}
    audit_event_id = pieza.audit_event_id
    audit_event_id = str(audit_event_id)
    proceso_nombre = next((nombre for codigo, nombre, _ in PROCESOS if codigo == pieza.proceso), pieza.proceso)
    spec = catalog().get((pieza.accion, pieza.proceso))
    accion_etiqueta = spec.label if spec else pieza.accion
    usuario = ""
    evento_uuid = pieza.audit_event_id
    if hasattr(evento_uuid, "hex"):
        evento_uuid = str(evento_uuid)
    evento = db.scalar(select(AuditEvent).where(AuditEvent.id == evento_uuid))
    if evento:
        usuario = evento.user_id or ""
    return {
        "id": str(pieza.id),
        "ordinal": ordinal if ordinal is not None else (pieza.ordinal if pieza.ordinal is not None else None),
        "evento_id": str(pieza.audit_event_id),
        "fecha": pieza.fecha,
        "proceso": pieza.proceso,
        "proceso_nombre": proceso_nombre,
        "accion": pieza.accion,
        "accion_etiqueta": accion_etiqueta,
        "entidad": pieza.entidad,
        "entidad_id": pieza.entidad_id,
        "usuario": usuario,
        "referencia": pieza.referencia,
        "objeto": objeto,
        "documentos": pieza.documentos or [],
        "huella": pieza.huella,
        "ruta_evento": f"/gobierno/bitacora/{pieza.audit_event_id}",
    }


def _ficha(db: Session, ctx: CompanyContext, expediente: GovernmentRenditionFile) -> dict[str, Any]:
    expediente_id = str(expediente.id)
    piezas = _ordinales_provisionales(db, expediente_id)
    piezas_out: list[dict[str, Any]] = []
    if expediente.estado == "EN_FORMACION":
        piezas_out = [_pieza_out(db, ctx, expediente, pieza, orden) for orden, pieza in enumerate(piezas, start=1)]
    else:
        piezas_out = [_pieza_out(db, ctx, expediente, pieza, pieza.ordinal) for pieza in piezas]
    plazo_participacion = expediente.periodo_hasta + timedelta(days=90)
    hallazgos = [
        {"ordinal": orden, "referencia": pieza.referencia, "objeto": pieza.objeto}
        for orden, pieza in enumerate(piezas, start=1)
        if pieza.entidad == "GovernmentFinding"
    ]
    ente = db.scalar(select(GovernmentEntity.denominacion).where(GovernmentEntity.company_id == ctx.company_id)) or ""
    return {
        "id": str(expediente.id),
        "codigo": expediente.codigo,
        "numero_version": expediente.numero_version,
        "version": expediente.version,
        "estado": expediente.estado,
        "anterior_id": expediente.anterior_id,
        "sustituido_por_id": expediente.sustitucion_motivo,
        "sustitucion_motivo": expediente.sustitucion_motivo,
        "denominacion": expediente.denominacion,
        "ejercicio": expediente.ejercicio,
        "periodo_desde": expediente.periodo_desde,
        "periodo_hasta": expediente.periodo_hasta,
        "fecha_corte": expediente.fecha_corte,
        "observaciones": expediente.observaciones,
        "ente": ente,
        "responsable": expediente.responsable or {},
        "piezas": piezas_out,
        "formado_en": expediente.formado_en,
        "formado_por": expediente.formado_por,
        "snapshot_sha256": expediente.snapshot_sha256,
        "informe": {
            "sha256": expediente.informe_sha256,
            "bytes": expediente.informe_bytes,
        }
        if expediente.informe_storage_key
        else None,
        "participacion": {
            "fecha": expediente.participacion_fecha,
            "oficio": expediente.participacion_oficio,
            "vence": plazo_participacion,
            "en_plazo": bool(
                expediente.participacion_fecha and expediente.participacion_fecha <= plazo_participacion
            ),
            "registrada_por": expediente.participacion_registrada_por,
            "registrada_en": expediente.participacion_registrada_en,
        }
        if expediente.estado in ("PARTICIPADA", "CALIFICADA", "FENECIDA")
        else None,
        "plazo_participacion": plazo_participacion,
        "calificacion": {
            "resultado": expediente.calificacion,
            "organo": expediente.calificacion_organo,
            "informe_numero": expediente.calificacion_informe_numero,
            "informe_fecha": expediente.calificacion_informe_fecha,
            "fundamento": expediente.calificacion_fundamento,
            "registrada_por": expediente.calificacion_registrada_por,
            "registrada_en": expediente.calificacion_registrada_en,
        }
        if expediente.estado in ("CALIFICADA", "FENECIDA")
        else None,
        "fenecimiento": {
            "auto_numero": expediente.fenecimiento_auto_numero,
            "auto_fecha": expediente.fenecimiento_auto_fecha,
            "fundamento": expediente.fenecimiento_fundamento,
            "registrado_por": expediente.fenecimiento_registrado_por,
            "registrado_en": expediente.fenecimiento_registrado_en,
        }
        if expediente.estado == "FENECIDA"
        else None,
        "hallazgos": hallazgos,
    }


def _exportar_pdf(db: Session, ctx: CompanyContext, expediente: GovernmentRenditionFile) -> tuple[str, bytes]:
    if expediente.estado == "EN_FORMACION":
        raise _not_formed()
    if expediente.informe_storage_key is None:
        raise _not_formed()
    nombre = f"{expediente.codigo}-v{expediente.numero_version}.pdf"
    storage = get_storage()
    contenido = storage.open(expediente.informe_storage_key)
    try:
        data = contenido.read()
    finally:
        if hasattr(contenido, "close"):
            contenido.close()
    return nombre, data


def _exportar_csv(db: Session, ctx: CompanyContext, expediente: GovernmentRenditionFile) -> tuple[str, bytes]:
    if expediente.estado == "EN_FORMACION":
        raise _not_formed()
    snapshot = expediente.snapshot or {}
    piezas = snapshot.get("piezas", [])
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow(["ordinal", "fecha", "proceso", "accion", "referencia", "entidad", "documentos", "huella"])
    for pieza in piezas:
        docs = pieza.get("documentos", [])
        writer.writerow(
            [
                pieza.get("ordinal", ""),
                pieza.get("fecha", ""),
                pieza.get("proceso", ""),
                pieza.get("accion", ""),
                pieza.get("referencia", ""),
                pieza.get("entidad", ""),
                str(len(docs)),
                pieza.get("huella", ""),
            ]
        )
    nombre = f"{expediente.codigo}-indice.csv"
    return nombre, buffer.getvalue().encode("utf-8")


def _auditar_exportado(db: Session, ctx: CompanyContext, expediente: GovernmentRenditionFile, formato: str) -> None:
    record_audit(
        db,
        action="GOV_RENDITION_FILE_EXPORTED",
        entity_type="GovernmentRenditionFile",
        entity_id=str(expediente.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={"codigo": expediente.codigo, "formato": formato},
    )


def verificar_integridad(db: Session, ctx: CompanyContext, expediente: GovernmentRenditionFile) -> dict[str, Any]:
    if expediente.estado == "EN_FORMACION":
        raise _not_formed()
    piezas = _ordinales_provisionales(db, str(expediente.id))
    resultado_piezas: list[dict[str, Any]] = []
    for pieza in piezas:
        evento = db.scalar(
            select(AuditEvent).where(
                AuditEvent.id == pieza.audit_event_id,
                AuditEvent.tenant_id == ctx.tenant_id,
                AuditEvent.company_id == ctx.company_id,
            )
        )
        if not evento:
            estado_pieza = "DESAPARECIDA"
            detalle = "El evento ya no existe."
        else:
            _detalle_catalogo, documento_ids = _detalle_de_evento_para_catalogo(evento)
            detalle = ""
            _documentos_ids = [d["documento_id"] for d in (pieza.documentos or [])]
            huella_actual = _huella_evento(evento, _documentos_ids)
            if huella_actual != pieza.huella:
                estado_pieza = "ALTERADA"
                detalle = "La huella del evento no coincide."
            else:
                estado_pieza = "VIGENTE"
                for doc in pieza.documentos or []:
                    version = (
                        db.query(DocumentVersion)
                        .filter(
                            DocumentVersion.id == doc["version_id"],
                            DocumentVersion.company_id == ctx.company_id,
                        )
                        .first()
                    )
                    if version is None or version.sha256 != doc.get("sha256"):
                        estado_pieza = "SIN_EVIDENCIA"
                        detalle = "Sin evidencia documental."
                        break
        resultado_piezas.append(
            {"ordinal": pieza.ordinal if pieza.ordinal is not None else 0, "estado": estado_pieza, "detalle": detalle}
        )
    snapshot_ok = expediente.snapshot_sha256 is not None and _hash_canonico(expediente.snapshot or {}) == expediente.snapshot_sha256
    informe_ok = False
    if expediente.informe_storage_key and expediente.informe_sha256:
        informe_ok = get_storage().verify(expediente.informe_storage_key, expediente.informe_sha256)
    estado = "VALIDO" if snapshot_ok and informe_ok and all(p["estado"] == "VIGENTE" for p in resultado_piezas) else "INCOMPLETO"
    return {"estado": estado, "snapshot_ok": snapshot_ok, "informe_ok": informe_ok, "piezas": resultado_piezas}
