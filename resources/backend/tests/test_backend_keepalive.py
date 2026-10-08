"""KA · El servidor HTTP conserva una conexión persistente ociosa más tiempo que cualquier cliente que la
reutilice (`BACKEND-KEEPALIVE-5S`; Spec 054, apoyo 052). El mecanismo de «5 segundos» de la deuda no es un
sondeo: es `timeout_keep_alive`, el valor por defecto de uvicorn, igual al del agente HTTP de Node; la
carrera en ese instante produce `ECONNRESET` o una petición sin respuesta. Aquí se arranca uvicorn de verdad,
con los argumentos EXACTOS de `Dockerfile.backend` y `Dockerfile.central` (leídos del fichero, no copiados), y
se mide con `qa/keepalive_sonda.py`: con el valor por defecto una conexión ociosa 5,3 s está cerrada; con el
de la imagen sigue viva. Sin red externa, sin base migrada (`/health/live` no la necesita).
"""

from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[3]
BACKEND = RAIZ / "resources" / "backend"
sys.path.insert(0, str(RAIZ))
from qa import keepalive_sonda  # noqa: E402

OCIO_QUE_SUPERA_EL_DEFECTO = 5.3  # > 5 s de uvicorn por defecto; < cualquier valor que la imagen fije
CONEXIONES = 12
#: Lo que la conexión debe sobrevivir, como mínimo: el agente de Node (5 s) y el `keepalive_timeout` de
#: upstream de nginx (60 s por defecto). Un valor igual al del proxy reproduce la misma carrera un piso más arriba.
MINIMO_EXIGIDO = 60


def _cmd_de_dockerfile(ruta: Path, modulo: str) -> list[list[str]]:
    """Cada `CMD [...]` de uvicorn para `modulo`, tal como lo ejecutará la imagen."""
    ordenes = []
    for linea in ruta.read_text().splitlines():
        if linea.startswith("CMD [") and modulo in linea:
            ordenes.append(json.loads(linea[4:]))
    assert ordenes, f"{ruta.name} no arranca {modulo}"
    return ordenes


def _keep_alive_de(orden: list[str]) -> int | None:
    if "--timeout-keep-alive" not in orden:
        return None
    return int(orden[orden.index("--timeout-keep-alive") + 1])


def _puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _responde(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=2) as r:  # noqa: S310 - loopback de la propia prueba
            return r.status == 200
    except Exception:  # noqa: BLE001 - arrancando
        return False


@contextmanager
def _uvicorn(orden: list[str], *, ruta_salud: str, entorno: dict[str, str]) -> Iterator[str]:
    """Arranca `orden` (un CMD de la imagen, sin `uvicorn`, `--host`/`--port` ni `--reload`) en un puerto libre."""
    args = [a for a in orden if a not in ("uvicorn", "--reload")]
    for bandera in ("--host", "--port"):
        i = args.index(bandera)
        del args[i : i + 2]
    puerto = _puerto_libre()
    proceso = subprocess.Popen([sys.executable, "-m", "uvicorn", *args, "--host", "127.0.0.1", "--port", str(puerto), "--log-level", "warning"],
                               cwd=BACKEND, env={**os.environ, **entorno}, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        url = f"http://127.0.0.1:{puerto}{ruta_salud}"
        limite = time.monotonic() + 40
        while not _responde(url):
            if proceso.poll() is not None:
                raise AssertionError(f"uvicorn terminó al arrancar: {proceso.stderr.read().decode()[-800:]}")  # type: ignore[union-attr]
            assert time.monotonic() < limite, "uvicorn no respondió en 40 s"
            time.sleep(0.2)
        yield url
    finally:
        proceso.terminate()
        proceso.wait(timeout=15)


def _entorno_cliente(tmp: Path) -> dict[str, str]:
    return {"KONTROL_ENVIRONMENT": "qa", "KONTROL_SECRET_KEY": "sonda-keepalive-" + "x" * 40, "KONTROL_DB_URL": f"sqlite:///{tmp / 'sonda.sqlite'}",
            "KONTROL_INSTALLATION_VOLUME_PATH": str(tmp / "volumen"), "KONTROL_STORAGE_PATH": str(tmp / "storage"), "KONTROL_BACKUP_PATH": str(tmp / "backups"),
            "KONTROL_LOG_JSON": "false"}


def _entorno_central(tmp: Path) -> dict[str, str]:
    return {"KONTROL_CENTRAL_ENVIRONMENT": "qa", "KONTROL_CENTRAL_DB_URL": f"sqlite+pysqlite:///{tmp / 'central.sqlite'}", "KONTROL_CENTRAL_LOG_JSON": "false"}


# ---------------------------------------------------------------- KA-01 · reproducción del defecto (valor por defecto)
def test_ka_01_con_el_valor_por_defecto_de_uvicorn_una_conexion_ociosa_5_3_s_esta_cerrada(tmp_path: Path):
    orden = [a for a in _cmd_de_dockerfile(RAIZ / "Dockerfile.backend", "app.main:app")[0] if a not in ("--timeout-keep-alive", "75")]
    assert _keep_alive_de(orden) is None  # el defecto que la deuda describe: sin bandera, 5 s
    with _uvicorn(orden, ruta_salud="/api/v1/health/live", entorno=_entorno_cliente(tmp_path)) as url:
        medicion = keepalive_sonda.sondear(url, ocio=OCIO_QUE_SUPERA_EL_DEFECTO, conexiones=CONEXIONES)
    assert medicion.reutilizadas == 0 and medicion.cerradas == CONEXIONES, medicion
    assert medicion.errores and set(medicion.errores) <= {"RemoteDisconnected", "ConnectionResetError", "BadStatusLine", "BrokenPipeError"}


# ---------------------------------------------------------------- KA-02 · con la orden de la imagen, la conexión sobrevive
@pytest.mark.parametrize(("dockerfile", "modulo", "salud", "entorno"), [
    ("Dockerfile.backend", "app.main:app", "/api/v1/health/live", _entorno_cliente),
    ("Dockerfile.central", "central_authority.main:app", "/health/live", _entorno_central),
])
def test_ka_02_con_la_orden_exacta_de_la_imagen_la_conexion_ociosa_se_reutiliza(tmp_path: Path, dockerfile: str, modulo: str, salud: str, entorno):
    orden = _cmd_de_dockerfile(RAIZ / dockerfile, modulo)[0]
    assert (_keep_alive_de(orden) or 0) > MINIMO_EXIGIDO, orden
    with _uvicorn(orden, ruta_salud=salud, entorno=entorno(tmp_path)) as url:
        medicion = keepalive_sonda.sondear(url, ocio=OCIO_QUE_SUPERA_EL_DEFECTO, conexiones=CONEXIONES)
    assert medicion.reutilizadas == CONEXIONES and medicion.errores == (), medicion


# ---------------------------------------------------------------- KA-03..05 · todos los arranques llevan el valor; nada más cambia
def test_ka_03_todos_los_arranques_de_uvicorn_del_repositorio_fijan_el_mismo_keep_alive_por_encima_del_proxy():
    valores = {}
    for dockerfile, modulo in (("Dockerfile.backend", "app.main:app"), ("Dockerfile.central", "central_authority.main:app")):
        for orden in _cmd_de_dockerfile(RAIZ / dockerfile, modulo):  # producción y desarrollo (`--reload`)
            valores[f"{dockerfile}:{' '.join(orden[1:3])}"] = _keep_alive_de(orden)
    assert valores and all(v is not None and v > MINIMO_EXIGIDO for v in valores.values()), valores
    assert len(set(valores.values())) == 1  # un solo valor, decidido una vez
    corrida = (RAIZ / "qa" / "e2e_corrida.py").read_text()
    assert re.search(r"^KEEP_ALIVE_SEGUNDOS = (\d+)$", corrida, re.M) and int(re.search(r"^KEEP_ALIVE_SEGUNDOS = (\d+)$", corrida, re.M).group(1)) == next(iter(valores.values()))
    assert corrida.count('"--timeout-keep-alive", str(KEEP_ALIVE_SEGUNDOS)') == 2  # el backend y la autoridad de la corrida


def test_ka_04_el_repositorio_no_tiene_ningun_sondeo_periodico_de_5_segundos():
    """La deuda se llamaba «keepalive» pero no hay latido: el único sondeo del frontend es la campana de
    notificaciones (60 s, Spec 047) y no se toca aquí."""
    frontend = RAIZ / "resources" / "frontend" / "src"
    sondeos = [(f.relative_to(RAIZ).as_posix(), m.group(0)) for f in frontend.rglob("*.ts*") if ".test." not in f.name and "tests" not in f.parts
               for m in re.finditer(r"refetchInterval:\s*[A-Za-z_0-9]+|setInterval\(", f.read_text())]
    assert sondeos == [("resources/frontend/src/modules/notificaciones/NotificationBell.tsx", "refetchInterval: INTERVALO_SONDEO_MS")], sondeos
    assert "INTERVALO_SONDEO_MS = 60_000" in (frontend / "modules" / "notificaciones" / "api.ts").read_text()


def test_ka_05_el_health_y_el_proxy_no_cambian():
    """`/health/live` sigue siendo «proceso vivo»; nginx no reutiliza conexiones con el backend (sin `upstream keepalive`),
    así que el valor del servidor solo tiene que superar a los clientes directos y a un proxy futuro."""
    from app.modules.system import api as sistema

    assert sistema.liveness() == {"status": "ok", "service": "kontrol-backend"}
    nginx = (RAIZ / "resources" / "nginx" / "nginx.conf").read_text()
    assert "proxy_http_version 1.1" in nginx and "upstream" not in nginx and "keepalive" not in nginx
