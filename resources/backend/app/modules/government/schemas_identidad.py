"""Esquemas Pydantic de la API de identidad institucional (ORG-06)."""

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Tipos literales
# ---------------------------------------------------------------------------

EstadoVinculo = Literal["BORRADOR", "ACTIVO", "CERRADO", "REVOCADO", "DESCARTADO"]
SituacionVinculo = Literal[
    "BORRADOR", "DESCARTADA", "FUTURA", "VIGENTE", "VENCIDA", "CERRADA", "REVOCADA"
]
CategoriaSeparacion = Literal[
    "OPERATIVO", "APROBADOR", "CONTROL_INTERNO", "AUDITORIA", "ADMINISTRACION_TECNICA"
]
MotivoSinAutoridad = Literal[
    "SIN_VINCULO", "CUENTA_INACTIVA", "FUNCIONARIO_INACTIVO", "SIN_OCUPACION"
]


# ---------------------------------------------------------------------------
# Base de entrada
# ---------------------------------------------------------------------------

class _Entrada(BaseModel):
    """Base de entrada que prohíbe campos extra y recorta cadenas."""

    model_config = ConfigDict(extra="forbid")

    @field_validator("*", mode="before")
    @classmethod
    def _recortar_cadenas(cls, valor: object) -> object:
        if isinstance(valor, str):
            return valor.strip()
        return valor


# ---------------------------------------------------------------------------
# Entradas
# ---------------------------------------------------------------------------

class VinculoIn(_Entrada):
    """Cuerpo de alta o modificación de un vínculo."""

    user_id: str = Field(min_length=1, max_length=36)
    official_id: str = Field(min_length=1, max_length=36)
    desde: date
    hasta: date | None = None
    motivo: str = Field(min_length=10, max_length=500)
    soporte: str | None = Field(default=None, min_length=3, max_length=200)

    @field_validator("soporte", mode="before")
    @classmethod
    def _soporte_vacio_a_none(cls, valor: object) -> object:
        if valor == "":
            return None
        return valor

    @model_validator(mode="after")
    def _validar_rango_fechas(self) -> "VinculoIn":
        if self.hasta is not None and self.hasta < self.desde:
            raise ValueError("hasta debe ser mayor o igual que desde")
        return self


class VinculoDescartarIn(_Entrada):
    """Cuerpo para descartar un vínculo."""

    motivo: str = Field(min_length=1)


class VinculoFinIn(_Entrada):
    """Cuerpo para cerrar o revocar un vínculo."""

    fecha: date
    motivo: str = Field(min_length=10, max_length=500)


class CategoriaRolIn(_Entrada):
    """Cuerpo para crear una categoría de rol."""

    role_id: str = Field(min_length=1, max_length=36)
    categoria: CategoriaSeparacion
    desde: date
    motivo: str = Field(min_length=10, max_length=500)


class CategoriaRetirarIn(_Entrada):
    """Cuerpo para retirar una categoría de rol."""

    fecha: date
    motivo: str = Field(min_length=10, max_length=500)


class PoliticaIdentidadIn(_Entrada):
    """Cuerpo para cambiar la política de identidad."""

    exige_identidad: bool
    motivo: str = Field(min_length=10, max_length=500)


# ---------------------------------------------------------------------------
# Referencias de salida
# ---------------------------------------------------------------------------

class RefCuentaIdentidad(BaseModel):
    """Referencia a una cuenta de usuario."""

    id: str
    usuario: str
    estado: str


class RefFuncionarioIdentidad(BaseModel):
    """Referencia a un funcionario con documento enmascarado."""

    id: str
    codigo: str
    nombre: str
    documento: str


class HistoriaIdentidadOut(BaseModel):
    """Evento histórico de una entidad de identidad."""

    id: str
    tipo: str
    detalle: Any
    actor: str | None = None
    creado_en: datetime


class CompetenciaIdentidadOut(BaseModel):
    """Competencia de autoridad de una ocupación."""

    accion: str
    materia: str
    tipo_limite: str | None = None
    monto: float | None = None
    moneda: str | None = None


class OcupacionInstitucional(BaseModel):
    """Ocupación institucional de un funcionario."""

    asignacion_id: str | None = None
    codigo: str
    figura: str
    figura_etiqueta: str
    cargo_id: str | None = None
    cargo: str
    cargo_codigo: str | None = None
    unidad_id: str | None = None
    unidad: str
    ejercicio: int
    ejerce: bool
    situacion: str
    desde: date
    hasta: date | None = None
    autoridad: list[CompetenciaIdentidadOut] = Field(default_factory=list)
    avocaciones: int = 0


class RolIdentidadOut(BaseModel):
    """Rol institucional."""

    id: str
    codigo: str
    nombre: str


class ConflictoCategoria(BaseModel):
    """Conflicto detectado entre dos categorías de separación."""

    regla_codigo: str
    regla_nombre: str
    categoria_a: str
    categoria_b: str


class EnteIdentidad(BaseModel):
    """Ente institucional."""

    id: str
    nombre: str


class RefVinculoIdentidad(BaseModel):
    """Referencia a un vínculo."""

    id: str
    codigo: str
    situacion: SituacionVinculo


class UnidadIdentidad(BaseModel):
    """Unidad institucional."""

    id: str
    nombre: str


class ContextoInstitucional(BaseModel):
    """Contexto institucional de una cuenta a una fecha."""

    fecha: date
    es_historica: bool
    ente: EnteIdentidad
    cuenta: RefCuentaIdentidad
    vinculo: RefVinculoIdentidad | None = None
    funcionario: RefFuncionarioIdentidad | None = None
    ocupaciones: list[OcupacionInstitucional] = Field(default_factory=list)
    unidades: list[UnidadIdentidad] = Field(default_factory=list)
    roles: list[RolIdentidadOut] = Field(default_factory=list)
    categorias: list[str] = Field(default_factory=list)
    conflictos: list[ConflictoCategoria] = Field(default_factory=list)
    tiene_autoridad: bool = False
    motivo_sin_autoridad: MotivoSinAutoridad | None = None


class VinculoResumen(BaseModel):
    """Resumen de un vínculo."""

    id: str
    codigo: str
    cuenta: RefCuentaIdentidad
    funcionario: RefFuncionarioIdentidad
    desde: date
    hasta: date | None = None
    fin_efectivo: date | None = None
    status: EstadoVinculo
    situacion: SituacionVinculo
    version: int


class VinculoDetalle(VinculoResumen):
    """Detalle completo de un vínculo."""

    motivo: str
    soporte: str | None = None
    motivo_fin: str | None = None
    registrado_por: str | None = None
    activado_por: str | None = None
    activado_en: datetime | None = None
    terminado_por: str | None = None
    terminado_en: datetime | None = None
    historia: list[HistoriaIdentidadOut] = Field(default_factory=list)
    contexto: ContextoInstitucional | None = None


class VinculosListado(BaseModel):
    """Listado paginado de vínculos."""

    items: list[VinculoResumen] = Field(default_factory=list)
    total: int
    pagina: int
    por_pagina: int
    fecha: date


class CategoriaRolOut(BaseModel):
    """Categoría de rol asociada a un funcionario."""

    id: str
    role_id: str
    rol_codigo: str
    rol_nombre: str
    categoria: CategoriaSeparacion
    categoria_etiqueta: str
    desde: date
    hasta: date | None = None
    status: str
    motivo: str
    version: int


class CategoriasListado(BaseModel):
    """Listado de categorías de rol y roles disponibles."""

    items: list[CategoriaRolOut] = Field(default_factory=list)
    roles: list[RolIdentidadOut] = Field(default_factory=list)


class ConflictoVinculo(BaseModel):
    """Conflicto de categorías de un vínculo."""

    vinculo_id: str
    codigo: str
    cuenta: RefCuentaIdentidad
    funcionario: RefFuncionarioIdentidad
    conflictos: list[ConflictoCategoria] = Field(default_factory=list)


class ConflictosIdentidad(BaseModel):
    """Listado de conflictos de identidad."""

    items: list[ConflictoVinculo] = Field(default_factory=list)


class PoliticaIdentidadOut(BaseModel):
    """Política de identidad institucional."""

    exige_identidad: bool
    version: int
    motivo: str | None = None
    historia: list[HistoriaIdentidadOut] = Field(default_factory=list)


class CategoriaCatalogo(BaseModel):
    """Entrada del catálogo de categorías."""

    codigo: CategoriaSeparacion
    etiqueta: str
    descripcion: str


class CatalogoIdentidad(BaseModel):
    """Catálogo de identidad institucional."""

    categorias: list[CategoriaCatalogo] = Field(default_factory=list)
    situaciones: list[SituacionVinculo] = Field(default_factory=list)
    estados: list[EstadoVinculo] = Field(default_factory=list)


class OpcionCuentaIdentidad(BaseModel):
    """Opción de cuenta para el selector."""

    id: str
    usuario: str
    estado: str
    vinculada: bool


class OpcionFuncionarioIdentidad(BaseModel):
    """Opción de funcionario para el selector."""

    id: str
    codigo: str
    nombre: str
    documento: str
    vinculado: bool


class OpcionesIdentidad(BaseModel):
    """Opciones para alta de vínculos."""

    cuentas: list[OpcionCuentaIdentidad] = Field(default_factory=list)
    funcionarios: list[OpcionFuncionarioIdentidad] = Field(default_factory=list)

