"""Guardias estructurales de la Spec 019 — recepción física.

Fallan en construcción. Existen para que un refactor no devuelva la recepción a
ser solo contable: sin unidad, sin bultos, sin observación física, y con el
asiento de inventario tomando la cantidad tecleada como si fuera la base.
"""

from __future__ import annotations

import ast
import pathlib
import re

from sqlalchemy import CheckConstraint

from app.core.database import Base, init_models
from app.core.scope import Scope, declared_scope

init_models()

BACKEND = pathlib.Path(__file__).resolve().parents[1]
COMPRAS = BACKEND / "app" / "modules" / "purchasing" / "service.py"
INVENTARIO = BACKEND / "app" / "modules" / "inventory" / "service.py"
API = BACKEND / "app" / "modules" / "purchasing" / "api.py"


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


def test_la_linea_de_recepcion_conserva_su_semantica_de_unidad():
    """Las columnas existían desde la Spec 011 y nadie las escribía."""
    t = Base.metadata.tables["goods_receipt_lines"]
    for col in ("uom_id", "presentation_id", "conversion_factor_snapshot",
                "base_quantity_received", "base_quantity_accepted", "base_quantity_rejected", "uom_source"):
        assert col in t.c, f"falta {col}"
    fuente = COMPRAS.read_text(encoding="utf-8")
    assert "def _unidad_recibida" in fuente, "desapareció la captura de unidad de la recepción"
    assert "uom_engine.to_base" in fuente, "la conversión dejó de pasar por la autoridad de la Spec 011"


def test_la_recepcion_registra_las_etapas_fisicas_del_proceso():
    """Etapas 1, 2, 4, 5, 6 y 11 del DOCX §2."""
    t = Base.metadata.tables["goods_receipts"]
    for col in ("arrival_at", "arrival_confirmed_by",            # etapa 1
                "unloading_scheduled_at",                          # etapa 2
                "packing_list_ref", "supplier_invoice_ref",        # etapa 4
                "packing_list_match", "supplier_invoice_match",
                "order_match", "documentation_match",
                "inspected_at", "inspected_by", "inspection_notes",  # etapa 5
                "packages_declared", "packages_received",            # etapa 6
                "record_issued_at", "record_issued_by"):             # etapa 11
        assert col in t.c, f"falta {col}"


def test_la_linea_conserva_la_observacion_fisica():
    """Etapa 6. El hecho observado es de 019; la incidencia es de la Spec 020."""
    t = Base.metadata.tables["goods_receipt_lines"]
    for col in ("physical_condition", "damaged_quantity", "damage_notes",
                "identification_ok", "reference_ok", "overage_base_quantity"):
        assert col in t.c, f"falta {col}"


def test_no_hay_un_segundo_veredicto_de_conformidad():
    """`quality_status` **es** la etapa 7. Un segundo campo para la misma
    pregunta se desincronizaría con el primero."""
    t = Base.metadata.tables["goods_receipts"]
    assert "quality_status" in t.c
    assert "conformity" not in t.c, "volvió el veredicto duplicado"


def test_el_saldo_se_acumula_en_cantidad_base():
    """El defecto de raíz: el movimiento guardaba la base y el saldo sumaba lo tecleado."""
    fuente = INVENTARIO.read_text(encoding="utf-8")
    cuerpo = fuente[fuente.index("def record_movement"):fuente.index("def reverse_movement")]
    assert "balance.qty_on_hand = _dec(balance.qty_on_hand) + _dec(base_signed)" in cuerpo, (
        "el saldo volvió a acumular la cantidad tecleada")
    assert "+ _dec(signed)" not in cuerpo.split("# Balance (cache)")[1], (
        "queda una acumulación con la cantidad tecleada tras el cálculo del saldo")


def test_la_aceptacion_pasa_la_presentacion_al_motor_y_no_la_ubicacion():
    """Sin presentación el factor sería 1; con ubicación 019 estaría haciendo put-away."""
    fuente = COMPRAS.read_text(encoding="utf-8")
    cuerpo = fuente[fuente.index("def accept_receipt"):fuente.index("def reject_receipt")]
    assert "presentation_id=line.presentation_id" in cuerpo, "el asiento perdió la presentación"
    assert "location_id=None" in cuerpo, "la recepción empezó a decidir la ubicación (es de la Spec 022)"


def test_la_aceptacion_bloquea_la_linea_de_orden_antes_de_acumular():
    """Dos recepciones simultáneas contra la misma línea perderían una acumulación."""
    fuente = COMPRAS.read_text(encoding="utf-8")
    cuerpo = fuente[fuente.index("def accept_receipt"):fuente.index("def reject_receipt")]
    assert "with_for_update()" in cuerpo, "la acumulación en la orden dejó de bloquearse"
    assert cuerpo.index("with_for_update()") < cuerpo.index("quantity_received = _dec("), (
        "se acumula antes de bloquear")


def _codigo_de_recepcion() -> str:
    """Solo el bloque de recepción del módulo de compras.

    Acotarlo importa: `CUARENTENA` es un destino legítimo de una devolución de
    compra (Spec 036) y buscarlo en el módulo entero haría fallar el guardia por
    código que no es de esta Spec.
    """
    fuente = COMPRAS.read_text(encoding="utf-8")
    fin = re.search(r"^def (?!create_receipt|confirmar_arribo|registrar_inspeccion|_unidad_recibida|_sobrante_observado|add_receipt_line|confirm_receipt|accept_receipt|reject_receipt)",
                    fuente[fuente.index("def create_receipt"):], re.M)
    bloque = fuente[fuente.index("def create_receipt"):][:fin.start() if fin else None]
    return "\n".join(x for x in bloque.splitlines() if not x.strip().startswith("#"))


def test_la_recepcion_no_invade_a_sus_vecinas():
    """020 incidencias, 021 confirmación, 022 put-away, 031/032 picking."""
    codigo = _codigo_de_recepcion()
    for prohibido in ("PickList", "put_away", "putaway", "InventoryConfirmation", "Reservation"):
        assert prohibido not in codigo, f"la recepción hace algo de otra Spec: {prohibido}"
    for estado in ("RECIBIDO", "PENDIENTE_CONFIRMACION", "BLOQUEADO", "CUARENTENA", "PICKING"):
        assert f'"{estado}"' not in codigo, f"019 escribió el estado de mercancía {estado} (es de 021/023)"


def test_las_restricciones_estan_en_el_orm_y_en_la_migracion():
    """Lección N7: solo en la migración, el esquema de pruebas sería más débil."""
    checks = {c.name for t in ("goods_receipts", "goods_receipt_lines")
              for c in Base.metadata.tables[t].constraints if isinstance(c, CheckConstraint)}
    assert "ck_goods_receipts_packages_nonneg" in checks
    assert "ck_goods_receipt_lines_damage_nonneg" in checks
    m = (BACKEND / "alembic" / "versions" / "0044_spec019_physical_receipt.py").read_text(encoding="utf-8")
    assert 'revision = "0044_spec019_receipt"' in m and len("0044_spec019_receipt") <= 32
    assert 'down_revision = "0043_spec030_reservation"' in m
    for token in ("ck_goods_receipts_packages_nonneg", "ck_goods_receipt_lines_damage_nonneg",
                  "arrival_at", "packages_declared", "physical_condition", "overage_base_quantity",
                  "record_issued_at"):
        assert token in m, f"la migración no declara {token}"


def test_el_alcance_de_empresa_no_cambio():
    from app.modules.purchasing.models import GoodsReceipt, GoodsReceiptLine

    assert declared_scope(GoodsReceipt) is Scope.COMPANY
    assert declared_scope(GoodsReceiptLine) is Scope.COMPANY
    # La línea deriva su empresa de la recepción y no la duplica
    assert "company_id" not in Base.metadata.tables["goods_receipt_lines"].c
    assert GoodsReceiptLine.__scope_authority__ == "receipt_id → goods_receipts"


def test_la_api_de_recepcion_valida_la_pertenencia_antes_de_operar():
    fuente = API.read_text(encoding="utf-8")
    for ruta in ('"/receipts/{receipt_id}/arrival"', '"/receipts/{receipt_id}/inspection"',
                 '"/receipts/{receipt_id}/lines"'):
        i = fuente.index(ruta)
        bloque = fuente[i:i + 1400]
        assert "_owned(db, GoodsReceipt" in bloque, f"{ruta} no acota la recepción a la empresa"


def test_los_seriales_se_normalizan_a_texto():
    """La API enviaba una lista a una columna de texto y la aceptación esperaba
    la cadena: los dos extremos no hablaban el mismo idioma."""
    fuente = COMPRAS.read_text(encoding="utf-8")
    assert "isinstance(serials, list)" in fuente, "se perdió la normalización de seriales"
    assert "def accept_receipt" in fuente
    assert 'inv_service.create_serial' in fuente


def test_solo_la_aceptacion_escribe_en_el_ledger_desde_compras():
    assert _funciones_que_llaman(COMPRAS, "record_movement") == {"accept_receipt"}
