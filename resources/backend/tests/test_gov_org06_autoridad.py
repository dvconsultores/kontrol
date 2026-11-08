from datetime import timedelta

from sqlalchemy import select

from app.modules.audit.models import AuditEvent
from app.modules.identity_access.models import User
from app.shared.clock import hoy_de_negocio
from tests.org06_ayudantes import (
    D,
    accion,
    activa,
    acto_eficaz,
    consultar,
    crear_funcionario,
    cuenta,
    cuerpo,
    cuerpo_vinculo,
    nuevo_cargo,
    post_vinculo,
    titular_activo,
    vinculo_activo,
)
from tests.org06_guarda import (
    acto_borrador,
    contexto_de,
    cuenta_con_permisos,
    emisor_vinculado,
    emitir,
    exigir_identidad,
)

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos", "tests.org04_ayudantes")


def _desde_hace_dias(dias=10):
    return (hoy_de_negocio() - timedelta(days=dias)).isoformat()


def _hasta_en_dias(dias=5):
    return (hoy_de_negocio() + timedelta(days=dias)).isoformat()


def test_A01_alcance_por_unidad(mundo, gobierno, ocupacion):
    nombre = "org06_A01"
    cargo = nuevo_cargo(mundo, ocupacion, unidad="unidad_hija")
    detalle, _ = titular_activo(mundo, ocupacion, cargo)
    funcionario_id = detalle["funcionario"]["id"]
    user_id = cuenta(mundo, nombre)
    vinculo = vinculo_activo(mundo, cuerpo_vinculo(user_id, funcionario_id))
    contexto = contexto_de(mundo, vinculo)

    ocupaciones = contexto["ocupaciones"]
    assert len(ocupaciones) == 1
    assert ocupaciones[0]["cargo_id"] == cargo
    assert ocupaciones[0]["ejerce"] is True
    assert contexto["unidades"] == [
        {"id": ocupaciones[0]["unidad_id"], "nombre": ocupaciones[0]["unidad"]}
    ]
    assert contexto["tiene_autoridad"] is True
    assert contexto["motivo_sin_autoridad"] is None


def test_A02_alcance_por_ente(mundo, gobierno, ocupacion):
    nombre = "org06_A02"
    user_id = cuenta(mundo, nombre, empresa=mundo.company_a)
    funcionario = crear_funcionario(mundo, usuario="ua")
    vinculo = vinculo_activo(mundo, cuerpo_vinculo(user_id, funcionario["id"]))

    response = consultar(mundo, "/mi-contexto", usuario="ub", empresa=mundo.company_b)
    assert response.status_code == 200
    contexto = response.json()
    assert contexto["vinculo"] is None
    assert contexto["motivo_sin_autoridad"] == "SIN_VINCULO"

    response = consultar(mundo, f"/vinculos/{vinculo['id']}", usuario="ub", empresa=mundo.company_b)
    assert response.status_code == 404


def test_A03_cliente_no_aporta_alcance(mundo, gobierno, ocupacion):
    nombre = "org06_A03"
    user_id = cuenta(mundo, nombre)
    funcionario = crear_funcionario(mundo, usuario="ua")
    response = post_vinculo(
        mundo,
        cuerpo_vinculo(user_id, funcionario["id"], company_id=mundo.company_b),
        usuario="ua",
        empresa=mundo.company_a,
    )
    assert response.status_code == 422

    response = consultar(
        mundo,
        "/mi-contexto",
        usuario="ua",
        empresa=mundo.company_a,
        params={"company_id": mundo.company_b, "ente": "x"},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "UNKNOWN_QUERY_PARAMETER"
    ca = consultar(mundo, "/mi-contexto", usuario="ua", empresa=mundo.company_a)
    assert ca.status_code == 200
    cb = consultar(mundo, "/mi-contexto", usuario="uab", empresa=mundo.company_b)
    assert cb.status_code == 200
    assert ca.json()["ente"]["id"] != cb.json()["ente"]["id"]


def test_A04_delegacion_de_atribuciones(mundo, gobierno, ocupacion):
    nombre = "org06_A04"
    delegante = nuevo_cargo(mundo, ocupacion, unidad="unidad_raiz")
    cargo_delegado = nuevo_cargo(mundo, ocupacion, unidad="unidad_hija")
    asig_d, _ = titular_activo(mundo, ocupacion, cargo_delegado)
    acto = acto_eficaz(mundo, delegante, medio="GACETA")
    datos = cuerpo(
        asig_d["funcionario"],
        delegante,
        acto,
        figura="DELEGACION_ATRIBUCIONES",
        cargo_origen_id=cargo_delegado,
        rendicion="Rendirá cuenta mensual ante el delegante.",
        declara_delegable=True,
        competencias=[{"accion": "APROBAR", "materia": "PRESUPUESTO"}],
    )
    activa(mundo, datos)

    user_id = cuenta(mundo, nombre)
    vinculo = vinculo_activo(mundo, cuerpo_vinculo(user_id, asig_d["funcionario"]["id"]))
    contexto = contexto_de(mundo, vinculo)

    ocupaciones = contexto["ocupaciones"]
    assert len(ocupaciones) == 2
    delegacion = next(o for o in ocupaciones if o["figura"] == "DELEGACION_ATRIBUCIONES")
    assert delegacion["cargo_id"] == delegante
    assert [(a["accion"], a["materia"]) for a in delegacion["autoridad"]] == [("APROBAR", "PRESUPUESTO")]
    acciones = {a["accion"] for a in delegacion["autoridad"]}
    assert "FIRMAR" not in acciones


def test_A05_suplencia(mundo, gobierno, ocupacion):
    nombre_suplente = "org06_A05_suplente"
    nombre_titular = "org06_A05_titular"
    cargo_suplido = nuevo_cargo(mundo, ocupacion, unidad="unidad_raiz")
    cargo_suplente = nuevo_cargo(mundo, ocupacion, unidad="unidad_hija")

    asig_titular, _ = titular_activo(mundo, ocupacion, cargo_suplido)
    asig_suplente, _ = titular_activo(mundo, ocupacion, cargo_suplente)
    acto = acto_eficaz(mundo, ocupacion["cargo_emisor"])
    datos = cuerpo(
        asig_suplente["funcionario"],
        cargo_suplido,
        acto,
        figura="SUPLENCIA",
        cargo_origen_id=cargo_suplente,
        desde=_desde_hace_dias(),
        hasta=_hasta_en_dias(),
    )
    activa(mundo, datos)

    user_suplente = cuenta(mundo, nombre_suplente)
    vinculo_suplente = vinculo_activo(mundo, cuerpo_vinculo(user_suplente, asig_suplente["funcionario"]["id"]))
    contexto_suplente = contexto_de(mundo, vinculo_suplente)
    suplencia = next(o for o in contexto_suplente["ocupaciones"] if o["figura"] == "SUPLENCIA")
    assert suplencia["ejerce"] is True

    user_titular = cuenta(mundo, nombre_titular)
    vinculo_titular = vinculo_activo(mundo, cuerpo_vinculo(user_titular, asig_titular["funcionario"]["id"]))
    contexto_titular = contexto_de(mundo, vinculo_titular)
    titular = next(o for o in contexto_titular["ocupaciones"] if o["cargo_id"] == cargo_suplido)
    assert titular["ejerce"] is False
    assert titular["autoridad"] == []
    assert contexto_titular["motivo_sin_autoridad"] == "SIN_OCUPACION"


def test_A06_encargaduria(mundo, gobierno, ocupacion):
    nombre = "org06_A06"
    cargo_vacante = nuevo_cargo(mundo, ocupacion, unidad="unidad_raiz")
    funcionario = crear_funcionario(mundo, usuario="ua")
    acto = acto_eficaz(mundo, ocupacion["cargo_emisor"])
    datos = cuerpo(funcionario, cargo_vacante, acto, figura="ENCARGADURIA")
    activa(mundo, datos)

    user_id = cuenta(mundo, nombre)
    vinculo = vinculo_activo(mundo, cuerpo_vinculo(user_id, funcionario["id"]))
    contexto = contexto_de(mundo, vinculo)
    encargaduria = next(o for o in contexto["ocupaciones"] if o["figura"] == "ENCARGADURIA")
    assert encargaduria["ejerce"] is True
    assert encargaduria["autoridad"]


def test_A07_comision(mundo, gobierno, ocupacion):
    nombre = "org06_A07"
    cargo_origen = nuevo_cargo(mundo, ocupacion, unidad="unidad_raiz")
    cargo_comision = nuevo_cargo(mundo, ocupacion, unidad="unidad_hija")
    asig_origen, _ = titular_activo(mundo, ocupacion, cargo_origen)
    acto = acto_eficaz(mundo, ocupacion["cargo_emisor"])
    datos = cuerpo(
        asig_origen["funcionario"],
        cargo_comision,
        acto,
        figura="COMISION_SERVICIO",
        cargo_origen_id=cargo_origen,
        desde=_desde_hace_dias(),
        hasta=_hasta_en_dias(),
    )
    activa(mundo, datos)

    user_id = cuenta(mundo, nombre)
    vinculo = vinculo_activo(mundo, cuerpo_vinculo(user_id, asig_origen["funcionario"]["id"]))
    contexto = contexto_de(mundo, vinculo)
    comision = next(o for o in contexto["ocupaciones"] if o["figura"] == "COMISION_SERVICIO")
    assert comision["ejerce"] is True


def test_A08_firma_solo_firmar(mundo, gobierno, ocupacion):
    nombre = "org06_A08"
    delegante = nuevo_cargo(mundo, ocupacion, unidad="unidad_raiz")
    cargo_delegado = nuevo_cargo(mundo, ocupacion, unidad="unidad_hija")
    asig_d, _ = titular_activo(mundo, ocupacion, cargo_delegado)
    acto = acto_eficaz(mundo, delegante, medio="GACETA")
    datos = cuerpo(
        asig_d["funcionario"],
        delegante,
        acto,
        figura="DELEGACION_FIRMA",
        cargo_origen_id=cargo_delegado,
        rendicion="Rendición de firma.",
        declara_delegable=True,
        competencias=[{"accion": "FIRMAR", "materia": "PRESUPUESTO"}],
    )
    activa(mundo, datos)
    emisor_vinculado(mundo, nombre, asig_d["funcionario"]["id"])
    exigir_identidad(mundo)

    response = emitir(mundo, acto_borrador(mundo, delegante, "APROBAR", "PRESUPUESTO"), nombre)
    assert response.status_code == 403
    assert response.json()["code"] == "GOV_FUNCTIONAL_AUTHORITY_REQUIRED"

    response = emitir(mundo, acto_borrador(mundo, delegante, "FIRMAR", "PRESUPUESTO"), nombre)
    assert response.status_code == 200

    exigir_identidad(mundo, False)


def test_A09_avocacion_no_termina_delegacion(mundo, gobierno, ocupacion):
    nombre = "org06_A09"
    delegante = nuevo_cargo(mundo, ocupacion, unidad="unidad_raiz")
    cargo_delegado = nuevo_cargo(mundo, ocupacion, unidad="unidad_hija")
    asig_d, _ = titular_activo(mundo, ocupacion, cargo_delegado)
    acto = acto_eficaz(mundo, delegante, medio="GACETA")
    datos = cuerpo(
        asig_d["funcionario"],
        delegante,
        acto,
        figura="DELEGACION_ATRIBUCIONES",
        cargo_origen_id=cargo_delegado,
        rendicion="Rendirá cuenta mensual ante el delegante.",
        declara_delegable=True,
        competencias=[{"accion": "APROBAR", "materia": "PRESUPUESTO"}],
    )
    asignacion_delegada = activa(mundo, datos)
    accion(
        mundo,
        asignacion_delegada,
        "avocar",
        cuerpo={"acto_id": acto, "asunto": "Avocación de prueba"},
        usuario="uab",
    )

    user_id = cuenta(mundo, nombre)
    vinculo = vinculo_activo(mundo, cuerpo_vinculo(user_id, asig_d["funcionario"]["id"]))
    contexto = contexto_de(mundo, vinculo)
    delegacion = next(o for o in contexto["ocupaciones"] if o["figura"] == "DELEGACION_ATRIBUCIONES")
    assert delegacion["situacion"] == "VIGENTE"
    assert delegacion["avocaciones"] == 1


def test_A10_historico_no_concede(mundo, gobierno, ocupacion):
    nombre = "org06_A10"
    cargo = nuevo_cargo(mundo, ocupacion, unidad="unidad_raiz")
    detalle, _ = titular_activo(mundo, ocupacion, cargo)
    asignacion = detalle
    accion(
        mundo,
        asignacion,
        "finalizar",
        cuerpo={"fecha": D(3, 1).isoformat(), "motivo": "Fin de la designación de prueba."},
        usuario="uab",
    )
    user_id = cuenta_con_permisos(mundo, nombre, [("gobierno_actos", "issue"), ("gobierno_actos", "view")])
    vinculo = vinculo_activo(mundo, cuerpo_vinculo(user_id, detalle["funcionario"]["id"]))
    contexto_historico = contexto_de(mundo, vinculo, fecha=D(2, 15))
    assert contexto_historico["es_historica"] is True
    assert len(contexto_historico["ocupaciones"]) == 1
    assert contexto_historico["ocupaciones"][0]["ejerce"] is True

    contexto_hoy = contexto_de(mundo, vinculo)
    assert contexto_hoy["ocupaciones"] == []
    assert contexto_hoy["motivo_sin_autoridad"] == "SIN_OCUPACION"

    exigir_identidad(mundo)
    response = emitir(mundo, acto_borrador(mundo, cargo), nombre)
    assert response.status_code == 403
    assert response.json()["code"] == "GOV_FUNCTIONAL_AUTHORITY_REQUIRED"
    exigir_identidad(mundo, False)


def test_A11_con_exigencia_sin_vinculo(mundo, gobierno, ocupacion):
    nombre = "org06_A11"
    user_id = cuenta_con_permisos(
        mundo, nombre, [("gobierno_actos", "issue"), ("gobierno_actos", "view")]
    )
    cargo = nuevo_cargo(mundo, ocupacion, unidad="unidad_raiz")
    titular_activo(mundo, ocupacion, cargo)

    exigir_identidad(mundo)
    response = emitir(mundo, acto_borrador(mundo, cargo), nombre)
    assert response.status_code == 403
    assert response.json()["code"] == "GOV_IDENTITY_LINK_REQUIRED"

    with mundo.factory() as session:
        event = session.execute(
            select(AuditEvent).where(
                AuditEvent.action == "GOV_IDENTITY_GUARD_BLOCKED",
                AuditEvent.user_id == user_id,
            )
        ).scalar_one()
        assert event is not None

    exigir_identidad(mundo, False)


def test_A12_sin_exigencia_la_guarda_no_actua(mundo, gobierno, ocupacion):
    nombre = "org06_A12"
    cuenta_con_permisos(mundo, nombre, [("gobierno_actos", "issue"), ("gobierno_actos", "view")])
    cargo = nuevo_cargo(mundo, ocupacion, unidad="unidad_raiz")
    titular_activo(mundo, ocupacion, cargo)

    exigir_identidad(mundo, False)
    response = emitir(mundo, acto_borrador(mundo, cargo), nombre)
    assert response.status_code == 200


def test_A13_cuenta_inactiva_conserva_historia(mundo, gobierno, ocupacion):
    nombre = "org06_A13"
    cargo = nuevo_cargo(mundo, ocupacion, unidad="unidad_raiz")
    detalle, _ = titular_activo(mundo, ocupacion, cargo)
    user_id = cuenta(mundo, nombre)
    vinculo = vinculo_activo(mundo, cuerpo_vinculo(user_id, detalle["funcionario"]["id"]))

    with mundo.factory() as session:
        user = session.get(User, user_id)
        user.status = "INACTIVE"
        session.commit()

    contexto = contexto_de(mundo, vinculo)
    assert contexto["tiene_autoridad"] is False
    assert contexto["motivo_sin_autoridad"] == "CUENTA_INACTIVA"
    assert len(contexto["ocupaciones"]) == 1
