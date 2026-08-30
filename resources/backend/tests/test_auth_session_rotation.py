"""Rotación de sesión y renovación concurrente (Spec 002, `REM-AUTH-ROUTE-CRAWL-001`).

El refresh token es **de un solo uso**: `rotate_session` revoca la sesión
anterior al emitir la nueva. Esa garantía es la que hace útil la rotación, y no
se toca. Lo que estas pruebas fijan es su consecuencia: dos renovaciones
simultáneas con la misma cookie **no pueden ganar las dos**, y por eso el
cliente debe compartir una sola petición en vuelo.

Aquí se comprueba el lado del servidor. El lado del cliente vive en
`src/api/client.test.ts`.
"""

from __future__ import annotations

import threading

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base, get_db, init_models
from app.core.errors import KontrolError
from app.modules.identity_access import service as identity_service
from app.modules.identity_access.models import Session as AuthSession
from app.modules.setup.api import SetupRequest, initialize
from tests.conftest import make_engine

_CLIENT: TestClient
_FACTORY: sessionmaker

PASSWORD = "Kontrol2026Segura!"


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
    _FACTORY = factory
    _CLIENT = TestClient(app)
    yield _CLIENT


def _login_cookie() -> str:
    r = _CLIENT.post("/api/v1/auth/login", json={
        "tenant_code": "DEMO", "username": "admin", "password": PASSWORD})
    assert r.status_code == 200, r.text
    cookie = r.cookies.get("kontrol_refresh")
    assert cookie, "el login debe entregar la cookie de refresco"
    return cookie


def _live_sessions(db: Session) -> int:
    return int(db.execute(select(func.count()).select_from(AuthSession)
                          .where(AuthSession.revoked_at.is_(None))).scalar_one())


# ------------------------------------------------------------------ rotación
def test_la_renovacion_rota_el_token_y_revoca_el_anterior():
    cookie = _login_cookie()
    r = _CLIENT.post("/api/v1/auth/refresh", cookies={"kontrol_refresh": cookie})
    assert r.status_code == 200, r.text
    assert r.json()["access_token"]
    nueva = r.cookies.get("kontrol_refresh")
    assert nueva and nueva != cookie, "la rotación debe entregar un token distinto"


def test_un_token_ya_usado_no_sirve_dos_veces():
    """Es la garantía que da valor a la rotación. No se debilita."""
    cookie = _login_cookie()
    primera = _CLIENT.post("/api/v1/auth/refresh", cookies={"kontrol_refresh": cookie})
    assert primera.status_code == 200

    segunda = _CLIENT.post("/api/v1/auth/refresh", cookies={"kontrol_refresh": cookie})
    assert segunda.status_code == 401, segunda.text
    assert segunda.json()["code"] in ("SESSION_REVOKED", "SESSION_INVALID")


def test_sin_cookie_se_responde_401_y_no_se_crea_sesion():
    """El arranque en frío de un visitante sin sesión: 401 correcto, sin efectos.

    Es exactamente lo que hace el navegador al abrir `/login` por primera vez, y
    la razón por la que el recorrido de rutas empieza a escuchar la consola
    después de iniciar sesión y no antes.
    """
    # El cliente conserva las cookies de pruebas anteriores: se vacía el tarro
    # para reproducir de verdad a quien nunca ha entrado.
    _CLIENT.cookies.clear()

    db = _FACTORY()
    try:
        antes = _live_sessions(db)
    finally:
        db.close()

    r = _CLIENT.post("/api/v1/auth/refresh")
    assert r.status_code == 401, r.text
    assert r.json()["code"] == "AUTH_REQUIRED"

    db = _FACTORY()
    try:
        assert _live_sessions(db) == antes, "un refresco fallido no crea sesión"
    finally:
        db.close()


def test_un_token_manipulado_no_renueva():
    cookie = _login_cookie()
    r = _CLIENT.post("/api/v1/auth/refresh",
                     cookies={"kontrol_refresh": cookie[:-4] + "AAAA"})
    assert r.status_code == 401
    assert r.json()["code"] in ("SESSION_INVALID", "SESSION_REVOKED", "AUTH_REQUIRED")


def test_tras_cerrar_sesion_el_token_deja_de_servir():
    login = _CLIENT.post("/api/v1/auth/login", json={
        "tenant_code": "DEMO", "username": "admin", "password": PASSWORD})
    cookie = login.cookies.get("kontrol_refresh")
    token = login.json()["access_token"]

    salida = _CLIENT.post("/api/v1/auth/logout",
                          headers={"Authorization": f"Bearer {token}"},
                          cookies={"kontrol_refresh": cookie})
    assert salida.status_code in (200, 204), salida.text

    r = _CLIENT.post("/api/v1/auth/refresh", cookies={"kontrol_refresh": cookie})
    assert r.status_code == 401, r.text


# -------------------------------------------------------------- concurrencia
def test_dos_renovaciones_simultaneas_no_pueden_ganar_las_dos():
    """El defecto que originó `REM-AUTH-ROUTE-CRAWL-001`.

    No se «arregla» en el servidor: que la segunda falle es **correcto** con
    tokens de un solo uso. Lo que se fija aquí es el hecho, para que quien lea
    el cliente entienda por qué comparte la petición en vuelo, y para que nadie
    intente resolverlo relajando la rotación.
    """
    cookie = _login_cookie()
    resultados: list[int] = []
    lock = threading.Lock()

    def _renovar() -> None:
        r = _CLIENT.post("/api/v1/auth/refresh", cookies={"kontrol_refresh": cookie})
        with lock:
            resultados.append(r.status_code)

    hilos = [threading.Thread(target=_renovar) for _ in range(2)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()

    assert len(resultados) == 2
    assert 200 in resultados, "alguna de las dos debe prosperar"
    # Como mucho una gana. Si ganaran las dos, la rotación no sería de un solo uso.
    assert resultados.count(200) == 1, f"dos renovaciones prosperaron: {resultados}"
    assert 401 in resultados


def test_una_renovacion_fallida_no_deja_sesiones_huerfanas():
    """La carrera perdida no puede dejar una sesión viva que nadie usa."""
    db = _FACTORY()
    try:
        antes = _live_sessions(db)
    finally:
        db.close()

    cookie = _login_cookie()          # +1 sesión viva
    primera = _CLIENT.post("/api/v1/auth/refresh", cookies={"kontrol_refresh": cookie})
    assert primera.status_code == 200
    segunda = _CLIENT.post("/api/v1/auth/refresh", cookies={"kontrol_refresh": cookie})
    assert segunda.status_code == 401

    db = _FACTORY()
    try:
        # El login dejó una, la rotación la sustituyó por otra: una viva de más,
        # no dos. El intento rechazado no creó nada.
        assert _live_sessions(db) == antes + 1
    finally:
        db.close()


def test_rotate_session_rechaza_un_token_de_sesion_revocada():
    """Comprobación directa del servicio, sin pasar por HTTP."""
    cookie = _login_cookie()
    db = _FACTORY()
    try:
        _sesion, nuevo, _user = identity_service.rotate_session(db, refresh_token=cookie)
        assert nuevo != cookie
        with pytest.raises(KontrolError) as excinfo:
            identity_service.rotate_session(db, refresh_token=cookie)
        assert excinfo.value.status_code == 401
        assert excinfo.value.code in ("SESSION_REVOKED", "SESSION_INVALID")
    finally:
        db.close()
