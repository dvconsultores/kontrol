"""Esquemas Pydantic de la matriz de autoridad (GOV-0 · ORG-07)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.modules.government.schemas_cargos import AccionCompetencia, MateriaCompetencia


class MatrizEjercicio(BaseModel):
    """Ejercicio disponible para la matriz de autoridad."""

    ejercicio: int = Field(..., description="Año fiscal de la estructura")
    estado: str = Field(..., description="Estado de la estructura")


class MatrizEjercicios(BaseModel):
    """Listado de ejercicios disponibles."""

    items: list[MatrizEjercicio] = Field(default_factory=list, description="Ejercicios disponibles")


class MatrizUnidadFiltro(BaseModel):
    """Unidad disponible para filtrar la matriz."""

    id: str = Field(..., description="Identificador de la unidad")
    codigo: str = Field(..., description="Código de la unidad")
    denominacion: str = Field(..., description="Denominación de la unidad")
    ruta: str = Field(..., description="Ruta jerárquica de códigos de la unidad")


class MatrizCargoFiltro(BaseModel):
    """Cargo activo disponible para filtrar la matriz."""

    id: str = Field(..., description="Identificador del cargo")
    codigo: str = Field(..., description="Código del cargo")
    denominacion: str = Field(..., description="Denominación del cargo")


class MatrizFiltros(BaseModel):
    """Valores disponibles para los filtros de la matriz."""

    unidades: list[MatrizUnidadFiltro] = Field(default_factory=list, description="Unidades de la estructura")
    cargos: list[MatrizCargoFiltro] = Field(default_factory=list, description="Cargos activos de la estructura")


class MatrizVersionDeFila(BaseModel):
    """Versión del cargo que aporta una fila de la matriz."""

    version: int = Field(..., description="Número de versión")
    registrada_en: datetime = Field(..., description="Fecha y hora de registro en UTC")
    motivo: str | None = Field(None, description="Motivo del cambio de versión")


class MatrizFila(BaseModel):
    """Fila de la matriz de autoridad proyectada a una fecha de corte."""

    id: str = Field(..., description="Identificador estable de la fila")
    cargo_id: str = Field(..., description="Identificador del cargo")
    cargo_codigo: str = Field(..., description="Código del cargo")
    cargo_denominacion: str = Field(..., description="Denominación del cargo")
    unidad_id: str = Field(..., description="Identificador de la unidad del cargo")
    unidad_codigo: str | None = Field(None, description="Código de la unidad del cargo")
    unidad_denominacion: str | None = Field(None, description="Denominación de la unidad del cargo")
    ruta_unidad: str = Field(..., description="Ruta jerárquica de códigos de la unidad")
    accion: AccionCompetencia = Field(..., description="Acción de la competencia")
    materia: MateriaCompetencia = Field(..., description="Materia de la competencia")
    tipo_limite: str = Field(..., description="Tipo de límite de la competencia")
    monto: str | None = Field(None, description="Monto del límite, si aplica")
    moneda: str | None = Field(None, description="Moneda del límite")
    fundamento: str | None = Field(None, description="Fundamento de la competencia")
    vigente_desde: date = Field(..., description="Inicio de vigencia del cargo")
    vigente_hasta: date | None = Field(None, description="Fin de vigencia del cargo")
    estado_cargo: str = Field(..., description="Estado actual del cargo")
    acto_soporte: list[str] = Field(default_factory=list, description="Títulos de los documentos de soporte")
    version: MatrizVersionDeFila = Field(..., description="Versión del cargo usada en la fila")
    origen: Literal["CARGO"] = Field("CARGO", description="Origen de la fila")


class MatrizEstructura(BaseModel):
    """Estado de la estructura consultada."""

    estado: str = Field(..., description="Estado de la estructura")


class MatrizAutoridad(BaseModel):
    """Respuesta paginada de la matriz de autoridad."""

    ejercicio: int = Field(..., description="Año fiscal consultado")
    fecha: date = Field(..., description="Fecha de corte aplicada")
    estructura: MatrizEstructura = Field(..., description="Estado de la estructura")
    items: list[MatrizFila] = Field(default_factory=list, description="Filas de la página solicitada")
    total: int = Field(..., description="Total de filas filtradas")
    cargos: int = Field(..., description="Cantidad de cargos distintos filtrados")
    pagina: int = Field(..., description="Página solicitada")
    por_pagina: int = Field(..., description="Tamaño de página solicitado")


class MatrizDocumento(BaseModel):
    """Documento de soporte de un cargo."""

    documento_id: str = Field(..., description="Identificador del documento")
    titulo: str = Field(..., description="Título del documento")


class MatrizCargo(BaseModel):
    """Registro actual de un cargo en el detalle."""

    id: str = Field(..., description="Identificador del cargo")
    codigo: str = Field(..., description="Código del cargo")
    denominacion: str = Field(..., description="Denominación del cargo")
    unidad_codigo: str | None = Field(None, description="Código de la unidad")
    unidad_denominacion: str | None = Field(None, description="Denominación de la unidad")
    ruta_unidad: str = Field(..., description="Ruta jerárquica de códigos de la unidad")
    estado: str = Field(..., description="Estado del cargo")
    vigente_desde: date = Field(..., description="Inicio de vigencia del cargo")
    vigente_hasta: date | None = Field(None, description="Fin de vigencia del cargo")


class MatrizVersion(BaseModel):
    """Versión histórica de un cargo."""

    version: int = Field(..., description="Número de versión")
    estado: str = Field(..., description="Estado de la versión")
    motivo: str | None = Field(None, description="Motivo del cambio de versión")
    creado_en: datetime = Field(..., description="Fecha y hora de creación en UTC")
    competencias: list[dict[str, Any]] = Field(default_factory=list, description="Competencias de la versión")


class MatrizDetalleCargo(BaseModel):
    """Detalle de un cargo y su historial de versiones."""

    cargo: MatrizCargo = Field(..., description="Registro actual del cargo")
    acto_soporte: list[MatrizDocumento] = Field(default_factory=list, description="Documentos de soporte vigentes")
    versiones: list[MatrizVersion] = Field(default_factory=list, description="Versiones del cargo")
