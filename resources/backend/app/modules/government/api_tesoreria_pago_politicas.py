"""API de políticas y configuración del pago (TRE-04, parte 2)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import require_module, require_permission, require_write_allowed
from app.modules.government import service_tesoreria_pago_politicas
from app.modules.government.api import _version
from app.modules.government.schemas_tesoreria_pago import (
    ActivarPoliticaPagoIn,
    CerrarPoliticaPagoIn,
    ConfiguracionPagoIn,
    MedioPagoCreate,
    MedioPagoUpdate,
    PoliticaPagoCreate,
    PoliticaPagoUpdate,
)
from app.modules.identity_access.models import User

router = APIRouter(prefix="/gobierno/tesoreria", tags=["gobierno"])


@router.get("/pagos/configuracion")
def get_pagos_configuracion(
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_pagos", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> dict[str, Any]:
    return service_tesoreria_pago_politicas.configuracion_actual(db, ctx)


@router.put("/pagos/configuracion")
def put_pagos_configuracion(
    cuerpo: ConfiguracionPagoIn,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_pagos", "policy")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> dict[str, Any]:
    version = _version(if_match)
    resultado = service_tesoreria_pago_politicas.actualizar_configuracion(
        db, ctx, cuerpo.model_dump(mode="python"), version
    )
    db.commit()
    return resultado


@router.get("/medios-pago")
def get_medios_pago(
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_pagos", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> list[dict[str, Any]]:
    return service_tesoreria_pago_politicas.listar_medios(db, ctx)


@router.post("/medios-pago", status_code=status.HTTP_201_CREATED)
def post_medios_pago(
    cuerpo: MedioPagoCreate,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_pagos", "policy")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
) -> dict[str, Any]:
    resultado = service_tesoreria_pago_politicas.crear_medio(
        db, ctx, cuerpo.model_dump(mode="python")
    )
    db.commit()
    return resultado


@router.get("/medios-pago/{method_id}")
def get_medio_pago(
    method_id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_pagos", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> dict[str, Any]:
    return service_tesoreria_pago_politicas.obtener_medio(db, ctx, method_id)


@router.put("/medios-pago/{method_id}")
def put_medio_pago(
    method_id: str,
    cuerpo: MedioPagoUpdate,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_pagos", "policy")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> dict[str, Any]:
    version = _version(if_match)
    resultado = service_tesoreria_pago_politicas.actualizar_medio(
        db, ctx, method_id, cuerpo.model_dump(mode="python"), version
    )
    db.commit()
    return resultado


@router.get("/politicas-pago")
def get_politicas_pago(
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_pagos", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> list[dict[str, Any]]:
    return service_tesoreria_pago_politicas.listar_politicas_pago(db, ctx)


@router.post("/politicas-pago", status_code=status.HTTP_201_CREATED)
def post_politicas_pago(
    cuerpo: PoliticaPagoCreate,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_pagos", "policy")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
) -> dict[str, Any]:
    resultado = service_tesoreria_pago_politicas.crear_politica_pago(
        db, ctx, cuerpo.model_dump(mode="python")
    )
    db.commit()
    return resultado


@router.get("/politicas-pago/{policy_id}")
def get_politica_pago(
    policy_id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_pagos", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> dict[str, Any]:
    return service_tesoreria_pago_politicas.obtener_politica_pago(db, ctx, policy_id)


@router.put("/politicas-pago/{policy_id}")
def put_politica_pago(
    policy_id: str,
    cuerpo: PoliticaPagoUpdate,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_pagos", "policy")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> dict[str, Any]:
    version = _version(if_match)
    resultado = service_tesoreria_pago_politicas.actualizar_politica_pago(
        db,
        ctx,
        policy_id,
        cuerpo.model_dump(mode="python", exclude_unset=True),
        version,
    )
    db.commit()
    return resultado


@router.post("/politicas-pago/{policy_id}/activar")
def post_politica_pago_activar(
    policy_id: str,
    cuerpo: ActivarPoliticaPagoIn,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_pagos", "policy")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> dict[str, Any]:
    version = _version(if_match)
    resultado = service_tesoreria_pago_politicas.activar_politica_pago(
        db,
        ctx,
        policy_id,
        cuerpo.model_dump(mode="python"),
        version,
    )
    db.commit()
    return resultado


@router.post("/politicas-pago/{policy_id}/cerrar")
def post_politica_pago_cerrar(
    policy_id: str,
    cuerpo: CerrarPoliticaPagoIn,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_pagos", "policy")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> dict[str, Any]:
    version = _version(if_match)
    resultado = service_tesoreria_pago_politicas.cerrar_politica_pago(
        db,
        ctx,
        policy_id,
        cuerpo.model_dump(mode="python"),
        version,
    )
    db.commit()
    return resultado


@router.post("/politicas-pago/{policy_id}/nueva-version", status_code=status.HTTP_201_CREATED)
def post_politica_pago_nueva_version(
    policy_id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_pagos", "policy")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
) -> dict[str, Any]:
    resultado = service_tesoreria_pago_politicas.nueva_version_politica_pago(
        db, ctx, policy_id
    )
    db.commit()
    return resultado
