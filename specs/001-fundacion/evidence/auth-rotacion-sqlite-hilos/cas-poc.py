"""POC (Claude, fuera del repositorio): (1) rowcount 1→0 del UPDATE condicional en SQLite y PostgreSQL; (2) I1 en SQLite
con conexiones independientes sobre el mismo fichero: T1 y T2 leen la sesión sin revocar, llegan a la frontera de escritura,
y ejecutan el UPDATE condicional exacto; se mide rowcount, excepciones y estado final. Sin retry, sin BEGIN IMMEDIATE."""
import os, sys, tempfile, threading, shutil
sys.path.insert(0, "<repo>/resources/backend/tests"); sys.path.insert(0, "<repo>/resources/backend")
from datetime import UTC, datetime, timedelta
from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import Session, sessionmaker
from app.core.database import Base, init_models
from app.modules.identity_access.models import Session as AuthSession, User
from app.modules.setup.api import SetupRequest, initialize
from tests.test_auth_session_rotation import PASSWORD
import pg_harness

def cas(db, sid, now):
    return db.execute(update(AuthSession).where(AuthSession.id == sid, AuthSession.revoked_at.is_(None)).values(revoked_at=now, updated_at=now)).rowcount

def mundo(engine):
    init_models(); Base.metadata.create_all(engine)
    f = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    with f() as db:
        if db.execute(select(User).where(User.username == "admin")).scalars().first() is None:
            initialize(db, SetupRequest(tenant_code="DEMO", tenant_name="Empresa Demo", company_code="D1", company_legal_name="Demo C.A.", company_rif="J-12345678-9", admin_username="admin", admin_password=PASSWORD))
        u = db.execute(select(User).where(User.username == "admin")).scalars().first()
        s = AuthSession(user_id=str(u.id), refresh_token_hash="h"*64, expires_at=datetime.now(UTC)+timedelta(days=1)); db.add(s); db.commit(); sid = str(s.id)
    return f, sid

def rowcount_secuencial(etiqueta, engine):
    f, sid = mundo(engine); now = datetime.now(UTC)
    with f() as db:
        r1 = cas(db, sid, now); db.commit()
    with f() as db:
        r2 = cas(db, sid, now); db.commit()
    with f() as db:
        fila = db.get(AuthSession, sid); print(f"[{etiqueta}] rowcount primero={r1} segundo={r2} · revoked_at puesto={fila.revoked_at is not None}")

def i1_sqlite(engine, rondas):
    f, _ = mundo(engine); res = []
    for _ in range(rondas):
        with f() as db:
            s = AuthSession(user_id=db.execute(select(User.id)).scalars().first(), refresh_token_hash="k"*64, expires_at=datetime.now(UTC)+timedelta(days=1)); db.add(s); db.commit(); sid = str(s.id)
        leidos = threading.Barrier(2, timeout=10); out = {}
        def hilo(n):
            try:
                with f() as db:
                    fila = db.execute(select(AuthSession).where(AuthSession.id == sid).with_for_update()).scalars().first()
                    vista = fila.revoked_at
                    leidos.wait()  # los dos han leído; frontera de escritura
                    rc = cas(db, sid, datetime.now(UTC))
                    if rc == 1:
                        db.add(AuthSession(user_id=fila.user_id, refresh_token_hash=f"n{n}"*16, expires_at=datetime.now(UTC)+timedelta(days=1)))
                    db.commit()
                    out[n] = ("leyó_revocada" if vista is not None else "leyó_libre", rc, fila.revoked_at is not None)
            except Exception as e:  # noqa: BLE001
                out[n] = ("EXC", type(e).__name__, str(e)[:60])
        hs = [threading.Thread(target=hilo, args=(i,)) for i in (1, 2)]
        for h in hs: h.start()
        for h in hs: h.join()
        with f() as db:
            vivas = db.execute(select(AuthSession).where(AuthSession.revoked_at.is_(None))).scalars().all()
            fila = db.get(AuthSession, sid)
        res.append((tuple(sorted(str(v) for v in out.values())), fila.revoked_at is not None, len([v for v in vivas if v.id != sid])))
    from collections import Counter
    for k, n in Counter(res).most_common(): print(f"  {n:3d}× hilos={list(k[0])} original_revocada={k[1]} nuevas_vivas_acumuladas≈{k[2]}")

d = tempfile.mkdtemp(prefix="kontrol-poc-cas-")
e = create_engine(f"sqlite+pysqlite:///{d}/base.db", future=True, connect_args={"check_same_thread": False})
rowcount_secuencial("SQLite fichero", e)
print("--- I1 SQLite (conexiones independientes, mismo fichero), 10 rondas ---"); i1_sqlite(e, 10)
e.dispose(); shutil.rmtree(d)
e2 = create_engine("sqlite+pysqlite:///:memory:", future=True, connect_args={"check_same_thread": False}, poolclass=__import__("sqlalchemy.pool", fromlist=["StaticPool"]).StaticPool)
rowcount_secuencial("SQLite :memory: StaticPool", e2)
url = os.environ.get("KONTROL_TEST_DB_URL")
if url:
    pg_harness.abrir_ambito("poc-cas"); ep = pg_harness.crear_motor_de_prueba(url)
    rowcount_secuencial("PostgreSQL", ep)
    print("--- I1 PostgreSQL (FOR UPDATE serializa la lectura: la barrera se pone tras leer; el segundo lee ya revocada), 5 rondas ---")
    # en PG el segundo SELECT FOR UPDATE espera al commit del primero: la barrera 'leidos' no puede reunir a los dos; se mide con barrera de arranque
    f, _ = mundo(ep); 
    from collections import Counter; res=[]
    for _ in range(5):
        with f() as db:
            s = AuthSession(user_id=db.execute(select(User.id)).scalars().first(), refresh_token_hash="p"*64, expires_at=datetime.now(UTC)+timedelta(days=1)); db.add(s); db.commit(); sid=str(s.id)
        arranque = threading.Barrier(2, timeout=10); out={}
        def hilo(n):
            try:
                arranque.wait()
                with f() as db:
                    fila = db.execute(select(AuthSession).where(AuthSession.id == sid).with_for_update()).scalars().first()
                    if fila.revoked_at is not None: out[n]=("leyó_revocada",); db.rollback(); return
                    rc = cas(db, sid, datetime.now(UTC)); db.commit(); out[n]=("leyó_libre", rc)
            except Exception as e:  # noqa: BLE001
                out[n]=("EXC", type(e).__name__)
        hs=[threading.Thread(target=hilo,args=(i,)) for i in (1,2)]
        for h in hs: h.start()
        for h in hs: h.join()
        res.append(tuple(sorted(str(v) for v in out.values())))
    for k,n in Counter(res).most_common(): print(f"  {n:3d}× hilos={list(k)}")
    pg_harness.cerrar_ambito(pg_harness.ambito_vigente())
