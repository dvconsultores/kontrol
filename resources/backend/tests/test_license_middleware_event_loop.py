"""Contrato y regresión de LicenseMiddleware.

Garantiza que `_get_mode` se ejecuta fuera del bucle de eventos y que el bucle
permanece vivo mientras la consulta espera por una conexión del pool.
"""

from __future__ import annotations

import ast
import asyncio
import contextvars
import os
import socket
import threading
import time
from collections.abc import Iterator, Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, cast

import httpx
import pytest
import uvicorn
from fastapi import Depends
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

import app.core.database as dm
from app.core import middleware as mw
from app.core.database import Base, get_db, init_models
from app.core.license import FULL_ACCESS, READ_ONLY, SECURITY_SUSPENSION
from app.core.middleware import LicenseMiddleware
from app.main import create_app
from app.modules.licensing import service as licensing_service
from app.modules.setup.api import SetupRequest, initialize
from tests.conftest import make_engine, motor_para_hilos

_READ_ONLY_BODY = {
    "code": "LICENSE_READ_ONLY",
    "message": (
        "La licencia anual de KONTROL no ha sido renovada. "
        "La instalación se encuentra en modo solo consulta."
    ),
    "field_errors": {},
    "request_id": None,
    "details": {"license_url": "/mi-licencia"},
}
_SECURITY_BODY = {
    "code": "LICENSE_SECURITY_SUSPENSION",
    "message": "La licencia no es válida. Contacte al soporte de KONTROL.",
    "field_errors": {},
    "request_id": None,
    "details": {"license_url": "/mi-licencia"},
}
_PASSWORD = "Kontrol2026Segura!"


class _Escenario:
    def __init__(self) -> None:
        self.ocupadas = threading.Semaphore(0)
        self.soltar = threading.Event()
        self.entro_al_modo = threading.Event()


_ESCENARIO = _Escenario()


class _Captura:
    def __init__(self, bloquear: bool = False) -> None:
        self.llamadas: list[dict[str, Any]] = []
        self.entro = threading.Event()
        self.soltar = threading.Event()
        self.modo: str = FULL_ACCESS
        self.bloquear = bloquear

    def __call__(self) -> str:
        self.llamadas.append(
            {
                "thread_id": threading.get_ident(),
                "contexto": _contexto_licencia.get(),
                "liberado": None,
            }
        )
        if self.bloquear:
            self.entro.set()
            self.llamadas[-1]["liberado"] = self.soltar.wait(timeout=10)
        return self.modo


_contexto_licencia: contextvars.ContextVar[str] = contextvars.ContextVar(
    "contexto_licencia", default="sin-contexto"
)


async def _endpoint_registrado(request: Any) -> JSONResponse:
    _ejecutados.append(request.method)
    return JSONResponse({"ok": True})


_ejecutados: list[str] = []


def _app_con_doble(captura: _Captura, endpoint: Any = _endpoint_registrado) -> Starlette:
    app = Starlette(
        routes=[
            Route("/api/v1/zona/recurso", endpoint, methods=["GET", "POST", "PUT", "PATCH", "DELETE"]),
            Route("/api/v1/{rest:path}", endpoint, methods=["GET", "POST", "PUT", "PATCH", "DELETE"]),
            Route(
                "/api/v1/auth/login",
                endpoint,
                methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
            ),
            Route(
                "/api/v1/health/ready",
                endpoint,
                methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
            ),
        ]
    )
    app.add_middleware(LicenseMiddleware, get_mode=captura)
    return app


def _peticion(app: Starlette, method: str, path: str) -> httpx.Response:
    async def _hacer() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
            return await client.request(method, path)

    return asyncio.run(_hacer())


@pytest.fixture(autouse=True)
def _limpiar_estado() -> Iterator[None]:
    _ejecutados.clear()
    yield
    _ejecutados.clear()


def test_l01_full_access_get_no_llama_al_doble() -> None:
    captura = _Captura()
    app = _app_con_doble(captura)
    respuesta = _peticion(app, "GET", "/api/v1/zona/recurso")
    assert respuesta.status_code == 200
    assert captura.llamadas == []


def test_l02_full_access_post_llama_una_vez() -> None:
    captura = _Captura()
    app = _app_con_doble(captura)
    respuesta = _peticion(app, "POST", "/api/v1/zona/recurso")
    assert respuesta.status_code == 200
    assert len(captura.llamadas) == 1


def test_l03_read_only_get_sin_llamada() -> None:
    captura = _Captura()
    captura.modo = READ_ONLY
    app = _app_con_doble(captura)
    respuesta = _peticion(app, "GET", "/api/v1/zona/recurso")
    assert respuesta.status_code == 200
    assert captura.llamadas == []


@pytest.mark.parametrize("metodo", ["POST", "PUT", "PATCH", "DELETE"])
def test_l04_read_only_escrituras_bloqueadas(metodo: str) -> None:
    captura = _Captura()
    captura.modo = READ_ONLY
    app = _app_con_doble(captura)
    respuesta = _peticion(app, metodo, "/api/v1/zona/recurso")
    assert respuesta.status_code == 423
    assert respuesta.json() == _READ_ONLY_BODY
    assert _ejecutados == []


def test_l05_security_suspension_bloquea_escritura() -> None:
    captura = _Captura()
    captura.modo = SECURITY_SUSPENSION
    app = _app_con_doble(captura)

    get = _peticion(app, "GET", "/api/v1/zona/recurso")
    assert get.status_code == 200

    _ejecutados.clear()
    post = _peticion(app, "POST", "/api/v1/zona/recurso")
    assert post.status_code == 423
    assert post.json() == _SECURITY_BODY
    assert _ejecutados == []


def test_l06_exenciones_y_metodos_contrato() -> None:
    assert mw.LICENSE_EXEMPT_PREFIXES == (
        "/api/v1/license/",
        "/api/v1/licensing/sync",
        "/api/v1/setup/",
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
        "/api/v1/auth/logout",
        "/api/v1/auth/change-password",
        "/api/v1/auth/password-reset/",
        "/api/v1/auth/mfa/verify",
        "/api/v1/auth/mfa/enrollment",
        "/api/v1/auth/reauth",
        "/api/v1/health/",
    )
    assert mw.WRITE_METHODS == {"POST", "PUT", "PATCH", "DELETE"}

    captura = _Captura()
    captura.modo = READ_ONLY
    app = _app_con_doble(captura)

    login = _peticion(app, "POST", "/api/v1/auth/login")
    assert login.status_code == 200
    for ruta in ("/api/v1/auth/mfa/verify", "/api/v1/auth/mfa/enrollment", "/api/v1/auth/mfa/enrollment/confirm",
                 "/api/v1/auth/reauth"):
        assert _peticion(app, "POST", ruta).status_code == 200, ruta
    health = _peticion(app, "POST", "/api/v1/health/ready")
    assert health.status_code == 200
    assert captura.llamadas == []

    recurso = _peticion(app, "POST", "/api/v1/zona/recurso")
    assert recurso.status_code == 423

    captura2 = _Captura()
    captura2.modo = READ_ONLY
    app2 = _app_con_doble(captura2)
    raiz = _peticion(app2, "POST", "/api/v1/")
    assert raiz.status_code == 423


def test_l07_doble_ejecutado_fuera_del_hilo_del_bucle() -> None:
    captura = _Captura()
    app = _app_con_doble(captura)
    hilo_bucle: int | None = None

    async def _correr() -> httpx.Response:
        nonlocal hilo_bucle
        hilo_bucle = threading.get_ident()
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
            return await client.post("/api/v1/zona/recurso")

    respuesta = asyncio.run(_correr())
    assert respuesta.status_code == 200
    assert len(captura.llamadas) == 1
    assert captura.llamadas[0]["thread_id"] != hilo_bucle


def test_l08_contextvar_visible_en_el_doble() -> None:
    captura = _Captura()
    app = _app_con_doble(captura)
    token = _contexto_licencia.set("valor-de-prueba")
    try:
        respuesta = _peticion(app, "POST", "/api/v1/zona/recurso")
    finally:
        _contexto_licencia.reset(token)
    assert respuesta.status_code == 200
    assert captura.llamadas[0]["contexto"] == "valor-de-prueba"


def test_l09_bucle_vivo_mientras_get_mode_espera() -> None:
    captura = _Captura(bloquear=True)
    app = _app_con_doble(captura)

    async def _correr() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
            tarea = asyncio.create_task(client.post("/api/v1/zona/recurso"))
            await asyncio.to_thread(captura.entro.wait, 10)
            captura.soltar.set()
            respuesta = await tarea
            assert respuesta.status_code == 200

    asyncio.run(_correr())
    assert captura.llamadas[0]["liberado"] is True


def test_l10_ast_middleware_ejecuta_get_mode_en_threadpool() -> None:
    ruta = Path(__file__).resolve().parents[1] / "app" / "core" / "middleware.py"
    codigo = ruta.read_text(encoding="utf-8")
    arbol = ast.parse(codigo)

    clase_license = next(
        nodo for nodo in ast.walk(arbol) if isinstance(nodo, ast.ClassDef) and nodo.name == "LicenseMiddleware"
    )
    dispatch = next(
        nodo
        for nodo in ast.walk(clase_license)
        if isinstance(nodo, ast.FunctionDef | ast.AsyncFunctionDef) and nodo.name == "dispatch"
    )

    llamadas_get_mode: list[ast.Call] = []
    awaits_run_in_threadpool: list[ast.Await] = []
    if_escritura: ast.If | None = None

    for nodo in ast.walk(dispatch):
        if isinstance(nodo, ast.If):
            test = ast.unparse(nodo.test)
            if "WRITE_METHODS" in test and "LICENSE_EXEMPT_PREFIXES" in test:
                if_escritura = nodo
        if isinstance(nodo, ast.Await) and isinstance(nodo.value, ast.Call):
            func = nodo.value.func
            if (
                isinstance(func, ast.Name)
                and func.id == "run_in_threadpool"
                and len(nodo.value.args) == 1
                and isinstance(nodo.value.args[0], ast.Attribute)
                and nodo.value.args[0].attr == "_get_mode"
            ):
                awaits_run_in_threadpool.append(nodo)
        if isinstance(nodo, ast.Call):
            func = nodo.func
            if isinstance(func, ast.Attribute) and func.attr == "_get_mode":
                llamadas_get_mode.append(nodo)

    assert llamadas_get_mode == []
    assert len(awaits_run_in_threadpool) == 1
    assert if_escritura is not None

    alcance_if: set[int] = set()
    for nodo in ast.walk(if_escritura):
        alcance_if.add(id(nodo))
    assert any(id(nodo) in alcance_if for nodo in awaits_run_in_threadpool)

    ultima_sentencia = dispatch.body[-1]
    assert isinstance(ultima_sentencia, ast.Return)
    assert isinstance(ultima_sentencia.value, ast.Await)
    assert isinstance(ultima_sentencia.value.value, ast.Call)
    assert isinstance(ultima_sentencia.value.value.func, ast.Name)
    assert ultima_sentencia.value.value.func.id == "call_next"


class _ServidorUvicorn(uvicorn.Server):
    def __init__(self, config: uvicorn.Config) -> None:
        super().__init__(config)
        self.listo = threading.Event()

    async def startup(self, sockets: Sequence[socket.socket] | None = None) -> None:
        await super().startup(sockets)
        self.listo.set()


class _Telemetria:
    def __init__(self) -> None:
        self.checkout = 0
        self.checkin = 0
        self.lock = threading.Lock()

    def incrementar(self, nombre: str) -> None:
        with self.lock:
            setattr(self, nombre, getattr(self, nombre) + 1)


class _Mundo:
    def __init__(self) -> None:
        self.engine: Engine | None = None
        self.factory: sessionmaker[Session] | None = None
        self.telemetria = _Telemetria()
        self.app: Any = None

    def _registrar_checkout(self, *args: Any) -> None:
        self.telemetria.incrementar("checkout")

    def _registrar_checkin(self, *args: Any) -> None:
        self.telemetria.incrementar("checkin")


def _montar(engine: Engine) -> _Mundo:
    mundo = _Mundo()
    mundo.engine = engine
    assert isinstance(engine.pool, QueuePool)
    assert engine.pool.size() == 5
    assert engine.pool._max_overflow == 10
    assert engine.pool._timeout == 30

    event.listen(engine, "checkout", mundo._registrar_checkout)
    event.listen(engine, "checkin", mundo._registrar_checkin)

    init_models()
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)

    dm._engine = engine
    dm._SessionLocal = factory

    db = factory()
    try:
        initialize(
            db,
            SetupRequest(
                tenant_code="T1",
                tenant_name="Tenant Uno",
                company_code="A",
                company_legal_name="Empresa A CA",
                company_rif="J-11111111-1",
                admin_username="admin",
                admin_password=_PASSWORD,
            ),
        )
        db.commit()
    finally:
        db.close()

    mundo.factory = factory
    mundo.app = create_app()

    @mundo.app.get("/regresion/retener")
    def retener(db: Session = Depends(get_db)) -> dict:
        db.execute(text("select 1"))
        _ESCENARIO.ocupadas.release()
        _ESCENARIO.soltar.wait(timeout=60)
        return {"ok": True}

    @mundo.app.get("/regresion/leer")
    def leer(db: Session = Depends(get_db)) -> dict:
        db.execute(text("select 1"))
        return {"ok": True}

    return mundo


@pytest.fixture(scope="module")
def motor_mundo() -> Iterator[_Mundo]:
    if os.environ.get("KONTROL_TEST_DB_URL"):
        engine = make_engine(pool_pre_ping=True, pool_recycle=1800)
        try:
            yield _montar(engine)
        finally:
            engine.dispose()
    else:
        with motor_para_hilos("license-event-loop") as engine:
            yield _montar(engine)


def _servidor_en_hilo(app: Any) -> tuple[_ServidorUvicorn, threading.Thread, int]:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sonda:
        sonda.bind(("127.0.0.1", 0))
        puerto = sonda.getsockname()[1]
    config = uvicorn.Config(app, host="127.0.0.1", port=puerto, log_level="critical")
    servidor = _ServidorUvicorn(config)
    hilo = threading.Thread(target=servidor.run, daemon=True)
    hilo.start()
    if not servidor.listo.wait(timeout=30):
        servidor.should_exit = True
        hilo.join(timeout=5)
        raise AssertionError("uvicorn no arrancó en 30 s")
    return servidor, hilo, puerto


def _cliente_sync(url: str, method: str, timeout: float = 90.0) -> tuple[httpx.Response, float]:
    inicio = time.monotonic()
    respuesta = httpx.request(method, url, timeout=timeout)
    duracion = time.monotonic() - inicio
    return respuesta, duracion


def _esperar_pool_en_reposo(engine: Engine, telemetria: _Telemetria, checkout_inicial: int, checkin_inicial: int,
                            plazo: float = 10.0) -> None:
    """Espera a que el pool converja tras la última respuesta.

    FastAPI cierra get_db después de enviar la respuesta; SQLAlchemy descuenta el pool
    después del evento checkin. El plazo es de SEGURIDAD, no define el comportamiento
    aceptable.
    """
    espera = threading.Event()
    inicio = time.monotonic()
    while True:
        d_co = telemetria.checkout - checkout_inicial
        d_ci = telemetria.checkin - checkin_inicial
        fuera = engine.pool.checkedout()
        if d_co == d_ci and fuera == 0:
            return
        transcurrido = time.monotonic() - inicio
        if transcurrido >= plazo:
            pytest.fail(
                f"pool no convergió: checkout={d_co}, checkin={d_ci}, checkedout={fuera}, "
                f"overflow={cast(QueuePool, engine.pool).overflow()}, transcurrido={transcurrido:.3f}s"
            )
        espera.wait(0.005)


def _resetea_escenario() -> None:
    _ESCENARIO.ocupadas = threading.Semaphore(0)
    _ESCENARIO.soltar = threading.Event()
    _ESCENARIO.entro_al_modo = threading.Event()


def test_regresion_u01_x3(monkeypatch: pytest.MonkeyPatch, motor_mundo: _Mundo) -> None:
    _resetea_escenario()
    engine = cast(Engine, motor_mundo.engine)
    original = licensing_service.current_mode

    def _current_mode_envuelto(db: Session) -> str:
        _ESCENARIO.entro_al_modo.set()
        return original(db)

    monkeypatch.setattr(licensing_service, "current_mode", _current_mode_envuelto)

    servidor, hilo, puerto = _servidor_en_hilo(motor_mundo.app)
    base = f"http://127.0.0.1:{puerto}"
    checkout_inicial = motor_mundo.telemetria.checkout
    checkin_inicial = motor_mundo.telemetria.checkin
    try:
        with ThreadPoolExecutor(max_workers=20) as pool:
            futuros_retenedoras = [
                pool.submit(_cliente_sync, f"{base}/regresion/retener", "GET", 90.0)
                for _ in range(15)
            ]
            for _ in range(15):
                if not _ESCENARIO.ocupadas.acquire(timeout=30):
                    raise AssertionError("no se ocuparon 15 conexiones")
            assert engine.pool.checkedout() == 15

            futuro_escritura = pool.submit(
                _cliente_sync, f"{base}/api/v1/regresion-escritura", "POST", 90.0
            )
            if not _ESCENARIO.entro_al_modo.wait(timeout=30):
                raise AssertionError("la escritura no llegó al middleware")
            _ESCENARIO.soltar.set()

            respuestas_retenedoras = [f.result(timeout=30) for f in futuros_retenedoras]
            respuesta_escritura, duracion_escritura = futuro_escritura.result(timeout=30)

        assert all(r.status_code == 200 for r, _ in respuestas_retenedoras)
        assert respuesta_escritura.status_code == 404
        assert duracion_escritura < engine.pool._timeout
        assert all(duracion < engine.pool._timeout for _, duracion in respuestas_retenedoras)
        _esperar_pool_en_reposo(engine, motor_mundo.telemetria, checkout_inicial, checkin_inicial)
        assert motor_mundo.telemetria.checkout - checkout_inicial == motor_mundo.telemetria.checkin - checkin_inicial
        assert engine.pool.checkedout() == 0
    finally:
        servidor.should_exit = True
        hilo.join(timeout=30)


def test_regresion_u02_c1(motor_mundo: _Mundo) -> None:
    _resetea_escenario()
    engine = cast(Engine, motor_mundo.engine)
    servidor, hilo, puerto = _servidor_en_hilo(motor_mundo.app)
    base = f"http://127.0.0.1:{puerto}"
    checkout_inicial = motor_mundo.telemetria.checkout
    checkin_inicial = motor_mundo.telemetria.checkin
    try:
        with ThreadPoolExecutor(max_workers=20) as pool:
            futuros = [
                pool.submit(_cliente_sync, f"{base}/regresion/retener", "GET", 90.0)
                for _ in range(15)
            ]
            for _ in range(15):
                if not _ESCENARIO.ocupadas.acquire(timeout=30):
                    raise AssertionError("no se ocuparon 15 conexiones")
            assert engine.pool.checkedout() == 15

            futuro_get = pool.submit(_cliente_sync, f"{base}/regresion/leer", "GET", 90.0)
            _ESCENARIO.soltar.set()
            respuestas = [f.result(timeout=30) for f in futuros]
            respuesta_get, _ = futuro_get.result(timeout=30)

        assert all(r.status_code == 200 for r, _ in respuestas)
        assert respuesta_get.status_code == 200
        _esperar_pool_en_reposo(engine, motor_mundo.telemetria, checkout_inicial, checkin_inicial)
        assert motor_mundo.telemetria.checkout - checkout_inicial == motor_mundo.telemetria.checkin - checkin_inicial
        assert engine.pool.checkedout() == 0
    finally:
        servidor.should_exit = True
        hilo.join(timeout=30)


def test_regresion_u03_c2(monkeypatch: pytest.MonkeyPatch, motor_mundo: _Mundo) -> None:
    _resetea_escenario()
    engine = cast(Engine, motor_mundo.engine)
    original = licensing_service.current_mode

    def _current_mode_envuelto(db: Session) -> str:
        _ESCENARIO.entro_al_modo.set()
        return original(db)

    monkeypatch.setattr(licensing_service, "current_mode", _current_mode_envuelto)

    servidor, hilo, puerto = _servidor_en_hilo(motor_mundo.app)
    base = f"http://127.0.0.1:{puerto}"
    checkout_inicial = motor_mundo.telemetria.checkout
    checkin_inicial = motor_mundo.telemetria.checkin
    try:
        with ThreadPoolExecutor(max_workers=20) as pool:
            futuros = [
                pool.submit(_cliente_sync, f"{base}/regresion/retener", "GET", 90.0)
                for _ in range(14)
            ]
            for _ in range(14):
                if not _ESCENARIO.ocupadas.acquire(timeout=30):
                    raise AssertionError("no se ocuparon 14 conexiones")
            assert engine.pool.checkedout() == 14

            futuro_escritura = pool.submit(
                _cliente_sync, f"{base}/api/v1/regresion-escritura", "POST", 90.0
            )
            respuesta_escritura, _ = futuro_escritura.result(timeout=30)
            assert respuesta_escritura.status_code == 404

            _ESCENARIO.soltar.set()
            respuestas = [f.result(timeout=30) for f in futuros]

        assert all(r.status_code == 200 for r, _ in respuestas)
        _esperar_pool_en_reposo(engine, motor_mundo.telemetria, checkout_inicial, checkin_inicial)
        assert motor_mundo.telemetria.checkout - checkout_inicial == motor_mundo.telemetria.checkin - checkin_inicial
        assert engine.pool.checkedout() == 0
    finally:
        servidor.should_exit = True
        hilo.join(timeout=30)


def test_regresion_u04_x2(motor_mundo: _Mundo) -> None:
    _resetea_escenario()
    engine = cast(Engine, motor_mundo.engine)
    servidor, hilo, puerto = _servidor_en_hilo(motor_mundo.app)
    base = f"http://127.0.0.1:{puerto}"
    checkout_inicial = motor_mundo.telemetria.checkout
    checkin_inicial = motor_mundo.telemetria.checkin
    try:
        with ThreadPoolExecutor(max_workers=20) as pool:
            futuros = [
                pool.submit(_cliente_sync, f"{base}/regresion/retener", "GET", 90.0)
                for _ in range(20)
            ]
            for _ in range(15):
                if not _ESCENARIO.ocupadas.acquire(timeout=30):
                    raise AssertionError("no se ocuparon 15 conexiones")
            _ESCENARIO.soltar.set()
            respuestas = [f.result(timeout=30) for f in futuros]

        assert all(r.status_code == 200 for r, _ in respuestas)
        _esperar_pool_en_reposo(engine, motor_mundo.telemetria, checkout_inicial, checkin_inicial)
        assert motor_mundo.telemetria.checkout - checkout_inicial == motor_mundo.telemetria.checkin - checkin_inicial
        assert engine.pool.checkedout() == 0
    finally:
        servidor.should_exit = True
        hilo.join(timeout=30)
