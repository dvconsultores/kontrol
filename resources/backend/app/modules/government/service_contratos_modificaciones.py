"""Modificaciones contractuales versionadas: adendas, prórrogas, modificaciones y variaciones (CNT-02, GOV-CNT-002)."""
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
from app.modules.documents.service import congelar_vinculo, sellar_documento, verificar_integridad
from app.modules.government.models import (
    PREFIJOS_MODIFICACION_CONTRATO,
    TIPOS_MODIFICACION_CONTRATO,
    GovernmentBudgetCertificate,
    GovernmentContract,
    GovernmentContractAmendment,
    GovernmentContractAmendmentAllocation,
    GovernmentContractBudgetAllocation,
    GovernmentOfficial,
    GovernmentPosition,
    GovernmentProcurementFile,
    GovernmentStructure,
)
from app.modules.government.monedas import canonical_currency
from app.modules.government.service_actos import _autoridad_valida
from app.modules.government.service_contratos import (
    CODIGOS_COMPROMISO,
    CODIGOS_FIRMANTE,
    ENTIDAD,
    ETIQUETA_TIPO_INSTRUMENTO,
    _anio_ejercicio,
    _auditar,
    _documento_valido,
    _documentos_elegibles,
    _etiqueta_credito,
    _inv,
    _motivo_certificado,
    _t,
    control_compromisos,
    control_firmante,
    equivalentes_moneda,
    saldo_libre,
)
from app.modules.government.service_decision_limite import competencia_en_vigor
from app.modules.government.service_expedientes import _evento
from app.modules.government.service_identidad import _funcionario_del_actor, exigir_autoridad_funcional
from app.modules.government.service_sod import evaluar_antes_de_actuar
from app.modules.government.situacion_contractual import exigir_vigente_para_modificacion
from app.shared.audit import record_audit_after_rollback
from app.shared.clock import hoy_de_negocio, instante_actual

ETIQUETA_ESTADO = {"BORRADOR": "Borrador", "FORMALIZADA": "Formalizada"}
ETIQUETA_TIPO = {
    "ADENDA": "Adenda",
    "PRORROGA": "Prórroga",
    "MODIFICACION": "Modificación",
    "VARIACION": "Variación",
}
SUJETO = "El monto efectivo nuevo del contrato"


def _contrato(
    db: Session, ctx: CompanyContext, contrato_id: str, *, bloquear: bool
) -> GovernmentContract:
    stmt = select(GovernmentContract).where(
        GovernmentContract.company_id == ctx.company_id,
        GovernmentContract.id == contrato_id,
    )
    if bloquear:
        stmt = stmt.with_for_update()
    contrato = db.scalar(stmt)
    if contrato is None:
        raise NotFoundError("GOV_CONTRACT_NOT_FOUND", "Contrato u orden no encontrado")
    return contrato


def _formalizadas(db: Session, contrato_id: str) -> list[GovernmentContractAmendment]:
    return list(
        db.scalars(
            select(GovernmentContractAmendment)
            .where(
                GovernmentContractAmendment.contract_id == contrato_id,
                GovernmentContractAmendment.estado == "FORMALIZADA",
            )
            .order_by(GovernmentContractAmendment.numero)
        )
    )


def _borrador(db: Session, contrato_id: str) -> GovernmentContractAmendment | None:
    return db.scalar(
        select(GovernmentContractAmendment).where(
            GovernmentContractAmendment.contract_id == contrato_id,
            GovernmentContractAmendment.estado == "BORRADOR",
        )
    )


def _base(
    c: GovernmentContract, formalizadas: list[GovernmentContractAmendment]
) -> dict[str, Any]:
    if formalizadas:
        u = formalizadas[-1]
        assert u.monto_nuevo is not None
        return {
            "monto": Decimal(u.monto_nuevo),
            "fecha_fin": u.fecha_fin_nueva,
            "numero": u.numero,
            "vigente_desde": u.vigente_desde,
            "codigo": u.codigo,
            "id": u.id,
        }
    return {
        "monto": Decimal(c.monto),
        "fecha_fin": c.fecha_fin,
        "numero": 0,
        "vigente_desde": None,
        "codigo": None,
        "id": None,
    }


def _vigente_a(
    c: GovernmentContract,
    formalizadas: list[GovernmentContractAmendment],
    fecha: date,
) -> dict[str, Any]:
    programadas: list[str] = []
    vigente: GovernmentContractAmendment | None = None
    for m in formalizadas:
        if m.vigente_desde is not None and m.vigente_desde > fecha:
            assert m.codigo is not None
            programadas.append(m.codigo)
        else:
            vigente = m
    if vigente is not None:
        assert vigente.monto_nuevo is not None
        assert vigente.fecha_fin_nueva is not None
        return {
            "fecha": fecha.isoformat(),
            "monto": _t(Decimal(vigente.monto_nuevo)),
            "fecha_fin": vigente.fecha_fin_nueva.isoformat(),
            "modificacion_codigo": vigente.codigo,
            "programadas": programadas,
        }
    return {
        "fecha": fecha.isoformat(),
        "monto": _t(Decimal(c.monto)),
        "fecha_fin": c.fecha_fin.isoformat() if c.fecha_fin else None,
        "modificacion_codigo": None,
        "programadas": programadas,
    }


def _identificacion(
    m: GovernmentContractAmendment, c: GovernmentContract
) -> str:
    return m.codigo or f"Borrador · {c.codigo}"


def _cargar(
    db: Session,
    ctx: CompanyContext,
    contrato_id: str,
    mod_id: str,
    *,
    bloquear: bool,
) -> GovernmentContractAmendment:
    stmt = select(GovernmentContractAmendment).where(
        GovernmentContractAmendment.company_id == ctx.company_id,
        GovernmentContractAmendment.contract_id == contrato_id,
        GovernmentContractAmendment.id == mod_id,
    )
    if bloquear:
        stmt = stmt.with_for_update()
    modificacion = db.scalar(stmt)
    if modificacion is None:
        raise NotFoundError(
            "GOV_CONTRACT_AMENDMENT_NOT_FOUND", "Modificación no encontrada"
        )
    return modificacion


def _para_escribir(
    db: Session,
    ctx: CompanyContext,
    contrato_id: str,
    mod_id: str,
    version: int | None,
) -> tuple[GovernmentContract, GovernmentContractAmendment]:
    if version is None:
        raise KontrolError(
            "GOV_CONTRACT_AMENDMENT_IF_MATCH_REQUIRED",
            "Se requiere la versión de la modificación",
            status_code=428,
        )
    c = _contrato(db, ctx, contrato_id, bloquear=True)
    m = _cargar(db, ctx, contrato_id, mod_id, bloquear=True)
    if m.version != version:
        raise ConflictError(
            "GOV_CONTRACT_AMENDMENT_STALE",
            "La modificación fue cambiada por otro usuario",
            details={"version_actual": m.version},
        )
    if m.estado != "BORRADOR":
        raise ConflictError(
            "GOV_CONTRACT_AMENDMENT_ALREADY_FORMALIZED",
            "La modificación ya está formalizada y no admite cambios",
        )
    return c, m


def _monto_nuevo(
    base: dict[str, Any], m: GovernmentContractAmendment
) -> Decimal:
    return Decimal(base["monto"]) + (
        Decimal(m.delta_monto) if m.delta_monto is not None else Decimal("0")
    )


def _existente_valida(db: Session, c: GovernmentContract) -> Decimal:
    contrato = db.scalar(
        select(func.coalesce(func.sum(GovernmentContractBudgetAllocation.monto), 0)).where(
            GovernmentContractBudgetAllocation.contract_id == c.id,
            GovernmentContractBudgetAllocation.certificate_id == GovernmentBudgetCertificate.id,
            GovernmentBudgetCertificate.estado == "VIGENTE",
        )
    )
    modificaciones = db.scalar(
        select(func.coalesce(func.sum(GovernmentContractAmendmentAllocation.monto), 0)).where(
            GovernmentContractAmendmentAllocation.contract_id == c.id,
            GovernmentContractAmendmentAllocation.amendment_id
            == GovernmentContractAmendment.id,
            GovernmentContractAmendment.estado == "FORMALIZADA",
            GovernmentContractAmendmentAllocation.certificate_id
            == GovernmentBudgetCertificate.id,
            GovernmentBudgetCertificate.estado == "VIGENTE",
        )
    )
    return Decimal(contrato or 0) + Decimal(modificaciones or 0)


def _asignaciones(
    db: Session, m: GovernmentContractAmendment
) -> list[GovernmentContractAmendmentAllocation]:
    return list(
        db.scalars(
            select(GovernmentContractAmendmentAllocation)
            .where(GovernmentContractAmendmentAllocation.amendment_id == m.id)
            .order_by(GovernmentContractAmendmentAllocation.certificado_codigo)
        )
    )


def _items_asignacion(
    db: Session,
    asignaciones: list[GovernmentContractAmendmentAllocation],
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for a in asignaciones:
        cert = db.get(GovernmentBudgetCertificate, a.certificate_id)
        partida, fuente = _etiqueta_credito(db, cert) if cert else ("", "")
        items.append(
            {
                "certificado_id": a.certificate_id,
                "codigo": a.certificado_codigo,
                "monto": _t(Decimal(a.monto)),
                "moneda": a.moneda,
                "anio": _anio_ejercicio(db, a.year_id),
                "partida": partida,
                "fuente": fuente,
                "estado": cert.estado if cert else None,
            }
        )
    return items


def _certificados_elegibles(
    db: Session, ctx: CompanyContext, c: GovernmentContract
) -> list[dict[str, Any]]:
    certificados = list(
        db.scalars(
            select(GovernmentBudgetCertificate)
            .where(
                GovernmentBudgetCertificate.company_id == ctx.company_id,
                GovernmentBudgetCertificate.estado == "VIGENTE",
                GovernmentBudgetCertificate.moneda.in_(equivalentes_moneda(c.moneda)),
            )
            .order_by(GovernmentBudgetCertificate.codigo)
        )
    )
    elegibles: list[dict[str, Any]] = []
    for cert in certificados:
        if _motivo_certificado(db, ctx, c, cert) is not None:
            continue
        saldo = saldo_libre(db, cert, c.file_id, None)
        if saldo <= 0:
            continue
        partida, fuente = _etiqueta_credito(db, cert)
        elegibles.append(
            {
                "id": str(cert.id),
                "codigo": cert.codigo,
                "monto": _t(Decimal(cert.monto)),
                "saldo_libre": _t(saldo),
                "moneda": canonical_currency(cert.moneda),
                "anio": _anio_ejercicio(db, cert.year_id),
                "partida": partida,
                "fuente": fuente,
                "concepto": cert.concepto,
            }
        )
    return elegibles


def _firmantes(
    db: Session, ctx: CompanyContext, c: GovernmentContract, monto: Decimal
) -> list[dict[str, Any]]:
    hoy = hoy_de_negocio()
    cargos = list(
        db.scalars(
            select(GovernmentPosition)
            .where(GovernmentPosition.company_id == ctx.company_id)
            .order_by(GovernmentPosition.name)
        )
    )
    firmantes: list[dict[str, Any]] = []
    for cargo in cargos:
        if (
            competencia_en_vigor(
                db, cargo, hoy, "FIRMAR", "CONTRATACIONES"
            )
            is None
        ):
            continue
        limite, control, _ = control_firmante(
            db,
            ctx,
            cargo,
            monto,
            c.moneda,
            hoy,
            bloquear=False,
            sujeto=SUJETO,
        )
        firmantes.append(
            {
                "cargo_id": str(cargo.id),
                "cargo": cargo.name,
                "limite": limite,
                "control": control,
            }
        )
    return firmantes


def _formato_fecha(fecha: date | None) -> str | None:
    if fecha is None:
        return None
    return fecha.strftime("%d/%m/%Y")


def _pendientes(
    db: Session,
    c: GovernmentContract,
    m: GovernmentContractAmendment,
    formalizadas: list[GovernmentContractAmendment],
) -> list[str]:
    hoy = hoy_de_negocio()
    base = _base(c, formalizadas)
    monto_nuevo = _monto_nuevo(base, m)
    moneda = canonical_currency(c.moneda)
    pendientes: list[str] = []

    if base["fecha_fin"] is None or hoy > base["fecha_fin"]:
        fecha_txt = _formato_fecha(base["fecha_fin"])
        pendientes.append(
            f"El plazo vigente del contrato terminó el {fecha_txt}: no admite modificaciones"
        )

    if m.base_numero != len(formalizadas):
        pendientes.append(
            "Otra modificación se formalizó después de crear este borrador: descártelo y cree uno nuevo"
        )

    if m.motivo is None or len(m.motivo) < 10:
        pendientes.append("Indique el motivo (10 a 2000 caracteres)")
    if m.fecha_instrumento is None:
        pendientes.append("Indique la fecha del instrumento")
    if m.vigente_desde is None:
        pendientes.append("Indique desde qué fecha rige")
    if not m.referencia_instrumento:
        pendientes.append("Indique la referencia del instrumento")
    if m.document_id is None:
        pendientes.append("Adjunte el instrumento modificatorio firmado")
    if m.tipo == "PRORROGA" and m.nueva_fecha_fin is None:
        pendientes.append("Una prórroga exige la nueva fecha de fin")

    if (
        m.nueva_fecha_fin is None
        and m.delta_monto is None
        and not (m.condiciones or "").strip()
    ):
        pendientes.append("Declare al menos un cambio: plazo, monto o condiciones")

    if m.fecha_instrumento is not None and m.fecha_instrumento > hoy:
        pendientes.append("La fecha del instrumento no puede ser futura")
    if m.vigente_desde is not None and m.vigente_desde < hoy:
        pendientes.append("La modificación no puede regir antes de hoy")
    if (
        m.fecha_instrumento is not None
        and m.vigente_desde is not None
        and m.vigente_desde < m.fecha_instrumento
    ):
        pendientes.append(
            "La vigencia no puede ser anterior a la fecha del instrumento"
        )
    if base["vigente_desde"] is not None and m.vigente_desde is not None:
        if m.vigente_desde < base["vigente_desde"]:
            fecha_txt = _formato_fecha(base["vigente_desde"])
            pendientes.append(
                f"Debe regir desde el {fecha_txt} o después (vigencia de la modificación anterior)"
            )

    if m.nueva_fecha_fin is not None and base["fecha_fin"] is not None:
        if m.nueva_fecha_fin <= base["fecha_fin"]:
            fecha_txt = _formato_fecha(base["fecha_fin"])
            pendientes.append(
                f"La nueva fecha de fin debe ser posterior a la vigente ({fecha_txt})"
            )

    if monto_nuevo <= 0:
        pendientes.append("El monto efectivo nuevo debe ser mayor que cero")

    existente = _existente_valida(db, c)
    requerida = max(monto_nuevo - existente, Decimal("0"))
    asignado = sum((Decimal(a.monto) for a in _asignaciones(db, m)), Decimal("0"))
    if asignado < requerida:
        pendientes.append(
            f"Falta cubrir {_t(requerida - asignado)} {moneda} con certificaciones de disponibilidad"
        )
    elif asignado > requerida:
        pendientes.append(
            f"La cobertura adicional ({_t(asignado)} {moneda}) supera lo requerido ({_t(requerida)} {moneda})"
        )

    if m.delta_monto is not None and m.delta_monto < 0:
        cc = control_compromisos(
            db, c.company_id, c.file_id, monto_nuevo, c.moneda
        )
        if not cc["permite"]:
            pendientes.append(cc["mensaje"])

    return pendientes


def _nodo(db: Session, m: GovernmentContractAmendment) -> dict[str, Any]:
    plazo = None
    if m.nueva_fecha_fin is not None:
        plazo = {
            "anterior": (
                m.fecha_fin_anterior.isoformat() if m.fecha_fin_anterior else None
            ),
            "nuevo": (
                m.fecha_fin_nueva.isoformat() if m.fecha_fin_nueva else None
            ),
        }
    monto = None
    if m.delta_monto is not None:
        assert m.monto_anterior is not None
        assert m.monto_nuevo is not None
        monto = {
            "anterior": _t(Decimal(m.monto_anterior)),
            "delta": _t(Decimal(m.delta_monto)),
            "nuevo": _t(Decimal(m.monto_nuevo)),
        }
    return {
        "id": str(m.id),
        "codigo": m.codigo,
        "numero": m.numero,
        "tipo": m.tipo,
        "tipo_etiqueta": ETIQUETA_TIPO.get(m.tipo or ""),
        "fecha_instrumento": (
            m.fecha_instrumento.isoformat() if m.fecha_instrumento else None
        ),
        "vigente_desde": m.vigente_desde.isoformat() if m.vigente_desde else None,
        "motivo": m.motivo,
        "plazo": plazo,
        "monto": monto,
        "condiciones": m.condiciones,
        "firmante": {
            "cargo": m.firmante_cargo_nombre,
            "funcionario": m.firmante_funcionario_nombre,
        },
        "documento": {
            "titulo": m.documento_titulo,
            "version": m.documento_version_numero,
            "sha256": m.documento_sha256,
        },
        "huella": m.huella,
        "formalizado_en": m.formalizado_en.isoformat() if m.formalizado_en else None,
        "cobertura_adicional": [
            {
                "codigo": a.certificado_codigo,
                "monto": _t(Decimal(a.monto)),
            }
            for a in _asignaciones(db, m)
        ],
    }


def historia(
    db: Session, ctx: CompanyContext, contrato_id: str, fecha: date | None
) -> dict[str, Any]:
    c = _contrato(db, ctx, contrato_id, bloquear=False)
    formalizadas = _formalizadas(db, str(c.id))
    hoy = hoy_de_negocio()
    d = fecha or hoy
    base = _base(c, formalizadas)
    borrador = _borrador(db, str(c.id))
    puede_crear = (
        c.estado == "FORMALIZADO"
        and borrador is None
        and base["fecha_fin"] is not None
        and hoy <= base["fecha_fin"]
    )
    motivo_no_crear: str | None = None
    if c.estado != "FORMALIZADO":
        motivo_no_crear = "El contrato aún no está formalizado"
    elif borrador is not None:
        motivo_no_crear = "Ya hay un borrador de modificación en curso"
    elif base["fecha_fin"] is None or hoy > base["fecha_fin"]:
        fecha_txt = _formato_fecha(base["fecha_fin"])
        motivo_no_crear = f"El plazo vigente del contrato terminó el {fecha_txt}"
    return {
        "contrato": {
            "id": str(c.id),
            "codigo": c.codigo,
            "identificacion": c.codigo or "Borrador",
            "tipo_etiqueta": ETIQUETA_TIPO_INSTRUMENTO.get(c.tipo or ""),
            "estado": c.estado,
            "contratista_nombre": c.contratista_nombre,
            "objeto": c.objeto,
            "moneda": canonical_currency(c.moneda),
        },
        "original": {
            "monto": _t(Decimal(c.monto)),
            "moneda": canonical_currency(c.moneda),
            "fecha_inicio": c.fecha_inicio.isoformat() if c.fecha_inicio else None,
            "fecha_fin": c.fecha_fin.isoformat() if c.fecha_fin else None,
            "huella": c.huella,
        },
        "vigente": _vigente_a(c, formalizadas, d),
        "ultima": {
            "monto": _t(Decimal(base["monto"])),
            "fecha_fin": (
                base["fecha_fin"].isoformat() if base["fecha_fin"] else None
            ),
            "vigente_desde": (
                base["vigente_desde"].isoformat() if base["vigente_desde"] else None
            ),
            "modificacion_codigo": base["codigo"],
        },
        "historial": [_nodo(db, m) for m in formalizadas],
        "borrador": (
            {
                "id": str(borrador.id),
                "tipo": borrador.tipo,
                "tipo_etiqueta": ETIQUETA_TIPO.get(borrador.tipo or ""),
            }
            if borrador
            else None
        ),
        "puede_crear": puede_crear,
        "motivo_no_crear": motivo_no_crear,
    }


def ficha(
    db: Session, ctx: CompanyContext, contrato_id: str, mod_id: str
) -> dict[str, Any]:
    c = _contrato(db, ctx, contrato_id, bloquear=False)
    m = _cargar(db, ctx, contrato_id, mod_id, bloquear=False)
    formalizadas = _formalizadas(db, str(c.id))
    borrador = m.estado == "BORRADOR"

    if borrador:
        base = _base(c, formalizadas)
        monto_nuevo = _monto_nuevo(base, m)
        fecha_fin_nueva = m.nueva_fecha_fin or base["fecha_fin"]
        existente = _existente_valida(db, c)
        requerida = max(monto_nuevo - existente, Decimal("0"))
        asignaciones = _asignaciones(db, m)
        asignado = sum(
            (Decimal(a.monto) for a in asignaciones), Decimal("0")
        )
        monto_compromiso = monto_nuevo if monto_nuevo > 0 else Decimal(base["monto"])
        cc = control_compromisos(
            db, c.company_id, c.file_id, monto_compromiso, c.moneda
        )
        cc["aplica"] = m.delta_monto is not None and m.delta_monto < 0
        pendientes = _pendientes(db, c, m, formalizadas)
        firmante = None
        opciones = {
            "certificados_elegibles": _certificados_elegibles(db, ctx, c),
            "documentos_elegibles": _documentos_elegibles(db, ctx, c),
            "firmantes": _firmantes(db, ctx, c, monto_compromiso),
        }
        propuesta_monto = _t(monto_nuevo) if monto_nuevo > 0 else None
    else:
        assert m.monto_anterior is not None
        assert m.monto_nuevo is not None
        base = {
            "monto": Decimal(m.monto_anterior),
            "fecha_fin": m.fecha_fin_anterior,
            "numero": (m.numero or 1) - 1,
        }
        monto_nuevo = Decimal(m.monto_nuevo)
        fecha_fin_nueva = m.fecha_fin_nueva
        existente = Decimal(0)
        requerida = Decimal(0)
        asignaciones = _asignaciones(db, m)
        asignado = sum(
            (Decimal(a.monto) for a in asignaciones), Decimal("0")
        )
        snapshot = m.snapshot or {}
        cobertura_snapshot = snapshot.get("cobertura") or {}
        compromisos_snapshot = snapshot.get("compromisos") or {}
        existente_txt = cobertura_snapshot.get("existente_valida")
        requerida_txt = cobertura_snapshot.get("requerida_adicional")
        existente = Decimal(existente_txt or "0")
        requerida = Decimal(requerida_txt or "0")
        cc = {
            "total": compromisos_snapshot.get("total"),
            "moneda": compromisos_snapshot.get("moneda"),
            "aplica": m.delta_monto is not None and m.delta_monto < 0,
            "permite": True,
        }
        pendientes = []
        opciones = None
        firmante_snapshot = snapshot.get("firmante") or {}
        firmante = {
            "cargo": m.firmante_cargo_nombre,
            "funcionario": m.firmante_funcionario_nombre,
            "limite": firmante_snapshot.get("limite"),
            "conversion": firmante_snapshot.get("conversion"),
        }
        propuesta_monto = _t(monto_nuevo)

    return {
        "id": str(m.id),
        "version": m.version,
        "estado": m.estado,
        "estado_etiqueta": ETIQUETA_ESTADO.get(m.estado or ""),
        "tipo": m.tipo,
        "tipo_etiqueta": ETIQUETA_TIPO.get(m.tipo or ""),
        "codigo": m.codigo,
        "identificacion": _identificacion(m, c),
        "contrato": {"id": str(c.id), "codigo": c.codigo},
        "moneda": m.moneda,
        "fecha_instrumento": (
            m.fecha_instrumento.isoformat() if m.fecha_instrumento else None
        ),
        "vigente_desde": m.vigente_desde.isoformat() if m.vigente_desde else None,
        "motivo": m.motivo,
        "nueva_fecha_fin": (
            m.nueva_fecha_fin.isoformat() if m.nueva_fecha_fin else None
        ),
        "delta_monto": _t(Decimal(m.delta_monto)) if m.delta_monto is not None else None,
        "condiciones": m.condiciones,
        "referencia_instrumento": m.referencia_instrumento,
        "documento": (
            {
                "id": m.document_id,
                "titulo": m.documento_titulo,
                "version": m.documento_version_numero,
                "sha256": m.documento_sha256,
            }
            if m.document_id
            else None
        ),
        "base": {
            "monto": _t(Decimal(base["monto"])),
            "fecha_fin": (
                base["fecha_fin"].isoformat() if base["fecha_fin"] else None
            ),
            "numero": base["numero"],
        },
        "propuesta": {
            "monto_nuevo": propuesta_monto,
            "fecha_fin_nueva": (
                fecha_fin_nueva.isoformat() if fecha_fin_nueva else None
            ),
        },
        "cobertura": {
            "existente_valida": _t(existente),
            "requerida_adicional": _t(requerida),
            "asignaciones": _items_asignacion(db, asignaciones),
            "total_asignado": _t(asignado),
            "completa": asignado == requerida,
        },
        "compromisos": cc,
        "firmante": firmante,
        "formalizado_en": m.formalizado_en.isoformat() if m.formalizado_en else None,
        "huella": m.huella,
        "opciones": opciones,
        "pendientes": pendientes,
        "puede_formalizar": borrador and not pendientes,
    }


def crear(
    db: Session,
    ctx: CompanyContext,
    user: Any,
    contrato_id: str,
    cuerpo: dict[str, Any],
) -> dict[str, Any]:
    c = _contrato(db, ctx, contrato_id, bloquear=True)
    if c.estado != "FORMALIZADO":
        raise ConflictError(
            "GOV_CONTRACT_NOT_FORMALIZED",
            "Solo un contrato u orden formalizado admite modificaciones",
        )
    tipo = cuerpo.get("tipo")
    if tipo not in TIPOS_MODIFICACION_CONTRATO:
        raise _inv(
            "tipo",
            "Tipo de modificación no válido",
            code="GOV_CONTRACT_AMENDMENT_INVALID",
        )
    existente = _borrador(db, str(c.id))
    if existente is not None:
        raise ConflictError(
            "GOV_CONTRACT_AMENDMENT_DRAFT_EXISTS",
            "Ya hay un borrador de modificación en curso para este contrato",
            details={"modificacion_id": str(existente.id)},
        )
    formalizadas = _formalizadas(db, str(c.id))
    base = _base(c, formalizadas)
    hoy = hoy_de_negocio()
    if base["fecha_fin"] is None or hoy > base["fecha_fin"]:
        fecha_txt = _formato_fecha(base["fecha_fin"])
        mensaje = (
            f"El plazo vigente del contrato terminó el {fecha_txt}: no admite modificaciones"
        )
        raise ConflictError("GOV_CONTRACT_AMENDMENT_CONTRACT_EXPIRED", mensaje)
    evaluar_antes_de_actuar(
        db, ctx, "PROC03_MODIFICACION_PREPARAR", ENTIDAD, c.file_id
    )
    m = GovernmentContractAmendment(
        company_id=ctx.company_id,
        contract_id=c.id,
        file_id=c.file_id,
        estado="BORRADOR",
        tipo=tipo,
        base_numero=len(formalizadas),
        moneda=canonical_currency(c.moneda),
        created_by=ctx.user_id,
    )
    db.add(m)
    try:
        with db.begin_nested():
            db.flush()
    except IntegrityError as error:
        if es_violacion_unica(error, "uq_gov_contract_amendments_borrador"):
            raise ConflictError(
                "GOV_CONTRACT_AMENDMENT_DRAFT_EXISTS",
                "Ya hay un borrador de modificación en curso para este contrato",
                details={"modificacion_id": None},
            ) from error
        raise
    _auditar(
        db,
        ctx,
        "GOV_CONTRACT_AMENDMENT_DRAFT_CREATED",
        c.file_id,
        {
            "contrato": c.codigo,
            "modificacion": _identificacion(m, c),
            "tipo": tipo,
        },
    )
    return ficha(db, ctx, contrato_id, str(m.id))


def actualizar(
    db: Session,
    ctx: CompanyContext,
    user: Any,
    contrato_id: str,
    mod_id: str,
    version: int | None,
    cuerpo: dict[str, Any],
) -> dict[str, Any]:
    c, m = _para_escribir(db, ctx, contrato_id, mod_id, version)
    campos: set[str] = set()
    for clave, valor in cuerpo.items():
        if clave == "tipo":
            if valor not in TIPOS_MODIFICACION_CONTRATO:
                raise _inv(
                    "tipo",
                    "Tipo de modificación no válido",
                    code="GOV_CONTRACT_AMENDMENT_INVALID",
                )
            m.tipo = valor
            campos.add(clave)
        elif clave in ("fecha_instrumento", "vigente_desde", "nueva_fecha_fin"):
            setattr(m, clave, valor)
            campos.add(clave)
        elif clave == "motivo":
            texto = (valor or "").strip()
            if not texto:
                m.motivo = None
            else:
                if len(texto) < 10 or len(texto) > 2000:
                    raise _inv(
                        "motivo",
                        "El motivo debe tener entre 10 y 2000 caracteres",
                        code="GOV_CONTRACT_AMENDMENT_INVALID",
                    )
                m.motivo = texto
            campos.add(clave)
        elif clave == "delta_monto":
            if valor is None:
                m.delta_monto = None
            else:
                decimal_valor = Decimal(str(valor))
                cuantizado = decimal_valor.quantize(Decimal("0.01"))
                if (
                    decimal_valor == 0
                    or decimal_valor != cuantizado
                    or abs(decimal_valor) >= Decimal("10000000000000000")
                ):
                    raise _inv(
                        "delta_monto",
                        "El cambio de monto debe ser distinto de cero y con dos decimales como máximo",
                        code="GOV_CONTRACT_AMENDMENT_INVALID",
                    )
                m.delta_monto = decimal_valor
            campos.add(clave)
        elif clave == "condiciones":
            texto = (valor or "").strip()
            if not texto:
                m.condiciones = None
            else:
                if len(texto) > 4000:
                    raise _inv(
                        "condiciones",
                        "Máximo 4000 caracteres",
                        code="GOV_CONTRACT_AMENDMENT_INVALID",
                    )
                m.condiciones = texto
            campos.add(clave)
        elif clave == "referencia_instrumento":
            texto = (valor or "").strip()
            if not texto:
                m.referencia_instrumento = None
            else:
                if len(texto) < 3 or len(texto) > 120:
                    raise _inv(
                        "referencia_instrumento",
                        "La referencia debe tener entre 3 y 120 caracteres",
                        code="GOV_CONTRACT_AMENDMENT_INVALID",
                    )
                m.referencia_instrumento = texto
            campos.add(clave)
        elif clave == "documento_id":
            if not valor:
                m.document_id = None
                m.document_version_id = None
                m.documento_version_numero = None
                m.documento_sha256 = None
                m.documento_titulo = None
            else:
                r = _documento_valido(db, ctx, c, valor)
                if r is None:
                    raise _inv(
                        "documento_id",
                        "El documento no existe en este ente, está sellado o no está vinculado al expediente",
                        code="GOV_CONTRACT_AMENDMENT_INVALID",
                    )
                doc, version_doc, _link = r
                m.document_id = str(doc.id)
                m.document_version_id = str(version_doc.id)
                m.documento_version_numero = version_doc.version_number
                m.documento_sha256 = version_doc.sha256
                m.documento_titulo = doc.title
            campos.add("documento")
    if (
        m.fecha_instrumento is not None
        and m.vigente_desde is not None
        and m.vigente_desde < m.fecha_instrumento
    ):
        raise _inv(
            "vigente_desde",
            "La vigencia no puede ser anterior a la fecha del instrumento",
            code="GOV_CONTRACT_AMENDMENT_DATE_INVALID",
        )
    if campos:
        m.version += 1
        db.flush()
        _auditar(
            db,
            ctx,
            "GOV_CONTRACT_AMENDMENT_DRAFT_UPDATED",
            c.file_id,
            {
                "contrato": c.codigo,
                "modificacion": _identificacion(m, c),
                "campos": sorted(campos),
            },
        )
    return ficha(db, ctx, contrato_id, mod_id)


def actualizar_cobertura(
    db: Session,
    ctx: CompanyContext,
    user: Any,
    contrato_id: str,
    mod_id: str,
    version: int | None,
    asignaciones: list[dict[str, Any]],
) -> dict[str, Any]:
    c, m = _para_escribir(db, ctx, contrato_id, mod_id, version)
    formalizadas = _formalizadas(db, str(c.id))
    base = _base(c, formalizadas)
    monto_nuevo = _monto_nuevo(base, m)
    existente = _existente_valida(db, c)
    requerida = max(monto_nuevo - existente, Decimal("0"))
    moneda = canonical_currency(c.moneda)

    codigos_vistos: set[str] = set()
    total = Decimal("0")
    ejercicio: int | None = None
    certificados: list[tuple[str, GovernmentBudgetCertificate, Decimal]] = []
    for item in asignaciones:
        certificado_id = str(item.get("certificado_id") or "")
        monto = Decimal(str(item.get("monto") or "0"))
        if monto <= 0 or monto != monto.quantize(Decimal("0.01")):
            raise _inv(
                "asignaciones",
                "Cada monto asignado debe ser positivo y con dos decimales como máximo",
                code="GOV_CONTRACT_AMENDMENT_INVALID",
            )
        if certificado_id in codigos_vistos:
            raise _inv(
                "asignaciones",
                "Una certificación aparece más de una vez",
                code="GOV_CONTRACT_AMENDMENT_INVALID",
            )
        codigos_vistos.add(certificado_id)
        cert = db.get(GovernmentBudgetCertificate, certificado_id)
        motivo = _motivo_certificado(db, ctx, c, cert)
        if motivo is not None:
            raise _inv(
                "asignaciones",
                motivo,
                code="GOV_CONTRACT_CERTIFICATE_INVALID",
            )
        assert cert is not None
        saldo = saldo_libre(db, cert, c.file_id, None)
        if monto > saldo:
            raise _inv(
                "asignaciones",
                f"La certificación {cert.codigo} solo tiene {_t(saldo)} {canonical_currency(cert.moneda)} libres",
                code="GOV_CONTRACT_CERTIFICATE_INVALID",
            )
        anio = _anio_ejercicio(db, cert.year_id)
        if ejercicio is None:
            ejercicio = anio
        elif anio != ejercicio:
            raise _inv(
                "asignaciones",
                "Todas las certificaciones deben ser del mismo ejercicio",
                code="GOV_CONTRACT_CERTIFICATE_INVALID",
            )
        total += monto
        certificados.append((str(cert.id), cert, monto))

    if total > requerida:
        raise _inv(
            "asignaciones",
            f"La cobertura adicional ({_t(total)} {moneda}) supera lo requerido ({_t(requerida)} {moneda})",
            code="GOV_CONTRACT_AMENDMENT_COVERAGE_EXCEEDS",
        )

    db.execute(
        delete(GovernmentContractAmendmentAllocation).where(
            GovernmentContractAmendmentAllocation.amendment_id == m.id
        )
    )
    db.flush()
    codigos: list[str] = []
    for certificado_id, cert, monto in certificados:
        db.add(
            GovernmentContractAmendmentAllocation(
                company_id=ctx.company_id,
                amendment_id=m.id,
                contract_id=c.id,
                certificate_id=certificado_id,
                year_id=cert.year_id,
                certificado_codigo=cert.codigo,
                monto=monto,
                moneda=canonical_currency(cert.moneda),
                created_by=ctx.user_id,
            )
        )
        codigos.append(cert.codigo)
    m.version += 1
    db.flush()
    _auditar(
        db,
        ctx,
        "GOV_CONTRACT_AMENDMENT_DRAFT_UPDATED",
        c.file_id,
        {
            "contrato": c.codigo,
            "modificacion": _identificacion(m, c),
            "campos": ["cobertura"],
            "certificados": sorted(codigos),
        },
    )
    return ficha(db, ctx, contrato_id, mod_id)


def descartar(
    db: Session,
    ctx: CompanyContext,
    user: Any,
    contrato_id: str,
    mod_id: str,
    version: int | None,
) -> None:
    c, m = _para_escribir(db, ctx, contrato_id, mod_id, version)
    ident = _identificacion(m, c)
    tipo = m.tipo
    db.execute(
        delete(GovernmentContractAmendmentAllocation).where(
            GovernmentContractAmendmentAllocation.amendment_id == m.id
        )
    )
    db.flush()
    db.delete(m)
    db.flush()
    _auditar(
        db,
        ctx,
        "GOV_CONTRACT_AMENDMENT_DRAFT_DISCARDED",
        c.file_id,
        {"contrato": c.codigo, "modificacion": ident, "tipo": tipo},
    )


def formalizar(
    db: Session,
    ctx: CompanyContext,
    user: Any,
    contrato_id: str,
    mod_id: str,
    version: int | None,
    cuerpo: dict[str, Any],
) -> dict[str, Any]:
    c, m = _para_escribir(db, ctx, contrato_id, mod_id, version)

    expediente = db.scalar(
        select(GovernmentProcurementFile)
        .where(
            GovernmentProcurementFile.company_id == ctx.company_id,
            GovernmentProcurementFile.id == c.file_id,
        )
        .with_for_update()
    )
    if expediente is None:
        raise NotFoundError("GOV_PROCUREMENT_FILE_NOT_FOUND", "Expediente no encontrado")

    formalizadas = _formalizadas(db, str(c.id))
    hoy = hoy_de_negocio()
    base = _base(c, formalizadas)
    moneda = canonical_currency(c.moneda)

    if base["fecha_fin"] is None or hoy > base["fecha_fin"]:
        fecha_txt = _formato_fecha(base["fecha_fin"])
        mensaje = (
            f"El plazo vigente del contrato terminó el {fecha_txt}: no admite modificaciones"
        )
        raise ConflictError("GOV_CONTRACT_AMENDMENT_CONTRACT_EXPIRED", mensaje)
    if m.base_numero != len(formalizadas):
        raise ConflictError(
            "GOV_CONTRACT_AMENDMENT_STALE",
            "Otra modificación se formalizó después de crear este borrador: descártelo y cree uno nuevo",
        )

    faltantes: dict[str, list[str]] = {}
    if m.motivo is None or len(m.motivo) < 10:
        faltantes["motivo"] = ["Obligatorio para formalizar"]
    if m.fecha_instrumento is None:
        faltantes["fecha_instrumento"] = ["Obligatorio para formalizar"]
    if m.vigente_desde is None:
        faltantes["vigente_desde"] = ["Obligatorio para formalizar"]
    if not m.referencia_instrumento:
        faltantes["referencia_instrumento"] = ["Obligatorio para formalizar"]
    if m.document_id is None:
        faltantes["documento_id"] = ["Obligatorio para formalizar"]
    if m.tipo == "PRORROGA" and m.nueva_fecha_fin is None:
        faltantes["nueva_fecha_fin"] = ["Obligatorio para formalizar"]
    if faltantes:
        raise KontrolError(
            "GOV_CONTRACT_AMENDMENT_INCOMPLETE",
            "Faltan datos para formalizar",
            status_code=422,
            field_errors=faltantes,
        )

    if (
        m.nueva_fecha_fin is None
        and m.delta_monto is None
        and not (m.condiciones or "").strip()
    ):
        raise KontrolError(
            "GOV_CONTRACT_AMENDMENT_NO_CHANGE",
            "Declare al menos un cambio: plazo, monto o condiciones",
            status_code=422,
        )

    fecha_instrumento = m.fecha_instrumento
    vigente_desde = m.vigente_desde
    assert fecha_instrumento is not None
    assert vigente_desde is not None
    exigir_vigente_para_modificacion(db, ctx.company_id, str(c.id), vigente_desde)

    errores_fechas: dict[str, list[str]] = {}
    if fecha_instrumento > hoy:
        errores_fechas["fecha_instrumento"] = [
            "La fecha del instrumento no puede ser futura"
        ]
    if vigente_desde < hoy:
        errores_fechas["vigente_desde"] = [
            "La modificación no puede regir antes de hoy"
        ]
    if vigente_desde < fecha_instrumento:
        errores_fechas["vigente_desde"] = [
            "La vigencia no puede ser anterior a la fecha del instrumento"
        ]
    if base["vigente_desde"] is not None and vigente_desde < base["vigente_desde"]:
        fecha_txt = _formato_fecha(base["vigente_desde"])
        errores_fechas["vigente_desde"] = [
            f"Debe regir desde el {fecha_txt} o después (vigencia de la modificación anterior)"
        ]
    if errores_fechas:
        raise KontrolError(
            "GOV_CONTRACT_AMENDMENT_DATE_INVALID",
            "Fechas de la modificación no válidas",
            status_code=422,
            field_errors=errores_fechas,
        )

    if m.nueva_fecha_fin is not None and base["fecha_fin"] is not None:
        if m.nueva_fecha_fin <= base["fecha_fin"]:
            fecha_txt = _formato_fecha(base["fecha_fin"])
            raise KontrolError(
                "GOV_CONTRACT_AMENDMENT_TERM_INVALID",
                f"La nueva fecha de fin debe ser posterior a la vigente ({fecha_txt})",
                status_code=422,
                field_errors={"nueva_fecha_fin": [
                    f"La nueva fecha de fin debe ser posterior a la vigente ({fecha_txt})"
                ]},
            )

    monto_nuevo = _monto_nuevo(base, m)
    if monto_nuevo <= 0:
        raise KontrolError(
            "GOV_CONTRACT_AMENDMENT_AMOUNT_INVALID",
            "El monto efectivo nuevo debe ser mayor que cero",
            status_code=422,
            field_errors={"delta_monto": ["El monto efectivo nuevo debe ser mayor que cero"]},
        )

    r = _documento_valido(db, ctx, c, m.document_id)
    if (
        r is None
        or str(r[1].id) != m.document_version_id
        or r[1].sha256 != m.documento_sha256
        or not verificar_integridad(db, r[1])
    ):
        raise ConflictError(
            "GOV_CONTRACT_AMENDMENT_DOCUMENT_CHANGED",
            "El instrumento modificatorio cambió o ya no está disponible: vuelva a adjuntarlo",
        )

    asignaciones = _asignaciones(db, m)
    if asignaciones:
        ids = [a.certificate_id for a in asignaciones]
        certificados = list(
            db.scalars(
                select(GovernmentBudgetCertificate)
                .where(GovernmentBudgetCertificate.id.in_(ids))
                .order_by(GovernmentBudgetCertificate.id)
                .with_for_update()
            )
        )
        certificado_por_id = {str(cert.id): cert for cert in certificados}
        for a in asignaciones:
            cert = certificado_por_id.get(str(a.certificate_id))
            if cert is None or cert.estado != "VIGENTE":
                raise ConflictError(
                    "GOV_CONTRACT_CERTIFICATE_NOT_ACTIVE",
                    f"La certificación {a.certificado_codigo} fue anulada: actualice la cobertura",
                )
            motivo = _motivo_certificado(db, ctx, c, cert)
            if motivo is not None:
                raise ConflictError(
                    "GOV_CONTRACT_CERTIFICATE_NOT_ACTIVE", motivo
                )
            saldo = saldo_libre(db, cert, c.file_id, None)
            if Decimal(a.monto) > saldo:
                raise ConflictError(
                    "GOV_CONTRACT_CERTIFICATE_OVERALLOCATED",
                    f"La certificación {cert.codigo} ya no tiene saldo libre suficiente",
                )

    existente = _existente_valida(db, c)
    requerida = max(monto_nuevo - existente, Decimal("0"))
    asignado = sum((Decimal(a.monto) for a in asignaciones), Decimal("0"))
    if asignado < requerida:
        mensaje = (
            f"Falta cubrir {_t(requerida - asignado)} {moneda} con certificaciones de disponibilidad"
        )
        raise ConflictError(
            "GOV_CONTRACT_AMENDMENT_COVERAGE_INSUFFICIENT",
            mensaje,
            details={
                "cubierto": _t(existente + asignado),
                "requerido": _t(monto_nuevo),
                "adicional_requerida": _t(requerida),
                "adicional_asignada": _t(asignado),
                "moneda": moneda,
            },
        )
    if asignado > requerida:
        mensaje = (
            f"La cobertura adicional ({_t(asignado)} {moneda}) supera lo requerido ({_t(requerida)} {moneda})"
        )
        raise ConflictError(
            "GOV_CONTRACT_AMENDMENT_COVERAGE_INSUFFICIENT",
            mensaje,
            details={
                "cubierto": _t(existente + asignado),
                "requerido": _t(monto_nuevo),
                "adicional_requerida": _t(requerida),
                "adicional_asignada": _t(asignado),
                "moneda": moneda,
            },
        )

    if m.delta_monto is not None and m.delta_monto < 0:
        cc = control_compromisos(
            db, c.company_id, c.file_id, monto_nuevo, c.moneda
        )
        if not cc["permite"]:
            raise ConflictError(
                CODIGOS_COMPROMISO[cc["estado"]],
                cc["mensaje"],
                details={
                    "comprometido": cc["total"],
                    "monto": _t(monto_nuevo),
                    "moneda": cc["moneda"],
                },
            )

    cargo_id = str(cuerpo.get("firmante_cargo_id") or "")
    cargo = db.scalar(
        select(GovernmentPosition).where(
            GovernmentPosition.company_id == ctx.company_id,
            GovernmentPosition.id == cargo_id,
        )
    )
    if cargo is None:
        raise _inv(
            "firmante_cargo_id",
            "Elija el cargo firmante",
            code="GOV_CONTRACT_SIGNER_INVALID",
        )
    db.execute(
        select(GovernmentStructure)
        .where(
            GovernmentStructure.id == cargo.structure_id,
            GovernmentStructure.company_id == ctx.company_id,
        )
        .with_for_update()
    )
    if not _autoridad_valida(
        db, ctx.company_id, str(cargo.id), hoy, "FIRMAR", "CONTRATACIONES"
    ):
        raise _inv(
            "firmante_cargo_id",
            "El cargo no tiene hoy la competencia Firmar sobre Contrataciones",
            code="GOV_CONTRACT_SIGNER_INVALID",
        )
    exigir_autoridad_funcional(db, ctx, str(cargo.id), "FIRMAR", "CONTRATACIONES")

    limite, control, conversion = control_firmante(
        db,
        ctx,
        cargo,
        monto_nuevo,
        c.moneda,
        hoy,
        bloquear=True,
        sujeto=SUJETO,
    )
    if not control["permite"]:
        estado = control["estado"]
        codigo = (
            "GOV_OFFICIAL_RATE_REQUIRED"
            if estado == "SIN_TASA"
            else CODIGOS_FIRMANTE.get(estado, "GOV_CONTRACT_SIGNER_INVALID")
        )
        record_audit_after_rollback(
            db,
            action="GOV_CONTRACT_AMENDMENT_SIGNER_BLOCKED",
            entity_type=ENTIDAD,
            entity_id=c.file_id,
            tenant_id=ctx.tenant_id,
            company_id=ctx.company_id,
            user_id=ctx.user_id,
            after={
                "contrato": c.codigo,
                "modificacion": _identificacion(m, c),
                "firmante_cargo": cargo.name,
                "causal": codigo,
            },
        )
        details = {
            "monto": _t(monto_nuevo),
            "moneda": moneda,
            "limite": limite["monto"],
            "moneda_limite": limite["moneda"],
            "cargo": cargo.name,
        }
        if estado == "SIN_TASA":
            raise KontrolError(
                code="GOV_OFFICIAL_RATE_REQUIRED",
                message=control["mensaje"],
                status_code=422,
                details={
                    **details,
                    "moneda_operacion": moneda,
                    "moneda_limite": canonical_currency(limite["moneda"]),
                    "fecha": hoy.isoformat(),
                    "monedas_sin_tasa": control["monedas_sin_tasa"],
                },
                field_errors={"firmante_cargo_id": [control["mensaje"]]},
            )
        raise ConflictError(
            codigo,
            control["mensaje"],
            details={**details, "conversion": conversion},
        )

    evaluar_antes_de_actuar(
        db, ctx, "PROC03_MODIFICACION_FORMALIZAR", ENTIDAD, c.file_id
    )

    numero = len(formalizadas) + 1
    codigo = f"{c.codigo}/{PREFIJOS_MODIFICACION_CONTRATO[m.tipo]}-{numero:03d}"
    previa = formalizadas[-1] if formalizadas else None

    official_id = _funcionario_del_actor(db, ctx)
    funcionario = db.get(GovernmentOfficial, official_id) if official_id else None
    nombre_funcionario = funcionario.nombre if funcionario else None

    cc = control_compromisos(
        db, c.company_id, c.file_id, monto_nuevo, c.moneda
    )
    items = _items_asignacion(db, asignaciones)
    fecha_fin_nueva = m.nueva_fecha_fin or base["fecha_fin"]
    delta = _t(Decimal(m.delta_monto)) if m.delta_monto is not None else None
    snapshot = {
        "codigo": codigo,
        "tipo": m.tipo,
        "numero": numero,
        "contrato": {"codigo": c.codigo, "huella": c.huella},
        "anterior": previa.codigo if previa else None,
        "motivo": m.motivo,
        "fecha_instrumento": fecha_instrumento.isoformat(),
        "vigente_desde": vigente_desde.isoformat(),
        "plazo": {
            "anterior": (
                base["fecha_fin"].isoformat() if base["fecha_fin"] else None
            ),
            "nuevo": (
                fecha_fin_nueva.isoformat() if fecha_fin_nueva else None
            ),
            "cambia": m.nueva_fecha_fin is not None,
        },
        "monto": {
            "anterior": _t(Decimal(base["monto"])),
            "delta": delta,
            "nuevo": _t(monto_nuevo),
            "moneda": moneda,
        },
        "condiciones": m.condiciones,
        "referencia_instrumento": m.referencia_instrumento,
        "documento": {
            "titulo": m.documento_titulo,
            "version": m.documento_version_numero,
            "sha256": m.documento_sha256,
        },
        "cobertura": {
            "existente_valida": _t(existente),
            "requerida_adicional": _t(requerida),
            "adicional": [
                {
                    "certificado": i["codigo"],
                    "monto": i["monto"],
                    "moneda": i["moneda"],
                    "anio": i["anio"],
                    "partida": i["partida"],
                    "fuente": i["fuente"],
                }
                for i in items
            ],
        },
        "compromisos": {"total": cc["total"], "moneda": cc["moneda"]},
        "firmante": {
            "cargo": cargo.name,
            "funcionario": nombre_funcionario,
            "limite": limite["etiqueta"],
            "conversion": conversion,
        },
        "fecha_formalizacion": hoy.isoformat(),
    }
    huella = hashlib.sha256(
        json.dumps(
            snapshot, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()

    m.estado = "FORMALIZADA"
    m.numero = numero
    m.codigo = codigo
    m.previous_amendment_id = str(previa.id) if previa else None
    m.monto_anterior = Decimal(base["monto"])
    m.monto_nuevo = monto_nuevo
    m.fecha_fin_anterior = base["fecha_fin"]
    m.fecha_fin_nueva = fecha_fin_nueva
    m.firmante_cargo_id = str(cargo.id)
    m.firmante_cargo_nombre = cargo.name
    m.firmante_funcionario_nombre = nombre_funcionario
    m.fecha_formalizacion = hoy
    m.formalizado_en = instante_actual()
    m.formalizado_por = ctx.user_id
    m.snapshot = snapshot
    m.huella = huella
    m.version += 1

    doc, version_doc, link = r
    sellar_documento(
        db,
        document=doc,
        resource_type="GovernmentContractAmendment",
        resource_id=str(m.id),
        actor_id=ctx.user_id,
        motivo=f"Instrumento modificatorio {codigo} formalizado (CNT-02)",
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
        f"{ETIQUETA_TIPO[m.tipo]} {codigo} formalizada",
        detalle=(
            f"Vigente desde {vigente_desde.isoformat()} · plazo hasta "
            f"{fecha_fin_nueva.isoformat() if fecha_fin_nueva else '-'} · "
            f"monto {_t(monto_nuevo)} {moneda}"
        ),
    )
    _auditar(
        db,
        ctx,
        "GOV_CONTRACT_AMENDMENT_FORMALIZED",
        c.file_id,
        {
            "contrato": c.codigo,
            "modificacion": codigo,
            "codigo": codigo,
            "tipo": m.tipo,
            "firmante_cargo": cargo.name,
            "certificados": [i["codigo"] for i in items],
            "huella": huella,
        },
    )
    return ficha(db, ctx, contrato_id, mod_id)
