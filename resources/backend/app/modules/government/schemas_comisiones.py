from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator


class _Entrada(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("*", mode="before")
    @classmethod
    def _recortar(cls, value: Any) -> Any:
        return value.strip() if isinstance(value, str) else value


class ComisionIn(_Entrada):
    nombre: str
    tipo: Literal["PERMANENTE", "TEMPORAL"]
    objeto: str | None = None
    desde: date
    hasta: date | None = None
    acto_id: str | None = None


class ComisionFinIn(_Entrada):
    fecha: date
    motivo: str


class ComisionDescartarIn(_Entrada):
    motivo: str


class SncIn(_Entrada):
    fecha: date
    referencia: str


class MiembroIn(_Entrada):
    funcionario_id: str
    funcion: Literal["MIEMBRO", "SECRETARIO"]
    area: Literal["JURIDICA", "TECNICA", "ECONOMICO_FINANCIERA"] | None = None
    condicion: Literal["PRINCIPAL", "SUPLENTE"]
    suplente_de_id: str | None = None
    certificacion_snc: str | None = None
    desde: date | None = None
    acto_id: str | None = None


class MiembroFinIn(_Entrada):
    fecha: date
    causa: Literal[
        "MUERTE_INCAPACIDAD",
        "DESPIDO_DESTITUCION",
        "RETIRO_RENUNCIA_REMOCION",
        "FIN_DESIGNACION",
    ]
    motivo: str


class InhibicionIn(_Entrada):
    miembro_id: str
    asunto: str
    causal: Literal[
        "INTERES",
        "AMISTAD_ENEMISTAD",
        "INTERVENCION_PREVIA",
        "SERVICIO_SUBORDINACION",
    ]
    descripcion: str
    fecha: date
    soporte: str | None = None


class InhibicionResolverIn(_Entrada):
    decision: Literal["ACEPTADA", "RECHAZADA"]
    motivo: str


class Etiquetado(BaseModel):
    codigo: str
    etiqueta: str


class CausalCatalogo(Etiquetado):
    fuente: str


class ComisionCatalogo(BaseModel):
    tipos: list[Etiquetado]
    funciones: list[Etiquetado]
    areas: list[Etiquetado]
    condiciones: list[Etiquetado]
    causas_fin: list[Etiquetado]
    causales: list[CausalCatalogo]
    situaciones: list[Etiquetado]
    regla_version: str
    fuente_regla: str


class OpcionFuncionarioComision(BaseModel):
    id: str
    nombre: str
    cargos: list[str]
    unidades: list[str]


class OpcionActoComision(BaseModel):
    id: str
    etiqueta: str
    medio: str | None
    fecha_eficacia: date | None


class ComisionOpciones(BaseModel):
    funcionarios: list[OpcionFuncionarioComision]
    actos: list[OpcionActoComision]


class ActoRef(BaseModel):
    id: str
    etiqueta: str
    medio: str | None
    fecha_eficacia: date | None
    emisor: str | None


class ComisionResumen(BaseModel):
    id: str
    codigo: str
    nombre: str
    tipo: str
    status: str
    situacion: str
    desde: date
    hasta: date | None
    acto: ActoRef | None
    miembros_principales: int
    miembros_total: int
    version: int


class ComisionesListado(BaseModel):
    items: list[ComisionResumen]
    total: int
    pagina: int
    por_pagina: int


class FuncionarioRef(BaseModel):
    id: str
    nombre: str
    cargos: list[str]
    unidades: list[str]


class MiembroOut(BaseModel):
    id: str
    funcionario: FuncionarioRef
    funcion: str
    area: str | None
    condicion: str
    suplente_de: str | None
    suplente_de_id: str | None
    desde: date
    fin_efectivo: date | None
    causa_fin: str | None
    motivo_fin: str | None
    acto: ActoRef | None
    certificacion_snc: str | None


class InhibicionOut(BaseModel):
    id: str
    miembro_id: str
    miembro: str
    suplente: str | None
    asunto: str
    causal: str
    causal_etiqueta: str
    descripcion: str
    fecha: date
    soporte: str | None
    estado: str
    motivo_resolucion: str | None
    version: int


class HistoriaComisionOut(BaseModel):
    tipo: str
    fecha: datetime
    usuario: str | None
    descripcion: str


class ComisionDetalle(ComisionResumen):
    objeto: str | None
    regla_version: str | None
    snc_notificada_en: date | None
    snc_referencia: str | None
    snc_pendiente: bool
    motivo_cierre: str | None
    fin_efectivo: date | None
    fecha: date
    es_historica: bool
    composicion: list[MiembroOut]
    miembros: list[MiembroOut]
    faltantes: list[str]
    inhibiciones: list[InhibicionOut]
    historia: list[HistoriaComisionOut]
