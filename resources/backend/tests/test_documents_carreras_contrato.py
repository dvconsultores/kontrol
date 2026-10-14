"""DOCENV-05/12/13/14 · contrato estático de las carreras de versión documental (OBS-08; Spec 046, apoyo 054).

Las siete carreras de `tests/test_documents_security.py` (las seis de OBS-08 y «subidas a documentos
distintos no se esperan», que también depende del bloqueo de fila) llevan, exactamente ellas, el marcador `solo_postgresql`; ninguna otra prueba del módulo lo lleva,
ninguna otra usa esas primitivas, y el módulo no sustituye ni apaga el analizador de archivos.
"""

from __future__ import annotations

import ast
import os
import re
from pathlib import Path

import pytest

MODULO = Path(__file__).with_name("test_documents_security.py")
CARRERAS = {
    "test_dos_subidas_simultaneas_no_producen_dos_v2",
    "test_la_primera_version_simultanea_tampoco_da_un_500",
    "test_la_peticion_http_que_pierde_la_carrera_recibe_un_409_y_no_un_500",
    "test_tres_subidas_simultaneas_crean_una_sola_version",
    "test_la_misma_clave_en_carrera_devuelve_la_version_ganadora",
    "test_otro_tenant_no_alcanza_un_documento_ajeno_durante_la_carrera",
    "test_subidas_a_documentos_distintos_no_se_esperan",
}
#: Mecanismos de carrera del módulo: los ayudantes de PostgreSQL (`carrera`, `esperar_bloqueados`, `_pid`)
#: y la carrera de tenant (`_subida` sin confirmar en `_FACTORY` + petición ajena en `_en_hilo`), que
#: solo es válida donde el bloqueo es de fila y no de toda la base.
NOMBRES_PG = {"carrera", "esperar_bloqueados", "_pid", "_en_hilo", "_subida"}
TEXTOS_PG = ("pg_backend_pid", "pg_stat_activity")


def _funciones() -> dict[str, tuple[ast.FunctionDef, str]]:
    fuente = MODULO.read_text(encoding="utf-8")
    arbol = ast.parse(fuente)
    return {n.name: (n, ast.get_source_segment(fuente, n) or "") for n in arbol.body if isinstance(n, ast.FunctionDef)}


def _decoradores(fn: ast.FunctionDef) -> list[str]:
    return [ast.unparse(d) for d in fn.decorator_list]


def test_docenv_05_exactamente_las_carreras_llevan_el_marcador_postgresql():
    funciones = _funciones()
    marcadas = {n for n, (fn, _) in funciones.items() if "solo_postgresql" in _decoradores(fn)}
    assert marcadas == CARRERAS, marcadas ^ CARRERAS


def _primitivas_usadas(fn: ast.FunctionDef) -> set[str]:
    """Mecanismos de carrera que usa el código de la función (no su docstring ni sus comentarios)."""
    usadas: set[str] = set()
    for nodo in ast.walk(fn):
        if isinstance(nodo, ast.Name) and nodo.id in NOMBRES_PG:
            usadas.add(nodo.id)
        if isinstance(nodo, ast.Constant) and isinstance(nodo.value, str) and nodo is not getattr(fn.body[0], "value", None):
            usadas.update(t for t in TEXTOS_PG if t in nodo.value)
    return usadas


def test_docenv_12_las_primitivas_de_postgresql_solo_viven_en_las_carreras_marcadas():
    funciones = _funciones()
    for nombre, (fn, _cuerpo) in funciones.items():
        if nombre.startswith("test_") and nombre not in CARRERAS:
            assert not _primitivas_usadas(fn), (nombre, _primitivas_usadas(fn))
    for nombre in CARRERAS:
        assert _primitivas_usadas(funciones[nombre][0]), nombre


def test_docenv_12_el_marcador_depende_del_motor_y_cita_su_autoridad():
    fuente = MODULO.read_text(encoding="utf-8")
    assert 'PG = os.environ.get("KONTROL_TEST_DB_URL", "").startswith("postgresql")' in fuente
    marcador = re.search(r'solo_postgresql = pytest\.mark\.skipif\(\n    not PG, reason="([^"]+)"\)', fuente)
    assert marcador, "el marcador canónico no está donde se espera"
    razon = marcador.group(1)
    assert "FR-046-115" in razon and "P21" in razon and "PostgreSQL" in razon, razon
    pg = os.environ.get("KONTROL_TEST_DB_URL", "").startswith("postgresql")
    import tests.test_documents_security as modulo

    assert modulo.PG is pg


def test_docenv_13_la_cobertura_documental_no_concurrente_sigue_en_los_dos_motores():
    funciones = _funciones()
    pruebas = {n for n in funciones if n.startswith("test_")}
    assert len(pruebas - CARRERAS) >= 25, len(pruebas - CARRERAS)
    for nombre in pruebas - CARRERAS:
        assert "skipif" not in " ".join(_decoradores(funciones[nombre][0])), nombre


def test_docenv_14_el_modulo_no_sustituye_ni_apaga_el_analizador():
    fuente = MODULO.read_text(encoding="utf-8")
    for prohibido in ("set_scanner(", "DisabledScanner(", "KONTROL_DOCUMENT_SCAN", "KONTROL_CLAMSCAN_PATH", "monkeypatch.setenv"):
        assert prohibido not in fuente, prohibido


def test_docenv_15_ningun_rechazo_del_analizador_se_acepta_como_subida():
    funciones = _funciones()
    for nombre, (_fn, cuerpo) in funciones.items():
        if nombre.startswith("test_"):
            assert "status_code in (200, 422)" not in cuerpo and "status_code in (422, 200)" not in cuerpo, nombre


@pytest.mark.skipif(os.environ.get("KONTROL_TEST_DB_URL", "").startswith("postgresql"), reason="la omisión se comprueba en SQLite")
def test_docenv_12_en_sqlite_las_carreras_se_omiten_con_su_razon():
    import tests.test_documents_security as modulo

    for nombre in CARRERAS:
        marcas = [m for m in getattr(getattr(modulo, nombre), "pytestmark", []) if m.name == "skipif"]
        assert marcas and marcas[0].args[0] is True, nombre
        assert "PostgreSQL" in marcas[0].kwargs["reason"], nombre
