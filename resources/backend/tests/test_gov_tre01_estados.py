from datetime import date, timedelta

from tests.test_gov_ctl06_hallazgos import _crear_usuario_con_permisos, _post
from tests.test_gov_tre01_cuentas import (
    HOY,
    T,
    activar,
    autorizar,
    crear_banco,
    crear_cuenta,
    cuenta_lista,
    cuenta_vigente,
    dejar_sin_efecto,
    eventos,
    nuevo_acto,
    patch,
    segundo_cargo,
    vincular,
)

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos")


def accion(mundo, cuenta, verbo, cuerpo, usuario="ua", empresa=None, version=None):
    return _post(
        mundo,
        f"{T}/cuentas/{cuenta['id']}/{verbo}",
        usuario,
        empresa or mundo.company_a,
        cuerpo,
        version=version if version is not None else cuenta["version"],
    )


def terminar(mundo, cuenta, autorizado_id, acto_id, usuario="ua", motivo="Cambio de autorizado por rotación.", hasta=None):
    return _post(
        mundo,
        f"{T}/cuentas/{cuenta['id']}/autorizados/{autorizado_id}/fin",
        usuario,
        mundo.company_a,
        {"acto_id": acto_id, "vigente_hasta": (hasta or HOY).isoformat(), "motivo": motivo},
        version=cuenta["version"],
    )


MOTIVO = "Motivo suficiente de la prueba."


def test_st01_activar(mundo, gobierno, siembra):
    """st01"""
    cuenta = cuenta_lista(mundo, siembra["cargo_vigente"])
    r = activar(mundo, cuenta)
    assert r["estado"] == "VIGENTE"
    assert r["en_vigor"] is True
    assert r["activada_por"] == "ua"
    assert r["activada_en"] is not None
    assert any(h["tipo"] == "ACTIVADA" for h in r["historia"])
    assert len(eventos(mundo, "GOV_BANK_ACCOUNT_ACTIVATED", r["id"])) == 1


def test_st02_activar_sin_preparar(mundo, gobierno, siembra):
    """st02"""
    banco = crear_banco(mundo)
    cuenta = crear_cuenta(mundo, banco=banco)
    r = accion(mundo, cuenta, "activar", {})
    assert r.status_code == 409
    cuerpo = r.json()
    assert cuerpo["code"] == "GOV_BANK_ACCOUNT_NOT_READY"
    assert "acto" in cuerpo["details"]["faltan"]
    assert "autorizado" in cuerpo["details"]["faltan"]

    acto_id = nuevo_acto(mundo, mundo.company_a, siembra["cargo_vigente"])
    cuenta = vincular(mundo, cuenta, acto_id)
    r = accion(mundo, cuenta, "activar", {})
    assert r.status_code == 409
    assert r.json()["details"]["faltan"] == ["autorizado"]

    banco = crear_banco(mundo)
    cuenta = crear_cuenta(mundo, banco=banco)
    cuenta = autorizar(mundo, cuenta, siembra["cargo_vigente"], acto_id)
    r = accion(mundo, cuenta, "activar", {})
    assert r.status_code == 409
    assert r.json()["details"]["faltan"] == ["acto"]

    desde = HOY - timedelta(days=5)
    hasta = HOY - timedelta(days=1)
    banco = crear_banco(mundo)
    cuenta = crear_cuenta(
        mundo,
        banco=banco,
        vigente_desde=desde.isoformat(),
        vigente_hasta=hasta.isoformat(),
    )
    acto_id = nuevo_acto(mundo, mundo.company_a, siembra["cargo_vigente"])
    cuenta = vincular(mundo, cuenta, acto_id)
    r = _post(
        mundo,
        f"{T}/cuentas/{cuenta['id']}/autorizados",
        "ua",
        mundo.company_a,
        {
            "cargo_id": siembra["cargo_vigente"],
            "acto_id": acto_id,
            "vigente_desde": desde.isoformat(),
        },
        version=cuenta["version"],
    )
    assert r.status_code == 201
    cuenta = r.json()
    r = accion(mundo, cuenta, "activar", {})
    assert r.status_code == 409
    assert "vigencia" in r.json()["details"]["faltan"]


def test_st03_activar_acto_revocado(mundo, gobierno, siembra):
    """st03"""
    cuenta = cuenta_lista(mundo, siembra["cargo_vigente"])
    dejar_sin_efecto(mundo, cuenta["acto"]["id"], mundo.company_a, siembra["cargo_vigente"], "REVOCADO")
    r = accion(mundo, cuenta, "activar", {})
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_BANK_ACCOUNT_ACT_WITHOUT_EFFECT"
    detalle = mundo.get(
        f"{T}/cuentas/{cuenta['id']}",
        "ua",
        mundo.company_a,
    ).json()
    assert detalle["estado"] == "BORRADOR"


def test_st04_acto_sin_efecto(mundo, gobierno, siembra):
    """st04"""
    cuenta = cuenta_vigente(mundo, siembra["cargo_vigente"])
    version = cuenta["version"]
    dejar_sin_efecto(mundo, cuenta["acto"]["id"], mundo.company_a, siembra["cargo_vigente"], "REVOCADO")
    detalle = mundo.get(
        f"{T}/cuentas/{cuenta['id']}",
        "ua",
        mundo.company_a,
    ).json()
    assert detalle["acto_sin_efecto"] is True
    assert detalle["estado"] == "VIGENTE"
    assert [a["id"] for a in detalle["autorizados"]] == [a["id"] for a in cuenta["autorizados"]]
    assert detalle["autorizados_en_vigor"] == cuenta["autorizados_en_vigor"]
    assert detalle["version"] == version
    listado = mundo.get(
        f"{T}/cuentas?estado=VIGENTE",
        "ua",
        mundo.company_a,
    ).json()
    assert any(
        item["id"] == cuenta["id"] and item["acto_sin_efecto"] is True
        for item in listado["items"]
    )

    otro_acto = nuevo_acto(mundo, mundo.company_a, siembra["cargo_vigente"])
    r = _post(
        mundo,
        f"{T}/cuentas/{cuenta['id']}/autorizados",
        "ua",
        mundo.company_a,
        {
            "cargo_id": segundo_cargo(mundo, siembra["cargo_vigente"]),
            "acto_id": otro_acto,
            "vigente_desde": HOY.isoformat(),
        },
        version=detalle["version"],
    )
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_BANK_ACCOUNT_ACT_WITHOUT_EFFECT"

    autorizado = cuenta["autorizados"][0]
    r = terminar(mundo, detalle, autorizado["id"], otro_acto)
    assert r.status_code == 200
    detalle = r.json()

    r = accion(mundo, detalle, "inactivar", {"motivo": MOTIVO})
    assert r.status_code == 200
    detalle = r.json()
    r = accion(mundo, detalle, "reactivar", {"motivo": MOTIVO})
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_BANK_ACCOUNT_ACT_WITHOUT_EFFECT"

    # NULO en otra cuenta
    cuenta2 = cuenta_vigente(mundo, siembra["cargo_vigente"])
    dejar_sin_efecto(mundo, cuenta2["acto"]["id"], mundo.company_a, siembra["cargo_vigente"], "NULO")
    detalle2 = mundo.get(
        f"{T}/cuentas/{cuenta2['id']}",
        "ua",
        mundo.company_a,
    ).json()
    assert detalle2["acto_sin_efecto"] is True

    # Vincular un acto vigente lo resuelve
    acto_vigente = nuevo_acto(mundo, mundo.company_a, siembra["cargo_vigente"])
    detalle = vincular(mundo, detalle, acto_vigente)
    assert detalle["acto_sin_efecto"] is False
    r = _post(
        mundo,
        f"{T}/cuentas/{detalle['id']}/autorizados",
        "ua",
        mundo.company_a,
        {
            "cargo_id": segundo_cargo(mundo, siembra["cargo_vigente"]),
            "acto_id": acto_vigente,
            "vigente_desde": HOY.isoformat(),
        },
        version=detalle["version"],
    )
    assert r.status_code == 201
    detalle = r.json()
    r = accion(mundo, detalle, "reactivar", {"motivo": MOTIVO})
    assert r.status_code == 200


def test_st05_inactivar_reactivar(mundo, gobierno, siembra):
    """st05"""
    cuenta = cuenta_vigente(mundo, siembra["cargo_vigente"])
    r = accion(mundo, cuenta, "inactivar", {"motivo": MOTIVO})
    assert r.status_code == 200
    cuenta = r.json()
    assert cuenta["estado"] == "INACTIVA"
    assert cuenta["en_vigor"] is False
    assert any(
        h["tipo"] == "INACTIVADA" and h["detalle"]["motivo"] == MOTIVO
        for h in cuenta["historia"]
    )
    r = accion(mundo, cuenta, "reactivar", {"motivo": MOTIVO})
    assert r.status_code == 200
    cuenta = r.json()
    assert cuenta["estado"] == "VIGENTE"
    assert any(h["tipo"] == "REACTIVADA" for h in cuenta["historia"])

    r = accion(mundo, cuenta, "inactivar", {"motivo": "corto"})
    assert r.status_code == 422
    assert r.json()["code"] == "VALIDATION_ERROR"

    borrador = cuenta_lista(mundo, siembra["cargo_vigente"])
    r = accion(mundo, borrador, "inactivar", {"motivo": MOTIVO})
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_BANK_ACCOUNT_INVALID_STATE"

    vigente = cuenta_vigente(mundo, siembra["cargo_vigente"])
    r = accion(mundo, vigente, "reactivar", {"motivo": MOTIVO})
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_BANK_ACCOUNT_INVALID_STATE"

    # Reactivar con 0 autorizados en vigor
    vigente2 = cuenta_vigente(mundo, siembra["cargo_vigente"])
    autorizado = vigente2["autorizados"][0]
    acto_fin = nuevo_acto(mundo, mundo.company_a, siembra["cargo_vigente"])
    r = terminar(mundo, vigente2, autorizado["id"], acto_fin)
    assert r.status_code == 200
    vigente2 = r.json()
    r = accion(mundo, vigente2, "inactivar", {"motivo": MOTIVO})
    assert r.status_code == 200
    vigente2 = r.json()
    r = accion(mundo, vigente2, "reactivar", {"motivo": MOTIVO})
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_BANK_ACCOUNT_NOT_READY"


def test_st06_cerrar(mundo, gobierno, siembra):
    """st06"""
    cuenta = cuenta_vigente(mundo, siembra["cargo_vigente"])
    fecha_cierre = HOY.isoformat()
    r = accion(mundo, cuenta, "cerrar", {"motivo": MOTIVO, "fecha_cierre": fecha_cierre})
    assert r.status_code == 200
    cuenta = r.json()
    assert cuenta["estado"] == "CERRADA"
    assert cuenta["fecha_cierre"] == fecha_cierre
    assert cuenta["motivo_cierre"] == MOTIVO
    assert cuenta["cerrada_por"] == "ua"
    assert cuenta["vigente_hasta"] == fecha_cierre
    assert cuenta["autorizados_en_vigor"] == 0
    autorizado = cuenta["autorizados"][0]
    assert autorizado["motivo_fin"] == "Cierre de la cuenta"
    assert autorizado["acto_fin"] is None
    assert any(h["tipo"] == "CERRADA" for h in cuenta["historia"])
    assert any(h["tipo"] == "AUTORIZADO_FIN" for h in cuenta["historia"])
    assert len(eventos(mundo, "GOV_BANK_ACCOUNT_CLOSED", cuenta["id"])) == 1
    assert len(eventos(mundo, "GOV_BANK_AUTHORIZATION_ENDED", cuenta["id"])) == 1

    cuenta2 = cuenta_vigente(mundo, siembra["cargo_vigente"])
    r = accion(
        mundo,
        cuenta2,
        "cerrar",
        {
            "motivo": MOTIVO,
            "fecha_cierre": (HOY + timedelta(days=1)).isoformat(),
        },
    )
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_BANK_ACCOUNT_INVALID"

    r = accion(
        mundo,
        cuenta2,
        "cerrar",
        {
            "motivo": MOTIVO,
            "fecha_cierre": (date.fromisoformat(cuenta2["vigente_desde"]) - timedelta(days=1)).isoformat(),
        },
    )
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_BANK_ACCOUNT_INVALID"


def test_st07_cerrada_no_admite_nada(mundo, gobierno, siembra):
    """st07"""
    cuenta = cuenta_vigente(mundo, siembra["cargo_vigente"])
    r = accion(mundo, cuenta, "cerrar", {"motivo": MOTIVO, "fecha_cierre": HOY.isoformat()})
    assert r.status_code == 200
    cuenta = r.json()
    assert cuenta["estado"] == "CERRADA"

    r = patch(
        mundo,
        f"{T}/cuentas/{cuenta['id']}",
        "ua",
        mundo.company_a,
        {"denominacion": "Nueva"},
        version=cuenta["version"],
    )
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_BANK_ACCOUNT_INVALID_STATE"

    acto_id = nuevo_acto(mundo, mundo.company_a, siembra["cargo_vigente"])
    r = _post(
        mundo,
        f"{T}/cuentas/{cuenta['id']}/acto",
        "ua",
        mundo.company_a,
        {"acto_id": acto_id},
        version=cuenta["version"],
    )
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_BANK_ACCOUNT_INVALID_STATE"

    r = _post(
        mundo,
        f"{T}/cuentas/{cuenta['id']}/autorizados",
        "ua",
        mundo.company_a,
        {
            "cargo_id": siembra["cargo_vigente"],
            "acto_id": acto_id,
            "vigente_desde": HOY.isoformat(),
        },
        version=cuenta["version"],
    )
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_BANK_ACCOUNT_INVALID_STATE"

    r = terminar(mundo, cuenta, cuenta["autorizados"][0]["id"], acto_id)
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_BANK_ACCOUNT_INVALID_STATE"

    for verbo, cuerpo in [
        ("activar", {}),
        ("inactivar", {"motivo": MOTIVO}),
        ("reactivar", {"motivo": MOTIVO}),
        ("cerrar", {"motivo": MOTIVO, "fecha_cierre": HOY.isoformat()}),
    ]:
        r = accion(mundo, cuenta, verbo, cuerpo)
        assert r.status_code == 409
        assert r.json()["code"] == "GOV_BANK_ACCOUNT_INVALID_STATE"

    r = mundo.get(f"{T}/cuentas/{cuenta['id']}", "ua", mundo.company_a)
    assert r.status_code == 200


def test_st08_cerrar_borrador_no(mundo, gobierno):
    """st08"""
    banco = crear_banco(mundo)
    cuenta = crear_cuenta(mundo, banco=banco)
    r = accion(
        mundo,
        cuenta,
        "cerrar",
        {"motivo": MOTIVO, "fecha_cierre": HOY.isoformat()},
    )
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_BANK_ACCOUNT_INVALID_STATE"


def test_st09_version_vieja(mundo, gobierno, siembra):
    """st09"""
    cuenta = cuenta_vigente(mundo, siembra["cargo_vigente"])
    version = cuenta["version"]
    r = accion(mundo, cuenta, "inactivar", {"motivo": MOTIVO})
    assert r.status_code == 200
    cuenta = r.json()

    r = accion(mundo, cuenta, "reactivar", {"motivo": MOTIVO}, version=version)
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_BANK_ACCOUNT_STALE"
    assert "version_actual" in r.json()["details"]

    r = accion(mundo, cuenta, "activar", {}, version=version)
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_BANK_ACCOUNT_STALE"

    cuenta2 = cuenta_vigente(mundo, siembra["cargo_vigente"])
    version2 = cuenta2["version"]
    acto_id = nuevo_acto(mundo, mundo.company_a, siembra["cargo_vigente"])
    r = _post(
        mundo,
        f"{T}/cuentas/{cuenta2['id']}/autorizados",
        "ua",
        mundo.company_a,
        {
            "cargo_id": segundo_cargo(mundo, siembra["cargo_vigente"]),
            "acto_id": acto_id,
            "vigente_desde": HOY.isoformat(),
        },
        version=cuenta2["version"],
    )
    assert r.status_code == 201
    r = _post(
        mundo,
        f"{T}/cuentas/{cuenta2['id']}/autorizados",
        "ua",
        mundo.company_a,
        {
            "cargo_id": segundo_cargo(mundo, siembra["cargo_vigente"]),
            "acto_id": acto_id,
            "vigente_desde": HOY.isoformat(),
        },
        version=version2,
    )
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_BANK_ACCOUNT_STALE"


def test_ix01_auditoria_institucional(mundo, gobierno, siembra):
    """ix01"""
    cuenta_lista(mundo, siembra["cargo_vigente"])
    r = mundo.get("/gobierno/auditoria/filtros", "ua", mundo.company_a)
    assert r.status_code == 200
    filtros = r.json()
    assert any(
        proceso["codigo"] == "TRE-01"
        for proceso in filtros["procesos"]
    )
    r = mundo.get(
        "/gobierno/auditoria/eventos?proceso=TRE-01&por_pagina=200",
        "ua",
        mundo.company_a,
    )
    assert r.status_code == 200
    items = r.json()["items"]
    item = next(
        i for i in items if i["accion"] == "GOV_BANK_ACCOUNT_CREATED"
    )
    r = mundo.get(f"/gobierno/auditoria/eventos/{item['id']}", "ua", mundo.company_a)
    assert r.status_code == 200
    detalle = r.json()
    assert detalle["objeto"]["ruta"].startswith("/gobierno/tesoreria/cuentas/")


def test_ix02_catalogo_sod(mundo, gobierno):
    """ix02"""
    r = mundo.get("/gobierno/sod/acciones", "ua", mundo.company_a)
    assert r.status_code == 200
    proceso = next(a for a in r.json()["procesos"] if a["proceso"] == "TRE-01")
    assert len(proceso["acciones"]) == 6
    tre01_registrar = next(
        a for a in proceso["acciones"] if a["codigo"] == "TRE01_REGISTRAR"
    )
    assert tre01_registrar["crea_objeto"] is True


def regla_tre01_vigente(mundo, accion_b: str, nombre: str) -> dict:
    r = _post(
        mundo,
        "/gobierno/sod/reglas",
        "ua",
        mundo.company_a,
        {
            "proceso": "TRE-01",
            "accion_a": "TRE01_REGISTRAR",
            "accion_b": accion_b,
            "nombre": nombre,
            "descripcion": "Descripción suficiente para la regla.",
            "vigente_desde": HOY.isoformat(),
        },
    )
    assert r.status_code == 201, r.text
    regla = r.json()
    r = _post(mundo, f"/gobierno/sod/reglas/{regla['id']}/activar", "ua", mundo.company_a, {}, version=regla["version"])
    assert r.status_code == 200, r.text
    return r.json()


def test_ix03_guarda_sod_bloquea(mundo, gobierno, siembra):
    """ix03"""
    regla = regla_tre01_vigente(mundo, "TRE01_ACTIVAR", "Quien registra no activa")
    try:
        cuenta = cuenta_lista(mundo, siembra["cargo_vigente"])
        r = accion(mundo, cuenta, "activar", {})
        assert r.status_code == 409
        assert r.json()["code"] == "GOV_SOD_CONFLICT"
        detalle = mundo.get(
            f"{T}/cuentas/{cuenta['id']}",
            "ua",
            mundo.company_a,
        ).json()
        assert detalle["estado"] == "BORRADOR"
        assert detalle["version"] == cuenta["version"]

        _crear_usuario_con_permisos(
            mundo,
            "tre_otro",
            [
                ("gobierno_cuentas", "view"),
                ("gobierno_cuentas", "manage"),
                ("gobierno_cuentas", "activate"),
            ],
            mundo.company_a,
        )
        r = accion(mundo, detalle, "activar", {}, usuario="tre_otro")
        assert r.status_code == 200
    finally:
        r = _post(
            mundo,
            f"/gobierno/sod/reglas/{regla['id']}/cerrar",
            "ua",
            mundo.company_a,
            {"motivo": MOTIVO},
            version=regla["version"],
        )
        assert r.status_code == 200


def test_ix04_guarda_sod_en_autorizar(mundo, gobierno, siembra):
    """ix04"""
    regla = regla_tre01_vigente(mundo, "TRE01_AUTORIZAR", "Quien registra no autoriza")
    try:
        banco = crear_banco(mundo)
        cuenta = crear_cuenta(mundo, banco=banco)
        acto_id = nuevo_acto(mundo, mundo.company_a, siembra["cargo_vigente"])
        cuenta = vincular(mundo, cuenta, acto_id)
        r = _post(
            mundo,
            f"{T}/cuentas/{cuenta['id']}/autorizados",
            "ua",
            mundo.company_a,
            {
                "cargo_id": siembra["cargo_vigente"],
                "acto_id": acto_id,
                "vigente_desde": HOY.isoformat(),
            },
            version=cuenta["version"],
        )
        assert r.status_code == 409
        assert r.json()["code"] == "GOV_SOD_CONFLICT"
        detalle = mundo.get(
            f"{T}/cuentas/{cuenta['id']}",
            "ua",
            mundo.company_a,
        ).json()
        assert len(detalle["autorizados"]) == 0
    finally:
        r = _post(
            mundo,
            f"/gobierno/sod/reglas/{regla['id']}/cerrar",
            "ua",
            mundo.company_a,
            {"motivo": MOTIVO},
            version=regla["version"],
        )
        assert r.status_code == 200
