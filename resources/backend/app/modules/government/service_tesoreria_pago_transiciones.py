from __future__ import annotations

import re
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext
from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.core.integrity import es_violacion_unica
from app.modules.government.models import (
    GovernmentBankAccount,
    GovernmentOfficial,
    GovernmentPayment,
    GovernmentPaymentApproval,
    GovernmentPosition,
)
from app.modules.government.proyeccion_obligaciones import montos_pagados
from app.modules.government.service_actos import _autoridad_valida
from app.modules.government.service_autoridad import competencias_en_vigor
from app.modules.government.service_cuentas import (
    _autorizados_en_vigor,
    _en_vigor,
)
from app.modules.government.service_identidad import (
    _funcionario_del_actor,
    exigir_autoridad_funcional,
)
from app.modules.government.service_presupuesto_causado import (
    _sha256,
    _unidad_nombre,
)
from app.modules.government.service_sod import (
    evaluar_antes_de_actuar,
    usuarios_equivalentes,
)
from app.modules.government.service_tasas import verificar_limite
from app.modules.government.service_tesoreria_pago import (
    _exigir_documentos,
    _guardar_documentos,
    _historia,
    _if_match,
    _orden_de_empresa,
    _pago_de_empresa,
    _validar_documentos_pago,
    obtener_pago,
)
from app.shared.audit import record_audit
from app.shared.clock import hoy_de_negocio, instante_actual


def _registrar_auditoria_tesoreria(
    db: Session,
    ctx: CompanyContext,
    action: str,
    payment_id: str,
    after: dict[str, Any],
) -> None:
    record_audit(
        db,
        action=action,
        entity_type="GovernmentPayment",
        entity_id=str(payment_id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after=after,
    )


def _validar_maker_checker(db: Session, ctx: CompanyContext, pago: GovernmentPayment) -> None:
    actores = usuarios_equivalentes(db, ctx, ctx.user_id)
    if pago.created_by in actores or pago.enviado_por in actores:
        raise ConflictError(
            "GOV_PAYMENT_MAKER_CHECKER",
            "Quien preparó o envió el pago no puede autorizarlo",
        )
    aprobaciones = db.scalars(
        select(GovernmentPaymentApproval).where(
            GovernmentPaymentApproval.company_id == ctx.company_id,
            GovernmentPaymentApproval.payment_id == pago.id,
        )
    ).all()
    for aprobacion in aprobaciones:
        if aprobacion.actor_id in actores:
            raise ConflictError("GOV_PAYMENT_ALREADY_DECIDED", "El actor ya decidió sobre este pago")


def aprobar_pago(
    db: Session,
    ctx: CompanyContext,
    payment_id: str,
    cuerpo: dict[str, Any],
    version: int | None,
) -> dict[str, Any]:
    pago = _pago_de_empresa(db, ctx, payment_id, bloquear=True)
    _if_match(pago, version)
    if pago.estado != "PENDIENTE_AUTORIZACION":
        raise ConflictError("GOV_PAYMENT_NOT_PENDING", "El pago no está pendiente de autorización")

    _validar_maker_checker(db, ctx, pago)

    cargo_id = cuerpo.get("cargo_id")
    if not isinstance(cargo_id, str):
        raise KontrolError(
            code="GOV_PAYMENT_AUTHORITY_INVALID",
            message="El cargo de autorización es obligatorio",
            field_errors={"cargo_id": ["Cargo obligatorio"]},
            status_code=422,
        )
    cargo = db.get(GovernmentPosition, cargo_id)
    if cargo is None or cargo.company_id != ctx.company_id:
        raise NotFoundError("GOV_POSITION_NOT_FOUND", "Cargo no encontrado")

    requisito_indice = cuerpo.get("requisito_indice")
    if isinstance(requisito_indice, bool) or not isinstance(requisito_indice, int):
        raise KontrolError(
            code="GOV_PAYMENT_REQUIREMENT_INVALID",
            message="El índice de requisito es inválido",
            field_errors={"requisito_indice": ["Requisito obligatorio"]},
            status_code=422,
        )
    requisitos = (pago.policy_snapshot or {}).get("banda", {}).get("requisitos") or []
    if requisito_indice < 0 or requisito_indice >= len(requisitos):
        raise KontrolError(
            code="GOV_PAYMENT_REQUIREMENT_INVALID",
            message="El índice de requisito es inválido",
            field_errors={"requisito_indice": ["Índice fuera de rango"]},
            status_code=422,
        )
    requisito = requisitos[requisito_indice]

    aprobaciones_existentes = db.scalars(
        select(GovernmentPaymentApproval).where(
            GovernmentPaymentApproval.company_id == ctx.company_id,
            GovernmentPaymentApproval.payment_id == pago.id,
            GovernmentPaymentApproval.decision == "APROBADA",
            GovernmentPaymentApproval.requisito_indice == requisito_indice,
        )
    ).all()
    if len(aprobaciones_existentes) >= int(requisito.get("cantidad", 0)):
        raise ConflictError("GOV_PAYMENT_REQUIREMENT_COVERED", "El requisito ya está cubierto")

    for aprobacion in db.scalars(
        select(GovernmentPaymentApproval).where(
            GovernmentPaymentApproval.company_id == ctx.company_id,
            GovernmentPaymentApproval.payment_id == pago.id,
        )
    ).all():
        if aprobacion.cargo_id == str(cargo.id):
            raise ConflictError("GOV_PAYMENT_CARGO_ALREADY_USED", "El cargo ya participó en este pago")

    hoy = hoy_de_negocio()
    accion = requisito.get("accion")
    materia = requisito.get("materia")
    if not isinstance(accion, str) or not isinstance(materia, str):
        raise KontrolError(
            code="GOV_PAYMENT_REQUIREMENT_INVALID",
            message="El requisito no define la competencia",
            status_code=422,
        )
    if not _autoridad_valida(db, ctx.company_id, str(cargo.id), hoy, accion, materia):
        raise KontrolError(
            code="GOV_PAYMENT_AUTHORITY_INVALID",
            message="El cargo no tiene la competencia en vigor para autorizar el pago",
            field_errors={"cargo_id": ["Competencia ausente"]},
            status_code=422,
        )
    exigir_autoridad_funcional(db, ctx, str(cargo.id), accion, materia)

    competencias = competencias_en_vigor(db, cargo, hoy)
    for competencia in competencias:
        if (
            competencia.get("accion") == accion
            and competencia.get("materia") == materia
            and competencia.get("tipo_limite") == "MONTO"
        ):
            monto_competencia = (
                Decimal(str(competencia.get("monto")))
                if competencia.get("monto") is not None
                else None
            )
            moneda_competencia = competencia.get("moneda")
            if monto_competencia is None or not isinstance(moneda_competencia, str):
                raise KontrolError(
                    code="GOV_PAYMENT_AUTHORITY_LIMIT_EXCEEDED",
                    message="El monto excede el límite de la competencia de la autoridad",
                    field_errors={"cargo_id": ["Monto excedido"]},
                    status_code=422,
                )
            limite = verificar_limite(
                db,
                ctx,
                pago.moneda,
                pago.monto,
                monto_competencia,
                moneda_competencia,
                hoy,
                bloquear=True,
                exigir=True,
            )
            if not limite.get("dentro_del_limite", False):
                raise KontrolError(
                    code="GOV_PAYMENT_AUTHORITY_LIMIT_EXCEEDED",
                    message="El monto excede el límite de la competencia de la autoridad",
                    field_errors={"cargo_id": ["Monto excedido"]},
                    status_code=422,
                )

    if (pago.policy_snapshot or {}).get("exige_cargo_autorizado_cuenta"):
        autorizados = _autorizados_en_vigor(db, ctx, pago.account_id)
        if not any(
            autorizado.position_id == str(cargo.id)
            and autorizado.vigente_desde is not None
            and autorizado.vigente_desde <= hoy
            for autorizado in autorizados
        ):
            raise KontrolError(
                code="GOV_PAYMENT_ACCOUNT_SIGNATORY_REQUIRED",
                message="El cargo debe ser firmante de la cuenta del pago",
                status_code=422,
            )

    orden = _orden_de_empresa(db, ctx, str(pago.order_id), bloquear=True)
    evaluar_antes_de_actuar(db, ctx, "TRE04_AUTORIZAR", "GovernmentPaymentOrder", str(orden.id))

    documentos = cuerpo.get("documentos") or []
    validados = _validar_documentos_pago(db, ctx, orden, documentos)
    _guardar_documentos(db, ctx, pago, "AUTORIZAR", validados)

    funcionario_id = _funcionario_del_actor(db, ctx)
    funcionario = db.get(GovernmentOfficial, funcionario_id) if funcionario_id else None
    db.add(
        GovernmentPaymentApproval(
            payment_id=str(pago.id),
            company_id=ctx.company_id,
            decision="APROBADA",
            requisito_indice=requisito_indice,
            competencia_accion=accion,
            competencia_materia=materia,
            cargo_id=str(cargo.id),
            cargo_codigo=cargo.code,
            cargo_nombre=cargo.name,
            unidad=_unidad_nombre(db, cargo.unit_id),
            funcionario_id=funcionario_id,
            funcionario_nombre=funcionario.nombre if funcionario else None,
            actor_id=ctx.user_id,
            policy_numero_version=pago.policy_numero_version,
            created_by=ctx.user_id,
        )
    )

    completo = True
    for indice, req in enumerate(requisitos):
        aprobadas = db.scalars(
            select(GovernmentPaymentApproval).where(
                GovernmentPaymentApproval.company_id == ctx.company_id,
                GovernmentPaymentApproval.payment_id == pago.id,
                GovernmentPaymentApproval.decision == "APROBADA",
                GovernmentPaymentApproval.requisito_indice == indice,
            )
        ).all()
        if len(aprobadas) < int(req.get("cantidad", 0)):
            completo = False
            break

    if completo:
        _exigir_documentos(db, ctx, pago, "AUTORIZAR")
        pago.estado = "AUTORIZADO"
        evento = "AUTORIZADO"
    else:
        evento = "APROBADO"

    pago.version += 1
    _historia(db, ctx, pago, evento)
    _registrar_auditoria_tesoreria(
        db,
        ctx,
        "GOV_PAYMENT_APPROVED",
        str(pago.id),
        {"cargo": cargo.code, "codigo": pago.codigo, "completo": completo, "requisito": requisito_indice},
    )
    return obtener_pago(db, ctx, str(pago.id))


def rechazar_pago(
    db: Session,
    ctx: CompanyContext,
    payment_id: str,
    cuerpo: dict[str, Any],
    version: int | None,
) -> dict[str, Any]:
    pago = _pago_de_empresa(db, ctx, payment_id, bloquear=True)
    _if_match(pago, version)
    if pago.estado != "PENDIENTE_AUTORIZACION":
        raise ConflictError("GOV_PAYMENT_NOT_PENDING", "El pago no está pendiente de autorización")

    _validar_maker_checker(db, ctx, pago)

    cargo_id = cuerpo.get("cargo_id")
    if not isinstance(cargo_id, str):
        raise KontrolError(
            code="GOV_PAYMENT_AUTHORITY_INVALID",
            message="El cargo de autorización es obligatorio",
            field_errors={"cargo_id": ["Cargo obligatorio"]},
            status_code=422,
        )
    cargo = db.get(GovernmentPosition, cargo_id)
    if cargo is None or cargo.company_id != ctx.company_id:
        raise NotFoundError("GOV_POSITION_NOT_FOUND", "Cargo no encontrado")

    requisitos = (pago.policy_snapshot or {}).get("banda", {}).get("requisitos") or []
    hoy = hoy_de_negocio()
    competencia_valida = False
    for requisito in requisitos:
        accion = requisito.get("accion")
        materia = requisito.get("materia")
        if isinstance(accion, str) and isinstance(materia, str) and _autoridad_valida(
            db, ctx.company_id, str(cargo.id), hoy, accion, materia
        ):
            competencia_valida = True
            exigir_autoridad_funcional(db, ctx, str(cargo.id), accion, materia)
            break
    if not competencia_valida:
        raise KontrolError(
            code="GOV_PAYMENT_AUTHORITY_INVALID",
            message="El cargo no tiene la competencia en vigor para rechazar el pago",
            field_errors={"cargo_id": ["Competencia ausente"]},
            status_code=422,
        )

    motivo = cuerpo.get("motivo")
    if not isinstance(motivo, str) or not motivo.strip():
        raise KontrolError(
            code="GOV_PAYMENT_REASON_REQUIRED",
            message="El motivo del rechazo es obligatorio",
            field_errors={"motivo": ["Motivo obligatorio"]},
            status_code=422,
        )

    instante = instante_actual()
    funcionario_id = _funcionario_del_actor(db, ctx)
    funcionario = db.get(GovernmentOfficial, funcionario_id) if funcionario_id else None
    db.add(
        GovernmentPaymentApproval(
            payment_id=str(pago.id),
            company_id=ctx.company_id,
            decision="RECHAZADA",
            requisito_indice=None,
            competencia_accion=None,
            competencia_materia=None,
            motivo=motivo.strip(),
            cargo_id=str(cargo.id),
            cargo_codigo=cargo.code,
            cargo_nombre=cargo.name,
            unidad=_unidad_nombre(db, cargo.unit_id),
            funcionario_id=funcionario_id,
            funcionario_nombre=funcionario.nombre if funcionario else None,
            actor_id=ctx.user_id,
            policy_numero_version=pago.policy_numero_version,
            created_by=ctx.user_id,
        )
    )

    pago.estado = "RECHAZADO"
    pago.rechazado_por = ctx.user_id
    pago.rechazado_en = instante
    pago.motivo_rechazo = motivo.strip()
    pago.version += 1

    _historia(db, ctx, pago, "RECHAZADO")
    _registrar_auditoria_tesoreria(
        db,
        ctx,
        "GOV_PAYMENT_REJECTED",
        str(pago.id),
        {"cargo": cargo.code, "codigo": pago.codigo, "motivo": motivo.strip()},
    )
    return obtener_pago(db, ctx, str(pago.id))


def registrar_pago(
    db: Session,
    ctx: CompanyContext,
    payment_id: str,
    cuerpo: dict[str, Any],
    version: int | None,
) -> dict[str, Any]:
    pago = _pago_de_empresa(db, ctx, payment_id, bloquear=True)
    idempotency_key = cuerpo.get("idempotency_key")
    if idempotency_key is not None:
        existente = db.scalar(
            select(GovernmentPayment).where(
                GovernmentPayment.company_id == ctx.company_id,
                GovernmentPayment.registro_idempotency_key == idempotency_key,
            )
        )
        if existente is not None:
            if str(existente.id) == str(pago.id):
                return obtener_pago(db, ctx, str(pago.id))
            raise ConflictError(
                "GOV_PAYMENT_IDEMPOTENCY_CONFLICT",
                "La clave de idempotencia ya fue usada en otro pago",
            )

    _if_match(pago, version)
    if pago.estado != "AUTORIZADO":
        raise ConflictError("GOV_PAYMENT_NOT_AUTHORIZED", "El pago no está autorizado")

    orden = _orden_de_empresa(db, ctx, str(pago.order_id), bloquear=True)
    if orden.estado != "EMITIDA":
        raise ConflictError("GOV_PAYMENT_ORDER_NOT_EMITTED", "La orden no está emitida")

    pagado = montos_pagados(db, ctx.company_id, [str(orden.id)]).get(str(orden.id), Decimal("0.00"))
    if pagado + pago.monto > orden.monto:
        raise ConflictError("GOV_PAYMENT_OVERPAYMENT", "El pago supera el monto de la orden")

    fecha_valor = cuerpo.get("fecha_valor")
    if not isinstance(fecha_valor, date):
        raise KontrolError(
            code="GOV_PAYMENT_VALUE_DATE_INVALID",
            message="La fecha de valor es inválida",
            status_code=422,
        )
    hoy = hoy_de_negocio()
    if fecha_valor < orden.fecha_orden or fecha_valor > hoy:
        raise KontrolError(
            code="GOV_PAYMENT_VALUE_DATE_INVALID",
            message="La fecha de valor no está dentro del rango permitido",
            status_code=422,
        )

    cuenta = db.get(GovernmentBankAccount, pago.account_id)
    if cuenta is None or not _en_vigor(cuenta, hoy):
        raise KontrolError(
            code="GOV_PAYMENT_ACCOUNT_INVALID",
            message="La cuenta del pago no está vigente",
            status_code=422,
        )

    medio = (pago.policy_snapshot or {}).get("medio") or {}
    referencia_externa = cuerpo.get("referencia_externa")
    referencia = (referencia_externa or "").strip() or None
    if medio.get("exige_referencia") and referencia is None:
        raise KontrolError(
            code="GOV_PAYMENT_REFERENCE_REQUIRED",
            message="La referencia externa es obligatoria",
            status_code=422,
        )
    patron = medio.get("patron_referencia")
    if patron and referencia is not None and not re.fullmatch(patron, referencia):
        raise KontrolError(
            code="GOV_PAYMENT_REFERENCE_INVALID",
            message="La referencia externa no cumple el patrón",
            status_code=422,
        )
    referencia_clave = None
    if referencia is not None:
        referencia_clave = referencia.upper()
        if medio.get("referencia_unica"):
            existente = db.scalar(
                select(GovernmentPayment).where(
                    GovernmentPayment.company_id == ctx.company_id,
                    GovernmentPayment.estado == "REGISTRADO",
                    GovernmentPayment.method_id == pago.method_id,
                    GovernmentPayment.referencia_clave == referencia_clave,
                )
            )
            if existente is not None:
                raise ConflictError("GOV_PAYMENT_DUPLICATE_REFERENCE", "La referencia ya fue registrada")

    documentos = cuerpo.get("documentos") or []
    validados = _validar_documentos_pago(db, ctx, orden, documentos)
    _guardar_documentos(db, ctx, pago, "REGISTRAR", validados)
    _exigir_documentos(db, ctx, pago, "REGISTRAR")

    instante = instante_actual()
    aprobaciones = db.scalars(
        select(GovernmentPaymentApproval).where(
            GovernmentPaymentApproval.company_id == ctx.company_id,
            GovernmentPaymentApproval.payment_id == pago.id,
            GovernmentPaymentApproval.decision == "APROBADA",
        ).order_by(GovernmentPaymentApproval.created_at)
    ).all()
    aprobaciones_ids = [a.actor_id for a in aprobaciones]

    huella = _sha256(
        {
            "codigo": pago.codigo,
            "orden": orden.codigo,
            "monto": f"{pago.monto:.2f}",
            "moneda": pago.moneda,
            "cuenta": cuenta.codigo,
            "medio": medio.get("codigo"),
            "fecha_valor": fecha_valor.isoformat(),
            "referencia": referencia,
            "aprobaciones": aprobaciones_ids,
        }
    )

    pago.estado = "REGISTRADO"
    pago.fecha_valor = fecha_valor
    pago.referencia_externa = referencia
    pago.referencia_clave = referencia_clave
    pago.registro_idempotency_key = idempotency_key
    pago.registrado_por = ctx.user_id
    pago.registrado_en = instante
    pago.huella = huella
    pago.version += 1

    try:
        with db.begin_nested():
            db.flush()
    except IntegrityError as error:
        if es_violacion_unica(error, "uq_gov_payments_referencia"):
            raise ConflictError("GOV_PAYMENT_DUPLICATE_REFERENCE", "La referencia ya fue registrada") from error
        if es_violacion_unica(error, "uq_gov_payments_registro_idempotency"):
            raise ConflictError("GOV_PAYMENT_IDEMPOTENCY_CONFLICT", "La clave de idempotencia ya fue usada") from error
        raise

    _historia(db, ctx, pago, "REGISTRADO")
    _registrar_auditoria_tesoreria(
        db,
        ctx,
        "GOV_PAYMENT_EXECUTED",
        str(pago.id),
        {
            "codigo": pago.codigo,
            "fecha_valor": fecha_valor.isoformat(),
            "medio": medio.get("codigo"),
            "monto": f"{pago.monto:.2f}",
            "referencia": referencia,
        },
    )
    return obtener_pago(db, ctx, str(pago.id))


def anular_pago(
    db: Session,
    ctx: CompanyContext,
    payment_id: str,
    cuerpo: dict[str, Any],
    version: int | None,
) -> dict[str, Any]:
    pago = _pago_de_empresa(db, ctx, payment_id, bloquear=True)
    if pago.estado == "REGISTRADO":
        raise ConflictError(
            "GOV_PAYMENT_NOT_CANCELLABLE",
            "Un pago ejecutado no se anula aquí: su reverso corresponde a TRE-07",
        )
    if pago.estado not in ("PENDIENTE_AUTORIZACION", "AUTORIZADO"):
        raise ConflictError("GOV_PAYMENT_NOT_CANCELLABLE", "El pago no se puede anular")
    _if_match(pago, version)

    orden = _orden_de_empresa(db, ctx, str(pago.order_id), bloquear=True)

    motivo = cuerpo.get("motivo")
    if not isinstance(motivo, str) or not motivo.strip():
        raise KontrolError(
            code="GOV_PAYMENT_REASON_REQUIRED",
            message="El motivo de la anulación es obligatorio",
            field_errors={"motivo": ["Motivo obligatorio"]},
            status_code=422,
        )

    documentos = cuerpo.get("documentos") or []
    validados = _validar_documentos_pago(db, ctx, orden, documentos)
    _guardar_documentos(db, ctx, pago, "ANULAR", validados)
    _exigir_documentos(db, ctx, pago, "ANULAR")

    estado_previo = pago.estado
    pago.estado = "ANULADO"
    pago.motivo_anulacion = motivo.strip()
    pago.anulado_por = ctx.user_id
    pago.anulado_en = instante_actual()
    pago.version += 1

    _historia(db, ctx, pago, "ANULADO")
    _registrar_auditoria_tesoreria(
        db,
        ctx,
        "GOV_PAYMENT_CANCELLED",
        str(pago.id),
        {"codigo": pago.codigo, "estado_previo": estado_previo, "motivo": motivo.strip()},
    )
    return obtener_pago(db, ctx, str(pago.id))
