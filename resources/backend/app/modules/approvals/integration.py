"""Integración de los dominios con el motor de aprobaciones (Spec 045, F6).

Punto único por el que los dominios consultan el motor. Vive en `approvals`
para que ningún módulo de dominio duplique la lógica (Constitución P22,
FR-045-075) y para que el motor siga sin importar dominios (`plan.md` §1).

**Compatibilidad (AC-20).** Si la empresa no tiene política activa para el
proceso, `require_for_document` no exige nada y el dominio avanza igual que
antes de esta Spec. El control de permiso propio de cada dominio se conserva:
el motor *añade* aprobación por política, no *sustituye* la autorización.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import ConflictError
from app.modules.approvals import service as approvals_service

# Tipos de proceso que los dominios usan hoy. Es un catálogo de constantes de
# integración, NO una política: no fija niveles, umbrales ni aprobadores (P8).
PROCESS_PURCHASE_REQUISITION = "PURCHASE_REQUISITION"
PROCESS_PURCHASE_ORDER = "PURCHASE_ORDER"
PROCESS_SALES_CREDIT = "SALES_CREDIT"
PROCESS_INVENTORY_ADJUSTMENT = "INVENTORY_ADJUSTMENT"
PROCESS_INVENTORY_COUNT = "INVENTORY_COUNT"
PROCESS_REGULATORY_APPROVAL = "REGULATORY_APPROVAL"


def require_for_document(db: Session, *, company_id: str, process_type: str, document_type: str,
                         document_id: str, context: dict[str, Any],
                         actor: str | None = None) -> dict[str, Any]:
    """Solicita aprobación si la política lo exige. Idempotente."""
    return approvals_service.require(
        db, company_id=company_id, process_type=process_type, document_type=document_type,
        document_id=document_id, context=context, actor=actor)


def ensure_approved(db: Session, *, company_id: str, document_type: str, document_id: str,
                    what: str = "el documento") -> None:
    """Impide avanzar mientras haya una solicitud viva (FR-045-029).

    No exige que exista aprobación: exige que, si el motor abrió una solicitud,
    esté resuelta favorablemente. Sin política, no hay solicitud y no bloquea.
    """
    state = approvals_service.status(db, company_id=company_id, document_type=document_type,
                                     document_id=document_id)
    if state["blocks_advance"]:
        raise ConflictError(
            code="APPROVAL_PENDING",
            message=f"No es posible avanzar {what}: la aprobación está pendiente.")
    current = state["current"]
    if current and current["status"] in {"REJECTED", "OBSOLETE"}:
        raise ConflictError(
            code="APPROVAL_NOT_GRANTED",
            message=f"No es posible avanzar {what}: la aprobación fue "
                    f"{'rechazada' if current['status'] == 'REJECTED' else 'invalidada por un cambio'}.")


def notify_document_changed(db: Session, *, company_id: str, document_type: str, document_id: str,
                            context: dict[str, Any]) -> int:
    """El documento cambió: invalida solicitudes que ya no le corresponden."""
    return approvals_service.document_changed(
        db, company_id=company_id, document_type=document_type,
        document_id=document_id, context=context)
