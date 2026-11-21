"""Esquemas Pydantic para retención (TRE-05, T004)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class ConfiguracionRetencionIn(BaseModel):
    patron: str = Field(min_length=3, max_length=60)


class CatalogoRetencionCreate(BaseModel):
    tipo: str
    codigo: str = Field(pattern=r"^[A-Z0-9][A-Z0-9_-]{1,19}$")
    nombre: str = Field(min_length=3, max_length=120)
    descripcion: str | None = Field(default=None, max_length=2000)
    clase: str | None = None
    serie_comprobante: str | None = Field(default=None, pattern=r"^[A-Z0-9-]{1,10}$")


class CatalogoRetencionUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=3, max_length=120)
    descripcion: str | None = Field(default=None, max_length=2000)
    clase: str | None = None
    serie_comprobante: str | None = Field(default=None, pattern=r"^[A-Z0-9-]{1,10}$")
    estado: str | None = None


class ReglaRetencionIn(BaseModel):
    orden: int = Field(ge=1)
    concept_id: str
    base_tipo: str
    base_porcentaje: Decimal | None = None
    tasa: Decimal
    umbral_tipo: str = "NINGUNO"
    umbral_monto: Decimal | None = None
    umbral_multiplo: Decimal | None = None
    umbral_moneda_tasa: str | None = None
    sustraendo: Decimal | None = None
    tope: Decimal | None = None
    condiciones_exigidas: list[str] = Field(default_factory=list)
    exclusiones: list[str] = Field(default_factory=list)
    tipos_persona: list[str] | None = None
    exige_comprobante: bool = False


class PoliticaRetencionCreate(BaseModel):
    codigo: str
    nombre: str = Field(min_length=3, max_length=200)
    descripcion: str | None = None
    moneda: str
    tipo_regla: str = "INSTITUTIONAL_POLICY"
    fuente_descripcion: str | None = Field(default=None, max_length=500)
    fuente_referencia: str | None = Field(default=None, max_length=200)
    fuente_documento_id: str | None = None
    act_id: str | None = None
    aprobador_competencia_accion: str
    aprobador_competencia_materia: str
    permite_ajuste: bool = False
    redondeo_decimales: int = Field(default=2, ge=0, le=4)
    redondeo_modo: str = "HALF_UP"
    vigente_desde: date
    vigente_hasta: date | None = None
    reglas: list[ReglaRetencionIn] = Field(default_factory=list)


class PoliticaRetencionUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=3, max_length=200)
    descripcion: str | None = None
    moneda: str | None = None
    tipo_regla: str | None = None
    estado_verificacion: str | None = None
    fuente_descripcion: str | None = Field(default=None, max_length=500)
    fuente_referencia: str | None = Field(default=None, max_length=200)
    fuente_documento_id: str | None = None
    act_id: str | None = None
    aprobador_competencia_accion: str | None = None
    aprobador_competencia_materia: str | None = None
    permite_ajuste: bool | None = None
    redondeo_decimales: int | None = Field(default=None, ge=0, le=4)
    redondeo_modo: str | None = None
    vigente_desde: date | None = None
    vigente_hasta: date | None = None
    reglas: list[ReglaRetencionIn] | None = None


class ActivarPoliticaRetencionIn(BaseModel):
    fundamento: str = Field(min_length=1, max_length=2000)
    act_id: str | None = None


class CerrarPoliticaRetencionIn(BaseModel):
    motivo: str = Field(min_length=1, max_length=500)
