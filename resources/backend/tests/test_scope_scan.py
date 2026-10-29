"""Pruebas del escáner de invariantes de alcance entre filas relacionadas."""

from __future__ import annotations

import secrets
import uuid

import pytest
from sqlalchemy import create_engine, insert
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.core.database import Base, init_models
from app.modules.inventory.models import InventoryLot
from app.modules.master_data.models import CatalogItem, Party
from app.modules.organization.models import Company, Installation, Tenant
from app.modules.purchasing.models import PurchaseOrder, PurchaseOrderLine
from app.modules.setup.api import SetupRequest, initialize
from app.ops.scope_scan import Informe, escanear, main
from tests.conftest import make_engine


@pytest.fixture(scope="module")
def motor() -> Engine:
    """Crea el motor y las tablas una única vez por módulo de pruebas."""
    engine = make_engine()
    init_models()
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture(scope="module")
def mundo(motor: Engine) -> dict[str, str]:
    """Siembra la base con dos tenants, tres empresas y datos base limpios."""
    with Session(motor) as db:
        resultado = initialize(
            db,
            SetupRequest(
                tenant_code="TA",
                tenant_name="Tenant A",
                company_code="A1",
                company_legal_name="A1 CA",
                company_rif="J-10000001-1",
                admin_username="admin_a",
                admin_password="Kx9!" + secrets.token_urlsafe(16),
            ),
        )
        tenant_a = str(resultado["tenant_id"])
        company_a1 = str(resultado["company_id"])
        instalacion = db.query(Installation).first()
        instalacion_id = str(instalacion.id)

        tenant_b = Tenant(
            installation_id=instalacion_id,
            code="TB",
            name="TB",
            plan="MONO_COMPANY",
            status="ACTIVE",
        )
        db.add(tenant_b)
        db.flush()
        tenant_b_id = str(tenant_b.id)

        company_a2 = Company(
            tenant_id=tenant_a,
            code="A2",
            legal_name="A2 CA",
            rif="J-10000002-9",
            legal_type="JURIDICA",
            functional_currency="VED",
            status="ACTIVE",
        )
        company_b1 = Company(
            tenant_id=tenant_b_id,
            code="B1",
            legal_name="B1 CA",
            rif="J-10000003-7",
            legal_type="JURIDICA",
            functional_currency="VED",
            status="ACTIVE",
        )
        db.add_all([company_a2, company_b1])
        db.flush()
        company_a2_id = str(company_a2.id)
        company_b1_id = str(company_b1.id)

        party_a1 = Party(company_id=company_a1, code="P-A1", name="Proveedor A1")
        party_a2 = Party(company_id=company_a2_id, code="P-A2", name="Proveedor A2")
        party_b1 = Party(company_id=company_b1_id, code="P-B1", name="Proveedor B1")
        product_a1 = CatalogItem(
            company_id=company_a1,
            item_type="PRODUCT",
            code="PRD-A1",
            name="Producto A1",
        )
        product_malo_a2 = CatalogItem(
            company_id=company_a2_id,
            item_type="PRODUCT",
            code="PRD-X-A2",
            name="Producto malo A2",
        )
        product_malo_b1 = CatalogItem(
            company_id=company_b1_id,
            item_type="PRODUCT",
            code="PRD-X-B1",
            name="Producto malo B1",
        )
        db.add_all(
            [
                party_a1,
                party_a2,
                party_b1,
                product_a1,
                product_malo_a2,
                product_malo_b1,
            ]
        )
        db.flush()

        orden = PurchaseOrder(company_id=company_a1, supplier_id=party_a1.id, code="PO-A1")
        db.add(orden)
        db.flush()
        db.add(
            PurchaseOrderLine(
                order_id=orden.id,
                product_id=product_a1.id,
                quantity_ordered=1,
                unit_price=1,
            )
        )
        db.commit()

        return {
            "company_a1": company_a1,
            "company_a2": company_a2_id,
            "company_b1": company_b1_id,
            "product_a1": str(product_a1.id),
            "product_a2": str(product_malo_a2.id),
            "product_b1": str(product_malo_b1.id),
            "orden_a1": str(orden.id),
        }


@pytest.fixture()
def conexion(motor: Engine):
    """Transacción con rollback automático para pruebas que siembran basura."""
    conn = motor.connect()
    trans = conn.begin()
    yield conn
    trans.rollback()
    conn.close()


def test_ss01_base_limpia_sin_violaciones(motor: Engine, mundo: dict[str, str]) -> None:
    """SS-01: los datos sembrados no generan violaciones de alcance."""
    with motor.connect() as conn:
        informe = escanear(conn)
    assert isinstance(informe, Informe)
    assert informe.limpio is True
    assert informe.aristas_comprobadas > 0
    assert informe.violaciones == ()


def test_ss02_cross_company_en_linea_de_orden(
    conexion: Connection, mundo: dict[str, str]
) -> None:
    """SS-02: producto de otra empresa del mismo tenant detecta CROSS_COMPANY."""
    fila_id = str(uuid.uuid4())
    conexion.execute(
        insert(PurchaseOrderLine.__table__).values(
            id=fila_id,
            order_id=mundo["orden_a1"],
            product_id=mundo["product_a2"],
            quantity_ordered=1,
            unit_price=1,
        )
    )
    informe = escanear(conexion)
    relevantes = [
        v
        for v in informe.violaciones
        if v.tabla == "purchase_order_lines"
        and v.columna == "product_id"
        and v.padre == "catalog_items"
        and v.clase == "CROSS_COMPANY"
        and v.filas == 1
        and fila_id in v.ejemplos
    ]
    assert len(relevantes) == 1


def test_ss03_cross_tenant_en_linea_de_orden(
    conexion: Connection, mundo: dict[str, str]
) -> None:
    """SS-03: producto de empresa en otro tenant detecta CROSS_TENANT."""
    fila_id = str(uuid.uuid4())
    conexion.execute(
        insert(PurchaseOrderLine.__table__).values(
            id=fila_id,
            order_id=mundo["orden_a1"],
            product_id=mundo["product_b1"],
            quantity_ordered=1,
            unit_price=1,
        )
    )
    informe = escanear(conexion)
    relevantes = [
        v
        for v in informe.violaciones
        if v.tabla == "purchase_order_lines"
        and v.columna == "product_id"
        and v.padre == "catalog_items"
        and v.clase == "CROSS_TENANT"
        and v.filas == 1
        and fila_id in v.ejemplos
    ]
    assert len(relevantes) == 1


def test_ss04_cadena_derivada_lote(
    conexion: Connection, mundo: dict[str, str]
) -> None:
    """SS-04: lote con producto de otro tenant detecta cruce derivado."""
    fila_id = str(uuid.uuid4())
    conexion.execute(
        insert(InventoryLot.__table__).values(
            id=fila_id,
            company_id=mundo["company_a1"],
            product_id=mundo["product_b1"],
            lot_number="L1",
        )
    )
    informe = escanear(conexion)
    relevantes = [
        v
        for v in informe.violaciones
        if v.tabla == "inventory_lots"
        and v.columna == "product_id"
        and v.padre == "catalog_items"
        and v.clase == "CROSS_TENANT"
        and v.filas == 1
        and fila_id in v.ejemplos
    ]
    assert len(relevantes) == 1


def test_ss05_cli_sin_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """SS-05: CLI sin KONTROL_SCAN_DB_URL devuelve código 2."""
    monkeypatch.delenv("KONTROL_SCAN_DB_URL", raising=False)
    assert main([]) == 2


def test_ss06_cli_json_sqlite(tmp_path, monkeypatch) -> None:
    """SS-06: CLI --json contra SQLite en fichero limpio y sucio."""
    url = f"sqlite+pysqlite:///{tmp_path/'s.db'}"
    engine = create_engine(url)
    init_models()
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        resultado = initialize(
            db,
            SetupRequest(
                tenant_code="TA",
                tenant_name="Tenant A",
                company_code="A1",
                company_legal_name="A1 CA",
                company_rif="J-10000001-1",
                admin_username="admin_a",
                admin_password="Kx9!" + secrets.token_urlsafe(16),
            ),
        )
        instalacion = db.query(Installation).first()
        empresa_a1 = str(resultado["company_id"])
        tenant_b = Tenant(
            installation_id=str(instalacion.id),
            code="TB",
            name="TB",
            plan="MONO_COMPANY",
            status="ACTIVE",
        )
        db.add(tenant_b)
        db.flush()
        empresa_b1 = Company(
            tenant_id=str(tenant_b.id),
            code="B1",
            legal_name="B1 CA",
            rif="J-10000003-7",
            legal_type="JURIDICA",
            functional_currency="VED",
            status="ACTIVE",
        )
        db.add(empresa_b1)
        db.flush()
        party = Party(company_id=empresa_a1, code="P-A1", name="Proveedor A1")
        producto_a1 = CatalogItem(
            company_id=empresa_a1,
            item_type="PRODUCT",
            code="PRD-A1",
            name="Producto A1",
        )
        producto_b1 = CatalogItem(
            company_id=str(empresa_b1.id),
            item_type="PRODUCT",
            code="PRD-X-B1",
            name="Producto malo B1",
        )
        db.add_all([party, producto_a1, producto_b1])
        db.flush()
        orden = PurchaseOrder(company_id=empresa_a1, supplier_id=party.id, code="PO-A1")
        db.add(orden)
        db.flush()
        db.add(
            PurchaseOrderLine(
                order_id=orden.id,
                product_id=producto_a1.id,
                quantity_ordered=1,
                unit_price=1,
            )
        )
        db.flush()
        orden_id = str(orden.id)
        producto_b1_id = str(producto_b1.id)
        db.commit()

    monkeypatch.setenv("KONTROL_SCAN_DB_URL", url)
    assert main(["--json"]) == 0

    with engine.connect() as conn:
        trans = conn.begin()
        conn.execute(
            insert(PurchaseOrderLine.__table__).values(
                id=str(uuid.uuid4()),
                order_id=orden_id,
                product_id=producto_b1_id,
                quantity_ordered=1,
                unit_price=1,
            )
        )
        trans.commit()

    assert main(["--json"]) == 1
    engine.dispose()


def test_ss07_solo_lectura_postgres(motor: Engine, mundo: dict[str, str]) -> None:
    """SS-07: tras escanear, la misma transacción rechaza escrituras."""
    if motor.dialect.name != "postgresql":
        pytest.skip("Solo PostgreSQL")
    with motor.connect() as conn:
        escanear(conn)
        with pytest.raises(DBAPIError):
            conn.exec_driver_sql("CREATE TEMPORARY TABLE ss07 (x int)")
