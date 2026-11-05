import itertools
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from tests.test_gov_ctl06_hallazgos import ANIO, _post
from tests.test_gov_tre01_cuentas import HOY, cuenta_vigente, eventos
from tests.tre02_ayudantes import (
    MOTIVO,
    accion,
    activar_programa,
    crear_programa,
    crear_rubro,
    declarar,
    delete_con_version,
    fijar_hoy,
    linea,
    patch_con_version,
    programa_listo,
    programa_vigente,
    reprogramar,
    ver,
)

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos")

_ejercicios = itertools.count(ANIO)


def _ejercicio() -> int:
    valor = next(_ejercicios)
    assert valor <= ANIO + 40
    return valor


def _programa_vigente(mundo, cargo_id, ejercicio=None, **kwargs):
    ejercicio = ejercicio or _ejercicio()
    return programa_vigente(mundo, cargo_id, ejercicio, **kwargs)


def _fecha_ejercicio(ejercicio: int, dia=15, mes=6) -> date:
    return date(ejercicio, mes, dia)


def _rubro_desembolso(mundo, **kwargs):
    return crear_rubro(mundo, "DESEMBOLSO", **kwargs)


def _linea_de_mes(detalle, mes: int):
    return next(item for item in detalle["lineas"] if item["mes"] == mes)


def test_rv01_reprogramar_con_motivo(mundo, gobierno, siembra, monkeypatch):
    """RV-01 reprogramar con motivo."""
    programa = _programa_vigente(mundo, siembra["cargo_vigente"])
    fijar_hoy(monkeypatch, _fecha_ejercicio(programa["ejercicio"]))

    r = accion(
        mundo,
        programa,
        "reprogramar",
        {"motivo": MOTIVO},
    )
    assert r.status_code == 201, r.text
    detalle = r.json()
    assert detalle["borrador_numero"] == 2
    assert detalle["version_vigente"] == 1
    assert detalle["version_vista"] == 2

    original = ver(mundo, programa, numero_version=1)
    assert [
        (linea_original["rubro_id"], linea_original["mes"], Decimal(linea_original["monto"]))
        for linea_original in original["lineas"]
    ] == [
        (linea_detalle["rubro_id"], linea_detalle["mes"], Decimal(linea_detalle["monto"]))
        for linea_detalle in detalle["lineas"]
    ]

    historia_reprogramado = [
        h for h in detalle["historia"] if h["tipo"] == "REPROGRAMADO"
    ]
    assert len(historia_reprogramado) == 1

    eventos_revisados = eventos(mundo, "GOV_CASH_PROGRAM_REVISED", programa["id"])
    assert len(eventos_revisados) == 1


def test_rv02_motivo_y_estado_rechazado(mundo, gobierno, siembra, monkeypatch):
    """RV-02 motivo corto, borrador abierto y estado inválido."""
    programa = _programa_vigente(mundo, siembra["cargo_vigente"])
    fijar_hoy(monkeypatch, _fecha_ejercicio(programa["ejercicio"]))

    r = accion(mundo, programa, "reprogramar", {"motivo": "corto"})
    assert r.status_code == 422
    assert r.json()["code"] == "VALIDATION_ERROR"

    r = accion(mundo, programa, "reprogramar", {})
    assert r.status_code == 422
    assert r.json()["code"] == "VALIDATION_ERROR"

    detalle = reprogramar(mundo, programa)
    assert detalle["borrador_numero"] == 2

    r = accion(mundo, detalle, "reprogramar", {"motivo": MOTIVO})
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_CASH_PROGRAM_DRAFT_OPEN"

    borrador = crear_programa(mundo, _ejercicio(), moneda="USD", mes_inicial=1)
    r = accion(mundo, borrador, "reprogramar", {"motivo": MOTIVO})
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_CASH_PROGRAM_INVALID_STATE"


def test_rv03_mes_pasado_en_reprogramacion(mundo, gobierno, siembra, monkeypatch):
    """RV-03 mes pasado: alta, cambio y baja de línea de mayo."""
    ejercicio = _ejercicio()
    programa = crear_programa(mundo, ejercicio, mes_inicial=1)

    cuenta = cuenta_vigente(
        mundo, siembra["cargo_vigente"], usuario="ua", empresa=mundo.company_a
    )
    programa = declarar(mundo, programa, cuenta, "1000.00", usuario="ua", empresa=mundo.company_a)

    rubro_ingreso = crear_rubro(
        mundo, "INGRESO", usuario="ua", empresa=mundo.company_a
    )
    programa = linea(
        mundo, programa, rubro_ingreso, 5, "500.00", usuario="ua", empresa=mundo.company_a
    )

    programa = activar_programa(mundo, programa)
    fijar_hoy(monkeypatch, _fecha_ejercicio(ejercicio))
    detalle = reprogramar(mundo, programa)
    assert detalle["borrador_numero"] == 2

    linea_mayo = _linea_de_mes(detalle, 5)

    rubro_alta_mayo = crear_rubro(
        mundo, "DESEMBOLSO", usuario="ua", empresa=mundo.company_a
    )
    r = accion(
        mundo,
        detalle,
        "lineas",
        {"rubro_id": rubro_alta_mayo["id"], "mes": 5, "monto": "10.00"},
    )
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_CASH_PROGRAM_PAST_MONTH"

    url = f"/gobierno/tesoreria/programas/{detalle['id']}/lineas/{linea_mayo['id']}"
    r = patch_con_version(
        mundo, url, {"monto": "20.00"}, detalle["version"], usuario="ua", empresa=mundo.company_a
    )
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_CASH_PROGRAM_PAST_MONTH"

    url = f"/gobierno/tesoreria/programas/{detalle['id']}/lineas/{linea_mayo['id']}"
    r = delete_con_version(
        mundo, url, detalle["version"], usuario="ua", empresa=mundo.company_a
    )
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_CASH_PROGRAM_PAST_MONTH"

    # Junio y julio se admiten.
    rubro_desembolso = _rubro_desembolso(mundo)
    r = accion(
        mundo,
        detalle,
        "lineas",
        {"rubro_id": rubro_desembolso["id"], "mes": 6, "monto": "10.00"},
    )
    assert r.status_code == 201, r.text
    detalle = r.json()

    r = accion(
        mundo,
        detalle,
        "lineas",
        {"rubro_id": rubro_desembolso["id"], "mes": 7, "monto": "10.00"},
    )
    assert r.status_code == 201, r.text


def test_rv04_declaracion_fija_en_reprogramacion(mundo, gobierno, siembra, monkeypatch):
    """RV-04 declaración fija: alta y baja rechazadas."""
    programa = _programa_vigente(mundo, siembra["cargo_vigente"])
    fijar_hoy(monkeypatch, _fecha_ejercicio(programa["ejercicio"]))
    detalle = reprogramar(mundo, programa)

    otra_cuenta = cuenta_vigente(mundo, siembra["cargo_vigente"], empresa=mundo.company_a)
    r = accion(
        mundo,
        detalle,
        "declaraciones",
        {
            "cuenta_id": otra_cuenta["id"],
            "monto": "100.00",
            "fecha_corte": date(programa["ejercicio"], 6, 15).isoformat(),
            "fundamento": MOTIVO,
        },
    )
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_CASH_PROGRAM_INVALID_STATE"

    declaracion_id = detalle["declaraciones"][0]["id"]
    url = f"/gobierno/tesoreria/programas/{detalle['id']}/declaraciones/{declaracion_id}"
    r = mundo.client.delete(
        f"/api/v1{url}",
        headers=mundo.como("ua", mundo.company_a) | {"If-Match": str(detalle["version"])},
    )
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_CASH_PROGRAM_INVALID_STATE"

    vista = ver(mundo, detalle)
    assert Decimal(vista["disponibilidad_inicial"]) == Decimal(
        detalle["disponibilidad_inicial"]
    )


def test_rv05_activar_reprogramacion(mundo, gobierno, siembra, monkeypatch):
    """RV-05 activar la versión 2."""
    programa = _programa_vigente(
        mundo, siembra["cargo_vigente"]
    )
    fijar_hoy(monkeypatch, _fecha_ejercicio(programa["ejercicio"]))
    detalle = reprogramar(mundo, programa)

    rubro = _rubro_desembolso(mundo)
    respuesta = accion(
        mundo,
        detalle,
        "lineas",
        {"rubro_id": rubro["id"], "mes": 6, "monto": "333.00"},
    )
    assert respuesta.status_code == 201, respuesta.text
    detalle = respuesta.json()

    activado = accion(mundo, detalle, "activar", {})
    assert activado.status_code == 200, activado.text
    detalle = activado.json()
    assert detalle["version_vigente"] == 2
    assert detalle["borrador_numero"] is None

    version_1 = ver(mundo, programa, numero_version=1)
    version_2 = ver(mundo, programa, numero_version=2)
    assert version_1["versiones"][0]["estado"] == "SUPERADA"
    assert [linea_uno["mes"] for linea_uno in version_1["lineas"]] == [1]
    assert [linea_dos["mes"] for linea_dos in version_2["lineas"]] == [1, 6]
    assert Decimal(version_1["meses"][5]["desembolsos"]) == Decimal("0.00")
    assert Decimal(version_2["meses"][5]["desembolsos"]) == Decimal("333.00")


def test_rv06_version_inexistente(mundo, gobierno, siembra):
    """RV-06 versión inexistente en la consulta."""
    programa = _programa_vigente(mundo, siembra["cargo_vigente"])
    r = mundo.get(
        f"/gobierno/tesoreria/programas/{programa['id']}?version=99",
        "ua",
        mundo.company_a,
    )
    assert r.status_code == 404
    assert r.json()["code"] == "GOV_CASH_PROGRAM_NOT_FOUND"


def test_rv07_descartar_borrador_y_reprogramar_de_nuevo(mundo, gobierno, siembra, monkeypatch):
    """RV-07 descartar el borrador 2 y nace la versión 3."""
    programa = _programa_vigente(mundo, siembra["cargo_vigente"])
    fijar_hoy(monkeypatch, _fecha_ejercicio(programa["ejercicio"]))
    detalle = reprogramar(mundo, programa)

    r = accion(mundo, detalle, "descartar", {})
    assert r.status_code == 200, r.text
    detalle = r.json()
    assert detalle["version_vigente"] == 1
    assert detalle["estado"] == "VIGENTE"
    assert detalle["versiones"][1]["estado"] == "DESCARTADA"
    historia_descartado = [
        h for h in detalle["historia"] if h["tipo"] == "DESCARTADO"
    ]
    assert len(historia_descartado) == 1

    eventos_descartados = eventos(mundo, "GOV_CASH_PROGRAM_DISCARDED", programa["id"])
    assert len(eventos_descartados) == 1

    detalle = reprogramar(mundo, detalle)
    assert detalle["borrador_numero"] == 3


def test_rv08_descartar_primera_version(mundo, gobierno, siembra):
    """RV-08 descartar la versión 1 deja el programa DESCARTADO."""
    programa = crear_programa(mundo, _ejercicio())

    r = accion(mundo, programa, "descartar", {})
    assert r.status_code == 200, r.text
    detalle = r.json()
    assert detalle["estado"] == "DESCARTADO"
    assert detalle["versiones"][0]["estado"] == "DESCARTADA"


def test_rv09_ejercicio_terminado(mundo, gobierno, siembra, monkeypatch):
    """RV-09 ejercicio terminado: reprogramar rechazado."""
    programa = _programa_vigente(mundo, siembra["cargo_vigente"])
    fijar_hoy(monkeypatch, date(programa["ejercicio"] + 1, 1, 10))

    r = accion(mundo, programa, "reprogramar", {"motivo": MOTIVO})
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_CASH_PROGRAM_EXERCISE_ENDED"


def test_rv10_ejercicio_futuro_sin_mes_pasado(mundo, gobierno, siembra, monkeypatch):
    """RV-10 ejercicio futuro: ningún mes es pasado."""
    ejercicio = _ejercicio()
    programa = programa_listo(mundo, siembra["cargo_vigente"], ejercicio)
    detalle = activar_programa(mundo, programa)
    fijar_hoy(monkeypatch, _fecha_ejercicio(ejercicio - 1))

    detalle = reprogramar(mundo, detalle)
    assert detalle["borrador_numero"] == 2

    rubro = _rubro_desembolso(mundo)
    r = accion(
        mundo,
        detalle,
        "lineas",
        {"rubro_id": rubro["id"], "mes": 1, "monto": "10.00"},
    )
    assert r.status_code == 201, r.text


def test_rv11_cuenta_cerrada_no_altera_declaracion(mundo, gobierno, siembra, monkeypatch):
    """RV-11 cuenta cerrada después de activar no altera la declaración."""
    ejercicio = _ejercicio()
    cuenta = cuenta_vigente(
        mundo,
        siembra["cargo_vigente"],
        usuario="ua",
        empresa=mundo.company_a,
    )
    rubro = crear_rubro(
        mundo, "INGRESO", usuario="ua", empresa=mundo.company_a
    )

    programa = crear_programa(
        mundo, ejercicio, mes_inicial=1, usuario="ua", empresa=mundo.company_a
    )
    programa = declarar(mundo, programa, cuenta, "1000.00", usuario="ua", empresa=mundo.company_a)
    programa = linea(mundo, programa, rubro, 1, "500.00", usuario="ua", empresa=mundo.company_a)
    programa = activar_programa(mundo, programa)

    r = _post(
        mundo,
        f"/gobierno/tesoreria/cuentas/{cuenta['id']}/cerrar",
        "ua",
        mundo.company_a,
        {"motivo": MOTIVO, "fecha_cierre": HOY.isoformat()},
        version=cuenta["version"],
    )
    assert r.status_code == 200, r.text

    fijar_hoy(monkeypatch, _fecha_ejercicio(ejercicio))
    detalle = reprogramar(mundo, programa)
    assert detalle["declaraciones"][0]["cuenta_id"] == cuenta["id"]
    assert Decimal(detalle["declaraciones"][0]["monto"]) == Decimal("1000.00")


def test_rv12_inmutabilidad_en_postgres(mundo, gobierno, siembra):
    """RV-12 inmutabilidad de versiones vigentes y datos históricos."""
    programa = _programa_vigente(mundo, siembra["cargo_vigente"])

    def _debe_rechazar(sql, params, fragmento):
        with pytest.raises(DBAPIError) as excinfo:
            with mundo.factory() as db:
                db.execute(text(sql), params)
                db.commit()
        assert fragmento in str(excinfo.value)

    version_vigente = ver(mundo, programa, numero_version=1)
    linea_vigente = _linea_de_mes(version_vigente, 1)
    declaracion_vigente = version_vigente["declaraciones"][0]

    _debe_rechazar(
        "UPDATE gov_cash_program_lines SET monto = :monto WHERE id = :id",
        {"monto": 999, "id": linea_vigente["id"]},
        "GOV_CASH_",
    )
    _debe_rechazar(
        "DELETE FROM gov_cash_program_lines WHERE id = :id",
        {"id": linea_vigente["id"]},
        "GOV_CASH_",
    )
    _debe_rechazar(
        "INSERT INTO gov_cash_program_lines "
        "(id, version_id, company_id, item_id, mes, monto) "
        "SELECT :nuevo_id, version_id, company_id, item_id, 6, 100 "
        "FROM gov_cash_program_lines WHERE id = :id",
        {"nuevo_id": str(uuid4()), "id": linea_vigente["id"]},
        "GOV_CASH_",
    )
    _debe_rechazar(
        "UPDATE gov_cash_program_declarations SET monto = :monto WHERE id = :id",
        {"monto": 999, "id": declaracion_vigente["id"]},
        "GOV_CASH_",
    )
    _debe_rechazar(
        "UPDATE gov_cash_program_history SET tipo = 'CERRADO' WHERE program_id = :program_id",
        {"program_id": programa["id"]},
        "GOV_CASH_PROGRAM_HISTORY_IMMUTABLE",
    )
    _debe_rechazar(
        "DELETE FROM gov_cash_program_history WHERE program_id = :program_id",
        {"program_id": programa["id"]},
        "GOV_CASH_PROGRAM_HISTORY_IMMUTABLE",
    )
    _debe_rechazar(
        "DELETE FROM gov_cash_program_versions WHERE program_id = :program_id",
        {"program_id": programa["id"]},
        "GOV_CASH_PROGRAM_NOT_DELETABLE",
    )
    _debe_rechazar(
        "DELETE FROM gov_cash_programs WHERE id = :id",
        {"id": programa["id"]},
        "GOV_CASH_PROGRAM_NOT_DELETABLE",
    )
