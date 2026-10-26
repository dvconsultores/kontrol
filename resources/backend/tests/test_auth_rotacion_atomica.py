"""SA-01…SA-16 · la rotación de sesión tiene exactamente un ganador, decidido en la escritura
(AUTH-ROTACION-SQLITE-HILOS, decisión A de la dueña; Spec 002 · Seguridad / sesiones, alojada en 001).

`rotate_session` revoca la sesión con un `UPDATE … WHERE id = :sid AND revoked_at IS NULL` y solo quien
actualiza exactamente una fila crea la sesión de reemplazo; la otra petición concurrente actualiza cero
filas y recibe 401 `SESSION_REVOKED`. El bloqueo de fila `with_for_update()` se conserva para PostgreSQL.
Las dos peticiones concurrentes corren sobre `motor_para_hilos` (una conexión por hilo, mismo datastore)
para medir el producto y no el arnés. Sin `skip`, sin `sleep`, sin reintentos, sin cerrojos en la prueba.
"""

from __future__ import annotations

import inspect
import os
import threading
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sesion_mfa import login_completo
from sqlalchemy import event, func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from app.core import security
from app.core.database import Base, get_db, init_models
from app.core.errors import KontrolError
from app.modules.identity_access import service as identity_service
from app.modules.identity_access.models import Session as AuthSession
from app.modules.identity_access.models import User
from app.modules.setup.api import SetupRequest, initialize
from tests.conftest import motor_para_hilos

PG = os.environ.get("KONTROL_TEST_DB_URL", "").startswith("postgresql")
PLAZO = 10  # segundos: tope de las barreras; una prueba que lo agota falla, no espera
PASSWORD = "Kontrol2026Segura!"  # contraseña sintética del mundo de prueba

_CLIENT: TestClient
_FACTORY: sessionmaker
_ENGINE = None


@pytest.fixture(scope="module", autouse=True)
def _mundo():
    global _CLIENT, _FACTORY, _ENGINE
    with motor_para_hilos("auth-rotacion-atomica") as engine:
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


def _login_cookie() -> str:
    r = login_completo(_CLIENT, "/api/v1/auth/login", json={"tenant_code": "DEMO", "username": "admin", "password": PASSWORD})
    assert r.status_code == 200, r.text
    cookie = r.cookies.get("kontrol_refresh")
    assert cookie
    return cookie


def _sid(cookie: str) -> str:
    return str(security.decode_token(cookie, expected_type="refresh")["sid"])


def _vivas(db: Session) -> int:
    return int(db.execute(select(func.count()).select_from(AuthSession).where(AuthSession.revoked_at.is_(None))).scalar_one())


def _revocada(sid: str) -> bool:
    with _FACTORY() as db:
        return db.get(AuthSession, sid).revoked_at is not None


def _refresh(cookie: str):
    return _CLIENT.post("/api/v1/auth/refresh", cookies={"kontrol_refresh": cookie})


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


# SA-01 (SQLite) / SA-02 (PostgreSQL) · entrelazado controlado I1: las dos peticiones leen la sesión
# antes de que ninguna escriba. En SQLite se fuerza con dos barreras (antes del SELECT y antes de la
# primera escritura); en PostgreSQL solo antes del SELECT, porque `FOR UPDATE` serializa la lectura y
# una barrera en la escritura pediría un orden de bloqueo imposible. SA-10/11/12/15 se miden aquí mismo.
def test_sa_01_02_dos_lecturas_antes_de_la_primera_escritura_dan_un_200_y_un_401_y_una_sola_sesion_nueva():
    with _FACTORY() as db:
        antes = _vivas(db)
    cookie = _login_cookie()
    sid = _sid(cookie)
    lectura = threading.Barrier(2, timeout=PLAZO)
    escritura = threading.Barrier(2, timeout=PLAZO)
    leyeron: set[int] = set()
    escribieron: set[int] = set()

    def gancho(conn, cursor, sentencia, parametros, contexto, muchos) -> None:
        s = sentencia.lstrip().upper()
        t = threading.get_ident()
        if s.startswith("SELECT SESSIONS") and t not in leyeron:
            leyeron.add(t)
            lectura.wait()
        elif not PG and s.startswith("UPDATE SESSIONS") and t not in escribieron:
            escribieron.add(t)
            escritura.wait()

    respuestas: list = []
    cerrojo = threading.Lock()

    def renovar() -> None:
        r = _refresh(cookie)
        with cerrojo:
            respuestas.append(r)

    event.listen(_ENGINE, "before_cursor_execute", gancho)
    try:
        errores = _en_hilos(renovar, renovar)
    finally:
        event.remove(_ENGINE, "before_cursor_execute", gancho)

    assert errores == [], errores  # SA-15: ningún hilo muere en silencio
    estados = sorted(r.status_code for r in respuestas)
    assert estados == [200, 401], [(r.status_code, r.text[:120]) for r in respuestas]
    perdedora = next(r for r in respuestas if r.status_code == 401)
    assert perdedora.json()["code"] == "SESSION_REVOKED", perdedora.text
    ganadora = next(r for r in respuestas if r.status_code == 200)
    assert ganadora.json()["access_token"] and ganadora.cookies.get("kontrol_refresh") not in (None, cookie)
    assert len(leyeron) == 2, "las dos peticiones leyeron la sesión antes de que ninguna escribiera"
    if not PG:
        assert len(escribieron) == 2, "las dos peticiones llegaron a la escritura condicional"
    assert _revocada(sid)
    with _FACTORY() as db:
        assert _vivas(db) == antes + 1  # el login dejó una; la rotación la sustituyó por exactamente una


# SA-05 · sesión ya revocada: 401 SESSION_REVOKED (misma respuesta que recibe el perdedor).
def test_sa_05_una_sesion_ya_revocada_responde_401_session_revoked():
    cookie = _login_cookie()
    with _FACTORY() as db:
        identity_service.revoke_session(db, session_id=_sid(cookie))
    r = _refresh(cookie)
    assert (r.status_code, r.json()["code"]) == (401, "SESSION_REVOKED"), r.text


# SA-06 · replay: el token ya usado no sirve dos veces, y el intento perdido no crea sesión (SA-10).
def test_sa_06_10_11_el_token_usado_recibe_401_y_el_perdedor_no_crea_sesion():
    with _FACTORY() as db:
        antes = _vivas(db)
    cookie = _login_cookie()
    primera = _refresh(cookie)
    assert primera.status_code == 200, primera.text
    segunda = _refresh(cookie)
    assert (segunda.status_code, segunda.json()["code"]) == (401, "SESSION_REVOKED"), segunda.text
    with _FACTORY() as db:
        assert _vivas(db) == antes + 1  # SA-11: el ganador creó exactamente una; SA-10: el perdedor, ninguna


# SA-07 · sesión expirada: 401 SESSION_EXPIRED, sin sesión nueva.
def test_sa_07_una_sesion_expirada_responde_401_session_expired():
    cookie = _login_cookie()
    sid = _sid(cookie)
    with _FACTORY() as db:
        antes = _vivas(db)
        fila = db.get(AuthSession, sid)
        fila.expires_at = identity_service._now() - timedelta(days=1)
        db.commit()
    r = _refresh(cookie)
    assert (r.status_code, r.json()["code"]) == (401, "SESSION_EXPIRED"), r.text
    with _FACTORY() as db:
        assert _vivas(db) == antes - 1  # la expirada queda revocada; nada nuevo


# SA-08 · hash distinto: 401 SESSION_INVALID y la sesión sigue viva (la validación va antes de la escritura).
def test_sa_08_un_hash_distinto_responde_401_session_invalid_y_no_revoca():
    cookie = _login_cookie()
    sid = _sid(cookie)
    with _FACTORY() as db:
        db.get(AuthSession, sid).refresh_token_hash = "0" * 64
        db.commit()
    r = _refresh(cookie)
    assert (r.status_code, r.json()["code"]) == (401, "SESSION_INVALID"), r.text
    assert not _revocada(sid)


# SA-09 · usuario inactivo: 403 AUTH_USER_INACTIVE y la sesión sigue viva.
def test_sa_09_un_usuario_inactivo_responde_403_y_no_revoca():
    cookie = _login_cookie()
    sid = _sid(cookie)
    with _FACTORY() as db:
        usuario = db.execute(select(User).where(User.username == "admin")).scalars().one()
        usuario.status = "INACTIVE"
        db.commit()
    try:
        r = _refresh(cookie)
        assert (r.status_code, r.json()["code"]) == (403, "AUTH_USER_INACTIVE"), r.text
        assert not _revocada(sid)
    finally:
        with _FACTORY() as db:
            db.execute(select(User).where(User.username == "admin")).scalars().one().status = "ACTIVE"
            db.commit()


# SA-13 · la instancia ORM ya cargada no reescribe la revocación condicional.
def test_sa_13_la_instancia_cargada_no_deshace_la_revocacion_condicional():
    cookie = _login_cookie()
    sid = _sid(cookie)
    db = _FACTORY()
    try:
        cargada = db.get(AuthSession, sid)  # misma identidad que usará rotate_session
        assert cargada.revoked_at is None
        _nueva, nuevo, _user = identity_service.rotate_session(db, refresh_token=cookie)
        assert nuevo != cookie
        assert cargada.revoked_at is not None  # la sesión ORM quedó sincronizada con la escritura
        cargada.user_agent = cargada.user_agent  # un flush posterior no tiene nada que reescribir
        db.flush()
        db.commit()
    finally:
        db.close()
    assert _revocada(sid)
    with _FACTORY() as db:
        assert db.get(AuthSession, sid).updated_at is not None


# SA-14 · un error de bloqueo/operacional no se confunde con SESSION_REVOKED: sube tal cual.
def test_sa_14_un_operational_error_en_la_escritura_no_se_traduce_a_session_revoked(monkeypatch):
    cookie = _login_cookie()
    sid = _sid(cookie)

    def bloqueo(*args, **kwargs):
        raise OperationalError("UPDATE sessions …", {}, Exception("database is locked"))

    monkeypatch.setattr(identity_service, "update", bloqueo)
    db = _FACTORY()
    try:
        with pytest.raises(OperationalError):
            identity_service.rotate_session(db, refresh_token=cookie)
        db.rollback()
    finally:
        db.close()
    assert not _revocada(sid)
    monkeypatch.undo()
    with _FACTORY() as db:
        with pytest.raises(KontrolError) as info:
            identity_service.rotate_session(db, refresh_token=cookie + "x")
        assert info.value.status_code == 401


# SA-15 · el ayudante de hilos no esconde ninguna excepción: la devuelve con su tipo y su mensaje.
def test_sa_15_las_excepciones_de_los_hilos_son_visibles():
    def falla() -> None:
        raise ValueError("fallo sintético del hilo")

    def pasa() -> None:
        return None

    assert _en_hilos(falla, pasa) == ["ValueError: fallo sintético del hilo"]


# SA-16 · contrato estático: la escritura condicional, el bloqueo de fila y la prueba objetivo intactos.
def test_sa_16_contrato_estatico_de_la_rotacion_y_de_la_prueba_objetivo():
    fuente = inspect.getsource(identity_service.rotate_session)
    assert ".with_for_update()" in fuente
    assert "AuthSession.revoked_at.is_(None)" in fuente and ".rowcount" in fuente
    assert "if revocadas == 0:" in fuente and 'code="SESSION_REVOKED"' in fuente
    assert "if revocadas != 1:" in fuente and "raise RuntimeError(" in fuente
    assert fuente.index("revocadas = db.execute(") < fuente.index("create_session(db, user=user")
    assert fuente.index("user.status != \"ACTIVE\"") < fuente.index("revocadas = db.execute(")
    for prohibido in ("BEGIN IMMEDIATE", "except OperationalError", "except Exception", "sleep(", "retry", "timeout"):
        assert prohibido not in fuente, prohibido
    assert fuente.count("session.revoked_at = _now()") == 1  # solo la sesión expirada se marca por atributo
    assert "ahora = _now()" in fuente and "datetime.now(" not in fuente and "utcnow(" not in fuente  # reloj canónico

    objetivo = Path(__file__).with_name("test_auth_session_rotation.py").read_text(encoding="utf-8")
    assert 'with motor_para_hilos("auth-session-rotation") as engine:' in objetivo
    assert "= make_engine()" not in objetivo
    inicio = objetivo.index("def test_dos_renovaciones_simultaneas_no_pueden_ganar_las_dos")
    bloque = objetivo[inicio:]
    bloque = bloque[: bloque.index("\ndef ")]
    for aserto in ("assert len(resultados) == 2", 'assert 200 in resultados, "alguna de las dos debe prosperar"',
                   'assert resultados.count(200) == 1, f"dos renovaciones prosperaron: {resultados}"', "assert 401 in resultados"):
        assert aserto in bloque, aserto
    for prohibido in ("sleep(", "retry", "skip", "xfail", " or len(resultados)", ">= 1"):
        assert prohibido not in bloque, prohibido
    for prohibido in ("pytest.mark.skip", "sleep(", "xfail"):
        assert prohibido not in objetivo, prohibido
