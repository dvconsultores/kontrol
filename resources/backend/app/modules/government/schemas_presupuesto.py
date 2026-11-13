"""Esquemas Pydantic del módulo de presupuesto gubernamental (BUD-01, BUD-02)."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

PresupuestoTipoPartida = Literal["RECURSO", "EGRESO"]


class _Entrada(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("*", mode="before")
    @classmethod
    def _recortar_cadenas(cls, valor: object) -> object:
        if isinstance(valor, str):
            return valor.strip()
        return valor


class PresupuestoEjercicioIn(_Entrada):
    anio: int = Field(ge=2000, le=2100)


class PresupuestoNivelIn(_Entrada):
    nombre: str = Field(min_length=1, max_length=80)


class PresupuestoNivelesIn(_Entrada):
    niveles: list[PresupuestoNivelIn] = Field(min_length=1, max_length=8)


class PresupuestoCategoriaIn(_Entrada):
    nivel_orden: int = Field(ge=1, le=8)
    parent_id: str | None = Field(default=None, max_length=36)
    codigo: str = Field(min_length=1, max_length=20)
    denominacion: str = Field(min_length=1, max_length=300)


class PresupuestoCategoriaCambioIn(_Entrada):
    denominacion: str = Field(min_length=1, max_length=300)


class PresupuestoClasificadorIn(_Entrada):
    edicion: str = Field(min_length=3, max_length=200)
    fecha_edicion: date | None = None
    procedencia: str = Field(min_length=10, max_length=1000)
    documento_id: str | None = Field(default=None, max_length=36)


class PresupuestoPartidaIn(_Entrada):
    tipo: PresupuestoTipoPartida
    codigo: str = Field(min_length=1, max_length=40)
    denominacion: str = Field(min_length=1, max_length=300)
    nivel: int = Field(ge=1, le=12)
    codigo_padre: str | None = Field(default=None, max_length=40)
    vigente_desde: date | None = None
    vigente_hasta: date | None = None


class PresupuestoFundamentoIn(_Entrada):
    referencia: str = Field(min_length=3, max_length=300)
    fecha: date
    documento_id: str = Field(min_length=1, max_length=36)


class PresupuestoCierreIn(_Entrada):
    motivo: str | None = Field(default=None, max_length=500)


class PresupuestoPrecompromisoIn(_Entrada):
    activo: bool
    vigente_desde: date
    motivo: str = Field(min_length=10, max_length=500)


class PresupuestoEjercicioResumen(BaseModel):
    id: str
    anio: int
    moneda_funcional: str
    estado: str
    version: int
    congelado: bool
    reconduccion_definitiva: bool
    precompromiso_activo: bool


class PresupuestoEjercicioListado(BaseModel):
    items: list[PresupuestoEjercicioResumen]
    total: int


class PresupuestoNivelOut(BaseModel):
    orden: int
    nombre: str


class PresupuestoCategoriaOut(BaseModel):
    id: str
    nivel_orden: int
    nivel_nombre: str
    parent_id: str | None
    codigo: str
    codigo_completo: str
    denominacion: str


class PresupuestoClasificadorOut(BaseModel):
    edicion: str
    fecha_edicion: date | None
    procedencia: str
    documento_id: str | None
    documento_sha256: str | None
    partidas_recurso: int
    partidas_egreso: int


class PresupuestoPartidaOut(BaseModel):
    id: str
    tipo: PresupuestoTipoPartida
    codigo: str
    denominacion: str
    nivel: int
    codigo_padre: str | None
    vigente_desde: date
    vigente_hasta: date | None


class PresupuestoPartidasListado(BaseModel):
    items: list[PresupuestoPartidaOut]
    total: int


class PresupuestoFundamentoOut(BaseModel):
    tipo: str
    referencia: str
    fecha: date
    documento_id: str
    documento_sha256: str
    huella: str
    en: datetime


class PresupuestoHistoriaOut(BaseModel):
    tipo: str
    detalle: dict | None
    en: datetime


class PresupuestoEjercicioDetalle(PresupuestoEjercicioResumen):
    precompromiso_desde: date | None
    niveles: list[PresupuestoNivelOut]
    categorias: list[PresupuestoCategoriaOut]
    clasificador: PresupuestoClasificadorOut | None
    fundamentos: list[PresupuestoFundamentoOut]
    faltantes: list[str]
    historia: list[PresupuestoHistoriaOut]
    fijado_en: datetime | None
    cerrado_en: datetime | None
    motivo_cierre: str | None = None
