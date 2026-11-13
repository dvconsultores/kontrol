"""Servicio de dominio del presupuesto anual (GOV-BUD-12 · BUD12)."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from datetime import UTC, date, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext
from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.documents.models import Document, DocumentLink, DocumentVersion
from app.modules.government.models import (
    GovernmentBudgetCategory,
    GovernmentBudgetClassifier,
    GovernmentBudgetClassifierItem,
    GovernmentBudgetProgramLevel,
    GovernmentBudgetYear,
    GovernmentBudgetYearFoundation,
    GovernmentBudgetYearHistory,
)
from app.modules.organization.models import Company
from app.shared.audit import record_audit
from app.shared.clock import hoy_de_negocio

ENTIDAD = "GovernmentBudgetYear"

RE_CODIGO_CATEGORIA = re.compile(r"^[0-9A-Za-z-]{1,20}$")
RE_CODIGO_PARTIDA = re.compile(r"^[0-9A-Za-z.-]{1,40}$")

CABECERA_PARTIDAS = ["tipo", "codigo", "denominacion", "nivel", "codigo_padre", "vigente_desde", "vigente_hasta"]


def _invalida(msg: str, campo: str | None = None) -> KontrolError:
    return KontrolError(
        code="GOV_BUDGET_INVALID",
        message=msg,
        field_errors={campo: [msg]} if campo else None,
        status_code=422,
    )


def _congelado() -> ConflictError:
    return ConflictError(
        "GOV_BUDGET_YEAR_FROZEN",
        "El ejercicio está fijado: su estructura y su clasificador ya no se pueden modificar",
    )


def _estado_invalido() -> ConflictError:
    return ConflictError(
        "GOV_BUDGET_YEAR_INVALID_STATE",
        "El estado del ejercicio no admite esta operación",
    )


def _ejercicio_de_empresa(
    db: Session,
    ctx: CompanyContext,
    year_id: str,
    *,
    bloquear: bool = False,
) -> GovernmentBudgetYear:
    consulta = select(GovernmentBudgetYear).where(
        GovernmentBudgetYear.id == year_id,
        GovernmentBudgetYear.tenant_id == ctx.tenant_id,
        GovernmentBudgetYear.company_id == ctx.company_id,
    )
    if bloquear:
        consulta = consulta.with_for_update()
    ejercicio = db.execute(consulta).scalar_one_or_none()
    if ejercicio is None:
        raise NotFoundError("GOV_BUDGET_YEAR_NOT_FOUND", "El ejercicio no existe en este ente")
    return ejercicio


def _para_escribir(
    db: Session,
    ctx: CompanyContext,
    year_id: str,
    version: int | None,
) -> GovernmentBudgetYear:
    if version is None:
        raise KontrolError(
            code="GOV_BUDGET_IF_MATCH_REQUIRED",
            message="Falta la cabecera If-Match con la versión del ejercicio",
            status_code=428,
        )
    ejercicio = _ejercicio_de_empresa(db, ctx, year_id, bloquear=True)
    if ejercicio.version != version:
        raise ConflictError(
            "GOV_BUDGET_YEAR_STALE",
            "El ejercicio cambió desde que lo abrió; recárguelo",
            details={"version_actual": ejercicio.version},
        )
    return ejercicio


def _historia(
    db: Session,
    ctx: CompanyContext,
    ejercicio: GovernmentBudgetYear,
    tipo: str,
    detalle: dict | None = None,
) -> None:
    db.add(
        GovernmentBudgetYearHistory(
            year_id=str(ejercicio.id),
            company_id=ctx.company_id,
            tipo=tipo,
            detalle=detalle,
            created_by=ctx.user_id,
        )
    )


def _auditar(
    db: Session,
    ctx: CompanyContext,
    ejercicio: GovernmentBudgetYear,
    accion: str,
    after: dict[str, Any],
) -> None:
    record_audit(
        db,
        action=accion,
        entity_type=ENTIDAD,
        entity_id=str(ejercicio.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after=after,
    )


def _exigir_borrador(ejercicio: GovernmentBudgetYear) -> None:
    if ejercicio.estado != "BORRADOR":
        raise _congelado()


def _niveles_del_ejercicio(db: Session, year_id: str) -> dict[int, GovernmentBudgetProgramLevel]:
    niveles = db.execute(
        select(GovernmentBudgetProgramLevel).where(
            GovernmentBudgetProgramLevel.year_id == year_id
        )
    ).scalars().all()
    return {nivel.orden: nivel for nivel in niveles}


def _mapa_codigos_partidas(
    db: Session,
    clasificador: GovernmentBudgetClassifier,
) -> dict[tuple[str, str], str]:
    partidas = db.execute(
        select(GovernmentBudgetClassifierItem).where(
            GovernmentBudgetClassifierItem.classifier_id == clasificador.id
        )
    ).scalars().all()
    return {(partida.tipo, partida.codigo): str(partida.id) for partida in partidas}


def _documento_valido(
    db: Session,
    ctx: CompanyContext,
    ejercicio: GovernmentBudgetYear,
    documento_id: str,
    campo: str,
) -> tuple[Document, str]:
    stmt = (
        select(Document)
        .join(DocumentLink, DocumentLink.document_id == Document.id)
        .where(
            Document.id == documento_id,
            Document.company_id == ctx.company_id,
            DocumentLink.resource_type == "GovernmentBudgetYear",
            DocumentLink.resource_id == ejercicio.id,
            DocumentLink.company_id == ctx.company_id,
            Document.status == "ACTIVE",
        )
        .limit(1)
    )
    documento = db.execute(stmt).scalar_one_or_none()
    mensaje = "El documento no es válido: debe estar activo y vinculado a este ejercicio"
    if documento is None:
        raise KontrolError(
            code="GOV_BUDGET_INVALID_DOCUMENT",
            message=mensaje,
            field_errors={campo: [mensaje]},
            status_code=422,
        )
    version = db.get(DocumentVersion, documento.current_version_id)
    if version is None or not version.sha256:
        raise KontrolError(
            code="GOV_BUDGET_INVALID_DOCUMENT",
            message=mensaje,
            field_errors={campo: [mensaje]},
            status_code=422,
        )
    return documento, version.sha256


def _faltantes(db: Session, ejercicio: GovernmentBudgetYear) -> list[str]:
    faltantes: list[str] = []
    niveles = db.execute(
        select(GovernmentBudgetProgramLevel.id).where(
            GovernmentBudgetProgramLevel.year_id == ejercicio.id
        ).limit(1)
    ).first()
    categorias = db.execute(
        select(GovernmentBudgetCategory.id).where(
            GovernmentBudgetCategory.year_id == ejercicio.id
        ).limit(1)
    ).first()
    clasificador = db.execute(
        select(GovernmentBudgetClassifier).where(
            GovernmentBudgetClassifier.year_id == ejercicio.id
        )
    ).scalar_one_or_none()
    if niveles is None:
        faltantes.append("Declare al menos un nivel programático")
    if categorias is None:
        faltantes.append("Registre al menos una categoría programática")
    if clasificador is None:
        faltantes.append("Registre el clasificador del ejercicio")
    elif not clasificador.documento_id:
        faltantes.append("Vincule el documento de procedencia del clasificador")
    if clasificador is not None:
        recurso = db.execute(
            select(GovernmentBudgetClassifierItem.id).where(
                GovernmentBudgetClassifierItem.classifier_id == clasificador.id,
                GovernmentBudgetClassifierItem.tipo == "RECURSO",
            ).limit(1)
        ).first()
        egreso = db.execute(
            select(GovernmentBudgetClassifierItem.id).where(
                GovernmentBudgetClassifierItem.classifier_id == clasificador.id,
                GovernmentBudgetClassifierItem.tipo == "EGRESO",
            ).limit(1)
        ).first()
        if recurso is None:
            faltantes.append("Registre al menos una partida de recursos")
        if egreso is None:
            faltantes.append("Registre al menos una partida de egresos")
    return faltantes


def _fotografia(db: Session, ejercicio: GovernmentBudgetYear) -> dict[str, Any]:
    niveles = db.execute(
        select(GovernmentBudgetProgramLevel)
        .where(GovernmentBudgetProgramLevel.year_id == ejercicio.id)
        .order_by(GovernmentBudgetProgramLevel.orden)
    ).scalars().all()
    categorias = db.execute(
        select(GovernmentBudgetCategory)
        .where(GovernmentBudgetCategory.year_id == ejercicio.id)
        .order_by(GovernmentBudgetCategory.codigo_completo)
    ).scalars().all()
    nivel_por_id = {str(nivel.id): nivel for nivel in niveles}
    clasificador = db.execute(
        select(GovernmentBudgetClassifier).where(
            GovernmentBudgetClassifier.year_id == ejercicio.id
        )
    ).scalar_one_or_none()
    partidas: list[dict[str, Any]] = []
    clasificador_foto: dict[str, Any] | None = None
    if clasificador is not None:
        items = db.execute(
            select(GovernmentBudgetClassifierItem)
            .where(GovernmentBudgetClassifierItem.classifier_id == clasificador.id)
            .order_by(GovernmentBudgetClassifierItem.tipo, GovernmentBudgetClassifierItem.codigo)
        ).scalars().all()
        codigo_por_id = {str(item.id): item.codigo for item in items}
        for item in items:
            partidas.append(
                {
                    "tipo": item.tipo,
                    "codigo": item.codigo,
                    "denominacion": item.denominacion,
                    "nivel": item.nivel,
                    "codigo_padre": codigo_por_id.get(str(item.parent_id)) if item.parent_id else None,
                    "vigente_desde": str(item.vigente_desde) if item.vigente_desde else None,
                    "vigente_hasta": str(item.vigente_hasta) if item.vigente_hasta else None,
                }
            )
        clasificador_foto = {
            "edicion": clasificador.edicion,
            "fecha_edicion": str(clasificador.fecha_edicion) if clasificador.fecha_edicion else None,
            "procedencia": clasificador.procedencia,
            "documento_sha256": clasificador.documento_sha256,
            "partidas": partidas,
        }
    return {
        "anio": ejercicio.anio,
        "moneda_funcional": ejercicio.moneda_funcional,
        "niveles": [{"orden": nivel.orden, "nombre": nivel.nombre} for nivel in niveles],
        "categorias": [
            {
                "codigo_completo": categoria.codigo_completo,
                "nivel_orden": nivel_por_id[str(categoria.level_id)].orden,
                "denominacion": categoria.denominacion,
            }
            for categoria in categorias
        ],
        "clasificador": clasificador_foto,
    }


def _huella(fotografia: dict[str, Any]) -> str:
    canon = json.dumps(fotografia, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canon.encode()).hexdigest()


def listar(db: Session, ctx: CompanyContext) -> dict[str, Any]:
    hoy = hoy_de_negocio()
    ejercicios = db.execute(
        select(GovernmentBudgetYear)
        .where(
            GovernmentBudgetYear.tenant_id == ctx.tenant_id,
            GovernmentBudgetYear.company_id == ctx.company_id,
        )
        .order_by(GovernmentBudgetYear.anio.desc())
    ).scalars().all()
    items: list[dict[str, Any]] = []
    for ejercicio in ejercicios:
        items.append(
            {
                "id": str(ejercicio.id),
                "anio": ejercicio.anio,
                "moneda_funcional": ejercicio.moneda_funcional,
                "estado": ejercicio.estado,
                "version": ejercicio.version,
                "congelado": ejercicio.estado != "BORRADOR",
                "reconduccion_definitiva": (
                    ejercicio.estado == "RECONDUCIDO" and hoy > date(ejercicio.anio, 3, 31)
                ),
                "precompromiso_activo": ejercicio.precompromiso_activo,
            }
        )
    return {"items": items, "total": len(items)}


def crear(db: Session, ctx: CompanyContext, anio: int) -> dict[str, Any]:
    existente = db.execute(
        select(GovernmentBudgetYear.id).where(
            GovernmentBudgetYear.tenant_id == ctx.tenant_id,
            GovernmentBudgetYear.company_id == ctx.company_id,
            GovernmentBudgetYear.anio == anio,
        )
    ).first()
    if existente is not None:
        raise ConflictError(
            "GOV_BUDGET_YEAR_EXISTS",
            "Ya existe un ejercicio para este ente y año",
        )
    empresa = db.get(Company, ctx.company_id)
    if empresa is None:
        raise NotFoundError("COMPANY_NOT_FOUND", "La empresa no existe")
    ejercicio = GovernmentBudgetYear(
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        anio=anio,
        moneda_funcional=empresa.functional_currency,
        estado="BORRADOR",
        precompromiso_activo=False,
        version=1,
        created_by=ctx.user_id,
    )
    db.add(ejercicio)
    db.flush()
    _historia(db, ctx, ejercicio, "CREADO", {"anio": anio, "moneda_funcional": ejercicio.moneda_funcional})
    _auditar(
        db,
        ctx,
        ejercicio,
        "GOV_BUDGET_YEAR_CREATED",
        {"anio": anio, "moneda_funcional": ejercicio.moneda_funcional},
    )
    db.flush()
    return detalle(db, ctx, str(ejercicio.id))


def detalle(db: Session, ctx: CompanyContext, year_id: str) -> dict[str, Any]:
    hoy = hoy_de_negocio()
    ejercicio = _ejercicio_de_empresa(db, ctx, year_id)
    niveles = db.execute(
        select(GovernmentBudgetProgramLevel)
        .where(GovernmentBudgetProgramLevel.year_id == ejercicio.id)
        .order_by(GovernmentBudgetProgramLevel.orden)
    ).scalars().all()
    nivel_por_id = {str(nivel.id): nivel for nivel in niveles}
    categorias = db.execute(
        select(GovernmentBudgetCategory)
        .where(GovernmentBudgetCategory.year_id == ejercicio.id)
        .order_by(GovernmentBudgetCategory.codigo_completo)
    ).scalars().all()
    clasificador = db.execute(
        select(GovernmentBudgetClassifier).where(
            GovernmentBudgetClassifier.year_id == ejercicio.id
        )
    ).scalar_one_or_none()
    clasificador_info: dict[str, Any] | None = None
    if clasificador is not None:
        recurso = db.execute(
            select(GovernmentBudgetClassifierItem.id).where(
                GovernmentBudgetClassifierItem.classifier_id == clasificador.id,
                GovernmentBudgetClassifierItem.tipo == "RECURSO",
            )
        ).scalars().all()
        egreso = db.execute(
            select(GovernmentBudgetClassifierItem.id).where(
                GovernmentBudgetClassifierItem.classifier_id == clasificador.id,
                GovernmentBudgetClassifierItem.tipo == "EGRESO",
            )
        ).scalars().all()
        clasificador_info = {
            "edicion": clasificador.edicion,
            "fecha_edicion": str(clasificador.fecha_edicion) if clasificador.fecha_edicion else None,
            "procedencia": clasificador.procedencia,
            "documento_id": str(clasificador.documento_id) if clasificador.documento_id else None,
            "documento_sha256": clasificador.documento_sha256,
            "partidas_recurso": len(recurso),
            "partidas_egreso": len(egreso),
        }
    fundamentos = db.execute(
        select(GovernmentBudgetYearFoundation)
        .where(GovernmentBudgetYearFoundation.year_id == ejercicio.id)
        .order_by(GovernmentBudgetYearFoundation.created_at)
    ).scalars().all()
    historias = db.execute(
        select(GovernmentBudgetYearHistory)
        .where(GovernmentBudgetYearHistory.year_id == ejercicio.id)
        .order_by(GovernmentBudgetYearHistory.created_at, GovernmentBudgetYearHistory.id)
    ).scalars().all()
    faltantes = _faltantes(db, ejercicio) if ejercicio.estado == "BORRADOR" else []
    return {
        "id": str(ejercicio.id),
        "anio": ejercicio.anio,
        "moneda_funcional": ejercicio.moneda_funcional,
        "estado": ejercicio.estado,
        "version": ejercicio.version,
        "congelado": ejercicio.estado != "BORRADOR",
        "reconduccion_definitiva": (
            ejercicio.estado == "RECONDUCIDO" and hoy > date(ejercicio.anio, 3, 31)
        ),
        "precompromiso_activo": ejercicio.precompromiso_activo,
        "precompromiso_desde": str(ejercicio.precompromiso_desde) if ejercicio.precompromiso_desde else None,
        "niveles": [{"orden": nivel.orden, "nombre": nivel.nombre} for nivel in niveles],
        "categorias": [
            {
                "id": str(categoria.id),
                "nivel_orden": nivel_por_id[str(categoria.level_id)].orden,
                "nivel_nombre": nivel_por_id[str(categoria.level_id)].nombre,
                "parent_id": str(categoria.parent_id) if categoria.parent_id else None,
                "codigo": categoria.codigo,
                "codigo_completo": categoria.codigo_completo,
                "denominacion": categoria.denominacion,
            }
            for categoria in categorias
        ],
        "clasificador": clasificador_info,
        "fundamentos": [
            {
                "tipo": fundamento.tipo,
                "referencia": fundamento.referencia,
                "fecha": str(fundamento.fecha) if fundamento.fecha else None,
                "documento_id": str(fundamento.documento_id) if fundamento.documento_id else None,
                "documento_sha256": fundamento.documento_sha256,
                "huella": fundamento.huella,
                "en": fundamento.created_at.isoformat() if fundamento.created_at else None,
            }
            for fundamento in fundamentos
        ],
        "faltantes": faltantes,
        "historia": [
            {
                "tipo": registro.tipo,
                "detalle": registro.detalle,
                "en": registro.created_at.isoformat() if registro.created_at else None,
            }
            for registro in historias
        ],
        "fijado_en": str(ejercicio.fijado_en) if ejercicio.fijado_en else None,
        "cerrado_en": str(ejercicio.cerrado_en) if ejercicio.cerrado_en else None,
        "motivo_cierre": ejercicio.motivo_cierre,
    }


def configurar_niveles(
    db: Session,
    ctx: CompanyContext,
    year_id: str,
    version: int | None,
    nombres: list[str],
) -> dict[str, Any]:
    ejercicio = _para_escribir(db, ctx, year_id, version)
    _exigir_borrador(ejercicio)
    if not 1 <= len(nombres) <= 8:
        raise _invalida("Debe declarar entre 1 y 8 niveles programáticos", "niveles")
    limpios: list[str] = []
    vistos: set[str] = set()
    for nombre in nombres:
        valor = nombre.strip()
        if not valor or len(valor) > 80:
            raise _invalida("Cada nivel debe tener entre 1 y 80 caracteres", "niveles")
        clave = valor.casefold()
        if clave in vistos:
            raise _invalida("Los nombres de los niveles no se pueden repetir", "niveles")
        vistos.add(clave)
        limpios.append(valor)
    categorias = db.execute(
        select(GovernmentBudgetCategory.id).where(
            GovernmentBudgetCategory.year_id == ejercicio.id
        ).limit(1)
    ).first()
    if categorias is not None:
        raise ConflictError(
            "GOV_BUDGET_LEVELS_IN_USE",
            "Hay categorías que dependen de los niveles actuales; elimínelas antes de cambiar los niveles",
        )
    for nivel in db.execute(
        select(GovernmentBudgetProgramLevel).where(
            GovernmentBudgetProgramLevel.year_id == ejercicio.id
        )
    ).scalars().all():
        db.delete(nivel)
    for orden, nombre in enumerate(limpios, start=1):
        db.add(
            GovernmentBudgetProgramLevel(
                year_id=str(ejercicio.id),
                company_id=ctx.company_id,
                orden=orden,
                nombre=nombre,
            )
        )
    ejercicio.version += 1
    db.flush()
    _historia(db, ctx, ejercicio, "NIVELES_CONFIGURADOS", {"niveles": limpios})
    _auditar(
        db,
        ctx,
        ejercicio,
        "GOV_BUDGET_LEVELS_CONFIGURED",
        {"anio": ejercicio.anio, "niveles": limpios},
    )
    db.flush()
    return detalle(db, ctx, str(ejercicio.id))


def crear_categoria(
    db: Session,
    ctx: CompanyContext,
    year_id: str,
    version: int | None,
    cuerpo: dict[str, Any],
) -> dict[str, Any]:
    ejercicio = _para_escribir(db, ctx, year_id, version)
    _exigir_borrador(ejercicio)
    niveles = _niveles_del_ejercicio(db, str(ejercicio.id))
    nivel_orden = cuerpo.get("nivel_orden")
    if not isinstance(nivel_orden, int) or nivel_orden not in niveles:
        raise _invalida("El nivel indicado no existe en el ejercicio", "nivel_orden")
    codigo = str(cuerpo.get("codigo") or "").strip()
    if not RE_CODIGO_CATEGORIA.match(codigo):
        raise _invalida("El código solo admite números, letras y guiones (máximo 20)", "codigo")
    denominacion = str(cuerpo.get("denominacion") or "").strip()
    if not denominacion or len(denominacion) > 300:
        raise _invalida("La denominación debe tener entre 1 y 300 caracteres", "denominacion")
    parent_id = cuerpo.get("parent_id")
    if isinstance(parent_id, str):
        parent_id = parent_id or None
    if nivel_orden == 1:
        if parent_id is not None:
            raise _invalida("El primer nivel no puede tener categoría padre", "parent_id")
        codigo_completo = codigo
    else:
        if parent_id is None:
            raise _invalida("La categoría de un nivel mayor que 1 debe tener padre", "parent_id")
        padre = db.execute(
            select(GovernmentBudgetCategory).where(
                GovernmentBudgetCategory.id == parent_id,
                GovernmentBudgetCategory.year_id == ejercicio.id,
            )
        ).scalar_one_or_none()
        if padre is None:
            raise _invalida("La categoría padre no pertenece a este ejercicio", "parent_id")
        padre_nivel = next(
            (nivel for nivel in niveles.values() if str(nivel.id) == str(padre.level_id)),
            None,
        )
        if padre_nivel is None or padre_nivel.orden != nivel_orden - 1:
            raise _invalida("La categoría padre debe ser del nivel inmediatamente anterior", "parent_id")
        codigo_completo = f"{padre.codigo_completo}.{codigo}"
    duplicada = db.execute(
        select(GovernmentBudgetCategory.id).where(
            GovernmentBudgetCategory.year_id == ejercicio.id,
            GovernmentBudgetCategory.codigo_completo == codigo_completo,
        )
    ).first()
    if duplicada is not None:
        raise _invalida("Ya existe una categoría con ese código completo", "codigo")
    categoria = GovernmentBudgetCategory(
        year_id=str(ejercicio.id),
        company_id=ctx.company_id,
        level_id=niveles[nivel_orden].id,
        parent_id=str(parent_id) if parent_id else None,
        codigo=codigo,
        codigo_completo=codigo_completo,
        denominacion=denominacion,
    )
    db.add(categoria)
    ejercicio.version += 1
    db.flush()
    _historia(db, ctx, ejercicio, "CATEGORIA_CREADA", {"codigo_completo": codigo_completo})
    _auditar(
        db,
        ctx,
        ejercicio,
        "GOV_BUDGET_CATEGORY_CREATED",
        {"anio": ejercicio.anio, "codigo_completo": codigo_completo},
    )
    db.flush()
    return detalle(db, ctx, str(ejercicio.id))


def modificar_categoria(
    db: Session,
    ctx: CompanyContext,
    year_id: str,
    version: int | None,
    categoria_id: str,
    denominacion: str,
) -> dict[str, Any]:
    ejercicio = _para_escribir(db, ctx, year_id, version)
    _exigir_borrador(ejercicio)
    categoria = db.execute(
        select(GovernmentBudgetCategory).where(
            GovernmentBudgetCategory.id == categoria_id,
            GovernmentBudgetCategory.year_id == ejercicio.id,
        )
    ).scalar_one_or_none()
    if categoria is None:
        raise NotFoundError("GOV_BUDGET_YEAR_NOT_FOUND", "La categoría no pertenece a este ejercicio")
    valor = denominacion.strip()
    if not valor or len(valor) > 300:
        raise _invalida("La denominación debe tener entre 1 y 300 caracteres", "denominacion")
    categoria.denominacion = valor
    ejercicio.version += 1
    db.flush()
    _historia(db, ctx, ejercicio, "CATEGORIA_MODIFICADA", {"codigo_completo": categoria.codigo_completo})
    _auditar(
        db,
        ctx,
        ejercicio,
        "GOV_BUDGET_CATEGORY_UPDATED",
        {"anio": ejercicio.anio, "codigo_completo": categoria.codigo_completo},
    )
    db.flush()
    return detalle(db, ctx, str(ejercicio.id))


def eliminar_categoria(
    db: Session,
    ctx: CompanyContext,
    year_id: str,
    version: int | None,
    categoria_id: str,
) -> dict[str, Any]:
    ejercicio = _para_escribir(db, ctx, year_id, version)
    _exigir_borrador(ejercicio)
    categoria = db.execute(
        select(GovernmentBudgetCategory).where(
            GovernmentBudgetCategory.id == categoria_id,
            GovernmentBudgetCategory.year_id == ejercicio.id,
        )
    ).scalar_one_or_none()
    if categoria is None:
        raise NotFoundError("GOV_BUDGET_YEAR_NOT_FOUND", "La categoría no pertenece a este ejercicio")
    hijos = db.execute(
        select(GovernmentBudgetCategory.id).where(
            GovernmentBudgetCategory.parent_id == categoria.id
        ).limit(1)
    ).first()
    if hijos is not None:
        raise ConflictError(
            "GOV_BUDGET_CATEGORY_HAS_CHILDREN",
            "La categoría tiene dependientes y no se puede eliminar",
        )
    db.delete(categoria)
    ejercicio.version += 1
    db.flush()
    _historia(db, ctx, ejercicio, "CATEGORIA_ELIMINADA", {"codigo_completo": categoria.codigo_completo})
    _auditar(
        db,
        ctx,
        ejercicio,
        "GOV_BUDGET_CATEGORY_DELETED",
        {"anio": ejercicio.anio, "codigo_completo": categoria.codigo_completo},
    )
    db.flush()
    return detalle(db, ctx, str(ejercicio.id))


def registrar_clasificador(
    db: Session,
    ctx: CompanyContext,
    year_id: str,
    version: int | None,
    cuerpo: dict[str, Any],
) -> dict[str, Any]:
    ejercicio = _para_escribir(db, ctx, year_id, version)
    _exigir_borrador(ejercicio)
    edicion = str(cuerpo.get("edicion") or "").strip()
    if not 3 <= len(edicion) <= 200:
        raise _invalida("La edición debe tener entre 3 y 200 caracteres", "edicion")
    fecha_edicion = cuerpo.get("fecha_edicion")
    if fecha_edicion is not None and not isinstance(fecha_edicion, date):
        raise _invalida("La fecha de edición no es válida", "fecha_edicion")
    procedencia = str(cuerpo.get("procedencia") or "").strip()
    if not 10 <= len(procedencia) <= 1000:
        raise _invalida("La procedencia debe tener entre 10 y 1000 caracteres", "procedencia")
    documento_id = cuerpo.get("documento_id")
    sha: str | None = None
    documento: Document | None = None
    if documento_id:
        documento, sha = _documento_valido(db, ctx, ejercicio, str(documento_id), "documento_id")
    existente = db.execute(
        select(GovernmentBudgetClassifier).where(
            GovernmentBudgetClassifier.year_id == ejercicio.id
        )
    ).scalar_one_or_none()
    if existente is None:
        clasificador = GovernmentBudgetClassifier(
            year_id=str(ejercicio.id),
            company_id=ctx.company_id,
            edicion=edicion,
            fecha_edicion=fecha_edicion,
            procedencia=procedencia,
            documento_id=str(documento_id) if documento_id else None,
            documento_sha256=sha,
        )
        db.add(clasificador)
        tipo_historia = "CLASIFICADOR_REGISTRADO"
        accion = "GOV_BUDGET_CLASSIFIER_REGISTERED"
        detalle_historia: dict[str, Any] = {"edicion": edicion}
        after: dict[str, Any] = {"anio": ejercicio.anio, "edicion": edicion}
    else:
        existente.edicion = edicion
        existente.fecha_edicion = fecha_edicion
        existente.procedencia = procedencia
        existente.documento_id = str(documento_id) if documento_id else None
        existente.documento_sha256 = sha
        tipo_historia = "PROCEDENCIA_MODIFICADA"
        accion = "GOV_BUDGET_CLASSIFIER_PROVENANCE_UPDATED"
        detalle_historia = {"edicion": edicion, "documento_sha256": sha}
        after = {"anio": ejercicio.anio, "documento_sha256": sha, "edicion": edicion}
    ejercicio.version += 1
    db.flush()
    _historia(db, ctx, ejercicio, tipo_historia, detalle_historia)
    _auditar(db, ctx, ejercicio, accion, after)
    db.flush()
    return detalle(db, ctx, str(ejercicio.id))


def _clasificador_del_ejercicio(
    db: Session,
    ejercicio: GovernmentBudgetYear,
) -> GovernmentBudgetClassifier | None:
    return db.execute(
        select(GovernmentBudgetClassifier).where(
            GovernmentBudgetClassifier.year_id == ejercicio.id
        )
    ).scalar_one_or_none()


def listar_partidas(
    db: Session,
    ctx: CompanyContext,
    year_id: str,
    tipo: str | None,
    q: str | None,
) -> dict[str, Any]:
    ejercicio = _ejercicio_de_empresa(db, ctx, year_id)
    clasificador = _clasificador_del_ejercicio(db, ejercicio)
    if clasificador is None:
        return {"items": [], "total": 0}
    consulta = select(GovernmentBudgetClassifierItem).where(
        GovernmentBudgetClassifierItem.classifier_id == clasificador.id
    )
    if tipo:
        consulta = consulta.where(GovernmentBudgetClassifierItem.tipo == tipo)
    if q:
        filtro = f"%{q.strip()}%"
        consulta = consulta.where(
            (GovernmentBudgetClassifierItem.codigo.ilike(filtro))
            | (GovernmentBudgetClassifierItem.denominacion.ilike(filtro))
        )
    partidas = db.execute(
        consulta.order_by(
            GovernmentBudgetClassifierItem.tipo,
            GovernmentBudgetClassifierItem.codigo,
        )
    ).scalars().all()
    codigo_por_id = {str(partida.id): partida.codigo for partida in partidas}
    items = [
        {
            "id": str(partida.id),
            "tipo": partida.tipo,
            "codigo": partida.codigo,
            "denominacion": partida.denominacion,
            "nivel": partida.nivel,
            "codigo_padre": codigo_por_id.get(str(partida.parent_id)) if partida.parent_id else None,
            "vigente_desde": str(partida.vigente_desde) if partida.vigente_desde else None,
            "vigente_hasta": str(partida.vigente_hasta) if partida.vigente_hasta else None,
        }
        for partida in partidas
    ]
    return {"items": items, "total": len(items)}


def _validar_partida(
    cuerpo: dict[str, Any],
    anio: int,
    existentes: dict[tuple[str, str], Any],
    *,
    fila: int | None = None,
) -> list[str]:
    errores: list[str] = []
    prefijo = f"Fila {fila}: " if fila is not None else ""
    tipo = str(cuerpo.get("tipo") or "").strip().upper()
    if tipo not in ("RECURSO", "EGRESO"):
        errores.append(f"{prefijo}El tipo debe ser RECURSO o EGRESO")
        return errores
    codigo = str(cuerpo.get("codigo") or "").strip()
    if not RE_CODIGO_PARTIDA.match(codigo):
        errores.append(f"{prefijo}El código solo admite números, letras, puntos y guiones (máximo 40)")
    denominacion = str(cuerpo.get("denominacion") or "").strip()
    if not denominacion or len(denominacion) > 300:
        errores.append(f"{prefijo}La denominación debe tener entre 1 y 300 caracteres")
    nivel = cuerpo.get("nivel")
    if not isinstance(nivel, int) or not 1 <= nivel <= 12:
        errores.append(f"{prefijo}El nivel debe estar entre 1 y 12")
        return errores
    codigo_padre = cuerpo.get("codigo_padre")
    if isinstance(codigo_padre, str):
        codigo_padre = codigo_padre.strip() or None
    if nivel == 1:
        if codigo_padre is not None:
            errores.append(f"{prefijo}El nivel 1 no puede tener partida padre")
    else:
        if codigo_padre is None:
            errores.append(f"{prefijo}La partida de nivel mayor que 1 debe indicar codigo_padre")
        elif (tipo, codigo_padre) not in existentes:
            errores.append(f"{prefijo}La partida padre no existe para este tipo y nivel inmediatamente anterior")
    vigente_desde = cuerpo.get("vigente_desde")
    if isinstance(vigente_desde, str):
        vigente_desde = vigente_desde.strip()
    vigente_hasta = cuerpo.get("vigente_hasta")
    if isinstance(vigente_hasta, str):
        vigente_hasta = vigente_hasta.strip()
    inicio_anio = date(anio, 1, 1)
    fin_anio = date(anio, 12, 31)
    desde: date | None = None
    hasta: date | None = None
    if vigente_desde is None or (
        isinstance(vigente_desde, str) and vigente_desde.strip() == ""
    ):
        desde = inicio_anio
        cuerpo["vigente_desde"] = inicio_anio
    elif isinstance(vigente_desde, date):
        desde = vigente_desde
        cuerpo["vigente_desde"] = vigente_desde
    else:
        vigente_desde = vigente_desde.strip()
        try:
            desde = date.fromisoformat(vigente_desde)
            cuerpo["vigente_desde"] = desde
        except ValueError:
            errores.append(f"{prefijo}vigente_desde debe ser una fecha ISO válida")
            desde = None
    if vigente_hasta is None or (
        isinstance(vigente_hasta, str) and vigente_hasta.strip() == ""
    ):
        hasta = None
        cuerpo["vigente_hasta"] = None
    elif isinstance(vigente_hasta, date):
        hasta = vigente_hasta
        cuerpo["vigente_hasta"] = vigente_hasta
    else:
        vigente_hasta = vigente_hasta.strip()
        try:
            hasta = date.fromisoformat(vigente_hasta)
            cuerpo["vigente_hasta"] = hasta
        except ValueError:
            errores.append(f"{prefijo}vigente_hasta debe ser una fecha ISO válida")
            hasta = None
    if desde is not None and (desde < inicio_anio or desde > fin_anio):
        errores.append(f"{prefijo}vigente_desde debe estar dentro del año {anio}")
    if hasta is not None and (hasta < inicio_anio or hasta > fin_anio):
        errores.append(f"{prefijo}vigente_hasta debe estar dentro del año {anio}")
    if desde is not None and hasta is not None and hasta < desde:
        errores.append(f"{prefijo}vigente_hasta no puede ser anterior a vigente_desde")
    clave = (tipo, codigo)
    if clave in existentes:
        errores.append(f"{prefijo}Ya existe una partida con ese código para este tipo")
    return errores


def crear_partida(
    db: Session,
    ctx: CompanyContext,
    year_id: str,
    version: int | None,
    cuerpo: dict[str, Any],
) -> dict[str, Any]:
    ejercicio = _para_escribir(db, ctx, year_id, version)
    _exigir_borrador(ejercicio)
    clasificador = _clasificador_del_ejercicio(db, ejercicio)
    if clasificador is None:
        raise ConflictError(
            "GOV_BUDGET_CLASSIFIER_MISSING",
            "Registre primero el clasificador del ejercicio",
        )
    errores = _validar_partida(cuerpo, ejercicio.anio, _mapa_codigos_partidas(db, clasificador))
    if errores:
        raise KontrolError(
            code="GOV_BUDGET_INVALID",
            message=errores[0],
            field_errors={"partida": errores},
            status_code=422,
        )
    tipo = str(cuerpo["tipo"]).upper()
    codigo = str(cuerpo["codigo"])
    codigo_padre = str(cuerpo["codigo_padre"]) if cuerpo.get("codigo_padre") else None
    padre_id = None
    if codigo_padre:
        padre = db.execute(
            select(GovernmentBudgetClassifierItem).where(
                GovernmentBudgetClassifierItem.classifier_id == clasificador.id,
                GovernmentBudgetClassifierItem.tipo == tipo,
                GovernmentBudgetClassifierItem.codigo == codigo_padre,
            )
        ).scalar_one_or_none()
        padre_id = str(padre.id) if padre else None
    partida = GovernmentBudgetClassifierItem(
        classifier_id=str(clasificador.id),
        company_id=ctx.company_id,
        tipo=tipo,
        codigo=codigo,
        denominacion=str(cuerpo["denominacion"]),
        nivel=int(cuerpo["nivel"]),
        parent_id=padre_id,
        vigente_desde=cuerpo.get("vigente_desde"),
        vigente_hasta=cuerpo.get("vigente_hasta"),
    )
    db.add(partida)
    ejercicio.version += 1
    db.flush()
    _historia(db, ctx, ejercicio, "PARTIDA_CREADA", {"tipo": tipo, "codigo": codigo})
    _auditar(
        db,
        ctx,
        ejercicio,
        "GOV_BUDGET_CLASSIFIER_ITEM_CREATED",
        {"anio": ejercicio.anio, "codigo": codigo, "tipo": tipo},
    )
    db.flush()
    return detalle(db, ctx, str(ejercicio.id))


def eliminar_partida(
    db: Session,
    ctx: CompanyContext,
    year_id: str,
    version: int | None,
    partida_id: str,
) -> dict[str, Any]:
    ejercicio = _para_escribir(db, ctx, year_id, version)
    _exigir_borrador(ejercicio)
    clasificador = _clasificador_del_ejercicio(db, ejercicio)
    if clasificador is None:
        raise ConflictError(
            "GOV_BUDGET_CLASSIFIER_MISSING",
            "Registre primero el clasificador del ejercicio",
        )
    partida = db.execute(
        select(GovernmentBudgetClassifierItem).where(
            GovernmentBudgetClassifierItem.id == partida_id,
            GovernmentBudgetClassifierItem.classifier_id == clasificador.id,
        )
    ).scalar_one_or_none()
    if partida is None:
        raise NotFoundError("GOV_BUDGET_YEAR_NOT_FOUND", "La partida no pertenece a este ejercicio")
    hijas = db.execute(
        select(GovernmentBudgetClassifierItem.id).where(
            GovernmentBudgetClassifierItem.parent_id == partida.id
        ).limit(1)
    ).first()
    if hijas is not None:
        raise ConflictError(
            "GOV_BUDGET_ITEM_HAS_CHILDREN",
            "La partida tiene partidas hijas y no se puede eliminar",
        )
    db.delete(partida)
    ejercicio.version += 1
    db.flush()
    _historia(db, ctx, ejercicio, "PARTIDA_ELIMINADA", {"tipo": partida.tipo, "codigo": partida.codigo})
    _auditar(
        db,
        ctx,
        ejercicio,
        "GOV_BUDGET_CLASSIFIER_ITEM_DELETED",
        {"anio": ejercicio.anio, "codigo": partida.codigo, "tipo": partida.tipo},
    )
    db.flush()
    return detalle(db, ctx, str(ejercicio.id))


def importar_partidas(
    db: Session,
    ctx: CompanyContext,
    year_id: str,
    version: int | None,
    contenido: bytes,
) -> dict[str, Any]:
    ejercicio = _para_escribir(db, ctx, year_id, version)
    _exigir_borrador(ejercicio)
    clasificador = _clasificador_del_ejercicio(db, ejercicio)
    if clasificador is None:
        raise ConflictError(
            "GOV_BUDGET_CLASSIFIER_MISSING",
            "Registre primero el clasificador del ejercicio",
        )
    if len(contenido) > 2_000_000:
        raise KontrolError(
            code="GOV_BUDGET_INVALID",
            message="El archivo supera los 2 MB",
            field_errors={"archivo": ["El archivo supera los 2 MB"]},
            status_code=422,
        )
    try:
        texto = contenido.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise KontrolError(
            code="GOV_BUDGET_INVALID",
            message="El archivo debe estar codificado en UTF-8",
            field_errors={"archivo": ["El archivo debe estar codificado en UTF-8"]},
            status_code=422,
        ) from None
    lector = csv.DictReader(io.StringIO(texto))
    if lector.fieldnames != CABECERA_PARTIDAS:
        raise KontrolError(
            code="GOV_BUDGET_INVALID",
            message=(
                "La cabecera debe ser: tipo,codigo,denominacion,nivel,codigo_padre,"
                "vigente_desde,vigente_hasta"
            ),
            field_errors={
                "archivo": [
                    "La cabecera debe ser: tipo,codigo,denominacion,nivel,codigo_padre,"
                    "vigente_desde,vigente_hasta"
                ]
            },
            status_code=422,
        )
    filas: list[dict[str, Any]] = []
    errores: list[str] = []
    existentes: dict[tuple[str, str], Any] = _mapa_codigos_partidas(db, clasificador)
    for numero_linea, fila in enumerate(lector, start=2):
        if len(filas) >= 5000:
            break
        fila_procesada: dict[str, Any] = dict(fila)
        nivel_crudo = str(fila_procesada.get("nivel") or "").strip()
        try:
            fila_procesada["nivel"] = int(nivel_crudo) if nivel_crudo else None
        except ValueError:
            fila_procesada["nivel"] = None
        if fila_procesada.get("vigente_desde") == "":
            fila_procesada["vigente_desde"] = None
        if fila_procesada.get("vigente_hasta") == "":
            fila_procesada["vigente_hasta"] = None
        if fila_procesada.get("codigo_padre") == "":
            fila_procesada["codigo_padre"] = None
        errores_fila = _validar_partida(
            fila_procesada,
            ejercicio.anio,
            existentes,
            fila=numero_linea,
        )
        if errores_fila:
            errores.extend(errores_fila)
        else:
            tipo = str(fila_procesada["tipo"]).upper()
            codigo = str(fila_procesada["codigo"])
            clave = (tipo, codigo)
            fila_procesada["_clave"] = clave
            filas.append(fila_procesada)
            existentes[clave] = True
            fila_procesada["_nivel"] = int(fila_procesada["nivel"])
    if not filas:
        if not errores:
            errores.append("El archivo no contiene filas de datos")
    if len(filas) > 5000:
        errores.append("El archivo supera las 5000 filas")
    if errores:
        raise KontrolError(
            code="GOV_BUDGET_INVALID",
            message="El archivo tiene errores: no se importó ninguna partida",
            field_errors={"archivo": errores[:50]},
            status_code=422,
        )
    codigo_a_id: dict[tuple[str, str], str] = {}
    for fila in filas:
        clave = fila["_clave"]
        fila["_id"] = str(uuid4())
        codigo_a_id[clave] = fila["_id"]
    codigo_por_padre: dict[str, str] = {}
    for fila in filas:
        tipo = str(fila["tipo"]).upper()
        codigo = str(fila["codigo"])
        codigo_padre = str(fila["codigo_padre"]) if fila.get("codigo_padre") else None
        padre_id = None
        if codigo_padre:
            padre_id = codigo_a_id.get((tipo, codigo_padre))
            if padre_id is None:
                padre = db.execute(
                    select(GovernmentBudgetClassifierItem).where(
                        GovernmentBudgetClassifierItem.classifier_id == clasificador.id,
                        GovernmentBudgetClassifierItem.tipo == tipo,
                        GovernmentBudgetClassifierItem.codigo == codigo_padre,
                    )
                ).scalar_one_or_none()
                if padre:
                    padre_id = str(padre.id)
        db.add(
            GovernmentBudgetClassifierItem(
                id=fila["_id"],
                classifier_id=str(clasificador.id),
                company_id=ctx.company_id,
                tipo=tipo,
                codigo=codigo,
                denominacion=str(fila["denominacion"]),
                nivel=int(fila["nivel"]),
                parent_id=padre_id,
                vigente_desde=fila.get("vigente_desde"),
                vigente_hasta=fila.get("vigente_hasta"),
            )
        )
        codigo_por_padre[codigo] = codigo
    ejercicio.version += 1
    db.flush()
    _historia(db, ctx, ejercicio, "PARTIDAS_IMPORTADAS", {"filas": len(filas)})
    _auditar(
        db,
        ctx,
        ejercicio,
        "GOV_BUDGET_CLASSIFIER_ITEMS_IMPORTED",
        {"anio": ejercicio.anio, "filas": len(filas)},
    )
    db.flush()
    return detalle(db, ctx, str(ejercicio.id))


def _fijar(
    db: Session,
    ctx: CompanyContext,
    ejercicio: GovernmentBudgetYear,
    tipo: str,
    referencia: str,
    fecha: date,
    documento_id: str,
) -> dict[str, Any]:
    documento, sha = _documento_valido(db, ctx, ejercicio, documento_id, "documento_id")
    fotografia = _fotografia(db, ejercicio)
    huella = _huella(fotografia)
    db.add(
        GovernmentBudgetYearFoundation(
            year_id=str(ejercicio.id),
            company_id=ctx.company_id,
            tipo=tipo,
            referencia=referencia,
            fecha=fecha,
            documento_id=str(documento.id),
            documento_sha256=sha,
            huella=huella,
            fotografia=fotografia,
            created_by=ctx.user_id,
        )
    )
    ejercicio.estado = "APROBADO" if tipo == "ORDENANZA" else "RECONDUCIDO"
    ejercicio.fijado_por = ctx.user_id
    ejercicio.fijado_en = datetime.now(UTC)
    ejercicio.version += 1
    db.flush()
    return {"huella": huella, "referencia": referencia, "fotografia": fotografia}


def aprobar(
    db: Session,
    ctx: CompanyContext,
    year_id: str,
    version: int | None,
    cuerpo: dict[str, Any],
) -> dict[str, Any]:
    ejercicio = _para_escribir(db, ctx, year_id, version)
    if ejercicio.estado != "BORRADOR":
        raise _estado_invalido()
    referencia = str(cuerpo.get("referencia") or "").strip()
    if not 3 <= len(referencia) <= 300:
        raise _invalida("La referencia debe tener entre 3 y 300 caracteres", "referencia")
    fecha = cuerpo.get("fecha")
    if not isinstance(fecha, date):
        raise _invalida("La fecha no es válida", "fecha")
    hoy = hoy_de_negocio()
    if fecha > hoy:
        raise _invalida("La fecha no puede ser futura", "fecha")
    if fecha > date(ejercicio.anio, 12, 31):
        raise _invalida("La fecha no puede ser posterior al cierre del año", "fecha")
    faltantes = _faltantes(db, ejercicio)
    if faltantes:
        raise KontrolError(
            code="GOV_BUDGET_YEAR_INCOMPLETE",
            message="El ejercicio está incompleto",
            details={"faltantes": faltantes},
            status_code=422,
        )
    documento_id = cuerpo.get("documento_id")
    if not documento_id:
        raise _invalida("El documento es obligatorio", "documento_id")
    resultado = _fijar(db, ctx, ejercicio, "ORDENANZA", referencia, fecha, str(documento_id))
    _historia(
        db,
        ctx,
        ejercicio,
        "APROBADO",
        {"referencia": referencia, "huella": resultado["huella"]},
    )
    _auditar(
        db,
        ctx,
        ejercicio,
        "GOV_BUDGET_YEAR_APPROVED",
        {"anio": ejercicio.anio, "huella": resultado["huella"], "referencia": referencia},
    )
    db.flush()
    return detalle(db, ctx, str(ejercicio.id))


def reconducir(
    db: Session,
    ctx: CompanyContext,
    year_id: str,
    version: int | None,
    cuerpo: dict[str, Any],
) -> dict[str, Any]:
    ejercicio = _para_escribir(db, ctx, year_id, version)
    if ejercicio.estado != "BORRADOR":
        raise _estado_invalido()
    referencia = str(cuerpo.get("referencia") or "").strip()
    if not 3 <= len(referencia) <= 300:
        raise _invalida("La referencia debe tener entre 3 y 300 caracteres", "referencia")
    fecha = cuerpo.get("fecha")
    if not isinstance(fecha, date):
        raise _invalida("La fecha no es válida", "fecha")
    hoy = hoy_de_negocio()
    if hoy <= date(ejercicio.anio - 1, 12, 15):
        raise ConflictError(
            "GOV_BUDGET_RECONDUCTION_PREMATURE",
            "La reconducción solo procede si la ordenanza no se sancionó antes del "
            "15 de diciembre del año anterior (LOPPM art. 234)",
        )
    if fecha < date(ejercicio.anio - 1, 12, 16) or fecha > hoy:
        raise _invalida("La fecha debe estar entre el 16 de diciembre del año anterior y hoy", "fecha")
    faltantes = _faltantes(db, ejercicio)
    if faltantes:
        raise KontrolError(
            code="GOV_BUDGET_YEAR_INCOMPLETE",
            message="El ejercicio está incompleto",
            details={"faltantes": faltantes},
            status_code=422,
        )
    documento_id = cuerpo.get("documento_id")
    if not documento_id:
        raise _invalida("El documento es obligatorio", "documento_id")
    resultado = _fijar(db, ctx, ejercicio, "RECONDUCCION", referencia, fecha, str(documento_id))
    _historia(
        db,
        ctx,
        ejercicio,
        "RECONDUCIDO",
        {"referencia": referencia, "huella": resultado["huella"]},
    )
    _auditar(
        db,
        ctx,
        ejercicio,
        "GOV_BUDGET_YEAR_RECONDUCTED",
        {"anio": ejercicio.anio, "huella": resultado["huella"], "referencia": referencia},
    )
    db.flush()
    return detalle(db, ctx, str(ejercicio.id))


def cerrar(
    db: Session,
    ctx: CompanyContext,
    year_id: str,
    version: int | None,
    cuerpo: dict[str, Any],
) -> dict[str, Any]:
    ejercicio = _para_escribir(db, ctx, year_id, version)
    if ejercicio.estado not in ("APROBADO", "RECONDUCIDO"):
        raise _estado_invalido()
    motivo = str(cuerpo.get("motivo") or "").strip() if cuerpo.get("motivo") else None
    if motivo is not None and len(motivo) > 500:
        raise _invalida("El motivo no puede superar los 500 caracteres", "motivo")
    if hoy_de_negocio() <= date(ejercicio.anio, 12, 31):
        raise ConflictError(
            "GOV_BUDGET_YEAR_NOT_ENDED",
            "El ejercicio solo se cierra después del 31 de diciembre (LOPPM art. 248)",
        )
    ejercicio.estado = "CERRADO"
    ejercicio.cerrado_por = ctx.user_id
    ejercicio.cerrado_en = datetime.now(UTC)
    ejercicio.motivo_cierre = motivo[:500] if motivo else None
    ejercicio.version += 1
    db.flush()
    _historia(db, ctx, ejercicio, "CERRADO", {"motivo": motivo})
    _auditar(db, ctx, ejercicio, "GOV_BUDGET_YEAR_CLOSED", {"anio": ejercicio.anio})
    db.flush()
    return detalle(db, ctx, str(ejercicio.id))


def cambiar_precompromiso(
    db: Session,
    ctx: CompanyContext,
    year_id: str,
    version: int | None,
    cuerpo: dict[str, Any],
) -> dict[str, Any]:
    ejercicio = _para_escribir(db, ctx, year_id, version)
    if ejercicio.estado == "CERRADO":
        raise _estado_invalido()
    activo = cuerpo.get("activo")
    if not isinstance(activo, bool):
        raise _invalida("El campo activo debe ser verdadero o falso", "activo")
    vigente_desde = cuerpo.get("vigente_desde")
    if not isinstance(vigente_desde, date):
        raise _invalida("La fecha de vigencia no es válida", "vigente_desde")
    if vigente_desde < date(ejercicio.anio, 1, 1) or vigente_desde > date(ejercicio.anio, 12, 31):
        raise _invalida("La fecha de vigencia debe estar dentro del año", "vigente_desde")
    motivo = str(cuerpo.get("motivo") or "").strip()
    if not 10 <= len(motivo) <= 500:
        raise _invalida("El motivo debe tener entre 10 y 500 caracteres", "motivo")
    if ejercicio.precompromiso_activo == activo and ejercicio.precompromiso_desde == vigente_desde:
        raise _invalida("No hay cambios", "activo")
    ejercicio.precompromiso_activo = activo
    ejercicio.precompromiso_desde = vigente_desde
    ejercicio.version += 1
    db.flush()
    _historia(
        db,
        ctx,
        ejercicio,
        "PRECOMPROMISO_CAMBIADO",
        {"activo": activo, "vigente_desde": str(vigente_desde), "motivo": motivo},
    )
    _auditar(
        db,
        ctx,
        ejercicio,
        "GOV_BUDGET_PRECOMMITMENT_POLICY_CHANGED",
        {"activo": activo, "anio": ejercicio.anio, "vigente_desde": str(vigente_desde)},
    )
    db.flush()
    return detalle(db, ctx, str(ejercicio.id))
