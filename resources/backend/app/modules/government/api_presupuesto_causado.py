"""API del causado presupuestario (BUD-09)."""

from __future__ import annotations

import io
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Header, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import require_module, require_permission, require_write_allowed
from app.modules.government import service_presupuesto_causado
from app.modules.government.api import _version
from app.modules.government.schemas_presupuesto_causado import (
    ActivarPoliticaIn,
    AnularCausadoIn,
    CausadoCreate,
    CausadoUpdate,
    CerrarPoliticaIn,
    ConfiguracionIn,
    PoliticaCreate,
    PoliticaUpdate,
)
from app.modules.identity_access.models import User

router = APIRouter(prefix="/gobierno/presupuesto", tags=["gobierno"])


@router.get("/causados/configuracion")
def get_causados_configuracion(
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_presupuesto", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> dict[str, Any]:
    return service_presupuesto_causado._configuracion_actual(db, ctx)


@router.put("/causados/configuracion")
def put_causados_configuracion(
    cuerpo: ConfiguracionIn,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_presupuesto", "cause_policy")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> dict[str, Any]:
    version = _version(if_match)
    resultado = service_presupuesto_causado._actualizar_configuracion(
        db, ctx, cuerpo.model_dump(), version
    )
    db.commit()
    return resultado


@router.get("/politicas-causado")
def get_politicas_causado(
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_presupuesto", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> list[dict[str, Any]]:
    return service_presupuesto_causado.listar_politicas(db, ctx)


@router.get("/politicas-causado/{policy_id}")
def get_politica_causado(
    policy_id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_presupuesto", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> dict[str, Any]:
    return service_presupuesto_causado._obtener_politica(db, ctx, policy_id)


@router.post("/politicas-causado", status_code=status.HTTP_201_CREATED)
def post_politica_causado(
    cuerpo: PoliticaCreate,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_presupuesto", "cause_policy")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
) -> dict[str, Any]:
    resultado = service_presupuesto_causado._crear_politica(db, ctx, cuerpo.model_dump())
    db.commit()
    return resultado


@router.put("/politicas-causado/{policy_id}")
def put_politica_causado(
    policy_id: str,
    cuerpo: PoliticaUpdate,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_presupuesto", "cause_policy")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> dict[str, Any]:
    version = _version(if_match)
    resultado = service_presupuesto_causado._actualizar_politica(
        db, ctx, policy_id, version, cuerpo.model_dump(exclude_unset=True)
    )
    db.commit()
    return resultado


@router.post("/politicas-causado/{policy_id}/activar")
def post_politica_causado_activar(
    policy_id: str,
    cuerpo: ActivarPoliticaIn,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_presupuesto", "cause_policy")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> dict[str, Any]:
    version = _version(if_match)
    resultado = service_presupuesto_causado._activar_politica(
        db, ctx, policy_id, version, cuerpo.model_dump()
    )
    db.commit()
    return resultado


@router.post("/politicas-causado/{policy_id}/cerrar")
def post_politica_causado_cerrar(
    policy_id: str,
    cuerpo: CerrarPoliticaIn,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_presupuesto", "cause_policy")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> dict[str, Any]:
    version = _version(if_match)
    resultado = service_presupuesto_causado._cerrar_politica(
        db, ctx, policy_id, version, cuerpo.model_dump()
    )
    db.commit()
    return resultado


@router.get("/ejercicios/{year_id}/causados")
def get_ejercicios_causados(
    year_id: str,
    estado: str | None = None,
    compromiso_id: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_presupuesto", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> dict[str, Any]:
    return service_presupuesto_causado._listar_causados(
        db, ctx, year_id, estado, compromiso_id, desde, hasta, q
    )


@router.get("/ejercicios/{year_id}/causados/reporte.csv")
def get_ejercicios_causados_reporte(
    year_id: str,
    estado: str | None = None,
    compromiso_id: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_presupuesto", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> StreamingResponse:
    year = service_presupuesto_causado._ejercicio_de_empresa(db, ctx, year_id)
    salida = service_presupuesto_causado._reporte_causados_csv(
        db, ctx, year_id, estado, compromiso_id, desde, hasta, q
    )
    contenido = "\ufeff" + salida.getvalue()
    return StreamingResponse(
        io.StringIO(contenido),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="causados-{year.anio}.csv"'},
    )


@router.get("/ejercicios/{year_id}/causados/opciones")
def get_ejercicios_causados_opciones(
    year_id: str,
    compromiso_id: str | None = None,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_presupuesto", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> dict[str, Any]:
    return service_presupuesto_causado._opciones_causados(
        db, ctx, year_id, compromiso_id, service_presupuesto_causado.hoy_de_negocio()
    )


@router.post("/ejercicios/{year_id}/causados", status_code=status.HTTP_201_CREATED)
def post_ejercicios_causados(
    year_id: str,
    cuerpo: CausadoCreate,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_presupuesto", "cause")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
) -> dict[str, Any]:
    resultado = service_presupuesto_causado._crear_causa(db, ctx, year_id, cuerpo.model_dump())
    db.commit()
    return resultado


@router.get("/causados/{causa_id}")
def get_causado(
    causa_id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_presupuesto", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> dict[str, Any]:
    return service_presupuesto_causado._obtener_causa(db, ctx, causa_id)


@router.get("/causados/{causa_id}/controles")
def get_causado_controles(
    causa_id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_presupuesto", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> dict[str, Any]:
    return service_presupuesto_causado._obtener_controles(db, ctx, causa_id)


@router.put("/causados/{causa_id}")
def put_causado(
    causa_id: str,
    cuerpo: CausadoUpdate,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_presupuesto", "cause")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> dict[str, Any]:
    version = _version(if_match)
    resultado = service_presupuesto_causado._actualizar_causa(
        db, ctx, causa_id, version, cuerpo.model_dump(exclude_unset=True)
    )
    db.commit()
    return resultado


@router.post("/causados/{causa_id}/formalizar")
def post_causado_formalizar(
    causa_id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_presupuesto", "cause")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> dict[str, Any]:
    version = _version(if_match)
    resultado = service_presupuesto_causado._formalizar_causa(db, ctx, causa_id, version)
    db.commit()
    return resultado


@router.post("/causados/{causa_id}/anular")
def post_causado_anular(
    causa_id: str,
    cuerpo: AnularCausadoIn,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_presupuesto", "cause")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> dict[str, Any]:
    version = _version(if_match)
    resultado = service_presupuesto_causado._anular_causa(
        db, ctx, causa_id, version, cuerpo.model_dump()
    )
    db.commit()
    return resultado
