from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, cast

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field
from sqlalchemy import Numeric

from app.modules.government.models import GovernmentProcurementOfferAmount
from app.shared.money import texto_decimal

_COLUMNA_MONTO = cast(Numeric, GovernmentProcurementOfferAmount.__table__.c.total_con_tributos.type)
if TYPE_CHECKING:
    MontoNoNegativo = Decimal
    MontoPositivo = Decimal
else:
    MontoNoNegativo = texto_decimal(_COLUMNA_MONTO, positivo=True, admite_cero=True)
    MontoPositivo = texto_decimal(_COLUMNA_MONTO, positivo=True)


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


class MontoOfertaOut(BaseModel):
    version: int
    moneda: str
    monto_sin_iva: str
    tributos: str
    total_con_tributos: str
    suma_coincide: bool
    diferencia: str
    soporte_tipo: str
    soporte_etiqueta: str
    soporte_titulo: str | None
    soporte_version: int
    soporte_huella: str
    motivo: str | None
    registrada_por: str | None
    registrada_en: datetime


class SoporteMontoOut(BaseModel):
    tipo: str
    etiqueta: str
    documento_id: str
    titulo: str | None
    version: int


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
    monto_estado: str
    monto_estado_etiqueta: str
    monto: MontoOfertaOut | None
    monto_bloqueo: str | None


class OfertaDetalle(OfertaResumen):
    documentos: list[OfertaDocumentoOut]
    montos_historial: list[MontoOfertaOut]
    soportes_monto: list[SoporteMontoOut]


class MontoEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")

    moneda: str
    monto_sin_iva: MontoNoNegativo
    tributos: MontoNoNegativo
    total_con_tributos: MontoPositivo
    soporte_tipo: str
    soporte_documento_id: str
    motivo: str | None = None
    version_anterior: int | None = None


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
