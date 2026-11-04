from datetime import timedelta

from tests.test_gov_ctl01_reglas import (
    HOY,
    S,
    activar_regla,
    cerrar_regla,
    crear_regla,
    eventos,
    regla_vigente,
)
from tests.test_gov_ctl06_hallazgos import (
    H,
    _crear_usuario_con_permisos,
    _cuerpo_independiente,
    _doc_vinculado,
    _hallazgo_en_remediacion,
    _post,
)

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos")


def test_sg01_bloqueo_sin_mutacion_evidencia_y_otro_actor(mundo, gobierno, siembra):
    """SG-01: bloqueo, sin mutación, evidencia y otro actor."""
    regla = regla_vigente(
        mundo, accion_a="CTL06_REGISTRAR", accion_b="CTL06_RECOMENDAR"
    )
    try:
        r = _post(mundo, H, "ua", mundo.company_a, _cuerpo_independiente())
        assert r.status_code == 201, r.text
        detalle = r.json()
        hallazgo_id = detalle["id"]
        version_antes = detalle["version"]

        r = _post(
            mundo,
            f"{H}/{hallazgo_id}/recomendaciones",
            "ua",
            mundo.company_a,
            {"texto": "recomendación del mismo actor"},
            version=version_antes,
        )
        assert r.status_code == 409, r.text
        cuerpo = r.json()
        assert cuerpo["code"] == "GOV_SOD_CONFLICT", r.text
        assert "segregación de funciones" in cuerpo["message"], r.text
        assert "Registrar el hallazgo" in cuerpo["message"], r.text
        details = cuerpo["details"]
        assert details["regla_codigo"] == regla["codigo"], r.text
        assert details["accion"] == "CTL06_RECOMENDAR", r.text
        assert details["accion_previa"] == "CTL06_REGISTRAR", r.text
        assert details["objeto_tipo"] == "GovernmentFinding", r.text
        assert details["objeto_id"] == hallazgo_id, r.text

        r = mundo.get(f"{H}/{hallazgo_id}", "ua", mundo.company_a)
        assert r.status_code == 200, r.text
        detalle_actual = r.json()
        assert detalle_actual["recomendaciones"] == [], r.text
        assert detalle_actual["version"] == version_antes, r.text

        bloqueos = eventos(mundo, "GOV_SOD_CONFLICT_BLOCKED", regla["id"])
        assert len(bloqueos) == 1, bloqueos
        after = bloqueos[0].after
        assert after["accion"] == "CTL06_RECOMENDAR", after
        assert after["objeto_id"] == hallazgo_id, after
        assert after["regla_version"] == regla["version"], after
        assert after["evento_previo_id"], after

        eventos_recomendacion = eventos(
            mundo, "GOV_FINDING_RECOMMENDATION_ADDED", hallazgo_id
        )
        assert eventos_recomendacion == [], eventos_recomendacion

        r = _post(
            mundo,
            f"{H}/{hallazgo_id}/recomendaciones",
            "uab",
            mundo.company_a,
            {"texto": "recomendación de otro actor"},
            version=version_antes,
        )
        assert r.status_code == 201, r.text
        r = mundo.get(f"{H}/{hallazgo_id}", "uab", mundo.company_a)
        assert r.status_code == 200, r.text
        detalle_uab = r.json()
        assert len(detalle_uab["recomendaciones"]) == 1, r.text

        r = mundo.get(f"{S}/reglas/{regla['id']}", "ua", mundo.company_a)
        assert r.status_code == 200, r.text
        detalle_regla = r.json()
        assert detalle_regla["conflictos"] == 1, r.text

        r = mundo.get(
            f"{S}/conflictos?regla_id={regla['id']}", "ua", mundo.company_a
        )
        assert r.status_code == 200, r.text
        conflictos = r.json()
        assert conflictos["total"] == 1, r.text
        assert conflictos["items"][0]["usuario"] == "ua", r.text
        assert (
            conflictos["items"][0]["accion_etiqueta"]
            == "Añadir una recomendación"
        ), r.text
    finally:
        cerrar_regla(mundo, regla, usuario="ua", empresa=mundo.company_a)


def test_sg02_bidireccional(mundo, gobierno, siembra):
    """SG-02: bidireccional."""
    regla = regla_vigente(
        mundo,
        accion_a="CTL06_ACCION",
        accion_b="CTL06_RECOMENDAR",
        bidireccional=True,
    )
    try:
        r = _post(mundo, H, "uab", mundo.company_a, _cuerpo_independiente())
        assert r.status_code == 201, r.text
        detalle = r.json()
        hallazgo_id = detalle["id"]
        version = detalle["version"]

        r = _post(
            mundo,
            f"{H}/{hallazgo_id}/recomendaciones",
            "ua",
            mundo.company_a,
            {"texto": "recomendación"},
            version=version,
        )
        assert r.status_code == 201, r.text
        detalle = r.json()
        recomendacion_id = detalle["recomendaciones"][0]["id"]
        version = detalle["version"]

        r = _post(
            mundo,
            f"{H}/{hallazgo_id}/acciones",
            "ua",
            mundo.company_a,
            {
                "recomendacion_id": recomendacion_id,
                "descripcion": "acción bloqueada por segregación",
                "cargo_id": siembra["cargo_vigente"],
                "fecha_objetivo": (HOY + timedelta(days=30)).isoformat(),
            },
            version=version,
        )
        assert r.status_code == 409, r.text
        cuerpo = r.json()
        assert cuerpo["code"] == "GOV_SOD_CONFLICT", r.text
        assert cuerpo["details"]["accion"] == "CTL06_ACCION", r.text
        assert (
            cuerpo["details"]["accion_previa"] == "CTL06_RECOMENDAR"
        ), r.text

        r = _post(
            mundo,
            f"{H}/{hallazgo_id}/acciones",
            "uab",
            mundo.company_a,
            {
                "recomendacion_id": recomendacion_id,
                "descripcion": "acción correctiva",
                "cargo_id": siembra["cargo_vigente"],
                "fecha_objetivo": (HOY + timedelta(days=30)).isoformat(),
            },
            version=version,
        )
        assert r.status_code == 201, r.text
    finally:
        cerrar_regla(mundo, regla, usuario="ua", empresa=mundo.company_a)


def test_sg03_no_en_vigor(mundo, gobierno, siembra):
    """SG-03: no en vigor."""
    crear_regla(
        mundo,
        accion_a="CTL06_REGISTRAR",
        accion_b="CTL06_RECOMENDAR",
    )
    regla_manana = crear_regla(
        mundo,
        accion_a="CTL06_REGISTRAR",
        accion_b="CTL06_RECOMENDAR",
        vigente_desde=(HOY + timedelta(days=1)).isoformat(),
    )
    regla_manana = activar_regla(
        mundo, regla_manana, usuario="ua", empresa=mundo.company_a
    )
    try:
        r = _post(mundo, H, "ua", mundo.company_a, _cuerpo_independiente())
        assert r.status_code == 201, r.text
        detalle = r.json()
        hallazgo_id = detalle["id"]
        version = detalle["version"]
        assert regla_manana["en_vigor"] is False, regla_manana

        r = _post(
            mundo,
            f"{H}/{hallazgo_id}/recomendaciones",
            "ua",
            mundo.company_a,
            {"texto": "recomendación sin regla en vigor"},
            version=version,
        )
        assert r.status_code == 201, r.text
    finally:
        cerrar_regla(mundo, regla_manana, usuario="ua", empresa=mundo.company_a)


def test_sg04_cerrada(mundo, gobierno, siembra):
    """SG-04: cerrada."""
    regla = regla_vigente(
        mundo, accion_a="CTL06_REGISTRAR", accion_b="CTL06_RECOMENDAR"
    )
    cerrar_regla(mundo, regla, usuario="ua", empresa=mundo.company_a)

    r = _post(mundo, H, "ua", mundo.company_a, _cuerpo_independiente())
    assert r.status_code == 201, r.text
    detalle = r.json()
    hallazgo_id = detalle["id"]
    version = detalle["version"]
    r = _post(
        mundo,
        f"{H}/{hallazgo_id}/recomendaciones",
        "ua",
        mundo.company_a,
        {"texto": "recomendación con regla cerrada"},
        version=version,
    )
    assert r.status_code == 201, r.text


def test_sg05_otra_empresa(mundo, gobierno, siembra):
    """SG-05: otra empresa."""
    regla = crear_regla(
        mundo,
        usuario="ub",
        empresa=mundo.company_b,
        accion_a="CTL06_REGISTRAR",
        accion_b="CTL06_RECOMENDAR",
    )
    regla = activar_regla(
        mundo, regla, usuario="ub", empresa=mundo.company_b
    )
    try:
        r = _post(mundo, H, "ua", mundo.company_a, _cuerpo_independiente())
        assert r.status_code == 201, r.text
        detalle = r.json()
        hallazgo_id = detalle["id"]
        version = detalle["version"]
        r = _post(
            mundo,
            f"{H}/{hallazgo_id}/recomendaciones",
            "ua",
            mundo.company_a,
            {"texto": "recomendación con regla de otra empresa"},
            version=version,
        )
        assert r.status_code == 201, r.text
    finally:
        cerrar_regla(mundo, regla, usuario="ub", empresa=mundo.company_b)


def test_sg06_otro_objeto(mundo, gobierno, siembra):
    """SG-06: otro objeto."""
    regla = regla_vigente(
        mundo, accion_a="CTL06_REGISTRAR", accion_b="CTL06_RECOMENDAR"
    )
    try:
        r = _post(mundo, H, "ua", mundo.company_a, _cuerpo_independiente())
        assert r.status_code == 201, r.text
        detalle_h1 = r.json()
        h1_id = detalle_h1["id"]
        version_h1 = detalle_h1["version"]

        r = _post(mundo, H, "uab", mundo.company_a, _cuerpo_independiente())
        assert r.status_code == 201, r.text
        detalle_h2 = r.json()
        h2_id = detalle_h2["id"]
        version_h2 = detalle_h2["version"]

        r = _post(
            mundo,
            f"{H}/{h2_id}/recomendaciones",
            "ua",
            mundo.company_a,
            {"texto": "recomendación sobre otro objeto"},
            version=version_h2,
        )
        assert r.status_code == 201, r.text

        r = _post(
            mundo,
            f"{H}/{h1_id}/recomendaciones",
            "ua",
            mundo.company_a,
            {"texto": "recomendación sobre objeto propio"},
            version=version_h1,
        )
        assert r.status_code == 409, r.text
        assert r.json()["code"] == "GOV_SOD_CONFLICT", r.text
    finally:
        cerrar_regla(mundo, regla, usuario="ua", empresa=mundo.company_a)


def test_sg07_el_maker_checker_de_ctl06_prevalece(mundo, gobierno, siembra):
    """SG-07: el maker-checker de CTL-06 prevalece."""
    regla = regla_vigente(
        mundo, accion_a="CTL06_PRESENTAR", accion_b="CTL06_VERIFICAR"
    )
    try:
        detalle = _hallazgo_en_remediacion(mundo, siembra)
        hallazgo_id = detalle["id"]
        accion_id = detalle["acciones"][0]["id"]
        documento_id = _doc_vinculado(mundo, mundo.company_a, accion_id)

        r = _post(
            mundo,
            f"{H}/{hallazgo_id}/acciones/{accion_id}/avances",
            "ua",
            mundo.company_a,
            {"nota": "avance al 100 %", "porcentaje": 100, "documento_id": documento_id},
            version=detalle["version"],
        )
        assert r.status_code == 201, r.text
        detalle = r.json()
        version = detalle["version"]

        r = _post(
            mundo,
            f"{H}/{hallazgo_id}/presentar",
            "ua",
            mundo.company_a,
            {},
            version=version,
        )
        assert r.status_code == 200, r.text
        detalle = r.json()
        version = detalle["version"]

        r = _post(
            mundo,
            f"{H}/{hallazgo_id}/verificar",
            "ua",
            mundo.company_a,
            {"nota": "intento de autoverificación"},
            version=version,
        )
        assert r.status_code == 409, r.text
        assert (
            r.json()["code"] == "GOV_FINDING_SELF_VERIFICATION"
        ), r.text

        bloqueos = eventos(mundo, "GOV_SOD_CONFLICT_BLOCKED", regla["id"])
        assert bloqueos == [], bloqueos

        _crear_usuario_con_permisos(
            mundo,
            "verificador_sod",
            [("gobierno_hallazgos", "view"), ("gobierno_hallazgos", "verify")],
            mundo.company_a,
        )
        r = _post(
            mundo,
            f"{H}/{hallazgo_id}/verificar",
            "verificador_sod",
            mundo.company_a,
            {"nota": "verificación por tercero"},
            version=version,
        )
        assert r.status_code == 200, r.text
        assert r.json()["estado"] == "CERRADO", r.text
    finally:
        cerrar_regla(mundo, regla, usuario="ua", empresa=mundo.company_a)
