import hashlib
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from tests.org06_guarda import cuenta_con_permisos, exigir_identidad
from tests.proc08_ayudantes import (
    evaluacion_concluida,
    post_recomendacion_cruda,
    recomendar,
)
from tests.test_gov_ctl01_reglas import eventos
from tests.test_gov_ctl06_hallazgos import _post
from tests.test_gov_proc03_expedientes import E
from tests.test_gov_proc07_evaluacion import _preparar

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos", "tests.org04_ayudantes")


def _cuerpo_base(comision, resultado="ADJUDICAR", opciones=None, rechazos=None, causal=None):
    return {
        "resultado_recomendado": resultado,
        "motivacion": "Motivación de prueba",
        "examen_legal": "Examen legal",
        "examen_financiero": "Examen financiero",
        "examen_tecnico": "Examen técnico",
        "resultado_matriz": "Resultado matriz",
        "medidas_promocion": "Medidas de promoción",
        "firmante_ids": [m["id"] for m in comision["miembros"]],
        "opciones": opciones or [],
        "rechazos": rechazos or [],
        "causal_desierta": causal,
    }


def test_adjudicar(mundo, gobierno, ocupacion):
    exp, comision, ofertas = evaluacion_concluida(mundo, ocupacion)
    estado = recomendar(
        mundo,
        exp,
        comision,
        ofertas,
        opciones=[
            {"posicion": 1, "offer_id": ofertas[0]["id"]},
            {"posicion": 2, "offer_id": ofertas[1]["id"]},
        ],
        rechazos=[
            {
                "offer_id": ofertas[2]["id"],
                "causal": "LCP76_1",
                "motivacion": "No cumple requisitos",
            }
        ],
    )
    rec = estado["recomendacion_vigente"]
    assert rec["referencia"] == "REC-01"
    assert rec["estado"] == "EMITIDA"
    assert [o["posicion"] for o in rec["opciones"]] == [1, 2]
    assert rec["rechazos"][0]["causal"] == "LCP76_1"
    assert rec["rechazos"][0]["motivacion"] == "No cumple requisitos"
    for firmante in rec["firmantes"]:
        if firmante["condicion"] == "SUPLENTE":
            assert firmante["cuenta_voto"] is False
        elif firmante["funcion"] == "MIEMBRO" and firmante["condicion"] == "PRINCIPAL":
            assert firmante["cuenta_voto"] is True
        elif firmante["funcion"] == "SECRETARIO":
            assert firmante["cuenta_voto"] is False
    assert rec["matriz_version"] is not None
    assert rec["evaluacion_concluida_en"] is not None
    assert estado["siguiente_accion"] == "Decidir el resultado"
    ofertas_estado = estado["ofertas"]
    rechazada = next(o for o in ofertas_estado if o["id"] == ofertas[2]["id"])
    assert rechazada["rechazada"] is True
    for o in ofertas_estado:
        if o["id"] != ofertas[2]["id"]:
            assert o["rechazada"] is False

    r = mundo.get(f"{E}/{exp['id']}/decision/recomendaciones/{rec['id']}/informe", "ua", mundo.company_a)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF")
    assert hashlib.sha256(r.content).hexdigest() == rec["informe"]["sha256"]

    cronologia = mundo.get(f"{E}/{exp['id']}/cronologia", "ua", mundo.company_a).json()
    assert any(e["clase"] == "RECOMENDACION" for e in cronologia["items"])
    assert eventos(mundo, "GOV_PROCUREMENT_RECOMMENDATION_ISSUED", exp["id"])


def test_negativas(mundo, gobierno, ocupacion):
    exp, comision, ofertas = evaluacion_concluida(mundo, ocupacion)

    exp_sin_eval, _ = _preparar(mundo, ocupacion)
    r = post_recomendacion_cruda(mundo, exp_sin_eval, _cuerpo_base(comision))
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_DECISION_EVALUATION_PENDING"

    r = _post(
        mundo,
        f"{E}/{exp['id']}/decision/recomendaciones",
        "ua",
        mundo.company_a,
        _cuerpo_base(comision),
    )
    assert r.status_code == 428
    assert r.json()["code"] == "GOV_DECISION_IF_MATCH_REQUIRED"

    secretario = next(m for m in comision["miembros"] if m["funcion"] == "SECRETARIO")["id"]
    cuerpo = _cuerpo_base(comision)
    cuerpo["firmante_ids"] = [secretario]
    r = post_recomendacion_cruda(
        mundo,
        exp,
        cuerpo,
    )
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_RECOMMENDATION_QUORUM"

    cuerpo = _cuerpo_base(comision)
    cuerpo["firmante_ids"] = ["0" * 36]
    r = post_recomendacion_cruda(mundo, exp, cuerpo)
    assert r.status_code == 422
    assert "firmantes" in r.json()["field_errors"]

    cuerpo = _cuerpo_base(
        comision,
        opciones=[{"posicion": 1, "offer_id": ofertas[2]["id"]}],
        rechazos=[
            {
                "offer_id": ofertas[2]["id"],
                "causal": "LCP76_1",
                "motivacion": "Oferta rechazada por no cumplir requisitos legales",
            }
        ],
    )
    r = post_recomendacion_cruda(mundo, exp, cuerpo)
    assert r.status_code == 422
    assert "opciones" in r.json()["field_errors"]

    cuerpo = _cuerpo_base(comision, resultado="DECLARAR_DESIERTA")
    r = post_recomendacion_cruda(mundo, exp, cuerpo)
    assert r.status_code == 422
    assert "causal_desierta" in r.json()["field_errors"]

    nombre = f"proc08_rec_view_{uuid4().hex[:8]}"
    cuenta_con_permisos(mundo, nombre, [("gobierno_decision", "view"), ("gobierno_expedientes", "view")])
    r = _post(
        mundo,
        f"{E}/{exp['id']}/decision/recomendaciones",
        nombre,
        mundo.company_a,
        _cuerpo_base(comision),
        version=exp["version"],
    )
    assert r.status_code == 403

    r = mundo.get(f"{E}/{exp['id']}/decision", "ub", mundo.company_b)
    assert r.status_code == 404

    exigir_identidad(mundo)
    try:
        r = post_recomendacion_cruda(mundo, exp, _cuerpo_base(comision))
        assert r.status_code == 403
        assert r.json()["code"] == "GOV_DECISION_IDENTITY_REQUIRED"
    finally:
        exigir_identidad(mundo, False)

    recomendar(
        mundo,
        exp,
        comision,
        ofertas,
        opciones=[{"posicion": 1, "offer_id": ofertas[0]["id"]}],
    )
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    r = post_recomendacion_cruda(mundo, exp, _cuerpo_base(comision))
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_RECOMMENDATION_ALREADY_ISSUED"


def test_sustitucion(mundo, gobierno, ocupacion):
    exp, comision, ofertas = evaluacion_concluida(mundo, ocupacion)
    estado = recomendar(
        mundo,
        exp,
        comision,
        ofertas,
        opciones=[{"posicion": 1, "offer_id": ofertas[0]["id"]}],
    )
    rec1 = estado["recomendacion_vigente"]
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()

    r = recomendar(
        mundo,
        exp,
        comision,
        ofertas,
        opciones=[{"posicion": 1, "offer_id": ofertas[0]["id"]}],
        sustituye_id=rec1["id"],
        esperado=422,
    )
    assert r.json()["code"] == "GOV_PROCUREMENT_FILE_INVALID"
    assert "motivo_sustitucion" in r.json()["field_errors"]

    estado = recomendar(
        mundo,
        exp,
        comision,
        ofertas,
        opciones=[{"posicion": 1, "offer_id": ofertas[0]["id"]}],
        sustituye_id=rec1["id"],
        motivo_sustitucion="Corrección de la recomendación",
    )
    rec2 = estado["recomendacion_vigente"]
    assert rec2["referencia"] == "REC-02"
    assert rec2["sustituye"] == "REC-01"
    rec1_serializada = next(r for r in estado["recomendaciones"] if r["id"] == rec1["id"])
    assert rec1_serializada["estado"] == "SUSTITUIDA"
    assert rec1_serializada["sustituida_en"] is not None
    assert eventos(mundo, "GOV_PROCUREMENT_RECOMMENDATION_SUPERSEDED", exp["id"])


def test_desierta_lcp113_2(mundo, gobierno, ocupacion):
    exp, comision, ofertas = evaluacion_concluida(mundo, ocupacion)
    rechazos = [
        {"offer_id": ofertas[0]["id"], "causal": "LCP76_1", "motivacion": "No cumple"},
        {"offer_id": ofertas[1]["id"], "causal": "LCP76_2", "motivacion": "No cumple"},
    ]
    r = recomendar(
        mundo,
        exp,
        comision,
        ofertas,
        resultado="DECLARAR_DESIERTA",
        causal="LCP113_2",
        rechazos=rechazos,
        esperado=422,
    )
    assert r.json()["code"] == "GOV_PROCUREMENT_FILE_INVALID"
    assert "rechazos" in r.json()["field_errors"]

    rechazos.append(
        {"offer_id": ofertas[2]["id"], "causal": "LCP76_3", "motivacion": "No cumple"}
    )
    estado = recomendar(
        mundo,
        exp,
        comision,
        ofertas,
        resultado="DECLARAR_DESIERTA",
        causal="LCP113_2",
        rechazos=rechazos,
    )
    assert estado["recomendacion_vigente"]["resultado_recomendado"] == "DECLARAR_DESIERTA"


def test_inmutable(mundo, gobierno, ocupacion):
    exp, comision, ofertas = evaluacion_concluida(mundo, ocupacion)
    estado = recomendar(
        mundo,
        exp,
        comision,
        ofertas,
        opciones=[{"posicion": 1, "offer_id": ofertas[0]["id"]}],
    )
    rec_id = estado["recomendacion_vigente"]["id"]

    with mundo.factory() as db:
        if db.get_bind().dialect.name != "postgresql":
            pytest.skip("Requiere postgresql para validar el trigger de inmutabilidad")
        with pytest.raises(DBAPIError):
            db.execute(
                text("UPDATE gov_procurement_recommendations SET motivacion='hack' WHERE id=:id"),
                {"id": rec_id},
            )
            db.commit()
        db.rollback()

        with pytest.raises(DBAPIError):
            db.execute(
                text("DELETE FROM gov_procurement_recommendations WHERE id=:id"),
                {"id": rec_id},
            )
            db.commit()
        db.rollback()

        with pytest.raises(DBAPIError):
            db.execute(
                text("UPDATE gov_procurement_recommendation_options SET posicion=99 WHERE recommendation_id=:id"),
                {"id": rec_id},
            )
            db.commit()
        db.rollback()
