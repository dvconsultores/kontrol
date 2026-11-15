"""Esquemas Pydantic de las modificaciones contractuales (CNT-02)."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class ModificacionCreate(BaseModel):
    tipo: str


class ModificacionUpdate(BaseModel):
    tipo: str | None = None
    fecha_instrumento: date | None = None
    vigente_desde: date | None = None
    motivo: str | None = None
    nueva_fecha_fin: date | None = None
    delta_monto: Decimal | None = None
    condiciones: str | None = None
    referencia_instrumento: str | None = None
    documento_id: str | None = None
