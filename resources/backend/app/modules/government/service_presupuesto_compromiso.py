"""Compromiso presupuestario (BUD-08, GOV-BUD-012): consume certificaciones vigentes de BUD-06.
Frontera BUD-09: cuando exista el causado, anular un compromiso causado se bloqueará en `anular`."""
import hashlib
import io
import json
from datetime import datetime
from decimal import Decimal
from typing import Any, BinaryIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext
from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.documents.models import Document, DocumentLink
from app.modules.documents.storage import generate_storage_key, get_storage
from app.modules.government.models import (
    GovernmentBudgetCategory,
    GovernmentBudgetCertificate,
    GovernmentBudgetClassifierItem,
    GovernmentBudgetCommitment,
    GovernmentBudgetCommitmentLine,
    GovernmentBudgetCredit,
    GovernmentBudgetFundingSource,
    GovernmentOfficial,
    GovernmentPosition,
    GovernmentStructure,
    GovernmentUnit,
)
from app.modules.government.monedas import canonical_currency
from app.modules.government.service_actos import _autoridad_valida
from app.modules.government.service_auditoria import _usuarios_por_ids
from app.modules.government.service_autoridad import competencias_en_vigor
from app.modules.government.service_identidad import _funcionario_del_actor, exigir_autoridad_funcional
from app.modules.government.service_presupuesto import (
    _auditar,
    _documento_valido,
    _ejercicio_de_empresa,
    _estado_invalido,
    _historia,
    _invalida,
)
from app.modules.government.service_presupuesto_certificacion import (
    _consumido_por_certificado,
    _decimal_finito,
    _etiqueta,
    _monto_es,
    _text,
    consumido_de_certificado,
    disponible_de_credito,
    situacion_de_certificado,
)
from app.modules.government.service_sod import funcionarios_de_actor, usuarios_equivalentes
from app.modules.government.service_tasas import verificar_limite
from app.modules.identity_access.models import User
from app.modules.organization.models import Company
from app.shared.audit import record_audit_after_rollback
from app.shared.clock import hoy_de_negocio, instante_actual


def _render_pdf_compromiso(snapshot: dict[str, Any], huella: str, emitido_en: datetime) -> bytes:
    styles = {
        "title": ParagraphStyle(name="TitleStyle", fontName="Helvetica-Bold", fontSize=13, leading=16),
        "label": ParagraphStyle(name="LabelStyle", fontName="Helvetica-Bold", fontSize=7, leading=9),
        "value": ParagraphStyle(name="ValueStyle", fontName="Helvetica", fontSize=7, leading=9),
        "h2": ParagraphStyle(
            name="Heading2",
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            spaceBefore=10,
            spaceAfter=4,
        ),
    }

    def styled(value: Any, style: str = "value") -> Paragraph:
        return Paragraph(_text(str(value) if value is not None else ""), styles[style])

    def pair_table(rows: list[tuple[str, Any]]) -> Table:
        data = [[styled(k, "label"), styled(v if v is not None else "")] for k, v in rows]
        table = Table(data, colWidths=[45 * mm, 125 * mm])
        table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        return table

    codigo = snapshot["codigo"]
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=f"Compromiso presupuestario {codigo}",
    )
    story: list[Any] = [
        Paragraph(f"Compromiso presupuestario {codigo}", styles["title"]),
        Spacer(1, 6 * mm),
    ]

    autoridad = snapshot.get("autoridad", {})
    expediente = snapshot.get("expediente", {})
    soporte = snapshot.get("soporte", {})

    conversion = autoridad.get("conversion") or None
    filas_conversion: list[tuple[str, Any]] = []
    if conversion:
        filas_conversion.append(
            (
                "Comparación del límite",
                f"{conversion.get('moneda_operacion', '')} frente a {conversion.get('moneda_limite', '')} en VES: {conversion.get('total_ves', '')} ≤ {conversion.get('limite_ves', '')}",
            )
        )
        for t in conversion.get("tasas", []):
            filas_conversion.append(
                (
                    f"Tasa oficial {t.get('moneda', '')}",
                    f"1 {t.get('moneda', '')} = {t.get('valor', '')} VES · {t.get('fuente', '')} · fecha efectiva {t.get('fecha_efectiva', '')} · versión {t.get('version', '')} · {t.get('fuente_referencia', '')}",
                )
            )

    story.append(
        pair_table(
            [
                ("Identificador", snapshot.get("codigo", "")),
                ("Ente", snapshot.get("ente", "")),
                ("Ejercicio", snapshot.get("anio", "")),
                ("Fecha", snapshot.get("fecha", "")),
                ("Estado", "VIGENTE"),
                ("Expediente", expediente.get("referencia", "")),
                ("Concepto", snapshot.get("concepto", "")),
                ("Moneda", snapshot.get("moneda", "")),
                ("Total", _monto_es(snapshot.get("total", 0))),
                ("Autoridad (cargo)", autoridad.get("cargo", "")),
                ("Unidad de la autoridad", autoridad.get("unidad", "")),
                ("Funcionario", autoridad.get("funcionario", "")),
                ("Límite de la autoridad", autoridad.get("limite", "")),
                *filas_conversion,
                ("Soporte", soporte.get("etiqueta", "")),
                ("Huella del soporte", soporte.get("sha256", "")),
                ("Emitido en", emitido_en.isoformat()),
                ("Huella", huella),
            ]
        )
    )
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("Imputaciones", styles["h2"]))
    lineas = snapshot.get("lineas") or []
    header = [
        styled("N.º", "label"),
        styled("CDP", "label"),
        styled("Categoría", "label"),
        styled("Unidad", "label"),
        styled("Partida", "label"),
        styled("Fuente", "label"),
        styled("Monto", "label"),
    ]
    rows = [header]
    for linea in lineas:
        rows.append(
            [
                styled(linea.get("linea", ""), "value"),
                styled(linea.get("certificado", ""), "value"),
                styled(linea.get("categoria", ""), "value"),
                styled(linea.get("unidad", ""), "value"),
                styled(linea.get("partida", ""), "value"),
                styled(linea.get("fuente", ""), "value"),
                styled(_monto_es(linea.get("monto", 0)), "value"),
            ]
        )
    table = Table(rows, colWidths=[10 * mm, 32 * mm, 32 * mm, 28 * mm, 32 * mm, 28 * mm, 28 * mm])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 4 * mm))
    story.append(
        Paragraph(
            "Compromiso registrado conforme a LOPPM arts. 242 y 248. Constancia institucional; no constituye firma electrónica.",
            styles["value"],
        )
    )

    doc.build(story)
    return buffer.getvalue()


def verificacion_limite(
    db: Session,
    ctx: CompanyContext,
    year_id: str,
    cargo_id: str,
    total: Decimal,
) -> dict[str, Any]:
    ejercicio = _ejercicio_de_empresa(db, ctx, year_id)
    hoy = hoy_de_negocio()
    cargo = db.execute(
        select(GovernmentPosition).where(
            GovernmentPosition.id == cargo_id,
            GovernmentPosition.company_id == ctx.company_id,
        )
    ).scalar_one_or_none()
    comp = None
    if cargo:
        competencias = competencias_en_vigor(db, cargo, hoy)
        comp = next(
            (c for c in competencias if c["accion"] == "COMPROMETER" and c["materia"] == "PRESUPUESTO"),
            None,
        )
    if not cargo or comp is None:
        mensaje = "El cargo no tiene hoy la competencia COMPROMETER en materia de PRESUPUESTO"
        raise KontrolError(
            code="GOV_BUDGET_COMMITMENT_AUTHORITY_INVALID",
            message=mensaje,
            field_errors={"autoridad_cargo_id": [mensaje]},
            status_code=422,
        )
    if comp.get("tipo_limite") != "MONTO":
        return {
            "cargo_id": cargo_id,
            "limite_tipo": "SIN_LIMITE",
            "limite": "Sin límite",
            "verificacion": None,
        }
    monto = Decimal(str(comp.get("monto", 0)))
    moneda = comp.get("moneda") or ""
    verificacion = verificar_limite(
        db,
        ctx,
        ejercicio.moneda_funcional or "",
        total,
        monto,
        moneda,
        hoy,
        bloquear=False,
        exigir=False,
    )
    return {
        "cargo_id": cargo_id,
        "limite_tipo": "MONTO",
        "limite": f"{_monto_es(monto)} {moneda}",
        "verificacion": verificacion,
    }


def _salida_compromiso(db: Session, ctx: CompanyContext, k: GovernmentBudgetCommitment) -> dict[str, Any]:
    usuarios_ids = list({u for u in (k.emitido_por, k.anulado_por) if u})
    usuarios = _usuarios_por_ids(db, usuarios_ids, ctx.tenant_id)

    lineas = db.execute(
        select(GovernmentBudgetCommitmentLine)
        .where(GovernmentBudgetCommitmentLine.commitment_id == k.id)
        .order_by(GovernmentBudgetCommitmentLine.linea)
    ).scalars().all()

    lineas_salida: list[dict[str, Any]] = []
    for linea in lineas:
        cdp = db.get(GovernmentBudgetCertificate, linea.certificate_id)
        certificado_codigo = cdp.codigo if cdp else ""
        credito = db.get(GovernmentBudgetCredit, linea.credit_id)
        categoria = None
        unidad = None
        partida = None
        fuente = None
        if credito:
            categoria = db.get(GovernmentBudgetCategory, credito.category_id)
            partida = db.get(GovernmentBudgetClassifierItem, credito.item_id)
            fuente = db.get(GovernmentBudgetFundingSource, credito.source_id)
            if categoria and categoria.unit_id:
                unidad = db.get(GovernmentUnit, categoria.unit_id)
        lineas_salida.append(
            {
                "linea": linea.linea,
                "certificado_id": str(linea.certificate_id),
                "certificado_codigo": certificado_codigo,
                "credito_id": str(linea.credit_id),
                "categoria": _etiqueta(categoria.codigo_completo, categoria.denominacion) if categoria else "",
                "unidad": _etiqueta(unidad.code, unidad.name) if unidad else None,
                "partida": _etiqueta(partida.codigo, partida.denominacion) if partida else "",
                "fuente": _etiqueta(fuente.codigo, fuente.denominacion) if fuente else "",
                "monto": str(linea.monto),
            }
        )

    snapshot = k.snapshot or {}
    autoridad = snapshot.get("autoridad", {})
    soporte = snapshot.get("soporte", {})
    total = sum((linea.monto for linea in lineas), Decimal("0"))

    return {
        "id": str(k.id),
        "codigo": k.codigo,
        "estado": k.estado,
        "fecha": k.fecha,
        "emitido_en": k.emitido_en,
        "total": str(total),
        "moneda": k.moneda,
        "concepto": k.concepto,
        "expediente_id": str(k.procurement_file_id) if k.procurement_file_id else None,
        "expediente_referencia": k.expediente_referencia,
        "autoridad_cargo": autoridad.get("cargo", "") or k.autoridad_cargo_nombre or "",
        "autoridad_unidad": autoridad.get("unidad", "") or k.autoridad_unidad or "",
        "autoridad_funcionario": autoridad.get("funcionario") or k.autoridad_funcionario_nombre or None,
        "limite": autoridad.get("limite", ""),
        "conversion": autoridad.get("conversion"),
        "soporte_documento_id": k.soporte_documento_id,
        "soporte": soporte.get("etiqueta", ""),
        "soporte_sha256": k.soporte_sha256,
        "emitido_por": usuarios.get(k.emitido_por or "", "") if k.emitido_por else "",
        "huella": k.huella,
        "documento_nombre": k.documento_nombre,
        "documento_sha256": k.documento_sha256,
        "anulado_en": k.anulado_en,
        "anulado_por": usuarios.get(k.anulado_por or "", "") if k.anulado_por else None,
        "motivo_anulacion": k.motivo_anulacion,
        "lineas": lineas_salida,
    }


def opciones(db: Session, ctx: CompanyContext, year_id: str) -> dict[str, Any]:
    ejercicio = _ejercicio_de_empresa(db, ctx, year_id)
    hoy = hoy_de_negocio()
    comprometible = ejercicio.estado in ("APROBADO", "RECONDUCIDO") and hoy.year == ejercicio.anio

    certificados = db.execute(
        select(GovernmentBudgetCertificate)
        .where(
            GovernmentBudgetCertificate.year_id == ejercicio.id,
            GovernmentBudgetCertificate.company_id == ctx.company_id,
            GovernmentBudgetCertificate.estado == "VIGENTE",
        )
        .order_by(GovernmentBudgetCertificate.numero)
    ).scalars().all()

    consumidos = _consumido_por_certificado(db, str(ejercicio.id))
    certificados_salida: list[dict[str, Any]] = []
    for c in certificados:
        monto = c.monto
        consumido = consumidos.get(str(c.id), Decimal("0.00"))
        remanente = monto - consumido
        if remanente <= 0:
            continue
        credito = db.get(GovernmentBudgetCredit, c.credit_id)
        categoria = None
        unidad = None
        partida = None
        fuente = None
        if credito:
            categoria = db.get(GovernmentBudgetCategory, credito.category_id)
            partida = db.get(GovernmentBudgetClassifierItem, credito.item_id)
            fuente = db.get(GovernmentBudgetFundingSource, credito.source_id)
            if categoria and categoria.unit_id:
                unidad = db.get(GovernmentUnit, categoria.unit_id)
        certificados_salida.append(
            {
                "certificado_id": str(c.id),
                "codigo": c.codigo,
                "expediente_id": str(c.procurement_file_id) if c.procurement_file_id else None,
                "expediente_referencia": c.expediente_referencia,
                "credito_id": str(c.credit_id),
                "categoria": _etiqueta(categoria.codigo_completo, categoria.denominacion) if categoria else "",
                "unidad": _etiqueta(unidad.code, unidad.name) if unidad else None,
                "partida": _etiqueta(partida.codigo, partida.denominacion) if partida else "",
                "fuente": _etiqueta(fuente.codigo, fuente.denominacion) if fuente else "",
                "monto": str(monto),
                "consumido": str(consumido),
                "remanente": str(remanente),
                "situacion": situacion_de_certificado(c.estado, monto, consumido),
                "etiqueta": f"{c.codigo} · saldo certificado disponible {_monto_es(remanente)} {c.moneda}",
            }
        )

    autoridades: list[dict[str, Any]] = []
    estructura = db.execute(
        select(GovernmentStructure).where(
            GovernmentStructure.company_id == ctx.company_id,
            GovernmentStructure.exercise == hoy.year,
        )
    ).scalar_one_or_none()
    if estructura:
        cargos = db.execute(
            select(GovernmentPosition).where(
                GovernmentPosition.company_id == ctx.company_id,
                GovernmentPosition.structure_id == estructura.id,
                GovernmentPosition.status.in_(("VIGENTE", "INACTIVO")),
            )
        ).scalars().all()
        for cargo in cargos:
            if cargo.valid_from and cargo.valid_from > hoy:
                continue
            if cargo.valid_to and cargo.valid_to < hoy:
                continue
            competencias = competencias_en_vigor(db, cargo, hoy)
            comp = next((c for c in competencias if c["accion"] == "COMPROMETER" and c["materia"] == "PRESUPUESTO"), None)
            if comp:
                unidad = db.get(GovernmentUnit, cargo.unit_id) if cargo.unit_id else None
                limite_tipo = comp.get("tipo_limite")
                limite_monto = None
                limite_moneda = None
                limite = ""
                if limite_tipo == "MONTO":
                    limite_monto = Decimal(str(comp.get("monto", 0)))
                    limite_moneda = comp.get("moneda")
                    limite = f"{_monto_es(limite_monto)} {limite_moneda}"
                else:
                    limite = "Sin límite"
                autoridades.append(
                    {
                        "cargo_id": str(cargo.id),
                        "etiqueta": _etiqueta(cargo.code, cargo.name),
                        "unidad": _etiqueta(unidad.code, unidad.name) if unidad else "",
                        "limite_tipo": limite_tipo,
                        "limite_monto": str(limite_monto) if limite_monto is not None else None,
                        "limite_moneda": limite_moneda,
                        "limite": limite,
                    }
                )
    autoridades.sort(key=lambda x: x["etiqueta"])

    soportes: list[dict[str, Any]] = []
    documentos = db.execute(
        select(Document)
        .join(DocumentLink, DocumentLink.document_id == Document.id)
        .where(
            DocumentLink.resource_type == "GovernmentBudgetYear",
            DocumentLink.resource_id == str(ejercicio.id),
            DocumentLink.company_id == ctx.company_id,
            Document.company_id == ctx.company_id,
            Document.status == "ACTIVE",
        )
    ).scalars().all()
    vistos: set[str] = set()
    for documento in documentos:
        if str(documento.id) in vistos:
            continue
        vistos.add(str(documento.id))
        etiqueta = f"{documento.document_number} · {documento.title}" if documento.document_number else documento.title
        soportes.append({"id": str(documento.id), "etiqueta": etiqueta})
    soportes.sort(key=lambda x: x["etiqueta"])

    return {
        "anio": ejercicio.anio,
        "estado": ejercicio.estado,
        "moneda": canonical_currency(ejercicio.moneda_funcional),
        "comprometible": comprometible,
        "certificados": certificados_salida,
        "autoridades": autoridades,
        "soportes": soportes,
    }


def listar(db: Session, ctx: CompanyContext, year_id: str) -> dict[str, Any]:
    ejercicio = _ejercicio_de_empresa(db, ctx, year_id)
    compromisos = db.execute(
        select(GovernmentBudgetCommitment)
        .where(
            GovernmentBudgetCommitment.year_id == ejercicio.id,
            GovernmentBudgetCommitment.company_id == ctx.company_id,
        )
        .order_by(GovernmentBudgetCommitment.numero.desc())
    ).scalars().all()
    return {"items": [_salida_compromiso(db, ctx, k) for k in compromisos]}


def detalle(db: Session, ctx: CompanyContext, year_id: str, compromiso_id: str) -> dict[str, Any]:
    ejercicio = _ejercicio_de_empresa(db, ctx, year_id)
    k = db.execute(
        select(GovernmentBudgetCommitment).where(
            GovernmentBudgetCommitment.id == compromiso_id,
            GovernmentBudgetCommitment.year_id == ejercicio.id,
            GovernmentBudgetCommitment.company_id == ctx.company_id,
        )
    ).scalar_one_or_none()
    if not k:
        raise NotFoundError("GOV_BUDGET_COMMITMENT_NOT_FOUND", "El compromiso no existe en este ejercicio")
    return _salida_compromiso(db, ctx, k)


def emitir(db: Session, ctx: CompanyContext, user: User, year_id: str, cuerpo: dict[str, Any]) -> dict[str, Any]:
    ejercicio = _ejercicio_de_empresa(db, ctx, year_id, bloquear=True)
    if ejercicio.estado not in ("APROBADO", "RECONDUCIDO"):
        raise _estado_invalido()

    hoy = hoy_de_negocio()
    if hoy.year != ejercicio.anio:
        raise _invalida("Solo se compromete dentro del año del ejercicio (LOPPM art. 248)", "fecha")

    concepto = (cuerpo.get("concepto") or "").strip()
    if len(concepto) < 10 or len(concepto) > 500:
        raise _invalida("El concepto debe tener entre 10 y 500 caracteres", "concepto")

    lineas_cuerpo = cuerpo.get("lineas")
    if not isinstance(lineas_cuerpo, list) or not (1 <= len(lineas_cuerpo) <= 20):
        raise _invalida("Indique entre 1 y 20 líneas de imputación", "lineas")

    certificados_ids: list[str] = []
    montos: list[Decimal] = []
    for linea in lineas_cuerpo:
        if not isinstance(linea, dict):
            raise _invalida("Cada línea debe ser un objeto", "lineas")
        certificado_id = str(linea.get("certificado_id") or "")
        if not certificado_id:
            raise _invalida("Indique el certificado de cada línea", "lineas")
        if certificado_id in certificados_ids:
            raise _invalida("Cada certificación se imputa una sola vez por compromiso", "lineas")
        certificados_ids.append(certificado_id)
        monto = _decimal_finito(linea.get("monto"))
        if monto is None:
            raise _invalida("El monto debe ser mayor que cero y tener como máximo 2 decimales", "lineas")
        exponente = monto.as_tuple().exponent
        if monto <= 0 or (not isinstance(exponente, int) or exponente < -2) or monto >= Decimal("10000000000000000"):
            raise _invalida("El monto debe ser mayor que cero y tener como máximo 2 decimales", "lineas")
        montos.append(monto)

    certificados = db.execute(
        select(GovernmentBudgetCertificate)
        .where(
            GovernmentBudgetCertificate.id.in_(certificados_ids),
            GovernmentBudgetCertificate.year_id == ejercicio.id,
            GovernmentBudgetCertificate.company_id == ctx.company_id,
        )
        .order_by(GovernmentBudgetCertificate.id)
        .with_for_update()
    ).scalars().all()
    if len(certificados) != len(certificados_ids):
        raise NotFoundError("GOV_BUDGET_CERTIFICATE_NOT_FOUND", "Una certificación no existe en este ejercicio")
    certificados_map = {str(c.id): c for c in certificados}

    for c in certificados:
        if c.estado != "VIGENTE":
            raise ConflictError(
                "GOV_BUDGET_CERTIFICATE_NOT_ACTIVE",
                f"La certificación {c.codigo} está anulada",
            )

    creditos_ids = list({c.credit_id for c in certificados})
    creditos = db.execute(
        select(GovernmentBudgetCredit)
        .where(GovernmentBudgetCredit.id.in_(creditos_ids))
        .order_by(GovernmentBudgetCredit.id)
        .with_for_update()
    ).scalars().all()
    creditos_map = {str(c.id): c for c in creditos}
    if len(creditos_map) != len(creditos_ids):
        raise NotFoundError("GOV_BUDGET_CREDIT_NOT_FOUND", "Un crédito no existe en este ejercicio")

    expedientes = {(c.procurement_file_id, c.expediente_referencia or "") for c in certificados}
    if len(expedientes) != 1:
        raise KontrolError(
            code="GOV_BUDGET_COMMITMENT_EXPEDIENTE_MISMATCH",
            message="Las certificaciones imputadas pertenecen a expedientes distintos",
            field_errors={"lineas": ["Las certificaciones imputadas pertenecen a expedientes distintos"]},
            status_code=422,
        )
    expediente_id, expediente_referencia = next(iter(expedientes))

    actores = usuarios_equivalentes(db, ctx, str(ctx.user_id))
    funcionarios = funcionarios_de_actor(db, ctx, str(ctx.user_id))
    en_conflicto = [
        c.codigo
        for c in certificados
        if c.emitida_por in actores or (c.firmante_funcionario_id and str(c.firmante_funcionario_id) in funcionarios)
    ]
    if en_conflicto:
        anio = ejercicio.anio
        year_id_str = str(ejercicio.id)
        certificados_texto = en_conflicto
        record_audit_after_rollback(
            db,
            action="GOV_BUDGET_COMMITMENT_SOD_BLOCKED",
            entity_type="GovernmentBudgetYear",
            entity_id=year_id_str,
            tenant_id=ctx.tenant_id,
            company_id=ctx.company_id,
            user_id=ctx.user_id,
            after={"anio": anio, "certificados": certificados_texto, "regla": "Quien certifica no compromete"},
        )
        raise ConflictError(
            "GOV_SOD_CONFLICT",
            f"Operación bloqueada por segregación de funciones: usted emitió o firmó {', '.join(en_conflicto)}. El compromiso debe registrarlo otro usuario (quien certifica no compromete).",
            details={"certificados": en_conflicto, "regla": "Quien certifica no compromete"},
        )

    total = Decimal("0")
    lineas_datos: list[tuple[str, Decimal]] = []
    for certificado_id, monto in zip(certificados_ids, montos, strict=True):
        c = certificados_map[certificado_id]
        consumido = consumido_de_certificado(db, c)
        remanente = c.monto - consumido
        if monto > remanente:
            mensaje = f"La certificación {c.codigo} tiene un remanente de {remanente}; solicitado {monto}"
            raise KontrolError(
                code="GOV_BUDGET_CERTIFICATE_INSUFFICIENT_REMAINING",
                message=mensaje,
                details={"certificado": c.codigo, "remanente": str(remanente), "solicitado": str(monto)},
                field_errors={"lineas": [mensaje]},
                status_code=422,
            )
        total += monto
        lineas_datos.append((certificado_id, monto))

    cargo_id = str(cuerpo.get("autoridad_cargo_id") or "")
    cargo = db.execute(
        select(GovernmentPosition).where(
            GovernmentPosition.id == cargo_id,
            GovernmentPosition.company_id == ctx.company_id,
        )
    ).scalar_one_or_none()
    comp = None
    if cargo:
        competencias = competencias_en_vigor(db, cargo, hoy)
        comp = next((c for c in competencias if c["accion"] == "COMPROMETER" and c["materia"] == "PRESUPUESTO"), None)
    if not cargo or not _autoridad_valida(db, ctx.company_id, cargo_id, hoy, "COMPROMETER", "PRESUPUESTO") or comp is None:
        mensaje = "El cargo no tiene hoy la competencia COMPROMETER en materia de PRESUPUESTO"
        raise KontrolError(
            code="GOV_BUDGET_COMMITMENT_AUTHORITY_INVALID",
            message=mensaje,
            field_errors={"autoridad_cargo_id": [mensaje]},
            status_code=422,
        )
    exigir_autoridad_funcional(db, ctx, str(cargo.id), "COMPROMETER", "PRESUPUESTO")

    conversion: dict[str, Any] | None = None
    limite_tipo = comp.get("tipo_limite")
    limite_monto = None
    limite_moneda = None
    limite = ""
    if limite_tipo == "MONTO":
        limite_monto = Decimal(str(comp.get("monto", 0)))
        limite_moneda = comp.get("moneda") or ""
        limite = f"{_monto_es(limite_monto)} {limite_moneda}"
        verificacion = verificar_limite(
            db,
            ctx,
            ejercicio.moneda_funcional or "",
            total,
            limite_monto,
            limite_moneda,
            hoy,
            bloquear=True,
            exigir=True,
        )
        if not verificacion["dentro_del_limite"]:
            moneda_canonica = canonical_currency(ejercicio.moneda_funcional)
            mensaje = f"El total {total} {moneda_canonica} excede el límite de {_etiqueta(cargo.code, cargo.name)} ({limite_monto} {canonical_currency(limite_moneda)})"
            details: dict[str, Any] = {
                "total": str(total),
                "moneda": moneda_canonica,
                "limite": str(limite_monto),
                "moneda_limite": canonical_currency(limite_moneda),
            }
            if verificacion["requiere_conversion"]:
                mensaje += f" (con la tasa oficial BCV: {verificacion['total_ves']} VES frente a {verificacion['limite_ves']} VES)"
                details["conversion"] = verificacion
            raise KontrolError(
                code="GOV_BUDGET_COMMITMENT_AUTHORITY_AMOUNT_EXCEEDED",
                message=mensaje,
                details=details,
                field_errors={"autoridad_cargo_id": [mensaje]},
                status_code=422,
            )
        if verificacion["requiere_conversion"]:
            conversion = verificacion
    else:
        limite = "Sin límite"

    documento, sha = _documento_valido(db, ctx, ejercicio, str(cuerpo["soporte_documento_id"]), "soporte_documento_id")

    antes_por_credito: dict[str, Decimal] = {str(cr.id): disponible_de_credito(db, cr) for cr in creditos}

    max_numero = db.execute(
        select(func.max(GovernmentBudgetCommitment.numero)).where(
            GovernmentBudgetCommitment.year_id == ejercicio.id
        )
    ).scalar_one_or_none()
    numero = (max_numero or 0) + 1
    codigo = f"CP-{ejercicio.anio}-{numero:04d}"

    unidad_cargo = db.get(GovernmentUnit, cargo.unit_id) if cargo.unit_id else None
    etiqueta_unidad_cargo = _etiqueta(unidad_cargo.code, unidad_cargo.name) if unidad_cargo else ""
    official_id = _funcionario_del_actor(db, ctx)
    funcionario_nombre = ""
    if official_id:
        funcionario = db.get(GovernmentOfficial, official_id)
        if funcionario:
            funcionario_nombre = funcionario.nombre
    ente = (db.get(Company, ctx.company_id) or Company()).legal_name or ""

    lineas_snapshot: list[dict[str, Any]] = []
    for i, (certificado_id, monto) in enumerate(lineas_datos, start=1):
        c = certificados_map[certificado_id]
        credito = creditos_map[str(c.credit_id)]
        categoria = db.get(GovernmentBudgetCategory, credito.category_id)
        partida = db.get(GovernmentBudgetClassifierItem, credito.item_id)
        fuente = db.get(GovernmentBudgetFundingSource, credito.source_id)
        unidad = db.get(GovernmentUnit, categoria.unit_id) if categoria and categoria.unit_id else None
        disponible_antes = antes_por_credito[str(credito.id)]
        lineas_snapshot.append(
            {
                "linea": i,
                "certificado_id": str(c.id),
                "certificado": c.codigo,
                "credito_id": str(credito.id),
                "categoria": _etiqueta(categoria.codigo_completo, categoria.denominacion) if categoria else "",
                "unidad": _etiqueta(unidad.code, unidad.name) if unidad else None,
                "partida": _etiqueta(partida.codigo, partida.denominacion) if partida else "",
                "fuente": _etiqueta(fuente.codigo, fuente.denominacion) if fuente else "",
                "monto": str(monto),
                "disponible_credito": str(disponible_antes),
            }
        )

    snapshot: dict[str, Any] = {
        "codigo": codigo,
        "ente": ente,
        "anio": ejercicio.anio,
        "moneda": canonical_currency(ejercicio.moneda_funcional),
        "fecha": hoy.isoformat(),
        "concepto": concepto,
        "total": str(total),
        "expediente": {"id": expediente_id, "referencia": expediente_referencia},
        "lineas": lineas_snapshot,
        "autoridad": {
            "cargo_id": str(cargo.id),
            "cargo": _etiqueta(cargo.code, cargo.name),
            "unidad": etiqueta_unidad_cargo,
            "funcionario_id": official_id,
            "funcionario": funcionario_nombre,
            "usuario_id": str(user.id),
            "limite_tipo": limite_tipo,
            "limite_monto": str(limite_monto) if limite_monto is not None else None,
            "limite_moneda": limite_moneda,
            "limite": limite,
            "conversion": conversion,
        },
        "soporte": {
            "documento_id": str(documento.id),
            "etiqueta": f"{documento.document_number} · {documento.title}" if documento.document_number else documento.title,
            "sha256": sha,
        },
    }
    huella = hashlib.sha256(
        json.dumps(snapshot, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    emitido_en = instante_actual()
    pdf = _render_pdf_compromiso(snapshot, huella, emitido_en)

    storage = get_storage()
    storage_key = generate_storage_key(ctx.company_id)
    size, sha_pdf = storage.put(storage_key, io.BytesIO(pdf))
    if sha_pdf != hashlib.sha256(pdf).hexdigest() or size != len(pdf):
        storage.delete(storage_key)
        raise KontrolError(
            code="STORAGE_HASH_MISMATCH",
            message="El reporte almacenado no coincide con su huella",
            status_code=500,
        )
    if not storage.verify(storage_key, sha_pdf):
        storage.delete(storage_key)
        raise KontrolError(
            code="STORAGE_HASH_MISMATCH",
            message="El reporte almacenado no coincide con su huella",
            status_code=500,
        )

    documento_nombre = f"compromiso-{codigo}.pdf"

    cargo_nombre = cargo.name or ""
    compromiso = GovernmentBudgetCommitment(
        year_id=ejercicio.id,
        company_id=ctx.company_id,
        numero=numero,
        codigo=codigo,
        estado="VIGENTE",
        moneda=canonical_currency(ejercicio.moneda_funcional),
        fecha=hoy,
        concepto=concepto,
        expediente_referencia=expediente_referencia,
        procurement_file_id=expediente_id,
        autoridad_cargo_id=cargo.id,
        autoridad_cargo_codigo=cargo.code,
        autoridad_cargo_nombre=cargo_nombre,
        autoridad_unidad=etiqueta_unidad_cargo,
        autoridad_funcionario_id=official_id,
        autoridad_funcionario_nombre=funcionario_nombre,
        limite_tipo=limite_tipo,
        limite_monto=limite_monto,
        limite_moneda=limite_moneda,
        soporte_documento_id=str(documento.id),
        soporte_sha256=sha,
        emitido_por=str(user.id),
        emitido_en=emitido_en,
        snapshot=snapshot,
        huella=huella,
        documento_storage_key=storage_key,
        documento_sha256=sha_pdf,
        documento_tamano=size,
        documento_nombre=documento_nombre,
        created_by=ctx.user_id,
    )
    db.add(compromiso)
    db.flush()

    for i, (certificado_id, monto) in enumerate(lineas_datos, start=1):
        c = certificados_map[certificado_id]
        db.add(
            GovernmentBudgetCommitmentLine(
                commitment_id=compromiso.id,
                year_id=ejercicio.id,
                company_id=ctx.company_id,
                certificate_id=c.id,
                credit_id=c.credit_id,
                linea=i,
                monto=monto,
                created_by=ctx.user_id,
            )
        )
    db.flush()

    for cr in creditos:
        despues = disponible_de_credito(db, cr)
        if despues < 0 or despues != antes_por_credito[str(cr.id)]:
            raise KontrolError(
                code="GOV_BUDGET_INSUFFICIENT_AVAILABILITY",
                message="El compromiso alteraría la disponibilidad del crédito",
                status_code=422,
            )

    _historia(
        db,
        ctx,
        ejercicio,
        "COMPROMISO_REGISTRADO",
        {"codigo": codigo, "total": str(total), "lineas": len(lineas_datos)},
    )
    _auditar(
        db,
        ctx,
        ejercicio,
        "GOV_BUDGET_COMMITMENT_ISSUED",
        {
            "anio": ejercicio.anio,
            "autoridad_cargo": _etiqueta(cargo.code, cargo_nombre),
            "codigo": codigo,
            "concepto": concepto,
            "expediente": expediente_referencia,
            "lineas": [f"{certificados_map[cid].codigo}: {m}" for cid, m in lineas_datos],
            "soporte": f"{documento.document_number} · {documento.title}" if documento.document_number else documento.title,
            "total": str(total),
        },
    )
    db.flush()
    return _salida_compromiso(db, ctx, compromiso)


def anular(
    db: Session, ctx: CompanyContext, user: User, year_id: str, compromiso_id: str, cuerpo: dict[str, Any]
) -> dict[str, Any]:
    ejercicio = _ejercicio_de_empresa(db, ctx, year_id, bloquear=True)
    if ejercicio.estado not in ("APROBADO", "RECONDUCIDO"):
        raise _estado_invalido()

    compromiso = db.execute(
        select(GovernmentBudgetCommitment)
        .where(
            GovernmentBudgetCommitment.id == compromiso_id,
            GovernmentBudgetCommitment.year_id == ejercicio.id,
            GovernmentBudgetCommitment.company_id == ctx.company_id,
        )
        .with_for_update()
    ).scalar_one_or_none()
    if not compromiso:
        raise NotFoundError("GOV_BUDGET_COMMITMENT_NOT_FOUND", "El compromiso no existe en este ejercicio")
    if compromiso.estado != "VIGENTE":
        raise ConflictError("GOV_BUDGET_COMMITMENT_NOT_ACTIVE", "El compromiso ya está anulado")

    motivo = (cuerpo.get("motivo") or "").strip()
    if len(motivo) < 10 or len(motivo) > 500:
        raise _invalida("El motivo debe tener entre 10 y 500 caracteres", "motivo")

    total = sum(
        (linea.monto for linea in db.execute(
            select(GovernmentBudgetCommitmentLine).where(GovernmentBudgetCommitmentLine.commitment_id == compromiso.id)
        ).scalars().all()),
        Decimal("0"),
    )

    compromiso.estado = "ANULADO"
    compromiso.anulado_por = str(user.id)
    compromiso.anulado_en = instante_actual()
    compromiso.motivo_anulacion = motivo
    db.flush()

    _historia(db, ctx, ejercicio, "COMPROMISO_ANULADO", {"codigo": compromiso.codigo, "total": str(total), "motivo": motivo})
    _auditar(
        db,
        ctx,
        ejercicio,
        "GOV_BUDGET_COMMITMENT_ANNULLED",
        {"anio": ejercicio.anio, "codigo": compromiso.codigo, "motivo": motivo, "total": str(total)},
    )
    return _salida_compromiso(db, ctx, compromiso)


def abrir_documento(
    db: Session, ctx: CompanyContext, year_id: str, compromiso_id: str
) -> tuple[str, BinaryIO, int]:
    ejercicio = _ejercicio_de_empresa(db, ctx, year_id)
    k = db.execute(
        select(GovernmentBudgetCommitment).where(
            GovernmentBudgetCommitment.id == compromiso_id,
            GovernmentBudgetCommitment.year_id == ejercicio.id,
            GovernmentBudgetCommitment.company_id == ctx.company_id,
        )
    ).scalar_one_or_none()
    if not k:
        raise NotFoundError("GOV_BUDGET_COMMITMENT_NOT_FOUND", "El compromiso no existe en este ejercicio")

    storage = get_storage()
    if not storage.verify(k.documento_storage_key, k.documento_sha256):
        raise KontrolError(
            code="STORAGE_HASH_MISMATCH",
            message="El documento almacenado no coincide con su huella",
            status_code=500,
        )
    return (k.documento_nombre or "", storage.open(k.documento_storage_key), k.documento_tamano or 0)
