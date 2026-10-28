"""Contrato de `record_audit` con el catálogo cerrado y su correlación.

Cubre la validación previa a la persistencia, la deducción del tenant, la
correlación automática del request_id y la frontera de rechazo.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.logging import request_id_actual
from app.core.middleware import RequestIDMiddleware
from app.modules.audit.models import AuditEvent
from app.modules.organization.models import Company
from app.shared.audit import record_audit, record_audit_after_rollback
from app.shared.audit_catalog import AuditContractError
from tests.conftest import seed_org_chain


def test_rec01_accion_no_catalogada_no_agrega_evento(sesion_de_prueba: Any) -> None:
    with pytest.raises(AuditContractError) as error:
        record_audit(
            sesion_de_prueba,
            action="ACCION_INVENTADA",
            entity_type="Nada",
            tenant_id="t",
        )
    assert error.value.code == "AUDIT_ACTION_UNCATALOGUED"
    assert len(sesion_de_prueba.new) == 0


def test_rec02_document_created_sin_company_id_exige_empresa(sesion_de_prueba: Any) -> None:
    with pytest.raises(AuditContractError) as error:
        record_audit(
            sesion_de_prueba,
            action="DOCUMENT_CREATED",
            entity_type="Document",
            tenant_id="t",
        )
    assert error.value.code == "AUDIT_COMPANY_REQUIRED"


def test_rec03_evento_de_tenant_con_empresa_genera_scope_mismatch(
    sesion_de_prueba: Any,
) -> None:
    seed_org_chain(sesion_de_prueba, "c-rec-03")
    empresa = sesion_de_prueba.get(Company, "c-rec-03")
    with pytest.raises(AuditContractError) as error:
        record_audit(
            sesion_de_prueba,
            action="USER_CREATED",
            entity_type="User",
            tenant_id=empresa.tenant_id,
            company_id=empresa.id,
        )
    assert error.value.code == "AUDIT_SCOPE_MISMATCH"


@pytest.mark.parametrize(
    ("kwargs", "codigo"),
    [
        ({"evidence": {"token": "x"}}, "AUDIT_DETAIL_FORBIDDEN"),
        ({"after": {"password": "x"}}, "AUDIT_DETAIL_FORBIDDEN"),
        ({"after": {"otro": 1}}, "AUDIT_DETAIL_KEY_NOT_ALLOWED"),
    ],
)
def test_rec04_detalle_prohibido_o_no_permitido(
    sesion_de_prueba: Any, kwargs: dict[str, Any], codigo: str
) -> None:
    with pytest.raises(AuditContractError) as error:
        record_audit(
            sesion_de_prueba,
            action="USER_CREATED",
            entity_type="User",
            tenant_id="t",
            **kwargs,
        )
    assert error.value.code == codigo


def test_rec05_evento_valido_de_tenant_sin_empresa(sesion_de_prueba: Any) -> None:
    seed_org_chain(sesion_de_prueba, "c-rec-05")
    empresa = sesion_de_prueba.get(Company, "c-rec-05")
    evento = record_audit(
        sesion_de_prueba,
        action="USER_CREATED",
        entity_type="User",
        tenant_id=empresa.tenant_id,
        after={"username": "u"},
    )
    sesion_de_prueba.commit()
    fila = sesion_de_prueba.get(AuditEvent, evento.id)
    assert fila is not None
    assert fila.company_id is None


def test_rec06_evento_valido_de_empresa_deduce_tenant(sesion_de_prueba: Any) -> None:
    seed_org_chain(sesion_de_prueba, "c-rec-06")
    empresa = sesion_de_prueba.get(Company, "c-rec-06")
    evento = record_audit(
        sesion_de_prueba,
        action="DOCUMENT_CREATED",
        entity_type="Document",
        entity_id="d1",
        company_id="c-rec-06",
        after={"title": "t"},
    )
    sesion_de_prueba.commit()
    fila = sesion_de_prueba.get(AuditEvent, evento.id)
    assert fila is not None
    assert fila.tenant_id == empresa.tenant_id


def test_rec07_correlacion_por_contextvar(sesion_de_prueba: Any) -> None:
    seed_org_chain(sesion_de_prueba, "c-rec-07")
    empresa = sesion_de_prueba.get(Company, "c-rec-07")

    token = request_id_actual.set("rid-ctx")
    try:
        evento_ctx = record_audit(
            sesion_de_prueba,
            action="USER_CREATED",
            entity_type="User",
            tenant_id=empresa.tenant_id,
        )
        evento_explicito = record_audit(
            sesion_de_prueba,
            action="USER_CREATED",
            entity_type="User",
            tenant_id=empresa.tenant_id,
            request_id="rid-explicito",
        )
    finally:
        request_id_actual.reset(token)

    assert evento_ctx.request_id == "rid-ctx"
    assert evento_explicito.request_id == "rid-explicito"


def test_rec08_correlacion_por_http(sesion_de_prueba: Any) -> None:
    app = FastAPI()
    app.add_middleware(RequestIDMiddleware)

    @app.get("/rid")
    def ruta() -> dict[str, str | None]:
        return {"rid": request_id_actual.get()}

    client = TestClient(app)
    respuesta = client.get("/rid")
    assert respuesta.status_code == 200
    rid = respuesta.json()["rid"]
    assert rid
    assert rid == respuesta.headers["X-Request-ID"]
    assert request_id_actual.get() is None


def test_rec09_frontera_de_rechazo_sobrevive_al_rollback(
    sesion_de_prueba: Any,
) -> None:
    seed_org_chain(sesion_de_prueba, "c-rec-09")
    sesion_de_prueba.commit()

    # Empresa pendiente sin confirmar: debe desaparecer con el rollback.
    seed_org_chain(sesion_de_prueba, "c-rec-09b")

    record_audit_after_rollback(
        sesion_de_prueba,
        action="DOCUMENT_CREATED",
        entity_type="Document",
        entity_id="d9",
        company_id="c-rec-09",
        after={"title": "t"},
    )

    assert sesion_de_prueba.get(Company, "c-rec-09b") is None
    evento = (
        sesion_de_prueba.execute(select(AuditEvent).where(AuditEvent.entity_id == "d9"))
        .scalars()
        .one_or_none()
    )
    assert evento is not None
