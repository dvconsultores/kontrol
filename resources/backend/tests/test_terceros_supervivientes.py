from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from conftest import seed_org_chain
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.errors import ConflictError
from app.modules.master_data.api import list_parties
from app.modules.master_data.models import Party
from app.modules.purchasing import service as ap_service
from app.modules.regulatory import service as regulatory_service
from app.modules.sales import service as sales_service
from tests.company_seed import EMPRESA_DOS, EMPRESA_UNO

COMPANY = EMPRESA_UNO
OTHER = EMPRESA_DOS


@pytest.fixture()
def db_session(sesion_de_prueba):
    seed_org_chain(sesion_de_prueba, COMPANY, OTHER)
    return sesion_de_prueba


def _tercero(db: Session, *, code: str, roles: list[str], status: str = "ACTIVE") -> Party:
    party = Party(company_id=COMPANY, code=code, name=f"Tercero {code}", person_type="JURIDICA",
                  tax_id=f"J-{uuid.uuid4().hex[:10]}", roles=roles, status=status)
    db.add(party)
    db.flush()
    return party


def test_k01_rol_cliente_minusculas_es_valido(db_session: Session) -> None:
    cliente = _tercero(db_session, code="K1-CLI", roles=["cliente"])
    resultado = sales_service.create_quote(
        db_session, company_id=COMPANY, code="Q-K1", customer_id=cliente.id
    )
    assert resultado is not None


def test_k02_filtro_api_role_case_insensitive(db_session: Session) -> None:
    case_sensitive_like_on = db_session.get_bind().dialect.name == "sqlite"
    if case_sensitive_like_on:
        db_session.execute(text("PRAGMA case_sensitive_like = ON"))
    try:
        cliente = _tercero(db_session, code="K2-CLI", roles=["cliente"])
        proveedor = _tercero(db_session, code="K2-PRO", roles=["PROVEEDOR"])
        for rol in ("CLIENTE", "cliente"):
            respuesta = list_parties(
                q="",
                status=None,
                role=rol,
                page=1,
                page_size=100,
                db=db_session,
                user=None,
                ctx=SimpleNamespace(company_id=COMPANY),
            )
            ids = {i["id"] for i in respuesta["items"]}
            assert cliente.id in ids
            assert proveedor.id not in ids
    finally:
        if case_sensitive_like_on:
            db_session.execute(text("PRAGMA case_sensitive_like = OFF"))


def test_k03_nota_debito_cliente_inactivo(db_session: Session) -> None:
    cliente = _tercero(db_session, code="K3-CLI", roles=["cliente"], status="INACTIVE")
    resultado = sales_service.create_debit_note(
        db_session, company_id=COMPANY, customer_id=cliente.id, number="ND-K3", amount=10.0
    )
    assert resultado is not None


def test_k04_nota_credito_proveedor_inactivo(db_session: Session) -> None:
    proveedor = _tercero(db_session, code="K4-PRO", roles=["PROVEEDOR"], status="INACTIVE")
    resultado = ap_service.create_credit_note(
        db_session, company_id=COMPANY, supplier_id=proveedor.id, number="NC-K4", amount=10.0
    )
    assert resultado is not None


def test_k05_retencion_proveedor_inactivo(db_session: Session) -> None:
    proveedor = _tercero(db_session, code="K5-PRO", roles=["PROVEEDOR"], status="INACTIVE")
    resultado = ap_service.create_withholding(
        db_session,
        company_id=COMPANY,
        party_id=proveedor.id,
        tax_type="IVA",
        rule_ref=None,
        base=100.0,
        rate_ref=None,
        amount=7.5,
        party_role="PROVEEDOR",
    )
    assert resultado is not None


def test_k06_vehiculo_owner_inactivo_lanza_conflict(db_session: Session) -> None:
    propietario = _tercero(db_session, code="K6-PRO", roles=["PROVEEDOR"], status="INACTIVE")
    with pytest.raises(ConflictError) as excinfo:
        regulatory_service.create_vehicle(
            db_session, company_id=COMPANY, plate="KKK-006", owner_party_id=propietario.id
        )
    assert excinfo.value.code == "PARTY_INACTIVE"
