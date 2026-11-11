"""Esquemas de actas de entrega (CTL-09)."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class ActaTestigo(BaseModel):
    nombre: str = Field(..., min_length=3, max_length=120)
    documento: str = Field(..., min_length=3, max_length=20)


class ActaCreate(BaseModel):
    assignment_id: str
    receptor_official_id: str
    receptor_assignment_id: str | None = None
    modalidad: Literal["ENTREGA", "LEVANTADA_POR_RECEPTOR"]
    testigos: list[ActaTestigo] = []
    auditor_official_id: str | None = None
    motivo: str = Field(..., min_length=10, max_length=1000)
    fundamento: str = Field(..., min_length=10, max_length=1000)
    lugar: str = Field(..., min_length=2, max_length=200)
    fecha_corte: date


class ActaUpdate(BaseModel):
    version: int
    receptor_official_id: str
    receptor_assignment_id: str | None = None
    modalidad: Literal["ENTREGA", "LEVANTADA_POR_RECEPTOR"]
    testigos: list[ActaTestigo] = []
    auditor_official_id: str | None = None
    motivo: str = Field(..., min_length=10, max_length=1000)
    fundamento: str = Field(..., min_length=10, max_length=1000)
    lugar: str = Field(..., min_length=2, max_length=200)
    fecha_corte: date


class ActaAnexoUpdate(BaseModel):
    incluir_generado: bool | None = None
    documento_ids: list[str] | None = None
    constancia: str | None = None


class ActaSuscribir(BaseModel):
    fecha_suscripcion: date
    errores_deficiencias: str | None = Field(None, max_length=2000)


class ActaRemision(BaseModel):
    fecha: date


class ActaObservacionCreate(BaseModel):
    fecha: date
    texto: str = Field(..., min_length=10, max_length=2000)


class ActaVerificacionCreate(BaseModel):
    numero: str = Field(..., min_length=1, max_length=50)
    fecha: date
    resultado: str
    fundamento: str = Field(..., min_length=10, max_length=2000)
