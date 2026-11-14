from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class SujetoAlertaOut(BaseModel):
    etiqueta: str
    valor: str


class RevisionAlertaOut(BaseModel):
    resultado: str
    resultado_etiqueta: str
    observacion: str
    revisada_por: str | None
    revisada_en: datetime


class AlertaOut(BaseModel):
    clave: str
    tipo: str
    tipo_etiqueta: str
    fecha: datetime
    titulo: str
    detalle: str
    sujetos: list[SujetoAlertaOut]
    estado: Literal["PENDIENTE", "REVISADA"]
    vigente: bool
    es_sujeto: bool
    revision: RevisionAlertaOut | None


class TipoAlertaOut(BaseModel):
    codigo: str
    etiqueta: str
    descripcion: str
    disponible: bool
    motivo_no_disponible: str | None
    requisito_habilitante: str | None
    total: int
    pendientes: int


class AlertasOut(BaseModel):
    aviso: str
    tipos: list[TipoAlertaOut]
    alertas: list[AlertaOut]


class RevisionAlertaIn(BaseModel):
    clave: str
    resultado: str
    observacion: str
