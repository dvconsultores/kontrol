from uuid import uuid4

import pytest
from sqlalchemy.exc import DBAPIError

from app.modules.government.models import GovernmentProcurementDecision
from tests.org06_guarda import cuenta_con_permisos
from tests.proc08_ayudantes import (
    acto_de_otro_ente,
    acto_decision,
    acto_sin_competencia,
    cargo_contrataciones,
    evaluacion_concluida,
    recomendar,
)
from tests.test_gov_ctl01_reglas import cerrar_regla, eventos, regla_vigente
from tests.test_gov_ctl06_hallazgos import _post
from tests.test_gov_proc03_expedientes import E

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos", "tests.org04_ayudantes")


_SIN_VERSION = object()


def _decision(mundo, exp, cuerpo, version=_SIN_VERSION, usuario="ua", empresa=None):
    return _post(
        mundo,
        f"{E}/{exp['id']}/decision/decisiones",
        usuario,
        empresa or mundo.company_a,
        cuerpo,
        version=exp["version"] if version is _SIN_VERSION else version,
    )


def _notificar(mundo, acto, oferta):
    r = _post(
        mundo,
        "/gobierno/notificaciones",
        "ua",
        mundo.company_a,
        {
            "acto_id": acto["id"],
            "tipo_persona": "JURIDICA",
            "nombre": oferta["oferente_nombre"],
            "identificacion": oferta["oferente_documento"],
            "domicilio": "Calle 1, casa 2, Caracas",
            "recursos": "Recurso de reconsideración ante el mismo órgano en 15 días hábiles (LOPA art. 94)",
        },
    )
    assert r.status_code == 201, r.text


def test_adjudicar_o01(mundo, gobierno, ocupacion):
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
    )
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    cargo_id = cargo_contrataciones(mundo, ocupacion)
    acto = acto_decision(mundo, cargo_id)

    r = _decision(
        mundo,
        exp,
        {
            "resultado": "ADJUDICADA",
            "recomendacion_id": estado["recomendacion_vigente"]["id"],
            "acto_id": acto["id"],
            "oferta_id": ofertas[0]["id"],
            "motivacion": "Adjudicación de prueba",
        },
    )
    assert r.status_code == 201, r.text
    estado = r.json()
    assert estado["decision_vigente"]["referencia"] == "DEC-01"
    assert estado["decision_vigente"]["resultado"] == "ADJUDICADA"
    assert len(estado["notificaciones"]) == 3
    assert all(n["estado"] == "SIN_NOTIFICACION" for n in estado["notificaciones"])
    assert estado["siguiente_accion"] == "Notificar a los oferentes"

    _notificar(mundo, acto, ofertas[0])
    estado = mundo.get(f"{E}/{exp['id']}/decision", "ua", mundo.company_a).json()
    noti = next(n for n in estado["notificaciones"] if n["offer_id"] == ofertas[0]["id"])
    assert noti["estado"] != "SIN_NOTIFICACION"

    cronologia = mundo.get(f"{E}/{exp['id']}/cronologia", "ua", mundo.company_a).json()
    assert any(e["clase"] == "ADJUDICACION" for e in cronologia["items"])
    assert eventos(mundo, "GOV_PROCUREMENT_DECISION_ISSUED", exp["id"])


def test_negativas(mundo, gobierno, ocupacion):
    exp, comision, ofertas = evaluacion_concluida(mundo, ocupacion)
    cargo_id = cargo_contrataciones(mundo, ocupacion)
    acto = acto_decision(mundo, cargo_id)

    r = _decision(
        mundo,
        exp,
        {
            "resultado": "ADJUDICADA",
            "recomendacion_id": "00000000-0000-0000-0000-000000000000",
            "acto_id": acto["id"],
            "oferta_id": ofertas[0]["id"],
            "motivacion": "Sin recomendación",
        },
    )
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_DECISION_RECOMMENDATION_REQUIRED"

    acto_interno = acto_decision(mundo, cargo_id, caracter="INTERNO")
    acto_borrador = acto_decision(mundo, cargo_id, emitido=False)
    acto_sin_comp = acto_sin_competencia(mundo, ocupacion)
    acto_otro_ente = acto_de_otro_ente(mundo, ocupacion)

    estado = recomendar(
        mundo,
        exp,
        comision,
        ofertas,
        opciones=[{"posicion": 1, "offer_id": ofertas[0]["id"]}],
    )
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()

    for acto_invalido in (acto_interno, acto_borrador, acto_sin_comp, acto_otro_ente):
        r = _decision(
            mundo,
            exp,
            {
                "resultado": "ADJUDICADA",
                "recomendacion_id": estado["recomendacion_vigente"]["id"],
                "acto_id": acto_invalido["id"],
                "oferta_id": ofertas[0]["id"],
                "motivacion": "Acto inválido",
            },
        )
        assert r.status_code == 422, r.text
        assert r.json()["code"] == "GOV_DECISION_INVALID_ACT"

    r = _decision(
        mundo,
        exp,
        {
            "resultado": "ADJUDICADA",
            "recomendacion_id": estado["recomendacion_vigente"]["id"],
            "acto_id": acto["id"],
            "oferta_id": ofertas[1]["id"],
            "motivacion": "Opción 2 sin nulidad",
        },
    )
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_DECISION_OPTION_ORDER"

    r = _decision(
        mundo,
        exp,
        {
            "resultado": "ADJUDICADA",
            "recomendacion_id": estado["recomendacion_vigente"]["id"],
            "acto_id": acto["id"],
            "oferta_id": ofertas[2]["id"],
            "motivacion": "Oferta no opción",
        },
    )
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_DECISION_OPTION_ORDER"

    nombre = f"proc08_dec_view_{uuid4().hex[:8]}"
    cuenta_con_permisos(mundo, nombre, [("gobierno_decision", "view"), ("gobierno_expedientes", "view")])
    r = _decision(
        mundo,
        exp,
        {
            "resultado": "ADJUDICADA",
            "recomendacion_id": estado["recomendacion_vigente"]["id"],
            "acto_id": acto["id"],
            "oferta_id": ofertas[0]["id"],
            "motivacion": "Sin permiso",
        },
        usuario=nombre,
    )
    assert r.status_code == 403

    r = _decision(
        mundo,
        exp,
        {
            "resultado": "ADJUDICADA",
            "recomendacion_id": estado["recomendacion_vigente"]["id"],
            "acto_id": acto["id"],
            "oferta_id": ofertas[0]["id"],
            "motivacion": "Sin If-Match",
        },
        version=None,
    )
    assert r.status_code == 428
    assert r.json()["code"] == "GOV_DECISION_IF_MATCH_REQUIRED"

    r = _decision(
        mundo,
        exp,
        {
            "resultado": "ADJUDICADA",
            "recomendacion_id": estado["recomendacion_vigente"]["id"],
            "acto_id": acto["id"],
            "oferta_id": ofertas[0]["id"],
            "motivacion": "Versión vieja",
        },
        version=exp["version"] - 1,
    )
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_PROCUREMENT_FILE_STALE"

    r = _decision(
        mundo,
        exp,
        {
            "resultado": "ADJUDICADA",
            "recomendacion_id": estado["recomendacion_vigente"]["id"],
            "acto_id": acto["id"],
            "oferta_id": ofertas[0]["id"],
            "motivacion": "Primera adjudicación",
        },
    )
    assert r.status_code == 201, r.text
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()

    r = _decision(
        mundo,
        exp,
        {
            "resultado": "ADJUDICADA",
            "recomendacion_id": estado["recomendacion_vigente"]["id"],
            "acto_id": acto["id"],
            "oferta_id": ofertas[0]["id"],
            "motivacion": "Mismo acto",
        },
    )
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_DECISION_ACT_IN_USE"

    acto2 = acto_decision(mundo, cargo_id)
    r = _decision(
        mundo,
        exp,
        {
            "resultado": "ADJUDICADA",
            "recomendacion_id": estado["recomendacion_vigente"]["id"],
            "acto_id": acto2["id"],
            "oferta_id": ofertas[0]["id"],
            "motivacion": "Segunda final",
        },
    )
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_DECISION_ALREADY_FINAL"

    r = _post(
        mundo,
        f"{E}/{exp['id']}/decision/recomendaciones",
        "ua",
        mundo.company_a,
        {
            "resultado_recomendado": "ADJUDICAR",
            "motivacion": "Nueva recomendación",
            "examen_legal": "Legal",
            "examen_financiero": "Financiero",
            "examen_tecnico": "Técnico",
            "resultado_matriz": "Matriz",
            "medidas_promocion": "Medidas",
            "firmante_ids": [m["id"] for m in comision["miembros"]],
            "opciones": [],
            "rechazos": [],
        },
        version=exp["version"],
    )
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_RECOMMENDATION_LOCKED_BY_DECISION"

    r = mundo.get(f"{E}/{exp['id']}/decision", "ub", mundo.company_b)
    assert r.status_code == 404

    r = _decision(
        mundo,
        exp,
        {
            "resultado": "ADJUDICADA",
            "recomendacion_id": estado["recomendacion_vigente"]["id"],
            "acto_id": acto2["id"],
            "oferta_id": ofertas[0]["id"],
            "motivacion": "Otra empresa",
        },
        usuario="ub",
        empresa=mundo.company_b,
    )
    assert r.status_code == 404


def test_nulidad_y_segunda_opcion(mundo, gobierno, ocupacion):
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
    )
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    cargo_id = cargo_contrataciones(mundo, ocupacion)
    acto = acto_decision(mundo, cargo_id)

    r = _decision(
        mundo,
        exp,
        {
            "resultado": "ADJUDICADA",
            "recomendacion_id": estado["recomendacion_vigente"]["id"],
            "acto_id": acto["id"],
            "oferta_id": ofertas[0]["id"],
            "motivacion": "Adjudicación O-01",
        },
    )
    assert r.status_code == 201, r.text
    decision_id = r.json()["decision_vigente"]["id"]
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()

    acto_nulidad = acto_decision(mundo, cargo_id)
    r = _decision(
        mundo,
        exp,
        {
            "resultado": "NULIDAD",
            "acto_id": acto_nulidad["id"],
            "causal_nulidad": "INFORMACION_FALSA",
            "anula_id": decision_id,
            "motivacion": "Nulidad por información falsa",
        },
    )
    assert r.status_code == 201, r.text
    estado = r.json()
    assert estado["decisiones"][0]["resultado"] == "NULIDAD"
    assert estado["decisiones"][1]["estado"] == "ANULADA"
    assert eventos(mundo, "GOV_PROCUREMENT_DECISION_NULLIFIED", exp["id"])
    cronologia = mundo.get(f"{E}/{exp['id']}/cronologia", "ua", mundo.company_a).json()
    assert any(e["clase"] == "NULIDAD" for e in cronologia["items"])

    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    acto2 = acto_decision(mundo, cargo_id)
    r = _decision(
        mundo,
        exp,
        {
            "resultado": "ADJUDICADA",
            "recomendacion_id": estado["recomendacion_vigente"]["id"],
            "acto_id": acto2["id"],
            "oferta_id": ofertas[1]["id"],
            "motivacion": "Adjudicación O-02",
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["decision_vigente"]["posicion"] == 2

    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    acto_nuevo = acto_decision(mundo, cargo_id)
    r = _decision(
        mundo,
        exp,
        {
            "resultado": "NULIDAD",
            "acto_id": acto_nuevo["id"],
            "causal_nulidad": "INFORMACION_FALSA",
            "anula_id": "00000000-0000-0000-0000-000000000000",
            "motivacion": "Nada que anular",
        },
    )
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_DECISION_NOTHING_TO_ANNUL"


def test_nulidad_violacion_legal_no_habilita_opcion(mundo, gobierno, ocupacion):
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
    )
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    cargo_id = cargo_contrataciones(mundo, ocupacion)
    acto = acto_decision(mundo, cargo_id)

    r = _decision(
        mundo,
        exp,
        {
            "resultado": "ADJUDICADA",
            "recomendacion_id": estado["recomendacion_vigente"]["id"],
            "acto_id": acto["id"],
            "oferta_id": ofertas[0]["id"],
            "motivacion": "Adjudicación O-01",
        },
    )
    assert r.status_code == 201, r.text
    decision_id = r.json()["decision_vigente"]["id"]
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()

    acto_nulidad = acto_decision(mundo, cargo_id)
    r = _decision(
        mundo,
        exp,
        {
            "resultado": "NULIDAD",
            "acto_id": acto_nulidad["id"],
            "causal_nulidad": "VIOLACION_LEGAL",
            "anula_id": decision_id,
            "motivacion": "Nulidad por violación legal",
        },
    )
    assert r.status_code == 201, r.text
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()

    acto2 = acto_decision(mundo, cargo_id)
    r = _decision(
        mundo,
        exp,
        {
            "resultado": "ADJUDICADA",
            "recomendacion_id": estado["recomendacion_vigente"]["id"],
            "acto_id": acto2["id"],
            "oferta_id": ofertas[1]["id"],
            "motivacion": "Opción 2 sin nulidad válida",
        },
    )
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_DECISION_OPTION_ORDER"


def test_desierta(mundo, gobierno, ocupacion):
    exp, comision, ofertas = evaluacion_concluida(mundo, ocupacion)
    estado = recomendar(
        mundo,
        exp,
        comision,
        ofertas,
        resultado="DECLARAR_DESIERTA",
        causal="LCP113_3",
    )
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    cargo_id = cargo_contrataciones(mundo, ocupacion)
    acto = acto_decision(mundo, cargo_id)

    r = _decision(
        mundo,
        exp,
        {
            "resultado": "DESIERTA",
            "recomendacion_id": estado["recomendacion_vigente"]["id"],
            "acto_id": acto["id"],
            "causal_desierta": "LCP113_3",
            "motivacion": "Declaratoria desierta",
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["decision_vigente"]["resultado"] == "DESIERTA"

    cronologia = mundo.get(f"{E}/{exp['id']}/cronologia", "ua", mundo.company_a).json()
    assert any(e["clase"] == "DESIERTA" for e in cronologia["items"])


def test_terminacion_tras_adjudicacion(mundo, gobierno, ocupacion):
    exp, comision, ofertas = evaluacion_concluida(mundo, ocupacion)
    estado = recomendar(
        mundo,
        exp,
        comision,
        ofertas,
        opciones=[{"posicion": 1, "offer_id": ofertas[0]["id"]}],
    )
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    cargo_id = cargo_contrataciones(mundo, ocupacion)
    acto = acto_decision(mundo, cargo_id)

    r = _decision(
        mundo,
        exp,
        {
            "resultado": "ADJUDICADA",
            "recomendacion_id": estado["recomendacion_vigente"]["id"],
            "acto_id": acto["id"],
            "oferta_id": ofertas[0]["id"],
            "motivacion": "Adjudicación",
        },
    )
    assert r.status_code == 201, r.text
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()

    acto_term = acto_decision(mundo, cargo_id)
    r = _decision(
        mundo,
        exp,
        {
            "resultado": "TERMINADA",
            "recomendacion_id": estado["recomendacion_vigente"]["id"],
            "acto_id": acto_term["id"],
            "motivacion": "Terminación del procedimiento",
        },
    )
    assert r.status_code == 201, r.text
    estado = r.json()
    assert estado["decisiones"][0]["resultado"] == "TERMINADA"
    assert estado["decisiones"][1]["estado"] == "SUSTITUIDA"

    cronologia = mundo.get(f"{E}/{exp['id']}/cronologia", "ua", mundo.company_a).json()
    assert any(e["clase"] == "TERMINACION" for e in cronologia["items"])

    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    acto_term2 = acto_decision(mundo, cargo_id)
    r = _decision(
        mundo,
        exp,
        {
            "resultado": "TERMINADA",
            "recomendacion_id": estado["recomendacion_vigente"]["id"],
            "acto_id": acto_term2["id"],
            "motivacion": "Otra terminación",
        },
    )
    assert r.status_code == 409


def test_sod(mundo, gobierno, ocupacion):
    exp, comision, ofertas = evaluacion_concluida(mundo, ocupacion)
    estado = recomendar(
        mundo,
        exp,
        comision,
        ofertas,
        opciones=[{"posicion": 1, "offer_id": ofertas[0]["id"]}],
    )
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    cargo_id = cargo_contrataciones(mundo, ocupacion)
    acto = acto_decision(mundo, cargo_id)

    regla = regla_vigente(mundo, proceso="PROC-03", accion_a="PROC03_RECOMENDAR", accion_b="PROC03_RESOLVER")
    try:
        r = _decision(
            mundo,
            exp,
            {
                "resultado": "ADJUDICADA",
                "recomendacion_id": estado["recomendacion_vigente"]["id"],
                "acto_id": acto["id"],
                "oferta_id": ofertas[0]["id"],
                "motivacion": "Conflicto SoD",
            },
        )
        assert r.status_code == 409
        assert r.json()["code"] == "GOV_SOD_CONFLICT"
    finally:
        cerrar_regla(mundo, regla)


def test_inmutable(mundo, gobierno, ocupacion):
    exp, comision, ofertas = evaluacion_concluida(mundo, ocupacion)
    estado = recomendar(
        mundo,
        exp,
        comision,
        ofertas,
        opciones=[{"posicion": 1, "offer_id": ofertas[0]["id"]}],
    )
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    cargo_id = cargo_contrataciones(mundo, ocupacion)
    acto = acto_decision(mundo, cargo_id)

    r = _decision(
        mundo,
        exp,
        {
            "resultado": "ADJUDICADA",
            "recomendacion_id": estado["recomendacion_vigente"]["id"],
            "acto_id": acto["id"],
            "oferta_id": ofertas[0]["id"],
            "motivacion": "Adjudicación",
        },
    )
    assert r.status_code == 201, r.text
    decision_id = r.json()["decision_vigente"]["id"]

    with mundo.factory() as db:
        if db.get_bind().dialect.name != "postgresql":
            pytest.skip("Requiere postgresql para validar el trigger de inmutabilidad")
        decision = db.get(GovernmentProcurementDecision, decision_id)
        decision.motivacion = "ALTERADA"
        with pytest.raises(DBAPIError):
            db.commit()
        db.rollback()
