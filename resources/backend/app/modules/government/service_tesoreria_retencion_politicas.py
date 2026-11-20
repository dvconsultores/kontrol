"""Servicio de políticas y configuración de retención (TRE-05, T004).

Numeración, catálogo del ente (conceptos y condiciones) y ciclo de vida de
las políticas de retención versionadas con sus reglas. Sigue el patrón de
políticas de pago de TRE-04.
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext
from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.documents.models import Document
from app.modules.government.models import (
    ACCIONES_COMPETENCIA,
    BASES_RETENCION,
    CLASES_CONCEPTO_RETENCION,
    ESTADOS_CATALOGO_RETENCION,
    MATERIAS_COMPETENCIA,
    MODOS_REDONDEO_RETENCION,
    MONEDAS_LIMITE,
    MONEDAS_TASA,
    TIPOS_CATALOGO_RETENCION,
    TIPOS_PERSONA_RETENCION,
    TIPOS_REGLA_ORDEN_PAGO,
    UMBRALES_RETENCION,
    GovernmentWithholdingCatalogItem,
    GovernmentWithholdingHistory,
    GovernmentWithholdingPolicy,
    GovernmentWithholdingPolicyRule,
    GovernmentWithholdingSettings,
)
from app.modules.government.service_tesoreria_pago_politicas import _validar_act_id_pago
from app.shared.audit import record_audit
from app.shared.clock import hoy_de_negocio, instante_actual

PATRON_DEFECTO = "{ANIO}-{NUMERO:6}"

_CENTAVOS = Decimal("0.01")


def formatear_codigo(patron: str, anio: int, numero: int, serie: str) -> str:
    """Renderiza un código de comprobante a partir del patrón configurado."""
    resultado = patron.replace("{ANIO}", str(anio))
    resultado = resultado.replace("{SERIE}", serie)
    # {NUMERO:n}, n 1..10
    patron_numero = re.search(r"\{NUMERO:(\d+)\}", resultado)
    if patron_numero is not None:
        ancho = int(patron_numero.group(1))
        resultado = re.sub(r"\{NUMERO:\d+\}", str(numero).zfill(ancho), resultado)
    else:
        resultado = resultado.replace("{NUMERO}", str(numero))
    return resultado


def _validar_patron_retencion(patron: str) -> None:
    if "{" in patron or "}" in patron:
        tokens = list(re.finditer(r"\{[^{}]*\}", patron))
        if not tokens:
            raise KontrolError(
                code="GOV_WITHHOLDING_PATTERN_INVALID",
                message="patron contiene llaves incompletas o vacías",
                status_code=422,
                field_errors={"patron": ["El patrón contiene llaves inválidas"]},
            )
        numero_token = None
        serie_token = 0
        for token in tokens:
            valor = token.group(0)
            if valor == "{ANIO}":
                continue
            if valor.startswith("{NUMERO:"):
                if numero_token is not None:
                    raise KontrolError(
                        code="GOV_WITHHOLDING_PATTERN_INVALID",
                        message="patron contiene más de una variable {NUMERO:n}",
                        status_code=422,
                        field_errors={"patron": ["La variable {NUMERO:n} solo puede aparecer una vez"]},
                    )
                ancho = valor[8:-1]
                if not ancho.isdigit() or not 1 <= int(ancho) <= 10:
                    raise KontrolError(
                        code="GOV_WITHHOLDING_PATTERN_INVALID",
                        message="patron debe usar {NUMERO:n} con n entre 1 y 10",
                        status_code=422,
                        field_errors={"patron": ["La variable {NUMERO:n} debe tener n entre 1 y 10"]},
                    )
                numero_token = valor
                continue
            if valor == "{SERIE}":
                serie_token += 1
                if serie_token > 1:
                    raise KontrolError(
                        code="GOV_WITHHOLDING_PATTERN_INVALID",
                        message="patron contiene más de una variable {SERIE}",
                        status_code=422,
                        field_errors={"patron": ["La variable {SERIE} solo puede aparecer una vez"]},
                    )
                continue
            raise KontrolError(
                code="GOV_WITHHOLDING_PATTERN_INVALID",
                message="patron contiene una variable no permitida",
                status_code=422,
                field_errors={"patron": ["Variables permitidas: {ANIO}, {NUMERO:n}, {SERIE}"]},
            )
        if numero_token is None:
            raise KontrolError(
                code="GOV_WITHHOLDING_PATTERN_INVALID",
                message="patron debe incluir {NUMERO:n} una vez",
                status_code=422,
                field_errors={"patron": ["La variable {NUMERO:n} es obligatoria"]},
            )
    else:
        if re.search(r"\{\{|\}\}", patron):
            raise KontrolError(
                code="GOV_WITHHOLDING_PATTERN_INVALID",
                message="patron contiene llaves sueltas",
                status_code=422,
                field_errors={"patron": ["El patrón contiene llaves sueltas"]},
            )
        if not patron.strip():
            raise KontrolError(
                code="GOV_WITHHOLDING_PATTERN_INVALID",
                message="patron no puede estar vacío",
                status_code=422,
                field_errors={"patron": ["El patrón no puede estar vacío"]},
            )


def _patron_actual_retencion(db: Session, ctx: CompanyContext) -> GovernmentWithholdingSettings:
    fila = db.scalar(
        select(GovernmentWithholdingSettings).where(
            GovernmentWithholdingSettings.company_id == ctx.company_id
        )
    )
    if fila is None:
        fila = GovernmentWithholdingSettings(
            company_id=ctx.company_id,
            patron=PATRON_DEFECTO,
            version=1,
        )
        db.add(fila)
        db.flush()
    return fila


def configuracion_actual(db: Session, ctx: CompanyContext) -> dict[str, Any]:
    fila = _patron_actual_retencion(db, ctx)
    ejemplo = formatear_codigo(fila.patron, hoy_de_negocio().year, 1, "SERIE")
    return {"id": str(fila.id) if fila.id else None, "patron": fila.patron, "version": fila.version, "ejemplo": ejemplo}


def actualizar_configuracion(
    db: Session,
    ctx: CompanyContext,
    cuerpo: dict[str, Any],
    version: int | None,
) -> dict[str, Any]:
    if version is None:
        raise KontrolError(
            code="GOV_WITHHOLDING_IF_MATCH_REQUIRED",
            message="Se requiere la versión de la configuración",
            status_code=428,
        )
    fila = _patron_actual_retencion(db, ctx)
    if fila.version != version:
        raise ConflictError(
            "GOV_WITHHOLDING_VERSION_CONFLICT",
            "La configuración fue cambiada por otro usuario",
            details={"version_actual": fila.version},
        )
    patron = cuerpo.get("patron")
    if not isinstance(patron, str) or not 3 <= len(patron) <= 60:
        raise KontrolError(
            code="GOV_WITHHOLDING_PATTERN_INVALID",
            message="patron debe ser texto de entre 3 y 60 caracteres",
            status_code=422,
            field_errors={"patron": ["patron debe ser texto de entre 3 y 60 caracteres"]},
        )
    _validar_patron_retencion(patron)
    fila.patron = patron
    fila.version += 1
    if fila.id is None or fila not in db:
        db.add(fila)
    record_audit(
        db,
        action="GOV_WITHHOLDING_SETTINGS_UPDATED",
        entity_type="GovernmentWithholdingSettings",
        entity_id=str(ctx.company_id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={"patron": fila.patron},
    )
    db.flush()
    return configuracion_actual(db, ctx)


def listar_catalogo(db: Session, ctx: CompanyContext, tipo: str | None) -> list[dict[str, Any]]:
    consulta = select(GovernmentWithholdingCatalogItem).where(
        GovernmentWithholdingCatalogItem.company_id == ctx.company_id
    )
    if tipo is not None:
        consulta = consulta.where(GovernmentWithholdingCatalogItem.tipo == tipo)
    filas = db.scalars(
        consulta.order_by(
            GovernmentWithholdingCatalogItem.tipo,
            GovernmentWithholdingCatalogItem.codigo,
        )
    ).all()
    return [_catalogo_item_a_dict(item) for item in filas]


def _catalogo_item_a_dict(item: GovernmentWithholdingCatalogItem) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "tipo": item.tipo,
        "codigo": item.codigo,
        "nombre": item.nombre,
        "descripcion": item.descripcion,
        "clase": item.clase,
        "serie_comprobante": item.serie_comprobante,
        "estado": item.estado,
        "version": item.version,
    }


def _catalogo_item_de_empresa(
    db: Session, ctx: CompanyContext, item_id: str, bloquear: bool = False
) -> GovernmentWithholdingCatalogItem:
    consulta = select(GovernmentWithholdingCatalogItem).where(
        GovernmentWithholdingCatalogItem.company_id == ctx.company_id,
        GovernmentWithholdingCatalogItem.id == item_id,
    )
    if bloquear:
        consulta = consulta.with_for_update()
    item = db.scalar(consulta)
    if item is None:
        raise NotFoundError("GOV_WITHHOLDING_CATALOG_NOT_FOUND", "Elemento de catálogo no encontrado")
    return item


def _validar_catalogo_comun(
    db: Session,
    ctx: CompanyContext,
    cuerpo: dict[str, Any],
    *,
    actualizacion: bool = False,
) -> dict[str, Any]:
    errores: dict[str, list[str]] = {}
    tipo = cuerpo.get("tipo")
    if not actualizacion or "tipo" in cuerpo:
        if tipo not in TIPOS_CATALOGO_RETENCION:
            errores.setdefault("tipo", []).append(f"tipo debe ser uno de {TIPOS_CATALOGO_RETENCION}")
    codigo = cuerpo.get("codigo")
    if not actualizacion or "codigo" in cuerpo:
        if not isinstance(codigo, str) or not re.fullmatch(r"^[A-Z0-9][A-Z0-9_-]{1,19}$", codigo):
            errores.setdefault("codigo", []).append("codigo no cumple el patrón requerido")
    nombre = cuerpo.get("nombre")
    if not actualizacion or "nombre" in cuerpo:
        if not isinstance(nombre, str) or not 3 <= len(nombre) <= 120:
            errores.setdefault("nombre", []).append("nombre debe tener entre 3 y 120 caracteres")
    descripcion = cuerpo.get("descripcion")
    if "descripcion" in cuerpo:
        if descripcion is not None and (not isinstance(descripcion, str) or len(descripcion) > 2000):
            errores.setdefault("descripcion", []).append("descripcion debe tener como máximo 2000 caracteres")
    clase = cuerpo.get("clase")
    if "clase" in cuerpo:
        if clase is not None and clase not in CLASES_CONCEPTO_RETENCION:
            errores.setdefault("clase", []).append(f"clase debe ser una de {CLASES_CONCEPTO_RETENCION}")
    serie_comprobante = cuerpo.get("serie_comprobante")
    if "serie_comprobante" in cuerpo:
        if serie_comprobante is not None and (
            not isinstance(serie_comprobante, str) or not re.fullmatch(r"^[A-Z0-9-]{1,10}$", serie_comprobante)
        ):
            errores.setdefault("serie_comprobante", []).append("serie_comprobante no cumple el patrón requerido")
    if tipo == "CONCEPTO":
        if clase is None:
            errores.setdefault("clase", []).append("clase es obligatoria para CONCEPTO")
        if serie_comprobante is not None and "clase" in errores:
            pass
    elif tipo == "CONDICION":
        if clase is not None:
            errores.setdefault("clase", []).append("clase solo está permitida para CONCEPTO")
        if serie_comprobante is not None:
            errores.setdefault("serie_comprobante", []).append("serie_comprobante solo está permitido para CONCEPTO")
    if errores:
        raise KontrolError(
            code="GOV_WITHHOLDING_CATALOG_INVALID",
            message="Catálogo de retención inválido",
            status_code=422,
            field_errors=errores,
        )
    return {
        "tipo": tipo,
        "codigo": codigo,
        "nombre": nombre,
        "descripcion": descripcion,
        "clase": clase,
        "serie_comprobante": serie_comprobante,
        "estado": cuerpo.get("estado", "ACTIVO" if not actualizacion else None),
    }


def crear_elemento_catalogo(
    db: Session, ctx: CompanyContext, cuerpo: dict[str, Any]
) -> dict[str, Any]:
    validado = _validar_catalogo_comun(db, ctx, cuerpo)
    existente = db.scalar(
        select(GovernmentWithholdingCatalogItem).where(
            GovernmentWithholdingCatalogItem.company_id == ctx.company_id,
            GovernmentWithholdingCatalogItem.tipo == validado["tipo"],
            GovernmentWithholdingCatalogItem.codigo == validado["codigo"],
        )
    )
    if existente is not None:
        raise ConflictError(
            "GOV_WITHHOLDING_CATALOG_DUPLICATE",
            "Ya existe un elemento de catálogo con ese tipo y código",
        )
    item = GovernmentWithholdingCatalogItem(
        company_id=ctx.company_id,
        tipo=validado["tipo"],
        codigo=validado["codigo"],
        nombre=validado["nombre"],
        descripcion=validado.get("descripcion"),
        clase=validado["clase"],
        serie_comprobante=validado["serie_comprobante"],
        estado=validado["estado"] or "ACTIVO",
        version=0,
        created_by=ctx.user_id,
    )
    db.add(item)
    db.flush()
    record_audit(
        db,
        action="GOV_WITHHOLDING_CATALOG_CREATED",
        entity_type="GovernmentWithholdingCatalogItem",
        entity_id=str(item.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={"tipo": item.tipo, "codigo": item.codigo, "nombre": item.nombre},
    )
    db.flush()
    return _catalogo_item_a_dict(item)


def actualizar_elemento_catalogo(
    db: Session,
    ctx: CompanyContext,
    item_id: str,
    cuerpo: dict[str, Any],
    version: int | None,
) -> dict[str, Any]:
    if version is None:
        raise KontrolError(
            code="GOV_WITHHOLDING_IF_MATCH_REQUIRED",
            message="Se requiere la versión del elemento de catálogo",
            status_code=428,
        )
    item = _catalogo_item_de_empresa(db, ctx, item_id, bloquear=True)
    if item.version != version:
        raise ConflictError(
            "GOV_WITHHOLDING_VERSION_CONFLICT",
            "El elemento de catálogo fue cambiado por otro usuario",
            details={"version_actual": item.version},
        )
    actualizacion = dict(cuerpo)
    actualizacion["tipo"] = item.tipo
    actualizacion["codigo"] = item.codigo
    actualizacion["nombre"] = cuerpo.get("nombre", item.nombre)
    validado = _validar_catalogo_comun(db, ctx, actualizacion, actualizacion=True)
    if validado["clase"] is not None and item.tipo != "CONCEPTO":
        raise KontrolError(
            code="GOV_WITHHOLDING_CATALOG_INVALID",
            message="clase solo está permitida para CONCEPTO",
            status_code=422,
        )
    item.nombre = validado["nombre"]
    if "descripcion" in cuerpo:
        item.descripcion = validado["descripcion"]
    if "clase" in cuerpo:
        item.clase = validado["clase"]
    if "serie_comprobante" in cuerpo:
        item.serie_comprobante = validado["serie_comprobante"]
    if "estado" in cuerpo:
        estado = cuerpo.get("estado")
        if estado not in ESTADOS_CATALOGO_RETENCION:
            raise KontrolError(
                code="GOV_WITHHOLDING_CATALOG_INVALID",
                message="estado debe ser ACTIVO o INACTIVO",
                status_code=422,
            )
        item.estado = estado
    item.version += 1
    db.flush()
    record_audit(
        db,
        action="GOV_WITHHOLDING_CATALOG_UPDATED",
        entity_type="GovernmentWithholdingCatalogItem",
        entity_id=str(item.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={"tipo": item.tipo, "codigo": item.codigo, "estado": item.estado},
    )
    db.flush()
    return _catalogo_item_a_dict(item)


def elementos_por_codigo(
    db: Session,
    ctx: CompanyContext,
    tipo: str,
    codigos: list[str],
    solo_activos: bool = True,
) -> dict[str, GovernmentWithholdingCatalogItem]:
    if tipo not in TIPOS_CATALOGO_RETENCION:
        raise KontrolError(
            code="GOV_WITHHOLDING_CATALOG_INVALID",
            message="tipo de catálogo inválido",
            status_code=422,
        )
    filas = db.scalars(
        select(GovernmentWithholdingCatalogItem).where(
            GovernmentWithholdingCatalogItem.company_id == ctx.company_id,
            GovernmentWithholdingCatalogItem.tipo == tipo,
            GovernmentWithholdingCatalogItem.codigo.in_(codigos),
        )
    ).all()
    por_codigo = {item.codigo: item for item in filas}
    if solo_activos:
        desconocidos = [
            codigo for codigo in codigos if codigo not in por_codigo or por_codigo[codigo].estado != "ACTIVO"
        ]
    else:
        desconocidos = [codigo for codigo in codigos if codigo not in por_codigo]
    if desconocidos:
        raise KontrolError(
            code="GOV_WITHHOLDING_CATALOG_INVALID",
            message=f"Código(s) de catálogo desconocido(s) o inactivo(s): {', '.join(desconocidos)}",
            status_code=422,
        )
    return por_codigo


def _regla_a_dict(db: Session, ctx: CompanyContext, regla: GovernmentWithholdingPolicyRule) -> dict[str, Any]:
    concepto = db.scalar(
        select(GovernmentWithholdingCatalogItem).where(
            GovernmentWithholdingCatalogItem.company_id == ctx.company_id,
            GovernmentWithholdingCatalogItem.id == regla.concept_id,
        )
    )
    return {
        "id": str(regla.id),
        "orden": regla.orden,
        "concept_id": str(regla.concept_id) if regla.concept_id else None,
        "concepto_codigo": concepto.codigo if concepto else None,
        "concepto_nombre": concepto.nombre if concepto else None,
        "concepto_clase": concepto.clase if concepto else None,
        "base_tipo": regla.base_tipo,
        "base_porcentaje": str(regla.base_porcentaje) if regla.base_porcentaje is not None else None,
        "tasa": str(regla.tasa) if regla.tasa is not None else None,
        "umbral_tipo": regla.umbral_tipo,
        "umbral_monto": str(regla.umbral_monto) if regla.umbral_monto is not None else None,
        "umbral_multiplo": str(regla.umbral_multiplo) if regla.umbral_multiplo is not None else None,
        "umbral_moneda_tasa": regla.umbral_moneda_tasa,
        "sustraendo": str(regla.sustraendo) if regla.sustraendo is not None else None,
        "tope": str(regla.tope) if regla.tope is not None else None,
        "condiciones_exigidas": regla.condiciones_exigidas or [],
        "exclusiones": regla.exclusiones or [],
        "tipos_persona": regla.tipos_persona,
        "exige_comprobante": regla.exige_comprobante,
    }


def _politica_a_dict(
    db: Session, ctx: CompanyContext, policy: GovernmentWithholdingPolicy, incluir_reglas: bool = True
) -> dict[str, Any]:
    reglas: list[dict[str, Any]] = []
    if incluir_reglas:
        reglas_db = db.scalars(
            select(GovernmentWithholdingPolicyRule)
            .where(
                GovernmentWithholdingPolicyRule.company_id == ctx.company_id,
                GovernmentWithholdingPolicyRule.policy_id == str(policy.id),
            )
            .order_by(GovernmentWithholdingPolicyRule.orden)
        ).all()
        reglas = [_regla_a_dict(db, ctx, regla) for regla in reglas_db]
    resultado: dict[str, Any] = {
        "id": str(policy.id),
        "codigo": policy.codigo,
        "numero_version": policy.numero_version,
        "version_anterior_id": str(policy.version_anterior_id) if policy.version_anterior_id else None,
        "nombre": policy.nombre,
        "descripcion": policy.descripcion,
        "moneda": policy.moneda,
        "tipo_regla": policy.tipo_regla,
        "estado_verificacion": policy.estado_verificacion,
        "fuente_descripcion": policy.fuente_descripcion,
        "fuente_referencia": policy.fuente_referencia,
        "fuente_documento_id": str(policy.fuente_documento_id) if policy.fuente_documento_id else None,
        "act_id": str(policy.act_id) if policy.act_id else None,
        "aprobador_competencia_accion": policy.aprobador_competencia_accion,
        "aprobador_competencia_materia": policy.aprobador_competencia_materia,
        "permite_ajuste": policy.permite_ajuste,
        "redondeo_decimales": policy.redondeo_decimales,
        "redondeo_modo": policy.redondeo_modo,
        "vigente_desde": policy.vigente_desde.isoformat() if policy.vigente_desde else None,
        "vigente_hasta": policy.vigente_hasta.isoformat() if policy.vigente_hasta else None,
        "fundamento": policy.fundamento,
        "estado": policy.estado,
        "activada_por": str(policy.activada_por) if policy.activada_por else None,
        "activada_en": policy.activada_en.isoformat() if policy.activada_en else None,
        "cerrada_por": str(policy.cerrada_por) if policy.cerrada_por else None,
        "cerrada_en": policy.cerrada_en.isoformat() if policy.cerrada_en else None,
        "motivo_cierre": policy.motivo_cierre,
        "version": policy.version,
        "created_at": policy.created_at.isoformat() if policy.created_at else None,
    }
    if incluir_reglas:
        resultado["reglas"] = reglas
    else:
        resultado["reglas_count"] = len(reglas)
    return resultado


def _historia(
    db: Session,
    ctx: CompanyContext,
    policy: GovernmentWithholdingPolicy,
    evento: str,
) -> None:
    db.add(
        GovernmentWithholdingHistory(
            company_id=ctx.company_id,
            recurso="POLITICA",
            recurso_id=str(policy.id),
            evento=evento,
            actor_id=ctx.user_id,
            instantanea=_politica_a_dict(db, ctx, policy),
            created_by=ctx.user_id,
        )
    )
    db.flush()


def _auditar_politica(
    db: Session,
    ctx: CompanyContext,
    action: str,
    policy: GovernmentWithholdingPolicy,
    after: dict[str, Any],
) -> None:
    record_audit(
        db,
        action=action,
        entity_type="GovernmentWithholdingPolicy",
        entity_id=str(policy.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after=after,
    )


def politica_de_empresa(
    db: Session,
    ctx: CompanyContext,
    policy_id: str,
    bloquear: bool = False,
) -> GovernmentWithholdingPolicy:
    consulta = select(GovernmentWithholdingPolicy).where(
        GovernmentWithholdingPolicy.company_id == ctx.company_id,
        GovernmentWithholdingPolicy.id == policy_id,
    )
    if bloquear:
        consulta = consulta.with_for_update()
    policy = db.scalar(consulta)
    if policy is None:
        raise NotFoundError("GOV_WITHHOLDING_POLICY_NOT_FOUND", "Política de retención no encontrada")
    return policy


def listar_politicas(
    db: Session, ctx: CompanyContext, estado: str | None
) -> list[dict[str, Any]]:
    consulta = select(GovernmentWithholdingPolicy).where(
        GovernmentWithholdingPolicy.company_id == ctx.company_id
    )
    if estado is not None:
        consulta = consulta.where(GovernmentWithholdingPolicy.estado == estado)
    filas = db.scalars(
        consulta.order_by(
            GovernmentWithholdingPolicy.codigo,
            GovernmentWithholdingPolicy.numero_version.desc(),
        )
    ).all()
    return [_politica_a_dict(db, ctx, policy, incluir_reglas=False) for policy in filas]


def obtener_politica(db: Session, ctx: CompanyContext, policy_id: str) -> dict[str, Any]:
    policy = politica_de_empresa(db, ctx, policy_id)
    return _politica_a_dict(db, ctx, policy)


def _asegurar_decimal(valor: Any, campo: str, *, minimo: Decimal | None = None, maximo: Decimal | None = None) -> Decimal:
    try:
        decimal = Decimal(str(valor))
    except (InvalidOperation, ValueError):
        raise KontrolError(
            code="GOV_WITHHOLDING_RULE_INVALID",
            message=f"{campo} no es un número válido",
            status_code=422,
            field_errors={campo: ["Debe ser un número decimal válido"]},
        ) from None
    if minimo is not None and decimal < minimo:
        raise KontrolError(
            code="GOV_WITHHOLDING_RULE_INVALID",
            message=f"{campo} debe ser mayor o igual a {minimo}",
            status_code=422,
            field_errors={campo: [f"Debe ser mayor o igual a {minimo}"]},
        )
    if maximo is not None and decimal > maximo:
        raise KontrolError(
            code="GOV_WITHHOLDING_RULE_INVALID",
            message=f"{campo} debe ser menor o igual a {maximo}",
            status_code=422,
            field_errors={campo: [f"Debe ser menor o igual a {maximo}"]},
        )
    return decimal


def validar_reglas(
    db: Session,
    ctx: CompanyContext,
    moneda: str,
    reglas: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    errores: dict[str, list[str]] = {}
    if not reglas:
        return []
    ordenes = [regla.get("orden") for regla in reglas]
    if any(not isinstance(orden, int) or orden < 1 for orden in ordenes):
        errores["reglas"] = ["orden debe ser un entero mayor o igual a 1"]
    if len(ordenes) != len(set(ordenes)):
        errores["reglas"] = ["orden no puede repetirse"]
    concept_ids = [regla.get("concept_id") for regla in reglas]
    if None in concept_ids or any(not isinstance(cid, str) or not cid.strip() for cid in concept_ids):
        errores["reglas"] = ["concept_id es obligatorio para cada regla"]
    else:
        conceptos = db.scalars(
            select(GovernmentWithholdingCatalogItem).where(
                GovernmentWithholdingCatalogItem.company_id == ctx.company_id,
                GovernmentWithholdingCatalogItem.id.in_(concept_ids),
            )
        ).all()
        conceptos_por_id = {str(item.id): item for item in conceptos}
        for indice, cid in enumerate(concept_ids):
            concepto = conceptos_por_id.get(str(cid))
            if concepto is None or concepto.tipo != "CONCEPTO" or concepto.estado != "ACTIVO":
                errores.setdefault(f"reglas.{indice}.concept_id", []).append("Debe ser un CONCEPTO ACTIVO")
        if len(concept_ids) != len(set(concept_ids)):
            errores["reglas"] = ["concept_id no puede repetirse en las reglas"]
    for indice, regla in enumerate(reglas):
        prefijo = f"reglas.{indice}"
        base_tipo = regla.get("base_tipo")
        if base_tipo not in BASES_RETENCION:
            errores.setdefault(f"{prefijo}.base_tipo", []).append("base_tipo debe ser MONTO_BRUTO o PORCENTAJE_DEL_BRUTO")
        base_porcentaje = regla.get("base_porcentaje")
        if base_tipo == "PORCENTAJE_DEL_BRUTO":
            if base_porcentaje is None:
                errores.setdefault(f"{prefijo}.base_porcentaje", []).append("base_porcentaje es obligatorio con PORCENTAJE_DEL_BRUTO")
            else:
                try:
                    decimal_bp = Decimal(str(base_porcentaje))
                    if not Decimal("0") < decimal_bp <= Decimal("100"):
                        raise InvalidOperation
                except (InvalidOperation, ValueError):
                    errores.setdefault(f"{prefijo}.base_porcentaje", []).append("base_porcentaje debe estar entre 0 y 100")
        elif base_porcentaje is not None:
            errores.setdefault(f"{prefijo}.base_porcentaje", []).append("base_porcentaje solo aplica con PORCENTAJE_DEL_BRUTO")

        tasa = regla.get("tasa")
        if tasa is None:
            errores.setdefault(f"{prefijo}.tasa", []).append("tasa es obligatoria")
        else:
            try:
                tasa_decimal = Decimal(str(tasa))
                if not Decimal("0") < tasa_decimal <= Decimal("100"):
                    raise InvalidOperation
            except (InvalidOperation, ValueError):
                errores.setdefault(f"{prefijo}.tasa", []).append("tasa debe estar entre 0 y 100")
        umbral_tipo = regla.get("umbral_tipo", "NINGUNO")
        if umbral_tipo not in UMBRALES_RETENCION:
            errores.setdefault(f"{prefijo}.umbral_tipo", []).append(f"umbral_tipo debe estar en {UMBRALES_RETENCION}")
        umbral_monto = regla.get("umbral_monto")
        umbral_multiplo = regla.get("umbral_multiplo")
        umbral_moneda_tasa = regla.get("umbral_moneda_tasa")
        if umbral_tipo == "MONTO":
            if umbral_monto is None:
                errores.setdefault(f"{prefijo}.umbral_monto", []).append("umbral_monto es obligatorio con MONTO")
            else:
                _asegurar_decimal(umbral_monto, f"{prefijo}.umbral_monto", minimo=Decimal("0"))
            if umbral_multiplo is not None:
                errores.setdefault(f"{prefijo}.umbral_multiplo", []).append("umbral_multiplo solo se permite con MULTIPLO_TASA")
            if umbral_moneda_tasa is not None:
                errores.setdefault(f"{prefijo}.umbral_moneda_tasa", []).append("umbral_moneda_tasa solo se permite con MULTIPLO_TASA")
        elif umbral_tipo == "MULTIPLO_TASA":
            if moneda != "VES":
                errores.setdefault(f"{prefijo}.umbral_tipo", []).append("MULTIPLO_TASA solo se permite con moneda VES")
            if umbral_multiplo is None:
                errores.setdefault(f"{prefijo}.umbral_multiplo", []).append("umbral_multiplo es obligatorio con MULTIPLO_TASA")
            else:
                try:
                    multiplo = Decimal(str(umbral_multiplo))
                    if multiplo <= Decimal("0"):
                        raise InvalidOperation
                except (InvalidOperation, ValueError):
                    errores.setdefault(f"{prefijo}.umbral_multiplo", []).append("umbral_multiplo debe ser mayor que 0")
            if umbral_moneda_tasa is None:
                errores.setdefault(f"{prefijo}.umbral_moneda_tasa", []).append("umbral_moneda_tasa es obligatorio con MULTIPLO_TASA")
            elif umbral_moneda_tasa not in MONEDAS_TASA:
                errores.setdefault(f"{prefijo}.umbral_moneda_tasa", []).append(f"umbral_moneda_tasa debe estar en {MONEDAS_TASA}")
            if umbral_monto is not None:
                errores.setdefault(f"{prefijo}.umbral_monto", []).append("umbral_monto solo se permite con MONTO")
        elif umbral_tipo == "NINGUNO":
            if umbral_monto is not None:
                errores.setdefault(f"{prefijo}.umbral_monto", []).append("umbral_monto solo se permite con MONTO")
            if umbral_multiplo is not None:
                errores.setdefault(f"{prefijo}.umbral_multiplo", []).append("umbral_multiplo solo se permite con MULTIPLO_TASA")
            if umbral_moneda_tasa is not None:
                errores.setdefault(f"{prefijo}.umbral_moneda_tasa", []).append("umbral_moneda_tasa solo se permite con MULTIPLO_TASA")
        else:
            errores.setdefault(f"{prefijo}.umbral_tipo", []).append("umbral_tipo no es válido")
        sustraendo = regla.get("sustraendo")
        if sustraendo is not None:
            _asegurar_decimal(sustraendo, f"{prefijo}.sustraendo", minimo=Decimal("0"))
        tope = regla.get("tope")
        if tope is not None:
            _asegurar_decimal(tope, f"{prefijo}.tope", minimo=Decimal("0.000001"))
        tipos_persona = regla.get("tipos_persona")
        if tipos_persona is not None:
            if not isinstance(tipos_persona, list) or not tipos_persona:
                errores.setdefault(f"{prefijo}.tipos_persona", []).append("tipos_persona debe ser una lista no vacía")
            else:
                if any(tp not in TIPOS_PERSONA_RETENCION for tp in tipos_persona):
                    errores.setdefault(f"{prefijo}.tipos_persona", []).append(f"tipos_persona debe estar incluido en {TIPOS_PERSONA_RETENCION}")
                if len(tipos_persona) != len(set(tipos_persona)):
                    errores.setdefault(f"{prefijo}.tipos_persona", []).append("tipos_persona no puede tener repetidos")
    for indice, regla in enumerate(reglas):
        prefijo = f"reglas.{indice}"
        condiciones = regla.get("condiciones_exigidas") or []
        exclusiones = regla.get("exclusiones") or []
        if condiciones and isinstance(condiciones, list):
            try:
                elementos_por_codigo(db, ctx, "CONDICION", condiciones)
            except KontrolError:
                errores.setdefault(f"{prefijo}.condiciones_exigidas", []).append("Contiene códigos desconocidos o inactivos")
        if exclusiones and isinstance(exclusiones, list):
            try:
                elementos_por_codigo(db, ctx, "CONDICION", exclusiones)
            except KontrolError:
                errores.setdefault(f"{prefijo}.exclusiones", []).append("Contiene códigos desconocidos o inactivos")
        if set(condiciones) & set(exclusiones):
            errores.setdefault(f"{prefijo}.condiciones_exigidas", []).append("condiciones_exigidas y exclusiones no deben tener intersección")
    if errores:
        raise KontrolError(
            code="GOV_WITHHOLDING_RULE_INVALID",
            message="Reglas de retención inválidas",
            status_code=422,
            field_errors=errores,
        )
    return reglas


def _validar_politica_comun(
    db: Session, ctx: CompanyContext, cuerpo: dict[str, Any], *, actualizacion: bool = False
) -> dict[str, Any]:
    errores: dict[str, list[str]] = {}
    estado_verificacion: str | None
    if not actualizacion:
        moneda = cuerpo.get("moneda")
        if moneda not in MONEDAS_LIMITE:
            errores.setdefault("moneda", []).append(f"moneda debe estar en {MONEDAS_LIMITE}")
        tipo_regla = cuerpo.get("tipo_regla", "INSTITUTIONAL_POLICY")
        if tipo_regla not in TIPOS_REGLA_ORDEN_PAGO:
            errores.setdefault("tipo_regla", []).append(f"tipo_regla debe estar en {TIPOS_REGLA_ORDEN_PAGO}")
        if tipo_regla == "LEGAL_MANDATORY":
            raise KontrolError(
                code="GOV_WITHHOLDING_LEGAL_SOURCE_UNVERIFIED",
                message="LEGAL_MANDATORY requiere verificación de fuente",
                status_code=422,
            )
        estado_verificacion = "PENDING_PIN"
    else:
        moneda = cuerpo.get("moneda")
        tipo_regla = cuerpo.get("tipo_regla")
        estado_verificacion = cuerpo.get("estado_verificacion")
        if "tipo_regla" in cuerpo:
            if tipo_regla not in TIPOS_REGLA_ORDEN_PAGO:
                errores.setdefault("tipo_regla", []).append(f"tipo_regla debe estar en {TIPOS_REGLA_ORDEN_PAGO}")
            if tipo_regla == "LEGAL_MANDATORY":
                raise KontrolError(
                    code="GOV_WITHHOLDING_LEGAL_SOURCE_UNVERIFIED",
                    message="LEGAL_MANDATORY requiere verificación de fuente",
                    status_code=422,
                )
    aprobador_accion = cuerpo.get("aprobador_competencia_accion")
    if not actualizacion or "aprobador_competencia_accion" in cuerpo:
        if aprobador_accion not in ACCIONES_COMPETENCIA:
            errores.setdefault("aprobador_competencia_accion", []).append(f"aprobador_competencia_accion debe estar en {ACCIONES_COMPETENCIA}")
    aprobador_materia = cuerpo.get("aprobador_competencia_materia")
    if not actualizacion or "aprobador_competencia_materia" in cuerpo:
        if aprobador_materia not in MATERIAS_COMPETENCIA:
            errores.setdefault("aprobador_competencia_materia", []).append(f"aprobador_competencia_materia debe estar en {MATERIAS_COMPETENCIA}")
    redondeo_decimales = cuerpo.get("redondeo_decimales", 2)
    if "redondeo_decimales" in cuerpo or not actualizacion:
        if not isinstance(redondeo_decimales, int) or not 0 <= redondeo_decimales <= 4:
            errores.setdefault("redondeo_decimales", []).append("redondeo_decimales debe ser un entero entre 0 y 4")
    redondeo_modo = cuerpo.get("redondeo_modo", "HALF_UP")
    if "redondeo_modo" in cuerpo or not actualizacion:
        if redondeo_modo not in MODOS_REDONDEO_RETENCION:
            errores.setdefault("redondeo_modo", []).append(f"redondeo_modo debe estar en {MODOS_REDONDEO_RETENCION}")
    vigente_desde = cuerpo.get("vigente_desde")
    vigente_hasta = cuerpo.get("vigente_hasta")
    if not actualizacion or "vigente_desde" in cuerpo:
        if not isinstance(vigente_desde, date):
            errores.setdefault("vigente_desde", []).append("vigente_desde es obligatorio")
    if not actualizacion or "vigente_hasta" in cuerpo:
        if vigente_hasta is not None and vigente_desde is not None and vigente_hasta < vigente_desde:
            errores.setdefault("vigente_hasta", []).append("vigente_hasta debe ser posterior o igual a vigente_desde")
    fuente_documento_id = cuerpo.get("fuente_documento_id")
    if fuente_documento_id is not None:
        documento = db.scalar(
            select(Document).where(
                Document.company_id == ctx.company_id,
                Document.id == fuente_documento_id,
            )
        )
        if documento is None:
            errores.setdefault("fuente_documento_id", []).append("El documento de fuente no existe")
    if errores:
        raise KontrolError(
            code="GOV_WITHHOLDING_POLICY_INVALID",
            message="Política de retención inválida",
            status_code=422,
            field_errors=errores,
        )
    return {
        "moneda": moneda,
        "tipo_regla": tipo_regla or "INSTITUTIONAL_POLICY",
        "estado_verificacion": estado_verificacion or "PENDING_PIN",
        "aprobador_competencia_accion": aprobador_accion,
        "aprobador_competencia_materia": aprobador_materia,
        "redondeo_decimales": redondeo_decimales,
        "redondeo_modo": redondeo_modo,
        "vigente_desde": vigente_desde,
        "vigente_hasta": vigente_hasta,
        "fuente_documento_id": fuente_documento_id,
    }


def _guardar_reglas(
    db: Session,
    ctx: CompanyContext,
    policy: GovernmentWithholdingPolicy,
    reglas: list[dict[str, Any]],
) -> None:
    for regla in reglas:
        db.add(
            GovernmentWithholdingPolicyRule(
                policy_id=str(policy.id),
                company_id=ctx.company_id,
                orden=regla["orden"],
                concept_id=regla["concept_id"],
                base_tipo=regla["base_tipo"],
                base_porcentaje=Decimal(str(regla["base_porcentaje"])) if regla.get("base_porcentaje") is not None else None,
                tasa=Decimal(str(regla["tasa"])) if regla.get("tasa") is not None else None,
                umbral_tipo=regla.get("umbral_tipo", "NINGUNO"),
                umbral_monto=Decimal(str(regla["umbral_monto"])) if regla.get("umbral_monto") is not None else None,
                umbral_multiplo=Decimal(str(regla["umbral_multiplo"])) if regla.get("umbral_multiplo") is not None else None,
                umbral_moneda_tasa=regla.get("umbral_moneda_tasa"),
                sustraendo=Decimal(str(regla["sustraendo"])) if regla.get("sustraendo") is not None else None,
                tope=Decimal(str(regla["tope"])) if regla.get("tope") is not None else None,
                condiciones_exigidas=regla.get("condiciones_exigidas") or [],
                exclusiones=regla.get("exclusiones") or [],
                tipos_persona=regla.get("tipos_persona"),
                exige_comprobante=bool(regla.get("exige_comprobante", False)),
                created_by=ctx.user_id,
            )
        )
        db.flush()


def crear_politica(
    db: Session, ctx: CompanyContext, cuerpo: dict[str, Any]
) -> dict[str, Any]:
    codigo = cuerpo.get("codigo")
    if not isinstance(codigo, str) or not codigo.strip():
        raise KontrolError(
            code="GOV_WITHHOLDING_POLICY_INVALID",
            message="codigo es obligatorio",
            status_code=422,
        )
    existente = db.scalar(
        select(GovernmentWithholdingPolicy).where(
            GovernmentWithholdingPolicy.company_id == ctx.company_id,
            GovernmentWithholdingPolicy.codigo == codigo,
        )
    )
    if existente is not None:
        raise ConflictError(
            "GOV_WITHHOLDING_POLICY_DUPLICATE",
            "El código de política de retención ya existe",
        )
    validado = _validar_politica_comun(db, ctx, cuerpo)
    if validado["tipo_regla"] == "LEGAL_MANDATORY":
        raise KontrolError(
            code="GOV_WITHHOLDING_LEGAL_SOURCE_UNVERIFIED",
            message="Las políticas LEGAL_MANDATORY requieren verificación de fuente",
            status_code=422,
        )
    cuerpo_reglas = cuerpo.get("reglas") or []
    if cuerpo_reglas:
        validar_reglas(db, ctx, validado["moneda"], cuerpo_reglas)
    policy = GovernmentWithholdingPolicy(
        company_id=ctx.company_id,
        codigo=codigo,
        numero_version=1,
        nombre=cuerpo.get("nombre"),
        descripcion=cuerpo.get("descripcion"),
        moneda=validado["moneda"],
        tipo_regla=validado["tipo_regla"],
        estado_verificacion=validado["estado_verificacion"],
        fuente_descripcion=cuerpo.get("fuente_descripcion"),
        fuente_referencia=cuerpo.get("fuente_referencia"),
        fuente_documento_id=validado["fuente_documento_id"],
        act_id=_validar_act_id_pago(db, ctx, cuerpo.get("act_id")),
        aprobador_competencia_accion=validado["aprobador_competencia_accion"],
        aprobador_competencia_materia=validado["aprobador_competencia_materia"],
        permite_ajuste=bool(cuerpo.get("permite_ajuste", False)),
        redondeo_decimales=validado["redondeo_decimales"],
        redondeo_modo=validado["redondeo_modo"],
        vigente_desde=validado["vigente_desde"],
        vigente_hasta=validado["vigente_hasta"],
        estado="BORRADOR",
        created_by=ctx.user_id,
    )
    db.add(policy)
    db.flush()
    if cuerpo_reglas:
        _guardar_reglas(db, ctx, policy, cuerpo_reglas)
    _historia(db, ctx, policy, "CREADA")
    _auditar_politica(
        db,
        ctx,
        "GOV_WITHHOLDING_POLICY_CREATED",
        policy,
        after={"codigo": policy.codigo, "nombre": policy.nombre, "moneda": policy.moneda},
    )
    db.flush()
    return _politica_a_dict(db, ctx, policy)


def actualizar_politica(
    db: Session,
    ctx: CompanyContext,
    policy_id: str,
    cuerpo: dict[str, Any],
    version: int | None,
) -> dict[str, Any]:
    if version is None:
        raise KontrolError(
            code="GOV_WITHHOLDING_IF_MATCH_REQUIRED",
            message="Se requiere la versión de la política",
            status_code=428,
        )
    policy = politica_de_empresa(db, ctx, policy_id, bloquear=True)
    if policy.estado != "BORRADOR":
        raise ConflictError(
            "GOV_WITHHOLDING_POLICY_NOT_DRAFT",
            "Solo las políticas en borrador pueden actualizarse",
        )
    if policy.version != version:
        raise ConflictError(
            "GOV_WITHHOLDING_VERSION_CONFLICT",
            "La política fue cambiada por otro usuario",
            details={"version_actual": policy.version},
        )
    combinado = dict(cuerpo)
    combinado.setdefault("moneda", policy.moneda)
    combinado.setdefault("tipo_regla", policy.tipo_regla)
    combinado.setdefault("aprobador_competencia_accion", policy.aprobador_competencia_accion)
    combinado.setdefault("aprobador_competencia_materia", policy.aprobador_competencia_materia)
    combinado.setdefault("redondeo_decimales", policy.redondeo_decimales)
    combinado.setdefault("redondeo_modo", policy.redondeo_modo)
    combinado.setdefault("vigente_desde", policy.vigente_desde)
    combinado.setdefault("vigente_hasta", policy.vigente_hasta)
    validado = _validar_politica_comun(db, ctx, combinado, actualizacion=True)
    if cuerpo.get("tipo_regla") == "LEGAL_MANDATORY":
        raise KontrolError(
            code="GOV_WITHHOLDING_LEGAL_SOURCE_UNVERIFIED",
            message="Las políticas LEGAL_MANDATORY requieren verificación de fuente",
            status_code=422,
        )
    if "reglas" in cuerpo:
        reglas = cuerpo["reglas"] or []
        validar_reglas(db, ctx, policy.moneda, reglas)
        db.query(GovernmentWithholdingPolicyRule).filter(
            GovernmentWithholdingPolicyRule.company_id == ctx.company_id,
            GovernmentWithholdingPolicyRule.policy_id == policy_id,
        ).delete()
        db.flush()
        _guardar_reglas(db, ctx, policy, reglas)
    if "nombre" in cuerpo:
        policy.nombre = cuerpo["nombre"]
    if "descripcion" in cuerpo:
        policy.descripcion = cuerpo["descripcion"]
    if "moneda" in cuerpo:
        policy.moneda = validado["moneda"]
    if "tipo_regla" in cuerpo:
        policy.tipo_regla = validado["tipo_regla"]
    if "estado_verificacion" in cuerpo:
        policy.estado_verificacion = cuerpo["estado_verificacion"]
    if "fuente_descripcion" in cuerpo:
        policy.fuente_descripcion = cuerpo["fuente_descripcion"]
    if "fuente_referencia" in cuerpo:
        policy.fuente_referencia = cuerpo["fuente_referencia"]
    if "fuente_documento_id" in cuerpo:
        policy.fuente_documento_id = validado["fuente_documento_id"]
    if "act_id" in cuerpo:
        policy.act_id = _validar_act_id_pago(db, ctx, cuerpo.get("act_id"))
    if "aprobador_competencia_accion" in cuerpo:
        policy.aprobador_competencia_accion = validado["aprobador_competencia_accion"]
    if "aprobador_competencia_materia" in cuerpo:
        policy.aprobador_competencia_materia = validado["aprobador_competencia_materia"]
    if "permite_ajuste" in cuerpo:
        policy.permite_ajuste = bool(cuerpo["permite_ajuste"])
    if "redondeo_decimales" in cuerpo:
        policy.redondeo_decimales = validado["redondeo_decimales"]
    if "redondeo_modo" in cuerpo:
        policy.redondeo_modo = validado["redondeo_modo"]
    if "vigente_desde" in cuerpo:
        policy.vigente_desde = validado["vigente_desde"]
    if "vigente_hasta" in cuerpo:
        policy.vigente_hasta = validado["vigente_hasta"]
    policy.version += 1
    _historia(db, ctx, policy, "ACTUALIZADA")
    _auditar_politica(
        db,
        ctx,
        "GOV_WITHHOLDING_POLICY_UPDATED",
        policy,
        after={"codigo": policy.codigo, "version": policy.numero_version},
    )
    db.flush()
    return _politica_a_dict(db, ctx, policy)


def activar_politica(
    db: Session,
    ctx: CompanyContext,
    policy_id: str,
    cuerpo: dict[str, Any],
    version: int | None,
) -> dict[str, Any]:
    if version is None:
        raise KontrolError(
            code="GOV_WITHHOLDING_IF_MATCH_REQUIRED",
            message="Se requiere la versión de la política",
            status_code=428,
        )
    policy = politica_de_empresa(db, ctx, policy_id, bloquear=True)
    if policy.estado != "BORRADOR":
        raise ConflictError(
            "GOV_WITHHOLDING_POLICY_NOT_DRAFT",
            "Solo las políticas en borrador pueden activarse",
        )
    if policy.version != version:
        raise ConflictError(
            "GOV_WITHHOLDING_VERSION_CONFLICT",
            "La política fue cambiada por otro usuario",
            details={"version_actual": policy.version},
        )
    fundamento = cuerpo.get("fundamento")
    if not isinstance(fundamento, str) or len(fundamento.strip()) < 20:
        raise KontrolError(
            code="GOV_WITHHOLDING_POLICY_INVALID",
            message="fundamento debe tener al menos 20 caracteres",
            status_code=422,
        )
    if not policy.fuente_descripcion or not policy.fuente_descripcion.strip():
        raise KontrolError(
            code="GOV_WITHHOLDING_POLICY_SOURCE_REQUIRED",
            message="La política requiere fuente_descripcion para activarse",
            status_code=422,
        )
    act_id = _validar_act_id_pago(db, ctx, cuerpo.get("act_id"))
    reglas = db.scalars(
        select(GovernmentWithholdingPolicyRule)
        .where(
            GovernmentWithholdingPolicyRule.company_id == ctx.company_id,
            GovernmentWithholdingPolicyRule.policy_id == policy_id,
        )
        .order_by(GovernmentWithholdingPolicyRule.orden)
    ).all()
    if not reglas:
        raise KontrolError(
            code="GOV_WITHHOLDING_POLICY_RULES_REQUIRED",
            message="La política debe tener al menos una regla para activarse",
            status_code=422,
        )
    reglas_dict = [
        {
            "orden": regla.orden,
            "concept_id": str(regla.concept_id),
            "base_tipo": regla.base_tipo,
            "base_porcentaje": str(regla.base_porcentaje) if regla.base_porcentaje is not None else None,
            "tasa": str(regla.tasa),
            "umbral_tipo": regla.umbral_tipo,
            "umbral_monto": str(regla.umbral_monto) if regla.umbral_monto is not None else None,
            "umbral_multiplo": str(regla.umbral_multiplo) if regla.umbral_multiplo is not None else None,
            "umbral_moneda_tasa": regla.umbral_moneda_tasa,
            "sustraendo": str(regla.sustraendo) if regla.sustraendo is not None else None,
            "tope": str(regla.tope) if regla.tope is not None else None,
            "condiciones_exigidas": regla.condiciones_exigidas or [],
            "exclusiones": regla.exclusiones or [],
            "tipos_persona": regla.tipos_persona,
            "exige_comprobante": regla.exige_comprobante,
        }
        for regla in reglas
    ]
    validar_reglas(db, ctx, policy.moneda, reglas_dict)
    ahora = instante_actual()
    nueva_vigente_desde = policy.vigente_desde
    if policy.version_anterior_id is not None:
        anterior = politica_de_empresa(db, ctx, policy.version_anterior_id)
        if anterior.estado == "VIGENTE":
            if nueva_vigente_desde <= anterior.vigente_desde:
                raise KontrolError(
                    code="GOV_WITHHOLDING_POLICY_INVALID",
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
                "GOV_WITHHOLDING_POLICY_CLOSED",
                anterior,
                after={"codigo": anterior.codigo, "version": anterior.numero_version, "motivo": anterior.motivo_cierre},
            )
    policy.fundamento = fundamento
    policy.act_id = act_id
    policy.estado = "VIGENTE"
    policy.activada_por = ctx.user_id
    policy.activada_en = ahora
    policy.vigente_desde = nueva_vigente_desde
    policy.version += 1
    _historia(db, ctx, policy, "ACTIVADA")
    _auditar_politica(
        db,
        ctx,
        "GOV_WITHHOLDING_POLICY_ACTIVATED",
        policy,
        after={
            "codigo": policy.codigo,
            "version": policy.numero_version,
            "fundamento": policy.fundamento,
            "fuente": policy.fuente_descripcion,
        },
    )
    db.flush()
    return _politica_a_dict(db, ctx, policy)


def cerrar_politica(
    db: Session,
    ctx: CompanyContext,
    policy_id: str,
    cuerpo: dict[str, Any],
    version: int | None,
) -> dict[str, Any]:
    if version is None:
        raise KontrolError(
            code="GOV_WITHHOLDING_IF_MATCH_REQUIRED",
            message="Se requiere la versión de la política",
            status_code=428,
        )
    policy = politica_de_empresa(db, ctx, policy_id, bloquear=True)
    if policy.estado != "VIGENTE":
        raise ConflictError(
            "GOV_WITHHOLDING_POLICY_NOT_ACTIVE",
            "Solo las políticas vigentes pueden cerrarse",
        )
    if policy.version != version:
        raise ConflictError(
            "GOV_WITHHOLDING_VERSION_CONFLICT",
            "La política fue cambiada por otro usuario",
            details={"version_actual": policy.version},
        )
    motivo = cuerpo.get("motivo")
    if not isinstance(motivo, str) or len(motivo.strip()) < 10:
        raise KontrolError(
            code="GOV_WITHHOLDING_POLICY_INVALID",
            message="motivo debe tener al menos 10 caracteres",
            status_code=422,
        )
    hoy = hoy_de_negocio()
    if policy.vigente_hasta is None or policy.vigente_hasta > hoy:
        policy.vigente_hasta = max(policy.vigente_desde, hoy) if policy.vigente_desde else hoy
    policy.estado = "CERRADA"
    policy.cerrada_por = ctx.user_id
    policy.cerrada_en = instante_actual()
    policy.motivo_cierre = motivo
    policy.version += 1
    _historia(db, ctx, policy, "CERRADA")
    _auditar_politica(
        db,
        ctx,
        "GOV_WITHHOLDING_POLICY_CLOSED",
        policy,
        after={"codigo": policy.codigo, "version": policy.numero_version, "motivo": motivo},
    )
    db.flush()
    return _politica_a_dict(db, ctx, policy)


def nueva_version_politica(
    db: Session, ctx: CompanyContext, policy_id: str
) -> dict[str, Any]:
    fuente = politica_de_empresa(db, ctx, policy_id, bloquear=True)
    if fuente.estado not in ("VIGENTE", "CERRADA"):
        raise ConflictError(
            "GOV_WITHHOLDING_POLICY_NOT_VERSIONABLE",
            "Solo las políticas vigentes o cerradas pueden versionarse",
        )
    existente_borrador = db.scalar(
        select(GovernmentWithholdingPolicy).where(
            GovernmentWithholdingPolicy.company_id == ctx.company_id,
            GovernmentWithholdingPolicy.codigo == fuente.codigo,
            GovernmentWithholdingPolicy.estado == "BORRADOR",
        )
    )
    if existente_borrador is not None:
        raise ConflictError(
            "GOV_WITHHOLDING_POLICY_DRAFT_EXISTS",
            "Ya existe un borrador para este código de política",
        )
    maximo = db.scalar(
        select(func.max(GovernmentWithholdingPolicy.numero_version)).where(
            GovernmentWithholdingPolicy.company_id == ctx.company_id,
            GovernmentWithholdingPolicy.codigo == fuente.codigo,
        )
    )
    numero_version = int(maximo) + 1 if maximo is not None else 1
    hoy = hoy_de_negocio()
    vigente_desde = hoy + timedelta(days=1) if (fuente.vigente_hasta is None or fuente.vigente_hasta >= hoy) else hoy
    nueva = GovernmentWithholdingPolicy(
        company_id=ctx.company_id,
        codigo=fuente.codigo,
        numero_version=numero_version,
        version_anterior_id=str(fuente.id),
        nombre=fuente.nombre,
        descripcion=fuente.descripcion,
        moneda=fuente.moneda,
        tipo_regla=fuente.tipo_regla,
        estado_verificacion=fuente.estado_verificacion,
        fuente_descripcion=fuente.fuente_descripcion,
        fuente_referencia=fuente.fuente_referencia,
        fuente_documento_id=fuente.fuente_documento_id,
        act_id=fuente.act_id,
        aprobador_competencia_accion=fuente.aprobador_competencia_accion,
        aprobador_competencia_materia=fuente.aprobador_competencia_materia,
        permite_ajuste=fuente.permite_ajuste,
        redondeo_decimales=fuente.redondeo_decimales,
        redondeo_modo=fuente.redondeo_modo,
        vigente_desde=vigente_desde,
        vigente_hasta=None,
        estado="BORRADOR",
        created_by=ctx.user_id,
    )
    db.add(nueva)
    db.flush()
    for regla in db.scalars(
        select(GovernmentWithholdingPolicyRule).where(
            GovernmentWithholdingPolicyRule.company_id == ctx.company_id,
            GovernmentWithholdingPolicyRule.policy_id == str(fuente.id),
        ).order_by(GovernmentWithholdingPolicyRule.orden)
    ):
        db.add(
            GovernmentWithholdingPolicyRule(
                policy_id=str(nueva.id),
                company_id=ctx.company_id,
                orden=regla.orden,
                concept_id=regla.concept_id,
                base_tipo=regla.base_tipo,
                base_porcentaje=regla.base_porcentaje,
                tasa=regla.tasa,
                umbral_tipo=regla.umbral_tipo,
                umbral_monto=regla.umbral_monto,
                umbral_multiplo=regla.umbral_multiplo,
                umbral_moneda_tasa=regla.umbral_moneda_tasa,
                sustraendo=regla.sustraendo,
                tope=regla.tope,
                condiciones_exigidas=regla.condiciones_exigidas,
                exclusiones=regla.exclusiones,
                tipos_persona=regla.tipos_persona,
                exige_comprobante=regla.exige_comprobante,
                created_by=ctx.user_id,
            )
        )
        db.flush()
    _historia(db, ctx, nueva, "VERSIONADA")
    _auditar_politica(
        db,
        ctx,
        "GOV_WITHHOLDING_POLICY_VERSIONED",
        nueva,
        after={
            "codigo": nueva.codigo,
            "version": nueva.numero_version,
            "version_anterior": fuente.numero_version,
        },
    )
    db.flush()
    return _politica_a_dict(db, ctx, nueva)


def historia_politica(db: Session, ctx: CompanyContext, policy_id: str) -> list[dict[str, Any]]:
    policy = politica_de_empresa(db, ctx, policy_id)
    filas = db.scalars(
        select(GovernmentWithholdingHistory)
        .where(
            GovernmentWithholdingHistory.company_id == ctx.company_id,
            GovernmentWithholdingHistory.recurso == "POLITICA",
            GovernmentWithholdingHistory.recurso_id == str(policy.id),
        )
        .order_by(GovernmentWithholdingHistory.created_at)
    ).all()
    return [
        {
            "id": str(historia.id),
            "evento": historia.evento,
            "numero_version": historia.instantanea.get("numero_version") if isinstance(historia.instantanea, dict) else None,
            "actor_id": str(historia.actor_id) if historia.actor_id else None,
            "created_at": historia.created_at.isoformat() if historia.created_at else None,
            "instantanea": historia.instantanea,
        }
        for historia in filas
    ]


def politicas_aplicables(
    db: Session, ctx: CompanyContext, moneda: str, fecha: date
) -> list[GovernmentWithholdingPolicy]:
    return list(
        db.scalars(
            select(GovernmentWithholdingPolicy).where(
                GovernmentWithholdingPolicy.company_id == ctx.company_id,
                GovernmentWithholdingPolicy.estado == "VIGENTE",
                GovernmentWithholdingPolicy.moneda == moneda,
                GovernmentWithholdingPolicy.vigente_desde <= fecha,
                (GovernmentWithholdingPolicy.vigente_hasta.is_(None))
                | (GovernmentWithholdingPolicy.vigente_hasta >= fecha),
            )
        ).all()
    )


def politica_aplicable(
    db: Session,
    ctx: CompanyContext,
    policy_id: str,
    moneda: str,
    fecha: date,
) -> GovernmentWithholdingPolicy:
    policy = politica_de_empresa(db, ctx, policy_id)
    if policy.moneda != moneda:
        raise KontrolError(
            code="GOV_WITHHOLDING_CURRENCY_MISMATCH",
            message="La moneda de la política no coincide con la solicitada",
            status_code=422,
        )
    if policy.estado != "VIGENTE":
        raise KontrolError(
            code="GOV_WITHHOLDING_POLICY_NOT_APPLICABLE",
            message="La política no está vigente",
            status_code=422,
        )
    if policy.vigente_desde is not None and policy.vigente_desde > fecha:
        raise KontrolError(
            code="GOV_WITHHOLDING_POLICY_NOT_APPLICABLE",
            message="La política no es aplicable en la fecha indicada",
            status_code=422,
        )
    if policy.vigente_hasta is not None and policy.vigente_hasta < fecha:
        raise KontrolError(
            code="GOV_WITHHOLDING_POLICY_NOT_APPLICABLE",
            message="La política no es aplicable en la fecha indicada",
            status_code=422,
        )
    return policy


def instantanea_politica(db: Session, ctx: CompanyContext, policy: GovernmentWithholdingPolicy) -> dict[str, Any]:
    return _politica_a_dict(db, ctx, policy)


def registrar_historia(
    db: Session,
    ctx: CompanyContext,
    recurso: str,
    recurso_id: str,
    evento: str,
    instantanea: dict[str, Any],
) -> None:
    db.add(
        GovernmentWithholdingHistory(
            company_id=ctx.company_id,
            recurso=recurso,
            recurso_id=recurso_id,
            evento=evento,
            actor_id=ctx.user_id,
            instantanea=instantanea,
            created_by=ctx.user_id,
        )
    )
    db.flush()


def auditar(
    db: Session,
    ctx: CompanyContext,
    accion: str,
    entidad: str,
    entidad_id: str,
    after: dict[str, Any],
) -> None:
    record_audit(
        db,
        action=accion,
        entity_type=entidad,
        entity_id=str(entidad_id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after=after,
    )
