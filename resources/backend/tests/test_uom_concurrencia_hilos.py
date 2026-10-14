"""O2-02…O2-12 · la carrera de versiones de presentación medida con conexiones propias
(OBS-02 · SQLITE-HILOS-REMANENTES; Spec 011, apoyo 054).

`test_concurrencia_una_sola_version_abierta` corre ahora sobre `motor_para_hilos`: cada petición
tiene su propia conexión DBAPI sobre el mismo datastore. Aquí se fuerza el entrelazado real (las dos
peticiones leen la versión abierta antes de que ninguna escriba), se prueba la topología durante la
carrera y que ninguna excepción de hilo puede esconderse. Sin `skip`, sin `sleep`, sin reintentos,
sin cerrojos que serialicen la carrera.
"""

from __future__ import annotations

import inspect
import os
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base, get_db, init_models
from app.modules.master_data.models import CatalogItem, ProductPresentationVersion
from app.modules.setup.api import SetupRequest, initialize
from tests.conftest import motor_para_hilos

PG = os.environ.get("KONTROL_TEST_DB_URL", "").startswith("postgresql")
PLAZO = 10  # segundos: tope de las barreras; una prueba que lo agota falla, no espera
PASSWORD = "Kontrol2026Segura!"  # contraseña sintética del mundo de prueba

_CLIENT: TestClient
_FACTORY: sessionmaker
_ENGINE = None
_SEQ = {"n": 0}


@pytest.fixture(scope="module", autouse=True)
def _mundo():
    global _CLIENT, _FACTORY, _ENGINE
    with motor_para_hilos("uom-concurrencia") as engine:
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
            admin_username="admin", admin_password=PASSWORD))
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
        _FACTORY, _ENGINE = factory, engine
        _CLIENT = TestClient(app)
        yield _CLIENT


def _headers() -> dict:
    r = _CLIENT.post("/api/v1/auth/login", json={"tenant_code": "DEMO", "username": "admin", "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _presentacion_con_version_abierta() -> str:
    """Unidad, producto y presentación con una versión abierta desde hace diez días; devuelve el id de la presentación."""
    _SEQ["n"] += 1
    n = _SEQ["n"]
    h = _headers()
    u = _CLIENT.post("/api/v1/maestros/unidades", headers=h, json={
        "code": f"UC{n}", "name": f"Unidad {n}", "symbol": f"uc{n}", "dimension": "CANTIDAD", "decimals": 0, "rounding_mode": "HALF_UP"})
    assert u.status_code == 200, u.text
    company = _CLIENT.get("/api/v1/organization/companies", headers=h).json()["items"][0]["id"]
    with _FACTORY() as db:
        item = CatalogItem(company_id=company, code=f"PC{n}", name=f"Producto {n}", item_type="PRODUCT",
                           status="ACTIVE", base_unit_id=u.json()["id"])
        db.add(item)
        db.commit()
        producto = str(item.id)
    c = _CLIENT.post(f"/api/v1/maestros/productos/{producto}/presentaciones", headers=h, json={
        "code": "CAJA", "name": "Caja", "exact_in_base": True, "factor_to_base": "100",
        "valid_from": (datetime.now(UTC) - timedelta(days=10)).isoformat()})
    assert c.status_code == 200, c.text
    return c.json()["id"]


def _versiones(presentacion: str) -> tuple[int, int]:
    """(abiertas, total) de la presentación."""
    with _FACTORY() as db:
        filas = db.execute(select(ProductPresentationVersion).where(
            ProductPresentationVersion.presentation_id == presentacion)).scalars().all()
    return sum(1 for v in filas if v.valid_to is None), len(filas)


def _en_hilos(*trabajos) -> list[str]:
    """Ejecuta cada trabajo en su hilo y devuelve las excepciones que los mataron (vacío si ninguna)."""
    errores: list[str] = []

    def envoltura(trabajo):
        try:
            trabajo()
        except Exception as exc:  # noqa: BLE001 — se mide exactamente qué mata al hilo
            errores.append(f"{type(exc).__name__}: {exc}"[:200])

    hilos = [threading.Thread(target=envoltura, args=(t,)) for t in trabajos]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(PLAZO * 2)
    assert not any(h.is_alive() for h in hilos), "un hilo no terminó"
    return errores


# O2-02/O2-03 · entrelazado controlado: las dos peticiones leen la versión abierta antes de que
# ninguna escriba. Contrato: una crea la versión (200) y la otra recibe 409 PRESENTATION_VERSION_OVERLAP;
# queda una sola abierta y exactamente una versión nueva. O2-09/O2-10: dos conexiones DBAPI distintas
# sobre el mismo datastore durante la carrera. O2-11: ninguna excepción de hilo.
def test_o2_02_dos_lecturas_antes_de_la_primera_escritura_dan_un_200_un_409_y_una_sola_version_nueva():
    presentacion = _presentacion_con_version_abierta()
    h = _headers()
    lectura = threading.Barrier(2, timeout=PLAZO)
    escritura = threading.Barrier(2, timeout=PLAZO)
    leyeron: set[int] = set()
    escribieron: set[int] = set()
    conexiones: set[int] = set()

    def gancho(conn, cursor, sentencia, parametros, contexto, muchos) -> None:
        s = sentencia.lstrip().upper()
        t = threading.get_ident()
        if "PRODUCT_PRESENTATION_VERSIONS" not in s:
            return
        conexiones.add(id(conn.connection.dbapi_connection))
        if s.startswith("SELECT") and t not in leyeron:
            leyeron.add(t)
            lectura.wait()
        elif not PG and s.startswith(("UPDATE", "INSERT")) and t not in escribieron:
            escribieron.add(t)
            escritura.wait()

    respuestas: list = []
    cerrojo = threading.Lock()

    def crear(factor: str) -> None:
        r = _CLIENT.post(f"/api/v1/maestros/presentaciones/{presentacion}/versiones", headers=h,
                         json={"factor_to_base": factor})
        with cerrojo:
            respuestas.append(r)

    event.listen(_ENGINE, "before_cursor_execute", gancho)
    try:
        errores = _en_hilos(lambda: crear("120"), lambda: crear("130"))
    finally:
        event.remove(_ENGINE, "before_cursor_execute", gancho)

    assert errores == [], errores
    estados = sorted(r.status_code for r in respuestas)
    assert estados == [200, 409], [(r.status_code, r.text[:120]) for r in respuestas]
    perdedora = next(r for r in respuestas if r.status_code == 409)
    assert perdedora.json()["code"] == "PRESENTATION_VERSION_OVERLAP", perdedora.text
    assert len(leyeron) == 2, "las dos peticiones leyeron la versión abierta antes de que ninguna escribiera"
    if not PG:
        assert len(escribieron) == 2, "las dos peticiones llegaron a la escritura"
    assert len(conexiones) == 2, "cada petición trabajó sobre su propia conexión DBAPI"
    assert _versiones(presentacion) == (1, 2)  # una abierta (la nueva), dos en total (la anterior cerrada)


# O2-11 · el ayudante de hilos no esconde ninguna excepción.
def test_o2_11_las_excepciones_de_los_hilos_son_visibles():
    def falla() -> None:
        raise ValueError("fallo sintético del hilo")

    assert _en_hilos(falla, lambda: None) == ["ValueError: fallo sintético del hilo"]


# O2-04/O2-12/O2-19 · contrato estático: fixture sobre motor_para_hilos, aserción funcional intacta,
# vector de resultados completo exigido, sin skip/sleep/retry/cerrojo de serialización.
def test_o2_04_contrato_estatico_del_modulo_objetivo():
    objetivo = Path(__file__).with_name("test_uom_conversion.py").read_text(encoding="utf-8")
    assert 'with motor_para_hilos("uom-conversion") as engine:' in objetivo
    assert "= make_engine()" not in objetivo
    inicio = objetivo.index("def test_concurrencia_una_sola_version_abierta")
    bloque = objetivo[inicio:]
    bloque = bloque[: bloque.index("\ndef ")]
    assert "barrier = threading.Barrier(2)" in bloque
    assert 'assert len(abiertas) == 1, f"quedaron {len(abiertas)} versiones abiertas · {results}"' in bloque
    assert "assert errores == [], errores" in bloque
    assert 'errores.append(f"{type(exc).__name__}: {exc}"[:200])' in bloque  # un hilo muerto se registra, no se calla
    assert "assert len(results) == 2 and set(results) <= {200, 409} and 200 in results, results" in bloque
    for prohibido in ("sleep(", "retry", "skip", "xfail", "Lock(", "timeout", ".clear(", "range(", "while "):
        assert prohibido not in bloque, prohibido
    for prohibido in ("pytest.mark.skip", "sleep(", "xfail"):
        assert prohibido not in objetivo, prohibido
    propio = inspect.getsource(test_o2_02_dos_lecturas_antes_de_la_primera_escritura_dan_un_200_un_409_y_una_sola_version_nueva)
    assert 'event.listen(_ENGINE, "before_cursor_execute", gancho)' in propio and "lectura.wait()" in propio
    visibles = inspect.getsource(test_o2_11_las_excepciones_de_los_hilos_son_visibles)
    assert 'raise ValueError("fallo sintético del hilo")' in visibles and '== ["ValueError: fallo sintético del hilo"]' in visibles
