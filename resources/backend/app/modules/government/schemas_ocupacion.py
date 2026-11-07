"""Esquemas Pydantic de la API de ocupación de cargos (ORG-04)."""

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Tipos literales
# ---------------------------------------------------------------------------

FiguraAsignacion = Literal[
    "TITULAR",
    "ENCARGADURIA",
    "SUPLENCIA",
    "COMISION_SERVICIO",
    "DELEGACION_ATRIBUCIONES",
    "DELEGACION_FIRMA",
]

EstadoAsignacion = Literal[
    "BORRADOR",
    "ACTIVO",
    "REVOCADO",
    "FINALIZADO",
    "DESCARTADO",
]

SituacionAsignacion = Literal[
    "BORRADOR",
    "DESCARTADA",
    "FUTURA",
    "VIGENTE",
    "VENCIDA",
    "REVOCADA",
    "FINALIZADA",
    "SIN_EFECTO",
]

EstadoFuncionario = Literal["ACTIVO", "INACTIVO"]

TipoDocumento = Literal["V", "E", "P"]

AccionCompetencia = Literal[
    "SOLICITAR",
    "COMPROMETER",
    "CAUSAR",
    "ORDENAR_PAGO",
    "PAGAR",
    "REGISTRAR",
    "CUSTODIAR",
    "APROBAR",
    "AUDITAR",
    "FIRMAR",
]

MateriaCompetencia = Literal[
    "PRESUPUESTO",
    "CONTRATACIONES",
    "TESORERIA",
    "CONTABILIDAD",
    "BIENES",
    "EXPEDIENTE",
]

FIGURAS_DELEGACION = ("DELEGACION_ATRIBUCIONES", "DELEGACION_FIRMA")


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

class FuncionarioIn(_Entrada):
    """Alta de un funcionario."""

    nombre: str = Field(min_length=3, max_length=200)
    tipo_documento: TipoDocumento
    numero_documento: str = Field(pattern=r"^[0-9A-Za-z-]{5,20}$")


class FuncionarioCambios(_Entrada):
    """Cambios parciales sobre un funcionario."""

    nombre: str | None = Field(default=None, min_length=3, max_length=200)
    estado: EstadoFuncionario | None = None


class CompetenciaDelegadaIn(_Entrada):
    """Competencia delegada por acción y materia."""

    accion: AccionCompetencia
    materia: MateriaCompetencia


class AsignacionIn(_Entrada):
    """Alta de una asignación de cargo."""

    funcionario_id: str = Field(min_length=1, max_length=36)
    cargo_id: str = Field(min_length=1, max_length=36)
    figura: FiguraAsignacion
    cargo_origen_id: str | None = Field(default=None, max_length=36)
    acto_id: str = Field(min_length=1, max_length=36)
    desde: date
    hasta: date | None = None
    fundamento: str = Field(min_length=10, max_length=500)
    rendicion: str | None = Field(default=None, min_length=10, max_length=500)
    maxima_autoridad: bool = False
    autorizacion_concejo: str | None = Field(default=None, min_length=5, max_length=200)
    declara_delegable: bool = False
    competencias: list[CompetenciaDelegadaIn] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validar(self) -> "AsignacionIn":
        if self.hasta is not None and self.hasta < self.desde:
            raise ValueError("La fecha final no puede ser anterior a la inicial")

        es_delegacion = self.figura in FIGURAS_DELEGACION

        if es_delegacion and not self.competencias:
            raise ValueError("Indique las competencias delegadas")
        if es_delegacion and not self.rendicion:
            raise ValueError(
                "Indique cómo se rendirá cuenta de la delegación (LOAP art. 35)"
            )
        if es_delegacion and not self.declara_delegable:
            raise ValueError(
                "Declare que la competencia no es indelegable (LOAP art. 35)"
            )
        if not es_delegacion and self.competencias:
            raise ValueError("Solo una delegación lleva competencias")

        pares = [(c.accion, c.materia) for c in self.competencias]
        if len(pares) != len(set(pares)):
            raise ValueError("Hay competencias repetidas")

        if self.figura in ("SUPLENCIA", "COMISION_SERVICIO") and self.hasta is None:
            raise ValueError("Esta figura exige fecha final")

        if self.maxima_autoridad and self.figura != "SUPLENCIA":
            raise ValueError("Solo una suplencia puede marcar a la máxima autoridad")

        return self


class DescartarIn(_Entrada):
    """Descarte de un borrador de asignación."""

    motivo: str = Field(min_length=10, max_length=500)


class RevocarIn(_Entrada):
    """Revocación de una asignación."""

    acto_id: str = Field(min_length=1, max_length=36)
    fecha: date
    motivo: str = Field(min_length=10, max_length=500)


class FinalizarIn(_Entrada):
    """Finalización de una asignación."""

    fecha: date
    motivo: str = Field(min_length=10, max_length=500)


class AvocarIn(_Entrada):
    """Avocación de una competencia."""

    acto_id: str = Field(min_length=1, max_length=36)
    asunto: str = Field(min_length=10, max_length=500)


# ---------------------------------------------------------------------------
# Salidas
# ---------------------------------------------------------------------------

class FuncionarioOut(BaseModel):
    """Funcionario expuesto por la API."""

    id: str
    codigo: str
    nombre: str
    documento: str
    estado: EstadoFuncionario
    version: int
    creado_en: datetime


class FuncionariosListado(BaseModel):
    """Listado paginado de funcionarios."""

    items: list[FuncionarioOut]
    total: int
    pagina: int
    por_pagina: int


class HistoriaOcupacionOut(BaseModel):
    """Entrada del historial de una entidad."""

    id: str
    tipo: str
    detalle: dict[str, Any] | None
    actor: str | None
    creado_en: datetime


class ReferenciaFuncionario(BaseModel):
    """Referencia mínima a un funcionario."""

    id: str
    codigo: str
    nombre: str
    documento: str


class ReferenciaCargo(BaseModel):
    """Referencia mínima a un cargo."""

    id: str
    codigo: str
    nombre: str
    unidad_id: str
    unidad: str
    ejercicio: int


class ReferenciaActo(BaseModel):
    """Referencia mínima a un acto administrativo."""

    id: str
    tipo: str
    numero: str
    fecha: date
    status: str
    fecha_eficacia: date | None
    medio: str | None
    emisor_cargo_id: str
    emisor_cargo: str
    funcionario: str
    asunto: str


class CompetenciaOcupacionOut(BaseModel):
    """Competencia expuesta por la API."""

    accion: str
    materia: str
    tipo_limite: str
    monto: str | None
    moneda: str | None


class AsignacionResumen(BaseModel):
    """Resumen de una asignación de cargo."""

    id: str
    codigo: str
    figura: FiguraAsignacion
    figura_etiqueta: str
    funcionario: ReferenciaFuncionario
    cargo: ReferenciaCargo
    cargo_origen: ReferenciaCargo | None
    acto: ReferenciaActo
    desde: date
    hasta: date | None
    fin_efectivo: date | None
    status: EstadoAsignacion
    situacion: SituacionAsignacion
    version: int


class AvocacionOut(BaseModel):
    """Avocación expuesta por la API."""

    id: str
    asunto: str
    acto: ReferenciaActo
    actor: str | None
    creado_en: datetime


class AsignacionDetalle(AsignacionResumen):
    """Detalle completo de una asignación de cargo."""

    fundamento: str
    rendicion: str | None
    maxima_autoridad: bool
    autorizacion_concejo: str | None
    declara_delegable: bool
    acto_revocacion: ReferenciaActo | None
    motivo_fin: str | None
    competencias: list[CompetenciaOcupacionOut]
    autoridad: list[CompetenciaOcupacionOut]
    ejerce: bool
    registrada_por: str | None
    activada_por: str | None
    activada_en: datetime | None
    terminada_por: str | None
    terminada_en: datetime | None
    historia: list[HistoriaOcupacionOut]
    avocaciones: list[AvocacionOut]


class AsignacionesListado(BaseModel):
    """Listado paginado de asignaciones en una fecha dada."""

    items: list[AsignacionResumen]
    total: int
    pagina: int
    por_pagina: int
    fecha: date


class FuncionarioDetalle(FuncionarioOut):
    """Detalle de un funcionario con su historia y asignaciones."""

    historia: list[HistoriaOcupacionOut]
    asignaciones: list[AsignacionResumen]


class OcupacionCargoFila(BaseModel):
    """Fila de ocupación por cargo."""

    cargo: ReferenciaCargo
    titular: AsignacionResumen | None
    ejerce: AsignacionResumen | None
    vacante: bool
    delegaciones: int


class OcupacionListado(BaseModel):
    """Listado paginado de ocupación de cargos."""

    ejercicio: int
    fecha: date
    items: list[OcupacionCargoFila]
    total: int
    pagina: int
    por_pagina: int


class CargoOcupacion(BaseModel):
    """Detalle de ocupación de un cargo."""

    cargo: ReferenciaCargo
    fecha: date
    titular: AsignacionResumen | None
    ejerce: AsignacionResumen | None
    vacante: bool
    delegaciones: list[AsignacionResumen]
    competencias: list[CompetenciaOcupacionOut]
    historial: list[AsignacionResumen]


class FiguraOut(BaseModel):
    """Figura de asignación expuesta en el catálogo."""

    codigo: str
    etiqueta: str
    grupo: str
    base_legal: str
    descripcion: str
    exige_fin: bool
    exige_cargo_origen: bool
    exige_gaceta: bool
    lleva_competencias: bool


class InstrumentoOut(BaseModel):
    """Instrumento expuesto en el catálogo."""

    codigo: str
    etiqueta: str


class CatalogoOcupacion(BaseModel):
    """Catálogo de ocupación de cargos."""

    figuras: list[FiguraOut]
    instrumentos: list[InstrumentoOut]
    situaciones: list[str]


class OpcionFuncionario(BaseModel):
    """Opción de funcionario para selectores."""

    id: str
    codigo: str
    nombre: str


class OpcionCargo(BaseModel):
    """Opción de cargo para selectores."""

    id: str
    codigo: str
    nombre: str
    unidad: str
    ejercicio: int
    competencias: list[CompetenciaOcupacionOut]


class OpcionActo(BaseModel):
    """Opción de acto para selectores."""

    id: str
    numero: str
    tipo: str
    fecha: date
    fecha_eficacia: date | None
    medio: str | None
    emisor_cargo_id: str
    emisor_cargo: str
    asunto: str


class OpcionesOcupacion(BaseModel):
    """Opciones de ocupación para selectores."""

    funcionarios: list[OpcionFuncionario]
    cargos: list[OpcionCargo]
    actos: list[OpcionActo]
