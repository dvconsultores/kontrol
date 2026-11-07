"""Esquemas Pydantic para las políticas de controles de cierre (CTL-10)."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

AccionCierre = Literal["ORG02_CERRAR_ESTRUCTURA", "TRE02_CERRAR_PROGRAMA"]
EstadoPoliticaCierre = Literal["BORRADOR", "VIGENTE", "RETIRADA"]
TipoControlCierre = Literal["HALLAZGOS_ABIERTOS", "ACTOS_SIN_EFICACIA"]
RiesgoMinimoCierre = Literal["ALTO", "MEDIO", "BAJO"]
EventoPoliticaCierre = Literal[
    "CREADA", "ACTUALIZADA", "CONTROL_ANADIDO", "CONTROL_RETIRADO", "ACTIVADA", "RETIRADA"
]


class _Entrada(BaseModel):
    """Base de entrada que prohíbe campos extra y recorta cadenas."""

    model_config = ConfigDict(extra="forbid")

    @field_validator("*", mode="before")
    @classmethod
    def _recortar_cadenas(cls, valor: object) -> object:
        if isinstance(valor, str):
            return valor.strip()
        return valor


class PoliticaIn(_Entrada):
    """Datos para crear una política de controles de cierre."""

    nombre: str = Field(min_length=3, max_length=200)
    accion_cierre: AccionCierre
    fundamento: str = Field(min_length=10, max_length=1000)
    vigente_desde: date
    vigente_hasta: date | None = None

    @model_validator(mode="after")
    def _validar_vigencia(self) -> "PoliticaIn":
        if self.vigente_hasta is not None and self.vigente_hasta < self.vigente_desde:
            raise ValueError("La vigencia final no puede ser anterior a la inicial")
        return self


class PoliticaCambios(_Entrada):
    """Cambios opcionales para una política en estado BORRADOR."""

    nombre: str | None = Field(default=None, min_length=3, max_length=200)
    fundamento: str | None = Field(default=None, min_length=10, max_length=1000)
    vigente_desde: date | None = None
    vigente_hasta: date | None = None


class ControlIn(_Entrada):
    """Datos para añadir un control a una política en BORRADOR."""

    tipo: TipoControlCierre
    riesgo_minimo: RiesgoMinimoCierre | None = None
    materialidad: str = Field(min_length=10, max_length=500)

    @model_validator(mode="after")
    def _validar_riesgo(self) -> "ControlIn":
        if self.tipo == "HALLAZGOS_ABIERTOS" and self.riesgo_minimo is None:
            raise ValueError("Los controles de hallazgos abiertos exigen riesgo mínimo")
        if self.tipo == "ACTOS_SIN_EFICACIA" and self.riesgo_minimo is not None:
            raise ValueError("Los controles de actos sin eficacia no admiten riesgo mínimo")
        return self


class MotivoRetiroIn(_Entrada):
    """Motivo para retirar una política."""

    motivo: str = Field(min_length=10, max_length=500)


class ItemCatalogoCierre(BaseModel):
    """Item del catálogo de cierres."""

    codigo: str
    etiqueta: str


class TipoCatalogoCierre(ItemCatalogoCierre):
    """Tipo de control del catálogo."""

    requiere_riesgo: bool


class CatalogoCierres(BaseModel):
    """Catálogo de acciones de cierre y tipos de control."""

    acciones: list[ItemCatalogoCierre]
    tipos: list[TipoCatalogoCierre]


class ControlOut(BaseModel):
    """Control de una política."""

    id: str
    tipo: TipoControlCierre
    riesgo_minimo: RiesgoMinimoCierre | None
    materialidad: str


class HistoriaPoliticaOut(BaseModel):
    """Entrada de historia de una política."""

    evento: EventoPoliticaCierre
    detalle: dict | None = None
    usuario: str | None = None
    instante: datetime


class PoliticaResumen(BaseModel):
    """Resumen de política de controles de cierre."""

    id: str
    codigo: str
    nombre: str
    accion_cierre: AccionCierre
    fundamento: str
    estado: EstadoPoliticaCierre
    vigente_desde: date
    vigente_hasta: date | None
    efectiva_hoy: bool
    version: int


class PoliticaDetalle(PoliticaResumen):
    """Detalle completo de una política de controles de cierre."""

    activada_por: str | None
    activada_en: datetime | None
    retirada_por: str | None
    retirada_en: datetime | None
    motivo_retiro: str | None
    controles: list[ControlOut]
    historia: list[HistoriaPoliticaOut]


class ResumenCierres(BaseModel):
    """Resumen agregado de políticas de cierre."""

    borradores: int
    vigentes: int
    retiradas: int


class PoliticasListado(BaseModel):
    """Listado paginado de políticas de cierre."""

    items: list[PoliticaResumen]
    total: int
    resumen: ResumenCierres


class MuestraBloqueoCierre(BaseModel):
    """Pendiente mostrado en un cierre bloqueado."""

    codigo: str | None = None
    numero: str | None = None
    titulo: str | None = None
    asunto: str | None = None
    ruta: str


class ControlBloqueoOut(BaseModel):
    """Control que bloquea un cierre."""

    tipo: TipoControlCierre
    etiqueta: str
    materialidad: str
    pendientes: int
    muestra: list[MuestraBloqueoCierre]
    ruta_lista: str


class BloqueoOut(BaseModel):
    """Cierre bloqueado por una política material de Control Interno."""

    id: str
    instante: datetime
    politica_id: str | None
    politica_codigo: str | None
    accion_cierre: str | None
    objeto_tipo: str | None
    objeto_id: str | None
    objeto_codigo: str | None
    total: int | None
    usuario: str | None


class BloqueosListado(BaseModel):
    """Listado paginado de cierres bloqueados."""

    items: list[BloqueoOut]
    total: int
    pagina: int
    tamano: int
