# ruff: noqa: E402, F811, F401, I001
import uuid

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

pytest_plugins = (
    "tests.conftest_multicompany",
    "tests.test_gov_ctl06_hallazgos",
    "tests.org04_ayudantes",
)

from app.modules.documents.models import DocumentType
from app.modules.government.models import GovernmentEntity
from tests.org04_ayudantes import (
    D, O, accion, activa, acto_eficaz, crear, crear_funcionario, cuerpo, nuevo_cargo, post_asignacion, titular_activo,
)
from tests.test_gov_ctl06_hallazgos import _post
from tests.test_gov_org04_politica import _entrada

P = "/gobierno/ocupacion/politicas"


def _nivel(mundo, nivel):
    with mundo.factory() as db:
        ente = db.execute(select(GovernmentEntity).where(GovernmentEntity.company_id == mundo.company_a)).scalar_one()
        ente.nivel_territorial = nivel
        db.commit()


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


def _suplencia(mundo, ocupacion, **cambios):
    _cerrar_vigentes(mundo, "TITULAR")
    cargo_suplido = nuevo_cargo(mundo, ocupacion, unidad="unidad_raiz")
    cargo_suplente = nuevo_cargo(mundo, ocupacion, unidad="unidad_hija")
    titular_activo(mundo, ocupacion, cargo_suplido)
    asig_sup, _ = titular_activo(mundo, ocupacion, cargo_suplente)
    acto = acto_eficaz(mundo, cargo_suplido)
    body = cuerpo(
        asig_sup["funcionario"],
        cargo_suplido,
        acto,
        figura="SUPLENCIA",
        cargo_origen_id=cargo_suplente,
        maxima_autoridad=True,
        desde=D(2, 1).isoformat(),
        hasta=D(2, 20).isoformat(),
    )
    body.update(cambios)
    return body


def _delegacion(mundo, ocupacion, **cambios):
    _cerrar_vigentes(mundo, "TITULAR")
    cargo_delegante = nuevo_cargo(mundo, ocupacion, unidad="unidad_raiz")
    cargo_delegado = nuevo_cargo(mundo, ocupacion, unidad="unidad_hija")
    asig_del, _ = titular_activo(mundo, ocupacion, cargo_delegado)
    acto = acto_eficaz(mundo, cargo_delegante, medio="GACETA")
    body = cuerpo(
        asig_del["funcionario"],
        cargo_delegante,
        acto,
        figura="DELEGACION_ATRIBUCIONES",
        cargo_origen_id=cargo_delegado,
        rendicion="Informe mensual de rendición de cuentas",
        declara_delegable=True,
        competencias=[{"accion": "APROBAR", "materia": "PRESUPUESTO"}],
    )
    body.update(cambios)
    return body


def _comision(mundo, ocupacion, **cambios):
    _cerrar_vigentes(mundo, "TITULAR")
    body = _suplencia(
        mundo,
        ocupacion,
        figura="COMISION_SERVICIO",
        **{k: v for k, v in cambios.items() if k != "maxima_autoridad"},
    )
    body.pop("maxima_autoridad", None)
    body["hasta"] = cambios.get("hasta", D(2, 20).isoformat())
    # La comisión de servicio la dispone otro cargo (un cargo no se designa a sí mismo).
    body["acto_id"] = acto_eficaz(mundo, ocupacion["cargo_emisor"])
    return body


def test_p0_no_municipal_sin_autorizacion(mundo, gobierno, ocupacion):
    _cerrar_vigentes(mundo, "SUPLENCIA")
    try:
        _nivel(mundo, "ESTADAL")
        body = _suplencia(mundo, ocupacion)
        resp = post_asignacion(mundo, body)
        assert resp.status_code == 201, resp.text
        asignacion = resp.json()

        resp = accion(mundo, asignacion, "activar")
        assert resp.status_code == 200, resp.text
        detalle = resp.json()
        assert detalle["regla"]["origen"] == "PISO_LEGAL"
        assert detalle["regla_congelada"] is True
    finally:
        _nivel(mundo, "MUNICIPAL")


def test_p0_municipal_exige_autorizacion(mundo, gobierno, ocupacion):
    _cerrar_vigentes(mundo, "SUPLENCIA")
    body = _suplencia(mundo, ocupacion)
    resp = post_asignacion(mundo, body)
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "GOV_ASSIGNMENT_LIMIT_EXCEEDED"
    assert "Concejo Municipal" in resp.json()["message"]

    body["autorizacion_especial"] = "Acuerdo N.º 12 del Concejo"
    resp = post_asignacion(mundo, body)
    assert resp.status_code == 201, resp.text


def test_politica_exige_autorizacion_en_ente_no_municipal(mundo, gobierno, ocupacion):
    _cerrar_vigentes(mundo, "SUPLENCIA")
    try:
        _nivel(mundo, "NACIONAL")
        politica = _politica(
            mundo,
            "SUPLENCIA",
            autorizacion_requerida=True,
            autorizacion_etiqueta="Autorización del Consejo Directivo",
            autorizacion_ambito="TODAS",
            autorizacion_mas_de_dias=10,
        )

        body = _suplencia(mundo, ocupacion)
        resp = post_asignacion(mundo, body)
        assert resp.status_code == 422, resp.text
        assert "Consejo Directivo" in resp.json()["message"]

        body["autorizacion_especial"] = "Autorización del Consejo Directivo N.º 1"
        resp = post_asignacion(mundo, body)
        assert resp.status_code == 201, resp.text
        asignacion = resp.json()

        resp = accion(mundo, asignacion, "activar")
        assert resp.status_code == 200, resp.text
        assert resp.json()["regla"]["politica"]["codigo"] == politica["codigo"]
    finally:
        _nivel(mundo, "MUNICIPAL")


def test_congelacion_de_version(mundo, gobierno, ocupacion):
    _cerrar_vigentes(mundo, "COMISION_SERVICIO")
    politica_v1 = _politica(mundo, "COMISION_SERVICIO", max_dias=60)

    body = _comision(mundo, ocupacion)
    resp = post_asignacion(mundo, body)
    assert resp.status_code == 201, resp.text
    asignacion_a = resp.json()
    resp = accion(mundo, asignacion_a, "activar")
    assert resp.status_code == 200, resp.text
    assert resp.json()["regla"]["politica"]["numero_version"] == 1

    resp = mundo.client.post(
        f"/api/v1{P}/{politica_v1['id']}/nueva-version",
        headers={**mundo.como("uab", mundo.company_a), "If-Match": str(politica_v1["version"])},
    )
    assert resp.status_code == 201, resp.text
    v2 = resp.json()
    resp = mundo.client.put(
        f"/api/v1{P}/{v2['id']}",
        headers={**mundo.como("uab", mundo.company_a), "If-Match": str(v2["version"])},
        json=_entrada(v2, max_dias=10),
    )
    assert resp.status_code == 200, resp.text
    v2 = resp.json()
    resp = mundo.client.post(
        f"/api/v1{P}/{v2['id']}/activar",
        headers={**mundo.como("uab", mundo.company_a), "If-Match": str(v2["version"])},
    )
    assert resp.status_code == 200, resp.text

    resp = mundo.client.get(
        f"/api/v1{O}/asignaciones/{asignacion_a['id']}",
        headers=mundo.como("ua", mundo.company_a),
    )
    assert resp.status_code == 200, resp.text
    detalle_a = resp.json()
    assert "v1" in detalle_a["regla"]["regla_version"]
    assert detalle_a["regla_congelada"] is True

    body_b = _comision(mundo, ocupacion)
    resp = post_asignacion(mundo, body_b)
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "GOV_ASSIGNMENT_LIMIT_EXCEEDED"


def test_competencias_permitidas(mundo, gobierno, ocupacion):
    _cerrar_vigentes(mundo, "DELEGACION_ATRIBUCIONES")
    _politica(
        mundo,
        "DELEGACION_ATRIBUCIONES",
        competencias=[{"accion": "FIRMAR", "materia": "PRESUPUESTO"}],
    )
    body = _delegacion(mundo, ocupacion)
    resp = post_asignacion(mundo, body)
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "GOV_ASSIGNMENT_NOT_DELEGABLE"


def test_emisor_por_cargo(mundo, gobierno, ocupacion):
    _cerrar_vigentes(mundo, "ENCARGADURIA")
    cargo_x = nuevo_cargo(mundo, ocupacion, unidad="unidad_otra")
    _politica(
        mundo,
        "ENCARGADURIA",
        emisor_tipo="CARGO",
        emisor_position_id=cargo_x,
    )

    cargo_encargado = nuevo_cargo(mundo, ocupacion, unidad="unidad_otra")
    asig_enc, _ = titular_activo(mundo, ocupacion, cargo_encargado)
    body = cuerpo(
        asig_enc["funcionario"],
        cargo_encargado,
        acto_eficaz(mundo, ocupacion["cargo_emisor"]),
        figura="ENCARGADURIA",
    )
    resp = post_asignacion(mundo, body)
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "GOV_ASSIGNMENT_ISSUER_INVALID"

    body["acto_id"] = acto_eficaz(mundo, cargo_x)
    resp = post_asignacion(mundo, body)
    assert resp.status_code == 201, resp.text


def test_documento_obligatorio_al_activar(mundo, gobierno, ocupacion):
    _cerrar_vigentes(mundo, "TITULAR")
    try:
        with mundo.factory() as db:
            dt = DocumentType(
                company_id=mundo.company_a,
                code=f"DT-{uuid.uuid4().hex[:6]}",
                name="Decreto de designación",
            )
            db.add(dt)
            db.commit()
            dt_id = dt.id

        _politica(
            mundo,
            "TITULAR",
            documentos=[{"document_type_id": dt_id, "etapa": "ACTIVACION", "obligatorio": True}],
        )

        cargo_titular = nuevo_cargo(mundo, ocupacion, unidad="unidad_otra")
        body = cuerpo(
            crear_funcionario(mundo),
            cargo_titular,
            acto_eficaz(mundo, ocupacion["cargo_emisor"]),
            figura="TITULAR",
        )
        resp = post_asignacion(mundo, body)
        assert resp.status_code == 201, resp.text
        asignacion = resp.json()

        resp = accion(mundo, asignacion, "activar")
        assert resp.status_code == 422, resp.text
        assert resp.json()["code"] == "GOV_ASSIGNMENT_DOCUMENTS_MISSING"
        assert "Decreto de designación" in resp.json()["message"]
    finally:
        _cerrar_vigentes(mundo, "TITULAR")


def test_avocacion_prohibida_por_politica(mundo, gobierno, ocupacion):
    _cerrar_vigentes(mundo, "DELEGACION_ATRIBUCIONES")
    _politica(mundo, "DELEGACION_ATRIBUCIONES", prohibe_avocacion=True)
    body = _delegacion(mundo, ocupacion)
    resp = post_asignacion(mundo, body)
    assert resp.status_code == 201, resp.text
    asignacion = resp.json()
    resp = accion(mundo, asignacion, "activar")
    assert resp.status_code == 200, resp.text
    asignacion = resp.json()

    resp = accion(
        mundo,
        asignacion,
        "avocar",
        {
            "acto_id": acto_eficaz(mundo, asignacion["cargo"]["id"], medio="GACETA"),
            "asunto": "Asunto avocado de prueba",
        },
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "GOV_ASSIGNMENT_INVALID"


def test_legado_regla_historica(mundo, gobierno, ocupacion):
    _cerrar_vigentes(mundo, "TITULAR")
    cargo_titular = nuevo_cargo(mundo, ocupacion, unidad="unidad_otra")
    body = cuerpo(
        crear_funcionario(mundo),
        cargo_titular,
        acto_eficaz(mundo, ocupacion["cargo_emisor"]),
        figura="TITULAR",
    )
    asignacion = crear(mundo, body)

    with mundo.factory() as db:
        db.execute(text("UPDATE gov_assignments SET regla = NULL WHERE id = :id"), {"id": asignacion["id"]})
        db.commit()

    resp = mundo.client.get(
        f"/api/v1{O}/asignaciones/{asignacion['id']}",
        headers=mundo.como("ua", mundo.company_a),
    )
    assert resp.status_code == 200, resp.text
    detalle = resp.json()
    assert detalle["regla"]["origen"] == "HISTORICA"
    assert detalle["regla_congelada"] is False


def test_regla_congelada_inmutable_pg(mundo, gobierno, ocupacion):
    _cerrar_vigentes(mundo, "TITULAR")
    asignacion, _ = titular_activo(mundo, ocupacion, nuevo_cargo(mundo, ocupacion, unidad="unidad_otra"))

    with pytest.raises(DBAPIError):
        with mundo.factory() as db:
            db.execute(text("UPDATE gov_assignments SET regla = NULL WHERE id = :id"), {"id": asignacion["id"]})
            db.commit()
    with mundo.factory() as db:
        db.rollback()
