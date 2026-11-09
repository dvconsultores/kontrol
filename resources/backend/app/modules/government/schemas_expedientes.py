from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator


class _Entrada(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("*", mode="before")
    @classmethod
    def _strip(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip()
        return value


TipoContratacion = Literal["BIENES", "SERVICIOS", "OBRAS"]
ModalidadDeclarada = Literal[
    "CONCURSO_ABIERTO",
    "CONCURSO_CERRADO",
    "CONSULTA_PRECIOS",
    "CONTRATACION_DIRECTA",
]
RolResponsable = Literal["RESPONSABLE", "REQUIRENTE", "SUSTANCIACION", "CUSTODIA"]
ClaseActuacion = Literal["ACTUACION", "DECISION"]


class ExpedienteIn(_Entrada):
    numero: str
    fecha_inicio: date
    objeto: str
    partes: str | None = None
    tipo_contratacion: TipoContratacion
    modalidad_declarada: ModalidadDeclarada | None = None
    modalidad_fundamento: str | None = None
    modalidad_fuente: str | None = None
    unidad_id: str
    responsable_id: str


class ExpedienteEdicionIn(_Entrada):
    numero: str
    fecha_inicio: date
    objeto: str
    partes: str | None = None
    tipo_contratacion: TipoContratacion
    modalidad_declarada: ModalidadDeclarada | None = None
    modalidad_fundamento: str | None = None
    modalidad_fuente: str | None = None
    unidad_id: str
    motivo: str


class ExpedienteFinIn(_Entrada):
    fecha: date
    motivo: str


class ExpedienteDescarteIn(_Entrada):
    motivo: str


class ExpedienteResponsableIn(_Entrada):
    funcionario_id: str
    rol: RolResponsable
    desde: date | None = None


class ExpedienteComisionIn(_Entrada):
    comision_id: str | None = None
    no_aplica_motivo: str | None = None
    motivo: str | None = None


class ExpedienteActuacionIn(_Entrada):
    clase: ClaseActuacion
    fecha: date
    titulo: str
    detalle: str | None = None
    resultado: str | None = None
    funcionario_id: str
    acto_id: str | None = None
    folio_id: str | None = None
    hito_id: str | None = None
    rectifica_id: str | None = None
    motivo: str | None = None


class ExpedienteFolioIn(_Entrada):
    clase: str
    documento_id: str | None = None
    acto_id: str | None = None
    hito_id: str | None = None
    reservado: bool = False
    motivo_reserva: str | None = None


class ExpedienteHitoIn(_Entrada):
    nombre: str
    fuente: str | None = None
    fecha_prevista: date
    funcionario_id: str | None = None


class ExpedienteHitoCambioIn(_Entrada):
    fecha_prevista: date
    fecha_real: date | None = None
    no_aplica: bool = False
    fuente: str | None = None
    funcionario_id: str | None = None
    motivo: str | None = None


class ExpedienteEtiqueta(BaseModel):
    codigo: str
    etiqueta: str


class ExpedienteClaseFolio(BaseModel):
    codigo: str
    etiqueta: str
    fuente: str
    grupo: str
    condicional: bool


class ExpedienteCatalogo(BaseModel):
    tipos: list[ExpedienteEtiqueta]
    modalidades: list[ExpedienteEtiqueta]
    roles: list[ExpedienteEtiqueta]
    estados: list[ExpedienteEtiqueta]
    clases_evento: list[ExpedienteEtiqueta]
    clases_folio: list[ExpedienteClaseFolio]
    aviso_modalidad: str
    aviso_lapsos: str


class ExpedienteOpcionFuncionario(BaseModel):
    id: str
    nombre: str
    cargos: list[str]
    unidades: list[str]


class ExpedienteOpcionUnidad(BaseModel):
    id: str
    nombre: str


class ExpedienteOpcionComision(BaseModel):
    id: str
    codigo: str
    nombre: str


class ExpedienteOpcionActo(BaseModel):
    id: str
    etiqueta: str


class ExpedienteOpciones(BaseModel):
    funcionarios: list[ExpedienteOpcionFuncionario]
    unidades: list[ExpedienteOpcionUnidad]
    comisiones: list[ExpedienteOpcionComision]
    actos: list[ExpedienteOpcionActo]


class ExpedienteHitoProximo(BaseModel):
    nombre: str
    fecha_prevista: date
    fecha_superada: bool


class ExpedienteResumen(BaseModel):
    id: str
    numero: str
    objeto: str
    fecha_inicio: date
    tipo_contratacion: str
    tipo_etiqueta: str
    modalidad_declarada: str | None
    modalidad_etiqueta: str | None
    unidad_id: str
    unidad_nombre: str
    responsable: str | None
    comision: str | None
    status: str
    status_etiqueta: str
    proximo_hito: ExpedienteHitoProximo | None
    version: int


class ExpedientesListado(BaseModel):
    items: list[ExpedienteResumen]
    total: int
    pagina: int
    por_pagina: int


class ExpedienteResponsable(BaseModel):
    id: str
    funcionario_id: str
    rol: str
    rol_etiqueta: str
    nombre: str
    cargo: str | None
    unidad: str | None
    desde: date
    fin_efectivo: date | None
    motivo_fin: str | None
    vigente: bool


class ExpedienteHito(BaseModel):
    id: str
    nombre: str
    fuente: str | None
    fecha_prevista: date
    fecha_real: date | None
    estado: str
    estado_etiqueta: str
    fecha_superada: bool
    funcionario_id: str | None
    responsable: str | None
    motivo_no_aplica: str | None


class ExpedienteFolio(BaseModel):
    id: str
    numero: int
    clase: str
    clase_etiqueta: str
    tipo_etiqueta: str
    etiqueta: str
    documento_id: str | None
    acto_id: str | None
    version_numero: int | None
    fecha_documento: date | None
    fecha_incorporacion: date
    incorporado_por: str | None
    reservado: bool
    motivo_reserva: str | None
    hito: str | None


class ExpedienteContenido(BaseModel):
    clase: str
    etiqueta: str
    fuente: str
    grupo: str
    condicional: bool
    folios: int


class ExpedientePendiente(BaseModel):
    codigo: str
    texto: str


class ExpedienteComision(BaseModel):
    id: str
    codigo: str
    nombre: str
    situacion: str
    situacion_etiqueta: str


class ExpedienteUltima(BaseModel):
    fecha: date
    titulo: str
    clase_etiqueta: str


class ExpedienteTotales(BaseModel):
    actuaciones: int
    decisiones: int
    folios: int
    hitos: int



class ExpedienteDetalle(ExpedienteResumen):
    ofertas_total: int = 0
    ofertas_selladas: int = 0
    recepcion_concluida_en: datetime | None = None

    partes: str | None
    modalidad_fundamento: str | None
    modalidad_fuente: str | None
    comision_no_aplica_motivo: str | None
    cierre_motivo: str | None
    cierre_fecha: date | None
    comision_detalle: ExpedienteComision | None
    responsables: list[ExpedienteResponsable]
    hitos: list[ExpedienteHito]
    folios: list[ExpedienteFolio]
    contenido: list[ExpedienteContenido]
    pendientes: list[ExpedientePendiente]
    siguiente_accion: str | None
    ultima_actuacion: ExpedienteUltima | None
    totales: ExpedienteTotales
    creado_por: str | None
    creado_en: datetime


class ExpedienteEvento(BaseModel):
    id: str
    secuencia: int
    fecha: date
    clase: str
    clase_etiqueta: str
    titulo: str
    detalle: str | None
    resultado: str | None
    responsable: str | None
    acto_id: str | None
    acto_etiqueta: str | None
    folio_id: str | None
    folio_etiqueta: str | None
    hito_etiqueta: str | None
    estado_expediente: str
    estado_etiqueta: str
    actor: str | None
    registrado_en: datetime
    motivo: str | None
    rectifica_secuencia: int | None
    rectificada_por_secuencia: int | None


class ExpedienteCronologia(BaseModel):
    items: list[ExpedienteEvento]
    total: int
    pagina: int
    por_pagina: int
