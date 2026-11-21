from __future__ import annotations

import hashlib
import json
from decimal import ROUND_DOWN, ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal
from typing import Any

from app.core.errors import KontrolError


def _redondear(valor: Decimal, decimales: int, modo: str) -> Decimal:
    redondeo = {
        "HALF_UP": ROUND_HALF_UP,
        "HALF_EVEN": ROUND_HALF_EVEN,
        "DOWN": ROUND_DOWN,
    }[modo]
    return Decimal(0) + valor.quantize(Decimal(1).scaleb(-decimales), rounding=redondeo)


def calcular(
    politica: dict[str, Any],
    conceptos: list[str],
    beneficiario: dict[str, Any],
    bruto: Decimal,
    tasas: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], Decimal]:
    decimales = int(politica["redondeo_decimales"])
    modo = str(politica["redondeo_modo"])
    reglas: list[dict[str, Any]] = sorted(
        politica["reglas"], key=lambda regla: int(regla["orden"])
    )
    seleccionados = set(conceptos)
    reglas_por_concepto = {str(r.get("concepto_codigo")): r for r in reglas}
    faltantes = [
        codigo for codigo in seleccionados if codigo not in reglas_por_concepto
    ]
    if faltantes:
        raise KontrolError(
            code="GOV_WITHHOLDING_CONCEPT_NOT_IN_POLICY",
            message="El concepto no tiene regla en la política",
            field_errors={"conceptos": faltantes},
            status_code=422,
        )

    lineas: list[dict[str, Any]] = []
    for regla in reglas:
        codigo = str(regla.get("concepto_codigo", ""))
        aplica = True
        motivo_no_aplica: str | None = None
        base = Decimal("0")
        umbral: Decimal | None = None
        tasa_referencia: dict[str, Any] | None = None
        monto = Decimal("0")

        # Concepto elegido
        if codigo not in seleccionados:
            aplica = False
            motivo_no_aplica = "CONCEPTO_NO_SELECCIONADO"

        # Tipo de persona
        if aplica and regla.get("tipos_persona") is not None:
            tipos = regla.get("tipos_persona") or []
            if beneficiario.get("tipo_persona") not in tipos:
                aplica = False
                motivo_no_aplica = "TIPO_PERSONA"

        # Condiciones exigidas
        if aplica and (regla.get("condiciones_exigidas") or []) and not set(
            regla.get("condiciones_exigidas") or []
        ).issubset(set(beneficiario.get("condiciones") or [])):
            aplica = False
            motivo_no_aplica = "CONDICION_FALTANTE"

        # Exclusiones
        if aplica and set(regla.get("exclusiones") or []).intersection(
            set(beneficiario.get("condiciones") or [])
        ):
            aplica = False
            motivo_no_aplica = "EXCLUSION"

        # Base
        if aplica:
            base_tipo = regla.get("base_tipo")
            if base_tipo == "MONTO_BRUTO":
                base = bruto
            elif base_tipo == "PORCENTAJE_DEL_BRUTO":
                base = _redondear(
                    bruto * Decimal(str(regla.get("base_porcentaje", 0))) / Decimal("100"),
                    decimales,
                    modo,
                )
            else:
                raise KontrolError(
                    code="GOV_WITHHOLDING_RULE_INVALID",
                    message=f"base_tipo desconocido: {base_tipo!r}",
                    status_code=422,
                )

        # Umbral
        if aplica:
            umbral_tipo = regla.get("umbral_tipo")
            if umbral_tipo == "NINGUNO":
                umbral = None
            elif umbral_tipo == "MONTO":
                umbral = Decimal(str(regla.get("umbral_monto", 0)))
            elif umbral_tipo == "MULTIPLO_TASA":
                moneda_tasa = str(regla.get("umbral_moneda_tasa", ""))
                instantanea = tasas.get(moneda_tasa)
                if instantanea is None:
                    raise KontrolError(
                        code="GOV_WITHHOLDING_RATE_MISSING",
                        message="Falta la tasa para calcular el umbral",
                        status_code=422,
                    )
                umbral = _redondear(
                    Decimal(str(regla.get("umbral_multiplo", 0)))
                    * Decimal(str(instantanea["valor"])),
                    decimales,
                    modo,
                )
                tasa_referencia = instantanea
            else:
                raise KontrolError(
                    code="GOV_WITHHOLDING_RULE_INVALID",
                    message=f"umbral_tipo desconocido: {umbral_tipo!r}",
                    status_code=422,
                )

        # Umbral
        if aplica and umbral is not None and base < umbral:
            aplica = False
            motivo_no_aplica = "UMBRAL"

        # Monto
        if aplica:
            monto = _redondear(
                base * Decimal(str(regla.get("tasa", 0))) / Decimal("100"),
                decimales,
                modo,
            ) - Decimal(str(regla.get("sustraendo") or 0))
            tope = regla.get("tope")
            if tope is not None:
                tope_decimal = Decimal(str(tope))
                if monto > tope_decimal:
                    monto = tope_decimal
            if monto <= 0:
                aplica = False
                motivo_no_aplica = "SIN_MONTO"

        if not aplica:
            base = base if base else Decimal("0")
            monto = Decimal("0")
            monto_calculado = Decimal("0")
            monto_aprobado = Decimal("0")
        else:
            monto_calculado = monto
            monto_aprobado = monto

        lineas.append(
            {
                "orden": int(regla.get("orden", 0)),
                "rule_snapshot": regla,
                "concept_id": regla.get("concept_id"),
                "concepto_codigo": codigo,
                "concepto_nombre": regla.get("concepto_nombre"),
                "clase": regla.get("concepto_clase"),
                "base": base,
                "tasa": Decimal(str(regla.get("tasa", 0))),
                "umbral": umbral,
                "tasa_referencia": tasa_referencia,
                "aplica": aplica,
                "motivo_no_aplica": motivo_no_aplica,
                "monto_calculado": monto_calculado,
                "monto_aprobado": monto_aprobado,
                "exige_comprobante": bool(regla.get("exige_comprobante")),
            }
        )

    total = sum((linea["monto_aprobado"] for linea in lineas), Decimal("0"))
    if total > bruto:
        raise KontrolError(
            code="GOV_WITHHOLDING_EXCEEDS_GROSS",
            message="El total retenido excede el bruto",
            status_code=422,
        )
    return lineas, total


def huella(datos: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(datos, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
