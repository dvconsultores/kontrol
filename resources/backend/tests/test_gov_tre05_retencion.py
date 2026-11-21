"""TRE-05 · Retención de Tesorería — pruebas backend (casos 01–15)."""

from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.modules.audit.models import AuditEvent
from app.modules.identity_access.models import User, UserScope
from app.shared.clock import hoy_de_negocio
from tests.test_gov_tre03_orden_pago import _get_op, _post_op
from tests.tre05_ayudantes import (
    R,
    aislar_caches,
    beneficiario,
    calcular,
    cargo_aprobador,
    concepto,
    cuentas_t05,
    pago_listo,
    politica_ret,
    regla,
    tasa_aprobada,
)

pytest_plugins = (
    "tests.conftest_multicompany",
    "tests.test_gov_ctl06_hallazgos",
    "tests.org04_ayudantes",
)


@pytest.fixture(scope="module", autouse=True)
def _aislar_caches_tre05():
    aislar_caches()
    yield
    aislar_caches()


def test_t05_01_crear_politica(mundo, gobierno, ocupacion):
    cuentas_t05(mundo)
    concepto_obj = concepto(mundo)

    # Creación mínima válida
    politica = politica_ret(mundo, "VES", [regla(concepto_obj)], activar=False)
    assert str(politica["codigo"]).startswith("P")
    assert politica["estado"] == "BORRADOR"
    assert politica["numero_version"] == 1
    assert politica["estado_verificacion"] == "PENDING_PIN"

    with mundo.factory() as db:
        assert db.scalar(
            select(AuditEvent).where(
                AuditEvent.action == "GOV_WITHHOLDING_POLICY_CREATED",
                AuditEvent.entity_id == politica["id"],
            )
        )

    # política legal sin fuente descripción verificable
    codigo = "P" + uuid4().hex[:8].upper()
    r = _post_op(
        mundo,
        f"{R}/politicas",
        "rt_mk",
        {
            "codigo": codigo,
            "nombre": "Política legal",
            "moneda": "VES",
            "aprobador_competencia_accion": "APROBAR",
            "aprobador_competencia_materia": "TESORERIA",
            "vigente_desde": (hoy_de_negocio() + timedelta(days=1)).isoformat(),
            "tipo_regla": "LEGAL_MANDATORY",
            "reglas": [regla(concepto_obj)],
        },
    )
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "GOV_WITHHOLDING_LEGAL_SOURCE_UNVERIFIED"


def test_t05_02_activar(mundo, gobierno, ocupacion):
    cuentas_t05(mundo)
    concepto_obj = concepto(mundo)

    # política sin fuente
    sin_fuente = politica_ret(
        mundo, "VES", [regla(concepto_obj)], activar=False, fuente_descripcion=None
    )
    r = _post_op(
        mundo,
        f"{R}/politicas/{sin_fuente['id']}/activar",
        "rt_mk",
        {"fundamento": "Fundamento de activación de más de veinte caracteres."},
        version=sin_fuente["version"],
    )
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "GOV_WITHHOLDING_POLICY_SOURCE_REQUIRED"

    # política con fuente pero sin reglas
    sin_reglas = politica_ret(mundo, "VES", [], activar=False)
    r = _post_op(
        mundo,
        f"{R}/politicas/{sin_reglas['id']}/activar",
        "rt_mk",
        {"fundamento": "Fundamento de activación de más de veinte caracteres."},
        version=sin_reglas["version"],
    )
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "GOV_WITHHOLDING_POLICY_RULES_REQUIRED"

    # fundamento corto
    politica = politica_ret(mundo, "VES", [regla(concepto_obj)], activar=False)
    r = _post_op(
        mundo,
        f"{R}/politicas/{politica['id']}/activar",
        "rt_mk",
        {"fundamento": "corto"},
        version=politica["version"],
    )
    assert r.status_code == 422, r.text

    # activación exitosa
    politica_valida = politica_ret(mundo, "VES", [regla(concepto_obj)], activar=False)
    r = _post_op(
        mundo,
        f"{R}/politicas/{politica_valida['id']}/activar",
        "rt_mk",
        {"fundamento": "Fundamento de activación de más de veinte caracteres."},
        version=politica_valida["version"],
    )
    assert r.status_code == 200, r.text
    activa = r.json()
    assert activa["estado"] == "VIGENTE"

    with mundo.factory() as db:
        assert db.scalar(
            select(AuditEvent).where(
                AuditEvent.action == "GOV_WITHHOLDING_POLICY_ACTIVATED",
                AuditEvent.entity_id == politica_valida["id"],
            )
        )


def test_t05_03_cerrar(mundo, gobierno, ocupacion):
    cuentas_t05(mundo)
    concepto_obj = concepto(mundo)
    politica = politica_ret(mundo, "VES", [regla(concepto_obj)])
    r = _post_op(
        mundo,
        f"{R}/politicas/{politica['id']}/cerrar",
        "rt_mk",
        {"motivo": "Motivo de cierre con más de diez caracteres."},
        version=politica["version"],
    )
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "CERRADA"

    vigente = politica_ret(mundo, "VES", [regla(concepto_obj)])
    corto = _post_op(
        mundo,
        f"{R}/politicas/{vigente['id']}/cerrar",
        "rt_mk",
        {"motivo": "corto"},
        version=vigente["version"],
    )
    assert corto.status_code == 422, corto.text

    borrador = politica_ret(mundo, "VES", [regla(concepto_obj)], activar=False)
    r = _post_op(
        mundo,
        f"{R}/politicas/{borrador['id']}/cerrar",
        "rt_mk",
        {"motivo": "Motivo de cierre con más de diez caracteres."},
        version=borrador["version"],
    )
    assert r.status_code == 409, r.text


def test_t05_04_nueva_version(mundo, gobierno, ocupacion):
    cuentas_t05(mundo)
    concepto_obj = concepto(mundo)
    politica_v1 = politica_ret(mundo, "VES", [regla(concepto_obj)])
    r = _post_op(mundo, f"{R}/politicas/{politica_v1['id']}/nueva-version", "rt_mk", {})
    assert r.status_code == 201, r.text
    politica_v2 = r.json()
    assert politica_v2["numero_version"] == 2
    assert politica_v2["estado"] == "BORRADOR"
    assert len(politica_v2["reglas"]) == len(politica_v1["reglas"])

    r = _post_op(mundo, f"{R}/politicas/{politica_v1['id']}/nueva-version", "rt_mk", {})
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_WITHHOLDING_POLICY_DRAFT_EXISTS"

    r = _post_op(
        mundo,
        f"{R}/politicas/{politica_v2['id']}/activar",
        "rt_mk",
        {"fundamento": "Fundamento de activación de más de veinte caracteres."},
        version=politica_v2["version"],
    )
    assert r.status_code == 200, r.text
    v1 = _get_op(mundo, f"{R}/politicas/{politica_v1['id']}", usuario="rt_mk")
    assert v1.status_code == 200, v1.text
    assert v1.json()["estado"] == "CERRADA"


def test_t05_05_procedencia(mundo, gobierno, ocupacion):
    cuentas_t05(mundo)
    concepto_obj = concepto(mundo)
    politica = politica_ret(mundo, "VES", [regla(concepto_obj)])
    datos = pago_listo(mundo, ocupacion, autorizado=True)
    r = calcular(
        mundo,
        datos["pago"],
        politica,
        [concepto_obj["codigo"]],
        beneficiario(),
    )
    assert r.status_code == 201, r.text
    liq = r.json()
    assert liq["politica_fuente"]["fuente_descripcion"] == "Acto del ente de prueba"
    assert liq["politica_fuente"]["fuente_referencia"] == "Art. 1"
    assert liq["politica_fuente"]["estado_verificacion"] == "PENDING_PIN"

    historia = _get_op(mundo, f"{R}/politicas/{politica['id']}/historia", usuario="rt_mk")
    assert historia.status_code == 200, historia.text
    hitos = [h["evento"] for h in historia.json()]
    assert "CREADA" in hitos
    assert "ACTIVADA" in hitos


def test_t05_06_vigencia(mundo, gobierno, ocupacion):
    cuentas_t05(mundo)
    concepto_obj = concepto(mundo)
    manana = (hoy_de_negocio() + timedelta(days=1)).isoformat()
    politica = politica_ret(
        mundo,
        "VES",
        [regla(concepto_obj)],
        vigente_desde=manana,
        activar=False,
    )
    r = _post_op(
        mundo,
        f"{R}/politicas/{politica['id']}/activar",
        "rt_mk",
        {"fundamento": "Fundamento de activación de más de veinte caracteres."},
        version=politica["version"],
    )
    assert r.status_code == 200, r.text
    politica_activa = r.json()
    datos = pago_listo(mundo, ocupacion)
    r = calcular(
        mundo,
        datos["pago"],
        politica_activa,
        [concepto_obj["codigo"]],
        beneficiario(),
    )
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "GOV_WITHHOLDING_POLICY_NOT_APPLICABLE"


def test_t05_07_aislamiento_tenant_empresa(mundo, gobierno, ocupacion):
    cuentas_t05(mundo)
    concepto_obj = concepto(mundo)
    politica = politica_ret(mundo, "VES", [regla(concepto_obj)])

    with mundo.factory() as db:
        rt_ver = db.scalar(select(User).where(User.username == "rt_ver"))
        db.add(UserScope(user_id=rt_ver.id, company_id=mundo.company_b))
        db.commit()

    r = _get_op(mundo, f"{R}/politicas", usuario="rt_ver", empresa=mundo.company_b)
    assert r.status_code == 200, r.text
    ids_politicas = {p["id"] for p in r.json()}
    assert politica["id"] not in ids_politicas

    r = _get_op(
        mundo,
        f"{R}/catalogo?tipo=CONCEPTO",
        usuario="rt_ver",
        empresa=mundo.company_b,
    )
    assert r.status_code == 200, r.text
    ids_conceptos = {c["id"] for c in r.json()}
    assert concepto_obj["id"] not in ids_conceptos

    r = _get_op(
        mundo,
        f"{R}/politicas/{politica['id']}",
        usuario="rt_ver",
        empresa=mundo.company_b,
    )
    assert r.status_code == 404, r.text

    # tenant "uc" sin permisos de retenciones ve 403 o 404
    r = mundo.client.get(
        f"/api/v1{R}/politicas",
        headers=mundo.como("uc", mundo.company_c, tenant="T2"),
    )
    assert r.status_code in (200, 403, 404), r.text
    if r.status_code == 200:
        ids_politicas = {p["id"] for p in r.json()}
        assert politica["id"] not in ids_politicas


def test_t05_08_aislamiento_empresa_liquidacion(mundo, gobierno, ocupacion):
    cuentas_t05(mundo)
    concepto_obj = concepto(mundo)
    politica = politica_ret(mundo, "VES", [regla(concepto_obj)])
    datos = pago_listo(mundo, ocupacion)
    r = calcular(
        mundo,
        datos["pago"],
        politica,
        [concepto_obj["codigo"]],
        beneficiario(),
    )
    assert r.status_code == 201, r.text
    liq = r.json()

    with mundo.factory() as db:
        mk = db.scalar(select(User).where(User.username == "rt_mk"))
        ck = db.scalar(select(User).where(User.username == "rt_ck"))
        db.add(UserScope(user_id=mk.id, company_id=mundo.company_b))
        db.add(UserScope(user_id=ck.id, company_id=mundo.company_b))
        db.commit()

    datos2 = pago_listo(mundo, ocupacion)
    r = _post_op(
        mundo,
        f"{R}/pagos/{datos2['pago']['id']}/liquidacion",
        "rt_mk",
        {"policy_id": politica["id"], "conceptos": [concepto_obj["codigo"]], "beneficiario": beneficiario()},
        empresa=mundo.company_b,
    )
    assert r.status_code == 404, r.text

    cargo = cargo_aprobador(mundo, ocupacion)
    r = _post_op(
        mundo,
        f"{R}/liquidaciones/{liq['id']}/aprobar",
        "rt_ck",
        {"cargo_id": cargo},
        empresa=mundo.company_b,
        version=liq["version"],
    )
    assert r.status_code == 404, r.text

    r = _post_op(
        mundo,
        f"{R}/liquidaciones/{liq['id']}/descartar",
        usuario="rt_mk",
        cuerpo={"motivo": "Motivo de descarte con más de diez caracteres."},
        version=liq["version"],
        empresa=mundo.company_b,
    )
    assert r.status_code == 404, r.text

    r = _get_op(
        mundo,
        f"{R}/liquidaciones/{liq['id']}",
        usuario="rt_mk",
        empresa=mundo.company_b,
    )
    assert r.status_code == 404, r.text


def test_t05_09_regla_aplicable(mundo, gobierno, ocupacion):
    cuentas_t05(mundo)
    concepto_obj = concepto(mundo)
    politica = politica_ret(mundo, "VES", [regla(concepto_obj, tasa="5")])
    datos = pago_listo(mundo, ocupacion, monto="100.00")
    r = calcular(
        mundo,
        datos["pago"],
        politica,
        [concepto_obj["codigo"]],
        beneficiario(),
    )
    assert r.status_code == 201, r.text
    liq = r.json()
    assert len(liq["lineas"]) == 1
    linea = liq["lineas"][0]
    assert linea["aplica"] is True
    assert linea["monto_calculado"] == "5.00"
    assert liq["total_retenido"] == "5.00"
    assert liq["neto"] == "95.00"


def test_t05_10_regla_no_aplicable(mundo, gobierno, ocupacion):
    cuentas_t05(mundo)
    concepto_a = concepto(mundo)
    concepto_b = concepto(mundo)
    politica = politica_ret(
        mundo,
        "VES",
        [
            regla(concepto_a, tipos_persona=["NATURAL"], orden=1),
            regla(concepto_b, orden=2),
        ],
    )
    datos = pago_listo(mundo, ocupacion, monto="100.00")
    r = calcular(
        mundo,
        datos["pago"],
        politica,
        [concepto_a["codigo"]],
        beneficiario(tipo="JURIDICA"),
    )
    assert r.status_code == 201, r.text
    liq = r.json()
    lineas = {linea["orden"]: linea for linea in liq["lineas"]}
    assert lineas[1]["aplica"] is False
    assert lineas[1]["motivo_no_aplica"] == "TIPO_PERSONA"
    assert lineas[2]["aplica"] is False
    assert lineas[2]["motivo_no_aplica"] == "CONCEPTO_NO_SELECCIONADO"
    assert liq["total_retenido"] == "0.00"


def test_t05_11_base_porcentaje_del_bruto(mundo, gobierno, ocupacion):
    cuentas_t05(mundo)
    concepto_obj = concepto(mundo)
    politica = politica_ret(
        mundo,
        "VES",
        [regla(concepto_obj, base_tipo="PORCENTAJE_DEL_BRUTO", base_porcentaje="70", tasa="10")],
    )
    datos = pago_listo(mundo, ocupacion, monto="1000.00")
    r = calcular(
        mundo,
        datos["pago"],
        politica,
        [concepto_obj["codigo"]],
        beneficiario(),
    )
    assert r.status_code == 201, r.text
    linea = r.json()["lineas"][0]
    assert linea["base"] == "700.00"
    assert linea["monto_calculado"] == "70.00"


def test_t05_12_alicuota_y_redondeo(mundo, gobierno, ocupacion):
    cuentas_t05(mundo)
    concepto_obj = concepto(mundo)
    politica = politica_ret(
        mundo,
        "VES",
        [regla(concepto_obj, tasa="3.5")],
        redondeo_decimales=2,
        redondeo_modo="HALF_UP",
    )
    datos = pago_listo(mundo, ocupacion, monto="200.00")
    r = calcular(
        mundo,
        datos["pago"],
        politica,
        [concepto_obj["codigo"]],
        beneficiario(),
    )
    assert r.status_code == 201, r.text
    assert r.json()["lineas"][0]["monto_calculado"] == "7.00"

    politica_15 = politica_ret(
        mundo,
        "VES",
        [regla(concepto_obj, tasa="1.5")],
        redondeo_decimales=2,
        redondeo_modo="HALF_UP",
    )
    datos2 = pago_listo(mundo, ocupacion, monto="333.33")
    r = calcular(
        mundo,
        datos2["pago"],
        politica_15,
        [concepto_obj["codigo"]],
        beneficiario(),
    )
    assert r.status_code == 201, r.text
    assert r.json()["lineas"][0]["monto_calculado"] == "5.00"


def test_t05_13_umbral(mundo, gobierno, ocupacion):
    cuentas_t05(mundo)
    concepto_obj = concepto(mundo)
    politica = politica_ret(
        mundo,
        "VES",
        [regla(concepto_obj, umbral_tipo="MONTO", umbral_monto="150", tasa="5")],
    )
    datos = pago_listo(mundo, ocupacion, monto="100.00")
    r = calcular(
        mundo,
        datos["pago"],
        politica,
        [concepto_obj["codigo"]],
        beneficiario(),
    )
    assert r.status_code == 201, r.text
    assert r.json()["lineas"][0]["motivo_no_aplica"] == "UMBRAL"

    datos2 = pago_listo(mundo, ocupacion, monto="200.00")
    r = calcular(
        mundo,
        datos2["pago"],
        politica,
        [concepto_obj["codigo"]],
        beneficiario(),
    )
    assert r.status_code == 201, r.text
    assert r.json()["lineas"][0]["aplica"] is True

    concepto_mult = concepto(mundo)
    politica_mult = politica_ret(
        mundo,
        "VES",
        [
            regla(
                concepto_mult,
                umbral_tipo="MULTIPLO_TASA",
                umbral_multiplo="10",
                umbral_moneda_tasa="USD",
                tasa="5",
            )
        ],
    )
    datos3 = pago_listo(mundo, ocupacion, monto="30.00")
    tasa_aprobada(mundo, datos3["s"], moneda="USD", valor="4.00")
    r = calcular(
        mundo,
        datos3["pago"],
        politica_mult,
        [concepto_mult["codigo"]],
        beneficiario(),
    )
    assert r.status_code == 201, r.text
    linea = r.json()["lineas"][0]
    assert linea["motivo_no_aplica"] == "UMBRAL"
    assert linea["tasa_referencia"]["valor"] == "4.000000000000"

    concepto_eur = concepto(mundo)
    politica_eur = politica_ret(
        mundo,
        "VES",
        [
            regla(
                concepto_eur,
                umbral_tipo="MULTIPLO_TASA",
                umbral_multiplo="10",
                umbral_moneda_tasa="EUR",
                tasa="5",
            )
        ],
    )
    datos4 = pago_listo(mundo, ocupacion, monto="10.00")
    r = calcular(
        mundo,
        datos4["pago"],
        politica_eur,
        [concepto_eur["codigo"]],
        beneficiario(),
    )
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "GOV_WITHHOLDING_RATE_MISSING"
