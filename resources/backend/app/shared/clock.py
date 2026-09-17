"""La fecha de negocio de KONTROL (Spec 001 · POLICY-CLOCK-LOCAL).

Hay dos tiempos en este producto y conviene no confundirlos.

El **instante técnico** es UTC y lo gobierna `ADR-D0-001`: sellos de auditoría,
`created_at`, vencimientos de sesión, comparaciones del planificador. Un instante
no tiene zona de negocio; tiene el momento absoluto en que ocurrió.

El **día de negocio** es otra cosa. Cuando una regla pregunta «qué política rige
hoy», «venció ya esta cotización» o «qué versión de la regla fiscal aplica», no
está preguntando por un instante: está preguntando por el día del calendario en
que opera la empresa. Ese calendario es el de **Caracas**, decidido por la dueña.

Antes de este módulo, esa pregunta se contestaba con `date.today()`, que devuelve
el día civil del proceso —el del contenedor, el del anfitrión, el de la máquina de
quien ejecuta las pruebas—. Con el despliegue en UTC, entre las 20:00 y las 24:00
de Caracas el sistema ya estaba operando en el día siguiente: cuatro horas al día
aplicando la política, la tasa o la regla fiscal equivocada.

La autoridad vive **aquí, en el código**. Fijar `TZ` en el contenedor es un
cinturón de seguridad útil, pero no es la autoridad: las pruebas, los guiones
sueltos y cualquier servidor futuro pueden correr en otra zona, y el resultado
tiene que ser el mismo.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from app.core.config import get_settings


def zona_de_negocio() -> ZoneInfo:
    """La zona del calendario de negocio. Una sola, y declarada en la configuración."""
    return ZoneInfo(get_settings().business_timezone)


def ahora_de_negocio(instante: datetime | None = None) -> datetime:
    """El instante dado —o el actual— visto desde el calendario de negocio.

    Recibe el instante por parámetro para que se pueda probar sin tocar el entorno:
    sobre un instante fijo la respuesta es siempre la misma, corra donde corra.
    Un `datetime` sin zona se interpreta como UTC, que es como los guarda la base.
    """
    if instante is None:
        instante = datetime.now(UTC)
    elif instante.tzinfo is None:
        instante = instante.replace(tzinfo=UTC)
    return instante.astimezone(zona_de_negocio())


def hoy_de_negocio(instante: datetime | None = None) -> date:
    """El día del calendario de negocio. Lo que antes se pedía a `date.today()`."""
    return ahora_de_negocio(instante).date()
