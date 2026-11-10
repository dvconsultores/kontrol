from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class MatrizCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pliego_documento_id: str = Field(min_length=36, max_length=36)


class CriterioCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    aspecto: str = Field(min_length=1, max_length=16)
    orden: int = Field(ge=1)
    nombre: str = Field(min_length=1, max_length=300)
    descripcion: str | None = Field(default=None, max_length=2000)
    escala: str = Field(min_length=1, max_length=16)
    puntaje_maximo: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    ponderacion: Decimal | None = Field(default=None, gt=0, decimal_places=4)


class AperturaCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    abierta_en: datetime
    oferta_ids: list[str] = Field(min_length=1)
    miembro_ids: list[str] = Field(min_length=1)
    acta_documento_id: str = Field(min_length=36, max_length=36)
    observaciones: str | None = Field(default=None, max_length=2000)


class AporteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    oferta_id: str = Field(min_length=36, max_length=36)
    criterio_id: str = Field(min_length=36, max_length=36)
    miembro_id: str = Field(min_length=36, max_length=36)
    matriz_version: int = Field(ge=1)
    puntaje: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    cumple: bool | None = Field(default=None)
    observacion: str | None = Field(default=None, max_length=2000)
    evidencia_documento_id: str | None = Field(default=None, min_length=36, max_length=36)


class ResultadoCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    oferta_id: str = Field(min_length=36, max_length=36)
    criterio_id: str = Field(min_length=36, max_length=36)
    miembro_id: str = Field(min_length=36, max_length=36)
    matriz_version: int = Field(ge=1)
    puntaje: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    cumple: bool | None = Field(default=None)
    observacion: str | None = Field(default=None, max_length=2000)
    evidencia_documento_id: str | None = Field(default=None, min_length=36, max_length=36)
