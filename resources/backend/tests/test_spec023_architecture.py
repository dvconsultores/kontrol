"""Spec 023 · guardias estructurales de la capacidad multiestado.

Estas pruebas no ejercitan el motor: leen el código. Defienden las fronteras que
`ADR-D0-010` v2 y el Constitution Gate imponen, y que una regresión silenciosa
rompería sin que ninguna prueba funcional se enterase.
"""

from __future__ import annotations

import re
from pathlib import Path

from app.modules.inventory import service as inv
from app.modules.inventory import states

RAIZ = Path(__file__).resolve().parents[1] / "app"
SERVICE = (RAIZ / "modules" / "inventory" / "service.py").read_text()
STATES = (RAIZ / "modules" / "inventory" / "states.py").read_text()


def test_hay_una_sola_autoridad_de_estados_de_mercancia():
    """El catálogo vive en un módulo. Copiarlo en otro es duplicar el motor."""
    otros = []
    for py in RAIZ.rglob("*.py"):
        if py.name == "states.py":
            continue
        texto = py.read_text()
        # Tres o más etiquetas exclusivas del catálogo juntas: eso es una copia.
        exclusivos = ("PENDIENTE_CONFIRMACION", "BLOQUEADO", "PREPARADO", "DESPACHADO", "DEVUELTO")
        if sum(1 for e in exclusivos if f'"{e}"' in texto) >= 3:
            otros.append(str(py.relative_to(RAIZ)))
    assert otros == [], f"catálogo de estados replicado en: {otros}"


def test_nadie_asigna_el_estado_del_saldo_a_mano():
    """`InventoryBalance.state` solo lo escribe el motor, al crear la fila."""
    culpables = []
    for py in RAIZ.rglob("*.py"):
        for m in re.finditer(r"^\s*(\w+)\.state\s*=\s*", py.read_text(), re.M):
            if m.group(1) in {"balance", "saldo", "origen", "destino", "bal"}:
                culpables.append(f"{py.relative_to(RAIZ)}: {m.group(0).strip()}")
    assert culpables == [], f"mutación directa del estado del saldo: {culpables}"


def test_la_reclasificacion_valida_antes_de_bloquear_y_de_mover():
    """Orden obligatorio: matriz → motivo → aprobación → bloqueo → escritura.

    Si la validación cayera después del bloqueo, una transición ilegal dejaría
    filas bloqueadas y podría escribir antes de fallar.
    """
    cuerpo = SERVICE[SERVICE.index("def reclassify("):SERVICE.index("def lock_balance(")]
    assert cuerpo.index("assert_transition") < cuerpo.index("lock_balance")
    assert cuerpo.index("TRANSITION_REASON_REQUIRED") < cuerpo.index("lock_balance")
    assert cuerpo.index("ensure_approved") < cuerpo.index("lock_balance")
    assert cuerpo.index("lock_balance") < cuerpo.index("qty_on_hand =")


def test_la_entrada_valida_el_estado_antes_de_convertir_unidades():
    cuerpo = SERVICE[SERVICE.index("def record_movement("):SERVICE.index("def _reverse_movement")] \
        if "def _reverse_movement" in SERVICE else SERVICE[SERVICE.index("def record_movement("):]
    assert cuerpo.index("assert_valid_state") < cuerpo.index("uom_engine.to_base")


def _cuerpo_recompute() -> tuple[str, str]:
    """Devuelve (bucle de movimientos, bucle de reservas) por separado.

    Importa distinguirlos: el estado de un movimiento sale del ledger, pero el
    reservado **sí** se proyecta sobre `DISPONIBLE` por `POL-D0-002` §1. Un
    guardia que mirase la función entera confundiría lo correcto con lo prohibido.
    """
    completo = SERVICE[SERVICE.index("def recompute_balances("):SERVICE.index("def get_available(")]
    corte = completo.index("# 2. Aplicar reservas activas")
    return completo[:corte], completo[corte:]


def test_la_reconstruccion_no_supone_disponible():
    """El fallo que `R-D0-10-5` prohíbe: reconstruir colapsando los estados."""
    movimientos, reservas = _cuerpo_recompute()
    assert "m.target_state" in movimientos and "m.source_state" in movimientos
    assert '"DISPONIBLE"' not in movimientos, \
        "la reconstrucción vuelve a fijar un estado en vez de leerlo del ledger"
    assert '"DISPONIBLE"' in reservas, "el reservado debe seguir proyectándose sobre DISPONIBLE"


def test_la_reconstruccion_acumula_la_cantidad_base():
    """La caja ×12 de la Spec 019, que en la reconstrucción seguía viva."""
    movimientos, _ = _cuerpo_recompute()
    assert "m.base_quantity" in movimientos
    # Se admite `m.quantity` **solo** como respaldo de movimientos históricos sin
    # cantidad base, y nunca como primera opción.
    for linea in movimientos.splitlines():
        if "_dec(m.quantity)" in linea:
            assert "m.base_quantity is not None else" in linea, \
                f"usa la cantidad tecleada fuera del respaldo histórico: {linea.strip()}"


def test_la_recepcion_de_transferencia_usa_el_destino_que_decide():
    """El defecto vivo que este ciclo cierra: el campo existía y se ignoraba."""
    cuerpo = SERVICE[SERVICE.index("def confirm_transfer_receipt("):]
    cuerpo = cuerpo[:cuerpo.index("\ndef ")]
    assert 'line.destination_state = "CUARENTENA"' in cuerpo
    assert "state=line.destination_state" in cuerpo, \
        "vuelve a llamar al motor sin pasar el destino que acaba de decidir"


def test_solo_disponible_es_vendible_en_el_codigo():
    assert states.SELLABLE_STATES == frozenset({"DISPONIBLE"})
    assert states.RESERVABLE_STATES == frozenset({"DISPONIBLE"})


def test_la_salida_de_disponible_es_solo_la_que_la_032_activo():
    """`R-D0-10-10` reservaba esta elección para la Spec que abriera la primera
    salida de `DISPONIBLE`. La abrió la 032 para extraer lo que se prepara; la
    guardia pasa de «no hay ninguna» a «no hay ninguna más»."""
    assert {(t.target, t.owner_spec) for t in states.ACTIVE_TRANSITIONS
            if t.source == "DISPONIBLE"} == {("PICKING", "032")}


def test_cada_arista_declara_su_evidencia():
    """Sin fuente documental no hay arista: es la regla que evita el grafo por olfato."""
    for t in states.ACTIVE_TRANSITIONS:
        assert t.evidence.strip(), f"{t.source}→{t.target} sin evidencia"
        assert t.owner_spec.isdigit(), f"{t.source}→{t.target} sin Spec dueña"
        assert t.permission, f"{t.source}→{t.target} sin permiso"


def test_los_vocabularios_no_se_mezclan():
    """Siete etiquetas coinciden; `VENCIDO` es solo de lote y ocho solo de mercancía.

    El solape es mayor de lo que parece —`VENDIDO` está en los dos—, y por eso
    la separación no puede apoyarse en los nombres: se apoya en la entidad.
    """
    compartidas = set(states.MERCHANDISE_STATES) & set(inv.LOT_SERIAL_TRANSITIONS)
    assert len(compartidas) == 7, sorted(compartidas)
    assert set(inv.LOT_SERIAL_TRANSITIONS) - compartidas == {"VENCIDO"}
    solo_mercancia = {"ESPERADO", "RECIBIDO", "PENDIENTE_CONFIRMACION", "BLOQUEADO",
                      "PICKING", "PREPARADO", "DESPACHADO", "DEVUELTO"}
    assert set(states.MERCHANDISE_STATES) - compartidas == solo_mercancia


def test_la_capacidad_no_implementa_flujo_de_la_021():
    """Frontera: 023 entrega el motor, no la confirmación de inventario."""
    prohibido = ("def confirmar_inventario", "def conciliar_recepcion", "def liberar_lote",
                 "/inventory-confirmation", "def confirm_inventory")
    for palabra in prohibido:
        assert palabra not in SERVICE, f"la 023 está implementando la 021: {palabra}"


def test_no_se_implementa_politica_de_conflicto_futura():
    """`R-D0-10-10` la reserva para la Spec que active la arista. No adelantarla."""
    for palabra in ("partial_reclassification", "auto_release", "reassign_reservation"):
        assert palabra not in SERVICE and palabra not in STATES, \
            f"política futura implementada sin autoridad: {palabra}"


def test_no_hay_segundo_motor_de_saldos_ni_de_disponible():
    for prohibido in ("InventoryStateBalance", "QuarantineBalance", "AvailableInventoryV2",
                      "StateStock", "ReceiptInventoryBalance"):
        assert not any(prohibido in py.read_text() for py in RAIZ.rglob("*.py")), prohibido
