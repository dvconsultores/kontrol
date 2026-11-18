from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class _Entrada(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("*", mode="before")
    @classmethod
    def _recortar(cls, value: Any) -> Any:
        return value.strip() if isinstance(value, str) else value


class PoliticaAsignacionCompetenciaIn(_Entrada):
    accion: Literal[
        "SOLICITAR", "COMPROMETER", "CAUSAR", "ORDENAR_PAGO", "PAGAR",
        "REGISTRAR", "CUSTODIAR", "APROBAR", "AUDITAR", "FIRMAR",
    ]
    materia: Literal["PRESUPUESTO", "CONTRATACIONES", "TESORERIA", "CONTABILIDAD", "BIENES", "EXPEDIENTE"]


class PoliticaAsignacionDocumentoIn(_Entrada):
    document_type_id: str = Field(min_length=36, max_length=36)
    etapa: Literal["ACTIVACION", "REVOCACION"]
    obligatorio: bool = True


class PoliticaAsignacionIn(_Entrada):
    codigo: str = Field(min_length=1, max_length=20)
    nombre: str = Field(min_length=1, max_length=200)
    descripcion: str | None = Field(default=None, max_length=2000)
    figura: Literal[
        "TITULAR",
        "ENCARGADURIA",
        "SUPLENCIA",
        "COMISION_SERVICIO",
        "DELEGACION_ATRIBUCIONES",
        "DELEGACION_FIRMA",
    ]
    fundamento: str | None = Field(default=None, max_length=2000)
    act_id: str | None = Field(default=None, min_length=36, max_length=36)
    vigente_desde: date
    vigente_hasta: date | None = None
    exige_fin: bool = False
    max_dias: int | None = Field(default=None, ge=1, le=3660)
    acto_medio: Literal["GACETA", "PERSONAL", "PRENSA"] | None = None
    emisor_tipo: Literal["CUALQUIERA", "CARGO", "COMPETENCIA"] = "CUALQUIERA"
    emisor_position_id: str | None = Field(default=None, min_length=36, max_length=36)
    emisor_competencia_accion: Literal[
        "SOLICITAR", "COMPROMETER", "CAUSAR", "ORDENAR_PAGO", "PAGAR",
        "REGISTRAR", "CUSTODIAR", "APROBAR", "AUDITAR", "FIRMAR",
    ] | None = None
    emisor_competencia_materia: Literal[
        "PRESUPUESTO", "CONTRATACIONES", "TESORERIA", "CONTABILIDAD", "BIENES", "EXPEDIENTE"
    ] | None = None
    autorizacion_requerida: bool = False
    autorizacion_etiqueta: str | None = Field(default=None, min_length=5, max_length=120)
    autorizacion_ambito: Literal["TODAS", "MAXIMA_AUTORIDAD"] | None = None
    autorizacion_mas_de_dias: int | None = Field(default=None, ge=0, le=3660)
    prohibe_avocacion: bool = False
    competencias: list[PoliticaAsignacionCompetenciaIn] = []
    documentos: list[PoliticaAsignacionDocumentoIn] = []


class PoliticaAsignacionCerrarIn(_Entrada):
    motivo: str = Field(min_length=5, max_length=500)

    @field_validator("motivo")
    @classmethod
    def _motivo_no_vacio(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("El motivo no puede estar vacío")
        return value


class PoliticaAsignacionResumen(BaseModel):
    id: str
    codigo: str
    numero_version: int
    nombre: str
    figura: str
    figura_etiqueta: str
    estado: str
    estado_etiqueta: str
    vigente_desde: date
    vigente_hasta: date | None
    version: int
    asignaciones: int


class PoliticaAsignacionListado(BaseModel):
    items: list[PoliticaAsignacionResumen]
    total: int


class PoliticaAsignacionHistoriaOut(BaseModel):
    evento: str
    version: int
    fecha: datetime
    actor: str | None


class PoliticaAsignacionVersionOut(BaseModel):
    id: str
    numero_version: int
    estado: str


class PoliticaAsignacionDetalle(PoliticaAsignacionResumen):
    descripcion: str | None
    fundamento: str | None
    act_id: str | None
    exige_fin: bool
    max_dias: int | None
    acto_medio: str | None
    emisor_tipo: str
    emisor_position_id: str | None
    emisor_competencia_accion: str | None
    emisor_competencia_materia: str | None
    autorizacion_requerida: bool
    autorizacion_etiqueta: str | None
    autorizacion_ambito: str | None
    autorizacion_mas_de_dias: int | None
    prohibe_avocacion: bool
    competencias: list[dict[str, Any]]
    documentos: list[dict[str, Any]]
    regla: dict[str, Any]
    historia: list[PoliticaAsignacionHistoriaOut]
    versiones: list[PoliticaAsignacionVersionOut]
    activada_en: datetime | None
    cerrada_en: datetime | None
    motivo_cierre: str | None
    version_anterior_id: str | None
    existe_borrador: bool


class PoliticaAsignacionOpciones(BaseModel):
    cargos: list[dict[str, str]]
    tipos_documentales: list[dict[str, str]]
    nivel_territorial: str | None
    pisos: list[dict[str, Any]]


class PoliticaAsignacionCatalogo(BaseModel):
    figuras: list[dict[str, str]]
    estados: list[dict[str, str]]
    medios: list[dict[str, str]]
    emisor_tipos: list[dict[str, str]]
    ambitos: list[dict[str, str]]
    etapas: list[dict[str, str]]
    acciones: list[dict[str, str]]
    materias: list[dict[str, str]]
