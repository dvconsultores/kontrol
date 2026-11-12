"""Guardias de la condición del proceso (Spec 018 · §3).

La fila «Estados recibido, disponible, pendiente, bloqueado» se cierra como
condición **derivada** del proceso. Estas guardias impiden que un refactor la
convierta en un cuarto estado de inventario, en una columna persistida que se
desincronice o en un segundo motor con sus propias reglas.

No tocan ninguna guardia de las Specs 019, 020, 021 y 022: comprueban que la
condición respeta sus fronteras.
"""

from __future__ import annotations

import ast
import pathlib

from app.core.database import Base, init_models
from app.modules.inventory import states as inv_states
from app.modules.purchasing import process_condition

init_models()

BACKEND = pathlib.Path(__file__).resolve().parents[1]
MODULO = BACKEND / "app" / "modules" / "purchasing" / "process_condition.py"
API = BACKEND / "app" / "modules" / "purchasing" / "api.py"
IMPORTS = BACKEND / "app" / "modules" / "imports" / "service.py"
COMPRAS = BACKEND / "app" / "modules" / "purchasing" / "service.py"


def _fuente(modulo: pathlib.Path) -> str:
    return modulo.read_text(encoding="utf-8")


def test_son_exactamente_tres_y_en_orden_de_precedencia():
    """El documento fija tres condiciones; una cuarta sería una decisión nueva."""
    assert process_condition.CONDICIONES_DEL_PROCESO == (
        "BLOQUEADO_POR_INCIDENCIA",
        "PENDIENTE_DE_VALIDACION",
        "RECIBIDO",
    )


def test_la_etiqueta_humana_existe_para_cada_condicion():
    assert set(process_condition.ETIQUETAS) == set(process_condition.CONDICIONES_DEL_PROCESO)
    assert process_condition.ETIQUETAS["RECIBIDO"] == "Recibido"
    assert process_condition.ETIQUETAS["PENDIENTE_DE_VALIDACION"] == "Pendiente de validación"
    assert process_condition.ETIQUETAS["BLOQUEADO_POR_INCIDENCIA"] == "Bloqueado por incidencia"


def test_la_condicion_no_se_persiste():
    """Se deriva del estado real; una columna se desincronizaría."""
    columnas = Base.metadata.tables["goods_receipts"].c
    for prohibida in ("process_condition", "process_state", "condition", "condition_status"):
        assert prohibida not in columnas, f"la condición se guardó en goods_receipts.{prohibida}"
    # `storage_conditions` es la clasificación de almacenamiento de la Spec 022
    # y no tiene nada que ver: se busca el vocabulario de esta condición.
    tablas = [t for t in Base.metadata.tables
              if "process_condition" in t or "receipt_condition" in t]
    assert tablas == [], f"apareció una tabla para la condición: {tablas}"


def test_la_condicion_no_escribe_inventario():
    """Mover stock para mostrarla revertiría la decisión de la Spec 020."""
    fuente = _fuente(MODULO).lower()
    for prohibido in ("record_movement", "inventorybalance", "qty_on_hand",
                      "costlayer", "location_id", "putaway", "picklist",
                      "db.add(", "db.commit(", "mapped_column", "insert("):
        assert prohibido not in fuente, f"la condición toca lo que no le toca: {prohibido}"


def test_no_se_crean_estados_de_inventario_para_la_condicion():
    """La condición pertenece al proceso, no a la mercancía."""
    for estado in ("PENDIENTE_DE_VALIDACION", "BLOQUEADO_POR_INCIDENCIA"):
        assert estado not in inv_states.MERCHANDISE_STATES, (
            f"{estado} se coló como estado de mercancía")
        assert estado not in {t.target for t in inv_states.ACTIVE_TRANSITIONS}, (
            f"{estado} se coló como destino de una arista de inventario")


def test_la_condicion_usa_las_incidencias_como_autoridad_de_la_020():
    """Un solo criterio de bloqueo: una incidencia viva que no está resuelta ni anulada."""
    fuente = _fuente(MODULO)
    assert 'ESTADOS_TERMINALES_DE_INCIDENCIA = ("RESUELTA", "ANULADA")' in fuente
    assert "ReceiptIncident" in fuente
    assert "Registrada" not in fuente and "Escalada" not in fuente, (
        "la condición reinterpretó el ciclo de vida de la incidencia")
    for motor_paralelo in ("INCIDENT_OPEN", "INCIDENT_CLOSE", "can_transition"):
        assert motor_paralelo not in fuente, f"segundo motor de incidencias: {motor_paralelo}"


def test_la_condicion_no_se_reimplementa_en_el_frontend():
    """Las dos superficies consumen el mismo resultado del backend."""
    assert "process_condition" in _fuente(API), "Recepciones no publica la condición"
    assert "process_condition" in _fuente(IMPORTS), "el expediente no publica la condición"
    assert "process_condition.condiciones_por_recepcion" in _fuente(IMPORTS), (
        "el expediente calculó una versión propia")
    assert "process_condition.condiciones_por_recepcion" in _fuente(API), (
        "el listado calculó una versión propia")


def test_el_listado_y_el_detalle_la_exponen_en_una_sola_consulta():
    """Sin N+1: una consulta por lote, no una por recepción."""
    fuente = _fuente(API)
    assert "condiciones_por_recepcion(db, items)" in fuente
    arbol = ast.parse(_fuente(MODULO))
    lecturas = [n for n in ast.walk(arbol)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "execute"]
    assert len(lecturas) == 1, f"la condición hace {len(lecturas)} consultas por lote"


def test_la_condicion_no_duplica_motores_de_las_specs_vecinas():
    """020 incidencias, 021 confirmación, 022 put-away, 023 inventario."""
    bloque = _fuente(MODULO)
    for prohibido in ("put_away", "desde_recepcion", "confirmacion_inventario",
                      "resolver_incidencia", "registrar_incidencia"):
        assert prohibido not in bloque, f"la condición ejecuta algo de otra Spec: {prohibido}"
    assert "inventory" not in bloque, "la condición importó el motor de inventario"
    assert "from app.modules.purchasing.service import" not in bloque, (
        "la condición depende del servicio de compras: debe ser autónoma")


def test_las_guardias_vecinas_siguen_sin_mencionar_la_condicion_en_su_codigo():
    """La 019 y la 020 no escriben la condición: no es su autoridad."""
    for modulo in (COMPRAS,):
        fuente = _fuente(modulo)
        for prohibido in ('"PENDIENTE_DE_VALIDACION"', '"BLOQUEADO_POR_INCIDENCIA"'):
            assert prohibido not in fuente, f"la condición se escribió en {modulo.name}"
