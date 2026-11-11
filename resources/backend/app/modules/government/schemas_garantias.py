"""Esquemas Pydantic para garantías y cauciones (PROC-10)."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class EmisorCreate(BaseModel):
    tipo: str
    rif: str
    nombre: str | None = None
    banco_id: str | None = None


class RequisitoCreate(BaseModel):
    regla_codigo: str
    fundamento: str
    documento_id: str
    porcentaje: Decimal | None = None
    monto_fijo: Decimal | None = None
    moneda: str | None = None
    nombre: str | None = None
    vigencia_minima_hasta: date | None = None


class GarantiaCreate(BaseModel):
    requisito_id: str
    oferta_id: str
    emisor_id: str
    referencia_emisor: str
    monto: Decimal
    moneda: str
    fecha_emision: date
    vigente_desde: date
    vigente_hasta: date
    documento_id: str
    observacion: str | None = None


class RenovacionCreate(BaseModel):
    vigente_hasta: date
    documento_id: str
    motivo: str
    monto: Decimal | None = None
    fecha_emision: date | None = None
    vigente_desde: date | None = None


class SustitucionCreate(BaseModel):
    emisor_id: str
    referencia_emisor: str
    monto: Decimal
    moneda: str
    fecha_emision: date
    vigente_desde: date
    vigente_hasta: date
    documento_id: str
    motivo: str


class LiberacionCreate(BaseModel):
    acto_id: str
    motivo: str
    documento_id: str | None = None


class EjecucionCreate(BaseModel):
    acto_id: str
    motivo: str
    monto_ejecutado: Decimal
    documento_id: str | None = None
