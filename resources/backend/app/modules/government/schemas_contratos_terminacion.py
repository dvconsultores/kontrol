"""Esquemas Pydantic de la terminación del contrato (CNT-07)."""

from datetime import date

from pydantic import BaseModel


class TerminacionCreate(BaseModel):
    figura: str
    causal: str | None = None
    causal_referencia: str | None = None
    hechos: str | None = None
    fundamento: str | None = None
    act_id: str | None = None
    apertura_act_id: str | None = None
    document_id: str | None = None
    conclusion_alcance: str | None = None
    conclusion_hasta: date | None = None


class TerminacionUpdate(BaseModel):
    figura: str | None = None
    causal: str | None = None
    causal_referencia: str | None = None
    hechos: str | None = None
    fundamento: str | None = None
    act_id: str | None = None
    apertura_act_id: str | None = None
    document_id: str | None = None
    conclusion_alcance: str | None = None
    conclusion_hasta: date | None = None
