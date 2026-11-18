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


class RequisitoIn(_Entrada):
    etiqueta: str
    funcion: Literal["MIEMBRO", "SECRETARIO"]
    condicion: Literal["PRINCIPAL", "SUPLENTE", "CUALQUIERA"]
    tipo: Literal["AREA", "CARGO", "UNIDAD", "COMPETENCIA", "FUNCIONARIO"]
    area: Literal["JURIDICA", "TECNICA", "ECONOMICO_FINANCIERA"] | None = None
    position_id: str | None = None
    unit_id: str | None = None
    competencia_accion: str | None = None
    competencia_materia: str | None = None
    official_id: str | None = None
    minimo: int = Field(ge=0)
    maximo: int | None = Field(default=None, ge=0)


class DocumentoIn(_Entrada):
    document_type_id: str
    etapa: Literal["CONSTITUCION", "APERTURA", "RECOMENDACION"]
    obligatorio: bool = True
    condicion: str | None = None


class MayoriaIn(_Entrada):
    tipo: Literal["ABSOLUTE_COUNT", "SIMPLE_MAJORITY", "QUALIFIED_MAJORITY", "UNANIMITY"]
    cantidad: int | None = None
    numerador: int | None = None
    denominador: int | None = None


class DecisionPoliticaIn(MayoriaIn):
    base: Literal["MIEMBROS_CON_VOTO", "ASISTENTES_CON_VOTO"] = "MIEMBROS_CON_VOTO"


class PoliticaComisionIn(_Entrada):
    codigo: str = Field(min_length=1, max_length=20)
    nombre: str
    descripcion: str | None = None
    tipo_comision: Literal["PERMANENTE", "TEMPORAL", "CUALQUIERA"] = "CUALQUIERA"
    aplica_apertura: bool = True
    aplica_recomendacion: bool = True
    base_normativa: Literal["LCP_ART14", "NINGUNA"] = "LCP_ART14"
    fundamento: str | None = None
    vigente_desde: date
    vigente_hasta: date | None = None
    min_principales: int = Field(default=1, ge=1)
    max_principales: int | None = None
    exige_impar: bool = False
    suplente_por_principal: bool = False
    exige_secretario: bool = False
    exige_suplente_secretario: bool = False
    exige_presidente: bool = False
    quorum: MayoriaIn
    decision: DecisionPoliticaIn
    presidente_vota: bool = True
    presidente_dirimente: bool = False
    acto_requerido: bool = True
    acto_medio: Literal["GACETA", "PERSONAL", "PRENSA"] | None = None
    requisitos: list[RequisitoIn] = []
    documentos: list[DocumentoIn] = []


class PoliticaCerrarIn(_Entrada):
    motivo: str = Field(min_length=1)

    @field_validator("motivo")
    @classmethod
    def _motivo_no_vacio(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("El motivo no puede estar vacío")
        return value


class PoliticaComisionResumen(BaseModel):
    id: str
    codigo: str
    numero_version: int
    nombre: str
    tipo_comision: str
    base_normativa: str
    estado: str
    vigente_desde: date
    vigente_hasta: date | None
    aplica_apertura: bool
    aplica_recomendacion: bool
    version: int
    comisiones: int


class PoliticasComisionListado(BaseModel):
    items: list[PoliticaComisionResumen]
    total: int


class HistoriaPoliticaComisionOut(BaseModel):
    evento: str
    version: int
    fecha: datetime
    actor: str | None


class VersionPoliticaOut(BaseModel):
    id: str
    numero_version: int
    estado: str


class PoliticaComisionDetalle(PoliticaComisionResumen):
    descripcion: str | None
    fundamento: str | None
    min_principales: int
    max_principales: int | None
    exige_impar: bool
    suplente_por_principal: bool
    exige_secretario: bool
    exige_suplente_secretario: bool
    exige_presidente: bool
    quorum: dict[str, Any]
    decision: dict[str, Any]
    presidente_vota: bool
    presidente_dirimente: bool
    acto_requerido: bool
    acto_medio: str | None
    requisitos: list[dict[str, Any]]
    documentos: list[dict[str, Any]]
    regla: dict[str, Any]
    historia: list[HistoriaPoliticaComisionOut]
    versiones: list[VersionPoliticaOut]
    activada_en: datetime | None
    cerrada_en: datetime | None
    motivo_cierre: str | None
    puede_editar: bool
    puede_activar: bool
    puede_cerrar: bool
    puede_versionar: bool


class PoliticaComisionCatalogo(BaseModel):
    estados: list[dict[str, str]]
    tipos_comision: list[dict[str, str]]
    bases_normativas: list[dict[str, str]]
    tipos_mayoria: list[dict[str, str]]
    bases_decision: list[dict[str, str]]
    funciones: list[dict[str, str]]
    condiciones: list[dict[str, str]]
    tipos_requisito: list[dict[str, str]]
    areas: list[dict[str, str]]
    etapas: list[dict[str, str]]
    medios: list[dict[str, str]]
    acciones_competencia: list[dict[str, str]]
    materias_competencia: list[dict[str, str]]
    piso_lcp: dict[str, Any]


class PoliticaComisionOpciones(BaseModel):
    cargos: list[dict[str, str]]
    unidades: list[dict[str, str]]
    funcionarios: list[dict[str, str]]
    tipos_documentales: list[dict[str, str]]
