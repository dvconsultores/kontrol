"""Esquemas Pydantic de los actos administrativos (DOC-02)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from app.modules.government.schemas_cargos import AccionCompetencia, MateriaCompetencia
from app.modules.government.schemas_estructura import _fecha_sin_hora, _uuid
from app.shared.clock import hoy_de_negocio

TipoActo = Literal[
    "DECRETO", "RESOLUCION", "ORDEN", "PROVIDENCIA", "INSTRUCCION", "CIRCULAR", "OTRA_DECISION"
]
Titularidad = Literal["TITULAR", "DELEGACION", "ENCARGADURIA", "SUPLENCIA"]
CaracterActo = Literal["GENERAL", "PARTICULAR", "INTERNO"]
MedioEficacia = Literal["GACETA", "PERSONAL", "PRENSA"]
EstadoActo = Literal["BORRADOR", "EMITIDO", "EFICAZ", "REVOCADO", "NULO"]


def _texto(
    v: str | None,
    minimo: int,
    maximo: int,
    *,
    obligatorio: bool = False,
) -> str | None:
    """Normaliza y valida un texto: strip, vacío a None (u obligatorio) y rango."""
    if v is None:
        if obligatorio:
            raise ValueError("Campo obligatorio")
        return None

    v = v.strip()
    if not v:
        if obligatorio:
            raise ValueError("Campo obligatorio")
        return None

    if minimo > 0 and len(v) < minimo:
        raise ValueError(f"Debe tener entre {minimo} y {maximo} caracteres")
    if len(v) > maximo:
        if minimo == 0:
            raise ValueError(f"Admite como máximo {maximo} caracteres")
        raise ValueError(f"Debe tener entre {minimo} y {maximo} caracteres")
    return v


def validar_coherencia(datos: dict[str, Any]) -> tuple[str, str] | None:
    """Devuelve (campo, mensaje) del primer incumplimiento de coherencia, o None."""
    tipo = datos.get("tipo")
    denominacion_tipo = datos.get("denominacion_tipo")
    titularidad = datos.get("titularidad")
    delegacion_numero = datos.get("delegacion_numero")
    delegacion_fecha = datos.get("delegacion_fecha")
    fecha = datos.get("fecha")
    simple_tramite = datos.get("simple_tramite", False)
    caracter = datos.get("caracter")

    if tipo == "OTRA_DECISION":
        if not denominacion_tipo:
            return "denominacion_tipo", "Indique la denominación del tipo de acto"
    elif denominacion_tipo:
        return "denominacion_tipo", "La denominación solo procede con OTRA_DECISION"

    if titularidad == "DELEGACION":
        if not delegacion_numero:
            return "delegacion_numero", "Indique el número del acto de delegación"
        if not delegacion_fecha:
            return "delegacion_fecha", "Indique la fecha del acto de delegación"
    else:
        if delegacion_numero:
            return "delegacion_numero", "Los datos de delegación solo proceden con titularidad DELEGACION"
        if delegacion_fecha:
            return "delegacion_fecha", "Los datos de delegación solo proceden con titularidad DELEGACION"

    if delegacion_fecha is not None and fecha is not None and delegacion_fecha > fecha:
        return "delegacion_fecha", "La fecha de delegación no puede ser posterior a la fecha del acto"

    if simple_tramite and caracter != "PARTICULAR":
        return "simple_tramite", "El trámite simple solo procede con carácter PARTICULAR"

    return None


class CompetenciaRef(BaseModel):
    """Referencia a la competencia ejercida por el acto."""

    model_config = ConfigDict(extra="forbid")

    accion: AccionCompetencia
    materia: MateriaCompetencia


class ActoIn(BaseModel):
    """Entrada para el alta de un acto administrativo."""

    model_config = ConfigDict(extra="forbid")

    tipo: TipoActo
    denominacion_tipo: str | None = Field(default=None, validate_default=True)
    numero: str
    fecha: date
    lugar: str
    cargo_id: str
    competencia: CompetenciaRef
    fundamento_competencia: str
    funcionario: str
    titularidad: Titularidad
    delegacion_numero: str | None = Field(default=None, validate_default=True)
    delegacion_fecha: date | None = Field(default=None, validate_default=True)
    caracter: CaracterActo
    simple_tramite: bool = Field(default=False, validate_default=True)
    destinatario: str | None = None
    asunto: str
    hechos: str | None = None
    fundamentos: str | None = None
    decision: str | None = None

    @field_validator("denominacion_tipo", mode="after")
    @classmethod
    def _valida_denominacion_tipo(cls, v: str | None, info: ValidationInfo) -> str | None:
        resultado = _texto(v, 3, 80)
        tipo = info.data.get("tipo")
        if tipo == "OTRA_DECISION":
            if resultado is None:
                raise ValueError("Campo obligatorio")
        elif resultado is not None:
            raise ValueError("La denominación solo procede con OTRA_DECISION")
        return resultado

    @field_validator("numero", mode="after")
    @classmethod
    def _valida_numero(cls, v: str) -> str:
        resultado = _texto(v, 1, 60, obligatorio=True)
        if resultado is None:
            raise ValueError("Campo obligatorio")
        return resultado

    @field_validator("fecha", mode="before")
    @classmethod
    def _fecha_acto_before(cls, v: Any) -> Any:
        return _fecha_sin_hora(v)

    @field_validator("fecha", mode="after")
    @classmethod
    def _fecha_acto_after(cls, v: date) -> date:
        if v > hoy_de_negocio():
            raise ValueError("La fecha del acto no puede ser futura")
        return v

    @field_validator("lugar", mode="after")
    @classmethod
    def _valida_lugar(cls, v: str) -> str:
        resultado = _texto(v, 2, 120, obligatorio=True)
        if resultado is None:
            raise ValueError("Campo obligatorio")
        return resultado

    @field_validator("cargo_id", mode="after")
    @classmethod
    def _valida_cargo_id(cls, v: str) -> str:
        resultado = _uuid(v)
        if resultado is None:
            raise ValueError("Campo obligatorio")
        return resultado

    @field_validator("fundamento_competencia", mode="after")
    @classmethod
    def _valida_fundamento_competencia(cls, v: str) -> str:
        resultado = _texto(v, 5, 500, obligatorio=True)
        if resultado is None:
            raise ValueError("Campo obligatorio")
        return resultado

    @field_validator("funcionario", mode="after")
    @classmethod
    def _valida_funcionario(cls, v: str) -> str:
        resultado = _texto(v, 3, 200, obligatorio=True)
        if resultado is None:
            raise ValueError("Campo obligatorio")
        return resultado

    @field_validator("delegacion_numero", mode="after")
    @classmethod
    def _valida_delegacion_numero(cls, v: str | None, info: ValidationInfo) -> str | None:
        resultado = _texto(v, 1, 60)
        titularidad = info.data.get("titularidad")
        if titularidad == "DELEGACION":
            if resultado is None:
                raise ValueError("Campo obligatorio")
        elif resultado is not None:
            raise ValueError("Los datos de delegación solo proceden con titularidad DELEGACION")
        return resultado

    @field_validator("delegacion_fecha", mode="before")
    @classmethod
    def _delegacion_fecha_before(cls, v: Any) -> Any:
        return _fecha_sin_hora(v)

    @field_validator("delegacion_fecha", mode="after")
    @classmethod
    def _valida_delegacion_fecha(cls, v: date | None, info: ValidationInfo) -> date | None:
        titularidad = info.data.get("titularidad")
        if titularidad == "DELEGACION" and v is None:
            raise ValueError("Campo obligatorio")
        if titularidad not in (None, "DELEGACION") and v is not None:
            raise ValueError("Los datos de delegación solo proceden con titularidad DELEGACION")

        fecha = info.data.get("fecha")
        if v is not None and isinstance(fecha, date) and v > fecha:
            raise ValueError("La fecha de delegación no puede ser posterior a la fecha del acto")
        return v

    @field_validator("destinatario", mode="after")
    @classmethod
    def _valida_destinatario(cls, v: str | None) -> str | None:
        return _texto(v, 3, 200)

    @field_validator("asunto", mode="after")
    @classmethod
    def _valida_asunto(cls, v: str) -> str:
        resultado = _texto(v, 3, 200, obligatorio=True)
        if resultado is None:
            raise ValueError("Campo obligatorio")
        return resultado

    @field_validator("hechos", mode="after")
    @classmethod
    def _valida_hechos(cls, v: str | None) -> str | None:
        return _texto(v, 0, 8000)

    @field_validator("fundamentos", mode="after")
    @classmethod
    def _valida_fundamentos(cls, v: str | None) -> str | None:
        return _texto(v, 0, 4000)

    @field_validator("decision", mode="after")
    @classmethod
    def _valida_decision(cls, v: str | None) -> str | None:
        return _texto(v, 3, 8000)

    @field_validator("simple_tramite", mode="after")
    @classmethod
    def _valida_simple_tramite(cls, v: bool, info: ValidationInfo) -> bool:
        caracter = info.data.get("caracter")
        if v and caracter not in (None, "PARTICULAR"):
            raise ValueError("El trámite simple solo procede con carácter PARTICULAR")
        return v


class ActoCambio(BaseModel):
    """Entrada para el PATCH de un acto en borrador."""

    model_config = ConfigDict(extra="forbid")

    tipo: TipoActo | None = None
    denominacion_tipo: str | None = None
    numero: str | None = None
    fecha: date | None = None
    lugar: str | None = None
    cargo_id: str | None = None
    competencia: CompetenciaRef | None = None
    fundamento_competencia: str | None = None
    funcionario: str | None = None
    titularidad: Titularidad | None = None
    delegacion_numero: str | None = None
    delegacion_fecha: date | None = None
    caracter: CaracterActo | None = None
    simple_tramite: bool | None = None
    destinatario: str | None = None
    asunto: str | None = None
    hechos: str | None = None
    fundamentos: str | None = None
    decision: str | None = None

    @field_validator("denominacion_tipo", mode="after")
    @classmethod
    def _valida_denominacion_tipo(cls, v: str | None) -> str | None:
        return _texto(v, 3, 80)

    @field_validator("numero", mode="after")
    @classmethod
    def _valida_numero(cls, v: str | None) -> str | None:
        return _texto(v, 1, 60)

    @field_validator("fecha", mode="before")
    @classmethod
    def _fecha_before(cls, v: Any) -> Any:
        return _fecha_sin_hora(v)

    @field_validator("fecha", mode="after")
    @classmethod
    def _valida_fecha(cls, v: date | None) -> date | None:
        if v is not None and v > hoy_de_negocio():
            raise ValueError("La fecha del acto no puede ser futura")
        return v

    @field_validator("lugar", mode="after")
    @classmethod
    def _valida_lugar(cls, v: str | None) -> str | None:
        return _texto(v, 2, 120)

    @field_validator("cargo_id", mode="after")
    @classmethod
    def _valida_cargo_id(cls, v: str | None) -> str | None:
        return _uuid(v)

    @field_validator("fundamento_competencia", mode="after")
    @classmethod
    def _valida_fundamento_competencia(cls, v: str | None) -> str | None:
        return _texto(v, 5, 500)

    @field_validator("funcionario", mode="after")
    @classmethod
    def _valida_funcionario(cls, v: str | None) -> str | None:
        return _texto(v, 3, 200)

    @field_validator("delegacion_numero", mode="after")
    @classmethod
    def _valida_delegacion_numero(cls, v: str | None) -> str | None:
        return _texto(v, 1, 60)

    @field_validator("delegacion_fecha", mode="before")
    @classmethod
    def _delegacion_fecha_before(cls, v: Any) -> Any:
        return _fecha_sin_hora(v)

    @field_validator("destinatario", mode="after")
    @classmethod
    def _valida_destinatario(cls, v: str | None) -> str | None:
        return _texto(v, 3, 200)

    @field_validator("asunto", mode="after")
    @classmethod
    def _valida_asunto(cls, v: str | None) -> str | None:
        return _texto(v, 3, 200)

    @field_validator("hechos", mode="after")
    @classmethod
    def _valida_hechos(cls, v: str | None) -> str | None:
        return _texto(v, 0, 8000)

    @field_validator("fundamentos", mode="after")
    @classmethod
    def _valida_fundamentos(cls, v: str | None) -> str | None:
        return _texto(v, 0, 4000)

    @field_validator("decision", mode="after")
    @classmethod
    def _valida_decision(cls, v: str | None) -> str | None:
        return _texto(v, 3, 8000)


class EmisionIn(BaseModel):
    """Entrada para emitir un acto."""

    model_config = ConfigDict(extra="forbid")

    documento_acto_id: str
    fecha_eficacia: date | None = None

    @field_validator("documento_acto_id", mode="after")
    @classmethod
    def _valida_documento_acto_id(cls, v: str) -> str:
        resultado = _uuid(v)
        if resultado is None:
            raise ValueError("Campo obligatorio")
        return resultado

    @field_validator("fecha_eficacia", mode="before")
    @classmethod
    def _fecha_eficacia_before(cls, v: Any) -> Any:
        return _fecha_sin_hora(v)


class EficaciaIn(BaseModel):
    """Entrada para registrar la eficacia de un acto."""

    model_config = ConfigDict(extra="forbid")

    medio: MedioEficacia
    referencia: str | None = None
    fecha: date
    documento_eficacia_id: str
    fecha_eficacia: date | None = None

    @field_validator("referencia", mode="after")
    @classmethod
    def _valida_referencia(cls, v: str | None) -> str | None:
        return _texto(v, 3, 120)

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

    @field_validator("documento_eficacia_id", mode="after")
    @classmethod
    def _valida_documento_eficacia_id(cls, v: str) -> str:
        resultado = _uuid(v)
        if resultado is None:
            raise ValueError("Campo obligatorio")
        return resultado

    @field_validator("fecha_eficacia", mode="before")
    @classmethod
    def _fecha_eficacia_before(cls, v: Any) -> Any:
        return _fecha_sin_hora(v)


class CorreccionIn(BaseModel):
    """Entrada para corregir un acto."""

    model_config = ConfigDict(extra="forbid")

    lugar: str | None = None
    asunto: str | None = None
    destinatario: str | None = None
    funcionario: str | None = None
    hechos: str | None = None
    fundamentos: str | None = None
    decision: str | None = None
    fundamento_competencia: str | None = None
    motivo: str

    @field_validator("lugar", mode="after")
    @classmethod
    def _valida_lugar(cls, v: str | None) -> str | None:
        return _texto(v, 2, 120)

    @field_validator("asunto", mode="after")
    @classmethod
    def _valida_asunto(cls, v: str | None) -> str | None:
        return _texto(v, 3, 200)

    @field_validator("destinatario", mode="after")
    @classmethod
    def _valida_destinatario(cls, v: str | None) -> str | None:
        return _texto(v, 3, 200)

    @field_validator("funcionario", mode="after")
    @classmethod
    def _valida_funcionario(cls, v: str | None) -> str | None:
        return _texto(v, 3, 200)

    @field_validator("hechos", mode="after")
    @classmethod
    def _valida_hechos(cls, v: str | None) -> str | None:
        return _texto(v, 0, 8000)

    @field_validator("fundamentos", mode="after")
    @classmethod
    def _valida_fundamentos(cls, v: str | None) -> str | None:
        return _texto(v, 0, 4000)

    @field_validator("decision", mode="after")
    @classmethod
    def _valida_decision(cls, v: str | None) -> str | None:
        return _texto(v, 3, 8000)

    @field_validator("fundamento_competencia", mode="after")
    @classmethod
    def _valida_fundamento_competencia(cls, v: str | None) -> str | None:
        return _texto(v, 5, 500)

    @field_validator("motivo", mode="after")
    @classmethod
    def _valida_motivo(cls, v: str) -> str:
        resultado = _texto(v, 5, 255, obligatorio=True)
        if resultado is None:
            raise ValueError("Campo obligatorio")
        return resultado


class ReferenciaIn(BaseModel):
    """Entrada para referenciar otro acto."""

    model_config = ConfigDict(extra="forbid")

    acto_id_referencia: str
    motivo: str

    @field_validator("acto_id_referencia", mode="after")
    @classmethod
    def _valida_acto_id_referencia(cls, v: str) -> str:
        resultado = _uuid(v)
        if resultado is None:
            raise ValueError("Campo obligatorio")
        return resultado

    @field_validator("motivo", mode="after")
    @classmethod
    def _valida_motivo(cls, v: str) -> str:
        resultado = _texto(v, 5, 255, obligatorio=True)
        if resultado is None:
            raise ValueError("Campo obligatorio")
        return resultado


class CargoDeActo(BaseModel):
    """Cargo emisor resumido para la salida de un acto."""

    id: str
    codigo: str
    denominacion: str
    unidad_codigo: str
    unidad_denominacion: str


class CompetenciaDeActo(BaseModel):
    """Competencia resumida para la salida."""

    accion: str
    materia: str


class ActoReferido(BaseModel):
    """Referencia corta a un acto relacionado."""

    id: str
    tipo: str
    numero: str
    fecha: date


class ActoReferidoCorto(BaseModel):
    """Referencia mínima a un acto relacionado."""

    id: str
    tipo: str
    numero: str


class ActoOut(BaseModel):
    """Representación completa de un acto administrativo para la API."""

    id: str
    tipo: str
    denominacion_tipo: str | None
    numero: str
    fecha: date
    lugar: str
    cargo: CargoDeActo
    competencia: CompetenciaDeActo
    fundamento_competencia: str
    funcionario: str
    titularidad: str
    delegacion_numero: str | None
    delegacion_fecha: date | None
    caracter: str
    simple_tramite: bool
    destinatario: str | None
    asunto: str
    hechos: str | None
    fundamentos: str | None
    decision: str | None
    estado: str
    faltantes_para_emitir: list[str]
    documento_acto_id: str | None
    medio: str | None
    referencia_publicacion: str | None
    fecha_publicacion_notificacion: date | None
    documento_eficacia_id: str | None
    fecha_eficacia: date | None
    revocado_por: ActoReferido | None
    anulado_por: ActoReferido | None
    revoca_a: list[ActoReferidoCorto]
    anula_a: list[ActoReferidoCorto]
    version: int
    emitido_en: datetime | None
    emitido_por: str | None
    creado_en: datetime


class ActoResumen(BaseModel):
    """Resumen de un acto para listados."""

    id: str
    tipo: str
    denominacion_tipo: str | None
    numero: str
    fecha: date
    cargo_codigo: str
    cargo_denominacion: str
    unidad_codigo: str
    caracter: str
    asunto: str
    estado: str
    fecha_eficacia: date | None


class ListaActos(BaseModel):
    """Listado anual de actos."""

    anio: int
    items: list[ActoResumen]
    total: int


class AutoridadOut(BaseModel):
    """Autoridad competente para emitir actos."""

    cargo_id: str
    codigo: str
    denominacion: str
    unidad_codigo: str
    unidad_denominacion: str
    estado: str
    competencias: list[CompetenciaDeActo]


class ListaAutoridades(BaseModel):
    """Listado de autoridades a una fecha."""

    fecha: date
    items: list[AutoridadOut]


class VersionActoOut(BaseModel):
    """Una versión histórica de un acto."""

    version: int
    estado: str
    motivo: str | None
    actor: str | None
    creado_en: datetime
    instantanea: dict[str, Any]


class VersionesActo(BaseModel):
    """Listado de versiones históricas de un acto."""

    items: list[VersionActoOut]
    total: int
