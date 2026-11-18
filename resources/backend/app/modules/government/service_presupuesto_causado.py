"""Servicio del causado presupuestario (BUD-09, GOV-BUD-013).

Frontera ACC-02: la instantánea lleva partida, categoría y fuente por línea;
no hay asiento, cuentas ni mapeo contable.
N36/ONCOP pendiente: ACCOUNTING_ENTRY fuera de alcance.
"""

from __future__ import annotations

import csv
import io
import json
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext
from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.core.integrity import es_violacion_unica
from app.modules.documents.models import Document, DocumentLink, DocumentType, DocumentVersion
from app.modules.government.models import (
    GovernmentAct,
    GovernmentBudgetCategory,
    GovernmentBudgetCause,
    GovernmentBudgetCauseEvidence,
    GovernmentBudgetCauseHistory,
    GovernmentBudgetCauseLine,
    GovernmentBudgetCauseSettings,
    GovernmentBudgetCausingPolicy,
    GovernmentBudgetCausingPolicyDocument,
    GovernmentBudgetCausingPolicyHistory,
    GovernmentBudgetClassifierItem,
    GovernmentBudgetCommitment,
    GovernmentBudgetCommitmentLine,
    GovernmentBudgetCredit,
    GovernmentBudgetFundingSource,
    GovernmentBudgetYear,
    GovernmentContractBudgetAllocation,
    GovernmentContractDeliverableSubmission,
    GovernmentContractInvoice,
    GovernmentContractReceipt,
    GovernmentContractValuation,
    GovernmentOfficial,
    GovernmentPosition,
    GovernmentSoDRule,
    GovernmentUnit,
)
from app.modules.government.monedas import canonical_currency
from app.modules.government.proyeccion_obligaciones import montos_ordenados, ordenes_emitidas_de_causa, pendiente_de_ordenar
from app.modules.government.service_actos import _autoridad_valida
from app.modules.government.service_autoridad import competencias_en_vigor
from app.modules.government.service_identidad import (
    _funcionario_del_actor,
    exigir_autoridad_funcional,
)
from app.modules.government.service_presupuesto import (
    _ejercicio_de_empresa,
    _estado_invalido,
    _invalida,
)
from app.modules.government.service_presupuesto_certificacion import (
    _decimal_finito,
    _etiqueta,
)
from app.modules.government.service_sod import (
    evaluar_antes_de_actuar,
    usuarios_equivalentes,
)
from app.modules.government.service_tasas import verificar_limite
from app.modules.identity_access.models import User
from app.shared.audit import record_audit
from app.shared.clock import hoy_de_negocio, instante_actual

ACCIONES_COMPETENCIA = ("SOLICITAR", "COMPROMETER", "CAUSAR", "ORDENAR_PAGO", "PAGAR", "REGISTRAR", "CUSTODIAR", "APROBAR", "AUDITAR", "FIRMAR")
MATERIAS_COMPETENCIA = ("PRESUPUESTO", "CONTRATACIONES", "TESORERIA", "CONTABILIDAD", "BIENES", "EXPEDIENTE")
PATRON_DEFECTO = "{ANIO}-{NUMERO:5}"


def _patron_actual(db: Session, ctx: CompanyContext) -> GovernmentBudgetCauseSettings:
    fila = db.scalar(
        select(GovernmentBudgetCauseSettings).where(
            GovernmentBudgetCauseSettings.company_id == ctx.company_id
        )
    )
    if fila is None:
        fila = GovernmentBudgetCauseSettings(
            company_id=ctx.company_id,
            patron=PATRON_DEFECTO,
            version=0,
        )
    return fila


def _validar_patron(patron: str) -> None:
    if not 9 <= len(patron) <= 60:
        raise _patron_invalido("La longitud debe estar entre 9 y 60 caracteres")
    if patron.count("{ANIO}") > 1:
        raise _patron_invalido("El marcador {ANIO} puede aparecer como máximo una vez")
    if patron.count("{NUMERO:") != 1:
        raise _patron_invalido("Debe existir exactamente un marcador {NUMERO:n}")
    import re

    marcador_numero = re.search(r"\{NUMERO:(\d+)\}", patron)
    if marcador_numero is None:
        raise _patron_invalido("El marcador {NUMERO:n} no es válido")
    n = int(marcador_numero.group(1))
    if not 3 <= n <= 8:
        raise _patron_invalido("El valor n de {NUMERO:n} debe estar entre 3 y 8")
    resto = re.sub(r"\{ANIO\}", "", patron)
    resto = re.sub(r"\{NUMERO:\d+\}", "", resto)
    if not re.fullmatch(r"[A-Za-z0-9/._-]*", resto):
        raise _patron_invalido("Solo se admiten literales [A-Za-z0-9/._-] y los marcadores")


def _patron_invalido(mensaje: str) -> KontrolError:
    return KontrolError(
        code="GOV_BUDGET_CAUSE_PATTERN_INVALID",
        message=mensaje,
        status_code=422,
    )


def _render_patron(patron: str, anio: int, numero: int) -> str:
    import re

    def reemplazar(match: re.Match[str]) -> str:
        cantidad = int(match.group(1))
        return str(numero).zfill(cantidad)

    resultado = patron.replace("{ANIO}", str(anio))
    resultado = re.sub(r"\{NUMERO:(\d+)\}", reemplazar, resultado)
    return resultado


def _configuracion_actual(db: Session, ctx: CompanyContext) -> dict[str, Any]:
    fila = _patron_actual(db, ctx)
    return {
        "patron": fila.patron,
        "ejemplo": _render_patron(fila.patron, hoy_de_negocio().year, 1),
        "version": fila.version,
        "configurado": fila.version > 0,
    }


def _actualizar_configuracion(
    db: Session,
    ctx: CompanyContext,
    cuerpo: dict[str, Any],
    version: int | None,
) -> dict[str, Any]:
    if version is None:
        raise KontrolError(
            "GOV_BUDGET_CAUSE_IF_MATCH_REQUIRED",
            "Se requiere la versión de la configuración",
            status_code=428,
        )
    patron = cuerpo.get("patron")
    if not isinstance(patron, str):
        raise _patron_invalido("El patron es obligatorio y debe ser texto")
    _validar_patron(patron)
    fila = db.scalar(
        select(GovernmentBudgetCauseSettings).where(
            GovernmentBudgetCauseSettings.company_id == ctx.company_id
        )
    )
    if fila is None:
        if version != 0:
            raise ConflictError(
                "GOV_BUDGET_CAUSE_SETTINGS_STALE",
                "La configuración fue cambiada por otro usuario",
            )
        fila = GovernmentBudgetCauseSettings(
            company_id=ctx.company_id,
            patron=patron,
            version=1,
        )
        db.add(fila)
    else:
        if fila.version != version:
            raise ConflictError(
                "GOV_BUDGET_CAUSE_SETTINGS_STALE",
                "La configuración fue cambiada por otro usuario",
                details={"version_actual": fila.version},
            )
        fila.patron = patron
        fila.version += 1
    record_audit(
        db,
        action="GOV_BUDGET_CAUSE_SETTINGS_UPDATED",
        entity_type="GovernmentBudgetCauseSettings",
        entity_id=str(fila.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={"patron": patron},
    )
    db.flush()
    return _configuracion_actual(db, ctx)


def _politica_por_id(db: Session, ctx: CompanyContext, policy_id: str) -> GovernmentBudgetCausingPolicy:
    politica = db.scalar(
        select(GovernmentBudgetCausingPolicy).where(
            GovernmentBudgetCausingPolicy.company_id == ctx.company_id,
            GovernmentBudgetCausingPolicy.id == policy_id,
        )
    )
    if politica is None:
        raise NotFoundError("GOV_BUDGET_CAUSING_POLICY_NOT_FOUND", "Política no encontrada")
    return politica


def _documentos_politica(db: Session, policy_id: str) -> list[GovernmentBudgetCausingPolicyDocument]:
    return list(
        db.scalars(
            select(GovernmentBudgetCausingPolicyDocument).where(
                GovernmentBudgetCausingPolicyDocument.policy_id == policy_id
            )
        )
    )


def _historia_politica(db: Session, policy_id: str) -> list[GovernmentBudgetCausingPolicyHistory]:
    return list(
        db.scalars(
            select(GovernmentBudgetCausingPolicyHistory)
            .where(GovernmentBudgetCausingPolicyHistory.policy_id == policy_id)
            .order_by(GovernmentBudgetCausingPolicyHistory.created_at.desc())
        )
    )


def _acto_etiqueta(db: Session, act_id: str | None) -> str | None:
    if act_id is None:
        return None
    acto = db.get(GovernmentAct, act_id)
    if acto is None:
        return None
    return f"{acto.tipo} {acto.numero}"


def _politica_a_dict(
    db: Session,
    ctx: CompanyContext,
    politica: GovernmentBudgetCausingPolicy,
    incluir_historia: bool,
) -> dict[str, Any]:
    documentos = []
    for documento in _documentos_politica(db, str(politica.id)):
        tipo_documental = db.get(DocumentType, documento.document_type_id)
        etiqueta = None
        if tipo_documental is not None:
            etiqueta = _etiqueta(tipo_documental.code, tipo_documental.name)
        documentos.append(
            {
                "id": str(documento.id),
                "document_type_id": documento.document_type_id,
                "tipo_documental": etiqueta,
                "obligatorio": documento.obligatorio,
                "etapa": documento.etapa,
                "condicion": documento.condicion,
            }
        )
    resultado: dict[str, Any] = {
        "id": str(politica.id),
        "codigo": politica.codigo,
        "tipo_gasto": politica.tipo_gasto,
        "nombre": politica.nombre,
        "descripcion": politica.descripcion,
        "disparador": politica.disparador,
        "requiere_recepcion": politica.requiere_recepcion,
        "requiere_valuacion": politica.requiere_valuacion,
        "requiere_conformidad": politica.requiere_conformidad,
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


def _validar_politica_create(db: Session, ctx: CompanyContext, cuerpo: dict[str, Any]) -> None:
    codigo = cuerpo.get("codigo")
    if not isinstance(codigo, str):
        raise _invalida("El codigo es obligatorio")
    existente = db.scalar(
        select(GovernmentBudgetCausingPolicy).where(
            GovernmentBudgetCausingPolicy.company_id == ctx.company_id,
            GovernmentBudgetCausingPolicy.codigo == codigo,
        )
    )
    if existente is not None:
        raise ConflictError(
            "GOV_BUDGET_CAUSING_POLICY_CODE_TAKEN",
            "Ya existe una política con ese código",
        )
    documentos = cuerpo.get("documentos") or []
    if "documentos" in cuerpo and not isinstance(documentos, list):
        raise _invalida("documentos debe ser una lista")
    tipos: set[str] = set()
    obligatorio = False
    for documento in documentos:
        if not isinstance(documento, dict):
            raise _invalida("documentos contiene elementos inválidos")
        document_type_id = documento.get("document_type_id")
        if not isinstance(document_type_id, str):
            raise _invalida("document_type_id es obligatorio")
        tipo = db.scalar(
            select(DocumentType).where(
                DocumentType.company_id == ctx.company_id,
                DocumentType.id == document_type_id,
                DocumentType.status == "ACTIVE",
            )
        )
        if tipo is None:
            raise _invalida("document_type_id no corresponde a un tipo documental activo")
        if document_type_id in tipos:
            raise _invalida("document_type_id repetido en documentos")
        tipos.add(document_type_id)
        if documento.get("obligatorio", True):
            obligatorio = True
    disparador = cuerpo.get("disparador")
    if disparador == "DOCUMENTARY" and len(documentos) > 0 and not obligatorio:
        raise _invalida("El disparador DOCUMENTARY requiere al menos un documento obligatorio")
    if disparador == "DOCUMENTARY" and len(documentos) == 0:
        raise _invalida("El disparador DOCUMENTARY requiere al menos un documento obligatorio")
    act_id = cuerpo.get("act_id")
    if act_id is not None:
        if not isinstance(act_id, str):
            raise _invalida("act_id debe ser texto")
        acto = db.scalar(
            select(GovernmentAct).where(
                GovernmentAct.company_id == ctx.company_id,
                GovernmentAct.id == act_id,
            )
        )
        if acto is None:
            raise _invalida("act_id no corresponde a un acto de la empresa")
    vigente_desde = cuerpo.get("vigente_desde")
    vigente_hasta = cuerpo.get("vigente_hasta")
    if isinstance(vigente_desde, date) and isinstance(vigente_hasta, date) and vigente_hasta < vigente_desde:
        raise _invalida("vigente_hasta no puede ser anterior a vigente_desde")


def _crear_politica(db: Session, ctx: CompanyContext, cuerpo: dict[str, Any]) -> dict[str, Any]:
    _validar_politica_create(db, ctx, cuerpo)
    politica = GovernmentBudgetCausingPolicy(
        company_id=ctx.company_id,
        codigo=cuerpo["codigo"],
        tipo_gasto=cuerpo["tipo_gasto"],
        nombre=cuerpo["nombre"],
        descripcion=cuerpo.get("descripcion"),
        disparador=cuerpo["disparador"],
        requiere_recepcion=cuerpo.get("requiere_recepcion", False),
        requiere_valuacion=cuerpo.get("requiere_valuacion", False),
        requiere_conformidad=cuerpo.get("requiere_conformidad", False),
        competencia_accion=cuerpo.get("competencia_accion", "CAUSAR"),
        competencia_materia=cuerpo.get("competencia_materia", "PRESUPUESTO"),
        vigente_desde=cuerpo["vigente_desde"],
        vigente_hasta=cuerpo.get("vigente_hasta"),
        fundamento=cuerpo.get("fundamento"),
        act_id=cuerpo.get("act_id"),
        tipo_regla=cuerpo.get("tipo_regla", "INSTITUTIONAL_POLICY"),
        estado="BORRADOR",
    )
    db.add(politica)
    db.flush()
    for documento in cuerpo.get("documentos") or []:
        db.add(
            GovernmentBudgetCausingPolicyDocument(
                policy_id=str(politica.id),
                company_id=ctx.company_id,
                document_type_id=documento["document_type_id"],
                obligatorio=documento.get("obligatorio", True),
                etapa=documento["etapa"],
                condicion=documento.get("condicion"),
            )
        )
    db.add(
        GovernmentBudgetCausingPolicyHistory(
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
        action="GOV_BUDGET_CAUSING_POLICY_CREATED",
        entity_type="GovernmentBudgetCausingPolicy",
        entity_id=str(politica.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={
            "codigo": politica.codigo,
            "disparador": politica.disparador,
            "tipo_gasto": politica.tipo_gasto,
        },
    )
    db.flush()
    return _politica_a_dict(db, ctx, politica, incluir_historia=True)


def _actualizar_politica(
    db: Session,
    ctx: CompanyContext,
    policy_id: str,
    version: int | None,
    cuerpo: dict[str, Any],
) -> dict[str, Any]:
    if version is None:
        raise KontrolError(
            "GOV_BUDGET_CAUSE_IF_MATCH_REQUIRED",
            "Se requiere la versión de la política",
            status_code=428,
        )
    politica = _politica_por_id(db, ctx, policy_id)
    if politica.estado != "BORRADOR":
        raise ConflictError(
            "GOV_BUDGET_CAUSING_POLICY_NOT_DRAFT",
            "Solo las políticas en borrador pueden actualizarse",
        )
    if politica.version != version:
        raise ConflictError(
            "GOV_BUDGET_CAUSING_POLICY_STALE",
            "La política fue cambiada por otro usuario",
            details={"version_actual": politica.version},
        )
    if "documentos" in cuerpo:
        documentos = cuerpo.get("documentos")
        if not isinstance(documentos, list):
            raise _invalida("documentos debe ser una lista")
        tipos: set[str] = set()
        obligatorio = False
        for documento in documentos:
            if not isinstance(documento, dict):
                raise _invalida("documentos contiene elementos inválidos")
            document_type_id = documento.get("document_type_id")
            if not isinstance(document_type_id, str):
                raise _invalida("document_type_id es obligatorio")
            tipo = db.scalar(
                select(DocumentType).where(
                    DocumentType.company_id == ctx.company_id,
                    DocumentType.id == document_type_id,
                    DocumentType.status == "ACTIVE",
                )
            )
            if tipo is None:
                raise _invalida("document_type_id no corresponde a un tipo documental activo")
            if document_type_id in tipos:
                raise _invalida("document_type_id repetido en documentos")
            tipos.add(document_type_id)
            if documento.get("obligatorio", True):
                obligatorio = True
        disparador = cuerpo.get("disparador", politica.disparador)
        if disparador == "DOCUMENTARY" and not obligatorio:
            raise _invalida("El disparador DOCUMENTARY requiere al menos un documento obligatorio")
    act_id = cuerpo.get("act_id", politica.act_id)
    if act_id is not None:
        acto = db.scalar(
            select(GovernmentAct).where(
                GovernmentAct.company_id == ctx.company_id,
                GovernmentAct.id == act_id,
            )
        )
        if acto is None:
            raise _invalida("act_id no corresponde a un acto de la empresa")
    vigente_desde = cuerpo.get("vigente_desde", politica.vigente_desde)
    vigente_hasta = cuerpo.get("vigente_hasta", politica.vigente_hasta)
    if isinstance(vigente_desde, date) and isinstance(vigente_hasta, date) and vigente_hasta < vigente_desde:
        raise _invalida("vigente_hasta no puede ser anterior a vigente_desde")
    for clave, valor in cuerpo.items():
        if clave != "documentos":
            setattr(politica, clave, valor)
    politica.version += 1
    if "documentos" in cuerpo:
        for documento in _documentos_politica(db, str(politica.id)):
            db.delete(documento)
        db.flush()
        for documento in cuerpo["documentos"]:
            db.add(
                GovernmentBudgetCausingPolicyDocument(
                    policy_id=str(politica.id),
                    company_id=ctx.company_id,
                    document_type_id=documento["document_type_id"],
                    obligatorio=documento.get("obligatorio", True),
                    etapa=documento["etapa"],
                    condicion=documento.get("condicion"),
                )
            )
    db.add(
        GovernmentBudgetCausingPolicyHistory(
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
        action="GOV_BUDGET_CAUSING_POLICY_UPDATED",
        entity_type="GovernmentBudgetCausingPolicy",
        entity_id=str(politica.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={"codigo": politica.codigo, "version": politica.version},
    )
    db.flush()
    return _politica_a_dict(db, ctx, politica, incluir_historia=True)


def _activar_politica(
    db: Session,
    ctx: CompanyContext,
    policy_id: str,
    version: int | None,
    cuerpo: dict[str, Any],
) -> dict[str, Any]:
    if version is None:
        raise KontrolError(
            "GOV_BUDGET_CAUSE_IF_MATCH_REQUIRED",
            "Se requiere la versión de la política",
            status_code=428,
        )
    politica = _politica_por_id(db, ctx, policy_id)
    if politica.estado != "BORRADOR":
        raise ConflictError(
            "GOV_BUDGET_CAUSING_POLICY_NOT_DRAFT",
            "Solo las políticas en borrador pueden activarse",
        )
    if politica.version != version:
        raise ConflictError(
            "GOV_BUDGET_CAUSING_POLICY_STALE",
            "La política fue cambiada por otro usuario",
            details={"version_actual": politica.version},
        )
    fundamento = cuerpo.get("fundamento")
    if not isinstance(fundamento, str) or not 20 <= len(fundamento) <= 2000:
        raise _invalida("El fundamento es obligatorio y debe tener entre 20 y 2000 caracteres")
    act_id = cuerpo.get("act_id", politica.act_id)
    if act_id is not None:
        acto = db.scalar(
            select(GovernmentAct).where(
                GovernmentAct.company_id == ctx.company_id,
                GovernmentAct.id == act_id,
            )
        )
        if acto is None:
            raise _invalida("act_id no corresponde a un acto de la empresa")
    solapada = db.scalar(
        select(GovernmentBudgetCausingPolicy).where(
            GovernmentBudgetCausingPolicy.company_id == ctx.company_id,
            GovernmentBudgetCausingPolicy.tipo_gasto == politica.tipo_gasto,
            GovernmentBudgetCausingPolicy.estado == "VIGENTE",
            GovernmentBudgetCausingPolicy.id != str(politica.id),
        )
    )
    if solapada is not None:
        desde_a = politica.vigente_desde
        hasta_a = politica.vigente_hasta
        desde_b = solapada.vigente_desde
        hasta_b = solapada.vigente_hasta
        if desde_a <= (hasta_b if hasta_b is not None else date.max) and desde_b <= (
            hasta_a if hasta_a is not None else date.max
        ):
            raise ConflictError(
                "GOV_BUDGET_CAUSING_POLICY_OVERLAP",
                "Ya existe una política vigente para el mismo tipo de gasto con vigencia solapada",
            )
    politica.estado = "VIGENTE"
    politica.fundamento = fundamento
    politica.act_id = act_id
    politica.activada_por = ctx.user_id
    politica.activada_en = instante_actual()
    politica.version += 1
    db.add(
        GovernmentBudgetCausingPolicyHistory(
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
        action="GOV_BUDGET_CAUSING_POLICY_ACTIVATED",
        entity_type="GovernmentBudgetCausingPolicy",
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


def _cerrar_politica(
    db: Session,
    ctx: CompanyContext,
    policy_id: str,
    version: int | None,
    cuerpo: dict[str, Any],
) -> dict[str, Any]:
    if version is None:
        raise KontrolError(
            "GOV_BUDGET_CAUSE_IF_MATCH_REQUIRED",
            "Se requiere la versión de la política",
            status_code=428,
        )
    politica = _politica_por_id(db, ctx, policy_id)
    if politica.estado != "VIGENTE":
        raise ConflictError(
            "GOV_BUDGET_CAUSING_POLICY_NOT_ACTIVE",
            "Solo las políticas vigentes pueden cerrarse",
        )
    if politica.version != version:
        raise ConflictError(
            "GOV_BUDGET_CAUSING_POLICY_STALE",
            "La política fue cambiada por otro usuario",
            details={"version_actual": politica.version},
        )
    motivo = cuerpo.get("motivo")
    if not isinstance(motivo, str) or not 10 <= len(motivo) <= 500:
        raise _invalida("El motivo es obligatorio y debe tener entre 10 y 500 caracteres")
    politica.estado = "CERRADA"
    politica.cerrada_por = ctx.user_id
    politica.cerrada_en = instante_actual()
    politica.motivo_cierre = motivo
    politica.version += 1
    db.add(
        GovernmentBudgetCausingPolicyHistory(
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
        action="GOV_BUDGET_CAUSING_POLICY_CLOSED",
        entity_type="GovernmentBudgetCausingPolicy",
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
        select(GovernmentBudgetCausingPolicy)
        .where(GovernmentBudgetCausingPolicy.company_id == ctx.company_id)
        .order_by(GovernmentBudgetCausingPolicy.created_at.desc())
    ).all()
    return [_politica_a_dict(db, ctx, p, incluir_historia=True) for p in politicas]


def _obtener_politica(db: Session, ctx: CompanyContext, policy_id: str) -> dict[str, Any]:
    return _politica_a_dict(db, ctx, _politica_por_id(db, ctx, policy_id), incluir_historia=True)


def _lineas_compromiso(db: Session, commitment_id: str) -> list[GovernmentBudgetCommitmentLine]:
    return list(
        db.scalars(
            select(GovernmentBudgetCommitmentLine)
            .where(GovernmentBudgetCommitmentLine.commitment_id == commitment_id)
            .order_by(GovernmentBudgetCommitmentLine.linea)
        )
    )


def causado_de_linea(
    db: Session,
    linea_compromiso_id: str,
    excluir_causa_id: str | None = None,
) -> Decimal:
    query = select(GovernmentBudgetCauseLine).join(
        GovernmentBudgetCause,
        GovernmentBudgetCause.id == GovernmentBudgetCauseLine.cause_id,
    ).where(
        GovernmentBudgetCauseLine.commitment_line_id == linea_compromiso_id,
        GovernmentBudgetCause.estado == "FORMALIZADO",
    )
    if excluir_causa_id is not None:
        query = query.where(GovernmentBudgetCauseLine.cause_id != excluir_causa_id)
    monto = Decimal("0.00")
    for linea in db.scalars(query):
        monto += linea.monto
    return monto


def _pendiente_de_linea(
    db: Session,
    linea: GovernmentBudgetCommitmentLine,
    excluir_causa_id: str | None = None,
) -> Decimal:
    causado = causado_de_linea(db, str(linea.id), excluir_causa_id)
    return linea.monto - causado


def _totales_compromiso(
    db: Session,
    commitment_id: str,
    excluir_causa_id: str | None = None,
) -> dict[str, Decimal]:
    total = Decimal("0.00")
    causado = Decimal("0.00")
    for linea in _lineas_compromiso(db, commitment_id):
        total += linea.monto
        causado += causado_de_linea(db, str(linea.id), excluir_causa_id)
    return {"total": total, "causado": causado, "pendiente": total - causado}


def _compromiso_por_id(db: Session, ctx: CompanyContext, commitment_id: str) -> GovernmentBudgetCommitment:
    compromiso = db.scalar(
        select(GovernmentBudgetCommitment).where(
            GovernmentBudgetCommitment.company_id == ctx.company_id,
            GovernmentBudgetCommitment.id == commitment_id,
        )
    )
    if compromiso is None:
        raise KontrolError(
            code="GOV_BUDGET_CAUSE_COMMITMENT_INVALID",
            message="El compromiso no existe o no pertenece a la empresa",
            field_errors={"compromiso_id": ["El compromiso no existe o no pertenece a la empresa"]},
            status_code=422,
        )
    return compromiso


def _causa_por_id(db: Session, ctx: CompanyContext, causa_id: str) -> GovernmentBudgetCause:
    causa = db.scalar(
        select(GovernmentBudgetCause).where(
            GovernmentBudgetCause.company_id == ctx.company_id,
            GovernmentBudgetCause.id == causa_id,
        )
    )
    if causa is None:
        raise NotFoundError("GOV_BUDGET_CAUSE_NOT_FOUND", "Causado no encontrado")
    return causa


def _historia_causa(db: Session, cause_id: str) -> list[GovernmentBudgetCauseHistory]:
    return list(
        db.scalars(
            select(GovernmentBudgetCauseHistory)
            .where(GovernmentBudgetCauseHistory.cause_id == cause_id)
            .order_by(GovernmentBudgetCauseHistory.created_at.desc())
        )
    )


def _evidencias_causa(db: Session, cause_id: str) -> list[GovernmentBudgetCauseEvidence]:
    return list(
        db.scalars(
            select(GovernmentBudgetCauseEvidence).where(
                GovernmentBudgetCauseEvidence.cause_id == cause_id
            )
        )
    )


def _lineas_causa(db: Session, cause_id: str) -> list[GovernmentBudgetCauseLine]:
    return list(
        db.scalars(
            select(GovernmentBudgetCauseLine).where(GovernmentBudgetCauseLine.cause_id == cause_id)
        )
    )


def _linea_detalle(
    db: Session,
    linea_compromiso: GovernmentBudgetCommitmentLine,
) -> dict[str, Any]:
    credito = db.get(GovernmentBudgetCredit, linea_compromiso.credit_id)
    if credito is None:
        raise _invalida("La línea del compromiso no tiene crédito")
    categoria = db.get(GovernmentBudgetCategory, credito.category_id)
    partida = db.get(GovernmentBudgetClassifierItem, credito.item_id)
    fuente = db.get(GovernmentBudgetFundingSource, credito.source_id)
    unidad = None
    if categoria is not None and categoria.unit_id is not None:
        unit = db.get(GovernmentUnit, categoria.unit_id)
        unidad = unit.name if unit is not None else None
    return {
        "linea": linea_compromiso.linea,
        "partida": partida.denominacion if partida is not None else None,
        "categoria": categoria.denominacion if categoria is not None else None,
        "fuente": fuente.denominacion if fuente is not None else None,
        "unidad": unidad,
    }


def _etiqueta_documento(db: Session, document_type_id: str) -> str | None:
    tipo = db.get(DocumentType, document_type_id)
    return _etiqueta(tipo.code, tipo.name) if tipo is not None else None


def _documento_valido(
    db: Session,
    ctx: CompanyContext,
    year_id: str,
    document_id: str,
    document_type_id: str | None = None,
) -> Document | None:
    documento = db.scalar(
        select(Document).where(
            Document.company_id == ctx.company_id,
            Document.id == document_id,
            Document.status == "ACTIVE",
        )
    )
    if documento is None:
        return None
    if document_type_id is not None and documento.document_type_id != document_type_id:
        return None
    version = None
    if documento.current_version_id is not None:
        version = db.get(DocumentVersion, documento.current_version_id)
    if version is None or version.sha256 is None:
        return None
    vinculo = db.scalar(
        select(DocumentLink).where(
            DocumentLink.document_id == document_id,
            DocumentLink.resource_type == "GovernmentBudgetYear",
            DocumentLink.resource_id == year_id,
            DocumentLink.company_id == ctx.company_id,
        )
    )
    if vinculo is None:
        return None
    return documento


def _contrato_ligado(
    db: Session,
    ctx: CompanyContext,
    commitment_id: str,
    contract_id: str,
) -> bool:
    certificados = set(
        db.scalars(
            select(GovernmentBudgetCommitmentLine.certificate_id).where(
                GovernmentBudgetCommitmentLine.commitment_id == commitment_id
            )
        )
    )
    if not certificados:
        return False
    asignacion = db.scalar(
        select(GovernmentContractBudgetAllocation).where(
            GovernmentContractBudgetAllocation.company_id == ctx.company_id,
            GovernmentContractBudgetAllocation.contract_id == contract_id,
            GovernmentContractBudgetAllocation.certificate_id.in_(certificados),
        )
    )
    return asignacion is not None


def _snapshot_evidencia_contractual(
    tipo: str,
    recurso: Any,
) -> dict[str, Any] | None:
    mapeo = {
        "CONTRACT_RECEIPT": ("VIGENTE", "fecha"),
        "CONTRACT_VALUATION": ("CONFORMADA", "fecha_conformidad"),
        "CONTRACT_DELIVERY": ("CONFORME", "fecha_revision"),
        "CONTRACT_INVOICE": ("VIGENTE", "fecha_conformidad"),
    }
    if tipo not in mapeo:
        return None
    estado_aceptado, atributo_fecha = mapeo[tipo]
    if recurso.estado != estado_aceptado:
        return {
            "etiqueta": recurso.numero,
            "estado": recurso.estado,
            "fecha": getattr(recurso, atributo_fecha).isoformat(),
            "sha256": recurso.documento_sha256,
            "contrato": recurso.contract_id,
        }
    return {
        "etiqueta": recurso.numero,
        "estado": recurso.estado,
        "fecha": getattr(recurso, atributo_fecha).isoformat(),
        "sha256": recurso.documento_sha256,
        "contrato": recurso.contract_id,
    }


def _obtener_recurso_contractual(
    db: Session,
    ctx: CompanyContext,
    tipo: str,
    resource_id: str,
) -> Any | None:
    mapeo: dict[
        str,
        type[GovernmentContractReceipt]
        | type[GovernmentContractValuation]
        | type[GovernmentContractDeliverableSubmission]
        | type[GovernmentContractInvoice],
    ] = {
        "CONTRACT_RECEIPT": GovernmentContractReceipt,
        "CONTRACT_VALUATION": GovernmentContractValuation,
        "CONTRACT_DELIVERY": GovernmentContractDeliverableSubmission,
        "CONTRACT_INVOICE": GovernmentContractInvoice,
    }
    clase = mapeo.get(tipo)
    if clase is None:
        return None
    return db.scalar(
        select(clase).where(
            clase.company_id == ctx.company_id,
            clase.id == resource_id,
        )
    )


def _evidencia_snapshot(
    db: Session,
    ctx: CompanyContext,
    year_id: str,
    commitment_id: str,
    tipo: str,
    resource_id: str,
) -> dict[str, Any] | None:
    if tipo == "DOCUMENT":
        documento = _documento_valido(db, ctx, year_id, resource_id)
        if documento is None:
            return None
        version = db.get(DocumentVersion, documento.current_version_id) if documento.current_version_id else None
        if version is None or version.sha256 is None:
            return None
        return {
            "etiqueta": documento.title,
            "estado": documento.status,
            "fecha": hoy_de_negocio(documento.created_at).isoformat(),
            "sha256": version.sha256,
            "contrato": None,
            "tipo_documental_id": documento.document_type_id,
        }
    recurso = _obtener_recurso_contractual(db, ctx, tipo, resource_id)
    if recurso is None:
        return None
    if not _contrato_ligado(db, ctx, commitment_id, recurso.contract_id):
        return None
    return _snapshot_evidencia_contractual(tipo, recurso)


def _validar_decimal(monto: Decimal, campo: str) -> bool:
    finito = _decimal_finito(monto)
    if finito is None or finito <= 0:
        return False
    exp = finito.as_tuple().exponent
    return isinstance(exp, int) and exp >= -2


def _validar_fuente(
    db: Session,
    ctx: CompanyContext,
    commitment_id: str,
    fuente_tipo: str | None,
    fuente_id: str | None,
) -> None:
    if (fuente_tipo is None) != (fuente_id is None):
        raise _invalida("fuente_tipo y fuente_id deben indicarse juntos")
    if fuente_tipo is None:
        return
    if fuente_tipo not in ("CONTRACT", "PROCUREMENT_FILE", "OTHER"):
        raise _invalida("fuente_tipo no válido")
    if fuente_tipo == "CONTRACT":
        if not isinstance(fuente_id, str) or not _contrato_ligado(db, ctx, commitment_id, fuente_id):
            raise _invalida("fuente_id no corresponde a un contrato ligado al compromiso")


def _validar_montos(
    db: Session,
    commitment_id: str,
    lineas: list[dict[str, Any]],
    excluir_causa_id: str | None = None,
) -> None:
    ids = [item["linea_compromiso_id"] for item in lineas]
    if len(set(ids)) != len(ids):
        raise _invalida("linea_compromiso_id repetido")
    for item in lineas:
        linea_id = item["linea_compromiso_id"]
        linea = db.get(GovernmentBudgetCommitmentLine, linea_id)
        if linea is None or linea.commitment_id != commitment_id:
            raise _invalida("La línea no pertenece al compromiso")
        monto = item["monto"]
        if not _validar_decimal(monto, "monto"):
            raise _invalida("El monto debe ser mayor a 0 con hasta 2 decimales")
        pendiente = _pendiente_de_linea(db, linea, excluir_causa_id)
        if monto > pendiente:
            raise KontrolError(
                code="GOV_BUDGET_CAUSE_OVER_COMMITMENT",
                message="El monto supera el pendiente de la línea del compromiso",
                field_errors={"lineas": ["Monto superior al pendiente"]},
                details={"linea": str(linea.id), "pendiente": str(pendiente), "solicitado": str(monto)},
                status_code=422,
            )


def _validar_evidencias_validas(
    db: Session,
    ctx: CompanyContext,
    year_id: str,
    commitment_id: str,
    evidencias: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    for evidencia in evidencias:
        tipo = evidencia.get("tipo")
        resource_id = evidencia.get("id")
        if not isinstance(tipo, str) or not isinstance(resource_id, str):
            raise KontrolError(
                code="GOV_BUDGET_CAUSE_EVIDENCE_INVALID",
                message="Evidencia inválida",
                field_errors={"evidencias": ["tipo e id son obligatorios"]},
                status_code=422,
            )
        snapshot = _evidencia_snapshot(db, ctx, year_id, commitment_id, tipo, resource_id)
        if snapshot is None:
            raise KontrolError(
                code="GOV_BUDGET_CAUSE_EVIDENCE_INVALID",
                message="La evidencia no existe o no es válida",
                field_errors={"evidencias": ["Evidencia inexistente o inválida"]},
                status_code=422,
            )
    return [item for item in evidencias]


def _exigir_completitud(
    db: Session,
    ctx: CompanyContext,
    year_id: str,
    commitment_id: str,
    politica: GovernmentBudgetCausingPolicy,
    fecha_efectiva: date,
    evidencias: list[dict[str, Any]],
) -> None:
    if politica.requiere_recepcion and not any(
        e.get("tipo") == "CONTRACT_RECEIPT" for e in evidencias
    ):
        raise KontrolError(
            code="GOV_BUDGET_CAUSE_EVIDENCE_MISSING",
            message="Falta evidencia de recepción",
            field_errors={"evidencias": ["Falta CONTRACT_RECEIPT"]},
            details={"faltan": ["CONTRACT_RECEIPT"]},
            status_code=422,
        )
    if politica.requiere_valuacion and not any(
        e.get("tipo") == "CONTRACT_VALUATION" for e in evidencias
    ):
        raise KontrolError(
            code="GOV_BUDGET_CAUSE_EVIDENCE_MISSING",
            message="Falta evidencia de valuación",
            field_errors={"evidencias": ["Falta CONTRACT_VALUATION"]},
            details={"faltan": ["CONTRACT_VALUATION"]},
            status_code=422,
        )
    if politica.requiere_conformidad and not any(
        e.get("tipo") in ("CONTRACT_DELIVERY", "CONTRACT_VALUATION", "CONTRACT_INVOICE")
        for e in evidencias
    ):
        raise KontrolError(
            code="GOV_BUDGET_CAUSE_EVIDENCE_MISSING",
            message="Falta evidencia de conformidad",
            field_errors={"evidencias": ["Falta evidencia de conformidad"]},
            details={"faltan": ["CONFORMIDAD"]},
            status_code=422,
        )
    if politica.disparador == "RECEIPT_ACCEPTED" and not any(
        e.get("tipo") == "CONTRACT_RECEIPT" for e in evidencias
    ):
        raise KontrolError(
            code="GOV_BUDGET_CAUSE_EVIDENCE_MISSING",
            message="Falta evidencia del disparador",
            field_errors={"evidencias": ["Falta CONTRACT_RECEIPT"]},
            details={"faltan": ["CONTRACT_RECEIPT"]},
            status_code=422,
        )
    if politica.disparador == "VALUATION_APPROVED" and not any(
        e.get("tipo") == "CONTRACT_VALUATION" for e in evidencias
    ):
        raise KontrolError(
            code="GOV_BUDGET_CAUSE_EVIDENCE_MISSING",
            message="Falta evidencia del disparador",
            field_errors={"evidencias": ["Falta CONTRACT_VALUATION"]},
            details={"faltan": ["CONTRACT_VALUATION"]},
            status_code=422,
        )
    if politica.disparador == "DELIVERY_ACCEPTED" and not any(
        e.get("tipo") == "CONTRACT_DELIVERY" for e in evidencias
    ):
        raise KontrolError(
            code="GOV_BUDGET_CAUSE_EVIDENCE_MISSING",
            message="Falta evidencia del disparador",
            field_errors={"evidencias": ["Falta CONTRACT_DELIVERY"]},
            details={"faltan": ["CONTRACT_DELIVERY"]},
            status_code=422,
        )
    if politica.disparador == "INVOICE_CONFORMED" and not any(
        e.get("tipo") == "CONTRACT_INVOICE" for e in evidencias
    ):
        raise KontrolError(
            code="GOV_BUDGET_CAUSE_EVIDENCE_MISSING",
            message="Falta evidencia del disparador",
            field_errors={"evidencias": ["Falta CONTRACT_INVOICE"]},
            details={"faltan": ["CONTRACT_INVOICE"]},
            status_code=422,
        )
    documentos_politica = _documentos_politica(db, str(politica.id))
    faltantes: list[str] = []
    for documento_politica in documentos_politica:
        if not documento_politica.obligatorio:
            continue
        encontrado = any(
            evidencia.get("tipo") == "DOCUMENT"
            and (
                snapshot := _evidencia_snapshot(
                    db,
                    ctx,
                    year_id,
                    commitment_id,
                    "DOCUMENT",
                    evidencia["id"],
                )
            ) is not None
            and snapshot.get("tipo_documental_id") == documento_politica.document_type_id
            for evidencia in evidencias
        )
        if not encontrado:
            faltantes.append(documento_politica.document_type_id)
    if faltantes:
        raise KontrolError(
            code="GOV_BUDGET_CAUSE_DOCUMENTS_MISSING",
            message="Faltan documentos exigidos por la política",
            field_errors={"evidencias": ["Faltan documentos"]},
            details={"faltan": faltantes},
            status_code=422,
        )

    posteriores: list[str] = []
    for evidencia in evidencias:
        tipo_evidencia = evidencia.get("tipo")
        if not isinstance(tipo_evidencia, str):
            continue
        es_evidencia_exigida = False
        if tipo_evidencia == "DOCUMENT":
            recurso_id = evidencia.get("id")
            if not isinstance(recurso_id, str):
                continue
            snapshot_tipo = _evidencia_snapshot(
                db,
                ctx,
                year_id,
                commitment_id,
                "DOCUMENT",
                recurso_id,
            )
            es_evidencia_exigida = snapshot_tipo is not None and any(
                documento_politica.obligatorio
                and documento_politica.document_type_id == snapshot_tipo.get("tipo_documental_id")
                for documento_politica in documentos_politica
            )
        else:
            es_evidencia_exigida = (
                (politica.requiere_recepcion and tipo_evidencia == "CONTRACT_RECEIPT")
                or (politica.requiere_valuacion and tipo_evidencia == "CONTRACT_VALUATION")
                or (politica.requiere_conformidad and tipo_evidencia in ("CONTRACT_DELIVERY", "CONTRACT_VALUATION", "CONTRACT_INVOICE"))
                or (politica.disparador == "RECEIPT_ACCEPTED" and tipo_evidencia == "CONTRACT_RECEIPT")
                or (politica.disparador == "VALUATION_APPROVED" and tipo_evidencia == "CONTRACT_VALUATION")
                or (politica.disparador == "DELIVERY_ACCEPTED" and tipo_evidencia == "CONTRACT_DELIVERY")
                or (politica.disparador == "INVOICE_CONFORMED" and tipo_evidencia == "CONTRACT_INVOICE")
            )
        if not es_evidencia_exigida:
            continue
        recurso_id = evidencia.get("id")
        if not isinstance(recurso_id, str):
            continue
        snapshot_fecha = _evidencia_snapshot(
            db,
            ctx,
            year_id,
            commitment_id,
            tipo_evidencia,
            recurso_id,
        )
        if snapshot_fecha is None:
            continue
        fecha_texto = snapshot_fecha.get("fecha")
        if fecha_texto is not None and isinstance(fecha_texto, str):
            fecha_evidencia = date.fromisoformat(fecha_texto[:10])
            if fecha_evidencia > fecha_efectiva:
                posteriores.append(str(evidencia["id"]))
    if posteriores:
        raise KontrolError(
            code="GOV_BUDGET_CAUSE_EVIDENCE_MISSING",
            message="Las evidencias exigidas no pueden ser posteriores a la fecha efectiva",
            field_errors={"evidencias": ["Evidencias posteriores a la fecha efectiva"]},
            details={"posteriores": posteriores},
            status_code=422,
        )


def _validar_fecha_efectiva(
    db: Session,
    ctx: CompanyContext,
    year_id: str,
    compromiso: GovernmentBudgetCommitment,
    fecha_efectiva: date,
) -> None:
    ejercicio = _ejercicio_de_empresa(db, ctx, year_id, bloquear=False)
    hoy = hoy_de_negocio()
    if fecha_efectiva > hoy:
        raise KontrolError(
            code="GOV_BUDGET_CAUSE_DATE_INVALID",
            message="La fecha efectiva no puede ser futura",
            field_errors={"fecha_efectiva": ["Fecha futura"]},
            status_code=422,
        )
    if fecha_efectiva.year != ejercicio.anio:
        raise KontrolError(
            code="GOV_BUDGET_CAUSE_DATE_INVALID",
            message="La fecha efectiva debe pertenecer al año del ejercicio",
            field_errors={"fecha_efectiva": ["Año distinto al ejercicio"]},
            status_code=422,
        )
    if fecha_efectiva < compromiso.fecha:
        raise KontrolError(
            code="GOV_BUDGET_CAUSE_DATE_INVALID",
            message="La fecha efectiva no puede ser anterior al compromiso",
            field_errors={"fecha_efectiva": ["Fecha anterior al compromiso"]},
            status_code=422,
        )


def _validar_politica_vigente(
    db: Session,
    ctx: CompanyContext,
    politica_id: str,
    fecha_efectiva: date,
) -> GovernmentBudgetCausingPolicy:
    politica = _politica_por_id(db, ctx, politica_id)
    if politica.estado != "VIGENTE":
        raise ConflictError(
            "GOV_BUDGET_CAUSE_POLICY_NOT_ACTIVE",
            "La política no está vigente",
        )
    if politica.vigente_desde > fecha_efectiva:
        raise ConflictError(
            "GOV_BUDGET_CAUSE_POLICY_NOT_ACTIVE",
            "La política no cubre la fecha efectiva",
        )
    if politica.vigente_hasta is not None and politica.vigente_hasta < fecha_efectiva:
        raise ConflictError(
            "GOV_BUDGET_CAUSE_POLICY_NOT_ACTIVE",
            "La política no cubre la fecha efectiva",
        )
    return politica


def _validar_compromiso(
    db: Session,
    ctx: CompanyContext,
    year_id: str,
    compromiso_id: str,
) -> GovernmentBudgetCommitment:
    compromiso = _compromiso_por_id(db, ctx, compromiso_id)
    if compromiso.estado != "VIGENTE" or compromiso.year_id != year_id:
        raise KontrolError(
            code="GOV_BUDGET_CAUSE_COMMITMENT_INVALID",
            message="El compromiso no es válido para el causado",
            field_errors={"compromiso_id": ["Compromiso inválido"]},
            status_code=422,
        )
    return compromiso


def _causa_a_dict(
    db: Session,
    ctx: CompanyContext,
    causa: GovernmentBudgetCause,
    incluir_controles: bool = False,
) -> dict[str, Any]:
    year = db.get(GovernmentBudgetYear, causa.year_id)
    anio = year.anio if year is not None else None
    compromiso = db.get(GovernmentBudgetCommitment, causa.commitment_id)
    if compromiso is None:
        raise _invalida("El compromiso no existe")
    totales = _totales_compromiso(db, str(compromiso.id), str(causa.id))
    lineas = []
    for linea_causa in _lineas_causa(db, str(causa.id)):
        linea_compromiso = db.get(GovernmentBudgetCommitmentLine, linea_causa.commitment_line_id)
        detalle = _linea_detalle(db, linea_compromiso) if linea_compromiso is not None else {}
        pendiente_tras = Decimal("0.00")
        if linea_compromiso is not None:
            causado_otros = causado_de_linea(db, str(linea_compromiso.id), str(causa.id))
            pendiente_tras = linea_compromiso.monto - causado_otros - linea_causa.monto
        lineas.append(
            {
                "id": str(linea_causa.id),
                "linea_compromiso_id": linea_causa.commitment_line_id,
                "linea": detalle.get("linea"),
                "partida": detalle.get("partida"),
                "categoria": detalle.get("categoria"),
                "comprometido": str(linea_compromiso.monto) if linea_compromiso is not None else "0.00",
                "causado_otros": str(
                    causado_de_linea(db, str(linea_compromiso.id), str(causa.id))
                    if linea_compromiso is not None
                    else Decimal("0.00")
                ),
                "monto": str(linea_causa.monto),
                "pendiente_tras": str(pendiente_tras),
            }
        )
    evidencias = []
    for evidencia in _evidencias_causa(db, str(causa.id)):
        snapshot = evidencia.snapshot
        evidencias.append(
            {
                "id": str(evidencia.id),
                "tipo": evidencia.resource_type,
                "recurso_id": evidencia.resource_id,
                "etiqueta": snapshot.get("etiqueta") if snapshot else None,
                "estado": snapshot.get("estado") if snapshot else None,
                "fecha": snapshot.get("fecha") if snapshot else None,
                "sha256": snapshot.get("sha256") if snapshot else None,
            }
        )
    politica_db = db.get(GovernmentBudgetCausingPolicy, causa.policy_id)
    politica = None
    if politica_db is not None:
        politica = {
            "id": str(politica_db.id),
            "codigo": politica_db.codigo,
            "nombre": politica_db.nombre,
            "tipo_gasto": politica_db.tipo_gasto,
            "disparador": politica_db.disparador,
            "version": politica_db.version,
        }
    autoridad = None
    if causa.autoridad_cargo_id is not None:
        autoridad = {
            "cargo": causa.autoridad_cargo_nombre,
            "unidad": causa.autoridad_unidad,
            "funcionario": causa.autoridad_funcionario_nombre,
        }
    controles = _controles(db, ctx, causa) if incluir_controles else []
    if causa.estado == "FORMALIZADO":
        monto_ordenado_str = str(montos_ordenados(db, causa.company_id, [str(causa.id)])[str(causa.id)])
        pendiente_str = str(pendiente_de_ordenar(causa.monto, Decimal(monto_ordenado_str)))
    else:
        monto_ordenado_str = "0.00"
        pendiente_str = "0.00"
    return {
        "id": str(causa.id),
        "codigo": causa.codigo,
        "numero": causa.numero,
        "estado": causa.estado,
        "version": causa.version,
        "year_id": causa.year_id,
        "anio": anio,
        "compromiso": {
            "id": str(compromiso.id),
            "codigo": compromiso.codigo,
            "concepto": compromiso.concepto,
            "total": str(totales["total"]),
            "causado": str(totales["causado"] + causa.monto),
            "pendiente": str(max(Decimal("0.00"), totales["pendiente"] - causa.monto)),
        },
        "politica": politica,
        "fecha_efectiva": causa.fecha_efectiva.isoformat(),
        "registrado_en": causa.created_at.isoformat(),
        "moneda": causa.moneda,
        "monto": str(causa.monto),
        "concepto": causa.concepto,
        "beneficiario": causa.beneficiario,
        "fuente_tipo": causa.source_resource_type,
        "fuente_id": causa.source_resource_id,
        "autoridad_cargo_id": causa.autoridad_cargo_id,
        "autoridad": autoridad,
        "lineas": lineas,
        "evidencias": evidencias,
        "formalizado_en": causa.formalizado_en.isoformat() if causa.formalizado_en else None,
        "formalizado_por": _username(db, causa.formalizado_por) if causa.formalizado_por else None,
        "anulado_en": causa.anulado_en.isoformat() if causa.anulado_en else None,
        "motivo_anulacion": causa.motivo_anulacion,
        "huella": causa.huella,
        "monto_ordenado": monto_ordenado_str,
        "pendiente_de_ordenar": pendiente_str,
        "controles": controles,
        "historia": _historia_causa_a_dict(db, causa),
    }


def _username(db: Session, user_id: str | None) -> str | None:
    if user_id is None:
        return None
    usuario = db.get(User, user_id)
    return usuario.username if usuario is not None else None


def _historia_causa_a_dict(
    db: Session,
    causa: GovernmentBudgetCause,
) -> list[dict[str, Any]]:
    historia = []
    for item in _historia_causa(db, str(causa.id)):
        historia.append(
            {
                "evento": item.evento,
                "fecha": item.created_at.isoformat(),
                "actor": _username(db, item.actor_id),
            }
        )
    return historia


def _control(
    codigo: str,
    cumplido: bool,
    mensaje: str,
) -> dict[str, Any]:
    return {"codigo": codigo, "cumplido": cumplido, "mensaje": mensaje}


def _controles(db: Session, ctx: CompanyContext, causa: GovernmentBudgetCause) -> list[dict[str, Any]]:
    controles: list[dict[str, Any]] = []
    compromiso = db.get(GovernmentBudgetCommitment, causa.commitment_id)
    if compromiso is None or compromiso.estado != "VIGENTE":
        controles.append(_control("COMPROMISO", False, "El compromiso no está vigente"))
    else:
        controles.append(_control("COMPROMISO", True, "Compromiso válido"))
    politica = db.get(GovernmentBudgetCausingPolicy, causa.policy_id)
    if politica is None or politica.estado != "VIGENTE":
        controles.append(_control("POLITICA", False, "La política no está vigente"))
    else:
        controles.append(_control("POLITICA", True, "Política vigente"))
    hoy = hoy_de_negocio()
    year = db.get(GovernmentBudgetYear, causa.year_id)
    if year is None or causa.fecha_efectiva.year != year.anio or causa.fecha_efectiva > hoy:
        controles.append(_control("FECHA_EFECTIVA", False, "Fecha efectiva inválida"))
    else:
        controles.append(_control("FECHA_EFECTIVA", True, "Fecha efectiva válida"))
    if compromiso is None:
        controles.append(_control("SALDO", False, "Compromiso no encontrado"))
    else:
        saldo_ok = True
        for linea_causa in _lineas_causa(db, str(causa.id)):
            linea_compromiso = db.get(GovernmentBudgetCommitmentLine, linea_causa.commitment_line_id)
            if linea_compromiso is None:
                saldo_ok = False
                break
            pendiente = _pendiente_de_linea(db, linea_compromiso, str(causa.id))
            if linea_causa.monto > pendiente:
                saldo_ok = False
                break
        controles.append(_control("SALDO", saldo_ok, "Saldos por línea correctos"))
    if politica is not None and politica.disparador in (
        "RECEIPT_ACCEPTED",
        "VALUATION_APPROVED",
        "DELIVERY_ACCEPTED",
        "INVOICE_CONFORMED",
        "DOCUMENTARY",
    ):
        tipo_exigido = {
            "RECEIPT_ACCEPTED": "CONTRACT_RECEIPT",
            "VALUATION_APPROVED": "CONTRACT_VALUATION",
            "DELIVERY_ACCEPTED": "CONTRACT_DELIVERY",
            "INVOICE_CONFORMED": "CONTRACT_INVOICE",
            "DOCUMENTARY": "DOCUMENT",
        }[politica.disparador]
        evidencias = _evidencias_causa(db, str(causa.id))
        disparador_ok = any(e.resource_type == tipo_exigido for e in evidencias)
        controles.append(
            _control(
                "EVIDENCIA_DISPARADOR",
                disparador_ok,
                "Evidencia del disparador presente" if disparador_ok else "Falta evidencia del disparador",
            )
        )
    else:
        controles.append(_control("EVIDENCIA_DISPARADOR", True, "Sin exigencia de disparador"))
    if politica is not None and politica.requiere_recepcion:
        recepcion_ok = any(e.resource_type == "CONTRACT_RECEIPT" for e in _evidencias_causa(db, str(causa.id)))
        controles.append(
            _control(
                "RECEPCION",
                recepcion_ok,
                "Recepción presente" if recepcion_ok else "Falta recepción",
            )
        )
    if politica is not None and politica.requiere_valuacion:
        valuacion_ok = any(e.resource_type == "CONTRACT_VALUATION" for e in _evidencias_causa(db, str(causa.id)))
        controles.append(
            _control(
                "VALUACION",
                valuacion_ok,
                "Valuación presente" if valuacion_ok else "Falta valuación",
            )
        )
    if politica is not None and politica.requiere_conformidad:
        conformidad_ok = any(
            e.resource_type in ("CONTRACT_DELIVERY", "CONTRACT_VALUATION", "CONTRACT_INVOICE")
            for e in _evidencias_causa(db, str(causa.id))
        )
        controles.append(
            _control(
                "CONFORMIDAD",
                conformidad_ok,
                "Conformidad presente" if conformidad_ok else "Falta conformidad",
            )
        )
    if politica is not None:
        documentos_politica = _documentos_politica(db, str(politica.id))
        documentos_obligatorios = [d for d in documentos_politica if d.obligatorio]
        if documentos_obligatorios:
            documentos_presentes = {
                e.snapshot.get("tipo_documental_id")
                for e in _evidencias_causa(db, str(causa.id))
                if e.resource_type == "DOCUMENT"
            }
            documentos_ok = all(
                d.document_type_id in documentos_presentes
                for d in documentos_obligatorios
            )
            controles.append(
                _control(
                    "DOCUMENTOS",
                    documentos_ok,
                    "Documentos exigidos presentes" if documentos_ok else "Faltan documentos exigidos",
                )
            )
        else:
            controles.append(_control("DOCUMENTOS", True, "Sin documentos exigidos"))
    if causa.autoridad_cargo_id is not None and politica is not None:
        cargo = db.get(GovernmentPosition, causa.autoridad_cargo_id)
        if cargo is None:
            controles.append(_control("AUTORIDAD", False, "Cargo de autoridad no encontrado"))
        else:
            valida = _autoridad_valida(
                db,
                ctx.company_id,
                str(cargo.id),
                hoy,
                politica.competencia_accion,
                politica.competencia_materia,
            )
            controles.append(
                _control(
                    "AUTORIDAD",
                    valida,
                    "Autoridad válida" if valida else "Autoridad sin competencia en vigor",
                )
            )
    else:
        controles.append(_control("AUTORIDAD", False, "Autoridad no definida"))
    segregacion_ok = True
    if compromiso is not None:
        emisor = compromiso.emitido_por
        equivalentes = usuarios_equivalentes(db, ctx, ctx.user_id)
        regla = db.scalar(
            select(GovernmentSoDRule).where(
                GovernmentSoDRule.tenant_id == ctx.tenant_id,
                GovernmentSoDRule.company_id == ctx.company_id,
                GovernmentSoDRule.proceso == "BUD-09",
                GovernmentSoDRule.accion_b == "BUD09_CAUSAR",
                GovernmentSoDRule.estado == "VIGENTE",
                GovernmentSoDRule.vigente_desde <= hoy,
                (GovernmentSoDRule.vigente_hasta.is_(None))
                | (GovernmentSoDRule.vigente_hasta >= hoy),
            )
        )
        if regla is not None and (ctx.user_id == emisor or emisor in equivalentes):
            segregacion_ok = False
    controles.append(
        _control(
            "SEGREGACION",
            segregacion_ok,
            "Segregación de funciones correcta" if segregacion_ok else "El actor o un equivalente emitió el compromiso",
        )
    )
    return controles


def _obtener_causa(db: Session, ctx: CompanyContext, causa_id: str) -> dict[str, Any]:
    return _causa_a_dict(db, ctx, _causa_por_id(db, ctx, causa_id), incluir_controles=True)


def _crear_causa(
    db: Session,
    ctx: CompanyContext,
    year_id: str,
    cuerpo: dict[str, Any],
) -> dict[str, Any]:
    ejercicio = _ejercicio_de_empresa(db, ctx, year_id, bloquear=False)
    if ejercicio.estado not in ("APROBADO", "RECONDUCIDO"):
        raise _estado_invalido()
    compromiso_id = cuerpo.get("compromiso_id")
    politica_id = cuerpo.get("politica_id")
    fecha_efectiva = cuerpo.get("fecha_efectiva")
    if not isinstance(compromiso_id, str):
        raise _invalida("compromiso_id es obligatorio")
    if not isinstance(politica_id, str):
        raise _invalida("politica_id es obligatorio")
    if not isinstance(fecha_efectiva, date):
        raise _invalida("fecha_efectiva es obligatoria")
    compromiso = _validar_compromiso(db, ctx, year_id, compromiso_id)
    _validar_fecha_efectiva(db, ctx, year_id, compromiso, fecha_efectiva)
    politica = _validar_politica_vigente(db, ctx, politica_id, fecha_efectiva)
    lineas = cuerpo.get("lineas")
    if not isinstance(lineas, list) or not 1 <= len(lineas) <= 20:
        raise _invalida("Debe indicar entre 1 y 20 líneas")
    lineas_validas: list[dict[str, Any]] = []
    for linea in lineas:
        if not isinstance(linea, dict):
            raise _invalida("lineas contiene elementos inválidos")
        linea_compromiso_id = linea.get("linea_compromiso_id")
        monto = linea.get("monto")
        if not isinstance(linea_compromiso_id, str):
            raise _invalida("linea_compromiso_id es obligatorio")
        if not isinstance(monto, Decimal) or not _validar_decimal(monto, "monto"):
            raise _invalida("El monto debe ser un decimal mayor a 0 con hasta 2 decimales")
        lineas_validas.append({"linea_compromiso_id": linea_compromiso_id, "monto": monto})
    _validar_montos(db, compromiso_id, lineas_validas)
    evidencias = cuerpo.get("evidencias") or []
    if not isinstance(evidencias, list) or len(evidencias) > 30:
        raise _invalida("evidencias debe ser una lista de hasta 30 elementos")
    evidencias_validas: list[dict[str, Any]] = []
    for evidencia in evidencias:
        if not isinstance(evidencia, dict):
            raise _invalida("evidencias contiene elementos inválidos")
        tipo = evidencia.get("tipo")
        recurso_id = evidencia.get("id")
        if not isinstance(tipo, str) or not isinstance(recurso_id, str):
            raise _invalida("tipo e id de evidencia son obligatorios")
        evidencias_validas.append({"tipo": tipo, "id": recurso_id})
    _validar_evidencias_validas(
        db,
        ctx,
        year_id,
        compromiso_id,
        evidencias_validas,
    )
    fuente_tipo = cuerpo.get("fuente_tipo")
    fuente_id = cuerpo.get("fuente_id")
    _validar_fuente(db, ctx, compromiso_id, fuente_tipo, fuente_id)
    autoridad_cargo_id = cuerpo.get("autoridad_cargo_id")
    if autoridad_cargo_id is not None and not isinstance(autoridad_cargo_id, str):
        raise _invalida("autoridad_cargo_id debe ser texto")
    concepto = cuerpo.get("concepto")
    if not isinstance(concepto, str) or not 10 <= len(concepto) <= 500:
        raise _invalida("El concepto debe tener entre 10 y 500 caracteres")
    monto_total = sum(
        (Decimal(str(linea["monto"])) for linea in lineas_validas),
        Decimal("0.00"),
    )
    causa = GovernmentBudgetCause(
        company_id=ctx.company_id,
        year_id=year_id,
        commitment_id=compromiso_id,
        policy_id=politica_id,
        policy_version=politica.version,
        estado="BORRADOR",
        fecha_efectiva=fecha_efectiva,
        moneda=canonical_currency(compromiso.moneda),
        monto=monto_total,
        concepto=concepto,
        beneficiario=cuerpo.get("beneficiario"),
        source_resource_type=fuente_tipo,
        source_resource_id=fuente_id,
        autoridad_cargo_id=autoridad_cargo_id,
    )
    db.add(causa)
    db.flush()
    for linea in lineas_validas:
        db.add(
            GovernmentBudgetCauseLine(
                cause_id=str(causa.id),
                company_id=ctx.company_id,
                commitment_line_id=linea["linea_compromiso_id"],
                monto=linea["monto"],
            )
        )
    for evidencia in evidencias_validas:
        snapshot = _evidencia_snapshot(
            db,
            ctx,
            year_id,
            compromiso_id,
            evidencia["tipo"],
            evidencia["id"],
        )
        if snapshot is None:
            raise KontrolError(
                code="GOV_BUDGET_CAUSE_EVIDENCE_INVALID",
                message="La evidencia no existe o no es válida",
                field_errors={"evidencias": ["Evidencia inexistente o inválida"]},
                status_code=422,
            )
        db.add(
            GovernmentBudgetCauseEvidence(
                cause_id=str(causa.id),
                company_id=ctx.company_id,
                resource_type=evidencia["tipo"],
                resource_id=evidencia["id"],
                snapshot=snapshot,
            )
        )
    db.add(
        GovernmentBudgetCauseHistory(
            cause_id=str(causa.id),
            company_id=ctx.company_id,
            evento="PREPARADO",
            actor_id=ctx.user_id,
            instantanea={"estado": causa.estado, "monto": str(causa.monto), "version": causa.version},
        )
    )
    record_audit(
        db,
        action="GOV_BUDGET_CAUSE_DRAFT_CREATED",
        entity_type="GovernmentBudgetCause",
        entity_id=str(causa.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={"compromiso": compromiso.codigo, "monto": str(causa.monto), "politica": politica.codigo},
    )
    db.flush()
    return _causa_a_dict(db, ctx, causa, incluir_controles=True)


def _actualizar_causa(
    db: Session,
    ctx: CompanyContext,
    causa_id: str,
    version: int | None,
    cuerpo: dict[str, Any],
) -> dict[str, Any]:
    if version is None:
        raise KontrolError(
            "GOV_BUDGET_CAUSE_IF_MATCH_REQUIRED",
            "Se requiere la versión del causado",
            status_code=428,
        )
    causa = _causa_por_id(db, ctx, causa_id)
    if causa.estado != "BORRADOR":
        raise ConflictError(
            "GOV_BUDGET_CAUSE_NOT_DRAFT",
            "Solo los causados en borrador pueden actualizarse",
        )
    if causa.version != version:
        raise ConflictError(
            "GOV_BUDGET_CAUSE_STALE",
            "El causado fue cambiado por otro usuario",
            details={"version_actual": causa.version},
        )
    year_id = causa.year_id
    compromiso_id = causa.commitment_id
    politica_id = cuerpo.get("politica_id", causa.policy_id)
    fecha_efectiva = cuerpo.get("fecha_efectiva", causa.fecha_efectiva)
    if not isinstance(politica_id, str):
        raise _invalida("politica_id debe ser texto")
    if not isinstance(fecha_efectiva, date):
        raise _invalida("fecha_efectiva debe ser fecha")
    compromiso = _validar_compromiso(db, ctx, year_id, compromiso_id)
    _validar_fecha_efectiva(db, ctx, year_id, compromiso, fecha_efectiva)
    politica = _validar_politica_vigente(db, ctx, politica_id, fecha_efectiva)
    if "lineas" in cuerpo:
        lineas = cuerpo.get("lineas")
        if not isinstance(lineas, list) or not 1 <= len(lineas) <= 20:
            raise _invalida("Debe indicar entre 1 y 20 líneas")
        lineas_validas = []
        for linea in lineas:
            if not isinstance(linea, dict):
                raise _invalida("lineas contiene elementos inválidos")
            linea_compromiso_id = linea.get("linea_compromiso_id")
            monto = linea.get("monto")
            if not isinstance(linea_compromiso_id, str):
                raise _invalida("linea_compromiso_id es obligatorio")
            if not isinstance(monto, Decimal) or not _validar_decimal(monto, "monto"):
                raise _invalida("El monto debe ser un decimal mayor a 0 con hasta 2 decimales")
            lineas_validas.append({"linea_compromiso_id": linea_compromiso_id, "monto": monto})
        _validar_montos(db, compromiso_id, lineas_validas, str(causa.id))
    else:
        lineas_validas = [
            {"linea_compromiso_id": linea_causa.commitment_line_id, "monto": linea_causa.monto}
            for linea_causa in _lineas_causa(db, str(causa.id))
        ]
    if "evidencias" in cuerpo:
        evidencias = cuerpo.get("evidencias")
        if not isinstance(evidencias, list) or len(evidencias) > 30:
            raise _invalida("evidencias debe ser una lista de hasta 30 elementos")
        evidencias_validas = []
        for evidencia in evidencias:
            if not isinstance(evidencia, dict):
                raise _invalida("evidencias contiene elementos inválidos")
            tipo = evidencia.get("tipo")
            recurso_id = evidencia.get("id")
            if not isinstance(tipo, str) or not isinstance(recurso_id, str):
                raise _invalida("tipo e id de evidencia son obligatorios")
            evidencias_validas.append({"tipo": tipo, "id": recurso_id})
        _validar_evidencias_validas(
            db,
            ctx,
            year_id,
            compromiso_id,
            evidencias_validas,
        )
    else:
        evidencias_validas = [
            {"tipo": e.resource_type, "id": e.resource_id}
            for e in _evidencias_causa(db, str(causa.id))
        ]
    fuente_tipo = cuerpo.get("fuente_tipo", causa.source_resource_type)
    fuente_id = cuerpo.get("fuente_id", causa.source_resource_id)
    _validar_fuente(db, ctx, compromiso_id, fuente_tipo, fuente_id)
    concepto = cuerpo.get("concepto", causa.concepto)
    if not isinstance(concepto, str) or not 10 <= len(concepto) <= 500:
        raise _invalida("El concepto debe tener entre 10 y 500 caracteres")
    monto_total = sum(
        (Decimal(str(linea["monto"])) for linea in lineas_validas),
        Decimal("0.00"),
    )
    causa.policy_id = politica_id
    causa.policy_version = politica.version
    causa.fecha_efectiva = fecha_efectiva
    causa.monto = monto_total
    causa.concepto = concepto
    causa.beneficiario = cuerpo.get("beneficiario", causa.beneficiario)
    if "fuente_tipo" in cuerpo or "fuente_id" in cuerpo:
        causa.source_resource_type = fuente_tipo
        causa.source_resource_id = fuente_id
    if "autoridad_cargo_id" in cuerpo:
        autoridad_cargo_id = cuerpo.get("autoridad_cargo_id")
        if autoridad_cargo_id is not None and not isinstance(autoridad_cargo_id, str):
            raise _invalida("autoridad_cargo_id debe ser texto")
        causa.autoridad_cargo_id = autoridad_cargo_id
    if "lineas" in cuerpo:
        for linea in _lineas_causa(db, str(causa.id)):
            db.delete(linea)
        db.flush()
        for linea in lineas_validas:
            db.add(
                GovernmentBudgetCauseLine(
                    cause_id=str(causa.id),
                    company_id=ctx.company_id,
                    commitment_line_id=linea["linea_compromiso_id"],
                    monto=linea["monto"],
                )
            )
    if "evidencias" in cuerpo:
        for evidencia in _evidencias_causa(db, str(causa.id)):
            db.delete(evidencia)
        db.flush()
        for evidencia in evidencias_validas:
            snapshot = _evidencia_snapshot(
                db,
                ctx,
                year_id,
                compromiso_id,
                evidencia["tipo"],
                evidencia["id"],
            )
            if snapshot is None:
                raise KontrolError(
                    code="GOV_BUDGET_CAUSE_EVIDENCE_INVALID",
                    message="La evidencia no existe o no es válida",
                    field_errors={"evidencias": ["Evidencia inexistente o inválida"]},
                    status_code=422,
                )
            db.add(
                GovernmentBudgetCauseEvidence(
                    cause_id=str(causa.id),
                    company_id=ctx.company_id,
                    resource_type=evidencia["tipo"],
                    resource_id=evidencia["id"],
                    snapshot=snapshot,
                )
            )
    causa.version += 1
    db.add(
        GovernmentBudgetCauseHistory(
            cause_id=str(causa.id),
            company_id=ctx.company_id,
            evento="ACTUALIZADO",
            actor_id=ctx.user_id,
            instantanea={"estado": causa.estado, "monto": str(causa.monto), "version": causa.version},
        )
    )
    record_audit(
        db,
        action="GOV_BUDGET_CAUSE_DRAFT_UPDATED",
        entity_type="GovernmentBudgetCause",
        entity_id=str(causa.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={"monto": str(causa.monto), "version": causa.version},
    )
    db.flush()
    return _causa_a_dict(db, ctx, causa, incluir_controles=True)


def _formalizar_causa(
    db: Session,
    ctx: CompanyContext,
    causa_id: str,
    version: int | None,
) -> dict[str, Any]:
    if version is None:
        raise KontrolError(
            "GOV_BUDGET_CAUSE_IF_MATCH_REQUIRED",
            "Se requiere la versión del causado",
            status_code=428,
        )
    causa = _causa_por_id(db, ctx, causa_id)
    if causa.estado != "BORRADOR":
        raise ConflictError(
            "GOV_BUDGET_CAUSE_NOT_DRAFT",
            "Solo los causados en borrador pueden formalizarse",
        )
    if causa.version != version:
        raise ConflictError(
            "GOV_BUDGET_CAUSE_STALE",
            "El causado fue cambiado por otro usuario",
            details={"version_actual": causa.version},
        )
    year = _ejercicio_de_empresa(db, ctx, causa.year_id, bloquear=True)
    if year.estado not in ("APROBADO", "RECONDUCIDO"):
        raise _estado_invalido()
    compromiso = db.scalar(
        select(GovernmentBudgetCommitment)
        .where(
            GovernmentBudgetCommitment.company_id == ctx.company_id,
            GovernmentBudgetCommitment.id == causa.commitment_id,
        )
        .with_for_update()
    )
    if compromiso is None or compromiso.estado != "VIGENTE" or compromiso.year_id != causa.year_id:
        raise KontrolError(
            code="GOV_BUDGET_CAUSE_COMMITMENT_INVALID",
            message="El compromiso no es válido para el causado",
            field_errors={"compromiso_id": ["Compromiso inválido"]},
            status_code=422,
        )
    politica = _validar_politica_vigente(db, ctx, causa.policy_id, causa.fecha_efectiva)
    _validar_fecha_efectiva(db, ctx, causa.year_id, compromiso, causa.fecha_efectiva)
    lineas_causa = _lineas_causa(db, str(causa.id))
    for linea in lineas_causa:
        linea_compromiso = db.get(GovernmentBudgetCommitmentLine, linea.commitment_line_id)
        if linea_compromiso is None:
            raise _invalida("La línea del compromiso no existe")
        pendiente = _pendiente_de_linea(db, linea_compromiso, str(causa.id))
        if linea.monto > pendiente:
            raise KontrolError(
                code="GOV_BUDGET_CAUSE_OVER_COMMITMENT",
                message="El monto supera el pendiente de la línea del compromiso",
                field_errors={"lineas": ["Monto superior al pendiente"]},
                details={"linea": str(linea_compromiso.id), "pendiente": str(pendiente), "solicitado": str(linea.monto)},
                status_code=422,
            )
    evidencias = [
        {"tipo": e.resource_type, "id": e.resource_id}
        for e in _evidencias_causa(db, str(causa.id))
    ]
    _validar_evidencias_validas(
        db,
        ctx,
        causa.year_id,
        causa.commitment_id,
        evidencias,
    )
    _exigir_completitud(
        db,
        ctx,
        causa.year_id,
        causa.commitment_id,
        politica,
        causa.fecha_efectiva,
        evidencias,
    )
    autoridad_cargo_id = causa.autoridad_cargo_id
    if not isinstance(autoridad_cargo_id, str):
        raise KontrolError(
            code="GOV_BUDGET_CAUSE_AUTHORITY_INVALID",
            message="La autoridad es obligatoria",
            field_errors={"autoridad_cargo_id": ["Autoridad obligatoria"]},
            status_code=422,
        )
    cargo = db.scalar(
        select(GovernmentPosition).where(
            GovernmentPosition.company_id == ctx.company_id,
            GovernmentPosition.id == autoridad_cargo_id,
        )
    )
    if cargo is None:
        raise KontrolError(
            code="GOV_BUDGET_CAUSE_AUTHORITY_INVALID",
            message="El cargo de autoridad no existe",
            field_errors={"autoridad_cargo_id": ["Cargo inexistente"]},
            status_code=422,
        )
    hoy = hoy_de_negocio()
    if not _autoridad_valida(
        db,
        ctx.company_id,
        str(cargo.id),
        hoy,
        politica.competencia_accion,
        politica.competencia_materia,
    ):
        raise KontrolError(
            code="GOV_BUDGET_CAUSE_AUTHORITY_INVALID",
            message="El cargo no tiene la competencia en vigor",
            field_errors={"autoridad_cargo_id": ["Competencia ausente"]},
            status_code=422,
        )
    exigir_autoridad_funcional(
        db,
        ctx,
        str(cargo.id),
        politica.competencia_accion,
        politica.competencia_materia,
    )
    competencias = competencias_en_vigor(db, cargo, hoy)
    for competencia in competencias:
        if (
            competencia["accion"] == politica.competencia_accion
            and competencia["materia"] == politica.competencia_materia
            and competencia["tipo_limite"] == "MONTO"
        ):
            limite = verificar_limite(
                db,
                ctx,
                year.moneda_funcional or "",
                causa.monto,
                competencia["monto"],
                competencia["moneda"],
                hoy,
                bloquear=True,
                exigir=True,
            )
            if not limite.get("dentro_del_limite", False):
                raise KontrolError(
                    code="GOV_BUDGET_CAUSE_AUTHORITY_AMOUNT_EXCEEDED",
                    message="El monto excede el límite de la competencia de la autoridad",
                    field_errors={"autoridad_cargo_id": ["Monto excedido"]},
                    status_code=422,
                )
    evaluar_antes_de_actuar(
        db,
        ctx,
        "BUD09_CAUSAR",
        "GovernmentBudgetCommitment",
        str(compromiso.id),
    )
    numero_maximo = db.scalar(
        select(func.max(GovernmentBudgetCause.numero)).where(
            GovernmentBudgetCause.company_id == ctx.company_id,
            GovernmentBudgetCause.year_id == causa.year_id,
        )
    )
    numero = (numero_maximo or 0) + 1
    configuracion = _patron_actual(db, ctx)
    codigo = _render_patron(configuracion.patron, year.anio, numero)
    lineas_snapshot = []
    for linea in lineas_causa:
        linea_compromiso = db.get(GovernmentBudgetCommitmentLine, linea.commitment_line_id)
        detalle = _linea_detalle(db, linea_compromiso) if linea_compromiso is not None else {}
        lineas_snapshot.append(
            {
                "linea": detalle.get("linea"),
                "partida": detalle.get("partida"),
                "categoria": detalle.get("categoria"),
                "fuente": detalle.get("fuente"),
                "unidad": detalle.get("unidad"),
                "monto": str(linea.monto),
            }
        )
    evidencias_snapshot = []
    for evidencia in _evidencias_causa(db, str(causa.id)):
        evidencias_snapshot.append(evidencia.snapshot)
    official_id = _funcionario_del_actor(db, ctx)
    funcionario_nombre: str | None = None
    if official_id is not None:
        funcionario = db.get(GovernmentOfficial, official_id)
        if funcionario is not None:
            funcionario_nombre = funcionario.nombre
    snapshot = {
        "codigo": codigo,
        "ente": ctx.company_id,
        "anio": year.anio,
        "moneda": causa.moneda,
        "monto": str(causa.monto),
        "fecha_efectiva": causa.fecha_efectiva.isoformat(),
        "registrado_en": causa.created_at.isoformat(),
        "concepto": causa.concepto,
        "beneficiario": causa.beneficiario,
        "compromiso": {
            "id": str(compromiso.id),
            "codigo": compromiso.codigo,
            "huella": compromiso.huella,
        },
        "politica": {
            "id": str(politica.id),
            "codigo": politica.codigo,
            "version": politica.version,
            "tipo_gasto": politica.tipo_gasto,
            "disparador": politica.disparador,
            "tipo_regla": politica.tipo_regla,
            "fundamento": politica.fundamento,
        },
        "lineas": lineas_snapshot,
        "evidencias": evidencias_snapshot,
        "autoridad": {
            "cargo_id": str(cargo.id),
            "cargo": cargo.name,
            "unidad": _unidad_nombre(db, cargo.unit_id),
            "funcionario_id": official_id,
            "funcionario": funcionario_nombre,
            "usuario_id": ctx.user_id,
        },
        "fuente": {"tipo": causa.source_resource_type, "id": causa.source_resource_id},
    }
    huella = _sha256(snapshot)
    unidad_autoridad = _unidad_nombre(db, cargo.unit_id)
    causa.estado = "FORMALIZADO"
    causa.numero = numero
    causa.codigo = codigo
    causa.autoridad_cargo_id = str(cargo.id)
    causa.autoridad_cargo_codigo = cargo.code
    causa.autoridad_cargo_nombre = cargo.name
    causa.autoridad_unidad = unidad_autoridad
    causa.autoridad_funcionario_id = official_id
    causa.autoridad_funcionario_nombre = funcionario_nombre
    causa.formalizado_por = ctx.user_id
    causa.formalizado_en = instante_actual()
    causa.snapshot = snapshot
    causa.huella = huella
    causa.version += 1
    try:
        with db.begin_nested():
            db.flush()
    except IntegrityError as error:
        if es_violacion_unica(error, "uq_gov_budget_causes_year_id_numero") or es_violacion_unica(
            error, "uq_gov_budget_causes_company_id_codigo"
        ):
            raise ConflictError(
                "GOV_BUDGET_CAUSE_NUMBER_CONFLICT",
                "Conflicto de numeración, reintente",
            ) from error
        raise
    db.add(
        GovernmentBudgetCauseHistory(
            cause_id=str(causa.id),
            company_id=ctx.company_id,
            evento="FORMALIZADO",
            actor_id=ctx.user_id,
            instantanea={"estado": causa.estado, "monto": str(causa.monto), "version": causa.version},
        )
    )
    record_audit(
        db,
        action="GOV_BUDGET_CAUSE_FORMALIZED",
        entity_type="GovernmentBudgetCause",
        entity_id=str(causa.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={
            "autoridad_cargo": str(cargo.id),
            "codigo": causa.codigo,
            "compromiso": compromiso.codigo,
            "fecha_efectiva": causa.fecha_efectiva.isoformat(),
            "lineas": len(lineas_causa),
            "moneda": causa.moneda,
            "monto": str(causa.monto),
            "politica": politica.codigo,
        },
    )
    db.flush()
    return _causa_a_dict(db, ctx, causa, incluir_controles=True)


def _unidad_nombre(db: Session, unit_id: str | None) -> str | None:
    if unit_id is None:
        return None
    unit = db.get(GovernmentUnit, unit_id)
    return unit.name if unit is not None else None


def _sha256(valor: dict[str, Any]) -> str:
    import hashlib

    texto = json.dumps(valor, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def _anular_causa(
    db: Session,
    ctx: CompanyContext,
    causa_id: str,
    version: int | None,
    cuerpo: dict[str, Any],
) -> dict[str, Any]:
    if version is None:
        raise KontrolError(
            "GOV_BUDGET_CAUSE_IF_MATCH_REQUIRED",
            "Se requiere la versión del causado",
            status_code=428,
        )
    causa = _causa_por_id(db, ctx, causa_id)
    _ejercicio_de_empresa(db, ctx, causa.year_id, bloquear=True)
    if causa.estado != "FORMALIZADO":
        raise ConflictError(
            "GOV_BUDGET_CAUSE_NOT_FORMALIZED",
            "Solo los causados formalizados pueden anularse",
        )
    if ordenes_emitidas_de_causa(db, ctx.company_id, str(causa.id)):
        raise ConflictError(
            "GOV_BUDGET_CAUSE_HAS_PAYMENT_ORDERS",
            "El causado tiene órdenes de pago emitidas vigentes: anúlelas antes de anular el causado",
        )
    if causa.version != version:
        raise ConflictError(
            "GOV_BUDGET_CAUSE_STALE",
            "El causado fue cambiado por otro usuario",
            details={"version_actual": causa.version},
        )
    motivo = cuerpo.get("motivo")
    if not isinstance(motivo, str) or not 10 <= len(motivo) <= 500:
        raise _invalida("El motivo es obligatorio y debe tener entre 10 y 500 caracteres")
    compromiso = db.scalar(
        select(GovernmentBudgetCommitment)
        .where(
            GovernmentBudgetCommitment.company_id == ctx.company_id,
            GovernmentBudgetCommitment.id == causa.commitment_id,
        )
        .with_for_update()
    )
    if compromiso is None:
        raise _invalida("El compromiso no existe")
    causa.estado = "ANULADO"
    causa.anulado_por = ctx.user_id
    causa.anulado_en = instante_actual()
    causa.motivo_anulacion = motivo
    causa.version += 1
    db.add(
        GovernmentBudgetCauseHistory(
            cause_id=str(causa.id),
            company_id=ctx.company_id,
            evento="ANULADO",
            actor_id=ctx.user_id,
            instantanea={"estado": causa.estado, "monto": str(causa.monto), "version": causa.version},
        )
    )
    record_audit(
        db,
        action="GOV_BUDGET_CAUSE_ANNULLED",
        entity_type="GovernmentBudgetCause",
        entity_id=str(causa.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={"codigo": causa.codigo, "motivo": causa.motivo_anulacion, "monto": str(causa.monto)},
    )
    db.flush()
    return _causa_a_dict(db, ctx, causa, incluir_controles=True)


def _listar_causados(
    db: Session,
    ctx: CompanyContext,
    year_id: str,
    estado: str | None,
    compromiso_id: str | None,
    desde: date | None,
    hasta: date | None,
    q: str | None,
) -> dict[str, Any]:
    _ejercicio_de_empresa(db, ctx, year_id, bloquear=False)
    query = select(GovernmentBudgetCause).where(
        GovernmentBudgetCause.company_id == ctx.company_id,
        GovernmentBudgetCause.year_id == year_id,
    )
    if estado is not None:
        query = query.where(GovernmentBudgetCause.estado == estado)
    if compromiso_id is not None:
        query = query.where(GovernmentBudgetCause.commitment_id == compromiso_id)
    if desde is not None:
        query = query.where(GovernmentBudgetCause.fecha_efectiva >= desde)
    if hasta is not None:
        query = query.where(GovernmentBudgetCause.fecha_efectiva <= hasta)
    if q is not None and q.strip() != "":
        texto = f"%{q.strip()}%"
        query = query.join(
            GovernmentBudgetCommitment,
            GovernmentBudgetCommitment.id == GovernmentBudgetCause.commitment_id,
        ).where(
            (GovernmentBudgetCause.codigo.ilike(texto))
            | (GovernmentBudgetCause.concepto.ilike(texto))
            | (GovernmentBudgetCause.beneficiario.ilike(texto))
            | (GovernmentBudgetCommitment.codigo.ilike(texto))
        )
    causas = list(db.scalars(query.order_by(GovernmentBudgetCause.created_at.desc())))
    items = []
    for causa in causas:
        compromiso = db.get(GovernmentBudgetCommitment, causa.commitment_id)
        if compromiso is None:
            continue
        totales = _totales_compromiso(db, str(compromiso.id), str(causa.id))
        unidad = None
        autoridad = None
        primera_linea = db.scalar(
            select(GovernmentBudgetCommitmentLine)
            .where(GovernmentBudgetCommitmentLine.commitment_id == str(compromiso.id))
            .order_by(GovernmentBudgetCommitmentLine.linea)
            .limit(1)
        )
        if primera_linea is not None:
            detalle = _linea_detalle(db, primera_linea)
            unidad = detalle.get("unidad")
        if causa.autoridad_cargo_nombre is not None:
            autoridad = causa.autoridad_cargo_nombre
            if causa.autoridad_funcionario_nombre is not None:
                autoridad = f"{autoridad} · {causa.autoridad_funcionario_nombre}"
        items.append(
            {
                "id": str(causa.id),
                "codigo": causa.codigo,
                "estado": causa.estado,
                "fecha_efectiva": causa.fecha_efectiva.isoformat(),
                "compromiso_id": str(compromiso.id),
                "compromiso_codigo": compromiso.codigo,
                "beneficiario": causa.beneficiario,
                "concepto": causa.concepto,
                "monto": str(causa.monto),
                "moneda": causa.moneda,
                "pendiente_compromiso": str(totales["pendiente"]),
                "unidad": unidad,
                "responsable": autoridad,
            }
        )
    return {"items": items, "total": len(items)}


def _reporte_causados_csv(
    db: Session,
    ctx: CompanyContext,
    year_id: str,
    estado: str | None,
    compromiso_id: str | None,
    desde: date | None,
    hasta: date | None,
    q: str | None,
) -> io.StringIO:
    datos = _listar_causados(db, ctx, year_id, estado, compromiso_id, desde, hasta, q)
    salida = io.StringIO()
    writer = csv.writer(salida, delimiter=";")
    writer.writerow(
        [
            "Código",
            "Fecha efectiva",
            "Compromiso",
            "Beneficiario",
            "Concepto",
            "Monto",
            "Moneda",
            "Pendiente del compromiso",
            "Estado",
            "Unidad",
            "Responsable",
        ]
    )
    for item in datos["items"]:
        writer.writerow(
            [
                item["codigo"] or "",
                item["fecha_efectiva"],
                item["compromiso_codigo"],
                item["beneficiario"] or "",
                item["concepto"],
                item["monto"],
                item["moneda"],
                item["pendiente_compromiso"],
                item["estado"],
                item["unidad"] or "",
                item["responsable"] or "",
            ]
        )
    return salida


def _opciones_causados(
    db: Session,
    ctx: CompanyContext,
    year_id: str,
    compromiso_id: str | None,
    hoy: date,
) -> dict[str, Any]:
    year = _ejercicio_de_empresa(db, ctx, year_id, bloquear=False)
    compromisos = []
    if compromiso_id is not None:
        compromiso = db.get(GovernmentBudgetCommitment, compromiso_id)
        if (
            compromiso is not None
            and compromiso.company_id == ctx.company_id
            and compromiso.year_id == year_id
        ):
            totales = _totales_compromiso(db, str(compromiso.id))
            lineas = []
            for linea in _lineas_compromiso(db, str(compromiso.id)):
                causado = causado_de_linea(db, str(linea.id))
                detalle = _linea_detalle(db, linea)
                pendiente_linea = linea.monto - causado
                lineas.append(
                    {
                        "id": str(linea.id),
                        "linea": linea.linea,
                        "partida": detalle.get("partida"),
                        "categoria": detalle.get("categoria"),
                        "unidad": detalle.get("unidad"),
                        "comprometido": str(linea.monto),
                        "causado": str(causado),
                        "pendiente": str(pendiente_linea),
                    }
                )
            if totales["pendiente"] > 0:
                compromisos.append(
                    {
                        "id": str(compromiso.id),
                        "codigo": compromiso.codigo,
                        "concepto": compromiso.concepto,
                        "fecha": compromiso.fecha.isoformat(),
                        "moneda": compromiso.moneda,
                        "total": str(totales["total"]),
                        "causado": str(totales["causado"]),
                        "pendiente": str(totales["pendiente"]),
                        "lineas": lineas,
                    }
                )
    else:
        compromisos_query = db.scalars(
            select(GovernmentBudgetCommitment).where(
                GovernmentBudgetCommitment.company_id == ctx.company_id,
                GovernmentBudgetCommitment.year_id == year_id,
                GovernmentBudgetCommitment.estado == "VIGENTE",
            )
        )
        for compromiso in compromisos_query:
            totales = _totales_compromiso(db, str(compromiso.id))
            if totales["pendiente"] <= 0:
                continue
            lineas = []
            for linea in _lineas_compromiso(db, str(compromiso.id)):
                causado = causado_de_linea(db, str(linea.id))
                detalle = _linea_detalle(db, linea)
                pendiente_linea = linea.monto - causado
                lineas.append(
                    {
                        "id": str(linea.id),
                        "linea": linea.linea,
                        "partida": detalle.get("partida"),
                        "categoria": detalle.get("categoria"),
                        "unidad": detalle.get("unidad"),
                        "comprometido": str(linea.monto),
                        "causado": str(causado),
                        "pendiente": str(pendiente_linea),
                    }
                )
            compromisos.append(
                {
                    "id": str(compromiso.id),
                    "codigo": compromiso.codigo,
                    "concepto": compromiso.concepto,
                    "fecha": compromiso.fecha.isoformat(),
                    "moneda": compromiso.moneda,
                    "total": str(totales["total"]),
                    "causado": str(totales["causado"]),
                    "pendiente": str(totales["pendiente"]),
                    "lineas": lineas,
                }
            )
    politicas = [
        _politica_a_dict(db, ctx, politica, incluir_historia=False)
        for politica in db.scalars(
            select(GovernmentBudgetCausingPolicy)
            .where(
                GovernmentBudgetCausingPolicy.company_id == ctx.company_id,
                GovernmentBudgetCausingPolicy.estado == "VIGENTE",
                GovernmentBudgetCausingPolicy.vigente_desde <= hoy,
            )
            .order_by(GovernmentBudgetCausingPolicy.created_at.desc())
        )
        if politica.vigente_hasta is None or politica.vigente_hasta >= hoy
    ]
    cargos = []
    for cargo in db.scalars(
        select(GovernmentPosition).where(GovernmentPosition.company_id == ctx.company_id)
    ):
        competencias = competencias_en_vigor(db, cargo, hoy)
        if not competencias:
            continue
        pares = {f"{c['accion']}·{c['materia']}" for c in competencias}
        coincide = any(
            f"{pol['competencia_accion']}·{pol['competencia_materia']}" in pares
            for pol in politicas
        )
        if coincide:
            cargos.append(
                {
                    "id": str(cargo.id),
                    "etiqueta": cargo.name,
                    "competencias": sorted(pares),
                }
            )
    evidencias = []
    if compromiso_id is not None:
        for tipo, clase in (
            ("CONTRACT_RECEIPT", GovernmentContractReceipt),
            ("CONTRACT_VALUATION", GovernmentContractValuation),
            ("CONTRACT_DELIVERY", GovernmentContractDeliverableSubmission),
            ("CONTRACT_INVOICE", GovernmentContractInvoice),
        ):
            for recurso in db.scalars(
                select(clase).where(
                    clase.company_id == ctx.company_id,
                    clase.contract_id.in_(
                        select(GovernmentContractBudgetAllocation.contract_id).where(
                            GovernmentContractBudgetAllocation.company_id == ctx.company_id,
                            GovernmentContractBudgetAllocation.certificate_id.in_(
                                select(GovernmentBudgetCommitmentLine.certificate_id).where(
                                    GovernmentBudgetCommitmentLine.commitment_id == compromiso_id
                                )
                            ),
                        )
                    ),
                )
            ):
                recurso_any: Any = recurso
                snapshot = _snapshot_evidencia_contractual(tipo, recurso_any)
                evidencias.append(
                    {
                        "tipo": tipo,
                        "id": str(recurso_any.id),
                        "etiqueta": recurso_any.numero,
                        "estado": recurso_any.estado,
                        "fecha": snapshot["fecha"] if snapshot else None,
                        "valida": snapshot is not None,
                    }
                )
    documentos = []
    for documento in db.scalars(
        select(Document).where(
            Document.company_id == ctx.company_id,
            Document.status == "ACTIVE",
            Document.id.in_(
                select(DocumentLink.document_id).where(
                    DocumentLink.company_id == ctx.company_id,
                    DocumentLink.resource_type == "GovernmentBudgetYear",
                    DocumentLink.resource_id == year_id,
                )
            ),
        )
    ):
        documentos.append(
            {
                "id": str(documento.id),
                "etiqueta": documento.title,
                "tipo_documental_id": documento.document_type_id,
                "tipo_documental": _etiqueta_documento(db, documento.document_type_id),
            }
        )
    return {
        "anio": year.anio,
        "moneda": year.moneda_funcional,
        "compromisos": compromisos,
        "politicas": politicas,
        "cargos": cargos,
        "evidencias": evidencias,
        "documentos": documentos,
    }


def _obtener_controles(db: Session, ctx: CompanyContext, causa_id: str) -> dict[str, Any]:
    causa = _causa_por_id(db, ctx, causa_id)
    return {"controles": _controles(db, ctx, causa)}


def obligaciones_pendientes_de_ordenar(
    db: Session,
    ctx: CompanyContext,
    year_id: str,
) -> list[dict[str, Any]]:
    """Proyección neutral: proyeccion_obligaciones."""
    causa_formalizadas = db.scalars(
        select(GovernmentBudgetCause).where(
            GovernmentBudgetCause.company_id == ctx.company_id,
            GovernmentBudgetCause.year_id == year_id,
            GovernmentBudgetCause.estado == "FORMALIZADO",
        )
    ).all()
    causa_ids = [str(causa.id) for causa in causa_formalizadas]
    montos_ordenados_por_causa = montos_ordenados(db, ctx.company_id, causa_ids)
    resultado = []
    for causa in causa_formalizadas:
        monto_ordenado = montos_ordenados_por_causa[str(causa.id)]
        resultado.append(
            {
                "id": str(causa.id),
                "codigo": causa.codigo,
                "beneficiario": causa.beneficiario,
                "moneda": causa.moneda,
                "fecha_efectiva": causa.fecha_efectiva.isoformat(),
                "monto_causado": str(causa.monto),
                "monto_ordenado": str(monto_ordenado),
                "pendiente_de_ordenar": str(pendiente_de_ordenar(causa.monto, monto_ordenado)),
            }
        )
    return resultado
