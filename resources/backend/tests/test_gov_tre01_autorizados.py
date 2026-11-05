from datetime import timedelta
from uuid import uuid4

from app.modules.government.models import GovernmentPosition
from tests.test_gov_ctl06_hallazgos import _post
from tests.test_gov_tre01_cuentas import (
    HOY,
    T,
    crear_banco,
    crear_cuenta,
    cuenta_vigente,
    dejar_sin_efecto,
    eventos,
    nuevo_acto,
    segundo_cargo,
)

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos")

MOTIVO = "Motivo suficiente de la prueba."


def accion(mundo, cuenta, verbo, cuerpo, usuario="ua", empresa=None):
    return _post(
        mundo,
        f"{T}/cuentas/{cuenta['id']}/{verbo}",
        usuario,
        empresa or mundo.company_a,
        cuerpo,
        version=cuenta["version"],
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


def test_ac01_vincular_acto(mundo, gobierno, siembra):
    """ac01"""
    banco = crear_banco(mundo)
    cuenta = crear_cuenta(mundo, banco)
    acto_id = nuevo_acto(mundo, mundo.company_a, siembra["cargo_vigente"])
    r = _post(
        mundo,
        f"{T}/cuentas/{cuenta['id']}/acto",
        "ua",
        mundo.company_a,
        {"acto_id": acto_id},
        version=cuenta["version"],
    )
    assert r.status_code == 200
    detalle = r.json()
    assert detalle["acto"]["id"] == acto_id
    assert "tipo" in detalle["acto"]
    assert "numero" in detalle["acto"]
    assert "fecha" in detalle["acto"]
    assert detalle["acto"]["estado"] == "EMITIDO"
    assert "asunto" in detalle["acto"]
    assert detalle["historia"][-1]["tipo"] == "ACTO_VINCULADO"
    evs = eventos(mundo, "GOV_BANK_ACCOUNT_ACT_LINKED", cuenta["id"])
    assert len(evs) == 1
    # EFICAZ
    cuenta2 = crear_cuenta(mundo, banco)
    acto2_id = nuevo_acto(mundo, mundo.company_a, siembra["cargo_vigente"], status="EFICAZ")
    r2 = _post(
        mundo,
        f"{T}/cuentas/{cuenta2['id']}/acto",
        "ua",
        mundo.company_a,
        {"acto_id": acto2_id},
        version=cuenta2["version"],
    )
    assert r2.status_code == 200
    # Sin If-Match 428
    cuenta3 = crear_cuenta(mundo, banco)
    acto3_id = nuevo_acto(mundo, mundo.company_a, siembra["cargo_vigente"])
    r3 = _post(
        mundo,
        f"{T}/cuentas/{cuenta3['id']}/acto",
        "ua",
        mundo.company_a,
        {"acto_id": acto3_id},
    )
    assert r3.status_code == 428
    assert r3.json()["code"] == "GOV_BANK_ACCOUNT_IF_MATCH_REQUIRED"


def test_ac02_acto_invalido(mundo, gobierno, siembra):
    """ac02"""
    banco = crear_banco(mundo)
    cuenta = crear_cuenta(mundo, banco)
    acto_borrador = nuevo_acto(mundo, mundo.company_a, siembra["cargo_vigente"], status="BORRADOR")
    acto_futuro = nuevo_acto(mundo, mundo.company_a, siembra["cargo_vigente"], fecha=HOY + timedelta(days=1))
    acto_otra = nuevo_acto(mundo, mundo.company_b, siembra["cargo_otra"])
    acto_revocado = nuevo_acto(mundo, mundo.company_a, siembra["cargo_vigente"])
    dejar_sin_efecto(mundo, acto_revocado, mundo.company_a, siembra["cargo_vigente"], status="REVOCADO")
    acto_nulo = nuevo_acto(mundo, mundo.company_a, siembra["cargo_vigente"])
    dejar_sin_efecto(mundo, acto_nulo, mundo.company_a, siembra["cargo_vigente"], status="NULO")
    acto_inexistente = str(uuid4())
    actos = [acto_borrador, acto_futuro, acto_otra, acto_revocado, acto_nulo, acto_inexistente]
    mensajes = set()
    for acto_id in actos:
        r = accion(mundo, cuenta, "acto", {"acto_id": acto_id})
        assert r.status_code == 422
        assert r.json()["code"] == "GOV_BANK_ACCOUNT_INVALID"
        mensajes.add(r.json()["message"])
    assert len(mensajes) == 1


def test_ac03_acto_cross_ente_no_se_filtra(mundo, gobierno, siembra):
    """ac03"""
    banco = crear_banco(mundo)
    cuenta = crear_cuenta(mundo, banco)
    acto_otra = nuevo_acto(mundo, mundo.company_b, siembra["cargo_otra"])
    r = accion(mundo, cuenta, "acto", {"acto_id": acto_otra})
    assert r.status_code == 422
    r_get = mundo.get(f"{T}/cuentas/{cuenta['id']}", "ua", mundo.company_a)
    detalle = r_get.json()
    assert detalle["acto"] is None
    assert detalle["version"] == cuenta["version"]


def test_au01_alta(mundo, gobierno, siembra):
    """au01"""
    banco = crear_banco(mundo)
    cuenta = crear_cuenta(mundo, banco)
    acto_id = nuevo_acto(mundo, mundo.company_a, siembra["cargo_vigente"])
    r = accion(mundo, cuenta, "autorizados", {"cargo_id": siembra["cargo_vigente"], "acto_id": acto_id, "vigente_desde": HOY.isoformat()})
    assert r.status_code == 201
    detalle = r.json()
    assert detalle["autorizados_en_vigor"] == 1
    autorizado = detalle["autorizados"][0]
    assert autorizado["cargo_id"] == siembra["cargo_vigente"]
    assert autorizado["cargo_codigo"] == "C-VIG"
    assert autorizado["cargo_denominacion"] == "Cargo Vigente"
    assert autorizado["cargo_unidad"] == "Unidad CTL-06 A"
    assert autorizado["cargo_vigente"] is True
    assert autorizado["en_vigor"] is True
    assert autorizado["vigente_hasta"] is None
    assert autorizado["acto_fin"] is None
    assert autorizado["acto_alta"]["id"] == acto_id
    assert autorizado["registrada_por"] == "ua"
    assert detalle["historia"][-1]["tipo"] == "AUTORIZADO_ALTA"
    evs = eventos(mundo, "GOV_BANK_AUTHORIZATION_ADDED", detalle["id"])
    assert len(evs) == 1
    assert evs[0].after["cargo_codigo"] == "C-VIG"


def test_au02_cargo_invalido(mundo, gobierno, siembra):
    """au02"""
    banco = crear_banco(mundo)
    cuenta = crear_cuenta(mundo, banco)
    acto_id = nuevo_acto(mundo, mundo.company_a, siembra["cargo_vigente"])
    cargos = [siembra["cargo_borrador"], siembra["cargo_anterior"], siembra["cargo_otra"], str(uuid4()), "Pedro Pérez"]
    mensajes = set()
    for cargo in cargos:
        r = accion(mundo, cuenta, "autorizados", {"cargo_id": cargo, "acto_id": acto_id, "vigente_desde": HOY.isoformat()})
        assert r.status_code == 422
        assert r.json()["code"] == "GOV_BANK_ACCOUNT_INVALID"
        mensajes.add(r.json()["message"])
        assert "Pedro" not in r.text
    assert len(mensajes) == 1


def test_au03_acto_de_alta_obligatorio_y_valido(mundo, gobierno, siembra):
    """au03"""
    banco = crear_banco(mundo)
    cuenta = crear_cuenta(mundo, banco)
    r_sin = accion(mundo, cuenta, "autorizados", {"cargo_id": siembra["cargo_vigente"], "vigente_desde": HOY.isoformat()})
    assert r_sin.status_code == 422
    assert r_sin.json()["code"] == "VALIDATION_ERROR"
    acto_borrador = nuevo_acto(mundo, mundo.company_a, siembra["cargo_vigente"], status="BORRADOR")
    r_borrador = accion(mundo, cuenta, "autorizados", {"cargo_id": siembra["cargo_vigente"], "acto_id": acto_borrador, "vigente_desde": HOY.isoformat()})
    assert r_borrador.status_code == 422
    assert r_borrador.json()["code"] == "GOV_BANK_ACCOUNT_INVALID"
    acto_otra = nuevo_acto(mundo, mundo.company_b, siembra["cargo_otra"])
    r_otra = accion(mundo, cuenta, "autorizados", {"cargo_id": siembra["cargo_vigente"], "acto_id": acto_otra, "vigente_desde": HOY.isoformat()})
    assert r_otra.status_code == 422
    assert r_otra.json()["code"] == "GOV_BANK_ACCOUNT_INVALID"


def test_au04_no_hay_campos_libres_de_persona(mundo, gobierno, siembra):
    """au04"""
    banco = crear_banco(mundo)
    cuenta = crear_cuenta(mundo, banco)
    acto_id = nuevo_acto(mundo, mundo.company_a, siembra["cargo_vigente"])
    base = {"cargo_id": siembra["cargo_vigente"], "acto_id": acto_id, "vigente_desde": HOY.isoformat()}
    for extra in [{"nombre": "Pedro"}, {"usuario_id": "x"}]:
        r = accion(mundo, cuenta, "autorizados", {**base, **extra})
        assert r.status_code == 422
        assert r.json()["code"] == "VALIDATION_ERROR"


def test_au05_duplicado_en_vigor(mundo, gobierno, siembra):
    """au05"""
    banco = crear_banco(mundo)
    cuenta = crear_cuenta(mundo, banco)
    acto_id = nuevo_acto(mundo, mundo.company_a, siembra["cargo_vigente"])
    r1 = accion(mundo, cuenta, "autorizados", {"cargo_id": siembra["cargo_vigente"], "acto_id": acto_id, "vigente_desde": HOY.isoformat()})
    assert r1.status_code == 201
    r2 = accion(mundo, r1.json(), "autorizados", {"cargo_id": siembra["cargo_vigente"], "acto_id": acto_id, "vigente_desde": HOY.isoformat()})
    assert r2.status_code == 409
    assert r2.json()["code"] == "GOV_BANK_AUTHORIZATION_DUPLICATE"
    autorizado_id = r1.json()["autorizados"][0]["id"]
    acto_fin = nuevo_acto(mundo, mundo.company_a, siembra["cargo_vigente"])
    r_fin = terminar(mundo, r1.json(), autorizado_id, acto_fin)
    assert r_fin.status_code == 200
    detalle = r_fin.json()
    assert detalle["autorizados_en_vigor"] == 0
    acto_nuevo = nuevo_acto(mundo, mundo.company_a, siembra["cargo_vigente"])
    r3 = accion(mundo, detalle, "autorizados", {"cargo_id": siembra["cargo_vigente"], "acto_id": acto_nuevo, "vigente_desde": HOY.isoformat()})
    assert r3.status_code == 201
    detalle_final = r3.json()
    autorizados = detalle_final["autorizados"]
    assert len(autorizados) == 2
    assert sum(1 for a in autorizados if a["en_vigor"]) == 1
    assert sum(1 for a in autorizados if not a["en_vigor"]) == 1


def test_au06_fechas(mundo, gobierno, siembra):
    """au06"""
    banco = crear_banco(mundo)
    acto_id = nuevo_acto(mundo, mundo.company_a, siembra["cargo_vigente"])
    cuenta_base = crear_cuenta(mundo, banco)
    manana = HOY + timedelta(days=1)
    r1 = accion(mundo, cuenta_base, "autorizados", {"cargo_id": siembra["cargo_vigente"], "acto_id": acto_id, "vigente_desde": manana.isoformat()})
    assert r1.status_code == 422
    assert r1.json()["code"] == "GOV_BANK_ACCOUNT_INVALID"
    # alta antes del inicio de la cuenta
    cuenta_pasada = crear_cuenta(mundo, banco, vigente_desde=(HOY - timedelta(days=5)).isoformat())
    r2 = accion(mundo, cuenta_pasada, "autorizados", {"cargo_id": siembra["cargo_vigente"], "acto_id": acto_id, "vigente_desde": (HOY - timedelta(days=6)).isoformat()})
    assert r2.status_code == 422
    assert r2.json()["code"] == "GOV_BANK_ACCOUNT_INVALID"
    # alta después del fin de la cuenta
    cuenta_finalizada = crear_cuenta(
        mundo,
        banco,
        vigente_desde=(HOY - timedelta(days=5)).isoformat(),
        vigente_hasta=(HOY - timedelta(days=2)).isoformat(),
    )
    r3 = accion(mundo, cuenta_finalizada, "autorizados", {"cargo_id": siembra["cargo_vigente"], "acto_id": acto_id, "vigente_desde": HOY.isoformat()})
    assert r3.status_code == 422
    assert r3.json()["code"] == "GOV_BANK_ACCOUNT_INVALID"
    # fin con fecha futura
    cuenta_ok = crear_cuenta(mundo, banco)
    r_autorizado = accion(mundo, cuenta_ok, "autorizados", {"cargo_id": siembra["cargo_vigente"], "acto_id": acto_id, "vigente_desde": HOY.isoformat()})
    detalle = r_autorizado.json()
    autorizado_id = detalle["autorizados"][0]["id"]
    r_fin_futuro = terminar(mundo, detalle, autorizado_id, acto_id, hasta=HOY + timedelta(days=1))
    assert r_fin_futuro.status_code == 422
    assert r_fin_futuro.json()["code"] == "GOV_BANK_ACCOUNT_INVALID"
    # fin antes del alta
    cuenta_fin = crear_cuenta(mundo, banco)
    acto_alta = nuevo_acto(mundo, mundo.company_a, siembra["cargo_vigente"])
    r_alta = accion(mundo, cuenta_fin, "autorizados", {"cargo_id": siembra["cargo_vigente"], "acto_id": acto_alta, "vigente_desde": HOY.isoformat()})
    detalle_fin = r_alta.json()
    autorizado_fin_id = detalle_fin["autorizados"][0]["id"]
    acto_fin_id = nuevo_acto(mundo, mundo.company_a, siembra["cargo_vigente"])
    r_fin_antes = terminar(mundo, detalle_fin, autorizado_fin_id, acto_fin_id, hasta=HOY - timedelta(days=1))
    assert r_fin_antes.status_code == 422
    assert r_fin_antes.json()["code"] == "GOV_BANK_ACCOUNT_INVALID"


def test_au07_cambio_conserva_historia(mundo, gobierno, siembra):
    """au07"""
    cuenta = cuenta_vigente(mundo, siembra["cargo_vigente"])
    cargo2 = segundo_cargo(mundo, siembra["cargo_vigente"])
    acto_alta2 = nuevo_acto(mundo, mundo.company_a, siembra["cargo_vigente"])
    r_alta2 = accion(mundo, cuenta, "autorizados", {"cargo_id": cargo2, "acto_id": acto_alta2, "vigente_desde": HOY.isoformat()})
    assert r_alta2.status_code == 201
    detalle = r_alta2.json()
    autorizado_original = next(a for a in detalle["autorizados"] if a["cargo_id"] == siembra["cargo_vigente"])
    acto_fin = nuevo_acto(mundo, mundo.company_a, siembra["cargo_vigente"])
    r_fin = terminar(mundo, detalle, autorizado_original["id"], acto_fin)
    assert r_fin.status_code == 200
    detalle_fin = r_fin.json()
    autorizados = detalle_fin["autorizados"]
    assert len(autorizados) == 2
    assert autorizados[0]["en_vigor"] is True
    assert autorizados[1]["cargo_id"] == siembra["cargo_vigente"]
    assert autorizados[1]["vigente_hasta"] == HOY.isoformat()
    assert autorizados[1]["acto_fin"]["id"] == acto_fin
    assert autorizados[1]["motivo_fin"] == "Cambio de autorizado por rotación."
    assert autorizados[1]["terminada_por"] == "ua"
    assert autorizados[1]["en_vigor"] is False
    assert detalle_fin["autorizados_en_vigor"] == 1
    historia = detalle_fin["historia"]
    tipos = [h["tipo"] for h in historia]
    assert tipos.count("AUTORIZADO_ALTA") == 2
    assert tipos.count("AUTORIZADO_FIN") == 1
    evs = eventos(mundo, "GOV_BANK_AUTHORIZATION_ENDED", detalle_fin["id"])
    assert len(evs) == 1


def test_au08_fin_invalido(mundo, gobierno, siembra):
    """au08"""
    cuenta = cuenta_vigente(mundo, siembra["cargo_vigente"])
    autorizado_id = cuenta["autorizados"][0]["id"]
    acto_id = nuevo_acto(mundo, mundo.company_a, siembra["cargo_vigente"])
    # motivo corto
    r_motivo = terminar(mundo, cuenta, autorizado_id, acto_id, motivo="corto")
    assert r_motivo.status_code == 422
    assert r_motivo.json()["code"] == "VALIDATION_ERROR"
    # sin acto
    r_sin_acto = _post(
        mundo,
        f"{T}/cuentas/{cuenta['id']}/autorizados/{autorizado_id}/fin",
        "ua",
        mundo.company_a,
        {"vigente_hasta": HOY.isoformat(), "motivo": MOTIVO},
        version=cuenta["version"],
    )
    assert r_sin_acto.status_code == 422
    assert r_sin_acto.json()["code"] == "VALIDATION_ERROR"
    # acto borrador
    acto_borrador = nuevo_acto(mundo, mundo.company_a, siembra["cargo_vigente"], status="BORRADOR")
    r_borrador = terminar(mundo, cuenta, autorizado_id, acto_borrador)
    assert r_borrador.status_code == 422
    assert r_borrador.json()["code"] == "GOV_BANK_ACCOUNT_INVALID"
    # autorización inexistente
    r_inexistente = terminar(mundo, cuenta, str(uuid4()), acto_id)
    assert r_inexistente.status_code == 404
    assert r_inexistente.json()["code"] == "GOV_BANK_AUTHORIZATION_NOT_FOUND"
    # autorización de otra cuenta
    otra_cuenta = cuenta_vigente(mundo, siembra["cargo_vigente"])
    r_otra = terminar(mundo, otra_cuenta, autorizado_id, acto_id)
    assert r_otra.status_code == 404
    assert r_otra.json()["code"] == "GOV_BANK_AUTHORIZATION_NOT_FOUND"
    # terminar dos veces
    acto_fin = nuevo_acto(mundo, mundo.company_a, siembra["cargo_vigente"])
    r_fin = terminar(mundo, cuenta, autorizado_id, acto_fin)
    assert r_fin.status_code == 200
    detalle = r_fin.json()
    r_doble = terminar(mundo, detalle, autorizado_id, acto_fin)
    assert r_doble.status_code == 409
    assert r_doble.json()["code"] == "GOV_BANK_ACCOUNT_INVALID_STATE"


def test_au09_cargo_inactivo_no_toca_la_autorizacion(mundo, gobierno, siembra):
    """au09"""
    cuenta = cuenta_vigente(mundo, siembra["cargo_vigente"])
    cargo2 = segundo_cargo(mundo, siembra["cargo_vigente"])
    acto_alta2 = nuevo_acto(mundo, mundo.company_a, siembra["cargo_vigente"])
    r_alta2 = accion(mundo, cuenta, "autorizados", {"cargo_id": cargo2, "acto_id": acto_alta2, "vigente_desde": HOY.isoformat()})
    assert r_alta2.status_code == 201
    # Desactivar el cargo directamente por modelo en sesión propia
    with mundo.factory() as db:
        cargo = db.get(GovernmentPosition, cargo2)
        cargo.status = "INACTIVO"
        cargo.valid_to = HOY
        db.commit()
    # El detalle muestra cargo_vigente False, en_vigor True
    r_get = mundo.get(f"{T}/cuentas/{r_alta2.json()['id']}", "ua", mundo.company_a)
    detalle = r_get.json()
    autorizado = next(a for a in detalle["autorizados"] if a["cargo_id"] == cargo2)
    assert autorizado["cargo_vigente"] is False
    assert autorizado["en_vigor"] is True


def test_au10_filtro_por_cargo_solo_en_vigor(mundo, gobierno, siembra):
    """au10"""
    cuenta = cuenta_vigente(mundo, siembra["cargo_vigente"])
    autorizado_id = cuenta["autorizados"][0]["id"]
    acto_fin = nuevo_acto(mundo, mundo.company_a, siembra["cargo_vigente"])
    r_fin = terminar(mundo, cuenta, autorizado_id, acto_fin)
    assert r_fin.status_code == 200
    r_lista = mundo.get(f"{T}/cuentas?cargo_id={siembra['cargo_vigente']}", "ua", mundo.company_a)
    lista = r_lista.json()
    assert all(item["id"] != cuenta["id"] for item in lista["items"])
