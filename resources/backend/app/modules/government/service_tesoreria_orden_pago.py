"""Servicio de la orden de pago (TRE-03, GOV-TRE-003).

Implementa el ciclo de vida de la orden de pago sobre los modelos de C1 y la
proyección neutral de C2a. No hay pagos, cuentas bancarias, retenciones ni
asiento contable.
"""

from __future__ import annotations

import csv
import io
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext
from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.core.integrity import es_violacion_unica
from app.modules.documents.models import Document, DocumentLink, DocumentType, DocumentVersion
from app.modules.government.models import (
    GovernmentBudgetCause,
    GovernmentBudgetCauseEvidence,
    GovernmentBudgetCausingPolicy,
    GovernmentBudgetCommitment,
    GovernmentBudgetYear,
    GovernmentOfficial,
    GovernmentPaymentOrder,
    GovernmentPaymentOrderDocument,
    GovernmentPaymentOrderHistory,
    GovernmentPaymentOrderLine,
    GovernmentPaymentOrderPolicy,
    GovernmentPaymentOrderPolicyDocument,
    GovernmentPosition,
)
from app.modules.government.monedas import canonical_currency
from app.modules.government.proyeccion_obligaciones import montos_ordenados, montos_pagados, pendiente_de_ordenar
from app.modules.government.service_actos import _autoridad_valida
from app.modules.government.service_autoridad import competencias_en_vigor
from app.modules.government.service_identidad import _funcionario_del_actor, exigir_autoridad_funcional
from app.modules.government.service_presupuesto_causado import (
    _control,
    _ejercicio_de_empresa,
    _estado_invalido,
    _etiqueta_documento,
    _invalida,
    _sha256,
    _unidad_nombre,
    _username,
)
from app.modules.government.service_sod import evaluar_antes_de_actuar
from app.modules.government.service_tasas import verificar_limite
from app.modules.government.service_tesoreria_orden_pago_politicas import (
    politica_de_empresa,
    politica_vigente_en,
    siguiente_codigo,
)
from app.shared.audit import record_audit
from app.shared.clock import hoy_de_negocio, instante_actual


def _orden_por_id(db: Session, ctx: CompanyContext, order_id: str, bloquear: bool = False) -> GovernmentPaymentOrder:
    consulta = select(GovernmentPaymentOrder).where(
        GovernmentPaymentOrder.company_id == ctx.company_id,
        GovernmentPaymentOrder.id == order_id,
    )
    if bloquear:
        consulta = consulta.with_for_update()
    orden = db.scalar(consulta)
    if orden is None:
        raise NotFoundError("GOV_PAYMENT_ORDER_NOT_FOUND", "Orden de pago no encontrada")
    return orden


def _lineas_orden(db: Session, order_id: str) -> list[GovernmentPaymentOrderLine]:
    return list(
        db.scalars(
            select(GovernmentPaymentOrderLine)
            .where(GovernmentPaymentOrderLine.order_id == order_id)
            .order_by(GovernmentPaymentOrderLine.cause_id)
        )
    )


def _documentos_orden(db: Session, order_id: str) -> list[GovernmentPaymentOrderDocument]:
    return list(
        db.scalars(
            select(GovernmentPaymentOrderDocument)
            .where(GovernmentPaymentOrderDocument.order_id == order_id)
            .order_by(GovernmentPaymentOrderDocument.document_id)
        )
    )


def _historia_orden(db: Session, order_id: str) -> list[dict[str, Any]]:
    historia: list[dict[str, Any]] = []
    for item in db.scalars(
        select(GovernmentPaymentOrderHistory)
        .where(GovernmentPaymentOrderHistory.order_id == order_id)
        .order_by(GovernmentPaymentOrderHistory.created_at.desc())
    ):
        historia.append(
            {
                "evento": item.evento,
                "fecha": item.created_at.isoformat(),
                "actor": _username(db, item.actor_id),
            }
        )
    return historia


def _politica_causado(db: Session, causa: GovernmentBudgetCause) -> GovernmentBudgetCausingPolicy | None:
    return db.get(GovernmentBudgetCausingPolicy, causa.policy_id)


def _validar_compatibilidad_lineas(
    db: Session,
    causados: list[GovernmentBudgetCause],
    politica: GovernmentPaymentOrderPolicy,
) -> None:
    monedas = {canonical_currency(c.moneda) for c in causados}
    beneficiarios = {c.beneficiario.strip() for c in causados if c.beneficiario and c.beneficiario.strip()}
    motivos: list[str] = []
    if len(monedas) > 1:
        motivos.append("Las líneas tienen monedas distintas")
    if len(beneficiarios) > 1:
        motivos.append("Las líneas tienen beneficiarios distintos")
    if politica.tipo_gasto:
        tipos: set[str | None] = set()
        for causa in causados:
            politica_causado = _politica_causado(db, causa)
            tipos.add(politica_causado.tipo_gasto if politica_causado else None)
        if len(tipos) > 1:
            motivos.append("Las líneas provienen de causados con tipo de gasto distinto al de la política")
    if motivos:
        raise KontrolError(
            code="GOV_PAYMENT_ORDER_INCOMPATIBLE",
            message="Las líneas de la orden no son compatibles",
            field_errors={"lineas": motivos},
            status_code=422,
        )


def _beneficiario_comun(causados: list[GovernmentBudgetCause]) -> str | None:
    valores = {c.beneficiario.strip() for c in causados if c.beneficiario and c.beneficiario.strip()}
    return next(iter(valores), None) if len(valores) == 1 else None


def _validar_documentos_orden(
    db: Session,
    ctx: CompanyContext,
    year_id: str,
    causados: list[GovernmentBudgetCause],
    document_ids: list[str],
) -> list[dict[str, Any]]:
    resultado: list[dict[str, Any]] = []
    vistos: set[str] = set()
    ids_causados = [str(c.id) for c in causados]
    evidencias_documento = {
        str(e.resource_id)
        for e in db.scalars(
            select(GovernmentBudgetCauseEvidence).where(
                GovernmentBudgetCauseEvidence.company_id == ctx.company_id,
                GovernmentBudgetCauseEvidence.cause_id.in_(ids_causados),
                GovernmentBudgetCauseEvidence.resource_type == "DOCUMENT",
            )
        )
    }
    for document_id in document_ids:
        if document_id in vistos:
            continue
        vistos.add(document_id)
        documento_candidato = db.scalar(
            select(Document).where(
                Document.company_id == ctx.company_id,
                Document.id == document_id,
                Document.status == "ACTIVE",
            )
        )
        documento = documento_candidato
        version_actual = None
        if documento is not None and documento.current_version_id is not None:
            version_actual = db.get(DocumentVersion, documento.current_version_id)
        if documento is None or version_actual is None or version_actual.sha256 is None:
            raise KontrolError(
                code="GOV_PAYMENT_ORDER_DOCUMENT_INVALID",
                message="Documento inválido para la orden de pago",
                field_errors={"documentos": [f"El documento {document_id} no tiene versión vigente con huella"]},
                status_code=422,
            )
        vinculo_ejercicio = db.scalar(
            select(DocumentLink).where(
                DocumentLink.document_id == document_id,
                DocumentLink.resource_type == "GovernmentBudgetYear",
                DocumentLink.resource_id == year_id,
                DocumentLink.company_id == ctx.company_id,
            )
        )
        if vinculo_ejercicio is None and document_id not in evidencias_documento:
            raise KontrolError(
                code="GOV_PAYMENT_ORDER_DOCUMENT_INVALID",
                message="Documento inválido para la orden de pago",
                field_errors={"documentos": [f"El documento {document_id} no está vinculado al ejercicio ni es evidencia de los causados"]},
                status_code=422,
            )
        resultado.append(
            {
                "document_id": document_id,
                "document_type_id": documento.document_type_id,
                "document_version_id": str(version_actual.id),
                "sha256": version_actual.sha256,
                "snapshot": {
                    "titulo": documento.title,
                    "tipo": _etiqueta_documento(db, documento.document_type_id),
                    "sha256": version_actual.sha256,
                    "version": version_actual.version_number,
                },
            }
        )
    return resultado


def _validar_fecha_orden(
    db: Session,
    ctx: CompanyContext,
    year: GovernmentBudgetYear,
    causados: list[GovernmentBudgetCause],
    fecha_orden: date,
) -> None:
    motivos: list[str] = []
    maxima = max((c.fecha_efectiva for c in causados), default=None)
    if maxima is not None and fecha_orden < maxima:
        motivos.append(f"La fecha de la orden no puede ser anterior a la fecha efectiva del causado {maxima.isoformat()}")
    if fecha_orden.year != year.anio:
        motivos.append(f"La fecha de la orden debe pertenecer al ejercicio {year.anio}")
    hoy = hoy_de_negocio()
    if fecha_orden > hoy:
        motivos.append("La fecha de la orden no puede ser posterior a hoy")
    if motivos:
        raise KontrolError(
            code="GOV_PAYMENT_ORDER_DATE_INVALID",
            message="La fecha de la orden no es válida",
            field_errors={"fecha_orden": motivos},
            status_code=422,
        )


def _causado_elegible(
    db: Session,
    ctx: CompanyContext,
    year_id: str,
    cause_id: str,
    bloquear: bool = False,
) -> GovernmentBudgetCause:
    consulta = select(GovernmentBudgetCause).where(
        GovernmentBudgetCause.company_id == ctx.company_id,
        GovernmentBudgetCause.year_id == year_id,
        GovernmentBudgetCause.id == cause_id,
    )
    if bloquear:
        consulta = consulta.with_for_update()
    causa = db.scalar(consulta)
    if causa is None:
        raise NotFoundError("GOV_PAYMENT_ORDER_CAUSE_NOT_FOUND", "Causado no encontrado para el ejercicio")
    if causa.estado != "FORMALIZADO":
        raise KontrolError(
            code="GOV_PAYMENT_ORDER_CAUSE_NOT_ELIGIBLE",
            message="El causado no está formalizado y no puede ordenarse",
            field_errors={"lineas": ["Causado no elegible"]},
            status_code=422,
        )
    return causa


def _montos_en_borrador(
    db: Session,
    ctx: CompanyContext,
    year_id: str,
    lineas: list[dict[str, Any]],
) -> tuple[list[GovernmentBudgetCause], Decimal, str | None]:
    if not lineas:
        raise _invalida("La orden debe tener al menos una línea")
    ids = [linea["cause_id"] for linea in lineas]
    if len(set(ids)) != len(ids):
        raise KontrolError(
            code="GOV_PAYMENT_ORDER_DUPLICATE_CAUSE",
            message="El causado está repetido en las líneas",
            field_errors={"lineas": ["Causado repetido"]},
            status_code=422,
        )
    causados = [_causado_elegible(db, ctx, year_id, linea["cause_id"]) for linea in lineas]
    ordenado = montos_ordenados(db, ctx.company_id, ids)
    monto_total = Decimal("0.00")
    for linea_entrada, causa in zip(lineas, causados, strict=True):
        pendiente = pendiente_de_ordenar(causa.monto, ordenado[str(causa.id)])
        if linea_entrada["monto"] > pendiente:
            raise KontrolError(
                code="GOV_PAYMENT_ORDER_OVER_ORDER",
                message=f"El monto de la línea del causado {causa.codigo} supera el pendiente de ordenar",
                field_errors={"lineas": [f"Pendiente de {causa.codigo}: {pendiente}"]},
                status_code=422,
            )
        monto_total += linea_entrada["monto"]
    return causados, monto_total, _beneficiario_comun(causados)


def _validar_lineas_y_calcular(
    db: Session,
    ctx: CompanyContext,
    year_id: str,
    cuerpo: dict[str, Any],
) -> tuple[list[GovernmentBudgetCause], Decimal, str | None]:
    if "lineas" in cuerpo:
        lineas_raw = cuerpo.get("lineas", [])
        lineas = [
            {"cause_id": str(linea["cause_id"]), "monto": linea["monto"]}
            for linea in lineas_raw
        ]
        causados, monto, beneficiario = _montos_en_borrador(db, ctx, year_id, lineas)
        return causados, monto, beneficiario
    raise _invalida("La orden debe tener al menos una línea")


def _causados_de_lineas(
    db: Session,
    ctx: CompanyContext,
    year_id: str,
    cause_ids: list[str],
    bloquear: bool = False,
) -> list[GovernmentBudgetCause]:
    if bloquear:
        consulta = select(GovernmentBudgetCause).where(
            GovernmentBudgetCause.company_id == ctx.company_id,
            GovernmentBudgetCause.year_id == year_id,
            GovernmentBudgetCause.id.in_(cause_ids),
        ).order_by(GovernmentBudgetCause.id).with_for_update()
        causados = list(db.scalars(consulta))
    else:
        causados = [_causado_elegible(db, ctx, year_id, cause_id) for cause_id in cause_ids]
    if len(causados) != len(cause_ids):
        raise NotFoundError("GOV_PAYMENT_ORDER_CAUSE_NOT_FOUND", "Uno o más causados no existen")
    for causa in causados:
        if causa.estado != "FORMALIZADO":
            raise KontrolError(
                code="GOV_PAYMENT_ORDER_CAUSE_NOT_ELIGIBLE",
                message="Uno o más causados no están formalizados",
                field_errors={"lineas": ["Causado no elegible"]},
                status_code=422,
            )
    return causados


def _lineas_a_dict(
    db: Session,
    ctx: CompanyContext,
    lineas: list[GovernmentPaymentOrderLine],
) -> list[dict[str, Any]]:
    resultado: list[dict[str, Any]] = []
    ids = [str(linea.cause_id) for linea in lineas]
    montos = montos_ordenados(db, ctx.company_id, ids)
    for linea in lineas:
        causa = db.get(GovernmentBudgetCause, linea.cause_id)
        compromiso = db.get(GovernmentBudgetCommitment, causa.commitment_id) if causa else None
        causa_dict: dict[str, Any] = {
            "cause_id": str(linea.cause_id),
            "codigo": causa.codigo if causa else "",
            "compromiso_codigo": compromiso.codigo if compromiso else "",
            "beneficiario": causa.beneficiario if causa else None,
            "fecha_efectiva": causa.fecha_efectiva.isoformat() if causa else None,
            "monto_causado": str(causa.monto) if causa else "0.00",
            "monto_ordenado": str(montos[str(linea.cause_id)]),
            "pendiente_de_ordenar": str(pendiente_de_ordenar(causa.monto, montos[str(linea.cause_id)])) if causa else "0.00",
            "monto_asignado": str(linea.monto),
        }
        resultado.append(causa_dict)
    return resultado


def _documentos_a_dict(db: Session, order_id: str) -> list[dict[str, Any]]:
    resultado: list[dict[str, Any]] = []
    for doc in _documentos_orden(db, order_id):
        documento = db.get(Document, doc.document_id)
        snapshot = doc.snapshot or {}
        resultado.append(
            {
                "document_id": str(doc.document_id),
                "titulo": snapshot.get("titulo") or (documento.title if documento else ""),
                "tipo": snapshot.get("tipo") or (doc.document_type_id or ""),
                "sha256": doc.sha256 or snapshot.get("sha256") or "",
            }
        )
    return resultado


def _autoridad_a_dict(db: Session, orden: GovernmentPaymentOrder) -> dict[str, Any] | None:
    if not orden.autoridad_cargo_id:
        return None
    cargo = db.get(GovernmentPosition, orden.autoridad_cargo_id)
    return {
        "cargo_id": str(orden.autoridad_cargo_id),
        "cargo": orden.autoridad_cargo_nombre or (cargo.name if cargo else None),
        "unidad": orden.autoridad_unidad or (_unidad_nombre(db, cargo.unit_id) if cargo else None),
        "funcionario_id": orden.autoridad_funcionario_id,
        "funcionario": orden.autoridad_funcionario_nombre,
        "usuario_id": orden.emitida_por,
    }


def _orden_a_dict(
    db: Session,
    ctx: CompanyContext,
    orden: GovernmentPaymentOrder,
    incluir_controles: bool = False,
) -> dict[str, Any]:
    year = _ejercicio_de_empresa(db, ctx, orden.year_id)
    politica = politica_de_empresa(db, ctx, orden.policy_id)
    lineas = _lineas_orden(db, str(orden.id))
    pagados = montos_pagados(db, ctx.company_id, [str(orden.id)])
    total_pagado = pagados.get(str(orden.id), Decimal("0.00"))
    pendiente_pago = max(orden.monto - total_pagado, Decimal("0.00"))
    resultado: dict[str, Any] = {
        "id": str(orden.id),
        "codigo": orden.codigo,
        "numero": orden.numero,
        "estado": orden.estado,
        "year_id": orden.year_id,
        "anio": year.anio,
        "fecha_orden": orden.fecha_orden,
        "concepto": orden.concepto,
        "moneda": orden.moneda,
        "monto": f"{orden.monto:.2f}",
        "beneficiario": orden.beneficiario,
        "policy": {
            "id": str(politica.id),
            "codigo": politica.codigo,
            "nombre": politica.nombre,
            "version": orden.policy_version,
        },
        "lineas": _lineas_a_dict(db, ctx, lineas),
        "documentos": _documentos_a_dict(db, str(orden.id)),
        "autoridad": _autoridad_a_dict(db, orden),
        "emitida_en": orden.emitida_en,
        "emitida_por": _username(db, orden.emitida_por) if orden.emitida_por else None,
        "anulada_en": orden.anulada_en,
        "motivo_anulacion": orden.motivo_anulacion,
        "huella": orden.huella,
        "version": orden.version,
        "monto_pagado": f"{total_pagado:.2f}",
        "pendiente_de_pagar": f"{pendiente_pago:.2f}",
        "siguiente_paso": "Pago (TRE-04)" if orden.estado == "EMITIDA" else None,
        "historia": _historia_orden(db, str(orden.id)),
    }
    if incluir_controles and orden.estado == "BORRADOR":
        resultado["controles"] = _controles_orden(db, ctx, orden)
    return resultado


def _politica_en_fecha_orden(
    db: Session,
    ctx: CompanyContext,
    orden: GovernmentPaymentOrder,
) -> GovernmentPaymentOrderPolicy:
    politica = politica_de_empresa(db, ctx, orden.policy_id)
    if not politica_vigente_en(politica, orden.fecha_orden):
        raise KontrolError(
            code="GOV_PAYMENT_ORDER_POLICY_NOT_IN_FORCE",
            message="La política de orden de pago no está vigente en la fecha de la orden",
            field_errors={"policy_id": ["Política no vigente en la fecha de la orden"]},
            status_code=422,
        )
    return politica


def _controles_orden(
    db: Session,
    ctx: CompanyContext,
    orden: GovernmentPaymentOrder,
) -> dict[str, Any]:
    controles: list[dict[str, Any]] = []
    year = _ejercicio_de_empresa(db, ctx, orden.year_id)
    politica = politica_de_empresa(db, ctx, orden.policy_id)
    lineas = _lineas_orden(db, str(orden.id))
    ids = [str(linea.cause_id) for linea in lineas]
    causados = _causados_de_lineas(db, ctx, orden.year_id, ids)
    ordenado = montos_ordenados(db, ctx.company_id, ids)

    controls_politica = politica_vigente_en(politica, orden.fecha_orden)
    controles.append(
        _control(
            "POLITICA",
            controls_politica,
            "La política no está vigente en la fecha de la orden" if not controls_politica else "Política vigente",
        )
    )

    monedas = {canonical_currency(c.moneda) for c in causados}
    beneficiarios = {c.beneficiario.strip() for c in causados if c.beneficiario and c.beneficiario.strip()}
    cumple_compatibilidad = len(monedas) == 1 and len(beneficiarios) <= 1
    tipos_gasto: set[str | None] = set()
    for causa in causados:
        politica_causado = _politica_causado(db, causa)
        tipos_gasto.add(politica_causado.tipo_gasto if politica_causado else None)
    cumple_compatibilidad = cumple_compatibilidad and (not politica.tipo_gasto or len(tipos_gasto) <= 1)
    controles.append(
        _control(
            "COMPATIBILIDAD",
            cumple_compatibilidad,
            "Las líneas no son compatibles en moneda, beneficiario o tipo de gasto" if not cumple_compatibilidad else "Líneas compatibles",
        )
    )

    falta_beneficiario = orden.beneficiario is None and any(c.beneficiario is None for c in causados)
    controles.append(
        _control(
            "FALTA_BENEFICIARIO",
            not falta_beneficiario,
            "Falta el beneficiario en el causado" if falta_beneficiario else "Beneficiario presente",
        )
    )

    insuficientes: list[str] = []
    for linea in lineas:
        causa_linea: GovernmentBudgetCause | None = next(
            (c for c in causados if str(c.id) == str(linea.cause_id)), None
        )
        if causa_linea is None:
            continue
        pendiente = pendiente_de_ordenar(causa_linea.monto, ordenado[str(causa_linea.id)])
        if linea.monto > pendiente:
            insuficientes.append(f"{causa_linea.codigo} (pendiente {pendiente})")
    saldo_ok = not insuficientes
    mensaje_saldo = (
        "Saldo insuficiente en: " + ", ".join(insuficientes)
        if insuficientes
        else "Saldos suficientes"
    )
    controles.append(_control("SALDO_INSUFICIENTE", saldo_ok, mensaje_saldo))

    if politica.requiere_expediente_completo:
        evidencias_ok = True
        for causa in causados:
            tiene = db.scalar(
                select(GovernmentBudgetCauseEvidence).where(
                    GovernmentBudgetCauseEvidence.company_id == ctx.company_id,
                    GovernmentBudgetCauseEvidence.cause_id == str(causa.id),
                )
            )
            if tiene is None:
                evidencias_ok = False
                break
        controles.append(
            _control(
                "FALTA_EVIDENCIA",
                evidencias_ok,
                "Faltan evidencias del expediente en los causados" if not evidencias_ok else "Evidencias completas",
            )
        )
    else:
        controles.append(_control("FALTA_EVIDENCIA", True, "Evidencias completas"))

    documentos = _documentos_orden(db, str(orden.id))
    faltantes: list[str] = []
    for doc_politica in db.scalars(
        select(GovernmentPaymentOrderPolicyDocument).where(
            GovernmentPaymentOrderPolicyDocument.policy_id == orden.policy_id,
            GovernmentPaymentOrderPolicyDocument.etapa == "EMISION",
            GovernmentPaymentOrderPolicyDocument.obligatorio.is_(True),
        )
    ):
        if not any(d.document_type_id == doc_politica.document_type_id for d in documentos):
            tipo = db.get(DocumentType, doc_politica.document_type_id)
            faltantes.append(tipo.name if tipo else doc_politica.document_type_id)
    controles.append(
        _control(
            "FALTA_DOCUMENTO",
            not faltantes,
            "Faltan documentos obligatorios: " + ", ".join(faltantes) if faltantes else "Documentos completos",
        )
    )

    fecha_valida = True
    maxima = max((c.fecha_efectiva for c in causados), default=None)
    if maxima is not None and orden.fecha_orden < maxima:
        fecha_valida = False
    if orden.fecha_orden.year != year.anio or orden.fecha_orden > hoy_de_negocio():
        fecha_valida = False
    controles.append(_control("FECHA", fecha_valida, "Fecha válida" if fecha_valida else "Fecha de la orden inválida"))

    autoridad_ok = False
    if orden.autoridad_cargo_id:
        cargo = db.get(GovernmentPosition, orden.autoridad_cargo_id)
        if cargo is not None:
            competencias = competencias_en_vigor(db, cargo, orden.fecha_orden)
            pares = {f"{c['accion']}·{c['materia']}" for c in competencias}
            if f"{politica.competencia_accion}·{politica.competencia_materia}" in pares:
                autoridad_ok = True
    controles.append(
        _control(
            "FALTA_AUTORIDAD",
            autoridad_ok,
            "Falta autoridad con competencia en la fecha de la orden" if not autoridad_ok else "Autoridad válida",
        )
    )

    limite_cumplido = True
    limite_mensaje = "Dentro del límite de la competencia"
    if not orden.autoridad_cargo_id:
        limite_cumplido = False
        limite_mensaje = "Sin autoridad para comparar el límite"
    else:
        cargo_limite = db.get(GovernmentPosition, orden.autoridad_cargo_id)
        if cargo_limite is None:
            limite_cumplido = False
            limite_mensaje = "Sin autoridad para comparar el límite"
        else:
            competencias_limite = competencias_en_vigor(db, cargo_limite, orden.fecha_orden)
            con_limite_monto = False
            for competencia in competencias_limite:
                if (
                    competencia["accion"] == politica.competencia_accion
                    and competencia["materia"] == politica.competencia_materia
                    and competencia["tipo_limite"] == "MONTO"
                ):
                    con_limite_monto = True
                    if competencia.get("monto") is None:
                        limite_cumplido = False
                        limite_mensaje = "Supera el límite de la competencia de la autoridad"
                    else:
                        resultado_limite = verificar_limite(
                            db,
                            ctx,
                            orden.moneda,
                            orden.monto,
                            Decimal(str(competencia["monto"])),
                            competencia["moneda"],
                            orden.fecha_orden,
                            bloquear=False,
                            exigir=False,
                        )
                        if not resultado_limite.get("dentro_del_limite", False):
                            limite_cumplido = False
                            if resultado_limite.get("resultado") == "SIN_TASA":
                                limite_mensaje = "No hay tasa oficial aprobada para comparar el límite"
                            else:
                                limite_mensaje = "Supera el límite de la competencia de la autoridad"
            if con_limite_monto and limite_cumplido:
                limite_mensaje = "Dentro del límite de la competencia"
            elif not con_limite_monto:
                limite_mensaje = "La competencia no tiene límite de monto"
    controles.append(_control("LIMITE", limite_cumplido, limite_mensaje))

    completo = all(c["cumplido"] for c in controles)
    return {"controles": controles, "completo": completo}


def listar_ordenes(
    db: Session,
    ctx: CompanyContext,
    year_id: str,
    estado: str | None,
    desde: date | None,
    hasta: date | None,
    beneficiario: str | None,
    moneda: str | None,
    cause_id: str | None,
    commitment_id: str | None,
    q: str | None,
) -> list[dict[str, Any]]:
    _ejercicio_de_empresa(db, ctx, year_id)
    consulta = select(GovernmentPaymentOrder).where(
        GovernmentPaymentOrder.company_id == ctx.company_id,
        GovernmentPaymentOrder.year_id == year_id,
    )
    if estado:
        consulta = consulta.where(GovernmentPaymentOrder.estado == estado)
    if desde:
        consulta = consulta.where(GovernmentPaymentOrder.fecha_orden >= desde)
    if hasta:
        consulta = consulta.where(GovernmentPaymentOrder.fecha_orden <= hasta)
    if beneficiario:
        consulta = consulta.where(GovernmentPaymentOrder.beneficiario.ilike(f"%{beneficiario}%"))
    if moneda:
        consulta = consulta.where(GovernmentPaymentOrder.moneda == moneda)
    if q:
        consulta = consulta.where(
            (GovernmentPaymentOrder.codigo.ilike(f"%{q}%"))
            | (GovernmentPaymentOrder.concepto.ilike(f"%{q}%"))
            | (GovernmentPaymentOrder.beneficiario.ilike(f"%{q}%"))
        )
    if cause_id:
        subquery = select(GovernmentPaymentOrderLine.order_id).where(GovernmentPaymentOrderLine.cause_id == cause_id)
        consulta = consulta.where(GovernmentPaymentOrder.id.in_(subquery))
    if commitment_id:
        causas_ids = select(GovernmentBudgetCause.id).where(GovernmentBudgetCause.commitment_id == commitment_id)
        subquery = select(GovernmentPaymentOrderLine.order_id).where(GovernmentPaymentOrderLine.cause_id.in_(causas_ids))
        consulta = consulta.where(GovernmentPaymentOrder.id.in_(subquery))
    consulta = consulta.order_by(GovernmentPaymentOrder.fecha_orden.desc(), GovernmentPaymentOrder.codigo.desc())
    ordenes = list(db.scalars(consulta))
    return [_orden_a_dict(db, ctx, orden, incluir_controles=True) for orden in ordenes]


def reporte_csv(
    db: Session,
    ctx: CompanyContext,
    year_id: str,
    estado: str | None,
    desde: date | None,
    hasta: date | None,
    beneficiario: str | None,
    moneda: str | None,
    cause_id: str | None,
    commitment_id: str | None,
    q: str | None,
) -> str:
    ordenes = listar_ordenes(db, ctx, year_id, estado, desde, hasta, beneficiario, moneda, cause_id, commitment_id, q)
    salida = io.StringIO()
    escritor = csv.writer(salida)
    escritor.writerow(
        [
            "codigo",
            "estado",
            "fecha_orden",
            "beneficiario",
            "moneda",
            "monto",
            "causados",
            "compromisos",
            "politica",
            "emitida_en",
            "anulada_en",
            "motivo_anulacion",
        ]
    )
    for orden in ordenes:
        causados = "; ".join(linea["codigo"] for linea in orden["lineas"])
        compromisos = "; ".join(linea["compromiso_codigo"] for linea in orden["lineas"])
        escritor.writerow(
            [
                orden["codigo"],
                orden["estado"],
                orden["fecha_orden"],
                orden["beneficiario"] or "",
                orden["moneda"],
                orden["monto"],
                causados,
                compromisos,
                orden["policy"]["codigo"],
                orden["emitida_en"].isoformat() if orden["emitida_en"] else "",
                orden["anulada_en"].isoformat() if orden["anulada_en"] else "",
                orden["motivo_anulacion"] or "",
            ]
        )
    return salida.getvalue()


def opciones(db: Session, ctx: CompanyContext, year_id: str) -> dict[str, Any]:
    _ejercicio_de_empresa(db, ctx, year_id)
    hoy = hoy_de_negocio()
    obligaciones: list[dict[str, Any]] = []
    causas_list = list(db.scalars(
        select(GovernmentBudgetCause).where(
            GovernmentBudgetCause.company_id == ctx.company_id,
            GovernmentBudgetCause.year_id == year_id,
            GovernmentBudgetCause.estado == "FORMALIZADO",
        )
    ))
    ids = [str(c.id) for c in causas_list]
    ordenados = montos_ordenados(db, ctx.company_id, ids)
    for causa in causas_list:
        pendiente = pendiente_de_ordenar(causa.monto, ordenados[str(causa.id)])
        if pendiente <= 0:
            continue
        compromiso = db.get(GovernmentBudgetCommitment, causa.commitment_id)
        politica_causado = _politica_causado(db, causa)
        tipo_gasto = politica_causado.tipo_gasto if politica_causado else None
        elegible = causa.beneficiario is not None and causa.beneficiario.strip() != ""
        obligaciones.append(
            {
                "id": str(causa.id),
                "codigo": causa.codigo,
                "beneficiario": causa.beneficiario,
                "moneda": causa.moneda,
                "fecha_efectiva": causa.fecha_efectiva.isoformat(),
                "monto_causado": f"{causa.monto:.2f}",
                "monto_ordenado": f"{ordenados[str(causa.id)]:.2f}",
                "pendiente_de_ordenar": f"{pendiente:.2f}",
                "compromiso_codigo": compromiso.codigo if compromiso else "",
                "tipo_gasto": tipo_gasto,
                "elegible": elegible,
                "motivo": None if elegible else "FALTA_BENEFICIARIO",
            }
        )
    politicas: list[dict[str, Any]] = []
    for politica in db.scalars(
        select(GovernmentPaymentOrderPolicy)
        .where(GovernmentPaymentOrderPolicy.company_id == ctx.company_id)
        .order_by(GovernmentPaymentOrderPolicy.created_at.desc())
    ):
        if politica_vigente_en(politica, hoy):
            documentos: list[dict[str, Any]] = []
            for doc in db.scalars(
                select(GovernmentPaymentOrderPolicyDocument).where(
                    GovernmentPaymentOrderPolicyDocument.policy_id == str(politica.id)
                )
            ):
                tipo = db.get(DocumentType, doc.document_type_id)
                documentos.append(
                    {
                        "document_type_id": doc.document_type_id,
                        "tipo": _etiqueta_documento(db, doc.document_type_id) or (tipo.name if tipo else ""),
                        "obligatorio": doc.obligatorio,
                    }
                )
            politicas.append(
                {
                    "id": str(politica.id),
                    "codigo": politica.codigo,
                    "nombre": politica.nombre,
                    "tipo_gasto": politica.tipo_gasto,
                    "documentos": documentos,
                }
            )
    documentos_candidatos: dict[str, dict[str, Any]] = {}
    for documento in db.scalars(
        select(Document).where(
            Document.company_id == ctx.company_id,
            Document.status == "ACTIVE",
        )
    ):
        vinculo = db.scalar(
            select(DocumentLink).where(
                DocumentLink.document_id == str(documento.id),
                DocumentLink.resource_type == "GovernmentBudgetYear",
                DocumentLink.resource_id == year_id,
                DocumentLink.company_id == ctx.company_id,
            )
        )
        if vinculo is None:
            continue
        version = db.get(DocumentVersion, documento.current_version_id) if documento.current_version_id else None
        if version is None or version.sha256 is None:
            continue
        documentos_candidatos[str(documento.id)] = {
            "id": str(documento.id),
            "titulo": documento.title,
            "tipo": _etiqueta_documento(db, documento.document_type_id),
            "document_type_id": documento.document_type_id,
        }
    evidencias = db.scalars(
        select(GovernmentBudgetCauseEvidence).where(
            GovernmentBudgetCauseEvidence.company_id == ctx.company_id,
            GovernmentBudgetCauseEvidence.cause_id.in_(ids),
            GovernmentBudgetCauseEvidence.resource_type == "DOCUMENT",
        )
    )
    for evidencia in evidencias:
        documento_evidencia: Document | None = db.scalar(
            select(Document).where(
                Document.company_id == ctx.company_id,
                Document.id == evidencia.resource_id,
                Document.status == "ACTIVE",
            )
        )
        if documento_evidencia is None:
            continue
        version = db.get(DocumentVersion, documento.current_version_id) if documento.current_version_id else None
        if version is None or version.sha256 is None:
            continue
        if str(documento.id) not in documentos_candidatos:
            documentos_candidatos[str(documento.id)] = {
                "id": str(documento.id),
                "titulo": documento.title,
                "tipo": _etiqueta_documento(db, documento.document_type_id),
                "document_type_id": documento.document_type_id,
            }
    cargos: list[dict[str, Any]] = []
    for cargo in db.scalars(
        select(GovernmentPosition).where(GovernmentPosition.company_id == ctx.company_id)
    ):
        competencias = competencias_en_vigor(db, cargo, hoy)
        pares = {f"{c['accion']}·{c['materia']}" for c in competencias}
        if "ORDENAR_PAGO·TESORERIA" in pares:
            cargos.append({"id": str(cargo.id), "codigo": cargo.code or "", "nombre": cargo.name})
    return {
        "obligaciones": obligaciones,
        "politicas": politicas,
        "documentos": sorted(documentos_candidatos.values(), key=lambda d: d["titulo"]),
        "cargos": cargos,
    }


def crear_orden(
    db: Session,
    ctx: CompanyContext,
    year_id: str,
    cuerpo: dict[str, Any],
) -> dict[str, Any]:
    year = _ejercicio_de_empresa(db, ctx, year_id, bloquear=True)
    if year.estado not in ("APROBADO", "RECONDUCIDO"):
        raise _estado_invalido()
    policy_id = cuerpo.get("policy_id")
    if not isinstance(policy_id, str):
        raise _invalida("La política es obligatoria")
    politica = politica_de_empresa(db, ctx, policy_id)
    linea_input = cuerpo.get("lineas")
    if not isinstance(linea_input, list) or not linea_input:
        raise _invalida("La orden debe tener al menos una línea")
    lineas = [
        {"cause_id": str(linea["cause_id"]), "monto": linea["monto"]}
        for linea in linea_input
    ]
    causados, monto, beneficiario = _montos_en_borrador(db, ctx, year_id, lineas)
    _validar_compatibilidad_lineas(db, causados, politica)
    fecha_orden = cuerpo.get("fecha_orden")
    if not isinstance(fecha_orden, date):
        raise _invalida("La fecha de la orden es obligatoria")
    _validar_fecha_orden(db, ctx, year, causados, fecha_orden)
    documentos = cuerpo.get("documentos", [])
    if not isinstance(documentos, list):
        raise _invalida("documentos debe ser una lista")
    docs_validados = _validar_documentos_orden(db, ctx, year_id, causados, documentos)
    orden = GovernmentPaymentOrder(
        company_id=ctx.company_id,
        year_id=year_id,
        policy_id=policy_id,
        policy_version=politica.version,
        estado="BORRADOR",
        fecha_orden=fecha_orden,
        moneda=canonical_currency(causados[0].moneda),
        monto=monto,
        concepto=cuerpo.get("concepto", ""),
        beneficiario=beneficiario,
        autoridad_cargo_id=cuerpo.get("autoridad_cargo_id"),
        version=1,
    )
    if not isinstance(orden.concepto, str) or len(orden.concepto) < 3 or len(orden.concepto) > 500:
        raise _invalida("El concepto es obligatorio y debe tener entre 3 y 500 caracteres")
    db.add(orden)
    db.flush()
    for linea in lineas:
        db.add(
            GovernmentPaymentOrderLine(
                order_id=str(orden.id),
                company_id=ctx.company_id,
                cause_id=linea["cause_id"],
                monto=linea["monto"],
            )
        )
    for doc in docs_validados:
        db.add(
            GovernmentPaymentOrderDocument(
                order_id=str(orden.id),
                company_id=ctx.company_id,
                document_id=doc["document_id"],
                document_type_id=doc["document_type_id"],
                document_version_id=doc["document_version_id"],
                sha256=doc["sha256"],
                snapshot=doc["snapshot"],
            )
        )
    db.add(
        GovernmentPaymentOrderHistory(
            order_id=str(orden.id),
            company_id=ctx.company_id,
            evento="BORRADOR_CREADO",
            actor_id=ctx.user_id,
            instantanea={"estado": "BORRADOR", "version": orden.version},
        )
    )
    record_audit(
        db,
        action="GOV_PAYMENT_ORDER_DRAFT_CREATED",
        entity_type="GovernmentPaymentOrder",
        entity_id=str(orden.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={
            "causados": [str(linea.cause_id) for linea in _lineas_orden(db, str(orden.id))],
            "monto": f"{orden.monto:.2f}",
            "politica": str(orden.policy_id),
        },
    )
    db.flush()
    return _orden_a_dict(db, ctx, orden, incluir_controles=True)


def obtener_orden(db: Session, ctx: CompanyContext, order_id: str) -> dict[str, Any]:
    orden = _orden_por_id(db, ctx, order_id)
    return _orden_a_dict(db, ctx, orden, incluir_controles=True)


def actualizar_orden(
    db: Session,
    ctx: CompanyContext,
    order_id: str,
    cuerpo: dict[str, Any],
    version: int | None,
) -> dict[str, Any]:
    if version is None:
        raise KontrolError(
            "GOV_PAYMENT_ORDER_IF_MATCH_REQUIRED",
            "Se requiere la versión de la orden",
            status_code=428,
        )
    orden = _orden_por_id(db, ctx, order_id, bloquear=True)
    if orden.estado != "BORRADOR":
        raise ConflictError(
            "GOV_PAYMENT_ORDER_NOT_DRAFT",
            "Solo las órdenes en borrador pueden actualizarse",
        )
    if orden.version != version:
        raise ConflictError(
            "GOV_PAYMENT_ORDER_STALE",
            "La orden fue cambiada por otro usuario",
            details={"version_actual": orden.version},
        )
    if "policy_id" in cuerpo:
        policy_id = cuerpo["policy_id"]
        if not isinstance(policy_id, str):
            raise _invalida("policy_id debe ser texto")
        nueva_politica = politica_de_empresa(db, ctx, policy_id)
        orden.policy_id = policy_id
        orden.policy_version = nueva_politica.version
    if "fecha_orden" in cuerpo:
        fecha = cuerpo["fecha_orden"]
        if not isinstance(fecha, date):
            raise _invalida("fecha_orden debe ser una fecha")
        orden.fecha_orden = fecha
    if "concepto" in cuerpo:
        concepto = cuerpo["concepto"]
        if not isinstance(concepto, str) or len(concepto) < 3 or len(concepto) > 500:
            raise _invalida("El concepto debe tener entre 3 y 500 caracteres")
        orden.concepto = concepto
    if "autoridad_cargo_id" in cuerpo:
        orden.autoridad_cargo_id = cuerpo.get("autoridad_cargo_id")
    if "lineas" in cuerpo:
        lineas = cuerpo["lineas"]
        if not isinstance(lineas, list) or not lineas:
            raise _invalida("La orden debe tener al menos una línea")
        lineas_validas = [
            {"cause_id": str(linea["cause_id"]), "monto": linea["monto"]}
            for linea in lineas
        ]
        causados, monto, beneficiario = _montos_en_borrador(db, ctx, orden.year_id, lineas_validas)
        politica_actual = politica_de_empresa(db, ctx, orden.policy_id)
        _validar_compatibilidad_lineas(db, causados, politica_actual)
        _validar_fecha_orden(db, ctx, _ejercicio_de_empresa(db, ctx, orden.year_id), causados, orden.fecha_orden)
        orden.monto = monto
        orden.beneficiario = beneficiario
        orden.moneda = canonical_currency(causados[0].moneda)
        for linea_existente in _lineas_orden(db, str(orden.id)):
            db.delete(linea_existente)
        db.flush()
        for linea_valida in lineas_validas:
            db.add(
                GovernmentPaymentOrderLine(
                    order_id=str(orden.id),
                    company_id=ctx.company_id,
                    cause_id=linea_valida["cause_id"],
                    monto=linea_valida["monto"],
                )
            )
    if "documentos" in cuerpo:
        documentos = cuerpo["documentos"]
        if not isinstance(documentos, list):
            raise _invalida("documentos debe ser una lista")
        lineas_actuales = _lineas_orden(db, str(orden.id))
        causados_actuales = _causados_de_lineas(
            db,
            ctx,
            orden.year_id,
            [str(linea.cause_id) for linea in lineas_actuales],
        )
        docs_validados = _validar_documentos_orden(db, ctx, orden.year_id, causados_actuales, documentos)
        for doc_existente in _documentos_orden(db, str(orden.id)):
            db.delete(doc_existente)
        db.flush()
        for doc in docs_validados:
            db.add(
                GovernmentPaymentOrderDocument(
                    order_id=str(orden.id),
                    company_id=ctx.company_id,
                    document_id=doc["document_id"],
                    document_type_id=doc["document_type_id"],
                    document_version_id=doc["document_version_id"],
                    sha256=doc["sha256"],
                    snapshot=doc["snapshot"],
                )
            )
    orden.version += 1
    db.add(
        GovernmentPaymentOrderHistory(
            order_id=str(orden.id),
            company_id=ctx.company_id,
            evento="BORRADOR_ACTUALIZADO",
            actor_id=ctx.user_id,
            instantanea={"estado": "BORRADOR", "version": orden.version},
        )
    )
    record_audit(
        db,
        action="GOV_PAYMENT_ORDER_DRAFT_UPDATED",
        entity_type="GovernmentPaymentOrder",
        entity_id=str(orden.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={"monto": f"{orden.monto:.2f}", "version": orden.version},
    )
    db.flush()
    return _orden_a_dict(db, ctx, orden, incluir_controles=True)


def obtener_controles(db: Session, ctx: CompanyContext, order_id: str) -> dict[str, Any]:
    orden = _orden_por_id(db, ctx, order_id)
    if orden.estado != "BORRADOR":
        return {"controles": [], "completo": True}
    return _controles_orden(db, ctx, orden)


def _validar_autoridad_emision(
    db: Session,
    ctx: CompanyContext,
    orden: GovernmentPaymentOrder,
    politica: GovernmentPaymentOrderPolicy,
    year: GovernmentBudgetYear,
) -> GovernmentPosition:
    autoridad_cargo_id = orden.autoridad_cargo_id
    if not isinstance(autoridad_cargo_id, str):
        raise KontrolError(
            code="GOV_PAYMENT_ORDER_AUTHORITY_REQUIRED",
            message="La autoridad es obligatoria para emitir la orden",
            field_errors={"autoridad_cargo_id": ["Autoridad obligatoria"]},
            status_code=422,
        )
    cargo = db.get(GovernmentPosition, autoridad_cargo_id)
    if cargo is None or cargo.company_id != ctx.company_id:
        raise KontrolError(
            code="GOV_PAYMENT_ORDER_AUTHORITY_INVALID",
            message="El cargo de autoridad no existe",
            field_errors={"autoridad_cargo_id": ["Cargo inexistente"]},
            status_code=422,
        )
    if not _autoridad_valida(
        db,
        ctx.company_id,
        str(cargo.id),
        orden.fecha_orden,
        politica.competencia_accion,
        politica.competencia_materia,
    ):
        raise KontrolError(
            code="GOV_PAYMENT_ORDER_AUTHORITY_INVALID",
            message="El cargo no tiene la competencia en vigor para emitir la orden",
            field_errors={"autoridad_cargo_id": ["Competencia ausente"]},
            status_code=422,
        )
    exigir_autoridad_funcional(
        db,
        ctx,
        str(cargo.id),
        politica.competencia_accion,
        politica.competencia_materia,
    )
    competencias = competencias_en_vigor(db, cargo, orden.fecha_orden)
    for competencia in competencias:
        if (
            competencia["accion"] == politica.competencia_accion
            and competencia["materia"] == politica.competencia_materia
            and competencia["tipo_limite"] == "MONTO"
        ):
            monto_competencia = (
                Decimal(str(competencia["monto"]))
                if competencia.get("monto") is not None
                else None
            )
            if monto_competencia is None:
                raise KontrolError(
                    code="GOV_PAYMENT_ORDER_AUTHORITY_LIMIT_EXCEEDED",
                    message="El monto excede el límite de la competencia de la autoridad",
                    field_errors={"autoridad_cargo_id": ["Monto excedido"]},
                    status_code=422,
                )
            limite = verificar_limite(
                db,
                ctx,
                orden.moneda,
                orden.monto,
                monto_competencia,
                competencia["moneda"],
                orden.fecha_orden,
                bloquear=True,
                exigir=True,
            )
            if not limite.get("dentro_del_limite", False):
                raise KontrolError(
                    code="GOV_PAYMENT_ORDER_AUTHORITY_LIMIT_EXCEEDED",
                    message="El monto excede el límite de la competencia de la autoridad",
                    field_errors={"autoridad_cargo_id": ["Monto excedido"]},
                    status_code=422,
                )
    return cargo


def emitir_orden(
    db: Session,
    ctx: CompanyContext,
    order_id: str,
    version: int | None,
) -> dict[str, Any]:
    if version is None:
        raise KontrolError(
            "GOV_PAYMENT_ORDER_IF_MATCH_REQUIRED",
            "Se requiere la versión de la orden",
            status_code=428,
        )
    orden = _orden_por_id(db, ctx, order_id, bloquear=True)
    if orden.version != version:
        raise ConflictError(
            "GOV_PAYMENT_ORDER_VERSION_CONFLICT",
            "La orden fue cambiada por otro usuario",
            details={"version_actual": orden.version},
        )
    if orden.estado != "BORRADOR":
        raise ConflictError(
            "GOV_PAYMENT_ORDER_NOT_DRAFT",
            "Solo las órdenes en borrador pueden emitirse",
        )
    year = _ejercicio_de_empresa(db, ctx, orden.year_id, bloquear=True)
    if year.estado not in ("APROBADO", "RECONDUCIDO"):
        raise _estado_invalido()
    lineas = _lineas_orden(db, str(orden.id))
    ids = [str(linea.cause_id) for linea in lineas]
    causados = _causados_de_lineas(db, ctx, orden.year_id, ids, bloquear=True)
    politica_actual = politica_de_empresa(db, ctx, orden.policy_id)
    _validar_compatibilidad_lineas(db, causados, politica_actual)
    _validar_fecha_orden(db, ctx, year, causados, orden.fecha_orden)
    politica = _politica_en_fecha_orden(db, ctx, orden)
    if orden.beneficiario is None:
        raise KontrolError(
            code="GOV_PAYMENT_ORDER_BENEFICIARY_REQUIRED",
            message="El beneficiario de la orden es obligatorio para emitirla",
            field_errors={"beneficiario": ["Beneficiario obligatorio"]},
            status_code=422,
        )
    ordenado = montos_ordenados(db, ctx.company_id, ids)
    for linea in lineas:
        causa = next(c for c in causados if str(c.id) == str(linea.cause_id))
        pendiente = pendiente_de_ordenar(causa.monto, ordenado[str(causa.id)])
        if linea.monto > pendiente:
            raise KontrolError(
                code="GOV_PAYMENT_ORDER_OVER_ORDER",
                message=f"El monto de la línea del causado {causa.codigo} supera el pendiente de ordenar",
                field_errors={"lineas": [f"Pendiente de {causa.codigo}: {pendiente}"]},
                status_code=409,
            )
    documentos = _documentos_orden(db, str(orden.id))
    faltantes: list[str] = []
    for doc_politica in db.scalars(
        select(GovernmentPaymentOrderPolicyDocument).where(
            GovernmentPaymentOrderPolicyDocument.policy_id == orden.policy_id,
            GovernmentPaymentOrderPolicyDocument.etapa == "EMISION",
            GovernmentPaymentOrderPolicyDocument.obligatorio.is_(True),
        )
    ):
        if not any(d.document_type_id == doc_politica.document_type_id for d in documentos):
            tipo = db.get(DocumentType, doc_politica.document_type_id)
            faltantes.append(tipo.name if tipo else doc_politica.document_type_id)
    if faltantes:
        raise KontrolError(
            code="GOV_PAYMENT_ORDER_DOCUMENT_MISSING",
            message="Faltan documentos obligatorios: " + ", ".join(faltantes),
            field_errors={"documentos": ["Faltan: " + ", ".join(faltantes)]},
            status_code=422,
        )
    if politica.requiere_expediente_completo:
        for causa in causados:
            tiene = db.scalar(
                select(GovernmentBudgetCauseEvidence).where(
                    GovernmentBudgetCauseEvidence.company_id == ctx.company_id,
                    GovernmentBudgetCauseEvidence.cause_id == str(causa.id),
                )
            )
            if tiene is None:
                raise KontrolError(
                    code="GOV_PAYMENT_ORDER_DOSSIER_INCOMPLETE",
                    message="El expediente del causado está incompleto",
                    field_errors={"lineas": ["Expediente incompleto"]},
                    status_code=422,
                )
    cargo = _validar_autoridad_emision(db, ctx, orden, politica, year)
    reglas_sod: list[Any] = []
    for causa in causados:
        evaluar_antes_de_actuar(
            db,
            ctx,
            "TRE03_ORDENAR",
            "GovernmentBudgetCause",
            str(causa.id),
        )
        # La evaluación de SoD registra la acción sin devolver un valor utilizable.
    if reglas_sod:
        reglas_sod = []
    numero, codigo = siguiente_codigo(db, ctx, year.anio, orden.year_id)
    unidad_autoridad = _unidad_nombre(db, cargo.unit_id)
    official_id = _funcionario_del_actor(db, ctx)
    funcionario_nombre = None
    if official_id is not None:
        funcionario = db.get(GovernmentOfficial, official_id)
        if funcionario is not None:
            funcionario_nombre = funcionario.nombre
    causados_snapshot: list[dict[str, Any]] = []
    for causa, linea in zip(causados, lineas, strict=True):
        compromiso = db.get(GovernmentBudgetCommitment, causa.commitment_id)
        pendiente_antes = pendiente_de_ordenar(causa.monto, ordenado[str(causa.id)])
        pendiente_despues = max(pendiente_antes - linea.monto, Decimal("0.00"))
        fuente = None
        if causa.source_resource_type and causa.source_resource_id:
            fuente = f"{causa.source_resource_type}:{causa.source_resource_id}"
        causados_snapshot.append(
            {
                "id": str(causa.id),
                "codigo": causa.codigo,
                "compromiso_codigo": compromiso.codigo if compromiso else "",
                "fuente": fuente,
                "monto_asignado": str(linea.monto),
                "pendiente_antes": str(pendiente_antes),
                "pendiente_despues": str(pendiente_despues),
            }
        )
    evidencias_snapshot: list[dict[str, Any]] = []
    for causa in causados:
        for evidencia in db.scalars(
            select(GovernmentBudgetCauseEvidence).where(
                GovernmentBudgetCauseEvidence.company_id == ctx.company_id,
                GovernmentBudgetCauseEvidence.cause_id == str(causa.id),
            )
        ):
            evidencias_snapshot.append(
                evidencia.snapshot if hasattr(evidencia, "snapshot") else {"tipo": evidencia.resource_type, "id": evidencia.resource_id}
            )
    snapshot: dict[str, Any] = {
        "orden": orden.codigo,
        "fecha": orden.fecha_orden.isoformat(),
        "beneficiario": orden.beneficiario,
        "moneda": orden.moneda,
        "monto": str(orden.monto),
        "causados": causados_snapshot,
        "politica": {
            "id": str(politica.id),
            "codigo": politica.codigo,
            "version": politica.version,
        },
        "documentos": [
            {
                "id": str(d.document_id),
                "titulo": d.snapshot.get("titulo") if hasattr(d, "snapshot") else None,
                "sha256": d.sha256,
            }
            for d in documentos
        ],
        "evidencias": evidencias_snapshot,
        "autoridad": {
            "cargo_id": str(cargo.id),
            "cargo": cargo.name,
            "unidad": unidad_autoridad,
            "funcionario_id": official_id,
            "funcionario": funcionario_nombre,
            "usuario_id": ctx.user_id,
        },
        "reglas_sod": reglas_sod,
    }
    huella = _sha256(snapshot)
    orden.estado = "EMITIDA"
    orden.numero = numero
    orden.codigo = codigo
    orden.emitida_por = ctx.user_id
    orden.emitida_en = instante_actual()
    orden.snapshot = snapshot
    orden.huella = huella
    orden.autoridad_cargo_id = str(cargo.id)
    orden.autoridad_cargo_codigo = cargo.code if hasattr(cargo, "code") else None
    orden.autoridad_cargo_nombre = cargo.name if hasattr(cargo, "name") else None
    orden.autoridad_unidad = unidad_autoridad
    orden.autoridad_funcionario_id = official_id
    orden.autoridad_funcionario_nombre = funcionario_nombre
    orden.policy_version = politica.version
    orden.version += 1
    try:
        with db.begin_nested():
            db.flush()
    except IntegrityError as error:
        if es_violacion_unica(error, "uq_gov_payment_orders_year_numero") or es_violacion_unica(error, "uq_gov_payment_orders_company_com_codigo"):
            raise ConflictError("GOV_PAYMENT_ORDER_NUMBER_CONFLICT", "Conflicto de numeración, reintente") from error
        raise
    db.add(
        GovernmentPaymentOrderHistory(
            order_id=str(orden.id),
            company_id=ctx.company_id,
            evento="EMITIDA",
            actor_id=ctx.user_id,
            instantanea={"estado": "EMITIDA", "version": orden.version},
        )
    )
    record_audit(
        db,
        action="GOV_PAYMENT_ORDER_ISSUED",
        entity_type="GovernmentPaymentOrder",
        entity_id=str(orden.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={
            "autoridad_cargo": str(orden.autoridad_cargo_id) if orden.autoridad_cargo_id else None,
            "beneficiario": orden.beneficiario,
            "causados": [str(linea.cause_id) for linea in _lineas_orden(db, str(orden.id))],
            "codigo": orden.codigo,
            "fecha_orden": orden.fecha_orden.isoformat(),
            "moneda": orden.moneda,
            "monto": f"{orden.monto:.2f}",
            "politica": str(orden.policy_id),
        },
    )
    db.flush()
    return _orden_a_dict(db, ctx, orden, incluir_controles=False)


def anular_orden(
    db: Session,
    ctx: CompanyContext,
    order_id: str,
    cuerpo: dict[str, Any],
    version: int | None,
) -> dict[str, Any]:
    if version is None:
        raise KontrolError(
            "GOV_PAYMENT_ORDER_IF_MATCH_REQUIRED",
            "Se requiere la versión de la orden",
            status_code=428,
        )
    orden = _orden_por_id(db, ctx, order_id, bloquear=True)
    if orden.version != version:
        raise ConflictError(
            "GOV_PAYMENT_ORDER_VERSION_CONFLICT",
            "La orden fue cambiada por otro usuario",
            details={"version_actual": orden.version},
        )
    if orden.estado != "EMITIDA":
        raise ConflictError(
            "GOV_PAYMENT_ORDER_NOT_ISSUED",
            "Solo las órdenes emitidas pueden anularse",
        )
    motivo = cuerpo.get("motivo")
    if not isinstance(motivo, str) or not 10 <= len(motivo) <= 500:
        raise _invalida("El motivo es obligatorio y debe tener entre 10 y 500 caracteres")
    cargo_id = cuerpo.get("cargo_id")
    if not isinstance(cargo_id, str):
        raise KontrolError(
            code="GOV_PAYMENT_ORDER_AUTHORITY_INVALID",
            message="El cargo de autoridad es obligatorio para anular",
            field_errors={"cargo_id": ["Cargo obligatorio"]},
            status_code=422,
        )
    politica = politica_de_empresa(db, ctx, orden.policy_id)
    cargo = db.get(GovernmentPosition, cargo_id)
    if cargo is None or cargo.company_id != ctx.company_id:
        raise KontrolError(
            code="GOV_PAYMENT_ORDER_AUTHORITY_INVALID",
            message="El cargo de autoridad no existe",
            field_errors={"cargo_id": ["Cargo inexistente"]},
            status_code=422,
        )
    hoy = hoy_de_negocio()
    if not _autoridad_valida(
        db,
        ctx.company_id,
        str(cargo.id),
        hoy,
        politica.competencia_accion,
        politica.competencia_materia,
    ):
        raise KontrolError(
            code="GOV_PAYMENT_ORDER_AUTHORITY_INVALID",
            message="El cargo no tiene la competencia en vigor para anular",
            field_errors={"cargo_id": ["Competencia ausente"]},
            status_code=422,
        )
    exigir_autoridad_funcional(
        db,
        ctx,
        str(cargo.id),
        politica.competencia_accion,
        politica.competencia_materia,
    )
    pagados = montos_pagados(db, ctx.company_id, [str(orden.id)])
    if pagados.get(str(orden.id), Decimal("0.00")) > 0:
        raise ConflictError(
            "GOV_PAYMENT_ORDER_HAS_PAYMENTS",
            "La orden tiene pagos registrados y no puede anularse",
        )
    orden.estado = "ANULADA"
    orden.anulada_por = ctx.user_id
    orden.anulada_en = instante_actual()
    orden.motivo_anulacion = motivo
    orden.anulacion_cargo_id = cargo_id
    orden.version += 1
    db.add(
        GovernmentPaymentOrderHistory(
            order_id=str(orden.id),
            company_id=ctx.company_id,
            evento="ANULADA",
            actor_id=ctx.user_id,
            instantanea={"estado": "ANULADA", "version": orden.version},
        )
    )
    record_audit(
        db,
        action="GOV_PAYMENT_ORDER_CANCELLED",
        entity_type="GovernmentPaymentOrder",
        entity_id=str(orden.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={
            "codigo": orden.codigo,
            "monto": f"{orden.monto:.2f}",
            "motivo": orden.motivo_anulacion,
        },
    )
    db.flush()
    return _orden_a_dict(db, ctx, orden, incluir_controles=False)
