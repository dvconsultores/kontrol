import itertools
from datetime import timedelta
from decimal import Decimal

from app.modules.identity_access.mfa_policy import SENSITIVE, STANDARD, classify
from app.modules.setup.api import CATALOGO_DE_PERMISOS
from app.shared.audit_catalog import catalog
from tests.test_gov_ctl06_hallazgos import ANIO, _post
from tests.test_gov_tre01_cuentas import HOY, crear_cuenta, cuenta_vigente, eventos
from tests.tre02_ayudantes import (
    MOTIVO,
    P,
    accion,
    activar_programa,
    crear_programa,
    crear_rubro,
    cuenta_en_estado,
    declarar,
    delete_con_version,
    linea,
    patch_con_version,
    programa_vigente,
)

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos")

_ejercicios = itertools.count(ANIO)


def _ejercicio() -> int:
    return next(_ejercicios)


def test_pg01_capacidades():
    """PG-01 capacidades: permisos, MFA y catálogo."""
    assert CATALOGO_DE_PERMISOS["gobierno_caja"] == ["view", "manage", "activate"]
    assert classify(["gobierno_caja:activate"]) == SENSITIVE
    assert classify(["gobierno_caja:view"]) == STANDARD
    assert classify(["gobierno_caja:manage"]) == STANDARD

    catalogo = catalog()
    acciones = {
        ("GOV_CASH_ITEM_CREATED", "GovernmentCashItem"),
        ("GOV_CASH_ITEM_UPDATED", "GovernmentCashItem"),
        ("GOV_CASH_PROGRAM_CREATED", "GovernmentCashProgram"),
        ("GOV_CASH_PROGRAM_UPDATED", "GovernmentCashProgram"),
        ("GOV_CASH_PROGRAM_ACTIVATED", "GovernmentCashProgram"),
        ("GOV_CASH_PROGRAM_REVISED", "GovernmentCashProgram"),
        ("GOV_CASH_PROGRAM_DISCARDED", "GovernmentCashProgram"),
        ("GOV_CASH_PROGRAM_CLOSED", "GovernmentCashProgram"),
    }
    for clave in acciones:
        assert clave in catalogo, f"Falta {clave}"
        assert catalogo[clave].owner_spec == "gov-tre-02"


def test_pg02_alta(mundo, gobierno):
    """PG-02 alta: 201, BORRADOR, código PF-AAAA-VES, versión 1, historia CREADO."""
    ejercicio = _ejercicio()
    r = _post(
        mundo,
        f"{P}/programas",
        "ua",
        mundo.company_a,
        {"ejercicio": ejercicio, "moneda": "VES", "mes_inicial": 1},
    )
    assert r.status_code == 201, r.text
    detalle = r.json()
    assert detalle["estado"] == "BORRADOR"
    assert detalle["codigo"] == f"PF-{ejercicio}-VES"
    assert detalle["version"] == 1
    assert detalle["version_vista"] == 1
    assert detalle["version_vigente"] is None
    assert any(h["tipo"] == "CREADO" for h in detalle["historia"])

    evs = eventos(mundo, "GOV_CASH_PROGRAM_CREATED", detalle["id"])
    assert len(evs) == 1


def test_pg03_duplicado(mundo, gobierno):
    """PG-03 duplicado 409 GOV_CASH_PROGRAM_DUPLICATE; otra moneda y otra empresa sí."""
    ejercicio = _ejercicio()
    crear_programa(mundo, ejercicio, moneda="VES")
    r = _post(
        mundo,
        f"{P}/programas",
        "ua",
        mundo.company_a,
        {"ejercicio": ejercicio, "moneda": "VES", "mes_inicial": 1},
    )
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_CASH_PROGRAM_DUPLICATE"

    r2 = _post(
        mundo,
        f"{P}/programas",
        "ua",
        mundo.company_a,
        {"ejercicio": ejercicio, "moneda": "USD", "mes_inicial": 1},
    )
    assert r2.status_code == 201, r2.text

    r3 = _post(
        mundo,
        f"{P}/programas",
        "ub",
        mundo.company_b,
        {"ejercicio": ejercicio, "moneda": "VES", "mes_inicial": 1},
    )
    assert r3.status_code == 201, r3.text

    # descartar programa company_a y crear otro igual
    programa = crear_programa(mundo, ejercicio, moneda="EUR")
    detalle = accion(mundo, programa, "descartar", {})
    assert detalle.status_code == 200, detalle.text
    r4 = _post(
        mundo,
        f"{P}/programas",
        "ua",
        mundo.company_a,
        {"ejercicio": ejercicio, "moneda": "EUR", "mes_inicial": 1},
    )
    assert r4.status_code == 201, r4.text


def test_pg04_validaciones(mundo, gobierno):
    """PG-04 validaciones: mes 0 y 13, moneda GBP, ejercicio anterior, company_id."""
    ejercicio = _ejercicio()
    for mes_inicial in (0, 13):
        r = _post(
            mundo,
            f"{P}/programas",
            "ua",
            mundo.company_a,
            {"ejercicio": ejercicio, "moneda": "VES", "mes_inicial": mes_inicial},
        )
        assert r.status_code == 422, r.text
        assert r.json()["code"] == "VALIDATION_ERROR"

    r = _post(
        mundo,
        f"{P}/programas",
        "ua",
        mundo.company_a,
        {"ejercicio": ejercicio, "moneda": "GBP", "mes_inicial": 1},
    )
    assert r.status_code == 422
    assert r.json()["code"] == "VALIDATION_ERROR"

    ejercicio_anterior = ANIO - 2
    r = _post(
        mundo,
        f"{P}/programas",
        "ua",
        mundo.company_a,
        {"ejercicio": ejercicio_anterior, "moneda": "VES", "mes_inicial": 1},
    )
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_CASH_PROGRAM_INVALID"

    r = _post(
        mundo,
        f"{P}/programas",
        "ua",
        mundo.company_a,
        {
            "ejercicio": ejercicio,
            "moneda": "VES",
            "mes_inicial": 1,
            "company_id": "00000000-0000-0000-0000-000000000001",
        },
    )
    assert r.status_code == 422
    assert r.json()["code"] == "VALIDATION_ERROR"


def test_pg05_declaracion(mundo, gobierno, siembra):
    """PG-05 declaración: 201 con cuenta vigente; detalle trae cuenta, banco, monto."""
    ejercicio = _ejercicio()
    cuenta = cuenta_vigente(mundo, siembra["cargo_vigente"], moneda="VES")
    programa = crear_programa(mundo, ejercicio)
    detalle = declarar(mundo, programa, cuenta, "1000.00")
    assert detalle["estado"] == "BORRADOR"
    assert detalle["declaraciones"][0]["cuenta_id"] == cuenta["id"]
    assert detalle["declaraciones"][0]["cuenta_codigo"] == cuenta["codigo"]
    assert detalle["declaraciones"][0]["cuenta_denominacion"]
    assert detalle["declaraciones"][0]["banco_nombre"]
    assert detalle["declaraciones"][0]["monto"] == "1000.00"
    assert detalle["declaraciones"][0]["fecha_corte"] == HOY.isoformat()
    assert detalle["declaraciones"][0]["fundamento"] == MOTIVO
    assert detalle["declaraciones"][0]["declarado_por"]
    assert detalle["declaraciones"][0]["declarado_en"]
    assert Decimal(detalle["disponibilidad_inicial"]) == Decimal("1000.00")

    cuenta2 = cuenta_vigente(mundo, siembra["cargo_vigente"], moneda="VES")
    detalle = declarar(mundo, detalle, cuenta2, "500.00")
    assert len(detalle["declaraciones"]) == 2
    assert Decimal(detalle["disponibilidad_inicial"]) == Decimal("1500.00")


def test_pg06_cuenta_no_valida(mundo, gobierno, siembra):
    """PG-06 cuenta no válida con el mismo mensaje: otra moneda, en borrador, inactiva, cerrada, company_b, uuid."""
    ejercicio = _ejercicio()
    cuenta_borrador = crear_cuenta(mundo, usuario="ua", empresa=mundo.company_a, moneda="VES")
    cuenta_usd = cuenta_vigente(mundo, siembra["cargo_vigente"], moneda="USD")
    cuenta_inactiva = cuenta_en_estado(
        mundo, siembra["cargo_vigente"], "INACTIVA", moneda="VES", usuario="ua", empresa=mundo.company_a
    )
    cuenta_cerrada = cuenta_en_estado(
        mundo, siembra["cargo_vigente"], "CERRADA", moneda="VES", usuario="ua", empresa=mundo.company_a
    )
    cuenta_company_b = crear_cuenta(mundo, usuario="ub", empresa=mundo.company_b)
    programa = crear_programa(mundo, ejercicio)
    cuentas = [
        cuenta_usd,
        cuenta_borrador,
        cuenta_inactiva,
        cuenta_cerrada,
        cuenta_company_b,
        {"id": "00000000-0000-0000-0000-000000000000"},
    ]
    mensajes = set()
    for cuenta in cuentas:
        r = _post(
            mundo,
            f"{P}/programas/{programa['id']}/declaraciones",
            "ua",
            mundo.company_a,
            {
                "cuenta_id": cuenta["id"],
                "monto": "100.00",
                "fecha_corte": HOY.isoformat(),
                "fundamento": MOTIVO,
            },
            version=programa["version"],
        )
        assert r.status_code == 422, r.text
        assert r.json()["code"] == "GOV_CASH_PROGRAM_INVALID"
        mensajes.add(r.json()["message"])
    assert len(mensajes) == 1


def test_pg07_declaracion_validaciones(mundo, gobierno, siembra):
    """PG-07 declaración: repetida 409; monto negativo, fecha futura y fundamento corto; monto 0 y quitar se aceptan."""
    ejercicio = _ejercicio()
    cuenta = cuenta_vigente(mundo, siembra["cargo_vigente"], moneda="VES")
    programa = crear_programa(mundo, ejercicio)
    detalle = declarar(mundo, programa, cuenta, "100.00")
    r = _post(
        mundo,
        f"{P}/programas/{detalle['id']}/declaraciones",
        "ua",
        mundo.company_a,
        {
            "cuenta_id": cuenta["id"],
            "monto": "200.00",
            "fecha_corte": HOY.isoformat(),
            "fundamento": MOTIVO,
        },
        version=detalle["version"],
    )
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_CASH_DECLARATION_DUPLICATE"

    for monto in ("-1.00", None):
        r = _post(
            mundo,
            f"{P}/programas/{detalle['id']}/declaraciones",
            "ua",
            mundo.company_a,
            {
                "cuenta_id": cuenta["id"],
                "monto": monto,
                "fecha_corte": HOY.isoformat(),
                "fundamento": MOTIVO,
            },
            version=detalle["version"],
        )
        assert r.status_code == 422
        assert r.json()["code"] == "VALIDATION_ERROR"

    fecha_futura = (HOY + timedelta(days=1)).isoformat()
    r = _post(
        mundo,
        f"{P}/programas/{detalle['id']}/declaraciones",
        "ua",
        mundo.company_a,
        {
            "cuenta_id": cuenta["id"],
            "monto": "100.00",
            "fecha_corte": fecha_futura,
            "fundamento": MOTIVO,
        },
        version=detalle["version"],
    )
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_CASH_PROGRAM_INVALID"

    r = _post(
        mundo,
        f"{P}/programas/{detalle['id']}/declaraciones",
        "ua",
        mundo.company_a,
        {
            "cuenta_id": cuenta["id"],
            "monto": "100.00",
            "fecha_corte": HOY.isoformat(),
            "fundamento": "corto",
        },
        version=detalle["version"],
    )
    assert r.status_code == 422
    assert r.json()["code"] == "VALIDATION_ERROR"

    cuenta2 = cuenta_vigente(mundo, siembra["cargo_vigente"], moneda="VES")
    detalle = declarar(mundo, detalle, cuenta2, "0.00")
    assert Decimal(detalle["disponibilidad_inicial"]) == Decimal("100.00")
    did = detalle["declaraciones"][0]["id"]
    r = delete_con_version(
        mundo,
        f"{P}/programas/{detalle['id']}/declaraciones/{did}",
        detalle["version"],
    )
    assert r.status_code == 200, r.text
    detalle = r.json()
    assert len(detalle["declaraciones"]) == 1
    assert detalle["declaraciones"][0]["cuenta_id"] == cuenta2["id"]


def test_pg08_linea(mundo, gobierno, siembra):
    """PG-08 línea: alta, cambio, baja; duplicada 409; mes anterior, montos y rubro inválidos."""
    ejercicio = _ejercicio()
    cuenta = cuenta_vigente(mundo, siembra["cargo_vigente"], moneda="VES")
    rubro = crear_rubro(mundo, "INGRESO")
    rubro_inactivo = crear_rubro(mundo, "INGRESO")
    r = patch_con_version(
        mundo,
        f"{P}/rubros/{rubro_inactivo['id']}",
        {"estado": "INACTIVO"},
        rubro_inactivo["version"],
    )
    assert r.status_code == 200, r.text
    rubro_otra_empresa = crear_rubro(
        mundo, "INGRESO", usuario="ub", empresa=mundo.company_b
    )
    programa = crear_programa(mundo, ejercicio)
    detalle = declarar(mundo, programa, cuenta, "1000.00")

    detalle = linea(mundo, detalle, rubro, 1, "500.00")
    assert detalle["lineas"][0]["monto"] == "500.00"

    r = _post(
        mundo,
        f"{P}/programas/{detalle['id']}/lineas",
        "ua",
        mundo.company_a,
        {"rubro_id": rubro["id"], "mes": 1, "monto": "600.00"},
        version=detalle["version"],
    )
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_CASH_LINE_DUPLICATE"

    r = _post(
        mundo,
        f"{P}/programas/{detalle['id']}/lineas",
        "ua",
        mundo.company_a,
        {"rubro_id": rubro["id"], "mes": 0, "monto": "100.00"},
        version=detalle["version"],
    )
    assert r.status_code == 422
    assert r.json()["code"] == "VALIDATION_ERROR"

    for monto in ("0.00", "-10.00", "10.001"):
        r = _post(
            mundo,
            f"{P}/programas/{detalle['id']}/lineas",
            "ua",
            mundo.company_a,
            {"rubro_id": rubro["id"], "mes": 2, "monto": monto},
            version=detalle["version"],
        )
        assert r.status_code == 422
        assert r.json()["code"] == "VALIDATION_ERROR"

    for rubro_invalido in (rubro_inactivo, rubro_otra_empresa):
        r = _post(
            mundo,
            f"{P}/programas/{detalle['id']}/lineas",
            "ua",
            mundo.company_a,
            {"rubro_id": rubro_invalido["id"], "mes": 2, "monto": "10.00"},
            version=detalle["version"],
        )
        assert r.status_code == 422
        assert r.json()["code"] == "GOV_CASH_PROGRAM_INVALID"

    lid = detalle["lineas"][0]["id"]
    r = patch_con_version(
        mundo,
        f"{P}/programas/{detalle['id']}/lineas/{lid}",
        {"monto": "700.00"},
        detalle["version"],
    )
    assert r.status_code == 200, r.text
    detalle = r.json()
    assert detalle["lineas"][0]["monto"] == "700.00"

    r = delete_con_version(
        mundo,
        f"{P}/programas/{detalle['id']}/lineas/{lid}",
        detalle["version"],
    )
    assert r.status_code == 200, r.text
    assert len(r.json()["lineas"]) == 0

    programa_otro = crear_programa(mundo, _ejercicio(), mes_inicial=3)
    detalle_otro = declarar(mundo, programa_otro, cuenta, "1000.00")
    r = _post(
        mundo,
        f"{P}/programas/{detalle_otro['id']}/lineas",
        "ua",
        mundo.company_a,
        {"rubro_id": rubro["id"], "mes": 2, "monto": "10.00"},
        version=detalle_otro["version"],
    )
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_CASH_PROGRAM_INVALID"


def test_pg09_formula(mundo, gobierno, siembra):
    """PG-09 fórmula: inicial, ingresos, desembolsos y finales exactos."""
    ejercicio = _ejercicio()
    cuenta = cuenta_vigente(mundo, siembra["cargo_vigente"], moneda="VES")
    rubro_ingreso = crear_rubro(mundo, "INGRESO")
    rubro_desembolso = crear_rubro(mundo, "DESEMBOLSO")
    programa = crear_programa(mundo, ejercicio)
    detalle = declarar(mundo, programa, cuenta, "1000.00")
    detalle = linea(mundo, detalle, rubro_ingreso, 1, "500.00")
    detalle = linea(mundo, detalle, rubro_desembolso, 1, "300.00")
    detalle = linea(mundo, detalle, rubro_desembolso, 3, "0.10")

    meses = detalle["meses"]
    assert len(meses) == 12
    assert Decimal(meses[0]["inicial"]) == Decimal("1000.00")
    assert Decimal(meses[0]["ingresos"]) == Decimal("500.00")
    assert Decimal(meses[0]["desembolsos"]) == Decimal("300.00")
    assert Decimal(meses[0]["final"]) == Decimal("1200.00")
    assert Decimal(meses[1]["inicial"]) == Decimal("1200.00")
    assert Decimal(meses[1]["ingresos"]) == Decimal("0.00")
    assert Decimal(meses[1]["desembolsos"]) == Decimal("0.00")
    assert Decimal(meses[2]["inicial"]) == Decimal("1200.00")
    assert Decimal(meses[2]["desembolsos"]) == Decimal("0.10")
    assert Decimal(meses[2]["final"]) == Decimal("1199.90")


def test_pg10_centimos(mundo, gobierno, siembra):
    """PG-10 céntimos: tres ingresos suman exactamente 0.35 más lo declarado."""
    ejercicio = _ejercicio()
    cuenta = cuenta_vigente(mundo, siembra["cargo_vigente"], moneda="VES")
    rubro_a = crear_rubro(mundo, "INGRESO")
    rubro_b = crear_rubro(mundo, "INGRESO")
    rubro_c = crear_rubro(mundo, "INGRESO")
    programa = crear_programa(mundo, ejercicio)
    detalle = declarar(mundo, programa, cuenta, "1000.00")
    detalle = linea(mundo, detalle, rubro_a, 1, "0.10")
    detalle = linea(mundo, detalle, rubro_b, 1, "0.20")
    detalle = linea(mundo, detalle, rubro_c, 1, "0.05")
    meses = detalle["meses"]
    assert Decimal(meses[0]["ingresos"]) == Decimal("0.35")
    assert Decimal(meses[0]["inicial"]) == Decimal("1000.00")
    assert Decimal(meses[0]["final"]) == Decimal("1000.35")


def test_pg11_deficit(mundo, gobierno, siembra):
    """PG-11 déficit: mes con final negativo y programa se activa."""
    ejercicio = _ejercicio()
    cuenta = cuenta_vigente(mundo, siembra["cargo_vigente"], moneda="VES")
    rubro = crear_rubro(mundo, "DESEMBOLSO")
    programa = crear_programa(mundo, ejercicio)
    detalle = declarar(mundo, programa, cuenta, "100.00")
    detalle = linea(mundo, detalle, rubro, 1, "200.00")
    meses = detalle["meses"]
    assert any(Decimal(m["final"]) < 0 for m in meses)
    assert any(m["deficit"] for m in meses)
    assert detalle["hay_deficit"] is True
    detalle = activar_programa(mundo, detalle)
    assert detalle["estado"] == "VIGENTE"


def test_pg12_mes_inicial(mundo, gobierno, siembra):
    """PG-12 mes inicial 7: meses empieza en 7 y hay 6 meses."""
    ejercicio = _ejercicio()
    cuenta = cuenta_vigente(mundo, siembra["cargo_vigente"], moneda="VES")
    rubro = crear_rubro(mundo, "INGRESO")
    programa = crear_programa(mundo, ejercicio, mes_inicial=7)
    detalle = declarar(mundo, programa, cuenta, "100.00")
    detalle = linea(mundo, detalle, rubro, 7, "10.00")
    meses = detalle["meses"]
    assert len(meses) == 6
    assert meses[0]["mes"] == 7
    assert meses[-1]["mes"] == 12


def test_pg13_activar(mundo, gobierno, siembra):
    """PG-13 activar: MFA, estado VIGENTE, version_vigente 1, historia y evento."""
    ejercicio = _ejercicio()
    cuenta = cuenta_vigente(mundo, siembra["cargo_vigente"], moneda="VES")
    rubro = crear_rubro(mundo, "INGRESO")
    programa = crear_programa(mundo, ejercicio)
    detalle = declarar(mundo, programa, cuenta, "100.00")
    detalle = linea(mundo, detalle, rubro, 1, "10.00")
    detalle = activar_programa(mundo, detalle)
    assert detalle["estado"] == "VIGENTE"
    assert detalle["version_vigente"] == 1
    assert detalle["versiones"][0]["activada_por"]
    assert detalle["versiones"][0]["activada_en"]
    assert any(h["tipo"] == "ACTIVADO" for h in detalle["historia"])
    evs = eventos(mundo, "GOV_CASH_PROGRAM_ACTIVATED", detalle["id"])
    assert len(evs) == 1
    assert classify(["gobierno_caja:activate"]) == SENSITIVE


def test_pg14_sin_preparar(mundo, gobierno, siembra):
    """PG-14 sin preparar: 409 GOV_CASH_PROGRAM_NOT_READY con details.faltan."""
    ejercicio = _ejercicio()
    cuenta = cuenta_vigente(mundo, siembra["cargo_vigente"], moneda="VES")
    programa = crear_programa(mundo, ejercicio)
    r = _post(
        mundo,
        f"{P}/programas/{programa['id']}/activar",
        "ua",
        mundo.company_a,
        {},
        version=programa["version"],
    )
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_CASH_PROGRAM_NOT_READY"
    faltan = r.json()["details"]["faltan"]
    assert "declaracion" in faltan
    assert "linea" in faltan

    detalle = declarar(mundo, programa, cuenta, "100.00")
    r = _post(
        mundo,
        f"{P}/programas/{detalle['id']}/activar",
        "ua",
        mundo.company_a,
        {},
        version=detalle["version"],
    )
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_CASH_PROGRAM_NOT_READY"
    assert r.json()["details"]["faltan"] == ["linea"]


def test_pg15_tras_activar(mundo, gobierno, siembra):
    """PG-15 tras activar, declaraciones y líneas rechazadas con 409 GOV_CASH_PROGRAM_INVALID_STATE."""
    ejercicio = _ejercicio()
    cuenta = cuenta_vigente(mundo, siembra["cargo_vigente"], moneda="VES")
    rubro = crear_rubro(mundo, "INGRESO")
    programa = crear_programa(mundo, ejercicio)
    detalle = declarar(mundo, programa, cuenta, "100.00")
    detalle = linea(mundo, detalle, rubro, 1, "10.00")
    detalle = activar_programa(mundo, detalle)

    r = _post(
        mundo,
        f"{P}/programas/{detalle['id']}/declaraciones",
        "ua",
        mundo.company_a,
        {
            "cuenta_id": cuenta["id"],
            "monto": "50.00",
            "fecha_corte": HOY.isoformat(),
            "fundamento": MOTIVO,
        },
        version=detalle["version"],
    )
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_CASH_PROGRAM_INVALID_STATE"

    r = _post(
        mundo,
        f"{P}/programas/{detalle['id']}/lineas",
        "ua",
        mundo.company_a,
        {"rubro_id": rubro["id"], "mes": 2, "monto": "20.00"},
        version=detalle["version"],
    )
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_CASH_PROGRAM_INVALID_STATE"


def test_pg16_listado(mundo, gobierno, siembra):
    """PG-16 listado: filtros ejercicio, moneda, estado; resumen no cambia al filtrar."""
    ejercicio1 = _ejercicio()
    ejercicio2 = _ejercicio()
    crear_programa(mundo, ejercicio1, moneda="VES")
    crear_programa(mundo, ejercicio2, moneda="USD")
    detalle_vigente = programa_vigente(mundo, siembra["cargo_vigente"], _ejercicio())

    r = mundo.get(f"{P}/programas", "ua", mundo.company_a)
    assert r.status_code == 200
    base = r.json()
    assert len(base["items"]) >= 3
    resumen_base = base["resumen"]

    r = mundo.get(
        f"{P}/programas?ejercicio={ejercicio1}&moneda=VES&estado=BORRADOR",
        "ua",
        mundo.company_a,
    )
    assert r.status_code == 200
    filtrado = r.json()
    assert len(filtrado["items"]) == 1
    assert filtrado["items"][0]["ejercicio"] == ejercicio1
    assert filtrado["items"][0]["moneda"] == "VES"
    assert filtrado["items"][0]["estado"] == "BORRADOR"
    assert filtrado["resumen"] == resumen_base

    r = mundo.get(
        f"{P}/programas?estado=VIGENTE",
        "ua",
        mundo.company_a,
    )
    assert r.status_code == 200
    vigentes = r.json()["items"]
    ids_vigentes = [item["id"] for item in vigentes]
    assert detalle_vigente["id"] in ids_vigentes
    assert all(item["estado"] == "VIGENTE" for item in vigentes)
    assert "disponibilidad_inicial" in vigentes[0]


def test_pg17_opciones(mundo, gobierno, siembra):
    """PG-17 opciones: cuentas vigentes solo de la moneda; rubros activos solo."""
    ejercicio = _ejercicio()
    cuenta_ves = cuenta_vigente(mundo, siembra["cargo_vigente"], moneda="VES")
    cuenta_usd = cuenta_vigente(mundo, siembra["cargo_vigente"], moneda="USD")
    rubro_activo = crear_rubro(mundo, "INGRESO")
    rubro_inactivo = crear_rubro(mundo, "INGRESO")
    r = patch_con_version(
        mundo,
        f"{P}/rubros/{rubro_inactivo['id']}",
        {"estado": "INACTIVO"},
        rubro_inactivo["version"],
    )
    assert r.status_code == 200, r.text
    programa = crear_programa(mundo, ejercicio, moneda="VES")

    r = mundo.get(f"{P}/programas/{programa['id']}/opciones", "ua", mundo.company_a)
    assert r.status_code == 200
    opciones = r.json()
    cuentas_ids = [c["id"] for c in opciones["cuentas"]]
    assert cuenta_ves["id"] in cuentas_ids
    assert cuenta_usd["id"] not in cuentas_ids
    rubros_ids = [i["id"] for i in opciones["rubros"]]
    assert rubro_activo["id"] in rubros_ids
    assert rubro_inactivo["id"] not in rubros_ids


def test_pg18_monedas(mundo, gobierno, siembra):
    """PG-18 monedas: dos programas USD y VES no se mezclan."""
    ejercicio_ves = _ejercicio()
    ejercicio_usd = _ejercicio()
    cuenta_ves = cuenta_vigente(mundo, siembra["cargo_vigente"], moneda="VES")
    rubro_ves = crear_rubro(mundo, "INGRESO")
    programa_ves = crear_programa(mundo, ejercicio_ves, moneda="VES")
    detalle_ves = declarar(mundo, programa_ves, cuenta_ves, "100.00")
    detalle_ves = linea(mundo, detalle_ves, rubro_ves, 1, "20.00")

    cuenta_usd = cuenta_vigente(mundo, siembra["cargo_vigente"], moneda="USD")
    rubro_usd = crear_rubro(mundo, "INGRESO")
    programa_usd = crear_programa(mundo, ejercicio_usd, moneda="USD")
    detalle_usd = declarar(mundo, programa_usd, cuenta_usd, "200.00")
    detalle_usd = linea(mundo, detalle_usd, rubro_usd, 1, "30.00")

    assert Decimal(detalle_ves["disponibilidad_inicial"]) == Decimal("100.00")
    assert Decimal(detalle_usd["disponibilidad_inicial"]) == Decimal("200.00")
    assert detalle_ves["moneda"] == "VES"
    assert detalle_usd["moneda"] == "USD"
    assert Decimal(detalle_ves["meses"][0]["final"]) == Decimal("120.00")
    assert Decimal(detalle_usd["meses"][0]["final"]) == Decimal("230.00")
    ids_ves = {linea_ves["id"] for linea_ves in detalle_ves["lineas"]}
    ids_usd = {linea_usd["id"] for linea_usd in detalle_usd["lineas"]}
    assert ids_ves.isdisjoint(ids_usd)
