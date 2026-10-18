"""OBS-07 · Aislamiento de pruebas del módulo tests/test_license_sync_client.py.

El módulo CSYNC compartía un mundo de módulo y sus pruebas dependían del estado de las anteriores;
aquí se prueba que cada una parte de cero.
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
MODULO = "tests/test_license_sync_client.py"


def _entorno() -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def _pytest(nodos: list[str], *extra: str) -> subprocess.CompletedProcess[str]:
    comando = [sys.executable, "-m", "pytest", *nodos, "-p", "no:cacheprovider", "-o", "addopts=", "-q", *extra]
    return subprocess.run(comando, cwd=BACKEND, env=_entorno(), capture_output=True, text=True, timeout=300)


def test_csync_aisl_01_la_prueba_csync_02_pasa_sola():
    nodo = "tests/test_license_sync_client.py::test_csync_02_la_licencia_emitida_por_la_autoridad_llega_autenticada_y_pasa_por_la_importacion"
    resultado = _pytest([nodo])
    assert resultado.returncode == 0, f"stdout:\n{resultado.stdout}\nstderr:\n{resultado.stderr}"
    assert "1 passed" in resultado.stdout, f"stdout:\n{resultado.stdout}\nstderr:\n{resultado.stderr}"


def test_csync_aisl_02_el_modulo_pasa_en_orden_inverso():
    recoleccion = _pytest([MODULO], "--collect-only")
    lineas = [linea.strip() for linea in recoleccion.stdout.splitlines() if "::" in linea]
    assert len(lineas) == 13, f"stdout:\n{recoleccion.stdout}\nstderr:\n{recoleccion.stderr}"
    nodos = list(reversed(lineas))
    resultado = _pytest(nodos, "-vv")
    ejecutadas = [linea.split(" ")[0] for linea in resultado.stdout.splitlines() if " PASSED" in linea]
    assert ejecutadas == nodos, f"orden ejecutado:\n{ejecutadas}"
    assert ejecutadas[0].endswith("test_csync_13_el_ayudante_local_exporta_solo_la_clave_publica_de_la_instalacion")
    assert ejecutadas[-1].endswith("test_csync_01_configurar_la_autoridad_por_http_local_en_qa_y_sin_licencia_el_sync_responde_no_license")
    assert resultado.returncode == 0, f"stdout:\n{resultado.stdout}\nstderr:\n{resultado.stderr}"
    assert "13 passed" in resultado.stdout, f"stdout:\n{resultado.stdout}\nstderr:\n{resultado.stderr}"


def test_csync_aisl_03_contrato_estatico():
    ruta = BACKEND / MODULO
    fuente = ruta.read_text(encoding="utf-8")
    arbol = ast.parse(fuente)

    funciones = {n.name: n for n in arbol.body if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)}
    assert "_mundo" in funciones

    decoradores_mundo = funciones["_mundo"].decorator_list
    for decorador in decoradores_mundo:
        if isinstance(decorador, ast.Call) and isinstance(decorador.func, ast.Attribute):
            if decorador.func.attr == "fixture":
                palabras_clave = {k.arg: ast.literal_eval(k.value) for k in decorador.keywords if k.arg is not None}
                assert palabras_clave.get("autouse") is True
                assert "scope" not in palabras_clave or palabras_clave["scope"] == "function"

    assert "_aplicaciones" in funciones
    aplicaciones = funciones["_aplicaciones"]
    for decorador in aplicaciones.decorator_list:
        if isinstance(decorador, ast.Call) and isinstance(decorador.func, ast.Attribute):
            if decorador.func.attr == "fixture":
                palabras_clave = {k.arg: ast.literal_eval(k.value) for k in decorador.keywords if k.arg is not None}
                assert palabras_clave.get("scope") == "module"
                assert palabras_clave.get("autouse") is True

    for nombre in ("_configura_autoridad", "_importa_licencia", "_sincronizacion_previa"):
        assert nombre in funciones

    primeras = {
        "_configura_autoridad": ["test_csync_02_la_licencia_emitida_por_la_autoridad_llega_autenticada_y_pasa_por_la_importacion",
                                 "test_csync_03_lo_que_viaja_son_los_bytes_hasheados_y_ninguna_clave_privada",
                                 "test_csync_05_si_el_transporte_falla_no_hay_retroceso_a_un_sync_anonimo_y_el_siguiente_intento_pide_otro_desafio",
                                 "test_csync_11_en_produccion_la_autoridad_debe_ir_por_https",
                                 "test_csync_12_sin_clave_privada_de_instalacion_el_sync_falla_cerrado_antes_de_contactar"],
        "_importa_licencia": ["test_csync_06_si_la_autoridad_rechaza_la_prueba_el_cliente_lo_anota_y_no_toca_el_estado",
                              "test_csync_07_un_artefacto_de_otra_instalacion_o_manipulado_no_entra_aunque_llegue_autenticado",
                              "test_csync_08_una_respuesta_fuera_de_contrato_se_rechaza",
                              "test_csync_10_en_solo_lectura_la_renovacion_por_sync_sigue_siendo_posible"],
        "_sincronizacion_previa": ["test_csync_04_la_sincronizacion_es_idempotente_por_dia_sin_contactar_de_nuevo"],
    }

    def primera_llamada(funcion: ast.FunctionDef | ast.AsyncFunctionDef) -> str | None:
        if not funcion.body:
            return None
        primera = funcion.body[0]
        if isinstance(primera, ast.Expr) and isinstance(primera.value, ast.Call):
            if isinstance(primera.value.func, ast.Name):
                return primera.value.func.id
        return None

    for prefijo_ayudante, nombres in primeras.items():
        for nombre in nombres:
            assert nombre in funciones, f"Falta la prueba {nombre}"
            assert primera_llamada(funciones[nombre]) == prefijo_ayudante, f"{nombre} no empieza por {prefijo_ayudante}"

    ayudantes = {"_configura_autoridad", "_importa_licencia", "_sincronizacion_previa"}
    sin_ayudante = [
        "test_csync_01_configurar_la_autoridad_por_http_local_en_qa_y_sin_licencia_el_sync_responde_no_license",
        "test_csync_09_la_ruta_local_sigue_exigiendo_sesion_y_license_create",
        "test_csync_13_el_ayudante_local_exporta_solo_la_clave_publica_de_la_instalacion",
    ]
    for nombre in sin_ayudante:
        assert nombre in funciones, f"Falta la prueba {nombre}"
        llamadas: list[str] = []
        for sentencia in ast.walk(funciones[nombre]):
            if isinstance(sentencia, ast.Call):
                if isinstance(sentencia.func, ast.Name):
                    llamadas.append(sentencia.func.id)
                elif isinstance(sentencia.func, ast.Attribute):
                    llamadas.append(sentencia.func.attr)
        assert not any(llamada in ayudantes for llamada in llamadas), f"{nombre} llama a un ayudante de precondición"

    for nombre in ("test_csync_01_configurar_la_autoridad_por_http_local_en_qa_y_sin_licencia_el_sync_responde_no_license",
                   "test_csync_02_la_licencia_emitida_por_la_autoridad_llega_autenticada_y_pasa_por_la_importacion",
                   "test_csync_03_lo_que_viaja_son_los_bytes_hasheados_y_ninguna_clave_privada",
                   "test_csync_04_la_sincronizacion_es_idempotente_por_dia_sin_contactar_de_nuevo",
                   "test_csync_05_si_el_transporte_falla_no_hay_retroceso_a_un_sync_anonimo_y_el_siguiente_intento_pide_otro_desafio",
                   "test_csync_06_si_la_autoridad_rechaza_la_prueba_el_cliente_lo_anota_y_no_toca_el_estado",
                   "test_csync_07_un_artefacto_de_otra_instalacion_o_manipulado_no_entra_aunque_llegue_autenticado",
                   "test_csync_08_una_respuesta_fuera_de_contrato_se_rechaza",
                   "test_csync_09_la_ruta_local_sigue_exigiendo_sesion_y_license_create",
                   "test_csync_10_en_solo_lectura_la_renovacion_por_sync_sigue_siendo_posible",
                   "test_csync_11_en_produccion_la_autoridad_debe_ir_por_https",
                   "test_csync_12_sin_clave_privada_de_instalacion_el_sync_falla_cerrado_antes_de_contactar",
                   "test_csync_13_el_ayudante_local_exporta_solo_la_clave_publica_de_la_instalacion"):
        assert nombre in funciones, f"Falta la prueba {nombre}"
        decoradores = [ast.unparse(d) for d in funciones[nombre].decorator_list]
        assert not any(marcador in decorador for marcador in ("order", "dependency", "depends") for decorador in decoradores)

    for palabra in ("sleep(", "retry", "pytest.skip", "xfail", "flaky", "reruns"):
        assert palabra not in fuente, f"Texto prohibido encontrado: {palabra}"

    assert "assert \"PRIVATE\" not in salida" in fuente
