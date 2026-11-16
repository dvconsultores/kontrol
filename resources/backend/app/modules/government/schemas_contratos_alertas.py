from typing import Literal

from pydantic import BaseModel, Field


class PoliticaItem(BaseModel):
    fuente: Literal["CONTRATO", "HITO", "ENTREGABLE"]
    activo: bool
    dias_anticipacion: int | None = Field(default=None, ge=1, le=365)


class PoliticasUpdate(BaseModel):
    items: list[PoliticaItem] = Field(min_length=1, max_length=3)
