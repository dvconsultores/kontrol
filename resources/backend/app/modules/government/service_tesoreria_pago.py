"""Servicio del pago de una orden de pago (TRE-04, GOV-TRE-004/005/010).

Implementa el ciclo de vida del pago sobre una orden TRE-03 emitida:
borrador -> envío a autorización maker-checker -> registro de la ejecución
externa. No hay integración bancaria: registrar es dejar constancia de un pago
que la Tesorería ejecutó fuera de KONTROL.
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
from app.modules.documents.models import Document, DocumentLink, DocumentVersion
from app.modules.government.models import (
    GovernmentBankAccount,
    GovernmentOfficial,
    GovernmentPayment,
    GovernmentPaymentApproval,
    GovernmentPaymentDocument,
    GovernmentPaymentHistory,
    GovernmentPaymentMethod,
    GovernmentPaymentOrder,
    GovernmentPaymentOrderDocument,
    GovernmentPaymentPolicy,
    GovernmentPaymentPolicyBand,
    GovernmentPaymentPolicyDocument,
    GovernmentPaymentPolicyMethod,
    GovernmentPosition,
)
from app.modules.government.proyeccion_obligaciones import (
    disponible_para_pago,
    montos_en_tramite,
    montos_pagados,
    pendiente_de_pagar,
)
from app.modules.government.proyeccion_retenciones import (
    exigir_sin_liquidacion,
    montos_de_pago,
)
from app.modules.government.service_actos import _autoridad_valida
from app.modules.government.service_autoridad import competencias_en_vigor
from app.modules.government.service_cuentas import _en_vigor, _enmascarar
from app.modules.government.service_identidad import _funcionario_del_actor, exigir_autoridad_funcional
from app.modules.government.service_presupuesto_causado import (
    _control,
    _etiqueta_documento,
    _username,
)
from app.modules.government.service_tesoreria_pago_politicas import (
    banda_para_monto,
    medio_utilizable,
    politica_pago_vigente_en,
    siguiente_codigo_pago,
)
from app.shared.audit import record_audit
from app.shared.clock import hoy_de_negocio, instante_actual

ESTADOS_PAGO_ACTIVOS = ("PENDIENTE_AUTORIZACION", "AUTORIZADO", "REGISTRADO")


def _orden_de_empresa(
    db: Session,
    ctx: CompanyContext,
    order_id: str,
    bloquear: bool = False,
) -> GovernmentPaymentOrder:
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


def _pago_de_empresa(
    db: Session,
    ctx: CompanyContext,
    payment_id: str,
    bloquear: bool = False,
) -> GovernmentPayment:
    consulta = select(GovernmentPayment).where(
        GovernmentPayment.company_id == ctx.company_id,
        GovernmentPayment.id == payment_id,
    )
    if bloquear:
        consulta = consulta.with_for_update()
    pago = db.scalar(consulta)
    if pago is None:
        raise NotFoundError("GOV_PAYMENT_NOT_FOUND", "Pago no encontrado")
    return pago


def _validar_documentos_pago(
    db: Session,
    ctx: CompanyContext,
    orden: GovernmentPaymentOrder,
    document_ids: list[str],
) -> list[dict[str, Any]]:
    """Regla de documento válido para el pago, adaptada de TRE-03.

    Documento ACTIVE de la empresa, con versión vigente y huella, y vinculado
    al ejercicio de la orden o ya congelado como documento de la orden.
    """
    resultado: list[dict[str, Any]] = []
    vistos: set[str] = set()
    documentos_orden = {
        str(d.document_id)
        for d in db.scalars(
            select(GovernmentPaymentOrderDocument).where(
                GovernmentPaymentOrderDocument.company_id == ctx.company_id,
                GovernmentPaymentOrderDocument.order_id == orden.id,
            )
        )
    }
    for document_id in document_ids:
        if document_id in vistos:
            continue
        vistos.add(document_id)
        documento = db.scalar(
            select(Document).where(
                Document.company_id == ctx.company_id,
                Document.id == document_id,
                Document.status == "ACTIVE",
            )
        )
        version_actual = None
        if documento is not None and documento.current_version_id is not None:
            version_actual = db.get(DocumentVersion, documento.current_version_id)
        if documento is None or version_actual is None or version_actual.sha256 is None:
            raise KontrolError(
                code="GOV_PAYMENT_DOCUMENT_INVALID",
                message="Documento inválido para el pago",
                field_errors={"documentos": [f"El documento {document_id} no tiene versión vigente con huella"]},
                status_code=422,
            )
        vinculo_ejercicio = db.scalar(
            select(DocumentLink).where(
                DocumentLink.document_id == document_id,
                DocumentLink.resource_type == "GovernmentBudgetYear",
                DocumentLink.resource_id == orden.year_id,
                DocumentLink.company_id == ctx.company_id,
            )
        )
        if vinculo_ejercicio is None and document_id not in documentos_orden:
            raise KontrolError(
                code="GOV_PAYMENT_DOCUMENT_INVALID",
                message="Documento inválido para el pago",
                field_errors={"documentos": [f"El documento {document_id} no está vinculado al ejercicio ni es de la orden"]},
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


def _guardar_documentos(
    db: Session,
    ctx: CompanyContext,
    pago: GovernmentPayment,
    etapa: str,
    validados: list[dict[str, Any]],
) -> None:
    """Crea GovernmentPaymentDocument sin duplicar document_id + etapa."""
    existentes = {
        (d.document_id, d.etapa)
        for d in db.scalars(
            select(GovernmentPaymentDocument).where(
                GovernmentPaymentDocument.company_id == ctx.company_id,
                GovernmentPaymentDocument.payment_id == pago.id,
            )
        )
    }
    for documento in validados:
        clave = (documento["document_id"], etapa)
        if clave in existentes:
            continue
        db.add(
            GovernmentPaymentDocument(
                payment_id=pago.id,
                company_id=ctx.company_id,
                etapa=etapa,
                document_id=documento["document_id"],
                document_type_id=documento["document_type_id"],
                document_version_id=documento["document_version_id"],
                sha256=documento["sha256"],
                snapshot=documento["snapshot"],
                created_by=ctx.user_id,
            )
        )
        db.flush()
        existentes.add(clave)


def _exigir_documentos(
    db: Session,
    ctx: CompanyContext,
    pago: GovernmentPayment,
    etapa: str,
) -> None:
    """Exige los tipos obligatorios de una etapa según la instantánea."""
    requisitos = (pago.policy_snapshot or {}).get("documentos") or []
    aportados = {
        d.document_type_id
        for d in db.scalars(
            select(GovernmentPaymentDocument).where(
                GovernmentPaymentDocument.company_id == ctx.company_id,
                GovernmentPaymentDocument.payment_id == pago.id,
                GovernmentPaymentDocument.etapa == etapa,
            )
        )
    }
    faltantes: list[str] = []
    for requisito in requisitos:
        if requisito.get("etapa") != etapa or not requisito.get("obligatorio"):
            continue
        if requisito.get("document_type_id") not in aportados:
            nombre = requisito.get("nombre") or requisito.get("document_type_id") or "documento"
            faltantes.append(nombre)
    if faltantes:
        raise KontrolError(
            code="GOV_PAYMENT_DOCUMENT_MISSING",
            message="Faltan documentos obligatorios del pago",
            field_errors={"documentos": faltantes},
            status_code=422,
        )


def _historia(
    db: Session,
    ctx: CompanyContext,
    pago: GovernmentPayment,
    evento: str,
) -> None:
    db.add(
        GovernmentPaymentHistory(
            payment_id=pago.id,
            company_id=ctx.company_id,
            evento=evento,
            actor_id=ctx.user_id,
            instantanea={"estado": pago.estado, "version": pago.version},
            created_by=ctx.user_id,
        )
    )
    db.flush()


def _saldo_de_orden_dict(
    db: Session,
    ctx: CompanyContext,
    orden: GovernmentPaymentOrder,
) -> dict[str, str]:
    ordenado = Decimal(orden.monto)
    pagado = montos_pagados(db, ctx.company_id, [str(orden.id)]).get(str(orden.id), Decimal("0.00"))
    en_tramite = montos_en_tramite(db, ctx.company_id, [str(orden.id)]).get(str(orden.id), Decimal("0.00"))
    pendiente = pendiente_de_pagar(ordenado, pagado)
    disponible = max(disponible_para_pago(ordenado, pagado, en_tramite), Decimal("0.00"))
    return {
        "monto_ordenado": f"{ordenado:.2f}",
        "monto_pagado": f"{pagado:.2f}",
        "monto_en_tramite": f"{en_tramite:.2f}",
        "pendiente_de_pagar": f"{pendiente:.2f}",
        "disponible_para_pago": f"{disponible:.2f}",
    }


def _detalle_cuenta(db: Session, ctx: CompanyContext, account_id: str) -> dict[str, Any]:
    cuenta = db.scalar(
        select(GovernmentBankAccount).where(
            GovernmentBankAccount.company_id == ctx.company_id,
            GovernmentBankAccount.id == account_id,
        )
    )
    if cuenta is None:
        raise NotFoundError("GOV_PAYMENT_ACCOUNT_NOT_FOUND", "Cuenta bancaria no encontrada")
    return {
        "id": str(cuenta.id),
        "codigo": cuenta.codigo,
        "denominacion": cuenta.denominacion,
        "moneda": cuenta.moneda,
        "numero_enmascarado": _enmascarar(cuenta.numero),
    }


def _detalle_medio(db: Session, ctx: CompanyContext, method_id: str) -> dict[str, Any]:
    medio = db.scalar(
        select(GovernmentPaymentMethod).where(
            GovernmentPaymentMethod.company_id == ctx.company_id,
            GovernmentPaymentMethod.id == method_id,
        )
    )
    if medio is None:
        raise NotFoundError("GOV_PAYMENT_METHOD_NOT_FOUND", "Medio de pago no encontrado")
    return {
        "id": str(medio.id),
        "codigo": medio.codigo,
        "nombre": medio.nombre,
        "exige_referencia": medio.exige_referencia,
        "referencia_unica": medio.referencia_unica,
        "patron_referencia": medio.patron_referencia,
    }


def _politica_actual(db: Session, ctx: CompanyContext, policy_id: str, bloquear: bool = False) -> GovernmentPaymentPolicy:
    consulta = select(GovernmentPaymentPolicy).where(
        GovernmentPaymentPolicy.company_id == ctx.company_id,
        GovernmentPaymentPolicy.id == policy_id,
    )
    if bloquear:
        consulta = consulta.with_for_update()
    politica = db.scalar(consulta)
    if politica is None:
        raise NotFoundError("GOV_PAYMENT_POLICY_NOT_FOUND", "Política de pago no encontrada")
    return politica


def _cuenta_de_empresa(db: Session, ctx: CompanyContext, account_id: str) -> GovernmentBankAccount:
    cuenta = db.scalar(
        select(GovernmentBankAccount).where(
            GovernmentBankAccount.company_id == ctx.company_id,
            GovernmentBankAccount.id == account_id,
        )
    )
    if cuenta is None:
        raise NotFoundError("GOV_PAYMENT_ACCOUNT_NOT_FOUND", "Cuenta bancaria no encontrada")
    return cuenta


def _medio_de_empresa(db: Session, ctx: CompanyContext, method_id: str) -> GovernmentPaymentMethod:
    medio = db.scalar(
        select(GovernmentPaymentMethod).where(
            GovernmentPaymentMethod.company_id == ctx.company_id,
            GovernmentPaymentMethod.id == method_id,
        )
    )
    if medio is None:
        raise NotFoundError("GOV_PAYMENT_METHOD_NOT_FOUND", "Medio de pago no encontrado")
    return medio





def _bandas_politica(db: Session, ctx: CompanyContext, policy_id: str) -> list[dict[str, Any]]:
    bandas: list[dict[str, Any]] = []
    for banda in db.scalars(
        select(GovernmentPaymentPolicyBand).where(
            GovernmentPaymentPolicyBand.company_id == ctx.company_id,
            GovernmentPaymentPolicyBand.policy_id == policy_id,
        ).order_by(GovernmentPaymentPolicyBand.orden)
    ):
        bandas.append(
            {
                "orden": banda.orden,
                "monto_desde": Decimal(banda.monto_desde),
                "monto_hasta": Decimal(banda.monto_hasta) if banda.monto_hasta is not None else None,
                "requisitos": list(banda.requisitos or []),
            }
        )
    return bandas


def _documentos_politica(db: Session, ctx: CompanyContext, policy_id: str) -> list[dict[str, Any]]:
    documentos: list[dict[str, Any]] = []
    for doc in db.scalars(
        select(GovernmentPaymentPolicyDocument).where(
            GovernmentPaymentPolicyDocument.company_id == ctx.company_id,
            GovernmentPaymentPolicyDocument.policy_id == policy_id,
        )
    ):
        documentos.append(
            {
                "document_type_id": doc.document_type_id,
                "etapa": doc.etapa,
                "obligatorio": doc.obligatorio,
                "nombre": _etiqueta_documento(db, doc.document_type_id),
            }
        )
    return documentos


def _medios_politica(db: Session, ctx: CompanyContext, policy_id: str) -> list[str]:
    return [
        str(m.method_id)
        for m in db.scalars(
            select(GovernmentPaymentPolicyMethod).where(
                GovernmentPaymentPolicyMethod.company_id == ctx.company_id,
                GovernmentPaymentPolicyMethod.policy_id == policy_id,
            )
        )
    ]


def _pago_a_dict(db: Session, ctx: CompanyContext, pago: GovernmentPayment) -> dict[str, Any]:
    orden = _orden_de_empresa(db, ctx, pago.order_id)
    cuenta = _detalle_cuenta(db, ctx, pago.account_id)
    medio_actual = _detalle_medio(db, ctx, pago.method_id)
    politica_actual = _politica_actual(db, ctx, pago.policy_id)
    medio = (pago.policy_snapshot or {}).get("medio")
    preparador = {
        "usuario": _username(db, pago.created_by) if pago.created_by else None,
        "cargo": pago.preparador_cargo_nombre,
        "funcionario": pago.preparador_funcionario_nombre,
    }
    aprobaciones: list[dict[str, Any]] = []
    for aprobacion in db.scalars(
        select(GovernmentPaymentApproval).where(
            GovernmentPaymentApproval.company_id == ctx.company_id,
            GovernmentPaymentApproval.payment_id == pago.id,
        ).order_by(GovernmentPaymentApproval.created_at)
    ):
        requisito = None
        if aprobacion.competencia_accion and aprobacion.competencia_materia:
            requisito = {
                "accion": aprobacion.competencia_accion,
                "materia": aprobacion.competencia_materia,
            }
        aprobaciones.append(
            {
                "actor": _username(db, aprobacion.actor_id),
                "cargo": aprobacion.cargo_nombre,
                "unidad": aprobacion.unidad,
                "funcionario": aprobacion.funcionario_nombre,
                "requisito_indice": aprobacion.requisito_indice,
                "requisito": requisito,
                "decision": aprobacion.decision,
                "motivo": aprobacion.motivo,
                "fecha": aprobacion.created_at,
                "policy_numero_version": aprobacion.policy_numero_version,
            }
        )
    documentos: list[dict[str, Any]] = []
    for doc in db.scalars(
        select(GovernmentPaymentDocument).where(
            GovernmentPaymentDocument.company_id == ctx.company_id,
            GovernmentPaymentDocument.payment_id == pago.id,
        ).order_by(GovernmentPaymentDocument.etapa, GovernmentPaymentDocument.created_at)
    ):
        documentos.append(
            {
                "etapa": doc.etapa,
                "document_id": doc.document_id,
                "titulo": doc.snapshot.get("titulo"),
                "tipo": doc.snapshot.get("tipo"),
                "sha256": doc.sha256,
            }
        )
    historia: list[dict[str, Any]] = []
    for h in db.scalars(
        select(GovernmentPaymentHistory).where(
            GovernmentPaymentHistory.company_id == ctx.company_id,
            GovernmentPaymentHistory.payment_id == pago.id,
        ).order_by(GovernmentPaymentHistory.created_at)
    ):
        historia.append(
            {
                "evento": h.evento,
                "actor": _username(db, h.actor_id) if h.actor_id else None,
                "fecha": h.created_at,
                "instantanea": h.instantanea,
            }
        )
    controles = None
    if pago.estado == "BORRADOR":
        controles = controles_pago(db, ctx, str(pago.id))
    return {
        "id": str(pago.id),
        "codigo": pago.codigo,
        "numero": pago.numero,
        "estado": pago.estado,
        "version": pago.version,
        "concepto": pago.concepto,
        "moneda": pago.moneda,
        "monto": f"{pago.monto:.2f}",
        "fecha_pago": pago.fecha_pago,
        "fecha_valor": pago.fecha_valor,
        "referencia_externa": pago.referencia_externa,
        "huella": pago.huella,
        "duplicado_confirmado": pago.duplicado_confirmado,
        "motivo_duplicado": pago.motivo_duplicado,
        "orden": {
            "id": str(orden.id),
            "codigo": orden.codigo,
            "beneficiario": orden.beneficiario,
            "moneda": orden.moneda,
            "fecha_orden": orden.fecha_orden,
            **_saldo_de_orden_dict(db, ctx, orden),
        },
        "politica": {
            "id": str(politica_actual.id),
            "codigo": politica_actual.codigo,
            "nombre": politica_actual.nombre,
            "numero_version": pago.policy_numero_version or politica_actual.numero_version,
        },
        "regla": pago.policy_snapshot,
        "cuenta": cuenta,
        "medio": medio
        or {
            "id": medio_actual["id"],
            "codigo": medio_actual["codigo"],
            "nombre": medio_actual["nombre"],
            "exige_referencia": medio_actual["exige_referencia"],
            "referencia_unica": medio_actual["referencia_unica"],
            "patron_referencia": medio_actual["patron_referencia"],
        },
        "preparador": preparador,
        "enviado_por": _username(db, pago.enviado_por) if pago.enviado_por else None,
        "enviado_en": pago.enviado_en,
        "aprobaciones_requeridas": pago.aprobaciones_requeridas,
        "aprobaciones": aprobaciones,
        "documentos": documentos,
        "documentos_preparar": pago.documentos_preparar or [],
        "registrado_por": _username(db, pago.registrado_por) if pago.registrado_por else None,
        "registrado_en": pago.registrado_en,
        "rechazado_por": _username(db, pago.rechazado_por) if pago.rechazado_por else None,
        "rechazado_en": pago.rechazado_en,
        "motivo_rechazo": pago.motivo_rechazo,
        "anulado_por": _username(db, pago.anulado_por) if pago.anulado_por else None,
        "anulado_en": pago.anulado_en,
        "motivo_anulacion": pago.motivo_anulacion,
        "historia": historia,
        "retenciones": montos_de_pago(db, ctx, pago),
        "ejecucion_externa": True,
        "fronteras": {
            "retenciones": "TRE-05",
            "conciliacion": "TRE-06",
            "reverso": "TRE-07",
            "contabilidad": "ACC",
        },
        "controles": controles,
    }


def _if_match(pago: GovernmentPayment, version: int | None) -> None:
    if version is None:
        raise KontrolError(
            code="GOV_PAYMENT_IF_MATCH_REQUIRED",
            message="Se requiere If-Match para modificar el pago",
            status_code=428,
        )
    if pago.version != version:
        raise ConflictError(
            "GOV_PAYMENT_VERSION_CONFLICT",
            "Conflicto de versión del pago",
            details={"version_actual": pago.version},
        )


def _exigir_borrador(pago: GovernmentPayment) -> None:
    if pago.estado != "BORRADOR":
        raise ConflictError("GOV_PAYMENT_NOT_DRAFT", "El pago no está en borrador")


def listar_pagos(
    db: Session,
    ctx: CompanyContext,
    estado: str | None,
    order_id: str | None,
    beneficiario: str | None,
    desde: date | None,
    hasta: date | None,
    account_id: str | None,
    method_id: str | None,
    moneda: str | None,
    q: str | None,
) -> list[dict[str, Any]]:
    consulta = select(GovernmentPayment).where(GovernmentPayment.company_id == ctx.company_id)
    if estado:
        consulta = consulta.where(GovernmentPayment.estado == estado)
    if order_id:
        consulta = consulta.where(GovernmentPayment.order_id == order_id)
    if desde:
        consulta = consulta.where(GovernmentPayment.fecha_pago >= desde)
    if hasta:
        consulta = consulta.where(GovernmentPayment.fecha_pago <= hasta)
    if account_id:
        consulta = consulta.where(GovernmentPayment.account_id == account_id)
    if method_id:
        consulta = consulta.where(GovernmentPayment.method_id == method_id)
    if moneda:
        consulta = consulta.where(GovernmentPayment.moneda == moneda)
    pagos = list(db.scalars(consulta.order_by(GovernmentPayment.created_at.desc())))
    if beneficiario or q:
        filtrados: list[GovernmentPayment] = []
        for pago in pagos:
            orden = _orden_de_empresa(db, ctx, pago.order_id)
            if beneficiario and beneficiario.lower() not in (orden.beneficiario or "").lower():
                continue
            if q:
                texto_q = q.lower()
                if (
                    texto_q not in (pago.codigo or "").lower()
                    and texto_q not in (pago.concepto or "").lower()
                    and texto_q not in (pago.referencia_externa or "").lower()
                ):
                    continue
            filtrados.append(pago)
        pagos = filtrados
    resultado: list[dict[str, Any]] = []
    for pago in pagos:
        orden = _orden_de_empresa(db, ctx, pago.order_id)
        cuenta = _cuenta_de_empresa(db, ctx, pago.account_id)
        medio = _medio_de_empresa(db, ctx, pago.method_id)
        resultado.append(
            {
                "id": str(pago.id),
                "codigo": pago.codigo,
                "estado": pago.estado,
                "orden_codigo": orden.codigo,
                "order_id": str(orden.id),
                "beneficiario": orden.beneficiario,
                "cuenta_codigo": cuenta.codigo,
                "medio_codigo": medio.codigo,
                "moneda": pago.moneda,
                "monto": f"{pago.monto:.2f}",
                "fecha_pago": pago.fecha_pago,
                "fecha_valor": pago.fecha_valor,
                "referencia_externa": pago.referencia_externa,
                "enviado_en": pago.enviado_en,
                "registrado_en": pago.registrado_en,
                "version": pago.version,
            }
        )
    return resultado


def reporte_csv_pagos(
    db: Session,
    ctx: CompanyContext,
    estado: str | None,
    order_id: str | None,
    beneficiario: str | None,
    desde: date | None,
    hasta: date | None,
    account_id: str | None,
    method_id: str | None,
    moneda: str | None,
    q: str | None,
) -> str:
    pagos = listar_pagos(
        db,
        ctx,
        estado,
        order_id,
        beneficiario,
        desde,
        hasta,
        account_id,
        method_id,
        moneda,
        q,
    )
    salida = io.StringIO()
    writer = csv.writer(salida, delimiter=";")
    writer.writerow(
        [
            "codigo",
            "estado",
            "orden",
            "beneficiario",
            "cuenta",
            "medio",
            "moneda",
            "monto",
            "fecha_pago",
            "fecha_valor",
            "referencia",
            "enviado_en",
            "registrado_en",
        ]
    )
    for pago in pagos:
        writer.writerow(
            [
                pago["codigo"],
                pago["estado"],
                pago["orden_codigo"],
                pago["beneficiario"],
                pago["cuenta_codigo"],
                pago["medio_codigo"],
                pago["moneda"],
                pago["monto"],
                pago["fecha_pago"].isoformat(),
                pago["fecha_valor"].isoformat() if pago["fecha_valor"] else "",
                pago["referencia_externa"] or "",
                pago["enviado_en"].isoformat() if pago["enviado_en"] else "",
                pago["registrado_en"].isoformat() if pago["registrado_en"] else "",
            ]
        )
    return salida.getvalue()


def saldo_de_orden(db: Session, ctx: CompanyContext, orden: GovernmentPaymentOrder) -> dict[str, str]:
    return _saldo_de_orden_dict(db, ctx, orden)


def opciones_pago(db: Session, ctx: CompanyContext, order_id: str | None) -> dict[str, Any]:
    hoy = hoy_de_negocio()
    ordenes: list[dict[str, Any]] = []
    for orden in db.scalars(
        select(GovernmentPaymentOrder)
        .where(
            GovernmentPaymentOrder.company_id == ctx.company_id,
            GovernmentPaymentOrder.estado == "EMITIDA",
        )
        .order_by(GovernmentPaymentOrder.fecha_orden.desc())
    ):
        disponible = Decimal(_saldo_de_orden_dict(db, ctx, orden)["disponible_para_pago"])
        if disponible <= 0:
            continue
        ordenes.append(
            {
                "id": str(orden.id),
                "codigo": orden.codigo,
                "beneficiario": orden.beneficiario,
                "moneda": orden.moneda,
                "fecha_orden": orden.fecha_orden,
                "year_id": orden.year_id,
                **_saldo_de_orden_dict(db, ctx, orden),
            }
        )

    politicas: list[dict[str, Any]] = []
    for politica in db.scalars(
        select(GovernmentPaymentPolicy).where(
            GovernmentPaymentPolicy.company_id == ctx.company_id,
            GovernmentPaymentPolicy.estado == "VIGENTE",
        )
    ):
        if not politica_pago_vigente_en(politica, hoy):
            continue
        politicas.append(
            {
                "id": str(politica.id),
                "codigo": politica.codigo,
                "numero_version": politica.numero_version,
                "nombre": politica.nombre,
                "moneda": politica.moneda,
                "permite_pago_parcial": politica.permite_pago_parcial,
                "control_duplicado": politica.control_duplicado,
                "medios": _medios_politica(db, ctx, str(politica.id)),
            }
        )

    cuentas: list[dict[str, Any]] = []
    for cuenta in db.scalars(
        select(GovernmentBankAccount).where(GovernmentBankAccount.company_id == ctx.company_id)
    ):
        if not _en_vigor(cuenta, hoy):
            continue
        cuentas.append(
            {
                "id": str(cuenta.id),
                "codigo": cuenta.codigo,
                "denominacion": cuenta.denominacion,
                "moneda": cuenta.moneda,
                "numero_enmascarado": _enmascarar(cuenta.numero),
            }
        )

    medios: list[dict[str, Any]] = []
    for medio in db.scalars(
        select(GovernmentPaymentMethod).where(GovernmentPaymentMethod.company_id == ctx.company_id)
    ):
        if not medio_utilizable(medio, hoy):
            continue
        medios.append(
            {
                "id": str(medio.id),
                "codigo": medio.codigo,
                "nombre": medio.nombre,
                "exige_referencia": medio.exige_referencia,
                "referencia_unica": medio.referencia_unica,
                "patron_referencia": medio.patron_referencia,
            }
        )

    cargos: list[dict[str, Any]] = []
    for cargo in db.scalars(select(GovernmentPosition).where(GovernmentPosition.company_id == ctx.company_id)):
        competencias = [f"{c['accion']}·{c['materia']}" for c in competencias_en_vigor(db, cargo, hoy)]
        cargos.append(
            {
                "id": str(cargo.id),
                "codigo": cargo.code,
                "nombre": cargo.name,
                "competencias": competencias,
            }
        )

    documentos: list[dict[str, Any]] = []
    if order_id:
        orden = _orden_de_empresa(db, ctx, order_id)
        for d in db.scalars(select(Document).where(Document.company_id == ctx.company_id, Document.status == "ACTIVE")):
            try:
                validados = _validar_documentos_pago(db, ctx, orden, [str(d.id)])
            except KontrolError:
                continue
            for doc in validados:
                documentos.append(
                    {
                        "id": doc["document_id"],
                        "titulo": doc["snapshot"]["titulo"],
                        "tipo": doc["snapshot"]["tipo"],
                        "document_type_id": doc["document_type_id"],
                    }
                )
    return {
        "ordenes": ordenes,
        "politicas": politicas,
        "cuentas": cuentas,
        "medios": medios,
        "cargos": cargos,
        "documentos": documentos,
    }


def crear_pago(db: Session, ctx: CompanyContext, cuerpo: dict[str, Any]) -> dict[str, Any]:
    if cuerpo.get("idempotency_key"):
        existente = db.scalar(
            select(GovernmentPayment).where(
                GovernmentPayment.company_id == ctx.company_id,
                GovernmentPayment.idempotency_key == cuerpo["idempotency_key"],
            )
        )
        if existente is not None:
            return obtener_pago(db, ctx, str(existente.id))

    orden = _orden_de_empresa(db, ctx, cuerpo["order_id"])
    if orden.estado != "EMITIDA":
        raise KontrolError(
            code="GOV_PAYMENT_ORDER_NOT_PAYABLE",
            message="La orden no está en estado EMITIDA",
            status_code=422,
        )
    politica = _politica_actual(db, ctx, cuerpo["policy_id"])
    cuenta = _cuenta_de_empresa(db, ctx, cuerpo["account_id"])
    medio = _medio_de_empresa(db, ctx, cuerpo["method_id"])
    documentos_preparar = list(dict.fromkeys(cuerpo.get("documentos") or []))
    pago = GovernmentPayment(
        company_id=ctx.company_id,
        order_id=orden.id,
        policy_id=politica.id,
        account_id=cuenta.id,
        method_id=medio.id,
        moneda=orden.moneda,
        monto=Decimal(cuerpo["monto"]),
        fecha_pago=cuerpo["fecha_pago"],
        concepto=cuerpo["concepto"],
        documentos_preparar=documentos_preparar,
        idempotency_key=cuerpo.get("idempotency_key"),
        created_by=ctx.user_id,
    )
    db.add(pago)
    db.flush()
    _historia(db, ctx, pago, "CREADO")
    record_audit(
        db,
        action="GOV_PAYMENT_CREATED",
        entity_type="GovernmentPayment",
        entity_id=str(pago.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={"monto": f"{pago.monto:.2f}", "orden": orden.codigo, "politica": politica.codigo},
    )
    return obtener_pago(db, ctx, str(pago.id))


def obtener_pago(db: Session, ctx: CompanyContext, payment_id: str) -> dict[str, Any]:
    pago = _pago_de_empresa(db, ctx, payment_id)
    return _pago_a_dict(db, ctx, pago)


def actualizar_pago(
    db: Session,
    ctx: CompanyContext,
    payment_id: str,
    cuerpo: dict[str, Any],
    version: int | None,
) -> dict[str, Any]:
    pago = _pago_de_empresa(db, ctx, payment_id, bloquear=True)
    _if_match(pago, version)
    _exigir_borrador(pago)
    exigir_sin_liquidacion(db, ctx, pago)
    if "order_id" in cuerpo:
        raise KontrolError(code="GOV_PAYMENT_ORDER_IMMUTABLE", message="La orden no puede cambiarse", status_code=422)
    if "policy_id" in cuerpo:
        _politica_actual(db, ctx, cuerpo["policy_id"])
        pago.policy_id = cuerpo["policy_id"]
    if "account_id" in cuerpo:
        _cuenta_de_empresa(db, ctx, cuerpo["account_id"])
        pago.account_id = cuerpo["account_id"]
    if "method_id" in cuerpo:
        _medio_de_empresa(db, ctx, cuerpo["method_id"])
        pago.method_id = cuerpo["method_id"]
    if "monto" in cuerpo:
        pago.monto = Decimal(cuerpo["monto"])
    if "fecha_pago" in cuerpo:
        pago.fecha_pago = cuerpo["fecha_pago"]
    if "concepto" in cuerpo:
        pago.concepto = cuerpo["concepto"]
    if "documentos" in cuerpo:
        pago.documentos_preparar = list(dict.fromkeys(cuerpo["documentos"]))
    pago.version += 1
    _historia(db, ctx, pago, "ACTUALIZADO")
    record_audit(
        db,
        action="GOV_PAYMENT_UPDATED",
        entity_type="GovernmentPayment",
        entity_id=str(pago.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={"monto": f"{pago.monto:.2f}", "version": pago.version},
    )
    return obtener_pago(db, ctx, str(pago.id))


def controles_pago(db: Session, ctx: CompanyContext, payment_id: str) -> dict[str, Any]:
    pago = _pago_de_empresa(db, ctx, payment_id)
    orden = _orden_de_empresa(db, ctx, pago.order_id)
    politica = _politica_actual(db, ctx, pago.policy_id)
    medio = _medio_de_empresa(db, ctx, pago.method_id)
    cuenta = _cuenta_de_empresa(db, ctx, pago.account_id)
    hoy = hoy_de_negocio()

    controles: list[dict[str, Any]] = []
    controles.append(
        _control("ORDEN", orden.estado == "EMITIDA", "Orden emitida" if orden.estado == "EMITIDA" else "La orden no está emitida")
    )
    controles.append(
        _control(
            "POLITICA",
            politica.estado == "VIGENTE" and politica_pago_vigente_en(politica, hoy),
            "Política vigente y aplicable" if politica.estado == "VIGENTE" and politica_pago_vigente_en(politica, hoy) else "La política no está vigente en la fecha actual",
        )
    )
    controles.append(
        _control(
            "MEDIO",
            medio_utilizable(medio, hoy) and str(medio.id) in _medios_politica(db, ctx, str(politica.id)),
            "Medio permitido por la política" if medio_utilizable(medio, hoy) and str(medio.id) in _medios_politica(db, ctx, str(politica.id)) else "El medio no está permitido por la política o no está vigente",
        )
    )
    controles.append(
        _control(
            "CUENTA",
            _en_vigor(cuenta, hoy) and cuenta.moneda == orden.moneda,
            "Cuenta vigente en la moneda de la orden" if _en_vigor(cuenta, hoy) and cuenta.moneda == orden.moneda else "La cuenta no está vigente o no coincide la moneda",
        )
    )
    controles.append(
        _control("MONEDA", pago.moneda == orden.moneda, "Moneda de la orden" if pago.moneda == orden.moneda else "La moneda no coincide con la orden")
    )
    disponible = Decimal(_saldo_de_orden_dict(db, ctx, orden)["disponible_para_pago"])
    controles.append(
        _control("SALDO", pago.monto <= disponible, "Monto dentro del disponible" if pago.monto <= disponible else f"El monto supera el disponible: {disponible:.2f}")
    )
    if not politica.permite_pago_parcial:
        controles.append(
            _control(
                "PARCIAL",
                pago.monto == disponible,
                "Pago parcial permitido o monto completo" if pago.monto == disponible else "La política no permite pago parcial",
            )
        )
    bandas = _bandas_politica(db, ctx, str(politica.id))
    banda = banda_para_monto(bandas, pago.monto)
    controles.append(
        _control("BANDA", banda is not None, "Banda de autorización encontrada" if banda is not None else "No hay banda de autorización para el monto")
    )
    aprobaciones_requeridas = None
    if banda is not None:
        aprobaciones_requeridas = sum(int(r.get("cantidad", 0)) for r in banda[1].get("requisitos", []))
    controles.append(
        _control(
            "DOCUMENTOS",
            True,
            "Documentos de preparación completos",
        )
    )

    duplicado = db.scalar(
        select(GovernmentPayment).where(
            GovernmentPayment.company_id == ctx.company_id,
            GovernmentPayment.order_id == pago.order_id,
            GovernmentPayment.monto == pago.monto,
            GovernmentPayment.estado.in_(ESTADOS_PAGO_ACTIVOS),
            GovernmentPayment.id != pago.id,
        )
    )
    if duplicado is not None:
        if politica.control_duplicado == "BLOQUEAR":
            controles.append(_control("DUPLICADO", False, "Hay otro pago activo de la orden por el mismo monto"))
        else:
            controles.append(
                _control(
                    "DUPLICADO",
                    False,
                    "Hay otro pago activo de la orden por el mismo monto: debe confirmarlo con motivo al enviar",
                )
            )
    else:
        controles.append(_control("DUPLICADO", True, "Sin pago activo del mismo importe"))

    if politica.preparador_competencia_accion and politica.preparador_competencia_materia:
        controles.append(
            _control(
                "PREPARADOR",
                True,
                f"Debe declarar la competencia {politica.preparador_competencia_accion}·{politica.preparador_competencia_materia}",
            )
        )

    completo = all(c["cumplido"] for c in controles if c["codigo"] != "DUPLICADO" or politica.control_duplicado != "ADVERTIR")
    return {
        "controles": controles,
        "completo": completo,
        "banda": banda[1] if banda else None,
        "aprobaciones_requeridas": aprobaciones_requeridas,
        "saldo": _saldo_de_orden_dict(db, ctx, orden),
    }


def enviar_pago(
    db: Session,
    ctx: CompanyContext,
    payment_id: str,
    cuerpo: dict[str, Any],
    version: int | None,
) -> dict[str, Any]:
    pago = _pago_de_empresa(db, ctx, payment_id, bloquear=True)
    _if_match(pago, version)
    _exigir_borrador(pago)
    orden = _orden_de_empresa(db, ctx, pago.order_id, bloquear=True)
    if orden.estado != "EMITIDA":
        raise KontrolError(
            code="GOV_PAYMENT_ORDER_NOT_PAYABLE",
            message="La orden no está en estado EMITIDA",
            status_code=422,
        )
    politica = _politica_actual(db, ctx, pago.policy_id, bloquear=True)
    hoy = hoy_de_negocio()
    if not (politica.estado == "VIGENTE" and politica_pago_vigente_en(politica, hoy) and politica.moneda == orden.moneda):
        raise KontrolError(
            code="GOV_PAYMENT_POLICY_NOT_APPLICABLE",
            message="La política no es aplicable a este pago",
            status_code=422,
        )
    medio = _medio_de_empresa(db, ctx, pago.method_id)
    if not medio_utilizable(medio, hoy) or str(medio.id) not in _medios_politica(db, ctx, str(politica.id)):
        raise KontrolError(
            code="GOV_PAYMENT_METHOD_NOT_ALLOWED",
            message="El medio no está permitido por la política o no está vigente",
            status_code=422,
        )
    cuenta = _cuenta_de_empresa(db, ctx, pago.account_id)
    if not _en_vigor(cuenta, hoy) or cuenta.moneda != orden.moneda:
        raise KontrolError(
            code="GOV_PAYMENT_ACCOUNT_INVALID",
            message="La cuenta no está vigente o no coincide la moneda",
            status_code=422,
        )
    if pago.moneda != orden.moneda:
        raise KontrolError(
            code="GOV_PAYMENT_CURRENCY_MISMATCH",
            message="La moneda del pago no coincide con la orden",
            status_code=422,
        )
    disponible = Decimal(_saldo_de_orden_dict(db, ctx, orden)["disponible_para_pago"])
    if pago.monto > disponible:
        raise KontrolError(
            code="GOV_PAYMENT_OVERPAYMENT",
            message="El monto supera el disponible de la orden",
            field_errors={"monto": [f"Disponible: {disponible:.2f}"]},
            status_code=409,
        )
    if not politica.permite_pago_parcial and pago.monto != disponible:
        raise KontrolError(
            code="GOV_PAYMENT_PARTIAL_NOT_ALLOWED",
            message="La política no permite pago parcial",
            status_code=422,
        )

    duplicado = db.scalar(
        select(GovernmentPayment).where(
            GovernmentPayment.company_id == ctx.company_id,
            GovernmentPayment.order_id == pago.order_id,
            GovernmentPayment.monto == pago.monto,
            GovernmentPayment.estado.in_(ESTADOS_PAGO_ACTIVOS),
            GovernmentPayment.id != pago.id,
        )
    )
    if duplicado is not None:
        if politica.control_duplicado == "BLOQUEAR":
            raise ConflictError("GOV_PAYMENT_DUPLICATE", "Ya existe un pago activo por el mismo monto")
        if not cuerpo.get("confirmar_duplicado"):
            raise ConflictError(
                "GOV_PAYMENT_DUPLICATE_CONFIRMATION_REQUIRED",
                "Debe confirmar el duplicado con motivo",
            )
        motivo = cuerpo.get("motivo_duplicado") or ""
        if len(motivo.strip()) < 10:
            raise KontrolError(
                code="GOV_PAYMENT_DUPLICATE_REASON_REQUIRED",
                message="El motivo del duplicado debe tener al menos 10 caracteres",
                status_code=422,
            )
        pago.duplicado_confirmado = True
        pago.motivo_duplicado = motivo.strip()

    bandas = _bandas_politica(db, ctx, str(politica.id))
    banda = banda_para_monto(bandas, pago.monto)
    if banda is None:
        raise KontrolError(
            code="GOV_PAYMENT_NO_APPROVAL_BAND",
            message="No hay banda de autorización para el monto",
            status_code=422,
        )
    aprobaciones_requeridas = sum(int(r.get("cantidad", 0)) for r in banda[1].get("requisitos", []))

    preparador_cargo_id = cuerpo.get("preparador_cargo_id")
    if politica.preparador_competencia_accion and politica.preparador_competencia_materia:
        if not preparador_cargo_id:
            raise KontrolError(
                code="GOV_PAYMENT_PREPARER_AUTHORITY_REQUIRED",
                message="Se requiere cargo preparador",
                status_code=422,
            )
        cargo = db.scalar(
            select(GovernmentPosition).where(
                GovernmentPosition.company_id == ctx.company_id,
                GovernmentPosition.id == preparador_cargo_id,
            )
        )
        if cargo is None or not _autoridad_valida(
            db,
            ctx.company_id,
            str(cargo.id),
            hoy,
            politica.preparador_competencia_accion,
            politica.preparador_competencia_materia,
        ):
            raise KontrolError(
                code="GOV_PAYMENT_PREPARER_AUTHORITY_INVALID",
                message="El cargo preparador no tiene la autoridad requerida",
                status_code=422,
            )
        exigir_autoridad_funcional(
            db,
            ctx,
            str(cargo.id),
            politica.preparador_competencia_accion,
            politica.preparador_competencia_materia,
        )
        pago.preparador_cargo_id = str(cargo.id)
        pago.preparador_cargo_codigo = cargo.code
        pago.preparador_cargo_nombre = cargo.name
        funcionario_id = _funcionario_del_actor(db, ctx)
        pago.preparador_funcionario_id = funcionario_id
        if funcionario_id:
            funcionario = db.scalar(
                select(GovernmentOfficial).where(
                    GovernmentOfficial.company_id == ctx.company_id,
                    GovernmentOfficial.id == funcionario_id,
                )
            )
            pago.preparador_funcionario_nombre = funcionario.nombre if funcionario else None
    elif preparador_cargo_id:
        cargo = db.scalar(
            select(GovernmentPosition).where(
                GovernmentPosition.company_id == ctx.company_id,
                GovernmentPosition.id == preparador_cargo_id,
            )
        )
        if cargo is None:
            raise NotFoundError("GOV_POSITION_NOT_FOUND", "Cargo no encontrado")
        pago.preparador_cargo_id = str(cargo.id)
        pago.preparador_cargo_codigo = cargo.code
        pago.preparador_cargo_nombre = cargo.name

    documentos_preparar = _validar_documentos_pago(db, ctx, orden, pago.documentos_preparar or [])

    banda_dict = {
        "orden": banda[1]["orden"],
        "monto_desde": f"{Decimal(banda[1]['monto_desde']):.2f}",
        "monto_hasta": f"{Decimal(banda[1]['monto_hasta']):.2f}" if banda[1].get("monto_hasta") is not None else None,
        "requisitos": banda[1]["requisitos"],
    }
    policy_snapshot = {
        "policy_id": str(politica.id),
        "codigo": politica.codigo,
        "numero_version": politica.numero_version,
        "nombre": politica.nombre,
        "moneda": politica.moneda,
        "permite_pago_parcial": politica.permite_pago_parcial,
        "control_duplicado": politica.control_duplicado,
        "exige_cargo_autorizado_cuenta": politica.exige_cargo_autorizado_cuenta,
        "preparador_competencia": (
            {
                "accion": politica.preparador_competencia_accion,
                "materia": politica.preparador_competencia_materia,
            }
            if politica.preparador_competencia_accion and politica.preparador_competencia_materia
            else None
        ),
        "medio": {
            "id": str(medio.id),
            "codigo": medio.codigo,
            "nombre": medio.nombre,
            "exige_referencia": medio.exige_referencia,
            "referencia_unica": medio.referencia_unica,
            "patron_referencia": medio.patron_referencia,
        },
        "banda": banda_dict,
        "documentos": _documentos_politica(db, ctx, str(politica.id)),
        "fundamento": politica.fundamento,
        "tipo_regla": politica.tipo_regla,
    }
    pago.policy_snapshot = policy_snapshot
    pago.policy_numero_version = politica.numero_version
    pago.aprobaciones_requeridas = aprobaciones_requeridas
    _guardar_documentos(db, ctx, pago, "PREPARAR", documentos_preparar)
    pago.policy_snapshot = policy_snapshot
    _exigir_documentos(db, ctx, pago, "PREPARAR")

    numero, codigo = siguiente_codigo_pago(db, ctx, hoy.year)
    instante = instante_actual()
    pago.numero = numero
    pago.codigo = codigo
    pago.estado = "PENDIENTE_AUTORIZACION"
    pago.enviado_por = ctx.user_id
    pago.enviado_en = instante

    try:
        with db.begin_nested():
            db.flush()
    except IntegrityError as error:
        if es_violacion_unica(error, "uq_gov_payments_company_codigo"):
            raise ConflictError("GOV_PAYMENT_NUMBER_CONFLICT", "Conflicto en el número de pago") from error
        raise

    pago.version += 1
    _historia(db, ctx, pago, "ENVIADO")
    record_audit(
        db,
        action="GOV_PAYMENT_SUBMITTED",
        entity_type="GovernmentPayment",
        entity_id=str(pago.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={
            "aprobaciones_requeridas": aprobaciones_requeridas,
            "banda": banda[0],
            "codigo": codigo,
            "cuenta": cuenta.codigo,
            "duplicado_confirmado": pago.duplicado_confirmado,
            "medio": medio.codigo,
            "moneda": pago.moneda,
            "monto": f"{pago.monto:.2f}",
            "numero_version": politica.numero_version,
            "orden": orden.codigo,
            "politica": politica.codigo,
        },
    )
    return obtener_pago(db, ctx, str(pago.id))


def descartar_borrador(
    db: Session,
    ctx: CompanyContext,
    payment_id: str,
    version: int | None,
) -> dict[str, Any]:
    pago = _pago_de_empresa(db, ctx, payment_id, bloquear=True)
    _if_match(pago, version)
    _exigir_borrador(pago)
    exigir_sin_liquidacion(db, ctx, pago)
    instante = instante_actual()
    pago.estado = "ANULADO"
    pago.anulado_por = ctx.user_id
    pago.anulado_en = instante
    pago.motivo_anulacion = "Borrador descartado"
    pago.version += 1
    _historia(db, ctx, pago, "DESCARTADO")
    record_audit(
        db,
        action="GOV_PAYMENT_CANCELLED",
        entity_type="GovernmentPayment",
        entity_id=str(pago.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={"codigo": pago.codigo, "estado_previo": "BORRADOR", "motivo": "Borrador descartado"},
    )
    return obtener_pago(db, ctx, str(pago.id))
