"""Servicio de dominio del plan operativo y metas (BUD-03)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext
from app.core.errors import ConflictError, NotFoundError
from app.modules.government.models import (
    GovernmentBudgetCategory,
    GovernmentBudgetGoal,
    GovernmentBudgetObjective,
    GovernmentBudgetPlan,
    GovernmentBudgetYear,
    GovernmentStructure,
    GovernmentUnit,
)
from app.modules.government.service_presupuesto import (
    _auditar,
    _documento_valido,
    _ejercicio_de_empresa,
    _exigir_borrador,
    _historia,
    _para_escribir,
)


def _no_encontrado(tipo: str) -> NotFoundError:
    return NotFoundError(tipo, "El elemento no existe en este ejercicio")


def _unidades_disponibles(db: Session, ejercicio: GovernmentBudgetYear, ctx: CompanyContext) -> list[dict[str, str]]:
    estructura = db.execute(
        select(GovernmentStructure).where(
            GovernmentStructure.company_id == ctx.company_id,
            GovernmentStructure.exercise == ejercicio.anio,
            GovernmentStructure.status == "VIGENTE",
        )
    ).scalar_one_or_none()
    if estructura is None:
        return []
    units = db.execute(
        select(GovernmentUnit)
        .where(
            GovernmentUnit.structure_id == estructura.id,
            GovernmentUnit.company_id == ctx.company_id,
            GovernmentUnit.status == "ACTIVA",
        )
        .order_by(GovernmentUnit.code)
    ).scalars().all()
    return [{"id": str(u.id), "codigo": u.code, "nombre": u.name} for u in units]


def _codigo_completo_de_categoria(categoria: GovernmentBudgetCategory) -> str:
    return categoria.codigo_completo


def _vista_plan(db: Session, ctx: CompanyContext, ejercicio: GovernmentBudgetYear) -> dict[str, Any]:
    plan = db.execute(
        select(GovernmentBudgetPlan).where(
            GovernmentBudgetPlan.year_id == ejercicio.id,
            GovernmentBudgetPlan.company_id == ctx.company_id,
        )
    ).scalar_one_or_none()

    objetivos = db.execute(
        select(GovernmentBudgetObjective)
        .where(
            GovernmentBudgetObjective.year_id == ejercicio.id,
            GovernmentBudgetObjective.company_id == ctx.company_id,
        )
        .order_by(GovernmentBudgetObjective.codigo)
    ).scalars().all()

    categorias = db.execute(
        select(GovernmentBudgetCategory)
        .where(
            GovernmentBudgetCategory.year_id == ejercicio.id,
            GovernmentBudgetCategory.company_id == ctx.company_id,
        )
        .order_by(GovernmentBudgetCategory.codigo_completo)
    ).scalars().all()

    metas = db.execute(
        select(GovernmentBudgetGoal)
        .where(
            GovernmentBudgetGoal.year_id == ejercicio.id,
            GovernmentBudgetGoal.company_id == ctx.company_id,
        )
        .order_by(GovernmentBudgetGoal.descripcion)
    ).scalars().all()

    unidades = _unidades_disponibles(db, ejercicio, ctx)
    unidad_por_id = {u["id"]: u for u in unidades}

    estructura = db.execute(
        select(GovernmentStructure).where(
            GovernmentStructure.company_id == ctx.company_id,
            GovernmentStructure.exercise == ejercicio.anio,
        )
    ).scalar_one_or_none()

    objetivo_por_id = {str(o.id): o for o in objetivos}
    categoria_por_id = {str(c.id): c for c in categorias}
    meta_por_categoria: dict[str, list[GovernmentBudgetGoal]] = {}
    for meta in metas:
        meta_por_categoria.setdefault(str(meta.category_id), []).append(meta)

    vinculos = []
    for categoria in categorias:
        unidad = None
        if categoria.unit_id and str(categoria.unit_id) in unidad_por_id:
            data = unidad_por_id[str(categoria.unit_id)]
            unidad = {"id": data["id"], "codigo": data["codigo"], "nombre": data["nombre"]}
        objetivo_ref = None
        if categoria.objective_id and str(categoria.objective_id) in objetivo_por_id:
            objetivo_ref = {
                "id": str(categoria.objective_id),
                "codigo": objetivo_por_id[str(categoria.objective_id)].codigo,
            }
        vinculos.append(
            {
                "categoria_id": str(categoria.id),
                "codigo_completo": categoria.codigo_completo,
                "denominacion": categoria.denominacion,
                "unidad": unidad,
                "objetivo": objetivo_ref,
            }
        )

    metas_vista = []
    for meta in metas:
        categoria_meta = categoria_por_id.get(str(meta.category_id))
        codigo_completo = categoria_meta.codigo_completo if categoria_meta else ""
        metas_vista.append(
            {
                "id": str(meta.id),
                "categoria_id": str(meta.category_id),
                "codigo_completo": codigo_completo,
                "descripcion": meta.descripcion,
                "unidad_medida": meta.unidad_medida,
                "cantidad": str(meta.cantidad),
                "indicador": meta.indicador,
                "formula": meta.formula,
            }
        )

    return {
        "version": ejercicio.version,
        "congelado": ejercicio.estado != "BORRADOR",
        "plan": {
            "denominacion": plan.denominacion,
            "documento_id": str(plan.documento_id) if plan.documento_id else None,
            "documento_sha256": plan.documento_sha256,
        }
        if plan
        else None,
        "objetivos": [
            {"id": str(o.id), "codigo": o.codigo, "descripcion": o.descripcion}
            for o in objetivos
        ],
        "vinculos": vinculos,
        "metas": metas_vista,
        "unidades_disponibles": unidades,
        "estructura_organizativa": {"estado": estructura.status} if estructura else None,
    }


def vista_plan(db: Session, ctx: CompanyContext, year_id: str) -> dict[str, Any]:
    ejercicio = _ejercicio_de_empresa(db, ctx, year_id)
    return _vista_plan(db, ctx, ejercicio)


def registrar_plan(
    db: Session,
    ctx: CompanyContext,
    year_id: str,
    version: int | None,
    cuerpo: dict[str, Any],
) -> dict[str, Any]:
    ejercicio = _para_escribir(db, ctx, year_id, version)
    _exigir_borrador(ejercicio)
    denominacion = cuerpo["denominacion"]
    documento_id = cuerpo.get("documento_id")
    plan = db.execute(
        select(GovernmentBudgetPlan).where(
            GovernmentBudgetPlan.year_id == ejercicio.id,
            GovernmentBudgetPlan.company_id == ctx.company_id,
        )
    ).scalar_one_or_none()
    documento_sha256 = None
    if documento_id:
        _documento, documento_sha256 = _documento_valido(
            db, ctx, ejercicio, documento_id, "documento_id"
        )
    if plan is None:
        plan = GovernmentBudgetPlan(
            year_id=str(ejercicio.id),
            company_id=ctx.company_id,
            denominacion=denominacion,
            documento_id=documento_id,
            documento_sha256=documento_sha256,
            created_by=ctx.user_id,
        )
        db.add(plan)
    else:
        plan.denominacion = denominacion
        plan.documento_id = documento_id
        plan.documento_sha256 = documento_sha256

    ejercicio.version += 1
    db.flush()
    _historia(db, ctx, ejercicio, "PLAN_REGISTRADO", {"denominacion": denominacion})
    _auditar(
        db,
        ctx,
        ejercicio,
        "GOV_BUDGET_PLAN_REGISTERED",
        {"anio": ejercicio.anio, "denominacion": denominacion},
    )
    db.flush()
    return _vista_plan(db, ctx, ejercicio)


def crear_objetivo(
    db: Session,
    ctx: CompanyContext,
    year_id: str,
    version: int | None,
    cuerpo: dict[str, Any],
) -> dict[str, Any]:
    ejercicio = _para_escribir(db, ctx, year_id, version)
    _exigir_borrador(ejercicio)
    codigo = cuerpo["codigo"]
    descripcion = cuerpo["descripcion"]
    existente = db.execute(
        select(GovernmentBudgetObjective).where(
            GovernmentBudgetObjective.year_id == ejercicio.id,
            GovernmentBudgetObjective.company_id == ctx.company_id,
            GovernmentBudgetObjective.codigo == codigo,
        )
    ).scalar_one_or_none()
    if existente is not None:
        from app.modules.government.service_presupuesto import _invalida

        raise _invalida("El código de objetivo ya existe en el ejercicio", "codigo")
    objetivo = GovernmentBudgetObjective(
        year_id=str(ejercicio.id),
        company_id=ctx.company_id,
        codigo=codigo,
        descripcion=descripcion,
        created_by=ctx.user_id,
    )
    db.add(objetivo)
    ejercicio.version += 1
    db.flush()
    _historia(db, ctx, ejercicio, "OBJETIVO_CREADO", {"codigo": codigo})
    _auditar(
        db,
        ctx,
        ejercicio,
        "GOV_BUDGET_OBJECTIVE_CREATED",
        {"anio": ejercicio.anio, "codigo": codigo},
    )
    db.flush()
    return _vista_plan(db, ctx, ejercicio)


def modificar_objetivo(
    db: Session,
    ctx: CompanyContext,
    year_id: str,
    version: int | None,
    objetivo_id: str,
    descripcion: str,
) -> dict[str, Any]:
    ejercicio = _para_escribir(db, ctx, year_id, version)
    _exigir_borrador(ejercicio)
    objetivo = db.execute(
        select(GovernmentBudgetObjective).where(
            GovernmentBudgetObjective.id == objetivo_id,
            GovernmentBudgetObjective.year_id == ejercicio.id,
            GovernmentBudgetObjective.company_id == ctx.company_id,
        )
    ).scalar_one_or_none()
    if objetivo is None:
        raise _no_encontrado("GOV_BUDGET_OBJECTIVE_NOT_FOUND")
    objetivo.descripcion = descripcion
    ejercicio.version += 1
    db.flush()
    _historia(db, ctx, ejercicio, "OBJETIVO_MODIFICADO", {"codigo": objetivo.codigo})
    _auditar(
        db,
        ctx,
        ejercicio,
        "GOV_BUDGET_OBJECTIVE_UPDATED",
        {"anio": ejercicio.anio, "codigo": objetivo.codigo},
    )
    db.flush()
    return _vista_plan(db, ctx, ejercicio)


def eliminar_objetivo(
    db: Session,
    ctx: CompanyContext,
    year_id: str,
    version: int | None,
    objetivo_id: str,
) -> dict[str, Any]:
    ejercicio = _para_escribir(db, ctx, year_id, version)
    _exigir_borrador(ejercicio)
    objetivo = db.execute(
        select(GovernmentBudgetObjective).where(
            GovernmentBudgetObjective.id == objetivo_id,
            GovernmentBudgetObjective.year_id == ejercicio.id,
            GovernmentBudgetObjective.company_id == ctx.company_id,
        )
    ).scalar_one_or_none()
    if objetivo is None:
        raise _no_encontrado("GOV_BUDGET_OBJECTIVE_NOT_FOUND")
    en_uso = db.execute(
        select(GovernmentBudgetCategory).where(
            GovernmentBudgetCategory.objective_id == objetivo.id,
            GovernmentBudgetCategory.year_id == ejercicio.id,
        )
    ).scalar_one_or_none()
    if en_uso is not None:
        raise ConflictError(
            "GOV_BUDGET_OBJECTIVE_IN_USE",
            "El objetivo está vinculado a categorías programáticas",
        )
    codigo = objetivo.codigo
    db.delete(objetivo)
    ejercicio.version += 1
    db.flush()
    _historia(db, ctx, ejercicio, "OBJETIVO_ELIMINADO", {"codigo": codigo})
    _auditar(
        db,
        ctx,
        ejercicio,
        "GOV_BUDGET_OBJECTIVE_DELETED",
        {"anio": ejercicio.anio, "codigo": codigo},
    )
    db.flush()
    return _vista_plan(db, ctx, ejercicio)


def vincular_categoria(
    db: Session,
    ctx: CompanyContext,
    year_id: str,
    version: int | None,
    categoria_id: str,
    cuerpo: dict[str, Any],
) -> dict[str, Any]:
    from app.modules.government.service_presupuesto import _invalida

    ejercicio = _para_escribir(db, ctx, year_id, version)
    _exigir_borrador(ejercicio)
    categoria = db.execute(
        select(GovernmentBudgetCategory).where(
            GovernmentBudgetCategory.id == categoria_id,
            GovernmentBudgetCategory.year_id == ejercicio.id,
            GovernmentBudgetCategory.company_id == ctx.company_id,
        )
    ).scalar_one_or_none()
    if categoria is None:
        raise _no_encontrado("GOV_BUDGET_CATEGORY_NOT_FOUND")

    unidad_id = cuerpo.get("unidad_id")
    objetivo_id = cuerpo.get("objetivo_id")

    objetivo_codigo = None
    if objetivo_id is not None:
        objetivo = db.execute(
            select(GovernmentBudgetObjective).where(
                GovernmentBudgetObjective.id == objetivo_id,
                GovernmentBudgetObjective.year_id == ejercicio.id,
                GovernmentBudgetObjective.company_id == ctx.company_id,
            )
        ).scalar_one_or_none()
        if objetivo is None:
            raise _invalida(
                "El objetivo no pertenece a este ejercicio", "objetivo_id"
            )
        objetivo_codigo = objetivo.codigo

    unidad_codigo = None
    if unidad_id is not None:
        unidades = _unidades_disponibles(db, ejercicio, ctx)
        unidad = next((u for u in unidades if u["id"] == unidad_id), None)
        if unidad is None:
            raise _invalida(
                "La unidad no pertenece a la estructura organizativa vigente del ejercicio",
                "unidad_id",
            )
        unidad_codigo = unidad["codigo"]

    categoria.unit_id = unidad_id
    categoria.objective_id = objetivo_id
    ejercicio.version += 1
    db.flush()
    _historia(
        db,
        ctx,
        ejercicio,
        "CATEGORIA_VINCULADA",
        {
            "codigo_completo": categoria.codigo_completo,
            "unidad": unidad_codigo,
            "objetivo": objetivo_codigo,
        },
    )
    _auditar(
        db,
        ctx,
        ejercicio,
        "GOV_BUDGET_CATEGORY_LINKED",
        {
            "anio": ejercicio.anio,
            "codigo_completo": categoria.codigo_completo,
            "objetivo": objetivo_codigo,
            "unidad": unidad_codigo,
        },
    )
    db.flush()
    return _vista_plan(db, ctx, ejercicio)


def _validar_cantidad(cantidad: Decimal, campo: str) -> None:
    from app.modules.government.service_presupuesto import _invalida

    if cantidad <= 0:
        raise _invalida("La cantidad debe ser mayor que cero", campo)
    if cantidad > Decimal("99999999999999"):
        raise _invalida("La cantidad excede el máximo permitido", campo)
    exponente = cantidad.as_tuple().exponent
    if not cantidad.is_finite() or not isinstance(exponente, int) or exponente < -4:
        raise _invalida("La cantidad admite a lo sumo 4 decimales", campo)


def crear_meta(
    db: Session,
    ctx: CompanyContext,
    year_id: str,
    version: int | None,
    cuerpo: dict[str, Any],
) -> dict[str, Any]:
    from app.modules.government.service_presupuesto import _invalida

    ejercicio = _para_escribir(db, ctx, year_id, version)
    _exigir_borrador(ejercicio)
    categoria = db.execute(
        select(GovernmentBudgetCategory).where(
            GovernmentBudgetCategory.id == cuerpo["categoria_id"],
            GovernmentBudgetCategory.year_id == ejercicio.id,
            GovernmentBudgetCategory.company_id == ctx.company_id,
        )
    ).scalar_one_or_none()
    if categoria is None:
        raise _invalida("La categoría no pertenece a este ejercicio", "categoria_id")
    cantidad = cuerpo["cantidad"]
    _validar_cantidad(cantidad, "cantidad")
    meta = GovernmentBudgetGoal(
        year_id=str(ejercicio.id),
        company_id=ctx.company_id,
        category_id=str(categoria.id),
        descripcion=cuerpo["descripcion"],
        unidad_medida=cuerpo["unidad_medida"],
        cantidad=cantidad,
        indicador=cuerpo["indicador"],
        formula=cuerpo.get("formula"),
        created_by=ctx.user_id,
    )
    db.add(meta)
    ejercicio.version += 1
    db.flush()
    _historia(
        db,
        ctx,
        ejercicio,
        "META_CREADA",
        {"codigo_completo": categoria.codigo_completo, "indicador": meta.indicador},
    )
    _auditar(
        db,
        ctx,
        ejercicio,
        "GOV_BUDGET_GOAL_CREATED",
        {
            "anio": ejercicio.anio,
            "codigo_completo": categoria.codigo_completo,
            "indicador": meta.indicador,
        },
    )
    db.flush()
    return _vista_plan(db, ctx, ejercicio)


def modificar_meta(
    db: Session,
    ctx: CompanyContext,
    year_id: str,
    version: int | None,
    meta_id: str,
    cuerpo: dict[str, Any],
) -> dict[str, Any]:
    ejercicio = _para_escribir(db, ctx, year_id, version)
    _exigir_borrador(ejercicio)
    meta = db.execute(
        select(GovernmentBudgetGoal).where(
            GovernmentBudgetGoal.id == meta_id,
            GovernmentBudgetGoal.year_id == ejercicio.id,
            GovernmentBudgetGoal.company_id == ctx.company_id,
        )
    ).scalar_one_or_none()
    if meta is None:
        raise _no_encontrado("GOV_BUDGET_GOAL_NOT_FOUND")
    cantidad = cuerpo["cantidad"]
    _validar_cantidad(cantidad, "cantidad")
    meta.descripcion = cuerpo["descripcion"]
    meta.unidad_medida = cuerpo["unidad_medida"]
    meta.cantidad = cantidad
    meta.indicador = cuerpo["indicador"]
    meta.formula = cuerpo.get("formula")
    categoria = db.get(GovernmentBudgetCategory, meta.category_id)
    codigo_completo = categoria.codigo_completo if categoria else ""
    ejercicio.version += 1
    db.flush()
    _historia(
        db,
        ctx,
        ejercicio,
        "META_MODIFICADA",
        {"codigo_completo": codigo_completo, "indicador": meta.indicador},
    )
    _auditar(
        db,
        ctx,
        ejercicio,
        "GOV_BUDGET_GOAL_UPDATED",
        {
            "anio": ejercicio.anio,
            "codigo_completo": codigo_completo,
            "indicador": meta.indicador,
        },
    )
    db.flush()
    return _vista_plan(db, ctx, ejercicio)


def eliminar_meta(
    db: Session,
    ctx: CompanyContext,
    year_id: str,
    version: int | None,
    meta_id: str,
) -> dict[str, Any]:
    ejercicio = _para_escribir(db, ctx, year_id, version)
    _exigir_borrador(ejercicio)
    meta = db.execute(
        select(GovernmentBudgetGoal).where(
            GovernmentBudgetGoal.id == meta_id,
            GovernmentBudgetGoal.year_id == ejercicio.id,
            GovernmentBudgetGoal.company_id == ctx.company_id,
        )
    ).scalar_one_or_none()
    if meta is None:
        raise _no_encontrado("GOV_BUDGET_GOAL_NOT_FOUND")
    categoria = db.get(GovernmentBudgetCategory, meta.category_id)
    codigo_completo = categoria.codigo_completo if categoria else ""
    indicador = meta.indicador
    db.delete(meta)
    ejercicio.version += 1
    db.flush()
    _historia(
        db,
        ctx,
        ejercicio,
        "META_ELIMINADA",
        {"codigo_completo": codigo_completo, "indicador": indicador},
    )
    _auditar(
        db,
        ctx,
        ejercicio,
        "GOV_BUDGET_GOAL_DELETED",
        {
            "anio": ejercicio.anio,
            "codigo_completo": codigo_completo,
            "indicador": indicador,
        },
    )
    db.flush()
    return _vista_plan(db, ctx, ejercicio)


def fotografia_plan(db: Session, ejercicio: GovernmentBudgetYear) -> dict[str, Any]:
    """Fotografía inmutable para la gestión de ejercicios posteriores."""
    plan = db.execute(
        select(GovernmentBudgetPlan).where(
            GovernmentBudgetPlan.year_id == ejercicio.id,
            GovernmentBudgetPlan.company_id == ejercicio.company_id,
        )
    ).scalar_one_or_none()
    objetivos = db.execute(
        select(GovernmentBudgetObjective)
        .where(
            GovernmentBudgetObjective.year_id == ejercicio.id,
            GovernmentBudgetObjective.company_id == ejercicio.company_id,
        )
        .order_by(GovernmentBudgetObjective.codigo)
    ).scalars().all()
    categorias = db.execute(
        select(GovernmentBudgetCategory)
        .where(
            GovernmentBudgetCategory.year_id == ejercicio.id,
            GovernmentBudgetCategory.company_id == ejercicio.company_id,
        )
        .order_by(GovernmentBudgetCategory.codigo_completo)
    ).scalars().all()
    metas = db.execute(
        select(GovernmentBudgetGoal)
        .where(
            GovernmentBudgetGoal.year_id == ejercicio.id,
            GovernmentBudgetGoal.company_id == ejercicio.company_id,
        )
        .order_by(GovernmentBudgetGoal.descripcion)
    ).scalars().all()

    categoria_por_id = {str(c.id): c for c in categorias}
    vinculos = []
    for categoria in categorias:
        if categoria.unit_id is None and categoria.objective_id is None:
            continue
        unidad = db.get(GovernmentUnit, categoria.unit_id) if categoria.unit_id else None
        objetivo = db.get(GovernmentBudgetObjective, categoria.objective_id) if categoria.objective_id else None
        vinculos.append(
            {
                "codigo_completo": categoria.codigo_completo,
                "unidad": unidad.code if unidad else None,
                "objetivo": objetivo.codigo if objetivo else None,
            }
        )
    metas_vista = []
    for meta in metas:
        categoria_meta = categoria_por_id.get(str(meta.category_id))
        codigo_completo = categoria_meta.codigo_completo if categoria_meta else ""
        metas_vista.append(
            {
                "codigo_completo": codigo_completo,
                "descripcion": meta.descripcion,
                "unidad_medida": meta.unidad_medida,
                "cantidad": str(meta.cantidad),
                "indicador": meta.indicador,
                "formula": meta.formula,
            }
        )
    return {
        "plan": {
            "denominacion": plan.denominacion,
            "documento_sha256": plan.documento_sha256,
        }
        if plan
        else None,
        "objetivos": [
            {"codigo": o.codigo, "descripcion": o.descripcion} for o in objetivos
        ],
        "vinculos": vinculos,
        "metas": metas_vista,
    }
