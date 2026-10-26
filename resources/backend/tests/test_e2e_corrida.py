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
import zipfile
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
    # 5 usuarios base + 6 clones por worker de cada uno (Spec 002, OQ-MFA-3).
    "    assert c.execute(text('select count(*) from users')).scalar_one() == 35\n"
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
    assert m["backend"] == {"base": corrida.base, "desafios": 1}
    assert m["migracion"]["actual"] == m["migracion"]["esperada"] and m["migracion"]["cabezas"] == 1
    assert m["siembra"]["linea_base"] == b.LINEA_BASE and len(m["siembra"]["version"]) == 16
    assert m["suite"]["codigo"] == 0 and m["codigo_de_salida"] == 0
    assert m["limpieza"]["base"] == {"estado": "ELIMINADA", "cortadas": 0} and m["limpieza"]["resultado"] == "LIMPIA"
    assert m["limpieza"]["material_mfa"] == {"retirados": [], "quedan": 0}
    assert m["medidas"]["usuarios"] == 35 and m["medidas"]["almacenes"] == 0
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
    monkeypatch.setattr(k.Corrida, "_desafios", lambda self: 0)  # el desafío MFA de la API «no aparece» en la base
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


def test_e2ecorrida_09_una_ruta_de_estado_larga_ya_no_impide_la_corrida_y_la_referencia_es_relativa(entorno, puerto_libre):
    """Antes el runner abortaba con más de 120 caracteres porque el producto persistía la ruta absoluta de la
    clave (INSTALACION-KEY-REFERENCE-120). Ahora la referencia es relativa al volumen: la corrida sigue, y el
    manifiesto deja constancia de la referencia persistida y del largo del volumen que no la condiciona."""
    entorno["KONTROL_E2E_STATE_DIR"] = "/tmp/" + "ruta-larga-" * 9
    corrida, _ = _corrida(entorno, "pass")
    assert corrida.ejecutar() == 0
    instalacion = _manifiesto(corrida)["instalacion"]
    assert instalacion["key_reference"] == "installation_private_key.pem" and instalacion["relativa"] is True
    assert instalacion["largo_del_volumen"] > 120


def test_e2ecorrida_09b_si_el_producto_volviera_a_persistir_la_ruta_absoluta_la_corrida_lo_dice(entorno, puerto_libre, monkeypatch):
    """El invariante que sustituye a la guarda: una referencia absoluta, con separadores o nula en la base de la
    corrida no se tolera en silencio. Se simula el defecto escribiendo la ruta absoluta tras la siembra."""
    from sqlalchemy import create_engine, text

    original = k.Corrida.verificar_backend

    def _con_ruta_absoluta(self):
        motor = create_engine(self.url, future=True)
        with motor.begin() as conn:
            # Una ruta absoluta que SÍ cabe en la columna: lo que debe rechazarla es el invariante del runner, no PostgreSQL.
            conn.execute(text("update installations set key_reference = :r"), {"r": "/data/license-state/installation_private_key.pem"})
        motor.dispose()
        return original(self)

    monkeypatch.setattr(k.Corrida, "verificar_backend", _con_ruta_absoluta)
    corrida, _ = _corrida(entorno, "pass")
    assert corrida.ejecutar() == k.SALIDA_PREPARACION
    assert "INSTALACION-KEY-REFERENCE-120" in _manifiesto(corrida)["error"]
    assert not _existe(corrida.base)


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


def test_e2ecorrida_19_la_corrida_anota_el_interprete_del_arnes_y_el_de_la_migracion_de_la_autoridad(entorno, puerto_libre):
    import sqlalchemy

    import alembic

    corrida, salida = _corrida(entorno, "pass")
    assert corrida.ejecutar() == 0
    m = _manifiesto(corrida)
    raices = k.raices_a_sanear(entorno)
    assert m["interpretes"]["paridad"] == 1
    arnes = m["interpretes"]["arnes"]
    assert arnes["ejecutable"] == k.sanear(sys.executable, raices)
    assert arnes["python"] == ".".join(str(parte) for parte in sys.version_info[:3])
    hijo = m["interpretes"]["migracion_autoridad"]
    assert hijo["ejecutable"] == arnes["ejecutable"]
    assert hijo["exe_real"] == arnes["exe_real"]
    assert hijo["python"] == arnes["python"]
    assert hijo["alembic"] == alembic.__version__
    assert hijo["sqlalchemy"] == sqlalchemy.__version__
    assert hijo["orden"] == [arnes["ejecutable"], "-m", "alembic", "-c", "central_authority/alembic.ini", "upgrade", "head"]
    assert str(k.base.RAIZ) not in json.dumps(m["interpretes"])
    assert tempfile.gettempdir() not in json.dumps(m["interpretes"])
    assert "] intérprete: arnés " in salida.getvalue()
    linea = next(x for x in salida.getvalue().splitlines() if "] intérprete: arnés " in x)
    assert linea.endswith("paridad 1")
    assert m["fases"] == ["comprobar", "crear base", "migrar", "sembrar", "backend", "comprobar la base del backend", "autoridad central", "suite", "limpiar"]


def test_e2ecorrida_20_la_paridad_falla_si_cambia_el_ejecutable_el_real_o_la_version():
    base = {"ejecutable": "a", "exe_real": "b", "python": "3.13.16"}
    assert k.paridad_de_interpretes(base, dict(base)) == 1
    for clave in ("ejecutable", "exe_real", "python"):
        hijo = dict(base)
        hijo[clave] = "distinto"
        assert k.paridad_de_interpretes(base, hijo) == 0


def test_e2ecorrida_21_el_saneado_quita_repo_tmp_y_home():
    raices = k.raices_a_sanear({"HOME": "/h/u"})
    assert k.sanear(str(k.base.RAIZ) + "/x", raices) == "<repo>/x"
    assert k.sanear(tempfile.gettempdir() + "/y", raices) == "<tmp>/y"
    assert k.sanear("/h/u/z", raices) == "<home>/z"
    assert k.sanear("/a/b/c", {"/a/b": "<largo>", "/a": "<corto>"}) == "<largo>/c"
    largos = list(raices.keys())
    assert all(len(largos[i]) >= len(largos[i + 1]) for i in range(len(largos) - 1))


def test_e2ecorrida_22_si_la_sonda_del_interprete_falla_la_corrida_no_sigue_y_limpia(entorno, puerto_libre, monkeypatch):
    monkeypatch.setattr(k, "SONDA_DEL_INTERPRETE", "import sys; sys.exit(3)")
    corrida = _corrida(entorno, "pass")[0]
    assert corrida.ejecutar() == k.SALIDA_PREPARACION
    _sin_rastro(corrida)
    assert "sonda del intérprete" in _manifiesto(corrida)["error"]
    assert "suite" not in _manifiesto(corrida)


def test_e2ecorrida_23_una_sonda_con_claves_de_mas_o_de_menos_tambien_falla_la_corrida(entorno, puerto_libre, monkeypatch):
    monkeypatch.setattr(k, "SONDA_DEL_INTERPRETE", 'import json; print(json.dumps({"x": "y"}))')
    corrida = _corrida(entorno, "pass")[0]
    assert corrida.ejecutar() == k.SALIDA_PREPARACION
    _sin_rastro(corrida)
    assert "sonda del intérprete" in _manifiesto(corrida)["error"]
    assert "suite" not in _manifiesto(corrida)


def test_e2ecorrida_24_una_sonda_que_termina_mal_aunque_imprima_un_json_valido_falla_la_corrida(entorno, puerto_libre, monkeypatch):
    monkeypatch.setattr(k, "SONDA_DEL_INTERPRETE", k.SONDA_DEL_INTERPRETE + "; sys.exit(3)")
    corrida = _corrida(entorno, "pass")[0]
    assert corrida.ejecutar() == k.SALIDA_PREPARACION
    _sin_rastro(corrida)
    m = _manifiesto(corrida)
    assert "sonda del intérprete" in m["error"]
    assert "suite" not in m
    assert "interpretes" not in m


def test_e2ecorrida_25_la_suite_recibe_el_interprete_de_la_certificacion_y_no_el_heredado(
    entorno, puerto_libre
):
    entorno["KONTROL_E2E_PYTHON"] = "/opt/heredado/bin/python3"
    programa = (
        "import os, sys\n"
        "assert os.environ['KONTROL_E2E_PYTHON'] == sys.executable, "
        "(os.environ['KONTROL_E2E_PYTHON'], sys.executable)\n"
    )
    corrida, _ = _corrida(entorno, programa)
    assert corrida.ejecutar() == 0
    _sin_rastro(corrida)
    m = _manifiesto(corrida)
    assert m["suite"]["codigo"] == 0


def test_e2ecorrida_26_la_autoridad_exportada_es_exactamente_sys_executable():
    import ast

    fuente = Path(k.__file__).read_text(encoding="utf-8")
    arbol = ast.parse(fuente)
    funcion = next(
        nodo
        for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.FunctionDef) and nodo.name == "entorno_de_procesos"
    )
    valores = []
    for nodo in ast.walk(funcion):
        if not isinstance(nodo, ast.Dict):
            continue
        for clave, valor in zip(nodo.keys, nodo.values, strict=True):
            if (
                isinstance(clave, ast.Constant)
                and clave.value == "KONTROL_E2E_PYTHON"
            ):
                valores.append(valor)
    assert len(valores) == 1
    assert ast.unparse(valores[0]) == "sys.executable"


def test_e2ecorrida_27_sin_opcion_el_producto_corre_con_el_interprete_del_arnes(entorno, puerto_libre):
    corrida, salida = _corrida(entorno, "pass")
    assert corrida.ejecutar() == 0
    m = _manifiesto(corrida)
    _sin_rastro(corrida)
    assert m["interprete_de_producto"]["modo"] == "UN_SOLO_ENTORNO"
    assert m["interprete_de_producto"]["autoridad"] == k.sanear(sys.executable, k.raices_a_sanear(entorno))
    assert m["interprete_de_producto"]["python"] == ".".join(str(p) for p in sys.version_info[:3])
    assert m["interprete_de_producto"]["paridad_runtime"] == 1
    assert m["interprete_de_producto"]["paquetes"] > 0
    assert "] producto: " in salida.getvalue()
    # En un solo entorno el intérprete del producto es el del arnés (tiene pytest); en V6R la lista sale vacía.
    assert "pytest" in m["interprete_de_producto"]["herramientas_de_prueba"]


def test_e2ecorrida_28_con_opcion_el_producto_corre_con_el_interprete_indicado(entorno, puerto_libre, tmp_path):
    envoltorio = tmp_path / "python-producto"
    envoltorio.write_text(f'#!/bin/sh\nexec "{sys.executable}" "$@"\n')
    envoltorio.chmod(0o755)
    corrida, salida = _corrida(entorno, "pass", python_de_producto=str(envoltorio))
    assert corrida.ejecutar() == 0
    m = _manifiesto(corrida)
    _sin_rastro(corrida)
    assert m["interprete_de_producto"]["modo"] == "RUNTIME_SEPARADO"
    assert m["interprete_de_producto"]["autoridad"] == k.sanear(str(envoltorio), k.raices_a_sanear(entorno))
    assert m["interprete_de_producto"]["paridad_runtime"] == 1


def test_e2ecorrida_29_un_interprete_de_producto_que_no_es_ruta_absoluta_ejecutable_no_crea_nada(entorno, puerto_libre, tmp_path):
    for valor in ("python3", str(tmp_path / "no-existe")):
        corrida = _corrida(entorno, "pass", python_de_producto=valor)[0]
        assert corrida.ejecutar() == k.SALIDA_PREPARACION
        m = _manifiesto(corrida)
        _sin_rastro(corrida)
        assert "intérprete de producto" in m["error"]
        assert "suite" not in m


def test_e2ecorrida_30_la_paridad_de_runtime_exige_misma_version_de_todo_paquete_del_producto():
    assert k.paridad_de_runtime({"a": "1", "b": "2"}, {"a": "1", "b": "2", "pytest": "9"}) == 1
    assert k.paridad_de_runtime({"a": "1"}, {"a": "2"}) == 0
    assert k.paridad_de_runtime({"a": "1"}, {}) == 0
    assert k.paridad_de_runtime({"pip": "1"}, {"pip": "2"}) == 1


def test_e2ecorrida_31_los_procesos_de_producto_usan_el_interprete_de_producto():
    import ast

    fuente = Path(k.__file__).read_text(encoding="utf-8")
    arbol = ast.parse(fuente)
    listas_uvicorn = []
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.Call):
            continue
        for argumento in nodo.args:
            if isinstance(argumento, ast.List) and any(
                isinstance(elemento, ast.Constant) and elemento.value == "uvicorn"
                for elemento in argumento.elts
            ):
                listas_uvicorn.append(argumento)
    assert len(listas_uvicorn) == 2
    for lista in listas_uvicorn:
        assert ast.unparse(lista.elts[0]) == "self.python_de_producto"
        assert ast.unparse(lista.elts[0]) != "sys.executable"


def test_e2ecorrida_32_main_pasa_el_interprete_de_producto_a_la_corrida(monkeypatch):
    vistas = []

    class Falsa:
        def __init__(self, servidor, **kwargs):
            vistas.append(kwargs)

        def ejecutar(self) -> int:
            return 0

    monkeypatch.setattr(k, "Corrida", Falsa)
    monkeypatch.setattr(k.base.Servidor, "del_entorno", staticmethod(lambda: object()))
    assert k.main(["--sin-frontend", "--python-de-producto", "/opt/v6r/bin/python"]) == 0
    assert k.main(["--sin-frontend"]) == 0
    assert vistas[0]["python_de_producto"] == "/opt/v6r/bin/python"
    assert vistas[1]["python_de_producto"] is None
    assert vistas[0]["sin_frontend"] is True


def test_e2ecorrida_33_la_evidencia_no_conserva_material_mfa_de_las_pruebas_fallidas(entorno):
    """Las trazas de las pruebas fallidas no dejan material MFA en la evidencia."""
    corrida, _ = _corrida(entorno, "pass")
    resultados = corrida.evidencia / "test-results"

    alta = resultados / "mfa-alta-chromium"
    alta.mkdir(parents=True)
    with zipfile.ZipFile(alta / "trace.zip", "w") as archivo:
        archivo.writestr("resources/a.json", '{"manual_key": "SINTETICA"}')
    (alta / "test-failed-1.png").write_bytes(b"\x89PNG")
    (alta / "error-context.md").write_text("falló")

    oculta = resultados / ".playwright-artifacts-1" / "traces" / "resources"
    oculta.mkdir(parents=True)
    (oculta / "b.json").write_text('{"recovery_codes": []}')

    limpia = resultados / "ventas-chromium"
    limpia.mkdir(parents=True)
    with zipfile.ZipFile(limpia / "trace.zip", "w") as archivo:
        archivo.writestr("resources/c.json", '{"ok": true}')

    (corrida.evidencia / "suite.log").write_text("1 failed")

    informe = corrida.retirar_material_mfa()
    assert informe == {"retirados": [".playwright-artifacts-1", "mfa-alta-chromium"], "quedan": 0}
    assert not alta.exists() and not (resultados / ".playwright-artifacts-1").exists()
    assert (limpia / "trace.zip").exists() and (corrida.evidencia / "suite.log").exists()


def test_e2ecorrida_33b_material_mfa_fuera_de_test_results_se_cuenta_y_no_se_borra(entorno):
    """El material MFA fuera de test-results se cuenta como residuo y no se borra."""
    corrida, _ = _corrida(entorno, "pass")
    corrida.evidencia.mkdir(parents=True)
    registro = corrida.evidencia / "backend.log"
    registro.write_text("otpauth://totp/x")

    informe = corrida.retirar_material_mfa()
    assert informe == {"retirados": [], "quedan": 1}
    assert registro.exists()
