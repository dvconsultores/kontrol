"""Esquemas Pydantic v2 del paquete de auditoría exportable (DOC-08 · GOV-DOC-010).

Define los contratos de entrada y salida para la generación, consulta y verificación
de paquetes de auditoría exportables.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

EstadoDocumento = Literal["INCLUIDO", "EXCLUIDO"]
MotivoExclusion = Literal["SIN_PERMISO", "NO_DISPONIBLE"]
ResultadoVerificacion = Literal["VALIDO", "INVALIDO", "INCOMPLETO", "VERSION_NO_SOPORTADA"]
TipoReferencia = Literal["evento", "objeto", "accion_correctiva", "avance"]


class PaqueteIn(BaseModel):
    """Cuerpo de entrada para solicitar la generación de un paquete de auditoría."""

    model_config = ConfigDict(extra="forbid")

    proposito: str

    @field_validator("proposito", mode="before")
    @classmethod
    def _validar_proposito(cls, valor: object) -> str:
        """Normaliza y valida el propósito del paquete."""
        if not isinstance(valor, str):
            raise ValueError("El propósito es obligatorio")
        recortado = valor.strip()
        if not (10 <= len(recortado) <= 1000):
            raise ValueError("El propósito debe tener entre 10 y 1000 caracteres")
        return recortado


class LimitesPaquete(BaseModel):
    """Límites aplicables a la generación de un paquete."""

    eventos: int
    documentos: int
    bytes: int


class MuestraDelPaquete(BaseModel):
    """Muestra asociada al paquete de auditoría."""

    id: str
    codigo: str
    titulo: str
    metodo: str
    semilla: int | None
    poblacion: int
    tamano: int
    creada_en: datetime
    creada_por: str | None


class Referencia(BaseModel):
    """Referencia a una entidad relacionada con un documento del paquete."""

    tipo: TipoReferencia
    id: str


class DocumentoDelPaquete(BaseModel):
    """Documento incluido o excluido del paquete, con su estado y metadatos."""

    id: str
    estado: EstadoDocumento
    motivo: MotivoExclusion | None = None
    version: int | None = None
    bytes: int | None = None
    sha256: str | None = None
    referencias: list[Referencia]


class VistaPrevia(BaseModel):
    """Vista previa del contenido y tamaño estimado de un paquete antes de generarlo."""

    muestra: MuestraDelPaquete
    eventos: int
    documentos_incluidos: int
    documentos_excluidos: int
    hallazgos: int
    bytes_estimados: int
    documentos: list[DocumentoDelPaquete]
    limites: LimitesPaquete
    excede_limite: bool
    motivo_limite: str | None = None
    paquetes_previos: int


class ObjetoReferido(BaseModel):
    """Objeto referido por un evento del paquete."""

    tipo: str
    id: str


class EventoDelPaquete(BaseModel):
    """Evento incluido en el contenido del paquete de auditoría."""

    orden: int
    id: str
    fecha: datetime
    proceso: str
    accion: str
    entidad: str
    entidad_id: str | None
    usuario: str | None
    objeto: ObjetoReferido | None = None
    documentos: list[str]


class HallazgoDelPaquete(BaseModel):
    """Hallazgo incluido en el contenido del paquete de auditoría."""

    id: str
    codigo: str
    titulo: str
    riesgo: str
    estado: str
    partidas: list[str]
    acciones: list[str]
    documentos: list[str]


class ContenidoPaquete(BaseModel):
    """Contenido completo de un paquete de auditoría."""

    eventos: list[EventoDelPaquete]
    documentos: list[DocumentoDelPaquete]
    hallazgos: list[HallazgoDelPaquete]


class MotivoVerificacion(BaseModel):
    """Motivo o incidencia detectada durante la verificación de un paquete."""

    codigo: str
    ruta: str | None = None


class VerificacionResumen(BaseModel):
    """Resumen de una verificación realizada sobre un paquete."""

    id: str
    resultado: ResultadoVerificacion
    motivos: list[MotivoVerificacion]
    huella_archivo: str
    bytes_archivo: int
    identico: bool
    verificado_por: str | None
    verificado_en: datetime


class PaqueteResumen(BaseModel):
    """Resumen de un paquete de auditoría generado."""

    id: str
    codigo: str
    muestra_id: str
    muestra_codigo: str
    numero_generacion: int
    titulo: str
    generado_por: str | None
    generado_en: datetime
    bytes: int
    huella_paquete: str
    eventos: int
    documentos_incluidos: int
    documentos_excluidos: int
    hallazgos: int


class PaqueteDetalle(PaqueteResumen):
    """Detalle completo de un paquete de auditoría, incluyendo contenido y verificaciones."""

    muestra_titulo: str
    proposito: str
    version_manifiesto: int
    huella_manifiesto: str
    archivos: int
    nombre_archivo: str
    contenido: ContenidoPaquete
    verificaciones: list[VerificacionResumen]


class PaquetesListado(BaseModel):
    """Listado paginado de paquetes de auditoría."""

    items: list[PaqueteResumen]
    total: int
    pagina: int
    por_pagina: int


class PaqueteReferido(BaseModel):
    """Referencia mínima a un paquete de auditoría."""

    id: str
    codigo: str


class ResultadoDeVerificacion(BaseModel):
    """Resultado de la verificación de un paquete de auditoría."""

    resultado: ResultadoVerificacion
    motivos: list[MotivoVerificacion]
    paquete: PaqueteReferido | None = None
    huella_archivo: str
    bytes_archivo: int
    identico: bool
    verificacion_id: str | None = None
