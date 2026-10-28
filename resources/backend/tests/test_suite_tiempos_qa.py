"""O12 · Contrato de medición de las certificaciones backend (Spec 054 · OBS-12 · SUITE-DURATION-VARIABILITY).

`qa/suite_tiempos.py` envuelve la orden canónica con telemetría. Aquí se prueba el contrato con dobles —una orden falsa
que imprime lo que pytest imprime, fuentes de `/proc` en texto, relojes inyectados— y nunca la suite real: la duración es
monotónica, el manifiesto es completo y saneado, la anomalía no cambia el veredicto, el almacén fijo no es residuo y nada
de esto toca producto, timeouts, orden de pruebas, paralelismo ni la seguridad del analizador.
"""

from __future__ import annotations

import ast
import json
import os
import re
import socket
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "qa"))

import clamav_qa  # noqa: E402
import suite_tiempos as st  # noqa: E402

RAIZ = Path(__file__).resolve().parents[3]
FUENTE = (RAIZ / "qa" / "suite_tiempos.py").read_text(encoding="utf-8")
SCANNING = (RAIZ / "resources" / "backend" / "app" / "modules" / "documents" / "scanning.py").read_text(encoding="utf-8")
CONFTEST = (RAIZ / "resources" / "backend" / "tests" / "conftest.py").read_text(encoding="utf-8")
HOGAR = "/home/usuaria-sintetica"
IPV4 = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")

LOADAVG = "1.50 0.90 0.70 2/2000 12345\n"
MEMINFO = "MemTotal:       16000000 kB\nMemFree:         1000000 kB\nMemAvailable:    3072000 kB\nSwapTotal:      28000000 kB\nSwapFree:       23000000 kB\n"
STAT = ["cpu  1000 0 500 8000 100 0 50 0 0 0\nctxt 100\nprocs_running 1\n", "cpu  1600 0 800 8400 100 0 50 0 0 0\nctxt 200\nprocs_running 2\n"]
DISKSTATS = ["259 0 nvme0n1 10 0 1000 0 5 0 2000 0 0 0 0\n259 1 nvme0n1p1 10 0 1000 0 5 0 2000 0 0 0 0\n",
             "259 0 nvme0n1 12 0 3000 0 6 0 6000 0 0 0 0\n259 1 nvme0n1p1 12 0 3000 0 6 0 6000 0 0 0 0\n"]
VMSTAT = ["pswpin 100\npswpout 50\n", "pswpin 130\npswpout 50\n"]

SALIDA_PYTEST = (
    "....s.F  [100%]\n"
    "============ slowest durations ============\n"
    "1.50s call     tests/test_a.py::test_uno\n"
    "0.20s setup    tests/test_a.py::test_uno\n"
    "0.80s call     tests/test_b.py::test_dos\n"
    "0.80s call     tests/test_a.py::test_cero\n"
    "0.10s teardown tests/test_b.py::test_dos\n"
    "1 failed, 1698 passed, 1046 skipped in 553.69s (0:09:13)\n"
)


class Alternante:
    """Una fuente de `/proc` que devuelve sus textos por turno (para producir deltas) y repite el último."""

    def __init__(self, *textos: str) -> None:
        self.textos = list(textos)
        self.llamadas = 0

    def __call__(self) -> str:
        texto = self.textos[min(self.llamadas, len(self.textos) - 1)]
        self.llamadas += 1
        return texto


def fuentes_falsas(**sustitutos: st.Lector) -> dict[str, st.Lector]:
    base: dict[str, st.Lector] = {"carga": Alternante(LOADAVG), "memoria": Alternante(MEMINFO), "cpu": Alternante(*STAT),
                                  "disco": Alternante(*DISKSTATS), "paginacion": Alternante(*VMSTAT)}
    base.update(sustitutos)
    return base


def orden_falsa(carpeta: Path, rc: int = 1, salida: str = SALIDA_PYTEST) -> tuple[str, ...]:
    """Un guion que imprime lo que imprimiría pytest (y dos variables del entorno) y sale con `rc`."""
    guion = carpeta / "pytest_falso.py"
    guion.write_text("import os, sys\n"
                     f"sys.stdout.write({salida!r})\n"
                     "print('SCAN=' + os.environ.get('KONTROL_CLAMSCAN_PATH', ''))\n"
                     "print('DOC=' + os.environ.get('KONTROL_DOCUMENT_SCAN', '-'))\n"
                     "print('BD=' + os.environ.get('KONTROL_TEST_DB_URL', '-'))\n"
                     f"sys.exit({rc})\n", encoding="utf-8")
    return (str(guion),)


def estado_falso() -> clamav_qa.Estado:
    return clamav_qa.Estado(motor="1.4.3", bases={"main": {"version": "63"}, "daily": {"version": "28153"}, "bytecode": {"version": "339"}},
                            clamscan="/x/bin/clamscan", db="/x/db")


def corrida(tmp_path: Path, **extra: object) -> tuple[int, dict, Path]:
    tmp = tmp_path / "tmp"
    tmp.mkdir(exist_ok=True)
    argumentos: dict = {"carpeta": tmp_path / "runs", "intervalo": 0.02, "orden": extra.get("orden") or orden_falsa(tmp_path), "cwd": tmp_path,
                        "entorno": {"HOME": HOGAR, "PATH": os.environ.get("PATH", ""), "KONTROL_DOCUMENT_SCAN": "off"},
                        "fuentes": fuentes_falsas(), "tmp": tmp, "asegurar": estado_falso, "decir": lambda _m: None}
    argumentos.update(extra)
    rc = st.ejecutar("sqlite", **argumentos)
    evidencia = next((tmp_path / "runs").glob("*/"))
    return rc, json.loads((evidencia / "manifest.json").read_text(encoding="utf-8")), evidencia


# ---------------------------------------------------------------- O12-01 … O12-07: duración y telemetría

def test_o12_01_la_duracion_es_monotonica_y_el_reloj_de_pared_solo_mide_su_desvio(tmp_path: Path) -> None:
    inicio = datetime(2026, 10, 15, 2, 0, tzinfo=UTC)
    llamadas = {"n": 0}

    def pared() -> datetime:  # el reloj de pared salta una hora en mitad de la corrida
        llamadas["n"] += 1
        return inicio if llamadas["n"] <= 2 else inicio + timedelta(hours=1)  # run_id y pared_inicio; luego salta

    rc, m, _ = corrida(tmp_path, pared=pared)
    assert m["duracion"]["monotonica_s"] < 60  # lo que de verdad tardó el guion falso
    assert m["duracion"]["pared_s"] >= 3600
    assert m["duracion"]["desvio_s"] >= 3500 and m["duracion"]["salto"] is True
    assert m["duracion"]["monotonica_s"] != m["duracion"]["pared_s"]


def test_o12_02_el_manifiesto_registra_la_duracion_total_y_la_identidad_de_la_corrida(tmp_path: Path) -> None:
    rc, m, evidencia = corrida(tmp_path)
    assert m["suite"] == "backend" and m["motor"] == "sqlite" and m["run_id"] == evidencia.name
    assert isinstance(m["duracion"]["monotonica_s"], float) and m["duracion"]["monotonica_s"] >= 0.0
    assert set(m["duracion"]) == {"monotonica_s", "pared_s", "desvio_s", "salto"}
    assert m["inicio_utc"].endswith("+00:00") and m["orden"][-1].endswith("pytest_falso.py")
    assert {"pytest", "perfil", "anfitrion", "recursos", "residuos", "anomalia", "analizador"} <= set(m)
    assert (evidencia / "pytest.txt").is_file() and (evidencia / "host.csv").is_file()


def test_o12_03_la_telemetria_de_carga_esta_saneada_y_es_numerica(tmp_path: Path) -> None:
    _, m, evidencia = corrida(tmp_path)
    cabecera = (evidencia / "host.csv").read_text(encoding="utf-8").splitlines()[0].split(",")
    assert cabecera == list(st.COLUMNAS)
    assert not any(palabra in cabecera for palabra in ("ip", "host", "hostname", "interfaz", "interface", "vpn", "tunel", "usuario", "user"))
    assert m["anfitrion"]["carga"] == {"load1_media": 1.5, "load1_max": 1.5, "load5_max": 0.9}
    assert m["anfitrion"]["cpu"]["util_max_pct"] == 69.2  # Δtotal 1300, Δocioso 400 → 69,2 % ocupado


def test_o12_04_la_telemetria_de_memoria_esta_saneada_sin_identidad_del_equipo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # El intérprete se invoca por un enlace bajo tmp_path: la prueba no depende de si vive bajo el HOME real.
    interprete = tmp_path / "interprete" / "python"
    interprete.parent.mkdir()
    interprete.symlink_to(sys.executable)
    monkeypatch.setattr(st.sys, "executable", str(interprete))
    _, m, evidencia = corrida(tmp_path)
    assert m["anfitrion"]["memoria"] == {"disponible_min_mb": 3000.0, "swap_usada_max_mb": 4883.0, "paginacion_entrante": 30.0, "paginacion_saliente": 0.0}
    texto = (evidencia / "manifest.json").read_text(encoding="utf-8") + (evidencia / "host.csv").read_text(encoding="utf-8")
    assert socket.gethostname() not in texto
    assert HOGAR not in texto and "/home/" not in texto
    assert IPV4.search(texto) is None
    assert not any(clave in texto for clave in ("tunel", "interfaces", "huella", "USER", "LOGNAME"))


def test_o12_05_la_telemetria_de_disco_no_lleva_rutas_ni_secretos(tmp_path: Path) -> None:
    _, m, evidencia = corrida(tmp_path)
    assert set(m["anfitrion"]["disco"]) == {"leido_mb", "escrito_mb"}
    assert m["anfitrion"]["disco"] == {"leido_mb": 1.0, "escrito_mb": 2.0}  # sectores del dispositivo entero, no de la partición
    texto = (evidencia / "manifest.json").read_text(encoding="utf-8")
    assert str(tmp_path) not in texto and str(RAIZ) not in texto
    assert "<repo>" in texto or "<tmp>" in texto or "<home>" in texto


def test_o12_06_el_top_n_es_determinista_y_los_empates_se_ordenan_por_nodo() -> None:
    duraciones = st.parsear_duraciones(SALIDA_PYTEST)
    assert len(duraciones) == 5 and duraciones[0] == {"segundos": 1.5, "fase": "call", "nodo": "tests/test_a.py::test_uno"}
    top = st.top_n(duraciones, 3)
    assert [f["nodo"] for f in top] == ["tests/test_a.py::test_uno", "tests/test_b.py::test_dos", "tests/test_a.py::test_cero"]
    assert top[0] == {"nodo": "tests/test_a.py::test_uno", "segundos": 1.7, "setup": 0.2, "call": 1.5, "teardown": 0.0}
    assert top[1]["segundos"] == 0.9 and top[2]["segundos"] == 0.8
    assert st.top_n(list(reversed(duraciones)), 3) == top
    assert st.top_n(duraciones, 2) == top[:2]
    p = st.perfil(SALIDA_PYTEST, 2)
    assert p["pruebas_listadas"] == 3 and p["suma_listada_s"] == 3.4 and p["por_fase_s"] == {"setup": 0.2, "call": 3.1, "teardown": 0.1}


def test_o12_07_una_fuente_de_metricas_ausente_no_falsea_la_duracion_ni_el_veredicto(tmp_path: Path) -> None:
    def sin_disco() -> str:
        raise OSError("sin /proc/diskstats")

    rc, m, _ = corrida(tmp_path, fuentes=fuentes_falsas(disco=sin_disco))
    assert rc == 1 and m["pytest"]["rc"] == 1
    assert m["anfitrion"]["disponible"]["disco"] is False and m["anfitrion"]["disponible"]["carga"] is True
    assert m["anfitrion"]["disco"] == {"leido_mb": None, "escrito_mb": None}
    assert m["anfitrion"]["carga"]["load1_max"] == 1.5
    assert isinstance(m["duracion"]["monotonica_s"], float)


# ---------------------------------------------------------------- O12-08 … O12-12: analizador, residuos, anomalía

def test_o12_08_los_metadatos_del_analizador_estan_presentes_y_el_analizador_nunca_se_apaga(tmp_path: Path) -> None:
    rc, m, evidencia = corrida(tmp_path, con_analizador=True)
    assert m["analizador"] == {"exigido": True, "habilitado": True, "motor": "1.4.3",
                               "bases": {"main": {"version": "63"}, "daily": {"version": "28153"}, "bytecode": {"version": "339"}}}
    salida = (evidencia / "pytest.txt").read_text(encoding="utf-8")
    assert "SCAN=/x/bin/clamscan" in salida and "DOC=-" in salida  # KONTROL_DOCUMENT_SCAN=off heredado no llega a pytest
    env, anotacion = st.entorno_de_pytest("postgres", con_analizador=False, base={"KONTROL_DOCUMENT_SCAN": "off"})
    assert "KONTROL_DOCUMENT_SCAN" not in env and env["KONTROL_TEST_DB_URL"] == st.MOTORES["postgres"]
    assert env["PYTHONDONTWRITEBYTECODE"] == "1" and anotacion == {"exigido": False, "habilitado": False}


def test_o12_09_el_almacen_fijo_legado_se_anota_aparte_y_no_como_residuo(tmp_path: Path) -> None:
    tmp = tmp_path / "tmp"
    tmp.mkdir()
    (tmp / st.ALMACEN_FIJO_LEGADO).mkdir()
    (tmp / "kontrol-test-sqlite-almacenes-abc").mkdir()
    assert st.residuos(tmp) == {"modo_almacen": "PROCESS_ISOLATED", "efimeros": ["kontrol-test-sqlite-almacenes-abc"], "almacen_por_proceso": [],
                                "almacen_fijo_legado_presente": True}
    rc, m, _ = corrida(tmp_path, tmp=tmp)
    assert m["residuos"]["efimeros"] == ["kontrol-test-sqlite-almacenes-abc"] and m["residuos"]["almacen_fijo_legado_presente"] is True
    assert rc == 1 and m["pytest"]["rc"] == 1  # el legado no cambia el veredicto (que aquí es el de la orden falsa)


def test_o12_10_los_directorios_efimeros_siguen_detectandose_incluido_el_almacen_por_proceso(tmp_path: Path) -> None:
    tmp = tmp_path / "tmp"
    tmp.mkdir()
    vacio = {"modo_almacen": "PROCESS_ISOLATED", "efimeros": [], "almacen_por_proceso": [], "almacen_fijo_legado_presente": False}
    assert st.residuos(tmp) == vacio
    for nombre in ("kontrol-test-license-xyz", "kontrol-test-sqlite-uom-1", "kontrol-test-almacen-ab12", "otra-cosa"):
        (tmp / nombre).mkdir()
    assert st.residuos(tmp)["efimeros"] == ["kontrol-test-almacen-ab12", "kontrol-test-license-xyz", "kontrol-test-sqlite-uom-1"]
    assert st.residuos(tmp)["almacen_por_proceso"] == ["kontrol-test-almacen-ab12"]
    assert st.residuos(tmp_path / "no-existe") == vacio


def _manifiesto_previo(carpeta: Path, motor: str, segundos: float, completo: bool = True) -> None:
    corrida_previa = carpeta / f"r20261001t000000p1n{len(list(carpeta.glob('*'))):06d}"
    corrida_previa.mkdir(parents=True)
    (corrida_previa / "manifest.json").write_text(json.dumps({"motor": motor, "pytest": {"completo": completo},
                                                              "duracion": {"monotonica_s": segundos}}), encoding="utf-8")


def test_o12_11_una_duracion_anomala_no_convierte_un_verde_en_rojo(tmp_path: Path) -> None:
    carpeta = tmp_path / "runs"
    for segundos in (100.0, 110.0, 105.0):
        _manifiesto_previo(carpeta, "sqlite", segundos)
    _manifiesto_previo(carpeta, "postgres", 1.0)  # otro motor: no es referencia
    _manifiesto_previo(carpeta, "sqlite", 1.0, completo=False)  # sin resumen: no es referencia
    valores = iter([0.0, 0.0, 0.0, 1000.0, 1000.0, 1000.0])
    rc, m, _ = corrida(tmp_path, orden=orden_falsa(tmp_path, rc=0), monotonico=lambda: next(valores, 1000.0), intervalo=1000.0)
    assert rc == 0 and m["pytest"]["rc"] == 0
    assert m["duracion"]["monotonica_s"] == 1000.0
    assert m["anomalia"]["indicador"] == "ANOMALIA" and m["anomalia"]["referencias"] == 3
    assert m["anomalia"]["mediana_s"] == 105.0 and m["anomalia"]["razon"] == 9.52 and m["anomalia"]["umbral_duro"] is None


def test_o12_12_el_indicador_de_anomalia_no_altera_el_veredicto_de_pytest(tmp_path: Path) -> None:
    rc, m, _ = corrida(tmp_path)  # la orden falsa sale 1 con duración normal
    assert rc == 1 and m["anomalia"]["indicador"] == "SIN_REFERENCIA"
    assert st.anomalia(600.0, [581.0, 610.0]) ["indicador"] == "SIN_REFERENCIA"
    normal = st.anomalia(610.0, [581.6, 601.5, 587.0])
    assert normal["indicador"] == "NORMAL" and normal["razon"] == 1.04 and normal["umbral_duro"] is None
    atipica = st.anomalia(2946.0, [581.6, 601.5, 587.0])
    assert atipica["indicador"] == "ANOMALIA" and atipica["razon"] == 5.02 and "mediana" in atipica["motivo"]
    assert st.RAZON_DE_ANOMALIA == 2.0 and st.MINIMO_DE_REFERENCIAS == 3
    with pytest.raises(ValueError):
        st.ejecutar("mysql")


# ---------------------------------------------------------------- O12-13 … O12-20: nada más cambia (contratos estáticos)

def test_o12_13_ningun_timeout_cambia() -> None:
    assert "timeout: int = 120) -> None:" in SCANNING  # el techo del subproceso clamscan, intacto
    assert "timeout=" not in FUENTE  # la medición no impone techos a la suite
    assert "subprocess.run(list(orden_final), cwd=cwd, env=env, stdout=salida, stderr=subprocess.STDOUT, check=False)" in FUENTE


def test_o12_14_el_busy_timeout_de_sqlite_no_cambia() -> None:
    assert "busy_timeout" not in CONFTEST and "PRAGMA" not in CONFTEST.replace("No fija `timeout`, `isolation_level` ni `PRAGMA` alguno", "")
    assert "busy_timeout" not in FUENTE and "PRAGMA" not in FUENTE and "isolation_level" not in FUENTE


def test_o12_15_la_seguridad_del_analizador_no_cambia() -> None:
    assert 'details={"reason": "scanner_unavailable"})' in SCANNING and "SCAN_FAILED" in SCANNING
    assert FUENTE.count("KONTROL_DOCUMENT_SCAN") == 1 and 'entorno.pop("KONTROL_DOCUMENT_SCAN", None)' in FUENTE
    assert "DisabledScanner" not in FUENTE and "set_scanner" not in FUENTE


def test_o12_16_la_herramienta_no_importa_ni_escribe_producto(tmp_path: Path) -> None:
    arbol = ast.parse(FUENTE)
    modulos = {n.names[0].name.split(".")[0] for n in ast.walk(arbol) if isinstance(n, ast.Import)}
    modulos |= {(n.module or "").split(".")[0] for n in ast.walk(arbol) if isinstance(n, ast.ImportFrom)}
    assert "app" not in modulos and "sqlalchemy" not in modulos and "tests" not in modulos
    orden = orden_falsa(tmp_path)
    (tmp_path / "tmp").mkdir()
    antes = {p.relative_to(tmp_path) for p in tmp_path.rglob("*")}
    _, _, evidencia = corrida(tmp_path, orden=orden)
    nuevos = {p.relative_to(tmp_path) for p in tmp_path.rglob("*")} - antes
    assert all(str(p).startswith("runs") for p in nuevos), nuevos
    assert {p.name for p in evidencia.iterdir()} == {"manifest.json", "pytest.txt", "host.csv"}


def test_o12_17_la_orden_canonica_no_reordena_las_pruebas() -> None:
    assert st.ORDEN_PYTEST == ("-m", "pytest", "tests", "-o", "addopts=", "-q", "--durations=0", "-p", "no:cacheprovider")
    for prohibido in ("random", "--reverse", "-k", "--lf", "--ff", "--sw", "--order", "shuffle", "-x"):
        assert prohibido not in st.ORDEN_PYTEST
    assert "random" not in FUENTE and "shuffle" not in FUENTE


def test_o12_18_no_hay_ejecucion_paralela() -> None:
    for prohibido in ("-n", "xdist", "--dist", "--forked", "--numprocesses", "parallel", "multiprocessing", "ProcessPool"):
        assert prohibido not in st.ORDEN_PYTEST and prohibido not in FUENTE, prohibido


def test_o12_19_los_recuentos_de_pytest_se_conservan_tal_cual(tmp_path: Path) -> None:
    assert st.parsear_resumen("1 failed, 1698 passed, 1046 skipped in 553.69s (0:09:13)\n") == {
        "completo": True, "passed": 1698, "failed": 1, "skipped": 1046, "errors": 0, "segundos": 553.69}
    assert st.parsear_resumen("2719 passed, 26 skipped in 1324.46s (0:22:04)\n")["failed"] == 0
    assert st.parsear_resumen("1699 passed, 1046 skipped, 3 warnings in 601.5s\n")["skipped"] == 1046
    assert st.parsear_resumen("....  [100%]\n") == {"completo": False, "passed": None, "failed": None, "skipped": None, "errors": None, "segundos": None}
    _, m, _ = corrida(tmp_path)
    assert (m["pytest"]["passed"], m["pytest"]["failed"], m["pytest"]["skipped"], m["pytest"]["rc"]) == (1698, 1, 1046, 1)
    assert m["pytest"]["segundos"] == 553.69 and m["pytest"]["completo"] is True


def test_o12_20_la_certificacion_e2e_no_depende_de_la_telemetria() -> None:
    for nombre in ("e2e_corrida.py", "e2e-run.py", "e2e_base.py", "clamav_qa.py"):
        assert "suite_tiempos" not in (RAIZ / "qa" / nombre).read_text(encoding="utf-8"), nombre
    assert "sleep(" not in FUENTE and "retry" not in FUENTE.lower() and "xfail" not in FUENTE and "pytest.skip" not in FUENTE and "skipif" not in FUENTE
    assert "qa/backend-runs/" in (RAIZ / ".gitignore").read_text(encoding="utf-8")
    assert "qa/suite_tiempos.py --motor sqlite|postgres" in (RAIZ / ".claude" / "CLAUDE.md").read_text(encoding="utf-8")
    assert time.monotonic.__name__ == "monotonic" and "time.monotonic" in FUENTE and "time.time()" not in FUENTE


def test_o12_21_el_resumen_dice_si_hubo_salto_de_reloj(tmp_path: Path) -> None:
    inicio = datetime(2026, 10, 15, 2, 0, tzinfo=UTC)
    llamadas = {"n": 0}

    def pared() -> datetime:  # el reloj de pared salta una hora en mitad de la corrida
        llamadas["n"] += 1
        return inicio if llamadas["n"] <= 2 else inicio + timedelta(hours=1)  # run_id y pared_inicio; luego salta

    mensajes: list[str] = []
    corrida(tmp_path, pared=pared, decir=mensajes.append)
    assert "salto de reloj: SÍ" in mensajes[-1]
    assert "la duración monotónica sigue siendo válida" in mensajes[-1]
    assert "anomalía:" in mensajes[-1]


def test_o12_22_sin_salto_el_resumen_lo_dice_tambien(tmp_path: Path) -> None:
    mensajes: list[str] = []
    corrida(tmp_path, pared=lambda: datetime(2026, 10, 15, 2, 0, tzinfo=UTC), decir=mensajes.append)
    assert "salto de reloj: NO" in mensajes[-1]
    assert "suspensión" not in mensajes[-1]
