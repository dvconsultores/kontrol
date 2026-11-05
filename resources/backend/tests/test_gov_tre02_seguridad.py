import itertools

import pytest
from sqlalchemy import text

from tests.test_gov_ctl06_hallazgos import ANIO, _crear_usuario_con_permisos
from tests.test_gov_tre01_cuentas import (
    HOY,
    crear_banco,
    crear_cuenta,
    cuenta_vigente,
    eventos,
    numero_de,
)
from tests.tre02_ayudantes import (
    MOTIVO,
    P,
    accion,
    activar_programa,
    cerrar_regla,
    crear_programa,
    crear_rubro,
    declarar,
    delete_con_version,
    linea,
    patch_con_version,
    programa_vigente,
    regla_sod_vigente,
    sin_if_match,
    ver,
)

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos")

_ejercicios = itertools.count(ANIO)


@pytest.fixture(scope="module")
def caja_consulta(mundo):
    _crear_usuario_con_permisos(
        mundo,
        "caja_consulta",
        [("gobierno_caja", "view")],
        mundo.company_a,
    )
    return "caja_consulta"


@pytest.fixture(scope="module")
def caja_gestor(mundo):
    _crear_usuario_con_permisos(
        mundo,
        "caja_gestor",
        [("gobierno_caja", "view"), ("gobierno_caja", "manage")],
        mundo.company_a,
    )
    return "caja_gestor"


@pytest.fixture(scope="module")
def caja_ajeno(mundo):
    _crear_usuario_con_permisos(
        mundo,
        "caja_ajeno",
        [("gobierno_hallazgos", "view")],
        mundo.company_a,
    )
    return "caja_ajeno"


@pytest.fixture(scope="module")
def caja_activador(mundo):
    _crear_usuario_con_permisos(
        mundo,
        "caja_activador",
        [("gobierno_caja", "view"), ("gobierno_caja", "activate")],
        mundo.company_a,
    )
    return "caja_activador"


def test_sg01_consulta_solo_lectura(mundo, gobierno, caja_consulta):
    ejercicio = next(_ejercicios)
    programa = crear_programa(mundo, ejercicio, usuario="ua")
    r = mundo.get("/gobierno/tesoreria/programas", caja_consulta, mundo.company_a)
    assert r.status_code == 200
    r = mundo.get(
        f"/gobierno/tesoreria/programas/{programa['id']}", caja_consulta, mundo.company_a
    )
    assert r.status_code == 200
    r = mundo.get("/gobierno/tesoreria/rubros", caja_consulta, mundo.company_a)
    assert r.status_code == 200

    for ruta, cuerpo in [
        ("/gobierno/tesoreria/rubros", {"codigo": "R100", "nombre": "Rubro", "tipo": "INGRESO"}),
        ("/gobierno/tesoreria/programas", {"ejercicio": ejercicio, "moneda": "VES", "mes_inicial": 1}),
        (
            f"/gobierno/tesoreria/programas/{programa['id']}/declaraciones",
            {
                "cuenta_id": "00000000-0000-0000-0000-000000000000",
                "monto": "10.00",
                "fecha_corte": HOY.isoformat(),
                "fundamento": MOTIVO,
            },
        ),
        (
            f"/gobierno/tesoreria/programas/{programa['id']}/lineas",
            {"rubro_id": "00000000-0000-0000-0000-000000000000", "mes": 1, "monto": "10.00"},
        ),
        (f"/gobierno/tesoreria/programas/{programa['id']}/activar", {}),
        (f"/gobierno/tesoreria/programas/{programa['id']}/reprogramar", {"motivo": MOTIVO}),
        (f"/gobierno/tesoreria/programas/{programa['id']}/descartar", {}),
        (f"/gobierno/tesoreria/programas/{programa['id']}/cerrar", {"motivo": MOTIVO}),
    ]:
        r = sin_if_match(mundo, ruta, cuerpo, usuario=caja_consulta)
        assert r.status_code == 403, r.text

    r = mundo.get(
        f"/gobierno/tesoreria/programas/{programa['id']}/opciones",
        caja_consulta,
        mundo.company_a,
    )
    assert r.status_code == 403


def test_sg02_gestor_sin_activar_ni_cerrar(mundo, gobierno, caja_gestor, siembra):
    ejercicio = next(_ejercicios)
    rubro = crear_rubro(mundo, "INGRESO", usuario=caja_gestor)
    cuenta = cuenta_vigente(mundo, siembra["cargo_vigente"], usuario="ua")
    programa = crear_programa(mundo, ejercicio, usuario=caja_gestor)
    programa = declarar(mundo, programa, cuenta, "100.00", usuario=caja_gestor)
    programa = linea(mundo, programa, rubro, 1, "50.00", usuario=caja_gestor)

    r = accion(mundo, programa, "activar", {}, usuario=caja_gestor)
    assert r.status_code == 403
    r = accion(mundo, programa, "cerrar", {"motivo": MOTIVO}, usuario=caja_gestor)
    assert r.status_code == 403

    programa = activar_programa(mundo, programa, usuario="ua")
    r = accion(mundo, programa, "reprogramar", {"motivo": MOTIVO}, usuario=caja_gestor)
    assert r.status_code == 201


def test_sg03_usuario_ajeno_403(mundo, gobierno, caja_ajeno):
    r = mundo.get("/gobierno/tesoreria/programas", caja_ajeno, mundo.company_a)
    assert r.status_code == 403


def test_sg04_empresa_ajena_no_accede(mundo, gobierno, siembra):
    ejercicio = next(_ejercicios)
    cuenta = cuenta_vigente(mundo, siembra["cargo_vigente"], usuario="ua")
    rubro = crear_rubro(mundo, "INGRESO", usuario="ua")
    programa = crear_programa(mundo, ejercicio, usuario="ua")
    programa = declarar(mundo, programa, cuenta, "100.00", usuario="ua")
    programa = linea(mundo, programa, rubro, 1, "50.00", usuario="ua")

    r = mundo.get(
        f"/gobierno/tesoreria/programas/{programa['id']}", "ub", mundo.company_b
    )
    assert r.status_code == 404
    assert r.json()["code"] == "GOV_CASH_PROGRAM_NOT_FOUND"

    for verbo, cuerpo in [
        (
            "declaraciones",
            {
                "cuenta_id": cuenta["id"],
                "monto": "10.00",
                "fecha_corte": HOY.isoformat(),
                "fundamento": MOTIVO,
            },
        ),
        ("lineas", {"rubro_id": rubro["id"], "mes": 1, "monto": "10.00"}),
        ("activar", {}),
        ("reprogramar", {"motivo": MOTIVO}),
        ("cerrar", {"motivo": MOTIVO}),
    ]:
        r = accion(mundo, programa, verbo, cuerpo, usuario="ub", empresa=mundo.company_b)
        assert r.status_code == 404, r.text

    r = mundo.get("/gobierno/tesoreria/programas", "ub", mundo.company_b)
    assert r.status_code == 200
    assert all(item["id"] != programa["id"] for item in r.json()["items"])


def test_sg05_rubro_y_cuenta_ajenos_y_linea_de_otro_programa(mundo, gobierno):
    ejercicio = next(_ejercicios)
    rubro_b = crear_rubro(mundo, "INGRESO", usuario="ub", empresa=mundo.company_b)
    cuenta_b = crear_cuenta(mundo, usuario="ub", empresa=mundo.company_b)
    programa = crear_programa(mundo, ejercicio, usuario="ua")
    programa_otro = crear_programa(mundo, next(_ejercicios), usuario="ua")
    programa_otro = linea(
        mundo, programa_otro, crear_rubro(mundo, "INGRESO", usuario="ua"), 1, "10.00"
    )
    linea_otra = programa_otro["lineas"][0]

    r = accion(
        mundo,
        programa,
        "lineas",
        {"rubro_id": rubro_b["id"], "mes": 1, "monto": "10.00"},
        usuario="ua",
    )
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_CASH_PROGRAM_INVALID"

    r = accion(
        mundo,
        programa,
        "declaraciones",
        {
            "cuenta_id": cuenta_b["id"],
            "monto": "10.00",
            "fecha_corte": HOY.isoformat(),
            "fundamento": MOTIVO,
        },
        usuario="ua",
    )
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_CASH_PROGRAM_INVALID"

    r = patch_con_version(
        mundo,
        f"/gobierno/tesoreria/programas/{programa['id']}/lineas/{linea_otra['id']}",
        {"monto": "20.00"},
        programa["version"],
        usuario="ua",
    )
    assert r.status_code == 404
    assert r.json()["code"] == "GOV_CASH_LINE_NOT_FOUND"

    r = delete_con_version(
        mundo,
        f"/gobierno/tesoreria/programas/{programa['id']}/lineas/{linea_otra['id']}",
        programa["version"],
        usuario="ua",
    )
    assert r.status_code == 404
    assert r.json()["code"] == "GOV_CASH_LINE_NOT_FOUND"


def test_sg14_cuenta_vigente_de_otra_empresa(mundo, gobierno, siembra):
    ejercicio = next(_ejercicios)
    cuenta = cuenta_vigente(mundo, siembra["cargo_vigente"])
    with mundo.factory() as db:
        db.execute(
            text("UPDATE gov_bank_accounts SET company_id = :empresa WHERE id = :id"),
            {"empresa": mundo.company_b, "id": cuenta["id"]},
        )
        db.commit()
    programa = crear_programa(mundo, ejercicio, usuario="ua")

    r = accion(
        mundo,
        programa,
        "declaraciones",
        {
            "cuenta_id": cuenta["id"],
            "monto": "10.00",
            "fecha_corte": HOY.isoformat(),
            "fundamento": MOTIVO,
        },
        usuario="ua",
    )
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_CASH_PROGRAM_INVALID"


def test_sg06_company_id_extra_rechazado(mundo, gobierno, siembra):
    ejercicio = next(_ejercicios)
    cuenta = cuenta_vigente(mundo, siembra["cargo_vigente"], usuario="ua")
    rubro = crear_rubro(mundo, "INGRESO", usuario="ua")
    for ruta, cuerpo in [
        (
            "/gobierno/tesoreria/rubros",
            {
                "codigo": "R200",
                "nombre": "Rubro",
                "tipo": "INGRESO",
                "company_id": mundo.company_a,
            },
        ),
        (
            "/gobierno/tesoreria/programas",
            {
                "ejercicio": ejercicio,
                "moneda": "VES",
                "mes_inicial": 1,
                "company_id": mundo.company_a,
            },
        ),
    ]:
        r = sin_if_match(mundo, ruta, cuerpo, usuario="ua")
        assert r.status_code == 422

    programa = crear_programa(mundo, ejercicio, usuario="ua")
    for ruta, cuerpo in [
        (
            f"/programas/{programa['id']}/declaraciones",
            {
                "cuenta_id": cuenta["id"],
                "monto": "10.00",
                "fecha_corte": HOY.isoformat(),
                "fundamento": MOTIVO,
                "company_id": mundo.company_a,
            },
        ),
        (
            f"/programas/{programa['id']}/lineas",
            {
                "rubro_id": rubro["id"],
                "mes": 1,
                "monto": "10.00",
                "company_id": mundo.company_a,
            },
        ),
    ]:
        r = sin_if_match(mundo, f"/gobierno/tesoreria{ruta}", cuerpo, usuario="ua")
        assert r.status_code == 422


def test_sg07_uuid_directo_inexistente_404(mundo, gobierno):
    r = mundo.get(
        "/gobierno/tesoreria/programas/00000000-0000-0000-0000-000000000000",
        "ua",
        mundo.company_a,
    )
    assert r.status_code == 404
    assert r.json()["code"] == "GOV_CASH_PROGRAM_NOT_FOUND"


def test_sg08_version_vieja_y_sin_if_match(mundo, gobierno, siembra):
    ejercicio = next(_ejercicios)
    cuenta = cuenta_vigente(mundo, siembra["cargo_vigente"], usuario="ua")
    rubro = crear_rubro(mundo, "INGRESO", usuario="ua")
    programa = crear_programa(mundo, ejercicio, usuario="ua")
    version_vieja = programa["version"]
    programa = declarar(mundo, programa, cuenta, "100.00", usuario="ua")
    programa = linea(mundo, programa, rubro, 1, "50.00", usuario="ua")

    for verbo, cuerpo in [
        ("activar", {}),
        ("reprogramar", {"motivo": MOTIVO}),
        (
            "declaraciones",
            {
                "cuenta_id": cuenta["id"],
                "monto": "10.00",
                "fecha_corte": HOY.isoformat(),
                "fundamento": MOTIVO,
            },
        ),
        ("lineas", {"rubro_id": rubro["id"], "mes": 2, "monto": "10.00"}),
    ]:
        r = accion(mundo, programa, verbo, cuerpo, usuario="ua", version=version_vieja)
        assert r.status_code == 409, r.text
        assert r.json()["code"] == "GOV_CASH_PROGRAM_STALE"
        assert "version_actual" in r.json()["details"]

    for verbo, cuerpo in [
        ("activar", {}),
        ("reprogramar", {"motivo": MOTIVO}),
        (
            "declaraciones",
            {
                "cuenta_id": cuenta["id"],
                "monto": "10.00",
                "fecha_corte": HOY.isoformat(),
                "fundamento": MOTIVO,
            },
        ),
        ("lineas", {"rubro_id": rubro["id"], "mes": 2, "monto": "10.00"}),
    ]:
        r = sin_if_match(
            mundo,
            f"{P}/programas/{programa['id']}/{verbo}",
            cuerpo,
            usuario="ua",
        )
        assert r.status_code == 428, r.text
        assert r.json()["code"] == "GOV_CASH_PROGRAM_IF_MATCH_REQUIRED"


def test_sg09_numero_de_cuenta_oculto(mundo, gobierno, siembra):
    ejercicio = next(_ejercicios)
    banco = crear_banco(mundo)
    numero_esperado = numero_de(banco)
    cuenta = cuenta_vigente(
        mundo,
        siembra["cargo_vigente"],
        usuario="ua",
        banco=banco,
        numero=numero_esperado,
    )
    programa = crear_programa(mundo, ejercicio, usuario="ua")
    programa = declarar(mundo, programa, cuenta, "100.00", usuario="ua")

    detalle = ver(mundo, programa, usuario="ua")
    assert numero_esperado not in str(detalle)

    historia = detalle["historia"]
    assert numero_esperado not in str(historia)

    for accion_nombre in ("GOV_CASH_PROGRAM_CREATED", "GOV_CASH_PROGRAM_UPDATED"):
        eventos_programa = eventos(mundo, accion_nombre, programa["id"])
        for evento in eventos_programa:
            assert numero_esperado not in str(evento.after)


def test_sg10_ctl04_auditoria_institucional(mundo, gobierno):
    ejercicio = next(_ejercicios)
    programa = crear_programa(mundo, ejercicio, usuario="ua")
    r = mundo.get("/gobierno/auditoria/filtros", "ua", mundo.company_a)
    assert r.status_code == 200
    procesos = r.json()["procesos"]
    assert any(p["codigo"] == "TRE-02" for p in procesos)

    r = mundo.get(
        "/gobierno/auditoria/eventos?proceso=TRE-02&por_pagina=200",
        "ua",
        mundo.company_a,
    )
    assert r.status_code == 200
    items = r.json()["items"]
    creado = next(
        i
        for i in items
        if i["accion"] == "GOV_CASH_PROGRAM_CREATED"
        and i["entidad_id"] == programa["id"]
    )
    r = mundo.get(f"/gobierno/auditoria/eventos/{creado['id']}", "ua", mundo.company_a)
    assert r.status_code == 200
    detalle = r.json()
    assert detalle["objeto"]["ruta"] == f"/gobierno/tesoreria/programacion/{programa['id']}"


def test_sg11_catalogo_sod(mundo, gobierno):
    r = mundo.get("/gobierno/sod/acciones", "ua", mundo.company_a)
    assert r.status_code == 200
    procesos = r.json()["procesos"]
    tre02 = next(p for p in procesos if p["proceso"] == "TRE-02")
    assert len(tre02["acciones"]) == 4
    registrar = next(a for a in tre02["acciones"] if a["codigo"] == "TRE02_REGISTRAR")
    assert registrar["crea_objeto"] is True


def test_sg12_guarda_sod_activar(mundo, gobierno, siembra, caja_activador):
    ejercicio = next(_ejercicios)
    regla = regla_sod_vigente(mundo, "TRE02_REGISTRAR", "TRE02_ACTIVAR", "Regla prueba")
    try:
        cuenta = cuenta_vigente(mundo, siembra["cargo_vigente"], usuario="ua")
        rubro = crear_rubro(mundo, "INGRESO", usuario="ua")
        programa = crear_programa(mundo, ejercicio, usuario="ua")
        programa = declarar(mundo, programa, cuenta, "100.00", usuario="ua")
        programa = linea(mundo, programa, rubro, 1, "50.00", usuario="ua")

        r = accion(mundo, programa, "activar", {}, usuario="ua")
        assert r.status_code == 409
        assert r.json()["code"] == "GOV_SOD_CONFLICT"

        detalle = ver(mundo, programa, usuario="ua")
        assert detalle["estado"] == "BORRADOR"

        r = accion(mundo, programa, "activar", {}, usuario=caja_activador)
        assert r.status_code == 200
    finally:
        cerrar_regla(mundo, regla)


def test_sg15_guarda_sod_reprogramar(mundo, gobierno, siembra, caja_gestor):
    ejercicio = next(_ejercicios)
    regla = regla_sod_vigente(mundo, "TRE02_ACTIVAR", "TRE02_REPROGRAMAR", "Regla prueba")
    try:
        programa = programa_vigente(mundo, siembra["cargo_vigente"], ejercicio)

        r = accion(mundo, programa, "reprogramar", {"motivo": MOTIVO}, usuario="ua")
        assert r.status_code == 409
        assert r.json()["code"] == "GOV_SOD_CONFLICT"

        detalle = ver(mundo, programa, usuario="ua")
        assert detalle["borrador_numero"] is None

        r = accion(mundo, programa, "reprogramar", {"motivo": MOTIVO}, usuario=caja_gestor)
        assert r.status_code == 201
    finally:
        cerrar_regla(mundo, regla)


def test_sg16_guarda_sod_cerrar(mundo, gobierno, siembra, caja_activador):
    ejercicio = next(_ejercicios)
    regla = regla_sod_vigente(mundo, "TRE02_ACTIVAR", "TRE02_CERRAR", "Regla prueba")
    try:
        programa = programa_vigente(mundo, siembra["cargo_vigente"], ejercicio)

        r = accion(mundo, programa, "cerrar", {"motivo": MOTIVO}, usuario="ua")
        assert r.status_code == 409
        assert r.json()["code"] == "GOV_SOD_CONFLICT"

        detalle = ver(mundo, programa, usuario="ua")
        assert detalle["estado"] == "VIGENTE"

        r = accion(mundo, programa, "cerrar", {"motivo": MOTIVO}, usuario=caja_activador)
        assert r.status_code == 200
    finally:
        cerrar_regla(mundo, regla)



def test_sg13_sin_presupuesto(mundo, gobierno):
    ejercicio = next(_ejercicios)
    programa = crear_programa(mundo, ejercicio, usuario="ua")

    def _sin_presupuesto(obj, ruta=""):
        if isinstance(obj, dict):
            for clave, valor in obj.items():
                assert "presupuest" not in clave.lower()
                _sin_presupuesto(valor, f"{ruta}.{clave}")
        elif isinstance(obj, list):
            for indice, valor in enumerate(obj):
                _sin_presupuesto(valor, f"{ruta}[{indice}]")

    r = mundo.get("/gobierno/tesoreria/programas", "ua", mundo.company_a)
    assert r.status_code == 200
    _sin_presupuesto(r.json())

    detalle = ver(mundo, programa, usuario="ua")
    _sin_presupuesto(detalle)
