"""La fecha de negocio en las tasas (Spec 001 · Caracas) con motores distintos.

Prueba que el módulo deriva el día de negocio en Caracas, interpreta las fechas
del CSV en Caracas y normaliza a UTC todo instante que persiste, para que
PostgreSQL y SQLite guarden lo mismo.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from conftest import seed_org_chain
from sqlalchemy import select

from app.modules.treasury import rates as rz
from app.modules.treasury import service as tz
from app.modules.treasury.models import ExchangeRate
from tests.company_seed import EMPRESA_DOS, EMPRESA_UNO

pytest_plugins = ("tests.conftest_multicompany",)


@pytest.fixture()
def db_session(sesion_de_prueba):
    seed_org_chain(sesion_de_prueba, EMPRESA_UNO, EMPRESA_DOS)
    return sesion_de_prueba


def _moneda(db, company_id, codigo):
    """Una moneda del maestro. Si ya está activa, se reutiliza."""
    ya = rz.moneda_por_codigo(db, company_id, codigo)
    if ya is not None:
        return ya
    cur = tz.create_currency(db, company_id=company_id, code=codigo, name=codigo, actor="qa")
    db.flush()
    return cur


def _codigo() -> str:
    """Un código de moneda que no choca con el de otra prueba."""
    return f"Z{uuid4().hex[:5].upper()}"


def _fuente(db, mundo, *, code=None, prioridad=100, manual=True, company_id=None):
    return rz.create_source(db, company_id=company_id or mundo.company_a,
                            code=code or f"SRC-{uuid4().hex[:6]}", name="Fuente de prueba",
                            source_type="OFFICIAL", allows_manual=manual, priority=prioridad,
                            authority_reference="Pendiente de validación legal (D0-07)",
                            actor="qa")


def _sin_politica(db, mundo, company_id=None):
    """La base del arnés es compartida: otra prueba pudo dejar política activa."""
    from app.modules.treasury.models import ExchangeRatePolicy
    for p in db.execute(select(ExchangeRatePolicy).where(
            ExchangeRatePolicy.company_id == (company_id or mundo.company_a),
            ExchangeRatePolicy.status == "ACTIVE")).scalars().all():
        p.status = "SUPERSEDED"
    db.flush()


def _csv(filas: list[str]) -> str:
    cabecera = "base_currency,quote_currency,rate,effective_at"
    return "\n".join([cabecera, *filas]) + "\n"


def _utc(v):
    return (v if v.tzinfo else v.replace(tzinfo=UTC)).astimezone(UTC)


def _dos_politicas_27_28(db, mundo):
    _sin_politica(db, mundo)
    sufijo = uuid4().hex[:6]
    p27 = rz.create_policy(db, company_id=mundo.company_a,
                           policy_code=f"PCD-27-{sufijo}", effective_from=date(2026, 10, 27),
                           allow_inversion=True,
                           authority_reference="Pendiente de validación legal (D0-07)",
                           actor="qa")
    p27.status = "ACTIVE"
    db.flush()
    p28 = rz.create_policy(db, company_id=mundo.company_a,
                           policy_code=f"PCD-28-{sufijo}", effective_from=date(2026, 10, 28),
                           allow_inversion=False,
                           authority_reference="Pendiente de validación legal (D0-07)",
                           actor="qa")
    p28.status = "ACTIVE"
    db.flush()


def test_la_rate_date_de_las_2330_de_caracas_es_la_del_dia_de_caracas(mundo):
    db = mundo.factory()
    try:
        funcional = rz.moneda_funcional(db, mundo.company_a)
        _moneda(db, mundo.company_a, funcional)
        a = _moneda(db, mundo.company_a, _codigo())
        fuente = _fuente(db, mundo)
        _dos_politicas_27_28(db, mundo)

        obs = rz.register_rate(
            db, company_id=mundo.company_a, base_code=a.code, quote_code=funcional,
            rate="40", effective_at=datetime(2026, 10, 28, 3, 30, tzinfo=UTC),
            source_id=str(fuente.id), actor="qa")

        assert obs.rate_date == date(2026, 10, 27)
    finally:
        db.close()


def test_la_politica_de_una_consulta_a_las_2330_es_la_del_dia_de_caracas(mundo):
    db = mundo.factory()
    try:
        funcional = rz.moneda_funcional(db, mundo.company_a)
        _moneda(db, mundo.company_a, funcional)
        a = _moneda(db, mundo.company_a, _codigo())
        fuente = _fuente(db, mundo)
        _dos_politicas_27_28(db, mundo)

        rz.register_rate(
            db, company_id=mundo.company_a, base_code=funcional, quote_code=a.code,
            rate="0.025", effective_at=datetime(2026, 10, 27, 15, 0, tzinfo=UTC),
            source_id=str(fuente.id), actor="qa")
        db.flush()

        res = rz.resolve_rate(
            db, company_id=mundo.company_a, base_code=a.code, quote_code=funcional,
            effective_at=datetime(2026, 10, 28, 3, 30, tzinfo=UTC))

        assert res.derived == "INVERSE"
    finally:
        db.close()


def test_una_fecha_registrada_rige_desde_las_cero_de_caracas_en_ambos_motores(mundo):
    db = mundo.factory()
    try:
        funcional = rz.moneda_funcional(db, mundo.company_a)
        _moneda(db, mundo.company_a, funcional)
        a = _moneda(db, mundo.company_a, _codigo())
        fuente = _fuente(db, mundo)
        _dos_politicas_27_28(db, mundo)

        obs = rz.register_rate(
            db, company_id=mundo.company_a, base_code=a.code, quote_code=funcional,
            rate="40", effective_at=date(2026, 10, 27),
            source_id=str(fuente.id), actor="qa")
        db.flush()
        db.expire(obs)

        assert _utc(obs.effective_at) == datetime(2026, 10, 27, 4, 0, tzinfo=UTC)
    finally:
        db.close()


def test_un_instante_con_desfase_de_caracas_se_guarda_como_el_mismo_instante(mundo):
    db = mundo.factory()
    try:
        funcional = rz.moneda_funcional(db, mundo.company_a)
        _moneda(db, mundo.company_a, funcional)
        a = _moneda(db, mundo.company_a, _codigo())
        fuente = _fuente(db, mundo)
        _dos_politicas_27_28(db, mundo)

        obs = rz.register_rate(
            db, company_id=mundo.company_a, base_code=a.code, quote_code=funcional,
            rate="40",
            effective_at=datetime(2026, 10, 27, 23, 30, tzinfo=ZoneInfo("America/Caracas")),
            source_id=str(fuente.id), actor="qa")
        db.flush()
        db.expire(obs)

        assert _utc(obs.effective_at) == datetime(2026, 10, 28, 3, 30, tzinfo=UTC)
        assert obs.rate_date == date(2026, 10, 27)
    finally:
        db.close()


def test_el_csv_con_fecha_rige_desde_las_cero_de_caracas(mundo):
    db = mundo.factory()
    try:
        funcional = rz.moneda_funcional(db, mundo.company_a)
        _moneda(db, mundo.company_a, funcional)
        a = _moneda(db, mundo.company_a, _codigo())
        fuente = _fuente(db, mundo)
        _dos_politicas_27_28(db, mundo)

        contenido = _csv([f"{a.code},{funcional},100.00,2026-10-27"])
        r = rz.import_rates(db, company_id=mundo.company_a, contenido=contenido,
                            source_id=str(fuente.id),
                            filename=f"t-{uuid4().hex[:6]}.csv", actor="qa")

        assert r["imported"] == 1

        obs = db.execute(select(ExchangeRate).where(
            ExchangeRate.company_id == mundo.company_a,
            ExchangeRate.base_currency_id == str(a.id))).scalars().one()

        assert _utc(obs.effective_at) == datetime(2026, 10, 27, 4, 0, tzinfo=UTC)
    finally:
        db.close()


def test_el_csv_con_hora_sin_zona_es_hora_de_caracas(mundo):
    db = mundo.factory()
    try:
        funcional = rz.moneda_funcional(db, mundo.company_a)
        _moneda(db, mundo.company_a, funcional)
        a = _moneda(db, mundo.company_a, _codigo())
        fuente = _fuente(db, mundo)
        _dos_politicas_27_28(db, mundo)

        contenido = _csv([f"{a.code},{funcional},100.00,2026-10-27T23:30:00"])
        r = rz.import_rates(db, company_id=mundo.company_a, contenido=contenido,
                            source_id=str(fuente.id),
                            filename=f"t-{uuid4().hex[:6]}.csv", actor="qa")

        assert r["imported"] == 1

        obs = db.execute(select(ExchangeRate).where(
            ExchangeRate.company_id == mundo.company_a,
            ExchangeRate.base_currency_id == str(a.id))).scalars().one()

        assert _utc(obs.effective_at) == datetime(2026, 10, 28, 3, 30, tzinfo=UTC)
        assert obs.rate_date == date(2026, 10, 27)
    finally:
        db.close()


def test_el_csv_con_desfase_explicito_se_respeta(mundo):
    db = mundo.factory()
    try:
        funcional = rz.moneda_funcional(db, mundo.company_a)
        _moneda(db, mundo.company_a, funcional)
        a = _moneda(db, mundo.company_a, _codigo())
        fuente = _fuente(db, mundo)
        _dos_politicas_27_28(db, mundo)

        contenido = _csv([f"{a.code},{funcional},100.00,2026-10-28T03:30:00Z"])
        r = rz.import_rates(db, company_id=mundo.company_a, contenido=contenido,
                            source_id=str(fuente.id),
                            filename=f"t-{uuid4().hex[:6]}.csv", actor="qa")

        assert r["imported"] == 1

        obs = db.execute(select(ExchangeRate).where(
            ExchangeRate.company_id == mundo.company_a,
            ExchangeRate.base_currency_id == str(a.id))).scalars().one()

        assert _utc(obs.effective_at) == datetime(2026, 10, 28, 3, 30, tzinfo=UTC)
    finally:
        db.close()


def test_en_ambos_motores_una_fecha_rige_desde_las_cero_de_caracas(db_session):
    funcional = rz.moneda_funcional(db_session, EMPRESA_UNO)
    _moneda(db_session, EMPRESA_UNO, funcional)
    a = _moneda(db_session, EMPRESA_UNO, _codigo())
    fuente = rz.create_source(
        db_session, company_id=EMPRESA_UNO, code=f"SRC-{uuid4().hex[:6]}",
        name="Fuente de prueba", source_type="OFFICIAL", allows_manual=True,
        priority=100, authority_reference="Pendiente de validación legal (D0-07)",
        actor="qa")
    obs = rz.register_rate(
        db_session, company_id=EMPRESA_UNO, base_code=a.code, quote_code=funcional,
        rate="40", effective_at=date(2026, 10, 27), source_id=str(fuente.id),
        actor="qa")
    db_session.flush()
    db_session.expire(obs)

    assert _utc(obs.effective_at) == datetime(2026, 10, 27, 4, 0, tzinfo=UTC)
    assert obs.rate_date == date(2026, 10, 27)


def test_en_ambos_motores_un_instante_de_caracas_es_el_mismo_instante(db_session):
    funcional = rz.moneda_funcional(db_session, EMPRESA_UNO)
    _moneda(db_session, EMPRESA_UNO, funcional)
    a = _moneda(db_session, EMPRESA_UNO, _codigo())
    fuente = rz.create_source(
        db_session, company_id=EMPRESA_UNO, code=f"SRC-{uuid4().hex[:6]}",
        name="Fuente de prueba", source_type="OFFICIAL", allows_manual=True,
        priority=100, authority_reference="Pendiente de validación legal (D0-07)",
        actor="qa")
    obs = rz.register_rate(
        db_session, company_id=EMPRESA_UNO, base_code=a.code, quote_code=funcional,
        rate="40",
        effective_at=datetime(2026, 10, 27, 23, 30, tzinfo=ZoneInfo("America/Caracas")),
        source_id=str(fuente.id), actor="qa")
    db_session.flush()
    db_session.expire(obs)

    assert _utc(obs.effective_at) == datetime(2026, 10, 28, 3, 30, tzinfo=UTC)
    assert obs.rate_date == date(2026, 10, 27)
