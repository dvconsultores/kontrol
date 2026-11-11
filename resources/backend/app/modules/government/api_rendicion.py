"""API de rendición de cuentas (CTL-05)."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, Query, Response, status
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import require_module, require_permission, require_write_allowed
from app.core.errors import ConflictError
from app.modules.government import service_rendicion as sr
from app.modules.government.schemas_rendicion import (
    RendicionCalificacionCreate,
    RendicionExpedienteCreate,
    RendicionExpedienteUpdate,
    RendicionFenecimientoCreate,
    RendicionNuevaVersionCreate,
    RendicionParticipacionCreate,
    RendicionPiezaCreate,
)
from app.modules.government.service_auditoria import _usuarios_por_ids
from app.modules.government.service_rendicion import (
    _actualizar,
    _auditar_exportado,
    _calificar,
    _candidatas,
    _cargar_expediente,
    _crear,
    _exportar_csv,
    _exportar_pdf,
    _fenecer,
    _ficha,
    _formar,
    _incluidas_ids,
    _incorporar,
    _nueva_version,
    _participar,
    _retirar_pieza,
    _snapshot_out,
    verificar_integridad,
)
from app.shared.audit import record_audit

router = APIRouter(prefix="/gobierno/rendicion", tags=["Gobierno - Rendición"])


def _permiso(capacidad: str):
    return require_permission("gobierno_rendicion", capacidad)


def _usuario_o_empty(ctx: CompanyContext) -> str:
    return ctx.user_id or ""


@router.get("/opciones")
def opciones(
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _: Any = Depends(require_module("gobierno")),
    __: Any = Depends(_permiso("view")),
):
    from sqlalchemy import select as _select

    from app.modules.government.models import GovernmentAssignment, GovernmentPosition
    from app.modules.government.service_rendicion import _snapshot_responsable

    asignaciones = db.scalars(
        _select(GovernmentAssignment).where(
            GovernmentAssignment.company_id == ctx.company_id,
            GovernmentAssignment.status.notin_(["BORRADOR", "DESCARTADO"]),
        )
    ).all()
    responsables = []
    for a in asignaciones:
        asignacion_id = str(a.id)
        pos = db.get(GovernmentPosition, a.position_id)
        snap = _snapshot_responsable(db, ctx, asignacion_id)
        responsables.append(
            {
                "asignacion_id": str(a.id),
                "codigo": a.codigo or "",
                "funcionario": snap["funcionario"],
                "cargo": snap["cargo"],
                "unidad": snap["unidad"],
                "figura": snap["figura"],
                "desde": a.desde.isoformat(),
                "official_id": str(a.official_id),
                "unidad_id": str(pos.unit_id) if pos else None,
                "hasta": a.hasta.isoformat() if a.hasta else None,
            }
        )
    procesos = [{"codigo": codigo, "nombre": nombre} for codigo, nombre, _ in sr.PROCESOS]
    return {"responsables": responsables, "procesos": procesos, "estados": sr.ESTADOS}


@router.get("/expedientes")
def listar_expedientes(
    estado: str | None = None,
    texto: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    responsable: str | None = None,
    unidad: str | None = None,
    pagina: int = Query(default=1),
    por_pagina: int = Query(default=20),
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _: Any = Depends(require_module("gobierno")),
    __: Any = Depends(_permiso("view")),
):
    from sqlalchemy import func as _func
    from sqlalchemy import or_
    from sqlalchemy import select as _select

    from app.modules.government.models import GovernmentRenditionFile

    if por_pagina < 1 or por_pagina > 50:
        raise sr._invalid_page()
    filtros = [GovernmentRenditionFile.company_id == ctx.company_id]
    if estado:
        filtros.append(GovernmentRenditionFile.estado == estado)
    if texto:
        patron = f"%{texto}%"
        filtros.append(
            or_(
                GovernmentRenditionFile.codigo.ilike(patron),
                GovernmentRenditionFile.denominacion.ilike(patron),
            )
        )
    if desde:
        filtros.append(GovernmentRenditionFile.periodo_hasta >= desde)
    if hasta:
        filtros.append(GovernmentRenditionFile.periodo_desde <= hasta)
    if responsable:
        filtros.append(GovernmentRenditionFile.responsable_official_id == responsable)
    if unidad:
        from app.modules.government.models import GovernmentAssignment, GovernmentPosition

        asignaciones_ids = db.scalars(
            _select(GovernmentAssignment.id).where(
                GovernmentAssignment.company_id == ctx.company_id,
                GovernmentAssignment.position_id.in_(
                    _select(GovernmentPosition.id).where(
                        GovernmentPosition.company_id == ctx.company_id,
                        GovernmentPosition.unit_id == unidad,
                    )
                ),
            )
        ).all()
        filtros.append(GovernmentRenditionFile.assignment_id.in_(asignaciones_ids))
    total = db.scalar(_select(_func.count()).select_from(GovernmentRenditionFile).where(*filtros)) or 0
    expedientes = db.scalars(
        _select(GovernmentRenditionFile)
        .where(*filtros)
        .order_by(GovernmentRenditionFile.created_at.desc())
        .offset((pagina - 1) * por_pagina)
        .limit(por_pagina)
    ).all()
    items = [_ficha(db, ctx, e) for e in expedientes]
    return {"items": items, "total": total, "pagina": pagina, "por_pagina": por_pagina}


@router.post("/expedientes", status_code=status.HTTP_201_CREATED)
def crear_expediente(
    datos: RendicionExpedienteCreate,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _: Any = Depends(require_module("gobierno")),
    __: Any = Depends(_permiso("form")),
    ___: Any = Depends(require_write_allowed),
):
    expediente = _crear(db, ctx, datos.model_dump())
    db.commit()
    return _ficha(db, ctx, expediente)


@router.get("/expedientes/{id}")
def obtener_expediente(
    id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _: Any = Depends(require_module("gobierno")),
    __: Any = Depends(_permiso("view")),
):
    return _ficha(db, ctx, _cargar_expediente(db, ctx, id))


@router.put("/expedientes/{id}")
def actualizar_expediente(
    id: str,
    datos: RendicionExpedienteUpdate,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _: Any = Depends(require_module("gobierno")),
    __: Any = Depends(_permiso("form")),
    ___: Any = Depends(require_write_allowed),
):
    if not if_match:
        raise ConflictError(code="VERSION_CONFLICT", message="If-Match requerido.")
    try:
        version = int(if_match)
    except ValueError:
        raise ConflictError(code="VERSION_CONFLICT", message="If-Match inválido.") from None
    expediente = _actualizar(db, ctx, id, datos.model_dump(), version=version)
    db.commit()
    return _ficha(db, ctx, expediente)


@router.get("/expedientes/{id}/candidatas")
def candidatas(
    id: str,
    proceso: str | None = None,
    accion: str | None = None,
    texto: str | None = None,
    pagina: int = Query(default=1),
    por_pagina: int = Query(default=20),
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _: Any = Depends(require_module("gobierno")),
    __: Any = Depends(_permiso("view")),
):
    expediente = _cargar_expediente(db, ctx, id)
    eventos, total = _candidatas(db, ctx, expediente, proceso, accion, texto, pagina, por_pagina)
    expediente_id = str(expediente.id)
    incluidas = _incluidas_ids(db, expediente_id)
    resumenes = sr._resumenes(db, eventos)
    usuarios = _usuarios_por_ids(db, [e.user_id or "" for e in eventos], ctx.tenant_id)
    items = []
    for evento in eventos:
        resumen = next((r for r in resumenes if r.id == evento.id), None)
        if resumen is None:
            continue
        objeto = sr._objeto_desde_evento(db, evento, ctx)
        detalle, _ = sr._detalle_de_evento_para_catalogo(evento)
        items.append(
            {
                "evento_id": str(evento.id),
                "fecha": evento.event_time,
                "proceso": resumen.proceso,
                "proceso_nombre": resumen.proceso_nombre,
                "accion": resumen.accion,
                "accion_etiqueta": resumen.accion_etiqueta,
                "usuario": usuarios.get(str(evento.user_id or ""), evento.user_id or ""),
                "referencia": sr._referencia_desde_accion(resumen.accion, detalle),
                "objeto": objeto.model_dump() if objeto else None,
                "incluida": str(evento.id) in incluidas,
            }
        )
    return {"items": items, "total": total, "pagina": pagina, "por_pagina": por_pagina}


@router.post("/expedientes/{id}/piezas", status_code=status.HTTP_201_CREATED)
def incorporar_pieza(
    id: str,
    datos: RendicionPiezaCreate,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _: Any = Depends(require_module("gobierno")),
    __: Any = Depends(_permiso("form")),
    ___: Any = Depends(require_write_allowed),
):
    pieza = _incorporar(db, ctx, id, datos.evento_id)
    db.commit()
    expediente = _cargar_expediente(db, ctx, id)
    expediente_id = str(expediente.id)
    piezas = sr._ordinales_provisionales(db, expediente_id)
    orden = next((i + 1 for i, p in enumerate(piezas) if p.id == pieza.id and pieza.id), len(piezas))
    return sr._pieza_out(db, ctx, expediente, pieza, orden)


@router.delete("/expedientes/{id}/piezas/{pieza_id}", status_code=status.HTTP_204_NO_CONTENT)
def retirar_pieza(
    id: str,
    pieza_id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _: Any = Depends(require_module("gobierno")),
    __: Any = Depends(_permiso("form")),
    ___: Any = Depends(require_write_allowed),
):
    _retirar_pieza(db, ctx, id, pieza_id)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/expedientes/{id}/formar")
def formar(
    id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _: Any = Depends(require_module("gobierno")),
    __: Any = Depends(_permiso("form")),
    ___: Any = Depends(require_write_allowed),
):
    expediente = _formar(db, ctx, id)
    db.commit()
    return _ficha(db, ctx, expediente)


@router.get("/expedientes/{id}/reporte")
def reporte(
    id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _: Any = Depends(require_module("gobierno")),
    __: Any = Depends(_permiso("view")),
):
    return _snapshot_out(db, ctx, _cargar_expediente(db, ctx, id))


@router.get("/expedientes/{id}/reporte.pdf")
def reporte_pdf(
    id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _: Any = Depends(require_module("gobierno")),
    __: Any = Depends(_permiso("view")),
):
    expediente = _cargar_expediente(db, ctx, id)
    nombre, contenido = _exportar_pdf(db, ctx, expediente)
    _auditar_exportado(db, ctx, expediente, "PDF")
    db.commit()
    return Response(
        content=contenido,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@router.get("/expedientes/{id}/indice.csv")
def indice_csv(
    id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _: Any = Depends(require_module("gobierno")),
    __: Any = Depends(_permiso("view")),
):
    expediente = _cargar_expediente(db, ctx, id)
    nombre, contenido = _exportar_csv(db, ctx, expediente)
    _auditar_exportado(db, ctx, expediente, "CSV")
    db.commit()
    return Response(
        content=contenido,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@router.get("/expedientes/{id}/integridad")
def integridad(
    id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _: Any = Depends(require_module("gobierno")),
    __: Any = Depends(_permiso("view")),
):
    expediente = _cargar_expediente(db, ctx, id)
    resultado = verificar_integridad(db, ctx, expediente)
    record_audit(
        db,
        action="GOV_RENDITION_FILE_VERIFIED",
        entity_type="GovernmentRenditionFile",
        entity_id=str(expediente.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after={"codigo": expediente.codigo, "estado": resultado["estado"]},
    )
    db.commit()
    return resultado


@router.post("/expedientes/{id}/participacion")
def participacion(
    id: str,
    datos: RendicionParticipacionCreate,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _: Any = Depends(require_module("gobierno")),
    __: Any = Depends(_permiso("form")),
    ___: Any = Depends(require_write_allowed),
):
    expediente = _participar(db, ctx, id, datos.fecha, datos.oficio)
    db.commit()
    return _ficha(db, ctx, expediente)


@router.post("/expedientes/{id}/calificacion")
def calificacion(
    id: str,
    datos: RendicionCalificacionCreate,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _: Any = Depends(require_module("gobierno")),
    __: Any = Depends(_permiso("qualify")),
    ___: Any = Depends(require_write_allowed),
):
    expediente = _calificar(db, ctx, id, datos.model_dump())
    db.commit()
    return _ficha(db, ctx, expediente)


@router.post("/expedientes/{id}/fenecimiento")
def fenecimiento(
    id: str,
    datos: RendicionFenecimientoCreate,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _: Any = Depends(require_module("gobierno")),
    __: Any = Depends(_permiso("qualify")),
    ___: Any = Depends(require_write_allowed),
):
    expediente = _fenecer(db, ctx, id, datos.model_dump())
    db.commit()
    return _ficha(db, ctx, expediente)


@router.post("/expedientes/{id}/nueva-version", status_code=status.HTTP_201_CREATED)
def nueva_version(
    id: str,
    datos: RendicionNuevaVersionCreate,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _: Any = Depends(require_module("gobierno")),
    __: Any = Depends(_permiso("form")),
    ___: Any = Depends(require_write_allowed),
):
    expediente = _nueva_version(db, ctx, id, datos.motivo)
    db.commit()
    return _ficha(db, ctx, expediente)


@router.get("/expedientes/{id}/historial")
def historial(
    id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _: Any = Depends(require_module("gobierno")),
    __: Any = Depends(_permiso("view")),
):
    expediente = _cargar_expediente(db, ctx, id)
    ids: set[str] = {str(expediente.id)}
    actual = expediente
    while actual.anterior_id:
        ids.add(str(actual.anterior_id))
        anterior = db.scalar(
            sr.select(sr.GovernmentRenditionFile).where(
                sr.GovernmentRenditionFile.id == actual.anterior_id,
                sr.GovernmentRenditionFile.company_id == ctx.company_id,
            )
        )
        if not anterior:
            break
        actual = anterior
    hijas = db.scalars(
        sr.select(sr.GovernmentRenditionFile).where(
            sr.GovernmentRenditionFile.anterior_id.in_(ids),
            sr.GovernmentRenditionFile.company_id == ctx.company_id,
        )
    ).all()
    for hija in hijas:
        ids.add(str(hija.id))
    from app.modules.audit.models import AuditEvent

    eventos = db.scalars(
        sr.select(AuditEvent)
        .where(
            AuditEvent.entity_type == "GovernmentRenditionFile",
            AuditEvent.entity_id.in_([str(i) for i in ids]),
            AuditEvent.company_id == ctx.company_id,
        )
        .order_by(AuditEvent.event_time)
    ).all()
    items = []
    for evento in eventos:
        catalogo = sr.catalog()
        items.append(
            {
                "fecha": evento.event_time,
                "accion": evento.action,
                "accion_etiqueta": (spec.label if (spec := catalogo.get((evento.action, evento.entity_type))) is not None else evento.action),
                "usuario": evento.user_id or "",
                "motivo": (evento.after or {}).get("motivo") if isinstance(evento.after, dict) else None,
                "version": (evento.after or {}).get("numero_version") if isinstance(evento.after, dict) else None,
            }
        )
    return {"items": items}
