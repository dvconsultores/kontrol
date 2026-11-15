from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class InicioCreate(BaseModel):
    fecha: date
    documento_id: str
    observacion: str | None = None


class HitoCreate(BaseModel):
    descripcion: str = Field(max_length=500)
    fecha_prevista: date
    monto_previsto: Decimal | None = Field(default=None, gt=0, max_digits=18, decimal_places=2)
    porcentaje_previsto: Decimal | None = Field(default=None, gt=0, le=100, max_digits=5, decimal_places=2)
    obligatorio: bool = True


class EntregableCreate(BaseModel):
    descripcion: str = Field(max_length=500)
    fecha_vencimiento: date
    obligatorio: bool = True
    hito_id: str | None = None


class EntregaCreate(BaseModel):
    fecha_entrega: date
    documento_id: str
    observacion: str | None = Field(default=None, max_length=1000)


class RevisionCreate(BaseModel):
    resultado: Literal["CONFORME", "RECHAZADA"]
    fecha_revision: date
    observacion: str | None = Field(default=None, max_length=1000)


class ValuacionCreate(BaseModel):
    hito_id: str
    periodo_desde: date
    periodo_hasta: date
    fecha: date
    monto: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    documento_id: str


class ResolucionValuacion(BaseModel):
    resultado: Literal["CONFORMADA", "REPARADA"]
    fecha_conformidad: date
    reparos: str | None = Field(default=None, max_length=1000)


class TerminacionCreate(BaseModel):
    fecha: date
    documento_id: str
    observacion: str | None = Field(default=None, max_length=1000)


class RecepcionCreate(BaseModel):
    tipo: Literal["PARCIAL", "PROVISIONAL", "DEFINITIVA"]
    fecha: date
    documento_id: str
    observacion: str | None = Field(default=None, max_length=1000)
    hito_ids: list[str] = Field(default_factory=list)
    representante_cargo_id: str | None = None
    fin_garantia: date | None = None


class FacturaCreate(BaseModel):
    numero_documento: str = Field(max_length=40)
    fecha: date
    monto: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    hito_id: str
    recepcion_id: str
    documento_id: str
    fecha_conformidad: date


class CierreCreate(BaseModel):
    fecha: date
    documento_id: str
    evaluacion_documento_id: str
    observacion: str | None = Field(default=None, max_length=1000)


class Anulacion(BaseModel):
    motivo: str = Field(min_length=1, max_length=500)
