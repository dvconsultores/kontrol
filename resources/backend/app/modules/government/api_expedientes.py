from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import require_module, require_permission, require_write_allowed
from app.modules.government import service_expedientes
from app.modules.government import service_expedientes_acciones as acciones
from app.modules.government.api import _version
from app.modules.government.schemas_expedientes import (
    ExpedienteActuacionIn,
    ExpedienteCatalogo,
    ExpedienteComisionIn,
    ExpedienteCronologia,
    ExpedienteDescarteIn,
    ExpedienteDetalle,
    ExpedienteEdicionIn,
    ExpedienteFinIn,
    ExpedienteFolioIn,
    ExpedienteHitoCambioIn,
    ExpedienteHitoIn,
    ExpedienteIn,
    ExpedienteOpciones,
    ExpedienteResponsableIn,
    ExpedientesListado,
)
from app.modules.identity_access.models import User

router = APIRouter(prefix="/gobierno/contrataciones/expedientes", tags=["gobierno"])


@router.get("/catalogo", response_model=ExpedienteCatalogo)
def catalogo(db: Session = Depends(get_db), _user: User = Depends(require_permission("gobierno_expedientes", "view")), ctx: CompanyContext = Depends(get_company_context), _modulo: None = Depends(require_module("gobierno"))):
    return service_expedientes.catalogo()


@router.get("/opciones", response_model=ExpedienteOpciones)
def opciones(db: Session = Depends(get_db), _user: User = Depends(require_permission("gobierno_expedientes", "view")), ctx: CompanyContext = Depends(get_company_context), _modulo: None = Depends(require_module("gobierno"))):
    return service_expedientes.opciones(db, ctx)


@router.get("", response_model=ExpedientesListado)
def listar(q: str | None = Query(default=None, max_length=100), status: str | None = None, unidad_id: str | None = None, responsable_id: str | None = None, modalidad: str | None = None, desde: date | None = None, hasta: date | None = None, pagina: int = Query(default=1, ge=1), por_pagina: int = Query(default=25, ge=10, le=200), db: Session = Depends(get_db), _user: User = Depends(require_permission("gobierno_expedientes", "view")), ctx: CompanyContext = Depends(get_company_context), _modulo: None = Depends(require_module("gobierno"))):
    return service_expedientes.listar(db, ctx, q=q, status=status, unidad_id=unidad_id, responsable_id=responsable_id, modalidad=modalidad, desde=desde, hasta=hasta, pagina=pagina, por_pagina=por_pagina)


@router.post("", status_code=201, response_model=ExpedienteDetalle, dependencies=[Depends(require_write_allowed)])
def crear(datos: ExpedienteIn, db: Session = Depends(get_db), _user: User = Depends(require_permission("gobierno_expedientes", "manage")), ctx: CompanyContext = Depends(get_company_context), _modulo: None = Depends(require_module("gobierno"))):
    resultado = service_expedientes.crear(db, ctx, datos.model_dump())
    db.commit()
    return resultado


@router.get("/{expediente_id}", response_model=ExpedienteDetalle)
def detalle(expediente_id: str, db: Session = Depends(get_db), _user: User = Depends(require_permission("gobierno_expedientes", "view")), ctx: CompanyContext = Depends(get_company_context), _modulo: None = Depends(require_module("gobierno"))):
    return service_expedientes.detalle(db, ctx, expediente_id)


@router.get("/{expediente_id}/cronologia", response_model=ExpedienteCronologia)
def cronologia(expediente_id: str, clases: str | None = None, pagina: int = Query(default=1, ge=1), por_pagina: int = Query(default=50, ge=10, le=200), db: Session = Depends(get_db), _user: User = Depends(require_permission("gobierno_expedientes", "view")), ctx: CompanyContext = Depends(get_company_context), _modulo: None = Depends(require_module("gobierno"))):
    lista_clases = [c.strip() for c in clases.split(",") if c.strip()] if clases else None
    return service_expedientes.cronologia(db, ctx, expediente_id, clases=lista_clases, pagina=pagina, por_pagina=por_pagina)


@router.patch("/{expediente_id}", response_model=ExpedienteDetalle, dependencies=[Depends(require_write_allowed)])
def editar(expediente_id: str, datos: ExpedienteEdicionIn, if_match: str | None = Header(default=None, alias="If-Match"), db: Session = Depends(get_db), _user: User = Depends(require_permission("gobierno_expedientes", "manage")), ctx: CompanyContext = Depends(get_company_context), _modulo: None = Depends(require_module("gobierno"))):
    resultado = service_expedientes.editar(db, ctx, expediente_id, _version(if_match), datos.model_dump(exclude_unset=True))
    db.commit()
    return resultado


@router.post("/{expediente_id}/descartar", response_model=ExpedienteDetalle, dependencies=[Depends(require_write_allowed)])
def descartar(expediente_id: str, datos: ExpedienteDescarteIn, if_match: str | None = Header(default=None, alias="If-Match"), db: Session = Depends(get_db), _user: User = Depends(require_permission("gobierno_expedientes", "manage")), ctx: CompanyContext = Depends(get_company_context), _modulo: None = Depends(require_module("gobierno"))):
    resultado = acciones.descartar(db, ctx, expediente_id, _version(if_match), datos.model_dump())
    db.commit()
    return resultado


@router.post("/{expediente_id}/cerrar", response_model=ExpedienteDetalle, dependencies=[Depends(require_write_allowed)])
def cerrar(expediente_id: str, datos: ExpedienteFinIn, if_match: str | None = Header(default=None, alias="If-Match"), db: Session = Depends(get_db), _user: User = Depends(require_permission("gobierno_expedientes", "close")), ctx: CompanyContext = Depends(get_company_context), _modulo: None = Depends(require_module("gobierno"))):
    resultado = acciones.cerrar(db, ctx, expediente_id, _version(if_match), datos.model_dump())
    db.commit()
    return resultado


@router.post("/{expediente_id}/responsables", response_model=ExpedienteDetalle, dependencies=[Depends(require_write_allowed)])
def asignar_responsable(expediente_id: str, datos: ExpedienteResponsableIn, if_match: str | None = Header(default=None, alias="If-Match"), db: Session = Depends(get_db), _user: User = Depends(require_permission("gobierno_expedientes", "manage")), ctx: CompanyContext = Depends(get_company_context), _modulo: None = Depends(require_module("gobierno"))):
    resultado = acciones.asignar_responsable(db, ctx, expediente_id, _version(if_match), datos.model_dump())
    db.commit()
    return resultado


@router.post("/{expediente_id}/responsables/{responsable_id}/terminar", response_model=ExpedienteDetalle, dependencies=[Depends(require_write_allowed)])
def terminar_responsable(expediente_id: str, responsable_id: str, datos: ExpedienteFinIn, if_match: str | None = Header(default=None, alias="If-Match"), db: Session = Depends(get_db), _user: User = Depends(require_permission("gobierno_expedientes", "manage")), ctx: CompanyContext = Depends(get_company_context), _modulo: None = Depends(require_module("gobierno"))):
    resultado = acciones.terminar_responsable(db, ctx, expediente_id, _version(if_match), responsable_id, datos.model_dump())
    db.commit()
    return resultado


@router.post("/{expediente_id}/comision", response_model=ExpedienteDetalle, dependencies=[Depends(require_write_allowed)])
def registrar_comision(expediente_id: str, datos: ExpedienteComisionIn, if_match: str | None = Header(default=None, alias="If-Match"), db: Session = Depends(get_db), _user: User = Depends(require_permission("gobierno_expedientes", "manage")), ctx: CompanyContext = Depends(get_company_context), _modulo: None = Depends(require_module("gobierno"))):
    resultado = acciones.registrar_comision(db, ctx, expediente_id, _version(if_match), datos.model_dump())
    db.commit()
    return resultado


@router.post("/{expediente_id}/actuaciones", response_model=ExpedienteDetalle, dependencies=[Depends(require_write_allowed)])
def registrar_actuacion(expediente_id: str, datos: ExpedienteActuacionIn, if_match: str | None = Header(default=None, alias="If-Match"), db: Session = Depends(get_db), _user: User = Depends(require_permission("gobierno_expedientes", "manage")), ctx: CompanyContext = Depends(get_company_context), _modulo: None = Depends(require_module("gobierno"))):
    resultado = acciones.registrar_actuacion(db, ctx, expediente_id, _version(if_match), datos.model_dump())
    db.commit()
    return resultado


@router.post("/{expediente_id}/folios", response_model=ExpedienteDetalle, dependencies=[Depends(require_write_allowed)])
def incorporar_folio(expediente_id: str, datos: ExpedienteFolioIn, if_match: str | None = Header(default=None, alias="If-Match"), db: Session = Depends(get_db), _user: User = Depends(require_permission("gobierno_expedientes", "manage")), ctx: CompanyContext = Depends(get_company_context), _modulo: None = Depends(require_module("gobierno"))):
    resultado = acciones.incorporar_folio(db, ctx, expediente_id, _version(if_match), datos.model_dump())
    db.commit()
    return resultado


@router.post("/{expediente_id}/hitos", response_model=ExpedienteDetalle, dependencies=[Depends(require_write_allowed)])
def crear_hito(expediente_id: str, datos: ExpedienteHitoIn, if_match: str | None = Header(default=None, alias="If-Match"), db: Session = Depends(get_db), _user: User = Depends(require_permission("gobierno_expedientes", "manage")), ctx: CompanyContext = Depends(get_company_context), _modulo: None = Depends(require_module("gobierno"))):
    resultado = acciones.crear_hito(db, ctx, expediente_id, _version(if_match), datos.model_dump())
    db.commit()
    return resultado


@router.post("/{expediente_id}/hitos/{hito_id}/actualizar", response_model=ExpedienteDetalle, dependencies=[Depends(require_write_allowed)])
def actualizar_hito(expediente_id: str, hito_id: str, datos: ExpedienteHitoCambioIn, if_match: str | None = Header(default=None, alias="If-Match"), db: Session = Depends(get_db), _user: User = Depends(require_permission("gobierno_expedientes", "manage")), ctx: CompanyContext = Depends(get_company_context), _modulo: None = Depends(require_module("gobierno"))):
    resultado = acciones.actualizar_hito(db, ctx, expediente_id, _version(if_match), hito_id, datos.model_dump())
    db.commit()
    return resultado
