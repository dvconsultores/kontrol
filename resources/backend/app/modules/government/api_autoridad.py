"""API de solo lectura de la matriz auditable de autoridad (ORG-07, GOV-ORG-010).

La matriz es una proyección de los cargos de ORG-03 (`/gobierno/autoridad`); la empresa la fija el contexto y todo exige el módulo `gobierno`.
"""

from __future__ import annotations

import io
from datetime import date

from fastapi import APIRouter, Depends, Path, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import require_module, require_permission
from app.modules.government import service_autoridad
from app.modules.government.schemas_autoridad import (
    MatrizAutoridad,
    MatrizDetalleCargo,
    MatrizEjercicios,
    MatrizFiltros,
)
from app.modules.government.schemas_cargos import (
    AccionCompetencia,
    MateriaCompetencia,
)
from app.modules.identity_access.models import User

router = APIRouter(prefix="/gobierno/autoridad", tags=["gobierno"])


@router.get("/ejercicios", response_model=MatrizEjercicios)
def listar_ejercicios(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_autoridad", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_autoridad.listar_ejercicios(db, ctx)


@router.get("/{ejercicio}/filtros", response_model=MatrizFiltros)
def filtros(
    ejercicio: int = Path(ge=2000, le=2100),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_autoridad", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_autoridad.filtros(db, ctx, ejercicio)


@router.get("/{ejercicio}/exportar")
def exportar(
    ejercicio: int = Path(ge=2000, le=2100),
    fecha: date | None = None,
    unidad_id: str | None = Query(None, max_length=36),
    cargo_id: str | None = Query(None, max_length=36),
    accion: AccionCompetencia | None = None,
    materia: MateriaCompetencia | None = None,
    texto: str | None = Query(None, min_length=1, max_length=100),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_autoridad", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    nombre, contenido = service_autoridad.exportar_matriz_csv(
        db,
        ctx,
        ejercicio,
        fecha=fecha,
        unidad_id=unidad_id,
        cargo_id=cargo_id,
        accion=accion,
        materia=materia,
        texto=texto,
    )
    db.commit()
    return StreamingResponse(
        io.BytesIO(contenido),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@router.get("/{ejercicio}/cargos/{cargo_id}", response_model=MatrizDetalleCargo)
def detalle_cargo(
    ejercicio: int = Path(ge=2000, le=2100),
    cargo_id: str = Path(max_length=36),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_autoridad", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_autoridad.detalle_cargo(db, ctx, ejercicio, cargo_id)


@router.get("/{ejercicio}", response_model=MatrizAutoridad)
def matriz(
    ejercicio: int = Path(ge=2000, le=2100),
    fecha: date | None = None,
    unidad_id: str | None = Query(None, max_length=36),
    cargo_id: str | None = Query(None, max_length=36),
    accion: AccionCompetencia | None = None,
    materia: MateriaCompetencia | None = None,
    texto: str | None = Query(None, min_length=1, max_length=100),
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(50, ge=10, le=200),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_autoridad", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_autoridad.matriz(
        db,
        ctx,
        ejercicio,
        fecha=fecha,
        unidad_id=unidad_id,
        cargo_id=cargo_id,
        accion=accion,
        materia=materia,
        texto=texto,
        pagina=pagina,
        por_pagina=por_pagina,
    )
