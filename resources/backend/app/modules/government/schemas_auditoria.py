"""Esquemas Pydantic de la consulta y el muestreo del auditor de Gobierno (CTL-04)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class AuditoriaProceso(BaseModel):
    """Proceso de Gobierno incluido en la auditoría institucional."""

    codigo: str
    nombre: str


class AuditoriaAccion(BaseModel):
    """Acción de auditoría de Gobierno."""

    codigo: str
    entidad: str
    etiqueta: str
    proceso: str


class AuditoriaFiltros(BaseModel):
    """Catálogo de procesos y acciones disponible para filtrar."""

    procesos: list[AuditoriaProceso]
    acciones: list[AuditoriaAccion]


class AuditoriaEventoResumen(BaseModel):
    """Resumen de un evento de auditoría de Gobierno."""

    id: str
    fecha: datetime
    proceso: str
    proceso_nombre: str
    accion: str
    accion_etiqueta: str
    entidad: str
    entidad_id: str | None
    usuario: str | None
    motivo: str | None
    request_id: str | None


class AuditoriaObjeto(BaseModel):
    """Objeto de negocio relacionado con un evento de auditoría."""

    tipo: str
    id: str
    ruta: str
    capacidad: str


class AuditoriaEventoDetalle(AuditoriaEventoResumen):
    """Detalle completo de un evento de auditoría de Gobierno."""

    detalle: dict[str, Any]
    documentos: list[str]
    objeto: AuditoriaObjeto | None


class AuditoriaEventos(BaseModel):
    """Página de eventos de auditoría."""

    items: list[AuditoriaEventoResumen]
    total: int
    pagina: int
    por_pagina: int


class AuditoriaFiltrosPoblacion(BaseModel):
    """Filtros de población para el muestreo del auditor."""

    model_config = ConfigDict(extra="forbid")

    desde: date | None = None
    hasta: date | None = None
    proceso: str | None = None
    accion: str | None = None
    usuario: str | None = Field(default=None, min_length=1, max_length=150)
    texto: str | None = Field(default=None, min_length=1, max_length=100)

    @field_validator("usuario", "texto", mode="before")
    @classmethod
    def _normalizar_texto(cls, value: Any) -> Any:
        """Recorta los textos; una cadena vacía tras el recorte se convierte en None."""
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value


class MuestraIn(BaseModel):
    """Datos de entrada para registrar una muestra de auditoría."""

    model_config = ConfigDict(extra="forbid")

    titulo: str = Field(min_length=3, max_length=200)
    criterio: str = Field(min_length=10, max_length=2000)
    justificacion: str = Field(min_length=10, max_length=2000)
    metodo: Literal["TODAS", "ESPECIFICA", "ALEATORIA"]
    filtros: AuditoriaFiltrosPoblacion = Field(default_factory=AuditoriaFiltrosPoblacion)
    semilla: int | None = Field(default=None, ge=1, le=999_999_999)
    tamano: int | None = Field(default=None)
    eventos: list[str] | None = None

    @field_validator("titulo", "criterio", "justificacion", mode="before")
    @classmethod
    def _recortar_campos(cls, value: Any) -> Any:
        """Recorta los campos antes de la validación de longitud."""
        if isinstance(value, str):
            return value.strip()
        return value

    @model_validator(mode="after")
    def _validar_metodo(self) -> MuestraIn:
        """Aplica las reglas de cardinalidad y pertinencia según el método de muestreo."""
        if self.metodo == "ESPECIFICA":
            if not self.eventos or not 1 <= len(self.eventos) <= 500:
                raise ValueError("El método ESPECIFICA requiere entre 1 y 500 eventos")
            if len(self.eventos) != len(set(self.eventos)):
                raise ValueError("El método ESPECIFICA no admite eventos repetidos")
            if self.semilla is not None:
                raise ValueError("La semilla solo se admite en el método ALEATORIA")
            if self.tamano is not None:
                raise ValueError("El tamaño solo se admite en el método ALEATORIA")
            return self

        if self.metodo == "ALEATORIA":
            if self.tamano is None:
                raise ValueError("El método ALEATORIA requiere un tamaño de muestra")
            if self.eventos:
                raise ValueError("El método ALEATORIA no admite eventos específicos")
            return self

        if self.eventos:
            raise ValueError("El método TODAS no admite eventos específicos")
        if self.semilla is not None:
            raise ValueError("La semilla solo se admite en el método ALEATORIA")
        if self.tamano is not None:
            raise ValueError("El tamaño solo se admite en el método ALEATORIA")
        return self


class AuditoriaMuestra(BaseModel):
    """Muestra de auditoría registrada."""

    id: str
    codigo: str
    titulo: str
    criterio: str
    justificacion: str
    metodo: str
    semilla: int | None
    tamano: int
    poblacion: int
    filtros: dict[str, Any]
    registrada_por: str | None
    registrada_en: datetime


class AuditoriaMuestraDetalle(AuditoriaMuestra):
    """Muestra de auditoría con sus eventos."""

    eventos: list[AuditoriaEventoResumen]


class AuditoriaMuestras(BaseModel):
    """Listado de muestras de auditoría."""

    items: list[AuditoriaMuestra]
