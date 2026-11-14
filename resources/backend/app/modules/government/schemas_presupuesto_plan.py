"""Esquemas Pydantic del plan operativo y fuentes de financiamiento (BUD-03, BUD-04)."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class _Entrada(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("*", mode="before")
    @classmethod
    def _recortar_cadenas(cls, valor: object) -> object:
        if isinstance(valor, str):
            return valor.strip()
        return valor


class PresupuestoPlanIn(_Entrada):
    denominacion: str = Field(min_length=3, max_length=300)
    documento_id: str | None = Field(default=None, max_length=36)


class PresupuestoObjetivoIn(_Entrada):
    codigo: str = Field(min_length=1, max_length=20)
    descripcion: str = Field(min_length=3, max_length=500)


class PresupuestoObjetivoCambioIn(_Entrada):
    descripcion: str = Field(min_length=3, max_length=500)


class PresupuestoVinculoIn(_Entrada):
    unidad_id: str | None = Field(default=None, max_length=36)
    objetivo_id: str | None = Field(default=None, max_length=36)


class PresupuestoMetaIn(_Entrada):
    categoria_id: str = Field(max_length=36)
    descripcion: str = Field(min_length=3, max_length=500)
    unidad_medida: str = Field(min_length=1, max_length=60)
    cantidad: Decimal
    indicador: str = Field(min_length=3, max_length=200)
    formula: str | None = Field(default=None, max_length=500)


class PresupuestoMetaCambioIn(_Entrada):
    descripcion: str = Field(min_length=3, max_length=500)
    unidad_medida: str = Field(min_length=1, max_length=60)
    cantidad: Decimal
    indicador: str = Field(min_length=3, max_length=200)
    formula: str | None = Field(default=None, max_length=500)


class PresupuestoFuenteIn(_Entrada):
    codigo: str = Field(min_length=1, max_length=20)
    denominacion: str = Field(min_length=3, max_length=300)
    procedencia: str = Field(min_length=10, max_length=1000)
    documento_id: str | None = Field(default=None, max_length=36)
    vigente_desde: date | None = None
    vigente_hasta: date | None = None


class PresupuestoFuenteCambioIn(_Entrada):
    denominacion: str = Field(min_length=3, max_length=300)
    procedencia: str = Field(min_length=10, max_length=1000)
    documento_id: str | None = Field(default=None, max_length=36)
    vigente_desde: date | None = None
    vigente_hasta: date | None = None


class PresupuestoRestriccionIn(_Entrada):
    descripcion: str = Field(min_length=3, max_length=500)
    fundamento: str = Field(min_length=3, max_length=500)
    partidas: list[str] = Field(default_factory=list, max_length=200)


class PresupuestoPlanDatos(BaseModel):
    denominacion: str
    documento_id: str | None
    documento_sha256: str | None


class PresupuestoObjetivoOut(BaseModel):
    id: str
    codigo: str
    descripcion: str


class PresupuestoUnidadOut(BaseModel):
    id: str
    codigo: str
    nombre: str


class PresupuestoObjetivoRef(BaseModel):
    id: str
    codigo: str


class PresupuestoVinculoOut(BaseModel):
    categoria_id: str
    codigo_completo: str
    denominacion: str
    unidad: PresupuestoUnidadOut | None
    objetivo: PresupuestoObjetivoRef | None


class PresupuestoMetaOut(BaseModel):
    id: str
    categoria_id: str
    codigo_completo: str
    descripcion: str
    unidad_medida: str
    cantidad: str
    indicador: str
    formula: str | None


class PresupuestoEstructuraRef(BaseModel):
    estado: str


class PresupuestoPlanVista(BaseModel):
    version: int
    congelado: bool
    plan: PresupuestoPlanDatos | None
    objetivos: list[PresupuestoObjetivoOut]
    vinculos: list[PresupuestoVinculoOut]
    metas: list[PresupuestoMetaOut]
    unidades_disponibles: list[PresupuestoUnidadOut]
    estructura_organizativa: PresupuestoEstructuraRef | None


class PresupuestoRestriccionOut(BaseModel):
    id: str
    descripcion: str
    fundamento: str
    partidas: list[str]


class PresupuestoFuenteOut(BaseModel):
    id: str
    codigo: str
    denominacion: str
    procedencia: str
    documento_id: str | None
    documento_sha256: str | None
    vigente_desde: str
    vigente_hasta: str | None
    restricciones: list[PresupuestoRestriccionOut]


class PresupuestoFuentesVista(BaseModel):
    version: int
    congelado: bool
    items: list[PresupuestoFuenteOut]
