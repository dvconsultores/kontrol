from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class CompetenciaSeparacionOut(BaseModel):
    accion: str
    materia: str


class OcupacionOut(BaseModel):
    cargo: str
    cargo_codigo: str
    figura_etiqueta: str
    unidad: str
    competencias: list[CompetenciaSeparacionOut]


class IdentidadOut(BaseModel):
    vinculo_codigo: str | None
    funcionario: str | None
    ocupaciones: list[OcupacionOut]
    tiene_autoridad: bool
    motivo: str | None
    motivo_etiqueta: str | None


class OrigenOut(BaseModel):
    fuente: Literal["INSTALACION", "ASIGNACION", "NO_REGISTRADO"]
    actor: str | None
    fecha: datetime | None


class RolOut(BaseModel):
    codigo: str
    nombre: str
    protegido: bool
    tipo: Literal["TECNICO", "FUNCIONAL"]
    alcance: Literal["TODAS", "ENTE"]
    capacidades: int
    categorias: list[str]
    origen: OrigenOut


class AdministradorOut(BaseModel):
    usuario: str
    estado: str
    separacion: Literal[
        "SOLO_TECNICO",
        "TECNICO_Y_FUNCIONAL_CON_AUTORIDAD",
        "TECNICO_Y_FUNCIONAL_SIN_AUTORIDAD",
    ]
    separacion_etiqueta: str
    separacion_detalle: str
    roles: list[RolOut]
    identidad: IdentidadOut


class RolProtegidoOut(BaseModel):
    codigo: str
    nombre: str
    capacidades: int
    fuera_de_lugar: list[str]


class IntegridadOut(BaseModel):
    integra: bool
    admin: RolProtegidoOut | None
    funcional: RolProtegidoOut | None


class ExigenciaOut(BaseModel):
    activa: bool
    version: int
    efecto: str


class DenegacionOut(BaseModel):
    id: str
    fecha: datetime
    usuario: str | None
    accion: str
    codigo: str | None
    codigo_etiqueta: str
    rol: str | None
    capacidades_excedidas: list[str]
    en_bitacora: bool


class SeparacionOut(BaseModel):
    ente: str
    integridad: IntegridadOut
    exigencia_identidad: ExigenciaOut
    administradores: list[AdministradorOut]
    denegaciones: list[DenegacionOut]
