"""Esquemas Pydantic de las funciones incompatibles del procedimiento (PROC-11)."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

FuncionProcedimiento = Literal["SOLICITANTE", "RECEPTOR", "EVALUADOR", "ADJUDICADOR", "PAGADOR"]
EstadoReglaFuncion = Literal["BORRADOR", "VIGENTE", "CERRADA"]


class _Entrada(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("*", mode="before")
    @classmethod
    def _recortar_cadenas(cls, valor: object) -> object:
        if isinstance(valor, str):
            return valor.strip()
        return valor


class FuncionProcedimientoOut(BaseModel):
    codigo: FuncionProcedimiento
    etiqueta: str
    fuente: str
    disponible: bool
    requisito_habilitante: str | None


class CatalogoFunciones(BaseModel):
    proceso: str
    funciones: list[FuncionProcedimientoOut]


class ReglaFuncionIn(_Entrada):
    nombre: str = Field(min_length=3, max_length=200)
    descripcion: str = Field(min_length=10, max_length=2000)
    rol_a: FuncionProcedimiento
    rol_b: FuncionProcedimiento
    fundamento: str = Field(min_length=10, max_length=1000)
    #: Vacío = desde hoy, que es como se usa casi siempre una matriz.
    vigente_desde: date | None = None
    vigente_hasta: date | None = None

    @model_validator(mode="after")
    def _validar(self) -> "ReglaFuncionIn":
        if self.rol_a == self.rol_b:
            raise ValueError("Las dos funciones de la regla deben ser distintas")
        if self.vigente_desde and self.vigente_hasta and self.vigente_hasta < self.vigente_desde:
            raise ValueError("La vigencia final no puede ser anterior a la inicial")
        return self


class ActivacionFuncionIn(_Entrada):
    vigente_desde: date | None = None
    vigente_hasta: date | None = None


class CierreFuncionIn(_Entrada):
    motivo: str = Field(min_length=10, max_length=500)


class ReglaFuncionResumen(BaseModel):
    id: str
    codigo: str
    nombre: str
    proceso: str
    rol_a: str
    rol_a_etiqueta: str | None
    rol_b: str
    rol_b_etiqueta: str | None
    vigente_desde: date
    vigente_hasta: date | None
    estado: EstadoReglaFuncion
    en_vigor: bool
    version: int


class ReglaFuncionDetalle(ReglaFuncionResumen):
    descripcion: str
    fundamento: str
    historia: list[dict]


class ReglasFuncionListado(BaseModel):
    items: list[ReglaFuncionResumen]
    total: int
    hoy: date


class EvidenciaConflicto(BaseModel):
    rol: str
    rol_etiqueta: str | None
    registro: str
    registro_id: str
    fecha: date
    etiqueta: str | None = None


class ConflictoFuncion(BaseModel):
    regla_id: str
    regla_codigo: str
    regla_nombre: str
    regla_version: int
    rol_a: str
    rol_a_etiqueta: str | None
    rol_b: str
    rol_b_etiqueta: str | None
    actor: str
    actor_nombre: str | None
    fecha: date
    evidencia: list[EvidenciaConflicto]
    expediente_id: str
    expediente_numero: str
    expediente_objeto: str | None = None


class ConflictosFuncionListado(BaseModel):
    items: list[ConflictoFuncion]
    total: int
    desde: date
    hasta: date
