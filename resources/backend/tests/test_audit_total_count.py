"""AUD-COUNT · El total del listado de auditoría lo cuenta la base (FR-001-211..219).

El handler del listado construía todas las entidades del tenant para devolver
un `len(...)` como total. Aquí se fija que `total` sale de un conteo sobre el
mismo conjunto del que sale la página: el tenant del usuario y los filtros
aplicados, antes de paginar. Una petición construye solo las entidades de su
página, no el conjunto entero.

SQLite en memoria por defecto; sobre PostgreSQL con `KONTROL_TEST_DB_URL`.
"""

from __future__ import annotations

import audit_world as mundo
import pytest

CLAVES_DE_ITEM = {"id", "action", "entity_type", "entity_id", "user_id", "request_id", "source", "event_time"}


@pytest.fixture(scope="module", autouse=True)
def _mundo():
    mundo.montar()
    yield


def _recorrer(cabeceras: dict[str, str], **filtros) -> tuple[list[str], set[int]]:
    """Recorre todas las páginas (de 100 en 100) y devuelve los ids vistos y los totales declarados."""
    vistos: list[str] = []
    totales: set[int] = set()
    page = 1
    while True:
        cuerpo = mundo.listar(cabeceras, page=page, page_size=100, **filtros)
        vistos += [i["id"] for i in cuerpo["items"]]
        totales.add(cuerpo["total"])
        if not cuerpo["items"]:
            break
        page += 1
    return vistos, totales


# --------------------------------------------------------------------------- #
# COUNT-01/02/03 · el total es exacto y no depende de la página
# --------------------------------------------------------------------------- #


def test_count_01_el_total_es_el_numero_de_eventos_no_el_de_la_pagina():
    h = mundo.como_a()
    m = mundo.marca()
    mundo.crear_eventos(mundo.W["tenant_a"], 37, entity_id=m)
    cuerpo = mundo.listar(h, entity_id=m, page=1, page_size=5)
    assert cuerpo["total"] == 37
    assert len(cuerpo["items"]) == 5


def test_count_02_la_pagina_pedida_no_cambia_el_total():
    h = mundo.como_a()
    m = mundo.marca()
    mundo.crear_eventos(mundo.W["tenant_a"], 37, entity_id=m)
    for page, esperados in ((1, 5), (2, 5), (8, 2), (9, 0)):
        cuerpo = mundo.listar(h, entity_id=m, page=page, page_size=5)
        assert cuerpo["total"] == 37, page
        assert len(cuerpo["items"]) == esperados, page


def test_count_03_el_tamano_de_pagina_no_cambia_el_total():
    h = mundo.como_a()
    m = mundo.marca()
    mundo.crear_eventos(mundo.W["tenant_a"], 37, entity_id=m)
    for tamano in (1, 10, 100):
        cuerpo = mundo.listar(h, entity_id=m, page=1, page_size=tamano)
        assert cuerpo["total"] == 37, tamano
        assert len(cuerpo["items"]) == min(tamano, 37), tamano


# --------------------------------------------------------------------------- #
# COUNT-04 · el total no sale del tenant
# --------------------------------------------------------------------------- #


def test_count_04_el_total_no_cuenta_eventos_de_otro_tenant():
    """Con la misma marca en los dos tenants, y también sin ningún filtro."""
    ha, hb = mundo.como_a(), mundo.como_b()
    m = mundo.marca()
    mundo.crear_eventos(mundo.W["tenant_a"], 7, entity_id=m)
    mundo.crear_eventos(mundo.W["tenant_b"], 4, entity_id=m)
    assert mundo.listar(ha, entity_id=m)["total"] == 7
    assert mundo.listar(hb, entity_id=m)["total"] == 4
    antes_a = mundo.listar(ha)["total"]
    antes_b = mundo.listar(hb)["total"]
    mundo.crear_eventos(mundo.W["tenant_b"], 3, entity_id=mundo.marca())
    mundo.crear_eventos(mundo.W["tenant_a"], 2, entity_id=mundo.marca())
    assert mundo.listar(ha)["total"] == antes_a + 2
    assert mundo.listar(hb)["total"] == antes_b + 3


# --------------------------------------------------------------------------- #
# COUNT-05/06/07/09 · el total respeta los filtros
# --------------------------------------------------------------------------- #


def test_count_05_el_total_respeta_el_filtro_de_accion():
    h = mundo.como_a()
    m = mundo.marca()
    accion = f"ACC-{m}"
    mundo.crear_eventos(mundo.W["tenant_a"], 3, entity_id=m, action=accion)
    mundo.crear_eventos(mundo.W["tenant_a"], 2, entity_id=m, action=f"OTRA-{m}")
    mundo.crear_eventos(mundo.W["tenant_b"], 5, entity_id=m, action=accion)
    cuerpo = mundo.listar(h, action=accion)
    assert cuerpo["total"] == 3
    assert {i["action"] for i in cuerpo["items"]} == {accion}


def test_count_06_el_total_respeta_el_filtro_de_tipo_de_entidad():
    h = mundo.como_a()
    m = mundo.marca()
    tipo = f"Tipo-{m}"
    mundo.crear_eventos(mundo.W["tenant_a"], 4, entity_id=m, entity_type=tipo)
    mundo.crear_eventos(mundo.W["tenant_a"], 1, entity_id=m, entity_type=f"Otro-{m}")
    mundo.crear_eventos(mundo.W["tenant_b"], 2, entity_id=m, entity_type=tipo)
    cuerpo = mundo.listar(h, entity_type=tipo)
    assert cuerpo["total"] == 4
    assert {i["entity_type"] for i in cuerpo["items"]} == {tipo}


def test_count_07_el_total_respeta_el_filtro_de_entidad():
    h = mundo.como_a()
    m, otra = mundo.marca(), mundo.marca()
    mundo.crear_eventos(mundo.W["tenant_a"], 6, entity_id=m)
    mundo.crear_eventos(mundo.W["tenant_a"], 3, entity_id=otra)
    cuerpo = mundo.listar(h, entity_id=m)
    assert cuerpo["total"] == 6
    assert {i["entity_id"] for i in cuerpo["items"]} == {m}


def test_count_09_con_filtros_combinados_el_total_es_el_del_conjunto_filtrado():
    h = mundo.como_a()
    m = mundo.marca()
    accion, tipo = f"ACC-{m}", f"Tipo-{m}"
    ambos = mundo.crear_eventos(mundo.W["tenant_a"], 2, entity_id=m, action=accion, entity_type=tipo)
    mundo.crear_eventos(mundo.W["tenant_a"], 3, entity_id=m, action=accion, entity_type=f"Otro-{m}")
    mundo.crear_eventos(mundo.W["tenant_a"], 4, entity_id=m, action=f"OTRA-{m}", entity_type=tipo)
    mundo.crear_eventos(mundo.W["tenant_b"], 5, entity_id=m, action=accion, entity_type=tipo)
    cuerpo = mundo.listar(h, entity_id=m, action=accion, entity_type=tipo)
    assert cuerpo["total"] == 2
    assert {i["id"] for i in cuerpo["items"]} == set(ambos)
    assert mundo.listar(h, action=accion)["total"] == 5
    assert mundo.listar(h, entity_type=tipo)["total"] == 6
    assert mundo.listar(h, entity_id=m)["total"] == 9


# --------------------------------------------------------------------------- #
# COUNT-10/11/14/15 · cómo se cuenta
# --------------------------------------------------------------------------- #


def test_count_10_una_peticion_construye_solo_las_entidades_de_su_pagina():
    """Si `total` saliera de traerse el conjunto, aquí se construirían 42 entidades."""
    h = mundo.como_a()
    m = mundo.marca()
    mundo.crear_eventos(mundo.W["tenant_a"], 37, entity_id=m)
    with mundo.observar() as visto:
        cuerpo = mundo.listar(h, entity_id=m, page=1, page_size=5)
    assert cuerpo["total"] == 37
    assert visto.cargadas == 5
    with mundo.observar() as fuera:
        cuerpo = mundo.listar(h, entity_id=m, page=9, page_size=5)
    assert cuerpo["total"] == 37 and cuerpo["items"] == []
    assert fuera.cargadas == 0


def test_count_11_dos_sentencias_un_conteo_sin_orden_ni_corte_y_la_pagina():
    h = mundo.como_a()
    m = mundo.marca()
    mundo.crear_eventos(mundo.W["tenant_a"], 37, entity_id=m)
    with mundo.observar() as visto:
        mundo.listar(h, entity_id=m, page=2, page_size=5)
    assert len(visto.sentencias) == 2, visto.sentencias
    assert len(visto.de_conteo) == 1 and len(visto.de_filas) == 1
    conteo, filas = visto.de_conteo[0].upper(), visto.de_filas[0].upper()
    assert conteo.startswith("SELECT COUNT(")
    assert "ORDER BY" not in conteo and "LIMIT" not in conteo and "OFFSET" not in conteo
    assert "ORDER BY AUDIT_EVENTS.EVENT_TIME DESC" in filas and "LIMIT" in filas and "OFFSET" in filas
    with mundo.observar() as grande:
        mundo.listar(h, entity_id=m, page=1, page_size=50)
    assert len(grande.sentencias) == 2


def test_count_14_sin_coincidencias_el_total_es_cero_y_se_sigue_contando_en_la_base():
    h = mundo.como_a()
    with mundo.observar() as visto:
        cuerpo = mundo.listar(h, entity_id=mundo.marca())
    assert cuerpo["items"] == [] and cuerpo["total"] == 0
    assert len(visto.de_conteo) == 1
    assert visto.cargadas == 0


def test_count_15_con_trescientos_eventos_se_construyen_los_diez_de_la_pagina():
    h = mundo.como_a()
    m = mundo.marca()
    mundo.crear_eventos(mundo.W["tenant_a"], 300, entity_id=m)
    with mundo.observar() as visto:
        cuerpo = mundo.listar(h, entity_id=m, page=1, page_size=10)
    assert cuerpo["total"] == 300
    assert len(cuerpo["items"]) == 10
    assert visto.cargadas == 10


# --------------------------------------------------------------------------- #
# COUNT-12/13 · regresión de forma y de paginación
# --------------------------------------------------------------------------- #


def test_count_12_la_forma_de_la_respuesta_no_cambia():
    h = mundo.como_a()
    m = mundo.marca()
    mundo.crear_eventos(mundo.W["tenant_a"], 3, entity_id=m)
    cuerpo = mundo.listar(h, entity_id=m, page=1, page_size=2)
    assert set(cuerpo) == {"items", "total", "page", "page_size"}
    assert (cuerpo["page"], cuerpo["page_size"]) == (1, 2)
    assert type(cuerpo["total"]) is int and cuerpo["total"] == 3
    assert all(set(i) == CLAVES_DE_ITEM for i in cuerpo["items"])


def test_count_13_la_paginacion_recorre_el_conjunto_entero_en_orden():
    h = mundo.como_a()
    m = mundo.marca()
    propios = mundo.crear_eventos(mundo.W["tenant_a"], 23, entity_id=m)
    tamanos: list[int] = []
    vistos: list[str] = []
    for page in (1, 2, 3):
        cuerpo = mundo.listar(h, entity_id=m, page=page, page_size=10)
        assert cuerpo["total"] == 23
        tamanos.append(len(cuerpo["items"]))
        vistos += [i["id"] for i in cuerpo["items"]]
        tiempos = [i["event_time"] for i in cuerpo["items"]]
        assert tiempos == sorted(tiempos, reverse=True), page
    assert tamanos == [10, 10, 3]
    assert len(vistos) == 23 and set(vistos) == set(propios)


# --------------------------------------------------------------------------- #
# COUNT-16 · paridad entre el conteo y los items recorridos
# --------------------------------------------------------------------------- #


def test_count_16_el_total_coincide_con_lo_que_se_obtiene_recorriendo_las_paginas():
    """Paridad entre el conteo y los items, filtro a filtro y combinados."""
    h = mundo.como_a()
    m = mundo.marca()
    accion, tipo = f"ACC-{m}", f"Tipo-{m}"
    g1 = mundo.crear_eventos(mundo.W["tenant_a"], 120, entity_id=m, action=accion, entity_type=tipo)
    g2 = mundo.crear_eventos(mundo.W["tenant_a"], 7, entity_id=m, action=accion, entity_type=f"Otro-{m}")
    g3 = mundo.crear_eventos(mundo.W["tenant_a"], 5, entity_id=m, action=f"OTRA-{m}", entity_type=tipo)
    mundo.crear_eventos(mundo.W["tenant_b"], 9, entity_id=m, action=accion, entity_type=tipo)
    casos = [
        ({"entity_id": m}, g1 + g2 + g3),
        ({"action": accion}, g1 + g2),
        ({"entity_type": tipo}, g1 + g3),
        ({"entity_id": m, "action": accion}, g1 + g2),
        ({"action": accion, "entity_type": tipo}, g1),
        ({"entity_id": m, "action": f"OTRA-{m}", "entity_type": tipo}, g3),
    ]
    for filtros, esperados in casos:
        vistos, totales = _recorrer(h, **filtros)
        assert totales == {len(esperados)}, filtros
        assert len(vistos) == len(esperados) and set(vistos) == set(esperados), filtros
