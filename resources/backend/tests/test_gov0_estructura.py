"""Suite de backend para ORG02-T001: Estructura organizativa por ejercicio.

Especifica el contrato del módulo `app.modules.government` antes de que exista.
"""
from csv import reader as csv_reader
from datetime import UTC, datetime
from io import StringIO
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.modules.audit.models import AuditEvent
from app.modules.documents.models import Document, DocumentLink, DocumentType
from app.modules.government.models import GovernmentEntity
from app.modules.identity_access import service as identity_service
from app.modules.identity_access.models import (
    Permission,
    Role,
    RolePermission,
    UserRole,
    UserScope,
)
from app.modules.licensing import service as licensing_service
from app.modules.licensing.models import LicenseEntitlementSnapshot
from app.shared.clock import hoy_de_negocio
from tests.conftest_multicompany import PASSWORD

pytest_plugins = ("tests.conftest_multicompany",)

ANIO = hoy_de_negocio().year
ANTERIOR = ANIO - 1
SIGUIENTE = ANIO + 1
E = "/gobierno/estructuras"
ESTADO = {}


def u(ej):
    return f"{E}/{ej}/unidades"


@pytest.fixture
def gobierno(mundo):
    """Garantiza el entitlement `gobierno` en la snapshot sincronizada."""
    with mundo.factory() as db:
        inst = licensing_service.get_installation(db)
        snapshot = db.scalar(
            select(LicenseEntitlementSnapshot).where(
                LicenseEntitlementSnapshot.installation_id
                == inst.installation_uuid,
                LicenseEntitlementSnapshot.version == "gov0-test",
            )
        )
        if snapshot is None:
            snapshot = LicenseEntitlementSnapshot(
                installation_id=inst.installation_uuid,
                modules={"gobierno": True},
                version="gov0-test",
                taken_at=datetime.now(UTC),
            )
            db.add(snapshot)
        else:
            snapshot.modules = {"gobierno": True}
        db.commit()


def _ente(mundo, company_id, estado):
    """Crea un GovernmentEntity con el estado indicado."""
    with mundo.factory() as db:
        ente = GovernmentEntity(
            company_id=company_id,
            denominacion=f"Ente {estado.lower()}",
            status=estado,
            version=1,
        )
        if estado == "ACTIVO":
            ente.activated_at = datetime.now(UTC)
        db.add(ente)
        db.commit()


def _acto(mundo, company_id, structure_id) -> str:
    """Vincula un documento ACTIVE de la empresa a la estructura."""
    with mundo.factory() as db:
        tipo = db.scalar(
            select(DocumentType).where(
                DocumentType.company_id == company_id,
                DocumentType.code == "GOV-ESTR",
            )
        )
        if tipo is None:
            tipo = DocumentType(
                company_id=company_id,
                code="GOV-ESTR",
                name="Acto de estructura",
            )
            db.add(tipo)
            db.flush()
        doc = Document(
            company_id=company_id,
            document_type_id=tipo.id,
            title="Acto que aprueba la estructura",
            status="ACTIVE",
        )
        db.add(doc)
        db.flush()
        db.add(
            DocumentLink(
                document_id=doc.id,
                company_id=company_id,
                document_type_id=tipo.id,
                resource_type="GovernmentStructure",
                resource_id=structure_id,
            )
        )
        db.commit()
        return str(doc.id)


def _eventos(mundo, action, company_id) -> list[AuditEvent]:
    """Devuelve los eventos de auditoría de una acción en orden ascendente."""
    with mundo.factory() as db:
        return list(
            db.scalars(
                select(AuditEvent)
                .where(
                    AuditEvent.action == action,
                    AuditEvent.company_id == company_id,
                )
                .order_by(AuditEvent.event_time.asc())
            )
        )


def test_gs01_modulo(mundo, gobierno):
    """GS-01: sin ente en el contenedor GET devuelve 404; sin módulo 403."""
    resp = mundo.get(E, "ua", mundo.company_a)
    assert resp.status_code == 404
    assert resp.json()["code"] == "GOV_ENTITY_NOT_FOUND"

    with mundo.factory() as db:
        inst = licensing_service.get_installation(db)
        snapshot = db.scalar(
            select(LicenseEntitlementSnapshot).where(
                LicenseEntitlementSnapshot.installation_id
                == inst.installation_uuid,
                LicenseEntitlementSnapshot.version == "gov0-test",
            )
        )
        snapshot.modules = {"gobierno": False}
        db.commit()

    try:
        resp = mundo.get(E, "ua", mundo.company_a)
        assert resp.status_code == 403
        assert resp.json()["code"] == "MODULE_NOT_ENTITLED"
    finally:
        with mundo.factory() as db:
            inst = licensing_service.get_installation(db)
            snapshot = db.scalar(
                select(LicenseEntitlementSnapshot).where(
                    LicenseEntitlementSnapshot.installation_id
                    == inst.installation_uuid,
                    LicenseEntitlementSnapshot.version == "gov0-test",
                )
            )
            snapshot.modules = {"gobierno": True}
            db.commit()


def test_gs02_sin_ente(mundo, gobierno):
    """GS-02: abrir estructura sin ente devuelve 404 GOV_ENTITY_NOT_FOUND."""
    resp = mundo.post(E, "ua", mundo.company_a, {"ejercicio": ANIO})
    assert resp.status_code == 404
    assert resp.json()["code"] == "GOV_ENTITY_NOT_FOUND"

    _ente(mundo, mundo.company_a, "ACTIVO")


def test_gs03_lista_vacia(mundo, gobierno):
    """GS-03: sin estructuras la lista está vacía."""
    resp = mundo.get(E, "ua", mundo.company_a)
    assert resp.status_code == 200
    assert resp.json() == {"items": [], "total": 0}


def test_gs04_abrir(mundo, gobierno):
    """GS-04: abrir una estructura crea un BORRADOR versión 1 con faltantes."""
    resp = mundo.post(E, "ua", mundo.company_a, {"ejercicio": ANIO})
    assert resp.status_code == 201
    cuerpo = resp.json()
    assert cuerpo["ejercicio"] == ANIO
    assert cuerpo["estado"] == "BORRADOR"
    assert cuerpo["version"] == 1
    assert cuerpo["unidades"] == []
    assert cuerpo["faltantes_para_publicar"] == ["UNIDADES", "DOCUMENTO_ACTO"]
    ESTADO["estructura_anio"] = cuerpo["id"]
    assert len(_eventos(mundo, "GOV_STRUCTURE_CREATED", mundo.company_a)) == 1


def test_gs05_validacion_apertura(mundo, gobierno):
    """GS-05: validaciones de apertura y copia de origen inválido."""
    resp = mundo.post(E, "ua", mundo.company_a, {"ejercicio": ANIO})
    assert resp.status_code == 409
    assert resp.json()["code"] == "GOV_STRUCTURE_ALREADY_EXISTS"

    for ejercicio in (1999, ANIO + 2):
        resp = mundo.post(E, "ua", mundo.company_a, {"ejercicio": ejercicio})
        assert resp.status_code == 422
        assert resp.json()["code"] == "VALIDATION_ERROR"
        assert "ejercicio" in resp.json()["field_errors"]

    resp = mundo.post(
        E, "ua", mundo.company_a, {"ejercicio": SIGUIENTE, "x": 1}
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_ERROR"
    assert "x" in resp.json()["field_errors"]

    resp = mundo.post(
        E, "ua", mundo.company_a, {"ejercicio": SIGUIENTE, "copiar_de": 1990}
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "GOV_STRUCTURE_COPY_SOURCE_INVALID"


def test_gs06_unidades_borrador(mundo, gobierno):
    """GS-06: alta de unidades en borrador con jerarquía y normalización."""
    resp = mundo.post(
        u(ANIO),
        "ua",
        mundo.company_a,
        {
            "codigo": "desp",
            "denominacion": "Despacho del Alcalde",
            "tipo": "ORGANO",
        },
    )
    assert resp.status_code == 201
    desp = resp.json()
    assert desp["codigo"] == "DESP"
    assert desp["nivel"] == 0
    assert desp["vigente_desde"] == f"{ANIO}-01-01"
    ESTADO["desp"] = desp["id"]

    resp = mundo.post(
        u(ANIO),
        "ua",
        mundo.company_a,
        {
            "codigo": "DA-01",
            "denominacion": "Administración",
            "tipo": "UNIDAD_ADMINISTRATIVA",
            "unidad_superior_id": desp["id"],
        },
    )
    assert resp.status_code == 201
    da = resp.json()
    assert da["nivel"] == 1
    ESTADO["da"] = da["id"]
    ESTADO["da_version"] = da["version"]

    resp = mundo.post(
        u(ANIO),
        "ua",
        mundo.company_a,
        {
            "codigo": "SEDE1",
            "denominacion": "Sede Principal",
            "tipo": "SEDE",
        },
    )
    assert resp.status_code == 201
    ESTADO["sede1"] = resp.json()["id"]

    assert len(_eventos(mundo, "GOV_UNIT_CREATED", mundo.company_a)) == 3


def test_gs07_validacion_unidad(mundo, gobierno):
    """GS-07: validaciones de unidad, superior inválido y código duplicado."""
    base = {
        "codigo": "VAL-01",
        "denominacion": "Unidad de Validación",
        "tipo": "DEPENDENCIA",
    }
    casos = [
        ({**base, "codigo": "?"}, "codigo"),
        ({**base, "denominacion": "  "}, "denominacion"),
        ({**base, "tipo": "GERENCIA"}, "tipo"),
        ({**base, "vigente_desde": f"{ANIO - 1}-12-31"}, "vigente_desde"),
        ({**base, "nivel": 3}, "nivel"),
    ]
    for cuerpo, campo in casos:
        resp = mundo.post(u(ANIO), "ua", mundo.company_a, cuerpo)
        assert resp.status_code == 422, f"cuerpo aceptado: {cuerpo} -> {resp.json()}"
        assert resp.json()["code"] == "VALIDATION_ERROR"
        assert campo in resp.json()["field_errors"], (
            f"campo {campo!r} no rechazado en {cuerpo}: {resp.json()}"
        )

    resp = mundo.post(
        u(ANIO),
        "ua",
        mundo.company_a,
        {**base, "unidad_superior_id": str(uuid4())},
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "GOV_UNIT_INVALID_PARENT"

    resp = mundo.post(
        u(ANIO),
        "ua",
        mundo.company_a,
        {
            "codigo": "DA-01",
            "denominacion": "Otra Dirección",
            "tipo": "UNIDAD_ADMINISTRATIVA",
        },
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "GOV_UNIT_CODE_DUPLICATE"


def test_gs08_jerarquia(mundo, gobierno):
    """GS-08: no se permiten ciclos de jerarquía."""
    resp = mundo.client.patch(
        f"/api/v1{u(ANIO)}/{ESTADO['desp']}",
        headers={
            **mundo.como("ua", mundo.company_a),
            "If-Match": "1",
        },
        json={"unidad_superior_id": ESTADO["desp"]},
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "GOV_UNIT_HIERARCHY_CYCLE"

    resp = mundo.client.patch(
        f"/api/v1{u(ANIO)}/{ESTADO['desp']}",
        headers={
            **mundo.como("ua", mundo.company_a),
            "If-Match": "1",
        },
        json={"unidad_superior_id": ESTADO["da"]},
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "GOV_UNIT_HIERARCHY_CYCLE"

    resp = mundo.get(f"{E}/{ANIO}", "ua", mundo.company_a)
    desp = next(
        unidad
        for unidad in resp.json()["unidades"]
        if unidad["id"] == ESTADO["desp"]
    )
    assert desp["nivel"] == 0


def test_gs09_otro_ejercicio(mundo, gobierno):
    """GS-09: una unidad de otro ejercicio no puede ser superior."""
    resp = mundo.post(E, "ua", mundo.company_a, {"ejercicio": ANTERIOR})
    assert resp.status_code == 201
    ESTADO["estructura_anterior"] = resp.json()["id"]

    resp = mundo.post(
        u(ANTERIOR),
        "ua",
        mundo.company_a,
        {
            "codigo": "X-01",
            "denominacion": "Unidad del ejercicio anterior",
            "tipo": "DEPENDENCIA",
        },
    )
    assert resp.status_code == 201
    ESTADO["x_anterior"] = resp.json()["id"]

    resp = mundo.post(
        u(ANIO),
        "ua",
        mundo.company_a,
        {
            "codigo": "VAL-02",
            "denominacion": "Unidad con superior ajeno",
            "tipo": "DEPENDENCIA",
            "unidad_superior_id": ESTADO["x_anterior"],
        },
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "GOV_UNIT_INVALID_PARENT"


def test_gs10_if_match_unidad(mundo, gobierno):
    """GS-10: PATCH de unidad exige If-Match y versión vigente."""
    resp = mundo.client.patch(
        f"/api/v1{u(ANIO)}/{ESTADO['da']}",
        headers=mundo.como("ua", mundo.company_a),
        json={"denominacion": "Dirección de Administración"},
    )
    assert resp.status_code == 428
    assert resp.json()["code"] == "GOV_UNIT_IF_MATCH_REQUIRED"

    resp = mundo.client.patch(
        f"/api/v1{u(ANIO)}/{ESTADO['da']}",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "99"},
        json={"denominacion": "Dirección de Administración"},
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "GOV_UNIT_STALE"

    resp = mundo.client.patch(
        f"/api/v1{u(ANIO)}/{ESTADO['da']}",
        headers={
            **mundo.como("ua", mundo.company_a),
            "If-Match": str(ESTADO["da_version"]),
        },
        json={"denominacion": "Dirección de Administración"},
    )
    assert resp.status_code == 200
    cuerpo = resp.json()
    assert cuerpo["version"] == ESTADO["da_version"] + 1
    ESTADO["da_version"] = cuerpo["version"]
    assert len(_eventos(mundo, "GOV_UNIT_UPDATED", mundo.company_a)) == 1


def test_gs11_eliminar_borrador(mundo, gobierno):
    """GS-11: en borrador se puede eliminar solo sin hijos."""
    resp = mundo.client.delete(
        f"/api/v1{u(ANIO)}/{ESTADO['desp']}",
        headers={
            **mundo.como("ua", mundo.company_a),
            "If-Match": "1",
        },
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "GOV_UNIT_HAS_CHILDREN"

    resp = mundo.client.delete(
        f"/api/v1{u(ANIO)}/{ESTADO['sede1']}",
        headers={
            **mundo.como("ua", mundo.company_a),
            "If-Match": "1",
        },
    )
    assert resp.status_code == 204
    assert len(_eventos(mundo, "GOV_UNIT_DELETED", mundo.company_a)) == 1

    resp = mundo.get(f"{E}/{ANIO}", "ua", mundo.company_a)
    ids = {unidad["id"] for unidad in resp.json()["unidades"]}
    assert ESTADO["sede1"] not in ids


def test_gs12_desactivar_borrador(mundo, gobierno):
    """GS-12: no se puede desactivar una unidad en estructura BORRADOR."""
    resp = mundo.client.post(
        f"/api/v1{u(ANIO)}/{ESTADO['da']}/desactivar",
        headers={
            **mundo.como("ua", mundo.company_a),
            "If-Match": str(ESTADO["da_version"]),
        },
        json={"fecha": f"{ANIO}-06-30", "motivo": "Prueba"},
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "GOV_STRUCTURE_INVALID_STATE"


def test_gs13_publicar_sin_acto(mundo, gobierno):
    """GS-13: publicar exige If-Match y estructura completa."""
    resp = mundo.client.post(
        f"/api/v1{E}/{ANIO}/publicar",
        headers=mundo.como("ua", mundo.company_a),
    )
    assert resp.status_code == 428
    assert resp.json()["code"] == "GOV_STRUCTURE_IF_MATCH_REQUIRED"

    resp = mundo.client.post(
        f"/api/v1{E}/{ANIO}/publicar",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "99"},
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "GOV_STRUCTURE_STALE"

    resp = mundo.client.post(
        f"/api/v1{E}/{ANIO}/publicar",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "1"},
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "GOV_STRUCTURE_INCOMPLETE"
    assert resp.json()["details"]["faltantes"] == ["DOCUMENTO_ACTO"]


def test_gs14_ente_no_activo(mundo, gobierno):
    """GS-14: ente no ACTIVO impide publicar; documento ajeno no cuenta."""
    _ente(mundo, mundo.company_b, "BORRADOR")

    resp = mundo.post(E, "ub", mundo.company_b, {"ejercicio": ANIO})
    assert resp.status_code == 201
    estructura_b = resp.json()["id"]

    resp = mundo.post(
        u(ANIO),
        "ub",
        mundo.company_b,
        {
            "codigo": "UB-01",
            "denominacion": "Unidad de B",
            "tipo": "DEPENDENCIA",
        },
    )
    assert resp.status_code == 201

    _acto(mundo, mundo.company_a, estructura_b)
    resp = mundo.get(f"{E}/{ANIO}", "ub", mundo.company_b)
    assert resp.json()["documento_vinculado"] is False

    _acto(mundo, mundo.company_b, estructura_b)
    resp = mundo.client.post(
        f"/api/v1{E}/{ANIO}/publicar",
        headers={**mundo.como("ub", mundo.company_b), "If-Match": "1"},
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "GOV_STRUCTURE_INCOMPLETE"
    assert resp.json()["details"]["faltantes"] == ["ENTE_ACTIVO"]


def test_gs15_publicar_a(mundo, gobierno):
    """GS-15: con acto vinculado la estructura A se publica."""
    _acto(mundo, mundo.company_a, ESTADO["estructura_anio"])

    resp = mundo.client.post(
        f"/api/v1{E}/{ANIO}/publicar",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "1"},
    )
    assert resp.status_code == 200
    cuerpo = resp.json()
    assert cuerpo["estado"] == "VIGENTE"
    assert cuerpo["publicada_en"] is not None
    assert len(_eventos(mundo, "GOV_STRUCTURE_PUBLISHED", mundo.company_a)) == 1


def test_gs16_cambios_vigor(mundo, gobierno):
    """GS-16: en VIGENTE el motivo es obligatorio y hay campos bloqueados."""
    resp = mundo.client.patch(
        f"/api/v1{u(ANIO)}/{ESTADO['da']}",
        headers={
            **mundo.como("ua", mundo.company_a),
            "If-Match": str(ESTADO["da_version"]),
        },
        json={"denominacion": "Dirección General de Administración"},
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "GOV_UNIT_REASON_REQUIRED"

    resp = mundo.client.patch(
        f"/api/v1{u(ANIO)}/{ESTADO['da']}",
        headers={
            **mundo.como("ua", mundo.company_a),
            "If-Match": str(ESTADO["da_version"]),
        },
        json={"denominacion": "Dirección General de Administración", "motivo": "x"},
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "GOV_UNIT_REASON_REQUIRED"

    resp = mundo.client.patch(
        f"/api/v1{u(ANIO)}/{ESTADO['da']}",
        headers={
            **mundo.como("ua", mundo.company_a),
            "If-Match": str(ESTADO["da_version"]),
        },
        json={
            "denominacion": "Dirección General de Administración",
            "motivo": "Reorganización aprobada",
        },
    )
    assert resp.status_code == 200
    cuerpo = resp.json()
    assert cuerpo["version"] == ESTADO["da_version"] + 1
    ESTADO["da_version"] = cuerpo["version"]
    eventos = _eventos(mundo, "GOV_UNIT_UPDATED", mundo.company_a)
    assert eventos[-1].reason == "Reorganización aprobada"

    resp = mundo.client.patch(
        f"/api/v1{u(ANIO)}/{ESTADO['da']}",
        headers={
            **mundo.como("ua", mundo.company_a),
            "If-Match": str(ESTADO["da_version"]),
        },
        json={"codigo": "DA-9", "motivo": "Cambio de código"},
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "GOV_UNIT_FIELD_LOCKED"

    resp = mundo.client.patch(
        f"/api/v1{u(ANIO)}/{ESTADO['da']}",
        headers={
            **mundo.como("ua", mundo.company_a),
            "If-Match": str(ESTADO["da_version"]),
        },
        json={"vigente_desde": f"{ANIO}-02-01", "motivo": "Cambio de fecha"},
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "GOV_UNIT_FIELD_LOCKED"

    resp = mundo.post(
        u(ANIO),
        "ua",
        mundo.company_a,
        {
            "codigo": "CG1",
            "denominacion": "Centro Gestor Uno",
            "tipo": "CENTRO_GESTOR",
            "unidad_superior_id": ESTADO["da"],
        },
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "GOV_UNIT_REASON_REQUIRED"

    resp = mundo.post(
        u(ANIO),
        "ua",
        mundo.company_a,
        {
            "codigo": "CG1",
            "denominacion": "Centro Gestor Uno",
            "tipo": "CENTRO_GESTOR",
            "unidad_superior_id": ESTADO["da"],
            "motivo": "Nuevo centro gestor",
        },
    )
    assert resp.status_code == 201
    ESTADO["cg1"] = resp.json()["id"]
    ESTADO["cg1_version"] = resp.json()["version"]


def test_gs17_sin_borrado_vigor(mundo, gobierno):
    """GS-17: no se puede eliminar una unidad en estructura VIGENTE."""
    resp = mundo.client.delete(
        f"/api/v1{u(ANIO)}/{ESTADO['da']}",
        headers={
            **mundo.como("ua", mundo.company_a),
            "If-Match": str(ESTADO["da_version"]),
        },
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "GOV_STRUCTURE_INVALID_STATE"


def test_gs18_desactivar(mundo, gobierno):
    """GS-18: desactivación con validaciones, hijos activos y estado."""
    resp = mundo.client.post(
        f"/api/v1{u(ANIO)}/{ESTADO['da']}/desactivar",
        headers={
            **mundo.como("ua", mundo.company_a),
            "If-Match": str(ESTADO["da_version"]),
        },
        json={"fecha": f"{ANIO}-06-30", "motivo": "Prueba"},
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "GOV_UNIT_HAS_ACTIVE_CHILDREN"

    resp = mundo.client.post(
        f"/api/v1{u(ANIO)}/{ESTADO['cg1']}/desactivar",
        headers={
            **mundo.como("ua", mundo.company_a),
            "If-Match": str(ESTADO["cg1_version"]),
        },
        json={"fecha": f"{ANIO - 1}-12-31", "motivo": "Cierre"},
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_ERROR"
    assert "fecha" in resp.json()["field_errors"]

    resp = mundo.client.post(
        f"/api/v1{u(ANIO)}/{ESTADO['cg1']}/desactivar",
        headers={
            **mundo.como("ua", mundo.company_a),
            "If-Match": str(ESTADO["cg1_version"]),
        },
        json={"fecha": f"{ANIO}-12-31", "motivo": "Supresión del centro"},
    )
    assert resp.status_code == 200
    cuerpo = resp.json()
    assert cuerpo["estado"] == "INACTIVA"
    assert cuerpo["vigente_hasta"] == f"{ANIO}-12-31"
    ESTADO["cg1_version"] = cuerpo["version"]

    resp = mundo.client.post(
        f"/api/v1{u(ANIO)}/{ESTADO['cg1']}/desactivar",
        headers={
            **mundo.como("ua", mundo.company_a),
            "If-Match": str(ESTADO["cg1_version"]),
        },
        json={"fecha": f"{ANIO}-06-30", "motivo": "Otra vez"},
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "GOV_UNIT_INVALID_STATE"

    eventos = _eventos(mundo, "GOV_UNIT_DEACTIVATED", mundo.company_a)
    assert len(eventos) == 1
    assert eventos[0].reason == "Supresión del centro"

    resp = mundo.post(
        u(ANIO),
        "ua",
        mundo.company_a,
        {
            "codigo": "CG2",
            "denominacion": "Centro Gestor Dos",
            "tipo": "CENTRO_GESTOR",
            "unidad_superior_id": ESTADO["cg1"],
            "motivo": "Nuevo centro",
        },
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "GOV_UNIT_INVALID_PARENT"


def test_gs19_historial(mundo, gobierno):
    """GS-19: el historial de una unidad lista sus versiones."""
    resp = mundo.get(
        f"{u(ANIO)}/{ESTADO['da']}/versiones", "ua", mundo.company_a
    )
    assert resp.status_code == 200
    cuerpo = resp.json()
    assert cuerpo["total"] == 3
    items = cuerpo["items"]
    assert [item["version"] for item in items] == [1, 2, 3]
    ultimo = items[-1]
    assert ultimo["motivo"] == "Reorganización aprobada"
    assert ultimo["datos"]["denominacion"] == "Dirección General de Administración"


def test_gs20_csv(mundo, gobierno):
    """GS-20: exportación CSV con cabecera exacta y filas ordenadas."""
    resp = mundo.get(f"{E}/{ANIO}/exportar", "ua", mundo.company_a)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert f"estructura-{ANIO}.csv" in resp.headers["content-disposition"]

    filas = list(csv_reader(StringIO(resp.text)))
    assert filas[0] == [
        "codigo",
        "denominacion",
        "tipo",
        "codigo_superior",
        "nivel",
        "estado",
        "vigente_desde",
        "vigente_hasta",
    ]
    assert [fila[0] for fila in filas[1:]] == ["CG1", "DA-01", "DESP"]
    cg1 = filas[1]
    assert cg1[3] == "DA-01"
    assert cg1[4] == "2"
    assert cg1[5] == "INACTIVA"
    da = filas[2]
    assert da[3] == "DESP"
    assert da[4] == "1"
    desp = filas[3]
    assert desp[3] == ""
    assert desp[4] == "0"
    assert len(_eventos(mundo, "GOV_STRUCTURE_EXPORTED", mundo.company_a)) == 1


def test_gs21_cerrar(mundo, gobierno):
    """GS-21: cierre solo de ejercicios terminados; CERRADA bloquea cambios."""
    version_anio = mundo.get(f"{E}/{ANIO}", "ua", mundo.company_a).json()["version"]
    resp = mundo.client.post(
        f"/api/v1{E}/{ANIO}/cerrar",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(version_anio)},
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "GOV_STRUCTURE_EXERCISE_NOT_ENDED"

    _acto(mundo, mundo.company_a, ESTADO["estructura_anterior"])
    resp = mundo.client.post(
        f"/api/v1{E}/{ANTERIOR}/publicar",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "1"},
    )
    assert resp.status_code == 200
    version_anterior = resp.json()["version"]

    resp = mundo.client.post(
        f"/api/v1{E}/{ANTERIOR}/cerrar",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(version_anterior)},
    )
    assert resp.status_code == 200
    cuerpo = resp.json()
    assert cuerpo["estado"] == "CERRADA"
    assert cuerpo["cerrada_en"] is not None

    resp = mundo.post(
        u(ANTERIOR),
        "ua",
        mundo.company_a,
        {
            "codigo": "X-02",
            "denominacion": "Unidad tardía",
            "tipo": "DEPENDENCIA",
            "motivo": "Prueba",
        },
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "GOV_STRUCTURE_CLOSED"

    resp = mundo.client.patch(
        f"/api/v1{u(ANTERIOR)}/{ESTADO['x_anterior']}",
        headers={
            **mundo.como("ua", mundo.company_a),
            "If-Match": "1",
        },
        json={"denominacion": "Unidad renombrada", "motivo": "Prueba"},
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "GOV_STRUCTURE_CLOSED"

    assert len(_eventos(mundo, "GOV_STRUCTURE_CLOSED", mundo.company_a)) == 1


def test_gs22_copia(mundo, gobierno):
    """GS-22: copiar estructura copia solo unidades ACTIVAS con nueva jerarquía."""
    resp = mundo.post(
        E, "ua", mundo.company_a, {"ejercicio": SIGUIENTE, "copiar_de": ANIO}
    )
    assert resp.status_code == 201
    cuerpo = resp.json()
    assert cuerpo["estado"] == "BORRADOR"
    assert cuerpo["copiada_de"] == ANIO
    ESTADO["estructura_siguiente"] = cuerpo["id"]

    unidades = {unidad["codigo"]: unidad for unidad in cuerpo["unidades"]}
    assert set(unidades) == {"DA-01", "DESP"}
    assert unidades["DA-01"]["unidad_superior_id"] == unidades["DESP"]["id"]
    assert unidades["DA-01"]["unidad_superior_id"] != ESTADO["desp"]
    assert unidades["DA-01"]["vigente_desde"] == f"{SIGUIENTE}-01-01"
    assert unidades["DA-01"]["version"] == 1

    resp = mundo.post(
        E, "ub", mundo.company_b, {"ejercicio": SIGUIENTE, "copiar_de": ANIO}
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "GOV_STRUCTURE_COPY_SOURCE_INVALID"


def test_gs23_permisos(mundo, gobierno):
    """GS-23: un usuario con solo lectura no puede editar ni publicar."""
    with mundo.factory() as db:
        usuario = identity_service.create_user(
            db,
            tenant_id=mundo.t1,
            username="estconsulta",
            email="estconsulta@example.test",
            password=PASSWORD,
            created_by=None,
        )
        rol = Role(
            code="R_EST_CONSULTA",
            name="Consulta Estructura",
            tenant_id=mundo.t1,
            protected=False,
            status="ACTIVE",
        )
        db.add(rol)
        db.flush()
        permiso = db.scalar(
            select(Permission).where(
                Permission.resource == "gobierno_estructura",
                Permission.action == "view",
            )
        )
        db.add(RolePermission(role_id=rol.id, permission_id=permiso.id))
        db.add(UserRole(user_id=usuario.id, role_id=rol.id, company_id=None))
        db.add(UserScope(user_id=usuario.id, company_id=mundo.company_a))
        db.commit()

    resp = mundo.get(f"{E}/{ANIO}", "estconsulta", mundo.company_a)
    assert resp.status_code == 200

    resp = mundo.get(f"{E}/{ANIO}/exportar", "estconsulta", mundo.company_a)
    assert resp.status_code == 200

    resp = mundo.post(
        u(ANIO),
        "estconsulta",
        mundo.company_a,
        {
            "codigo": "NO-01",
            "denominacion": "No debería",
            "tipo": "DEPENDENCIA",
        },
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "PERMISSION_DENIED"

    resp = mundo.client.post(
        f"/api/v1{E}/{SIGUIENTE}/publicar",
        headers={
            **mundo.como("estconsulta", mundo.company_a),
            "If-Match": "1",
        },
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "PERMISSION_DENIED"

    resp = mundo.client.patch(
        f"/api/v1{u(ANIO)}/{ESTADO['da']}",
        headers={
            **mundo.como("estconsulta", mundo.company_a),
            "If-Match": str(ESTADO["da_version"]),
        },
        json={"denominacion": "No", "motivo": "No debería"},
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "PERMISSION_DENIED"


def test_gs24_aislamiento(mundo, gobierno):
    """GS-24: cada empresa y tenant ve únicamente sus estructuras."""
    resp = mundo.get(E, "ub", mundo.company_a)
    assert resp.status_code == 404
    assert resp.json()["code"] == "COMPANY_NOT_FOUND"

    resp = mundo.get(E, "uc", mundo.company_a, tenant="T2")
    assert resp.status_code == 404
    assert resp.json()["code"] == "COMPANY_NOT_FOUND"

    resp = mundo.get(
        f"{u(ANIO)}/{ESTADO['da']}/versiones", "uab", mundo.company_b
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "GOV_UNIT_NOT_FOUND"

    resp = mundo.client.patch(
        f"/api/v1{u(ANIO)}/{ESTADO['da']}",
        headers={
            **mundo.como("uab", mundo.company_b),
            "If-Match": "1",
        },
        json={"denominacion": "Intruso", "motivo": "No debería"},
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "GOV_UNIT_NOT_FOUND"

    resp = mundo.get(f"{E}/{ANIO}", "ua", mundo.company_a)
    da = next(
        unidad
        for unidad in resp.json()["unidades"]
        if unidad["id"] == ESTADO["da"]
    )
    assert da["denominacion"] == "Dirección General de Administración"


def test_gs25_sin_put(mundo, gobierno):
    """GS-25: no hay PUT en estructuras; DELETE solo en unidades."""
    rutas = {}
    for ruta in mundo.client.app.routes:
        if ruta.path.startswith("/api/v1/gobierno/estructuras"):
            metodos = set(ruta.methods) - {"HEAD", "OPTIONS"}
            rutas.setdefault(ruta.path, set()).update(metodos)
    esperado = {
        "/api/v1/gobierno/estructuras": {"GET", "POST"},
        "/api/v1/gobierno/estructuras/{ejercicio}": {"GET"},
        "/api/v1/gobierno/estructuras/{ejercicio}/publicar": {"POST"},
        "/api/v1/gobierno/estructuras/{ejercicio}/cerrar": {"POST"},
        "/api/v1/gobierno/estructuras/{ejercicio}/exportar": {"GET"},
        "/api/v1/gobierno/estructuras/{ejercicio}/unidades": {"POST"},
        "/api/v1/gobierno/estructuras/{ejercicio}/unidades/{unidad_id}": {"PATCH", "DELETE"},
        "/api/v1/gobierno/estructuras/{ejercicio}/unidades/{unidad_id}/desactivar": {"POST"},
        "/api/v1/gobierno/estructuras/{ejercicio}/unidades/{unidad_id}/versiones": {"GET"},
    }
    assert rutas == esperado
    for metodos in rutas.values():
        assert "PUT" not in metodos


@pytest.mark.parametrize(
    "unidades_activas, documento_vinculado, ente_activo, esperado",
    [
        (0, False, False, ["UNIDADES", "DOCUMENTO_ACTO", "ENTE_ACTIVO"]),
        (1, True, True, []),
        (2, False, True, ["DOCUMENTO_ACTO"]),
        (1, True, False, ["ENTE_ACTIVO"]),
    ],
)
def test_gs26_faltantes_unidad(
    unidades_activas, documento_vinculado, ente_activo, esperado
):
    """GS-26: la función pura de faltantes respeta las reglas de completitud."""
    from app.modules.government.service_estructura import (
        faltantes_para_publicar,
    )

    assert (
        faltantes_para_publicar(
            unidades_activas, documento_vinculado, ente_activo
        )
        == esperado
    )


def test_gs27_documento_de_otra_empresa(mundo, gobierno):
    """GS-27: un vínculo de B a un documento de A no cuenta."""
    resp = mundo.post(E, "ub", mundo.company_b, {"ejercicio": 2001})
    assert resp.status_code == 201
    estructura_b = resp.json()["id"]

    with mundo.factory() as db:
        tipo = DocumentType(
            company_id=mundo.company_a,
            code="GOV-AJENO",
            name="Acto ajeno",
        )
        db.add(tipo)
        db.flush()
        doc = Document(
            company_id=mundo.company_a,
            document_type_id=tipo.id,
            title="Documento de A",
            status="ACTIVE",
        )
        db.add(doc)
        db.flush()
        db.add(
            DocumentLink(
                document_id=doc.id,
                company_id=mundo.company_b,
                document_type_id=tipo.id,
                resource_type="GovernmentStructure",
                resource_id=estructura_b,
            )
        )
        db.commit()

    resp = mundo.get(f"{E}/2001", "ub", mundo.company_b)
    assert resp.status_code == 200
    cuerpo = resp.json()
    assert cuerpo["documento_vinculado"] is False
    assert "DOCUMENTO_ACTO" in cuerpo["faltantes_para_publicar"]


def test_gs28_estructura_inexistente(mundo, gobierno):
    """GS-28: operaciones sobre un ejercicio sin estructura devuelven 404."""
    resp = mundo.get(f"{E}/2003", "ua", mundo.company_a)
    assert resp.status_code == 404
    assert resp.json()["code"] == "GOV_STRUCTURE_NOT_FOUND"

    resp = mundo.get(f"{E}/2003/exportar", "ua", mundo.company_a)
    assert resp.status_code == 404
    assert resp.json()["code"] == "GOV_STRUCTURE_NOT_FOUND"

    resp = mundo.client.post(
        f"/api/v1{E}/2003/publicar",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "1"},
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "GOV_STRUCTURE_NOT_FOUND"

    resp = mundo.client.post(
        f"/api/v1{E}/2003/cerrar",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "1"},
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "GOV_STRUCTURE_NOT_FOUND"

    resp = mundo.post(
        u(2003),
        "ua",
        mundo.company_a,
        {"codigo": "X-01", "denominacion": "Unidad inexistente", "tipo": "SEDE"},
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "GOV_STRUCTURE_NOT_FOUND"


def test_gs29_sin_cambios(mundo, gobierno):
    """GS-29: PATCH sin cambios devuelve 422 y no genera versión ni evento."""
    resp = mundo.post(E, "ub", mundo.company_b, {"ejercicio": 2002})
    assert resp.status_code == 201

    resp = mundo.post(
        u(2002),
        "ub",
        mundo.company_b,
        {"codigo": "NC-01", "denominacion": "Unidad sin cambios", "tipo": "SEDE"},
    )
    assert resp.status_code == 201
    unidad = resp.json()
    assert unidad["version"] == 1
    unidad_id = unidad["id"]

    n = len(_eventos(mundo, "GOV_UNIT_UPDATED", mundo.company_b))

    resp = mundo.client.patch(
        f"/api/v1{u(2002)}/{unidad_id}",
        headers={**mundo.como("ub", mundo.company_b), "If-Match": "1"},
        json={"denominacion": "Unidad sin cambios"},
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "GOV_UNIT_NO_CHANGES"

    resp = mundo.get(f"{u(2002)}/{unidad_id}/versiones", "ub", mundo.company_b)
    assert resp.status_code == 200
    assert resp.json()["total"] == 1

    assert len(_eventos(mundo, "GOV_UNIT_UPDATED", mundo.company_b)) == n
