"""Esquemas Pydantic para el pago (TRE-04)."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class ConfiguracionPagoIn(BaseModel):
    patron: str = Field(min_length=3, max_length=60)


class MedioPagoCreate(BaseModel):
    codigo: str = Field(pattern=r"^[A-Z0-9][A-Z0-9_-]{1,19}$")
    nombre: str = Field(min_length=3, max_length=120)
    descripcion: str | None = Field(default=None, max_length=2000)
    vigente_desde: date
    vigente_hasta: date | None = None
    exige_referencia: bool = False
    referencia_unica: bool = False
    patron_referencia: str | None = Field(default=None, max_length=200)
    fundamento: str | None = Field(default=None, max_length=2000)


class MedioPagoUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=3, max_length=120)
    descripcion: str | None = Field(default=None, max_length=2000)
    vigente_desde: date | None = None
    vigente_hasta: date | None = None
    exige_referencia: bool | None = None
    referencia_unica: bool | None = None
    patron_referencia: str | None = Field(default=None, max_length=200)
    fundamento: str | None = Field(default=None, max_length=2000)
    estado: str | None = None


class RequisitoBandaPagoIn(BaseModel):
    accion: str
    materia: str
    cantidad: int = Field(ge=1, le=5)


class BandaPagoIn(BaseModel):
    monto_desde: Decimal = Field(ge=0)
    monto_hasta: Decimal | None = None
    requisitos: list[RequisitoBandaPagoIn] = Field(
        min_length=1, max_length=5, default_factory=list
    )


class DocumentoPoliticaPagoIn(BaseModel):
    document_type_id: str
    etapa: str
    obligatorio: bool = True


class PoliticaPagoCreate(BaseModel):
    codigo: str = Field(pattern=r"^[A-Z0-9][A-Z0-9_-]{1,19}$")
    nombre: str = Field(min_length=3, max_length=200)
    descripcion: str | None = Field(default=None, max_length=2000)
    moneda: str = Field(pattern=r"^[A-Z]{3}$")
    permite_pago_parcial: bool = True
    preparador_competencia_accion: str | None = None
    preparador_competencia_materia: str | None = None
    exige_cargo_autorizado_cuenta: bool = False
    control_duplicado: str = "BLOQUEAR"
    vigente_desde: date
    vigente_hasta: date | None = None
    fundamento: str | None = Field(default=None, max_length=2000)
    act_id: str | None = None
    tipo_regla: str = "INSTITUTIONAL_POLICY"
    medios: list[str] = Field(default_factory=list, max_length=20)
    bandas: list[BandaPagoIn] = Field(default_factory=list, max_length=10)
    documentos: list[DocumentoPoliticaPagoIn] = Field(
        default_factory=list, max_length=30
    )


class PoliticaPagoUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=3, max_length=200)
    descripcion: str | None = Field(default=None, max_length=2000)
    moneda: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    permite_pago_parcial: bool | None = None
    preparador_competencia_accion: str | None = None
    preparador_competencia_materia: str | None = None
    exige_cargo_autorizado_cuenta: bool | None = None
    control_duplicado: str | None = None
    vigente_desde: date | None = None
    vigente_hasta: date | None = None
    fundamento: str | None = Field(default=None, max_length=2000)
    act_id: str | None = None
    tipo_regla: str | None = None
    medios: list[str] | None = Field(default=None, max_length=20)
    bandas: list[BandaPagoIn] | None = Field(default=None, max_length=10)
    documentos: list[DocumentoPoliticaPagoIn] | None = Field(
        default=None, max_length=30
    )


class ActivarPoliticaPagoIn(BaseModel):
    fundamento: str = Field(min_length=20, max_length=2000)
    act_id: str | None = None


class CerrarPoliticaPagoIn(BaseModel):
    motivo: str = Field(min_length=10, max_length=500)


class PagoCreate(BaseModel):
    order_id: str
    policy_id: str
    account_id: str
    method_id: str
    monto: Decimal = Field(gt=0)
    fecha_pago: date
    concepto: str = Field(min_length=3, max_length=500)
    documentos: list[str] = Field(default_factory=list, max_length=20)
    idempotency_key: str | None = Field(default=None, max_length=120)


class PagoUpdate(BaseModel):
    policy_id: str | None = None
    account_id: str | None = None
    method_id: str | None = None
    monto: Decimal | None = Field(default=None, gt=0)
    fecha_pago: date | None = None
    concepto: str | None = Field(default=None, min_length=3, max_length=500)
    documentos: list[str] | None = Field(default=None, max_length=20)


class EnviarPagoIn(BaseModel):
    preparador_cargo_id: str | None = None
    confirmar_duplicado: bool = False
    motivo_duplicado: str | None = Field(default=None, max_length=500)


class AprobarPagoIn(BaseModel):
    cargo_id: str
    requisito_indice: int = Field(ge=0)
    documentos: list[str] = Field(default_factory=list, max_length=20)


class RechazarPagoIn(BaseModel):
    cargo_id: str
    motivo: str = Field(min_length=10, max_length=500)


class RegistrarPagoIn(BaseModel):
    fecha_valor: date
    referencia_externa: str | None = Field(default=None, max_length=120)
    documentos: list[str] = Field(default_factory=list, max_length=20)
    idempotency_key: str | None = Field(default=None, max_length=120)


class AnularPagoIn(BaseModel):
    motivo: str = Field(min_length=10, max_length=500)
    documentos: list[str] = Field(default_factory=list, max_length=20)
