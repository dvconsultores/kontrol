"""Carreras forzadas contra PostgreSQL, sin depender de la suerte.

Dos hilos con una barrera no garantizan que las dos transacciones pasen la
comprobación previa antes de insertar: casi siempre una llega tarde, ve la fila
de la otra y se rechaza por la vía cómoda. Una prueba así pasa aunque la captura
de la colisión no exista, y una mutación que la quite sobrevive por azar.

Aquí la carrera se **fuerza**. La primera transacción inserta y se queda sin
confirmar; la segunda arranca, no puede ver esa fila —`READ COMMITTED`—, pasa la
comprobación y queda bloqueada en el índice único. Solo cuando PostgreSQL la
muestra esperando un bloqueo se confirma la primera, y la segunda recibe la
colisión de verdad. Siempre por el camino difícil.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker


def _esperando_bloqueo(factory: sessionmaker, pid: int, plazo: float) -> bool:
    fin = time.monotonic() + plazo
    while time.monotonic() < fin:
        vigia = factory()
        try:
            espera = vigia.execute(
                text("SELECT wait_event_type FROM pg_stat_activity WHERE pid = :pid"),
                {"pid": pid}).scalar()
        finally:
            vigia.close()
        if espera == "Lock":
            return True
        time.sleep(0.05)
    return False


def carrera(factory: sessionmaker,
            primero: Callable[[Session], Any],
            segundo: Callable[[Session], Any]) -> tuple[Any, Any]:
    """Ejecuta `primero` sin confirmar, fuerza a `segundo` a chocar, y confirma.

    Devuelve `(resultado_primero, resultado_segundo)`. Si `segundo` lanza, su
    resultado es la excepción: la prueba decide qué excepción es aceptable.
    Si `segundo` nunca llega a bloquearse, la prueba falla —no se certifica una
    carrera que no ocurrió—.
    """
    s1, s2 = factory(), factory()
    salida: dict[str, Any] = {}
    try:
        r1 = primero(s1)
        s1.flush()
        pid2 = s2.execute(text("SELECT pg_backend_pid()")).scalar()

        def ejecutar() -> None:
            try:
                salida["r"] = segundo(s2)
                s2.commit()
            except Exception as e:  # noqa: BLE001 - el resultado es la excepción
                s2.rollback()
                salida["r"] = e

        hilo = threading.Thread(target=ejecutar)
        hilo.start()
        bloqueado = _esperando_bloqueo(factory, pid2, plazo=15)
        s1.commit()
        hilo.join(timeout=30)
        assert bloqueado, "la segunda transacción nunca chocó: no hubo carrera que probar"
        assert not hilo.is_alive(), "la segunda transacción no terminó"
        return r1, salida.get("r")
    finally:
        s1.close()
        s2.close()


def esperar_bloqueados(factory: sessionmaker, cuantos: int, *, excluir: int, plazo: float = 20) -> bool:
    """`True` cuando al menos `cuantos` conexiones de esta base, sin contar `excluir`, esperan un bloqueo.

    Sirve cuando quien choca es una petición HTTP —o varias—, cuyo `pid` no se
    conoce de antemano. La prueba mantiene abierta la transacción que bloquea,
    espera aquí y solo entonces confirma: la carrera ocurrió, no se supuso.
    """
    fin = time.monotonic() + plazo
    while time.monotonic() < fin:
        vigia = factory()
        try:
            esperando = vigia.execute(text(
                "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() "
                "AND wait_event_type = 'Lock' AND pid <> :pid"), {"pid": excluir}).scalar()
        finally:
            vigia.close()
        if esperando >= cuantos:
            return True
        time.sleep(0.05)
    return False


def empresa_nueva(factory: sessionmaker, tenant_id: str, marca: str) -> str:
    """Una empresa sin catálogo: la única en la que «todavía no existe» es cierto."""
    from app.modules.organization.models import Company

    db = factory()
    try:
        empresa = Company(tenant_id=tenant_id, code=f"CR-{marca}", legal_name=f"Carrera {marca}",
                          rif=f"J-{marca[:8]}", functional_currency="VED", created_by="qa")
        db.add(empresa)
        db.commit()
        return str(empresa.id)
    finally:
        db.close()
