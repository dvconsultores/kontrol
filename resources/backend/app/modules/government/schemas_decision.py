from pydantic import BaseModel, ConfigDict, Field


class OpcionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    posicion: int = Field(ge=1, le=3)
    offer_id: str = Field(min_length=36, max_length=36)


class RechazoIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    offer_id: str = Field(min_length=36, max_length=36)
    causal: str = Field(min_length=1, max_length=16)
    motivacion: str = Field(min_length=1, max_length=4000)


class RecomendacionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    resultado_recomendado: str = Field(min_length=1, max_length=24)
    causal_desierta: str | None = Field(default=None, max_length=16)
    motivacion: str = Field(min_length=1, max_length=8000)
    examen_legal: str = Field(min_length=1, max_length=8000)
    examen_financiero: str = Field(min_length=1, max_length=8000)
    examen_tecnico: str = Field(min_length=1, max_length=8000)
    resultado_matriz: str = Field(min_length=1, max_length=8000)
    medidas_promocion: str | None = Field(default=None, max_length=8000)
    firmante_ids: list[str] = Field(min_length=1)
    opciones: list[OpcionIn] = Field(default_factory=list)
    rechazos: list[RechazoIn] = Field(default_factory=list)
    sustituye_id: str | None = Field(default=None, min_length=36, max_length=36)
    motivo_sustitucion: str | None = Field(default=None, max_length=2000)


class DecisionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resultado: str = Field(min_length=1, max_length=16)
    recomendacion_id: str | None = Field(default=None, min_length=36, max_length=36)
    acto_id: str = Field(min_length=36, max_length=36)
    oferta_id: str | None = Field(default=None, min_length=36, max_length=36)
    causal_desierta: str | None = Field(default=None, max_length=16)
    causal_nulidad: str | None = Field(default=None, max_length=24)
    anula_id: str | None = Field(default=None, min_length=36, max_length=36)
    motivacion: str = Field(min_length=1, max_length=8000)
