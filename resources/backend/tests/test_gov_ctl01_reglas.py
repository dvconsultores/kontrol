import os
import re
from datetime import timedelta

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.modules.audit.models import AuditEvent
from app.modules.government.models import GovernmentSoDRuleHistory
from app.modules.identity_access.mfa_policy import SENSITIVE, STANDARD, classify
from app.modules.setup.api import CATALOGO_DE_PERMISOS
from app.shared.clock import hoy_de_negocio
from tests.test_gov_ctl06_hallazgos import _crear_usuario_con_permisos, _post

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos")

S = "/gobierno/sod"
HOY = hoy_de_negocio()
ANIO = HOY.year


def cuerpo_regla(**cambios) -> dict:
    cuerpo = {
        "nombre": "Regla de prueba",
        "descripcion": "Descripción válida de la regla de prueba.",
        "proceso": "CTL-06",
        "accion_a": "CTL06_REGISTRAR",
        "accion_b": "CTL06_RECOMENDAR",
        "bidireccional": False,
        "vigente_desde": HOY.isoformat(),
    }
    cuerpo.update(cambios)
    return cuerpo


def patch_regla(mundo, regla_id, usuario, empresa, cuerpo, version=None):
    cabeceras = mundo.como(usuario, empresa)
    if version is not None:
        cabeceras["If-Match"] = str(version)
    return mundo.client.patch(f"/api/v1{S}/reglas/{regla_id}", headers=cabeceras, json=cuerpo)


def crear_regla(mundo, usuario="ua", empresa=None, **cambios) -> dict:
    empresa = empresa or mundo.company_a
    r = _post(mundo, f"{S}/reglas", usuario, empresa, cuerpo_regla(**cambios))
    assert r.status_code == 201, r.text
    return r.json()


def activar_regla(mundo, regla: dict, usuario="ua", empresa=None) -> dict:
    empresa = empresa or mundo.company_a
    r = _post(
        mundo,
        f"{S}/reglas/{regla['id']}/activar",
        usuario,
        empresa,
        {},
        version=regla["version"],
    )
    assert r.status_code == 200, r.text
    return r.json()


def cerrar_regla(
    mundo,
    regla: dict,
    usuario="ua",
    empresa=None,
    motivo="Cierre de la regla al terminar la prueba.",
) -> dict:
    empresa = empresa or mundo.company_a
    r = _post(
        mundo,
        f"{S}/reglas/{regla['id']}/cerrar",
        usuario,
        empresa,
        {"motivo": motivo},
        version=regla["version"],
    )
    assert r.status_code == 200, r.text
    return r.json()


def regla_vigente(mundo, **cambios) -> dict:
    return activar_regla(mundo, crear_regla(mundo, **cambios))


def eventos(mundo, accion, entity_id) -> list:
    with mundo.factory() as db:
        filas = db.scalars(
            select(AuditEvent)
            .where(AuditEvent.action == accion, AuditEvent.entity_id == entity_id)
            .order_by(AuditEvent.event_time.asc())
        ).all()
        return list(filas)


def test_cr01_catalogo_acciones(mundo, gobierno):
    """CR-01: el catálogo de acciones de segregación de funciones expone los procesos esperados."""
    r = mundo.get(f"{S}/acciones", "ua", mundo.company_a)
    assert r.status_code == 200, r.text
    datos = r.json()
    procesos = datos["procesos"]
    assert [p["proceso"] for p in procesos] == ["DOC-02", "CTL-06"], r.text

    por_codigo = {p["proceso"]: p for p in procesos}
    assert len(por_codigo["DOC-02"]["acciones"]) == 7, r.text
    assert len(por_codigo["CTL-06"]["acciones"]) == 9, r.text

    acciones_doc = {a["codigo"]: a for a in por_codigo["DOC-02"]["acciones"]}
    acciones_ctl = {a["codigo"]: a for a in por_codigo["CTL-06"]["acciones"]}
    assert acciones_doc["DOC02_REGISTRAR"]["crea_objeto"] is True, r.text
    assert acciones_ctl["CTL06_REGISTRAR"]["crea_objeto"] is True, r.text
    assert acciones_ctl["CTL06_VERIFICAR"]["etiqueta"] == "Verificar y cerrar", r.text


def test_cr02_permisos_y_clasificacion():
    """CR-02: los permisos del módulo y su clasificación MFA son los esperados."""
    assert CATALOGO_DE_PERMISOS["gobierno_sod"] == ["view", "manage", "activate"]
    assert classify(["gobierno_sod:activate"]) == SENSITIVE
    assert classify(["gobierno_sod:view"]) == STANDARD
    assert classify(["gobierno_sod:manage"]) == STANDARD


def test_cr03_crear_regla(mundo, gobierno):
    """CR-03: crear una regla devuelve un borrador correctamente inicializado y auditable."""
    regla = crear_regla(mundo)
    assert regla["estado"] == "BORRADOR", regla
    assert re.fullmatch(rf"SOD-{ANIO}-\d{{4}}", regla["codigo"]), regla
    assert regla["version"] == 1, regla
    assert regla["en_vigor"] is False, regla
    assert regla["alcance"] == "MISMO_OBJETO", regla
    assert regla["modo"] == "BLOQUEAR", regla
    assert regla["creada_por"] == "ua", regla
    assert [h["tipo"] for h in regla["historia"]] == ["CREADA"], regla

    audit = eventos(mundo, "GOV_SOD_RULE_CREATED", regla["id"])
    assert len(audit) == 1, regla
    assert audit[0].after["codigo"] == regla["codigo"], regla


def test_cr04_validaciones(mundo, gobierno):
    """CR-04: las validaciones de par y vigencia rechazan reglas inválidas."""
    casos_invalidos = [
        (cuerpo_regla(accion_a="CTL06_PLAN", accion_b="CTL06_PLAN"), "VALIDATION_ERROR"),
        (cuerpo_regla(proceso="DOC-02", accion_b="CTL06_VERIFICAR"), "GOV_SOD_RULE_INVALID"),
        (cuerpo_regla(accion_a="CTL06_PLAN", accion_b="CTL06_REGISTRAR"), "GOV_SOD_RULE_INVALID"),
        (cuerpo_regla(vigente_desde=(HOY - timedelta(days=1)).isoformat()), "GOV_SOD_RULE_INVALID"),
        (cuerpo_regla(vigente_hasta=(HOY - timedelta(days=1)).isoformat()), "VALIDATION_ERROR"),
    ]

    for cuerpo, codigo in casos_invalidos:
        r = _post(mundo, f"{S}/reglas", "ua", mundo.company_a, cuerpo)
        assert r.status_code == 422, r.text
        assert r.json()["code"] == codigo, r.text

    r = _post(
        mundo,
        f"{S}/reglas",
        "ua",
        mundo.company_a,
        cuerpo_regla(accion_a="CTL06_PLAN", accion_b="CTL06_REGISTRAR", bidireccional=True),
    )
    assert r.status_code == 201, r.text


def test_cr05_editar_regla(mundo, gobierno):
    """CR-05: editar una regla exige If-Match y deja historia y auditoría."""
    regla = crear_regla(
        mundo,
        accion_a="CTL06_PLAN",
        accion_b="CTL06_EJECUCION",
    )

    r = patch_regla(mundo, regla["id"], "ua", mundo.company_a, {"nombre": "Nuevo nombre"})
    assert r.status_code == 428, r.text
    assert r.json()["code"] == "GOV_SOD_IF_MATCH_REQUIRED", r.text

    r = patch_regla(mundo, regla["id"], "ua", mundo.company_a, {"nombre": "Nuevo nombre"}, version=99)
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_SOD_RULE_STALE", r.text

    r = patch_regla(
        mundo,
        regla["id"],
        "ua",
        mundo.company_a,
        {"nombre": "Nuevo nombre"},
        version=regla["version"],
    )
    assert r.status_code == 200, r.text
    actualizada = r.json()
    assert actualizada["nombre"] == "Nuevo nombre", r.text
    assert actualizada["version"] == regla["version"] + 1, r.text
    assert actualizada["historia"][-1]["tipo"] == "EDITADA", r.text
    assert actualizada["historia"][-1]["detalle"] == {"campos": ["nombre"]}, r.text

    audit = eventos(mundo, "GOV_SOD_RULE_UPDATED", regla["id"])
    assert len(audit) == 1, r.text


def test_cr06_activar_regla(mundo, gobierno):
    """CR-06: activar una regla la hace vigente e impide editarla o reactivarla."""
    regla = crear_regla(
        mundo,
        accion_a="CTL06_PRESENTAR",
        accion_b="CTL06_VERIFICAR",
    )
    regla = activar_regla(mundo, regla)
    assert regla["estado"] == "VIGENTE", regla
    assert regla["en_vigor"] is True, regla
    assert regla["activada_por"] == "ua", regla

    r = patch_regla(mundo, regla["id"], "ua", mundo.company_a, {"nombre": "Otro"}, version=regla["version"])
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_SOD_RULE_INVALID_STATE", r.text

    r = _post(
        mundo,
        f"{S}/reglas/{regla['id']}/activar",
        "ua",
        mundo.company_a,
        {},
        version=regla["version"],
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_SOD_RULE_INVALID_STATE", r.text

    audit = eventos(mundo, "GOV_SOD_RULE_ACTIVATED", regla["id"])
    assert len(audit) == 1, regla

    cerrar_regla(mundo, regla)


def test_cr07_regla_duplicada(mundo, gobierno):
    """CR-07: no pueden convivir dos reglas vigentes con el mismo par, incluso invertido y bidireccional."""
    r1 = regla_vigente(
        mundo,
        accion_a="CTL06_AVANCE",
        accion_b="CTL06_DEVOLVER",
    )

    segunda = crear_regla(mundo, accion_a="CTL06_AVANCE", accion_b="CTL06_DEVOLVER")
    r = _post(
        mundo,
        f"{S}/reglas/{segunda['id']}/activar",
        "ua",
        mundo.company_a,
        {},
        version=segunda["version"],
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_SOD_RULE_DUPLICATE", r.text

    invertida = crear_regla(
        mundo,
        accion_a="CTL06_DEVOLVER",
        accion_b="CTL06_AVANCE",
        bidireccional=True,
    )
    r = _post(
        mundo,
        f"{S}/reglas/{invertida['id']}/activar",
        "ua",
        mundo.company_a,
        {},
        version=invertida["version"],
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_SOD_RULE_DUPLICATE", r.text

    cerrar_regla(mundo, r1)

    segunda = activar_regla(mundo, segunda)
    assert segunda["estado"] == "VIGENTE", segunda

    cerrar_regla(mundo, segunda)


def test_cr08_cerrar_regla(mundo, gobierno):
    """CR-08: cerrar una regla solo es válido en estado vigente y deja historia y auditoría."""
    regla = crear_regla(
        mundo,
        accion_a="CTL06_RECOMENDAR",
        accion_b="CTL06_ACCION",
    )

    r = _post(
        mundo,
        f"{S}/reglas/{regla['id']}/cerrar",
        "ua",
        mundo.company_a,
        {"motivo": "Motivo suficientemente largo para el cierre."},
        version=regla["version"],
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_SOD_RULE_INVALID_STATE", r.text

    regla = activar_regla(mundo, regla)

    r = _post(
        mundo,
        f"{S}/reglas/{regla['id']}/cerrar",
        "ua",
        mundo.company_a,
        {"motivo": "corto"},
        version=regla["version"],
    )
    assert r.status_code == 422, r.text

    motivo_largo = "Motivo perfectamente válido con más de diez caracteres para cerrar la regla."
    regla = cerrar_regla(mundo, regla, motivo=motivo_largo)
    assert regla["estado"] == "CERRADA", regla
    assert regla["motivo_cierre"] == motivo_largo, regla
    assert regla["cerrada_por"] == "ua", regla
    assert [h["tipo"] for h in regla["historia"]] == ["CREADA", "ACTIVADA", "CERRADA"], regla

    audit = eventos(mundo, "GOV_SOD_RULE_CLOSED", regla["id"])
    assert len(audit) == 1, regla

    r = mundo.get(f"{S}/reglas?estado=CERRADA", "ua", mundo.company_a)
    assert r.status_code == 200, r.text
    ids = [item["id"] for item in r.json()["items"]]
    assert regla["id"] in ids, r.text
    assert r.json()["resumen"]["cerradas"] >= 1, r.text


def test_cr09_permisos(mundo, gobierno):
    """CR-09: los permisos de consulta, gestión y activación se aplican correctamente."""
    _crear_usuario_con_permisos(
        mundo,
        "sod_consulta",
        [("gobierno_sod", "view")],
        mundo.company_a,
    )
    _crear_usuario_con_permisos(
        mundo,
        "sod_gestor",
        [("gobierno_sod", "view"), ("gobierno_sod", "manage")],
        mundo.company_a,
    )
    _crear_usuario_con_permisos(
        mundo,
        "sin_sod",
        [("gobierno_hallazgos", "view")],
        mundo.company_a,
    )

    r = mundo.get(f"{S}/reglas", "sod_consulta", mundo.company_a)
    assert r.status_code == 200, r.text

    r = _post(mundo, f"{S}/reglas", "sod_consulta", mundo.company_a, cuerpo_regla())
    assert r.status_code == 403, r.text

    regla = crear_regla(mundo, usuario="sod_gestor")
    r = _post(
        mundo,
        f"{S}/reglas/{regla['id']}/activar",
        "sod_gestor",
        mundo.company_a,
        {},
        version=regla["version"],
    )
    assert r.status_code == 403, r.text

    r = mundo.get(f"{S}/reglas", "sin_sod", mundo.company_a)
    assert r.status_code == 403, r.text


def test_cr10_alcance_por_empresa(mundo, gobierno):
    """CR-10: las reglas solo son visibles dentro de su empresa."""
    regla = crear_regla(mundo)

    r = mundo.get(f"{S}/reglas/{regla['id']}", "ub", mundo.company_b)
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "GOV_SOD_RULE_NOT_FOUND", r.text

    r = mundo.get(f"{S}/reglas", "ub", mundo.company_b)
    assert r.status_code == 200, r.text
    ids = [item["id"] for item in r.json()["items"]]
    assert regla["id"] not in ids, r.text


def test_cr11_inmutabilidad_postgresql(mundo, gobierno):
    """CR-11: PostgreSQL impide mutar directamente las tablas de reglas y su historia."""
    if not os.environ.get("KONTROL_TEST_DB_URL", "").startswith("postgresql"):
        pytest.skip("solo PostgreSQL")

    regla = crear_regla(mundo)

    with mundo.factory() as db:
        historia_id = db.scalar(
            select(GovernmentSoDRuleHistory.id).where(
                GovernmentSoDRuleHistory.rule_id == regla["id"]
            )
        )

    sentencias = [
        ("UPDATE gov_sod_rule_history SET tipo = 'EDITADA' WHERE id = :id", historia_id),
        ("DELETE FROM gov_sod_rules WHERE id = :id", regla["id"]),
    ]

    for sentencia, identificador in sentencias:
        with mundo.factory() as db:
            with pytest.raises(DBAPIError):
                db.execute(text(sentencia), {"id": identificador})
                db.commit()
            db.rollback()
