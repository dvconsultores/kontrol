"""Esquemas Pydantic del contrato u orden (CNT-01)."""
from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class ContratoCreate(BaseModel):
    expediente_id: str


class ContratoUpdate(BaseModel):
    tipo: str | None = None
    fecha_inicio: date | None = None
    fecha_fin: date | None = None
    referencia_instrumento: str | None = None
    descripcion_complementaria: str | None = None
    documento_id: str | None = None


class AsignacionCobertura(BaseModel):
    certificado_id: str
    monto: Decimal


class CoberturaUpdate(BaseModel):
    asignaciones: list[AsignacionCobertura]


class GarantiasUpdate(BaseModel):
    instrumento_ids: list[str]


class FormalizacionCreate(BaseModel):
    firmante_cargo_id: str
