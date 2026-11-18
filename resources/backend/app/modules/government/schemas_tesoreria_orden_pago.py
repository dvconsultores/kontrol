"""Esquemas Pydantic para la orden de pago (TRE-03)."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class PoliticaOrdenPagoDocumentoIn(BaseModel):
    document_type_id: str
    obligatorio: bool = True
    etapa: str = "EMISION"
    condicion: str | None = Field(default=None, max_length=300)


class PoliticaOrdenPagoCreate(BaseModel):
    codigo: str = Field(pattern=r"^[A-Z0-9][A-Z0-9_-]{1,19}$")
    nombre: str = Field(min_length=3, max_length=200)
    descripcion: str | None = Field(default=None, max_length=2000)
    tipo_gasto: str | None = Field(default=None, pattern=r"^[A-Z0-9_]{2,40}$")
    requiere_expediente_completo: bool = False
    competencia_accion: str = "ORDENAR_PAGO"
    competencia_materia: str = "TESORERIA"
    vigente_desde: date
    vigente_hasta: date | None = None
    fundamento: str | None = Field(default=None, max_length=2000)
    act_id: str | None = None
    tipo_regla: str = "INSTITUTIONAL_POLICY"
    documentos: list[PoliticaOrdenPagoDocumentoIn] = Field(default_factory=list, max_length=20)


class PoliticaOrdenPagoUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=3, max_length=200)
    descripcion: str | None = Field(default=None, max_length=2000)
    tipo_gasto: str | None = Field(default=None, pattern=r"^[A-Z0-9_]{2,40}$")
    requiere_expediente_completo: bool | None = None
    competencia_accion: str | None = None
    competencia_materia: str | None = None
    vigente_desde: date | None = None
    vigente_hasta: date | None = None
    fundamento: str | None = Field(default=None, max_length=2000)
    act_id: str | None = None
    tipo_regla: str | None = None
    documentos: list[PoliticaOrdenPagoDocumentoIn] | None = Field(default=None, max_length=20)


class ActivarPoliticaIn(BaseModel):
    fundamento: str = Field(min_length=20, max_length=2000)
    act_id: str | None = None


class CerrarPoliticaIn(BaseModel):
    motivo: str = Field(min_length=10, max_length=500)


class ConfiguracionOrdenPagoIn(BaseModel):
    patron: str = Field(min_length=3, max_length=60)


class OrdenLineaIn(BaseModel):
    cause_id: str
    monto: Decimal = Field(gt=0, max_digits=18, decimal_places=2)


class OrdenCreate(BaseModel):
    policy_id: str
    fecha_orden: date
    concepto: str = Field(min_length=3, max_length=500)
    lineas: list[OrdenLineaIn] = Field(min_length=1, max_length=100)
    documentos: list[str] = Field(default_factory=list, max_length=50)
    autoridad_cargo_id: str | None = None


class OrdenUpdate(BaseModel):
    policy_id: str | None = None
    fecha_orden: date | None = None
    concepto: str | None = Field(default=None, min_length=3, max_length=500)
    lineas: list[OrdenLineaIn] | None = Field(default=None, min_length=1, max_length=100)
    documentos: list[str] | None = Field(default=None, max_length=50)
    autoridad_cargo_id: str | None = None


class AnularOrdenIn(BaseModel):
    motivo: str = Field(min_length=10, max_length=500)
    cargo_id: str
