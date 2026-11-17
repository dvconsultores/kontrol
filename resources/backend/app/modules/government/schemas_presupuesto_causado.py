"""Esquemas Pydantic para el causado presupuestario (BUD-09)."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class PoliticaDocumentoIn(BaseModel):
    document_type_id: str
    obligatorio: bool = True
    etapa: str
    condicion: str | None = Field(default=None, max_length=300)


class PoliticaCreate(BaseModel):
    codigo: str = Field(pattern=r"^[A-Z0-9][A-Z0-9_-]{1,19}$")
    tipo_gasto: str = Field(pattern=r"^[A-Z0-9_]{2,40}$")
    nombre: str = Field(min_length=3, max_length=200)
    descripcion: str | None = Field(default=None, max_length=2000)
    disparador: str
    requiere_recepcion: bool = False
    requiere_valuacion: bool = False
    requiere_conformidad: bool = False
    competencia_accion: str = "CAUSAR"
    competencia_materia: str = "PRESUPUESTO"
    vigente_desde: date
    vigente_hasta: date | None = None
    fundamento: str | None = Field(default=None, max_length=2000)
    act_id: str | None = None
    tipo_regla: str = "INSTITUTIONAL_POLICY"
    documentos: list[PoliticaDocumentoIn] = Field(default_factory=list, max_length=20)


class PoliticaUpdate(BaseModel):
    tipo_gasto: str | None = Field(default=None, pattern=r"^[A-Z0-9_]{2,40}$")
    nombre: str | None = Field(default=None, min_length=3, max_length=200)
    descripcion: str | None = Field(default=None, max_length=2000)
    disparador: str | None = None
    requiere_recepcion: bool | None = None
    requiere_valuacion: bool | None = None
    requiere_conformidad: bool | None = None
    competencia_accion: str | None = None
    competencia_materia: str | None = None
    vigente_desde: date | None = None
    vigente_hasta: date | None = None
    fundamento: str | None = Field(default=None, max_length=2000)
    act_id: str | None = None
    tipo_regla: str | None = None
    documentos: list[PoliticaDocumentoIn] | None = Field(default=None, max_length=20)


class ActivarPoliticaIn(BaseModel):
    fundamento: str = Field(min_length=20, max_length=2000)
    act_id: str | None = None


class CerrarPoliticaIn(BaseModel):
    motivo: str = Field(min_length=10, max_length=500)


class ConfiguracionIn(BaseModel):
    patron: str


class LineaCausadoIn(BaseModel):
    linea_compromiso_id: str
    monto: Decimal


class EvidenciaIn(BaseModel):
    tipo: str
    id: str


class CausadoCreate(BaseModel):
    compromiso_id: str
    politica_id: str
    fecha_efectiva: date
    concepto: str = Field(min_length=10, max_length=500)
    beneficiario: str | None = Field(default=None, max_length=200)
    fuente_tipo: str | None = None
    fuente_id: str | None = None
    autoridad_cargo_id: str | None = None
    lineas: list[LineaCausadoIn] = Field(min_length=1, max_length=20)
    evidencias: list[EvidenciaIn] = Field(default_factory=list, max_length=30)


class CausadoUpdate(BaseModel):
    politica_id: str | None = None
    fecha_efectiva: date | None = None
    concepto: str | None = Field(default=None, min_length=10, max_length=500)
    beneficiario: str | None = Field(default=None, max_length=200)
    fuente_tipo: str | None = None
    fuente_id: str | None = None
    autoridad_cargo_id: str | None = None
    lineas: list[LineaCausadoIn] | None = Field(default=None, min_length=1, max_length=20)
    evidencias: list[EvidenciaIn] | None = Field(default=None, max_length=30)


class AnularCausadoIn(BaseModel):
    motivo: str = Field(min_length=10, max_length=500)
