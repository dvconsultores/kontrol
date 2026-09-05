"""Autoridad única de los estados de mercancía y sus transiciones (`ADR-D0-010` v2).

Antes de este módulo el catálogo vivía en un documento y el motor escribía
`DISPONIBLE` fijo. `R-D0-10-7` obliga a rechazar toda transición no declarada, y
la v2 del ADR declaró por fin contra qué decidir: nueve transiciones activas,
cada una con evidencia. Aquí se ejecuta esa decisión y **solo** esa.

Dos advertencias que el ADR hace explícitas:

- Estos estados **no** son los de lote y serial (`FR-003-035`,
  `LOT_SERIAL_TRANSITIONS`). **Siete** etiquetas coinciden —`VENDIDO` entre
  ellas— y ninguna semántica se comparte: un lote `CUARENTENA` describe el lote
  entero; un saldo `CUARENTENA`, una cantidad en una combinación dimensional.
  `VENCIDO` pertenece solo al otro vocabulario y no aparece aquí.
- Vendible es **exclusivamente** `DISPONIBLE` (`R-D0-10-3`), y solo lo vendible
  se reserva (`R-D0-03-5`, `POL-D0-002` §7). No se distribuyen listas de estados
  por los módulos: se pregunta aquí.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.errors import ConflictError, KontrolError

#: Estado con el que nace el stock cuando el llamante no dice otra cosa. El ADR
#: lo conserva a propósito: «el cambio de comportamiento (la recepción ya no
#: salta a `DISPONIBLE`) llega con la Spec 021, no con esta decisión».
DEFAULT_STATE = "DISPONIBLE"

#: Estado con el que la recepción física materializa lo recibido (Spec 019 lo
#: escribe, Spec 021 lo libera). Nombrarlo aquí evita que el literal se
#: distribuya por los módulos de compras.
RECEIVED_STATE = "RECIBIDO"

#: Estado al que la confirmación libera formalmente (`R-D0-10-4`).
RELEASED_STATE = "DISPONIBLE"

#: Estado de lo que la confirmación declara no apto.
REJECTED_STATE = "RECHAZADO"

#: Estado de retención por calidad, del que la confirmación también puede salir.
QUARANTINE_STATE = "CUARENTENA"

#: Los quince del `ADR-D0-010` §Conjunto de estados de mercancía. El orden es el
#: del ADR: de lo que aún no llegó a lo que ya no está.
MERCHANDISE_STATES: tuple[str, ...] = (
    "ESPERADO",
    "RECIBIDO",
    "PENDIENTE_CONFIRMACION",
    "CUARENTENA",
    "BLOQUEADO",
    "DISPONIBLE",
    "RESERVADO",
    "PICKING",
    "PREPARADO",
    "TRANSITO",
    "DESPACHADO",
    "DEVUELTO",
    "RECHAZADO",
    "DESECHO",
    "VENDIDO",
)

#: `R-D0-10-3`: «`disponible para venta` es **exclusivamente** `DISPONIBLE`».
#: No es una lista configurable ni admite excepción por empresa.
SELLABLE_STATES: frozenset[str] = frozenset({"DISPONIBLE"})

#: `R-D0-03-5` y `POL-D0-002` §7: la reserva solo consume saldo `DISPONIBLE` y no
#: cambia el estado de custodia. El estado `RESERVADO` del catálogo **no** es el
#: mecanismo de reserva y hoy no tiene productor.
RESERVABLE_STATES: frozenset[str] = frozenset({"DISPONIBLE"})


@dataclass(frozen=True)
class Transition:
    """Una arista declarada. Sin evidencia documental no entra en la tabla."""

    source: str | None  # `None` = entrada de mercancía al inventario
    target: str
    event: str
    owner_spec: str
    #: `resource:action` del catálogo real de `setup/api.py`. No es decorativo:
    #: es el permiso que el endpoint dueño del evento debe exigir.
    permission: str
    approval_required: bool
    reason_required: bool
    evidence: str


#: Las nueve activas de `ADR-D0-010` v2, más las entradas que la propia v2
#: conserva. Ninguna tiene `DISPONIBLE` como origen: la cadena de la recepción va
#: **hacia** lo vendible. Por eso el conflicto de `R-D0-10-9` no es alcanzable
#: con esta tabla, y por eso no se implementa política de conflicto alguna
#: (`R-D0-10-10` la reserva para la Spec que active la primera arista de salida).
ACTIVE_TRANSITIONS: tuple[Transition, ...] = (
    Transition(None, "DISPONIBLE", "STOCK_ENTRY", "023", "inventario:create", False, False,
               "ADR-D0-010 v2 §Migración: el salto a DISPONIBLE se conserva hasta que 021 lo cambie"),
    Transition(None, "RECIBIDO", "RECEIPT_ACCEPTANCE", "019", "compras:quality", False, False,
               "R-D0-10-4 · ADR §Migración · flujo objetivo del checkpoint operativo"),
    Transition(None, "CUARENTENA", "TRANSFER_DISCREPANCY", "025", "inventario:transition", True, True,
               "FR-003-062: destino definido (cuarentena/ajuste) y aprobación"),
    Transition("RECIBIDO", "DISPONIBLE", "FORMAL_RELEASE", "021", "inventario:confirm", False, False,
               "R-D0-10-4 · flujo «liberación formal de los 90 a DISPONIBLE»"),
    Transition("RECIBIDO", "RECHAZADO", "CONFIRMATION_REJECT", "021", "inventario:confirm", False, True,
               "flujo «Confirmación: aceptado 90, rechazado 10» · ADR: «no apto; no se incorpora»"),
    Transition("RECIBIDO", "CUARENTENA", "INCIDENT_QUARANTINE", "020", "compras:quality", False, True,
               "flujo «resolución [aceptar / reclamar / devolver / cuarentena]» · INCIDENT_RESOLUTIONS"),
    Transition("RECIBIDO", "BLOQUEADO", "INCIDENT_OPEN", "020", "compras:quality", False, True,
               "ADR §Problema «bloqueado por incidencia» · R-D0-10-6"),
    Transition("BLOQUEADO", "RECIBIDO", "INCIDENT_CLOSE", "020", "compras:quality", False, True,
               "R-D0-10-6: «solo se libera cerrando la incidencia que lo originó»"),
    Transition("CUARENTENA", "DISPONIBLE", "FORMAL_RELEASE", "021", "inventario:confirm", False, True,
               "R-D0-10-4 — la cuarentena está en la cadena de recepción"),
    Transition("CUARENTENA", "RECHAZADO", "QUALITY_REJECT", "021", "inventario:confirm", False, True,
               "ADR: significados de ambos estados · flujo de confirmación"),
    # Las dos primeras aristas que salen de `DISPONIBLE`. La matriz de `D0-10`
    # las declaró —«`DISPONIBLE` | `PICKING` → `PREPARADO` | 031, 032 | Specs no
    # construidas»— y las dejó denegadas por no existir su dueña. Este es el
    # ciclo que la construye.
    #
    # `R-D0-10-10` exigía elegir aquí entre bloquear la salida o reclasificar
    # solo lo no reservado. Ninguna de las dos aplica: sus dos opciones
    # gobiernan la reclasificación **por un tercero** —calidad, que no tiene
    # relación con el cliente—, y el propio análisis del conflicto distingue el
    # caso: «allí el que libera es el proceso de preparación, dueño del pedido
    # en ese momento». Aquí quien extrae es el dueño de la reserva.
    Transition("DISPONIBLE", "PICKING", "PICK_EXECUTION", "032", "ventas:create", False, False,
               "DOCX ¶37 «Extrae la mercancía» · matriz D0-10 fila DISPONIBLE → PICKING (dueñas 031/032)"),
    Transition("PICKING", "PREPARADO", "CONSOLIDATION", "032", "ventas:create", False, False,
               "DOCX ¶55-58 «se concentran como un único pedido… se traslada al Área de Confirmación»"),
)

_BY_PAIR: dict[tuple[str | None, str], Transition] = {
    (t.source, t.target): t for t in ACTIVE_TRANSITIONS
}


def is_valid_state(state: str) -> bool:
    return state in MERCHANDISE_STATES


def assert_valid_state(state: str) -> str:
    """Un estado fuera del catálogo es error de negocio, nunca un 500."""
    if not is_valid_state(state):
        raise KontrolError(
            code="MERCHANDISE_STATE_UNKNOWN",
            message=f"El estado de mercancía «{state}» no existe en el catálogo",
            status_code=422,
            details={"allowed": list(MERCHANDISE_STATES)})
    return state


def is_sellable(state: str) -> bool:
    return state in SELLABLE_STATES


def is_reservable(state: str) -> bool:
    return state in RESERVABLE_STATES


def find_transition(source: str | None, target: str) -> Transition | None:
    return _BY_PAIR.get((source, target))


def can_transition(source: str | None, target: str) -> bool:
    """`R-D0-10-7`: lo no declarado está prohibido. Sin inferencia por parecido."""
    return (source, target) in _BY_PAIR


def assert_transition(source: str | None, target: str) -> Transition:
    """Devuelve la arista o rechaza **antes** de tocar existencias.

    El rechazo no distingue entre «no existe» y «existe pero es futura»: para el
    motor las dos son lo mismo, y `R-D0-10-7` no admite un tercer resultado.
    """
    assert_valid_state(target)
    if source is not None:
        assert_valid_state(source)
    transition = _BY_PAIR.get((source, target))
    if transition is None:
        desde = source or "(entrada)"
        raise ConflictError(
            code="MERCHANDISE_TRANSITION_DENIED",
            message=f"La transición de mercancía {desde} → {target} no está declarada.",
            details={"source_state": source, "target_state": target,
                     "declared": sorted(f"{s or '(entrada)'}→{t}" for s, t in _BY_PAIR)})
    return transition
