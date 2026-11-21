"""Servicio de comprobantes de retención (TRE05-T006)."""

from __future__ import annotations

import hashlib
import io
import json
import re
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext
from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.government.models import (
    GovernmentPayment,
    GovernmentWithholdingCatalogItem,
    GovernmentWithholdingHistory,
    GovernmentWithholdingReceipt,
    GovernmentWithholdingSettings,
    GovernmentWithholdingSettlement,
    GovernmentWithholdingSettlementLine,
)
from app.modules.government.service_presupuesto_causado import _username
from app.modules.government.service_tesoreria_pago import _detalle_cuenta
from app.modules.government.service_tesoreria_retencion_politicas import (
    auditar,
    configuracion_actual,
    formatear_codigo,
    registrar_historia,
)
from app.modules.organization.models import Company
from app.shared.clock import hoy_de_negocio, instante_actual


def _liquidacion_de_empresa(
    db: Session, ctx: CompanyContext, settlement_id: str
) -> GovernmentWithholdingSettlement:
    liquidacion = db.execute(
        select(GovernmentWithholdingSettlement).where(
            GovernmentWithholdingSettlement.company_id == ctx.company_id,
            GovernmentWithholdingSettlement.id == settlement_id,
        )
    ).scalar_one_or_none()
    if liquidacion is None:
        raise NotFoundError(
            "GOV_WITHHOLDING_SETTLEMENT_NOT_FOUND",
            "La liquidación de retención no existe o no pertenece a la empresa.",
        )
    return liquidacion


def _pago_de_liquidacion(
    db: Session, ctx: CompanyContext, liquidacion: GovernmentWithholdingSettlement
) -> GovernmentPayment:
    pago = db.execute(
        select(GovernmentPayment).where(
            GovernmentPayment.company_id == ctx.company_id,
            GovernmentPayment.id == liquidacion.payment_id,
        )
    ).scalar_one_or_none()
    if pago is None:
        raise NotFoundError(
            "GOV_PAYMENT_NOT_FOUND",
            "El pago asociado a la liquidación no existe o no pertenece a la empresa.",
        )
    return pago


def _lineas_de_liquidacion(
    db: Session,
    ctx: CompanyContext,
    liquidacion: GovernmentWithholdingSettlement,
) -> list[GovernmentWithholdingSettlementLine]:
    return list(
        db.execute(
            select(GovernmentWithholdingSettlementLine)
            .where(
                GovernmentWithholdingSettlementLine.company_id == ctx.company_id,
                GovernmentWithholdingSettlementLine.settlement_id
                == str(liquidacion.id),
            )
            .order_by(GovernmentWithholdingSettlementLine.orden)
        ).scalars()
    )


def _siguiente_numero(
    db: Session, ctx: CompanyContext, anio: int, serie: str | None
) -> tuple[int, str]:
    configuracion_actual(db, ctx)
    settings = db.execute(
        select(GovernmentWithholdingSettings)
        .where(GovernmentWithholdingSettings.company_id == ctx.company_id)
        .with_for_update()
    ).scalar_one()
    patron = settings.patron
    inicio = datetime(anio, 1, 1, tzinfo=UTC)
    fin = datetime(anio + 1, 1, 1, tzinfo=UTC)
    if "{ANIO}" in patron:
        max_numero = db.execute(
            select(GovernmentWithholdingReceipt.numero)
            .where(
                GovernmentWithholdingReceipt.company_id == ctx.company_id,
                GovernmentWithholdingReceipt.emitido_en >= inicio,
                GovernmentWithholdingReceipt.emitido_en < fin,
            )
            .order_by(GovernmentWithholdingReceipt.numero.desc())
            .limit(1)
        ).scalar()
    else:
        max_numero = db.execute(
            select(GovernmentWithholdingReceipt.numero)
            .where(GovernmentWithholdingReceipt.company_id == ctx.company_id)
            .order_by(GovernmentWithholdingReceipt.numero.desc())
            .limit(1)
        ).scalar()
    numero = (max_numero or 0) + 1
    codigo = formatear_codigo(patron, anio, numero, serie or "")
    return numero, codigo


def _serie_a_string(valor: Any) -> str | None:
    return str(valor) if valor is not None else None


def _instantanea(
    db: Session,
    ctx: CompanyContext,
    liquidacion: GovernmentWithholdingSettlement,
    pago: GovernmentPayment,
    concepto: GovernmentWithholdingCatalogItem,
    lineas: list[GovernmentWithholdingSettlementLine],
    numero: int,
    serie: str | None,
    codigo: str,
    beneficiario: dict[str, Any],
    sustituye_a: str | None,
) -> dict[str, Any]:
    company = db.execute(
        select(Company).where(Company.id == ctx.company_id)
    ).scalar_one()
    cuenta = _detalle_cuenta(db, ctx, str(pago.account_id)) if pago.account_id else {}
    total = sum((linea.monto_aprobado for linea in lineas), 0)
    politica = liquidacion.policy_snapshot or {}
    return {
        "tipo": {
            "clase": concepto.clase,
            "concepto_codigo": concepto.codigo,
            "concepto_nombre": concepto.nombre,
        },
        "numero": numero,
        "serie": serie,
        "codigo": codigo,
        "fecha_emision": instante_actual().isoformat(),
        "emisor": {"nombre": company.legal_name, "rif": company.rif},
        "beneficiario": {
            "nombre": beneficiario["nombre"],
            "identificacion_fiscal": beneficiario["identificacion_fiscal"],
            "tipo_persona": beneficiario["tipo_persona"],
            "condiciones": beneficiario["condiciones"],
            "declarado": True,
        },
        "pago": {
            "codigo": pago.codigo,
            "fecha_pago": pago.fecha_pago.isoformat() if pago.fecha_pago else None,
            "fecha_valor": pago.fecha_valor.isoformat() if pago.fecha_valor else None,
            "moneda": pago.moneda,
            "bruto": f"{liquidacion.bruto:.2f}",
            "referencia_externa": pago.referencia_externa,
            "cuenta": cuenta,
        },
        "lineas": [
            {
                "concepto_codigo": linea.concepto_codigo,
                "concepto_nombre": linea.concepto_nombre,
                "base": f"{linea.base:.2f}",
                "tasa": f"{linea.tasa:.4f}",
                "umbral": f"{linea.umbral:.2f}" if linea.umbral is not None else None,
                "tasa_referencia": f"{linea.tasa_referencia:.4f}"
                if linea.tasa_referencia is not None
                else None,
                "monto": f"{linea.monto_aprobado:.2f}",
            }
            for linea in lineas
        ],
        "total": f"{total:.2f}",
        "moneda": liquidacion.moneda,
        "politica": {
            "codigo": politica.get("codigo"),
            "numero_version": politica.get("numero_version"),
            "tipo_regla": politica.get("tipo_regla"),
            "estado_verificacion": politica.get("estado_verificacion"),
            "fuente_descripcion": politica.get("fuente_descripcion"),
            "fuente_referencia": politica.get("fuente_referencia"),
        },
        "liquidacion": {"id": str(liquidacion.id), "huella": liquidacion.huella},
        "sustituye_a": sustituye_a,
        "leyenda": "Comprobante emitido según la configuración de retenciones adoptada por el ente. Verificación normativa pendiente.",
    }


def emitir_comprobantes(
    db: Session, ctx: CompanyContext, liquidacion: GovernmentWithholdingSettlement
) -> list[GovernmentWithholdingReceipt]:
    lineas = _lineas_de_liquidacion(db, ctx, liquidacion)
    pago = _pago_de_liquidacion(db, ctx, liquidacion)
    lineas_aplicables = [
        linea
        for linea in lineas
        if linea.aplica and linea.exige_comprobante
    ]
    grupos: dict[str, list[GovernmentWithholdingSettlementLine]] = {}
    for linea in lineas_aplicables:
        grupos.setdefault(str(linea.concept_id), []).append(linea)
    for grupo in grupos.values():
        grupo.sort(key=lambda linea: linea.orden)
    emitidos: list[GovernmentWithholdingReceipt] = []
    anio = hoy_de_negocio().year
    for concept_id, lineas_grupo in grupos.items():
        concepto = db.get(GovernmentWithholdingCatalogItem, concept_id)
        if (
            concepto is None
            or concepto.company_id != ctx.company_id
        ):
            raise NotFoundError(
                "GOV_WITHHOLDING_CATALOG_NOT_FOUND",
                "El concepto de retención no existe o no pertenece a la empresa.",
            )
        numero, codigo = _siguiente_numero(
            db, ctx, anio, _serie_a_string(concepto.serie_comprobante)
        )
        beneficiario = liquidacion.beneficiario or {}
        snapshot = _instantanea(
            db,
            ctx,
            liquidacion,
            pago,
            concepto,
            lineas_grupo,
            numero,
            _serie_a_string(concepto.serie_comprobante),
            codigo,
            beneficiario,
            None,
        )
        huella = hashlib.sha256(
            json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        comprobante = GovernmentWithholdingReceipt(
            company_id=ctx.company_id,
            settlement_id=liquidacion.id,
            payment_id=liquidacion.payment_id,
            concept_id=concepto.id,
            numero=numero,
            serie=_serie_a_string(concepto.serie_comprobante),
            codigo=codigo,
            estado="EMITIDO",
            snapshot=snapshot,
            huella=huella,
            emitido_por=ctx.user_id,
            emitido_en=instante_actual(),
        )
        db.add(comprobante)
        db.flush()
        registrar_historia(
            db,
            ctx,
            "COMPROBANTE",
            str(comprobante.id),
            "EMITIDO",
            snapshot,
        )
        auditar(
            db,
            ctx,
            "GOV_WITHHOLDING_RECEIPT_ISSUED",
            "GovernmentWithholdingReceipt",
            str(comprobante.id),
            {
                "codigo": codigo,
                "pago": pago.codigo,
                "concepto": concepto.codigo,
                "monto": snapshot["total"],
            },
        )
        emitidos.append(comprobante)
    return emitidos


def comprobante_a_dict(
    db: Session, ctx: CompanyContext, c: GovernmentWithholdingReceipt
) -> dict[str, Any]:
    snapshot = c.snapshot or {}
    tipo = snapshot.get("tipo") or {}
    beneficiario = snapshot.get("beneficiario") or {}
    pago = snapshot.get("pago") or {}
    sustituido = db.execute(
        select(GovernmentWithholdingReceipt).where(
            GovernmentWithholdingReceipt.company_id == ctx.company_id,
            GovernmentWithholdingReceipt.sustituye_a_id == c.id,
        )
    ).scalar_one_or_none()
    return {
        "id": str(c.id),
        "codigo": c.codigo,
        "numero": c.numero,
        "serie": c.serie,
        "estado": c.estado,
        "settlement_id": str(c.settlement_id),
        "payment_id": str(c.payment_id),
        "pago_codigo": pago.get("codigo"),
        "concepto_codigo": tipo.get("concepto_codigo"),
        "concepto_nombre": tipo.get("concepto_nombre"),
        "clase": tipo.get("clase"),
        "beneficiario_nombre": beneficiario.get("nombre"),
        "identificacion_fiscal": beneficiario.get("identificacion_fiscal"),
        "monto": snapshot.get("total"),
        "moneda": snapshot.get("moneda"),
        "fecha_emision": snapshot.get("fecha_emision"),
        "emitido_por": _username(db, c.emitido_por) if c.emitido_por else None,
        "emitido_en": c.emitido_en.isoformat() if c.emitido_en else None,
        "anulado_por": _username(db, c.anulado_por) if c.anulado_por else None,
        "anulado_en": c.anulado_en.isoformat() if c.anulado_en else None,
        "motivo_anulacion": c.motivo_anulacion,
        "sustituye_a_id": str(c.sustituye_a_id) if c.sustituye_a_id else None,
        "sustituido_por_id": str(sustituido.id) if sustituido else None,
        "huella": c.huella,
        "snapshot": c.snapshot,
    }


def comprobante_de_empresa(
    db: Session, ctx: CompanyContext, id: str, bloquear: bool = False
) -> GovernmentWithholdingReceipt:
    query = select(GovernmentWithholdingReceipt).where(
        GovernmentWithholdingReceipt.company_id == ctx.company_id,
        GovernmentWithholdingReceipt.id == id,
    )
    if bloquear:
        query = query.with_for_update()
    comprobante = db.execute(query).scalar_one_or_none()
    if comprobante is None:
        raise NotFoundError(
            "GOV_WITHHOLDING_RECEIPT_NOT_FOUND",
            "Comprobante de retención no encontrado.",
        )
    return comprobante


def listar_comprobantes(
    db: Session,
    ctx: CompanyContext,
    estado: str | None,
    desde: date | None,
    hasta: date | None,
    payment_id: str | None,
) -> list[dict[str, Any]]:
    query = (
        select(GovernmentWithholdingReceipt)
        .where(GovernmentWithholdingReceipt.company_id == ctx.company_id)
        .order_by(GovernmentWithholdingReceipt.emitido_en.desc())
    )
    if estado:
        query = query.where(GovernmentWithholdingReceipt.estado == estado)
    if desde:
        inicio = datetime.combine(desde, time.min, tzinfo=UTC)
        query = query.where(GovernmentWithholdingReceipt.emitido_en >= inicio)
    if hasta:
        fin = datetime.combine(hasta + timedelta(days=1), time.min, tzinfo=UTC)
        query = query.where(GovernmentWithholdingReceipt.emitido_en < fin)
    if payment_id:
        query = query.where(GovernmentWithholdingReceipt.payment_id == payment_id)
    comprobantes = db.execute(query).scalars().all()
    resultado = []
    for c in comprobantes:
        dato = comprobante_a_dict(db, ctx, c)
        dato.pop("snapshot", None)
        resultado.append(dato)
    return resultado


def obtener_comprobante(
    db: Session, ctx: CompanyContext, id: str
) -> dict[str, Any]:
    return comprobante_a_dict(db, ctx, comprobante_de_empresa(db, ctx, id))


def historia_comprobante(
    db: Session, ctx: CompanyContext, id: str
) -> list[dict[str, Any]]:
    comprobante_de_empresa(db, ctx, id)
    registros = db.execute(
        select(GovernmentWithholdingHistory)
        .where(
            GovernmentWithholdingHistory.company_id == ctx.company_id,
            GovernmentWithholdingHistory.recurso == "COMPROBANTE",
            GovernmentWithholdingHistory.recurso_id == id,
        )
        .order_by(GovernmentWithholdingHistory.created_at)
    ).scalars()
    return [
        {
            "id": str(registro.id),
            "evento": registro.evento,
            "actor_id": str(registro.actor_id) if registro.actor_id else None,
            "created_at": registro.created_at.isoformat()
            if registro.created_at
            else None,
            "instantanea": registro.instantanea,
        }
        for registro in registros
    ]


def pdf_comprobante(db: Session, ctx: CompanyContext, id: str) -> tuple[bytes, str]:
    c = comprobante_de_empresa(db, ctx, id)
    snapshot = c.snapshot or {}
    huella = hashlib.sha256(
        json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    if huella != c.huella:
        raise KontrolError(
            code="GOV_WITHHOLDING_RECEIPT_INTEGRITY",
            message="La huella del comprobante no coincide con la instantánea.",
            status_code=500,
        )
    buffer = io.BytesIO()
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )
    elementos: list[Any] = []
    elementos.append(
        Paragraph(f"Comprobante de retención {snapshot.get('codigo', '')}", styles["Title"])
    )
    elementos.append(Spacer(1, 6 * mm))
    emisor = snapshot.get("emisor") or {}
    elementos.append(Paragraph("Emisor", styles["Heading2"]))
    elementos.append(Paragraph(f"{emisor.get('nombre', '')} — RIF {emisor.get('rif', '')}", styles["Normal"]))
    elementos.append(Spacer(1, 4 * mm))
    beneficiario = snapshot.get("beneficiario") or {}
    elementos.append(Paragraph("Beneficiario", styles["Heading2"]))
    elementos.append(
        Paragraph(
            f"{beneficiario.get('nombre', '')} — {beneficiario.get('identificacion_fiscal', '')}"
            "<br/>Datos declarados por el ente pagador",
            styles["Normal"],
        )
    )
    elementos.append(Spacer(1, 4 * mm))
    pago = snapshot.get("pago") or {}
    elementos.append(Paragraph("Pago", styles["Heading2"]))
    elementos.append(
        Paragraph(
            f"Código: {pago.get('codigo', '')}<br/>"
            f"Fecha: {pago.get('fecha_pago', '')}<br/>"
            f"Moneda: {snapshot.get('moneda', '')}<br/>"
            f"Bruto: {pago.get('bruto', '')}",
            styles["Normal"],
        )
    )
    elementos.append(Spacer(1, 4 * mm))
    lineas = snapshot.get("lineas") or []
    tabla_datos = [["Concepto", "Base", "Alícuota %", "Monto"]]
    for linea in lineas:
        tabla_datos.append(
            [
                linea.get("concepto_nombre", ""),
                str(linea.get("base", "")),
                str(linea.get("tasa", "")),
                str(linea.get("monto", "")),
            ]
        )
    tabla = Table(tabla_datos)
    tabla.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ]
        )
    )
    elementos.append(tabla)
    elementos.append(Spacer(1, 4 * mm))
    elementos.append(Paragraph(f"Total: {snapshot.get('total', '')}", styles["Heading3"]))
    elementos.append(Spacer(1, 4 * mm))
    politica = snapshot.get("politica") or {}
    elementos.append(Paragraph("Política y fuente", styles["Heading2"]))
    elementos.append(
        Paragraph(
            f"Código: {politica.get('codigo', '')}<br/>"
            f"Versión: {politica.get('numero_version', '')}<br/>"
            f"Fuente: {politica.get('fuente_descripcion', '')} — {politica.get('fuente_referencia', '')}",
            styles["Normal"],
        )
    )
    elementos.append(Spacer(1, 4 * mm))
    elementos.append(Paragraph(snapshot.get("leyenda", ""), styles["Normal"]))
    if c.estado == "ANULADO":
        elementos.append(Spacer(1, 4 * mm))
        elementos.append(Paragraph(f"ANULADO: {c.motivo_anulacion or ''}", styles["Heading2"]))
    doc.build(elementos)
    nombre = re.sub(r"[^A-Za-z0-9._-]", "", f"comprobante-{c.codigo}.pdf")
    return buffer.getvalue(), nombre


def anular_comprobante(
    db: Session, ctx: CompanyContext, id: str, cuerpo: dict[str, Any]
) -> dict[str, Any]:
    c = comprobante_de_empresa(db, ctx, id, bloquear=True)
    if c.estado == "ANULADO":
        raise ConflictError(
            "GOV_WITHHOLDING_RECEIPT_ALREADY_CANCELLED",
            "El comprobante ya está anulado.",
        )
    motivo = cuerpo.get("motivo")
    if not isinstance(motivo, str):
        raise KontrolError(
            code="GOV_WITHHOLDING_REASON_REQUIRED",
            message="El motivo de anulación debe ser una cadena de texto.",
            status_code=422,
        )
    motivo_limpio = motivo.strip()
    if len(motivo_limpio) < 10:
        raise KontrolError(
            code="GOV_WITHHOLDING_REASON_REQUIRED",
            message="El motivo de anulación debe tener al menos 10 caracteres.",
            status_code=422,
        )
    c.estado = "ANULADO"
    c.anulado_por = ctx.user_id
    c.anulado_en = instante_actual()
    c.motivo_anulacion = motivo_limpio
    db.flush()
    sustituto_id: str | None = None
    if cuerpo.get("sustituir"):
        beneficiario_original = (c.snapshot or {}).get("beneficiario") or {}
        beneficiario_corregido = cuerpo.get("beneficiario") or {}
        nombre = beneficiario_corregido.get("nombre")
        identificacion = beneficiario_corregido.get("identificacion_fiscal")
        if (
            not isinstance(nombre, str)
            or len(nombre) < 3
            or len(nombre) > 200
            or (
                identificacion is not None
                and (
                    not isinstance(identificacion, str)
                    or len(identificacion) > 30
                )
            )
            or set(beneficiario_corregido.keys()) - {"nombre", "identificacion_fiscal"}
        ):
            raise KontrolError(
                code="GOV_WITHHOLDING_BENEFICIARY_INVALID",
                message="Beneficiario corregido inválido.",
                status_code=422,
            )
        sustituto_beneficiario = {
            "nombre": nombre,
            "identificacion_fiscal": identificacion,
            "tipo_persona": beneficiario_original.get("tipo_persona"),
            "condiciones": beneficiario_original.get("condiciones", []),
        }
        liquidacion = _liquidacion_de_empresa(db, ctx, str(c.settlement_id))
        pago = _pago_de_liquidacion(db, ctx, liquidacion)
        concepto = db.get(GovernmentWithholdingCatalogItem, c.concept_id)
        if (
            concepto is None
            or concepto.company_id != ctx.company_id
        ):
            raise NotFoundError(
                "GOV_WITHHOLDING_CATALOG_NOT_FOUND",
                "El concepto de retención no existe o no pertenece a la empresa.",
            )
        lineas = _lineas_de_liquidacion(db, ctx, liquidacion)
        lineas = [
            linea
            for linea in lineas
            if str(linea.concept_id) == str(c.concept_id)
            and linea.aplica
            and linea.exige_comprobante
        ]
        lineas.sort(key=lambda linea: linea.orden)
        numero, codigo = _siguiente_numero(
            db, ctx, hoy_de_negocio().year, c.serie
        )
        snapshot = _instantanea(
            db,
            ctx,
            liquidacion,
            pago,
            concepto,
            lineas,
            numero,
            c.serie,
            codigo,
            sustituto_beneficiario,
            c.codigo,
        )
        huella = hashlib.sha256(
            json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        nuevo = GovernmentWithholdingReceipt(
            company_id=ctx.company_id,
            settlement_id=c.settlement_id,
            payment_id=c.payment_id,
            concept_id=c.concept_id,
            numero=numero,
            serie=c.serie,
            codigo=codigo,
            estado="EMITIDO",
            snapshot=snapshot,
            huella=huella,
            sustituye_a_id=c.id,
            emitido_por=ctx.user_id,
            emitido_en=instante_actual(),
        )
        db.add(nuevo)
        db.flush()
        registrar_historia(
            db,
            ctx,
            "COMPROBANTE",
            str(nuevo.id),
            "EMITIDO",
            snapshot,
        )
        auditar(
            db,
            ctx,
            "GOV_WITHHOLDING_RECEIPT_ISSUED",
            "GovernmentWithholdingReceipt",
            str(nuevo.id),
            {"codigo": codigo, "concepto": concepto.codigo, "monto": snapshot["total"]},
        )
        sustituto_id = str(nuevo.id)
    registrar_historia(
        db,
        ctx,
        "COMPROBANTE",
        str(c.id),
        "ANULADO",
        {"motivo": motivo_limpio, "sustituto": sustituto_id},
    )
    auditar(
        db,
        ctx,
        "GOV_WITHHOLDING_RECEIPT_CANCELLED",
        "GovernmentWithholdingReceipt",
        str(c.id),
        {"codigo": c.codigo, "motivo": motivo_limpio, "sustituto": sustituto_id},
    )
    resultado = comprobante_a_dict(db, ctx, c)
    resultado["sustituido_por_id"] = sustituto_id
    return resultado
