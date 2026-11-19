from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class _Entrada(BaseModel):
    model_config = ConfigDict(extra="forbid")


class VinculoIn(_Entrada):
    supuesto: Literal[
        "N34_ART11",
        "N34_ART12",
        "N34_ART13",
        "N34_ART14",
        "N34_ART15",
        "N34_ART16",
        "N34_ART17",
    ]
    alcance: Literal["ENTE", "UNIDAD"]
    unit_id: str | None = None


class RequisitoIn(_Entrada):
    codigo: str = Field(min_length=2, max_length=8)
    titulo: str = Field(min_length=3, max_length=200)
    evidencia: Literal["DOCUMENTO", "CERTIFICACION", "DECLARACION", "DATO"]
    obligatorio: bool = True
    ambito: Literal["TODAS", "ENTE", "UNIDAD"] = "TODAS"
    supuesto: Literal[
        "N34_ART11",
        "N34_ART12",
        "N34_ART13",
        "N34_ART14",
        "N34_ART15",
        "N34_ART16",
        "N34_ART17",
    ] | None = None
    document_type_id: str | None = None
    fuente: str | None = Field(default=None, max_length=500)


class PlazoIn(_Entrada):
    hito: Literal["ELABORACION", "REMISION_UAI"]
    valor: int = Field(ge=1)
    unidad: Literal["DIAS_HABILES", "DIAS_CONTINUOS"]
    fuente: str | None = Field(default=None, max_length=500)


class PoliticaActaIn(_Entrada):
    codigo: str = Field(pattern=r"^[A-Z0-9][A-Z0-9-]{1,19}$")
    nombre: str = Field(min_length=3, max_length=200)
    descripcion: str | None = Field(default=None, max_length=2000)
    fundamento: str | None = Field(default=None, max_length=2000)
    act_id: str | None = None
    vigente_desde: date
    vigente_hasta: date | None = None
    numeracion_patron: str | None = Field(default=None, max_length=60)
    testigos_en_entrega: int = Field(default=0, ge=0, le=5)
    cargo_maxima_autoridad_codigo: str | None = Field(
        default=None, max_length=30, pattern=r"^[A-Za-z0-9._-]{1,30}$"
    )
    vinculos: list[VinculoIn] = []
    requisitos: list[RequisitoIn] = []
    plazos: list[PlazoIn] = []


class PoliticaActaCerrarIn(_Entrada):
    motivo: str = Field(min_length=10, max_length=500)


class CatalogoItem(BaseModel):
    codigo: str
    etiqueta: str


class PoliticaActaCatalogo(BaseModel):
    estados: list[CatalogoItem]
    evidencias: list[CatalogoItem]
    ambitos_requisito: list[CatalogoItem]
    alcances: list[CatalogoItem]
    hitos: list[CatalogoItem]
    unidades_plazo: list[CatalogoItem]


class VinculoOut(BaseModel):
    supuesto: str
    articulo: str | None = None
    titulo: str | None = None
    alcance: str
    unit_id: str | None = None
    unidad: str | None = None


class RequisitoOut(BaseModel):
    codigo: str
    titulo: str
    evidencia: str
    obligatorio: bool
    ambito: str
    supuesto: str | None = None
    document_type_id: str | None = None
    document_type_nombre: str | None = None
    fuente: str | None = None


class PlazoOut(BaseModel):
    hito: str
    valor: int
    unidad: str
    fuente: str | None = None
    legal_valor: int | None = None
    legal_fuente: str | None = None


class PoliticaActaResumen(BaseModel):
    id: str
    codigo: str
    numero_version: int
    nombre: str
    estado: str
    estado_etiqueta: str
    vigente_desde: date
    vigente_hasta: date | None = None
    total_vinculos: int
    total_requisitos: int
    version: int


class PoliticaActaListado(BaseModel):
    items: list[PoliticaActaResumen]
    total: int
    pagina: int
    por_pagina: int


class PoliticaActaHistoriaOut(BaseModel):
    evento: str
    version: int
    fecha: datetime
    actor: str | None = None


class PoliticaActaVersionOut(BaseModel):
    id: str
    numero_version: int
    estado: str


class PoliticaActaDetalle(PoliticaActaResumen):
    descripcion: str | None = None
    fundamento: str | None = None
    act_id: str | None = None
    numeracion_patron: str | None = None
    testigos_en_entrega: int
    cargo_maxima_autoridad_codigo: str | None = None
    version_anterior_id: str | None = None
    activada_en: datetime | None = None
    cerrada_en: datetime | None = None
    motivo_cierre: str | None = None
    vinculos: list[VinculoOut]
    requisitos: list[RequisitoOut]
    plazos: list[PlazoOut]
    regla_ente: dict[str, Any]
    historia: list[PoliticaActaHistoriaOut]
    versiones: list[PoliticaActaVersionOut]
    actas_que_la_usan: int
    acciones: dict[str, bool]


class PoliticaActaOpciones(BaseModel):
    nivel_territorial: str | None = None
    forma_organizativa: str | None = None
    supuestos: list[dict[str, Any]]
    unidades: list[dict[str, str]]
    tipos_documento: list[dict[str, str]]
    actos: list[dict[str, str]]
    testigos_legales: dict[str, Any]
    plazos_legales: list[dict[str, Any]]
    patron_por_defecto: str
