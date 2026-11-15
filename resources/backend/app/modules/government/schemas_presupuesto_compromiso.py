"""Esquemas Pydantic del compromiso presupuestario (BUD-08)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.modules.government.schemas_presupuesto_certificacion import _Entrada


class LineaCompromisoIn(_Entrada):
    certificado_id: str = Field(max_length=36)
    monto: Decimal = Field(gt=0, max_digits=18, decimal_places=2)


class CompromisoIn(_Entrada):
    concepto: str = Field(min_length=10, max_length=500)
    autoridad_cargo_id: str = Field(max_length=36)
    soporte_documento_id: str = Field(max_length=36)
    lineas: list[LineaCompromisoIn] = Field(min_length=1, max_length=20)


class AnulacionCompromisoIn(_Entrada):
    motivo: str = Field(min_length=10, max_length=500)


class CertificadoOpcionOut(BaseModel):
    certificado_id: str
    codigo: str
    credito_id: str
    categoria: str
    unidad: str | None
    partida: str
    fuente: str
    expediente_id: str | None
    expediente_referencia: str
    monto: Decimal
    consumido: Decimal
    remanente: Decimal
    situacion: str
    etiqueta: str


class AutoridadOpcionOut(BaseModel):
    cargo_id: str
    etiqueta: str
    unidad: str
    limite_tipo: str
    limite_monto: Decimal | None
    limite_moneda: str | None
    limite: str


class SoporteOpcionOut(BaseModel):
    id: str
    etiqueta: str


class OpcionesCompromisoVista(BaseModel):
    anio: int
    estado: str
    moneda: str
    comprometible: bool
    certificados: list[CertificadoOpcionOut]
    autoridades: list[AutoridadOpcionOut]
    soportes: list[SoporteOpcionOut]


class LineaCompromisoOut(BaseModel):
    linea: int
    certificado_id: str
    certificado_codigo: str
    credito_id: str
    categoria: str
    unidad: str | None
    partida: str
    fuente: str
    monto: Decimal


class TasaUsadaOut(BaseModel):
    tasa_id: str
    moneda: str
    moneda_cotizacion: str
    fecha_efectiva: str
    valor: str
    fuente: str
    fuente_referencia: str
    version: int
    evidencia_sha256: str | None


class ConversionLimiteOut(BaseModel):
    requiere_conversion: bool
    moneda_operacion: str
    moneda_limite: str
    fecha: str
    tasas: list[TasaUsadaOut]
    total: str
    limite: str
    total_ves: str | None
    limite_ves: str | None
    dentro_del_limite: bool
    resultado: str
    monedas_sin_tasa: list[str]


class VerificacionLimiteOut(BaseModel):
    cargo_id: str
    limite_tipo: str
    limite: str
    verificacion: ConversionLimiteOut | None


class CompromisoOut(BaseModel):
    id: str
    codigo: str
    estado: str
    fecha: date
    emitido_en: datetime
    total: Decimal
    moneda: str
    concepto: str
    expediente_id: str | None
    expediente_referencia: str
    autoridad_cargo: str
    autoridad_unidad: str
    autoridad_funcionario: str | None
    limite: str
    conversion: ConversionLimiteOut | None = None
    soporte_documento_id: str
    soporte: str
    soporte_sha256: str
    emitido_por: str
    huella: str
    documento_nombre: str
    documento_sha256: str
    anulado_en: datetime | None
    anulado_por: str | None
    motivo_anulacion: str | None
    lineas: list[LineaCompromisoOut]


class CompromisosVista(BaseModel):
    items: list[CompromisoOut]
