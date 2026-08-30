"""Unidades, presentaciones y conversiones (Spec 011).

Cubre lo que la Spec declara no negociable: que una transacción histórica no
dependa de la configuración vigente, que el factor se congele al emitir, que la
unidad base no cambie con historial y que ninguna cantidad use coma flotante.

Sobre PostgreSQL cuando `KONTROL_TEST_DB_URL` lo indica (P21).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base, get_db, init_models
from app.modules.master_data import uom
from app.modules.master_data.models import (
    CatalogItem,
    ProductPresentationVersion,
    UnitOfMeasure,
)
from app.modules.setup.api import SetupRequest, initialize
from tests.conftest import make_engine

_CLIENT: TestClient
_FACTORY: sessionmaker


@pytest.fixture(scope="module", autouse=True)
def _app_client():
    global _CLIENT, _FACTORY
    engine = make_engine()
    init_models()
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    import app.core.database as dm

    dm._engine = engine  # type: ignore[attr-defined]
    dm._SessionLocal = factory  # type: ignore[attr-defined]

    db = factory()
    initialize(db, SetupRequest(
        tenant_code="DEMO", tenant_name="Empresa Demo", company_code="D1",
        company_legal_name="Demo C.A.", company_rif="J-12345678-9",
        admin_username="admin", admin_password="Kontrol2026Segura!"))
    db.close()

    from app.main import create_app

    app = create_app()

    def _override_get_db():
        d = factory()
        try:
            yield d
        finally:
            d.close()

    app.dependency_overrides[get_db] = _override_get_db
    _FACTORY = factory
    _CLIENT = TestClient(app)
    yield _CLIENT


def _headers() -> dict:
    r = _CLIENT.post("/api/v1/auth/login", json={
        "tenant_code": "DEMO", "username": "admin", "password": "Kontrol2026Segura!"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _tenant_id() -> str:
    db = _FACTORY()
    try:
        from app.modules.organization.models import Tenant

        return str(db.execute(select(Tenant).where(Tenant.code == "DEMO")).scalars().first().id)
    finally:
        db.close()


_SEQ = {"n": 0}


def _unit(code: str, *, dimension: str = "CANTIDAD", decimals: int = 0,
          rounding: str = "HALF_UP") -> dict:
    r = _CLIENT.post("/api/v1/maestros/unidades", headers=_headers(), json={
        "code": code, "name": f"Unidad {code}", "symbol": code.lower(),
        "dimension": dimension, "decimals": decimals, "rounding_mode": rounding})
    assert r.status_code == 200, r.text
    return r.json()


def _product(code: str, base_unit_id: str | None, item_type: str = "PRODUCT") -> str:
    """Crea el item directamente: 011 no implementa el alta de producto."""
    db = _FACTORY()
    try:
        item = CatalogItem(company_id=_tenant_id(), code=code, name=f"Producto {code}",
                           item_type=item_type, status="ACTIVE", base_unit_id=base_unit_id)
        db.add(item)
        db.commit()
        return str(item.id)
    finally:
        db.close()


def _presentation(product_id: str, code: str, factor: str | None,
                  *, exact: bool = True, valid_from: datetime | None = None) -> dict:
    body: dict = {"code": code, "name": f"{code.title()}", "exact_in_base": exact}
    if factor is not None:
        body["factor_to_base"] = factor
    if valid_from:
        body["valid_from"] = valid_from.isoformat()
    r = _CLIENT.post(f"/api/v1/maestros/productos/{product_id}/presentaciones",
                     headers=_headers(), json=body)
    assert r.status_code == 200, r.text
    return r.json()


# ---------------------------------------------------------------- AC-011-01
def test_catalogo_global_nace_vacio():
    """KONTROL no entrega `UND`, `KG` ni ninguna otra unidad (P8)."""
    db = _FACTORY()
    try:
        globals_ = db.execute(select(UnitOfMeasure).where(
            UnitOfMeasure.company_id.is_(None))).scalars().all()
    finally:
        db.close()
    assert globals_ == []


# ---------------------------------------------------------------- AC-011-02
def test_unidad_global_es_de_solo_lectura():
    db = _FACTORY()
    try:
        global_unit = UnitOfMeasure(company_id=None, code="GLB", name="Global",
                                    symbol="glb", dimension="CANTIDAD", decimals=0,
                                    status="ACTIVE")
        db.add(global_unit)
        db.commit()
        global_id = str(global_unit.id)
    finally:
        db.close()

    h = _headers()
    listed = _CLIENT.get("/api/v1/maestros/unidades", headers=h).json()
    assert any(u["id"] == global_id and u["scope"] == "GLOBAL" for u in listed["items"])

    blocked = _CLIENT.patch(f"/api/v1/maestros/unidades/{global_id}", headers=h,
                            json={"name": "Intruso"})
    assert blocked.status_code == 403
    assert blocked.json()["code"] == "UOM_GLOBAL_READ_ONLY"

    # Una unidad de empresa puede repetir el código de una global.
    same = _CLIENT.post("/api/v1/maestros/unidades", headers=h, json={
        "code": "GLB", "name": "Propia", "symbol": "glb", "dimension": "CANTIDAD"})
    assert same.status_code == 200, same.text
    assert same.json()["scope"] == "COMPANY"


# ---------------------------------------------------------------- AC-011-03
def test_conversion_fisica_solo_dentro_de_la_dimension():
    h = _headers()
    kg = _unit("KG3", dimension="PESO", decimals=3)
    g = _unit("G3", dimension="PESO", decimals=0)
    litro = _unit("L3", dimension="VOLUMEN", decimals=3)

    ok = _CLIENT.post(f"/api/v1/maestros/unidades/{kg['id']}/conversiones-fisicas",
                      headers=h, json={"to_unit_id": g["id"], "factor": "1000"})
    assert ok.status_code == 200, ok.text

    bad = _CLIENT.post(f"/api/v1/maestros/unidades/{kg['id']}/conversiones-fisicas",
                       headers=h, json={"to_unit_id": litro["id"], "factor": "1"})
    assert bad.status_code == 422
    assert bad.json()["code"] == "UOM_DIMENSION_MISMATCH"


# ---------------------------------------------------------------- AC-011-04
def test_unidad_base_obligatoria_en_producto_y_opcional_en_servicio():
    h = _headers()
    und = _unit("UND4")
    sin_base = _product("P-SINBASE", None)
    r = _CLIENT.post(f"/api/v1/maestros/productos/{sin_base}/presentaciones", headers=h,
                     json={"code": "CAJA", "name": "Caja", "factor_to_base": "100"})
    assert r.status_code == 422
    assert r.json()["code"] == "BASE_UNIT_REQUIRED"

    servicio = _product("S-HORA", None, item_type="SERVICE")
    ok = _CLIENT.post(f"/api/v1/maestros/productos/{servicio}/presentaciones", headers=h,
                      json={"code": "HORA", "name": "Hora"})
    assert ok.status_code == 200, ok.text
    del und


# ---------------------------------------------------------------- AC-011-05
def test_producto_simple_sin_presentaciones():
    """No se obliga a crear una presentación «Unidad» (FR-011-024)."""
    und = _unit("UND5")
    product = _product("P-SIMPLE", und["id"])
    db = _FACTORY()
    try:
        conversion = uom.to_base(db, Decimal("7"), product)
    finally:
        db.close()
    assert conversion.base_quantity == Decimal("7")
    assert conversion.factor == Decimal(1)
    assert conversion.version_id is None

    presentations = _CLIENT.get(f"/api/v1/maestros/productos/{product}/presentaciones",
                                headers=_headers()).json()
    assert presentations == []


# ---------------------------------------------------------------- AC-011-06
def test_producto_complejo_tres_presentaciones():
    und = _unit("UND6")
    product = _product("P-CPLX", und["id"])
    bolsa = _presentation(product, "BOLSA", "20")
    caja = _presentation(product, "CAJA", "100")
    pallet = _presentation(product, "PALLET", "2000")

    db = _FACTORY()
    try:
        assert uom.to_base(db, 5, product, bolsa["id"]).base_quantity == Decimal("100")
        assert uom.to_base(db, 10, product, caja["id"]).base_quantity == Decimal("1000")
        assert uom.to_base(db, 1, product, pallet["id"]).base_quantity == Decimal("2000")
    finally:
        db.close()

    # Tres presentaciones, un solo producto: no se creó ningún SKU nuevo.
    db = _FACTORY()
    try:
        items = db.execute(select(CatalogItem).where(
            CatalogItem.code.like("P-CPLX%"))).scalars().all()
    finally:
        db.close()
    assert len(items) == 1


# ------------------------------------------------------ AC-011-07 / AC-011-08
def test_factor_decimal_sin_error_binario():
    kg = _unit("KG7", dimension="PESO", decimals=3)
    product = _product("P-SACO", kg["id"])
    saco = _presentation(product, "SACO", "25.5")

    db = _FACTORY()
    try:
        conversion = uom.to_base(db, 3, product, saco["id"])
    finally:
        db.close()
    # Exactamente 76,500: con `float` habría dado 76.49999999999999.
    assert conversion.base_quantity == Decimal("76.500")
    assert isinstance(conversion.base_quantity, Decimal)

    db = _FACTORY()
    try:
        for value, expected in (("2.75", "2.750"), ("1.5", "1.500"), ("0.750", "0.750")):
            assert uom.to_base(db, Decimal(value), product).base_quantity == Decimal(expected)
    finally:
        db.close()


# ---------------------------------------------------------------- AC-011-09
def test_factor_invalido_rechazado():
    und = _unit("UND9")
    product = _product("P-F0", und["id"])
    h = _headers()
    for bad in ("0", "-5"):
        r = _CLIENT.post(f"/api/v1/maestros/productos/{product}/presentaciones", headers=h,
                         json={"code": f"X{bad}", "name": "X", "factor_to_base": bad})
        assert r.status_code == 422, r.text


# ---------------------------------------------------------------- AC-011-24
def test_ninguna_cantidad_usa_float():
    """Las 31 columnas de partida: 0 quedan en `Float`."""
    import re

    from app.core.database import Base as B

    floats = []
    for table in B.metadata.tables.values():
        for column in table.columns:
            name = column.name
            if not re.search(r"quantity|_qty$|^qty_|^factor$|^variance", name):
                continue
            if table.name == "presentations" and name == "content":
                continue  # dato legado conservado a propósito (CL-011-11)
            if column.type.__class__.__name__ == "Float":
                floats.append(f"{table.name}.{name}")
    assert floats == [], floats


# ============================================================================
# Versionado, snapshot e inmutabilidad histórica
# ============================================================================

# ---------------------------------------------------------------- AC-011-10
def test_cambiar_el_factor_crea_version_y_no_edita_la_anterior():
    h = _headers()
    und = _unit("UND10")
    product = _product("P-VER", und["id"])
    caja = _presentation(product, "CAJA", "100",
                         valid_from=datetime.now(UTC) - timedelta(days=30))

    nueva = _CLIENT.post(f"/api/v1/maestros/presentaciones/{caja['id']}/versiones",
                         headers=h, json={"factor_to_base": "120"})
    assert nueva.status_code == 200, nueva.text

    versiones = _CLIENT.get(f"/api/v1/maestros/presentaciones/{caja['id']}/versiones",
                            headers=h).json()
    assert len(versiones) == 2
    abierta = [v for v in versiones if v["is_open"]]
    cerrada = [v for v in versiones if not v["is_open"]]
    assert len(abierta) == 1 and abierta[0]["factor_to_base"] == "120.000000"
    assert len(cerrada) == 1 and cerrada[0]["factor_to_base"] == "100.000000"
    # La versión cerrada no ofrece ninguna acción: no se edita ni se borra.
    assert cerrada[0]["allowed_actions"] == []

    # Y no existe endpoint que la edite.
    from app.main import create_app

    paths = set(create_app().openapi()["paths"])
    assert not any("versiones/{" in p and "PATCH" in str(paths) and p.endswith("}")
                   for p in paths if "versiones" in p and p.count("{") > 1)


# ------------------------------------------------ AC-011-11 · EL CORAZÓN
def test_el_historico_no_cambia_al_cambiar_el_factor():
    """Una compra de 10 CAJAS con CAJA=100 vale 1.000 UND para siempre.

    Aunque mañana la caja pase a 120. Es la razón de existir de esta Spec.
    """
    from app.modules.purchasing.models import PurchaseOrder, PurchaseOrderLine

    h = _headers()
    und = _unit("UND11")
    product = _product("P-HIST", und["id"])
    caja = _presentation(product, "CAJA", "100",
                         valid_from=datetime.now(UTC) - timedelta(days=60))

    # Documento histórico: 10 cajas, congelado con el factor de entonces.
    db = _FACTORY()
    try:
        from app.modules.master_data.models import Party

        # `purchase_orders.supplier_id` referencia `parties`, no `suppliers`.
        party = Party(company_id=_tenant_id(), code="PROV-HIST", name="Proveedor",
                      legal_name="Proveedor C.A.", tax_id="J-9", status="ACTIVE")
        db.add(party)
        db.flush()
        order = PurchaseOrder(company_id=_tenant_id(), code="OC-HIST", status="APPROVED",
                              currency="VED", supplier_id=str(party.id))
        db.add(order)
        db.flush()
        line = PurchaseOrderLine(order_id=str(order.id), product_id=product,
                                 quantity_ordered=Decimal("10"), quantity_received=Decimal("0"),
                                 unit_price=Decimal("5"), presentation_id=caja["id"])
        db.add(line)
        db.flush()
        uom.freeze_line(db, line, product, "quantity_ordered", "base_quantity_ordered")
        db.commit()
        line_id = str(line.id)
        assert line.base_quantity_ordered == Decimal("1000")
        assert line.conversion_factor_snapshot == Decimal("100")
    finally:
        db.close()

    # El factor cambia a 120.
    nueva = _CLIENT.post(f"/api/v1/maestros/presentaciones/{caja['id']}/versiones",
                         headers=h, json={"factor_to_base": "120"})
    assert nueva.status_code == 200, nueva.text

    # El documento histórico **no cambia**.
    db = _FACTORY()
    try:
        line = db.get(PurchaseOrderLine, line_id)
        assert line.quantity_ordered == Decimal("10"), "la cantidad original nunca se toca"
        assert line.base_quantity_ordered == Decimal("1000"), "sigue valiendo 1.000, no 1.200"
        assert line.conversion_factor_snapshot == Decimal("100")
    finally:
        db.close()

    # Un documento **nuevo** sí usa el factor vigente.
    db = _FACTORY()
    try:
        conversion = uom.to_base(db, 10, product, caja["id"])
    finally:
        db.close()
    assert conversion.base_quantity == Decimal("1200")
    assert conversion.factor == Decimal("120")


# ---------------------------------------------------------------- AC-011-13
def test_resolucion_por_fecha_y_bordes():
    und = _unit("UND13")
    product = _product("P-FECHA", und["id"])
    inicio = datetime(2026, 1, 1, tzinfo=UTC)
    corte = datetime(2026, 6, 1, tzinfo=UTC)
    caja = _presentation(product, "CAJA", "100", valid_from=inicio)
    r = _CLIENT.post(f"/api/v1/maestros/presentaciones/{caja['id']}/versiones",
                     headers=_headers(),
                     json={"factor_to_base": "120", "valid_from": corte.isoformat()})
    assert r.status_code == 200, r.text

    db = _FACTORY()
    try:
        assert uom.to_base(db, 1, product, caja["id"],
                           datetime(2026, 5, 15, tzinfo=UTC)).factor == Decimal("100")
        assert uom.to_base(db, 1, product, caja["id"],
                           datetime(2026, 6, 15, tzinfo=UTC)).factor == Decimal("120")
        # Borde exacto: la vigencia nueva empieza ese instante.
        assert uom.to_base(db, 1, product, caja["id"], corte).factor == Decimal("120")
        # Antes de toda versión: se falla, no se inventa un factor.
        with pytest.raises(Exception) as exc:
            uom.to_base(db, 1, product, caja["id"], datetime(2025, 1, 1, tzinfo=UTC))
        assert "CONVERSION_NOT_RESOLVABLE" in str(getattr(exc.value, "code", exc.value))
    finally:
        db.close()


# ---------------------------------------------------------------- AC-011-12
def test_sin_versiones_solapadas():
    h = _headers()
    und = _unit("UND12")
    product = _product("P-OVER", und["id"])
    caja = _presentation(product, "CAJA", "100",
                         valid_from=datetime(2026, 6, 1, tzinfo=UTC))
    # Una vigencia que empieza antes que la abierta se rechaza.
    r = _CLIENT.post(f"/api/v1/maestros/presentaciones/{caja['id']}/versiones", headers=h,
                     json={"factor_to_base": "120",
                           "valid_from": datetime(2026, 1, 1, tzinfo=UTC).isoformat()})
    assert r.status_code == 409
    assert r.json()["code"] == "PRESENTATION_VERSION_OVERLAP"

    db = _FACTORY()
    try:
        abiertas = db.execute(select(ProductPresentationVersion).where(
            ProductPresentationVersion.presentation_id == caja["id"],
            ProductPresentationVersion.valid_to.is_(None))).scalars().all()
    finally:
        db.close()
    assert len(abiertas) == 1


def test_concurrencia_una_sola_version_abierta():
    """Dos usuarios creando versión a la vez: solo una queda abierta."""
    import threading

    h = _headers()
    und = _unit("UNDC")
    product = _product("P-CONC", und["id"])
    caja = _presentation(product, "CAJA", "100",
                         valid_from=datetime.now(UTC) - timedelta(days=10))
    results: list[int] = []
    barrier = threading.Barrier(2)

    def attempt(factor: str) -> None:
        barrier.wait()
        r = _CLIENT.post(f"/api/v1/maestros/presentaciones/{caja['id']}/versiones",
                         headers=h, json={"factor_to_base": factor})
        results.append(r.status_code)

    threads = [threading.Thread(target=attempt, args=(f,)) for f in ("120", "130")]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    db = _FACTORY()
    try:
        abiertas = db.execute(select(ProductPresentationVersion).where(
            ProductPresentationVersion.presentation_id == caja["id"],
            ProductPresentationVersion.valid_to.is_(None))).scalars().all()
    finally:
        db.close()
    assert len(abiertas) == 1, f"quedaron {len(abiertas)} versiones abiertas · {results}"


# ---------------------------------------------------------------- AC-011-19
def test_redondeo_en_un_solo_lugar_y_fraccion_declarada():
    """La unidad declara su precisión; una fracción no declarada se rechaza."""
    und = _unit("UND19", decimals=0)          # indivisible
    product = _product("P-FRAC", und["id"])
    # 1 presentación = 0,5 unidades base -> 3 x 0,5 = 1,5, que no cabe en 0 decimales.
    media = _presentation(product, "MEDIA", "0.5", exact=True)

    db = _FACTORY()
    try:
        with pytest.raises(Exception) as exc:
            uom.to_base(db, 3, product, media["id"])
        assert "CONVERSION_NOT_EXACT" in str(getattr(exc.value, "code", exc.value))
    finally:
        db.close()

    # Declarada como inexacta, se permite y se redondea con el modo de la unidad.
    declarada = _presentation(product, "MEDIA2", "0.5", exact=False)
    db = _FACTORY()
    try:
        conversion = uom.to_base(db, 3, product, declarada["id"])
    finally:
        db.close()
    assert conversion.base_quantity == Decimal("2")     # HALF_UP sobre 1,5
    assert conversion.exact is False


# ---------------------------------------------------------------- AC-011-25
def test_coherencia_base_igual_cantidad_por_factor():
    und = _unit("UND25", decimals=3)
    product = _product("P-COH", und["id"])
    caja = _presentation(product, "CAJA", "12.5")
    db = _FACTORY()
    try:
        for quantity in ("1", "3", "7.25"):
            conversion = uom.to_base(db, Decimal(quantity), product, caja["id"])
            esperado = uom.quantize(Decimal(quantity) * conversion.factor,
                                    db.get(UnitOfMeasure, und["id"]))
            assert conversion.base_quantity == esperado
    finally:
        db.close()
