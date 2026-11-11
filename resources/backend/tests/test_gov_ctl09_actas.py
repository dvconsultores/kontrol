import os
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.modules.identity_access.mfa_policy import SENSITIVE, STANDARD, classify
from app.shared.clock import hoy_de_negocio
from tests.org04_ayudantes import crear_funcionario, titular_activo
from tests.org06_guarda import cuenta_con_permisos
from tests.test_gov_doc02_actos import _doc_con_version

pytestmark = pytest.mark.skipif(
    not os.environ.get("KONTROL_TEST_DB_URL", "").startswith("postgresql"),
    reason="Requiere PostgreSQL",
)
pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos", "tests.org04_ayudantes")


def _acta_body(mundo, ocupacion, *, modalidad="ENTREGA"):
    asignacion, cargo_id = titular_activo(mundo, ocupacion)
    receptor = crear_funcionario(mundo)
    saliente_official_id = asignacion["funcionario"]["id"]
    return (
        {
            "assignment_id": asignacion["id"],
            "receptor_official_id": receptor["id"],
            "receptor_assignment_id": None,
            "modalidad": modalidad,
            "testigos": [],
            "auditor_official_id": None,
            "motivo": "Motivo de prueba para el acta de entrega",
            "fundamento": "Fundamento de prueba para el acta de entrega",
            "lugar": "Sede del ente",
            "fecha_corte": hoy_de_negocio().isoformat(),
        },
        saliente_official_id,
    )


def _crear_acta(mundo, ocupacion, *, modalidad="ENTREGA"):
    cuerpo, saliente_official_id = _acta_body(mundo, ocupacion, modalidad=modalidad)
    respuesta = mundo.post("/gobierno/actas-entrega/actas", "ua", mundo.company_a, cuerpo)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json(), cuerpo


def _resolver_anexos(mundo, acta):
    doc_id = _doc_con_version(
        mundo,
        mundo.company_a,
        resource_id=acta["id"],
        resource_type="GovernmentHandoverAct",
    )
    r1 = mundo.put_json(
        f"/gobierno/actas-entrega/actas/{acta['id']}/anexos/A11_3",
        "ua",
        mundo.company_a,
        {"documento_ids": [doc_id]},
    )
    assert r1.status_code == 200, r1.text
    r2 = mundo.put_json(
        f"/gobierno/actas-entrega/actas/{acta['id']}/anexos/A11_4",
        "ua",
        mundo.company_a,
        {"constancia": "Constancia válida para el inventario de bienes muebles"},
    )
    assert r2.status_code == 200, r2.text


def test_ae01_alta_y_validaciones(mundo, gobierno, ocupacion):
    acta, cuerpo = _crear_acta(mundo, ocupacion)

    assert acta["estado"] == "BORRADOR"
    assert acta["codigo"].startswith(f"AE-{hoy_de_negocio().year}-")
    assert len(acta["anexos"]) == 6
    assert acta["anexos"][0]["resuelto"] is True
    assert acta["anexos"][1]["resuelto"] is True
    assert acta["anexos"][4]["resuelto"] is True

    cuerpo_nuevo_receptor_saliente, saliente_official_id = _acta_body(mundo, ocupacion)
    cuerpo_nuevo_receptor_saliente["receptor_official_id"] = saliente_official_id
    r = mundo.post(
        "/gobierno/actas-entrega/actas", "ua", mundo.company_a, cuerpo_nuevo_receptor_saliente
    )
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_HANDOVER_RECEIVER_INVALID"

    r = mundo.post("/gobierno/actas-entrega/actas", "ua", mundo.company_a, cuerpo)
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_HANDOVER_DUPLICATE"

    cuerpo_modalidad_invalida = dict(cuerpo)
    cuerpo_modalidad_invalida["modalidad"] = "OTRA"
    r = mundo.post("/gobierno/actas-entrega/actas", "ua", mundo.company_a, cuerpo_modalidad_invalida)
    assert r.status_code == 422

    cuerpo_levantada, _ = _acta_body(mundo, ocupacion, modalidad="LEVANTADA_POR_RECEPTOR")
    r = mundo.post("/gobierno/actas-entrega/actas", "ua", mundo.company_a, cuerpo_levantada)
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_HANDOVER_WITNESSES_REQUIRED"


def test_ae02_anexos_y_pendientes(mundo, gobierno, ocupacion):
    acta, _ = _crear_acta(mundo, ocupacion)
    r = mundo.post(
        f"/gobierno/actas-entrega/actas/{acta['id']}/suscribir",
        "ua",
        mundo.company_a,
        {"fecha_suscripcion": hoy_de_negocio().isoformat()},
    )
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_HANDOVER_ANNEXES_PENDING"

    r = mundo.put_json(
        f"/gobierno/actas-entrega/actas/{acta['id']}/anexos/A11_4",
        "ua",
        mundo.company_a,
        {"constancia": "corta"},
    )
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_HANDOVER_ANNEX_INVALID"

    doc_id = _doc_con_version(
        mundo,
        mundo.company_a,
        resource_id=acta["id"],
        resource_type="GovernmentHandoverAct",
    )
    r = mundo.put_json(
        f"/gobierno/actas-entrega/actas/{acta['id']}/anexos/A11_3",
        "ua",
        mundo.company_a,
        {"documento_ids": [doc_id]},
    )
    assert r.status_code == 200, r.text
    r = mundo.put_json(
        f"/gobierno/actas-entrega/actas/{acta['id']}/anexos/A11_4",
        "ua",
        mundo.company_a,
        {"constancia": "Constancia válida para el inventario"},
    )
    assert r.status_code == 200, r.text
    ficha = r.json()
    resueltos = {a["codigo"]: a["resuelto"] for a in ficha["anexos"]}
    assert resueltos["A11_3"] is True
    assert resueltos["A11_4"] is True

    cuerpo, _ = _acta_body(mundo, ocupacion)
    otra = cuerpo.copy()
    r = mundo.post("/gobierno/actas-entrega/actas", "ua", mundo.company_a, otra)
    if r.status_code == 201:
        acta2 = r.json()
        r2 = mundo.put_json(
            f"/gobierno/actas-entrega/actas/{acta2['id']}/anexos/A11_3",
            "ua",
            mundo.company_a,
            {"documento_ids": [str(uuid4())]},
        )
        assert r2.status_code == 422
        assert r2.json()["code"] == "GOV_HANDOVER_ANNEX_INVALID"


def test_ae03_contenido_generado_al_corte(mundo, gobierno, ocupacion):
    acta, _ = _crear_acta(mundo, ocupacion)
    vista = mundo.get(
        f"/gobierno/actas-entrega/actas/{acta['id']}/anexos/A11_2/vista",
        "ua",
        mundo.company_a,
    )
    assert vista.status_code == 200, vista.text
    contenido = vista.json()
    assert any(c["ocupante"] for c in contenido["cargos"])


def test_ae04_suscribir_congela_y_pdf(mundo, gobierno, ocupacion):
    acta, _ = _crear_acta(mundo, ocupacion)
    _resolver_anexos(mundo, acta)
    r = mundo.post(
        f"/gobierno/actas-entrega/actas/{acta['id']}/suscribir",
        "ua",
        mundo.company_a,
        {"fecha_suscripcion": hoy_de_negocio().isoformat(), "errores_deficiencias": "Ninguna"},
    )
    assert r.status_code == 200, r.text
    ficha = r.json()
    assert ficha["estado"] == "SUSCRITA"
    assert len(ficha["snapshot_sha256"]) == 64

    r_pdf = mundo.get(f"/gobierno/actas-entrega/actas/{acta['id']}/acta.pdf", "ua", mundo.company_a)
    assert r_pdf.status_code == 200
    assert r_pdf.content.startswith(b"%PDF")
    import hashlib

    assert hashlib.sha256(r_pdf.content).hexdigest() == ficha["informe"]["sha256"]

    cuerpo_update, _ = _acta_body(mundo, ocupacion)
    r = mundo.client.put(
        f"/api/v1/gobierno/actas-entrega/actas/{acta['id']}",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(ficha["version"])},
        json={**cuerpo_update, "version": int(ficha["version"])},
    )
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_HANDOVER_STATE"

    r = mundo.put_json(
        f"/gobierno/actas-entrega/actas/{acta['id']}/anexos/A11_6",
        "ua",
        mundo.company_a,
        {"constancia": "Constancia después de suscribir no permitida"},
    )
    assert r.status_code == 409


def test_ae05_disparadores_postgresql(mundo, gobierno, ocupacion):
    acta, _ = _crear_acta(mundo, ocupacion)
    _resolver_anexos(mundo, acta)
    r = mundo.post(
        f"/gobierno/actas-entrega/actas/{acta['id']}/suscribir",
        "ua",
        mundo.company_a,
        {"fecha_suscripcion": hoy_de_negocio().isoformat()},
    )
    assert r.status_code == 200, r.text
    with mundo.factory() as db:
        from sqlalchemy.exc import DBAPIError

        with pytest.raises(DBAPIError):
            db.execute(
                text(
                    "UPDATE gov_handover_acts SET motivo = 'alterado' WHERE id = :id"
                ),
                {"id": acta["id"]},
            )
            db.commit()


def test_ae06_remision_observacion_verificacion(mundo, gobierno, ocupacion):
    acta, _ = _crear_acta(mundo, ocupacion)
    _resolver_anexos(mundo, acta)
    r = mundo.post(
        f"/gobierno/actas-entrega/actas/{acta['id']}/suscribir",
        "ua",
        mundo.company_a,
        {"fecha_suscripcion": hoy_de_negocio().isoformat()},
    )
    assert r.status_code == 200, r.text

    r = mundo.post(
        f"/gobierno/actas-entrega/actas/{acta['id']}/remision",
        "ua",
        mundo.company_a,
        {"fecha": hoy_de_negocio().isoformat()},
    )
    assert r.status_code == 200, r.text
    assert r.json()["remision_uai_fecha"] == hoy_de_negocio().isoformat()

    r = mundo.post(
        f"/gobierno/actas-entrega/actas/{acta['id']}/observaciones",
        "ua",
        mundo.company_a,
        {"fecha": hoy_de_negocio().isoformat(), "texto": "Observación de prueba para el acta"},
    )
    assert r.status_code == 201, r.text

    r = mundo.post(
        f"/gobierno/actas-entrega/actas/{acta['id']}/verificacion",
        "ua",
        mundo.company_a,
        {
            "numero": "VER-1",
            "fecha": hoy_de_negocio().isoformat(),
            "resultado": "CONFORME",
            "fundamento": "Fundamento de verificación adecuado",
        },
    )
    assert r.status_code == 403
    assert r.json()["code"] == "GOV_HANDOVER_SAME_ACTOR"

    nombre_verificador = f"verificador_{uuid4().hex[:8]}"
    cuenta_con_permisos(
        mundo,
        nombre_verificador,
        [("gobierno_actas", "view"), ("gobierno_actas", "verify")],
    )
    r = mundo.post(
        f"/gobierno/actas-entrega/actas/{acta['id']}/verificacion",
        nombre_verificador,
        mundo.company_a,
        {
            "numero": "VER-2",
            "fecha": hoy_de_negocio().isoformat(),
            "resultado": "CONFORME",
            "fundamento": "Fundamento de verificación adecuado",
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "VERIFICADA"


def test_ae07_aislamiento_y_permisos(mundo, gobierno, ocupacion):
    from app.modules.setup.api import CATALOGO_DE_PERMISOS

    acta, _ = _crear_acta(mundo, ocupacion)
    r = mundo.get(f"/gobierno/actas-entrega/actas/{acta['id']}", "ub", mundo.company_b)
    assert r.status_code == 404
    assert CATALOGO_DE_PERMISOS["gobierno_actas"] == ["view", "manage", "verify"]
    assert classify(["gobierno_actas:manage"]) == SENSITIVE
    assert classify(["gobierno_actas:view"]) == STANDARD


def test_ae08_integridad_y_historial(mundo, gobierno, ocupacion):
    acta, _ = _crear_acta(mundo, ocupacion)
    _resolver_anexos(mundo, acta)
    r = mundo.post(
        f"/gobierno/actas-entrega/actas/{acta['id']}/suscribir",
        "ua",
        mundo.company_a,
        {"fecha_suscripcion": hoy_de_negocio().isoformat()},
    )
    assert r.status_code == 200, r.text

    r = mundo.get(f"/gobierno/actas-entrega/actas/{acta['id']}/integridad", "ua", mundo.company_a)
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "VALIDO"

    r = mundo.get(f"/gobierno/actas-entrega/actas/{acta['id']}/historial", "ua", mundo.company_a)
    assert r.status_code == 200, r.text
    acciones = [item["accion"] for item in r.json()["items"]]
    assert "GOV_HANDOVER_ACT_CREATED" in acciones
    assert "GOV_HANDOVER_ACT_SUBSCRIBED" in acciones

