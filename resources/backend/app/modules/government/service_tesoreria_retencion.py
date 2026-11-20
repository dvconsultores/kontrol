from __future__ import annotations

import csv
import io
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext
from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.core.integrity import es_violacion_unica
from app.modules.government.models import (
    TIPOS_PERSONA_RETENCION,
    GovernmentOfficial,
    GovernmentPayment,
    GovernmentPosition,
    GovernmentWithholdingHistory,
    GovernmentWithholdingReceipt,
    GovernmentWithholdingSettlement,
    GovernmentWithholdingSettlementLine,
)
from app.modules.government.motor_retenciones import (
    calcular as motor_calcular,
)
from app.modules.government.motor_retenciones import huella as motor_huella
from app.modules.government.proyeccion_retenciones import (
    liquidacion_activa,
    montos_de_pago,
)
from app.modules.government.service_actos import _autoridad_valida
from app.modules.government.service_identidad import (
    _funcionario_del_actor,
    exigir_autoridad_funcional,
)
from app.modules.government.service_presupuesto_causado import (
    _unidad_nombre,
    _username,
)
from app.modules.government.service_sod import (
    evaluar_antes_de_actuar,
    usuarios_equivalentes,
)
from app.modules.government.service_tasas import instantanea_tasa, tasa_aplicable
from app.modules.government.service_tesoreria_retencion_comprobantes import (
    emitir_comprobantes,
)
from app.modules.government.service_tesoreria_retencion_politicas import (
    elementos_por_codigo,
    instantanea_politica,
    listar_catalogo,
    politica_aplicable,
    politicas_aplicables,
    registrar_historia,
)
from app.shared.audit import record_audit
from app.shared.clock import hoy_de_negocio, instante_actual


def _auditar(
    db: Session,
    ctx: CompanyContext,
    action: str,
    settlement: GovernmentWithholdingSettlement,
    after: dict[str, Any],
) -> None:
    record_audit(
        db,
        action=action,
        entity_type="GovernmentWithholdingSettlement",
        entity_id=str(settlement.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after=after,
    )


def _liquidacion_de_empresa_bloqueada(
    db: Session, ctx: CompanyContext, settlement_id: str
) -> GovernmentWithholdingSettlement:
    liquidacion = db.scalars(
        select(GovernmentWithholdingSettlement)
        .where(
            GovernmentWithholdingSettlement.company_id == ctx.company_id,
            GovernmentWithholdingSettlement.id == settlement_id,
        )
        .with_for_update()
    ).one_or_none()
    if liquidacion is None:
        raise NotFoundError(
            "GOV_WITHHOLDING_SETTLEMENT_NOT_FOUND", "Liquidación no encontrada"
        )
    return liquidacion


def _pago_de_liquidacion(
    db: Session, ctx: CompanyContext, settlement: GovernmentWithholdingSettlement
) -> GovernmentPayment:
    pago = db.get(GovernmentPayment, settlement.payment_id)
    if pago is None or pago.company_id != ctx.company_id:
        raise NotFoundError("GOV_PAYMENT_NOT_FOUND", "Pago no encontrado")
    return pago


def _comprobantes(
    db: Session,
    ctx: CompanyContext,
    settlement_id: str,
) -> list[dict[str, Any]]:
    comprobantes = db.scalars(
        select(GovernmentWithholdingReceipt).where(
            GovernmentWithholdingReceipt.company_id == ctx.company_id,
            GovernmentWithholdingReceipt.settlement_id == settlement_id,
        )
    ).all()
    resultado: list[dict[str, Any]] = []
    for comprobante in comprobantes:
        snapshot = comprobante.snapshot or {}
        resultado.append(
            {
                "id": str(comprobante.id),
                "codigo": comprobante.codigo,
                "estado": comprobante.estado,
                "concepto_codigo": getattr(comprobante, "concepto_codigo", None),
                "monto": snapshot.get("total"),
                "sustituye_a_id": comprobante.sustituye_a_id,
                "emitido_en": comprobante.emitido_en,
            }
        )
    return resultado


def _liquidacion_a_dict(
    db: Session,
    ctx: CompanyContext,
    liquidacion: GovernmentWithholdingSettlement,
) -> dict[str, Any]:
    lineas = db.scalars(
        select(GovernmentWithholdingSettlementLine)
        .where(GovernmentWithholdingSettlementLine.settlement_id == liquidacion.id)
        .order_by(GovernmentWithholdingSettlementLine.orden)
    ).all()
    pago = _pago_de_liquidacion(db, ctx, liquidacion)
    politica_fuente = {
        "tipo_regla": liquidacion.policy_snapshot.get("tipo_regla"),
        "estado_verificacion": liquidacion.policy_snapshot.get("estado_verificacion"),
        "fuente_descripcion": liquidacion.policy_snapshot.get("fuente_descripcion"),
        "fuente_referencia": liquidacion.policy_snapshot.get("fuente_referencia"),
    }
    return {
        "id": str(liquidacion.id),
        "payment_id": str(liquidacion.payment_id),
        "pago_codigo": pago.codigo,
        "pago_estado": pago.estado,
        "policy_id": str(liquidacion.policy_id),
        "policy_codigo": liquidacion.policy_snapshot.get("codigo"),
        "policy_numero_version": liquidacion.policy_numero_version,
        "estado": liquidacion.estado,
        "fecha_referencia": liquidacion.fecha_referencia,
        "moneda": liquidacion.moneda,
        "bruto": f"{liquidacion.bruto:.2f}",
        "total_retenido": f"{liquidacion.total_retenido:.2f}",
        "neto": f"{liquidacion.neto:.2f}",
        "conceptos": liquidacion.conceptos,
        "beneficiario": liquidacion.beneficiario,
        "permite_ajuste": bool(liquidacion.policy_snapshot.get("permite_ajuste")),
        "politica_fuente": politica_fuente,
        "calculado_por": _username(db, liquidacion.calculado_por),
        "calculado_en": liquidacion.calculado_en,
        "aprobado_por": _username(db, liquidacion.aprobado_por)
        if liquidacion.aprobado_por
        else None,
        "aprobado_en": liquidacion.aprobado_en,
        "aprobador_cargo_codigo": liquidacion.aprobador_cargo_codigo,
        "aprobador_cargo_nombre": liquidacion.aprobador_cargo_nombre,
        "aprobador_funcionario_nombre": liquidacion.aprobador_funcionario_nombre,
        "aplicado_en": liquidacion.aplicado_en,
        "anulado_por": _username(db, liquidacion.anulado_por)
        if liquidacion.anulado_por
        else None,
        "anulado_en": liquidacion.anulado_en,
        "motivo_anulacion": liquidacion.motivo_anulacion,
        "huella": liquidacion.huella,
        "version": liquidacion.version,
        "lineas": [
            {
                "id": str(linea.id),
                "orden": int(linea.orden),
                "concepto_codigo": linea.concepto_codigo,
                "concepto_nombre": linea.concepto_nombre,
                "clase": linea.clase,
                "base": str(linea.base),
                "tasa": f"{linea.tasa:.4f}",
                "umbral": str(linea.umbral) if linea.umbral is not None else None,
                "tasa_referencia": linea.tasa_referencia,
                "aplica": linea.aplica,
                "motivo_no_aplica": linea.motivo_no_aplica,
                "monto_calculado": str(linea.monto_calculado),
                "monto_aprobado": str(linea.monto_aprobado),
                "motivo_ajuste": linea.motivo_ajuste,
                "ajustado_por": _username(db, linea.ajustado_por)
                if linea.ajustado_por
                else None,
                "ajustado_en": linea.ajustado_en,
                "exige_comprobante": linea.exige_comprobante,
            }
            for linea in lineas
        ],
        "comprobantes": _comprobantes(db, ctx, str(liquidacion.id)),
    }


def _validar_if_match(liquidacion: GovernmentWithholdingSettlement, version: int | None) -> None:
    if version is None:
        raise KontrolError(
            code="GOV_WITHHOLDING_IF_MATCH_REQUIRED",
            message="If-Match es obligatorio",
            status_code=428,
        )
    if version != liquidacion.version:
        raise ConflictError(
            "GOV_WITHHOLDING_VERSION_CONFLICT", "La versión no coincide"
        )


def _validar_estado_calculada(liquidacion: GovernmentWithholdingSettlement) -> None:
    if liquidacion.estado != "CALCULADA":
        raise ConflictError(
            "GOV_WITHHOLDING_NOT_CALCULATED",
            "La liquidación no está calculada",
        )


def opciones(db: Session, ctx: CompanyContext, payment_id: str) -> dict[str, Any]:
    pago = _pago_de_empresa_simple(db, ctx, payment_id)
    politicas = politicas_aplicables(db, ctx, pago.moneda, pago.fecha_pago)
    conceptos = listar_catalogo(db, ctx, "CONCEPTO")
    condiciones = listar_catalogo(db, ctx, "CONDICION")
    liquidacion = liquidacion_activa(db, ctx.company_id, str(pago.id))
    return {
        "pago": {
            "id": str(pago.id),
            "codigo": pago.codigo,
            "estado": pago.estado,
            "moneda": pago.moneda,
            "monto": str(pago.monto),
            "fecha_pago": pago.fecha_pago,
        },
        "politicas": [
            {
                "id": str(politica.id),
                "codigo": politica.codigo,
                "numero_version": politica.numero_version,
                "nombre": politica.nombre,
                "permite_ajuste": instantanea_politica(db, ctx, politica)["permite_ajuste"],
                "conceptos": [
                    str(regla.get("concepto_codigo"))
                    for regla in instantanea_politica(db, ctx, politica)["reglas"]
                ],
            }
            for politica in politicas
        ],
        "conceptos": conceptos,
        "condiciones": condiciones,
        "tipos_persona": list(TIPOS_PERSONA_RETENCION),
        "liquidacion": (
            _liquidacion_a_dict(db, ctx, liquidacion) if liquidacion else None
        ),
    }


def liquidacion_del_pago(db: Session, ctx: CompanyContext, payment_id: str) -> dict[str, Any]:
    pago = _pago_de_empresa_simple(db, ctx, payment_id)
    activa = liquidacion_activa(db, ctx.company_id, str(pago.id))
    return {
        "montos": montos_de_pago(db, ctx, pago),
        "liquidacion": _liquidacion_a_dict(db, ctx, activa) if activa else None,
    }


def calcular(
    db: Session,
    ctx: CompanyContext,
    payment_id: str,
    cuerpo: dict[str, Any],
) -> dict[str, Any]:
    pago = _pago_de_empresa_simple(db, ctx, payment_id, bloquear=True)
    if pago.estado not in {"BORRADOR", "PENDIENTE_AUTORIZACION", "AUTORIZADO"}:
        raise ConflictError(
            "GOV_WITHHOLDING_PAYMENT_STATE",
            "El pago no admite cálculo de retenciones",
        )
    if liquidacion_activa(db, ctx.company_id, str(pago.id)) is not None:
        raise ConflictError(
            "GOV_WITHHOLDING_SETTLEMENT_EXISTS",
            "La liquidación de retenciones del pago ya existe",
        )
    policy_id = cuerpo.get("policy_id")
    if not isinstance(policy_id, str) or not policy_id.strip():
        raise KontrolError(
            code="GOV_WITHHOLDING_POLICY_NOT_APPLICABLE",
            message="La política no es aplicable",
            field_errors={"policy_id": ["Obligatorio"]},
            status_code=422,
        )
    politica = politica_aplicable(
        db, ctx, policy_id, pago.moneda, pago.fecha_pago
    )
    snapshot = instantanea_politica(db, ctx, politica)

    conceptos = cuerpo.get("conceptos")
    if not isinstance(conceptos, list) or not conceptos or len(conceptos) != len(
        set(conceptos)
    ):
        raise KontrolError(
            code="GOV_WITHHOLDING_CONCEPTOS_INVALID",
            message="Los conceptos son inválidos",
            field_errors={"conceptos": ["Lista obligatoria y sin repetidos"]},
            status_code=422,
        )
    elementos_por_codigo(db, ctx, "CONCEPTO", conceptos)

    beneficiario = cuerpo.get("beneficiario") or {}
    errores_beneficiario: dict[str, list[str]] = {}
    nombre = beneficiario.get("nombre")
    if not isinstance(nombre, str) or not 3 <= len(nombre) <= 200:
        errores_beneficiario["nombre"] = ["Nombre entre 3 y 200 caracteres"]
    identificacion_fiscal = beneficiario.get("identificacion_fiscal")
    if identificacion_fiscal is not None and (
        not isinstance(identificacion_fiscal, str) or len(identificacion_fiscal) > 30
    ):
        errores_beneficiario["identificacion_fiscal"] = [
            "Máximo 30 caracteres"
        ]
    tipo_persona = beneficiario.get("tipo_persona")
    if tipo_persona not in TIPOS_PERSONA_RETENCION:
        errores_beneficiario["tipo_persona"] = ["Tipo de persona inválido"]
    condiciones = beneficiario.get("condiciones")
    if not isinstance(condiciones, list):
        errores_beneficiario["condiciones"] = ["Lista requerida"]
    else:
        try:
            elementos_por_codigo(db, ctx, "CONDICION", condiciones)
        except KontrolError:
            errores_beneficiario["condiciones"] = ["Código desconocido"]
    if errores_beneficiario:
        raise KontrolError(
            code="GOV_WITHHOLDING_BENEFICIARY_INVALID",
            message="Beneficiario inválido",
            field_errors={
                f"beneficiario.{campo}": mensajes
                for campo, mensajes in errores_beneficiario.items()
            },
            status_code=422,
        )

    tasas: dict[str, dict[str, Any]] = {}
    for regla in snapshot["reglas"]:
        if regla.get("umbral_tipo") == "MULTIPLO_TASA":
            moneda_tasa = str(regla.get("umbral_moneda_tasa"))
            if moneda_tasa not in tasas:
                tasa = tasa_aplicable(db, ctx, moneda_tasa, pago.fecha_pago)
                if tasa is not None:
                    tasas[moneda_tasa] = instantanea_tasa(tasa)

    lineas_calculadas, total = motor_calcular(
        snapshot,
        conceptos,
        {
            "nombre": nombre,
            "identificacion_fiscal": identificacion_fiscal,
            "tipo_persona": tipo_persona,
            "condiciones": condiciones or [],
        },
        pago.monto,
        tasas,
    )

    neto = pago.monto - total
    liquidacion = GovernmentWithholdingSettlement(
        company_id=ctx.company_id,
        payment_id=payment_id,
        policy_id=snapshot["id"],
        policy_numero_version=snapshot["numero_version"],
        policy_snapshot=snapshot,
        estado="CALCULADA",
        fecha_referencia=pago.fecha_pago,
        moneda=pago.moneda,
        bruto=pago.monto,
        total_retenido=total,
        neto=neto,
        conceptos=conceptos,
        beneficiario={
            "nombre": nombre,
            "identificacion_fiscal": identificacion_fiscal,
            "tipo_persona": tipo_persona,
            "condiciones": condiciones or [],
        },
        calculado_por=ctx.user_id,
        calculado_en=instante_actual(),
        version=1,
    )
    db.add(liquidacion)
    db.flush()
    for linea in lineas_calculadas:
        db.add(
            GovernmentWithholdingSettlementLine(
                settlement_id=str(liquidacion.id),
                company_id=ctx.company_id,
                orden=linea["orden"],
                rule_snapshot=linea["rule_snapshot"],
                concept_id=linea["concept_id"],
                concepto_codigo=linea["concepto_codigo"],
                concepto_nombre=linea["concepto_nombre"],
                clase=linea["clase"],
                base=linea["base"],
                tasa=linea["tasa"],
                umbral=linea["umbral"],
                tasa_referencia=linea["tasa_referencia"],
                aplica=linea["aplica"],
                motivo_no_aplica=linea["motivo_no_aplica"],
                monto_calculado=linea["monto_calculado"],
                monto_aprobado=linea["monto_aprobado"],
                exige_comprobante=linea["exige_comprobante"],
            )
        )
    try:
        db.flush()
    except IntegrityError as exc:
        if es_violacion_unica(exc, "uq_gov_withholding_settlements_activa"):
            raise ConflictError(
                "GOV_WITHHOLDING_SETTLEMENT_EXISTS",
                "La liquidación de retenciones del pago ya existe",
            ) from exc
        raise
    registrar_historia(db, ctx, "LIQUIDACION", str(liquidacion.id), "CALCULADA", snapshot)
    _auditar(
        db,
        ctx,
        "GOV_WITHHOLDING_CALCULATED",
        liquidacion,
        {
            "pago": pago.codigo,
            "politica": snapshot["codigo"],
            "bruto": f"{liquidacion.bruto:.2f}",
            "total_retenido": f"{liquidacion.total_retenido:.2f}",
            "neto": f"{liquidacion.neto:.2f}",
        },
    )
    return _liquidacion_a_dict(db, ctx, liquidacion)


def ajustar_linea(
    db: Session,
    ctx: CompanyContext,
    settlement_id: str,
    linea_id: str,
    cuerpo: dict[str, Any],
    version: int | None,
) -> dict[str, Any]:
    liquidacion = _liquidacion_de_empresa_bloqueada(db, ctx, settlement_id)
    _validar_if_match(liquidacion, version)
    _validar_estado_calculada(liquidacion)

    if not bool(liquidacion.policy_snapshot.get("permite_ajuste")):
        raise KontrolError(
            code="GOV_WITHHOLDING_ADJUSTMENT_FORBIDDEN",
            message="La política no permite ajustes",
            status_code=422,
        )
    linea = db.scalars(
        select(GovernmentWithholdingSettlementLine).where(
            GovernmentWithholdingSettlementLine.id == linea_id,
            GovernmentWithholdingSettlementLine.settlement_id == str(liquidacion.id),
        )
    ).one_or_none()
    if linea is None or not linea.aplica:
        raise KontrolError(
            code="GOV_WITHHOLDING_ADJUSTMENT_FORBIDDEN",
            message="La línea no admite ajuste",
            status_code=422,
        )
    try:
        monto_aprobado = Decimal(str(cuerpo.get("monto_aprobado")))
    except (InvalidOperation, TypeError) as exc:
        raise KontrolError(
            code="GOV_WITHHOLDING_ADJUSTMENT_INVALID",
            message="Monto inválido",
            field_errors={"monto_aprobado": ["Decimal requerido"]},
            status_code=422,
        ) from exc
    decimales = int(liquidacion.policy_snapshot["redondeo_decimales"])
    cuantum = Decimal(1).scaleb(-decimales)
    monto_aprobado = Decimal(0) + monto_aprobado.quantize(cuantum)
    if monto_aprobado < 0 or monto_aprobado > linea.base:
        raise KontrolError(
            code="GOV_WITHHOLDING_ADJUSTMENT_INVALID",
            message="Monto fuera de rango",
            field_errors={"monto_aprobado": ["Entre 0 y la base"]},
            status_code=422,
        )
    motivo = cuerpo.get("motivo")
    motivo_limpio: str | None = None
    if monto_aprobado != linea.monto_calculado:
        if not isinstance(motivo, str) or len(motivo.strip()) < 10:
            raise KontrolError(
                code="GOV_WITHHOLDING_ADJUSTMENT_INVALID",
                message="Motivo de ajuste requerido",
                field_errors={"motivo": ["Mínimo 10 caracteres"]},
                status_code=422,
            )
        motivo_limpio = motivo.strip()

    if monto_aprobado == linea.monto_calculado:
        linea.motivo_ajuste = None
        linea.ajustado_por = None
        linea.ajustado_en = None
    else:
        linea.motivo_ajuste = motivo_limpio
        linea.ajustado_por = ctx.user_id
        linea.ajustado_en = instante_actual()
    linea.monto_aprobado = monto_aprobado

    lineas_actuales = db.scalars(
        select(GovernmentWithholdingSettlementLine).where(
            GovernmentWithholdingSettlementLine.settlement_id == str(liquidacion.id)
        )
    ).all()
    total = sum((linea.monto_aprobado for linea in lineas_actuales), Decimal("0"))
    if total > liquidacion.bruto:
        raise KontrolError(
            code="GOV_WITHHOLDING_EXCEEDS_GROSS",
            message="El total retenido excede el bruto",
            status_code=422,
        )
    liquidacion.total_retenido = total
    liquidacion.neto = liquidacion.bruto - total
    liquidacion.version += 1
    db.flush()
    registrar_historia(db, ctx, "LIQUIDACION", str(liquidacion.id), "AJUSTADA", {})
    _auditar(
        db,
        ctx,
        "GOV_WITHHOLDING_ADJUSTED",
        liquidacion,
        {
            "linea": str(linea.id),
            "monto_calculado": f"{linea.monto_calculado:.2f}",
            "monto_aprobado": f"{linea.monto_aprobado:.2f}",
            "motivo": linea.motivo_ajuste,
        },
    )
    return _liquidacion_a_dict(db, ctx, liquidacion)


def aprobar(
    db: Session,
    ctx: CompanyContext,
    settlement_id: str,
    cuerpo: dict[str, Any],
    version: int | None,
) -> dict[str, Any]:
    liquidacion = _liquidacion_de_empresa_bloqueada(db, ctx, settlement_id)
    _validar_if_match(liquidacion, version)
    _validar_estado_calculada(liquidacion)
    pago = _pago_de_liquidacion(db, ctx, liquidacion)
    if pago.estado in {"REGISTRADO", "RECHAZADO", "ANULADO"}:
        raise ConflictError(
            "GOV_WITHHOLDING_PAYMENT_STATE",
            "El pago no admite aprobación de retenciones",
        )
    actores = usuarios_equivalentes(db, ctx, ctx.user_id)
    lineas = db.scalars(
        select(GovernmentWithholdingSettlementLine).where(
            GovernmentWithholdingSettlementLine.settlement_id == str(liquidacion.id)
        )
    ).all()
    if liquidacion.calculado_por in actores or any(
        linea.ajustado_por and linea.ajustado_por in actores for linea in lineas
    ):
        raise ConflictError(
            "GOV_WITHHOLDING_MAKER_CHECKER",
            "Quien calculó o ajustó no puede aprobar",
        )
    cargo_id = cuerpo.get("cargo_id")
    if not isinstance(cargo_id, str):
        raise KontrolError(
            code="GOV_WITHHOLDING_AUTHORITY_INVALID",
            message="Cargo de aprobación obligatorio",
            field_errors={"cargo_id": ["Cargo obligatorio"]},
            status_code=422,
        )
    cargo = db.get(GovernmentPosition, cargo_id)
    if cargo is None or cargo.company_id != ctx.company_id:
        raise NotFoundError("GOV_POSITION_NOT_FOUND", "Cargo no encontrado")
    accion = liquidacion.policy_snapshot.get("aprobador_competencia_accion")
    materia = liquidacion.policy_snapshot.get("aprobador_competencia_materia")
    if not isinstance(accion, str) or not isinstance(materia, str):
        raise KontrolError(
            code="GOV_WITHHOLDING_AUTHORITY_INVALID",
            message="La política no define la competencia",
            status_code=422,
        )
    if not _autoridad_valida(db, ctx.company_id, str(cargo.id), hoy_de_negocio(), accion, materia):
        raise KontrolError(
            code="GOV_WITHHOLDING_AUTHORITY_INVALID",
            message="El cargo no tiene competencia",
            field_errors={"cargo_id": ["Competencia ausente"]},
            status_code=422,
        )
    exigir_autoridad_funcional(db, ctx, str(cargo.id), accion, materia)
    evaluar_antes_de_actuar(db, ctx, "TRE05_APROBAR", "GovernmentPayment", str(pago.id))

    datos_huella = {
        "pago": str(pago.id),
        "politica": {
            "codigo": liquidacion.policy_snapshot.get("codigo"),
            "numero_version": liquidacion.policy_numero_version,
        },
        "bruto": str(liquidacion.bruto),
        "total": str(liquidacion.total_retenido),
        "neto": str(liquidacion.neto),
        "beneficiario": liquidacion.beneficiario,
        "conceptos": liquidacion.conceptos,
        "lineas": [
            {
                "concepto_codigo": linea.concepto_codigo,
                "base": str(linea.base),
                "tasa": str(linea.tasa),
                "monto_aprobado": str(linea.monto_aprobado),
                "aplica": linea.aplica,
            }
            for linea in lineas
        ],
    }
    liquidacion.aprobado_por = ctx.user_id
    liquidacion.aprobado_en = instante_actual()
    liquidacion.aprobador_cargo_id = str(cargo.id)
    liquidacion.aprobador_cargo_codigo = cargo.code
    liquidacion.aprobador_cargo_nombre = cargo.name
    liquidacion.aprobador_unidad = _unidad_nombre(db, cargo.unit_id)
    funcionario_id = _funcionario_del_actor(db, ctx)
    funcionario = db.get(GovernmentOfficial, funcionario_id) if funcionario_id else None
    liquidacion.aprobador_funcionario_id = funcionario_id
    liquidacion.aprobador_funcionario_nombre = funcionario.nombre if funcionario else None
    liquidacion.huella = motor_huella(datos_huella)
    liquidacion.estado = "APROBADA"
    liquidacion.version += 1
    db.flush()
    registrar_historia(db, ctx, "LIQUIDACION", str(liquidacion.id), "APROBADA", {})
    _auditar(
        db,
        ctx,
        "GOV_WITHHOLDING_APPROVED",
        liquidacion,
        {
            "pago": pago.codigo,
            "cargo": cargo.code,
            "total_retenido": f"{liquidacion.total_retenido:.2f}",
            "huella": liquidacion.huella,
        },
    )
    return _liquidacion_a_dict(db, ctx, liquidacion)


def anular(
    db: Session,
    ctx: CompanyContext,
    settlement_id: str,
    cuerpo: dict[str, Any],
    version: int | None,
) -> dict[str, Any]:
    liquidacion = _liquidacion_de_empresa_bloqueada(db, ctx, settlement_id)
    _validar_if_match(liquidacion, version)
    motivo = cuerpo.get("motivo")
    if not isinstance(motivo, str) or len(motivo.strip()) < 10:
        raise KontrolError(
            code="GOV_WITHHOLDING_REASON_REQUIRED",
            message="Motivo de anulación requerido",
            field_errors={"motivo": ["Mínimo 10 caracteres"]},
            status_code=422,
        )
    if liquidacion.estado == "APLICADA":
        raise ConflictError(
            "GOV_WITHHOLDING_APPLIED_IMMUTABLE",
            "La liquidación aplicada no puede anularse",
        )
    if liquidacion.estado == "ANULADA":
        raise ConflictError(
            "GOV_WITHHOLDING_ALREADY_CANCELLED", "La liquidación ya está anulada"
        )
    liquidacion.anulado_por = ctx.user_id
    liquidacion.anulado_en = instante_actual()
    estado_previo = liquidacion.estado
    liquidacion.motivo_anulacion = motivo.strip()
    liquidacion.estado = "ANULADA"
    liquidacion.version += 1
    db.flush()
    registrar_historia(db, ctx, "LIQUIDACION", str(liquidacion.id), "ANULADA", {})
    _auditar(
        db,
        ctx,
        "GOV_WITHHOLDING_CANCELLED",
        liquidacion,
        {
            "pago": _pago_de_liquidacion(db, ctx, liquidacion).codigo,
            "estado_previo": estado_previo,
            "motivo": liquidacion.motivo_anulacion,
        },
    )
    return _liquidacion_a_dict(db, ctx, liquidacion)


def estado_de(db: Session, ctx: CompanyContext, settlement_id: str) -> str:
    liquidacion = liquidacion_de_empresa(db, ctx, settlement_id)
    return liquidacion.estado


def listar(
    db: Session,
    ctx: CompanyContext,
    estado: str | None,
    desde: date | None,
    hasta: date | None,
    payment_id: str | None,
) -> list[dict[str, Any]]:
    query = select(GovernmentWithholdingSettlement).where(
        GovernmentWithholdingSettlement.company_id == ctx.company_id
    )
    if estado:
        query = query.where(GovernmentWithholdingSettlement.estado == estado)
    if desde:
        query = query.where(GovernmentWithholdingSettlement.fecha_referencia >= desde)
    if hasta:
        query = query.where(GovernmentWithholdingSettlement.fecha_referencia <= hasta)
    if payment_id:
        query = query.where(GovernmentWithholdingSettlement.payment_id == payment_id)
    query = query.order_by(
        GovernmentWithholdingSettlement.fecha_referencia.desc(),
        GovernmentWithholdingSettlement.created_at.desc(),
    )
    liquidaciones = db.scalars(query).all()
    resultado: list[dict[str, Any]] = []
    for liquidacion in liquidaciones:
        pago = _pago_de_liquidacion(db, ctx, liquidacion)
        resultado.append(
            {
                "id": str(liquidacion.id),
                "payment_id": str(liquidacion.payment_id),
                "pago_codigo": pago.codigo,
                "policy_codigo": liquidacion.policy_snapshot.get("codigo"),
                "policy_numero_version": liquidacion.policy_numero_version,
                "estado": liquidacion.estado,
                "fecha_referencia": liquidacion.fecha_referencia,
                "moneda": liquidacion.moneda,
                "bruto": f"{liquidacion.bruto:.2f}",
                "total_retenido": f"{liquidacion.total_retenido:.2f}",
                "neto": f"{liquidacion.neto:.2f}",
                "beneficiario_nombre": liquidacion.beneficiario.get("nombre"),
                "comprobantes": len(
                    _comprobantes(db, ctx, str(liquidacion.id))
                ),
            }
        )
    return resultado


def reporte_csv(
    db: Session,
    ctx: CompanyContext,
    estado: str | None,
    desde: date | None,
    hasta: date | None,
) -> str:
    resumenes = listar(db, ctx, estado, desde, hasta, None)
    salida = io.StringIO()
    writer = csv.writer(salida)
    writer.writerow(
        [
            "liquidacion",
            "pago",
            "politica",
            "version",
            "estado",
            "fecha",
            "moneda",
            "bruto",
            "total_retenido",
            "neto",
            "beneficiario",
            "identificacion_fiscal",
            "comprobantes",
        ]
    )
    for resumen in resumenes:
        liquidacion_id = resumen["id"]
        liquidacion = liquidacion_de_empresa(db, ctx, liquidacion_id)
        beneficiario = liquidacion.beneficiario or {}
        writer.writerow(
            [
                liquidacion_id,
                resumen["pago_codigo"],
                resumen["policy_codigo"],
                resumen["policy_numero_version"],
                resumen["estado"],
                resumen["fecha_referencia"],
                resumen["moneda"],
                resumen["bruto"],
                resumen["total_retenido"],
                resumen["neto"],
                beneficiario.get("nombre"),
                beneficiario.get("identificacion_fiscal"),
                resumen["comprobantes"],
            ]
        )
    return salida.getvalue()


def obtener(
    db: Session, ctx: CompanyContext, settlement_id: str
) -> dict[str, Any]:
    liquidacion = liquidacion_de_empresa(db, ctx, settlement_id)
    return _liquidacion_a_dict(db, ctx, liquidacion)


def historia(db: Session, ctx: CompanyContext, settlement_id: str) -> list[dict[str, Any]]:
    liquidacion_de_empresa(db, ctx, settlement_id)
    registros = db.scalars(
        select(GovernmentWithholdingHistory)
        .where(
            GovernmentWithholdingHistory.company_id == ctx.company_id,
            GovernmentWithholdingHistory.recurso == "LIQUIDACION",
            GovernmentWithholdingHistory.recurso_id == settlement_id,
        )
        .order_by(GovernmentWithholdingHistory.created_at)
    ).all()
    return [
        {
            "id": str(registro.id),
            "evento": registro.evento,
            "actor_id": registro.created_by,
            "created_at": registro.created_at,
            "instantanea": registro.instantanea,
        }
        for registro in registros
    ]


def liquidacion_de_empresa(
    db: Session,
    ctx: CompanyContext,
    id: str,
    bloquear: bool = False,
) -> GovernmentWithholdingSettlement:
    query = select(GovernmentWithholdingSettlement).where(
        GovernmentWithholdingSettlement.company_id == ctx.company_id,
        GovernmentWithholdingSettlement.id == id,
    )
    if bloquear:
        query = query.with_for_update()
    liquidacion = db.scalars(query).one_or_none()
    if liquidacion is None:
        raise NotFoundError(
            "GOV_WITHHOLDING_SETTLEMENT_NOT_FOUND", "Liquidación no encontrada"
        )
    return liquidacion


def al_registrar_pago(
    db: Session, ctx: CompanyContext, pago: GovernmentPayment
) -> None:
    activa = db.scalars(
        select(GovernmentWithholdingSettlement)
        .where(
            GovernmentWithholdingSettlement.company_id == ctx.company_id,
            GovernmentWithholdingSettlement.payment_id == str(pago.id),
            GovernmentWithholdingSettlement.estado != "ANULADA",
        )
        .with_for_update()
    ).one_or_none()
    if activa is None:
        return
    if activa.estado == "CALCULADA":
        raise ConflictError(
            "GOV_WITHHOLDING_PENDING_APPROVAL",
            "La liquidación de retenciones del pago está pendiente de aprobación",
        )
    if activa.estado == "APROBADA":
        activa.estado = "APLICADA"
        activa.aplicado_en = instante_actual()
        activa.version += 1
        db.flush()
        registrar_historia(db, ctx, "LIQUIDACION", str(activa.id), "APLICADA", {})
        _auditar(
            db,
            ctx,
            "GOV_WITHHOLDING_APPLIED",
            activa,
            {
                "pago": pago.codigo,
                "total_retenido": f"{activa.total_retenido:.2f}",
                "neto": f"{activa.neto:.2f}",
            },
        )
        emitir_comprobantes(db, ctx, activa)


def al_cancelar_pago(
    db: Session, ctx: CompanyContext, pago: GovernmentPayment, motivo: str
) -> None:
    activa = db.scalars(
        select(GovernmentWithholdingSettlement)
        .where(
            GovernmentWithholdingSettlement.company_id == ctx.company_id,
            GovernmentWithholdingSettlement.payment_id == str(pago.id),
            GovernmentWithholdingSettlement.estado != "ANULADA",
        )
        .with_for_update()
    ).one_or_none()
    if activa is None:
        return
    if activa.estado == "APLICADA":
        return
    estado_previo = activa.estado
    activa.motivo_anulacion = (f"Pago {pago.estado.lower()}: {motivo}")[:500]
    activa.anulado_por = ctx.user_id
    activa.anulado_en = instante_actual()
    activa.estado = "ANULADA"
    activa.version += 1
    db.flush()
    registrar_historia(db, ctx, "LIQUIDACION", str(activa.id), "ANULADA", {})
    _auditar(
        db,
        ctx,
        "GOV_WITHHOLDING_CANCELLED",
        activa,
        after={
            "pago": pago.codigo,
            "estado_previo": estado_previo,
            "motivo": activa.motivo_anulacion,
        },
    )


def _pago_de_empresa_simple(
    db: Session, ctx: CompanyContext, payment_id: str, bloquear: bool = False
) -> GovernmentPayment:
    query = select(GovernmentPayment).where(
        GovernmentPayment.company_id == ctx.company_id,
        GovernmentPayment.id == payment_id,
    )
    if bloquear:
        query = query.with_for_update()
    pago = db.scalars(query).one_or_none()
    if pago is None:
        raise NotFoundError("GOV_PAYMENT_NOT_FOUND", "Pago no encontrado")
    return pago
