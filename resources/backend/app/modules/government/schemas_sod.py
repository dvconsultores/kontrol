"""Esquemas Pydantic para las reglas de segregación de funciones (CTL-01)."""

from datetime import date, datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

ProcesoSod = Literal["DOC-02", "CTL-06"]
EstadoReglaSod = Literal["BORRADOR", "VIGENTE", "CERRADA"]


class _Entrada(BaseModel):
    """Base de entrada que prohíbe campos extra y recorta cadenas."""

    model_config = ConfigDict(extra="forbid")

    @field_validator("*", mode="before")
    @classmethod
    def _recortar_cadenas(cls, valor: object) -> object:
        """Recorta los espacios de las cadenas recibidas."""
        if isinstance(valor, str):
            return valor.strip()
        return valor


class ReglaSodIn(_Entrada):
    """Datos de entrada para crear una regla de segregación de funciones."""

    nombre: str = Field(min_length=3, max_length=200)
    descripcion: str = Field(min_length=10, max_length=2000)
    proceso: ProcesoSod
    accion_a: str = Field(min_length=3, max_length=32)
    accion_b: str = Field(min_length=3, max_length=32)
    bidireccional: bool = False
    vigente_desde: date
    vigente_hasta: date | None = None

    @model_validator(mode="after")
    def _validar_regla(self) -> "ReglaSodIn":
        """Valida que las acciones sean distintas y la vigencia sea coherente."""
        if self.accion_a == self.accion_b:
            raise ValueError("La acción A y la acción B deben ser distintas")
        if self.vigente_hasta is not None and self.vigente_hasta < self.vigente_desde:
            raise ValueError("La vigencia final no puede ser anterior a la inicial")
        return self


class ReglaSodCambios(_Entrada):
    """Cambios opcionales para editar un borrador de regla."""

    nombre: str | None = Field(default=None, min_length=3, max_length=200)
    descripcion: str | None = Field(default=None, min_length=10, max_length=2000)
    accion_a: str | None = Field(default=None, min_length=3, max_length=32)
    accion_b: str | None = Field(default=None, min_length=3, max_length=32)
    bidireccional: bool | None = None
    vigente_desde: date | None = None
    vigente_hasta: date | None = None


class CierreSodIn(_Entrada):
    """Datos de entrada para cerrar una regla de segregación de funciones."""

    motivo: str = Field(min_length=10, max_length=500)


class AccionSod(BaseModel):
    """Acción disponible dentro de un proceso."""

    codigo: str
    etiqueta: str
    crea_objeto: bool


class ProcesoAccionesSod(BaseModel):
    """Proceso con las acciones que lo componen."""

    proceso: ProcesoSod
    nombre: str
    objeto: str
    acciones: list[AccionSod]


class CatalogoSod(BaseModel):
    """Catálogo de procesos y acciones para reglas de segregación."""

    procesos: list[ProcesoAccionesSod]


class HistoriaSod(BaseModel):
    """Entrada de la historia de una regla de segregación."""

    tipo: str
    detalle: dict | None = None
    registrado_por: str | None = None
    registrado_en: datetime


class ReglaSodResumen(BaseModel):
    """Resumen de una regla de segregación de funciones."""

    id: str
    codigo: str
    nombre: str
    proceso: ProcesoSod
    accion_a: str
    accion_a_etiqueta: str
    accion_b: str
    accion_b_etiqueta: str
    bidireccional: bool
    alcance: str
    modo: str
    vigente_desde: date
    vigente_hasta: date | None
    estado: EstadoReglaSod
    en_vigor: bool
    version: int


class ReglaSodDetalle(ReglaSodResumen):
    """Detalle completo de una regla de segregación de funciones."""

    descripcion: str
    creada_por: str | None
    creada_en: datetime
    activada_por: str | None
    activada_en: datetime | None
    cerrada_por: str | None
    cerrada_en: datetime | None
    motivo_cierre: str | None
    conflictos: int
    historia: list[HistoriaSod]


class ResumenSod(BaseModel):
    """Resumen agregado del estado de las reglas de segregación."""

    borradores: int
    vigentes: int
    cerradas: int
    conflictos_30_dias: int


class ReglasSodListado(BaseModel):
    """Listado paginado de reglas con su resumen."""

    items: list[ReglaSodResumen]
    resumen: ResumenSod


class ConflictoSod(BaseModel):
    """Conflicto de segregación de funciones registrado."""

    id: str
    fecha: datetime
    usuario: str | None
    regla_id: str | None
    regla_codigo: str | None
    regla_nombre: str | None
    proceso: str | None
    accion: str | None
    accion_etiqueta: str | None
    accion_previa: str | None
    accion_previa_etiqueta: str | None
    objeto_tipo: str | None
    objeto_id: str | None


class ConflictosSodListado(BaseModel):
    """Listado paginado de conflictos de segregación."""

    items: list[ConflictoSod]
    total: int
    pagina: int
    por_pagina: int
