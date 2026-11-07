"""Pruebas RED de ORG-04: flujo de ocupación de cargos."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select

from app.modules.audit.models import AuditEvent
from app.shared.clock import hoy_de_negocio
from tests.org04_ayudantes import (
    D,
    O,
    accion,
    acto_eficaz,
    crear,
    crear_funcionario,
    cuerpo,
    nuevo_cargo,
    post_asignacion,
)
from tests.test_gov_ctl06_hallazgos import _post

pytest_plugins = (
    "tests.conftest_multicompany",
    "tests.test_gov_ctl06_hallazgos",
    "tests.org04_ayudantes",
)


def test_f01_funcionario_alta_enmascara_documento(mundo, gobierno, ocupacion):
    """f01: el alta de funcionario enmascara el documento."""
    nombre = "Funcionario F01"
    numero = "12345678"
    r = _post(
        mundo,
        f"{O}/funcionarios",
        "ua",
        None,
        {
            "nombre": nombre,
            "tipo_documento": "V",
            "numero_documento": numero,
        },
    )
    assert r.status_code == 201, r.text
    assert numero not in r.text
    assert r.json()["documento"] == "V-******78"


def test_f02_funcionario_documento_repetido(mundo, gobierno, ocupacion):
    """f02: documento repetido devuelve 409 GOV_OFFICIAL_DUPLICATE."""
    numero = "87654321"
    payload = {
        "nombre": "Funcionario F02",
        "tipo_documento": "V",
        "numero_documento": numero,
    }
    r1 = _post(mundo, f"{O}/funcionarios", "ua", None, payload)
    assert r1.status_code == 201, r1.text
    r2 = _post(
        mundo,
        f"{O}/funcionarios",
        "ua",
        None,
        {**payload, "nombre": "Funcionario F02 bis"},
    )
    assert r2.status_code == 409, r2.text
    assert r2.json()["code"] == "GOV_OFFICIAL_DUPLICATE"


def test_f03_funcionario_patch_if_match(mundo, gobierno, ocupacion):
    """f03: PATCH de funcionario exige If-Match y registra historia."""
    funcionario = crear_funcionario(mundo, nombre="Nombre original")
    fid = funcionario["id"]
    version = funcionario["version"]

    r_sin = mundo.client.patch(
        f"/api/v1{O}/funcionarios/{fid}",
        json={"nombre": "Nombre nuevo"},
        headers=mundo.como("ua", None),
    )
    assert r_sin.status_code == 428, r_sin.text
    assert r_sin.json()["code"] == "GOV_OFFICIAL_IF_MATCH_REQUIRED"

    r_vieja = mundo.client.patch(
        f"/api/v1{O}/funcionarios/{fid}",
        json={"nombre": "Nombre nuevo"},
        headers={**mundo.como("ua", None), "If-Match": str(version - 1)},
    )
    assert r_vieja.status_code == 409, r_vieja.text
    assert r_vieja.json()["code"] == "GOV_OFFICIAL_STALE"

    r_ok = mundo.client.patch(
        f"/api/v1{O}/funcionarios/{fid}",
        json={"nombre": "Nombre nuevo"},
        headers={**mundo.como("ua", None), "If-Match": str(version)},
    )
    assert r_ok.status_code == 200, r_ok.text
    assert r_ok.json()["nombre"] == "Nombre nuevo"

    with mundo.factory() as db:
        eventos = db.execute(
            select(AuditEvent).where(
                AuditEvent.action == "GOV_OFFICIAL_UPDATED",
                AuditEvent.entity_id == fid,
            )
        ).scalars().all()
    assert eventos
    assert eventos[-1].before["nombre"] == "Nombre original"
    assert eventos[-1].after["nombre"] == "Nombre nuevo"

    r = mundo.client.get(f"/api/v1{O}/funcionarios/{fid}", headers=mundo.como("ua", mundo.company_a))
    assert r.status_code == 200, r.json()
    historia = r.json()["historia"]
    entradas = [e for e in historia if e["tipo"] == "EDITADO"]
    assert entradas
    entrada = entradas[-1]
    assert entrada["detalle"]["antes"]["nombre"] == "Nombre original"
    assert entrada["detalle"]["despues"]["nombre"] == "Nombre nuevo"


def test_f04_titular_valido_activa(mundo, gobierno, ocupacion):
    """f04: titular válido se activa y muestra autoridad completa."""
    funcionario = crear_funcionario(mundo)
    cargo_id = nuevo_cargo(mundo, ocupacion)
    acto_id = acto_eficaz(mundo, ocupacion["cargo_emisor"])
    datos = cuerpo(funcionario, cargo_id, acto_id, figura="TITULAR")

    borrador = crear(mundo, datos)
    assert borrador["status"] == "BORRADOR"

    r = accion(mundo, borrador, "activar", usuario="uab")
    assert r.status_code == 200, r.text
    detalle = r.json()
    assert detalle["status"] == "ACTIVO"
    assert detalle["situacion"] == "VIGENTE"
    assert detalle["ejerce"] is True
    assert detalle["competencias"] == []
    acciones = {c["accion"] for c in detalle["autoridad"]}
    assert acciones == {"FIRMAR", "APROBAR"}
    assert len(detalle["autoridad"]) == 2


def test_f05_quien_registra_no_activa(mundo, gobierno, ocupacion):
    """f05: el registrante no puede activar (403)."""
    funcionario = crear_funcionario(mundo)
    cargo_id = nuevo_cargo(mundo, ocupacion)
    acto_id = acto_eficaz(mundo, ocupacion["cargo_emisor"])
    datos = cuerpo(funcionario, cargo_id, acto_id, figura="TITULAR")
    borrador = crear(mundo, datos, usuario="ua")

    r = accion(mundo, borrador, "activar", usuario="ua")
    assert r.status_code == 403, r.text
    assert r.json()["code"] == "GOV_ASSIGNMENT_SELF_ACTIVATION"


def test_f06_acto_no_eficaz(mundo, gobierno, ocupacion):
    """f06: acto no eficaz produce 422 GOV_ASSIGNMENT_ACT_INVALID."""
    funcionario = crear_funcionario(mundo)
    cargo_id = nuevo_cargo(mundo, ocupacion)
    acto_id = acto_eficaz(
        mundo,
        ocupacion["cargo_emisor"],
        status="EMITIDO",
    )
    datos = cuerpo(funcionario, cargo_id, acto_id)
    r = post_asignacion(mundo, datos)
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "GOV_ASSIGNMENT_ACT_INVALID"


def test_f07_acto_eficaz_despues_de_desde(mundo, gobierno, ocupacion):
    """f07: acto eficaz posterior a desde produce 422."""
    funcionario = crear_funcionario(mundo)
    cargo_id = nuevo_cargo(mundo, ocupacion)
    acto_id = acto_eficaz(
        mundo,
        ocupacion["cargo_emisor"],
        fecha=D(3, 1),
        fecha_eficacia=D(3, 5),
    )
    datos = cuerpo(funcionario, cargo_id, acto_id, desde=D(2, 1).isoformat())
    r = post_asignacion(mundo, datos)
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "GOV_ASSIGNMENT_ACT_INVALID"


def test_f08_acto_emitido_por_mismo_cargo(mundo, gobierno, ocupacion):
    """f08: acto emitido por el propio cargo no puede titularizar."""
    funcionario = crear_funcionario(mundo)
    cargo_id = nuevo_cargo(mundo, ocupacion)
    acto_id = acto_eficaz(mundo, cargo_id)
    datos = cuerpo(funcionario, cargo_id, acto_id, figura="TITULAR")
    r = post_asignacion(mundo, datos)
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "GOV_ASSIGNMENT_ISSUER_INVALID"


def test_f09_cargo_inactivo_o_borrador(mundo, gobierno, ocupacion):
    """f09: cargo INACTIVO o BORRADOR produce 422."""
    funcionario = crear_funcionario(mundo)
    acto_id = acto_eficaz(mundo, ocupacion["cargo_emisor"])

    cargo_inactivo = nuevo_cargo(
        mundo,
        ocupacion,
        status="INACTIVO",
        valid_to=D(12, 31),
    )
    r1 = post_asignacion(
        mundo,
        cuerpo(funcionario, cargo_inactivo, acto_id),
    )
    assert r1.status_code == 422, r1.text
    assert r1.json()["code"] == "GOV_ASSIGNMENT_POSITION_INVALID"

    cargo_borrador = nuevo_cargo(mundo, ocupacion, status="BORRADOR")
    r2 = post_asignacion(
        mundo,
        cuerpo(funcionario, cargo_borrador, acto_id),
    )
    assert r2.status_code == 422, r2.text
    assert r2.json()["code"] == "GOV_ASSIGNMENT_POSITION_INVALID"


def test_f10_desde_anterior_a_valid_from(mundo, gobierno, ocupacion):
    """f10: desde anterior a valid_from del cargo produce 422."""
    funcionario = crear_funcionario(mundo)
    cargo_id = nuevo_cargo(mundo, ocupacion)
    acto_id = acto_eficaz(mundo, ocupacion["cargo_emisor"])
    datos = cuerpo(
        funcionario,
        cargo_id,
        acto_id,
        desde=date(hoy_de_negocio().year - 1, 12, 1).isoformat(),
    )
    r = post_asignacion(mundo, datos)
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "GOV_ASSIGNMENT_POSITION_INVALID"


def test_f11_hasta_posterior_al_ejercicio(mundo, gobierno, ocupacion):
    """f11: hasta posterior al ejercicio produce 422."""
    funcionario = crear_funcionario(mundo)
    cargo_id = nuevo_cargo(mundo, ocupacion)
    acto_id = acto_eficaz(mundo, ocupacion["cargo_emisor"])
    hasta = date(hoy_de_negocio().year + 1, 1, 1).isoformat()
    datos = cuerpo(funcionario, cargo_id, acto_id, hasta=hasta)
    r = post_asignacion(mundo, datos)
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "GOV_ASSIGNMENT_POSITION_INVALID"


def test_f12_funcionario_inactivo(mundo, gobierno, ocupacion):
    """f12: funcionario INACTIVO produce 422 GOV_ASSIGNMENT_OFFICIAL_INVALID."""
    funcionario = crear_funcionario(mundo)
    r_patch = mundo.client.patch(
        f"/api/v1{O}/funcionarios/{funcionario['id']}",
        json={"estado": "INACTIVO"},
        headers={
            **mundo.como("ua", None),
            "If-Match": str(funcionario["version"]),
        },
    )
    assert r_patch.status_code == 200, r_patch.text

    cargo_id = nuevo_cargo(mundo, ocupacion)
    acto_id = acto_eficaz(mundo, ocupacion["cargo_emisor"])
    datos = cuerpo(funcionario, cargo_id, acto_id)
    r = post_asignacion(mundo, datos)
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "GOV_ASSIGNMENT_OFFICIAL_INVALID"
