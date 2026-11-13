"""Condición del proceso de recepción (Spec 018 · §3).

La fila «Estados recibido, disponible, pendiente, bloqueado» del DOCX se cierra
como **condición del proceso**, no como estado físico del inventario: la
decisión de la dueña mantiene intacta la de la Spec 020 —una incidencia no toca
el stock— y esta condición solo describe en qué punto del procedimiento está la
recepción.

No hay columna nueva ni motor paralelo: la condición se deriva del estado real
de la recepción, de su confirmación de inventario (Spec 021) y de las
incidencias vivas (Spec 020). Por eso se calcula aquí, en el backend, y las dos
superficies de producto —Recepciones y el expediente de Importación— consumen
este mismo resultado.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.purchasing.models import (
    CONFIRMATION_DONE,
    GoodsReceipt,
    ReceiptIncident,
)

RECIBIDO = "RECIBIDO"
PENDIENTE_DE_VALIDACION = "PENDIENTE_DE_VALIDACION"
BLOQUEADO_POR_INCIDENCIA = "BLOQUEADO_POR_INCIDENCIA"

#: Orden de precedencia: la primera que aplica es la condición visible.
CONDICIONES_DEL_PROCESO = (
    BLOQUEADO_POR_INCIDENCIA,
    PENDIENTE_DE_VALIDACION,
    RECIBIDO,
)

#: Texto humano. El código interno no se muestra en pantalla.
ETIQUETAS = {
    RECIBIDO: "Recibido",
    PENDIENTE_DE_VALIDACION: "Pendiente de validación",
    BLOQUEADO_POR_INCIDENCIA: "Bloqueado por incidencia",
}

#: Por qué la recepción está donde está. Se calcula aquí para que las dos
#: pantallas digan lo mismo y el frontend no invente su propia explicación.
_MOTIVOS = {
    RECIBIDO: None,
    PENDIENTE_DE_VALIDACION: "Falta confirmar el inventario de la recepción.",
    BLOQUEADO_POR_INCIDENCIA:
        "No se puede confirmar el inventario mientras existan incidencias sin resolver.",
}

#: Una incidencia deja de bloquear cuando se resuelve o se anula. El resto de
#: estados —incluida `PENDIENTE_AUTORIZACION`— impide confirmar y, por tanto,
#: bloquea la condición. Es el mismo conjunto que consume la Spec 021.
ESTADOS_TERMINALES_DE_INCIDENCIA = ("RESUELTA", "ANULADA")

#: Recepciones sin condición de proceso: su documento terminó fuera del flujo
#: normal (anulada o rechazada). No son una cuarta condición; la pantalla sigue
#: mostrando el estado del documento, que ya existe.
ESTADOS_SIN_CONDICION = ("CANCELLED", "REJECTED")


def _aplica(receipt: GoodsReceipt) -> bool:
    return receipt.status not in ESTADOS_SIN_CONDICION and receipt.quality_status != "REJECTED"


def _codigo(receipt: GoodsReceipt, bloqueantes: int) -> str:
    if bloqueantes:
        return BLOQUEADO_POR_INCIDENCIA
    if receipt.confirmation_status == CONFIRMATION_DONE:
        return RECIBIDO
    return PENDIENTE_DE_VALIDACION


def _describir(receipt: GoodsReceipt, bloqueantes: list[Any]) -> dict[str, Any] | None:
    if not _aplica(receipt):
        return None
    codigo = _codigo(receipt, len(bloqueantes))
    return {
        "code": codigo,
        "label": ETIQUETAS[codigo],
        "blocking_incidents": len(bloqueantes),
        "incidents": [{"id": str(x.id), "code": x.code} for x in bloqueantes],
        "reason": _MOTIVOS[codigo],
    }


def _incidencias_bloqueantes(
    db: Session, receipts: Iterable[GoodsReceipt]
) -> dict[str, list[Any]]:
    aplicables = [receipt for receipt in receipts if _aplica(receipt)]
    por_recepcion: dict[str, list[Any]] = {}
    if not aplicables:
        return por_recepcion

    ids = [receipt.id for receipt in aplicables]
    empresas = {str(receipt.company_id) for receipt in aplicables}
    filas = db.execute(
        select(
            ReceiptIncident.id,
            ReceiptIncident.receipt_id,
            ReceiptIncident.code,
            ReceiptIncident.status,
        )
        .where(
            ReceiptIncident.receipt_id.in_(ids),
            ReceiptIncident.company_id.in_(empresas),
            ReceiptIncident.status.notin_(ESTADOS_TERMINALES_DE_INCIDENCIA),
        )
        .order_by(ReceiptIncident.created_at, ReceiptIncident.id)
    ).all()
    for fila in filas:
        por_recepcion.setdefault(str(fila.receipt_id), []).append(fila)
    return por_recepcion


def condiciones_por_recepcion(
    db: Session, receipts: Iterable[GoodsReceipt]
) -> dict[str, dict[str, Any] | None]:
    """Condición de cada recepción, con una sola consulta para todas.

    La clave es el id de la recepción y el valor es `None` cuando la condición
    no aplica (anulada o rechazada).
    """
    receipts = list(receipts)
    bloqueantes = _incidencias_bloqueantes(db, receipts)
    return {
        str(receipt.id): _describir(receipt, bloqueantes.get(str(receipt.id), []))
        for receipt in receipts
    }


def condicion_de_recepcion(db: Session, receipt: GoodsReceipt) -> dict[str, Any] | None:
    return condiciones_por_recepcion(db, [receipt])[str(receipt.id)]
