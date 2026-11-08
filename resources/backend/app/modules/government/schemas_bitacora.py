from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.modules.government.schemas_auditoria import AuditoriaObjeto


class BitacoraOpcion(BaseModel):
    id: str
    nombre: str


class BitacoraResultado(BaseModel):
    codigo: str
    etiqueta: str


class BitacoraAccion(BaseModel):
    codigo: str
    entidad: str
    etiqueta: str
    proceso: str


class BitacoraFiltros(BaseModel):
    resultados: list[BitacoraResultado]
    acciones: list[BitacoraAccion]
    funcionarios: list[BitacoraOpcion]
    unidades: list[BitacoraOpcion]


class BitacoraEvento(BaseModel):
    id: str
    fecha: datetime
    resultado: str
    accion: str
    accion_etiqueta: str
    proceso: str
    proceso_nombre: str
    usuario: str | None
    funcionario: str | None
    cargos: list[str]
    unidades: list[str]
    estado_contexto: str
    request_id: str | None
    motivo: str | None


class BitacoraEventoDetalle(BitacoraEvento):
    entidad: str
    entidad_id: str | None
    sesion_id: str | None
    ip: str | None
    detalle: dict[str, Any]
    objeto: AuditoriaObjeto | None
    contexto: dict[str, Any] | None


class BitacoraEventos(BaseModel):
    items: list[BitacoraEvento]
    total: int
    pagina: int
    por_pagina: int
