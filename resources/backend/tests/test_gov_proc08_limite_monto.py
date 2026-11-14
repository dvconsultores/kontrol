from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.core.company_context import CompanyContext
from app.core.errors import ConflictError
from app.modules.government.models import (
    GovernmentPosition,
    GovernmentPositionCompetency,
    GovernmentPositionVersion,
    GovernmentProcurementDecision,
    GovernmentStructure,
)
from app.modules.government.service_decision_resolver import registrar_decision
from app.modules.identity_access.models import User
from app.modules.organization.models import Company
from tests.concurrency import carrera
from tests.org04_ayudantes import _codigo
from tests.proc08_ayudantes import (
    acto_decision,
    cargo_contrataciones,
    evaluacion_concluida,
    recomendar,
)
from tests.test_gov_ctl01_reglas import eventos
from tests.test_gov_ctl06_hallazgos import _post
from tests.test_gov_proc03_expedientes import E
from tests.test_gov_proc06_montos import _insertar_monto

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos", "tests.org04_ayudantes")


def _cargo_con_limite(mundo, ocupacion, monto: str, moneda: str) -> str:
    with mundo.factory() as db:
        cargo = GovernmentPosition(
            company_id=mundo.company_a,
            structure_id=ocupacion["estructura"],
            unit_id=ocupacion["unidad_raiz"],
            code=_codigo("C"),
            name=f"Cargo con límite {_codigo('N')}",
            status="VIGENTE",
            valid_from=datetime(2024, 1, 1),
            activated_at=datetime.now(UTC),
            version=1,
        )
        db.add(cargo)
        db.flush()
        db.add(
            GovernmentPositionCompetency(
                position_id=cargo.id,
                company_id=mundo.company_a,
                action="APROBAR",
                subject="CONTRATACIONES",
                limit_type="MONTO",
                limit_amount=Decimal(monto),
                limit_currency=moneda,
                basis="Fundamento de prueba",
            )
        )
        db.add(
            GovernmentPositionVersion(
                position_id=cargo.id,
                structure_id=ocupacion["estructura"],
                company_id=mundo.company_a,
                version=1,
                status="VIGENTE",
                snapshot={
                    "competencias": [
                        {
                            "accion": "APROBAR",
                            "materia": "CONTRATACIONES",
                            "tipo_limite": "MONTO",
                            "monto": monto,
                            "moneda": moneda,
                        }
                    ]
                },
                reason=None,
                actor_id=None,
            )
        )
        db.commit()
        return str(cargo.id)


def _nueva_version_limite(db, cargo_id: str, ocupacion, company_id: str, monto: str, moneda: str) -> None:
    db.add(
        GovernmentPositionVersion(
            position_id=cargo_id,
            structure_id=ocupacion["estructura"],
            company_id=company_id,
            version=2,
            status="VIGENTE",
            snapshot={
                "competencias": [
                    {
                        "accion": "APROBAR",
                        "materia": "CONTRATACIONES",
                        "tipo_limite": "MONTO",
                        "monto": monto,
                        "moneda": moneda,
                    }
                ]
            },
            reason="Límite reducido",
            actor_id=None,
        )
    )


def _adjudicar(mundo, exp_id: str, rec_id: str, acto_id: str, oferta_id: str):
    exp = mundo.get(f"{E}/{exp_id}", "ua", mundo.company_a).json()
    return _post(
        mundo,
        f"{E}/{exp_id}/decision/decisiones",
        "ua",
        mundo.company_a,
        {
            "resultado": "ADJUDICADA",
            "recomendacion_id": rec_id,
            "acto_id": acto_id,
            "oferta_id": oferta_id,
            "motivacion": "Adjudicación de prueba",
        },
        version=exp["version"],
    )


def _preparar(mundo, ocupacion):
    exp, comision, ofertas = evaluacion_concluida(mundo, ocupacion, n=2)
    estado = recomendar(
        mundo,
        exp,
        comision,
        ofertas,
        opciones=[{"posicion": 1, "offer_id": ofertas[0]["id"]}],
    )
    return exp, ofertas, estado["recomendacion_vigente"]["id"]


def _decisiones(mundo, exp_id) -> int:
    with mundo.factory() as db:
        return db.scalar(
            select(func.count())
            .select_from(GovernmentProcurementDecision)
            .where(GovernmentProcurementDecision.file_id == exp_id)
        )


@pytest.mark.parametrize(
    ("total", "neto", "tributos", "esperado"),
    [
        ("40000.00", "34482.76", "5517.24", 201),
        ("50000.00", "43103.45", "6896.55", 201),
        ("50000.01", "43103.46", "6896.55", 409),
    ],
)
def test_misma_moneda_compara_el_total(mundo, gobierno, ocupacion, total, neto, tributos, esperado):
    """Verifica que el límite monetario se compare sobre el total de la oferta en la misma moneda."""
    exp, ofertas, rec_id = _preparar(mundo, ocupacion)
    _insertar_monto(mundo, ofertas[0]["id"], neto, tributos, total, moneda="USD")
    cargo = _cargo_con_limite(mundo, ocupacion, "50000.00", "USD")
    acto = acto_decision(mundo, cargo)
    r = _adjudicar(mundo, exp["id"], rec_id, acto["id"], ofertas[0]["id"])

    assert r.status_code == esperado
    if esperado == 409:
        cuerpo = r.json()
        assert cuerpo["code"] == "GOV_DECISION_AUTHORITY_AMOUNT_EXCEEDED"
        assert "excede el límite de aprobación" in cuerpo["message"]
        assert cuerpo["details"]["monto"] == "50000.01"
        assert cuerpo["details"]["moneda"] == "USD"
        assert cuerpo["details"]["limite"] == "50000.00"
        assert cuerpo["details"]["moneda_limite"] == "USD"
        assert isinstance(cuerpo["details"]["cargo"], str) and cuerpo["details"]["cargo"]
        assert _decisiones(mundo, exp["id"]) == 0
    else:
        assert _decisiones(mundo, exp["id"]) == 1


def test_moneda_distinta_bloquea_sin_convertir(mundo, gobierno, ocupacion):
    """Bloquea una adjudicación cuando la oferta y el límite están en monedas distintas."""
    exp, ofertas, rec_id = _preparar(mundo, ocupacion)
    _insertar_monto(mundo, ofertas[0]["id"], "43103.45", "6896.55", "50000.00", moneda="USD")
    cargo = _cargo_con_limite(mundo, ocupacion, "50000.00", "EUR")
    acto = acto_decision(mundo, cargo)

    r = _adjudicar(mundo, exp["id"], rec_id, acto["id"], ofertas[0]["id"])

    assert r.status_code == 409
    cuerpo = r.json()
    assert cuerpo["code"] == "GOV_DECISION_AUTHORITY_CURRENCY_MISMATCH"
    assert cuerpo["message"].startswith(
        "No puede verificarse el límite de esta autoridad porque la oferta y el límite están expresados en monedas diferentes."
    )
    assert cuerpo["details"]["moneda"] == "USD"
    assert cuerpo["details"]["moneda_limite"] == "EUR"
    assert _decisiones(mundo, exp["id"]) == 0


def test_sin_limite_pasa_con_cualquier_monto(mundo, gobierno, ocupacion):
    """Una autoridad sin límite admite cualquier monto de oferta."""
    exp, ofertas, rec_id = _preparar(mundo, ocupacion)
    _insertar_monto(mundo, ofertas[0]["id"], "431034.48", "68965.52", "500000.00", moneda="USD")
    cargo = cargo_contrataciones(mundo, ocupacion)
    acto = acto_decision(mundo, cargo)

    r = _adjudicar(mundo, exp["id"], rec_id, acto["id"], ofertas[0]["id"])

    assert r.status_code == 201


def test_oferta_sin_monto_con_limite_bloquea(mundo, gobierno, ocupacion):
    """Sin monto declarado, una autoridad con límite MONTO bloquea; una SIN_LIMITE permite."""
    exp, ofertas, rec_id = _preparar(mundo, ocupacion)
    cargo = _cargo_con_limite(mundo, ocupacion, "50000.00", "USD")
    acto = acto_decision(mundo, cargo)

    r = _adjudicar(mundo, exp["id"], rec_id, acto["id"], ofertas[0]["id"])

    assert r.status_code == 409
    assert r.json()["code"] == "GOV_DECISION_OFFER_AMOUNT_REQUIRED"
    assert _decisiones(mundo, exp["id"]) == 0

    cargo_sin_limite = cargo_contrataciones(mundo, ocupacion)
    acto_sin_limite = acto_decision(mundo, cargo_sin_limite)
    r = _adjudicar(mundo, exp["id"], rec_id, acto_sin_limite["id"], ofertas[0]["id"])

    assert r.status_code == 201
    assert _decisiones(mundo, exp["id"]) == 1


def test_desierta_no_compara_monto(mundo, gobierno, ocupacion):
    """Una declaratoria desierta no valida montos de ofertas."""
    exp, comision, ofertas = evaluacion_concluida(mundo, ocupacion, n=2)
    estado = recomendar(
        mundo,
        exp,
        comision,
        ofertas,
        resultado="DECLARAR_DESIERTA",
        causal="LCP113_3",
    )
    rec_id = estado["recomendacion_vigente"]["id"]
    cargo = _cargo_con_limite(mundo, ocupacion, "1.00", "USD")
    acto = acto_decision(mundo, cargo)
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()

    r = _post(
        mundo,
        f"{E}/{exp['id']}/decision/decisiones",
        "ua",
        mundo.company_a,
        {
            "resultado": "DESIERTA",
            "recomendacion_id": rec_id,
            "acto_id": acto["id"],
            "causal_desierta": "LCP113_3",
            "motivacion": "Declaratoria desierta",
        },
        version=exp["version"],
    )

    assert r.status_code == 201


def test_bloqueo_auditado_sin_importes(mundo, gobierno, ocupacion):
    """El bloqueo por límite se audita sin registrar importes en el evento."""
    exp, ofertas, rec_id = _preparar(mundo, ocupacion)
    _insertar_monto(mundo, ofertas[0]["id"], "43103.46", "6896.55", "50000.01", moneda="USD")
    cargo = _cargo_con_limite(mundo, ocupacion, "50000.00", "USD")
    acto = acto_decision(mundo, cargo)

    r = _adjudicar(mundo, exp["id"], rec_id, acto["id"], ofertas[0]["id"])

    assert r.status_code == 409
    ev = eventos(mundo, "GOV_PROCUREMENT_DECISION_AUTHORITY_BLOCKED", exp["id"])
    assert len(ev) == 1
    after = ev[0].after
    assert after["causal"] == "GOV_DECISION_AUTHORITY_AMOUNT_EXCEEDED"
    assert after["oferta"] == "O-01"
    assert after["resultado"] == "ADJUDICADA"
    assert "monto" not in after
    assert "50000" not in str(after)
    assert eventos(mundo, "GOV_PROCUREMENT_DECISION_ISSUED", exp["id"]) == []


def test_vista_previa_por_acto_y_oferta(mundo, gobierno, ocupacion):
    """La vista previa de decisión muestra el control de límite por acto y oferta."""
    exp, ofertas, _ = _preparar(mundo, ocupacion)
    _insertar_monto(mundo, ofertas[0]["id"], "43103.46", "6896.55", "50000.01", moneda="USD")
    cargo_monto_usd = _cargo_con_limite(mundo, ocupacion, "50000.00", "USD")
    cargo_monto_eur = _cargo_con_limite(mundo, ocupacion, "60000.00", "EUR")
    cargo_sin_limite = cargo_contrataciones(mundo, ocupacion)
    acto_usd = acto_decision(mundo, cargo_monto_usd)
    acto_eur = acto_decision(mundo, cargo_monto_eur)
    acto_sin = acto_decision(mundo, cargo_sin_limite)

    r = mundo.get(f"{E}/{exp['id']}/decision", "ua", mundo.company_a)
    assert r.status_code == 200
    actos = {a["id"]: a for a in r.json()["actos_elegibles"]}

    control_usd = {c["offer_id"]: c for c in actos[acto_usd["id"]]["control_monto"]}
    assert actos[acto_usd["id"]]["limite"]["etiqueta"] == "50000.00 USD"
    assert control_usd[ofertas[0]["id"]]["estado"] == "EXCEDE_LIMITE"
    assert control_usd[ofertas[0]["id"]]["estado_etiqueta"] == "Excede el límite"
    assert control_usd[ofertas[0]["id"]]["permite"] is False
    assert control_usd[ofertas[0]["id"]]["monto_oferta"] == {
        "total_con_tributos": "50000.01",
        "moneda": "USD",
    }
    assert control_usd[ofertas[1]["id"]]["estado"] == "MONTO_NO_DECLARADO"
    assert control_usd[ofertas[1]["id"]]["monto_oferta"] is None

    control_eur = {c["offer_id"]: c for c in actos[acto_eur["id"]]["control_monto"]}
    assert control_eur[ofertas[0]["id"]]["estado"] == "MONEDA_DISTINTA"
    assert control_eur[ofertas[0]["id"]]["estado_etiqueta"] == "No comparable por moneda"

    control_sin = {c["offer_id"]: c for c in actos[acto_sin["id"]]["control_monto"]}
    assert actos[acto_sin["id"]]["limite"]["etiqueta"] == "Sin límite"
    for oferta in ofertas:
        assert control_sin[oferta["id"]]["estado"] == "SIN_LIMITE"
        assert control_sin[oferta["id"]]["permite"] is True

    for acto in actos.values():
        for control in acto["control_monto"]:
            assert control["offer_id"] not in control["mensaje"]


def test_limite_reducido_tras_la_vista_previa_bloquea(mundo, gobierno, ocupacion):
    """Un cambio posterior del límite invalida la vista previa y bloquea la adjudicación."""
    exp, ofertas, rec_id = _preparar(mundo, ocupacion)
    _insertar_monto(mundo, ofertas[0]["id"], "34482.76", "5517.24", "40000.00", moneda="USD")
    cargo = _cargo_con_limite(mundo, ocupacion, "50000.00", "USD")
    acto = acto_decision(mundo, cargo)

    r = mundo.get(f"{E}/{exp['id']}/decision", "ua", mundo.company_a)
    actos = {a["id"]: a for a in r.json()["actos_elegibles"]}
    control = {c["offer_id"]: c for c in actos[acto["id"]]["control_monto"]}
    assert control[ofertas[0]["id"]]["estado"] == "DENTRO_LIMITE"

    with mundo.factory() as db:
        _nueva_version_limite(db, cargo, ocupacion, mundo.company_a, "30000.00", "USD")
        db.commit()

    r = _adjudicar(mundo, exp["id"], rec_id, acto["id"], ofertas[0]["id"])
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_DECISION_AUTHORITY_AMOUNT_EXCEEDED"
    assert r.json()["details"]["limite"] == "30000.00"


def test_dos_intentos_de_decidir(mundo, gobierno, ocupacion):
    """Un segundo intento de decidir con la misma versión debe fallar por conflicto."""
    exp, ofertas, rec_id = _preparar(mundo, ocupacion)
    _insertar_monto(mundo, ofertas[0]["id"], "34482.76", "5517.24", "40000.00", moneda="USD")
    cargo = _cargo_con_limite(mundo, ocupacion, "50000.00", "USD")
    acto = acto_decision(mundo, cargo)

    exp_v = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()["version"]
    r = _post(
        mundo,
        f"{E}/{exp['id']}/decision/decisiones",
        "ua",
        mundo.company_a,
        {
            "resultado": "ADJUDICADA",
            "recomendacion_id": rec_id,
            "acto_id": acto["id"],
            "oferta_id": ofertas[0]["id"],
            "motivacion": "Adjudicación de prueba",
        },
        version=exp_v,
    )
    assert r.status_code == 201

    r = _post(
        mundo,
        f"{E}/{exp['id']}/decision/decisiones",
        "ua",
        mundo.company_a,
        {
            "resultado": "ADJUDICADA",
            "recomendacion_id": rec_id,
            "acto_id": acto["id"],
            "oferta_id": ofertas[0]["id"],
            "motivacion": "Segunda adjudicación",
        },
        version=exp_v,
    )
    assert r.status_code == 409
    assert _decisiones(mundo, exp["id"]) == 1


def test_carrera_con_cambio_de_limite(mundo, gobierno, ocupacion):
    """En concurrencia, un cambio de límite concurrente con la decisión debe bloquearla."""
    exp, ofertas, rec_id = _preparar(mundo, ocupacion)
    _insertar_monto(mundo, ofertas[0]["id"], "34482.76", "5517.24", "40000.00", moneda="USD")
    cargo = _cargo_con_limite(mundo, ocupacion, "50000.00", "USD")
    acto = acto_decision(mundo, cargo)
    exp_v = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()["version"]

    with mundo.factory() as db:
        uid = db.scalar(select(User.id).where(User.username == "ua"))

    def primero(s):
        s.execute(
            select(GovernmentStructure)
            .where(GovernmentStructure.id == ocupacion["estructura"])
            .with_for_update()
        ).scalar_one()
        _nueva_version_limite(s, cargo, ocupacion, mundo.company_a, "30000.00", "USD")

    def segundo(s):
        ctx = CompanyContext(
            tenant_id=mundo.t1,
            company_id=mundo.company_a,
            company=s.get(Company, mundo.company_a),
            user_id=uid,
        )
        return registrar_decision(
            s,
            ctx,
            s.get(User, uid),
            exp["id"],
            exp_v,
            {
                "resultado": "ADJUDICADA",
                "recomendacion_id": rec_id,
                "acto_id": acto["id"],
                "oferta_id": ofertas[0]["id"],
                "motivacion": "Adjudicación en carrera",
            },
        )

    r1, r2 = carrera(mundo.factory, primero, segundo)

    assert isinstance(r2, ConflictError)
    assert r2.code == "GOV_DECISION_AUTHORITY_AMOUNT_EXCEEDED"
    assert _decisiones(mundo, exp["id"]) == 0
