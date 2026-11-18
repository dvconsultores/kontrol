"""Servicio de políticas y configuración de la orden de pago (TRE-03, parte 1).

Numeración, configuración del patrón y ciclo de vida de las políticas de orden
de pago aplicables a los causados formalizados. Se comporta como BUD-09, pero
sin disparador documental: las políticas pueden no exigir documentos.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext
from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.documents.models import DocumentType
from app.modules.government.models import (
    ACCIONES_COMPETENCIA,
    ETAPAS_DOCUMENTO_ORDEN_PAGO,
    MATERIAS_COMPETENCIA,
    TIPOS_REGLA_ORDEN_PAGO,
    GovernmentAct,
    GovernmentPaymentOrder,
    GovernmentPaymentOrderPolicy,
    GovernmentPaymentOrderPolicyDocument,
    GovernmentPaymentOrderPolicyHistory,
    GovernmentPaymentOrderSettings,
)
from app.modules.government.service_presupuesto_causado import (
    PATRON_DEFECTO,
    _patron_invalido,
    _render_patron,
    _validar_patron,
)
from app.modules.identity_access.models import User
from app.shared.audit import record_audit
from app.shared.clock import hoy_de_negocio, instante_actual


def _patron_actual(db: Session, ctx: CompanyContext) -> GovernmentPaymentOrderSettings:
    fila = db.scalar(
        select(GovernmentPaymentOrderSettings).where(
            GovernmentPaymentOrderSettings.company_id == ctx.company_id
        )
    )
    if fila is None:
        fila = GovernmentPaymentOrderSettings(
            company_id=ctx.company_id,
            patron=PATRON_DEFECTO,
            version=0,
        )
    return fila


def configuracion_actual(db: Session, ctx: CompanyContext) -> dict[str, Any]:
    fila = _patron_actual(db, ctx)
    return {
        "patron": fila.patron,
        "ejemplo": _render_patron(fila.patron, hoy_de_negocio().year, 1),
        "version": fila.version,
        "configurado": fila.version > 0,
    }


def actualizar_configuracion(
    db: Session,
    ctx: CompanyContext,
    cuerpo: dict[str, Any],
    version: int | None,
) -> dict[str, Any]:
    if version is None:
        raise KontrolError(
            code="GOV_PAYMENT_ORDER_SETTINGS_IF_MATCH_REQUIRED",
            message="Se requiere la versión de la configuración",
            status_code=428,
        )
    patron = cuerpo.get("patron")
    if not isinstance(patron, str):
        raise _patron_invalido("El patron es obligatorio y debe ser texto")
    _validar_patron(patron)
    fila = db.scalar(
        select(GovernmentPaymentOrderSettings).where(
            GovernmentPaymentOrderSettings.company_id == ctx.company_id
        )
    )
    if fila is None:
        if version != 0:
            raise ConflictError(
                "GOV_PAYMENT_ORDER_SETTINGS_STALE",
                "La configuración fue cambiada por otro usuario",
            )
        fila = GovernmentPaymentOrderSettings(
            company_id=ctx.company_id,
            patron=patron,
            version=1,
        )
        db.add(fila)
    else:
        if fila.version != version:
            raise ConflictError(
                "GOV_PAYMENT_ORDER_SETTINGS_STALE",
                "La configuración fue cambiada por otro usuario",
                details={"version_actual": fila.version},
            )
        fila.patron = patron
        fila.version += 1
    record_audit(
        db,
        action="GOV_PAYMENT_ORDER_SETTINGS_UPDATED",
        entity_type="GovernmentPaymentOrderSettings",
        entity_id=str(fila.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={"patron": patron},
    )
    db.flush()
    return configuracion_actual(db, ctx)


def politica_de_empresa(db: Session, ctx: CompanyContext, policy_id: str) -> GovernmentPaymentOrderPolicy:
    politica = db.scalar(
        select(GovernmentPaymentOrderPolicy).where(
            GovernmentPaymentOrderPolicy.company_id == ctx.company_id,
            GovernmentPaymentOrderPolicy.id == policy_id,
        )
    )
    if politica is None:
        raise NotFoundError(
            "GOV_PAYMENT_ORDER_POLICY_NOT_FOUND",
            "Política de orden de pago no encontrada",
        )
    return politica


def documentos_de_politica(db: Session, policy_id: str) -> list[GovernmentPaymentOrderPolicyDocument]:
    return list(
        db.scalars(
            select(GovernmentPaymentOrderPolicyDocument).where(
                GovernmentPaymentOrderPolicyDocument.policy_id == policy_id
            )
        )
    )


def _historia_politica(db: Session, policy_id: str) -> list[GovernmentPaymentOrderPolicyHistory]:
    return list(
        db.scalars(
            select(GovernmentPaymentOrderPolicyHistory)
            .where(GovernmentPaymentOrderPolicyHistory.policy_id == policy_id)
            .order_by(GovernmentPaymentOrderPolicyHistory.created_at.desc())
        )
    )


def _acto_etiqueta(db: Session, act_id: str | None) -> str | None:
    if act_id is None:
        return None
    acto = db.get(GovernmentAct, act_id)
    if acto is None:
        return None
    return f"{acto.tipo} {acto.numero}"


def _etiqueta_tipo_documental(code: str, name: str) -> str:
    return f"{code} {name}".strip()


def _politica_a_dict(
    db: Session,
    ctx: CompanyContext,
    politica: GovernmentPaymentOrderPolicy,
    incluir_historia: bool,
) -> dict[str, Any]:
    documentos = []
    for documento in documentos_de_politica(db, str(politica.id)):
        tipo_documental = db.get(DocumentType, documento.document_type_id)
        etiqueta = None
        if tipo_documental is not None:
            etiqueta = _etiqueta_tipo_documental(tipo_documental.code, tipo_documental.name)
        documentos.append(
            {
                "id": str(documento.id),
                "document_type_id": documento.document_type_id,
                "tipo": etiqueta,
                "obligatorio": documento.obligatorio,
                "etapa": documento.etapa,
                "condicion": documento.condicion,
            }
        )
    resultado: dict[str, Any] = {
        "id": str(politica.id),
        "codigo": politica.codigo,
        "nombre": politica.nombre,
        "descripcion": politica.descripcion,
        "tipo_gasto": politica.tipo_gasto,
        "requiere_expediente_completo": politica.requiere_expediente_completo,
        "competencia_accion": politica.competencia_accion,
        "competencia_materia": politica.competencia_materia,
        "vigente_desde": politica.vigente_desde.isoformat(),
        "vigente_hasta": politica.vigente_hasta.isoformat() if politica.vigente_hasta else None,
        "fundamento": politica.fundamento,
        "act_id": politica.act_id,
        "acto": _acto_etiqueta(db, politica.act_id),
        "tipo_regla": politica.tipo_regla,
        "estado": politica.estado,
        "version": politica.version,
        "activada_en": politica.activada_en.isoformat() if politica.activada_en else None,
        "cerrada_en": politica.cerrada_en.isoformat() if politica.cerrada_en else None,
        "motivo_cierre": politica.motivo_cierre,
        "documentos": documentos,
    }
    if incluir_historia:
        historia = []
        for item in _historia_politica(db, str(politica.id)):
            actor = None
            if item.actor_id is not None:
                usuario = db.get(User, item.actor_id)
                actor = usuario.username if usuario is not None else None
            historia.append(
                {
                    "evento": item.evento,
                    "version": item.version,
                    "fecha": item.created_at.isoformat(),
                    "actor": actor,
                }
            )
        resultado["historia"] = historia
    return resultado


def _validar_documentos_politica(
    db: Session,
    ctx: CompanyContext,
    documentos: Any,
) -> list[dict[str, Any]]:
    if documentos is None:
        return []
    if not isinstance(documentos, list):
        raise KontrolError(
            code="GOV_PAYMENT_ORDER_POLICY_INVALID",
            message="documentos debe ser una lista",
            status_code=422,
        )
    tipos: set[str] = set()
    resultado: list[dict[str, Any]] = []
    for documento in documentos:
        if not isinstance(documento, dict):
            raise KontrolError(
                code="GOV_PAYMENT_ORDER_POLICY_INVALID",
                message="documentos contiene elementos inválidos",
                status_code=422,
            )
        document_type_id = documento.get("document_type_id")
        if not isinstance(document_type_id, str):
            raise KontrolError(
                code="GOV_PAYMENT_ORDER_POLICY_INVALID",
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
                code="GOV_PAYMENT_ORDER_POLICY_INVALID",
                message="document_type_id no corresponde a un tipo documental activo",
                status_code=422,
            )
        if document_type_id in tipos:
            raise KontrolError(
                code="GOV_PAYMENT_ORDER_POLICY_INVALID",
                message="document_type_id repetido en documentos",
                status_code=422,
            )
        tipos.add(document_type_id)
        etapa = documento.get("etapa", "EMISION")
        if etapa not in ETAPAS_DOCUMENTO_ORDEN_PAGO:
            raise KontrolError(
                code="GOV_PAYMENT_ORDER_POLICY_INVALID",
                message="etapa inválida para documento de política de orden de pago",
                status_code=422,
            )
        condicion = documento.get("condicion")
        if condicion is not None:
            if not isinstance(condicion, str) or len(condicion) > 300:
                raise KontrolError(
                    code="GOV_PAYMENT_ORDER_POLICY_INVALID",
                    message="condicion debe ser texto de hasta 300 caracteres",
                    status_code=422,
                )
        resultado.append(
            {
                "document_type_id": document_type_id,
                "obligatorio": bool(documento.get("obligatorio", True)),
                "etapa": etapa,
                "condicion": condicion,
            }
        )
    return resultado


def _validar_act_id(db: Session, ctx: CompanyContext, act_id: Any) -> str | None:
    if act_id is None:
        return None
    if not isinstance(act_id, str):
        raise KontrolError(
            code="GOV_PAYMENT_ORDER_POLICY_INVALID",
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
            code="GOV_PAYMENT_ORDER_POLICY_INVALID",
            message="act_id no corresponde a un acto de la empresa",
            status_code=422,
        )
    return act_id


def _validar_competencias(cuerpo: dict[str, Any]) -> None:
    competencia_accion = cuerpo.get("competencia_accion", "ORDENAR_PAGO")
    competencia_materia = cuerpo.get("competencia_materia", "TESORERIA")
    if competencia_accion not in ACCIONES_COMPETENCIA:
        raise KontrolError(
            code="GOV_PAYMENT_ORDER_POLICY_INVALID",
            message="competencia_accion inválida",
            status_code=422,
        )
    if competencia_materia not in MATERIAS_COMPETENCIA:
        raise KontrolError(
            code="GOV_PAYMENT_ORDER_POLICY_INVALID",
            message="competencia_materia inválida",
            status_code=422,
        )


def _validar_tipo_regla(tipo_regla: Any) -> str:
    if tipo_regla not in TIPOS_REGLA_ORDEN_PAGO:
        raise KontrolError(
            code="GOV_PAYMENT_ORDER_POLICY_INVALID",
            message="tipo_regla inválida",
            status_code=422,
        )
    return tipo_regla


def _validar_vigencia(vigente_desde: Any, vigente_hasta: Any) -> None:
    if isinstance(vigente_desde, date) and isinstance(vigente_hasta, date) and vigente_hasta < vigente_desde:
        raise KontrolError(
            code="GOV_PAYMENT_ORDER_POLICY_INVALID",
            message="vigente_hasta no puede ser anterior a vigente_desde",
            status_code=422,
        )


def crear_politica(db: Session, ctx: CompanyContext, cuerpo: dict[str, Any]) -> dict[str, Any]:
    codigo = cuerpo.get("codigo")
    if not isinstance(codigo, str):
        raise KontrolError(
            code="GOV_PAYMENT_ORDER_POLICY_INVALID",
            message="El codigo es obligatorio",
            status_code=422,
        )
    existente = db.scalar(
        select(GovernmentPaymentOrderPolicy).where(
            GovernmentPaymentOrderPolicy.company_id == ctx.company_id,
            GovernmentPaymentOrderPolicy.codigo == codigo,
        )
    )
    if existente is not None:
        raise ConflictError(
            "GOV_PAYMENT_ORDER_POLICY_CODE_TAKEN",
            "Ya existe una política de orden de pago con ese código",
        )
    _validar_competencias(cuerpo)
    _validar_tipo_regla(cuerpo.get("tipo_regla", "INSTITUTIONAL_POLICY"))
    _validar_vigencia(cuerpo.get("vigente_desde"), cuerpo.get("vigente_hasta"))
    _validar_act_id(db, ctx, cuerpo.get("act_id"))
    documentos = _validar_documentos_politica(db, ctx, cuerpo.get("documentos") or [])
    politica = GovernmentPaymentOrderPolicy(
        company_id=ctx.company_id,
        codigo=codigo,
        nombre=cuerpo["nombre"],
        descripcion=cuerpo.get("descripcion"),
        tipo_gasto=cuerpo.get("tipo_gasto"),
        requiere_expediente_completo=cuerpo.get("requiere_expediente_completo", False),
        competencia_accion=cuerpo.get("competencia_accion", "ORDENAR_PAGO"),
        competencia_materia=cuerpo.get("competencia_materia", "TESORERIA"),
        vigente_desde=cuerpo["vigente_desde"],
        vigente_hasta=cuerpo.get("vigente_hasta"),
        fundamento=cuerpo.get("fundamento"),
        act_id=cuerpo.get("act_id"),
        tipo_regla=cuerpo.get("tipo_regla", "INSTITUTIONAL_POLICY"),
        estado="BORRADOR",
    )
    db.add(politica)
    db.flush()
    for documento in documentos:
        db.add(
            GovernmentPaymentOrderPolicyDocument(
                policy_id=str(politica.id),
                company_id=ctx.company_id,
                document_type_id=documento["document_type_id"],
                obligatorio=documento["obligatorio"],
                etapa=documento["etapa"],
                condicion=documento["condicion"],
            )
        )
    db.add(
        GovernmentPaymentOrderPolicyHistory(
            policy_id=str(politica.id),
            company_id=ctx.company_id,
            evento="CREADA",
            version=politica.version,
            instantanea=_politica_a_dict(db, ctx, politica, incluir_historia=False),
            actor_id=ctx.user_id,
        )
    )
    record_audit(
        db,
        action="GOV_PAYMENT_ORDER_POLICY_CREATED",
        entity_type="GovernmentPaymentOrderPolicy",
        entity_id=str(politica.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={
            "codigo": politica.codigo,
            "nombre": politica.nombre,
            "tipo_gasto": politica.tipo_gasto,
        },
    )
    db.flush()
    return _politica_a_dict(db, ctx, politica, incluir_historia=True)


def actualizar_politica(
    db: Session,
    ctx: CompanyContext,
    policy_id: str,
    cuerpo: dict[str, Any],
    version: int | None,
) -> dict[str, Any]:
    if version is None:
        raise KontrolError(
            code="GOV_PAYMENT_ORDER_POLICY_IF_MATCH_REQUIRED",
            message="Se requiere la versión de la política",
            status_code=428,
        )
    politica = politica_de_empresa(db, ctx, policy_id)
    if politica.estado != "BORRADOR":
        raise ConflictError(
            "GOV_PAYMENT_ORDER_POLICY_NOT_DRAFT",
            "Solo las políticas en borrador pueden actualizarse",
        )
    if politica.version != version:
        raise ConflictError(
            "GOV_PAYMENT_ORDER_POLICY_STALE",
            "La política fue cambiada por otro usuario",
            details={"version_actual": politica.version},
        )
    _validar_competencias(cuerpo)
    if "tipo_regla" in cuerpo:
        _validar_tipo_regla(cuerpo.get("tipo_regla"))
    vigente_desde = cuerpo.get("vigente_desde", politica.vigente_desde)
    vigente_hasta = cuerpo.get("vigente_hasta", politica.vigente_hasta)
    _validar_vigencia(vigente_desde, vigente_hasta)
    act_id = _validar_act_id(db, ctx, cuerpo.get("act_id", politica.act_id))
    documentos: list[dict[str, Any]] | None = None
    if "documentos" in cuerpo:
        documentos = _validar_documentos_politica(db, ctx, cuerpo.get("documentos"))
    for clave, valor in cuerpo.items():
        if clave != "documentos":
            setattr(politica, clave, valor)
    politica.act_id = act_id
    politica.version += 1
    if documentos is not None:
        for existente in documentos_de_politica(db, str(politica.id)):
            db.delete(existente)
        db.flush()
        for documento in documentos:
            db.add(
                GovernmentPaymentOrderPolicyDocument(
                    policy_id=str(politica.id),
                    company_id=ctx.company_id,
                    document_type_id=documento["document_type_id"],
                    obligatorio=documento["obligatorio"],
                    etapa=documento["etapa"],
                    condicion=documento["condicion"],
                )
            )
    db.add(
        GovernmentPaymentOrderPolicyHistory(
            policy_id=str(politica.id),
            company_id=ctx.company_id,
            evento="ACTUALIZADA",
            version=politica.version,
            instantanea=_politica_a_dict(db, ctx, politica, incluir_historia=False),
            actor_id=ctx.user_id,
        )
    )
    record_audit(
        db,
        action="GOV_PAYMENT_ORDER_POLICY_UPDATED",
        entity_type="GovernmentPaymentOrderPolicy",
        entity_id=str(politica.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={"codigo": politica.codigo, "version": politica.version},
    )
    db.flush()
    return _politica_a_dict(db, ctx, politica, incluir_historia=True)


def activar_politica(
    db: Session,
    ctx: CompanyContext,
    policy_id: str,
    cuerpo: dict[str, Any],
    version: int | None,
) -> dict[str, Any]:
    if version is None:
        raise KontrolError(
            code="GOV_PAYMENT_ORDER_POLICY_IF_MATCH_REQUIRED",
            message="Se requiere la versión de la política",
            status_code=428,
        )
    politica = politica_de_empresa(db, ctx, policy_id)
    if politica.estado != "BORRADOR":
        raise ConflictError(
            "GOV_PAYMENT_ORDER_POLICY_NOT_DRAFT",
            "Solo las políticas en borrador pueden activarse",
        )
    if politica.version != version:
        raise ConflictError(
            "GOV_PAYMENT_ORDER_POLICY_STALE",
            "La política fue cambiada por otro usuario",
            details={"version_actual": politica.version},
        )
    fundamento = cuerpo.get("fundamento")
    if not isinstance(fundamento, str) or not 20 <= len(fundamento) <= 2000:
        raise KontrolError(
            code="GOV_PAYMENT_ORDER_POLICY_INVALID",
            message="El fundamento es obligatorio y debe tener entre 20 y 2000 caracteres",
            status_code=422,
        )
    act_id = _validar_act_id(db, ctx, cuerpo.get("act_id", politica.act_id))
    politica.estado = "VIGENTE"
    politica.fundamento = fundamento
    politica.act_id = act_id
    politica.activada_por = ctx.user_id
    politica.activada_en = instante_actual()
    politica.version += 1
    db.add(
        GovernmentPaymentOrderPolicyHistory(
            policy_id=str(politica.id),
            company_id=ctx.company_id,
            evento="ACTIVADA",
            version=politica.version,
            instantanea=_politica_a_dict(db, ctx, politica, incluir_historia=False),
            actor_id=ctx.user_id,
        )
    )
    record_audit(
        db,
        action="GOV_PAYMENT_ORDER_POLICY_ACTIVATED",
        entity_type="GovernmentPaymentOrderPolicy",
        entity_id=str(politica.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={
            "codigo": politica.codigo,
            "fundamento": politica.fundamento,
            "version": politica.version,
            "vigente_desde": politica.vigente_desde.isoformat(),
        },
    )
    db.flush()
    return _politica_a_dict(db, ctx, politica, incluir_historia=True)


def cerrar_politica(
    db: Session,
    ctx: CompanyContext,
    policy_id: str,
    cuerpo: dict[str, Any],
    version: int | None,
) -> dict[str, Any]:
    if version is None:
        raise KontrolError(
            code="GOV_PAYMENT_ORDER_POLICY_IF_MATCH_REQUIRED",
            message="Se requiere la versión de la política",
            status_code=428,
        )
    politica = politica_de_empresa(db, ctx, policy_id)
    if politica.estado != "VIGENTE":
        raise ConflictError(
            "GOV_PAYMENT_ORDER_POLICY_NOT_ACTIVE",
            "Solo las políticas vigentes pueden cerrarse",
        )
    if politica.version != version:
        raise ConflictError(
            "GOV_PAYMENT_ORDER_POLICY_STALE",
            "La política fue cambiada por otro usuario",
            details={"version_actual": politica.version},
        )
    motivo = cuerpo.get("motivo")
    if not isinstance(motivo, str) or not 10 <= len(motivo) <= 500:
        raise KontrolError(
            code="GOV_PAYMENT_ORDER_POLICY_INVALID",
            message="El motivo es obligatorio y debe tener entre 10 y 500 caracteres",
            status_code=422,
        )
    politica.estado = "CERRADA"
    politica.cerrada_por = ctx.user_id
    politica.cerrada_en = instante_actual()
    politica.motivo_cierre = motivo
    politica.version += 1
    db.add(
        GovernmentPaymentOrderPolicyHistory(
            policy_id=str(politica.id),
            company_id=ctx.company_id,
            evento="CERRADA",
            version=politica.version,
            instantanea=_politica_a_dict(db, ctx, politica, incluir_historia=False),
            actor_id=ctx.user_id,
        )
    )
    record_audit(
        db,
        action="GOV_PAYMENT_ORDER_POLICY_CLOSED",
        entity_type="GovernmentPaymentOrderPolicy",
        entity_id=str(politica.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={"codigo": politica.codigo, "motivo": politica.motivo_cierre, "version": politica.version},
    )
    db.flush()
    return _politica_a_dict(db, ctx, politica, incluir_historia=True)


def listar_politicas(db: Session, ctx: CompanyContext) -> list[dict[str, Any]]:
    politicas = db.scalars(
        select(GovernmentPaymentOrderPolicy)
        .where(GovernmentPaymentOrderPolicy.company_id == ctx.company_id)
        .order_by(GovernmentPaymentOrderPolicy.created_at.desc())
    ).all()
    return [_politica_a_dict(db, ctx, p, incluir_historia=True) for p in politicas]


def obtener_politica(db: Session, ctx: CompanyContext, policy_id: str) -> dict[str, Any]:
    return _politica_a_dict(db, ctx, politica_de_empresa(db, ctx, policy_id), incluir_historia=True)


def politica_vigente_en(politica: GovernmentPaymentOrderPolicy, fecha: date) -> bool:
    if politica.estado != "VIGENTE":
        return False
    if politica.vigente_desde > fecha:
        return False
    if politica.vigente_hasta is not None and politica.vigente_hasta < fecha:
        return False
    return True


def siguiente_codigo(
    db: Session,
    ctx: CompanyContext,
    anio: int,
    year_id: str,
) -> tuple[int, str]:
    maximo = db.scalar(
        select(func.max(GovernmentPaymentOrder.numero)).where(
            GovernmentPaymentOrder.company_id == ctx.company_id,
            GovernmentPaymentOrder.year_id == year_id,
        )
    )
    siguiente = 1 if maximo is None else int(maximo) + 1
    fila = _patron_actual(db, ctx)
    codigo = _render_patron(fila.patron, anio, siguiente)
    return siguiente, codigo
