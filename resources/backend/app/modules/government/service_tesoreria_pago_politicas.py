"""Servicio de políticas y configuración del pago (TRE-04, parte 1).

Numeración, configuración del patrón, medios de pago y ciclo de vida de las
políticas de pago aplicables a las órdenes de pago. Se comporta como TRE-03,
pero con medios, bandas de aprobación y versionado de políticas.
"""

from __future__ import annotations

import re
from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext
from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.documents.models import DocumentType
from app.modules.government.models import (
    ACCIONES_COMPETENCIA,
    CONTROLES_DUPLICADO_PAGO,
    ESTADOS_MEDIO_PAGO,
    ETAPAS_DOCUMENTO_PAGO,
    MATERIAS_COMPETENCIA,
    MONEDAS_LIMITE,
    TIPOS_REGLA_ORDEN_PAGO,
    GovernmentAct,
    GovernmentPayment,
    GovernmentPaymentMethod,
    GovernmentPaymentPolicy,
    GovernmentPaymentPolicyBand,
    GovernmentPaymentPolicyDocument,
    GovernmentPaymentPolicyHistory,
    GovernmentPaymentPolicyMethod,
    GovernmentPaymentSettings,
)
from app.modules.government.service_presupuesto_causado import (
    PATRON_DEFECTO,
    _render_patron,
    _validar_patron,
)
from app.shared.audit import record_audit
from app.shared.clock import instante_actual

CENTAVOS = Decimal("0.01")


def _patron_actual(db: Session, ctx: CompanyContext) -> GovernmentPaymentSettings:
    fila = db.scalar(
        select(GovernmentPaymentSettings).where(
            GovernmentPaymentSettings.company_id == ctx.company_id
        )
    )
    if fila is None:
        fila = GovernmentPaymentSettings(
            company_id=ctx.company_id,
            patron=PATRON_DEFECTO,
            version=0,
        )
    return fila


def _medio_a_dict(medio: GovernmentPaymentMethod) -> dict[str, Any]:
    return {
        "id": str(medio.id),
        "codigo": medio.codigo,
        "nombre": medio.nombre,
        "descripcion": medio.descripcion,
        "estado": medio.estado,
        "vigente_desde": medio.vigente_desde.isoformat(),
        "vigente_hasta": medio.vigente_hasta.isoformat() if medio.vigente_hasta else None,
        "exige_referencia": medio.exige_referencia,
        "referencia_unica": medio.referencia_unica,
        "patron_referencia": medio.patron_referencia,
        "fundamento": medio.fundamento,
        "version": medio.version,
    }


def _validar_medio_comun(cuerpo: dict[str, Any]) -> None:
    vigente_desde = cuerpo.get("vigente_desde")
    vigente_hasta = cuerpo.get("vigente_hasta")
    if vigente_hasta is not None and vigente_desde is not None and vigente_hasta < vigente_desde:
        raise KontrolError(
            code="GOV_PAYMENT_METHOD_INVALID",
            message="vigente_hasta no puede ser anterior a vigente_desde",
            status_code=422,
            details={"field_errors": {"vigente_hasta": "Debe ser mayor o igual a vigente_desde"}},
        )
    exige_referencia = bool(cuerpo.get("exige_referencia", False))
    referencia_unica = bool(cuerpo.get("referencia_unica", False))
    if referencia_unica and not exige_referencia:
        raise KontrolError(
            code="GOV_PAYMENT_METHOD_INVALID",
            message="referencia_unica exige exige_referencia",
            status_code=422,
            details={"field_errors": {"referencia_unica": "Requiere exige_referencia=true"}},
        )
    patron_referencia = cuerpo.get("patron_referencia")
    if patron_referencia is not None:
        try:
            re.compile(patron_referencia)
        except re.error as exc:
            raise KontrolError(
                code="GOV_PAYMENT_METHOD_INVALID",
                message="patron_referencia no es una expresión regular válida",
                status_code=422,
                details={"field_errors": {"patron_referencia": str(exc)}},
            ) from exc


def _validar_documentos_politica_pago(
    db: Session,
    ctx: CompanyContext,
    documentos: Any,
) -> list[dict[str, Any]]:
    if documentos is None:
        return []
    if not isinstance(documentos, list):
        raise KontrolError(
            code="GOV_PAYMENT_POLICY_INVALID",
            message="documentos debe ser una lista",
            status_code=422,
        )
    tipos: set[tuple[str, str]] = set()
    resultado: list[dict[str, Any]] = []
    for documento in documentos:
        if not isinstance(documento, dict):
            raise KontrolError(
                code="GOV_PAYMENT_POLICY_INVALID",
                message="documentos contiene elementos inválidos",
                status_code=422,
            )
        document_type_id = documento.get("document_type_id")
        if not isinstance(document_type_id, str):
            raise KontrolError(
                code="GOV_PAYMENT_POLICY_INVALID",
                message="document_type_id es obligatorio",
                status_code=422,
            )
        tipo = db.scalar(
            select(DocumentType).where(
                DocumentType.company_id == ctx.company_id,
                DocumentType.id == document_type_id,
                DocumentType.status == "ACTIVE",
            )
        )
        if tipo is None:
            raise KontrolError(
                code="GOV_PAYMENT_POLICY_INVALID",
                message="document_type_id no corresponde a un tipo documental activo",
                status_code=422,
            )
        etapa = documento.get("etapa", "PREPARAR")
        if etapa not in ETAPAS_DOCUMENTO_PAGO:
            raise KontrolError(
                code="GOV_PAYMENT_POLICY_INVALID",
                message="etapa inválida para documento de política de pago",
                status_code=422,
            )
        clave = (document_type_id, etapa)
        if clave in tipos:
            raise KontrolError(
                code="GOV_PAYMENT_POLICY_INVALID",
                message="document_type_id y etapa repetidos en documentos",
                status_code=422,
            )
        tipos.add(clave)
        resultado.append(
            {
                "document_type_id": document_type_id,
                "etapa": etapa,
                "obligatorio": bool(documento.get("obligatorio", True)),
            }
        )
    return resultado


def _validar_medios_politica(
    db: Session,
    ctx: CompanyContext,
    medios: Any,
) -> list[str]:
    if medios is None:
        return []
    if not isinstance(medios, list):
        raise KontrolError(
            code="GOV_PAYMENT_POLICY_INVALID",
            message="medios debe ser una lista",
            status_code=422,
        )
    ids: set[str] = set()
    for medio_id in medios:
        if not isinstance(medio_id, str):
            raise KontrolError(
                code="GOV_PAYMENT_POLICY_INVALID",
                message="medios contiene identificadores inválidos",
                status_code=422,
            )
        if medio_id in ids:
            raise KontrolError(
                code="GOV_PAYMENT_POLICY_INVALID",
                message="medios repetidos",
                status_code=422,
            )
        ids.add(medio_id)
        medio = db.scalar(
            select(GovernmentPaymentMethod).where(
                GovernmentPaymentMethod.company_id == ctx.company_id,
                GovernmentPaymentMethod.id == medio_id,
            )
        )
        if medio is None:
            raise KontrolError(
                code="GOV_PAYMENT_POLICY_INVALID",
                message="medios contiene un identificador inexistente",
                status_code=422,
            )
    return list(ids)


def _validar_politica_comun(
    db: Session,
    ctx: CompanyContext,
    cuerpo: dict[str, Any],
) -> dict[str, Any]:
    if "moneda" in cuerpo or "moneda" not in cuerpo:
        moneda = cuerpo.get("moneda")
        if moneda is not None:
            if not isinstance(moneda, str) or moneda.upper() not in MONEDAS_LIMITE:
                raise KontrolError(
                    code="GOV_PAYMENT_POLICY_INVALID",
                    message="moneda inválida para política de pago",
                    status_code=422,
                )
    if "tipo_regla" in cuerpo:
        tipo_regla = cuerpo.get("tipo_regla")
        if tipo_regla not in TIPOS_REGLA_ORDEN_PAGO:
            raise KontrolError(
                code="GOV_PAYMENT_POLICY_INVALID",
                message="tipo_regla inválida para política de pago",
                status_code=422,
            )
    if "control_duplicado" in cuerpo:
        if cuerpo.get("control_duplicado") not in CONTROLES_DUPLICADO_PAGO:
            raise KontrolError(
                code="GOV_PAYMENT_POLICY_INVALID",
                message="control_duplicado inválido para política de pago",
                status_code=422,
            )
    preparador_accion = cuerpo.get("preparador_competencia_accion")
    preparador_materia = cuerpo.get("preparador_competencia_materia")
    if (preparador_accion is None) != (preparador_materia is None):
        raise KontrolError(
            code="GOV_PAYMENT_POLICY_INVALID",
            message="preparador_competencia_accion y preparador_competencia_materia deben ir juntos",
            status_code=422,
        )
    if preparador_accion is not None and preparador_accion not in ACCIONES_COMPETENCIA:
        raise KontrolError(
            code="GOV_PAYMENT_POLICY_INVALID",
            message="preparador_competencia_accion inválida",
            status_code=422,
        )
    if preparador_materia is not None and preparador_materia not in MATERIAS_COMPETENCIA:
        raise KontrolError(
            code="GOV_PAYMENT_POLICY_INVALID",
            message="preparador_competencia_materia inválida",
            status_code=422,
        )
    vigente_desde = cuerpo.get("vigente_desde")
    vigente_hasta = cuerpo.get("vigente_hasta")
    if vigente_desde is not None and vigente_hasta is not None and vigente_hasta < vigente_desde:
        raise KontrolError(
            code="GOV_PAYMENT_POLICY_INVALID",
            message="vigente_hasta no puede ser anterior a vigente_desde",
            status_code=422,
        )
    documentos = _validar_documentos_politica_pago(db, ctx, cuerpo.get("documentos"))
    medios = _validar_medios_politica(db, ctx, cuerpo.get("medios"))
    bandas = validar_bandas(cuerpo.get("bandas") or [])
    return {
        "documentos": documentos,
        "medios": medios,
        "bandas": bandas,
    }


def _validar_act_id_pago(db: Session, ctx: CompanyContext, act_id: Any) -> str | None:
    if act_id is None:
        return None
    if not isinstance(act_id, str):
        raise KontrolError(
            code="GOV_PAYMENT_POLICY_INVALID",
            message="act_id debe ser texto",
            status_code=422,
        )
    acto = db.scalar(
        select(GovernmentAct).where(
            GovernmentAct.company_id == ctx.company_id,
            GovernmentAct.id == act_id,
        )
    )
    if acto is None:
        raise KontrolError(
            code="GOV_PAYMENT_POLICY_INVALID",
            message="act_id no corresponde a un acto de la empresa",
            status_code=422,
        )
    return act_id


def _guardar_colecciones(
    db: Session,
    ctx: CompanyContext,
    policy: GovernmentPaymentPolicy,
    medios: list[str],
    bandas: list[dict[str, Any]],
    documentos: list[dict[str, Any]],
) -> None:
    for medio_id in medios:
        db.add(
            GovernmentPaymentPolicyMethod(
                policy_id=str(policy.id),
                company_id=ctx.company_id,
                method_id=medio_id,
            )
        )
    for orden, banda in enumerate(bandas, start=1):
        db.add(
            GovernmentPaymentPolicyBand(
                policy_id=str(policy.id),
                company_id=ctx.company_id,
                orden=orden,
                monto_desde=banda["monto_desde"],
                monto_hasta=banda["monto_hasta"],
                requisitos=banda["requisitos"],
            )
        )
    for documento in documentos:
        db.add(
            GovernmentPaymentPolicyDocument(
                policy_id=str(policy.id),
                company_id=ctx.company_id,
                document_type_id=documento["document_type_id"],
                etapa=documento["etapa"],
                obligatorio=documento["obligatorio"],
            )
        )
        db.flush()


def _borrar_colecciones(db: Session, ctx: CompanyContext, policy_id: str) -> None:
    for medio_fila in db.scalars(
        select(GovernmentPaymentPolicyMethod).where(
            GovernmentPaymentPolicyMethod.company_id == ctx.company_id,
            GovernmentPaymentPolicyMethod.policy_id == policy_id,
        )
    ):
        db.delete(medio_fila)
    for banda_fila in db.scalars(
        select(GovernmentPaymentPolicyBand).where(
            GovernmentPaymentPolicyBand.company_id == ctx.company_id,
            GovernmentPaymentPolicyBand.policy_id == policy_id,
        )
    ):
        db.delete(banda_fila)
    for documento_fila in db.scalars(
        select(GovernmentPaymentPolicyDocument).where(
            GovernmentPaymentPolicyDocument.company_id == ctx.company_id,
            GovernmentPaymentPolicyDocument.policy_id == policy_id,
        )
    ):
        db.delete(documento_fila)
    db.flush()


def _etiqueta_tipo_documental(db: Session, ctx: CompanyContext, tipo_id: str) -> str:
    tipo = db.scalar(
        select(DocumentType).where(
            DocumentType.company_id == ctx.company_id,
            DocumentType.id == tipo_id,
        )
    )
    if tipo is None:
        return tipo_id
    return f"{tipo.code} · {tipo.name}"


def _politica_a_dict(
    db: Session,
    ctx: CompanyContext,
    policy: GovernmentPaymentPolicy,
    incluir_historia: bool = True,
) -> dict[str, Any]:
    medios = db.scalars(
        select(GovernmentPaymentMethod)
        .join(
            GovernmentPaymentPolicyMethod,
            GovernmentPaymentPolicyMethod.method_id == GovernmentPaymentMethod.id,
        )
        .where(
            GovernmentPaymentPolicyMethod.company_id == ctx.company_id,
            GovernmentPaymentPolicyMethod.policy_id == str(policy.id),
        )
        .order_by(GovernmentPaymentMethod.codigo)
    ).all()
    bandas = db.scalars(
        select(GovernmentPaymentPolicyBand)
        .where(
            GovernmentPaymentPolicyBand.company_id == ctx.company_id,
            GovernmentPaymentPolicyBand.policy_id == str(policy.id),
        )
        .order_by(GovernmentPaymentPolicyBand.orden)
    ).all()
    documentos = db.scalars(
        select(GovernmentPaymentPolicyDocument)
        .where(
            GovernmentPaymentPolicyDocument.company_id == ctx.company_id,
            GovernmentPaymentPolicyDocument.policy_id == str(policy.id),
        )
        .order_by(
            GovernmentPaymentPolicyDocument.etapa,
            GovernmentPaymentPolicyDocument.document_type_id,
        )
    ).all()
    historia: list[dict[str, Any]] = []
    if incluir_historia:
        filas_historia = db.scalars(
            select(GovernmentPaymentPolicyHistory)
            .where(
                GovernmentPaymentPolicyHistory.company_id == ctx.company_id,
                GovernmentPaymentPolicyHistory.policy_id == str(policy.id),
            )
            .order_by(GovernmentPaymentPolicyHistory.created_at)
        ).all()
        historia = [
            {
                "evento": fila.evento,
                "numero_version": fila.numero_version,
                "actor_id": fila.actor_id,
                "created_at": fila.created_at.isoformat(),
            }
            for fila in filas_historia
        ]

    def _decimal2(value: Decimal | None) -> str | None:
        if value is None:
            return None
        return str(value.quantize(CENTAVOS, rounding=ROUND_HALF_UP))

    return {
        "id": str(policy.id),
        "codigo": policy.codigo,
        "numero_version": policy.numero_version,
        "nombre": policy.nombre,
        "descripcion": policy.descripcion,
        "moneda": policy.moneda,
        "permite_pago_parcial": policy.permite_pago_parcial,
        "preparador_competencia_accion": policy.preparador_competencia_accion,
        "preparador_competencia_materia": policy.preparador_competencia_materia,
        "exige_cargo_autorizado_cuenta": policy.exige_cargo_autorizado_cuenta,
        "control_duplicado": policy.control_duplicado,
        "vigente_desde": policy.vigente_desde.isoformat(),
        "vigente_hasta": policy.vigente_hasta.isoformat() if policy.vigente_hasta else None,
        "fundamento": policy.fundamento,
        "act_id": policy.act_id,
        "tipo_regla": policy.tipo_regla,
        "estado": policy.estado,
        "version": policy.version,
        "version_anterior_id": policy.version_anterior_id,
        "medios": [
            {
                "id": str(medio.id),
                "codigo": medio.codigo,
                "nombre": medio.nombre,
                "estado": medio.estado,
            }
            for medio in medios
        ],
        "bandas": [
            {
                "orden": banda.orden,
                "monto_desde": _decimal2(banda.monto_desde),
                "monto_hasta": _decimal2(banda.monto_hasta),
                "requisitos": banda.requisitos,
            }
            for banda in bandas
        ],
        "documentos": [
            {
                "document_type_id": documento.document_type_id,
                "etiqueta": _etiqueta_tipo_documental(
                    db, ctx, documento.document_type_id
                ),
                "etapa": documento.etapa,
                "obligatorio": documento.obligatorio,
            }
            for documento in documentos
        ],
        "historia": historia,
    }


# 1. Configuración
def configuracion_actual(db: Session, ctx: CompanyContext) -> dict[str, Any]:
    fila = _patron_actual(db, ctx)
    return {"patron": fila.patron, "version": fila.version}


def actualizar_configuracion(
    db: Session,
    ctx: CompanyContext,
    cuerpo: dict[str, Any],
    version: int | None,
) -> dict[str, Any]:
    if version is None:
        raise KontrolError(
            code="GOV_PAYMENT_SETTINGS_IF_MATCH_REQUIRED",
            message="Se requiere la versión de la configuración",
            status_code=428,
        )
    fila = _patron_actual(db, ctx)
    if fila.version != version:
        raise ConflictError(
            "GOV_PAYMENT_SETTINGS_STALE",
            "La configuración fue cambiada por otro usuario",
            details={"version_actual": fila.version},
        )
    patron = cuerpo.get("patron")
    if not isinstance(patron, str) or not 3 <= len(patron) <= 60:
        raise KontrolError(
            code="GOV_PAYMENT_SETTINGS_INVALID",
            message="patron debe ser texto de entre 3 y 60 caracteres",
            status_code=422,
        )
    _validar_patron(patron)
    fila.patron = patron
    fila.version += 1
    if fila.id is None or fila not in db:
        db.add(fila)
    record_audit(
        db,
        action="GOV_PAYMENT_SETTINGS_UPDATED",
        entity_type="GovernmentPaymentSettings",
        entity_id=str(ctx.company_id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={"patron": fila.patron},
    )
    db.flush()
    return {"patron": fila.patron, "version": fila.version}


# 2. Numeración
def siguiente_codigo_pago(
    db: Session,
    ctx: CompanyContext,
    anio: int,
) -> tuple[int, str]:
    inicio = datetime(anio, 1, 1, tzinfo=UTC)
    fin = datetime(anio + 1, 1, 1, tzinfo=UTC)
    maximo = db.scalar(
        select(func.max(GovernmentPayment.numero)).where(
            GovernmentPayment.company_id == ctx.company_id,
            GovernmentPayment.enviado_en >= inicio,
            GovernmentPayment.enviado_en < fin,
        )
    )
    siguiente = 1 if maximo is None else int(maximo) + 1
    fila = _patron_actual(db, ctx)
    codigo = _render_patron(fila.patron, anio, siguiente)
    return siguiente, codigo


# 3. Medios de pago
def listar_medios(db: Session, ctx: CompanyContext) -> list[dict[str, Any]]:
    filas = db.scalars(
        select(GovernmentPaymentMethod)
        .where(GovernmentPaymentMethod.company_id == ctx.company_id)
        .order_by(GovernmentPaymentMethod.codigo)
    ).all()
    return [_medio_a_dict(medio) for medio in filas]


def medio_de_empresa(
    db: Session,
    ctx: CompanyContext,
    method_id: str,
) -> GovernmentPaymentMethod:
    medio = db.scalar(
        select(GovernmentPaymentMethod).where(
            GovernmentPaymentMethod.company_id == ctx.company_id,
            GovernmentPaymentMethod.id == method_id,
        )
    )
    if medio is None:
        raise NotFoundError(
            "GOV_PAYMENT_METHOD_NOT_FOUND",
            "Medio de pago no encontrado",
        )
    return medio


def obtener_medio(
    db: Session,
    ctx: CompanyContext,
    method_id: str,
) -> dict[str, Any]:
    return _medio_a_dict(medio_de_empresa(db, ctx, method_id))


def crear_medio(
    db: Session,
    ctx: CompanyContext,
    cuerpo: dict[str, Any],
) -> dict[str, Any]:
    codigo = cuerpo.get("codigo")
    if not isinstance(codigo, str) or not re.fullmatch(r"^[A-Z0-9][A-Z0-9_-]{1,19}$", codigo):
        raise KontrolError(
            code="GOV_PAYMENT_METHOD_INVALID",
            message="codigo inválido",
            status_code=422,
        )
    existente = db.scalar(
        select(GovernmentPaymentMethod).where(
            GovernmentPaymentMethod.company_id == ctx.company_id,
            GovernmentPaymentMethod.codigo == codigo,
        )
    )
    if existente is not None:
        raise ConflictError(
            "GOV_PAYMENT_METHOD_CODE_DUPLICATE",
            "El código de medio de pago ya existe",
        )
    _validar_medio_comun(cuerpo)
    medio = GovernmentPaymentMethod(
        company_id=ctx.company_id,
        codigo=codigo,
        nombre=cuerpo["nombre"],
        descripcion=cuerpo.get("descripcion"),
        estado="ACTIVO",
        vigente_desde=cuerpo["vigente_desde"],
        vigente_hasta=cuerpo.get("vigente_hasta"),
        exige_referencia=bool(cuerpo.get("exige_referencia", False)),
        referencia_unica=bool(cuerpo.get("referencia_unica", False)),
        patron_referencia=cuerpo.get("patron_referencia"),
        fundamento=cuerpo.get("fundamento"),
    )
    db.add(medio)
    record_audit(
        db,
        action="GOV_PAYMENT_METHOD_CREATED",
        entity_type="GovernmentPaymentMethod",
        entity_id=str(medio.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={"codigo": medio.codigo, "nombre": medio.nombre},
    )
    db.flush()
    return _medio_a_dict(medio)


def actualizar_medio(
    db: Session,
    ctx: CompanyContext,
    method_id: str,
    cuerpo: dict[str, Any],
    version: int | None,
) -> dict[str, Any]:
    if version is None:
        raise KontrolError(
            code="GOV_PAYMENT_METHOD_IF_MATCH_REQUIRED",
            message="Se requiere la versión del medio de pago",
            status_code=428,
        )
    medio = medio_de_empresa(db, ctx, method_id)
    if medio.version != version:
        raise ConflictError(
            "GOV_PAYMENT_METHOD_VERSION_CONFLICT",
            "El medio de pago fue cambiado por otro usuario",
            details={"version_actual": medio.version},
        )
    datos_actualizados: dict[str, Any] = {}
    for campo in (
        "nombre",
        "descripcion",
        "vigente_desde",
        "vigente_hasta",
        "exige_referencia",
        "referencia_unica",
        "patron_referencia",
        "fundamento",
    ):
        if campo in cuerpo:
            datos_actualizados[campo] = cuerpo[campo]
    if "estado" in cuerpo:
        estado = cuerpo["estado"]
        if estado not in ESTADOS_MEDIO_PAGO:
            raise KontrolError(
                code="GOV_PAYMENT_METHOD_INVALID",
                message="estado inválido para medio de pago",
                status_code=422,
            )
        datos_actualizados["estado"] = estado
    datos_validacion = {
        "vigente_desde": datos_actualizados.get("vigente_desde", medio.vigente_desde),
        "vigente_hasta": datos_actualizados.get("vigente_hasta", medio.vigente_hasta),
        "exige_referencia": datos_actualizados.get("exige_referencia", medio.exige_referencia),
        "referencia_unica": datos_actualizados.get("referencia_unica", medio.referencia_unica),
        "patron_referencia": datos_actualizados.get("patron_referencia", medio.patron_referencia),
    }
    _validar_medio_comun(datos_validacion)
    for campo, valor in datos_actualizados.items():
        setattr(medio, campo, valor)
    medio.version += 1
    record_audit(
        db,
        action="GOV_PAYMENT_METHOD_UPDATED",
        entity_type="GovernmentPaymentMethod",
        entity_id=str(medio.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={"codigo": medio.codigo, "estado": medio.estado, "version": medio.version},
    )
    db.flush()
    return _medio_a_dict(medio)


def medio_utilizable(medio: GovernmentPaymentMethod, fecha: date) -> bool:
    if medio.estado != "ACTIVO":
        return False
    if medio.vigente_desde > fecha:
        return False
    if medio.vigente_hasta is not None and fecha > medio.vigente_hasta:
        return False
    return True


# 5. Validación de bandas
def validar_bandas(bandas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if bandas is None:
        return []
    if not isinstance(bandas, list):
        raise KontrolError(
            code="GOV_PAYMENT_POLICY_BANDS_INVALID",
            message="bandas debe ser una lista",
            status_code=422,
        )
    if not bandas:
        return []
    resultado: list[dict[str, Any]] = []
    anterior_hasta: Decimal | None = None
    for indice, banda in enumerate(bandas):
        if not isinstance(banda, dict):
            raise KontrolError(
                code="GOV_PAYMENT_POLICY_BANDS_INVALID",
                message="bandas contiene elementos inválidos",
                status_code=422,
            )
        monto_desde = banda.get("monto_desde")
        monto_hasta = banda.get("monto_hasta")
        if monto_desde is None:
            raise KontrolError(
                code="GOV_PAYMENT_POLICY_BANDS_INVALID",
                message="monto_desde es obligatorio en cada banda",
                status_code=422,
            )
        try:
            desde = Decimal(str(monto_desde)).quantize(CENTAVOS, rounding=ROUND_HALF_UP)
            hasta = (
                None
                if monto_hasta is None
                else Decimal(str(monto_hasta)).quantize(CENTAVOS, rounding=ROUND_HALF_UP)
            )
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise KontrolError(
                code="GOV_PAYMENT_POLICY_BANDS_INVALID",
                message="montos de banda inválidos",
                status_code=422,
            ) from exc
        if desde < 0:
            raise KontrolError(
                code="GOV_PAYMENT_POLICY_BANDS_INVALID",
                message="monto_desde no puede ser negativo",
                status_code=422,
            )
        if hasta is not None and hasta <= desde:
            raise KontrolError(
                code="GOV_PAYMENT_POLICY_BANDS_INVALID",
                message="monto_hasta debe ser mayor que monto_desde",
                status_code=422,
            )
        if indice == 0:
            if desde != 0:
                raise KontrolError(
                    code="GOV_PAYMENT_POLICY_BANDS_INVALID",
                    message="la primera banda debe iniciar en 0",
                    status_code=422,
                )
        else:
            if anterior_hasta is None or desde != anterior_hasta:
                raise KontrolError(
                    code="GOV_PAYMENT_POLICY_BANDS_INVALID",
                    message="cada banda debe iniciar exactamente donde termina la anterior",
                    status_code=422,
                )
        if hasta is None and indice != len(bandas) - 1:
            raise KontrolError(
                code="GOV_PAYMENT_POLICY_BANDS_INVALID",
                message="solo la última banda puede tener monto_hasta nulo",
                status_code=422,
            )
        requisitos_brutos = banda.get("requisitos") or []
        if not isinstance(requisitos_brutos, list) or not 1 <= len(requisitos_brutos) <= 5:
            raise KontrolError(
                code="GOV_PAYMENT_POLICY_BANDS_INVALID",
                message="cada banda debe tener entre 1 y 5 requisitos",
                status_code=422,
            )
        requisitos: list[dict[str, Any]] = []
        vistos: set[tuple[str, str]] = set()
        for requisito_bruto in requisitos_brutos:
            if not isinstance(requisito_bruto, dict):
                raise KontrolError(
                    code="GOV_PAYMENT_POLICY_BANDS_INVALID",
                    message="requisitos contiene elementos inválidos",
                    status_code=422,
                )
            accion = requisito_bruto.get("accion")
            materia = requisito_bruto.get("materia")
            cantidad = requisito_bruto.get("cantidad")
            if accion not in ACCIONES_COMPETENCIA:
                raise KontrolError(
                    code="GOV_PAYMENT_POLICY_BANDS_INVALID",
                    message="accion inválida en requisito de banda",
                    status_code=422,
                )
            if materia not in MATERIAS_COMPETENCIA:
                raise KontrolError(
                    code="GOV_PAYMENT_POLICY_BANDS_INVALID",
                    message="materia inválida en requisito de banda",
                    status_code=422,
                )
            if not isinstance(cantidad, int) or not 1 <= cantidad <= 5:
                raise KontrolError(
                    code="GOV_PAYMENT_POLICY_BANDS_INVALID",
                    message="cantidad debe ser un entero entre 1 y 5",
                    status_code=422,
                )
            clave = (accion, materia)
            if clave in vistos:
                raise KontrolError(
                    code="GOV_PAYMENT_POLICY_BANDS_INVALID",
                    message="requisito repetido en la misma banda",
                    status_code=422,
                )
            vistos.add(clave)
            requisitos.append({"accion": accion, "materia": materia, "cantidad": cantidad})
        resultado.append(
            {
                "monto_desde": desde,
                "monto_hasta": hasta,
                "requisitos": requisitos,
            }
        )
        anterior_hasta = hasta
    return resultado


def banda_para_monto(
    bandas: list[dict[str, Any]],
    monto: Decimal,
) -> tuple[int, dict[str, Any]] | None:
    if not isinstance(bandas, list) or not bandas:
        return None
    monto_dec = Decimal(str(monto))
    for indice, banda in enumerate(bandas, start=1):
        if not isinstance(banda, dict):
            continue
        desde = Decimal(str(banda.get("monto_desde", "0") or "0"))
        hasta = banda.get("monto_hasta")
        if hasta is not None:
            hasta_dec = Decimal(str(hasta))
            if desde < monto_dec <= hasta_dec:
                return indice, banda
        else:
            if desde < monto_dec:
                return indice, banda
    return None


def _historia(
    db: Session,
    ctx: CompanyContext,
    policy: GovernmentPaymentPolicy,
    evento: str,
) -> None:
    db.add(
        GovernmentPaymentPolicyHistory(
            policy_id=str(policy.id),
            company_id=ctx.company_id,
            evento=evento,
            numero_version=policy.numero_version,
            instantanea=_politica_a_dict(db, ctx, policy, incluir_historia=False),
            actor_id=ctx.user_id,
            created_by=ctx.user_id,
        )
    )
    db.flush()


def _auditar_politica(
    db: Session,
    ctx: CompanyContext,
    action: str,
    policy: GovernmentPaymentPolicy,
    after: dict[str, Any] | None = None,
) -> None:
    record_audit(
        db,
        action=action,
        entity_type="GovernmentPaymentPolicy",
        entity_id=str(policy.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after=after or {"codigo": policy.codigo, "numero_version": policy.numero_version},
    )


def politica_pago_de_empresa(
    db: Session,
    ctx: CompanyContext,
    policy_id: str,
    bloquear: bool = False,
) -> GovernmentPaymentPolicy:
    consulta = select(GovernmentPaymentPolicy).where(
        GovernmentPaymentPolicy.company_id == ctx.company_id,
        GovernmentPaymentPolicy.id == policy_id,
    )
    if bloquear:
        consulta = consulta.with_for_update()
    policy = db.scalar(consulta)
    if policy is None:
        raise NotFoundError(
            "GOV_PAYMENT_POLICY_NOT_FOUND",
            "Política de pago no encontrada",
        )
    return policy


def listar_politicas_pago(db: Session, ctx: CompanyContext) -> list[dict[str, Any]]:
    filas = db.scalars(
        select(GovernmentPaymentPolicy)
        .where(GovernmentPaymentPolicy.company_id == ctx.company_id)
        .order_by(
            GovernmentPaymentPolicy.codigo,
            GovernmentPaymentPolicy.numero_version,
        )
    ).all()
    return [
        {
            "id": str(policy.id),
            "codigo": policy.codigo,
            "numero_version": policy.numero_version,
            "nombre": policy.nombre,
            "moneda": policy.moneda,
            "estado": policy.estado,
            "vigente_desde": policy.vigente_desde.isoformat(),
            "vigente_hasta": policy.vigente_hasta.isoformat() if policy.vigente_hasta else None,
            "version": policy.version,
        }
        for policy in filas
    ]


def obtener_politica_pago(db: Session, ctx: CompanyContext, policy_id: str) -> dict[str, Any]:
    policy = politica_pago_de_empresa(db, ctx, policy_id)
    return _politica_a_dict(db, ctx, policy)


def crear_politica_pago(
    db: Session,
    ctx: CompanyContext,
    cuerpo: dict[str, Any],
) -> dict[str, Any]:
    codigo = cuerpo.get("codigo")
    if not isinstance(codigo, str) or not codigo.strip():
        raise KontrolError(
            code="GOV_PAYMENT_POLICY_INVALID",
            message="codigo es obligatorio",
            status_code=422,
        )
    existente = db.scalar(
        select(GovernmentPaymentPolicy).where(
            GovernmentPaymentPolicy.company_id == ctx.company_id,
            GovernmentPaymentPolicy.codigo == codigo,
        )
    )
    if existente is not None:
        raise ConflictError(
            "GOV_PAYMENT_POLICY_CODE_DUPLICATE",
            "El código de política de pago ya existe",
        )
    validados = _validar_politica_comun(db, ctx, cuerpo)
    policy = GovernmentPaymentPolicy(
        company_id=ctx.company_id,
        codigo=codigo,
        numero_version=1,
        nombre=cuerpo.get("nombre"),
        descripcion=cuerpo.get("descripcion"),
        moneda=cuerpo.get("moneda"),
        permite_pago_parcial=bool(cuerpo.get("permite_pago_parcial", False)),
        preparador_competencia_accion=cuerpo.get("preparador_competencia_accion"),
        preparador_competencia_materia=cuerpo.get("preparador_competencia_materia"),
        exige_cargo_autorizado_cuenta=bool(cuerpo.get("exige_cargo_autorizado_cuenta", False)),
        control_duplicado=cuerpo.get("control_duplicado"),
        vigente_desde=cuerpo.get("vigente_desde"),
        vigente_hasta=cuerpo.get("vigente_hasta"),
        fundamento=cuerpo.get("fundamento"),
        act_id=_validar_act_id_pago(db, ctx, cuerpo.get("act_id")),
        tipo_regla=cuerpo.get("tipo_regla"),
        estado="BORRADOR",
        created_by=ctx.user_id,
    )
    db.add(policy)
    db.flush()
    _guardar_colecciones(
        db,
        ctx,
        policy,
        validados["medios"],
        validados["bandas"],
        validados["documentos"],
    )
    _historia(db, ctx, policy, "CREADA")
    _auditar_politica(db, ctx, "GOV_PAYMENT_POLICY_CREATED", policy)
    db.flush()
    return _politica_a_dict(db, ctx, policy)


def _actualizar_politica(
    db: Session,
    ctx: CompanyContext,
    policy: GovernmentPaymentPolicy,
    cuerpo: dict[str, Any],
) -> None:
    campos_directos = [
        "nombre",
        "descripcion",
        "moneda",
        "permite_pago_parcial",
        "preparador_competencia_accion",
        "preparador_competencia_materia",
        "exige_cargo_autorizado_cuenta",
        "control_duplicado",
        "vigente_desde",
        "vigente_hasta",
        "fundamento",
        "tipo_regla",
    ]
    for campo in campos_directos:
        if campo in cuerpo:
            setattr(policy, campo, cuerpo[campo])
    if "act_id" in cuerpo:
        policy.act_id = _validar_act_id_pago(db, ctx, cuerpo.get("act_id"))


def actualizar_politica_pago(
    db: Session,
    ctx: CompanyContext,
    policy_id: str,
    cuerpo: dict[str, Any],
    version: int | None,
) -> dict[str, Any]:
    if version is None:
        raise KontrolError(
            code="GOV_PAYMENT_POLICY_IF_MATCH_REQUIRED",
            message="Se requiere la versión de la política de pago",
            status_code=428,
        )
    policy = politica_pago_de_empresa(db, ctx, policy_id, bloquear=True)
    if policy.estado != "BORRADOR":
        raise ConflictError(
            "GOV_PAYMENT_POLICY_NOT_DRAFT",
            "Solo las políticas en borrador pueden actualizarse",
        )
    if policy.version != version:
        raise ConflictError(
            "GOV_PAYMENT_POLICY_VERSION_CONFLICT",
            "La política de pago fue cambiada por otro usuario",
            details={"version_actual": policy.version},
        )
    validados = _validar_politica_comun(db, ctx, cuerpo)
    _actualizar_politica(db, ctx, policy, cuerpo)
    if "medios" in cuerpo or "bandas" in cuerpo or "documentos" in cuerpo:
        _borrar_colecciones(db, ctx, str(policy.id))
        _guardar_colecciones(
            db,
            ctx,
            policy,
            validados["medios"],
            validados["bandas"],
            validados["documentos"],
        )
    policy.version += 1
    _historia(db, ctx, policy, "ACTUALIZADA")
    _auditar_politica(
        db,
        ctx,
        "GOV_PAYMENT_POLICY_UPDATED",
        policy,
        after={"codigo": policy.codigo, "version": policy.version},
    )
    db.flush()
    return _politica_a_dict(db, ctx, policy)


def activar_politica_pago(
    db: Session,
    ctx: CompanyContext,
    policy_id: str,
    cuerpo: dict[str, Any],
    version: int | None,
) -> dict[str, Any]:
    if version is None:
        raise KontrolError(
            code="GOV_PAYMENT_POLICY_IF_MATCH_REQUIRED",
            message="Se requiere la versión de la política de pago",
            status_code=428,
        )
    policy = politica_pago_de_empresa(db, ctx, policy_id, bloquear=True)
    if policy.estado != "BORRADOR":
        raise ConflictError(
            "GOV_PAYMENT_POLICY_NOT_DRAFT",
            "Solo las políticas en borrador pueden activarse",
        )
    if policy.version != version:
        raise ConflictError(
            "GOV_PAYMENT_POLICY_VERSION_CONFLICT",
            "La política de pago fue cambiada por otro usuario",
            details={"version_actual": policy.version},
        )
    fundamento = cuerpo.get("fundamento")
    if not isinstance(fundamento, str) or not fundamento.strip():
        raise KontrolError(
            code="GOV_PAYMENT_POLICY_INVALID",
            message="fundamento es obligatorio para activar",
            status_code=422,
        )
    act_id = _validar_act_id_pago(db, ctx, cuerpo.get("act_id"))
    metodos = db.scalars(
        select(GovernmentPaymentPolicyMethod).where(
            GovernmentPaymentPolicyMethod.company_id == ctx.company_id,
            GovernmentPaymentPolicyMethod.policy_id == policy_id,
        )
    ).all()
    if not metodos:
        raise KontrolError(
            code="GOV_PAYMENT_POLICY_METHODS_REQUIRED",
            message="La política debe tener al menos un medio de pago para activarse",
            status_code=422,
        )
    medios = db.scalars(
        select(GovernmentPaymentMethod)
        .join(
            GovernmentPaymentPolicyMethod,
            GovernmentPaymentPolicyMethod.method_id == GovernmentPaymentMethod.id,
        )
        .where(
            GovernmentPaymentPolicyMethod.company_id == ctx.company_id,
            GovernmentPaymentPolicyMethod.policy_id == policy_id,
        )
    ).all()
    for medio in medios:
        if medio.estado != "ACTIVO":
            raise KontrolError(
                code="GOV_PAYMENT_POLICY_METHODS_REQUIRED",
                message="Todos los medios de pago deben estar activos para activar la política",
                status_code=422,
            )
    bandas = db.scalars(
        select(GovernmentPaymentPolicyBand)
        .where(
            GovernmentPaymentPolicyBand.company_id == ctx.company_id,
            GovernmentPaymentPolicyBand.policy_id == policy_id,
        )
        .order_by(GovernmentPaymentPolicyBand.orden)
    ).all()
    if not bandas:
        raise KontrolError(
            code="GOV_PAYMENT_POLICY_BANDS_INVALID",
            message="La política debe tener al menos una banda para activarse",
            status_code=422,
        )
    bandas_normalizadas = validar_bandas(
        [
            {
                "monto_desde": banda.monto_desde,
                "monto_hasta": banda.monto_hasta,
                "requisitos": banda.requisitos,
            }
            for banda in bandas
        ]
    )
    ahora = instante_actual()
    nueva_vigente_desde = policy.vigente_desde
    if policy.version_anterior_id is not None:
        anterior = politica_pago_de_empresa(db, ctx, policy.version_anterior_id)
        if anterior.estado == "VIGENTE":
            if nueva_vigente_desde <= anterior.vigente_desde:
                raise KontrolError(
                    code="GOV_PAYMENT_POLICY_INVALID",
                    message="vigente_desde debe ser posterior al de la política anterior",
                    status_code=422,
                )
            un_dia = timedelta(days=1)
            if anterior.vigente_hasta is None or anterior.vigente_hasta >= nueva_vigente_desde:
                anterior.vigente_hasta = nueva_vigente_desde - un_dia
            anterior.estado = "CERRADA"
            anterior.cerrada_por = ctx.user_id
            anterior.cerrada_en = ahora
            anterior.motivo_cierre = f"Sustituida por la versión {policy.numero_version}"
            anterior.version += 1
            _historia(db, ctx, anterior, "CERRADA")
            _auditar_politica(
                db,
                ctx,
                "GOV_PAYMENT_POLICY_CLOSED",
                anterior,
                after={"codigo": anterior.codigo, "motivo": anterior.motivo_cierre, "numero_version": anterior.numero_version},
            )
    policy.fundamento = fundamento
    policy.act_id = act_id
    policy.estado = "VIGENTE"
    policy.activada_por = ctx.user_id
    policy.activada_en = ahora
    policy.vigente_desde = nueva_vigente_desde
    policy.version += 1
    for banda, normalizada in zip(bandas, bandas_normalizadas, strict=True):
        banda.monto_desde = normalizada["monto_desde"]
        banda.monto_hasta = normalizada["monto_hasta"]
        banda.requisitos = normalizada["requisitos"]
    _historia(db, ctx, policy, "ACTIVADA")
    _auditar_politica(db, ctx, "GOV_PAYMENT_POLICY_ACTIVATED", policy)
    db.flush()
    return _politica_a_dict(db, ctx, policy)


def cerrar_politica_pago(
    db: Session,
    ctx: CompanyContext,
    policy_id: str,
    cuerpo: dict[str, Any],
    version: int | None,
) -> dict[str, Any]:
    if version is None:
        raise KontrolError(
            code="GOV_PAYMENT_POLICY_IF_MATCH_REQUIRED",
            message="Se requiere la versión de la política de pago",
            status_code=428,
        )
    policy = politica_pago_de_empresa(db, ctx, policy_id, bloquear=True)
    if policy.estado != "VIGENTE":
        raise ConflictError(
            "GOV_PAYMENT_POLICY_NOT_ACTIVE",
            "Solo las políticas vigentes pueden cerrarse",
        )
    if policy.version != version:
        raise ConflictError(
            "GOV_PAYMENT_POLICY_VERSION_CONFLICT",
            "La política de pago fue cambiada por otro usuario",
            details={"version_actual": policy.version},
        )
    motivo = cuerpo.get("motivo")
    if not isinstance(motivo, str) or not motivo.strip():
        raise KontrolError(
            code="GOV_PAYMENT_POLICY_INVALID",
            message="motivo es obligatorio para cerrar",
            status_code=422,
        )
    policy.estado = "CERRADA"
    policy.cerrada_por = ctx.user_id
    policy.cerrada_en = instante_actual()
    policy.motivo_cierre = motivo
    policy.version += 1
    _historia(db, ctx, policy, "CERRADA")
    _auditar_politica(
        db,
        ctx,
        "GOV_PAYMENT_POLICY_CLOSED",
        policy,
        after={"codigo": policy.codigo, "motivo": motivo, "numero_version": policy.numero_version},
    )
    db.flush()
    return _politica_a_dict(db, ctx, policy)


def nueva_version_politica_pago(
    db: Session,
    ctx: CompanyContext,
    policy_id: str,
) -> dict[str, Any]:
    fuente = politica_pago_de_empresa(db, ctx, policy_id, bloquear=True)
    if fuente.estado not in ("VIGENTE", "CERRADA"):
        raise ConflictError(
            "GOV_PAYMENT_POLICY_NOT_VERSIONABLE",
            "Solo las políticas vigentes o cerradas pueden versionarse",
        )
    existente_borrador = db.scalar(
        select(GovernmentPaymentPolicy).where(
            GovernmentPaymentPolicy.company_id == ctx.company_id,
            GovernmentPaymentPolicy.codigo == fuente.codigo,
            GovernmentPaymentPolicy.estado == "BORRADOR",
        )
    )
    if existente_borrador is not None:
        raise ConflictError(
            "GOV_PAYMENT_POLICY_DRAFT_EXISTS",
            "Ya existe un borrador para este código de política",
        )
    maximo = db.scalar(
        select(func.max(GovernmentPaymentPolicy.numero_version)).where(
            GovernmentPaymentPolicy.company_id == ctx.company_id,
            GovernmentPaymentPolicy.codigo == fuente.codigo,
        )
    )
    numero_version = int(maximo) + 1 if maximo is not None else 1
    nueva = GovernmentPaymentPolicy(
        company_id=ctx.company_id,
        codigo=fuente.codigo,
        numero_version=numero_version,
        nombre=fuente.nombre,
        descripcion=fuente.descripcion,
        moneda=fuente.moneda,
        permite_pago_parcial=fuente.permite_pago_parcial,
        preparador_competencia_accion=fuente.preparador_competencia_accion,
        preparador_competencia_materia=fuente.preparador_competencia_materia,
        exige_cargo_autorizado_cuenta=fuente.exige_cargo_autorizado_cuenta,
        control_duplicado=fuente.control_duplicado,
        vigente_desde=fuente.vigente_desde,
        vigente_hasta=fuente.vigente_hasta,
        fundamento=fuente.fundamento,
        act_id=fuente.act_id,
        tipo_regla=fuente.tipo_regla,
        estado="BORRADOR",
        version_anterior_id=str(fuente.id),
        created_by=ctx.user_id,
    )
    db.add(nueva)
    db.flush()
    for metodo in db.scalars(
        select(GovernmentPaymentPolicyMethod).where(
            GovernmentPaymentPolicyMethod.company_id == ctx.company_id,
            GovernmentPaymentPolicyMethod.policy_id == str(fuente.id),
        )
    ):
        db.add(
            GovernmentPaymentPolicyMethod(
                policy_id=str(nueva.id),
                company_id=ctx.company_id,
                method_id=metodo.method_id,
                created_by=ctx.user_id,
            )
        )
        db.flush()
    for banda in db.scalars(
        select(GovernmentPaymentPolicyBand).where(
            GovernmentPaymentPolicyBand.company_id == ctx.company_id,
            GovernmentPaymentPolicyBand.policy_id == str(fuente.id),
        )
    ):
        db.add(
            GovernmentPaymentPolicyBand(
                policy_id=str(nueva.id),
                company_id=ctx.company_id,
                orden=banda.orden,
                monto_desde=banda.monto_desde,
                monto_hasta=banda.monto_hasta,
                requisitos=banda.requisitos,
                created_by=ctx.user_id,
            )
        )
        db.flush()
    for documento in db.scalars(
        select(GovernmentPaymentPolicyDocument).where(
            GovernmentPaymentPolicyDocument.company_id == ctx.company_id,
            GovernmentPaymentPolicyDocument.policy_id == str(fuente.id),
        )
    ):
        db.add(
            GovernmentPaymentPolicyDocument(
                policy_id=str(nueva.id),
                company_id=ctx.company_id,
                document_type_id=documento.document_type_id,
                etapa=documento.etapa,
                obligatorio=documento.obligatorio,
                created_by=ctx.user_id,
            )
        )
    _historia(db, ctx, nueva, "VERSIONADA")
    _auditar_politica(
        db,
        ctx,
        "GOV_PAYMENT_POLICY_VERSIONED",
        nueva,
        after={"codigo": nueva.codigo, "version_anterior": fuente.numero_version},
    )
    db.flush()
    return _politica_a_dict(db, ctx, nueva)


def politica_pago_vigente_en(
    policy: GovernmentPaymentPolicy,
    fecha: date,
) -> bool:
    if policy.estado != "VIGENTE":
        return False
    if policy.vigente_desde is not None and policy.vigente_desde > fecha:
        return False
    if policy.vigente_hasta is not None and policy.vigente_hasta < fecha:
        return False
    return True
