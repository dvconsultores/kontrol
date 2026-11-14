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
from app.modules.documents.storage import generate_storage_key, get_storage
from app.modules.government.models import (
    GovernmentBudgetCategory,
    GovernmentBudgetCertificate,
    GovernmentBudgetClassifierItem,
    GovernmentBudgetCredit,
    GovernmentBudgetFundingSource,
    GovernmentOfficial,
    GovernmentPosition,
    GovernmentProcurementFile,
    GovernmentStructure,
    GovernmentUnit,
)
from app.modules.government.service_actos import _autoridad_valida
from app.modules.government.service_auditoria import _usuarios_por_ids
from app.modules.government.service_autoridad import competencias_en_vigor
from app.modules.government.service_identidad import _funcionario_del_actor, exigir_autoridad_funcional
from app.modules.government.service_presupuesto import _auditar, _ejercicio_de_empresa, _estado_invalido, _historia, _invalida
from app.modules.identity_access.models import User
from app.modules.organization.models import Company
from app.shared.clock import hoy_de_negocio, instante_actual


def _text(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _etiqueta(codigo: str, nombre: str) -> str:
    return f"{codigo} · {nombre}"


def _monto_es(monto: Decimal | str) -> str:
    valor = Decimal(str(monto))
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def disponible_de_credito(db: Session, credito: GovernmentBudgetCredit) -> Decimal:
    """Disponibilidad certificable = crédito aprobado − certificaciones vigentes. Cuando existan, BUD-10 sumará \
modificaciones netas y BUD-08 restará compromisos aquí, sin tocar certificados emitidos."""
    resultado = db.execute(
        select(func.coalesce(func.sum(GovernmentBudgetCertificate.monto), 0)).where(
            GovernmentBudgetCertificate.credit_id == credito.id,
            GovernmentBudgetCertificate.estado == "VIGENTE",
        )
    ).scalar_one_or_none()
    vigente = Decimal(str(resultado or 0))
    return credito.monto - vigente


def _vigentes_por_credito(db: Session, year_id: str) -> dict[str, Decimal]:
    filas = db.execute(
        select(
            GovernmentBudgetCertificate.credit_id,
            func.sum(GovernmentBudgetCertificate.monto),
        )
        .where(
            GovernmentBudgetCertificate.year_id == year_id,
            GovernmentBudgetCertificate.estado == "VIGENTE",
        )
        .group_by(GovernmentBudgetCertificate.credit_id)
    ).all()
    return {str(credit_id): Decimal(str(monto or 0)) for credit_id, monto in filas}


def _refs_unicas(items: list[dict[str, Any]], campo: str) -> list[dict[str, Any]]:
    vistos: dict[str, dict[str, Any]] = {}
    for item in items:
        valor = item.get(campo)
        if valor and valor["id"] not in vistos:
            vistos[valor["id"]] = {"id": valor["id"], "etiqueta": valor["etiqueta"]}
    return sorted(vistos.values(), key=lambda x: x["etiqueta"])


def _render_pdf(snapshot: dict[str, Any], huella: str, emitida_en: datetime) -> bytes:
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
        title=f"Certificación de disponibilidad presupuestaria {codigo}",
    )
    story: list[Any] = [
        Paragraph(f"Certificación de disponibilidad presupuestaria {codigo}", styles["title"]),
        Spacer(1, 6 * mm),
    ]

    credito = snapshot.get("credito", {})
    firmante = snapshot.get("firmante", {})
    expediente = snapshot.get("expediente", {})

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
                ("Categoría programática", credito.get("categoria", "")),
                ("Unidad ejecutora", credito.get("unidad", "")),
                ("Partida", credito.get("partida", "")),
                ("Fuente", credito.get("fuente", "")),
                ("Moneda", snapshot.get("moneda", "")),
                ("Monto", _monto_es(snapshot.get("monto", 0))),
                ("Saldo antes", _monto_es(snapshot.get("saldo_antes", 0))),
                ("Saldo después", _monto_es(snapshot.get("saldo_despues", 0))),
                ("Firmante (cargo)", firmante.get("cargo", "")),
                ("Unidad del firmante", firmante.get("unidad", "")),
                ("Funcionario", firmante.get("funcionario", "")),
                ("Emitida en", emitida_en.isoformat()),
                ("Huella", huella),
            ]
        )
    )
    story.append(Spacer(1, 4 * mm))
    story.append(
        Paragraph(
            "Certificación emitida conforme a LOPPM art. 242. Constancia institucional; no constituye firma electrónica.",
            styles["value"],
        )
    )

    doc.build(story)
    return buffer.getvalue()


def _salida(c: GovernmentBudgetCertificate, username_emitida: str | None = None, username_anulada: str | None = None) -> dict[str, Any]:
    snapshot = c.snapshot or {}
    credito = snapshot.get("credito", {})
    firmante = snapshot.get("firmante", {})
    return {
        "id": str(c.id),
        "codigo": c.codigo,
        "estado": c.estado,
        "fecha": c.fecha,
        "emitida_en": c.emitida_en,
        "monto": c.monto,
        "saldo_antes": c.saldo_antes,
        "saldo_despues": c.saldo_despues,
        "moneda": c.moneda,
        "concepto": c.concepto,
        "expediente_id": str(c.procurement_file_id) if c.procurement_file_id else None,
        "expediente_referencia": c.expediente_referencia,
        "credito_id": str(c.credit_id),
        "categoria": credito.get("categoria", ""),
        "unidad": credito.get("unidad") or None,
        "partida": credito.get("partida", ""),
        "fuente": credito.get("fuente", ""),
        "firmante_cargo": firmante.get("cargo", ""),
        "firmante_unidad": firmante.get("unidad", ""),
        "firmante_funcionario": firmante.get("funcionario") or None,
        "emitida_por": username_emitida or "",
        "huella": c.huella,
        "documento_nombre": c.documento_nombre,
        "documento_sha256": c.documento_sha256,
        "anulada_en": c.anulada_en,
        "anulada_por": username_anulada,
        "motivo_anulacion": c.motivo_anulacion,
    }


def _salida_con_usuarios(db: Session, c: GovernmentBudgetCertificate, tenant_id: str) -> dict[str, Any]:
    ids: list[str] = []
    if c.emitida_por:
        ids.append(c.emitida_por)
    if c.anulada_por:
        ids.append(c.anulada_por)
    usuarios = _usuarios_por_ids(db, ids, tenant_id) if ids else {}
    return _salida(c, usuarios.get(c.emitida_por) if c.emitida_por else None, usuarios.get(c.anulada_por) if c.anulada_por else None)


def disponibilidad(db: Session, ctx: CompanyContext, year_id: str, filtros: dict[str, str | None]) -> dict[str, Any]:
    ejercicio = _ejercicio_de_empresa(db, ctx, year_id)
    creditos = db.execute(
        select(GovernmentBudgetCredit).where(
            GovernmentBudgetCredit.year_id == ejercicio.id,
            GovernmentBudgetCredit.company_id == ctx.company_id,
        )
    ).scalars().all()

    vigentes = _vigentes_por_credito(db, str(ejercicio.id))

    categorias = {str(c.id): c for c in db.execute(select(GovernmentBudgetCategory).where(GovernmentBudgetCategory.id.in_([cr.category_id for cr in creditos]))).scalars().all()}
    items = {str(i.id): i for i in db.execute(select(GovernmentBudgetClassifierItem).where(GovernmentBudgetClassifierItem.id.in_([cr.item_id for cr in creditos]))).scalars().all()}
    fuentes = {str(f.id): f for f in db.execute(select(GovernmentBudgetFundingSource).where(GovernmentBudgetFundingSource.id.in_([cr.source_id for cr in creditos]))).scalars().all()}
    unidades: dict[Any, GovernmentUnit] = {}
    unit_ids = [categorias[str(cr.category_id)].unit_id for cr in creditos if str(cr.category_id) in categorias and categorias[str(cr.category_id)].unit_id]
    if unit_ids:
        unidades = {str(u.id): u for u in db.execute(select(GovernmentUnit).where(GovernmentUnit.id.in_(unit_ids))).scalars().all()}

    crudos: list[dict[str, Any]] = []
    for cr in creditos:
        categoria = categorias.get(str(cr.category_id))
        unidad = unidades.get(str(categoria.unit_id)) if categoria and categoria.unit_id else None
        partida = items.get(str(cr.item_id))
        fuente = fuentes.get(str(cr.source_id))
        certificado = vigentes.get(str(cr.id), Decimal("0.00"))
        disponible = cr.monto - certificado
        crudos.append(
            {
                "credito_id": str(cr.id),
                "categoria": {"id": str(categoria.id), "etiqueta": _etiqueta(categoria.codigo_completo, categoria.denominacion)} if categoria else None,
                "unidad": {"id": str(unidad.id), "etiqueta": _etiqueta(unidad.code, unidad.name)} if unidad else None,
                "partida": {"id": str(partida.id), "etiqueta": _etiqueta(partida.codigo, partida.denominacion)} if partida else None,
                "fuente": {"id": str(fuente.id), "etiqueta": _etiqueta(fuente.codigo, fuente.denominacion)} if fuente else None,
                "credito": cr.monto,
                "certificado": certificado,
                "disponible": disponible,
            }
        )

    filtrados = []
    for item in crudos:
        if filtros.get("categoria_id") and (not item["categoria"] or item["categoria"]["id"] != filtros["categoria_id"]):
            continue
        if filtros.get("unidad_id") and (not item["unidad"] or item["unidad"]["id"] != filtros["unidad_id"]):
            continue
        if filtros.get("partida_id") and (not item["partida"] or item["partida"]["id"] != filtros["partida_id"]):
            continue
        if filtros.get("fuente_id") and (not item["fuente"] or item["fuente"]["id"] != filtros["fuente_id"]):
            continue
        filtrados.append(item)

    filtrados.sort(
        key=lambda x: (
            x["categoria"]["etiqueta"] if x["categoria"] else "",
            x["partida"]["etiqueta"] if x["partida"] else "",
            x["fuente"]["etiqueta"] if x["fuente"] else "",
        )
    )

    totales = {
        "credito": sum((item["credito"] for item in filtrados), Decimal("0.00")),
        "certificado": sum((item["certificado"] for item in filtrados), Decimal("0.00")),
        "disponible": sum((item["disponible"] for item in filtrados), Decimal("0.00")),
    }

    hoy = hoy_de_negocio()
    estructura = db.execute(
        select(GovernmentStructure).where(
            GovernmentStructure.company_id == ctx.company_id,
            GovernmentStructure.exercise == hoy.year,
        )
    ).scalar_one_or_none()
    firmantes: list[dict[str, Any]] = []
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
            if any(c["accion"] == "FIRMAR" and c["materia"] == "PRESUPUESTO" for c in competencias):
                unidad = db.get(GovernmentUnit, cargo.unit_id) if cargo.unit_id else None
                firmantes.append(
                    {
                        "cargo_id": str(cargo.id),
                        "etiqueta": _etiqueta(cargo.code, cargo.name),
                        "unidad": _etiqueta(unidad.code, unidad.name) if unidad else "",
                    }
                )
    firmantes.sort(key=lambda x: x["etiqueta"])

    expedientes = db.execute(
        select(GovernmentProcurementFile)
        .where(GovernmentProcurementFile.company_id == ctx.company_id)
        .order_by(GovernmentProcurementFile.numero.desc())
        .limit(200)
    ).scalars().all()

    return {
        "anio": ejercicio.anio,
        "estado": ejercicio.estado,
        "moneda": ejercicio.moneda_funcional,
        "certificable": ejercicio.estado in ("APROBADO", "RECONDUCIDO") and hoy.year == ejercicio.anio,
        "items": filtrados,
        "totales": totales,
        "filtros": {
            "categorias": _refs_unicas(crudos, "categoria"),
            "unidades": _refs_unicas(crudos, "unidad"),
            "partidas": _refs_unicas(crudos, "partida"),
            "fuentes": _refs_unicas(crudos, "fuente"),
        },
        "firmantes": firmantes,
        "expedientes": [
            {"id": str(e.id), "etiqueta": f"{e.numero} · {(e.objeto or '')[:80]}"}
            for e in expedientes
        ],
    }


def listar(db: Session, ctx: CompanyContext, year_id: str) -> dict[str, Any]:
    ejercicio = _ejercicio_de_empresa(db, ctx, year_id)
    certificaciones = db.execute(
        select(GovernmentBudgetCertificate)
        .where(
            GovernmentBudgetCertificate.year_id == ejercicio.id,
            GovernmentBudgetCertificate.company_id == ctx.company_id,
        )
        .order_by(GovernmentBudgetCertificate.numero.desc())
    ).scalars().all()
    return {"items": [_salida_con_usuarios(db, c, ctx.tenant_id) for c in certificaciones]}


def detalle(db: Session, ctx: CompanyContext, year_id: str, certificacion_id: str) -> dict[str, Any]:
    ejercicio = _ejercicio_de_empresa(db, ctx, year_id)
    c = db.execute(
        select(GovernmentBudgetCertificate).where(
            GovernmentBudgetCertificate.id == certificacion_id,
            GovernmentBudgetCertificate.year_id == ejercicio.id,
            GovernmentBudgetCertificate.company_id == ctx.company_id,
        )
    ).scalar_one_or_none()
    if not c:
        raise NotFoundError("GOV_BUDGET_CERTIFICATE_NOT_FOUND", "La certificación no existe en este ejercicio")
    return _salida_con_usuarios(db, c, ctx.tenant_id)


def _decimal_finito(valor: Any) -> Decimal | None:
    if isinstance(valor, Decimal):
        return valor if valor.is_finite() else None
    return None


def emitir(db: Session, ctx: CompanyContext, user: User, year_id: str, cuerpo: dict[str, Any]) -> dict[str, Any]:
    ejercicio = _ejercicio_de_empresa(db, ctx, year_id, bloquear=True)
    if ejercicio.estado not in ("APROBADO", "RECONDUCIDO"):
        raise _estado_invalido()

    hoy = hoy_de_negocio()
    if hoy.year != ejercicio.anio:
        raise _invalida("Solo se certifica dentro del año del ejercicio (LOPPM art. 250)", "fecha")

    credito = db.execute(
        select(GovernmentBudgetCredit)
        .where(
            GovernmentBudgetCredit.id == cuerpo.get("credito_id"),
            GovernmentBudgetCredit.year_id == ejercicio.id,
            GovernmentBudgetCredit.company_id == ctx.company_id,
        )
        .with_for_update()
    ).scalar_one_or_none()
    if not credito:
        raise NotFoundError("GOV_BUDGET_CREDIT_NOT_FOUND", "El crédito no existe en este ejercicio")

    monto = _decimal_finito(cuerpo.get("monto"))
    if monto is None:
        raise _invalida("El monto debe ser mayor que cero y tener como máximo 2 decimales", "monto")
    exponente = monto.as_tuple().exponent
    if (
        monto <= 0
        or (not isinstance(exponente, int) or exponente < -2)
        or monto >= Decimal("10000000000000000")
    ):
        raise _invalida("El monto debe ser mayor que cero y tener como máximo 2 decimales", "monto")

    concepto = (cuerpo.get("concepto") or "").strip()
    if len(concepto) < 10 or len(concepto) > 500:
        raise _invalida("El concepto debe tener entre 10 y 500 caracteres", "concepto")

    expediente_id = cuerpo.get("expediente_id")
    referencia = ""
    if expediente_id:
        expediente = db.execute(
            select(GovernmentProcurementFile).where(
                GovernmentProcurementFile.id == expediente_id,
                GovernmentProcurementFile.company_id == ctx.company_id,
            )
        ).scalar_one_or_none()
        if not expediente:
            raise _invalida("El expediente no existe en este ente", "expediente_id")
        referencia = expediente.numero
    else:
        referencia = (cuerpo.get("expediente_referencia") or "").strip()
        if len(referencia) < 3 or len(referencia) > 120:
            raise _invalida(
                "Indique el expediente: elija uno de contratación o escriba su referencia institucional",
                "expediente_referencia",
            )

    cargo_id = str(cuerpo.get("firmante_cargo_id") or "")
    cargo = db.execute(
        select(GovernmentPosition).where(
            GovernmentPosition.id == cargo_id,
            GovernmentPosition.company_id == ctx.company_id,
        )
    ).scalar_one_or_none()
    if not cargo or not _autoridad_valida(db, ctx.company_id, cargo_id, hoy, "FIRMAR", "PRESUPUESTO"):
        mensaje = "El cargo no tiene hoy la competencia FIRMAR en materia de PRESUPUESTO"
        raise KontrolError(
            code="GOV_BUDGET_CERTIFICATE_SIGNER_INVALID",
            message=mensaje,
            field_errors={"firmante_cargo_id": [mensaje]},
            status_code=422,
        )
    exigir_autoridad_funcional(db, ctx, str(cargo.id), "FIRMAR", "PRESUPUESTO")

    disponible = disponible_de_credito(db, credito)
    if monto > disponible:
        mensaje = f"Disponibilidad insuficiente: disponible {disponible}, solicitado {monto}"
        raise KontrolError(
            code="GOV_BUDGET_INSUFFICIENT_AVAILABILITY",
            message=mensaje,
            details={"disponible": str(disponible), "solicitado": str(monto)},
            field_errors={"monto": [mensaje]},
            status_code=422,
        )

    max_numero = db.execute(
        select(func.max(GovernmentBudgetCertificate.numero)).where(
            GovernmentBudgetCertificate.year_id == ejercicio.id
        )
    ).scalar_one_or_none()
    numero = (max_numero or 0) + 1
    codigo = f"CDP-{ejercicio.anio}-{numero:04d}"

    categoria = db.get(GovernmentBudgetCategory, credito.category_id)
    partida = db.get(GovernmentBudgetClassifierItem, credito.item_id)
    fuente = db.get(GovernmentBudgetFundingSource, credito.source_id)
    unidad_credito = db.get(GovernmentUnit, categoria.unit_id) if categoria and categoria.unit_id else None

    unidad_firmante = db.get(GovernmentUnit, cargo.unit_id) if cargo.unit_id else None
    etiqueta_unidad_firmante = _etiqueta(unidad_firmante.code, unidad_firmante.name) if unidad_firmante else ""

    official_id = _funcionario_del_actor(db, ctx)
    funcionario_nombre = ""
    if official_id:
        funcionario = db.get(GovernmentOfficial, official_id)
        if funcionario:
            funcionario_nombre = funcionario.nombre

    ente = (db.get(Company, ctx.company_id) or Company()).legal_name or ""

    saldo_antes = disponible
    saldo_despues = disponible - monto

    snapshot: dict[str, Any] = {
        "codigo": codigo,
        "ente": ente,
        "anio": ejercicio.anio,
        "moneda": ejercicio.moneda_funcional or "",
        "fecha": hoy.isoformat(),
        "concepto": concepto,
        "monto": str(monto),
        "saldo_antes": str(saldo_antes),
        "saldo_despues": str(saldo_despues),
        "expediente": {"id": expediente_id, "referencia": referencia},
        "credito": {
            "id": credito.id,
            "categoria": _etiqueta(categoria.codigo_completo, categoria.denominacion) if categoria else "",
            "unidad": _etiqueta(unidad_credito.code, unidad_credito.name) if unidad_credito else "",
            "partida": _etiqueta(partida.codigo, partida.denominacion) if partida else "",
            "fuente": _etiqueta(fuente.codigo, fuente.denominacion) if fuente else "",
            "aprobado": str(credito.monto),
        },
        "firmante": {
            "cargo_id": cargo.id,
            "cargo": _etiqueta(cargo.code, cargo.name),
            "unidad": etiqueta_unidad_firmante,
            "funcionario_id": official_id,
            "funcionario": funcionario_nombre,
            "usuario_id": str(user.id),
        },
    }
    huella = hashlib.sha256(
        json.dumps(snapshot, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    emitida_en = instante_actual()
    pdf = _render_pdf(snapshot, huella, emitida_en)

    storage = get_storage()
    storage_key = generate_storage_key(ctx.company_id)
    size, sha = storage.put(storage_key, io.BytesIO(pdf))
    if sha != hashlib.sha256(pdf).hexdigest() or size != len(pdf):
        storage.delete(storage_key)
        raise KontrolError(
            code="STORAGE_HASH_MISMATCH",
            message="El reporte almacenado no coincide con su huella",
            status_code=500,
        )
    if not storage.verify(storage_key, sha):
        storage.delete(storage_key)
        raise KontrolError(
            code="STORAGE_HASH_MISMATCH",
            message="El reporte almacenado no coincide con su huella",
            status_code=500,
        )

    documento_nombre = f"certificacion-{codigo}.pdf"

    cargo_nombre = cargo.name or ""
    certificacion = GovernmentBudgetCertificate(
        credit_id=credito.id,
        year_id=ejercicio.id,
        company_id=ctx.company_id,
        numero=numero,
        codigo=codigo,
        estado="VIGENTE",
        monto=monto,
        saldo_antes=saldo_antes,
        saldo_despues=saldo_despues,
        moneda=ejercicio.moneda_funcional or "",
        fecha=hoy,
        concepto=concepto,
        expediente_referencia=referencia,
        procurement_file_id=expediente_id,
        firmante_cargo_id=cargo.id,
        firmante_cargo_codigo=cargo.code,
        firmante_cargo_nombre=cargo_nombre,
        firmante_unidad=etiqueta_unidad_firmante,
        firmante_funcionario_id=official_id,
        firmante_funcionario_nombre=funcionario_nombre,
        emitida_por=str(user.id),
        emitida_en=emitida_en,
        snapshot=snapshot,
        huella=huella,
        documento_storage_key=storage_key,
        documento_sha256=sha,
        documento_tamano=size,
        documento_nombre=documento_nombre,
        created_by=ctx.user_id,
    )
    db.add(certificacion)
    db.flush()

    credito_etiqueta = f"{snapshot['credito']['categoria']} | {snapshot['credito']['partida']} | {snapshot['credito']['fuente']}"
    _historia(
        db,
        ctx,
        ejercicio,
        "CERTIFICACION_EMITIDA",
        {
            "codigo": codigo,
            "monto": str(monto),
            "credito": credito_etiqueta,
        },
    )
    _auditar(
        db,
        ctx,
        ejercicio,
        "GOV_BUDGET_CERTIFICATE_ISSUED",
        {
            "anio": ejercicio.anio,
            "codigo": codigo,
            "credito": credito_etiqueta,
            "expediente": referencia,
            "firmante_cargo": _etiqueta(cargo.code, cargo_nombre),
            "monto": str(monto),
            "saldo_antes": str(saldo_antes),
            "saldo_despues": str(saldo_despues),
        },
    )
    db.flush()
    return _salida_con_usuarios(db, certificacion, ctx.tenant_id)


def anular(db: Session, ctx: CompanyContext, user: User, year_id: str, certificacion_id: str, cuerpo: dict[str, Any]) -> dict[str, Any]:
    ejercicio = _ejercicio_de_empresa(db, ctx, year_id, bloquear=True)
    if ejercicio.estado not in ("APROBADO", "RECONDUCIDO"):
        raise _estado_invalido()

    c = db.execute(
        select(GovernmentBudgetCertificate)
        .where(
            GovernmentBudgetCertificate.id == certificacion_id,
            GovernmentBudgetCertificate.year_id == ejercicio.id,
            GovernmentBudgetCertificate.company_id == ctx.company_id,
        )
        .with_for_update()
    ).scalar_one_or_none()
    if not c:
        raise NotFoundError("GOV_BUDGET_CERTIFICATE_NOT_FOUND", "La certificación no existe en este ejercicio")

    if c.estado != "VIGENTE":
        raise ConflictError("GOV_BUDGET_CERTIFICATE_NOT_ACTIVE", "La certificación ya está anulada")

    motivo = (cuerpo.get("motivo") or "").strip()
    if len(motivo) < 10 or len(motivo) > 500:
        raise _invalida("El motivo debe tener entre 10 y 500 caracteres", "motivo")

    c.estado = "ANULADA"
    c.anulada_por = str(user.id)
    c.anulada_en = instante_actual()
    c.motivo_anulacion = motivo
    db.flush()

    _historia(db, ctx, ejercicio, "CERTIFICACION_ANULADA", {"codigo": c.codigo, "monto": str(c.monto), "motivo": motivo})
    _auditar(
        db,
        ctx,
        ejercicio,
        "GOV_BUDGET_CERTIFICATE_ANNULLED",
        {"anio": ejercicio.anio, "codigo": c.codigo, "monto": str(c.monto), "motivo": motivo},
    )
    db.flush()
    return _salida_con_usuarios(db, c, ctx.tenant_id)


def abrir_documento(db: Session, ctx: CompanyContext, year_id: str, certificacion_id: str) -> tuple[str, BinaryIO, int]:
    ejercicio = _ejercicio_de_empresa(db, ctx, year_id)
    c = db.execute(
        select(GovernmentBudgetCertificate).where(
            GovernmentBudgetCertificate.id == certificacion_id,
            GovernmentBudgetCertificate.year_id == ejercicio.id,
            GovernmentBudgetCertificate.company_id == ctx.company_id,
        )
    ).scalar_one_or_none()
    if not c:
        raise NotFoundError("GOV_BUDGET_CERTIFICATE_NOT_FOUND", "La certificación no existe en este ejercicio")

    storage = get_storage()
    if not storage.verify(c.documento_storage_key, c.documento_sha256):
        raise KontrolError(
            code="STORAGE_HASH_MISMATCH",
            message="El documento almacenado no coincide con su huella",
            status_code=500,
        )
    return (c.documento_nombre or "", storage.open(c.documento_storage_key), c.documento_tamano or 0)
