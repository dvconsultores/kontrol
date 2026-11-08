"""Pruebas de elegibilidad de terceros por rol y estado (TER-C).

Reproducen en rojo que ventas, compras y regulatorio aceptan terceros con rol o
estado no elegibles, y que GET /maestros/terceros no filtra por rol.
"""

from __future__ import annotations

import datetime
import uuid

import pytest
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.modules.master_data.models import Party, Supplier
from app.modules.purchasing import service as ap_service
from app.modules.regulatory import service as regulatory_service
from app.modules.sales import service as sales_service
from app.modules.sales.models import SalesQuote
from tests.company_seed import EMPRESA_DOS, EMPRESA_UNO

pytest_plugins = ("mfa_apoyo",)

COMPANY = EMPRESA_UNO
OTHER = EMPRESA_DOS

NON_EXISTENT_PARTY_ID = "00000000-0000-4000-8000-000000000999"


@pytest.fixture()
def db_session(sesion_de_prueba):
    from conftest import seed_org_chain

    seed_org_chain(sesion_de_prueba, COMPANY, OTHER)
    return sesion_de_prueba


def _tercero(
    db: Session,
    *,
    company: str = COMPANY,
    code: str,
    roles: list[str],
    status: str = "ACTIVE",
) -> Party:
    party = Party(
        company_id=company,
        code=code,
        name=f"Tercero {code}",
        person_type="JURIDICA",
        tax_id=f"J-{uuid.uuid4().hex[:10]}",
        roles=roles,
        status=status,
    )
    db.add(party)
    db.flush()
    if "PROVEEDOR" in roles:
        db.add(Supplier(party_id=str(party.id), approval_status="APPROVED"))
        db.flush()
    return party


@pytest.mark.parametrize(
    "func_name",
    ["create_quote", "create_order", "create_invoice"],
)
def test_venta_cliente_valido(db_session: Session, func_name: str):
    customer = _tercero(db_session, code="CLI-VENTA", roles=["CLIENTE"])
    func = getattr(sales_service, func_name)
    params = {"db": db_session, "company_id": COMPANY, "customer_id": customer.id}
    if func_name == "create_quote":
        params.update(code="Q-1")
    elif func_name == "create_order":
        params.update(code="O-1")
    result = func(**params)
    assert result is not None


@pytest.mark.parametrize(
    "func_name,kwargs",
    [
        ("create_quote", {"code": "Q-1"}),
        ("create_order", {"code": "O-1"}),
        ("create_invoice", {}),
        ("create_credit_note", {"number": "NC-1", "amount": 10.0}),
        ("create_debit_note", {"number": "ND-1", "amount": 10.0}),
    ],
)
def test_venta_rechaza_cliente_con_rol_proveedor_solo(
    db_session: Session, func_name: str, kwargs: dict
):
    supplier_only = _tercero(db_session, code="PROV-VENTA", roles=["PROVEEDOR"])
    func = getattr(sales_service, func_name)
    params = {
        "db": db_session,
        "company_id": COMPANY,
        "customer_id": supplier_only.id,
        **kwargs,
    }
    with pytest.raises(ConflictError) as excinfo:
        func(**params)
    assert excinfo.value.code == "PARTY_ROLE_REQUIRED"


@pytest.mark.parametrize(
    "func_name",
    ["create_quote", "create_order", "create_invoice"],
)
def test_venta_multirol_cliente_valido(db_session: Session, func_name: str):
    customer = _tercero(
        db_session, code="MULTI-VENTA", roles=["CLIENTE", "PROVEEDOR"]
    )
    func = getattr(sales_service, func_name)
    params = {"db": db_session, "company_id": COMPANY, "customer_id": customer.id}
    if func_name == "create_quote":
        params.update(code="Q-1")
    elif func_name == "create_order":
        params.update(code="O-1")
    result = func(**params)
    assert result is not None


@pytest.mark.parametrize(
    "func_name",
    ["create_quote", "create_order", "create_invoice"],
)
def test_compra_proveedor_valido(db_session: Session, func_name: str):
    supplier = _tercero(db_session, code="PROV-COMPRA", roles=["PROVEEDOR"])
    func = getattr(ap_service, func_name)
    params = {"db": db_session, "company_id": COMPANY, "supplier_id": supplier.id}
    if func_name == "create_quote":
        params.update(code="Q-1")
    elif func_name == "create_order":
        params.update(code="O-1")
    elif func_name == "create_invoice":
        params.update(invoice_number="F-1")
    result = func(**params)
    assert result is not None


@pytest.mark.parametrize(
    "func_name,kwargs",
    [
        ("create_quote", {"code": "Q-1"}),
        ("create_order", {"code": "O-1"}),
        ("create_invoice", {"invoice_number": "F-1"}),
        ("create_credit_note", {"number": "NC-1", "amount": 10.0}),
    ],
)
def test_compra_rechaza_supplier_con_rol_cliente_solo(
    db_session: Session, func_name: str, kwargs: dict
):
    client_only = _tercero(db_session, code="CLI-COMPRA", roles=["CLIENTE"])
    func = getattr(ap_service, func_name)
    params = {
        "db": db_session,
        "company_id": COMPANY,
        "supplier_id": client_only.id,
        **kwargs,
    }
    with pytest.raises(ConflictError) as excinfo:
        func(**params)
    assert excinfo.value.code == "PARTY_ROLE_REQUIRED"


def test_compra_rechaza_schedule_con_cliente_solo(db_session: Session):
    client_only = _tercero(db_session, code="CLI-COMPRA-SCH", roles=["CLIENTE"])
    with pytest.raises(ConflictError) as excinfo:
        ap_service.create_schedule(
            db=db_session,
            company_id=COMPANY,
            party_id=client_only.id,
            due_date=datetime.date(2026, 12, 31),
            amount=10.0,
        )
    assert excinfo.value.code == "PARTY_ROLE_REQUIRED"


@pytest.mark.parametrize(
    "func_name",
    ["create_quote", "create_order", "create_invoice"],
)
def test_compra_multirol_proveedor_valido(db_session: Session, func_name: str):
    supplier = _tercero(
        db_session, code="MULTI-COMPRA", roles=["CLIENTE", "PROVEEDOR"]
    )
    func = getattr(ap_service, func_name)
    params = {"db": db_session, "company_id": COMPANY, "supplier_id": supplier.id}
    if func_name == "create_quote":
        params.update(code="Q-1")
    elif func_name == "create_order":
        params.update(code="O-1")
    elif func_name == "create_invoice":
        params.update(invoice_number="F-1")
    result = func(**params)
    assert result is not None


@pytest.mark.parametrize(
    "module,func_name,customer_or_supplier",
    [
        ("sales", "create_quote", "customer_id"),
        ("purchasing", "create_quote", "supplier_id"),
    ],
)
def test_tercero_otra_empresa_rechazado(
    db_session: Session, module: str, func_name: str, customer_or_supplier: str
):
    other_party = _tercero(
        db_session, company=OTHER, code="OTHER-EMP", roles=["CLIENTE", "PROVEEDOR"]
    )
    service = sales_service if module == "sales" else ap_service
    func = getattr(service, func_name)
    params = {
        "db": db_session,
        "company_id": COMPANY,
        customer_or_supplier: other_party.id,
        "code": "Q-1",
    }
    with pytest.raises(NotFoundError) as excinfo:
        func(**params)
    assert excinfo.value.code == "PARTY_NOT_FOUND"


@pytest.mark.parametrize(
    "module,func_name,customer_or_supplier",
    [
        ("sales", "create_quote", "customer_id"),
        ("purchasing", "create_quote", "supplier_id"),
    ],
)
def test_tercero_inexistente_rechazado(
    db_session: Session, module: str, func_name: str, customer_or_supplier: str
):
    service = sales_service if module == "sales" else ap_service
    func = getattr(service, func_name)
    params = {
        "db": db_session,
        "company_id": COMPANY,
        customer_or_supplier: NON_EXISTENT_PARTY_ID,
        "code": "Q-1",
    }
    with pytest.raises(NotFoundError) as excinfo:
        func(**params)
    assert excinfo.value.code == "PARTY_NOT_FOUND"


def test_no_revela_existencia_de_tercero_ajeno_o_inexistente(db_session: Session):
    other_party = _tercero(
        db_session, company=OTHER, code="AJENO-BR09", roles=["CLIENTE"]
    )

    parametros = [
        (sales_service, "create_quote", "customer_id"),
        (ap_service, "create_quote", "supplier_id"),
    ]

    resultados_ajeno = []
    resultados_inexistente = []

    for service, func_name, party_key in parametros:
        func = getattr(service, func_name)

        with pytest.raises(NotFoundError) as excinfo_ajeno:
            func(
                db=db_session,
                company_id=COMPANY,
                code="Q-BR09-A",
                **{party_key: other_party.id},
            )
        resultados_ajeno.append((excinfo_ajeno.value.code, str(excinfo_ajeno.value)))

        with pytest.raises(NotFoundError) as excinfo_inexistente:
            func(
                db=db_session,
                company_id=COMPANY,
                code="Q-BR09-I",
                **{party_key: NON_EXISTENT_PARTY_ID},
            )
        resultados_inexistente.append(
            (excinfo_inexistente.value.code, str(excinfo_inexistente.value))
        )

    assert resultados_ajeno == resultados_inexistente


def test_pagos_direccion_out_exige_proveedor(db_session: Session):
    client_only = _tercero(db_session, code="CLI-PAGO", roles=["CLIENTE"])
    with pytest.raises(ConflictError) as excinfo:
        ap_service.register_payment(
            db=db_session,
            company_id=COMPANY,
            party_id=client_only.id,
            amount=10.0,
            direction="OUT",
        )
    assert excinfo.value.code == "PARTY_ROLE_REQUIRED"

    supplier_only = _tercero(db_session, code="PROV-PAGO", roles=["PROVEEDOR"])
    result = ap_service.register_payment(
        db=db_session,
        company_id=COMPANY,
        party_id=supplier_only.id,
        amount=10.0,
        direction="OUT",
    )
    assert result is not None


def test_pagos_direccion_in_exige_cliente(db_session: Session):
    supplier_only = _tercero(db_session, code="PROV-PAGO-IN", roles=["PROVEEDOR"])
    with pytest.raises(ConflictError) as excinfo:
        ap_service.register_payment(
            db=db_session,
            company_id=COMPANY,
            party_id=supplier_only.id,
            amount=10.0,
            direction="IN",
        )
    assert excinfo.value.code == "PARTY_ROLE_REQUIRED"

    client_only = _tercero(db_session, code="CLI-PAGO-IN", roles=["CLIENTE"])
    result = ap_service.register_payment(
        db=db_session,
        company_id=COMPANY,
        party_id=client_only.id,
        amount=10.0,
        direction="IN",
    )
    assert result is not None


def test_anticipos_direccion_out_exige_proveedor_activo(db_session: Session):
    client_only = _tercero(db_session, code="CLI-ANTICIPO", roles=["CLIENTE"])
    with pytest.raises(ConflictError) as excinfo:
        ap_service.register_advance(
            db=db_session,
            company_id=COMPANY,
            party_id=client_only.id,
            amount=10.0,
            direction="OUT",
        )
    assert excinfo.value.code == "PARTY_ROLE_REQUIRED"

    supplier_only = _tercero(db_session, code="PROV-ANTICIPO", roles=["PROVEEDOR"])
    result = ap_service.register_advance(
        db=db_session,
        company_id=COMPANY,
        party_id=supplier_only.id,
        amount=10.0,
        direction="OUT",
    )
    assert result is not None


def test_anticipos_direccion_in_exige_cliente_activo(db_session: Session):
    supplier_only = _tercero(db_session, code="PROV-ANTICIPO-IN", roles=["PROVEEDOR"])
    with pytest.raises(ConflictError) as excinfo:
        ap_service.register_advance(
            db=db_session,
            company_id=COMPANY,
            party_id=supplier_only.id,
            amount=10.0,
            direction="IN",
        )
    assert excinfo.value.code == "PARTY_ROLE_REQUIRED"

    client_only = _tercero(db_session, code="CLI-ANTICIPO-IN", roles=["CLIENTE"])
    result = ap_service.register_advance(
        db=db_session,
        company_id=COMPANY,
        party_id=client_only.id,
        amount=10.0,
        direction="IN",
    )
    assert result is not None


def test_retencion_exige_rol_declarado(db_session: Session):
    client_only = _tercero(db_session, code="CLI-RETENCION", roles=["CLIENTE"])
    with pytest.raises(ConflictError) as excinfo:
        ap_service.create_withholding(
            db=db_session,
            company_id=COMPANY,
            party_id=client_only.id,
            tax_type="IVA",
            rule_ref=None,
            base=100.0,
            rate_ref=None,
            amount=7.5,
            party_role="PROVEEDOR",
        )
    assert excinfo.value.code == "PARTY_ROLE_REQUIRED"

    supplier_only = _tercero(db_session, code="PROV-RETENCION", roles=["PROVEEDOR"])
    result = ap_service.create_withholding(
        db=db_session,
        company_id=COMPANY,
        party_id=supplier_only.id,
        tax_type="IVA",
        rule_ref=None,
        base=100.0,
        rate_ref=None,
        amount=7.5,
        party_role="PROVEEDOR",
    )
    assert result is not None

    result = ap_service.create_withholding(
        db=db_session,
        company_id=COMPANY,
        party_id=client_only.id,
        tax_type="IVA",
        rule_ref=None,
        base=100.0,
        rate_ref=None,
        amount=7.5,
        party_role="CLIENTE",
    )
    assert result is not None


@pytest.mark.parametrize(
    "func_name",
    ["create_quote", "create_order", "create_invoice"],
)
def test_venta_rechaza_cliente_inactivo(db_session: Session, func_name: str):
    inactive = _tercero(
        db_session, code="CLI-INACTIVO", roles=["CLIENTE"], status="INACTIVE"
    )
    func = getattr(sales_service, func_name)
    params = {
        "db": db_session,
        "company_id": COMPANY,
        "customer_id": inactive.id,
    }
    if func_name == "create_quote":
        params.update(code="Q-1")
    elif func_name == "create_order":
        params.update(code="O-1")
    with pytest.raises(ConflictError) as excinfo:
        func(**params)
    assert excinfo.value.code == "PARTY_INACTIVE"


@pytest.mark.parametrize(
    "func_name",
    ["create_quote", "create_order", "create_invoice"],
)
def test_compra_rechaza_proveedor_inactivo(db_session: Session, func_name: str):
    inactive = _tercero(
        db_session, code="PROV-INACTIVO", roles=["PROVEEDOR"], status="INACTIVE"
    )
    func = getattr(ap_service, func_name)
    params = {
        "db": db_session,
        "company_id": COMPANY,
        "supplier_id": inactive.id,
    }
    if func_name == "create_quote":
        params.update(code="Q-1")
    elif func_name == "create_order":
        params.update(code="O-1")
    elif func_name == "create_invoice":
        params.update(invoice_number="F-1")
    with pytest.raises(ConflictError) as excinfo:
        func(**params)
    assert excinfo.value.code == "PARTY_INACTIVE"


def test_anticipo_rechaza_proveedor_inactivo(db_session: Session):
    inactive = _tercero(
        db_session, code="PROV-INACTIVO-ANT", roles=["PROVEEDOR"], status="INACTIVE"
    )
    with pytest.raises(ConflictError) as excinfo:
        ap_service.register_advance(
            db=db_session,
            company_id=COMPANY,
            party_id=inactive.id,
            amount=10.0,
            direction="OUT",
        )
    assert excinfo.value.code == "PARTY_INACTIVE"


def test_liquidaciones_permiten_tercero_inactivo(db_session: Session):
    inactive_supplier = _tercero(
        db_session, code="PROV-INACTIVO-LIQ", roles=["PROVEEDOR"], status="INACTIVE"
    )
    result = ap_service.register_payment(
        db=db_session,
        company_id=COMPANY,
        party_id=inactive_supplier.id,
        amount=10.0,
        direction="OUT",
    )
    assert result is not None

    inactive_customer = _tercero(
        db_session, code="CLI-INACTIVO-LIQ", roles=["CLIENTE"], status="INACTIVE"
    )
    result = sales_service.create_credit_note(
        db=db_session,
        company_id=COMPANY,
        customer_id=inactive_customer.id,
        number="NC-1",
        amount=10.0,
    )
    assert result is not None

    result = ap_service.create_schedule(
        db=db_session,
        company_id=COMPANY,
        party_id=inactive_supplier.id,
        due_date=datetime.date(2026, 12, 31),
        amount=10.0,
    )
    assert result is not None


def test_historia_persiste_al_inactivar_cliente(db_session: Session):
    active = _tercero(db_session, code="CLI-HISTORIA", roles=["CLIENTE"])
    quote = sales_service.create_quote(
        db=db_session,
        company_id=COMPANY,
        code="Q-HIST-1",
        customer_id=active.id,
    )
    quote_status = quote.status

    active.status = "INACTIVE"
    db_session.flush()

    persisted = db_session.get(SalesQuote, quote.id)
    assert persisted is not None
    assert persisted.customer_id == active.id
    assert persisted.status == quote_status


def test_regulatorio_rechaza_conductor_otra_empresa(db_session: Session):
    other_party = _tercero(
        db_session, company=OTHER, code="DRIVER-OTHER", roles=["CLIENTE"]
    )
    with pytest.raises(NotFoundError) as excinfo:
        regulatory_service.create_driver(
            db=db_session,
            company_id=COMPANY,
            party_id=other_party.id,
        )
    assert excinfo.value.code == "PARTY_NOT_FOUND"

    with pytest.raises(NotFoundError) as excinfo:
        regulatory_service.create_driver(
            db=db_session,
            company_id=COMPANY,
            party_id=NON_EXISTENT_PARTY_ID,
        )
    assert excinfo.value.code == "PARTY_NOT_FOUND"


def test_regulatorio_rechaza_conductor_inactivo(db_session: Session):
    inactive = _tercero(
        db_session, code="DRIVER-INACTIVO", roles=["CLIENTE"], status="INACTIVE"
    )
    with pytest.raises(ConflictError) as excinfo:
        regulatory_service.create_driver(
            db=db_session,
            company_id=COMPANY,
            party_id=inactive.id,
        )
    assert excinfo.value.code == "PARTY_INACTIVE"


def test_regulatorio_acepta_conductor_activo_sin_roles(db_session: Session):
    no_roles = _tercero(db_session, code="DRIVER-NO-ROLES", roles=[])
    result = regulatory_service.create_driver(
        db=db_session,
        company_id=COMPANY,
        party_id=no_roles.id,
    )
    assert result is not None


def test_regulatorio_vehiculo_rechaza_owner_otra_empresa(db_session: Session):
    other_owner = _tercero(
        db_session, company=OTHER, code="OWNER-OTHER", roles=["CLIENTE"]
    )
    with pytest.raises(NotFoundError) as excinfo:
        regulatory_service.create_vehicle(
            db=db_session,
            company_id=COMPANY,
            plate="ABC-123",
            owner_party_id=other_owner.id,
        )
    assert excinfo.value.code == "PARTY_NOT_FOUND"


def test_regulatorio_vehiculo_sin_owner(db_session: Session):
    result = regulatory_service.create_vehicle(
        db=db_session,
        company_id=COMPANY,
        plate="ABC-123",
    )
    assert result is not None


@pytest.fixture(scope="module")
def mundo():
    from mfa_mundo import mundo_mfa

    with mundo_mfa() as m:
        yield m


@pytest.fixture(scope="module")
def rol_operador(mundo):
    import uuid as uuid_mod

    from app.modules.identity_access import service as identity_service

    db = mundo.factory()
    try:
        rol = identity_service.create_role(
            db,
            tenant_id=mundo.tenant_id,
            code=f"terc{uuid_mod.uuid4().hex[:12]}",
            name="Terceros Elegibilidad",
            company_id=None,
            permissions=[
                "maestros:view",
                "maestros:create",
            ],
            actor=mundo.admin_id,
        )
        db.commit()
        return rol["id"]
    finally:
        db.close()


def _dar(mundo, user_id, role_id, company_id):
    from app.modules.identity_access.models import UserRole

    db = mundo.factory()
    try:
        db.add(UserRole(user_id=user_id, role_id=role_id, company_id=company_id))
        db.commit()
    finally:
        db.close()


def _entrar(mundo, reloj, nombre):
    from mfa_mundo import alta_por_desafio, login

    r = login(mundo.client, nombre)
    assert r.status_code == 200, r.text
    if r.json().get("status") == "AUTHENTICATED":
        return {"Authorization": f"Bearer {r.json()['access_token']}"}
    return alta_por_desafio(mundo.client, reloj, nombre).cabeceras


def _operador(mundo, reloj, rol):
    from mfa_mundo import crear_usuario

    nombre = f"terc{uuid.uuid4().hex[:12]}"
    user_id = crear_usuario(mundo, nombre)
    _dar(mundo, user_id, rol, mundo.company_id)
    cabeceras = _entrar(mundo, reloj, nombre)
    cabeceras["X-Kontrol-Company"] = str(mundo.company_id)
    return cabeceras


def _api_tercero(mundo, cabeceras, code, roles):
    return mundo.client.post(
        "/api/v1/maestros/terceros",
        headers=cabeceras,
        json={
            "code": code,
            "name": f"Tercero {code}",
            "roles": roles,
        },
    )


def _api_items(mundo, cabeceras, role=None):
    url = "/api/v1/maestros/terceros?page_size=100"
    if role is not None:
        url += f"&role={role}"
    response = mundo.client.get(
        url,
        headers=cabeceras,
    )
    assert response.status_code == 200
    payload = response.json()
    return payload.get("items", payload if isinstance(payload, list) else [])


def test_api_filtra_por_role_sin_distinguir_mayusculas(mundo, reloj_mfa, rol_operador):
    cabeceras = _operador(mundo, reloj_mfa, rol_operador)
    marca = uuid.uuid4().hex[:8]

    cliente = _api_tercero(
        mundo, cabeceras, f"T-RF-CLI-{marca}", ["CLIENTE"]
    )
    proveedor = _api_tercero(
        mundo, cabeceras, f"T-RF-PROV-{marca}", ["PROVEEDOR"]
    )
    multirol = _api_tercero(
        mundo, cabeceras, f"T-RF-MULTI-{marca}", ["CLIENTE", "PROVEEDOR"]
    )
    assert cliente.status_code == proveedor.status_code == multirol.status_code == 200

    cliente_id = cliente.json()["id"]
    proveedor_id = proveedor.json()["id"]
    multirol_id = multirol.json()["id"]

    items_cliente = _api_items(mundo, cabeceras, role="CLIENTE")
    ids_cliente = {item["id"] for item in items_cliente}
    assert cliente_id in ids_cliente
    assert multirol_id in ids_cliente
    assert proveedor_id not in ids_cliente

    items_proveedor = _api_items(mundo, cabeceras, role="PROVEEDOR")
    ids_proveedor = {item["id"] for item in items_proveedor}
    assert proveedor_id in ids_proveedor
    assert multirol_id in ids_proveedor
    assert cliente_id not in ids_proveedor

    items_lower = _api_items(mundo, cabeceras, role="cliente")
    ids_lower = {item["id"] for item in items_lower}
    assert ids_lower == ids_cliente

    items_sin_role = _api_items(mundo, cabeceras)
    ids_sin_role = {item["id"] for item in items_sin_role}
    assert cliente_id in ids_sin_role
    assert proveedor_id in ids_sin_role
    assert multirol_id in ids_sin_role


def test_api_role_invalido_retorna_422(mundo, reloj_mfa, rol_operador):
    cabeceras = _operador(mundo, reloj_mfa, rol_operador)
    response = mundo.client.get(
        "/api/v1/maestros/terceros?role=CLI%25",
        headers=cabeceras,
    )
    assert response.status_code == 422
