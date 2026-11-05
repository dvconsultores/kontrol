import itertools

from tests.test_gov_ctl06_hallazgos import ANIO, _post
from tests.test_gov_tre01_cuentas import HOY, cuenta_vigente, eventos
from tests.tre02_ayudantes import (
    MOTIVO,
    P,
    accion,
    crear_programa,
    crear_rubro,
    declarar,
    linea,
    patch_con_version,
    programa_vigente,
    reprogramar,
    ver,
)

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos")

_ejercicios = itertools.count(ANIO)


def test_ci01_cierre_motivo_completo(mundo, gobierno, siembra):
    """CI-01: cerrar con motivo deja programa CERRADO, versión CERRADA y auditoría."""
    ejercicio = next(_ejercicios)
    programa = programa_vigente(mundo, siembra["cargo_vigente"], ejercicio)
    r = accion(mundo, programa, "cerrar", {"motivo": MOTIVO})
    assert r.status_code == 200, r.text
    detalle = r.json()
    assert detalle["estado"] == "CERRADO"
    assert detalle["cerrado_por"] is not None
    assert detalle["cerrado_en"] is not None
    assert detalle["motivo_cierre"] == MOTIVO
    assert detalle["version_vigente"] is None
    version_vista = detalle["version_vista"]
    version_cerrada = next(v for v in detalle["versiones"] if v["numero"] == version_vista)
    assert version_cerrada["estado"] == "CERRADA"
    historia = next(h for h in detalle["historia"] if h["tipo"] == "CERRADO")
    assert historia["version_numero"] == version_vista

    eventos_cierre = eventos(mundo, "GOV_CASH_PROGRAM_CLOSED", programa["id"])
    assert len(eventos_cierre) == 1


def test_ci02_motivo_corto_rechazado(mundo, gobierno, siembra):
    """CI-02: motivo menor a 10 caracteres se rechaza con 422."""
    ejercicio = next(_ejercicios)
    programa = programa_vigente(mundo, siembra["cargo_vigente"], ejercicio)
    r = accion(mundo, programa, "cerrar", {"motivo": "corto"})
    assert r.status_code == 422
    assert r.json()["code"] == "VALIDATION_ERROR"


def test_ci03_borrador_abierto_rechaza_cierre(mundo, gobierno, siembra):
    """CI-03: con borrador abierto no se puede cerrar."""
    ejercicio = next(_ejercicios)
    programa = programa_vigente(mundo, siembra["cargo_vigente"], ejercicio)
    programa = reprogramar(mundo, programa)
    r = accion(mundo, programa, "cerrar", {"motivo": MOTIVO})
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_CASH_PROGRAM_DRAFT_OPEN"


def test_ci04_borrador_no_se_puede_cerrar(mundo, gobierno, siembra):
    """CI-04: un programa en BORRADOR no se puede cerrar."""
    ejercicio = next(_ejercicios)
    programa = crear_programa(mundo, ejercicio)
    r = accion(mundo, programa, "cerrar", {"motivo": MOTIVO})
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_CASH_PROGRAM_INVALID_STATE"


def test_ci05_cerrado_no_admite_operaciones(mundo, gobierno, siembra):
    """CI-05: un programa cerrado rechaza reprogramar, activar, descartar, declarar, línea y cerrar."""
    ejercicio = next(_ejercicios)
    programa = programa_vigente(mundo, siembra["cargo_vigente"], ejercicio)
    r_cierre = accion(mundo, programa, "cerrar", {"motivo": MOTIVO})
    assert r_cierre.status_code == 200, r_cierre.text
    programa = r_cierre.json()

    r = accion(mundo, programa, "reprogramar", {"motivo": MOTIVO})
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_CASH_PROGRAM_INVALID_STATE"

    r = accion(mundo, programa, "activar", {})
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_CASH_PROGRAM_INVALID_STATE"

    r = accion(mundo, programa, "descartar", {})
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_CASH_PROGRAM_INVALID_STATE"

    cuenta = cuenta_vigente(mundo, siembra["cargo_vigente"])
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
    )
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_CASH_PROGRAM_INVALID_STATE"

    rubro = crear_rubro(mundo, "INGRESO")
    r = accion(
        mundo,
        programa,
        "lineas",
        {"rubro_id": rubro["id"], "mes": 1, "monto": "10.00"},
    )
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_CASH_PROGRAM_INVALID_STATE"

    r = accion(mundo, programa, "cerrar", {"motivo": MOTIVO})
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_CASH_PROGRAM_INVALID_STATE"

    assert ver(mundo, programa)["estado"] == "CERRADO"


def test_ci06_ejercicio_moneda_duplicado_tras_cierre(mundo, gobierno, siembra):
    """CI-06: ejercicio y moneda de un programa cerrado no admiten otro programa."""
    ejercicio = next(_ejercicios)
    programa = programa_vigente(mundo, siembra["cargo_vigente"], ejercicio)
    r_cierre = accion(mundo, programa, "cerrar", {"motivo": MOTIVO})
    assert r_cierre.status_code == 200, r_cierre.text
    r = _post(
        mundo,
        f"{P}/programas",
        "ua",
        mundo.company_a,
        {"ejercicio": ejercicio, "moneda": programa["moneda"], "mes_inicial": 1},
    )
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_CASH_PROGRAM_DUPLICATE"


def test_rb01_alta_rubro(mundo, gobierno):
    """RB-01: alta de rubro 201 ACTIVO y evento GOV_CASH_ITEM_CREATED."""
    rubro = crear_rubro(mundo, "INGRESO")
    assert rubro["estado"] == "ACTIVO"

    eventos_creados = eventos(mundo, "GOV_CASH_ITEM_CREATED", rubro["id"])
    assert len(eventos_creados) == 1


def test_rb02_codigo_repetido_por_empresa(mundo, gobierno):
    """RB-02: código repetido en la misma empresa 409; en company_b se admite."""
    rubro = crear_rubro(mundo, "INGRESO", codigo="R-DUP")
    r = _post(
        mundo,
        f"{P}/rubros",
        "ua",
        mundo.company_a,
        {"codigo": rubro["codigo"], "nombre": "Repetido", "tipo": "INGRESO"},
    )
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_CASH_ITEM_DUPLICATE"

    r = _post(
        mundo,
        f"{P}/rubros",
        "ub",
        mundo.company_b,
        {"codigo": rubro["codigo"], "nombre": "Rubro B", "tipo": "INGRESO"},
    )
    assert r.status_code == 201, r.text


def test_rb03_validacion_campos(mundo, gobierno):
    """RB-03: tipo no válido, código vacío y nombre corto responden 422."""
    casos = [
        {"codigo": "R-OK", "nombre": "Nombre válido", "tipo": "GASTO"},
        {"codigo": "", "nombre": "Nombre válido", "tipo": "INGRESO"},
        {"codigo": "R-OK", "nombre": "ab", "tipo": "INGRESO"},
    ]
    for cuerpo in casos:
        r = _post(mundo, f"{P}/rubros", "ua", mundo.company_a, cuerpo)
        assert r.status_code == 422, cuerpo
        assert r.json()["code"] == "VALIDATION_ERROR"


def test_rb04_patch_rubro(mundo, gobierno):
    """RB-04: exige If-Match, controla versión vieja, rechaza tipo/código y audita."""
    rubro = crear_rubro(mundo, "INGRESO")
    version_actual = rubro["version"]

    r = patch_con_version(
        mundo,
        f"{P}/rubros/{rubro['id']}",
        {"nombre": "Otro nombre"},
        None,
    )
    assert r.status_code == 428
    assert r.json()["code"] == "GOV_CASH_PROGRAM_IF_MATCH_REQUIRED"

    r = patch_con_version(
        mundo,
        f"{P}/rubros/{rubro['id']}",
        {"nombre": "Otro nombre"},
        version_actual,
    )
    assert r.status_code == 200, r.text
    version_actual = r.json()["version"]

    r = patch_con_version(
        mundo,
        f"{P}/rubros/{rubro['id']}",
        {"nombre": "Versión vieja"},
        version_actual - 1,
    )
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_CASH_PROGRAM_STALE"

    for cuerpo in ({"tipo": "DESEMBOLSO"}, {"codigo": "OTRO"}):
        r = patch_con_version(
            mundo,
            f"{P}/rubros/{rubro['id']}",
            cuerpo,
            version_actual,
        )
        assert r.status_code == 422, cuerpo
        assert r.json()["code"] == "VALIDATION_ERROR"

    eventos_actualizados = eventos(mundo, "GOV_CASH_ITEM_UPDATED", rubro["id"])
    assert len(eventos_actualizados) == 1


def test_rb05_inactivar_rubro(mundo, gobierno, siembra):
    """RB-05: rubro inactivo no aparece en filtro ACTIVO ni en opciones, rechaza línea nueva y conserva existente."""
    rubro = crear_rubro(mundo, "INGRESO")

    ejercicio = next(_ejercicios)
    programa = crear_programa(mundo, ejercicio)
    cuenta = cuenta_vigente(mundo, siembra["cargo_vigente"])
    programa = declarar(mundo, programa, cuenta, "100.00")
    programa = linea(mundo, programa, rubro, 1, "10.00")

    r = patch_con_version(mundo, f"{P}/rubros/{rubro['id']}", {"estado": "INACTIVO"}, rubro["version"])
    assert r.status_code == 200, r.text

    r = mundo.get(f"{P}/rubros?estado=ACTIVO", "ua", mundo.company_a)
    assert r.status_code == 200
    ids_activos = {item["id"] for item in r.json()["items"]}
    assert rubro["id"] not in ids_activos

    detalle = ver(mundo, programa)
    assert any(linea_actual["rubro_id"] == rubro["id"] for linea_actual in detalle["lineas"])

    r = accion(
        mundo,
        programa,
        "lineas",
        {"rubro_id": rubro["id"], "mes": 2, "monto": "10.00"},
    )
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_CASH_PROGRAM_INVALID"

    r = mundo.get(f"{P}/programas/{programa['id']}/opciones", "ua", mundo.company_a)
    assert r.status_code == 200
    ids_rubros = {item["id"] for item in r.json()["rubros"]}
    assert rubro["id"] not in ids_rubros


def test_rb06_filtro_tipo(mundo, gobierno):
    """RB-06: GET /rubros?tipo= devuelve solo el tipo pedido."""
    rubro_ingreso = crear_rubro(mundo, "INGRESO")
    rubro_desembolso = crear_rubro(mundo, "DESEMBOLSO")

    r = mundo.get(f"{P}/rubros?tipo=INGRESO", "ua", mundo.company_a)
    assert r.status_code == 200
    ids = {item["id"] for item in r.json()["items"]}
    assert rubro_ingreso["id"] in ids
    assert rubro_desembolso["id"] not in ids

    r = mundo.get(f"{P}/rubros?tipo=DESEMBOLSO", "ua", mundo.company_a)
    assert r.status_code == 200
    ids = {item["id"] for item in r.json()["items"]}
    assert rubro_desembolso["id"] in ids
    assert rubro_ingreso["id"] not in ids


def test_rb07_rubro_ajeno_no_encontrado(mundo, gobierno):
    """RB-07: PATCH de rubro de otra empresa responde 404 GOV_CASH_ITEM_NOT_FOUND."""
    rubro = crear_rubro(mundo, "INGRESO", usuario="ub", empresa=mundo.company_b)
    r = patch_con_version(
        mundo,
        f"{P}/rubros/{rubro['id']}",
        {"nombre": "No debería cambiar"},
        rubro["version"],
        empresa=mundo.company_a,
    )
    assert r.status_code == 404
    assert r.json()["code"] == "GOV_CASH_ITEM_NOT_FOUND"
