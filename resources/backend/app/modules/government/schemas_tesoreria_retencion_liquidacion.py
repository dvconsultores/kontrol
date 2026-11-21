"""Esquemas HTTP de liquidaciones y comprobantes de retención."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field


class BeneficiarioIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=200)
    identificacion_fiscal: str | None = Field(default=None, max_length=30)
    tipo_persona: str
    condiciones: list[str] = []


class CalcularRetencionIn(BaseModel):
    policy_id: str
    conceptos: list[str]
    beneficiario: BeneficiarioIn


class AjustarLineaIn(BaseModel):
    monto_aprobado: Decimal
    motivo: str = Field(min_length=1, max_length=500)


class AprobarLiquidacionIn(BaseModel):
    cargo_id: str


class AnularLiquidacionIn(BaseModel):
    motivo: str = Field(min_length=1, max_length=500)


class BeneficiarioCorregidoIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=200)
    identificacion_fiscal: str | None = Field(default=None, max_length=30)


class AnularComprobanteIn(BaseModel):
    motivo: str = Field(min_length=1, max_length=500)
    sustituir: bool = False
    beneficiario: BeneficiarioCorregidoIn | None = None
