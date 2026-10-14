"""POC (Claude, fuera del repositorio): la carrera de dos versiones de presentación bajo (a) StaticPool :memory: y (b) fichero
temporal con una conexión por hilo (= motor_para_hilos), en modo natural (×N) y con entrelazado controlado: barrera antes de
la PRIMERA escritura a product_presentation_versions de cada hilo (los dos han leído la versión abierta)."""
import os, sys, tempfile, threading, shutil
sys.path.insert(0, "<repo>/resources/backend/tests"); sys.path.insert(0, "<repo>/resources/backend")
from collections import Counter
from datetime import UTC, datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from app.core.database import Base, get_db, init_models
from app.modules.master_data.models import CatalogItem, ProductPresentationVersion
from app.modules.organization.models import Company, Tenant
from app.modules.setup.api import SetupRequest, initialize
import app.core.database as dm
from tests.test_auth_session_rotation import PASSWORD

def mundo(engine):
    init_models(); Base.metadata.create_all(engine)
    f = sessionmaker(bind=engine, class_=Session, expire_on_commit=False); dm._engine, dm._SessionLocal = engine, f
    with f() as db:
        initialize(db, SetupRequest(tenant_code="DEMO", tenant_name="Empresa Demo", company_code="D1", company_legal_name="Demo C.A.",
                                    company_rif="J-12345678-9", admin_username="admin", admin_password=PASSWORD))
        t = db.execute(select(Tenant).where(Tenant.code == "DEMO")).scalars().one(); d1 = str(db.execute(select(Company).where(Company.tenant_id == t.id)).scalars().one().id); db.commit()
    from app.main import create_app
    app = create_app()
    def _db():
        d = f()
        try: yield d
        finally: d.close()
    app.dependency_overrides[get_db] = _db
    cli = TestClient(app)
    r = cli.post("/api/v1/auth/login", json={"tenant_code": "DEMO", "username": "admin", "password": PASSWORD}); assert r.status_code == 200
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    return cli, f, h

def preparar(cli, f, h, n):
    u = cli.post("/api/v1/maestros/unidades", headers=h, json={"code": f"U{n}", "name": f"Unidad {n}", "symbol": f"u{n}".lower(), "dimension": "CANTIDAD", "decimals": 0, "rounding_mode": "HALF_UP"}); assert u.status_code == 200, u.text
    company = cli.get("/api/v1/organization/companies", headers=h).json()["items"][0]["id"]
    with f() as db:
        item = CatalogItem(company_id=company, code=f"P{n}", name=f"Producto {n}", item_type="PRODUCT", status="ACTIVE", base_unit_id=u.json()["id"]); db.add(item); db.commit(); pid = str(item.id)
    c = cli.post(f"/api/v1/maestros/productos/{pid}/presentaciones", headers=h, json={"code": "CAJA", "name": "Caja", "exact_in_base": True, "factor_to_base": "100", "valid_from": (datetime.now(UTC) - timedelta(days=10)).isoformat()}); assert c.status_code == 200, c.text
    return c.json()["id"]

def carrera(cli, f, h, n, controlado, prefijo):
    firmas = []
    for i in range(n):
        caja = preparar(cli, f, h, f"{prefijo}{i}")
        results, errores, pasaron = [], [], set(); barrera = threading.Barrier(2); bsql = threading.Barrier(2, timeout=10) if controlado else None
        def hook(conn, cursor, stmt, params, ctx, many):
            s = stmt.lstrip().upper(); t = threading.get_ident()
            if bsql and (s.startswith("UPDATE PRODUCT_PRESENTATION_VERSIONS") or s.startswith("INSERT INTO PRODUCT_PRESENTATION_VERSIONS")) and threading.current_thread() is not threading.main_thread() and t not in pasaron:
                pasaron.add(t)
                try: bsql.wait()
                except threading.BrokenBarrierError: pass
        event.listen(Engine, "before_cursor_execute", hook)
        def intento(factor):
            barrera.wait()
            try: results.append(cli.post(f"/api/v1/maestros/presentaciones/{caja}/versiones", headers=h, json={"factor_to_base": factor}).status_code)
            except Exception as e:  # noqa: BLE001
                errores.append(type(e).__name__ + ": " + str(e)[:70])
        hs = [threading.Thread(target=intento, args=(x,)) for x in ("120", "130")]
        for t in hs: t.start()
        for t in hs: t.join()
        event.remove(Engine, "before_cursor_execute", hook)
        with f() as db:
            abiertas = len(db.execute(select(ProductPresentationVersion).where(ProductPresentationVersion.presentation_id == caja, ProductPresentationVersion.valid_to.is_(None))).scalars().all())
            total = len(db.execute(select(ProductPresentationVersion).where(ProductPresentationVersion.presentation_id == caja)).scalars().all())
        firmas.append((tuple(sorted(results)), tuple(errores[:1]), abiertas, total))
    return firmas

def resumen(et, firmas):
    print(f"--- {et}: {len(firmas)} rondas ---")
    for (r, e, a, t), n in Counter(firmas).most_common(): print(f"  {n:3d}× resultados={list(r)} abiertas={a} versiones={t} error={e[0] if e else '-'}")

modo = sys.argv[1] if len(sys.argv) > 1 else "todas"; N = int(os.environ.get("N", 20))
if modo in ("memoria", "todas"):
    print("### (a) StaticPool :memory: — la topología actual ###")
    e = create_engine("sqlite+pysqlite:///:memory:", future=True, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    cli, f, h = mundo(e); ids = set(); event.listen(e, "checkout", lambda d, r, p: ids.add(id(d)))
    resumen("(a) natural", carrera(cli, f, h, N, False, "A")); print("  conexiones DBAPI distintas vistas:", len(ids))
    resumen("(a) controlado: los dos leen antes de que ninguno escriba", carrera(cli, f, h, 5, True, "B"))
if modo in ("fichero", "todas"):
    print("### (b) fichero temporal — una conexión por hilo (lo que entrega motor_para_hilos) ###")
    d = tempfile.mkdtemp(prefix="kontrol-poc-uom-"); e = create_engine(f"sqlite+pysqlite:///{d}/base.db", future=True, connect_args={"check_same_thread": False})
    cli, f, h = mundo(e); ids = set(); event.listen(e, "checkout", lambda d_, r, p: ids.add(id(d_)))
    resumen("(b) natural", carrera(cli, f, h, N, False, "C")); print("  conexiones DBAPI distintas vistas:", len(ids))
    resumen("(b) controlado: los dos leen antes de que ninguno escriba", carrera(cli, f, h, 5, True, "D"))
    e.dispose(); shutil.rmtree(d)
