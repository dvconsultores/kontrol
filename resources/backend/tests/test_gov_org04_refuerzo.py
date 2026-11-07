"""Refuerzo de ocupación: situación a fecha, aislamiento de listados y esquema de delegación (ORG-04)."""

pytest_plugins = (
    "tests.conftest_multicompany",
    "tests.test_gov_ctl06_hallazgos",
    "tests.org04_ayudantes",
)

from tests.org04_ayudantes import (  # noqa: E402
    D,
    O,
    accion,
    activa,
    acto_eficaz,
    crear_funcionario,
    cuerpo,
    nuevo_cargo,
    post_asignacion,
    titular_activo,
)


def _get(mundo, ruta, usuario="ua", empresa=None, params=None):
    if empresa is None:
        empresa = mundo.company_a
    return mundo.client.get(
        f"/api/v1{O}{ruta}",
        headers=mundo.como(usuario, empresa),
        params=params or {},
    )


def test_r1_futura_no_ocupa(mundo, gobierno, ocupacion):
    cargo = nuevo_cargo(mundo, ocupacion)
    funcionario = crear_funcionario(mundo)

    acto = acto_eficaz(mundo, ocupacion["cargo_emisor"])
    datos = cuerpo(
        funcionario,
        cargo,
        acto,
        desde=D(6, 1).isoformat(),
    )
    asignacion = activa(mundo, datos)

    respuesta_antes = _get(mundo, f"/asignaciones/{asignacion['id']}", params={"fecha": D(5, 1).isoformat()})
    assert respuesta_antes.status_code == 200
    detalle = respuesta_antes.json()
    assert detalle["situacion"] == "FUTURA"
    assert detalle["ejerce"] is False

    respuesta_cargo_antes = _get(mundo, f"/cargos/{cargo}", params={"fecha": D(5, 1).isoformat()})
    assert respuesta_cargo_antes.status_code == 200
    assert respuesta_cargo_antes.json()["vacante"] is True

    respuesta_desde = _get(mundo, f"/asignaciones/{asignacion['id']}", params={"fecha": D(6, 1).isoformat()})
    assert respuesta_desde.status_code == 200
    detalle_desde = respuesta_desde.json()
    assert detalle_desde["situacion"] == "VIGENTE"

    respuesta_cargo_desde = _get(mundo, f"/cargos/{cargo}", params={"fecha": D(6, 1).isoformat()})
    assert respuesta_cargo_desde.status_code == 200
    assert respuesta_cargo_desde.json()["vacante"] is False


def test_r2_revocada_incluye_el_dia_final(mundo, gobierno, ocupacion):
    cargo = nuevo_cargo(mundo, ocupacion)
    funcionario = crear_funcionario(mundo)

    acto = acto_eficaz(mundo, ocupacion["cargo_emisor"])
    datos = cuerpo(
        funcionario,
        cargo,
        acto,
        desde=D(2, 1).isoformat(),
    )
    asignacion = activa(mundo, datos)

    acto_rev = acto_eficaz(mundo, ocupacion["cargo_emisor"], fecha=D(3, 1))
    respuesta_revocacion = accion(
        mundo,
        asignacion,
        "revocar",
        cuerpo={
            "acto_id": acto_rev,
            "fecha": D(3, 1).isoformat(),
            "motivo": "Revocación de prueba",
        },
        usuario="uab",
    )
    assert respuesta_revocacion.status_code == 200

    respuesta_cargo_ultimo_dia = _get(mundo, f"/cargos/{cargo}", params={"fecha": D(3, 1).isoformat()})
    assert respuesta_cargo_ultimo_dia.status_code == 200
    cargo_ultimo_dia = respuesta_cargo_ultimo_dia.json()
    assert cargo_ultimo_dia["historial"][0]["situacion"] == "VIGENTE"
    assert cargo_ultimo_dia["vacante"] is False

    respuesta_cargo_despues = _get(mundo, f"/cargos/{cargo}", params={"fecha": D(3, 2).isoformat()})
    assert respuesta_cargo_despues.status_code == 200
    cargo_despues = respuesta_cargo_despues.json()
    assert cargo_despues["historial"][0]["situacion"] == "REVOCADA"
    assert cargo_despues["vacante"] is True


def test_r3_listado_y_csv_aislados(mundo, gobierno, ocupacion):
    cargo = nuevo_cargo(mundo, ocupacion)
    funcionario = crear_funcionario(mundo)

    acto = acto_eficaz(mundo, ocupacion["cargo_emisor"])
    datos = cuerpo(
        funcionario,
        cargo,
        acto,
    )
    asignacion = activa(mundo, datos)

    respuesta_listado = _get(mundo, "/asignaciones", usuario="ub", empresa=mundo.company_b)
    assert respuesta_listado.status_code == 200
    ids = [item["id"] for item in respuesta_listado.json()["items"]]
    assert asignacion["id"] not in ids

    respuesta_csv = _get(mundo, "/asignaciones.csv", usuario="ub", empresa=mundo.company_b)
    assert respuesta_csv.status_code == 200
    assert asignacion["codigo"] not in respuesta_csv.text

    respuesta_funcionarios = _get(mundo, "/funcionarios", usuario="ub", empresa=mundo.company_b)
    assert respuesta_funcionarios.status_code == 200
    ids_funcionarios = [item["id"] for item in respuesta_funcionarios.json()["items"]]
    assert funcionario["id"] not in ids_funcionarios


def test_r4_delegacion_exige_declaracion_y_rendicion(mundo, gobierno, ocupacion):
    delegante = nuevo_cargo(mundo, ocupacion, unidad="unidad_raiz")
    cargo_delegado = nuevo_cargo(mundo, ocupacion, unidad="unidad_hija")
    asig_d, _ = titular_activo(mundo, ocupacion, cargo_delegado)
    acto = acto_eficaz(mundo, delegante, medio="GACETA")

    cuerpo_base = cuerpo(
        asig_d["funcionario"],
        delegante,
        acto,
        figura="DELEGACION_ATRIBUCIONES",
        cargo_origen_id=cargo_delegado,
        rendicion="Rendirá cuenta mensual ante el delegante.",
        declara_delegable=True,
        competencias=[{"accion": "APROBAR", "materia": "PRESUPUESTO"}],
    )

    sin_declaracion = dict(cuerpo_base)
    sin_declaracion.pop("declara_delegable")
    respuesta_sin_declaracion = post_asignacion(mundo, sin_declaracion)
    assert respuesta_sin_declaracion.status_code == 422
    assert respuesta_sin_declaracion.json()["code"] == "VALIDATION_ERROR"

    sin_rendicion = dict(cuerpo_base)
    sin_rendicion.pop("rendicion")
    respuesta_sin_rendicion = post_asignacion(mundo, sin_rendicion)
    assert respuesta_sin_rendicion.status_code == 422
    assert respuesta_sin_rendicion.json()["code"] == "VALIDATION_ERROR"
