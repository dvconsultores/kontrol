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

La zona de negocio es constante (OD-TIME-01, ADR-020) y no se lee de la
configuración. Los límites de día y de período son semiabiertos: [inicio, fin).
"""

from __future__ import annotations

import re
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.core.errors import KontrolError

ZONA_DE_NEGOCIO = ZoneInfo("America/Caracas")


def zona_de_negocio() -> ZoneInfo:
    """La zona del calendario de negocio. Constante: America/Caracas (OD-TIME-01)."""
    return ZONA_DE_NEGOCIO


def instante_actual() -> datetime:
    """El instante técnico actual, en UTC. Es la única costura del reloj: las pruebas la sustituyen."""
    return datetime.now(UTC)


def ahora_de_negocio(instante: datetime | None = None) -> datetime:
    """El instante dado —o el actual— visto desde el calendario de negocio.

    Recibe el instante por parámetro para que se pueda probar sin tocar el entorno:
    sobre un instante fijo la respuesta es siempre la misma, corra donde corra.
    Un `datetime` sin zona se interpreta como UTC, que es como los guarda la base.
    """
    if instante is None:
        instante = instante_actual()
    elif instante.tzinfo is None:
        instante = instante.replace(tzinfo=UTC)
    return instante.astimezone(zona_de_negocio())


def hoy_de_negocio(instante: datetime | None = None) -> date:
    """El día del calendario de negocio. Lo que antes se pedía a `date.today()`."""
    return ahora_de_negocio(instante).date()


def inicio_del_dia_de_negocio(dia: date) -> datetime:
    """El inicio civil (medianoche) del día dado en la zona de negocio."""
    return datetime(dia.year, dia.month, dia.day, tzinfo=ZONA_DE_NEGOCIO)


def limites_del_dia_utc(dia: date) -> tuple[datetime, datetime]:
    """Límites semiabiertos UTC del día civil dado: [inicio, inicio_del_siguiente)."""
    inicio = inicio_del_dia_de_negocio(dia)
    fin = inicio_del_dia_de_negocio(dia + timedelta(days=1))
    return inicio.astimezone(UTC), fin.astimezone(UTC)


_PATRON_PERIODO = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def periodo_valido(texto: str) -> tuple[int, int]:
    """Valida y descompone un período «AAAA-MM»; lanza `KontrolError` si no es válido."""
    if not _PATRON_PERIODO.fullmatch(texto):
        raise KontrolError(
            code="INVALID_PERIOD",
            message="El período debe tener el formato AAAA-MM.",
            field_errors={"period": ["Formato AAAA-MM, mes 01 a 12."]},
            status_code=422,
        )
    return int(texto[:4]), int(texto[5:7])


def limites_del_periodo_utc(periodo: str) -> tuple[datetime, datetime]:
    """Límites semiabiertos UTC del mes dado: [1.º a las 00:00, 1.º del mes siguiente)."""
    año, mes = periodo_valido(periodo)
    inicio = datetime(año, mes, 1, tzinfo=ZONA_DE_NEGOCIO)
    fin_mes = 1 if mes == 12 else mes + 1
    fin_año = año + 1 if mes == 12 else año
    fin = datetime(fin_año, fin_mes, 1, tzinfo=ZONA_DE_NEGOCIO)
    return inicio.astimezone(UTC), fin.astimezone(UTC)
