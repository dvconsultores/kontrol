"""Guardias estructurales de la Spec 020 — incidencias de recepción.

Fallan en construcción. Existen para que la incidencia no se convierta en una
segunda versión del hecho físico, no invente tipos ni tratamientos, no ejecute
lo que es de la Spec 021 y no monte motores propios de aprobación o documentos.
"""

from __future__ import annotations

import ast
import pathlib

from sqlalchemy import CheckConstraint

from app.core.database import Base, init_models
from app.core.scope import Scope, declared_scope
from app.modules.purchasing import models as compras_models
from app.modules.purchasing import service as compras

init_models()

BACKEND = pathlib.Path(__file__).resolve().parents[1]
SERVICE = BACKEND / "app" / "modules" / "purchasing" / "service.py"
API = BACKEND / "app" / "modules" / "purchasing" / "api.py"


def _bloque_de_incidencias(fuente: str) -> str:
    inicio = fuente.index("def registrar_incidencia")
    fin = fuente.index("def _sync_order_status")
    return "\n".join(x for x in fuente[inicio:fin].splitlines() if not x.strip().startswith("#"))


def _funciones_que_llaman(modulo: pathlib.Path, nombre: str) -> set[str]:
    arbol = ast.parse(modulo.read_text(encoding="utf-8"))
    salida = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.FunctionDef):
            for sub in ast.walk(nodo):
                if isinstance(sub, ast.Call):
                    f = sub.func
                    if (isinstance(f, ast.Attribute) and f.attr == nombre) or (isinstance(f, ast.Name) and f.id == nombre):
                        salida.add(nodo.name)
    return salida


def test_los_tipos_son_los_cinco_de_la_etapa_ocho():
    """«faltantes; sobrantes; daños; referencias incorrectas; diferencias documentales»."""
    assert compras_models.INCIDENT_TYPES == (
        "FALTANTE", "SOBRANTE", "DANO", "REFERENCIA_INCORRECTA", "DIFERENCIA_DOCUMENTAL")
    assert compras_models.INCIDENT_TYPE_DOCUMENTAL == "DIFERENCIA_DOCUMENTAL"


def test_los_tratamientos_son_los_cuatro_del_contrato():
    """«ajuste autorizado; reclamo al proveedor; investigación interna; mercancía en cuarentena»."""
    assert compras_models.INCIDENT_RESOLUTIONS == (
        "AJUSTE_AUTORIZADO", "RECLAMO_PROVEEDOR", "INVESTIGACION_INTERNA", "CUARENTENA")
    assert compras_models.INCIDENT_RESOLUTION_APPROVED == "AJUSTE_AUTORIZADO"


def test_el_ciclo_de_vida_es_explicito_y_sus_terminales_no_se_mueven():
    t = compras.INCIDENT_TRANSITIONS
    assert set(t) == set(compras_models.INCIDENT_STATUSES)
    assert t["RESUELTA"] == set() and t["ANULADA"] == set()
    assert "RESUELTA" in t["PENDIENTE_AUTORIZACION"]


def test_la_incidencia_apunta_al_hecho_y_no_lo_copia():
    """El producto, la unidad, la presentación y el daño viven en la línea de
    recepción. Duplicarlos aquí crearía dos verdades para el mismo hecho."""
    t = Base.metadata.tables["receipt_incidents"]
    assert "receipt_line_id" in t.c and "receipt_id" in t.c
    for duplicado in ("product_id", "presentation_id", "uom_id", "conversion_factor_snapshot",
                      "physical_condition", "damaged_quantity", "lot_number", "expiry_date",
                      "quantity_received", "is_conformant", "quality_status"):
        assert duplicado not in t.c, f"la incidencia duplica el hecho de la Spec 019: {duplicado}"


def test_las_restricciones_estan_en_el_orm_y_en_la_migracion():
    t = Base.metadata.tables["receipt_incidents"]
    checks = {c.name for c in t.constraints if isinstance(c, CheckConstraint)}
    esperadas = {"ck_receipt_incidents_type", "ck_receipt_incidents_status",
                 "ck_receipt_incidents_resolution", "ck_receipt_incidents_line_and_quantity_by_type",
                 "ck_receipt_incidents_quantity_positive",
                 "ck_receipt_incidents_resolved_has_resolution"}
    assert esperadas <= checks, esperadas - checks
    m = (BACKEND / "alembic" / "versions" / "0045_spec020_receipt_incidents.py").read_text(encoding="utf-8")
    assert 'revision = "0045_spec020_incidents"' in m and len("0045_spec020_incidents") <= 32
    assert 'down_revision = "0044_spec019_receipt"' in m
    for nombre in esperadas:
        assert nombre in m, f"la migración no declara {nombre}"


def test_la_cantidad_afectada_es_decimal_y_en_base():
    from sqlalchemy import Numeric

    col = Base.metadata.tables["receipt_incidents"].c["affected_base_quantity"]
    assert isinstance(col.type, Numeric) and col.type.scale == 6
    assert "affected_quantity" not in Base.metadata.tables["receipt_incidents"].c, (
        "apareció una cantidad sin decir en qué unidad está")


def test_la_incidencia_no_ejecuta_lo_que_es_de_otras_specs():
    bloque = _bloque_de_incidencias(SERVICE.read_text(encoding="utf-8"))
    for prohibido in ("record_movement", "InventoryBalance", "qty_on_hand", "location_id",
                      "PickList", "put_away"):
        assert prohibido not in bloque, f"la incidencia hace algo de otra Spec: {prohibido}"
    for estado in ("RECIBIDO", "PENDIENTE_CONFIRMACION", "BLOQUEADO", "DISPONIBLE"):
        assert f'"{estado}"' not in bloque, f"020 escribió el estado de mercancía {estado}"


def test_no_hay_motor_de_aprobaciones_ni_de_documentos_local():
    bloque = _bloque_de_incidencias(SERVICE.read_text(encoding="utf-8"))
    assert "approvals_integration.require_for_document" in bloque
    assert "approvals_integration.ensure_approved" in bloque
    for tabla in ("incident_approvals", "receipt_incident_files", "incident_documents"):
        assert tabla not in Base.metadata.tables, f"motor paralelo: {tabla}"
    # La evidencia va por el registro cerrado de la Spec 046
    from app.modules.documents.resources import RESOURCE_KINDS

    assert "ReceiptIncident" in RESOURCE_KINDS
    assert RESOURCE_KINDS["ReceiptIncident"].permission == "compras:view"


def test_solo_el_ajuste_autorizado_pide_aprobacion():
    """Control crítico 115 del proceso; ningún otro tratamiento lo exige."""
    bloque = _bloque_de_incidencias(SERVICE.read_text(encoding="utf-8"))
    assert "resolution == INCIDENT_RESOLUTION_APPROVED" in bloque
    assert bloque.count("require_for_document") == 1, (
        "más de un tratamiento pide aprobación, o se pide en otro punto")


def test_resolver_bloquea_la_incidencia_y_registrar_bloquea_la_linea():
    """Dos resoluciones a la vez no pueden decidir cosas distintas, y dos
    incidencias no pueden comprometer entre las dos más de lo que llegó."""
    bloque = _bloque_de_incidencias(SERVICE.read_text(encoding="utf-8"))
    resolver = bloque[bloque.index("def resolver_incidencia"):bloque.index("def anular_incidencia")]
    assert "with_for_update()" in resolver, "la resolución dejó de bloquear la incidencia"
    registrar = bloque[bloque.index("def registrar_incidencia"):bloque.index("def escalar_incidencia")]
    assert "with_for_update()" in registrar, "el registro dejó de bloquear la línea"


def test_el_resultado_para_la_021_es_estructurado():
    bloque = _bloque_de_incidencias(SERVICE.read_text(encoding="utf-8"))
    assert "def resultado_de_incidencias" in bloque
    for clave in ("ready_for_confirmation", "unresolved", "incident_type", "resolution",
                  "affected_base_quantity"):
        assert clave in bloque, f"el contrato para la 021 no expone {clave}"


def test_la_api_valida_la_cadena_entera():
    fuente = API.read_text(encoding="utf-8")
    assert "def _owned_incident" in fuente
    cuerpo = fuente[fuente.index("def _owned_incident"):fuente.index("def get_receipt_incident")]
    assert "_owned(db, GoodsReceipt" in cuerpo and "_owned(db, ReceiptIncident" in cuerpo
    assert "incident.receipt_id) != str(receipt_id)" in cuerpo, (
        "no comprueba que la incidencia sea de esta recepción")
    for ruta in ("escalate", "resolve", "cancel"):
        i = fuente.index(f'"/receipts/{{receipt_id}}/incidencias/{{incident_id}}/{ruta}"')
        assert "_owned_incident(" in fuente[i:i + 1600], f"{ruta} no valida la cadena"


def test_el_alcance_de_empresa_es_directo_y_no_anulable():
    assert declared_scope(compras_models.ReceiptIncident) is Scope.COMPANY
    col = Base.metadata.tables["receipt_incidents"].c["company_id"]
    assert not col.nullable
    assert {fk.column.table.name for fk in col.foreign_keys} == {"companies"}


def test_la_incidencia_solo_se_crea_en_su_propio_servicio():
    """Una segunda vía de creación se saltaría los topes de cantidad."""
    arbol = ast.parse(SERVICE.read_text(encoding="utf-8"))
    creadores = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.FunctionDef):
            for sub in ast.walk(nodo):
                if (isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name)
                        and sub.func.id == "ReceiptIncident"):
                    creadores.add(nodo.name)
    assert creadores == {"registrar_incidencia"}, creadores
