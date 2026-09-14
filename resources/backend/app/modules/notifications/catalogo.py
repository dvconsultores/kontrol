"""Qué hechos sabe consumir la 047 y adónde lleva cada origen (Spec 047).

# Spec 047 · Catálogo de fuentes y orígenes

Es un registro explícito en código: ni rutas ni eventos se configuran desde la
base. Añadir una fuente es añadir aquí su contrato y su prueba.
"""

from __future__ import annotations

from dataclasses import dataclass

FUENTE_APROBACION = "APPROVAL"

#: Hechos de la 045 que pueden producir efectos, con los efectos admitidos.
EVENTOS_CONSUMIBLES: dict[str, dict[str, frozenset[str]]] = {
    FUENTE_APROBACION: {
        "approval.step_opened": frozenset({"NOTIFICATION", "TASK", "ALERT"}),
        "approval.step_expired": frozenset({"NOTIFICATION", "TASK", "ALERT"}),
    },
}

#: Hechos de la 045 que cierran lo que abrieron las reglas con `auto_close`.
EVENTOS_DE_CIERRE = frozenset({"approval.decided", "approval.resolved", "approval.obsolete"})


@dataclass(frozen=True)
class Origen:
    route_key: str
    recurso: str
    accion: str

    @property
    def permiso(self) -> str:
        return f"{self.recurso}:{self.accion}"


#: El permiso que exige ver el recurso origen. Sin él, el ítem no es visible
#: (FR-047-014, FR-047-032): coincide con el de `GET /approvals/requests/{id}`.
ORIGENES: dict[str, Origen] = {
    "ApprovalRequest": Origen(route_key="approval_inbox", recurso="aprobaciones", accion="view"),
}

CATEGORIA_RECORDATORIO = "task.reminder"
CATEGORIA_ESCALADA = "task.escalation"


def tipos_prohibidos(permisos: set[str]) -> list[str]:
    """Orígenes cuyo recurso no puede ver quien tiene estos permisos."""
    return sorted(t for t, o in ORIGENES.items() if o.permiso not in permisos)
