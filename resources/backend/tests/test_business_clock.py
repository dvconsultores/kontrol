"""Spec 001 · POLICY-CLOCK-LOCAL — el día de negocio es el de Caracas, no el del anfitrión.

La auditoría lo demostró con dos políticas y un reloj: a las 02:36 UTC del 17 de
septiembre, en Caracas todavía era el 16, y KONTROL elegía la política del 17 porque
preguntaba `date.today()` al proceso. Cuatro horas cada día aplicando la regla del día
siguiente, sin que nada avisara.

Lo que estas pruebas fijan es la separación que faltaba: el **instante técnico** sigue
siendo UTC —sellos, auditoría, planificador— y el **día de negocio** es el del calendario
de Caracas, venga el proceso de donde venga.
"""

from __future__ import annotations

import os
import time
from datetime import UTC, date, datetime, timedelta

import pytest

from app.shared.clock import ahora_de_negocio, hoy_de_negocio

pytest_plugins = ("tests.conftest_multicompany",)

#: El instante de la auditoría: en UTC es el 17; en Caracas, el 16.
INSTANTE = datetime(2026, 9, 17, 2, 36, tzinfo=UTC)
#: Cuatro zonas reales, dos de ellas en un día civil distinto del de Caracas.
ZONAS = ("UTC", "America/Caracas", "Europe/Amsterdam", "Pacific/Kiritimati")


def _bajo(zona: str, funcion):
    """Ejecuta `funcion` con el proceso en `zona` y restituye la del entorno."""
    original = os.environ.get("TZ")
    try:
        os.environ["TZ"] = zona
        time.tzset()
        return funcion()
    finally:
        if original is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = original
        time.tzset()


# --------------------------------------------------------------------------- #
# El ayudante
# --------------------------------------------------------------------------- #
def test_el_dia_de_negocio_es_el_de_caracas():
    assert hoy_de_negocio(INSTANTE) == date(2026, 9, 16)
    assert ahora_de_negocio(INSTANTE).isoformat() == "2026-09-16T22:36:00-04:00"


@pytest.mark.parametrize("zona", ZONAS)
def test_el_dia_de_negocio_no_cambia_con_la_zona_del_proceso(zona):
    """El mismo instante absoluto da el mismo día de negocio, corra donde corra."""
    assert _bajo(zona, lambda: hoy_de_negocio(INSTANTE)) == date(2026, 9, 16)


@pytest.mark.parametrize("zona", ZONAS)
def test_sin_instante_tampoco_depende_del_proceso(zona):
    """Sin argumento parte de `now(UTC)`: lo que no puede es leer el reloj local."""
    esperado = datetime.now(UTC).astimezone(ahora_de_negocio(INSTANTE).tzinfo).date()
    obtenido = _bajo(zona, hoy_de_negocio)
    assert obtenido == esperado, f"en {zona} el día de negocio fue {obtenido}"


def test_un_instante_sin_zona_se_lee_como_utc():
    """Es como los devuelve la base cuando el motor no conserva la zona."""
    assert hoy_de_negocio(datetime(2026, 9, 17, 2, 36)) == date(2026, 9, 16)


def test_la_frontera_del_dia_esta_donde_dice_caracas():
    """Las 00:00 de Caracas son las 04:00 UTC: ni un minuto antes."""
    assert hoy_de_negocio(datetime(2026, 9, 17, 3, 59, tzinfo=UTC)) == date(2026, 9, 16)
    assert hoy_de_negocio(datetime(2026, 9, 17, 4, 0, tzinfo=UTC)) == date(2026, 9, 17)


# --------------------------------------------------------------------------- #
# La política, que es donde se vio
# --------------------------------------------------------------------------- #
def _dos_politicas(db, empresa):
    from app.modules.treasury import rates as rz

    for codigo, desde in (("PCL-16", date(2026, 9, 16)), ("PCL-17", date(2026, 9, 17))):
        p = rz.create_policy(db, company_id=empresa, policy_code=codigo, effective_from=desde,
                             authority_reference="Pendiente de validación legal (D0-07)",
                             actor="qa")
        p.status = "ACTIVE"
        db.flush()


@pytest.mark.parametrize("zona", ZONAS)
def test_la_politica_vigente_no_depende_de_la_zona_del_proceso(mundo, zona):
    """El caso exacto de la auditoría, ahora como regresión permanente."""
    from app.modules.treasury import rates as rz

    db = mundo.factory()
    try:
        _dos_politicas(db, mundo.company_a)
        elegida = _bajo(zona, lambda: rz.active_policy(
            db, mundo.company_a, hoy_de_negocio(INSTANTE)))
        assert elegida is not None and elegida.policy_code == "PCL-16", (
            f"en {zona} rigió {elegida.policy_code if elegida else 'ninguna'}")
    finally:
        db.close()


@pytest.mark.parametrize("zona", ZONAS)
def test_sin_fecha_la_politica_sale_del_calendario_de_negocio(mundo, zona):
    """El respaldo, que es donde vivía el defecto.

    La prueba anterior pasa la fecha explícita y por tanto no ve el `or` del
    servicio. Aquí no se pasa ninguna: se siembra una política vigente desde el día
    de negocio y otra desde el siguiente, y se exige que rija la primera. Si el
    respaldo vuelve a preguntar el día al proceso, en las zonas que van por delante
    de Caracas elegirá la de mañana.
    """
    from app.modules.treasury import rates as rz

    db = mundo.factory()
    try:
        hoy = hoy_de_negocio()
        for codigo, desde in ((f"PCB-{zona[:3]}-H", hoy), (f"PCB-{zona[:3]}-M", hoy + timedelta(days=1))):
            p = rz.create_policy(db, company_id=mundo.company_a, policy_code=codigo,
                                 effective_from=desde,
                                 authority_reference="Pendiente de validación legal (D0-07)",
                                 actor="qa")
            p.status = "ACTIVE"
            db.flush()
        elegida = _bajo(zona, lambda: rz.active_policy(db, mundo.company_a))
        assert elegida is not None, "no rigió ninguna política"
        assert elegida.effective_from == hoy, (
            f"en {zona} rigió la del {elegida.effective_from} en vez de la del {hoy}")
    finally:
        db.close()


def test_una_fecha_explicita_manda_sobre_el_hoy_de_negocio(mundo):
    """El respaldo es respaldo: si la operación trae fecha, decide ella."""
    from app.modules.treasury import rates as rz

    db = mundo.factory()
    try:
        _dos_politicas(db, mundo.company_a)
        explicita = rz.active_policy(db, mundo.company_a, date(2026, 9, 17))
        assert explicita is not None and explicita.policy_code == "PCL-17"
    finally:
        db.close()


# --------------------------------------------------------------------------- #
# Lo que NO cambia
# --------------------------------------------------------------------------- #
def test_los_instantes_tecnicos_siguen_siendo_utc_con_zona():
    """`ADR-D0-001` no se toca: los sellos técnicos son instantes absolutos."""
    from app.shared.mixins import utcnow

    def comprobar():
        ahora = utcnow()
        assert ahora.tzinfo is not None, "un sello técnico perdió la zona"
        assert ahora.utcoffset() == timedelta(0), f"un sello técnico dejó de ser UTC: {ahora}"
        return ahora

    for zona in ZONAS:
        _bajo(zona, comprobar)


def test_las_fronteras_de_licencia_son_las_de_caracas():
    """Ya lo eran —el contrato emite el desfase—, y aquí queda fijado.

    La auditoría previa afirmó que se evaluaban en UTC. No era cierto: lo que llega
    firmado trae `-04:00`, y `compute_mode` compara instantes. Esta prueba impide que
    alguien «simplifique» el contrato a fechas sin zona y lo rompa sin enterarse.
    """
    from app.core.license import compute_mode, parse_license_payload

    licencia = parse_license_payload({
        "license_id": "L-TZ", "installation_id": "I-TZ",
        "period_start": "2026-04-01T00:00:00-04:00",
        "period_end": "2027-03-31T23:59:59-04:00",
        "critical_warning_start": "2027-04-21T00:00:00-04:00",
        "read_only_start": "2027-05-01T00:00:00-04:00",
    })
    # 1 de mayo 00:00 en UTC son todavía las 20:00 del 30 de abril en Caracas.
    assert compute_mode(licencia, datetime(2027, 5, 1, 0, 0, tzinfo=UTC)) == "CRITICAL_RENEWAL_NOTICE"
    assert compute_mode(licencia, datetime(2027, 5, 1, 3, 59, tzinfo=UTC)) == "CRITICAL_RENEWAL_NOTICE"
    # 00:00 de Caracas son las 04:00 UTC: ahí sí.
    assert compute_mode(licencia, datetime(2027, 5, 1, 4, 0, tzinfo=UTC)) == "READ_ONLY"
