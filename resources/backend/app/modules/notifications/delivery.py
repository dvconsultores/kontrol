"""Frontera de entrega externa (Spec 047 · FR-047-019..022).

# Spec 047 · Frontera de entrega externa

La 047 compone la intención y lleva el estado; **el proveedor es de la 048**.
En producción el registro está vacío: no hay correo, push ni SMS, y ninguna
entrega se declara enviada. Una prueba puede registrar un proveedor en la
frontera para demostrar que un fallo externo no toca la notificación interna.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

from sqlalchemy import or_, select

from app.core.logging import get_logger
from app.modules.notifications.messages import renderizar
from app.modules.notifications.models import Notification, NotificationDelivery, NotificationRecipient

log = get_logger("kontrol.spec047.delivery")


@dataclass(frozen=True)
class Envio:
    #: Clave de idempotencia para el proveedor: la entrega, no un UUID nuevo.
    delivery_id: str
    channel: str
    user_id: str
    company_id: str
    text: str


class ProveedorExterno(Protocol):
    """Contrato que implementará un adaptador de la 048."""

    max_intentos: int
    espera_entre_intentos: timedelta

    def enviar(self, envio: Envio) -> None: ...


#: Canal → proveedor. Vacío en producción.
PROVEEDORES: dict[str, ProveedorExterno] = {}


def entregar(contexto) -> object:
    """Manejador `notification_delivery` (política `DUE_RETRY`)."""
    from app.modules.scheduler.service import Resultado

    resultado = Resultado()
    with contexto.session_factory() as db:
        pendientes = db.execute(
            select(NotificationDelivery.id)
            .where(NotificationDelivery.status.in_(("PENDING", "RETRYING")),
                   or_(NotificationDelivery.next_attempt_at.is_(None),
                       NotificationDelivery.next_attempt_at <= contexto.now))
            .order_by(NotificationDelivery.created_at, NotificationDelivery.id)
        ).scalars().all()

    for delivery_id in pendientes:
        resultado.seen += 1
        with contexto.session_factory() as db:
            entrega = db.execute(
                select(NotificationDelivery).where(NotificationDelivery.id == delivery_id)
                .with_for_update(skip_locked=True)
            ).scalars().first()
            if entrega is None or entrega.status not in ("PENDING", "RETRYING"):
                resultado.skipped += 1
                continue
            destinatario = db.get(NotificationRecipient, entrega.recipient_id)
            notificacion = db.get(Notification, destinatario.notification_id) if destinatario else None
            proveedor = PROVEEDORES.get(entrega.channel)
            if proveedor is None or notificacion is None:
                entrega.status = "FAILED"
                entrega.last_error_code = "CHANNEL_UNAVAILABLE"
                db.commit()
                resultado.failed += 1
                continue
            render = renderizar(notificacion.message_key, notificacion.message_params)
            entrega.attempts += 1
            log.info("spec047.delivery_attempted", extra={"delivery_id": str(entrega.id),
                                                          "channel": entrega.channel})
            try:
                proveedor.enviar(Envio(delivery_id=str(entrega.id), channel=entrega.channel,
                                       user_id=destinatario.user_id,
                                       company_id=entrega.company_id, text=render.text or ""))
            except Exception as error:  # el proveedor es ajeno: cualquier fallo es un fallo de canal
                entrega.last_error_code = type(error).__name__[:64]
                if entrega.attempts >= proveedor.max_intentos:
                    entrega.status = "FAILED"
                else:
                    entrega.status = "RETRYING"
                    entrega.next_attempt_at = _siguiente(contexto.now, proveedor.espera_entre_intentos)
                log.info("spec047.delivery_failed", extra={"delivery_id": str(entrega.id),
                                                           "error_code": entrega.last_error_code})
                db.commit()
                resultado.failed += 1
                continue
            entrega.status = "SENT"
            entrega.sent_at = contexto.now
            entrega.last_error_code = None
            db.commit()
            resultado.processed += 1
    return resultado


def _siguiente(ahora: datetime, espera: timedelta) -> datetime:
    return ahora + espera
