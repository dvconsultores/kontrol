"""Esquemas Pydantic para hallazgos de control gubernamental (CTL-06)."""
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class _EntradaBase(BaseModel):
    """Configuración común de los esquemas de entrada."""

    model_config = ConfigDict(extra="forbid")

    @field_validator("*", mode="before")
    @classmethod
    def recortar_texto(cls, valor):
        """Recorta espacios en blanco si el valor es una cadena."""
        if isinstance(valor, str):
            return valor.strip()
        return valor


class HallazgoIn(_EntradaBase):
    """Datos para registrar un nuevo hallazgo."""

    titulo: str = Field(min_length=3, max_length=200)
    condicion: str = Field(min_length=10, max_length=4000)
    criterio: str = Field(min_length=10, max_length=4000)
    causa: str = Field(min_length=10, max_length=4000)
    efecto: str = Field(min_length=10, max_length=4000)
    riesgo: Literal["ALTO", "MEDIO", "BAJO"]
    origen: Literal["MUESTRA", "INDEPENDIENTE"]
    muestra_id: str | None = None
    partidas: list[str] = Field(default_factory=list, max_length=50)
    origen_descripcion: str | None = Field(default=None, min_length=10, max_length=500)

    @model_validator(mode="after")
    def validar_origen(self):
        """Valida la consistencia entre el origen y los campos asociados."""
        if self.origen == "INDEPENDIENTE":
            if self.origen_descripcion is None:
                raise ValueError("origen_descripcion es obligatoria para hallazgos independientes")
            if self.muestra_id is not None:
                raise ValueError("muestra_id no aplica para hallazgos independientes")
            if self.partidas:
                raise ValueError("partidas no aplican para hallazgos independientes")
        elif self.origen == "MUESTRA":
            if self.muestra_id is None:
                raise ValueError("muestra_id es obligatorio para hallazgos por muestra")
            if self.origen_descripcion is not None:
                raise ValueError("origen_descripcion no aplica para hallazgos por muestra")

        if len(self.partidas) != len(set(self.partidas)):
            raise ValueError("partidas no puede contener elementos repetidos")

        return self


class RecomendacionIn(_EntradaBase):
    """Datos para agregar una recomendación."""

    texto: str = Field(min_length=10, max_length=2000)


class AccionIn(_EntradaBase):
    """Datos para agregar una acción correctiva."""

    recomendacion_id: str
    descripcion: str = Field(min_length=10, max_length=2000)
    cargo_id: str
    fecha_objetivo: date


class AvanceIn(_EntradaBase):
    """Datos para registrar un avance de una acción correctiva."""

    nota: str = Field(min_length=10, max_length=2000)
    porcentaje: int = Field(ge=0, le=100)
    documento_id: str | None = None


class VerificacionIn(_EntradaBase):
    """Datos para verificar un hallazgo."""

    nota: str = Field(min_length=10, max_length=2000)


class DevolucionIn(_EntradaBase):
    """Datos para devolver un hallazgo."""

    motivo: str = Field(min_length=10, max_length=2000)


class HallazgosFiltros(BaseModel):
    """Filtros para el listado de hallazgos."""

    model_config = ConfigDict(extra="forbid")

    estado: Literal["ABIERTO", "PLAN_DE_ACCION", "EN_REMEDIACION", "EVIDENCIA_PRESENTADA", "CERRADO"] | None = None
    riesgo: Literal["ALTO", "MEDIO", "BAJO"] | None = None
    origen: Literal["MUESTRA", "INDEPENDIENTE"] | None = None
    vencidas: bool = False
    texto: str | None = Field(default=None, min_length=1, max_length=100)
    abiertos: bool = False
    riesgo_minimo: Literal["ALTO", "MEDIO", "BAJO"] | None = None


class RecomendacionOut(BaseModel):
    """Recomendación de un hallazgo."""

    id: str
    orden: int
    texto: str
    created_by: str | None
    created_at: datetime


class AvanceOut(BaseModel):
    """Avance de una acción correctiva."""

    id: str
    nota: str
    porcentaje: int
    documento_id: str | None
    created_by: str | None
    created_at: datetime


class AccionOut(BaseModel):
    """Acción correctiva de un hallazgo."""

    id: str
    recomendacion_id: str
    orden: int
    descripcion: str
    cargo_id: str
    cargo_codigo: str
    cargo_denominacion: str
    unidad_id: str
    unidad_nombre: str
    ejercicio: int
    fecha_objetivo: date
    porcentaje: int
    estado: str
    vencida: bool
    documentos: list[str]
    avances: list[AvanceOut]


class HistoriaOut(BaseModel):
    """Registro histórico de un hallazgo."""

    id: str
    tipo: str
    estado_desde: str | None
    estado_hasta: str | None
    detalle: dict | None
    created_by: str | None
    created_at: datetime


class MuestraRef(BaseModel):
    """Referencia breve a una muestra de auditoría."""

    id: str
    codigo: str
    titulo: str


class HallazgoDetalle(BaseModel):
    """Detalle completo de un hallazgo."""

    id: str
    codigo: str
    titulo: str
    condicion: str
    criterio: str
    causa: str
    efecto: str
    riesgo: str
    origen: str
    origen_descripcion: str | None
    muestra: MuestraRef | None
    partidas: list[str]
    estado: str
    version: int
    presentado_por: str | None
    presentado_en: datetime | None
    verificado_por: str | None
    verificado_en: datetime | None
    nota_verificacion: str | None
    created_by: str | None
    created_at: datetime
    recomendaciones: list[RecomendacionOut]
    acciones: list[AccionOut]
    historia: list[HistoriaOut]


class HallazgoResumen(BaseModel):
    """Resumen de un hallazgo para listados."""

    id: str
    codigo: str
    titulo: str
    riesgo: str
    estado: str
    origen: str
    acciones_total: int
    acciones_vencidas: int
    created_at: datetime


class ResumenHallazgos(BaseModel):
    """Resumen global de hallazgos de la empresa."""

    abiertos: int
    pendientes_verificacion: int
    acciones_vencidas: int
    cerrados: int


class HallazgosListado(BaseModel):
    """Listado paginado de hallazgos."""

    items: list[HallazgoResumen]
    total: int
    pagina: int
    por_pagina: int
    resumen: ResumenHallazgos


class CargoResponsable(BaseModel):
    """Cargo responsable elegible para una acción correctiva."""

    id: str
    codigo: str
    denominacion: str
    unidad_nombre: str
    ejercicio: int


class CargosResponsables(BaseModel):
    """Listado de cargos responsables elegibles."""

    items: list[CargoResponsable]
