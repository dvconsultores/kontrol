"""Servicio del paquete exportable del expediente contractual (CNT-08, GOV-CNT-009).

Genera un ZIP íntegro con proyección, cronología, índice y documentos del expediente,
con verificación de integridad por SHA-256. La huella prueba integridad; no es una
firma electrónica.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, BinaryIO, cast

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import __version__
from app.core.company_context import CompanyContext
from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.documents import service as documentos
from app.modules.documents.models import Document
from app.modules.documents.storage import generate_storage_key, get_storage, safe_extension
from app.modules.government import service_expediente_contractual
from app.modules.government.models import (
    GovernmentContract,
    GovernmentContractDossierPackage,
    GovernmentContractDossierPackageVerification,
)
from app.modules.government.service_auditoria import _instante
from app.modules.government.service_paquetes import (
    ALGORITMO_HASH,
    AVISO_HUELLA,
    EXCLUIDO,
    INCLUIDO,
    MAX_BYTES,
    MAX_DOCUMENTOS,
    NO_DISPONIBLE,
    PERMISO_DESCARGA,
    SIN_PERMISO,
    _copiar_subida,
    _Documento,
    _entradas_seguras,
    _entregable,
    _evaluar,
    _huella_de_entrada,
    _json_bytes,
    _permisos,
    _rechazo,
    _sha256,
)
from app.modules.identity_access.models import User
from app.shared.audit import record_audit
from app.shared.clock import hoy_de_negocio

FORMATO = "kontrol-gobierno-expediente-contractual"
VERSION_MANIFIESTO = 1
PERMISO_PRESUPUESTO = "gobierno_presupuesto:view"
RESERVADO = "RESERVADO"
SELLADO = "SELLADO"


def _slug(texto: str) -> str:
    salida = "".join(c if c.isascii() and (c.isalnum()) else "-" for c in texto)
    salida = "-".join(t for t in salida.split("-") if t)[:60]
    return salida.strip("-")


def _nombre_de_usuario(db: Session, tenant_id: str, user_id: str | None) -> str | None:
    if not user_id:
        return None
    usuario = db.scalar(select(User).where(User.tenant_id == tenant_id, User.id == user_id))
    return usuario.username if usuario else None


def _paquete_de_empresa(db: Session, ctx: CompanyContext, paquete_id: str) -> GovernmentContractDossierPackage:
    paquete = db.scalar(
        select(GovernmentContractDossierPackage).where(
            GovernmentContractDossierPackage.id == paquete_id,
            GovernmentContractDossierPackage.tenant_id == ctx.tenant_id,
            GovernmentContractDossierPackage.company_id == ctx.company_id,
        )
    )
    if paquete is None:
        raise NotFoundError(code="GOV_CONTRACT_DOSSIER_PACKAGE_NOT_FOUND", message="El paquete no existe en este ente")
    return paquete


def _siguiente_codigo(db: Session, ctx: CompanyContext) -> str:
    prefijo = f"EC-{hoy_de_negocio().year}-"
    n = db.scalar(
        select(func.count(GovernmentContractDossierPackage.id)).where(
            GovernmentContractDossierPackage.company_id == ctx.company_id,
            GovernmentContractDossierPackage.codigo.like(f"{prefijo}%"),
        )
    ) or 0
    return f"{prefijo}{n + 1:04d}"


@dataclass
class _Incluido:
    ruta: str
    entrada: service_expediente_contractual.EntradaDocumental
    storage_key: str
    sha256: str
    bytes: int


def _incluir_documento(
    db: Session,
    ctx: CompanyContext,
    permisos: set[str],
    entrada: service_expediente_contractual.EntradaDocumental,
    numero: int,
) -> tuple[_Incluido | None, _Documento]:
    """Evalúa la entrada en el orden indicado; devuelve archivo final y documento candidato."""
    if entrada.document_id and entrada.version_id:
        candidato = _Documento(id=entrada.document_id, version_preferida=entrada.version_id)
        if entrada.estado == RESERVADO:
            candidato.estado = EXCLUIDO
            candidato.motivo = RESERVADO
        elif entrada.sellado:
            candidato.estado = EXCLUIDO
            candidato.motivo = SELLADO
        else:
            _evaluar(db, ctx, permisos, candidato)
        if candidato.estado == INCLUIDO:
            version, archivo = _entregable(candidato)
            ext = safe_extension(archivo.original_name)
            sufijo = f".{ext}" if ext else ""
            ruta = f"documentos/{numero:03d}-{_slug(entrada.referencia)}-v{version.version_number}{sufijo}"
            incluido = _Incluido(
                ruta=ruta,
                entrada=entrada,
                storage_key=archivo.storage_key,
                sha256=version.sha256,
                bytes=archivo.size,
            )
            return incluido, candidato
        return None, candidato

    if entrada.storage_key:
        if PERMISO_PRESUPUESTO not in permisos:
            candidato = _Documento(id="", version_preferida=None)
            candidato.estado = EXCLUIDO
            candidato.motivo = SIN_PERMISO
            return None, candidato
        if entrada.sha256 is None:
            candidato = _Documento(id="", version_preferida=None)
            candidato.estado = EXCLUIDO
            candidato.motivo = NO_DISPONIBLE
            return None, candidato
        if not get_storage().verify(entrada.storage_key, entrada.sha256):
            candidato = _Documento(id="", version_preferida=None)
            candidato.estado = EXCLUIDO
            candidato.motivo = NO_DISPONIBLE
            return None, candidato
        candidato = _Documento(id="", version_preferida=None)
        candidato.estado = INCLUIDO
        candidato.motivo = None
        ruta = f"comprobantes/{numero:03d}-{_slug(entrada.referencia)}.pdf"
        incluido = _Incluido(
            ruta=ruta,
            entrada=entrada,
            storage_key=entrada.storage_key,
            sha256=entrada.sha256,
            bytes=get_storage().size(entrada.storage_key),
        )
        return incluido, candidato

    candidato = _Documento(id="", version_preferida=None)
    candidato.estado = EXCLUIDO
    candidato.motivo = NO_DISPONIBLE
    return None, candidato


def _construir_zip(
    db: Session,
    ctx: CompanyContext,
    contrato: GovernmentContract,
    entradas: list[service_expediente_contractual.EntradaDocumental],
    eventos: list[dict[str, Any]],
    expediente_json: dict[str, Any],
    paquete_meta: dict[str, Any],
    corte: datetime,
    generado_por: str | None,
) -> tuple[BinaryIO, dict[str, Any], bytes]:
    permisos = _permisos(db, ctx)
    documentos_manifiesto: list[dict[str, Any]] = []
    archivos_zip: dict[str, bytes] = {}
    incluidos: dict[str, _Incluido] = {}
    numero_incluido = 0
    for entrada in entradas:
        incluido, candidato = _incluir_documento(db, ctx, permisos, entrada, numero_incluido + 1)
        if candidato.estado == INCLUIDO and incluido is not None:
            numero_incluido += 1
            incluidos[incluido.ruta] = incluido
        documento_manifiesto: dict[str, Any] = {
            "clave": entrada.clave,
            "tipo": entrada.tipo,
            "titulo": entrada.titulo,
            "referencia": entrada.referencia,
            "proceso": entrada.proceso,
            "fuente_id": entrada.fuente_id,
            "document_id": entrada.document_id,
            "version": entrada.version,
            "fecha": entrada.fecha.isoformat() if entrada.fecha else None,
            "estado_documental": entrada.estado,
            "estado": candidato.estado,
            "motivo": candidato.motivo,
            "sha256_registrado": entrada.sha256,
            "sha256": incluido.sha256 if incluido is not None else None,
            "bytes": incluido.bytes if incluido is not None else None,
            "archivo": incluido.ruta if incluido is not None else None,
            "enlace": entrada.enlace,
        }
        documentos_manifiesto.append(documento_manifiesto)

    incluidos_lista = [d for d in documentos_manifiesto if d["estado"] == INCLUIDO]
    bytes_incluidos = sum(d["bytes"] or 0 for d in incluidos_lista)

    if len(incluidos_lista) > MAX_DOCUMENTOS or bytes_incluidos > MAX_BYTES:
        raise KontrolError(
            code="GOV_CONTRACT_DOSSIER_PACKAGE_TOO_LARGE",
            message=f"El paquete excede los límites (máximo {MAX_DOCUMENTOS} documentos ó {MAX_BYTES // (1024 * 1024)} MiB)",
            status_code=422,
        )

    archivos_zip["expediente.json"] = _json_bytes(expediente_json)

    cronologia_csv = io.StringIO()
    writer = csv.writer(cronologia_csv, delimiter=";", lineterminator="\n")
    writer.writerow(["orden", "fecha", "fecha_registro", "fecha_documento", "fecha_efectiva", "proceso", "tipo", "titulo", "actor", "autoridad", "unidad", "estado", "documentos"])
    for evento in eventos:
        writer.writerow([
            evento.get("orden") or "",
            evento.get("fecha") or "",
            evento.get("fecha_registro") or "",
            evento.get("fecha_documento") or "",
            evento.get("fecha_efectiva") or "",
            evento.get("proceso") or "",
            evento.get("tipo") or "",
            evento.get("titulo") or "",
            evento.get("actor") or "",
            evento.get("autoridad") or "",
            evento.get("unidad") or "",
            evento.get("estado") or "",
            " ".join(evento.get("documentos") or []),
        ])
    archivos_zip["cronologia.csv"] = ("﻿" + cronologia_csv.getvalue()).encode("utf-8")

    indice_csv = io.StringIO()
    writer = csv.writer(indice_csv, delimiter=";", lineterminator="\n")
    writer.writerow(["clave", "tipo", "titulo", "proceso", "referencia", "version", "sha256", "fecha", "estado", "inclusion", "motivo", "archivo"])
    for d in documentos_manifiesto:
        writer.writerow([
            d["clave"],
            d["tipo"],
            d["titulo"],
            d["proceso"],
            d["referencia"],
            d["version"] or "",
            d["sha256_registrado"] or "",
            d["fecha"] or "",
            d["estado_documental"],
            d["estado"],
            d["motivo"] or "",
            d["archivo"] or "",
        ])
    archivos_zip["indice.csv"] = ("﻿" + indice_csv.getvalue()).encode("utf-8")

    fuentes_vistas: list[tuple[str, str]] = []
    for evento in eventos:
        if evento.get("fuente_id"):
            proceso = str(evento["proceso"])
            fuente_id = str(evento["fuente_id"])
            if (proceso, fuente_id) not in fuentes_vistas:
                fuentes_vistas.append((proceso, fuente_id))
    referencias_json = {
        "documentos": [
            {"clave": d["clave"], "proceso": d["proceso"], "referencia": d["referencia"], "fuente_id": d["fuente_id"], "enlace": d["enlace"]}
            for d in documentos_manifiesto
        ],
        "fuentes": [
            {"proceso": p, "fuente_id": f, "enlace": next((e.get("enlace") for e in eventos if str(e.get("proceso")) == p and str(e.get("fuente_id")) == f), None)}
            for p, f in fuentes_vistas
        ],
    }
    archivos_zip["referencias.json"] = _json_bytes(referencias_json)

    leeme = (
        "Paquete del expediente contractual KONTROL\n"
        f"Código: {paquete_meta['codigo']}\n"
        f"Contrato: {contrato.codigo}\n"
        f"Generado el: {corte.isoformat()}\n"
        f"Generado por: {generado_por or 'sistema'}\n"
        "Contenido: manifest.json, SHA256SUMS, LEEME.txt, expediente.json, cronologia.csv, indice.csv, referencias.json, documentos/ y comprobantes/.\n"
        f"{AVISO_HUELLA}\n"
        "Verificación: Gobierno › Expedientes contractuales › Verificar un paquete, o `sha256sum -c SHA256SUMS` "
        "comparando la huella de manifest.json con la registrada en KONTROL. Las fuentes no disponibles se declaran en el manifiesto.\n"
    )
    archivos_zip["LEEME.txt"] = leeme.encode("utf-8")

    archivos = sorted(
        [{"ruta": r, "bytes": len(b), "sha256": _sha256(b)} for r, b in archivos_zip.items()]
        + [{"ruta": i.ruta, "bytes": i.bytes, "sha256": i.sha256} for i in incluidos.values()],
        key=lambda a: str(a["ruta"]),
    )

    manifiesto: dict[str, Any] = {
        "formato": FORMATO,
        "version_manifiesto": VERSION_MANIFIESTO,
        "paquete": {
            "codigo": paquete_meta["codigo"],
            "numero_generacion": paquete_meta["numero_generacion"],
            "proposito": paquete_meta["proposito"],
            "corte": corte.isoformat(),
            "aviso": AVISO_HUELLA,
        },
        "contract_id": str(contrato.id),
        "contract_code": contrato.codigo,
        "company_id": ctx.company_id,
        "generated_at": corte.isoformat(),
        "generated_by": generado_por,
        "product_version": __version__,
        "included_sources": list(service_expediente_contractual.ORDEN_PROCESO) + ["PROC-06", "PROC-08", "DOC-02"],
        "excluded_sources": [
            {"proceso": f["proceso"], "titulo": f["titulo"], "estado": "SOURCE_PROCESS_NOT_AVAILABLE", "motivo": service_expediente_contractual.NO_DISPONIBLE_MENSAJE}
            for f in service_expediente_contractual.FUENTES_FUTURAS
        ],
        "hash_algorithm": ALGORITMO_HASH,
        "document_count": len(incluidos_lista),
        "event_count": len(eventos),
        "documentos": documentos_manifiesto,
        "archivos": archivos,
        "totales": {
            "eventos": len(eventos),
            "documentos_incluidos": sum(1 for d in documentos_manifiesto if d["estado"] == INCLUIDO),
            "documentos_excluidos": sum(1 for d in documentos_manifiesto if d["estado"] == EXCLUIDO),
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
    fecha = corte.astimezone(UTC).timetuple()[:6]

    def _info(ruta: str, compresion: int) -> zipfile.ZipInfo:
        zi = zipfile.ZipInfo(ruta, date_time=fecha)
        zi.compress_type = compresion
        zi.external_attr = 0o644 << 16
        return zi

    with zipfile.ZipFile(destino, mode="w") as zf:
        zf.writestr(_info("manifest.json", zipfile.ZIP_DEFLATED), manifiesto_bytes)
        zf.writestr(_info("SHA256SUMS", zipfile.ZIP_DEFLATED), sha256sums)
        for ruta in ["LEEME.txt", "expediente.json", "cronologia.csv", "indice.csv", "referencias.json"]:
            zf.writestr(_info(ruta, zipfile.ZIP_DEFLATED), archivos_zip[ruta])
        for ruta in sorted(incluidos):
            incluido = incluidos[ruta]
            with get_storage().open(incluido.storage_key) as origen, zf.open(_info(ruta, zipfile.ZIP_STORED), mode="w") as salida:
                while True:
                    trozo = origen.read(1024 * 1024)
                    if not trozo:
                        break
                    salida.write(trozo)
    destino.seek(0)
    return cast(BinaryIO, destino), manifiesto, manifiesto_bytes


def generar(
    db: Session,
    ctx: CompanyContext,
    contrato_id: str,
    proposito: str,
    idempotency_key: str | None,
) -> tuple[GovernmentContractDossierPackage, bool]:
    """Genera y registra el paquete; devuelve (paquete, creado). `creado` es False en una repetición idempotente."""
    clave_idem = idempotency_key.strip() if idempotency_key else None
    if clave_idem and len(clave_idem) > 100:
        raise KontrolError(code="VALIDATION_ERROR", message="La clave de idempotencia supera 100 caracteres", status_code=422)
    if clave_idem:
        existente = db.scalars(
            select(GovernmentContractDossierPackage).where(
                GovernmentContractDossierPackage.company_id == ctx.company_id,
                GovernmentContractDossierPackage.idempotency_key == clave_idem,
            )
        ).first()
        if existente:
            if str(existente.contract_id) != str(contrato_id):
                raise ConflictError(
                    code="GOV_CONTRACT_DOSSIER_PACKAGE_IDEMPOTENCY_CONFLICT",
                    message="La clave de idempotencia ya se usó para otro contrato",
                )
            return existente, False

    db.commit()
    if db.get_bind().dialect.name == "postgresql":
        db.connection(execution_options={"isolation_level": "REPEATABLE READ"})

    corte = datetime.now(UTC).replace(microsecond=0)
    contrato = service_expediente_contractual.contrato_formalizado(db, ctx, contrato_id)
    entradas = service_expediente_contractual.entradas_documentales(db, ctx, contrato)
    eventos = service_expediente_contractual.cronologia_completa(db, ctx, contrato)
    expediente_json = service_expediente_contractual.proyeccion(db, ctx, contrato)

    numero = (db.scalar(
        select(func.count(GovernmentContractDossierPackage.id)).where(
            GovernmentContractDossierPackage.contract_id == contrato.id,
            GovernmentContractDossierPackage.company_id == ctx.company_id,
        )
    ) or 0) + 1
    codigo = _siguiente_codigo(db, ctx)
    generado_por = _nombre_de_usuario(db, ctx.tenant_id, ctx.user_id)
    paquete_meta = {
        "codigo": codigo,
        "numero_generacion": numero,
        "proposito": proposito,
    }
    fichero, manifiesto, manifiesto_bytes = _construir_zip(db, ctx, contrato, entradas, eventos, expediente_json, paquete_meta, corte, generado_por)

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

    paquete_obj = GovernmentContractDossierPackage(
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        contract_id=str(contrato.id),
        codigo=codigo,
        numero_generacion=numero,
        proposito=proposito,
        version_manifiesto=VERSION_MANIFIESTO,
        corte=corte,
        huella_manifiesto=_sha256(manifiesto_bytes),
        huella_paquete=sha,
        bytes=tamano,
        clave_almacenamiento=clave,
        nombre_archivo=f"expediente-{codigo}.zip",
        eventos=manifiesto["totales"]["eventos"],
        documentos_incluidos=manifiesto["totales"]["documentos_incluidos"],
        documentos_excluidos=manifiesto["totales"]["documentos_excluidos"],
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
        raise ConflictError(code="GOV_CONTRACT_DOSSIER_PACKAGE_CONFLICT", message="Otro paquete se registró al mismo tiempo; vuelva a intentarlo") from None

    record_audit(
        db,
        action="GOV_CONTRACT_DOSSIER_PACKAGE_GENERATED",
        entity_type="GovernmentContractDossierPackage",
        entity_id=str(paquete_obj.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={
            "codigo": codigo,
            "contrato": contrato.codigo,
            "huella_paquete": sha,
            "huella_manifiesto": paquete_obj.huella_manifiesto,
            "tamano_bytes": tamano,
            "eventos": paquete_obj.eventos,
            "documentos_incluidos": paquete_obj.documentos_incluidos,
            "documentos_excluidos": paquete_obj.documentos_excluidos,
        },
    )
    return paquete_obj, True


def detalle(db: Session, ctx: CompanyContext, paquete: GovernmentContractDossierPackage) -> dict[str, Any]:
    """Proyecta el resumen del paquete para la API."""
    verificacion = db.scalars(
        select(GovernmentContractDossierPackageVerification)
        .where(
            GovernmentContractDossierPackageVerification.package_id == paquete.id,
            GovernmentContractDossierPackageVerification.company_id == ctx.company_id,
        )
        .order_by(GovernmentContractDossierPackageVerification.created_at.desc())
        .limit(1)
    ).first()
    return {
        "id": str(paquete.id),
        "codigo": paquete.codigo,
        "numero_generacion": paquete.numero_generacion,
        "proposito": paquete.proposito,
        "generado_en": _instante(paquete.created_at).isoformat(),
        "generado_por": _nombre_de_usuario(db, ctx.tenant_id, paquete.created_by),
        "corte": _instante(paquete.corte).isoformat(),
        "eventos": paquete.eventos,
        "documentos_incluidos": paquete.documentos_incluidos,
        "documentos_excluidos": paquete.documentos_excluidos,
        "archivos": paquete.archivos,
        "bytes": paquete.bytes,
        "huella_paquete": paquete.huella_paquete,
        "huella_manifiesto": paquete.huella_manifiesto,
        "nombre_archivo": paquete.nombre_archivo,
        "ultima_verificacion": {
            "resultado": verificacion.resultado,
            "verificado_en": _instante(verificacion.created_at).isoformat(),
        } if verificacion else None,
    }


def listar(db: Session, ctx: CompanyContext, contrato_id: str, *, limit: int, offset: int) -> dict[str, Any]:
    contrato = service_expediente_contractual.contrato_formalizado(db, ctx, contrato_id)
    total = db.scalar(
        select(func.count(GovernmentContractDossierPackage.id)).where(
            GovernmentContractDossierPackage.company_id == ctx.company_id,
            GovernmentContractDossierPackage.contract_id == contrato.id,
        )
    ) or 0
    paquetes = db.scalars(
        select(GovernmentContractDossierPackage)
        .where(
            GovernmentContractDossierPackage.company_id == ctx.company_id,
            GovernmentContractDossierPackage.contract_id == contrato.id,
        )
        .order_by(GovernmentContractDossierPackage.created_at.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return {"items": [detalle(db, ctx, p) for p in paquetes], "total": total}


def descargar(db: Session, ctx: CompanyContext, paquete_id: str) -> tuple[str, BinaryIO, int]:
    paquete = _paquete_de_empresa(db, ctx, paquete_id)
    permisos = _permisos(db, ctx)
    for doc in paquete.manifiesto.get("documentos", []):
        if doc.get("estado") != INCLUIDO:
            continue
        clave = doc.get("clave") or ""
        if clave.startswith("doc:"):
            documento = db.get(Document, doc.get("document_id") or "")
            if documento is None or PERMISO_DESCARGA not in permisos or not documentos.puede_leer_archivo(db, documento, ctx.company_id, permisos):
                raise KontrolError(code="GOV_CONTRACT_DOSSIER_PACKAGE_DOCUMENTS_FORBIDDEN", message="No tiene permiso para leer todos los documentos incluidos", status_code=403)
        elif clave.startswith("cdp:") or clave.startswith("cmp:"):
            if PERMISO_PRESUPUESTO not in permisos:
                raise KontrolError(code="GOV_CONTRACT_DOSSIER_PACKAGE_DOCUMENTS_FORBIDDEN", message="No tiene permiso para leer todos los documentos incluidos", status_code=403)

    if not get_storage().verify(paquete.clave_almacenamiento, paquete.huella_paquete):
        raise KontrolError(code="STORAGE_HASH_MISMATCH", message="El paquete almacenado no coincide con su huella registrada", status_code=500)
    flujo = get_storage().open(paquete.clave_almacenamiento)
    record_audit(
        db,
        action="GOV_CONTRACT_DOSSIER_PACKAGE_DOWNLOADED",
        entity_type="GovernmentContractDossierPackage",
        entity_id=str(paquete.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={"codigo": paquete.codigo, "contrato": paquete.manifiesto.get("contract_code")},
    )
    return paquete.nombre_archivo, flujo, paquete.bytes


def verificar(db: Session, ctx: CompanyContext, archivo: BinaryIO) -> dict[str, Any]:
    """Verifica una copia del paquete contra el registro de la empresa activa."""
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
            paquete: GovernmentContractDossierPackage | None = None
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
                                select(GovernmentContractDossierPackage).where(
                                    GovernmentContractDossierPackage.tenant_id == ctx.tenant_id,
                                    GovernmentContractDossierPackage.company_id == ctx.company_id,
                                    GovernmentContractDossierPackage.codigo == codigo,
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
        verificacion = GovernmentContractDossierPackageVerification(
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
            action="GOV_CONTRACT_DOSSIER_PACKAGE_VERIFIED",
            entity_type="GovernmentContractDossierPackage",
            entity_id=str(paquete.id),
            tenant_id=ctx.tenant_id,
            company_id=ctx.company_id,
            user_id=ctx.user_id,
            after={"codigo": paquete.codigo, "resultado": resultado, "huella_archivo": huella_archivo, "identico": identico},
        )
    else:
        record_audit(
            db,
            action="GOV_CONTRACT_DOSSIER_PACKAGE_VERIFICATION_FAILED",
            entity_type="GovernmentContractDossierPackage",
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
        "paquete": {
            "id": str(paquete.id),
            "codigo": paquete.codigo,
            "contrato_codigo": paquete.manifiesto.get("contract_code"),
        } if paquete is not None else None,
        "huella_archivo": huella_archivo,
        "bytes_archivo": bytes_archivo,
        "identico": identico,
        "verificacion_id": verificacion_id,
    }
