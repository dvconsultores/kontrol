"""POC (guion de Claude, fuera del repositorio): la carrera de dos renovaciones con la misma cookie bajo tres topologías
SQLite —(a) StaticPool :memory: (la actual), (b) fichero temporal con una conexión por hilo (lo que da motor_para_hilos),
(c) EXPLORACIÓN: (b) + BEGIN IMMEDIATE en cada transacción— en modo natural (×N) y con entrelazado controlado:
barrera antes de la PRIMERA escritura a `sessions` de cada hilo (los dos leen antes de que ninguno escriba)."""
import os, sys, tempfile, threading
sys.path.insert(0, "<repo>/resources/backend/tests"); sys.path.insert(0, "<repo>/resources/backend")
from collections import Counter
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from app.core.database import Base, get_db, init_models
from app.modules.identity_access.models import Session as AuthSession
from app.modules.setup.api import SetupRequest, initialize
import app.core.database as dm
from tests.test_auth_session_rotation import PASSWORD  # contraseña sintética de la propia prueba; no se copia aquí

def mundo(engine):
    init_models(); Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    dm._engine, dm._SessionLocal = engine, factory
    db = factory(); initialize(db, SetupRequest(tenant_code="DEMO", tenant_name="Empresa Demo", company_code="D1", company_legal_name="Demo C.A.",
                                             company_rif="J-12345678-9", admin_username="admin", admin_password=PASSWORD)); db.close()
    from app.main import create_app
    app = create_app()
    def _db():
        d = factory()
        try: yield d
        finally: d.close()
    app.dependency_overrides[get_db] = _db
    return TestClient(app), factory

def vivas(factory):
    with factory() as db: return int(db.execute(select(func.count()).select_from(AuthSession).where(AuthSession.revoked_at.is_(None))).scalar_one())

def carrera(cli, factory, n, controlado: bool):
    firmas = []
    for _ in range(n):
        r = cli.post("/api/v1/auth/login", json={"tenant_code": "DEMO", "username": "admin", "password": PASSWORD}); assert r.status_code == 200
        cookie = r.cookies.get("kontrol_refresh"); antes = vivas(factory)
        results, errores, pasaron = [], [], set()
        barrera = threading.Barrier(2); barrera_sql = threading.Barrier(2, timeout=10) if controlado else None
        def hook(conn, cursor, stmt, params, ctx, many):
            s = stmt.lstrip().upper(); t = threading.get_ident()
            if barrera_sql and (s.startswith("UPDATE SESSIONS") or s.startswith("INSERT INTO SESSIONS")) and threading.current_thread() is not threading.main_thread() and t not in pasaron:
                pasaron.add(t)
                try: barrera_sql.wait()
                except threading.BrokenBarrierError: pass
        event.listen(Engine, "before_cursor_execute", hook)
        def intento():
            barrera.wait()
            try: results.append(cli.post("/api/v1/auth/refresh", cookies={"kontrol_refresh": cookie}).status_code)
            except Exception as e:  # noqa: BLE001 — se mide lo que mata al hilo
                errores.append(type(e).__name__ + ": " + str(e)[:70])
        hilos = [threading.Thread(target=intento) for _ in range(2)]
        for t in hilos: t.start()
        for t in hilos: t.join()
        event.remove(Engine, "before_cursor_execute", hook)
        firmas.append((tuple(sorted(results)), tuple(errores[:1]), vivas(factory) - antes))
    return firmas

def resumen(etiqueta, firmas):
    print(f"--- {etiqueta}: {len(firmas)} rondas ---")
    for (r, e, d), n in Counter(firmas).most_common(): print(f"  {n:3d}× resultados={list(r)} vivas_delta={d:+d} error={e[0] if e else '-'}")

modo = sys.argv[1] if len(sys.argv) > 1 else "todas"; N = int(os.environ.get("N", 20))
if modo in ("memoria", "todas"):
    print("### (a) StaticPool :memory: — la topología actual ###")
    e = create_engine("sqlite+pysqlite:///:memory:", future=True, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    cli, factory = mundo(e); ids = set(); event.listen(e, "checkout", lambda dbapi, rec, proxy: ids.add(id(dbapi)))
    resumen("(a) natural", carrera(cli, factory, N, False)); print("  conexiones DBAPI distintas vistas:", len(ids))
    resumen("(a) controlado: los dos leen antes de que ninguno escriba", carrera(cli, factory, 5, True))
if modo in ("fichero", "todas"):
    print("### (b) fichero temporal — una conexión por hilo (lo que entrega motor_para_hilos) ###")
    d = tempfile.mkdtemp(prefix="kontrol-poc-auth-"); e = create_engine(f"sqlite+pysqlite:///{d}/base.db", future=True, connect_args={"check_same_thread": False})
    cli, factory = mundo(e); ids = set(); event.listen(e, "checkout", lambda dbapi, rec, proxy: ids.add(id(dbapi)))
    resumen("(b) natural", carrera(cli, factory, N, False)); print("  conexiones DBAPI distintas vistas:", len(ids))
    resumen("(b) controlado: los dos leen antes de que ninguno escriba", carrera(cli, factory, 5, True))
    e.dispose(); import shutil; shutil.rmtree(d)
if modo in ("inmediato", "todas"):
    print("### (c) EXPLORACIÓN, no corrección: (b) + BEGIN IMMEDIATE por transacción ###")
    d = tempfile.mkdtemp(prefix="kontrol-poc-auth-"); e = create_engine(f"sqlite+pysqlite:///{d}/base.db", future=True, connect_args={"check_same_thread": False})
    @event.listens_for(e, "connect")
    def _sin_begin_implicito(dbapi, rec): dbapi.isolation_level = None
    @event.listens_for(e, "begin")
    def _begin_immediate(conn): conn.exec_driver_sql("BEGIN IMMEDIATE")
    cli, factory = mundo(e)
    resumen("(c) natural", carrera(cli, factory, N, False))
    resumen("(c) controlado", carrera(cli, factory, 5, True))
    e.dispose(); import shutil; shutil.rmtree(d)
