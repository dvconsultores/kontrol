"""Esquemas Pydantic de la programación financiera de caja (TRE-02, GOV-TRE-002)."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

TipoRubro = Literal["INGRESO", "DESEMBOLSO"]
EstadoRubro = Literal["ACTIVO", "INACTIVO"]
MonedaPrograma = Literal["VES", "USD", "EUR"]
EstadoPrograma = Literal["BORRADOR", "VIGENTE", "CERRADO", "DESCARTADO"]
EstadoVersion = Literal["BORRADOR", "VIGENTE", "SUPERADA", "DESCARTADA", "CERRADA"]
TipoHistoria = Literal[
    "CREADO",
    "DECLARACION",
    "LINEA",
    "ACTIVADO",
    "REPROGRAMADO",
    "DESCARTADO",
    "CERRADO",
]


class _Entrada(BaseModel):
    """Base de entrada que prohíbe campos extra y recorta cadenas."""

    model_config = ConfigDict(extra="forbid")

    @field_validator("*", mode="before")
    @classmethod
    def _recortar_cadenas(cls, valor: object) -> object:
        """Recorta los espacios de las cadenas recibidas."""
        if isinstance(valor, str):
            return valor.strip()
        return valor


class RubroIn(_Entrada):
    """Entrada de alta de rubro."""

    codigo: str = Field(min_length=1, max_length=20)
    nombre: str = Field(min_length=3, max_length=120)
    tipo: TipoRubro


class RubroCambios(_Entrada):
    """Entrada de edición de rubro."""

    nombre: str | None = Field(default=None, min_length=3, max_length=120)
    estado: EstadoRubro | None = None


class ProgramaIn(_Entrada):
    """Entrada de alta de programa."""

    ejercicio: int = Field(ge=1900, le=9999)
    moneda: MonedaPrograma
    mes_inicial: int = Field(ge=1, le=12)


class DeclaracionIn(_Entrada):
    """Entrada de alta de declaración de disponibilidad."""

    cuenta_id: str = Field(min_length=1, max_length=36)
    monto: Decimal = Field(ge=0, max_digits=18, decimal_places=2)
    fecha_corte: date
    fundamento: str = Field(min_length=10, max_length=500)


class LineaIn(_Entrada):
    """Entrada de alta de línea de programación."""

    rubro_id: str = Field(min_length=1, max_length=36)
    mes: int = Field(ge=1, le=12)
    monto: Decimal = Field(gt=0, max_digits=18, decimal_places=2)


class LineaCambios(_Entrada):
    """Entrada de edición de línea de programación."""

    monto: Decimal = Field(gt=0, max_digits=18, decimal_places=2)


class MotivoProgramaIn(_Entrada):
    """Entrada de motivo de reprogramación y cierre."""

    motivo: str = Field(min_length=10, max_length=500)


class RubroOut(BaseModel):
    """Salida de rubro."""

    id: str
    codigo: str
    nombre: str
    tipo: TipoRubro
    estado: EstadoRubro
    version: int


class RubrosListado(BaseModel):
    """Listado de rubros."""

    items: list[RubroOut]


class OpcionCuenta(BaseModel):
    """Cuenta vigente disponible para declarar."""

    id: str
    codigo: str
    denominacion: str
    banco_nombre: str


class OpcionRubro(BaseModel):
    """Rubro activo disponible para programar."""

    id: str
    codigo: str
    nombre: str
    tipo: TipoRubro


class OpcionesPrograma(BaseModel):
    """Cuentas y rubros ofrecidos para el programa."""

    cuentas: list[OpcionCuenta]
    rubros: list[OpcionRubro]


class DeclaracionOut(BaseModel):
    """Salida de declaración de disponibilidad."""

    id: str
    cuenta_id: str
    cuenta_codigo: str
    cuenta_denominacion: str
    banco_nombre: str
    monto: Decimal
    fecha_corte: date
    fundamento: str
    declarado_por: str | None
    declarado_en: datetime


class LineaOut(BaseModel):
    """Salida de línea de programación."""

    id: str
    rubro_id: str
    rubro_codigo: str
    rubro_nombre: str
    tipo: TipoRubro
    mes: int
    monto: Decimal


class MesDisponibilidadOut(BaseModel):
    """Salida de disponibilidad calculada de un mes."""

    mes: int
    inicial: Decimal
    ingresos: Decimal
    desembolsos: Decimal
    final: Decimal
    deficit: bool


class VersionProgramaOut(BaseModel):
    """Salida resumida de una versión del programa."""

    numero: int
    estado: EstadoVersion
    motivo: str | None
    activada_por: str | None
    activada_en: datetime | None
    registrado_por: str | None
    registrado_en: datetime


class HistoriaProgramaOut(BaseModel):
    """Salida de un asiento de historia del programa."""

    version_numero: int
    tipo: TipoHistoria
    detalle: dict[str, str | int | None] | None
    registrado_por: str | None
    registrado_en: datetime


class ProgramaResumen(BaseModel):
    """Resumen de programas por estado."""

    borradores: int
    vigentes: int
    cerrados: int


class ProgramaListItem(BaseModel):
    """Elemento de listado de programas."""

    id: str
    codigo: str
    ejercicio: int
    moneda: MonedaPrograma
    mes_inicial: int
    estado: EstadoPrograma
    version: int
    version_vigente: int | None
    disponibilidad_inicial: Decimal


class ProgramasListado(BaseModel):
    """Listado de programas con resumen."""

    items: list[ProgramaListItem]
    resumen: ProgramaResumen


class ProgramaDetalle(BaseModel):
    """Detalle de programa."""

    id: str
    codigo: str
    ejercicio: int
    moneda: MonedaPrograma
    mes_inicial: int
    estado: EstadoPrograma
    version: int
    version_vista: int
    version_vigente: int | None
    borrador_numero: int | None
    cerrado_por: str | None
    cerrado_en: datetime | None
    motivo_cierre: str | None
    registrado_por: str | None
    registrado_en: datetime
    declaraciones: list[DeclaracionOut]
    disponibilidad_inicial: Decimal
    lineas: list[LineaOut]
    meses: list[MesDisponibilidadOut]
    hay_deficit: bool
    versiones: list[VersionProgramaOut]
    historia: list[HistoriaProgramaOut]
