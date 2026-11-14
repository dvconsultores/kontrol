"""Esquemas Pydantic del presupuesto aprobado (BUD-05)."""

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


class PresupuestoIngresoIn(_Entrada):
    partida_id: str = Field(max_length=36)
    monto: Decimal = Field(gt=0, max_digits=18, decimal_places=2)


class PresupuestoMontoIn(_Entrada):
    monto: Decimal = Field(gt=0, max_digits=18, decimal_places=2)


class PresupuestoCreditoIn(_Entrada):
    categoria_id: str = Field(max_length=36)
    partida_id: str = Field(max_length=36)
    fuente_id: str = Field(max_length=36)
    monto: Decimal = Field(gt=0, max_digits=18, decimal_places=2)


class PresupuestoExistenciasIn(_Entrada):
    monto: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    fecha_corte: date
    documento_id: str = Field(max_length=36)


class PresupuestoPartidaRef(BaseModel):
    id: str
    codigo: str
    denominacion: str


class PresupuestoCategoriaRef(BaseModel):
    id: str
    codigo_completo: str
    denominacion: str


class PresupuestoFuenteRef(BaseModel):
    id: str
    codigo: str
    denominacion: str


class PresupuestoUnidadRef(BaseModel):
    id: str
    codigo: str
    nombre: str


class PresupuestoIngresoOut(BaseModel):
    id: str
    partida: PresupuestoPartidaRef
    monto: Decimal


class PresupuestoCreditoOut(BaseModel):
    id: str
    categoria: PresupuestoCategoriaRef
    unidad: PresupuestoUnidadRef | None
    partida: PresupuestoPartidaRef
    fuente: PresupuestoFuenteRef
    monto: Decimal


class PresupuestoExistenciasOut(BaseModel):
    monto: Decimal
    fecha_corte: date
    documento_id: str
    documento_sha256: str


class PresupuestoTotalesOut(BaseModel):
    ingresos: Decimal
    creditos: Decimal
    existencias: Decimal
    holgura_tesoro: Decimal
    disponible: Decimal
    diferencia: Decimal
    cuadra: bool


class PresupuestoFuenteOpcion(BaseModel):
    id: str
    codigo: str
    denominacion: str
    partidas_permitidas: list[str] | None


class PresupuestoOpcionesOut(BaseModel):
    categorias: list[PresupuestoCategoriaRef]
    partidas_egreso: list[PresupuestoPartidaRef]
    partidas_recurso: list[PresupuestoPartidaRef]
    fuentes: list[PresupuestoFuenteOpcion]


class PresupuestoAprobadoVista(BaseModel):
    version: int
    congelado: bool
    moneda: str
    ingresos: list[PresupuestoIngresoOut]
    creditos: list[PresupuestoCreditoOut]
    existencias_tesoro: PresupuestoExistenciasOut | None
    totales: PresupuestoTotalesOut
    opciones: PresupuestoOpcionesOut
