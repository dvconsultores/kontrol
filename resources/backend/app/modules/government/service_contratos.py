"""Contrato u orden derivada de la adjudicación (CNT-01, GOV-CNT-001)."""
from __future__ import annotations

import hashlib
import json
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext
from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.core.integrity import es_violacion_unica
from app.modules.documents.models import Document, DocumentLink, DocumentVersion
from app.modules.documents.service import congelar_vinculo, documento_sellado, sellar_documento, verificar_integridad
from app.modules.government.garantias_reglas import ETIQUETA_TIPO
from app.modules.government.models import (
    PREFIJOS_INSTRUMENTO_CONTRATO,
    TIPOS_INSTRUMENTO_CONTRATO,
    GovernmentAct,
    GovernmentBudgetCertificate,
    GovernmentBudgetClassifierItem,
    GovernmentBudgetCredit,
    GovernmentBudgetFundingSource,
    GovernmentBudgetYear,
    GovernmentContract,
    GovernmentContractBudgetAllocation,
    GovernmentContractGuarantee,
    GovernmentGuaranteeInstrument,
    GovernmentGuaranteeIssuer,
    GovernmentOfficial,
    GovernmentPosition,
    GovernmentProcurementFile,
    GovernmentProcurementOffer,
    GovernmentStructure,
)
from app.modules.government.service_actos import _autoridad_valida
from app.modules.government.service_decision_limite import (
    ESTADOS_LIMITE,
    _monto_vigente,
    clasificar_monto,
    competencia_en_vigor,
    limite_de_competencia,
)
from app.modules.government.service_decision_resolver import _decision_vigente
from app.modules.government.service_expedientes import _abierto, _evento
from app.modules.government.service_identidad import _funcionario_del_actor, exigir_autoridad_funcional
from app.modules.government.service_sod import evaluar_antes_de_actuar
from app.shared.audit import record_audit, record_audit_after_rollback
from app.shared.clock import hoy_de_negocio, instante_actual

ENTIDAD = "GovernmentProcurementFile"
ETIQUETA_ESTADO = {"BORRADOR": "Borrador", "FORMALIZADO": "Formalizado"}
ETIQUETA_TIPO_INSTRUMENTO = {
    "CONTRATO": "Contrato",
    "ORDEN_COMPRA": "Orden de compra",
    "ORDEN_SERVICIO": "Orden de servicio",
}
EJERCICIOS_VIGENTES = ("APROBADO", "RECONDUCIDO")
CODIGOS_FIRMANTE = {
    "EXCEDE_LIMITE": "GOV_CONTRACT_SIGNER_AMOUNT_EXCEEDED",
    "MONEDA_DISTINTA": "GOV_CONTRACT_SIGNER_CURRENCY_MISMATCH",
}
BLOQUEO_CODIGO = 7012001


def _inv(campo: str, mensaje: str, code: str = "GOV_CONTRACT_INVALID") -> KontrolError:
    return KontrolError(code, "Datos del contrato inválidos", field_errors={campo: [mensaje]}, status_code=422)


def _t(valor: Decimal) -> str:
    return f"{Decimal(valor):.2f}"


def _identificacion(c: GovernmentContract) -> str:
    if c.codigo:
        return c.codigo
    return f"Borrador · {c.expediente_numero} · {c.decision_referencia}"


def _auditar(db: Session, ctx: CompanyContext, accion: str, expediente_id: str, after: dict[str, Any]) -> None:
    record_audit(
        db,
        action=accion,
        entity_type=ENTIDAD,
        entity_id=expediente_id,
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={k: v for k, v in after.items() if v is not None},
    )


def _cargar(db: Session, ctx: CompanyContext, contrato_id: str) -> GovernmentContract:
    contrato = db.scalar(
        select(GovernmentContract).where(
            GovernmentContract.company_id == ctx.company_id,
            GovernmentContract.id == contrato_id,
        )
    )
    if contrato is None:
        raise NotFoundError("GOV_CONTRACT_NOT_FOUND", "Contrato u orden no encontrado")
    return contrato


def _para_escribir(db: Session, ctx: CompanyContext, contrato_id: str, version: int | None) -> GovernmentContract:
    if version is None:
        raise KontrolError("GOV_CONTRACT_IF_MATCH_REQUIRED", "Se requiere la versión del contrato", status_code=428)
    contrato = db.scalar(
        select(GovernmentContract)
        .where(
            GovernmentContract.company_id == ctx.company_id,
            GovernmentContract.id == contrato_id,
        )
        .with_for_update()
    )
    if contrato is None:
        raise NotFoundError("GOV_CONTRACT_NOT_FOUND", "Contrato u orden no encontrado")
    if contrato.version != version:
        raise ConflictError(
            "GOV_CONTRACT_STALE",
            "El contrato fue modificado por otro usuario",
            details={"version_actual": contrato.version},
        )
    if contrato.estado != "BORRADOR":
        raise ConflictError("GOV_CONTRACT_ALREADY_FORMALIZED", "El contrato ya está formalizado y no admite cambios")
    return contrato


def _expediente(
    db: Session, ctx: CompanyContext, file_id: str, bloquear: bool
) -> GovernmentProcurementFile:
    stmt = select(GovernmentProcurementFile).where(
        GovernmentProcurementFile.company_id == ctx.company_id,
        GovernmentProcurementFile.id == file_id,
    )
    if bloquear:
        stmt = stmt.with_for_update()
    expediente = db.scalar(stmt)
    if expediente is None:
        raise NotFoundError("GOV_PROCUREMENT_FILE_NOT_FOUND", "Expediente no encontrado")
    return expediente


def _adjudicacion_vigente(db: Session, c: GovernmentContract) -> bool:
    d = _decision_vigente(db, c.file_id)
    return d is not None and d.id == c.decision_id and d.resultado == "ADJUDICADA" and d.offer_id == c.offer_id


def _exigir_adjudicacion_vigente(db: Session, c: GovernmentContract) -> None:
    if not _adjudicacion_vigente(db, c):
        raise ConflictError(
            "GOV_CONTRACT_AWARD_NOT_CURRENT",
            "La adjudicación de origen ya no está vigente: este contrato no puede modificarse ni formalizarse",
        )


def _anio_ejercicio(db: Session, year_id: str) -> int | None:
    ejercicio = db.get(GovernmentBudgetYear, year_id)
    return ejercicio.anio if ejercicio else None


def _etiqueta_credito(db: Session, cert: GovernmentBudgetCertificate) -> tuple[str, str]:
    credit = db.get(GovernmentBudgetCredit, cert.credit_id)
    if credit is None:
        return "", ""
    item = db.get(GovernmentBudgetClassifierItem, credit.item_id) if credit.item_id else None
    source = db.get(GovernmentBudgetFundingSource, credit.source_id) if credit.source_id else None
    partida = f"{item.codigo} · {item.denominacion}" if item else ""
    fuente = f"{source.codigo} · {source.denominacion}" if source else ""
    return partida, fuente


def _asignado_formalizado(db: Session, cert_id: str, excluir_contrato_id: str) -> Decimal:
    total = db.scalar(
        select(func.coalesce(func.sum(GovernmentContractBudgetAllocation.monto), Decimal("0"))).join(
            GovernmentContract,
            GovernmentContract.id == GovernmentContractBudgetAllocation.contract_id,
        ).where(
            GovernmentContractBudgetAllocation.certificate_id == cert_id,
            GovernmentContract.estado == "FORMALIZADO",
            GovernmentContract.id != excluir_contrato_id,
        )
    )
    return Decimal(total or Decimal("0"))


def _saldo_libre(db: Session, cert: GovernmentBudgetCertificate, excluir_contrato_id: str) -> Decimal:
    return Decimal(cert.monto) - _asignado_formalizado(db, str(cert.id), excluir_contrato_id)


def _motivo_certificado(
    db: Session, ctx: CompanyContext, c: GovernmentContract, cert: GovernmentBudgetCertificate | None
) -> str | None:
    if cert is None or cert.company_id != ctx.company_id:
        return "La certificación no existe en este ente"
    if cert.estado != "VIGENTE":
        return f"La certificación {cert.codigo} está anulada"
    if cert.moneda != c.moneda:
        return f"La certificación {cert.codigo} está en {cert.moneda} y el contrato en {c.moneda}: no se convierten monedas"
    anio = db.get(GovernmentBudgetYear, cert.year_id)
    if anio is None or anio.estado not in EJERCICIOS_VIGENTES:
        return f"El ejercicio de la certificación {cert.codigo} no está aprobado"
    if cert.procurement_file_id is not None and cert.procurement_file_id != c.file_id:
        return f"La certificación {cert.codigo} corresponde a otro expediente"
    return None


def _documento_valido(
    db: Session, ctx: CompanyContext, c: GovernmentContract, documento_id: str | None
) -> tuple[Document, DocumentVersion, DocumentLink] | None:
    if not documento_id:
        return None
    doc = db.scalar(
        select(Document).where(
            Document.company_id == ctx.company_id,
            Document.id == documento_id,
            Document.status.in_(("DRAFT", "ACTIVE")),
        )
    )
    if doc is None or doc.current_version_id is None or documento_sellado(db, str(doc.id)):
        return None
    version = db.scalar(
        select(DocumentVersion).where(
            DocumentVersion.id == doc.current_version_id,
            DocumentVersion.document_id == doc.id,
        )
    )
    if version is None:
        return None
    link = db.scalar(
        select(DocumentLink).where(
            DocumentLink.document_id == doc.id,
            DocumentLink.resource_type == "GovernmentProcurementFile",
            DocumentLink.resource_id == c.file_id,
        )
    )
    if link is None:
        return None
    return doc, version, link


def _cobertura(db: Session, c: GovernmentContract) -> dict[str, Any]:
    asignaciones = db.scalars(
        select(GovernmentContractBudgetAllocation)
        .where(GovernmentContractBudgetAllocation.contract_id == c.id)
        .order_by(GovernmentContractBudgetAllocation.certificado_codigo)
    ).all()
    items: list[dict[str, Any]] = []
    total = Decimal("0")
    for asig in asignaciones:
        cert = db.get(GovernmentBudgetCertificate, asig.certificate_id)
        partida, fuente = _etiqueta_credito(db, cert) if cert else ("", "")
        items.append(
            {
                "certificado_id": asig.certificate_id,
                "codigo": asig.certificado_codigo,
                "monto": _t(Decimal(asig.monto)),
                "moneda": asig.moneda,
                "anio": _anio_ejercicio(db, asig.year_id),
                "partida": partida,
                "fuente": fuente,
                "estado": cert.estado if cert else None,
            }
        )
        total += Decimal(asig.monto)
    return {
        "asignaciones": items,
        "total_asignado": _t(total),
        "faltante": _t(max(Decimal(c.monto) - total, Decimal("0"))),
        "completa": total == Decimal(c.monto),
    }


def _garantias(db: Session, c: GovernmentContract) -> list[dict[str, Any]]:
    vinculos = db.scalars(
        select(GovernmentContractGuarantee)
        .where(GovernmentContractGuarantee.contract_id == c.id)
        .order_by(GovernmentContractGuarantee.garantia_referencia)
    ).all()
    items: list[dict[str, Any]] = []
    for vinculo in vinculos:
        instrumento = db.get(GovernmentGuaranteeInstrument, vinculo.instrument_id)
        if instrumento is None:
            continue
        emisor = db.get(GovernmentGuaranteeIssuer, instrumento.issuer_id)
        items.append(
            {
                "instrumento_id": instrumento.id,
                "referencia": f"GAR-{instrumento.numero:02d}",
                "tipo_etiqueta": ETIQUETA_TIPO.get(instrumento.tipo, instrumento.tipo),
                "emisor": emisor.nombre if emisor else None,
                "monto": _t(Decimal(instrumento.monto)),
                "moneda": instrumento.moneda,
                "vigente_hasta": instrumento.vigente_hasta.isoformat(),
                "estado": instrumento.estado,
            }
        )
    return items


def _certificados_elegibles(db: Session, ctx: CompanyContext, c: GovernmentContract) -> list[dict[str, Any]]:
    certs = db.scalars(
        select(GovernmentBudgetCertificate)
        .where(
            GovernmentBudgetCertificate.company_id == ctx.company_id,
            GovernmentBudgetCertificate.estado == "VIGENTE",
            GovernmentBudgetCertificate.moneda == c.moneda,
        )
        .order_by(GovernmentBudgetCertificate.codigo)
    ).all()
    items: list[dict[str, Any]] = []
    for cert in certs:
        if _motivo_certificado(db, ctx, c, cert) is not None:
            continue
        saldo = _saldo_libre(db, cert, str(c.id))
        if saldo <= 0:
            continue
        partida, fuente = _etiqueta_credito(db, cert)
        items.append(
            {
                "id": cert.id,
                "codigo": cert.codigo,
                "monto": _t(Decimal(cert.monto)),
                "saldo_libre": _t(saldo),
                "moneda": cert.moneda,
                "anio": _anio_ejercicio(db, cert.year_id),
                "partida": partida,
                "fuente": fuente,
                "concepto": cert.concepto,
            }
        )
    return items


def _garantias_elegibles(db: Session, ctx: CompanyContext, c: GovernmentContract) -> list[dict[str, Any]]:
    instrumentos = db.scalars(
        select(GovernmentGuaranteeInstrument)
        .where(
            GovernmentGuaranteeInstrument.company_id == ctx.company_id,
            GovernmentGuaranteeInstrument.file_id == c.file_id,
            GovernmentGuaranteeInstrument.offer_id == c.offer_id,
            GovernmentGuaranteeInstrument.estado == "REGISTRADA",
        )
        .order_by(GovernmentGuaranteeInstrument.numero)
    ).all()
    items: list[dict[str, Any]] = []
    for instrumento in instrumentos:
        emisor = db.get(GovernmentGuaranteeIssuer, instrumento.issuer_id)
        items.append(
            {
                "instrumento_id": instrumento.id,
                "referencia": f"GAR-{instrumento.numero:02d}",
                "tipo_etiqueta": ETIQUETA_TIPO.get(instrumento.tipo, instrumento.tipo),
                "emisor": emisor.nombre if emisor else None,
                "monto": _t(Decimal(instrumento.monto)),
                "moneda": instrumento.moneda,
                "vigente_hasta": instrumento.vigente_hasta.isoformat(),
                "estado": instrumento.estado,
            }
        )
    return items


def _documentos_elegibles(db: Session, ctx: CompanyContext, c: GovernmentContract) -> list[dict[str, Any]]:
    documentos = db.scalars(
        select(Document)
        .join(DocumentLink, DocumentLink.document_id == Document.id)
        .where(
            Document.company_id == ctx.company_id,
            Document.status.in_(("DRAFT", "ACTIVE")),
            Document.current_version_id.is_not(None),
            DocumentLink.resource_type == "GovernmentProcurementFile",
            DocumentLink.resource_id == c.file_id,
        )
        .order_by(Document.title)
    ).all()
    items: list[dict[str, Any]] = []
    for doc in documentos:
        if documento_sellado(db, str(doc.id)):
            continue
        version = db.get(DocumentVersion, doc.current_version_id)
        if version is None:
            continue
        items.append({"id": doc.id, "titulo": doc.title, "version": version.version_number})
    return items


def _mensaje_firmante(estado: str, cargo_nombre: str, c: GovernmentContract, limite: dict[str, Any]) -> str:
    m = _t(Decimal(c.monto))
    mon = c.moneda
    lim = limite["monto"]
    mon_l = limite["moneda"]
    if estado == "DENTRO_LIMITE":
        return f"El monto del contrato ({m} {mon}) está dentro del límite de firma de {cargo_nombre} ({lim} {mon_l})."
    if estado == "SIN_LIMITE":
        return f"{cargo_nombre} firma contrataciones sin límite de monto."
    if estado == "EXCEDE_LIMITE":
        return f"El monto del contrato ({m} {mon}) excede el límite de firma de {cargo_nombre} ({lim} {mon_l}). Elija un firmante con límite suficiente."
    if estado == "MONEDA_DISTINTA":
        return f"No puede verificarse el límite de este firmante porque el contrato y el límite están expresados en monedas diferentes. El contrato está en {mon} y el límite de {cargo_nombre} es {lim} {mon_l}. Elija un firmante con límite en {mon} o sin límite."
    return f"{cargo_nombre} no tiene hoy la competencia Firmar sobre Contrataciones."


def _control_firmante(
    db: Session, c: GovernmentContract, cargo: GovernmentPosition, fecha: date
) -> tuple[dict[str, Any], dict[str, Any]]:
    comp = competencia_en_vigor(db, cargo, fecha, "FIRMAR", "CONTRATACIONES")
    limite = limite_de_competencia(cargo, comp)
    estado = clasificar_monto(
        limite["tipo_limite"],
        limite["monto"],
        limite["moneda"],
        Decimal(c.monto),
        c.moneda,
    )
    control = {
        "estado": estado,
        "estado_etiqueta": ESTADOS_LIMITE[estado],
        "permite": estado in ("DENTRO_LIMITE", "SIN_LIMITE"),
        "mensaje": _mensaje_firmante(estado, cargo.name, c, limite),
    }
    return limite, control


def _firmantes(db: Session, ctx: CompanyContext, c: GovernmentContract) -> list[dict[str, Any]]:
    hoy = hoy_de_negocio()
    cargos = db.scalars(
        select(GovernmentPosition)
        .where(GovernmentPosition.company_id == ctx.company_id)
        .order_by(GovernmentPosition.name)
    ).all()
    items: list[dict[str, Any]] = []
    for cargo in cargos:
        comp = competencia_en_vigor(db, cargo, hoy, "FIRMAR", "CONTRATACIONES")
        if comp is None:
            continue
        limite, control = _control_firmante(db, c, cargo, hoy)
        items.append({"cargo_id": cargo.id, "cargo": cargo.name, "limite": limite, "control": control})
    return items


def _pendientes(db: Session, c: GovernmentContract) -> list[str]:
    pendientes: list[str] = []
    if not _adjudicacion_vigente(db, c):
        pendientes.append("La adjudicación de origen ya no está vigente: este borrador no puede formalizarse")
    if c.tipo is None:
        pendientes.append("Elija el tipo de instrumento")
    if c.fecha_inicio is None or c.fecha_fin is None:
        pendientes.append("Registre el plazo del instrumento (inicio y fin)")
    if c.referencia_instrumento is None:
        pendientes.append("Indique la referencia del instrumento")
    if c.document_id is None:
        pendientes.append("Adjunte el instrumento contractual firmado")
    cobertura = _cobertura(db, c)
    if not cobertura["completa"]:
        pendientes.append(f"Falta cubrir {cobertura['faltante']} {c.moneda} con certificaciones de disponibilidad")
    return pendientes


def ficha(db: Session, ctx: CompanyContext, contrato_id: str) -> dict[str, Any]:
    c = _cargar(db, ctx, contrato_id)
    borrador = c.estado == "BORRADOR"
    cobertura = _cobertura(db, c)
    pendientes = _pendientes(db, c) if borrador else []
    documento = None
    if c.document_id:
        documento = {
            "id": c.document_id,
            "titulo": c.documento_titulo,
            "version": c.documento_version_numero,
            "sha256": c.documento_sha256,
        }
    firmante = None
    if c.estado == "FORMALIZADO":
        firmante = {"cargo": c.firmante_cargo_nombre, "funcionario": c.firmante_funcionario_nombre}
    return {
        "id": c.id,
        "version": c.version,
        "estado": c.estado,
        "estado_etiqueta": ETIQUETA_ESTADO[c.estado],
        "tipo": c.tipo,
        "tipo_etiqueta": ETIQUETA_TIPO_INSTRUMENTO.get(c.tipo) if c.tipo else None,
        "codigo": c.codigo,
        "identificacion": _identificacion(c),
        "expediente": {"id": c.file_id, "numero": c.expediente_numero},
        "decision": {
            "id": c.decision_id,
            "referencia": c.decision_referencia,
            "fecha": c.decision_fecha.isoformat(),
            "acto": c.acto_etiqueta,
            "vigente": _adjudicacion_vigente(db, c),
        },
        "oferta": {"id": c.offer_id, "referencia": c.oferta_referencia},
        "contratista": {
            "nombre": c.contratista_nombre,
            "documento": c.contratista_documento,
            "representante": c.contratista_representante,
        },
        "objeto": c.objeto,
        "descripcion_complementaria": c.descripcion_complementaria,
        "monto": _t(Decimal(c.monto)),
        "moneda": c.moneda,
        "fecha_inicio": c.fecha_inicio.isoformat() if c.fecha_inicio else None,
        "fecha_fin": c.fecha_fin.isoformat() if c.fecha_fin else None,
        "referencia_instrumento": c.referencia_instrumento,
        "documento": documento,
        "cobertura": cobertura,
        "garantias": _garantias(db, c),
        "firmante": firmante,
        "fecha_formalizacion": c.fecha_formalizacion.isoformat() if c.fecha_formalizacion else None,
        "formalizado_en": c.formalizado_en.isoformat() if c.formalizado_en else None,
        "huella": c.huella,
        "opciones": (
            {
                "certificados_elegibles": _certificados_elegibles(db, ctx, c),
                "garantias_elegibles": _garantias_elegibles(db, ctx, c),
                "documentos_elegibles": _documentos_elegibles(db, ctx, c),
                "firmantes": _firmantes(db, ctx, c),
            }
            if borrador
            else None
        ),
        "pendientes": pendientes,
        "puede_formalizar": borrador and not pendientes,
    }


def listar(db: Session, ctx: CompanyContext, estado: str | None, tipo: str | None) -> dict[str, Any]:
    stmt = select(GovernmentContract).where(GovernmentContract.company_id == ctx.company_id)
    if estado is not None:
        stmt = stmt.where(GovernmentContract.estado == estado)
    if tipo is not None:
        stmt = stmt.where(GovernmentContract.tipo == tipo)
    contratos = db.scalars(stmt.order_by(GovernmentContract.created_at.desc())).all()
    items = []
    for c in contratos:
        items.append(
            {
                "id": c.id,
                "identificacion": _identificacion(c),
                "codigo": c.codigo,
                "estado": c.estado,
                "estado_etiqueta": ETIQUETA_ESTADO[c.estado],
                "tipo": c.tipo,
                "tipo_etiqueta": ETIQUETA_TIPO_INSTRUMENTO.get(c.tipo) if c.tipo else None,
                "expediente_numero": c.expediente_numero,
                "decision_referencia": c.decision_referencia,
                "contratista_nombre": c.contratista_nombre,
                "monto": _t(Decimal(c.monto)),
                "moneda": c.moneda,
                "fecha_inicio": c.fecha_inicio,
                "fecha_fin": c.fecha_fin,
            }
        )
    return {"items": items}


def crear(db: Session, ctx: CompanyContext, user: Any, cuerpo: dict[str, Any]) -> dict[str, Any]:
    expediente = _expediente(db, ctx, str(cuerpo.get("expediente_id") or ""), bloquear=True)
    _abierto(expediente)
    d = _decision_vigente(db, str(expediente.id))
    if d is None or d.resultado != "ADJUDICADA" or d.offer_id is None:
        raise ConflictError(
            "GOV_CONTRACT_AWARD_REQUIRED",
            "El expediente no tiene una adjudicación vigente: el contrato u orden solo nace de una decisión ADJUDICADA vigente",
        )
    existente = db.scalar(
        select(GovernmentContract).where(
            GovernmentContract.company_id == ctx.company_id,
            GovernmentContract.decision_id == d.id,
        )
    )
    if existente is not None:
        raise ConflictError(
            "GOV_CONTRACT_ALREADY_EXISTS",
            "Ya existe un contrato u orden para esta adjudicación",
            details={"contrato_id": existente.id},
        )
    oferta = db.scalar(
        select(GovernmentProcurementOffer).where(
            GovernmentProcurementOffer.company_id == ctx.company_id,
            GovernmentProcurementOffer.id == d.offer_id,
        )
    )
    if oferta is None:
        raise ConflictError(
            "GOV_CONTRACT_AWARD_REQUIRED",
            "La oferta adjudicada no existe en este ente",
        )
    fila = _monto_vigente(db, ctx.company_id, oferta)
    if fila is None:
        raise KontrolError(
            "GOV_CONTRACT_OFFER_AMOUNT_REQUIRED",
            "La oferta adjudicada no tiene monto declarado: no puede prepararse el contrato",
            status_code=422,
        )
    acto = db.get(GovernmentAct, d.act_id)
    evaluar_antes_de_actuar(db, ctx, "PROC03_CONTRATO_PREPARAR", ENTIDAD, str(expediente.id))
    c = GovernmentContract(
        company_id=ctx.company_id,
        file_id=expediente.id,
        decision_id=d.id,
        offer_id=oferta.id,
        act_id=d.act_id,
        amount_id=fila.id,
        estado="BORRADOR",
        expediente_numero=expediente.numero,
        objeto=expediente.objeto,
        decision_referencia=f"DEC-{d.numero:02d}",
        decision_fecha=hoy_de_negocio(d.decidida_en),
        acto_etiqueta=f"{acto.tipo} {acto.numero}" if acto else "",
        oferta_referencia=f"R-{oferta.numero:04d}",
        contratista_nombre=oferta.oferente_nombre,
        contratista_documento=oferta.oferente_documento,
        contratista_representante=oferta.representante,
        monto=fila.total_con_tributos,
        moneda=fila.moneda,
        created_by=ctx.user_id,
    )
    db.add(c)
    try:
        with db.begin_nested():
            db.flush()
    except IntegrityError as error:
        if es_violacion_unica(error, "uq_gov_contracts_decision"):
            raise ConflictError("GOV_CONTRACT_ALREADY_EXISTS", "Ya existe un contrato u orden para esta adjudicación") from error
        raise
    _auditar(
        db,
        ctx,
        "GOV_CONTRACT_DRAFT_CREATED",
        str(expediente.id),
        {
            "contrato": _identificacion(c),
            "decision": c.decision_referencia,
            "oferta": c.oferta_referencia,
            "expediente": c.expediente_numero,
        },
    )
    return ficha(db, ctx, str(c.id))


def actualizar(
    db: Session, ctx: CompanyContext, user: Any, contrato_id: str, version: int | None, cuerpo: dict[str, Any]
) -> dict[str, Any]:
    c = _para_escribir(db, ctx, contrato_id, version)
    _exigir_adjudicacion_vigente(db, c)
    campos: list[str] = []
    if "tipo" in cuerpo:
        valor = cuerpo["tipo"]
        if valor is None or valor not in TIPOS_INSTRUMENTO_CONTRATO:
            raise _inv("tipo", "Tipo de instrumento no válido")
        c.tipo = valor
        campos.append("tipo")
    if "fecha_inicio" in cuerpo:
        c.fecha_inicio = cuerpo["fecha_inicio"]
        campos.append("fecha_inicio")
    if "fecha_fin" in cuerpo:
        c.fecha_fin = cuerpo["fecha_fin"]
        campos.append("fecha_fin")
    if c.fecha_inicio and c.fecha_fin and c.fecha_fin < c.fecha_inicio:
        raise _inv("fecha_fin", "La fecha de fin no puede ser anterior a la de inicio")
    if "referencia_instrumento" in cuerpo:
        valor = str(cuerpo["referencia_instrumento"] or "").strip()
        valor = valor or None
        if valor is not None and (len(valor) < 3 or len(valor) > 120):
            raise _inv("referencia_instrumento", "La referencia debe tener entre 3 y 120 caracteres")
        c.referencia_instrumento = valor
        campos.append("referencia_instrumento")
    if "descripcion_complementaria" in cuerpo:
        valor = str(cuerpo["descripcion_complementaria"] or "").strip()
        valor = valor or None
        if valor is not None and len(valor) > 2000:
            raise _inv("descripcion_complementaria", "Máximo 2000 caracteres")
        c.descripcion_complementaria = valor
        campos.append("descripcion_complementaria")
    if "documento_id" in cuerpo:
        valor = cuerpo["documento_id"]
        if not valor:
            c.document_id = None
            c.document_version_id = None
            c.documento_version_numero = None
            c.documento_sha256 = None
            c.documento_titulo = None
        else:
            r = _documento_valido(db, ctx, c, str(valor))
            if r is None:
                raise _inv("documento_id", "El documento no existe en este ente, está sellado o no está vinculado al expediente")
            doc, version_doc, _ = r
            c.document_id = str(doc.id)
            c.document_version_id = str(version_doc.id)
            c.documento_version_numero = version_doc.version_number
            c.documento_sha256 = version_doc.sha256
            c.documento_titulo = doc.title
        campos.append("documento")
    if campos:
        c.version += 1
        db.flush()
        _auditar(
            db,
            ctx,
            "GOV_CONTRACT_DRAFT_UPDATED",
            c.file_id,
            {"contrato": _identificacion(c), "campos": sorted(campos)},
        )
    return ficha(db, ctx, str(c.id))


def actualizar_cobertura(
    db: Session,
    ctx: CompanyContext,
    user: Any,
    contrato_id: str,
    version: int | None,
    asignaciones: list[dict[str, Any]],
) -> dict[str, Any]:
    c = _para_escribir(db, ctx, contrato_id, version)
    _exigir_adjudicacion_vigente(db, c)
    ids = [str(item["certificado_id"]) for item in asignaciones]
    if len(ids) != len(set(ids)):
        raise _inv("asignaciones", "Una certificación aparece más de una vez")
    certs = []
    total = Decimal("0")
    years: set[str] = set()
    for item in asignaciones:
        monto = Decimal(str(item["monto"]))
        if monto <= 0 or monto != monto.quantize(Decimal("0.01")):
            raise _inv("asignaciones", "Cada monto asignado debe ser positivo y con dos decimales como máximo")
        cert = db.get(GovernmentBudgetCertificate, str(item["certificado_id"]))
        motivo = _motivo_certificado(db, ctx, c, cert)
        if motivo:
            raise _inv("asignaciones", motivo, code="GOV_CONTRACT_CERTIFICATE_INVALID")
        assert cert is not None
        saldo = _saldo_libre(db, cert, str(c.id))
        if monto > saldo:
            raise _inv(
                "asignaciones",
                f"La certificación {cert.codigo} solo tiene {_t(saldo)} {cert.moneda} libres",
                code="GOV_CONTRACT_CERTIFICATE_INVALID",
            )
        certs.append((cert, monto))
        years.add(cert.year_id)
        total += monto
    if len(years) > 1:
        raise _inv("asignaciones", "Todas las certificaciones deben ser del mismo ejercicio", code="GOV_CONTRACT_CERTIFICATE_INVALID")
    if total > Decimal(c.monto):
        raise _inv(
            "asignaciones",
            f"La cobertura ({_t(total)} {c.moneda}) supera el monto del contrato ({_t(Decimal(c.monto))} {c.moneda})",
        )
    db.execute(
        delete(GovernmentContractBudgetAllocation).where(
            GovernmentContractBudgetAllocation.contract_id == c.id
        )
    )
    db.flush()
    for cert, monto in certs:
        db.add(
            GovernmentContractBudgetAllocation(
                company_id=ctx.company_id,
                contract_id=c.id,
                certificate_id=cert.id,
                year_id=cert.year_id,
                certificado_codigo=cert.codigo,
                monto=monto,
                moneda=cert.moneda,
                created_by=ctx.user_id,
            )
        )
    c.version += 1
    db.flush()
    _auditar(
        db,
        ctx,
        "GOV_CONTRACT_DRAFT_UPDATED",
        c.file_id,
        {
            "contrato": _identificacion(c),
            "campos": ["cobertura"],
            "certificados": sorted(cert.codigo for cert, _ in certs),
        },
    )
    return ficha(db, ctx, str(c.id))


def actualizar_garantias(
    db: Session,
    ctx: CompanyContext,
    user: Any,
    contrato_id: str,
    version: int | None,
    instrumento_ids: list[str],
) -> dict[str, Any]:
    c = _para_escribir(db, ctx, contrato_id, version)
    _exigir_adjudicacion_vigente(db, c)
    if len(instrumento_ids) != len(set(instrumento_ids)):
        raise _inv("instrumento_ids", "Una garantía aparece más de una vez")
    instrumentos = []
    for instrumento_id in instrumento_ids:
        instrumento = db.scalar(
            select(GovernmentGuaranteeInstrument).where(
                GovernmentGuaranteeInstrument.company_id == ctx.company_id,
                GovernmentGuaranteeInstrument.id == instrumento_id,
                GovernmentGuaranteeInstrument.file_id == c.file_id,
                GovernmentGuaranteeInstrument.offer_id == c.offer_id,
                GovernmentGuaranteeInstrument.estado == "REGISTRADA",
            )
        )
        if instrumento is None:
            raise _inv("instrumento_ids", "La garantía no pertenece a la oferta adjudicada o no está vigente")
        instrumentos.append(instrumento)
    db.execute(
        delete(GovernmentContractGuarantee).where(
            GovernmentContractGuarantee.contract_id == c.id
        )
    )
    db.flush()
    for instrumento in instrumentos:
        db.add(
            GovernmentContractGuarantee(
                company_id=ctx.company_id,
                contract_id=c.id,
                instrument_id=instrumento.id,
                garantia_referencia=f"GAR-{instrumento.numero:02d}",
                created_by=ctx.user_id,
            )
        )
    c.version += 1
    db.flush()
    _auditar(
        db,
        ctx,
        "GOV_CONTRACT_DRAFT_UPDATED",
        c.file_id,
        {
            "contrato": _identificacion(c),
            "campos": ["garantias"],
            "garantias": sorted(f"GAR-{inst.numero:02d}" for inst in instrumentos),
        },
    )
    return ficha(db, ctx, str(c.id))


def formalizar(
    db: Session, ctx: CompanyContext, user: Any, contrato_id: str, version: int | None, cuerpo: dict[str, Any]
) -> dict[str, Any]:
    c = _para_escribir(db, ctx, contrato_id, version)
    expediente = _expediente(db, ctx, c.file_id, bloquear=True)
    _abierto(expediente)
    _exigir_adjudicacion_vigente(db, c)
    oferta = db.get(GovernmentProcurementOffer, c.offer_id)
    fila = _monto_vigente(db, ctx.company_id, oferta) if oferta else None
    if (
        fila is None
        or fila.id != c.amount_id
        or Decimal(fila.total_con_tributos) != Decimal(c.monto)
        or fila.moneda != c.moneda
    ):
        raise ConflictError(
            "GOV_CONTRACT_SOURCE_CHANGED",
            "El monto declarado de la oferta cambió después de preparar el contrato",
        )
    tipo = c.tipo
    fecha_inicio = c.fecha_inicio
    fecha_fin = c.fecha_fin
    faltan: dict[str, list[str]] = {}
    if tipo is None:
        faltan["tipo"] = ["Obligatorio para formalizar"]
    if fecha_inicio is None:
        faltan["fecha_inicio"] = ["Obligatorio para formalizar"]
    if fecha_fin is None:
        faltan["fecha_fin"] = ["Obligatorio para formalizar"]
    if c.referencia_instrumento is None:
        faltan["referencia_instrumento"] = ["Obligatorio para formalizar"]
    if c.document_id is None:
        faltan["documento_id"] = ["Obligatorio para formalizar"]
    if faltan or tipo is None or fecha_inicio is None or fecha_fin is None:
        raise KontrolError(
            "GOV_CONTRACT_INCOMPLETE",
            "Faltan datos para formalizar",
            field_errors=faltan,
            status_code=422,
        )
    r = _documento_valido(db, ctx, c, c.document_id)
    if (
        r is None
        or r[1].id != c.document_version_id
        or r[1].sha256 != c.documento_sha256
        or not verificar_integridad(db, r[1])
    ):
        raise ConflictError(
            "GOV_CONTRACT_DOCUMENT_CHANGED",
            "El instrumento contractual cambió o ya no está disponible: vuelva a adjuntarlo",
        )
    asignaciones = db.scalars(
        select(GovernmentContractBudgetAllocation).where(
            GovernmentContractBudgetAllocation.contract_id == c.id
        )
    ).all()
    total = Decimal("0")
    if asignaciones:
        cert_ids = [asig.certificate_id for asig in asignaciones]
        certs = db.scalars(
            select(GovernmentBudgetCertificate)
            .where(GovernmentBudgetCertificate.id.in_(cert_ids))
            .order_by(GovernmentBudgetCertificate.id)
            .with_for_update()
        ).all()
        certs_map = {str(cert.id): cert for cert in certs}
        for asig in asignaciones:
            cert = certs_map.get(str(asig.certificate_id))
            if cert is None or cert.estado != "VIGENTE":
                codigo = asig.certificado_codigo
                raise ConflictError(
                    "GOV_CONTRACT_CERTIFICATE_NOT_ACTIVE",
                    f"La certificación {codigo} fue anulada: actualice la cobertura",
                )
            motivo = _motivo_certificado(db, ctx, c, cert)
            if motivo:
                raise ConflictError("GOV_CONTRACT_CERTIFICATE_NOT_ACTIVE", motivo)
            saldo = _saldo_libre(db, cert, str(c.id))
            if Decimal(asig.monto) > saldo:
                raise ConflictError(
                    "GOV_CONTRACT_CERTIFICATE_OVERALLOCATED",
                    f"La certificación {cert.codigo} ya no tiene saldo libre suficiente",
                )
            total += Decimal(asig.monto)
    if total != Decimal(c.monto):
        raise ConflictError(
            "GOV_CONTRACT_COVERAGE_INSUFFICIENT",
            f"La cobertura presupuestaria ({_t(total)} {c.moneda}) no es igual al monto del contrato ({_t(Decimal(c.monto))} {c.moneda})",
            details={"cubierto": _t(total), "monto": _t(Decimal(c.monto)), "moneda": c.moneda},
        )
    for vinculo in db.scalars(
        select(GovernmentContractGuarantee).where(GovernmentContractGuarantee.contract_id == c.id)
    ).all():
        instrumento = db.get(GovernmentGuaranteeInstrument, vinculo.instrument_id)
        if instrumento is None or instrumento.estado != "REGISTRADA":
            raise ConflictError(
                "GOV_CONTRACT_GUARANTEE_NOT_ACTIVE",
                f"La garantía {vinculo.garantia_referencia} ya no está vigente: actualice las garantías",
            )
    cargo = db.scalar(
        select(GovernmentPosition).where(
            GovernmentPosition.company_id == ctx.company_id,
            GovernmentPosition.id == str(cuerpo.get("firmante_cargo_id") or ""),
        )
    )
    if cargo is None:
        raise _inv("firmante_cargo_id", "Elija el cargo firmante", code="GOV_CONTRACT_SIGNER_INVALID")
    db.execute(
        select(GovernmentStructure)
        .where(
            GovernmentStructure.id == cargo.structure_id,
            GovernmentStructure.company_id == ctx.company_id,
        )
        .with_for_update()
    )
    hoy = hoy_de_negocio()
    if not _autoridad_valida(db, ctx.company_id, str(cargo.id), hoy, "FIRMAR", "CONTRATACIONES"):
        raise _inv(
            "firmante_cargo_id",
            "El cargo no tiene hoy la competencia Firmar sobre Contrataciones",
            code="GOV_CONTRACT_SIGNER_INVALID",
        )
    exigir_autoridad_funcional(db, ctx, str(cargo.id), "FIRMAR", "CONTRATACIONES")
    limite, control = _control_firmante(db, c, cargo, hoy)
    if not control["permite"]:
        codigo = CODIGOS_FIRMANTE.get(control["estado"], "GOV_CONTRACT_SIGNER_INVALID")
        mensaje = control["mensaje"]
        details = {
            "monto": _t(Decimal(c.monto)),
            "moneda": c.moneda,
            "limite": limite["monto"],
            "moneda_limite": limite["moneda"],
            "cargo": cargo.name,
        }
        record_audit_after_rollback(
            db,
            action="GOV_CONTRACT_SIGNER_BLOCKED",
            entity_type=ENTIDAD,
            entity_id=c.file_id,
            tenant_id=ctx.tenant_id,
            company_id=ctx.company_id,
            user_id=ctx.user_id,
            after={"contrato": _identificacion(c), "firmante_cargo": cargo.name, "causal": codigo},
        )
        raise ConflictError(codigo, mensaje, details=details)
    evaluar_antes_de_actuar(db, ctx, "PROC03_CONTRATO_FORMALIZAR", ENTIDAD, str(c.file_id))
    if db.get_bind().dialect.name == "postgresql":
        db.execute(select(func.pg_advisory_xact_lock(BLOQUEO_CODIGO, func.hashtext(str(ctx.company_id)))))
    prefijo = PREFIJOS_INSTRUMENTO_CONTRATO[tipo]
    anio = hoy.year
    maximo = db.scalar(
        select(func.max(GovernmentContract.numero)).where(
            GovernmentContract.company_id == ctx.company_id,
            GovernmentContract.anio == anio,
            GovernmentContract.tipo == c.tipo,
            GovernmentContract.estado == "FORMALIZADO",
        )
    )
    numero = (maximo or 0) + 1
    codigo = f"{prefijo}-{anio}-{numero:04d}"
    official_id = _funcionario_del_actor(db, ctx)
    funcionario = db.get(GovernmentOfficial, official_id) if official_id else None
    nombre_funcionario = funcionario.nombre if funcionario else None
    cobertura = _cobertura(db, c)
    garantias = _garantias(db, c)
    snapshot = {
        "codigo": codigo,
        "tipo": c.tipo,
        "expediente": {"numero": c.expediente_numero, "objeto": c.objeto},
        "decision": {
            "referencia": c.decision_referencia,
            "fecha": c.decision_fecha.isoformat(),
            "acto": c.acto_etiqueta,
        },
        "oferta": c.oferta_referencia,
        "contratista": {
            "nombre": c.contratista_nombre,
            "documento": c.contratista_documento,
            "representante": c.contratista_representante,
        },
        "descripcion_complementaria": c.descripcion_complementaria,
        "monto": _t(Decimal(c.monto)),
        "moneda": c.moneda,
        "plazo": {
            "inicio": fecha_inicio.isoformat(),
            "fin": fecha_fin.isoformat(),
        },
        "referencia_instrumento": c.referencia_instrumento,
        "documento": {
            "titulo": c.documento_titulo,
            "version": c.documento_version_numero,
            "sha256": c.documento_sha256,
        },
        "cobertura": [
            {
                "certificado": item["codigo"],
                "monto": item["monto"],
                "moneda": item["moneda"],
                "anio": item["anio"],
                "partida": item["partida"],
                "fuente": item["fuente"],
            }
            for item in cobertura["asignaciones"]
        ],
        "garantias": [
            {
                "referencia": item["referencia"],
                "tipo": item["tipo_etiqueta"],
                "emisor": item["emisor"],
                "monto": item["monto"],
                "moneda": item["moneda"],
                "vigente_hasta": item["vigente_hasta"],
            }
            for item in garantias
        ],
        "firmante": {
            "cargo": cargo.name,
            "funcionario": nombre_funcionario,
            "limite": limite["etiqueta"],
        },
        "fecha_formalizacion": hoy.isoformat(),
    }
    huella = hashlib.sha256(
        json.dumps(snapshot, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    c.codigo = codigo
    c.numero = numero
    c.anio = anio
    c.estado = "FORMALIZADO"
    c.firmante_cargo_id = str(cargo.id)
    c.firmante_cargo_nombre = cargo.name
    c.firmante_funcionario_nombre = nombre_funcionario
    c.fecha_formalizacion = hoy
    c.formalizado_en = instante_actual()
    c.formalizado_por = ctx.user_id
    c.snapshot = snapshot
    c.huella = huella
    c.version += 1
    doc, version_doc, link = r
    sellar_documento(
        db,
        document=doc,
        resource_type="GovernmentContract",
        resource_id=str(c.id),
        actor_id=ctx.user_id,
        motivo=f"Instrumento contractual {codigo} formalizado (CNT-01)",
    )
    congelar_vinculo(db, link=link, version_id=str(version_doc.id), actor=user)
    db.flush()
    expediente.version += 1
    _evento(
        db,
        ctx,
        expediente,
        "CONTRATO",
        hoy,
        f"{ETIQUETA_TIPO_INSTRUMENTO[tipo]} {codigo} formalizado",
        detalle=f"{c.contratista_nombre} · {_t(Decimal(c.monto))} {c.moneda} · del {fecha_inicio.isoformat()} al {fecha_fin.isoformat()}",
    )
    _auditar(
        db,
        ctx,
        "GOV_CONTRACT_FORMALIZED",
        str(c.file_id),
        {
            "contrato": codigo,
            "codigo": codigo,
            "tipo": c.tipo,
            "decision": c.decision_referencia,
            "oferta": c.oferta_referencia,
            "firmante_cargo": cargo.name,
            "certificados": [item["codigo"] for item in cobertura["asignaciones"]],
            "garantias": [item["referencia"] for item in garantias],
            "huella": huella,
        },
    )
    return ficha(db, ctx, str(c.id))
