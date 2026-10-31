"""Esquemas Pydantic de la estructura organizativa por ejercicio (ORG-02)."""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.shared.clock import hoy_de_negocio

TipoDeUnidad = Literal[
    "ORGANO",
    "UNIDAD_ADMINISTRATIVA",
    "UNIDAD_EJECUTORA_LOCAL",
    "DEPENDENCIA",
    "SEDE",
    "CENTRO_GESTOR",
]

_CODIGO_RE = re.compile(r"^[A-Z0-9][A-Z0-9.-]{0,29}$")
_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
_FECHA_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _fecha_sin_hora(v: Any) -> Any:
    """Valida una fecha sin hora; acepta date o cadena AAAA-MM-DD."""
    if v is None:
        return None
    if isinstance(v, datetime):
        raise ValueError("Indique solo la fecha, sin hora")
    if isinstance(v, date):
        return v
    if isinstance(v, str):
        if not _FECHA_RE.match(v):
            raise ValueError("Use el formato AAAA-MM-DD")
        try:
            return date.fromisoformat(v)
        except ValueError:
            raise ValueError("Use el formato AAAA-MM-DD") from None
    raise ValueError("Indique una fecha (AAAA-MM-DD)")


def _codigo(v: str | None) -> str | None:
    """Normaliza y valida el código de unidad."""
    if v is None:
        return None
    v = v.strip().upper()
    if not _CODIGO_RE.match(v):
        raise ValueError(
            "El código admite de 1 a 30 caracteres: letras, números, punto y guion, sin espacios"
        )
    return v


def _denominacion(v: str | None) -> str | None:
    """Normaliza y valida la denominación de unidad."""
    if v is None:
        return None
    v = v.strip()
    if len(v) < 3 or len(v) > 200:
        raise ValueError("La denominación debe tener entre 3 y 200 caracteres")
    return v


def _uuid(v: str | None) -> str | None:
    """Normaliza y valida un identificador UUID de unidad."""
    if v is None:
        return None
    v = v.strip()
    if not _UUID_RE.match(v):
        raise ValueError("Identificador de unidad inválido")
    return v


def _motivo(v: str | None) -> str | None:
    """Normaliza el motivo: strip y vacío a None."""
    if v is None:
        return None
    v = v.strip()
    return v or None


class EstructuraIn(BaseModel):
    """Datos para crear la estructura organizativa de un ejercicio."""

    model_config = ConfigDict(extra="forbid")

    ejercicio: int
    copiar_de: int | None = None

    @field_validator("ejercicio", mode="after")
    @classmethod
    def _ejercicio(cls, v: int) -> int:
        if not 2000 <= v <= hoy_de_negocio().year + 1:
            raise ValueError(
                "El ejercicio debe estar entre 2000 y el año siguiente al actual"
            )
        return v


class UnidadIn(BaseModel):
    """Datos para crear una unidad en la estructura."""

    model_config = ConfigDict(extra="forbid")

    codigo: str
    denominacion: str
    tipo: TipoDeUnidad
    unidad_superior_id: str | None = None
    vigente_desde: date | None = None
    motivo: str | None = Field(default=None, max_length=255)

    @field_validator("codigo", mode="after")
    @classmethod
    def _codigo_validator(cls, v: str) -> str:
        resultado = _codigo(v)
        if resultado is None:
            raise ValueError("Campo obligatorio")
        return resultado

    @field_validator("denominacion", mode="after")
    @classmethod
    def _denominacion_validator(cls, v: str) -> str:
        resultado = _denominacion(v)
        if resultado is None:
            raise ValueError("Campo obligatorio")
        return resultado

    @field_validator("unidad_superior_id", mode="after")
    @classmethod
    def _unidad_superior_id(cls, v: str | None) -> str | None:
        return _uuid(v)

    @field_validator("vigente_desde", mode="before")
    @classmethod
    def _vigente_desde(cls, v: Any) -> Any:
        return _fecha_sin_hora(v)

    @field_validator("motivo", mode="after")
    @classmethod
    def _motivo_validator(cls, v: str | None) -> str | None:
        return _motivo(v)


class UnidadCambio(BaseModel):
    """Cambios parciales de una unidad; solo se aplican los campos presentes."""

    model_config = ConfigDict(extra="forbid")

    codigo: str | None = None
    denominacion: str | None = None
    tipo: TipoDeUnidad | None = None
    unidad_superior_id: str | None = None
    vigente_desde: date | None = None
    motivo: str | None = Field(default=None, max_length=255)

    @field_validator("codigo", mode="after")
    @classmethod
    def _codigo_validator(cls, v: str | None) -> str | None:
        return _codigo(v)

    @field_validator("denominacion", mode="after")
    @classmethod
    def _denominacion_validator(cls, v: str | None) -> str | None:
        return _denominacion(v)

    @field_validator("unidad_superior_id", mode="after")
    @classmethod
    def _unidad_superior_id(cls, v: str | None) -> str | None:
        return _uuid(v)

    @field_validator("vigente_desde", mode="before")
    @classmethod
    def _vigente_desde(cls, v: Any) -> Any:
        return _fecha_sin_hora(v)

    @field_validator("motivo", mode="after")
    @classmethod
    def _motivo_validator(cls, v: str | None) -> str | None:
        return _motivo(v)

    @model_validator(mode="after")
    def _campos_no_nulos(self) -> UnidadCambio:
        for campo in ("codigo", "denominacion", "tipo"):
            if campo in self.model_fields_set and getattr(self, campo) is None:
                raise ValueError(f"{campo} no puede quedar vacío")
        return self


class DesactivacionIn(BaseModel):
    """Datos para desactivar una unidad."""

    model_config = ConfigDict(extra="forbid")

    fecha: date
    motivo: str | None = Field(default=None, max_length=255)

    @field_validator("fecha", mode="before")
    @classmethod
    def _fecha_validator(cls, v: Any) -> Any:
        return _fecha_sin_hora(v)

    @field_validator("motivo", mode="after")
    @classmethod
    def _motivo_validator(cls, v: str | None) -> str | None:
        return _motivo(v)


class UnidadOut(BaseModel):
    """Representación de una unidad para la API."""

    id: str
    codigo: str
    denominacion: str
    tipo: str
    unidad_superior_id: str | None
    nivel: int
    estado: str
    vigente_desde: date
    vigente_hasta: date | None
    version: int


class EstructuraOut(BaseModel):
    """Representación de la estructura organizativa para la API."""

    id: str
    ejercicio: int
    estado: str
    version: int
    copiada_de: int | None
    publicada_en: datetime | None
    publicada_por: str | None
    cerrada_en: datetime | None
    cerrada_por: str | None
    documento_vinculado: bool
    faltantes_para_publicar: list[str]
    unidades: list[UnidadOut]
    creado_en: datetime


class EstructuraResumen(BaseModel):
    """Resumen de una estructura organizativa."""

    ejercicio: int
    estado: str
    version: int
    unidades_activas: int
    publicada_en: datetime | None
    cerrada_en: datetime | None


class ListaEstructuras(BaseModel):
    """Listado de estructuras organizativas."""

    items: list[EstructuraResumen]
    total: int


class VersionUnidadOut(BaseModel):
    """Una versión histórica de una unidad."""

    version: int
    estado: str
    motivo: str | None
    actor_id: str | None
    creado_en: datetime
    datos: dict[str, Any]


class VersionesUnidad(BaseModel):
    """Listado de versiones históricas de una unidad."""

    items: list[VersionUnidadOut]
    total: int
