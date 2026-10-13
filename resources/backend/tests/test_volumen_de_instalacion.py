"""TV · El volumen de instalación de las pruebas es efímero: una raíz por proceso de `pytest`, un volumen
por módulo, nada compartido y nada que sobreviva (SPEC054 · TEST-VOLUMEN-DE-INSTALACION-COMPARTIDO;
FR-TV-001…007, 011, 012, 014).

Antes, `tests/conftest.py` fijaba `KONTROL_INSTALLATION_VOLUME_PATH` en una ruta constante por máquina y
dos `pytest` se reescribían `installation_private_key.pem`: la sincronización firmaba con la clave ajena y
la Autoridad Central respondía `SYNC_AUTH_INVALID` (evidencia `parallel-processes.md` del delta).

Las sondas de `tests/sondas_volumen/` corren en procesos aparte —en serie o a la vez— y cuentan por JSON
dónde quedó su volumen y la huella sha256 truncada de su clave sintética; nunca el contenido. Aquí se mide
el sistema de ficheros, no la base: las sondas corren sobre SQLite. Las comprobaciones en proceso del
gestor de contexto están en `test_volumen_de_instalacion_ambito.py`.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from conftest import PREFIJO_DEL_VOLUMEN, VARIABLE_DEL_VOLUMEN

BACKEND = Path(__file__).resolve().parent.parent
RUTA_FIJA_ANTIGUA = PREFIJO_DEL_VOLUMEN.rstrip("-")


def _entorno(informe: Path, **extra: str) -> dict[str, str]:
    entorno = dict(os.environ)
    entorno.pop("KONTROL_TEST_DB_URL", None)
    entorno.update({"KONTROL_SONDA_INFORME": str(informe), "PYTHONDONTWRITEBYTECODE": "1", **extra})
    return entorno


def _orden(*sondas: str) -> list[str]:
    return [sys.executable, "-m", "pytest", *(f"tests/sondas_volumen/{s}" for s in sondas), "-p", "no:cacheprovider", "-q"]


def _correr(informe: Path, *sondas: str, **extra: str) -> subprocess.CompletedProcess:
    """Lanza `pytest` sobre unas sondas en un proceso aparte, como una corrida más, y espera a que termine."""
    return subprocess.run(_orden(*sondas), cwd=BACKEND, env=_entorno(informe, **extra), capture_output=True, text=True, timeout=300)


def _lanzar(informe: Path, *sondas: str) -> subprocess.Popen:
    return subprocess.Popen(_orden(*sondas), cwd=BACKEND, env=_entorno(informe), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def _registros(informe: Path) -> list[dict]:
    return [json.loads(linea) for linea in informe.read_text(encoding="utf-8").splitlines() if linea.strip()]


def _raiz(registro: dict) -> str:
    return os.path.dirname(registro["volumen"])


def _sin_material_de_clave(*textos: str) -> None:
    for texto in textos:
        assert "PRIVATE KEY" not in texto and "-----BEGIN" not in texto


# ---------------------------------------------------------------- TV-01 / TV-02 · raíz propia por proceso, vacía al empezar
def test_tv_01_dos_procesos_consecutivos_reciben_raices_distintas_y_ninguna_es_fija(tmp_path):
    primero = _correr(tmp_path / "a.jsonl", "sonda_a.py")
    segundo = _correr(tmp_path / "b.jsonl", "sonda_a.py")
    assert primero.returncode == 0 and segundo.returncode == 0, primero.stdout + segundo.stdout
    a, b = _registros(tmp_path / "a.jsonl")[0], _registros(tmp_path / "b.jsonl")[0]
    assert a["volumen"] != b["volumen"] and _raiz(a) != _raiz(b)
    for registro in (a, b):
        assert os.path.dirname(_raiz(registro)) == tempfile.gettempdir()
        assert os.path.basename(_raiz(registro)).startswith(PREFIJO_DEL_VOLUMEN)
        assert os.path.basename(_raiz(registro)) != RUTA_FIJA_ANTIGUA
        # El hijo no hereda el volumen de este proceso aunque viaje en su entorno.
        assert not registro["volumen"].startswith(os.environ[VARIABLE_DEL_VOLUMEN])
        assert registro["settings"] == registro["volumen"]


def test_tv_02_el_volumen_de_un_modulo_empieza_vacio_y_la_clave_cae_dentro(tmp_path):
    hecho = _correr(tmp_path / "a.jsonl", "sonda_a.py")
    assert hecho.returncode == 0, hecho.stdout
    a = _registros(tmp_path / "a.jsonl")[0]
    assert a["ficheros_al_empezar"] == [] and a["clave_dentro"] is True and a["modo"] == "0o600"


# ---------------------------------------------------------------- TV-03 / TV-08 · la sesión B no ve nada de la sesión A; A no deja nada
def test_tv_03_la_sesion_b_no_ve_la_clave_de_la_sesion_a_y_a_no_deja_rastro(tmp_path):
    assert _correr(tmp_path / "a.jsonl", "sonda_a.py").returncode == 0
    a = _registros(tmp_path / "a.jsonl")[0]
    assert not os.path.exists(a["clave"]) and not os.path.exists(a["volumen"]) and not os.path.exists(_raiz(a))
    assert _correr(tmp_path / "b.jsonl", "sonda_a.py", KONTROL_SONDA_RUTA_AJENA=a["clave"]).returncode == 0
    b = _registros(tmp_path / "b.jsonl")[0]
    assert b["ruta_ajena_visible"] is False and b["ficheros_al_empezar"] == [] and b["huella"] != a["huella"]


# ---------------------------------------------------------------- TV-04 · dos procesos a la vez
def test_tv_04_dos_procesos_a_la_vez_escriben_claves_distintas_y_ninguno_pisa_la_del_otro(tmp_path):
    pa, pb = _lanzar(tmp_path / "a.jsonl", "sonda_a.py"), _lanzar(tmp_path / "b.jsonl", "sonda_b.py")
    salida_a, error_a = pa.communicate(timeout=300)
    salida_b, error_b = pb.communicate(timeout=300)
    assert pa.returncode == 0 and pb.returncode == 0, salida_a + salida_b
    a, b = _registros(tmp_path / "a.jsonl"), _registros(tmp_path / "b.jsonl")
    assert a[0]["pid"] != b[0]["pid"] and a[0]["volumen"] != b[0]["volumen"] and _raiz(a[0]) != _raiz(b[0])
    assert a[0]["huella"] != b[0]["huella"]
    # Cada proceso relee exactamente la clave que escribió: nadie se la cambió por debajo.
    assert a[1]["huella"] == a[0]["huella"] and b[1]["huella"] == b[0]["huella"]
    for registro in (a[0], b[0]):
        assert registro["clave_dentro"] is True and registro["modo"] == "0o600" and not os.path.exists(registro["volumen"])
    _sin_material_de_clave(salida_a, error_a, salida_b, error_b)


# ---------------------------------------------------------------- TV-09 · limpieza aunque la prueba falle
def test_tv_09_cuando_la_prueba_falla_el_volumen_y_la_raiz_desaparecen_igual(tmp_path):
    hecho = _correr(tmp_path / "f.jsonl", "sonda_falla.py")
    assert hecho.returncode != 0 and "fallo deliberado de la sonda" in hecho.stdout
    f = _registros(tmp_path / "f.jsonl")[0]
    assert f["clave_dentro"] is True
    assert not os.path.exists(f["clave"]) and not os.path.exists(f["volumen"]) and not os.path.exists(_raiz(f))
    _sin_material_de_clave(hecho.stdout, hecho.stderr, (tmp_path / "f.jsonl").read_text(encoding="utf-8"))


# ---------------------------------------------------------------- TV-11 · ningún material de clave en la salida ni en el informe
def test_tv_11_las_sondas_no_cuentan_mas_que_huellas(tmp_path):
    hecho = _correr(tmp_path / "a.jsonl", "sonda_a.py")
    informe = (tmp_path / "a.jsonl").read_text(encoding="utf-8")
    _sin_material_de_clave(hecho.stdout, hecho.stderr, informe)
    for registro in _registros(tmp_path / "a.jsonl"):
        assert re.fullmatch(r"[0-9a-f]{16}", registro["huella"])


# ---------------------------------------------------------------- TV-12 · independencia del orden
def test_tv_12_el_resultado_no_depende_del_orden_de_los_modulos(tmp_path):
    ab = _correr(tmp_path / "ab.jsonl", "sonda_a.py", "sonda_b.py")
    ba = _correr(tmp_path / "ba.jsonl", "sonda_b.py", "sonda_a.py")
    assert ab.returncode == 0 and ba.returncode == 0, ab.stdout + ba.stdout
    for informe in (tmp_path / "ab.jsonl", tmp_path / "ba.jsonl"):
        escrituras = {r["modulo"]: r for r in _registros(informe) if "ficheros_al_empezar" in r}
        assert set(escrituras) == {"sonda_a", "sonda_b"}
        assert all(r["ficheros_al_empezar"] == [] and r["clave_dentro"] is True for r in escrituras.values())
        # Dentro de un proceso cada módulo tiene su volumen, hijo de la misma raíz.
        assert escrituras["sonda_a"]["volumen"] != escrituras["sonda_b"]["volumen"]
        assert _raiz(escrituras["sonda_a"]) == _raiz(escrituras["sonda_b"])
        assert escrituras["sonda_a"]["huella"] != escrituras["sonda_b"]["huella"]


# ---------------------------------------------------------------- TV-23 · nada de esto se sostiene reordenando pruebas ni con una ruta fija
def test_tv_23_sin_reordenacion_de_pruebas_ni_ruta_fija_en_el_arnes():
    conftest = (BACKEND / "tests" / "conftest.py").read_text(encoding="utf-8")
    assert "pytest_collection_modifyitems" not in conftest
    assert f'"{RUTA_FIJA_ANTIGUA}"' not in conftest
    pyproject = (BACKEND / "pyproject.toml").read_text(encoding="utf-8")
    assert "pytest-order" not in pyproject and "pytest-randomly" not in pyproject
    fuentes = "\n".join(p.read_text(encoding="utf-8") for p in (BACKEND / "tests").rglob("*.py"))
    assert re.search(r"mark\.order\b", fuentes) is None
