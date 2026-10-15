"""O06 · El almacén y los respaldos de las pruebas son por proceso: una raíz propia por `pytest`, la misma para toda la
sesión, invisible a otros procesos y eliminada al terminar (SPEC054 · OBS-06 · HARNESS-SHARED-STORAGE-PATHS).

Antes, `tests/conftest.py` fijaba `KONTROL_STORAGE_PATH` y `KONTROL_BACKUP_PATH` en rutas constantes por máquina al importar:
dos `pytest` compartían el almacén, uno veía los documentos y exportaciones del otro, dos exportaciones del mismo informe en
el mismo segundo se sobrescribían (`report-<clave>-<AAAAMMDDhhmmss>`) y nada se limpiaba nunca (evidencia `d1…d8` de la
delta). Las sondas de `tests/sondas_almacen/` corren en procesos aparte —en serie o a la vez— y cuentan por JSON dónde quedó
su raíz y qué marcadores sintéticos vieron; nunca documentos ni respaldos reales. Aquí se mide el sistema de ficheros, no la
base: las sondas corren sobre SQLite.
"""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from conftest import (
    PREFIJO_DEL_ALMACEN,
    RAIZ_DEL_ALMACEN,
    VARIABLE_DE_RESPALDOS,
    VARIABLE_DEL_ALMACEN,
)

from app.core.config import get_settings
from app.modules.reporting.service import _exports_dir

BACKEND = Path(__file__).resolve().parent.parent
RAIZ = BACKEND.parent.parent
CONFTEST = (BACKEND / "tests" / "conftest.py").read_text(encoding="utf-8")
RUTA_FIJA_ANTIGUA = os.path.join(tempfile.gettempdir(), "kontrol-test-storage")
RESPALDOS_FIJOS_ANTIGUOS = os.path.join(tempfile.gettempdir(), "kontrol-test-backups")


def _entorno(informe: Path, **extra: str) -> dict[str, str]:
    entorno = dict(os.environ)
    entorno.pop("KONTROL_TEST_DB_URL", None)
    entorno.update({"KONTROL_SONDA_INFORME": str(informe), "PYTHONDONTWRITEBYTECODE": "1", **extra})
    return entorno


def _orden(*sondas: str) -> list[str]:
    return [sys.executable, "-m", "pytest", *(f"tests/sondas_almacen/{s}" for s in sondas), "-p", "no:cacheprovider", "-o", "addopts=", "-q"]


def _correr(informe: Path, *sondas: str, **extra: str) -> subprocess.CompletedProcess:
    """Lanza `pytest` sobre unas sondas en un proceso aparte, como una corrida más, y espera a que termine."""
    return subprocess.run(_orden(*sondas), cwd=BACKEND, env=_entorno(informe, **extra), capture_output=True, text=True, timeout=300)


def _lanzar(informe: Path, *sondas: str, **extra: str) -> subprocess.Popen:
    return subprocess.Popen(_orden(*sondas), cwd=BACKEND, env=_entorno(informe, **extra), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def _registros(informe: Path) -> list[dict]:
    return [json.loads(linea) for linea in informe.read_text(encoding="utf-8").splitlines() if linea.strip()]


def _raiz(registro: dict) -> str:
    return os.path.dirname(registro["storage"])


def _es_raiz_propia(registro: dict) -> None:
    raiz = _raiz(registro)
    assert os.path.dirname(raiz) == tempfile.gettempdir() and os.path.basename(raiz).startswith(PREFIJO_DEL_ALMACEN)
    assert registro["storage"] == os.path.join(raiz, "storage") and registro["backup"] == os.path.join(raiz, "backups")
    assert registro["storage"] != RUTA_FIJA_ANTIGUA and registro["backup"] != RESPALDOS_FIJOS_ANTIGUOS


def _misma_raiz_dentro(registro: dict) -> None:
    assert registro["settings_storage"] == registro["storage"] and registro["settings_backup"] == registro["backup"]
    assert registro["documentos"] == os.path.join(registro["storage"], "documents")
    assert registro["exports"] == os.path.join(registro["storage"], "exports")


# ---------------------------------------------------------------- O06-01 / O06-02 · dos procesos a la vez, raíces distintas
def test_o06_01_dos_procesos_a_la_vez_reciben_almacenes_distintos_y_ninguno_es_el_fijo(tmp_path: Path) -> None:
    pa, pb = _lanzar(tmp_path / "a.jsonl", "sonda_a.py"), _lanzar(tmp_path / "b.jsonl", "sonda_b.py")
    salida_a, _ = pa.communicate(timeout=300)
    salida_b, _ = pb.communicate(timeout=300)
    assert pa.returncode == 0 and pb.returncode == 0, salida_a + salida_b
    a, b = _registros(tmp_path / "a.jsonl")[0], _registros(tmp_path / "b.jsonl")[0]
    assert a["pid"] != b["pid"] and a["storage"] != b["storage"] and _raiz(a) != _raiz(b)
    for registro in (a, b):
        _es_raiz_propia(registro)
        # El hijo no hereda el almacén de este proceso aunque viaje en su entorno.
        assert not registro["storage"].startswith(os.environ[VARIABLE_DEL_ALMACEN])
        assert registro["vistos_storage"] == []


def test_o06_02_dos_procesos_a_la_vez_reciben_respaldos_distintos(tmp_path: Path) -> None:
    pa, pb = _lanzar(tmp_path / "a.jsonl", "sonda_a.py"), _lanzar(tmp_path / "b.jsonl", "sonda_b.py")
    pa.communicate(timeout=300)
    pb.communicate(timeout=300)
    assert pa.returncode == 0 and pb.returncode == 0
    a, b = _registros(tmp_path / "a.jsonl")[0], _registros(tmp_path / "b.jsonl")[0]
    assert a["backup"] != b["backup"] and a["backup"] != RESPALDOS_FIJOS_ANTIGUOS
    assert not a["backup"].startswith(os.environ[VARIABLE_DE_RESPALDOS])
    assert a["vistos_backup"] == [] and b["vistos_backup"] == []


# ---------------------------------------------------------------- O06-03 / O06-04 · lo que escribe A no lo ve B
def test_o06_03_el_proceso_b_no_ve_el_documento_sintetico_del_proceso_a(tmp_path: Path) -> None:
    assert _correr(tmp_path / "a.jsonl", "sonda_a.py").returncode == 0
    a = _registros(tmp_path / "a.jsonl")[0]
    assert not os.path.exists(a["marcador"])
    assert _correr(tmp_path / "b.jsonl", "sonda_b.py", KONTROL_SONDA_RUTA_AJENA=a["marcador"]).returncode == 0
    b = _registros(tmp_path / "b.jsonl")[0]
    assert b["ruta_ajena_visible"] is False and b["vistos_storage"] == [] and _raiz(a) != _raiz(b)


def test_o06_04_el_proceso_b_no_ve_el_respaldo_sintetico_del_proceso_a(tmp_path: Path) -> None:
    assert _correr(tmp_path / "a.jsonl", "sonda_a.py").returncode == 0
    a = _registros(tmp_path / "a.jsonl")[0]
    assert not os.path.exists(a["marcador_respaldo"])
    assert _correr(tmp_path / "b.jsonl", "sonda_b.py", KONTROL_SONDA_RUTA_AJENA=a["marcador_respaldo"]).returncode == 0
    b = _registros(tmp_path / "b.jsonl")[0]
    assert b["ruta_ajena_visible"] is False and b["vistos_backup"] == []


# ---------------------------------------------------------------- O06-05 … O06-08 · dentro de un proceso, una sola raíz
def test_o06_05_en_el_proceso_a_configuracion_aplicacion_documentos_y_exportaciones_usan_la_misma_raiz(tmp_path: Path) -> None:
    hecho = _correr(tmp_path / "a.jsonl", "sonda_app.py", "sonda_a.py")
    assert hecho.returncode == 0, hecho.stdout
    app, a = _registros(tmp_path / "a.jsonl")
    assert app["salud"] == 200 and app["settings_tras_app"] == app["storage"]
    for registro in (app, a):
        _misma_raiz_dentro(registro)
    assert app["storage"] == a["storage"] and _raiz(app) == _raiz(a)


def test_o06_06_en_el_proceso_a_los_respaldos_usan_la_misma_raiz_del_proceso(tmp_path: Path) -> None:
    hecho = _correr(tmp_path / "a.jsonl", "sonda_app.py", "sonda_a.py")
    assert hecho.returncode == 0, hecho.stdout
    for registro in _registros(tmp_path / "a.jsonl"):
        assert registro["settings_backup"] == registro["backup"] == os.path.join(_raiz(registro), "backups")


def test_o06_07_el_proceso_b_es_igual_de_consistente_y_distinto_de_a(tmp_path: Path) -> None:
    assert _correr(tmp_path / "a.jsonl", "sonda_a.py").returncode == 0
    assert _correr(tmp_path / "b.jsonl", "sonda_app.py", "sonda_b.py").returncode == 0
    a = _registros(tmp_path / "a.jsonl")[0]
    app_b, b = _registros(tmp_path / "b.jsonl")
    for registro in (app_b, b):
        _misma_raiz_dentro(registro)
        _es_raiz_propia(registro)
    assert app_b["storage"] == b["storage"] and b["storage"] != a["storage"]


def test_o06_08_la_configuracion_se_construye_despues_de_la_inyeccion_del_arnes(request) -> None:
    raiz = request.config.stash[RAIZ_DEL_ALMACEN]
    assert os.environ[VARIABLE_DEL_ALMACEN] == os.path.join(raiz, "storage") == get_settings().storage_path
    assert os.environ[VARIABLE_DE_RESPALDOS] == os.path.join(raiz, "backups") == get_settings().backup_path
    assert str(_exports_dir()) == os.path.join(raiz, "storage", "exports")
    assert os.path.basename(raiz).startswith(PREFIJO_DEL_ALMACEN) and os.path.isdir(raiz)


# ---------------------------------------------------------------- O06-09 … O06-12 · limpieza propia, segura y aunque falle
def test_o06_09_al_terminar_la_sesion_el_almacen_del_proceso_desaparece(tmp_path: Path) -> None:
    assert _correr(tmp_path / "a.jsonl", "sonda_a.py").returncode == 0
    a = _registros(tmp_path / "a.jsonl")[0]
    assert not os.path.exists(a["marcador"]) and not os.path.exists(a["storage"]) and not os.path.exists(_raiz(a))


def test_o06_10_al_terminar_la_sesion_los_respaldos_del_proceso_desaparecen(tmp_path: Path) -> None:
    assert _correr(tmp_path / "a.jsonl", "sonda_a.py").returncode == 0
    a = _registros(tmp_path / "a.jsonl")[0]
    assert not os.path.exists(a["marcador_respaldo"]) and not os.path.exists(a["backup"])


def test_o06_11_la_limpieza_de_un_proceso_no_toca_la_raiz_de_otro(tmp_path: Path) -> None:
    ajena = tempfile.mkdtemp(prefix=PREFIJO_DEL_ALMACEN)
    try:
        marcador = Path(ajena, "storage", "sonda", "marcador-ajeno")
        marcador.parent.mkdir(parents=True)
        marcador.write_text("sintetico", encoding="utf-8")
        hecho = _correr(tmp_path / "b.jsonl", "sonda_b.py", KONTROL_SONDA_RAIZ_AJENA=ajena)
        assert hecho.returncode == 0, hecho.stdout
        b = _registros(tmp_path / "b.jsonl")[0]
        assert b["raiz_ajena_existe"] is True and b["vistos_storage"] == [] and _raiz(b) != ajena
        assert os.path.isdir(ajena) and marcador.is_file() and not os.path.exists(_raiz(b))
    finally:
        import shutil

        shutil.rmtree(ajena)


def test_o06_12_cuando_la_prueba_falla_la_raiz_desaparece_igual(tmp_path: Path) -> None:
    hecho = _correr(tmp_path / "f.jsonl", "sonda_falla.py")
    assert hecho.returncode != 0 and "fallo deliberado de la sonda" in hecho.stdout
    f = _registros(tmp_path / "f.jsonl")[0]
    assert os.path.basename(f["marcador"]).startswith("marcador-")
    assert not os.path.exists(f["marcador"]) and not os.path.exists(f["storage"]) and not os.path.exists(_raiz(f))


# ---------------------------------------------------------------- O06-13 / O06-14 · ni la ruta fija antigua ni el producto
def test_o06_13_la_ruta_fija_antigua_no_se_reutiliza(tmp_path: Path) -> None:
    assert os.environ[VARIABLE_DEL_ALMACEN] != RUTA_FIJA_ANTIGUA and os.environ[VARIABLE_DE_RESPALDOS] != RESPALDOS_FIJOS_ANTIGUOS
    for fichero in ("conftest.py", "test_migrations_offline.py"):
        fuente = (BACKEND / "tests" / fichero).read_text(encoding="utf-8")
        assert 'setdefault("KONTROL_STORAGE_PATH"' not in fuente and 'setdefault("KONTROL_BACKUP_PATH"' not in fuente
    hecho = _correr(tmp_path / "a.jsonl", "sonda_a.py", KONTROL_STORAGE_PATH=RUTA_FIJA_ANTIGUA, KONTROL_BACKUP_PATH=RESPALDOS_FIJOS_ANTIGUOS)
    assert hecho.returncode == 0, hecho.stdout
    a = _registros(tmp_path / "a.jsonl")[0]
    _es_raiz_propia(a)  # ni siquiera si la ruta fija viaja en el entorno del hijo


def test_o06_14_los_valores_por_defecto_del_producto_no_cambian() -> None:
    config = (BACKEND / "app" / "core" / "config.py").read_text(encoding="utf-8")
    assert 'storage_path: str = "/data/storage"' in config and 'backup_path: str = "/data/backups"' in config
    assert "kontrol-test" not in config
    for consumidor in ("app/modules/documents/storage.py", "app/modules/reporting/service.py"):
        assert "get_settings().storage_path" in (BACKEND / consumidor).read_text(encoding="utf-8")


# ---------------------------------------------------------------- O06-15 … O06-17 · las aserciones funcionales y el analizador siguen
def test_o06_15_las_pruebas_documentales_conservan_su_contrato() -> None:
    for fichero in ("test_documents.py", "test_documents_security.py", "test_documents_legacy_import.py"):
        fuente = (BACKEND / "tests" / fichero).read_text(encoding="utf-8")
        assert fuente.count("set_storage(FilesystemStorageProvider(_ROOT))") == 1 and "set_storage(None)" in fuente


def test_o06_16_las_pruebas_de_exportacion_conservan_su_contrato() -> None:
    fuente = (BACKEND / "tests" / "test_reporting.py").read_text(encoding="utf-8")
    assert 'assert export.file_ref and export.file_ref.endswith(".csv")' in fuente
    assert "assert filename == export.file_ref" in fuente
    assert 'assert export.file_ref and export.file_ref.endswith(".pdf")' in fuente
    assert "KONTROL_STORAGE_PATH" not in fuente and "KONTROL_BACKUP_PATH" not in fuente


def test_o06_17_el_contrato_del_analizador_real_no_cambia() -> None:
    scanning = (BACKEND / "app" / "modules" / "documents" / "scanning.py").read_text(encoding="utf-8")
    assert 'details={"reason": "scanner_unavailable"})' in scanning and "timeout: int = 120) -> None:" in scanning
    assert "KONTROL_CLAMSCAN_PATH" not in CONFTEST and "KONTROL_DOCUMENT_SCAN" not in CONFTEST and "KONTROL_CLAMAV_DB" not in CONFTEST


# ---------------------------------------------------------------- O06-18 … O06-20 · OBS-12, prohibiciones y producto 0
def test_o06_18_la_telemetria_de_obs12_distingue_el_residuo_de_corrida_del_almacen_legado(tmp_path: Path) -> None:
    sys.path.insert(0, str(RAIZ / "qa"))
    import suite_tiempos as st

    assert st.MODO_DE_ALMACEN == "PROCESS_ISOLATED" and PREFIJO_DEL_ALMACEN in st.PREFIJOS_EFIMEROS
    assert st.ALMACEN_FIJO_LEGADO == os.path.basename(RUTA_FIJA_ANTIGUA)
    tmp = tmp_path / "tmp"
    tmp.mkdir()
    (tmp / st.ALMACEN_FIJO_LEGADO).mkdir()
    (tmp / f"{PREFIJO_DEL_ALMACEN}huerfano").mkdir()
    residuos = st.residuos(tmp)
    assert residuos["almacen_por_proceso"] == [f"{PREFIJO_DEL_ALMACEN}huerfano"] == residuos["efimeros"]
    assert residuos["almacen_fijo_legado_presente"] is True and residuos["modo_almacen"] == "PROCESS_ISOLATED"


def test_o06_19_el_aislamiento_no_introduce_esperas_ni_omisiones() -> None:
    inicio = CONFTEST.index("Almacén y respaldos aislados")
    bloque = CONFTEST[inicio:CONFTEST.index("def pytest_unconfigure")]
    for prohibido in ("sleep(", "retry", "pytest.skip", "xfail", "timeout", "busy_timeout", "glob(", "kontrol-*"):
        assert prohibido not in bloque, prohibido
    arbol = ast.parse(CONFTEST)
    limpieza = next(n for n in arbol.body if isinstance(n, ast.FunctionDef) and n.name == "pytest_unconfigure")
    llamadas = [ast.unparse(n) for n in ast.walk(limpieza) if isinstance(n, ast.Call) and ast.unparse(n.func) == "shutil.rmtree"]
    assert llamadas == ["shutil.rmtree(raiz)", "shutil.rmtree(almacen)"]  # solo las raíces exactas del stash, nunca un patrón
    orden = _orden("sonda_a.py")
    for prohibido in ("-n", "xdist", "--dist", "--forked", "-x", "--lf", "--ff", "random"):
        assert prohibido not in orden, prohibido  # las sondas corren como una corrida más: en serie y en orden


def test_o06_20_el_aislamiento_no_toca_el_producto() -> None:
    bloque = CONFTEST[CONFTEST.index("Almacén y respaldos aislados"):CONFTEST.index("@contextmanager\ndef volumen_de_instalacion_aislado")]
    assert "import " not in bloque  # solo os, shutil, tempfile, pytest y get_settings, ya importados por el conftest
    for nombre in ("_fijar_almacen", "pytest_configure", "pytest_unconfigure"):
        assert f"def {nombre}(" in bloque
    assert "get_settings.cache_clear()" in bloque and "set_storage" not in bloque and "/data/" not in bloque
    for fichero in ("informar.py", "sonda_a.py", "sonda_b.py", "sonda_app.py", "sonda_export.py", "sonda_falla.py"):
        fuente = (BACKEND / "tests" / "sondas_almacen" / fichero).read_text(encoding="utf-8")
        assert "set_storage" not in fuente and "monkeypatch" not in fuente and "/data/" not in fuente
