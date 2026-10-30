"""Esquemas Pydantic del módulo de Gobierno (GOV-0 · Configurar el ente)."""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.shared.clock import hoy_de_negocio

NivelTerritorial = Literal["NACIONAL", "ESTADAL", "MUNICIPAL"]
FormaOrganizativa = Literal[
    "ADMINISTRACION_CENTRAL",
    "INSTITUTO_PUBLICO",
    "SERVICIO_DESCONCENTRADO",
    "ENTE_DESCENTRALIZADO",
]
TipoDeActo = Literal["LEY", "DECRETO", "ORDENANZA", "RESOLUCION", "OTRO"]

_RIF_RE = re.compile(r"^([JGVEP])-?(\d{8})-?(\d)$")
_FECHA_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _texto_opcional(v: str | None, minimo: int, maximo: int, etiqueta: str) -> str | None:
    """Normaliza un texto opcional: strip, vacío a None y valida longitudes."""
    if v is None:
        return None
    v = v.strip()
    if not v:
        return None
    if len(v) < minimo or len(v) > maximo:
        raise ValueError(f"{etiqueta} debe tener entre {minimo} y {maximo} caracteres")
    return v


def _rif(v: str | None) -> str | None:
    """Normaliza un RIF venezolano al formato X-dddddddd-d."""
    if v is None:
        return None
    v = v.strip().upper()
    if not v:
        return None
    m = _RIF_RE.match(v)
    if not m:
        raise ValueError("RIF inválido; formato esperado: J-12345678-9")
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"


def _acto_fecha(v: Any) -> Any:
    """Valida una fecha de acto: solo fecha, sin hora, y no futura."""
    if v is None:
        return None
    if isinstance(v, datetime):
        raise ValueError("La fecha del acto debe ser una fecha sin hora")
    if isinstance(v, date):
        if v > hoy_de_negocio():
            raise ValueError("La fecha del acto no puede ser futura")
        return v
    if isinstance(v, str):
        if not _FECHA_RE.match(v):
            raise ValueError("La fecha del acto debe tener formato YYYY-MM-DD")
        try:
            d = date.fromisoformat(v)
        except ValueError:
            raise ValueError("La fecha del acto debe tener formato YYYY-MM-DD") from None
        if d > hoy_de_negocio():
            raise ValueError("La fecha del acto no puede ser futura")
        return d
    raise ValueError("La fecha del acto debe ser una fecha sin hora")


class EnteIn(BaseModel):
    """Datos para crear el ente de Gobierno."""

    model_config = ConfigDict(extra="forbid")

    denominacion: str
    siglas: str | None = None
    rif: str | None = None
    nivel_territorial: NivelTerritorial | None = None
    forma_organizativa: FormaOrganizativa | None = None
    organo_adscripcion: str | None = None
    entidad_federal: str | None = None
    municipio: str | None = None
    acto_tipo: TipoDeActo | None = None
    acto_numero: str | None = None
    acto_fecha: date | None = None
    acto_publicacion: str | None = None

    @field_validator("denominacion", mode="after")
    @classmethod
    def _denominacion(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("La denominación es obligatoria")
        if len(v) < 3 or len(v) > 200:
            raise ValueError("La denominación debe tener entre 3 y 200 caracteres")
        return v

    @field_validator("siglas", mode="after")
    @classmethod
    def _siglas(cls, v: str | None) -> str | None:
        return _texto_opcional(v, 1, 20, "Las siglas")

    @field_validator("rif", mode="after")
    @classmethod
    def _rif_validator(cls, v: str | None) -> str | None:
        return _rif(v)

    @field_validator("organo_adscripcion", mode="after")
    @classmethod
    def _organo_adscripcion(cls, v: str | None) -> str | None:
        return _texto_opcional(v, 3, 200, "El órgano de adscripción")

    @field_validator("entidad_federal", mode="after")
    @classmethod
    def _entidad_federal(cls, v: str | None) -> str | None:
        return _texto_opcional(v, 2, 120, "La entidad federal")

    @field_validator("municipio", mode="after")
    @classmethod
    def _municipio(cls, v: str | None) -> str | None:
        return _texto_opcional(v, 2, 120, "El municipio")

    @field_validator("acto_numero", mode="after")
    @classmethod
    def _acto_numero(cls, v: str | None) -> str | None:
        return _texto_opcional(v, 1, 60, "El número del acto")

    @field_validator("acto_fecha", mode="before")
    @classmethod
    def _acto_fecha_validator(cls, v: Any) -> Any:
        return _acto_fecha(v)

    @field_validator("acto_publicacion", mode="after")
    @classmethod
    def _acto_publicacion(cls, v: str | None) -> str | None:
        return _texto_opcional(v, 3, 200, "La publicación del acto")


class EnteCambio(BaseModel):
    """Cambios parciales del ente; solo se aplican los campos presentes."""

    model_config = ConfigDict(extra="forbid")

    denominacion: str | None = None
    siglas: str | None = None
    rif: str | None = None
    nivel_territorial: NivelTerritorial | None = None
    forma_organizativa: FormaOrganizativa | None = None
    organo_adscripcion: str | None = None
    entidad_federal: str | None = None
    municipio: str | None = None
    acto_tipo: TipoDeActo | None = None
    acto_numero: str | None = None
    acto_fecha: date | None = None
    acto_publicacion: str | None = None
    motivo: str | None = Field(default=None, max_length=255)

    @field_validator("denominacion", mode="after")
    @classmethod
    def _denominacion(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        if len(v) < 3 or len(v) > 200:
            raise ValueError("La denominación debe tener entre 3 y 200 caracteres")
        return v

    @field_validator("siglas", mode="after")
    @classmethod
    def _siglas(cls, v: str | None) -> str | None:
        return _texto_opcional(v, 1, 20, "Las siglas")

    @field_validator("rif", mode="after")
    @classmethod
    def _rif_validator(cls, v: str | None) -> str | None:
        return _rif(v)

    @field_validator("organo_adscripcion", mode="after")
    @classmethod
    def _organo_adscripcion(cls, v: str | None) -> str | None:
        return _texto_opcional(v, 3, 200, "El órgano de adscripción")

    @field_validator("entidad_federal", mode="after")
    @classmethod
    def _entidad_federal(cls, v: str | None) -> str | None:
        return _texto_opcional(v, 2, 120, "La entidad federal")

    @field_validator("municipio", mode="after")
    @classmethod
    def _municipio(cls, v: str | None) -> str | None:
        return _texto_opcional(v, 2, 120, "El municipio")

    @field_validator("acto_numero", mode="after")
    @classmethod
    def _acto_numero(cls, v: str | None) -> str | None:
        return _texto_opcional(v, 1, 60, "El número del acto")

    @field_validator("acto_fecha", mode="before")
    @classmethod
    def _acto_fecha_validator(cls, v: Any) -> Any:
        return _acto_fecha(v)

    @field_validator("acto_publicacion", mode="after")
    @classmethod
    def _acto_publicacion(cls, v: str | None) -> str | None:
        return _texto_opcional(v, 3, 200, "La publicación del acto")

    @field_validator("motivo", mode="after")
    @classmethod
    def _motivo(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        return v or None

    @model_validator(mode="after")
    def _denominacion_no_nula(self) -> EnteCambio:
        if "denominacion" in self.model_fields_set and self.denominacion is None:
            raise ValueError("La denominación no puede quedar vacía")
        return self


class EnteOut(BaseModel):
    """Representación del ente para la API."""

    id: str
    denominacion: str
    siglas: str | None
    rif: str | None
    nivel_territorial: NivelTerritorial | None
    forma_organizativa: FormaOrganizativa | None
    organo_adscripcion: str | None
    entidad_federal: str | None
    municipio: str | None
    acto_tipo: TipoDeActo | None
    acto_numero: str | None
    acto_fecha: date | None
    acto_publicacion: str | None
    estado: str
    version: int
    faltantes_para_activar: list[str]
    documento_vinculado: bool
    activado_en: datetime | None
    activado_por: str | None
    creado_en: datetime
    actualizado_en: datetime


class VersionOut(BaseModel):
    """Una versión histórica del ente."""

    version: int
    estado: str
    motivo: str | None
    actor_id: str | None
    creado_en: datetime
    datos: dict[str, Any]


class VersionesOut(BaseModel):
    """Listado de versiones históricas."""

    items: list[VersionOut]
    total: int


class ModuloOut(BaseModel):
    """Estado del módulo de Gobierno."""

    habilitado: bool
