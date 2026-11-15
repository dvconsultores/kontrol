"""Esquemas Pydantic de la supervisión del contrato (CNT-04)."""
from datetime import date

from pydantic import BaseModel


class DesignacionCreate(BaseModel):
    funcionario_id: str
    asignacion_id: str
    acto_id: str
    desde: date
    motivo: str | None = None
    sustituye_id: str | None = None
