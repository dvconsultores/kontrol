"""Términos contractuales efectivos (CNT-01 + modificaciones CNT-02 formalizadas vigentes a una fecha). Autoridad única del plazo y el monto vigentes; no depende de CNT-03, CNT-04, CNT-07 ni CNT-09."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.modules.government.models import GovernmentContract
from app.modules.government.service_contratos_modificaciones import _formalizadas, _vigente_a
from app.shared.clock import hoy_de_negocio


def terminos_efectivos(
    db: Session, contrato: GovernmentContract, fecha: date | None = None
) -> dict[str, Any]:
    """Proyección CNT-01 + adendas CNT-02 formalizadas vigentes a la fecha."""
    fecha = fecha or hoy_de_negocio()
    proy = _vigente_a(contrato, _formalizadas(db, str(contrato.id)), fecha)
    return {
        "monto": Decimal(proy["monto"]),
        "moneda": contrato.moneda,
        "fecha_inicio": contrato.fecha_inicio,
        "fecha_fin": date.fromisoformat(proy["fecha_fin"]) if proy["fecha_fin"] else None,
        "fuente": "CNT02_MODIFICACION" if proy["modificacion_codigo"] else "CNT01_ORIGINAL",
        "modificacion": proy["modificacion_codigo"],
        "monto_original": Decimal(contrato.monto),
    }
