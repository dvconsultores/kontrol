"""POC (guion de Claude, fuera del repositorio): la misma carrera de la prueba objetivo bajo dos topologías SQLite —
(a) StaticPool :memory: (una conexión compartida por todos los hilos, la actual) y (b) fichero temporal con una conexión
por hilo— en modo natural (×N) y con entrelazado controlado (barrera antes de que cada hilo ejecute su INSERT)."""
import os, sys, tempfile, threading, time
sys.path.insert(0, "<repo>/resources/backend/tests"); sys.path.insert(0, "<repo>/resources/backend")
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from app.core.database import Base, get_db, init_models
from app.modules.organization.models import Company, Tenant
from app.modules.setup.api import SetupRequest, initialize
from tests.test_system_access import PASSWORD
import app.core.database as dm

def mundo(engine):
    init_models(); Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    dm._engine, dm._SessionLocal = engine, factory
    with factory() as db:
        initialize(db, SetupRequest(tenant_code="DEMO", tenant_name="Empresa Demo", company_code="D1", company_legal_name="Demo C.A.",
                                    company_rif="J-12345678-9", admin_username="admin", admin_password=PASSWORD))
        tenant = db.execute(select(Tenant).where(Tenant.code == "DEMO")).scalars().one()
        d1 = str(db.execute(select(Company).where(Company.tenant_id == tenant.id)).scalars().one().id)
        db.commit()
    from app.main import create_app
    app = create_app()
    def _db():
        d = factory()
        try: yield d
        finally: d.close()
    app.dependency_overrides[get_db] = _db
    cli = TestClient(app)  # como la prueba: relanza los errores del servidor en el hilo
    r = cli.post("/api/v1/auth/login", json={"tenant_code": "DEMO", "username": "admin", "password": PASSWORD}); assert r.status_code == 200
    h = {"Authorization": f"Bearer {r.json()['access_token']}", "X-Kontrol-Company": d1}
    return cli, factory, h, d1

def carrera(cli, h, d1, n, barrera_insert: bool, prefijo: str = "W"):
    """n rondas: dos hilos crean la misma ubicación. Devuelve firmas por ronda."""
    firmas = []
    for ronda in range(n):
        wh = cli.post("/api/v1/organization/warehouses", headers=h, json={"company_id": d1, "code": f"{prefijo}{ronda:03d}", "name": "W", "location_managed": True}).json()
        results, errores = [], []
        barrera = threading.Barrier(2); barrera_sql = threading.Barrier(2, timeout=10) if barrera_insert else None
        def hook(conn, cursor, stmt, params, ctx, many):
            if barrera_sql and stmt.lstrip().upper().startswith("INSERT INTO WAREHOUSE_LOCATIONS") and threading.current_thread() is not threading.main_thread():
                try: barrera_sql.wait()
                except threading.BrokenBarrierError: pass
        event.listen(Engine, "before_cursor_execute", hook)
        def intento():
            barrera.wait()
            try:
                r = cli.post("/api/v1/organization/locations", headers=h, json={"warehouse_id": wh["id"], "code": "RACE-1"})
                results.append(r.status_code)
            except Exception as e:  # noqa: BLE001 — se mide lo que mata al hilo
                errores.append(type(e).__name__ + ": " + str(e)[:90])
        hilos = [threading.Thread(target=intento) for _ in range(2)]
        for t in hilos: t.start()
        for t in hilos: t.join()
        event.remove(Engine, "before_cursor_execute", hook)
        total = cli.get(f"/api/v1/organization/locations?warehouse_id={wh['id']}&q=RACE-1", headers=h).json()["total"]
        firmas.append((tuple(sorted(results)), tuple(errores), total))
    return firmas

def resumen(etiqueta, firmas):
    from collections import Counter
    c = Counter((r, tuple(e[:1]), t) for r, e, t in firmas)
    print(f"--- {etiqueta}: {len(firmas)} rondas ---")
    for (r, e, t), n in c.most_common(): print(f"  {n:3d}× resultados={list(r)} total={t} error={e[0] if e else '-'}")
    return c

modo = sys.argv[1] if len(sys.argv) > 1 else "ambas"
N = int(os.environ.get("N", 30))
if modo in ("memoria", "ambas"):
    print("### (a) StaticPool :memory: — la topología actual ###")
    e = create_engine("sqlite+pysqlite:///:memory:", future=True, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    cli, factory, h, d1 = mundo(e)
    ids = set()
    event.listen(e, "checkout", lambda dbapi, rec, proxy: ids.add(id(dbapi)))
    resumen("(a) natural", carrera(cli, h, d1, N, False)); print("  conexiones DBAPI distintas vistas:", len(ids))
    resumen("(a) entrelazado controlado: los dos INSERT a la vez", carrera(cli, h, d1, 5, True, "C"))
if modo in ("fichero", "ambas"):
    print("### (b) fichero temporal — una conexión por hilo (QueuePool por defecto, check_same_thread=False) ###")
    d = tempfile.mkdtemp(prefix="kontrol-poc-sqlite-"); ruta = os.path.join(d, "carrera.db")
    e = create_engine(f"sqlite+pysqlite:///{ruta}", future=True, connect_args={"check_same_thread": False})
    print("  timeout del driver (busy):", e.raw_connection().connection.__class__, "default sqlite3 timeout=5.0 s (no se toca)")
    cli, factory, h, d1 = mundo(e)
    ids = set()
    event.listen(e, "checkout", lambda dbapi, rec, proxy: ids.add(id(dbapi)))
    # misma base, conexiones distintas: lo que inserta A lo ve B
    a, b = e.raw_connection(), e.raw_connection()
    assert a.connection is not b.connection, "¡misma conexión!"
    a.cursor().execute("create table poc_marcador (x int)"); a.cursor().execute("insert into poc_marcador values (1)"); a.commit()
    print("  conexiones A != B:", a.connection is not b.connection, "· B ve lo que confirmó A:", b.cursor().execute("select count(*) from poc_marcador").fetchone()[0] == 1)
    a.close(); b.close()
    t0 = time.perf_counter(); resumen("(b) natural", carrera(cli, h, d1, N, False)); print(f"  conexiones DBAPI distintas vistas: {len(ids)} · {time.perf_counter()-t0:.1f}s")
    t0 = time.perf_counter(); resumen("(b) entrelazado controlado: los dos INSERT a la vez", carrera(cli, h, d1, 5, True, "C")); print(f"  {time.perf_counter()-t0:.1f}s")
    e.dispose(); import shutil; shutil.rmtree(d); print("  fichero temporal eliminado:", not os.path.exists(ruta))
