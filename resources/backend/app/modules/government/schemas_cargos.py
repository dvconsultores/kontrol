"""Esquemas Pydantic de los cargos con competencias y límites de firma/aprobación (ORG-03)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import Numeric

from app.modules.government.models import GovernmentPositionCompetency
from app.modules.government.schemas_estructura import _codigo, _denominacion, _fecha_sin_hora, _motivo, _uuid
from app.shared.money import texto_de_salida, texto_decimal

AccionCompetencia = Literal["SOLICITAR", "COMPROMETER", "CAUSAR", "ORDENAR_PAGO", "PAGAR", "REGISTRAR", "CUSTODIAR", "APROBAR", "AUDITAR", "FIRMAR"]
MateriaCompetencia = Literal["PRESUPUESTO", "CONTRATACIONES", "TESORERIA", "CONTABILIDAD", "BIENES", "EXPEDIENTE"]
TipoDeLimite = Literal["SIN_LIMITE", "MONTO"]
MonedaDeLimite = Literal["VES", "USD", "EUR"]
_COLUMNA_MONTO = cast(Numeric, GovernmentPositionCompetency.__table__.c.limit_amount.type)
if TYPE_CHECKING:
    MontoDeLimite = Decimal
    MontoDeSalida = str
else:
    MontoDeLimite = texto_decimal(_COLUMNA_MONTO, positivo=True)
    MontoDeSalida = texto_de_salida(_COLUMNA_MONTO)


def _fundamento(v: str | None) -> str | None:
    """Normaliza el fundamento: strip y vacío a None."""
    if v is None:
        return None
    v = v.strip()
    if not v:
        return None
    if len(v) > 255:
        raise ValueError("El fundamento admite como máximo 255 caracteres")
    return v


def _limite_coherente(tipo_limite: str, monto: Any, moneda: str | None) -> None:
    """Exige monto y moneda con MONTO y ninguno con SIN_LIMITE (OD-ORG03-03)."""
    if tipo_limite == "SIN_LIMITE" and (monto is not None or moneda is not None):
        raise ValueError("Sin límite no lleva monto ni moneda")
    if tipo_limite == "MONTO" and (monto is None or moneda is None):
        raise ValueError("Indique el monto máximo por operación y su moneda")


class CargoIn(BaseModel):
    """Datos para registrar un cargo en la estructura del ejercicio."""

    model_config = ConfigDict(extra="forbid")

    codigo: str
    denominacion: str
    unidad_id: str
    vigente_desde: date | None = None

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

    @field_validator("unidad_id", mode="after")
    @classmethod
    def _unidad_id_validator(cls, v: str) -> str:
        resultado = _uuid(v)
        if resultado is None:
            raise ValueError("Campo obligatorio")
        return resultado

    @field_validator("vigente_desde", mode="before")
    @classmethod
    def _vigente_desde_validator(cls, v: Any) -> Any:
        return _fecha_sin_hora(v)


class CargoCambio(BaseModel):
    """Cambios parciales de un cargo; solo se aplican los campos presentes."""

    model_config = ConfigDict(extra="forbid")

    codigo: str | None = None
    denominacion: str | None = None
    unidad_id: str | None = None
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

    @field_validator("unidad_id", mode="after")
    @classmethod
    def _unidad_id_validator(cls, v: str | None) -> str | None:
        return _uuid(v)

    @field_validator("vigente_desde", mode="before")
    @classmethod
    def _vigente_desde_validator(cls, v: Any) -> Any:
        return _fecha_sin_hora(v)

    @field_validator("motivo", mode="after")
    @classmethod
    def _motivo_validator(cls, v: str | None) -> str | None:
        return _motivo(v)

    @model_validator(mode="after")
    def _campos_no_nulos(self) -> CargoCambio:
        for campo in ("codigo", "denominacion", "unidad_id", "vigente_desde"):
            if campo in self.model_fields_set and getattr(self, campo) is None:
                raise ValueError(f"{campo} no puede quedar vacío")
        return self


class DesactivacionCargoIn(BaseModel):
    """Datos para desactivar un cargo vigente."""

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


class CompetenciaIn(BaseModel):
    """Una competencia nueva del cargo: acción × materia con su límite."""

    model_config = ConfigDict(extra="forbid")

    accion: AccionCompetencia
    materia: MateriaCompetencia
    tipo_limite: TipoDeLimite
    monto: MontoDeLimite | None = None
    moneda: MonedaDeLimite | None = None
    fundamento: str | None = None
    motivo: str | None = Field(default=None, max_length=255)

    @field_validator("fundamento", mode="after")
    @classmethod
    def _fundamento_validator(cls, v: str | None) -> str | None:
        return _fundamento(v)

    @field_validator("motivo", mode="after")
    @classmethod
    def _motivo_validator(cls, v: str | None) -> str | None:
        return _motivo(v)

    @model_validator(mode="after")
    def _coherencia(self) -> CompetenciaIn:
        _limite_coherente(self.tipo_limite, self.monto, self.moneda)
        return self


class CompetenciaCambio(BaseModel):
    """Nuevo límite y fundamento de una competencia; la acción y la materia no cambian."""

    model_config = ConfigDict(extra="forbid")

    tipo_limite: TipoDeLimite
    monto: MontoDeLimite | None = None
    moneda: MonedaDeLimite | None = None
    fundamento: str | None = None
    motivo: str | None = Field(default=None, max_length=255)

    @field_validator("fundamento", mode="after")
    @classmethod
    def _fundamento_validator(cls, v: str | None) -> str | None:
        return _fundamento(v)

    @field_validator("motivo", mode="after")
    @classmethod
    def _motivo_validator(cls, v: str | None) -> str | None:
        return _motivo(v)

    @model_validator(mode="after")
    def _coherencia(self) -> CompetenciaCambio:
        _limite_coherente(self.tipo_limite, self.monto, self.moneda)
        return self


class RetiroCompetenciaIn(BaseModel):
    """Motivo para retirar una competencia."""

    model_config = ConfigDict(extra="forbid")

    motivo: str | None = Field(default=None, max_length=255)

    @field_validator("motivo", mode="after")
    @classmethod
    def _motivo_validator(cls, v: str | None) -> str | None:
        return _motivo(v)


class CompetenciaOut(BaseModel):
    """Representación de una competencia para la API."""

    id: str
    accion: str
    materia: str
    tipo_limite: str
    monto: MontoDeSalida | None
    moneda: str | None
    fundamento: str | None


class CargoOut(BaseModel):
    """Representación de un cargo para la API."""

    id: str
    codigo: str
    denominacion: str
    unidad_id: str
    unidad_codigo: str
    unidad_denominacion: str
    estado: str
    vigente_desde: date
    vigente_hasta: date | None
    version: int
    competencias: list[CompetenciaOut]
    faltantes_para_activar: list[str]
    documento_vinculado: bool
    activado_en: datetime | None
    activado_por: str | None
    creado_en: datetime


class EstructuraDeCargos(BaseModel):
    """Estado de la estructura a la que pertenecen los cargos."""

    ejercicio: int
    estado: str
    version: int


class ListaCargos(BaseModel):
    """Listado de cargos."""

    estructura: EstructuraDeCargos
    items: list[CargoOut]
    total: int


class VersionCargoOut(BaseModel):
    """Una versión histórica de un cargo."""

    version: int
    estado: str
    motivo: str | None
    actor_id: str | None
    creado_en: datetime
    datos: dict[str, Any]


class VersionesCargo(BaseModel):
    """Listado de versiones históricas de un cargo."""

    items: list[VersionCargoOut]
    total: int
