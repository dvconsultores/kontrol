import os

import pytest
from sqlalchemy import func, select

from app.modules.government.models import GovernmentUserOfficialLink
from app.shared.clock import hoy_de_negocio
from tests.org06_ayudantes import I, consultar, crear_funcionario, crear_vinculo, cuenta, cuerpo_vinculo, vinculo_activo
from tests.org06_guarda import rol_de
from tests.test_gov_ctl01_reglas import cerrar_regla, regla_vigente
from tests.test_gov_org04_concurrencia import _carrera

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos", "tests.org04_ayudantes")

pytestmark = pytest.mark.skipif(
    not os.environ.get("KONTROL_TEST_DB_URL", "").startswith("postgresql"),
    reason="la carrera se mide en PostgreSQL",
)


def _post(mundo, cabeceras, ruta, cuerpo=None, version=None):
    h = dict(cabeceras)
    if version is not None:
        h["If-Match"] = str(version)
    return mundo.client.post(f"/api/v1{I}{ruta}", headers=h, json=cuerpo or {})


def _activos(mundo, columna, valor):
    with mundo.factory() as db:
        return db.scalar(
            select(func.count())
            .select_from(GovernmentUserOfficialLink)
            .where(columna == valor, GovernmentUserOfficialLink.status == "ACTIVO")
        )


def test_c01_misma_cuenta_dos_funcionarios(mundo, gobierno, ocupacion):
    user_id = cuenta(mundo, "org06_c01")
    f1 = crear_funcionario(mundo)
    f2 = crear_funcionario(mundo)
    v1 = crear_vinculo(mundo, cuerpo_vinculo(user_id, f1["id"]))
    v2 = crear_vinculo(mundo, cuerpo_vinculo(user_id, f2["id"]))

    cabeceras = mundo.como("uab", mundo.company_a)

    def activar_v1(m):
        return _post(m, cabeceras, f"/vinculos/{v1['id']}/activar", version=v1["version"])

    def activar_v2(m):
        return _post(m, cabeceras, f"/vinculos/{v2['id']}/activar", version=v2["version"])

    r1, r2 = _carrera(mundo, [activar_v1, activar_v2])
    codigos = sorted([r1.status_code, r2.status_code])
    assert codigos == [200, 409]
    conflicto = r1 if r1.status_code == 409 else r2
    assert conflicto.json()["code"] == "GOV_IDENTITY_OVERLAP"
    assert _activos(mundo, GovernmentUserOfficialLink.user_id, user_id) == 1


def test_c02_mismo_funcionario_dos_cuentas(mundo, gobierno, ocupacion):
    user_a = cuenta(mundo, "org06_c02_a")
    user_b = cuenta(mundo, "org06_c02_b")
    f = crear_funcionario(mundo)
    f_id = f["id"]
    v1 = crear_vinculo(mundo, cuerpo_vinculo(user_a, f_id))
    v2 = crear_vinculo(mundo, cuerpo_vinculo(user_b, f_id))

    cabeceras = mundo.como("uab", mundo.company_a)

    def activar_v1(m):
        return _post(m, cabeceras, f"/vinculos/{v1['id']}/activar", version=v1["version"])

    def activar_v2(m):
        return _post(m, cabeceras, f"/vinculos/{v2['id']}/activar", version=v2["version"])

    r1, r2 = _carrera(mundo, [activar_v1, activar_v2])
    codigos = sorted([r1.status_code, r2.status_code])
    assert codigos == [200, 409]
    conflicto = r1 if r1.status_code == 409 else r2
    assert conflicto.json()["code"] == "GOV_IDENTITY_OVERLAP"
    assert _activos(mundo, GovernmentUserOfficialLink.official_id, f_id) == 1


def test_c03_mismo_vinculo_misma_version(mundo, gobierno, ocupacion):
    user_id = cuenta(mundo, "org06_c03")
    f = crear_funcionario(mundo)
    v = crear_vinculo(mundo, cuerpo_vinculo(user_id, f["id"]))

    cabeceras = mundo.como("uab", mundo.company_a)

    def activar_1(m):
        return _post(m, cabeceras, f"/vinculos/{v['id']}/activar", version=v["version"])

    def activar_2(m):
        return _post(m, cabeceras, f"/vinculos/{v['id']}/activar", version=v["version"])

    r1, r2 = _carrera(mundo, [activar_1, activar_2])
    codigos = sorted([r1.status_code, r2.status_code])
    assert codigos == [200, 409]
    conflicto = r1 if r1.status_code == 409 else r2
    assert conflicto.json()["code"] in {"GOV_IDENTITY_STALE", "GOV_IDENTITY_INVALID_STATE"}


def test_c04_cierre_y_alta(mundo, gobierno, ocupacion):
    user_a = cuenta(mundo, "org06_c04_a")
    user_b = cuenta(mundo, "org06_c04_b")
    f = crear_funcionario(mundo)
    f_id = f["id"]
    hoy = hoy_de_negocio()
    hoy_iso = hoy.isoformat()

    activo = vinculo_activo(mundo, cuerpo_vinculo(user_a, f_id))

    v2 = crear_vinculo(mundo, cuerpo_vinculo(user_b, f_id, desde=hoy_iso))

    cabeceras_uab = mundo.como("uab", mundo.company_a)

    def cerrar_v1(m):
        return _post(
            m,
            cabeceras_uab,
            f"/vinculos/{activo['id']}/cerrar",
            cuerpo={"fecha": hoy_iso, "motivo": "Cierre del vínculo de prueba."},
            version=activo["version"],
        )

    def activar_v2(m):
        return _post(m, cabeceras_uab, f"/vinculos/{v2['id']}/activar", version=v2["version"])

    r1, r2 = _carrera(mundo, [cerrar_v1, activar_v2])

    with mundo.factory() as db:
        hoy_activos = db.scalar(
            select(func.count())
            .select_from(GovernmentUserOfficialLink)
            .where(
                GovernmentUserOfficialLink.official_id == f_id,
                GovernmentUserOfficialLink.status == "ACTIVO",
                GovernmentUserOfficialLink.desde <= hoy,
                (func.coalesce(GovernmentUserOfficialLink.fin_efectivo, GovernmentUserOfficialLink.hasta).is_(None)) | (func.coalesce(GovernmentUserOfficialLink.fin_efectivo, GovernmentUserOfficialLink.hasta) >= hoy),
            )
        )

    assert hoy_activos <= 1
    assert any(r.status_code == 200 for r in (r1, r2))


def test_c05_politica_concurrente(mundo, gobierno, ocupacion):
    cabeceras_ua = mundo.como("ua", mundo.company_a)
    get_politica = consultar(mundo, "/politica", usuario="ua")
    version = get_politica.json()["version"]

    def post_true(m):
        return _post(
            m,
            cabeceras_ua,
            "/politica",
            cuerpo={"exige_identidad": True, "motivo": "Cambio concurrente de la política."},
            version=version,
        )

    def post_false(m):
        return _post(
            m,
            cabeceras_ua,
            "/politica",
            cuerpo={"exige_identidad": False, "motivo": "Cambio concurrente de la política."},
            version=version,
        )

    try:
        r1, r2 = _carrera(mundo, [post_true, post_false])
        codigos = sorted([r1.status_code, r2.status_code])
        assert codigos == [200, 409]
        conflicto = r1 if r1.status_code == 409 else r2
        assert conflicto.json()["code"] == "GOV_IDENTITY_STALE"
    finally:
        get_politica = consultar(mundo, "/politica", usuario="ua")
        datos = get_politica.json()
        if datos.get("exige_identidad") is True:
            _post(
                mundo,
                cabeceras_ua,
                "/politica",
                cuerpo={"exige_identidad": False, "motivo": "Restaurar política por defecto."},
                version=datos["version"],
            )


def test_c06_clasificar_frente_a_activar(mundo, gobierno, ocupacion):
    user_id = cuenta(mundo, "org06_c06")
    role_id = rol_de(mundo, "org06_c06")
    regla = regla_vigente(
        mundo,
        proceso="ORG-06",
        accion_a="ORG06_CAT_OPERATIVO",
        accion_b="ORG06_CAT_APROBADOR",
        bidireccional=True,
        nombre="Incompatibilidad concurrente",
    )

    cabeceras_ua = mundo.como("ua", mundo.company_a)
    cabeceras_uab = mundo.como("uab", mundo.company_a)

    try:
        desde = hoy_de_negocio().replace(month=1, day=1).isoformat()
        clasificar = _post(
            mundo,
            cabeceras_ua,
            "/categorias",
            cuerpo={
                "role_id": role_id,
                "categoria": "OPERATIVO",
                "desde": desde,
                "motivo": "Clasificación del rol de prueba.",
            },
        )
        assert clasificar.status_code == 201

        f = crear_funcionario(mundo)
        v = crear_vinculo(mundo, cuerpo_vinculo(user_id, f["id"]))

        def clasificar_aprobador(m):
            return _post(
                m,
                cabeceras_ua,
                "/categorias",
                cuerpo={
                    "role_id": role_id,
                    "categoria": "APROBADOR",
                    "desde": desde,
                    "motivo": "Clasificación del rol de prueba.",
                },
            )

        def activar_vinculo(m):
            return _post(m, cabeceras_uab, f"/vinculos/{v['id']}/activar", version=v["version"])

        r1, r2 = _carrera(mundo, [clasificar_aprobador, activar_vinculo])

        assert not (r1.status_code == 201 and r2.status_code == 200)
        fallo = r1 if r1.status_code == 409 else r2
        assert fallo.status_code == 409
        assert fallo.json()["code"] == "GOV_SOD_CONFLICT"
    finally:
        cerrar_regla(mundo, regla)
