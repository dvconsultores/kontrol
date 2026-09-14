"""Spec 047 · mensajes por clave y parámetros (FR-047-050..053, OQ-047-02)."""

from __future__ import annotations

import ast
import pathlib

import pytest

from app.modules.notifications import catalogo
from app.modules.notifications.messages import (
    CATALOGOS,
    IDIOMAS,
    MESSAGE_KEY_UNKNOWN,
    MESSAGE_PARAM_INVALID,
    MESSAGE_PARAM_MISSING,
    MensajeInvalido,
    renderizar,
    texto,
    validar,
)

CLAVE = "approval.step_opened.notification"
PARAMS = {"process_type": "COMPRAS", "document_type": "PurchaseOrder", "level_order": 2}
MODULOS = pathlib.Path(__file__).resolve().parents[1] / "app" / "modules"


def test_clave_conocida_con_sus_parametros_da_el_texto_en_espanol():
    r = renderizar(CLAVE, PARAMS)
    assert r.render_error is None
    assert r.text == "Hay una aprobación de COMPRAS pendiente en el nivel 2."


def test_una_clave_desconocida_es_un_error_controlado_y_nunca_la_clave_cruda():
    r = renderizar("approval.no_existe", PARAMS)
    assert r.text is None
    assert r.render_error == MESSAGE_KEY_UNKNOWN


def test_un_parametro_faltante_es_un_error_controlado():
    r = renderizar(CLAVE, {"process_type": "COMPRAS"})
    assert (r.text, r.render_error) == (None, MESSAGE_PARAM_MISSING)


def test_un_parametro_sobrante_se_ignora_siempre_igual():
    assert renderizar(CLAVE, {**PARAMS, "importe": "1000.00"}) == renderizar(CLAVE, PARAMS)


def test_un_parametro_compuesto_se_rechaza():
    assert renderizar(CLAVE, {**PARAMS, "process_type": {"a": 1}}).render_error == MESSAGE_PARAM_INVALID


def test_un_parametro_no_ejecuta_ni_expande_nada():
    r = renderizar(CLAVE, {**PARAMS, "process_type": "{document_type.__class__}"})
    assert r.text == "Hay una aprobación de {document_type.__class__} pendiente en el nivel 2."


def test_el_nulo_se_muestra_como_raya():
    assert renderizar(CLAVE, {**PARAMS, "process_type": None}).text.startswith("Hay una aprobación de — ")


def test_un_contrato_roto_se_rechaza_antes_de_guardar():
    with pytest.raises(MensajeInvalido) as e:
        validar(CLAVE, {})
    assert e.value.codigo == MESSAGE_PARAM_MISSING


def test_el_ingles_esta_diferido_y_no_hay_traducciones_parciales():
    assert IDIOMAS == ("es",)
    assert set(CATALOGOS) == {"es"}
    assert renderizar(CLAVE, PARAMS, idioma="en") == renderizar(CLAVE, PARAMS)


def test_cada_efecto_consumible_tiene_su_mensaje():
    faltan = [f"{e}.{x.lower()}" for eventos in catalogo.EVENTOS_CONSUMIBLES.values()
              for e, efectos in eventos.items() for x in efectos
              if f"{e}.{x.lower()}" not in CATALOGOS["es"]]
    assert faltan == []


def test_toda_clave_citada_en_el_codigo_de_la_047_existe():
    claves: set[str] = set()
    for fichero in [*(MODULOS / "notifications").glob("*.py"), *(MODULOS / "scheduler").glob("*.py")]:
        for nodo in ast.walk(ast.parse(fichero.read_text())):
            if (isinstance(nodo, ast.Call) and getattr(nodo.func, "id", None) == "texto"
                    and nodo.args and isinstance(nodo.args[0], ast.Constant)):
                claves.add(nodo.args[0].value)
            if isinstance(nodo, ast.keyword) and nodo.arg == "message_key" \
                    and isinstance(nodo.value, ast.Constant):
                claves.add(nodo.value.value)
    assert len(claves) > 10, "la guarda no encontró claves: no estaría mirando nada"
    assert sorted(claves - set(CATALOGOS["es"])) == []


def test_texto_de_una_clave_rota_es_un_defecto():
    with pytest.raises(MensajeInvalido):
        texto("error.no_existe")
