"""PROC-08 × TRE-09 · límite de autoridad multimoneda al adjudicar (delta X08)."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.core.company_context import CompanyContext
from app.core.errors import KontrolError
from app.modules.government.models import (
    GovernmentOfficialExchangeRate,
    GovernmentProcurementDecision,
    GovernmentProcurementOfferDocument,
)
from app.modules.government.service_decision_resolver import registrar_decision
from app.modules.identity_access.models import User
from app.modules.organization.models import Company
from app.shared.clock import hoy_de_negocio
from tests.concurrency import carrera
from tests.proc08_ayudantes import acto_decision
from tests.test_gov_ctl01_reglas import eventos
from tests.test_gov_proc03_expedientes import E
from tests.test_gov_proc06_montos import _insertar_monto
from tests.test_gov_proc08_limite_monto import _adjudicar, _cargo_con_limite, _decisiones, _preparar

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos", "tests.org04_ayudantes")

pytestmark = pytest.mark.skipif(
    "postgresql" not in os.environ.get("KONTROL_TEST_DB_URL", ""),
    reason="La conversión con bloqueo FOR SHARE se verifica sobre PostgreSQL",
)


def _tasa(mundo, oferta_id: str, moneda: str, valor: str, dias_atras: int, empresa: str | None = None) -> str:
    with mundo.factory() as db:
        doc = db.scalar(
            select(GovernmentProcurementOfferDocument).where(
                GovernmentProcurementOfferDocument.offer_id == oferta_id
            )
        )
        uid = db.scalar(select(User.id).where(User.username == "ua"))
        tasa = GovernmentOfficialExchangeRate(
            company_id=empresa or mundo.company_a,
            moneda=moneda,
            moneda_cotizacion="VES",
            fecha_efectiva=hoy_de_negocio() - timedelta(days=dias_atras),
            valor=Decimal(valor),
            fuente="BCV",
            fuente_referencia="BCV · tipo de cambio oficial de referencia",
            estado="APROBADA",
            version=1,
            capturada_por=uid,
            capturada_en=datetime.now(UTC),
            aprobada_por="00000000-0000-0000-0000-0000000000a1",
            aprobada_en=datetime.now(UTC),
            evidencia_documento_id=doc.document_id,
            evidencia_sha256=doc.sha256,
            created_by=uid,
        )
        db.add(tasa)
        db.commit()
        return tasa.id


def _control(mundo, exp_id: str, acto_id: str, oferta_id: str) -> dict:
    r = mundo.get(f"{E}/{exp_id}/decision", "ua", mundo.company_a)
    assert r.status_code == 200
    actos = r.json()["actos_elegibles"]
    for acto in actos:
        if acto["id"] == acto_id:
            for control in acto["control_monto"]:
                if control["offer_id"] == oferta_id:
                    return control
    raise AssertionError("control_monto no encontrado")


def test_sin_tasa_bloquea_y_audita(mundo, gobierno, ocupacion):
    exp, ofertas, rec_id = _preparar(mundo, ocupacion)
    _insertar_monto(mundo, ofertas[0]["id"], "862.08", "137.93", "1000.01", moneda="USD")
    cargo = _cargo_con_limite(mundo, ocupacion, "60000.00", "EUR")
    acto = acto_decision(mundo, cargo)

    control = _control(mundo, exp["id"], acto["id"], ofertas[0]["id"])
    assert control["estado"] == "SIN_TASA"
    assert control["estado_etiqueta"] == "Sin tasa oficial aprobada"
    assert control["permite"] is False
    assert control["conversion"] is None
    assert control["monedas_sin_tasa"] == ["USD", "EUR"]
    assert "Tasas oficiales" in control["mensaje"]

    r = _adjudicar(mundo, exp["id"], rec_id, acto["id"], ofertas[0]["id"])

    assert r.status_code == 422
    cuerpo = r.json()
    assert cuerpo["code"] == "GOV_OFFICIAL_RATE_REQUIRED"
    assert cuerpo["details"]["moneda_operacion"] == "USD"
    assert cuerpo["details"]["moneda_limite"] == "EUR"
    assert cuerpo["details"]["fecha"] == hoy_de_negocio().isoformat()
    assert cuerpo["details"]["monedas_sin_tasa"] == ["USD", "EUR"]
    assert _decisiones(mundo, exp["id"]) == 0
    bloqueados = eventos(mundo, "GOV_PROCUREMENT_DECISION_AUTHORITY_BLOCKED", exp["id"])
    assert len(bloqueados) == 1
    assert bloqueados[0].after["causal"] == "GOV_OFFICIAL_RATE_REQUIRED"
    assert "1000.01" not in str(bloqueados[0].after)
    assert eventos(mundo, "GOV_PROCUREMENT_DECISION_ISSUED", exp["id"]) == []


def test_tasa_anulada_en_carrera(mundo, gobierno, ocupacion):
    exp, ofertas, rec_id = _preparar(mundo, ocupacion)
    _insertar_monto(mundo, ofertas[0]["id"], "86.21", "13.79", "100.00", moneda="EUR")
    cargo = _cargo_con_limite(mundo, ocupacion, "100000.00", "VES")
    acto = acto_decision(mundo, cargo)
    tasa_id = _tasa(mundo, ofertas[0]["id"], "EUR", "45.000000000000", 30)

    control = _control(mundo, exp["id"], acto["id"], ofertas[0]["id"])
    assert control["estado"] == "DENTRO_LIMITE"
    assert control["conversion"]["tasas"][0]["tasa_id"] == tasa_id

    uid = None
    with mundo.factory() as db:
        uid = db.scalar(select(User.id).where(User.username == "ua"))

    def primero(s):
        t = s.get(GovernmentOfficialExchangeRate, tasa_id, with_for_update=True)
        t.estado = "ANULADA"
        t.anulada_por = uid
        t.anulada_en = datetime.now(UTC)
        t.motivo_anulacion = "Anulación concurrente de prueba"

    version = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()["version"]
    user_id = uid
    with mundo.factory() as db:
        ctx = CompanyContext(
            tenant_id=mundo.t1, company_id=mundo.company_a, company=db.get(Company, mundo.company_a), user_id=user_id
        )
        user = db.get(User, user_id)
        cuerpo = {
            "resultado": "ADJUDICADA",
            "recomendacion_id": rec_id,
            "acto_id": acto["id"],
            "oferta_id": ofertas[0]["id"],
            "motivacion": "Motivación de prueba",
        }

        def segundo(s):
            registrar_decision(s, ctx, user, exp["id"], version, cuerpo)

        r1, r2 = carrera(mundo.factory, primero, segundo)

    assert isinstance(r2, KontrolError)
    assert r2.code == "GOV_OFFICIAL_RATE_REQUIRED"
    assert _decisiones(mundo, exp["id"]) == 0


def test_conversion_exacta_dentro_y_fuera(mundo, gobierno, ocupacion):
    exp, ofertas, rec_id = _preparar(mundo, ocupacion)
    _insertar_monto(mundo, ofertas[0]["id"], "862.08", "137.93", "1000.01", moneda="USD")
    tasa_id = _tasa(mundo, ofertas[0]["id"], "USD", "36.123456789012", 28)
    cargo_bajo = _cargo_con_limite(mundo, ocupacion, "36123.81", "VES")
    cargo_alto = _cargo_con_limite(mundo, ocupacion, "36123.82", "VES")
    acto_bajo = acto_decision(mundo, cargo_bajo)
    acto_alto = acto_decision(mundo, cargo_alto)

    r = _adjudicar(mundo, exp["id"], rec_id, acto_bajo["id"], ofertas[0]["id"])
    assert r.status_code == 409
    cuerpo = r.json()
    assert cuerpo["code"] == "GOV_DECISION_AUTHORITY_AMOUNT_EXCEEDED"
    assert Decimal(cuerpo["details"]["conversion"]["total_ves"]) == Decimal("36123.81802357989012")
    assert Decimal(cuerpo["details"]["conversion"]["limite_ves"]) == Decimal("36123.81")
    assert "36123.81802357989012" in cuerpo["message"]
    assert _decisiones(mundo, exp["id"]) == 0

    r = _adjudicar(mundo, exp["id"], rec_id, acto_alto["id"], ofertas[0]["id"])
    assert r.status_code == 201
    with mundo.factory() as db:
        dec = db.scalar(
            select(GovernmentProcurementDecision).where(
                GovernmentProcurementDecision.file_id == exp["id"]
            )
        )
        conv = dec.conversion_autoridad
        assert conv["moneda_operacion"] == "USD"
        assert conv["moneda_limite"] == "VES"
        assert conv["fecha"] == hoy_de_negocio().isoformat()
        assert len(conv["tasas"]) == 1
        assert conv["tasas"][0]["tasa_id"] == tasa_id
        assert conv["tasas"][0]["version"] == 1
        assert Decimal(conv["tasas"][0]["valor"]) == Decimal("36.123456789012")
        assert conv["tasas"][0]["fuente"] == "BCV"
        assert len(conv["tasas"][0]["evidencia_sha256"]) == 64
        assert conv["resultado"] == "DENTRO_DEL_LIMITE"

    vista = mundo.get(f"{E}/{exp['id']}/decision", "ua", mundo.company_a)
    assert vista.status_code == 200
    assert vista.json()["decisiones"][0]["conversion"] == conv

    emitidos = eventos(mundo, "GOV_PROCUREMENT_DECISION_ISSUED", exp["id"])
    assert len(emitidos) == 1
    assert emitidos[0].after["conversion"] == {
        "moneda_operacion": "USD",
        "moneda_limite": "VES",
        "fecha": hoy_de_negocio().isoformat(),
        "tasas": [{"tasa_id": tasa_id, "moneda": "USD", "version": 1}],
    }
    assert "36123" not in str(emitidos[0].after)

    with mundo.factory() as s, pytest.raises(DBAPIError):
        s.execute(
            text(
                "UPDATE gov_procurement_decisions SET conversion_autoridad = NULL WHERE file_id = :f"
            ),
            {"f": exp["id"]},
        )
        s.commit()


def test_ambas_monedas_extranjeras(mundo, gobierno, ocupacion):
    exp, ofertas, rec_id = _preparar(mundo, ocupacion)
    _insertar_monto(mundo, ofertas[0]["id"], "862.07", "137.93", "1000.00", moneda="USD")
    _tasa(mundo, ofertas[0]["id"], "EUR", "40.000000000000", 26)
    cargo = _cargo_con_limite(mundo, ocupacion, "903.09", "EUR")
    acto = acto_decision(mundo, cargo)

    r = _adjudicar(mundo, exp["id"], rec_id, acto["id"], ofertas[0]["id"])
    assert r.status_code == 201
    with mundo.factory() as db:
        dec = db.scalar(
            select(GovernmentProcurementDecision).where(
                GovernmentProcurementDecision.file_id == exp["id"]
            )
        )
        conv = dec.conversion_autoridad
        assert len(conv["tasas"]) == 2
        assert conv["tasas"][0]["moneda"] == "USD"
        assert conv["tasas"][1]["moneda"] == "EUR"
        assert Decimal(conv["total_ves"]) == Decimal("36123.456789012")
        assert Decimal(conv["limite_ves"]) == Decimal("36123.6")


def test_misma_moneda_no_usa_tasa(mundo, gobierno, ocupacion):
    exp, ofertas, rec_id = _preparar(mundo, ocupacion)
    _insertar_monto(mundo, ofertas[0]["id"], "862.07", "137.93", "1000.00", moneda="VES")
    cargo = _cargo_con_limite(mundo, ocupacion, "1000.00", "VES")
    acto = acto_decision(mundo, cargo)

    control = _control(mundo, exp["id"], acto["id"], ofertas[0]["id"])
    assert control["estado"] == "DENTRO_LIMITE"
    assert control["conversion"] is None

    r = _adjudicar(mundo, exp["id"], rec_id, acto["id"], ofertas[0]["id"])
    assert r.status_code == 201
    with mundo.factory() as db:
        dec = db.scalar(
            select(GovernmentProcurementDecision).where(
                GovernmentProcurementDecision.file_id == exp["id"]
            )
        )
        assert dec.conversion_autoridad is None

    vista = mundo.get(f"{E}/{exp['id']}/decision", "ua", mundo.company_a)
    assert vista.json()["decisiones"][0]["conversion"] is None
    emitidos = eventos(mundo, "GOV_PROCUREMENT_DECISION_ISSUED", exp["id"])
    assert "conversion" not in emitidos[0].after


def test_vista_previa_muestra_tasa_y_equivalentes(mundo, gobierno, ocupacion):
    exp, ofertas, rec_id = _preparar(mundo, ocupacion)
    _insertar_monto(mundo, ofertas[0]["id"], "86.21", "13.79", "100.00", moneda="USD")
    cargo = _cargo_con_limite(mundo, ocupacion, "3000.00", "VES")
    acto = acto_decision(mundo, cargo)

    control = _control(mundo, exp["id"], acto["id"], ofertas[0]["id"])
    assert control["estado"] == "EXCEDE_LIMITE"
    assert control["permite"] is False
    assert control["conversion"]["tasas"][0]["fuente_referencia"] == "BCV · tipo de cambio oficial de referencia"
    assert Decimal(control["conversion"]["total_ves"]) == Decimal("3612.3456789012")
    assert "tasa oficial BCV" in control["mensaje"]
    assert "excede el límite de aprobación" in control["mensaje"]


def test_tasa_sustituida_tras_la_vista_previa(mundo, gobierno, ocupacion):
    exp, ofertas, rec_id = _preparar(mundo, ocupacion)
    _insertar_monto(mundo, ofertas[0]["id"], "86.21", "13.79", "100.00", moneda="USD")
    v1 = _tasa(mundo, ofertas[0]["id"], "USD", "37.000000000000", 24)
    cargo = _cargo_con_limite(mundo, ocupacion, "10000.00", "VES")
    acto = acto_decision(mundo, cargo)

    control = _control(mundo, exp["id"], acto["id"], ofertas[0]["id"])
    assert control["conversion"]["tasas"][0]["tasa_id"] == v1

    v2 = None
    with mundo.factory() as s:
        t1 = s.get(GovernmentOfficialExchangeRate, v1)
        t1.estado = "SUSTITUIDA"
        t1.sustituida_en = datetime.now(UTC)
        s.flush()
        doc = s.scalar(
            select(GovernmentProcurementOfferDocument).where(
                GovernmentProcurementOfferDocument.offer_id == ofertas[0]["id"]
            )
        )
        uid = s.scalar(select(User.id).where(User.username == "ua"))
        t2 = GovernmentOfficialExchangeRate(
            company_id=mundo.company_a,
            moneda="USD",
            moneda_cotizacion="VES",
            fecha_efectiva=t1.fecha_efectiva,
            valor=Decimal("38.000000000000"),
            fuente="BCV",
            fuente_referencia="BCV · tipo de cambio oficial de referencia",
            estado="APROBADA",
            version=2,
            capturada_por=uid,
            capturada_en=datetime.now(UTC),
            aprobada_por="00000000-0000-0000-0000-0000000000a1",
            aprobada_en=datetime.now(UTC),
            evidencia_documento_id=doc.document_id,
            evidencia_sha256=doc.sha256,
            created_by=uid,
            sustituye_id=v1,
            motivo_correccion="Corrección de prueba de la tasa",
        )
        s.add(t2)
        s.commit()
        v2 = t2.id

    r = _adjudicar(mundo, exp["id"], rec_id, acto["id"], ofertas[0]["id"])
    assert r.status_code == 201
    with mundo.factory() as db:
        dec = db.scalar(
            select(GovernmentProcurementDecision).where(
                GovernmentProcurementDecision.file_id == exp["id"]
            )
        )
        assert dec.conversion_autoridad["tasas"][0]["tasa_id"] == v2
        assert dec.conversion_autoridad["tasas"][0]["version"] == 2
        assert Decimal(dec.conversion_autoridad["tasas"][0]["valor"]) == Decimal("38")


def test_adjudicacion_concurrente(mundo, gobierno, ocupacion):
    exp, ofertas, rec_id = _preparar(mundo, ocupacion)
    _insertar_monto(mundo, ofertas[0]["id"], "86.21", "13.79", "100.00", moneda="USD")
    cargo = _cargo_con_limite(mundo, ocupacion, "100000.00", "VES")
    acto = acto_decision(mundo, cargo)
    version = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()["version"]
    uid = None
    with mundo.factory() as db:
        uid = db.scalar(select(User.id).where(User.username == "ua"))
    cuerpo = {
        "resultado": "ADJUDICADA",
        "recomendacion_id": rec_id,
        "acto_id": acto["id"],
        "oferta_id": ofertas[0]["id"],
        "motivacion": "Motivación de prueba",
    }

    def primero(s):
        ctx1 = CompanyContext(
            tenant_id=mundo.t1, company_id=mundo.company_a, company=s.get(Company, mundo.company_a), user_id=uid
        )
        registrar_decision(s, ctx1, s.get(User, uid), exp["id"], version, cuerpo)

    def segundo(s):
        ctx2 = CompanyContext(
            tenant_id=mundo.t1, company_id=mundo.company_a, company=s.get(Company, mundo.company_a), user_id=uid
        )
        registrar_decision(s, ctx2, s.get(User, uid), exp["id"], version, cuerpo)

    r1, r2 = carrera(mundo.factory, primero, segundo)
    assert isinstance(r2, Exception)
    assert _decisiones(mundo, exp["id"]) == 1
    with mundo.factory() as db:
        dec = db.scalar(
            select(GovernmentProcurementDecision).where(
                GovernmentProcurementDecision.file_id == exp["id"]
            )
        )
        assert dec.conversion_autoridad is not None
        assert dec.conversion_autoridad["tasas"][0]["version"] == 2


def test_aislamiento_de_tasas(mundo, gobierno, ocupacion):
    exp, ofertas, rec_id = _preparar(mundo, ocupacion)
    _insertar_monto(mundo, ofertas[0]["id"], "86.21", "13.79", "100.00", moneda="USD")
    _tasa(mundo, ofertas[0]["id"], "USD", "99.000000000000", 1, empresa=mundo.company_b)
    cargo = _cargo_con_limite(mundo, ocupacion, "100000.00", "VES")
    acto = acto_decision(mundo, cargo)

    control = _control(mundo, exp["id"], acto["id"], ofertas[0]["id"])
    assert Decimal(control["conversion"]["tasas"][0]["valor"]) == Decimal("38")

    r = mundo.get(f"{E}/{exp['id']}/decision", "ub", mundo.company_b)
    assert r.status_code == 404
