"""Esquemas para la API de tasas oficiales BCV de Gobierno (TRE-09)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.modules.government.schemas_presupuesto_certificacion import _Entrada


class TasaOficialIn(_Entrada):
    moneda: Literal["USD", "EUR"]
    fecha_efectiva: date
    valor: Decimal = Field(gt=0, max_digits=28, decimal_places=12)
    fuente_referencia: str = Field(min_length=10, max_length=300)
    publicada_en: date | None = None

    @model_validator(mode="after")
    def validar_publicacion(self) -> TasaOficialIn:
        if self.publicada_en and self.publicada_en > self.fecha_efectiva:
            raise ValueError("La fecha de publicación no puede ser posterior a la fecha efectiva")
        return self


class CorreccionTasaOficialIn(_Entrada):
    valor: Decimal = Field(gt=0, max_digits=28, decimal_places=12)
    fuente_referencia: str = Field(min_length=10, max_length=300)
    publicada_en: date | None = None
    motivo: str = Field(min_length=10, max_length=500)


class AnulacionTasaOficialIn(_Entrada):
    motivo: str = Field(min_length=10, max_length=500)


class TasaOficialOut(BaseModel):
    id: str
    moneda: str
    moneda_cotizacion: str
    fecha_efectiva: date
    valor: Decimal
    fuente: str
    fuente_referencia: str
    publicada_en: date | None
    estado: str
    version: int
    sustituye_id: str | None
    motivo_correccion: str | None
    capturada_por: str
    capturada_en: datetime
    aprobada_por: str | None
    aprobada_en: datetime | None
    evidencia_documento_id: str | None
    evidencia_sha256: str | None
    sustituida_en: datetime | None
    anulada_por: str | None
    anulada_en: datetime | None
    motivo_anulacion: str | None


class TasaOficialDetalle(TasaOficialOut):
    historia: list[TasaOficialOut]


class TasasOficialesVista(BaseModel):
    items: list[TasaOficialOut]
    monedas: list[str]
    estados: list[str]
