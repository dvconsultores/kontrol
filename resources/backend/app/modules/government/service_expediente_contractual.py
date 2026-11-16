from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext
from app.core.errors import KontrolError
from app.modules.audit.models import AuditEvent
from app.modules.documents.models import Document, DocumentVersion, StoredFile
from app.modules.documents.service import documento_sellado
from app.modules.documents.storage import get_storage
from app.modules.government.garantias_reglas import ETIQUETA_ACCION, ETIQUETA_ESTADO, ETIQUETA_TIPO
from app.modules.government.models import (
    GovernmentAct,
    GovernmentBudgetCertificate,
    GovernmentBudgetCommitment,
    GovernmentBudgetCommitmentLine,
    GovernmentContract,
    GovernmentContractAmendment,
    GovernmentContractAmendmentAllocation,
    GovernmentContractBudgetAllocation,
    GovernmentContractDossierPackage,
    GovernmentContractDossierPackageVerification,
    GovernmentContractGuarantee,
    GovernmentContractSupervisorAssignment,
    GovernmentGuaranteeEvent,
    GovernmentGuaranteeInstrument,
    GovernmentGuaranteeIssuer,
    GovernmentPosition,
    GovernmentProcurementDecision,
    GovernmentProcurementFile,
    GovernmentProcurementFileEvent,
    GovernmentProcurementFileFolio,
    GovernmentProcurementOffer,
)
from app.modules.government.monedas import canonical_currency
from app.modules.government.service_auditoria import _instante, _resumenes, _usuarios_por_ids
from app.modules.government.service_contratos import (
    ETIQUETA_ESTADO as ETIQUETA_ESTADO_CONTRATO,
)
from app.modules.government.service_contratos import (
    ETIQUETA_TIPO_INSTRUMENTO,
    _cargar,
    _resumen_modificaciones,
    _t,
    control_compromisos,
    ficha,
)
from app.modules.government.service_contratos_ejecucion import ejecucion as ejecucion_contrato
from app.modules.government.service_contratos_modificaciones import (
    ETIQUETA_ESTADO as ETIQUETA_ESTADO_MODIFICACION,
)
from app.modules.government.service_contratos_modificaciones import ETIQUETA_TIPO as ETIQUETA_TIPO_MODIFICACION
from app.modules.government.service_contratos_modificaciones import historia as historia_modificaciones
from app.modules.government.service_contratos_supervision import (
    ETIQUETA_ESTADO as ETIQUETA_ESTADO_SUPERVISION,
)
from app.modules.government.service_contratos_supervision import _etiqueta_acto, supervision, supervisor_vigente
from app.modules.government.service_expedientes import _ETIQUETAS_ESTADO, _ETIQUETAS_EVENTO
from app.modules.identity_access import authority
from app.modules.identity_access.models import User
from app.shared.clock import hoy_de_negocio, instante_actual

ORDEN_PROCESO: tuple[str, ...] = ("PROC-03", "PROC-10", "BUD-06", "BUD-08", "CNT-01", "CNT-02", "CNT-03", "CNT-04", "CNT-08")
VIGENCIAS: dict[str, str] = {"POR_INICIAR": "Por iniciar", "EN_PLAZO": "En plazo", "VENCIDO": "Plazo vencido"}
NO_DISPONIBLE_MENSAJE = "El módulo aún no está disponible: el expediente no puede afirmar si hubo actuaciones de este tipo."
FUENTES_FUTURAS: tuple[dict[str, str], ...] = (
    {"proceso": "CNT-05", "titulo": "Bloqueo de pagos por encima del monto contractual"},
    {"proceso": "CNT-06", "titulo": "Penalidades y retenciones"},
    {"proceso": "CNT-07", "titulo": "Terminación, resolución o rescisión"},
    {"proceso": "TRE-04", "titulo": "Pagos"},
)
ETIQUETA_TIPO_DOCUMENTO: dict[str, str] = {
    "INSTRUMENTO": "Instrumento contractual",
    "MODIFICACION": "Modificación contractual",
    "GARANTIA": "Garantía",
    "FOLIO": "Folio del expediente de contratación",
    "ACTO": "Acto administrativo",
    "COMPROBANTE_CDP": "Comprobante de certificación",
    "COMPROBANTE_COMPROMISO": "Comprobante de compromiso",
}
ETIQUETA_TIPO_EVENTO: dict[str, str] = {
    "CDP_EMITIDA": "Certificación emitida",
    "CDP_ANULADA": "Certificación anulada",
    "COMPROMISO_REGISTRADO": "Compromiso registrado",
    "COMPROMISO_ANULADO": "Compromiso anulado",
    "GARANTIA_REGISTRADA": "Garantía registrada",
    "CONTRATO_FORMALIZADO": "Contrato formalizado",
    "MODIFICACION_FORMALIZADA": "Modificación formalizada",
    "SUPERVISOR_DESIGNADO": "Supervisor designado",
    "SUPERVISOR_SUSTITUIDO": "Supervisor sustituido",
    "EJECUCION_INICIO": "Inicio de la ejecución",
    "EJECUCION_TERMINACION": "Terminación de la obra",
    "EJECUCION_CIERRE": "Cierre de la ejecución",
    "EJECUCION_HITO": "Hito de ejecución",
    "EJECUCION_ENTREGA": "Entrega",
    "EJECUCION_REVISION_ENTREGA": "Revisión de entrega",
    "EJECUCION_VALUACION": "Valuación presentada",
    "EJECUCION_RESOLUCION_VALUACION": "Valuación resuelta",
    "EJECUCION_RECEPCION": "Recepción",
    "EJECUCION_FACTURA": "Factura conformada",
    "PAQUETE_GENERADO": "Paquete del expediente generado",
}
for _accion, _etiqueta in ETIQUETA_ACCION.items():
    ETIQUETA_TIPO_EVENTO[f"GARANTIA_{_accion}"] = f"Garantía: {_etiqueta}"
del _accion, _etiqueta


def _iso_instante(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return _instante(dt).isoformat()


def _clave_documento_contractual(document_id: str | None, version_id: str | None) -> str | None:
    if not document_id or not version_id:
        return None
    return f"doc:{document_id}:{version_id}"


@dataclass
class EntradaDocumental:
    clave: str
    tipo: str
    titulo: str
    proceso: str
    referencia: str
    fecha: date | None
    estado: str
    fuente_id: str
    document_id: str | None = None
    version_id: str | None = None
    version: int | None = None
    sha256: str | None = None
    storage_key: str | None = None
    year_id: str | None = None
    enlace: str | None = None
    sellado: bool = False
    referencias: list[dict[str, str]] = field(default_factory=list)

    def descarga(self) -> str | None:
        if self.sellado:
            return None
        if self.proceso in ("BUD-06", "BUD-08"):
            if not self.year_id or not self.storage_key:
                return None
            segmento = "certificaciones" if self.proceso == "BUD-06" else "compromisos"
            return f"/gobierno/presupuesto/ejercicios/{self.year_id}/{segmento}/{self.fuente_id}/documento"
        if self.document_id and self.version_id:
            return f"/documentos/{self.document_id}/versiones/{self.version_id}/descargar"
        return None

    def publico(self) -> dict[str, Any]:
        return {
            "clave": self.clave,
            "tipo": self.tipo,
            "tipo_etiqueta": ETIQUETA_TIPO_DOCUMENTO[self.tipo],
            "titulo": self.titulo,
            "proceso": self.proceso,
            "referencia": self.referencia,
            "version": self.version,
            "sha256": self.sha256,
            "fecha": self.fecha.isoformat() if self.fecha else None,
            "estado": self.estado,
            "sellado": self.sellado,
            "document_id": self.document_id,
            "version_id": self.version_id,
            "descarga": self.descarga(),
            "enlace": self.enlace,
        }


def _consultar_contrato(db: Session, ctx: CompanyContext, contrato_id: str) -> GovernmentContract:
    c = _cargar(db, ctx, contrato_id)
    if c.estado != "FORMALIZADO":
        raise KontrolError(
            "GOV_CONTRACT_DOSSIER_NOT_FORMALIZED",
            "El expediente contractual existe solo para contratos formalizados",
            status_code=409,
        )
    return c


def contrato_formalizado(db: Session, ctx: CompanyContext, contrato_id: str) -> GovernmentContract:
    return _consultar_contrato(db, ctx, contrato_id)


def vigencia(fecha_inicio: date | None, fecha_fin_vigente: date | None, hoy: date) -> str:
    if fecha_inicio is not None and hoy < fecha_inicio:
        return "POR_INICIAR"
    if fecha_fin_vigente is not None and hoy > fecha_fin_vigente:
        return "VENCIDO"
    return "EN_PLAZO"


def _ids_modificaciones_formalizadas(db: Session, c: GovernmentContract) -> list[str]:
    filas = db.scalars(
        select(GovernmentContractAmendment).where(
            GovernmentContractAmendment.company_id == c.company_id,
            GovernmentContractAmendment.contract_id == c.id,
            GovernmentContractAmendment.estado == "FORMALIZADA",
        )
    ).all()
    return [str(m.id) for m in filas]


def certificados_trazados(db: Session, c: GovernmentContract) -> list[GovernmentBudgetCertificate]:
    ids: set[str] = set()

    asignaciones = db.scalars(
        select(GovernmentContractBudgetAllocation).where(
            GovernmentContractBudgetAllocation.company_id == c.company_id,
            GovernmentContractBudgetAllocation.contract_id == c.id,
        )
    ).all()
    for asignacion in asignaciones:
        if asignacion.certificate_id:
            ids.add(asignacion.certificate_id)

    for amendment_id in _ids_modificaciones_formalizadas(db, c):
        for asignacion_modificacion in db.scalars(
            select(GovernmentContractAmendmentAllocation).where(
                GovernmentContractAmendmentAllocation.company_id == c.company_id,
                GovernmentContractAmendmentAllocation.amendment_id == amendment_id,
            )
        ).all():
            if asignacion_modificacion.certificate_id:
                ids.add(asignacion_modificacion.certificate_id)

    for cert in db.scalars(
        select(GovernmentBudgetCertificate).where(
            GovernmentBudgetCertificate.company_id == c.company_id,
            GovernmentBudgetCertificate.procurement_file_id == c.file_id,
        )
    ).all():
        ids.add(str(cert.id))

    for compromiso in compromisos_trazados(db, c):
        for linea in db.scalars(
            select(GovernmentBudgetCommitmentLine).where(
                GovernmentBudgetCommitmentLine.company_id == c.company_id,
                GovernmentBudgetCommitmentLine.commitment_id == compromiso.id,
            )
        ).all():
            if linea.certificate_id:
                ids.add(linea.certificate_id)

    if not ids:
        return []
    certificados = db.scalars(
        select(GovernmentBudgetCertificate).where(
            GovernmentBudgetCertificate.company_id == c.company_id,
            GovernmentBudgetCertificate.id.in_(list(ids)),
        )
    ).all()
    return sorted(certificados, key=lambda cert: cert.codigo)


def compromisos_trazados(db: Session, c: GovernmentContract) -> list[GovernmentBudgetCommitment]:
    compromisos = db.scalars(
        select(GovernmentBudgetCommitment).where(
            GovernmentBudgetCommitment.company_id == c.company_id,
            GovernmentBudgetCommitment.procurement_file_id == c.file_id,
        )
    ).all()
    return sorted(compromisos, key=lambda comp: comp.codigo)


def _instrumento_contractual(db: Session, c: GovernmentContract) -> EntradaDocumental | None:
    if not c.document_id or not c.document_version_id:
        return None
    return EntradaDocumental(
        clave=_clave_documento_contractual(c.document_id, c.document_version_id) or "",
        tipo="INSTRUMENTO",
        titulo=c.documento_titulo or "Instrumento contractual",
        proceso="CNT-01",
        referencia=c.codigo or "",
        fecha=c.fecha_formalizacion,
        estado="DISPONIBLE",
        fuente_id=str(c.id),
        document_id=c.document_id,
        version_id=c.document_version_id,
        version=c.documento_version_numero,
        sha256=c.documento_sha256,
        enlace=f"/documentos/{c.document_id}",
    )


def _entradas_modificaciones(db: Session, c: GovernmentContract) -> list[EntradaDocumental]:
    entradas: list[EntradaDocumental] = []
    for m in db.scalars(
        select(GovernmentContractAmendment)
        .where(
            GovernmentContractAmendment.company_id == c.company_id,
            GovernmentContractAmendment.contract_id == c.id,
            GovernmentContractAmendment.estado == "FORMALIZADA",
        )
        .order_by(GovernmentContractAmendment.numero)
    ).all():
        if not m.document_id or not m.document_version_id:
            continue
        entradas.append(
            EntradaDocumental(
                clave=_clave_documento_contractual(m.document_id, m.document_version_id) or "",
                tipo="MODIFICACION",
                titulo=m.documento_titulo or ETIQUETA_TIPO_DOCUMENTO["MODIFICACION"],
                proceso="CNT-02",
                referencia=m.codigo or f"CT-{m.numero}",
                fecha=m.fecha_instrumento,
                estado="DISPONIBLE",
                fuente_id=str(m.id),
                document_id=m.document_id,
                version_id=m.document_version_id,
                version=m.documento_version_numero,
                sha256=m.documento_sha256,
                enlace=f"/documentos/{m.document_id}",
            )
        )
    return entradas


def _entradas_garantias(db: Session, c: GovernmentContract) -> list[EntradaDocumental]:
    entradas: list[EntradaDocumental] = []
    vinculos = db.scalars(
        select(GovernmentContractGuarantee)
        .where(
            GovernmentContractGuarantee.company_id == c.company_id,
            GovernmentContractGuarantee.contract_id == c.id,
        )
        .order_by(GovernmentContractGuarantee.garantia_referencia)
    ).all()
    for vinculo in vinculos:
        instrumento = db.get(GovernmentGuaranteeInstrument, vinculo.instrument_id)
        if not instrumento or instrumento.company_id != c.company_id or not instrumento.document_id or not instrumento.document_version_id:
            continue
        referencia_emisor = instrumento.referencia_emisor
        entradas.append(
            EntradaDocumental(
                clave=_clave_documento_contractual(instrumento.document_id, instrumento.document_version_id) or "",
                tipo="GARANTIA",
                titulo=f"{ETIQUETA_TIPO.get(instrumento.tipo) or 'Garantía'} · {referencia_emisor}",
                proceso="PROC-10",
                referencia=f"GAR-{instrumento.numero:02d}",
                fecha=instrumento.fecha_emision,
                estado="DISPONIBLE",
                fuente_id=str(instrumento.id),
                document_id=instrumento.document_id,
                version_id=instrumento.document_version_id,
                version=instrumento.version_numero,
                sha256=instrumento.sha256,
                enlace=f"/documentos/{instrumento.document_id}",
            )
        )
    return entradas


def _entradas_folios(db: Session, c: GovernmentContract) -> list[EntradaDocumental]:
    entradas: list[EntradaDocumental] = []
    folios = db.scalars(
        select(GovernmentProcurementFileFolio)
        .where(
            GovernmentProcurementFileFolio.company_id == c.company_id,
            GovernmentProcurementFileFolio.file_id == c.file_id,
            GovernmentProcurementFileFolio.document_id.is_not(None),
        )
        .order_by(GovernmentProcurementFileFolio.numero)
    ).all()
    for folio in folios:
        version_id = folio.document_version_id
        documento = db.get(Document, folio.document_id) if folio.document_id else None
        if version_id is None and documento is not None:
            version_id = documento.current_version_id
        version_obj = db.get(DocumentVersion, version_id) if version_id else None
        version = version_obj.version_number if version_obj else None
        sha256 = version_obj.sha256 if version_obj else None
        entradas.append(
            EntradaDocumental(
                clave=_clave_documento_contractual(folio.document_id, version_id) or "",
                tipo="FOLIO",
                titulo=folio.etiqueta,
                proceso="PROC-03",
                referencia=f"Folio {folio.numero}",
                fecha=folio.fecha_documento or folio.fecha_incorporacion,
                estado="RESERVADO" if folio.reservado else "DISPONIBLE",
                fuente_id=str(folio.id),
                document_id=folio.document_id,
                version_id=version_id,
                version=version if version_obj is not None else folio.version_numero,
                sha256=sha256,
                enlace=f"/documentos/{folio.document_id}" if folio.document_id else None,
            )
        )
    return entradas


def _documento_de_acto(db: Session, acto: GovernmentAct) -> tuple[str | None, str | None]:
    if not acto or not acto.documento_acto_id:
        return None, None
    documento = db.get(Document, acto.documento_acto_id)
    if not documento or documento.company_id != acto.company_id:
        return None, None
    return str(documento.id), documento.current_version_id


def _entrada_acto(
    db: Session,
    c: GovernmentContract,
    acto: GovernmentAct | None,
    etiqueta: str,
) -> EntradaDocumental | None:
    if not acto:
        return None
    if not acto.documento_acto_id:
        return None
    document_id, version_id = _documento_de_acto(db, acto)
    if not document_id or not version_id:
        return None
    version_obj = db.get(DocumentVersion, version_id) if version_id else None
    return EntradaDocumental(
        clave=_clave_documento_contractual(document_id, version_id) or "",
        tipo="ACTO",
        titulo=etiqueta,
        proceso="DOC-02",
        referencia=etiqueta,
        fecha=acto.fecha,
        estado="DISPONIBLE",
        fuente_id=str(acto.id),
        document_id=document_id,
        version_id=version_id,
        version=version_obj.version_number if version_obj else None,
        sha256=version_obj.sha256 if version_obj else None,
        enlace=f"/gobierno/actos/{acto.id}",
    )


def _entradas_actos(db: Session, c: GovernmentContract) -> list[EntradaDocumental]:
    entradas: list[EntradaDocumental] = []
    decision = db.get(GovernmentProcurementDecision, c.decision_id) if c.decision_id else None
    if decision and decision.company_id == c.company_id and c.act_id:
        acto = db.get(GovernmentAct, c.act_id)
        if acto and acto.company_id == c.company_id:
            entrada = _entrada_acto(db, c, acto, c.acto_etiqueta or _etiqueta_acto(acto))
            if entrada:
                entradas.append(entrada)

    designaciones = db.scalars(
        select(GovernmentContractSupervisorAssignment).where(
            GovernmentContractSupervisorAssignment.company_id == c.company_id,
            GovernmentContractSupervisorAssignment.contract_id == c.id,
            GovernmentContractSupervisorAssignment.act_id.is_not(None),
        )
    ).all()
    for designacion in designaciones:
        acto = db.get(GovernmentAct, designacion.act_id)
        if not acto or acto.company_id != c.company_id:
            continue
        entrada = _entrada_acto(db, c, acto, designacion.acto_etiqueta or _etiqueta_acto(acto))
        if entrada:
            entradas.append(entrada)
    return entradas


def _entradas_certificados(db: Session, c: GovernmentContract) -> list[EntradaDocumental]:
    return [
        EntradaDocumental(
            clave=f"cdp:{cert.id}",
            tipo="COMPROBANTE_CDP",
            titulo=f"Certificación {cert.codigo}",
            proceso="BUD-06",
            referencia=cert.codigo,
            fecha=cert.fecha,
            estado="DISPONIBLE",
            fuente_id=str(cert.id),
            sha256=cert.documento_sha256,
            storage_key=cert.documento_storage_key,
            year_id=cert.year_id,
            enlace=f"/gobierno/presupuesto/ejercicios/{cert.year_id}",
        )
        for cert in certificados_trazados(db, c)
    ]


def _entradas_compromisos(db: Session, c: GovernmentContract) -> list[EntradaDocumental]:
    return [
        EntradaDocumental(
            clave=f"cmp:{compromiso.id}",
            tipo="COMPROBANTE_COMPROMISO",
            titulo=f"Compromiso {compromiso.codigo}",
            proceso="BUD-08",
            referencia=compromiso.codigo,
            fecha=compromiso.fecha,
            estado="DISPONIBLE",
            fuente_id=str(compromiso.id),
            sha256=compromiso.documento_sha256,
            storage_key=compromiso.documento_storage_key,
            year_id=compromiso.year_id,
            enlace=f"/gobierno/presupuesto/ejercicios/{compromiso.year_id}",
        )
        for compromiso in compromisos_trazados(db, c)
    ]


def entradas_documentales(db: Session, ctx: CompanyContext, c: GovernmentContract) -> list[EntradaDocumental]:
    entradas: list[EntradaDocumental] = []
    for entrada in (
        _instrumento_contractual(db, c),
        *_entradas_modificaciones(db, c),
        *_entradas_garantias(db, c),
        *_entradas_folios(db, c),
        *_entradas_actos(db, c),
        *_entradas_certificados(db, c),
        *_entradas_compromisos(db, c),
    ):
        if entrada is None:
            continue
        entradas.append(entrada)

    indice: dict[str, EntradaDocumental] = {}
    for entrada in entradas:
        existente = indice.get(entrada.clave)
        if existente is None:
            indice[entrada.clave] = entrada
            continue
        existente.referencias = [
            *existente.referencias,
            {"tipo": entrada.tipo, "id": entrada.fuente_id},
        ]
    consolidadas = list(indice.values())
    for entrada in consolidadas:
        if entrada.document_id:
            entrada.sellado = documento_sellado(db, entrada.document_id)
    consolidadas.sort(key=lambda entrada: (entrada.fecha is None, entrada.fecha or date.min, entrada.clave))
    return consolidadas


def resultado_integridad(db: Session, entrada: EntradaDocumental) -> tuple[str, str]:
    if entrada.sha256 is None:
        return "NOT_APPLICABLE", "La autoridad no registró una huella"
    storage_key = entrada.storage_key
    if storage_key is not None:
        storage = get_storage()
        if not storage.exists(storage_key):
            return "MISSING", "El comprobante no está en el almacenamiento"
        if not storage.verify(storage_key, entrada.sha256):
            return "MISMATCH", "El comprobante almacenado no coincide con su huella"
        return "VERIFIED", "Huella comprobada"

    version = db.get(DocumentVersion, entrada.version_id) if entrada.version_id else None
    if version is None or (entrada.document_id and version.document_id != entrada.document_id):
        return "MISSING", "La versión registrada no existe"
    if version.sha256 != entrada.sha256:
        return "MISMATCH", "La versión no coincide con la huella registrada por la autoridad"
    stored = db.get(StoredFile, version.stored_file_id) if version.stored_file_id else None
    if stored is None or not get_storage().exists(stored.storage_key):
        return "MISSING", "El archivo no está en el almacenamiento"
    if not get_storage().verify(stored.storage_key, entrada.sha256):
        return "MISMATCH", "El archivo almacenado no coincide con su huella"
    return "VERIFIED", "Huella comprobada"


def integridad(db: Session, ctx: CompanyContext, contrato_id: str) -> dict[str, Any]:
    c = contrato_formalizado(db, ctx, contrato_id)
    documentos: list[dict[str, Any]] = []
    resumen = {"VERIFIED": 0, "MISSING": 0, "MISMATCH": 0, "NOT_APPLICABLE": 0}
    for entrada in entradas_documentales(db, ctx, c):
        resultado, detalle = resultado_integridad(db, entrada)
        resumen[resultado] += 1
        documentos.append(
            {
                "clave": entrada.clave,
                "titulo": entrada.titulo,
                "tipo": entrada.tipo,
                "sha256_registrado": entrada.sha256,
                "resultado": resultado,
                "detalle": detalle,
            }
        )
    return {
        "verificado_en": _iso_instante(instante_actual()),
        "resumen": resumen,
        "documentos": documentos,
    }


def _eventos_proc03(db: Session, ctx: CompanyContext, c: GovernmentContract) -> list[dict[str, Any]]:
    eventos = db.scalars(
        select(GovernmentProcurementFileEvent).where(
            GovernmentProcurementFileEvent.company_id == c.company_id,
            GovernmentProcurementFileEvent.file_id == c.file_id,
            GovernmentProcurementFileEvent.clase.not_in(["CONTRATO", "GARANTIA"]),
        )
    ).all()
    usuarios = _usuarios_por_ids(db, [e.created_by for e in eventos if e.created_by is not None], ctx.tenant_id)
    nodos: list[dict[str, Any]] = []
    for evento in eventos:
        nodos.append(
            {
                "fecha": evento.fecha,
                "fecha_registro": _iso_instante(evento.created_at),
                "fecha_documento": None,
                "fecha_efectiva": None,
                "tipo": evento.clase,
                "tipo_etiqueta": _ETIQUETAS_EVENTO.get(evento.clase, evento.clase),
                "proceso": "PROC-03",
                "fuente_id": str(evento.id),
                "titulo": evento.titulo,
                "actor": usuarios.get(evento.created_by) if evento.created_by is not None else None,
                "autoridad": evento.acto_etiqueta,
                "unidad": None,
                "documentos": [],
                "estado": evento.resultado,
                "enlace": f"/gobierno/contrataciones/expedientes/{c.file_id}",
            }
        )
    return nodos


def _eventos_proc10(db: Session, c: GovernmentContract) -> list[dict[str, Any]]:
    vinculos = db.scalars(
        select(GovernmentContractGuarantee).where(
            GovernmentContractGuarantee.company_id == c.company_id,
            GovernmentContractGuarantee.contract_id == c.id,
        )
    ).all()
    nodos: list[dict[str, Any]] = []
    for vinculo in vinculos:
        instrumento = db.get(GovernmentGuaranteeInstrument, vinculo.instrument_id)
        if not instrumento or instrumento.company_id != c.company_id:
            continue
        clave_instrumento = _clave_documento_contractual(instrumento.document_id, instrumento.document_version_id)
        nodos.append(
            {
                "fecha": instrumento.fecha_emision,
                "fecha_registro": _iso_instante(instrumento.registrada_en),
                "fecha_documento": instrumento.fecha_emision,
                "fecha_efectiva": instrumento.vigente_desde,
                "tipo": "GARANTIA_REGISTRADA",
                "tipo_etiqueta": ETIQUETA_TIPO_EVENTO["GARANTIA_REGISTRADA"],
                "proceso": "PROC-10",
                "fuente_id": str(instrumento.id),
                "titulo": f"{ETIQUETA_TIPO.get(instrumento.tipo) or 'Garantía'} GAR-{instrumento.numero:02d}",
                "actor": None,
                "autoridad": None,
                "unidad": None,
                "documentos": [clave_instrumento] if clave_instrumento else [],
                "estado": ETIQUETA_ESTADO[instrumento.estado],
                "enlace": f"/gobierno/contrataciones/expedientes/{c.file_id}",
            }
        )
        for evento in db.scalars(
            select(GovernmentGuaranteeEvent).where(
                GovernmentGuaranteeEvent.company_id == c.company_id,
                GovernmentGuaranteeEvent.instrument_id == instrumento.id,
                GovernmentGuaranteeEvent.accion != "REGISTRO",
            )
        ).all():
            nodos.append(
                {
                    "fecha": evento.fecha,
                    "fecha_registro": _iso_instante(evento.registrada_en),
                    "fecha_documento": None,
                    "fecha_efectiva": None,
                    "tipo": f"GARANTIA_{evento.accion}",
                    "tipo_etiqueta": ETIQUETA_TIPO_EVENTO.get(f"GARANTIA_{evento.accion}", evento.accion),
                    "proceso": "PROC-10",
                    "fuente_id": str(evento.id),
                    "titulo": f"{ETIQUETA_ACCION.get(evento.accion, evento.accion)} de GAR-{instrumento.numero:02d}",
                    "actor": None,
                    "autoridad": None,
                    "unidad": None,
                    "documentos": [],
                    "estado": evento.motivo,
                    "enlace": f"/gobierno/contrataciones/expedientes/{c.file_id}",
                }
            )
    return nodos


def _eventos_bud06(db: Session, c: GovernmentContract) -> list[dict[str, Any]]:
    nodos: list[dict[str, Any]] = []
    for cert in certificados_trazados(db, c):
        nodos.append(
            {
                "fecha": cert.fecha,
                "fecha_registro": _iso_instante(cert.emitida_en),
                "fecha_documento": None,
                "fecha_efectiva": None,
                "tipo": "CDP_EMITIDA",
                "tipo_etiqueta": ETIQUETA_TIPO_EVENTO["CDP_EMITIDA"],
                "proceso": "BUD-06",
                "fuente_id": str(cert.id),
                "titulo": f"Certificación {cert.codigo} · {_t(cert.monto)} {cert.moneda}",
                "actor": cert.firmante_funcionario_nombre,
                "autoridad": cert.firmante_cargo_nombre,
                "unidad": cert.firmante_unidad,
                "documentos": [f"cdp:{cert.id}"],
                "estado": cert.estado,
                "enlace": f"/gobierno/presupuesto/ejercicios/{cert.year_id}",
            }
        )
        if cert.anulada_en:
            nodos.append(
                {
                    "fecha": cert.anulada_en.date(),
                    "fecha_registro": _iso_instante(cert.anulada_en),
                    "fecha_documento": None,
                    "fecha_efectiva": None,
                    "tipo": "CDP_ANULADA",
                    "tipo_etiqueta": ETIQUETA_TIPO_EVENTO["CDP_ANULADA"],
                    "proceso": "BUD-06",
                    "fuente_id": str(cert.id),
                    "titulo": f"Certificación {cert.codigo}",
                    "actor": None,
                    "autoridad": None,
                    "unidad": None,
                    "documentos": [],
                    "estado": cert.motivo_anulacion,
                    "enlace": f"/gobierno/presupuesto/ejercicios/{cert.year_id}",
                }
            )
    return nodos


def _lineas_compromiso(db: Session, compromiso: GovernmentBudgetCommitment) -> list[GovernmentBudgetCommitmentLine]:
    return list(
        db.scalars(
            select(GovernmentBudgetCommitmentLine).where(
                GovernmentBudgetCommitmentLine.company_id == compromiso.company_id,
                GovernmentBudgetCommitmentLine.commitment_id == compromiso.id,
            )
        ).all()
    )


def _eventos_bud08(db: Session, c: GovernmentContract) -> list[dict[str, Any]]:
    nodos: list[dict[str, Any]] = []
    for compromiso in compromisos_trazados(db, c):
        total = sum((linea.monto for linea in _lineas_compromiso(db, compromiso)), Decimal("0"))
        nodos.append(
            {
                "fecha": compromiso.fecha,
                "fecha_registro": _iso_instante(compromiso.emitido_en),
                "fecha_documento": None,
                "fecha_efectiva": None,
                "tipo": "COMPROMISO_REGISTRADO",
                "tipo_etiqueta": ETIQUETA_TIPO_EVENTO["COMPROMISO_REGISTRADO"],
                "proceso": "BUD-08",
                "fuente_id": str(compromiso.id),
                "titulo": f"Compromiso {compromiso.codigo} · {_t(total)} {compromiso.moneda}",
                "actor": compromiso.autoridad_funcionario_nombre,
                "autoridad": compromiso.autoridad_cargo_nombre,
                "unidad": compromiso.autoridad_unidad,
                "documentos": [f"cmp:{compromiso.id}"],
                "estado": compromiso.estado,
                "enlace": f"/gobierno/presupuesto/ejercicios/{compromiso.year_id}",
            }
        )
        if compromiso.anulado_en:
            nodos.append(
                {
                    "fecha": compromiso.anulado_en.date(),
                    "fecha_registro": _iso_instante(compromiso.anulado_en),
                    "fecha_documento": None,
                    "fecha_efectiva": None,
                    "tipo": "COMPROMISO_ANULADO",
                    "tipo_etiqueta": ETIQUETA_TIPO_EVENTO["COMPROMISO_ANULADO"],
                    "proceso": "BUD-08",
                    "fuente_id": str(compromiso.id),
                    "titulo": f"Compromiso {compromiso.codigo}",
                    "actor": None,
                    "autoridad": None,
                    "unidad": None,
                    "documentos": [],
                    "estado": compromiso.motivo_anulacion,
                    "enlace": f"/gobierno/presupuesto/ejercicios/{compromiso.year_id}",
                }
            )
    return nodos


def _clave_instrumento_contractual(c: GovernmentContract) -> str | None:
    return _clave_documento_contractual(c.document_id, c.document_version_id)


def _eventos_cnt01(db: Session, ctx: CompanyContext, c: GovernmentContract) -> list[dict[str, Any]]:
    usuarios = _usuarios_por_ids(db, [c.formalizado_por] if c.formalizado_por else [], ctx.tenant_id)
    clave = _clave_instrumento_contractual(c)
    return [
        {
            "fecha": c.fecha_formalizacion,
            "fecha_registro": _iso_instante(c.formalizado_en),
            "fecha_documento": None,
            "fecha_efectiva": c.fecha_inicio,
            "tipo": "CONTRATO_FORMALIZADO",
            "tipo_etiqueta": ETIQUETA_TIPO_EVENTO["CONTRATO_FORMALIZADO"],
            "proceso": "CNT-01",
            "fuente_id": str(c.id),
            "titulo": f"{ETIQUETA_TIPO_INSTRUMENTO.get(c.tipo or '') or 'Contrato'} {c.codigo} formalizado",
            "actor": usuarios.get(c.formalizado_por) if c.formalizado_por else None,
            "autoridad": c.firmante_cargo_nombre,
            "unidad": None,
            "documentos": [clave] if clave else [],
            "estado": ETIQUETA_ESTADO_CONTRATO[c.estado],
            "enlace": f"/gobierno/contratos/{c.id}",
        }
    ]


def _eventos_cnt02(db: Session, ctx: CompanyContext, c: GovernmentContract) -> list[dict[str, Any]]:
    modificaciones = db.scalars(
        select(GovernmentContractAmendment)
        .where(
            GovernmentContractAmendment.company_id == c.company_id,
            GovernmentContractAmendment.contract_id == c.id,
            GovernmentContractAmendment.estado == "FORMALIZADA",
        )
        .order_by(GovernmentContractAmendment.numero)
    ).all()
    autores = [m.formalizado_por for m in modificaciones if m.formalizado_por]
    usuarios = _usuarios_por_ids(db, autores, ctx.tenant_id)
    nodos: list[dict[str, Any]] = []
    for m in modificaciones:
        clave = _clave_documento_contractual(m.document_id, m.document_version_id)
        nodos.append(
            {
                "fecha": m.fecha_instrumento,
                "fecha_registro": _iso_instante(m.formalizado_en),
                "fecha_documento": m.fecha_instrumento,
                "fecha_efectiva": m.vigente_desde,
                "tipo": "MODIFICACION_FORMALIZADA",
                "tipo_etiqueta": ETIQUETA_TIPO_EVENTO["MODIFICACION_FORMALIZADA"],
                "proceso": "CNT-02",
                "fuente_id": str(m.id),
                "titulo": f"{ETIQUETA_TIPO_MODIFICACION.get(m.tipo) or 'Modificación'} {m.codigo or f'CT-{m.numero}'}",
                "actor": usuarios.get(m.formalizado_por) if m.formalizado_por else None,
                "autoridad": m.firmante_cargo_nombre,
                "unidad": None,
                "documentos": [clave] if clave else [],
                "estado": ETIQUETA_ESTADO_MODIFICACION.get(m.estado, m.estado),
                "enlace": f"/gobierno/contratos/{c.id}/modificaciones/{m.id}",
            }
        )
    return nodos


def _eventos_cnt04(db: Session, ctx: CompanyContext, c: GovernmentContract) -> list[dict[str, Any]]:
    designaciones = db.scalars(
        select(GovernmentContractSupervisorAssignment)
        .where(
            GovernmentContractSupervisorAssignment.company_id == c.company_id,
            GovernmentContractSupervisorAssignment.contract_id == c.id,
        )
        .order_by(GovernmentContractSupervisorAssignment.numero)
    ).all()
    nodos: list[dict[str, Any]] = []
    for designacion in designaciones:
        acto = db.get(GovernmentAct, designacion.act_id) if designacion.act_id else None
        clave_acto = None
        if acto and acto.documento_acto_id:
            documento = db.get(Document, acto.documento_acto_id)
            if documento and documento.company_id == c.company_id and documento.current_version_id:
                clave_acto = _clave_documento_contractual(str(documento.id), documento.current_version_id)
        nodos.append(
            {
                "fecha": designacion.desde,
                "fecha_registro": _iso_instante(designacion.registrado_en),
                "fecha_documento": acto.fecha if acto else None,
                "fecha_efectiva": designacion.desde,
                "tipo": "SUPERVISOR_SUSTITUIDO" if designacion.sustituye_id else "SUPERVISOR_DESIGNADO",
                "tipo_etiqueta": ETIQUETA_TIPO_EVENTO[
                    "SUPERVISOR_SUSTITUIDO" if designacion.sustituye_id else "SUPERVISOR_DESIGNADO"
                ],
                "proceso": "CNT-04",
                "fuente_id": str(designacion.id),
                "titulo": f"{designacion.funcionario_nombre} · SUP-{designacion.numero:02d}",
                "actor": None,
                "autoridad": designacion.acto_emisor_cargo,
                "unidad": designacion.unidad_nombre,
                "documentos": [clave_acto] if clave_acto else [],
                "estado": ETIQUETA_ESTADO_SUPERVISION.get(designacion.estado, designacion.estado),
                "enlace": f"/gobierno/contratos/{c.id}",
            }
        )
    return nodos


def _eventos_cnt08(db: Session, ctx: CompanyContext, c: GovernmentContract) -> list[dict[str, Any]]:
    paquetes = db.scalars(
        select(GovernmentContractDossierPackage)
        .where(
            GovernmentContractDossierPackage.company_id == c.company_id,
            GovernmentContractDossierPackage.contract_id == c.id,
        )
        .order_by(GovernmentContractDossierPackage.created_at)
    ).all()
    usuarios = _usuarios_por_ids(db, [p.created_by for p in paquetes if p.created_by is not None], ctx.tenant_id)
    nodos: list[dict[str, Any]] = []
    for paquete in paquetes:
        nodos.append(
            {
                "fecha": paquete.created_at.date(),
                "fecha_registro": _iso_instante(paquete.created_at),
                "fecha_documento": None,
                "fecha_efectiva": None,
                "tipo": "PAQUETE_GENERADO",
                "tipo_etiqueta": ETIQUETA_TIPO_EVENTO["PAQUETE_GENERADO"],
                "proceso": "CNT-08",
                "fuente_id": str(paquete.id),
                "titulo": f"Paquete {paquete.codigo}",
                "actor": usuarios.get(paquete.created_by) if paquete.created_by is not None else None,
                "autoridad": None,
                "unidad": None,
                "documentos": [],
                "estado": None,
                "enlace": None,
            }
        )
    return nodos


def _eventos_cnt03(db: Session, ctx: CompanyContext, c: GovernmentContract) -> list[dict[str, Any]]:
    nodos: list[dict[str, Any]] = []
    for ev in ejecucion_contrato(db, ctx, str(c.id))["cronologia"]:
        tipo = f"EJECUCION_{ev['tipo'].upper()}"
        titulo = f"{ev['referencia']} · {ev['titulo']}"
        if ev["monto"]:
            titulo = f"{titulo} · {ev['monto']} {ev['moneda']}"
        nodos.append(
            {
                "fecha": date.fromisoformat(ev["fecha"]),
                "fecha_registro": None,
                "fecha_documento": None,
                "fecha_efectiva": None,
                "tipo": tipo,
                "tipo_etiqueta": ETIQUETA_TIPO_EVENTO.get(tipo, ev["tipo"]),
                "proceso": "CNT-03",
                "fuente_id": ev["referencia"],
                "titulo": titulo,
                "actor": None,
                "autoridad": None,
                "unidad": None,
                "documentos": [],
                "estado": ev["estado"],
                "enlace": f"/gobierno/contratos/{c.id}/ejecucion",
            }
        )
    return nodos


def cronologia_completa(db: Session, ctx: CompanyContext, c: GovernmentContract) -> list[dict[str, Any]]:
    nodos: list[dict[str, Any]] = [
        *_eventos_proc03(db, ctx, c),
        *_eventos_proc10(db, c),
        *_eventos_bud06(db, c),
        *_eventos_bud08(db, c),
        *_eventos_cnt01(db, ctx, c),
        *_eventos_cnt02(db, ctx, c),
        *_eventos_cnt03(db, ctx, c),
        *_eventos_cnt04(db, ctx, c),
        *_eventos_cnt08(db, ctx, c),
    ]

    def _clave_orden(nodo: dict[str, Any]) -> tuple[Any, ...]:
        fecha = nodo["fecha"]
        fecha_registro = nodo["fecha_registro"]
        try:
            proceso_pos = ORDEN_PROCESO.index(nodo["proceso"])
        except ValueError:
            proceso_pos = len(ORDEN_PROCESO)
        return (fecha is None, fecha or date.min, fecha_registro is None, fecha_registro or "", proceso_pos)

    nodos.sort(key=_clave_orden)
    for indice, nodo in enumerate(nodos, start=1):
        nodo["orden"] = indice
        nodo["fecha"] = nodo["fecha"].isoformat() if nodo["fecha"] else None
    return nodos


def cronologia(
    db: Session,
    ctx: CompanyContext,
    contrato_id: str,
    *,
    proceso: str | None,
    desde: date | None,
    hasta: date | None,
    limit: int,
    offset: int,
) -> dict[str, Any]:
    c = contrato_formalizado(db, ctx, contrato_id)
    filas = cronologia_completa(db, ctx, c)
    if proceso:
        filas = [fila for fila in filas if fila["proceso"] == proceso]
    if desde:
        filas = [fila for fila in filas if fila["fecha"] is not None and fila["fecha"] >= desde.isoformat()]
    if hasta:
        filas = [fila for fila in filas if fila["fecha"] is not None and fila["fecha"] <= hasta.isoformat()]
    total = len(filas)
    return {
        "items": filas[offset : offset + limit],
        "total": total,
        "limit": limit,
        "offset": offset,
        "procesos": list(ORDEN_PROCESO),
    }


def ids_del_expediente(db: Session, c: GovernmentContract) -> list[str]:
    ids: list[str] = []
    for valor in (c.file_id, c.id, c.decision_id):
        if valor is not None and str(valor) not in ids:
            ids.append(str(valor))
    for m in db.scalars(
        select(GovernmentContractAmendment).where(
            GovernmentContractAmendment.company_id == c.company_id,
            GovernmentContractAmendment.contract_id == c.id,
        )
    ).all():
        if str(m.id) not in ids:
            ids.append(str(m.id))
    for designacion in db.scalars(
        select(GovernmentContractSupervisorAssignment).where(
            GovernmentContractSupervisorAssignment.company_id == c.company_id,
            GovernmentContractSupervisorAssignment.contract_id == c.id,
        )
    ).all():
        if str(designacion.id) not in ids:
            ids.append(str(designacion.id))
    vinculos = db.scalars(
        select(GovernmentContractGuarantee).where(
            GovernmentContractGuarantee.company_id == c.company_id,
            GovernmentContractGuarantee.contract_id == c.id,
        )
    ).all()
    for vinculo in vinculos:
        instrumento = db.get(GovernmentGuaranteeInstrument, vinculo.instrument_id)
        if instrumento and instrumento.company_id == c.company_id and str(instrumento.id) not in ids:
            ids.append(str(instrumento.id))
    for cert in certificados_trazados(db, c):
        if str(cert.id) not in ids:
            ids.append(str(cert.id))
    for compromiso in compromisos_trazados(db, c):
        if str(compromiso.id) not in ids:
            ids.append(str(compromiso.id))
    for paquete in db.scalars(
        select(GovernmentContractDossierPackage).where(
            GovernmentContractDossierPackage.company_id == c.company_id,
            GovernmentContractDossierPackage.contract_id == c.id,
        )
    ).all():
        if str(paquete.id) not in ids:
            ids.append(str(paquete.id))
    return ids


def auditoria(db: Session, ctx: CompanyContext, contrato_id: str, *, limit: int, offset: int) -> dict[str, Any]:
    c = contrato_formalizado(db, ctx, contrato_id)
    ids = ids_del_expediente(db, c)
    condicion = (
        AuditEvent.tenant_id == ctx.tenant_id,
        AuditEvent.company_id == ctx.company_id,
        AuditEvent.entity_id.in_(ids),
    )
    total = db.scalar(select(func.count(AuditEvent.id)).where(*condicion)) or 0
    filas = db.scalars(
        select(AuditEvent)
        .where(*condicion)
        .order_by(AuditEvent.event_time.desc(), AuditEvent.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    resumenes = _resumenes(db, filas)
    return {
        "items": [
            {
                "id": resumen.id,
                "fecha": resumen.fecha.isoformat(),
                "proceso": resumen.proceso,
                "proceso_nombre": resumen.proceso_nombre,
                "accion": resumen.accion,
                "accion_etiqueta": resumen.accion_etiqueta,
                "entidad": resumen.entidad,
                "usuario": resumen.usuario,
                "enlace": f"/gobierno/auditoria?evento={resumen.id}",
            }
            for resumen in resumenes
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def _permisos(db: Session, ctx: CompanyContext) -> set[str]:
    usuario = db.get(User, ctx.user_id)
    if usuario is None:
        return set()
    return authority.capabilities_in_company(db, usuario, ctx.company_id)


def _origen(db: Session, c: GovernmentContract) -> dict[str, Any]:
    expediente = db.get(GovernmentProcurementFile, c.file_id) if c.file_id else None
    oferta = db.get(GovernmentProcurementOffer, c.offer_id) if c.offer_id else None
    return {
        "expediente": (
            {
                "id": str(expediente.id),
                "numero": expediente.numero,
                "objeto": expediente.objeto,
                "tipo_contratacion": expediente.tipo_contratacion,
                "modalidad": expediente.modalidad_declarada,
                "unidad": expediente.unidad_nombre,
                "estado": _ETIQUETAS_ESTADO.get(expediente.status, expediente.status),
                "fecha_inicio": expediente.fecha_inicio.isoformat() if expediente.fecha_inicio else None,
                "enlace": f"/gobierno/contrataciones/expedientes/{expediente.id}",
            }
            if expediente and expediente.company_id == c.company_id
            else None
        ),
        "oferta": (
            {
                "id": str(oferta.id),
                "referencia": c.oferta_referencia,
                "oferente": oferta.oferente_nombre,
                "documento": oferta.oferente_documento,
                "recibida_en": _iso_instante(oferta.recibida_en),
            }
            if oferta and oferta.company_id == c.company_id
            else None
        ),
    }


def _adjudicacion(db: Session, c: GovernmentContract, vigente: bool) -> dict[str, Any]:
    decision = db.get(GovernmentProcurementDecision, c.decision_id) if c.decision_id else None
    if decision is None or decision.company_id != c.company_id:
        return {
            "id": str(c.decision_id) if c.decision_id else None,
            "referencia": c.decision_referencia,
            "fecha": c.decision_fecha.isoformat() if c.decision_fecha else None,
            "resultado": None,
            "motivacion": None,
            "vigente": vigente,
            "acto": None,
            "cargo": None,
            "enlace": f"/gobierno/contrataciones/expedientes/{c.file_id}",
        }
    cargo = db.get(GovernmentPosition, decision.cargo_id) if decision.cargo_id else None
    return {
        "id": str(decision.id),
        "referencia": c.decision_referencia,
        "fecha": c.decision_fecha.isoformat() if c.decision_fecha else None,
        "resultado": decision.resultado,
        "motivacion": decision.motivacion,
        "vigente": vigente,
        "acto": (
            {
                "id": str(c.act_id),
                "etiqueta": c.acto_etiqueta,
                "enlace": f"/gobierno/actos/{c.act_id}",
            }
            if c.act_id
            else None
        ),
        "cargo": cargo.name if cargo else None,
        "enlace": f"/gobierno/contrataciones/expedientes/{c.file_id}",
    }

def _asignaciones_certificado(db: Session, c: GovernmentContract, certificate_id: str) -> tuple[Decimal, Decimal]:
    contrato_total = sum(
        (
            asignacion.monto
            for asignacion in db.scalars(
                select(GovernmentContractBudgetAllocation).where(
                    GovernmentContractBudgetAllocation.company_id == c.company_id,
                    GovernmentContractBudgetAllocation.contract_id == c.id,
                    GovernmentContractBudgetAllocation.certificate_id == certificate_id,
                )
            ).all()
        ),
        Decimal("0"),
    )
    mod_total = Decimal("0")
    for amendment_id in _ids_modificaciones_formalizadas(db, c):
        mod_total += sum(
            (
                asignacion.monto
                for asignacion in db.scalars(
                    select(GovernmentContractAmendmentAllocation).where(
                        GovernmentContractAmendmentAllocation.company_id == c.company_id,
                        GovernmentContractAmendmentAllocation.amendment_id == amendment_id,
                        GovernmentContractAmendmentAllocation.certificate_id == certificate_id,
                    )
                ).all()
            ),
            Decimal("0"),
        )
    return contrato_total, mod_total


def _certificados_publicos(db: Session, c: GovernmentContract) -> list[dict[str, Any]]:
    filas: list[dict[str, Any]] = []
    for cert in certificados_trazados(db, c):
        asignado_contrato, asignado_modificaciones = _asignaciones_certificado(db, c, str(cert.id))
        filas.append(
            {
                "id": str(cert.id),
                "codigo": cert.codigo,
                "fecha": cert.fecha.isoformat() if cert.fecha else None,
                "monto": _t(cert.monto),
                "moneda": cert.moneda,
                "estado": cert.estado,
                "concepto": cert.concepto,
                "asignado_contrato": _t(asignado_contrato),
                "asignado_modificaciones": _t(asignado_modificaciones),
                "comprobante_sha256": cert.documento_sha256,
                "enlace": f"/gobierno/presupuesto/ejercicios/{cert.year_id}",
            }
        )
    return filas


def _compromisos_publicos(db: Session, c: GovernmentContract) -> list[dict[str, Any]]:
    filas: list[dict[str, Any]] = []
    for compromiso in compromisos_trazados(db, c):
        lineas: list[dict[str, Any]] = []
        total = Decimal("0")
        for linea in _lineas_compromiso(db, compromiso):
            total += linea.monto
            cert = db.get(GovernmentBudgetCertificate, linea.certificate_id) if linea.certificate_id else None
            lineas.append(
                {
                    "certificado_codigo": cert.codigo if cert and cert.company_id == c.company_id else None,
                    "monto": _t(linea.monto),
                }
            )
        filas.append(
            {
                "id": str(compromiso.id),
                "codigo": compromiso.codigo,
                "fecha": compromiso.fecha.isoformat() if compromiso.fecha else None,
                "estado": compromiso.estado,
                "moneda": compromiso.moneda,
                "total": _t(total),
                "concepto": compromiso.concepto,
                "lineas": lineas,
                "comprobante_sha256": compromiso.documento_sha256,
                "enlace": f"/gobierno/presupuesto/ejercicios/{compromiso.year_id}",
            }
        )
    return filas


def _garantias_publicas(db: Session, c: GovernmentContract) -> list[dict[str, Any]]:
    vinculos = db.scalars(
        select(GovernmentContractGuarantee)
        .where(
            GovernmentContractGuarantee.company_id == c.company_id,
            GovernmentContractGuarantee.contract_id == c.id,
        )
        .order_by(GovernmentContractGuarantee.garantia_referencia)
    ).all()
    filas: list[dict[str, Any]] = []
    for vinculo in vinculos:
        instrumento = db.get(GovernmentGuaranteeInstrument, vinculo.instrument_id)
        if not instrumento or instrumento.company_id != c.company_id:
            continue
        emisor = db.get(GovernmentGuaranteeIssuer, instrumento.issuer_id) if instrumento.issuer_id else None
        eventos = db.scalars(
            select(GovernmentGuaranteeEvent)
            .where(
                GovernmentGuaranteeEvent.company_id == c.company_id,
                GovernmentGuaranteeEvent.instrument_id == instrumento.id,
            )
            .order_by(GovernmentGuaranteeEvent.fecha, GovernmentGuaranteeEvent.registrada_en)
        ).all()
        filas.append(
            {
                "instrumento_id": str(instrumento.id),
                "referencia": vinculo.garantia_referencia,
                "tipo_etiqueta": ETIQUETA_TIPO.get(instrumento.tipo) or instrumento.tipo,
                "emisor": emisor.nombre if emisor else None,
                "monto": _t(instrumento.monto),
                "moneda": instrumento.moneda,
                "vigente_desde": instrumento.vigente_desde.isoformat() if instrumento.vigente_desde else None,
                "vigente_hasta": instrumento.vigente_hasta.isoformat() if instrumento.vigente_hasta else None,
                "estado": instrumento.estado,
                "estado_etiqueta": ETIQUETA_ESTADO.get(instrumento.estado, instrumento.estado),
                "documento": {
                    "id": instrumento.document_id,
                    "version": instrumento.version_numero,
                    "sha256": instrumento.sha256,
                },
                "eventos": [
                    {
                        "accion": evento.accion,
                        "accion_etiqueta": ETIQUETA_ACCION.get(evento.accion, evento.accion),
                        "fecha": evento.fecha.isoformat() if evento.fecha else None,
                        "motivo": evento.motivo,
                    }
                    for evento in eventos
                ],
                "enlace": f"/gobierno/contrataciones/expedientes/{c.file_id}",
            }
        )
    return filas


def _actos_publicos(db: Session, c: GovernmentContract) -> list[dict[str, Any]]:
    filas: list[tuple[GovernmentAct, str]] = []
    if c.act_id:
        acto = db.get(GovernmentAct, c.act_id)
        if acto and acto.company_id == c.company_id:
            filas.append((acto, "ADJUDICACION"))
    for designacion in db.scalars(
        select(GovernmentContractSupervisorAssignment).where(
            GovernmentContractSupervisorAssignment.company_id == c.company_id,
            GovernmentContractSupervisorAssignment.contract_id == c.id,
            GovernmentContractSupervisorAssignment.act_id.is_not(None),
        )
    ).all():
        acto = db.get(GovernmentAct, designacion.act_id)
        if acto and acto.company_id == c.company_id:
            filas.append((acto, "DESIGNACION_SUPERVISOR"))
    for folio in db.scalars(
        select(GovernmentProcurementFileFolio).where(
            GovernmentProcurementFileFolio.company_id == c.company_id,
            GovernmentProcurementFileFolio.file_id == c.file_id,
            GovernmentProcurementFileFolio.act_id.is_not(None),
        )
    ).all():
        acto = db.get(GovernmentAct, folio.act_id)
        if acto and acto.company_id == c.company_id:
            filas.append((acto, "FOLIO"))

    vistos: set[str] = set()
    publicos: list[dict[str, Any]] = []
    for acto, rol in sorted(filas, key=lambda par: (par[0].fecha is not None, par[0].fecha)):
        if str(acto.id) in vistos:
            continue
        vistos.add(str(acto.id))
        publicos.append(
            {
                "id": str(acto.id),
                "etiqueta": _etiqueta_acto(acto),
                "tipo": acto.tipo,
                "numero": acto.numero,
                "fecha": acto.fecha.isoformat() if acto.fecha else None,
                "estado": acto.status,
                "asunto": acto.asunto,
                "rol": rol,
                "enlace": f"/gobierno/actos/{acto.id}",
            }
        )
    return publicos


def _supervisor_actual(db: Session, ctx: CompanyContext, c: GovernmentContract) -> dict[str, Any] | None:
    actual = supervisor_vigente(db, ctx, str(c.id))
    if not actual:
        return None
    return {
        "referencia": actual.get("referencia"),
        "nombre": (actual.get("funcionario") or {}).get("nombre"),
        "cargo": (actual.get("cargo") or {}).get("nombre"),
        "unidad": (actual.get("unidad") or {}).get("nombre"),
    }


def proyeccion(db: Session, ctx: CompanyContext, c: GovernmentContract) -> dict[str, Any]:
    detalle = ficha(db, ctx, str(c.id))
    ej = ejecucion_contrato(db, ctx, str(c.id))
    historia = historia_modificaciones(db, ctx, str(c.id), None)
    hoy = hoy_de_negocio()
    fecha_inicio_original = c.fecha_inicio
    fecha_fin_vigente_str = historia["vigente"].get("fecha_fin")
    fecha_fin_vigente = date.fromisoformat(fecha_fin_vigente_str) if fecha_fin_vigente_str else None
    vigencia_actual = vigencia(fecha_inicio_original, fecha_fin_vigente, hoy)
    monto_vigente_str = historia["vigente"].get("monto")
    cobertura = detalle.get("cobertura") or {}
    resumen = {
        "codigo": c.codigo,
        "tipo_etiqueta": detalle.get("tipo_etiqueta"),
        "contratista": {
            "nombre": c.contratista_nombre,
            "documento": c.contratista_documento,
            "representante": c.contratista_representante,
        },
        "objeto": c.objeto,
        "monto_original": detalle.get("monto"),
        "monto_vigente": monto_vigente_str,
        "moneda": detalle.get("moneda"),
        "fecha_inicio": detalle.get("fecha_inicio"),
        "fecha_fin_original": detalle.get("fecha_fin"),
        "fecha_fin_vigente": fecha_fin_vigente_str,
        "vigencia": vigencia_actual,
        "vigencia_etiqueta": VIGENCIAS[vigencia_actual],
        "adjudicacion_referencia": c.decision_referencia,
        "expediente_numero": c.expediente_numero,
        "supervisor_actual": _supervisor_actual(db, ctx, c),
        "cobertura": {
            "total_asignado": cobertura.get("total_asignado"),
            "completa": cobertura.get("completa"),
            "moneda": detalle.get("moneda"),
        },
        "ejecucion": {"estado": ej["resumen"]["estado_ejecucion"], "mensaje": ej["resumen"]["estado_etiqueta"]},
    }
    instrumento_original = {
        "monto": detalle.get("monto"),
        "moneda": detalle.get("moneda"),
        "fecha_inicio": detalle.get("fecha_inicio"),
        "fecha_fin": detalle.get("fecha_fin"),
        "referencia_instrumento": c.referencia_instrumento,
        "fecha_formalizacion": detalle.get("fecha_formalizacion"),
        "firmante": detalle.get("firmante"),
        "documento": detalle.get("documento"),
        "huella": detalle.get("huella"),
        "enlace": f"/gobierno/contratos/{c.id}",
    }
    supervisoria = supervision(db, ctx, str(c.id))
    entradas = entradas_documentales(db, ctx, c)
    return {
        "contrato": {
            "id": str(c.id),
            "codigo": c.codigo,
            "tipo": c.tipo,
            "tipo_etiqueta": detalle.get("tipo_etiqueta"),
            "estado": c.estado,
        },
        "resumen": resumen,
        "origen": _origen(db, c),
        "adjudicacion": _adjudicacion(db, c, bool(detalle["decision"]["vigente"])),
        "presupuesto": {
            "certificados": _certificados_publicos(db, c),
            "compromisos": _compromisos_publicos(db, c),
            "control": control_compromisos(db, c.company_id, c.file_id, Decimal(historia["vigente"].get("monto") or "0"), c.moneda),
            "efectos": "Este expediente no crea certificaciones ni compromisos ni cambia disponibilidades.",
        },
        "instrumento": {
            "original": instrumento_original,
            "vigente": historia["vigente"],
            "fecha_consulta": hoy.isoformat(),
        },
        "garantias": _garantias_publicas(db, c),
        "modificaciones": {
            "cantidad": len(historia["historial"]),
            "historial": [
                {**nodo, "enlace": f"/gobierno/contratos/{c.id}/modificaciones/{nodo['id']}"}
                for nodo in historia["historial"]
            ],
        },
        "supervision": {
            "vigente": supervisoria.get("vigente"),
            "programada": supervisoria.get("programada"),
            "historia": supervisoria.get("historia"),
        },
        "ejecucion": {
            "proceso": "CNT-03",
            "estado": "DISPONIBLE",
            "estado_ejecucion": ej["resumen"]["estado_ejecucion"],
            "estado_etiqueta": ej["resumen"]["estado_etiqueta"],
            "resumen": {
                clave: ej["resumen"][clave]
                for clave in (
                    "valuado_conformado",
                    "valuado_presentado",
                    "saldo",
                    "facturado",
                    "hitos_total",
                    "hitos_cumplidos",
                    "entregables_pendientes",
                )
            },
            "inicio": ej["inicio"],
            "terminacion": ej["terminacion"],
            "cierre": ej["cierre"],
            "hitos": ej["hitos"],
            "entregables": ej["entregables"],
            "valuaciones": ej["valuaciones"],
            "recepciones": ej["recepciones"],
            "facturas": ej["facturas"],
            "enlace": f"/gobierno/contratos/{c.id}/ejecucion",
        },
        "fuentes_futuras": [
            {**fuente, "estado": "SOURCE_PROCESS_NOT_AVAILABLE", "mensaje": NO_DISPONIBLE_MENSAJE}
            for fuente in FUENTES_FUTURAS
        ],
        "actos": _actos_publicos(db, c),
        "documentos": [entrada.publico() for entrada in entradas],
        "cronologia_total": len(cronologia_completa(db, ctx, c)),
    }


def expediente(db: Session, ctx: CompanyContext, contrato_id: str) -> dict[str, Any]:
    c = contrato_formalizado(db, ctx, contrato_id)
    base = proyeccion(db, ctx, c)
    caps = _permisos(db, ctx)
    base["permisos"] = {
        "auditoria": "gobierno_auditoria:view" in caps,
        "ver_paquetes": "gobierno_paquetes:view" in caps,
        "generar_paquete": "gobierno_paquetes:generate" in caps,
    }
    return base


def _ultimo_paquete(db: Session, c: GovernmentContract) -> dict[str, Any] | None:
    paquete = db.scalars(
        select(GovernmentContractDossierPackage)
        .where(
            GovernmentContractDossierPackage.company_id == c.company_id,
            GovernmentContractDossierPackage.contract_id == c.id,
        )
        .order_by(GovernmentContractDossierPackage.created_at.desc(), GovernmentContractDossierPackage.id.desc())
        .limit(1)
    ).first()
    if paquete is None:
        return None
    verificacion = db.scalars(
        select(GovernmentContractDossierPackageVerification)
        .where(
            GovernmentContractDossierPackageVerification.company_id == c.company_id,
            GovernmentContractDossierPackageVerification.package_id == paquete.id,
        )
        .order_by(
            GovernmentContractDossierPackageVerification.created_at.desc(),
            GovernmentContractDossierPackageVerification.id.desc(),
        )
        .limit(1)
    ).first()
    return {
        "codigo": paquete.codigo,
        "generado_en": _iso_instante(paquete.created_at),
        "verificacion": verificacion.resultado if verificacion else None,
    }


def _ultima_actuacion(db: Session, ctx: CompanyContext, c: GovernmentContract) -> dict[str, Any] | None:
    hoy = hoy_de_negocio()
    candidatas: list[dict[str, Any]] = []

    def _agregar(fecha: date | None, registro: datetime | None, titulo: str, proceso: str) -> None:
        if fecha is None:
            return
        candidatas.append(
            {
                "_fecha": fecha,
                "_registro": registro,
                "fecha": fecha.isoformat(),
                "titulo": titulo,
                "proceso": proceso,
            }
        )

    _agregar(c.fecha_formalizacion, c.formalizado_en, f"{ETIQUETA_TIPO_INSTRUMENTO.get(c.tipo or '') or 'Contrato'} {c.codigo} formalizado", "CNT-01")
    for m in db.scalars(
        select(GovernmentContractAmendment).where(
            GovernmentContractAmendment.company_id == c.company_id,
            GovernmentContractAmendment.contract_id == c.id,
            GovernmentContractAmendment.estado == "FORMALIZADA",
        )
    ).all():
        _agregar(m.fecha_instrumento, m.formalizado_en, f"{ETIQUETA_TIPO_MODIFICACION.get(m.tipo) or 'Modificación'} {m.codigo}", "CNT-02")
    for designacion in db.scalars(
        select(GovernmentContractSupervisorAssignment).where(
            GovernmentContractSupervisorAssignment.company_id == c.company_id,
            GovernmentContractSupervisorAssignment.contract_id == c.id,
            GovernmentContractSupervisorAssignment.desde <= hoy,
        )
    ).all():
        _agregar(designacion.desde, designacion.registrado_en, f"{designacion.funcionario_nombre} · SUP-{designacion.numero:02d}", "CNT-04")
    for paquete in db.scalars(
        select(GovernmentContractDossierPackage).where(
            GovernmentContractDossierPackage.company_id == c.company_id,
            GovernmentContractDossierPackage.contract_id == c.id,
        )
    ).all():
        _agregar(paquete.created_at.date(), paquete.created_at, f"Paquete {paquete.codigo}", "CNT-08")

    if not candidatas:
        return None
    candidatas.sort(key=lambda fila: (fila["_fecha"], fila["_registro"] is None, fila["_registro"] or ""))
    elegida = candidatas[-1]
    return {"fecha": elegida["fecha"], "titulo": elegida["titulo"], "proceso": elegida["proceso"]}


def listar(
    db: Session,
    ctx: CompanyContext,
    *,
    codigo: str | None,
    expediente_numero: str | None,
    contratista: str | None,
    tipo: str | None,
    vigencia_filtro: str | None,
    supervisor: str | None,
    desde: date | None,
    hasta: date | None,
    limit: int,
    offset: int,
) -> dict[str, Any]:
    consulta = select(GovernmentContract).where(
        GovernmentContract.company_id == ctx.company_id,
        GovernmentContract.estado == "FORMALIZADO",
    )
    if codigo:
        consulta = consulta.where(GovernmentContract.codigo.ilike(f"%{codigo}%"))
    if expediente_numero:
        consulta = consulta.where(GovernmentContract.expediente_numero.ilike(f"%{expediente_numero}%"))
    if contratista:
        consulta = consulta.where(
            or_(
                GovernmentContract.contratista_nombre.ilike(f"%{contratista}%"),
                GovernmentContract.contratista_documento.ilike(f"%{contratista}%"),
            )
        )
    if tipo:
        consulta = consulta.where(GovernmentContract.tipo == tipo)
    if supervisor:
        hoy = hoy_de_negocio()
        subconsulta = select(GovernmentContractSupervisorAssignment.contract_id).where(
            GovernmentContractSupervisorAssignment.company_id == ctx.company_id,
            GovernmentContractSupervisorAssignment.estado == "VIGENTE",
            GovernmentContractSupervisorAssignment.desde <= hoy,
            GovernmentContractSupervisorAssignment.funcionario_nombre.ilike(f"%{supervisor}%"),
        )
        consulta = consulta.where(GovernmentContract.id.in_(subconsulta))
    if desde:
        consulta = consulta.where(GovernmentContract.fecha_formalizacion >= desde)
    if hasta:
        consulta = consulta.where(GovernmentContract.fecha_formalizacion <= hasta)

    consulta = consulta.order_by(
        GovernmentContract.fecha_formalizacion.desc(),
        GovernmentContract.codigo.desc(),
    )

    def _item(c: GovernmentContract) -> dict[str, Any]:
        resumen_mod = _resumen_modificaciones(db, c)
        fecha_fin_vigente = None
        fecha_fin_vigente_str = (resumen_mod.get("vigente") or {}).get("fecha_fin")
        if fecha_fin_vigente_str:
            fecha_fin_vigente = date.fromisoformat(fecha_fin_vigente_str)
        estado_vigencia = vigencia(c.fecha_inicio, fecha_fin_vigente, hoy_de_negocio())
        supervisor_dict = _supervisor_actual(db, ctx, c)
        return {
            "id": str(c.id),
            "codigo": c.codigo,
            "tipo": c.tipo,
            "tipo_etiqueta": ETIQUETA_TIPO_INSTRUMENTO.get(c.tipo) if c.tipo else None,
            "contratista": {"nombre": c.contratista_nombre, "documento": c.contratista_documento},
            "objeto": c.objeto,
            "monto_original": _t(Decimal(c.monto)),
            "monto_vigente": (resumen_mod.get("vigente") or {}).get("monto"),
            "moneda": canonical_currency(c.moneda),
            "fecha_inicio": c.fecha_inicio.isoformat() if c.fecha_inicio else None,
            "fecha_fin_original": c.fecha_fin.isoformat() if c.fecha_fin else None,
            "fecha_fin_vigente": fecha_fin_vigente_str,
            "vigencia": estado_vigencia,
            "vigencia_etiqueta": VIGENCIAS[estado_vigencia],
            "supervisor": (
                {"nombre": supervisor_dict.get("nombre"), "cargo": supervisor_dict.get("cargo")}
                if supervisor_dict
                else None
            ),
            "expediente": {"id": str(c.file_id) if c.file_id else None, "numero": c.expediente_numero},
            "fecha_formalizacion": c.fecha_formalizacion.isoformat() if c.fecha_formalizacion else None,
            "modificaciones": resumen_mod.get("cantidad", 0),
            "ultimo_paquete": _ultimo_paquete(db, c),
            "ultima_actuacion": _ultima_actuacion(db, ctx, c),
        }

    if vigencia_filtro:
        contratos = list(db.scalars(consulta).all())
        items_proyectados = []
        for c in contratos:
            item = _item(c)
            if item["vigencia"] == vigencia_filtro:
                items_proyectados.append(item)
        return {
            "items": items_proyectados[offset : offset + limit],
            "total": len(items_proyectados),
            "limit": limit,
            "offset": offset,
        }

    total = db.scalar(select(func.count()).select_from(consulta.subquery())) or 0
    contratos = list(db.scalars(consulta.offset(offset).limit(limit)).all())
    items = [_item(c) for c in contratos]
    return {"items": items, "total": total, "limit": limit, "offset": offset}
