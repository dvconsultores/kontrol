"""Servicio del paquete de auditoría exportable (DOC-08, GOV-DOC-010).

Incluye el alcance desde una muestra inmutable de CTL-04, la inclusión de documentos con
el control documental de la Spec 046, la generación síncrona y acotada, la descarga y la
verificación de integridad. La huella SHA-256 prueba integridad; no es una firma
electrónica.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import tempfile
import zipfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, BinaryIO

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext
from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.audit.models import AuditEvent
from app.modules.documents import service as documentos
from app.modules.documents.models import Document, DocumentVersion, StoredFile
from app.modules.documents.storage import generate_storage_key, get_storage, safe_extension, sanitize_filename
from app.modules.government.models import (
    GovernmentAuditPackage,
    GovernmentAuditPackageVerification,
    GovernmentAuditSample,
    GovernmentAuditSampleItem,
    GovernmentCorrectiveAction,
    GovernmentCorrectiveActionProgress,
    GovernmentEntity,
    GovernmentFinding,
    GovernmentFindingEvent,
    GovernmentFindingHistory,
    GovernmentFindingRecommendation,
)
from app.modules.government.service_auditoria import (
    _detalle_de_evento_para_catalogo,
    _instante,
    _objeto_desde_evento,
    _resumenes,
    _usuarios_por_ids,
)
from app.modules.identity_access import authority
from app.modules.identity_access.models import User
from app.shared.audit import record_audit
from app.shared.clock import hoy_de_negocio

FORMATO = "kontrol-gobierno-paquete-auditoria"
VERSION_MANIFIESTO = 1
ALGORITMO_HASH = "SHA-256"
AVISO_HUELLA = "La huella SHA-256 prueba integridad; no es una firma electrónica."
MAX_EVENTOS = 500
MAX_DOCUMENTOS = 200
MAX_BYTES = 250 * 1024 * 1024
MAX_SUBIDA = 300 * 1024 * 1024
MAX_ENTRADAS = 1000
MAX_DESCOMPRIMIDO = 300 * 1024 * 1024
MAX_RAZON = 200
PERMISO_DESCARGA = "documentos:download"
INCLUIDO = "INCLUIDO"
EXCLUIDO = "EXCLUIDO"
SIN_PERMISO = "SIN_PERMISO"
NO_DISPONIBLE = "NO_DISPONIBLE"


@dataclass
class _Documento:
    """Documento candidato del paquete y su evaluación."""

    id: str
    referencias: list[dict[str, str]] = field(default_factory=list)
    version_preferida: str | None = None
    estado: str = EXCLUIDO
    motivo: str | None = None
    version: DocumentVersion | None = None
    archivo: StoredFile | None = None


@dataclass
class _Alcance:
    """Lo que entra en el paquete de una muestra."""

    muestra: GovernmentAuditSample
    eventos: list[AuditEvent]
    ordenes: dict[str, int]
    detalles: dict[str, dict[str, Any]]
    objetos: dict[str, dict[str, str] | None]
    documentos_de_evento: dict[str, list[str]]
    hallazgos: list[GovernmentFinding]
    documentos: dict[str, _Documento]


def _permisos(db: Session, ctx: CompanyContext) -> set[str]:
    usuario = db.get(User, ctx.user_id)
    if usuario is None:
        return set()
    return authority.capabilities_in_company(db, usuario, ctx.company_id)


def _muestra_de_empresa(db: Session, ctx: CompanyContext, muestra_id: str) -> GovernmentAuditSample:
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
    return muestra


def _referenciar(
    documentos_: dict[str, _Documento],
    documento_id: str,
    tipo: str,
    referencia_id: str,
    version_preferida: str | None = None,
) -> None:
    candidato = documentos_.setdefault(documento_id, _Documento(id=documento_id))
    referencia = {"tipo": tipo, "id": referencia_id}
    if referencia not in candidato.referencias:
        candidato.referencias.append(referencia)
    if version_preferida is not None and candidato.version_preferida is None:
        candidato.version_preferida = version_preferida


def _version_del_vinculo(link) -> str | None:
    return link.frozen_version_id if link.is_frozen else None


def _documentos_vinculados(db: Session, ctx: CompanyContext, tipo: str, recurso_id: str) -> list[tuple[str, str | None]]:
    try:
        filas = documentos.documents_for(
            db,
            resource_type=tipo,
            resource_id=recurso_id,
            company_ids=[ctx.company_id],
        )
    except KontrolError:
        return []
    return [(str(documento.id), _version_del_vinculo(link)) for documento, link in filas]


def _alcance(db: Session, ctx: CompanyContext, muestra: GovernmentAuditSample) -> _Alcance:
    partidas = list(
        db.scalars(
            select(GovernmentAuditSampleItem)
            .where(
                GovernmentAuditSampleItem.sample_id == muestra.id,
                GovernmentAuditSampleItem.company_id == ctx.company_id,
            )
            .order_by(GovernmentAuditSampleItem.orden)
        )
    )

    ids = [str(partida.audit_event_id) for partida in partidas]
    por_id: dict[str, AuditEvent] = {}
    if ids:
        filas = db.scalars(
            select(AuditEvent).where(
                AuditEvent.id.in_(ids),
                AuditEvent.tenant_id == ctx.tenant_id,
                AuditEvent.company_id == ctx.company_id,
            )
        )
        por_id = {str(evento.id): evento for evento in filas}

    eventos: list[AuditEvent] = []
    ordenes: dict[str, int] = {}
    for partida in partidas:
        evento_id = str(partida.audit_event_id)
        evento = por_id.get(evento_id)
        if evento is None:
            continue
        eventos.append(evento)
        ordenes[evento_id] = partida.orden

    detalles: dict[str, dict[str, Any]] = {}
    objetos: dict[str, dict[str, str] | None] = {}
    documentos_de_evento: dict[str, list[str]] = {}
    documentos_: dict[str, _Documento] = {}

    for evento in eventos:
        eid = str(evento.id)
        detalle, citados = _detalle_de_evento_para_catalogo(evento)
        detalles[eid] = detalle

        objeto = _objeto_desde_evento(db, evento, ctx)
        objetos[eid] = {"tipo": objeto.tipo, "id": objeto.id} if objeto else None

        lista = list(citados)
        for documento_id in citados:
            _referenciar(documentos_, documento_id, "evento", eid)

        if objeto:
            for doc_id, version in _documentos_vinculados(db, ctx, objeto.tipo, objeto.id):
                _referenciar(documentos_, doc_id, "objeto", objeto.id, version)
                if doc_id not in lista:
                    lista.append(doc_id)

        documentos_de_evento[eid] = lista

    hallazgos = list(
        db.scalars(
            select(GovernmentFinding)
            .where(
                GovernmentFinding.sample_id == muestra.id,
                GovernmentFinding.company_id == ctx.company_id,
            )
            .order_by(GovernmentFinding.codigo)
        )
    )

    for hallazgo in hallazgos:
        acciones = list(
            db.scalars(
                select(GovernmentCorrectiveAction)
                .where(
                    GovernmentCorrectiveAction.finding_id == hallazgo.id,
                    GovernmentCorrectiveAction.company_id == ctx.company_id,
                )
                .order_by(GovernmentCorrectiveAction.orden)
            )
        )
        for accion in acciones:
            for doc_id, version in _documentos_vinculados(db, ctx, "GovernmentCorrectiveAction", str(accion.id)):
                _referenciar(documentos_, doc_id, "accion_correctiva", str(accion.id), version)

            avances = list(
                db.scalars(
                    select(GovernmentCorrectiveActionProgress)
                    .where(
                        GovernmentCorrectiveActionProgress.action_id == accion.id,
                        GovernmentCorrectiveActionProgress.company_id == ctx.company_id,
                    )
                    .order_by(GovernmentCorrectiveActionProgress.created_at)
                )
            )
            for avance in avances:
                if avance.document_id is not None:
                    _referenciar(documentos_, str(avance.document_id), "avance", str(avance.id))

    return _Alcance(
        muestra=muestra,
        eventos=eventos,
        ordenes=ordenes,
        detalles=detalles,
        objetos=objetos,
        documentos_de_evento=documentos_de_evento,
        hallazgos=hallazgos,
        documentos=documentos_,
    )


def _evaluar(db: Session, ctx: CompanyContext, permisos: set[str], candidato: _Documento) -> None:
    documento = db.get(Document, candidato.id)
    if documento is None or documento.company_id != ctx.company_id:
        candidato.estado = EXCLUIDO
        candidato.motivo = NO_DISPONIBLE
        return

    if PERMISO_DESCARGA not in permisos or not documentos.puede_leer_archivo(
        db, documento, ctx.company_id, permisos
    ):
        candidato.estado = EXCLUIDO
        candidato.motivo = SIN_PERMISO
        return

    version_id = candidato.version_preferida or documento.current_version_id
    version = db.get(DocumentVersion, version_id) if version_id else None
    if version is None or str(version.document_id) != str(documento.id):
        candidato.estado = EXCLUIDO
        candidato.motivo = NO_DISPONIBLE
        return

    try:
        archivo = documentos.assert_deliverable(db, version)
    except KontrolError:
        candidato.estado = EXCLUIDO
        candidato.motivo = NO_DISPONIBLE
        return

    candidato.estado = INCLUIDO
    candidato.motivo = None
    candidato.version = version
    candidato.archivo = archivo


def _evaluar_todo(db: Session, ctx: CompanyContext, alcance: _Alcance) -> list[_Documento]:
    permisos = _permisos(db, ctx)
    for candidato in alcance.documentos.values():
        _evaluar(db, ctx, permisos, candidato)
    return [alcance.documentos[documento_id] for documento_id in sorted(alcance.documentos)]


def _motivo_de_limite(eventos: int, incluidos: int, bytes_: int) -> str | None:
    if eventos > MAX_EVENTOS:
        return "La muestra supera 500 eventos"
    if incluidos > MAX_DOCUMENTOS:
        return "El paquete supera 200 documentos incluidos"
    if bytes_ > MAX_BYTES:
        return "Los documentos incluidos superan 250 MiB"
    return None


def _documento_publico(candidato: _Documento) -> dict[str, Any]:
    incluido = candidato.estado == INCLUIDO
    return {
        "id": candidato.id,
        "estado": candidato.estado,
        "motivo": candidato.motivo,
        "version": candidato.version.version_number if incluido and candidato.version else None,
        "bytes": candidato.archivo.size if incluido and candidato.archivo else None,
        "sha256": candidato.version.sha256 if incluido and candidato.version else None,
        "referencias": list(candidato.referencias),
    }


def _nombre_de_usuario(db: Session, tenant_id: str, usuario_id: str | None) -> str | None:
    if usuario_id is None:
        return None
    return _usuarios_por_ids(db, [usuario_id], tenant_id).get(str(usuario_id))


def _paquetes_previos(db: Session, muestra: GovernmentAuditSample) -> int:
    total = db.scalar(
        select(func.count()).select_from(GovernmentAuditPackage).where(
            GovernmentAuditPackage.sample_id == muestra.id,
            GovernmentAuditPackage.company_id == muestra.company_id,
        )
    )
    return total or 0


def vista_previa(db: Session, ctx: CompanyContext, muestra_id: str) -> dict[str, Any]:
    """Alcance del paquete antes de generarlo (spec §9 S1)."""
    muestra = _muestra_de_empresa(db, ctx, muestra_id)
    alcance = _alcance(db, ctx, muestra)
    docs = _evaluar_todo(db, ctx, alcance)

    incluidos = [documento for documento in docs if documento.estado == INCLUIDO]
    bytes_ = sum(documento.archivo.size for documento in incluidos if documento.archivo)

    motivo = _motivo_de_limite(len(alcance.eventos), len(incluidos), bytes_)

    return {
        "muestra": {
            "id": str(muestra.id),
            "codigo": muestra.codigo,
            "titulo": muestra.titulo,
            "metodo": muestra.metodo,
            "semilla": muestra.semilla,
            "poblacion": muestra.poblacion,
            "tamano": muestra.tamano,
            "creada_en": _instante(muestra.created_at),
            "creada_por": _nombre_de_usuario(db, ctx.tenant_id, muestra.created_by),
        },
        "eventos": len(alcance.eventos),
        "documentos_incluidos": len(incluidos),
        "documentos_excluidos": len(docs) - len(incluidos),
        "hallazgos": len(alcance.hallazgos),
        "bytes_estimados": bytes_,
        "documentos": [_documento_publico(documento) for documento in docs],
        "limites": {
            "eventos": MAX_EVENTOS,
            "documentos": MAX_DOCUMENTOS,
            "bytes": MAX_BYTES,
        },
        "excede_limite": motivo is not None,
        "motivo_limite": motivo,
        "paquetes_previos": _paquetes_previos(db, muestra),
    }


def _json_bytes(valor: Any) -> bytes:
    """Serializa un valor JSON determinista a bytes UTF-8."""
    return json.dumps(valor, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")


def _sha256(datos: bytes) -> str:
    """Calcula la huella SHA-256 hexadecimal de unos bytes."""
    return hashlib.sha256(datos).hexdigest()


def _iso(dt: datetime | None) -> str | None:
    """Devuelve una marca de tiempo normalizada en ISO-8601 o None."""
    if dt is None:
        return None
    return _instante(dt).isoformat()


def _entregable(candidato: _Documento) -> tuple[DocumentVersion, StoredFile]:
    """Versión y archivo de un documento INCLUIDO; `_evaluar` garantiza que existen."""
    if candidato.version is None or candidato.archivo is None:
        raise KontrolError(
            code="GOV_PACKAGE_DOCUMENT_STATE",
            message="Documento incluido sin versión entregable",
            status_code=500,
        )
    return candidato.version, candidato.archivo


def _ruta_documento(candidato: _Documento) -> str:
    """Construye la ruta estable de un documento dentro del paquete."""
    version, archivo = _entregable(candidato)
    ext = safe_extension(archivo.original_name)
    sufijo = f".{ext}" if ext else ""
    return f"documentos/{candidato.id}-v{version.version_number}{sufijo}"


def _hallazgo_json(db: Session, ctx: CompanyContext, hallazgo: GovernmentFinding) -> tuple[dict[str, Any], list[str], list[str], list[str]]:
    """Devuelve (contenido del fichero, partidas, acciones, documentos) de un hallazgo originado en la muestra."""
    partidas = [
        str(f.audit_event_id)
        for f in db.scalars(
            select(GovernmentFindingEvent).where(
                GovernmentFindingEvent.finding_id == hallazgo.id,
                GovernmentFindingEvent.company_id == ctx.company_id,
            )
        )
    ]
    recomendaciones = db.scalars(
        select(GovernmentFindingRecommendation)
        .where(
            GovernmentFindingRecommendation.finding_id == hallazgo.id,
            GovernmentFindingRecommendation.company_id == ctx.company_id,
        )
        .order_by(GovernmentFindingRecommendation.orden)
    ).all()
    acciones = db.scalars(
        select(GovernmentCorrectiveAction)
        .where(
            GovernmentCorrectiveAction.finding_id == hallazgo.id,
            GovernmentCorrectiveAction.company_id == ctx.company_id,
        )
        .order_by(GovernmentCorrectiveAction.orden)
    ).all()
    ids_acciones = [a.id for a in acciones]
    avances = (
        db.scalars(
            select(GovernmentCorrectiveActionProgress)
            .where(
                GovernmentCorrectiveActionProgress.action_id.in_(ids_acciones),
                GovernmentCorrectiveActionProgress.company_id == ctx.company_id,
            )
            .order_by(GovernmentCorrectiveActionProgress.created_at)
        ).all()
        if ids_acciones
        else []
    )
    historia = db.scalars(
        select(GovernmentFindingHistory)
        .where(
            GovernmentFindingHistory.finding_id == hallazgo.id,
            GovernmentFindingHistory.company_id == ctx.company_id,
        )
        .order_by(GovernmentFindingHistory.created_at)
    ).all()
    usuarios = _usuarios_por_ids(
        db,
        [hallazgo.created_by, hallazgo.presentado_por, hallazgo.verificado_por]
        + [a.created_by for a in avances]
        + [h.created_by for h in historia],
        ctx.tenant_id,
    )
    vistos: set[str] = set()
    documentos_: list[str] = []
    for avance in avances:
        if avance.document_id is not None:
            clave = str(avance.document_id)
            if clave not in vistos:
                documentos_.append(clave)
                vistos.add(clave)
    contenido: dict[str, Any] = {
        "id": str(hallazgo.id),
        "codigo": hallazgo.codigo,
        "titulo": hallazgo.titulo,
        "condicion": hallazgo.condicion,
        "criterio": hallazgo.criterio,
        "causa": hallazgo.causa,
        "efecto": hallazgo.efecto,
        "riesgo": hallazgo.riesgo,
        "origen": hallazgo.origen,
        "estado": hallazgo.estado,
        "registrado_por": usuarios.get(str(hallazgo.created_by)),
        "registrado_en": _iso(hallazgo.created_at),
        "presentado_por": usuarios.get(str(hallazgo.presentado_por)),
        "presentado_en": _iso(hallazgo.presentado_en),
        "verificado_por": usuarios.get(str(hallazgo.verificado_por)),
        "verificado_en": _iso(hallazgo.verificado_en),
        "nota_verificacion": hallazgo.nota_verificacion,
        "partidas": partidas,
        "recomendaciones": [{"id": str(r.id), "orden": r.orden, "texto": r.texto} for r in recomendaciones],
        "acciones": [
            {
                "id": str(a.id),
                "recomendacion_id": str(a.recommendation_id) if a.recommendation_id is not None else None,
                "orden": a.orden,
                "descripcion": a.descripcion,
                "cargo": {
                    "id": a.position_id,
                    "codigo": a.cargo_codigo,
                    "denominacion": a.cargo_denominacion,
                    "unidad_id": a.unidad_id,
                    "unidad": a.unidad_nombre,
                    "ejercicio": a.ejercicio,
                },
                "fecha_objetivo": a.fecha_objetivo.isoformat(),
                "porcentaje": a.porcentaje,
                "estado": a.estado,
            }
            for a in acciones
        ],
        "avances": [
            {
                "id": str(avance.id),
                "accion_id": str(avance.action_id),
                "nota": avance.nota,
                "porcentaje": avance.porcentaje,
                "documento_id": str(avance.document_id) if avance.document_id is not None else None,
                "registrado_por": usuarios.get(str(avance.created_by)),
                "registrado_en": _iso(avance.created_at),
            }
            for avance in avances
        ],
        "historia": [
            {
                "tipo": h.tipo,
                "estado_desde": h.estado_desde,
                "estado_hasta": h.estado_hasta,
                "registrado_por": usuarios.get(str(h.created_by)),
                "registrado_en": _iso(h.created_at),
            }
            for h in historia
        ],
    }
    return contenido, partidas, [str(a.id) for a in acciones], documentos_


def _construir_zip(db: Session, ctx: CompanyContext, alcance: _Alcance, docs: list[_Documento], paquete: dict[str, Any], generado_en: datetime) -> tuple[Any, dict[str, Any], bytes]:
    """Construye el ZIP en un fichero temporal y devuelve (fichero posicionado al inicio, manifiesto, bytes del manifiesto)."""
    ficheros: dict[str, bytes] = {}
    descripciones: dict[str, tuple[str, str, str]] = {}
    muestra = alcance.muestra
    muestra_json: dict[str, Any] = {
        "id": str(muestra.id),
        "codigo": muestra.codigo,
        "titulo": muestra.titulo,
        "criterio": muestra.criterio,
        "justificacion": muestra.justificacion,
        "metodo": muestra.metodo,
        "semilla": muestra.semilla,
        "filtros": muestra.filtros or {},
        "poblacion": muestra.poblacion,
        "tamano": muestra.tamano,
        "partidas": [str(e.id) for e in alcance.eventos],
        "creada_por": _nombre_de_usuario(db, ctx.tenant_id, muestra.created_by),
        "creada_en": _iso(muestra.created_at),
    }
    ficheros["muestra/muestra.json"] = _json_bytes(muestra_json)
    descripciones["muestra/muestra.json"] = ("muestra", muestra.codigo, muestra.titulo)
    resumenes = {r.id: r for r in _resumenes(db, alcance.eventos)}
    eventos_manifiesto: list[dict[str, Any]] = []
    for evento in alcance.eventos:
        eid = str(evento.id)
        orden = alcance.ordenes[eid]
        r = resumenes[eid]
        ruta = f"eventos/{orden:04d}-{eid}.json"
        entrada = {
            "orden": orden,
            "id": eid,
            "fecha": r.fecha.isoformat(),
            "proceso": r.proceso,
            "accion": r.accion,
            "entidad": r.entidad,
            "entidad_id": r.entidad_id,
            "usuario": r.usuario,
            "objeto": alcance.objetos[eid],
            "documentos": alcance.documentos_de_evento[eid],
        }
        ficheros[ruta] = _json_bytes({**entrada, "detalle": alcance.detalles[eid]})
        descripciones[ruta] = ("evento", eid, r.accion)
        eventos_manifiesto.append({**entrada, "archivo": ruta})
    hallazgos_manifiesto: list[dict[str, Any]] = []
    for h in alcance.hallazgos:
        contenido, partidas, acciones, docs_h = _hallazgo_json(db, ctx, h)
        ruta = f"hallazgos/{h.codigo}.json"
        ficheros[ruta] = _json_bytes(contenido)
        descripciones[ruta] = ("hallazgo", h.codigo, h.titulo)
        hallazgos_manifiesto.append(
            {
                "id": str(h.id),
                "codigo": h.codigo,
                "titulo": h.titulo,
                "riesgo": h.riesgo,
                "estado": h.estado,
                "archivo": ruta,
                "partidas": partidas,
                "acciones": acciones,
                "documentos": docs_h,
            }
        )
    documentos_manifiesto: list[dict[str, Any]] = []
    archivos_documento: dict[str, _Documento] = {}
    for d in docs:
        if d.estado == INCLUIDO:
            version, archivo = _entregable(d)
            ruta = _ruta_documento(d)
            archivos_documento[ruta] = d
            descripciones[ruta] = ("documento", d.id, sanitize_filename(archivo.original_name))
            documentos_manifiesto.append(
                {
                    "id": d.id,
                    "estado": INCLUIDO,
                    "version_id": str(version.id),
                    "version": version.version_number,
                    "archivo": ruta,
                    "nombre_original": sanitize_filename(archivo.original_name),
                    "tipo_mime": archivo.mime_type,
                    "bytes": archivo.size,
                    "sha256": version.sha256,
                    "referencias": d.referencias,
                }
            )
        else:
            documentos_manifiesto.append({"id": d.id, "estado": EXCLUIDO, "motivo": d.motivo, "referencias": d.referencias})
    leeme = "\n".join(
        [
            "Paquete de auditoría KONTROL",
            f"Código: {paquete['codigo']}",
            f"Muestra: {muestra.codigo} · {muestra.titulo}",
            f"Generado en: {generado_en.isoformat()}",
            f"Generado por: {paquete['generado_por']}",
            "",
            "Este paquete contiene el índice (INDICE.csv), el manifiesto (manifest.json), metadatos seguros de eventos, "
            "copia de documentos autorizados y hallazgos.",
            "",
            AVISO_HUELLA,
            "",
            "Para verificarlo: en KONTROL, Gobierno › Paquetes de auditoría › Verificar un paquete; o fuera del sistema con "
            "`sha256sum -c SHA256SUMS` y comparando la huella de manifest.json con la registrada en KONTROL.",
            "",
            "Los documentos excluidos se declaran en el manifiesto con su motivo.",
        ]
    )
    ficheros["LEEME.txt"] = leeme.encode("utf-8")
    descripciones["LEEME.txt"] = ("leeme", paquete["codigo"], "Instrucciones de verificación")
    indice = io.StringIO()
    writer = csv.writer(indice, delimiter=";", lineterminator="\n")
    writer.writerow(["ruta", "tipo", "referencia", "descripcion", "bytes", "sha256"])
    filas = []
    for ruta, datos_fichero in ficheros.items():
        if ruta == "INDICE.csv":
            continue
        filas.append(
            (
                ruta,
                descripciones[ruta][0],
                descripciones[ruta][1],
                descripciones[ruta][2],
                len(datos_fichero),
                _sha256(datos_fichero),
            )
        )
    for ruta, documento in archivos_documento.items():
        filas.append(
            (
                ruta,
                descripciones[ruta][0],
                descripciones[ruta][1],
                descripciones[ruta][2],
                _entregable(documento)[1].size,
                _entregable(documento)[0].sha256,
            )
        )
    for fila in sorted(filas, key=lambda f: f[0]):
        writer.writerow(fila)
    ficheros["INDICE.csv"] = ("﻿" + indice.getvalue()).encode("utf-8")
    archivos = sorted(
        [{"ruta": r, "bytes": len(b), "sha256": _sha256(b)} for r, b in ficheros.items()]
        + [{"ruta": r, "bytes": _entregable(d)[1].size, "sha256": _entregable(d)[0].sha256} for r, d in archivos_documento.items()],
        key=lambda a: str(a["ruta"]),
    )
    ente = db.scalars(select(GovernmentEntity).where(GovernmentEntity.company_id == ctx.company_id)).first()
    manifiesto: dict[str, Any] = {
        "formato": FORMATO,
        "version_manifiesto": VERSION_MANIFIESTO,
        "paquete": {**paquete, "algoritmo_hash": ALGORITMO_HASH, "aviso": AVISO_HUELLA},
        "ente": {"empresa_id": ctx.company_id, "denominacion": ente.denominacion if ente else None},
        "muestra": {**muestra_json, "archivo": "muestra/muestra.json"},
        "eventos": eventos_manifiesto,
        "documentos": documentos_manifiesto,
        "hallazgos": hallazgos_manifiesto,
        "archivos": archivos,
        "totales": {
            "eventos": len(eventos_manifiesto),
            "documentos_incluidos": sum(1 for d in documentos_manifiesto if d["estado"] == INCLUIDO),
            "documentos_excluidos": sum(1 for d in documentos_manifiesto if d["estado"] == EXCLUIDO),
            "hallazgos": len(hallazgos_manifiesto),
            "archivos": len(archivos),
            "bytes": sum(a["bytes"] for a in archivos),
        },
    }
    manifiesto_bytes = _json_bytes(manifiesto)
    sha256sums = "".join(
        f"{a['sha256']}  {a['ruta']}\n"
        for a in sorted(archivos + [{"ruta": "manifest.json", "sha256": _sha256(manifiesto_bytes)}], key=lambda a: str(a["ruta"]))
    ).encode("utf-8")
    destino = tempfile.SpooledTemporaryFile(max_size=16 * 1024 * 1024)
    fecha = generado_en.astimezone(UTC).timetuple()[:6]

    def _info(ruta: str, compresion: int) -> zipfile.ZipInfo:
        zi = zipfile.ZipInfo(ruta, date_time=fecha)
        zi.compress_type = compresion
        zi.external_attr = 0o644 << 16
        return zi

    with zipfile.ZipFile(destino, mode="w") as zf:
        zf.writestr(_info("manifest.json", zipfile.ZIP_DEFLATED), manifiesto_bytes)
        zf.writestr(_info("SHA256SUMS", zipfile.ZIP_DEFLATED), sha256sums)
        zf.writestr(_info("INDICE.csv", zipfile.ZIP_DEFLATED), ficheros["INDICE.csv"])
        zf.writestr(_info("LEEME.txt", zipfile.ZIP_DEFLATED), ficheros["LEEME.txt"])
        zf.writestr(_info("muestra/muestra.json", zipfile.ZIP_DEFLATED), ficheros["muestra/muestra.json"])
        for ruta in sorted(r for r in ficheros if r.startswith("eventos/")):
            zf.writestr(_info(ruta, zipfile.ZIP_DEFLATED), ficheros[ruta])
        for ruta in sorted(archivos_documento):
            documento = archivos_documento[ruta]
            with get_storage().open(_entregable(documento)[1].storage_key) as origen, zf.open(_info(ruta, zipfile.ZIP_STORED), mode="w") as salida:
                while True:
                    trozo = origen.read(1024 * 1024)
                    if not trozo:
                        break
                    salida.write(trozo)
        for ruta in sorted(r for r in ficheros if r.startswith("hallazgos/")):
            zf.writestr(_info(ruta, zipfile.ZIP_DEFLATED), ficheros[ruta])
    destino.seek(0)
    return destino, manifiesto, manifiesto_bytes


def _siguiente_codigo(db: Session, ctx: CompanyContext) -> str:
    """Calcula el siguiente código correlativo anual del paquete."""
    prefijo = f"PA-{hoy_de_negocio().year}-"
    n = db.scalar(
        select(func.count(GovernmentAuditPackage.id)).where(
            GovernmentAuditPackage.company_id == ctx.company_id,
            GovernmentAuditPackage.codigo.like(f"{prefijo}%"),
        )
    ) or 0
    return f"{prefijo}{n + 1:04d}"


def generar(db: Session, ctx: CompanyContext, muestra_id: str, proposito: str, idempotency_key: str | None) -> tuple[GovernmentAuditPackage, bool]:
    """Genera y registra el paquete; devuelve (paquete, creado). `creado` es False en una repetición idempotente."""
    clave_idem = idempotency_key.strip() if idempotency_key else None
    if clave_idem and len(clave_idem) > 100:
        raise KontrolError(code="VALIDATION_ERROR", message="La clave de idempotencia supera 100 caracteres", status_code=422)
    if clave_idem:
        existente = db.scalars(
            select(GovernmentAuditPackage).where(
                GovernmentAuditPackage.company_id == ctx.company_id,
                GovernmentAuditPackage.idempotency_key == clave_idem,
            )
        ).first()
        if existente:
            if str(existente.sample_id) != str(muestra_id):
                raise ConflictError(
                    code="GOV_PACKAGE_IDEMPOTENCY_CONFLICT",
                    message="La clave de idempotencia ya se usó para otra muestra",
                )
            return existente, False
    muestra = _muestra_de_empresa(db, ctx, muestra_id)
    alcance = _alcance(db, ctx, muestra)
    docs = _evaluar_todo(db, ctx, alcance)
    incluidos = [d for d in docs if d.estado == INCLUIDO]
    bytes_ = sum(_entregable(d)[1].size for d in incluidos)
    motivo = _motivo_de_limite(len(alcance.eventos), len(incluidos), bytes_)
    if motivo:
        raise KontrolError(code="GOV_PACKAGE_TOO_LARGE", message=motivo, status_code=422)
    numero = (db.scalar(select(func.count(GovernmentAuditPackage.id)).where(GovernmentAuditPackage.sample_id == muestra.id, GovernmentAuditPackage.company_id == ctx.company_id)) or 0) + 1
    codigo = _siguiente_codigo(db, ctx)
    generado_en = datetime.now(UTC).replace(microsecond=0)
    generado_por = _nombre_de_usuario(db, ctx.tenant_id, ctx.user_id)
    titulo = f"Paquete de auditoría · {muestra.titulo}"[:200]
    paquete_meta = {
        "codigo": codigo,
        "numero_generacion": numero,
        "titulo": titulo,
        "proposito": proposito,
        "generado_en": generado_en.isoformat(),
        "generado_por": generado_por,
    }
    fichero, manifiesto, manifiesto_bytes = _construir_zip(db, ctx, alcance, docs, paquete_meta, generado_en)
    huella = hashlib.sha256()
    total = 0
    while True:
        trozo = fichero.read(1024 * 1024)
        if not trozo:
            break
        huella.update(trozo)
        total += len(trozo)
    fichero.seek(0)
    clave = generate_storage_key(ctx.company_id)
    almacen = get_storage()
    tamano, sha = almacen.put(clave, fichero)
    fichero.close()
    if sha != huella.hexdigest() or tamano != total:
        almacen.delete(clave)
        raise KontrolError(code="STORAGE_HASH_MISMATCH", message="El paquete almacenado no coincide con su huella", status_code=500)
    paquete_obj = GovernmentAuditPackage(
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        codigo=codigo,
        sample_id=str(muestra.id),
        numero_generacion=numero,
        titulo=titulo,
        proposito=proposito,
        version_manifiesto=VERSION_MANIFIESTO,
        huella_manifiesto=_sha256(manifiesto_bytes),
        huella_paquete=sha,
        bytes=tamano,
        clave_almacenamiento=clave,
        nombre_archivo=f"paquete-{codigo}.zip",
        eventos=manifiesto["totales"]["eventos"],
        documentos_incluidos=manifiesto["totales"]["documentos_incluidos"],
        documentos_excluidos=manifiesto["totales"]["documentos_excluidos"],
        hallazgos=manifiesto["totales"]["hallazgos"],
        archivos=manifiesto["totales"]["archivos"],
        manifiesto=manifiesto,
        idempotency_key=clave_idem,
        created_by=ctx.user_id,
    )
    db.add(paquete_obj)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        almacen.delete(clave)
        raise ConflictError(code="GOV_PACKAGE_CONFLICT", message="Otro paquete se registró al mismo tiempo; vuelva a intentarlo") from None
    record_audit(
        db,
        action="GOV_AUDIT_PACKAGE_GENERATED",
        entity_type="GovernmentAuditPackage",
        entity_id=str(paquete_obj.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={
            "codigo": codigo,
            "muestra_codigo": muestra.codigo,
            "huella_paquete": sha,
            "huella_manifiesto": paquete_obj.huella_manifiesto,
            "tamano_bytes": tamano,
            "eventos": paquete_obj.eventos,
            "documentos_incluidos": paquete_obj.documentos_incluidos,
            "documentos_excluidos": paquete_obj.documentos_excluidos,
            "hallazgos": paquete_obj.hallazgos,
        },
    )
    return paquete_obj, True


def _paquete_de_empresa(db, ctx, paquete_id: str) -> GovernmentAuditPackage:
    """Recupera un paquete de auditoría de la empresa activa o lanza NotFoundError."""
    paquete = db.scalar(
        select(GovernmentAuditPackage).where(
            GovernmentAuditPackage.id == paquete_id,
            GovernmentAuditPackage.tenant_id == ctx.tenant_id,
            GovernmentAuditPackage.company_id == ctx.company_id,
        )
    )
    if paquete is None:
        raise NotFoundError(code="GOV_PACKAGE_NOT_FOUND", message="El paquete no existe en este ente")
    return paquete


def _resumen(paquete: GovernmentAuditPackage, muestra_codigo: str, usuarios: dict[str, str]) -> dict[str, Any]:
    """Resumen del paquete para listados."""
    return {
        "id": str(paquete.id),
        "codigo": paquete.codigo,
        "muestra_id": str(paquete.sample_id),
        "muestra_codigo": muestra_codigo,
        "numero_generacion": paquete.numero_generacion,
        "titulo": paquete.titulo,
        "generado_por": usuarios.get(str(paquete.created_by)) if paquete.created_by else None,
        "generado_en": _instante(paquete.created_at),
        "bytes": paquete.bytes,
        "huella_paquete": paquete.huella_paquete,
        "eventos": paquete.eventos,
        "documentos_incluidos": paquete.documentos_incluidos,
        "documentos_excluidos": paquete.documentos_excluidos,
        "hallazgos": paquete.hallazgos,
    }


def listar(db, ctx, muestra_id: str | None, pagina: int, por_pagina: int) -> dict[str, Any]:
    """Lista paginadamente los paquetes de auditoría de la empresa activa."""
    condiciones = [
        GovernmentAuditPackage.tenant_id == ctx.tenant_id,
        GovernmentAuditPackage.company_id == ctx.company_id,
    ]
    if muestra_id:
        condiciones.append(GovernmentAuditPackage.sample_id == muestra_id)

    total = db.scalar(select(func.count()).select_from(GovernmentAuditPackage).where(*condiciones)) or 0
    filas = db.scalars(
        select(GovernmentAuditPackage)
        .where(*condiciones)
        .order_by(GovernmentAuditPackage.created_at.desc(), GovernmentAuditPackage.codigo.desc())
        .offset((pagina - 1) * por_pagina)
        .limit(por_pagina)
    ).all()

    sample_ids = {str(p.sample_id) for p in filas}
    codigos: dict[str, str] = {}
    if sample_ids:
        muestras = db.scalars(
            select(GovernmentAuditSample).where(
                GovernmentAuditSample.tenant_id == ctx.tenant_id,
                GovernmentAuditSample.company_id == ctx.company_id,
                GovernmentAuditSample.id.in_(sample_ids),
            )
        ).all()
        codigos = {str(m.id): m.codigo for m in muestras}

    usuarios = _usuarios_por_ids(db, [p.created_by for p in filas if p.created_by], ctx.tenant_id)
    return {
        "items": [_resumen(p, codigos.get(str(p.sample_id), ""), usuarios) for p in filas],
        "total": total,
        "pagina": pagina,
        "por_pagina": por_pagina,
    }


def _contenido(manifiesto: dict[str, Any]) -> dict[str, Any]:
    """Resumen del manifiesto SIN nombres de documento (PDD-DOC08-04)."""
    eventos = [
        {k: e.get(k) for k in ("orden", "id", "fecha", "proceso", "accion", "entidad", "entidad_id", "usuario", "objeto", "documentos")}
        for e in manifiesto.get("eventos", [])
    ]
    documentos_ = [
        {
            "id": d["id"],
            "estado": d["estado"],
            "motivo": d.get("motivo"),
            "version": d.get("version"),
            "bytes": d.get("bytes"),
            "sha256": d.get("sha256"),
            "referencias": d.get("referencias", []),
        }
        for d in manifiesto.get("documentos", [])
    ]
    hallazgos = [
        {k: h.get(k) for k in ("id", "codigo", "titulo", "riesgo", "estado", "partidas", "acciones", "documentos")}
        for h in manifiesto.get("hallazgos", [])
    ]
    return {"eventos": eventos, "documentos": documentos_, "hallazgos": hallazgos}


def detalle(db, ctx, paquete_id: str) -> dict[str, Any]:
    """Detalle del paquete, verificación de integridad e información histórica."""
    paquete = _paquete_de_empresa(db, ctx, paquete_id)
    muestra = db.get(GovernmentAuditSample, paquete.sample_id)
    verificaciones = db.scalars(
        select(GovernmentAuditPackageVerification)
        .where(
            GovernmentAuditPackageVerification.package_id == paquete.id,
            GovernmentAuditPackageVerification.company_id == ctx.company_id,
        )
        .order_by(GovernmentAuditPackageVerification.created_at.desc())
    ).all()

    usuarios = _usuarios_por_ids(
        db,
        [paquete.created_by] + [v.created_by for v in verificaciones if v.created_by],
        ctx.tenant_id,
    )
    return {
        **_resumen(paquete, muestra.codigo if muestra else "", usuarios),
        "muestra_titulo": muestra.titulo if muestra else "",
        "proposito": paquete.proposito,
        "version_manifiesto": paquete.version_manifiesto,
        "huella_manifiesto": paquete.huella_manifiesto,
        "archivos": paquete.archivos,
        "nombre_archivo": paquete.nombre_archivo,
        "contenido": _contenido(paquete.manifiesto),
        "verificaciones": [
            {
                "id": str(v.id),
                "resultado": v.resultado,
                "motivos": v.motivos,
                "huella_archivo": v.huella_archivo,
                "bytes_archivo": v.bytes_archivo,
                "identico": v.identico,
                "verificado_por": usuarios.get(str(v.created_by)) if v.created_by else None,
                "verificado_en": _instante(v.created_at),
            }
            for v in verificaciones
        ],
    }


def _exigir_documentos_legibles(db, ctx, paquete: GovernmentAuditPackage) -> None:
    """La descarga no salta el control documental (spec §4.9, OD-DOC08-04)."""
    permisos = _permisos(db, ctx)
    prohibido = KontrolError(
        code="GOV_PACKAGE_DOCUMENTS_FORBIDDEN",
        message="No tiene permiso sobre todos los documentos del paquete",
        status_code=403,
    )
    if PERMISO_DESCARGA not in permisos:
        raise prohibido

    for d in paquete.manifiesto.get("documentos", []):
        if d.get("estado") != INCLUIDO:
            continue
        documento = db.get(Document, d.get("id"))
        if documento is None or not documentos.puede_leer_archivo(db, documento, ctx.company_id, permisos):
            raise prohibido


def _abrir_almacenado(paquete: GovernmentAuditPackage) -> BinaryIO:
    """Abre el paquete almacenado comprobando su huella de integridad."""
    almacen = get_storage()
    if not almacen.verify(paquete.clave_almacenamiento, paquete.huella_paquete):
        raise KontrolError(
            code="STORAGE_HASH_MISMATCH",
            message="El paquete almacenado no coincide con su huella registrada",
            status_code=500,
        )
    return almacen.open(paquete.clave_almacenamiento)


def _auditar_descarga(db, ctx, paquete: GovernmentAuditPackage, archivo: str) -> None:
    """Registra la descarga del paquete o del manifiesto."""
    record_audit(
        db,
        action="GOV_AUDIT_PACKAGE_DOWNLOADED",
        entity_type="GovernmentAuditPackage",
        entity_id=str(paquete.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={"codigo": paquete.codigo, "archivo": archivo},
    )


def descargar(db, ctx, paquete_id: str) -> tuple[str, BinaryIO, int]:
    """Devuelve el archivo ZIP del paquete para su descarga."""
    paquete = _paquete_de_empresa(db, ctx, paquete_id)
    _exigir_documentos_legibles(db, ctx, paquete)
    flujo = _abrir_almacenado(paquete)
    _auditar_descarga(db, ctx, paquete, "paquete")
    return paquete.nombre_archivo, flujo, paquete.bytes


def manifiesto(db, ctx, paquete_id: str) -> tuple[str, bytes]:
    """Extrae y devuelve el manifiesto original del paquete almacenado."""
    paquete = _paquete_de_empresa(db, ctx, paquete_id)
    _exigir_documentos_legibles(db, ctx, paquete)
    with _abrir_almacenado(paquete) as flujo:
        with zipfile.ZipFile(flujo) as zf:
            datos = zf.read("manifest.json")
    if _sha256(datos) != paquete.huella_manifiesto:
        raise KontrolError(
            code="STORAGE_HASH_MISMATCH",
            message="El paquete almacenado no coincide con su huella registrada",
            status_code=500,
        )
    _auditar_descarga(db, ctx, paquete, "manifiesto")
    return f"manifiesto-{paquete.codigo}.json", datos


def _rechazo(motivo: str) -> KontrolError:
    """Error de validación al verificar una subida."""
    return KontrolError(code="GOV_PACKAGE_UPLOAD_INVALID", message=motivo, status_code=422)


def _copiar_subida(archivo: BinaryIO) -> tuple[Any, str, int]:
    """Copia la subida a un fichero temporal, calculando su huella y tamaño."""
    destino = tempfile.SpooledTemporaryFile(max_size=16 * 1024 * 1024)
    huella = hashlib.sha256()
    total = 0
    while True:
        trozo = archivo.read(1024 * 1024)
        if not trozo:
            break
        total += len(trozo)
        if total > MAX_SUBIDA:
            destino.close()
            raise _rechazo("El archivo supera 300 MiB")
        huella.update(trozo)
        destino.write(trozo)
    destino.seek(0)
    return destino, huella.hexdigest(), total


def _ruta_insegura(nombre: str) -> bool:
    """Comprueba si una ruta de entrada ZIP es insegura."""
    return nombre == "" or nombre.startswith("/") or "\\" in nombre or ":" in nombre or ".." in nombre.split("/")


def _entradas_seguras(zf: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
    """Valida número, unicidad, rutas, tamaño total y compresión de las entradas ZIP."""
    infos = zf.infolist()
    if len(infos) > MAX_ENTRADAS:
        raise _rechazo("El archivo tiene demasiadas entradas")

    vistos: set[str] = set()
    for info in infos:
        if info.filename in vistos:
            raise _rechazo("El archivo tiene entradas duplicadas")
        vistos.add(info.filename)
        if _ruta_insegura(info.filename):
            raise _rechazo("El archivo contiene rutas inseguras")

    if sum(info.file_size for info in infos) > MAX_DESCOMPRIMIDO:
        raise _rechazo("El contenido descomprimido supera 300 MiB")

    for info in infos:
        if info.file_size > 0 and (info.compress_size == 0 or info.file_size / info.compress_size > MAX_RAZON):
            raise _rechazo("El archivo tiene una compresión anómala")

    return infos


def _huella_de_entrada(zf: zipfile.ZipFile, nombre: str) -> tuple[str, int] | None:
    """sha256 y tamaño leídos por trozos; None si el CRC no cuadra (entrada alterada)."""
    calculo = hashlib.sha256()
    total = 0
    try:
        with zf.open(nombre) as origen:
            while True:
                trozo = origen.read(1024 * 1024)
                if not trozo:
                    break
                calculo.update(trozo)
                total += len(trozo)
    except zipfile.BadZipFile:
        return None
    return calculo.hexdigest(), total


def verificar(db, ctx, archivo: BinaryIO) -> dict[str, Any]:
    """Verifica una copia del paquete contra el registro de la empresa activa (spec §4.7)."""
    copia, huella_archivo, bytes_archivo = _copiar_subida(archivo)
    try:
        if not zipfile.is_zipfile(copia):
            raise _rechazo("El archivo no es un ZIP legible")
        copia.seek(0)
        try:
            zf = zipfile.ZipFile(copia)
        except (zipfile.BadZipFile, zipfile.LargeZipFile):
            raise _rechazo("El archivo no es un ZIP legible") from None

        with zf:
            infos = _entradas_seguras(zf)
            nombres = {i.filename for i in infos}
            motivos: list[dict[str, Any]] = []
            paquete: GovernmentAuditPackage | None = None
            no_soportada = False

            if "manifest.json" not in nombres:
                motivos.append({"codigo": "MANIFIESTO_AUSENTE", "ruta": None})
            else:
                try:
                    datos = zf.read("manifest.json")
                    contenido = json.loads(datos.decode("utf-8"))
                except (zipfile.BadZipFile, ValueError, UnicodeDecodeError):
                    contenido = None
                    motivos.append({"codigo": "MANIFIESTO_ILEGIBLE", "ruta": "manifest.json"})

                if contenido is not None:
                    if not isinstance(contenido, dict) or contenido.get("formato") != FORMATO or contenido.get("version_manifiesto") != VERSION_MANIFIESTO:
                        no_soportada = True
                    else:
                        registro = contenido.get("paquete") or {}
                        codigo = registro.get("codigo") if isinstance(registro, dict) else None
                        if isinstance(codigo, str):
                            paquete = db.scalar(
                                select(GovernmentAuditPackage).where(
                                    GovernmentAuditPackage.tenant_id == ctx.tenant_id,
                                    GovernmentAuditPackage.company_id == ctx.company_id,
                                    GovernmentAuditPackage.codigo == codigo,
                                )
                            )
                        else:
                            paquete = None

                        if paquete is None:
                            motivos.append({"codigo": "PAQUETE_NO_REGISTRADO", "ruta": None})
                        else:
                            if _sha256(datos) != paquete.huella_manifiesto:
                                motivos.append({"codigo": "MANIFIESTO_ALTERADO", "ruta": "manifest.json"})

                            listados = {a["ruta"]: a for a in paquete.manifiesto.get("archivos", [])}
                            for ruta in sorted(listados):
                                if ruta not in nombres:
                                    motivos.append({"codigo": "ARCHIVO_AUSENTE", "ruta": ruta})
                                else:
                                    medida = _huella_de_entrada(zf, ruta)
                                    esperado = (listados[ruta]["sha256"], listados[ruta]["bytes"])
                                    if medida is None or medida != esperado:
                                        motivos.append({"codigo": "ARCHIVO_ALTERADO", "ruta": ruta})

                            for nombre in sorted(nombres - set(listados) - {"manifest.json", "SHA256SUMS"}):
                                motivos.append({"codigo": "ARCHIVO_INESPERADO", "ruta": nombre})
    finally:
        copia.close()

    if no_soportada:
        resultado = "VERSION_NO_SOPORTADA"
    elif any(m["codigo"] != "ARCHIVO_AUSENTE" for m in motivos):
        resultado = "INVALIDO"
    elif motivos:
        resultado = "INCOMPLETO"
    else:
        resultado = "VALIDO"

    identico = paquete is not None and huella_archivo == paquete.huella_paquete
    verificacion_id = None
    if paquete is not None:
        verificacion = GovernmentAuditPackageVerification(
            company_id=ctx.company_id,
            package_id=str(paquete.id),
            resultado=resultado,
            motivos=motivos,
            huella_archivo=huella_archivo,
            bytes_archivo=bytes_archivo,
            identico=identico,
            created_by=ctx.user_id,
        )
        db.add(verificacion)
        db.flush()
        verificacion_id = str(verificacion.id)

    if resultado == "VALIDO" and paquete is not None:
        record_audit(
            db,
            action="GOV_AUDIT_PACKAGE_VERIFIED",
            entity_type="GovernmentAuditPackage",
            entity_id=str(paquete.id),
            tenant_id=ctx.tenant_id,
            company_id=ctx.company_id,
            user_id=ctx.user_id,
            after={"codigo": paquete.codigo, "resultado": resultado, "huella_archivo": huella_archivo, "identico": identico},
        )
    else:
        record_audit(
            db,
            action="GOV_AUDIT_PACKAGE_VERIFICATION_FAILED",
            entity_type="GovernmentAuditPackage",
            entity_id=str(paquete.id) if paquete is not None else None,
            tenant_id=ctx.tenant_id,
            company_id=ctx.company_id,
            user_id=ctx.user_id,
            after={
                "codigo": paquete.codigo if paquete is not None else None,
                "resultado": resultado,
                "motivos": [m["codigo"] for m in motivos],
                "huella_archivo": huella_archivo,
            },
        )

    return {
        "resultado": resultado,
        "motivos": motivos,
        "paquete": {"id": str(paquete.id), "codigo": paquete.codigo} if paquete is not None else None,
        "huella_archivo": huella_archivo,
        "bytes_archivo": bytes_archivo,
        "identico": identico,
        "verificacion_id": verificacion_id,
    }
