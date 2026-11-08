from __future__ import annotations

import io
from datetime import date

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_module, require_permission, require_write_allowed
from app.modules.government import service_identidad
from app.modules.government.api import _version
from app.modules.government.schemas_identidad import (
    CatalogoIdentidad,
    CategoriaRetirarIn,
    CategoriaRolIn,
    CategoriaRolOut,
    CategoriasListado,
    ConflictosIdentidad,
    ContextoInstitucional,
    EstadoVinculo,
    OpcionesIdentidad,
    PoliticaIdentidadIn,
    PoliticaIdentidadOut,
    VinculoDescartarIn,
    VinculoDetalle,
    VinculoFinIn,
    VinculoIn,
    VinculosListado,
)
from app.modules.identity_access.models import User

router = APIRouter(prefix="/gobierno/identidad", tags=["gobierno"])


@router.get("/catalogo", response_model=CatalogoIdentidad)
def catalogo_identidad(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_identidad", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_identidad.catalogo()


@router.get("/opciones", response_model=OpcionesIdentidad)
def opciones_identidad(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_identidad", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_identidad.opciones(db, ctx)


@router.get("/vinculos", response_model=VinculosListado)
def listar_vinculos(
    estado: EstadoVinculo | None = Query(None),
    usuario_id: str | None = Query(None, max_length=36),
    funcionario_id: str | None = Query(None, max_length=36),
    fecha: date | None = Query(None),
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(50, ge=10, le=200),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_identidad", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_identidad.listar(db, ctx, estado, usuario_id, funcionario_id, fecha, pagina, por_pagina)


@router.get("/vinculos.csv")
def exportar_vinculos_csv(
    estado: EstadoVinculo | None = Query(None),
    usuario_id: str | None = Query(None, max_length=36),
    funcionario_id: str | None = Query(None, max_length=36),
    fecha: date | None = Query(None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_identidad", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    nombre, contenido = service_identidad.exportar_csv(db, ctx, estado, usuario_id, funcionario_id, fecha)
    db.commit()
    return StreamingResponse(
        io.BytesIO(contenido),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@router.post("/vinculos", response_model=VinculoDetalle, status_code=201, dependencies=[Depends(require_write_allowed)])
def crear_vinculo(
    datos: VinculoIn,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_identidad", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    v = service_identidad.crear(db, ctx, datos)
    db.commit()
    return service_identidad.detalle(db, ctx, str(v.id), None)


@router.get("/vinculos/{vinculo_id}", response_model=VinculoDetalle)
def detalle_vinculo(
    vinculo_id: str,
    fecha: date | None = Query(None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_identidad", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_identidad.detalle(db, ctx, vinculo_id, fecha)


@router.patch("/vinculos/{vinculo_id}", response_model=VinculoDetalle, dependencies=[Depends(require_write_allowed)])
def editar_vinculo(
    vinculo_id: str,
    datos: VinculoIn,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_identidad", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    service_identidad.editar(db, ctx, vinculo_id, _version(if_match), datos)
    db.commit()
    return service_identidad.detalle(db, ctx, vinculo_id, None)


@router.post("/vinculos/{vinculo_id}/activar", response_model=VinculoDetalle, dependencies=[Depends(require_write_allowed)])
def activar_vinculo(
    vinculo_id: str,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_identidad", "activate")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    service_identidad.activar(db, ctx, vinculo_id, _version(if_match))
    db.commit()
    return service_identidad.detalle(db, ctx, vinculo_id, None)


@router.post("/vinculos/{vinculo_id}/descartar", response_model=VinculoDetalle, dependencies=[Depends(require_write_allowed)])
def descartar_vinculo(
    vinculo_id: str,
    datos: VinculoDescartarIn,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_identidad", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    service_identidad.descartar(db, ctx, vinculo_id, _version(if_match), datos)
    db.commit()
    return service_identidad.detalle(db, ctx, vinculo_id, None)


@router.post("/vinculos/{vinculo_id}/cerrar", response_model=VinculoDetalle, dependencies=[Depends(require_write_allowed)])
def cerrar_vinculo(
    vinculo_id: str,
    datos: VinculoFinIn,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_identidad", "revoke")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    service_identidad.cerrar(db, ctx, vinculo_id, _version(if_match), datos)
    db.commit()
    return service_identidad.detalle(db, ctx, vinculo_id, None)


@router.post("/vinculos/{vinculo_id}/revocar", response_model=VinculoDetalle, dependencies=[Depends(require_write_allowed)])
def revocar_vinculo(
    vinculo_id: str,
    datos: VinculoFinIn,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_identidad", "revoke")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    service_identidad.revocar(db, ctx, vinculo_id, _version(if_match), datos)
    db.commit()
    return service_identidad.detalle(db, ctx, vinculo_id, None)


@router.get("/mi-contexto", response_model=ContextoInstitucional)
def mi_contexto_institucional(
    fecha: date | None = Query(None),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_identidad.mi_contexto(db, ctx, fecha)


@router.get("/categorias", response_model=CategoriasListado)
def listar_categorias_identidad(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_identidad", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_identidad.listar_categorias(db, ctx)


@router.post("/categorias", response_model=CategoriaRolOut, status_code=201, dependencies=[Depends(require_write_allowed)])
def crear_categoria_identidad(
    datos: CategoriaRolIn,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_identidad", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_identidad.crear_categoria(db, ctx, datos)
    db.commit()
    return resultado


@router.post("/categorias/{categoria_id}/retirar", response_model=CategoriaRolOut, dependencies=[Depends(require_write_allowed)])
def retirar_categoria_identidad(
    categoria_id: str,
    datos: CategoriaRetirarIn,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_identidad", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_identidad.retirar_categoria(db, ctx, categoria_id, datos, _version(if_match))
    db.commit()
    return resultado


@router.get("/conflictos", response_model=ConflictosIdentidad)
def conflictos_identidad(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_identidad", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_identidad.conflictos(db, ctx)


@router.get("/politica", response_model=PoliticaIdentidadOut)
def politica_identidad(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_identidad", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_identidad.politica(db, ctx)


@router.post("/politica", response_model=PoliticaIdentidadOut, dependencies=[Depends(require_write_allowed)])
def cambiar_politica_identidad(
    datos: PoliticaIdentidadIn,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_identidad", "activate")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_identidad.cambiar_politica(db, ctx, datos, _version(if_match))
    db.commit()
    return resultado
