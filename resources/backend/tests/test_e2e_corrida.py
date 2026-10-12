"""E2ECORRIDA · Una corrida entera: lo que se crea se elimina, pase lo que pase (FR-054-E2EDB-008..017).

El lanzador de verdad (`qa/e2e_corrida.py`), con su backend de verdad, contra el servidor
PostgreSQL de `KONTROL_TEST_DB_URL`. En lugar de Playwright corre una orden mínima: lo que se
prueba no es la suite sino el ciclo —la base nace, el backend escribe en ella, y desaparece
cuando la corrida acaba bien, cuando acaba mal y cuando no llega a empezar—.

Necesita el puerto del backend libre: en una máquina cabe una corrida a la vez.
"""

from __future__ import annotations

import io
import json
import os
import shutil
import signal
import socket
import sys
import tempfile
import threading
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "qa"))

import e2e_base as b  # noqa: E402
import e2e_corrida as k  # noqa: E402

URL_DE_PRUEBA = os.environ.get("KONTROL_TEST_DB_URL", "")
pytestmark = pytest.mark.skipif(not URL_DE_PRUEBA.startswith("postgresql"),
                                reason="una corrida E2E solo existe sobre PostgreSQL")

#: Lo que corre en lugar de la suite: comprueba que su entorno apunta a la base de su corrida.
MIRA_SU_BASE = (
    "import os, urllib.request\n"
    "from sqlalchemy import create_engine, text\n"
    "run = os.environ['KONTROL_E2E_RUN_ID']\n"
    "assert os.environ['KONTROL_DB_URL'] == os.environ['KONTROL_E2E_DB_URL']\n"
    "assert 'KONTROL_TEST_DB_URL' not in os.environ\n"
    # El ancla de confianza de la corrida es explícita y sintética: la pública en el entorno y la
    # privada del firmante en el estado efímero, nunca la clave de la instalación (FR-010-154).
    "assert os.environ['KONTROL_LICENSE_PUBLIC_KEY_PEM'].startswith('-----BEGIN PUBLIC KEY-----')\n"
    "assert os.path.exists(os.environ['KONTROL_E2E_LICENSE_SIGNING_KEY'])\n"
    "assert (os.stat(os.environ['KONTROL_E2E_LICENSE_SIGNING_KEY']).st_mode & 0o777) == 0o600\n"
    "with create_engine(os.environ['KONTROL_E2E_DB_URL']).connect() as c:\n"
    "    assert c.execute(text('select current_database()')).scalar_one() == 'kontrol_e2e_test_' + run\n"
    "    assert c.execute(text('select count(*) from users')).scalar_one() == 5\n"
    "    {extra}\n"
    "assert urllib.request.urlopen(os.environ['KONTROL_E2E_API'] + '/health/ready', timeout=10).status == 200\n"
    "print('postgresql://usuario:secreto@host:5432/test_db')\n"
)


def _servidor() -> b.Servidor:
    mantenimiento = make_url(URL_DE_PRUEBA).set(database="postgres").render_as_string(hide_password=False)
    return b.Servidor(admin_url=mantenimiento, duena_url=mantenimiento)


def _existe(nombre: str) -> bool:
    admin = b.motor_administrativo(_servidor())
    try:
        with admin.connect() as c:
            return bool(c.execute(text("select count(*) from pg_database where datname = :n"), {"n": nombre}).scalar())
    finally:
        admin.dispose()


@pytest.fixture
def entorno(tmp_path):
    """El entorno de una corrida de prueba: estado en una ruta corta, evidencia en la carpeta de la prueba.

    Lleva a propósito tres variables que apuntan a otra base: la corrida tiene que ignorarlas.
    """
    estado = Path(tempfile.mkdtemp(prefix="ke2e-", dir="/tmp"))
    env = {clave: valor for clave, valor in os.environ.items()}
    env.update({
        "KONTROL_ENVIRONMENT": "local",
        "KONTROL_E2E_PG_HOSTS": (make_url(URL_DE_PRUEBA).host or "localhost").replace("127.0.0.1", "localhost"),
        "KONTROL_E2E_STATE_DIR": str(estado),
        "KONTROL_E2E_EVIDENCE_DIR": str(tmp_path / "evidencia"),
        "KONTROL_TEST_DB_URL": URL_DE_PRUEBA,
        "KONTROL_DB_URL": URL_DE_PRUEBA,
        "KONTROL_E2E_DB_URL": URL_DE_PRUEBA,
    })
    yield env
    shutil.rmtree(estado, ignore_errors=True)


@pytest.fixture
def puerto_libre():
    if k._puerto_ocupado("127.0.0.1", k.PUERTO_BACKEND):
        pytest.skip(f"el puerto {k.PUERTO_BACKEND} está ocupado: hay otra pila en marcha")


def _corrida(entorno, codigo_python: str, **kwargs) -> tuple[k.Corrida, io.StringIO]:
    salida = io.StringIO()
    corrida = k.Corrida(_servidor(), orden=[sys.executable], argumentos=["-c", codigo_python],
                        sin_frontend=True, entorno=entorno, salida=salida, **kwargs)
    return corrida, salida


def _manifiesto(corrida: k.Corrida) -> dict:
    return json.loads((corrida.evidencia / "manifest.json").read_text())


def _sin_rastro(corrida: k.Corrida) -> None:
    assert not _existe(corrida.base), "la base de la corrida sigue existiendo"
    assert not corrida.estado.exists(), "el estado efímero de la corrida sigue en disco"
    assert all(p.poll() is not None for p in corrida.procesos.values()), "queda un proceso de la corrida en marcha"
    assert not k._puerto_ocupado("127.0.0.1", k.PUERTO_BACKEND), "el backend de la corrida sigue escuchando"
    assert b.procesos_de(corrida.run_id) == []


# ---------------------------------------------------------------- DB-08, DB-09, DB-17..19
def test_e2ecorrida_01_una_corrida_verde_usa_su_base_y_no_deja_nada(entorno, puerto_libre):
    corrida, salida = _corrida(entorno, MIRA_SU_BASE.format(extra="pass"))
    assert corrida.ejecutar() == 0
    _sin_rastro(corrida)

    m = _manifiesto(corrida)
    assert m["base"] == corrida.base == "kontrol_e2e_test_" + corrida.run_id
    assert m["backend"] == {"base": corrida.base, "sesiones": 1}
    assert m["migracion"]["actual"] == m["migracion"]["esperada"] and m["migracion"]["cabezas"] == 1
    assert m["siembra"]["linea_base"] == b.LINEA_BASE and len(m["siembra"]["version"]) == 16
    assert m["suite"]["codigo"] == 0 and m["codigo_de_salida"] == 0
    assert m["limpieza"]["base"] == {"estado": "ELIMINADA", "cortadas": 0} and m["limpieza"]["resultado"] == "LIMPIA"
    assert m["medidas"]["usuarios"] == 5 and m["medidas"]["almacenes"] == 0
    assert m["fases"] == ["comprobar", "crear base", "migrar", "sembrar", "backend",
                          "comprobar la base del backend", "autoridad central", "suite", "limpiar"]
    assert "autoridad" in m["procesos"] and m["limpieza"]["autoridad"] == "detenido"  # la autoridad real de la corrida, y se detiene
    # La base de las pruebas de backend, protegida: nadie se conectó a ella ni la escribió.
    de_prueba = make_url(URL_DE_PRUEBA).database
    assert de_prueba in m["protegidas_antes"] and m["protegidas_sin_cambios"] is True

    # Ni la consola ni lo que queda escrito llevan una URL con usuario y clave.
    escrito = salida.getvalue() + "".join(p.read_text(errors="replace")
                                          for p in corrida.evidencia.iterdir() if p.is_file())
    assert "secreto" not in escrito and k.URL_CON_CREDENCIALES.search(escrito) is None
    assert "://***@host:5432/test_db" in salida.getvalue()
    assert "://***@host:5432/test_db" in (corrida.evidencia / "suite.log").read_text()


# ---------------------------------------------------------------- DB-10, DB-20
def test_e2ecorrida_02_si_la_suite_falla_la_base_desaparece_y_el_codigo_es_el_de_la_suite(entorno, puerto_libre):
    corrida, _ = _corrida(entorno, "import sys; sys.exit(3)")
    assert corrida.ejecutar() == 3
    _sin_rastro(corrida)
    m = _manifiesto(corrida)
    assert m["suite"]["codigo"] == 3 and m["codigo_de_salida"] == 3
    assert m["limpieza"]["resultado"] == "LIMPIA" and m["limpieza"]["base"]["estado"] == "ELIMINADA"


# ---------------------------------------------------------------- DB-11, DB-12, DB-13
def test_e2ecorrida_03_si_falla_la_migracion_la_base_desaparece(entorno, puerto_libre, monkeypatch):
    def rota(*_a, **_k):
        # Un error de migración suele traer la URL de la base, con su clave, en el mensaje.
        raise b.CicloDeBaseRoto("alembic upgrade head terminó con código 1 en postgresql://usuario:secreto@host:5432/test_db")

    monkeypatch.setattr(b, "migrar", rota)
    corrida, salida = _corrida(entorno, "raise SystemExit(0)")
    assert corrida.ejecutar() == k.SALIDA_PREPARACION
    assert corrida.creada is True
    _sin_rastro(corrida)
    m = _manifiesto(corrida)
    assert "suite" not in m and "alembic" in m["error"] and m["limpieza"]["base"]["estado"] == "ELIMINADA"
    assert "backend" not in corrida.procesos
    assert "FALLO" in salida.getvalue()
    # El error queda escrito y dicho, sin la clave.
    escrito = (corrida.evidencia / "manifest.json").read_text()
    assert "://***@host:5432/test_db" in m["error"] and "secreto" not in escrito
    assert "://***@host:5432/test_db" in salida.getvalue() and "secreto" not in salida.getvalue()


def test_e2ecorrida_04_si_falla_la_siembra_la_base_desaparece(entorno, puerto_libre, monkeypatch):
    def rota(*_a, **_k):
        raise b.CicloDeBaseRoto("la siembra terminó con código 1")

    monkeypatch.setattr(b, "sembrar", rota)
    corrida, _ = _corrida(entorno, "raise SystemExit(0)")
    assert corrida.ejecutar() == k.SALIDA_PREPARACION
    _sin_rastro(corrida)
    m = _manifiesto(corrida)
    assert m["migracion"]["cabezas"] == 1 and "siembra" not in m and "suite" not in m


def test_e2ecorrida_05_si_el_backend_no_arranca_se_detiene_y_la_base_desaparece(entorno, puerto_libre, monkeypatch):
    def nunca(self, nombre, url, limite=60.0):
        raise b.CicloDeBaseRoto(f"{nombre} no respondió")

    monkeypatch.setattr(k.Corrida, "esperar_salud", nunca)
    corrida, _ = _corrida(entorno, "raise SystemExit(0)")
    assert corrida.ejecutar() == k.SALIDA_PREPARACION
    assert "backend" in corrida.procesos, "la prueba no llegó a arrancar el backend"
    _sin_rastro(corrida)
    assert _manifiesto(corrida)["limpieza"]["backend"].startswith("detenido")


def test_e2ecorrida_06_si_el_backend_escribe_en_otra_base_la_corrida_se_aborta(entorno, puerto_libre, monkeypatch):
    monkeypatch.setattr(k.Corrida, "_sesiones", lambda self: 0)  # la sesión de la API «no aparece» en la base
    corrida, _ = _corrida(entorno, "raise SystemExit(0)")
    assert corrida.ejecutar() == k.SALIDA_PREPARACION
    _sin_rastro(corrida)
    m = _manifiesto(corrida)
    assert "otra base" in m["error"] and "suite" not in m


# ---------------------------------------------------------------- DB-16
def test_e2ecorrida_07_la_segunda_corrida_no_ve_lo_que_dejo_la_primera(entorno, puerto_libre):
    deja = MIRA_SU_BASE.format(
        extra="c.execute(text('create table rastro_de_la_corrida_a (x int)')); "
              "c.execute(text(\"update tenants set name = 'tocado por A' where code = 'DEMO'\")); c.commit()")
    busca = MIRA_SU_BASE.format(
        extra="assert c.execute(text(\"select to_regclass('public.rastro_de_la_corrida_a')\")).scalar_one() is None; "
              "assert c.execute(text(\"select name from tenants where code = 'DEMO'\")).scalar_one() != 'tocado por A'")
    a, _ = _corrida(entorno, deja)
    assert a.ejecutar() == 0
    segunda, _ = _corrida(entorno, busca)
    assert segunda.ejecutar() == 0
    assert a.base != segunda.base and a.estado != segunda.estado and a.evidencia != segunda.evidencia
    _sin_rastro(a)
    _sin_rastro(segunda)


# ---------------------------------------------------------------- DB-22
def test_e2ecorrida_08_con_el_puerto_ocupado_no_se_crea_nada(entorno, puerto_libre):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as ocupante:
        ocupante.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        ocupante.bind(("127.0.0.1", k.PUERTO_BACKEND))
        ocupante.listen(1)
        corrida, _ = _corrida(entorno, "raise SystemExit(0)")
        assert corrida.ejecutar() == k.SALIDA_PREPARACION
    assert corrida.creada is False and not _existe(corrida.base)
    m = _manifiesto(corrida)
    assert "puertos ocupados" in m["error"] and m["limpieza"]["base"] == {"estado": "NO_CREADA"}
    assert m["fases"] == ["comprobar", "limpiar"]


def test_e2ecorrida_09_una_ruta_de_estado_demasiado_larga_se_dice_antes_de_crear_nada(entorno, puerto_libre):
    entorno["KONTROL_E2E_STATE_DIR"] = "/tmp/" + "ruta-larga-" * 9
    corrida, _ = _corrida(entorno, "raise SystemExit(0)")
    assert corrida.ejecutar() == k.SALIDA_PREPARACION
    assert corrida.creada is False and not _existe(corrida.base)
    assert "demasiado larga" in _manifiesto(corrida)["error"]


def test_e2ecorrida_10_en_un_entorno_que_sirve_a_usuarios_no_se_crea_nada(entorno, puerto_libre):
    entorno["KONTROL_ENVIRONMENT"] = "prod"
    corrida, _ = _corrida(entorno, "raise SystemExit(0)")
    assert corrida.ejecutar() == k.SALIDA_PREPARACION
    assert corrida.creada is False and not _existe(corrida.base)
    assert "BaseNoEsE2E" in _manifiesto(corrida)["error"]


def test_e2ecorrida_11_dos_corridas_no_comparten_nombre_estado_ni_evidencia(entorno):
    a, _ = _corrida(entorno, "pass")
    otra, _ = _corrida(entorno, "pass")
    assert len({a.run_id, otra.run_id}) == len({a.base, otra.base}) == 2
    assert len({a.estado, otra.estado}) == len({a.evidencia, otra.evidencia}) == 2


# ---------------------------------------------------------------- FR-012 · interrupción
def test_e2ecorrida_12_una_corrida_interrumpida_tambien_limpia(entorno, puerto_libre):
    corrida, salida = _corrida(entorno, "import time; time.sleep(120)")
    temporizador = threading.Timer(1.0, lambda: None)

    def interrumpir_cuando_corra_la_suite() -> None:
        while "suite" not in corrida.procesos:
            if not hilo_vigia_activo.is_set():
                return
            threading.Event().wait(0.05)
        os.kill(os.getpid(), signal.SIGTERM)

    hilo_vigia_activo = threading.Event()
    hilo_vigia_activo.set()
    vigia = threading.Thread(target=interrumpir_cuando_corra_la_suite, daemon=True)
    vigia.start()
    try:
        assert corrida.ejecutar() == k.SALIDA_INTERRUMPIDA
    finally:
        hilo_vigia_activo.clear()
        temporizador.cancel()
    _sin_rastro(corrida)
    m = _manifiesto(corrida)
    assert "interrumpida" in m["error"] and m["limpieza"]["resultado"] == "LIMPIA"
    assert "interrumpida" in salida.getvalue()


# ---------------------------------------------------------------- el entorno de los procesos
def test_e2ecorrida_13_los_procesos_de_la_corrida_solo_conocen_su_base(entorno):
    corrida, _ = _corrida(entorno, "pass")
    with pytest.raises(b.CicloDeBaseRoto):
        corrida.entorno_de_procesos()
    corrida.url = corrida.servidor.url_de(corrida.base)
    env = corrida.entorno_de_procesos()
    assert env["KONTROL_DB_URL"] == env["KONTROL_E2E_DB_URL"] == corrida.url
    assert make_url(env["KONTROL_DB_URL"]).database == corrida.base
    assert "KONTROL_TEST_DB_URL" not in env
    assert env["KONTROL_E2E_RUN_ID"] == corrida.run_id
    for clave in ("KONTROL_INSTALLATION_VOLUME_PATH", "KONTROL_STORAGE_PATH", "KONTROL_BACKUP_PATH",
                  "KONTROL_QA_IDS_FILE", "KONTROL_E2E_LICENSE_SIGNING_KEY"):
        assert env[clave].startswith(str(corrida.estado))
    # El ancla de confianza es la del firmante sintético de la corrida, la misma para todos sus
    # procesos, y nunca la clave de la instalación (FR-010-154).
    assert env["KONTROL_LICENSE_PUBLIC_KEY_PEM"].startswith("-----BEGIN PUBLIC KEY-----")
    assert corrida.entorno_de_procesos()["KONTROL_LICENSE_PUBLIC_KEY_PEM"] == env["KONTROL_LICENSE_PUBLIC_KEY_PEM"]
    assert env["KONTROL_E2E_LICENSE_SIGNING_KEY"].endswith("qa_license_signing_key.pem")
    assert not env["KONTROL_E2E_LICENSE_SIGNING_KEY"].endswith("installation_private_key.pem")


def test_e2ecorrida_14_la_orden_por_defecto_es_la_suite_de_playwright_con_su_evidencia_aparte(entorno):
    corrida = k.Corrida(_servidor(), argumentos=["e2e/smoke.spec.ts"], entorno=entorno, salida=io.StringIO())
    orden, cwd = corrida.orden_de_la_suite()
    # `chromium` y, detrás (depende de él), el proyecto `licencia-revision`: el linaje de la licencia corre al final.
    assert orden[:8] == ["node", "node_modules/@playwright/test/cli.js", "test", "--project=chromium", "--project=licencia-revision", "--project=licencia-sync",
                         "--project=licencia-rotacion", "--project=licencia-tasa"]
    assert orden[8:] == ["--output", str(corrida.evidencia / "test-results"), "e2e/smoke.spec.ts"]
    assert cwd == k.FRONTEND
    assert not any(a.startswith(("--retries", "--workers")) for a in orden)


# ---------------------------------------------------------------- el entorno observado (E2E-PANTALLA-SIN-PINTAR)
ENLACES_SINTETICOS = ("lo               UNKNOWN        00:00:00:00:00:00 <LOOPBACK,UP,LOWER_UP>\n"
                      "enp9s9           DOWN           02:00:00:00:00:01 <NO-CARRIER,BROADCAST,MULTICAST,UP>\n"
                      "wlx0             UP             02:00:00:00:00:02 <BROADCAST,MULTICAST,UP,LOWER_UP>\n"
                      "tun7             UNKNOWN        <POINTOPOINT,NOARP,UP,LOWER_UP>\n")
DIRECCIONES_SINTETICAS = ("lo               UNKNOWN        127.0.0.1/8 ::1/128\n"
                          "wlx0             UP             192.0.2.77/24 2001:db8::77/64\n"
                          "tun7             UNKNOWN        198.51.100.9/32\n")


def test_e2ecorrida_15_el_resumen_de_red_no_guarda_direcciones():
    """Lo que entra en el manifiesto: nombres y estado, bandera de túnel y una huella; ninguna dirección."""
    resumen = k.resumir_red(ENLACES_SINTETICOS, DIRECCIONES_SINTETICAS)
    assert resumen["interfaces"] == ["enp9s9:DOWN", "lo:UNKNOWN", "tun7:UNKNOWN", "wlx0:UP"]
    assert resumen["tunel_presente"] is True
    assert len(resumen["huella"]) == 12 and int(resumen["huella"], 16) >= 0
    plano = json.dumps(resumen)
    for direccion in ("192.0.2.77", "2001:db8::77", "198.51.100.9", "127.0.0.1", "02:00:00:00:00:02"):
        assert direccion not in plano, f"el manifiesto filtraría {direccion}"
    sin_tunel = k.resumir_red(ENLACES_SINTETICOS.replace("tun7", "eth7"), DIRECCIONES_SINTETICAS)
    assert sin_tunel["tunel_presente"] is False


def test_e2ecorrida_16_la_huella_cambia_si_cambia_la_red_y_no_si_no_cambia():
    antes = k.resumir_red(ENLACES_SINTETICOS, DIRECCIONES_SINTETICAS)["huella"]
    igual = k.resumir_red(ENLACES_SINTETICOS, DIRECCIONES_SINTETICAS)["huella"]
    otra_ip = k.resumir_red(ENLACES_SINTETICOS, DIRECCIONES_SINTETICAS.replace("192.0.2.77", "192.0.2.78"))["huella"]
    sin_tunel = k.resumir_red(ENLACES_SINTETICOS, DIRECCIONES_SINTETICAS.replace("tun7             UNKNOWN        198.51.100.9/32\n", ""))["huella"]
    assert antes == igual
    assert antes != otra_ip and antes != sin_tunel and otra_ip != sin_tunel


def test_e2ecorrida_17_el_desvio_de_reloj_detecta_un_salto_y_tolera_el_ruido():
    from datetime import UTC, datetime, timedelta

    t0 = datetime(2026, 10, 6, 4, 56, tzinfo=UTC)
    # Reloj coherente: 211 s de pared por 211 s monotónicos (más el ruido de medir).
    coherente = k.desvio_de_reloj(t0, 1000.0, t0 + timedelta(seconds=211.4), 1211.0)
    assert coherente == {"desvio_s": 0.4, "salto": False}
    # El salto del 2026-10-06: +5 h 08 min de pared en una suite de 211 s.
    salto = k.desvio_de_reloj(t0, 1000.0, t0 + timedelta(hours=5, minutes=8, seconds=211), 1211.0)
    assert salto["salto"] is True and salto["desvio_s"] == 18480.0
    # Un salto hacia atrás también cuenta.
    atras = k.desvio_de_reloj(t0, 1000.0, t0 - timedelta(minutes=2), 1211.0)
    assert atras["salto"] is True and atras["desvio_s"] < 0


def test_e2ecorrida_18_una_corrida_anota_el_entorno_sin_direcciones_y_lo_dice(entorno, puerto_libre):
    corrida, salida = _corrida(entorno, "pass")
    assert corrida.ejecutar() == 0
    m = _manifiesto(corrida)
    observado = m["entorno"]
    assert observado["red_inicio"]["disponible"] is True and observado["red_fin"]["disponible"] is True
    assert observado["red_cambio"] is False
    assert observado["reloj"]["salto"] is False and abs(observado["reloj"]["desvio_s"]) <= k.UMBRAL_SALTO_DE_RELOJ_S
    assert set(observado["red_inicio"]) == {"disponible", "interfaces", "tunel_presente", "huella"}
    import re

    assert not re.search(r"\b\d{1,3}(\.\d{1,3}){3}\b", json.dumps(observado)), "el entorno observado no lleva direcciones"
    assert "] entorno: " in salida.getvalue()
