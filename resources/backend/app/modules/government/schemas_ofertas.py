from datetime import datetime

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class OfertaEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")

    oferente_nombre: str
    oferente_documento: str
    representante: str | None = None
    tipo_sobre: str
    canal: str
    recibida_en: AwareDatetime
    funcionario_id: str
    condicion_sobre: str | None = None
    confidencial: bool = True
    motivo_sin_sello: str | None = None
    documento_ids: list[str] = Field(default_factory=list)


class OfertaDocumentoOut(BaseModel):
    version_numero: int
    huella: str
    integridad: str
    documento_id: str | None
    titulo: str | None


class OfertaResumen(BaseModel):
    id: str
    referencia: str
    oferente_nombre: str
    oferente_documento: str
    identidad_etiqueta: str
    representante: str | None
    tipo_sobre: str
    tipo_sobre_etiqueta: str
    canal: str
    canal_etiqueta: str
    recibida_en: datetime
    registrada_en: datetime
    receptor: str
    registrado_por: str | None
    confidencial: bool
    confidencialidad_etiqueta: str
    fundamento_confidencialidad: str
    situacion: str
    situacion_etiqueta: str
    condicion_sobre: str | None
    documentos_total: int
    integridad: str


class OfertaDetalle(OfertaResumen):
    documentos: list[OfertaDocumentoOut]


class CodigoEtiqueta(BaseModel):
    codigo: str
    etiqueta: str


class OfertasLista(BaseModel):
    items: list[OfertaResumen]
    total: int
    canales: list[CodigoEtiqueta]
    tipos_sobre: list[CodigoEtiqueta]
    recepcion_concluida_en: datetime | None
    puede_recibir_sin_sello: bool
    aviso_identidad: str


class ConcluirRecepcionEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")

    motivo: str | None = None


class ConcluirRecepcionOut(BaseModel):
    expediente_id: str
    recepcion_concluida_en: datetime
    version: int
