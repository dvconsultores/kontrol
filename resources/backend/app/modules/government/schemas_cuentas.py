"""Esquemas Pydantic de las cuentas bancarias públicas (TRE-01, GOV-TRE-001)."""

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

EstadoBanco = Literal["ACTIVO", "INACTIVO"]
EstadoCuenta = Literal["BORRADOR", "VIGENTE", "INACTIVA", "CERRADA"]
TipoCuenta = Literal["CORRIENTE", "AHORRO"]
MonedaCuenta = Literal["VES", "USD", "EUR"]


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


class BancoIn(_Entrada):
    """Entrada de alta de banco."""

    codigo: str
    nombre: str = Field(min_length=3, max_length=120)


class BancoCambios(_Entrada):
    """Entrada de edición de banco."""

    nombre: str | None = Field(default=None, min_length=3, max_length=120)
    estado: EstadoBanco | None = None


class CuentaIn(_Entrada):
    """Entrada de alta de cuenta bancaria."""

    denominacion: str = Field(min_length=3, max_length=200)
    banco_id: str = Field(min_length=1, max_length=36)
    tipo: TipoCuenta
    numero: str
    moneda: MonedaCuenta
    vigente_desde: date
    vigente_hasta: date | None = None


class CuentaCambios(_Entrada):
    """Entrada de edición de cuenta bancaria."""

    denominacion: str | None = Field(default=None, min_length=3, max_length=200)
    banco_id: str | None = Field(default=None, min_length=1, max_length=36)
    tipo: TipoCuenta | None = None
    numero: str | None = None
    moneda: MonedaCuenta | None = None
    vigente_desde: date | None = None
    vigente_hasta: date | None = None


class ActoCuentaIn(_Entrada):
    """Entrada de vinculación de acto a la cuenta."""

    acto_id: str = Field(min_length=1, max_length=36)


class AutorizadoIn(_Entrada):
    """Entrada de alta de autorización de cargo."""

    cargo_id: str = Field(min_length=1, max_length=36)
    acto_id: str = Field(min_length=1, max_length=36)
    vigente_desde: date


class FinAutorizacionIn(_Entrada):
    """Entrada de fin de autorización."""

    acto_id: str = Field(min_length=1, max_length=36)
    vigente_hasta: date
    motivo: str = Field(min_length=10, max_length=500)


class MotivoCuentaIn(_Entrada):
    """Entrada de inactivación y reactivación con motivo."""

    motivo: str = Field(min_length=10, max_length=500)


class CierreCuentaIn(_Entrada):
    """Entrada de cierre de cuenta."""

    motivo: str = Field(min_length=10, max_length=500)
    fecha_cierre: date


class BancoOut(BaseModel):
    """Salida de banco."""

    id: str
    codigo: str
    nombre: str
    estado: EstadoBanco
    version: int


class BancosListado(BaseModel):
    """Listado de bancos."""

    items: list[BancoOut]


class ActoReferencia(BaseModel):
    """Referencia resumida de un acto."""

    id: str
    tipo: str
    numero: str
    fecha: date
    estado: str
    asunto: str


class AutorizadoOut(BaseModel):
    """Salida de autorización de cargo."""

    id: str
    cargo_id: str
    cargo_codigo: str
    cargo_denominacion: str
    cargo_unidad: str
    cargo_vigente: bool
    acto_alta: ActoReferencia
    vigente_desde: date
    vigente_hasta: date | None
    acto_fin: ActoReferencia | None
    motivo_fin: str | None
    en_vigor: bool
    registrada_por: str | None
    registrada_en: datetime
    terminada_por: str | None
    terminada_en: datetime | None


class HistoriaCuentaOut(BaseModel):
    """Entrada de historia de la cuenta."""

    tipo: str
    detalle: dict[str, Any] | None
    registrado_por: str | None
    registrado_en: datetime


class CuentaResumen(BaseModel):
    """Resumen de cuenta bancaria."""

    id: str
    codigo: str
    denominacion: str
    banco_id: str
    banco_codigo: str
    banco_nombre: str
    tipo: TipoCuenta
    moneda: MonedaCuenta
    numero_enmascarado: str
    vigente_desde: date
    vigente_hasta: date | None
    estado: EstadoCuenta
    en_vigor: bool
    acto_sin_efecto: bool
    autorizados_en_vigor: int
    version: int


class ResumenCuentas(BaseModel):
    """Conteo de cuentas por estado."""

    borradores: int
    vigentes: int
    inactivas: int
    cerradas: int


class CuentasListado(BaseModel):
    """Listado de cuentas con resumen por estado."""

    items: list[CuentaResumen]
    resumen: ResumenCuentas


class CuentaDetalle(CuentaResumen):
    """Detalle de cuenta bancaria."""

    acto: ActoReferencia | None
    registrada_por: str | None
    registrada_en: datetime
    activada_por: str | None
    activada_en: datetime | None
    cerrada_por: str | None
    cerrada_en: datetime | None
    fecha_cierre: date | None
    motivo_cierre: str | None
    autorizados: list[AutorizadoOut]
    historia: list[HistoriaCuentaOut]


class NumeroCuentaOut(BaseModel):
    """Salida del número completo de la cuenta."""

    numero: str


class BancoOpcion(BaseModel):
    """Opción de banco para selectores."""

    id: str
    codigo: str
    nombre: str


class CargoOpcion(BaseModel):
    """Opción de cargo para selectores."""

    id: str
    codigo: str
    denominacion: str
    unidad: str


class CuentasOpciones(BaseModel):
    """Opciones para los selectores de cuentas."""

    bancos: list[BancoOpcion]
    cargos: list[CargoOpcion]
    actos: list[ActoReferencia]
