"""Esquemas Pydantic de disponibilidad y certificación presupuestaria (BUD-06)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class _Entrada(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("*", mode="before")
    @classmethod
    def _recortar_cadenas(cls, valor: object) -> object:
        if isinstance(valor, str):
            return valor.strip()
        return valor


class CertificacionIn(_Entrada):
    credito_id: str = Field(max_length=36)
    monto: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    concepto: str = Field(min_length=10, max_length=500)
    expediente_id: str | None = Field(default=None, max_length=36)
    expediente_referencia: str | None = Field(default=None, max_length=120)
    firmante_cargo_id: str = Field(max_length=36)


class AnulacionIn(_Entrada):
    motivo: str = Field(min_length=10, max_length=500)


class RefOut(BaseModel):
    id: str
    etiqueta: str


class CreditoDisponibleOut(BaseModel):
    credito_id: str
    categoria: RefOut
    unidad: RefOut | None
    partida: RefOut
    fuente: RefOut
    credito: Decimal
    certificado: Decimal
    disponible: Decimal


class TotalesDisponibilidadOut(BaseModel):
    credito: Decimal
    certificado: Decimal
    disponible: Decimal


class FiltrosDisponibilidadOut(BaseModel):
    categorias: list[RefOut]
    unidades: list[RefOut]
    partidas: list[RefOut]
    fuentes: list[RefOut]


class FirmanteOpcionOut(BaseModel):
    cargo_id: str
    etiqueta: str
    unidad: str


class ExpedienteOpcionOut(BaseModel):
    id: str
    etiqueta: str


class DisponibilidadVista(BaseModel):
    anio: int
    estado: str
    moneda: str
    certificable: bool
    items: list[CreditoDisponibleOut]
    totales: TotalesDisponibilidadOut
    filtros: FiltrosDisponibilidadOut
    firmantes: list[FirmanteOpcionOut]
    expedientes: list[ExpedienteOpcionOut]


class CertificacionOut(BaseModel):
    id: str
    codigo: str
    estado: str
    fecha: date
    emitida_en: datetime
    monto: Decimal
    saldo_antes: Decimal
    saldo_despues: Decimal
    moneda: str
    concepto: str
    expediente_id: str | None
    expediente_referencia: str
    credito_id: str
    categoria: str
    unidad: str | None
    partida: str
    fuente: str
    firmante_cargo: str
    firmante_unidad: str
    firmante_funcionario: str | None
    emitida_por: str
    huella: str
    documento_nombre: str
    documento_sha256: str
    anulada_en: datetime | None
    anulada_por: str | None
    motivo_anulacion: str | None


class CertificacionesVista(BaseModel):
    items: list[CertificacionOut]
