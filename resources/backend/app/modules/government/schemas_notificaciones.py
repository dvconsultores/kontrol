"""Esquemas Pydantic de notificaciones administrativas (DOC-04)."""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from app.modules.government.schemas_actos import _texto
from app.modules.government.schemas_estructura import _fecha_sin_hora, _uuid
from app.shared.clock import hoy_de_negocio

TipoPersona = Literal["NATURAL", "JURIDICA"]
MedioIntento = Literal["PERSONAL", "PRENSA"]
ResultadoIntento = Literal["ENTREGADA", "FALLIDA", "PUBLICADA"]
EstadoNotificacion = Literal["PENDIENTE", "NOTIFICADA", "ANULADA"]


def clave_identificacion(valor: str) -> str:
    """Normaliza una identificación: mayúsculas, sin espacios, puntos ni guiones."""
    return valor.upper().replace(" ", "").replace(".", "").replace("-", "")


def validar_identificacion(tipo: TipoPersona, valor: str) -> str:
    """Valida una identificación según el tipo de persona y devuelve la forma de presentación, p. ej. V-12345678.

    Lanza ValueError con mensaje en español si el formato no corresponde.
    """
    v = clave_identificacion(valor)
    if tipo == "NATURAL":
        if not re.match(r"^[VE]\d{5,9}$", v):
            raise ValueError("Escriba la cédula con su letra, p. ej. V-12345678")
        return f"{v[0]}-{v[1:]}"
    else:
        if not re.match(r"^[JGVEP]\d{8}\d$", v):
            raise ValueError("Escriba el RIF con su letra y su dígito, p. ej. J-12345678-9")
        return f"{v[0]}-{v[1:9]}-{v[9]}"


def _identificacion_texto(v: str | None) -> str | None:
    if v is None:
        return None
    resultado = _texto(v, 5, 20)
    if resultado is None:
        return None
    return resultado


class ActoDeNotificacion(BaseModel):
    """Referencia corta al acto notificado."""

    id: str
    tipo: str
    denominacion_tipo: str | None
    numero: str
    fecha: date
    estado: str


class NotificacionIn(BaseModel):
    """Entrada para el alta de una notificación."""

    model_config = ConfigDict(extra="forbid")

    acto_id: str
    tipo_persona: TipoPersona
    nombre: str
    identificacion: str
    domicilio: str
    apoderado_nombre: str | None = Field(default=None, validate_default=True)
    apoderado_identificacion: str | None = Field(default=None, validate_default=True)
    recursos: str

    @field_validator("acto_id", mode="after")
    @classmethod
    def _valida_acto_id(cls, v: str) -> str:
        resultado = _uuid(v)
        if resultado is None:
            raise ValueError("Campo obligatorio")
        return resultado

    @field_validator("nombre", mode="after")
    @classmethod
    def _valida_nombre(cls, v: str) -> str:
        resultado = _texto(v, 3, 200, obligatorio=True)
        if resultado is None:
            raise ValueError("Campo obligatorio")
        return resultado

    @field_validator("identificacion", mode="after")
    @classmethod
    def _valida_identificacion(cls, v: str, info: ValidationInfo) -> str:
        resultado = _identificacion_texto(v)
        if resultado is None:
            raise ValueError("Campo obligatorio")
        tipo = info.data.get("tipo_persona")
        if tipo is None:
            return _texto(v, 1, 20, obligatorio=True) or ""
        return validar_identificacion(tipo, resultado)

    @field_validator("domicilio", mode="after")
    @classmethod
    def _valida_domicilio(cls, v: str) -> str:
        resultado = _texto(v, 5, 500, obligatorio=True)
        if resultado is None:
            raise ValueError("Campo obligatorio")
        return resultado

    @field_validator("recursos", mode="after")
    @classmethod
    def _valida_recursos(cls, v: str) -> str:
        resultado = _texto(v, 5, 2000, obligatorio=True)
        if resultado is None:
            raise ValueError("Campo obligatorio")
        return resultado

    @field_validator("apoderado_nombre", mode="after")
    @classmethod
    def _valida_apoderado_nombre(cls, v: str | None) -> str | None:
        return _texto(v, 3, 200)

    @field_validator("apoderado_identificacion", mode="after")
    @classmethod
    def _valida_apoderado_identificacion(
        cls, v: str | None, info: ValidationInfo
    ) -> str | None:
        resultado = _identificacion_texto(v)
        nombre = info.data.get("apoderado_nombre")

        if nombre is not None and resultado is None:
            raise ValueError("Indique la cédula del apoderado")

        if nombre is None:
            if resultado is not None:
                raise ValueError("Indique el nombre del apoderado")
            return None

        if resultado is None:
            raise ValueError("Indique la cédula del apoderado")
        return validar_identificacion("NATURAL", resultado)


class NotificacionCambio(BaseModel):
    """Entrada para el PATCH de una notificación pendiente."""

    model_config = ConfigDict(extra="forbid")

    tipo_persona: TipoPersona | None = None
    nombre: str | None = None
    identificacion: str | None = None
    domicilio: str | None = None
    apoderado_nombre: str | None = Field(default=None, validate_default=True)
    apoderado_identificacion: str | None = Field(default=None, validate_default=True)
    recursos: str | None = None

    @field_validator("nombre", mode="after")
    @classmethod
    def _valida_nombre(cls, v: str | None) -> str | None:
        return _texto(v, 3, 200)

    @field_validator("identificacion", mode="after")
    @classmethod
    def _valida_identificacion(cls, v: str | None, info: ValidationInfo) -> str | None:
        resultado = _identificacion_texto(v)
        if resultado is None:
            return None

        tipo = info.data.get("tipo_persona")
        if tipo is None:
            return resultado
        return validar_identificacion(tipo, resultado)

    @field_validator("domicilio", mode="after")
    @classmethod
    def _valida_domicilio(cls, v: str | None) -> str | None:
        return _texto(v, 5, 500)

    @field_validator("apoderado_nombre", mode="after")
    @classmethod
    def _valida_apoderado_nombre(cls, v: str | None) -> str | None:
        return _texto(v, 3, 200)

    @field_validator("apoderado_identificacion", mode="after")
    @classmethod
    def _valida_apoderado_identificacion(
        cls, v: str | None, info: ValidationInfo
    ) -> str | None:
        resultado = _identificacion_texto(v)
        nombre = info.data.get("apoderado_nombre")

        if nombre is not None and resultado is None:
            raise ValueError("Indique la cédula del apoderado")

        if nombre is None:
            if resultado is not None:
                raise ValueError("Indique el nombre del apoderado")
            return None

        if resultado is None:
            raise ValueError("Indique la cédula del apoderado")
        return validar_identificacion("NATURAL", resultado)

    @field_validator("recursos", mode="after")
    @classmethod
    def _valida_recursos(cls, v: str | None) -> str | None:
        return _texto(v, 5, 2000)


class AnulacionIn(BaseModel):
    """Entrada para anular una notificación."""

    model_config = ConfigDict(extra="forbid")

    motivo: str

    @field_validator("motivo", mode="after")
    @classmethod
    def _valida_motivo(cls, v: str) -> str:
        resultado = _texto(v, 5, 255, obligatorio=True)
        if resultado is None:
            raise ValueError("Campo obligatorio")
        return resultado


class IntentoIn(BaseModel):
    """Entrada para registrar un intento de notificación."""

    model_config = ConfigDict(extra="forbid")

    medio: MedioIntento
    resultado: ResultadoIntento
    fecha: date
    documento_oficio_id: str
    documento_id: str
    receptor_nombre: str | None = Field(default=None, validate_default=True)
    receptor_identificacion: str | None = Field(default=None, validate_default=True)
    motivo_fallo: str | None = Field(default=None, validate_default=True)
    diario: str | None = Field(default=None, validate_default=True)
    referencia: str | None = Field(default=None, validate_default=True)

    @field_validator("fecha", mode="before")
    @classmethod
    def _fecha_before(cls, v: Any) -> Any:
        return _fecha_sin_hora(v)

    @field_validator("fecha", mode="after")
    @classmethod
    def _valida_fecha(cls, v: date) -> date:
        if v > hoy_de_negocio():
            raise ValueError("No puede ser futura")
        return v

    @field_validator("documento_oficio_id", mode="after")
    @classmethod
    def _valida_documento_oficio_id(cls, v: str) -> str:
        resultado = _uuid(v)
        if resultado is None:
            raise ValueError("Campo obligatorio")
        return resultado

    @field_validator("documento_id", mode="after")
    @classmethod
    def _valida_documento_id(cls, v: str, info: ValidationInfo) -> str:
        resultado = _uuid(v)
        if resultado is None:
            raise ValueError("Campo obligatorio")
        oficio_id = info.data.get("documento_oficio_id")
        if isinstance(oficio_id, str) and resultado == oficio_id:
            raise ValueError("La constancia debe ser un documento distinto del oficio")
        return resultado

    @field_validator("resultado", mode="after")
    @classmethod
    def _valida_resultado(cls, v: ResultadoIntento, info: ValidationInfo) -> ResultadoIntento:
        medio = info.data.get("medio")
        if medio == "PERSONAL":
            if v not in ("ENTREGADA", "FALLIDA"):
                raise ValueError("El resultado no corresponde al canal")
        elif medio == "PRENSA":
            if v != "PUBLICADA":
                raise ValueError("El resultado no corresponde al canal")
        return v

    @field_validator("receptor_nombre", mode="after")
    @classmethod
    def _valida_receptor_nombre(cls, v: str | None, info: ValidationInfo) -> str | None:
        resultado = _texto(v, 3, 200)
        if info.data.get("resultado") == "ENTREGADA":
            if resultado is None:
                raise ValueError("Campo obligatorio")
        elif resultado is not None:
            if info.data.get("resultado") in ("FALLIDA", "PUBLICADA"):
                raise ValueError("No corresponde a este resultado")
        return resultado

    @field_validator("receptor_identificacion", mode="after")
    @classmethod
    def _valida_receptor_identificacion(
        cls, v: str | None, info: ValidationInfo
    ) -> str | None:
        resultado = _identificacion_texto(v)
        if info.data.get("resultado") == "ENTREGADA":
            if resultado is None:
                raise ValueError("Campo obligatorio")
            return validar_identificacion("NATURAL", resultado)
        if resultado is not None:
            if info.data.get("resultado") in ("FALLIDA", "PUBLICADA"):
                raise ValueError("No corresponde a este resultado")
        return resultado

    @field_validator("motivo_fallo", mode="after")
    @classmethod
    def _valida_motivo_fallo(cls, v: str | None, info: ValidationInfo) -> str | None:
        resultado = _texto(v, 5, 500)
        if info.data.get("resultado") == "FALLIDA":
            if resultado is None:
                raise ValueError("Campo obligatorio")
        elif resultado is not None:
            raise ValueError("No corresponde a este resultado")
        return resultado

    @field_validator("diario", mode="after")
    @classmethod
    def _valida_diario(cls, v: str | None, info: ValidationInfo) -> str | None:
        resultado = _texto(v, 3, 120)
        if info.data.get("resultado") == "PUBLICADA":
            if resultado is None:
                raise ValueError("Campo obligatorio")
        elif resultado is not None:
            raise ValueError("No corresponde a este resultado")
        return resultado

    @field_validator("referencia", mode="after")
    @classmethod
    def _valida_referencia(cls, v: str | None, info: ValidationInfo) -> str | None:
        resultado = _texto(v, 3, 120)
        if info.data.get("resultado") == "PUBLICADA":
            if resultado is None:
                raise ValueError("Campo obligatorio")
        elif resultado is not None:
            raise ValueError("No corresponde a este resultado")
        return resultado


class IntentoOut(BaseModel):
    """Salida de un intento de notificación."""

    numero: int
    medio: str
    resultado: str
    fecha: date
    receptor_nombre: str | None
    receptor_identificacion: str | None
    motivo_fallo: str | None
    diario: str | None
    referencia: str | None
    documento_id: str
    registrado_por: str | None
    creado_en: datetime


class NotificacionAdministrativaOut(BaseModel):
    """Representación completa de una notificación para la API."""

    id: str
    acto: ActoDeNotificacion
    tipo_persona: str
    nombre: str
    identificacion: str
    domicilio: str
    apoderado_nombre: str | None
    apoderado_identificacion: str | None
    recursos: str
    documento_oficio_id: str | None
    estado: str
    fecha_notificacion: date | None
    medio_notificacion: str | None
    motivo_anulacion: str | None
    intentos: list[IntentoOut]
    puede_publicar_en_prensa: bool
    version: int
    creado_en: datetime


class NotificacionResumen(BaseModel):
    """Resumen de una notificación para listados."""

    id: str
    acto: ActoDeNotificacion
    tipo_persona: str
    nombre: str
    identificacion: str
    estado: str
    intentos: int
    fecha_notificacion: date | None
    medio_notificacion: str | None


class ListaNotificaciones(BaseModel):
    """Listado de notificaciones."""

    anio: int
    items: list[NotificacionResumen]
    total: int


class VersionNotificacionOut(BaseModel):
    """Una versión histórica de una notificación."""

    version: int
    estado: str
    motivo: str | None
    actor: str | None
    creado_en: datetime
    instantanea: dict[str, Any]


class VersionesNotificacion(BaseModel):
    """Listado de versiones históricas de una notificación."""

    items: list[VersionNotificacionOut]
    total: int
