"""API de actas de entrega (CTL-09)."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, Query, Response, status
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import require_module, require_permission, require_write_allowed
from app.core.errors import KontrolError
from app.modules.government import service_actas as sa
from app.modules.government.schemas_actas import (
    ActaAnexoUpdate,
    ActaCreate,
    ActaObservacionCreate,
    ActaRemision,
    ActaSuscribir,
    ActaUpdate,
    ActaVerificacionCreate,
)
from app.shared.audit import record_audit

router = APIRouter(prefix="/gobierno/actas-entrega", tags=["Gobierno - Actas de entrega"])


def _permiso(capacidad: str):
    return require_permission("gobierno_actas", capacidad)


@router.get("/opciones")
def opciones(
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _: Any = Depends(require_module("gobierno")),
    __: Any = Depends(_permiso("view")),
):
    return sa._opciones(db, ctx)


@router.get("/actas")
def listar(
    estado: str | None = None,
    texto: str | None = None,
    ambito: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _: Any = Depends(require_module("gobierno")),
    __: Any = Depends(_permiso("view")),
):
    if por_pagina < 1 or por_pagina > 50:
        raise KontrolError(
            code="GOV_HANDOVER_INVALID_PAGE",
            message="Paginación fuera de rango.",
            status_code=422,
        )
    return sa._listar(
        db,
        ctx,
        estado=estado,
        texto=texto,
        ambito=ambito,
        desde=desde,
        hasta=hasta,
        pagina=pagina,
        por_pagina=por_pagina,
    )


@router.post("/actas", status_code=status.HTTP_201_CREATED)
def crear(
    cuerpo: ActaCreate,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _: Any = Depends(require_module("gobierno")),
    __: Any = Depends(_permiso("manage")),
    ___: Any = Depends(require_write_allowed),
):
    acta = sa._crear(
        db,
        ctx,
        assignment_id=cuerpo.assignment_id,
        receptor_official_id=cuerpo.receptor_official_id,
        receptor_assignment_id=cuerpo.receptor_assignment_id,
        modalidad=cuerpo.modalidad,
        testigos=[t.model_dump() for t in cuerpo.testigos],
        auditor_official_id=cuerpo.auditor_official_id,
        motivo=cuerpo.motivo,
        fundamento=cuerpo.fundamento,
        lugar=cuerpo.lugar,
        fecha_corte=cuerpo.fecha_corte,
    )
    db.commit()
    return sa._ficha(db, ctx, acta)


@router.get("/actas/{id}")
def ficha(
    id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _: Any = Depends(require_module("gobierno")),
    __: Any = Depends(_permiso("view")),
):
    acta = sa._cargar_acta(db, ctx, id)
    return sa._ficha(db, ctx, acta)


@router.put("/actas/{id}")
def actualizar(
    id: str,
    cuerpo: ActaUpdate,
    if_match: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _: Any = Depends(require_module("gobierno")),
    __: Any = Depends(_permiso("manage")),
    ___: Any = Depends(require_write_allowed),
):
    if if_match is None:
        from app.core.errors import ConflictError

        raise ConflictError(code="VERSION_CONFLICT", message="If-Match es obligatorio.")
    acta = sa._cargar_acta(db, ctx, id)
    acta = sa._actualizar(
        db,
        ctx,
        acta,
        version=int(if_match),
        receptor_official_id=cuerpo.receptor_official_id,
        receptor_assignment_id=cuerpo.receptor_assignment_id,
        modalidad=cuerpo.modalidad,
        testigos=[t.model_dump() for t in cuerpo.testigos],
        auditor_official_id=cuerpo.auditor_official_id,
        motivo=cuerpo.motivo,
        fundamento=cuerpo.fundamento,
        lugar=cuerpo.lugar,
        fecha_corte=cuerpo.fecha_corte,
    )
    db.commit()
    return sa._ficha(db, ctx, acta)


@router.get("/actas/{id}/anexos/{codigo}/vista")
def anexo_vista(
    id: str,
    codigo: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _: Any = Depends(require_module("gobierno")),
    __: Any = Depends(_permiso("view")),
):
    acta = sa._cargar_acta(db, ctx, id)
    return sa._contenido_anexo_vista(db, ctx, acta, codigo)


@router.put("/actas/{id}/anexos/{codigo}")
def actualizar_anexo(
    id: str,
    codigo: str,
    cuerpo: ActaAnexoUpdate,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _: Any = Depends(require_module("gobierno")),
    __: Any = Depends(_permiso("manage")),
    ___: Any = Depends(require_write_allowed),
):
    acta = sa._cargar_acta(db, ctx, id)
    acta = sa._actualizar_anexo(
        db,
        ctx,
        acta,
        codigo,
        incluir_generado=cuerpo.incluir_generado,
        documento_ids=cuerpo.documento_ids,
        constancia=cuerpo.constancia,
    )
    db.commit()
    return sa._ficha(db, ctx, acta)


@router.post("/actas/{id}/suscribir")
def suscribir(
    id: str,
    cuerpo: ActaSuscribir,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _: Any = Depends(require_module("gobierno")),
    __: Any = Depends(_permiso("manage")),
    ___: Any = Depends(require_write_allowed),
):
    acta = sa._cargar_acta(db, ctx, id, bloqueo=True)
    acta = sa._suscribir(
        db,
        ctx,
        acta,
        fecha_suscripcion=cuerpo.fecha_suscripcion,
        errores_deficiencias=cuerpo.errores_deficiencias,
    )
    db.commit()
    return sa._ficha(db, ctx, acta)


@router.post("/actas/{id}/remision")
def remision(
    id: str,
    cuerpo: ActaRemision,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _: Any = Depends(require_module("gobierno")),
    __: Any = Depends(_permiso("manage")),
    ___: Any = Depends(require_write_allowed),
):
    acta = sa._cargar_acta(db, ctx, id)
    acta = sa._remitir(db, ctx, acta, fecha=cuerpo.fecha)
    db.commit()
    return sa._ficha(db, ctx, acta)


@router.post("/actas/{id}/observaciones", status_code=status.HTTP_201_CREATED)
def observacion(
    id: str,
    cuerpo: ActaObservacionCreate,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _: Any = Depends(require_module("gobierno")),
    __: Any = Depends(_permiso("manage")),
    ___: Any = Depends(require_write_allowed),
):
    acta = sa._cargar_acta(db, ctx, id)
    acta = sa._observar(db, ctx, acta, fecha=cuerpo.fecha, texto=cuerpo.texto)
    db.commit()
    return sa._ficha(db, ctx, acta)


@router.post("/actas/{id}/verificacion")
def verificacion(
    id: str,
    cuerpo: ActaVerificacionCreate,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _: Any = Depends(require_module("gobierno")),
    __: Any = Depends(_permiso("verify")),
    ___: Any = Depends(require_write_allowed),
):
    acta = sa._cargar_acta(db, ctx, id)
    acta = sa._verificar(
        db,
        ctx,
        acta,
        numero=cuerpo.numero,
        fecha=cuerpo.fecha,
        resultado=cuerpo.resultado,
        fundamento=cuerpo.fundamento,
    )
    db.commit()
    return sa._ficha(db, ctx, acta)


@router.get("/actas/{id}/acta.pdf")
def acta_pdf(
    id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _: Any = Depends(require_module("gobierno")),
    __: Any = Depends(_permiso("view")),
):
    acta = sa._cargar_acta(db, ctx, id)
    contenido = sa._pdf_bytes(db, ctx, acta)
    record_audit(
        db,
        action="GOV_HANDOVER_ACT_EXPORTED",
        entity_type="GovernmentHandoverAct",
        entity_id=str(acta.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={"codigo": acta.codigo, "formato": "PDF"},
    )
    db.commit()
    return Response(
        content=contenido,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{acta.codigo}.pdf"'},
    )


@router.get("/actas/{id}/integridad")
def integridad(
    id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _: Any = Depends(require_module("gobierno")),
    __: Any = Depends(_permiso("view")),
):
    acta = sa._cargar_acta(db, ctx, id)
    resultado = sa.verificar_integridad(db, ctx, acta)
    record_audit(
        db,
        action="GOV_HANDOVER_ACT_INTEGRITY_CHECKED",
        entity_type="GovernmentHandoverAct",
        entity_id=str(acta.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={"codigo": acta.codigo, "estado": resultado["estado"]},
    )
    db.commit()
    return resultado


@router.get("/actas/{id}/historial")
def historial(
    id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _: Any = Depends(require_module("gobierno")),
    __: Any = Depends(_permiso("view")),
):
    acta = sa._cargar_acta(db, ctx, id)
    return sa._historial(db, ctx, acta)
