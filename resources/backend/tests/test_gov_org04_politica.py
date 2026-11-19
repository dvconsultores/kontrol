# ruff: noqa: E402, F811, F401, I001
import uuid

import pytest
from sqlalchemy import select, text

pytest_plugins = (
    "tests.conftest_multicompany",
    "tests.test_gov_ctl06_hallazgos",
    "tests.org04_ayudantes",
)

from sqlalchemy.exc import DBAPIError

from app.modules.government.models import GovernmentEntity
from tests.org04_ayudantes import (
    D, O, accion, activa, acto_eficaz, crear, crear_funcionario, cuerpo, nuevo_cargo, post_asignacion, titular_activo,
)
from tests.test_gov_ctl06_hallazgos import _post

P = "/gobierno/ocupacion/politicas"


def _entrada(detalle, **cambios):
    claves = {
        "codigo",
        "nombre",
        "descripcion",
        "figura",
        "fundamento",
        "act_id",
        "vigente_desde",
        "vigente_hasta",
        "exige_fin",
        "max_dias",
        "acto_medio",
        "emisor_tipo",
        "emisor_position_id",
        "emisor_competencia_accion",
        "emisor_competencia_materia",
        "autorizacion_requerida",
        "autorizacion_etiqueta",
        "autorizacion_ambito",
        "autorizacion_mas_de_dias",
        "prohibe_avocacion",
        "competencias",
        "documentos",
    }
    entrada = {k: v for k, v in detalle.items() if k in claves}
    entrada["competencias"] = [
        {"accion": c["accion"], "materia": c["materia"]}
        for c in detalle.get("competencias") or []
    ]
    entrada["documentos"] = [
        {
            "document_type_id": d["document_type_id"],
            "etapa": d["etapa"],
            "obligatorio": d.get("obligatorio", True),
        }
        for d in detalle.get("documentos") or []
    ]
    entrada.update(cambios)
    return entrada


def _politica(mundo, figura, activar=True, **cambios):
    cuerpo_politica = {
        "codigo": f"POL-{uuid.uuid4().hex[:6]}",
        "nombre": "Política de prueba",
        "figura": figura,
        "fundamento": "Fundamento institucional de la política de prueba",
        "vigente_desde": D(1, 1).isoformat(),
    }
    cuerpo_politica.update(cambios)
    resp = _post(mundo, P, "ua", mundo.company_a, cuerpo_politica)
    assert resp.status_code == 201, resp.text
    detalle = resp.json()
    if activar:
        resp = mundo.client.post(
            f"/api/v1{P}/{detalle['id']}/activar",
            headers={**mundo.como("uab", mundo.company_a), "If-Match": str(detalle["version"])},
        )
        assert resp.status_code == 200, resp.text
        detalle = resp.json()
    return detalle


def _cerrar_vigentes(mundo, figura):
    resp = mundo.client.get(
        f"/api/v1{P}",
        headers=mundo.como("ua", mundo.company_a),
        params={"estado": "VIGENTE", "figura": figura},
    )
    assert resp.status_code == 200, resp.text
    for item in resp.json()["items"]:
        resp = mundo.client.post(
            f"/api/v1{P}/{item['id']}/cerrar",
            headers={**mundo.como("uab", mundo.company_a), "If-Match": str(item["version"])},
            json={"motivo": "Cierre de prueba"},
        )
        assert resp.status_code == 200, resp.text


def test_politica_ciclo_vida_e_historia(mundo, gobierno, ocupacion):
    _cerrar_vigentes(mundo, "TITULAR")
    detalle = _politica(mundo, "TITULAR", activar=False)
    assert detalle["estado"] == "BORRADOR"
    assert detalle["numero_version"] == 1

    resp = mundo.client.put(
        f"/api/v1{P}/{detalle['id']}",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(detalle["version"])},
        json=_entrada(detalle, nombre="Política editada"),
    )
    assert resp.status_code == 200, resp.text
    editada = resp.json()
    assert editada["version"] > detalle["version"]

    resp = mundo.client.post(
        f"/api/v1{P}/{editada['id']}/activar",
        headers={**mundo.como("uab", mundo.company_a), "If-Match": str(editada["version"])},
    )
    assert resp.status_code == 200, resp.text
    vigente = resp.json()
    assert vigente["estado"] == "VIGENTE"

    resp = mundo.client.put(
        f"/api/v1{P}/{vigente['id']}",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(vigente["version"])},
        json=_entrada(vigente, nombre="No debería poder"),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "GOV_ASSIGNMENT_POLICY_NOT_DRAFT"

    resp = mundo.client.post(
        f"/api/v1{P}/{vigente['id']}/cerrar",
        headers={**mundo.como("uab", mundo.company_a), "If-Match": str(vigente["version"])},
        json={"motivo": "Fin de ciclo"},
    )
    assert resp.status_code == 200, resp.text
    cerrada = resp.json()
    assert cerrada["estado"] == "CERRADA"

    eventos = [h["evento"] for h in cerrada["historia"]]
    for evento in ("CREADA", "EDITADA", "ACTIVADA", "CERRADA"):
        assert evento in eventos


def test_politica_aislamiento_empresas(mundo, gobierno, ocupacion):
    _cerrar_vigentes(mundo, "TITULAR")
    detalle = _politica(mundo, "TITULAR")

    resp = mundo.client.get(
        f"/api/v1{P}/{detalle['id']}",
        headers=mundo.como("ub", mundo.company_b),
    )
    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == "GOV_ASSIGNMENT_POLICY_NOT_FOUND"

    resp = mundo.client.get(
        f"/api/v1{P}",
        headers=mundo.como("ub", mundo.company_b),
    )
    assert resp.status_code == 200, resp.text
    ids = [item["id"] for item in resp.json()["items"]]
    assert detalle["id"] not in ids

    resp = mundo.client.post(
        f"/api/v1{P}/{detalle['id']}/activar",
        headers={**mundo.como("ub", mundo.company_b), "If-Match": str(detalle["version"])},
    )
    assert resp.status_code == 404, resp.text


def test_politica_codigo_duplicado_y_if_match(mundo, gobierno, ocupacion):
    _cerrar_vigentes(mundo, "TITULAR")
    codigo = f"POL-{uuid.uuid4().hex[:6]}"
    detalle = _politica(mundo, "TITULAR", activar=False, codigo=codigo)

    resp = _post(
        mundo,
        P,
        "ua",
        mundo.company_a,
        {
            "codigo": codigo,
            "nombre": "Otra política",
            "figura": "TITULAR",
            "fundamento": "Fundamento institucional",
            "vigente_desde": D(1, 1).isoformat(),
        },
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "GOV_ASSIGNMENT_POLICY_DUPLICATE"

    resp = mundo.client.put(
        f"/api/v1{P}/{detalle['id']}",
        headers=mundo.como("ua", mundo.company_a),
        json=_entrada(detalle, nombre="Sin If-Match"),
    )
    assert resp.status_code == 428, resp.text
    assert resp.json()["code"] == "GOV_ASSIGNMENT_POLICY_IF_MATCH_REQUIRED"

    resp = mundo.client.put(
        f"/api/v1{P}/{detalle['id']}",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(detalle["version"] - 1)},
        json=_entrada(detalle, nombre="Versión vieja"),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "GOV_ASSIGNMENT_POLICY_STALE"


def test_politica_validaciones_de_piso(mundo, gobierno, ocupacion):
    base = {
        "codigo": f"POL-{uuid.uuid4().hex[:6]}",
        "nombre": "Política de prueba",
        "fundamento": "Fundamento institucional",
        "vigente_desde": D(1, 1).isoformat(),
    }

    resp = _post(
        mundo,
        P,
        "ua",
        mundo.company_a,
        {**base, "figura": "DELEGACION_ATRIBUCIONES", "acto_medio": "PERSONAL"},
    )
    assert resp.status_code == 422, resp.text
    assert "acto_medio" in resp.json()["field_errors"]

    resp = _post(
        mundo,
        P,
        "ua",
        mundo.company_a,
        {**base, "figura": "DELEGACION_ATRIBUCIONES", "emisor_tipo": "CARGO"},
    )
    assert resp.status_code == 422, resp.text
    assert "emisor_tipo" in resp.json()["field_errors"]

    resp = _post(
        mundo,
        P,
        "ua",
        mundo.company_a,
        {
            **base,
            "figura": "TITULAR",
            "competencias": [{"accion": "FIRMAR", "materia": "PRESUPUESTO"}],
        },
    )
    assert resp.status_code == 422, resp.text
    assert "competencias" in resp.json()["field_errors"]

    resp = _post(
        mundo,
        P,
        "ua",
        mundo.company_a,
        {**base, "figura": "SUPLENCIA", "autorizacion_requerida": True},
    )
    assert resp.status_code == 422, resp.text
    assert "autorizacion_etiqueta" in resp.json()["field_errors"]

    resp = _post(
        mundo,
        P,
        "ua",
        mundo.company_a,
        {
            **base,
            "figura": "TITULAR",
            "autorizacion_requerida": True,
            "autorizacion_etiqueta": "Autorización X",
            "autorizacion_ambito": "MAXIMA_AUTORIDAD",
        },
    )
    assert resp.status_code == 422, resp.text
    assert "autorizacion_ambito" in resp.json()["field_errors"]


def test_politica_solapamiento_y_sustitucion(mundo, gobierno, ocupacion):
    _cerrar_vigentes(mundo, "ENCARGADURIA")
    x = _politica(mundo, "ENCARGADURIA")

    y = _politica(mundo, "ENCARGADURIA", activar=False)
    resp = mundo.client.post(
        f"/api/v1{P}/{y['id']}/activar",
        headers={**mundo.como("uab", mundo.company_a), "If-Match": str(y["version"])},
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "GOV_ASSIGNMENT_POLICY_OVERLAP"

    resp = mundo.client.post(
        f"/api/v1{P}/{x['id']}/nueva-version",
        headers={**mundo.como("uab", mundo.company_a), "If-Match": str(x["version"])},
    )
    assert resp.status_code == 201, resp.text
    v2 = resp.json()
    assert v2["numero_version"] == 2
    assert v2["estado"] == "BORRADOR"

    resp = mundo.client.post(
        f"/api/v1{P}/{v2['id']}/activar",
        headers={**mundo.como("uab", mundo.company_a), "If-Match": str(v2["version"])},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["estado"] == "VIGENTE"

    resp = mundo.client.get(
        f"/api/v1{P}/{x['id']}",
        headers=mundo.como("ua", mundo.company_a),
    )
    assert resp.status_code == 200, resp.text
    v1 = resp.json()
    assert v1["estado"] == "CERRADA"
    assert any(h["evento"] == "SUSTITUIDA" for h in v1["historia"])


def test_politica_fundamento_obligatorio_al_activar(mundo, gobierno, ocupacion):
    _cerrar_vigentes(mundo, "TITULAR")
    cuerpo_politica = {
        "codigo": f"POL-{uuid.uuid4().hex[:6]}",
        "nombre": "Política sin fundamento",
        "figura": "TITULAR",
        "vigente_desde": D(1, 1).isoformat(),
    }
    resp = _post(mundo, P, "ua", mundo.company_a, cuerpo_politica)
    assert resp.status_code == 201, resp.text
    detalle = resp.json()

    resp = mundo.client.post(
        f"/api/v1{P}/{detalle['id']}/activar",
        headers={**mundo.como("uab", mundo.company_a), "If-Match": str(detalle["version"])},
    )
    assert resp.status_code == 422, resp.text
    assert "fundamento" in resp.json()["field_errors"]


def test_regla_sin_politica_municipal_y_no_municipal(mundo, gobierno, ocupacion):
    _cerrar_vigentes(mundo, "SUPLENCIA")
    resp = mundo.client.get(
        f"/api/v1{O}/regla",
        headers=mundo.como("ua", mundo.company_a),
        params={"figura": "SUPLENCIA", "desde": D(2, 1).isoformat()},
    )
    assert resp.status_code == 200, resp.text
    regla = resp.json()
    assert regla["origen"] == "PISO_LEGAL"
    assert any(p["codigo"] == "LOPPM_ART87" for p in regla["pisos"])
    assert regla["autorizaciones"][0]["etiqueta"] == "Autorización del Concejo Municipal"

    try:
        with mundo.factory() as db:
            ente = db.execute(
                select(GovernmentEntity).where(GovernmentEntity.company_id == mundo.company_a)
            ).scalar_one()
            ente.nivel_territorial = "ESTADAL"
            db.commit()

        resp = mundo.client.get(
            f"/api/v1{O}/regla",
            headers=mundo.como("ua", mundo.company_a),
            params={"figura": "SUPLENCIA", "desde": D(2, 1).isoformat()},
        )
        assert resp.status_code == 200, resp.text
        regla = resp.json()
        assert regla["autorizaciones"] == []
        assert not any(p["codigo"] == "LOPPM_ART87" for p in regla["pisos"])
    finally:
        with mundo.factory() as db:
            ente = db.execute(
                select(GovernmentEntity).where(GovernmentEntity.company_id == mundo.company_a)
            ).scalar_one()
            ente.nivel_territorial = "MUNICIPAL"
            db.commit()


def test_regla_con_politica_endurece(mundo, gobierno, ocupacion):
    _cerrar_vigentes(mundo, "COMISION_SERVICIO")
    politica = _politica(mundo, "COMISION_SERVICIO", max_dias=30)

    resp = mundo.client.get(
        f"/api/v1{O}/regla",
        headers=mundo.como("ua", mundo.company_a),
        params={"figura": "COMISION_SERVICIO", "desde": D(2, 1).isoformat()},
    )
    assert resp.status_code == 200, resp.text
    regla = resp.json()
    assert regla["origen"] == "POLITICA"
    assert regla["politica"]["codigo"] == politica["codigo"]
    assert any(limite.get("unidad") == "ANIOS" for limite in regla["limites"])
    assert any(limite.get("unidad") == "DIAS" and limite.get("valor") == 30 for limite in regla["limites"])


def test_auditoria_politica(mundo, gobierno, ocupacion):
    _cerrar_vigentes(mundo, "TITULAR")
    politica = _politica(mundo, "TITULAR")

    with mundo.factory() as db:
        rows = db.execute(
            text(
                "SELECT action FROM audit_events WHERE entity_id = :id ORDER BY created_at"
            ),
            {"id": politica["id"]},
        ).fetchall()
    acciones = [row[0] for row in rows]
    assert "GOV_ASSIGNMENT_POLICY_CREATED" in acciones
    assert "GOV_ASSIGNMENT_POLICY_ACTIVATED" in acciones


def test_historia_inmutable_pg(mundo, gobierno, ocupacion):
    _cerrar_vigentes(mundo, "TITULAR")
    politica = _politica(mundo, "TITULAR")

    with pytest.raises(DBAPIError):
        with mundo.factory() as db:
            db.execute(
                text(
                    "UPDATE gov_assignment_policy_history SET evento = 'EDITADA' WHERE policy_id = :id"
                ),
                {"id": politica["id"]},
            )
            db.commit()
    with mundo.factory() as db:
        db.rollback()
