from datetime import date, datetime

from pydantic import BaseModel, Field


class RendicionResponsableOut(BaseModel):
    funcionario: str
    funcionario_codigo: str
    cargo: str
    cargo_codigo: str
    unidad: str
    unidad_codigo: str
    figura: str
    asignacion_codigo: str


class RendicionPiezaOut(BaseModel):
    id: str
    ordinal: int | None
    evento_id: str
    fecha: datetime
    proceso: str
    proceso_nombre: str
    accion: str
    accion_etiqueta: str
    entidad: str
    entidad_id: str | None
    usuario: str
    referencia: str
    objeto: dict | None = None
    documentos: list[dict]
    huella: str
    ruta_evento: str


class RendicionParticipacionOut(BaseModel):
    fecha: date
    oficio: str
    vence: date
    en_plazo: bool
    registrada_por: str | None = None
    registrada_en: datetime | None = None


class RendicionCalificacionOut(BaseModel):
    resultado: str
    organo: str
    informe_numero: str
    informe_fecha: date
    fundamento: str | None = None
    registrada_por: str | None = None
    registrada_en: datetime | None = None


class RendicionFenecimientoOut(BaseModel):
    auto_numero: str
    auto_fecha: date
    fundamento: str | None = None
    registrado_por: str | None = None
    registrado_en: datetime | None = None


class RendicionHallazgoOut(BaseModel):
    ordinal: int
    referencia: str
    objeto: dict | None = None


class RendicionInformeOut(BaseModel):
    sha256: str | None
    bytes: int | None


class RendicionExpedienteOut(BaseModel):
    id: str
    codigo: str
    numero_version: int
    version: int
    estado: str
    anterior_id: str | None = None
    sustituido_por_id: str | None = None
    sustitucion_motivo: str | None = None
    denominacion: str
    ejercicio: int | None = None
    periodo_desde: date
    periodo_hasta: date
    fecha_corte: date
    observaciones: str | None = None
    ente: str
    responsable: RendicionResponsableOut
    piezas: list[RendicionPiezaOut] = []
    formado_en: datetime | None = None
    formado_por: str | None = None
    snapshot_sha256: str | None = None
    informe: RendicionInformeOut | None = None
    participacion: RendicionParticipacionOut | None = None
    plazo_participacion: date
    calificacion: RendicionCalificacionOut | None = None
    fenecimiento: RendicionFenecimientoOut | None = None
    hallazgos: list[RendicionHallazgoOut] = []


class RendicionExpedienteCreate(BaseModel):
    denominacion: str = Field(min_length=3, max_length=200)
    periodo_desde: date
    periodo_hasta: date
    fecha_corte: date
    ejercicio: int | None = None
    observaciones: str | None = Field(default=None, max_length=1000)
    assignment_id: str


class RendicionExpedienteUpdate(BaseModel):
    denominacion: str = Field(min_length=3, max_length=200)
    periodo_desde: date
    periodo_hasta: date
    fecha_corte: date
    ejercicio: int | None = None
    observaciones: str | None = Field(default=None, max_length=1000)
    assignment_id: str


class RendicionPiezaCreate(BaseModel):
    evento_id: str


class RendicionParticipacionCreate(BaseModel):
    fecha: date
    oficio: str = Field(min_length=3, max_length=100)


class RendicionCalificacionCreate(BaseModel):
    resultado: str
    organo: str = Field(min_length=3, max_length=200)
    informe_numero: str = Field(min_length=1, max_length=50)
    informe_fecha: date
    fundamento: str | None = Field(default=None, max_length=1000)


class RendicionFenecimientoCreate(BaseModel):
    auto_numero: str = Field(min_length=1, max_length=50)
    auto_fecha: date
    fundamento: str | None = Field(default=None, max_length=1000)


class RendicionNuevaVersionCreate(BaseModel):
    motivo: str = Field(max_length=500)


class RendicionCandidataOut(BaseModel):
    evento_id: str
    fecha: datetime
    proceso: str
    proceso_nombre: str
    accion: str
    accion_etiqueta: str
    usuario: str
    referencia: str
    objeto: dict | None = None
    incluida: bool


class RendicionCandidatasList(BaseModel):
    items: list[RendicionCandidataOut]
    total: int
    pagina: int
    por_pagina: int


class RendicionListFiltros(BaseModel):
    estado: str | None = None
    texto: str | None = None
    desde: date | None = None
    hasta: date | None = None
    responsable: str | None = None
    unidad: str | None = None
    pagina: int = 1
    por_pagina: int = 20


class RendicionResumenFila(BaseModel):
    concepto: str
    fuente: str
    filtro: str
    periodo: str
    conjunto: str
    regla: str
    resultado: int | str


class RendicionReporteOut(BaseModel):
    provisional: bool
    generado_en: datetime | None
    expediente: dict
    ente: str
    responsable: RendicionResponsableOut
    piezas: list[RendicionPiezaOut]
    resumen: list[RendicionResumenFila]
    hallazgos: list[RendicionHallazgoOut]
    snapshot_sha256: str | None


class RendicionIntegridadPieza(BaseModel):
    ordinal: int
    estado: str
    detalle: str


class RendicionIntegridadOut(BaseModel):
    estado: str
    snapshot_ok: bool
    informe_ok: bool
    piezas: list[RendicionIntegridadPieza]


class RendicionHistorialItem(BaseModel):
    fecha: datetime
    accion: str
    accion_etiqueta: str
    usuario: str
    motivo: str | None = None
    version: int | None = None
