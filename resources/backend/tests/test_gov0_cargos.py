"""Suite de backend para ORG03-T001: cargos con competencias y límites de firma/aprobación.

Especifica el contrato del módulo `app.modules.government` antes de que exista.
"""
from csv import reader as csv_reader
from datetime import UTC, datetime
from decimal import Decimal
from io import StringIO
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.modules.audit.models import AuditEvent
from app.modules.documents.models import Document, DocumentLink, DocumentType
from app.modules.government.models import (
    GovernmentEntity,
    GovernmentPosition,
    GovernmentPositionCompetency,
    GovernmentPositionVersion,
    GovernmentUnit,
)
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


def c(ej):
    return f"{E}/{ej}/cargos"


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


def _acto_estructura(mundo, company_id, structure_id) -> str:
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


def _acto_cargo(mundo, company_id, position_id) -> str:
    """Vincula un documento ACTIVE de la empresa al cargo."""
    with mundo.factory() as db:
        tipo = db.scalar(
            select(DocumentType).where(
                DocumentType.company_id == company_id,
                DocumentType.code == "GOV-CARGO",
            )
        )
        if tipo is None:
            tipo = DocumentType(
                company_id=company_id,
                code="GOV-CARGO",
                name="Acto del cargo",
            )
            db.add(tipo)
            db.flush()
        doc = Document(
            company_id=company_id,
            document_type_id=tipo.id,
            title="Acto del cargo",
            status="ACTIVE",
        )
        db.add(doc)
        db.flush()
        db.add(
            DocumentLink(
                document_id=doc.id,
                company_id=company_id,
                document_type_id=tipo.id,
                resource_type="GovernmentPosition",
                resource_id=position_id,
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


def test_gc01_modulo(mundo, gobierno):
    """GC-01: sin estructura en el contenedor GET devuelve 404; sin módulo 403."""
    resp = mundo.get(c(ANIO), "ua", mundo.company_a)
    assert resp.status_code == 404
    assert resp.json()["code"] == "GOV_STRUCTURE_NOT_FOUND"

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
        resp = mundo.get(c(ANIO), "ua", mundo.company_a)
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


def test_gc02_preparacion(mundo, gobierno):
    """GC-02: crea la estructura vigente y las unidades base."""
    _ente(mundo, mundo.company_a, "ACTIVO")
    resp = mundo.post(E, "ua", mundo.company_a, {"ejercicio": ANIO})
    assert resp.status_code == 201, resp.text
    ESTADO["est_anio"] = resp.json()["id"]

    resp = mundo.post(
        f"{E}/{ANIO}/unidades",
        "ua",
        mundo.company_a,
        {"codigo": "DESP", "denominacion": "Despacho del Alcalde", "tipo": "ORGANO"},
    )
    assert resp.status_code == 201, resp.text
    ESTADO["desp"] = resp.json()["id"]

    resp = mundo.post(
        f"{E}/{ANIO}/unidades",
        "ua",
        mundo.company_a,
        {
            "codigo": "DA-01",
            "denominacion": "Dirección de Administración",
            "tipo": "UNIDAD_ADMINISTRATIVA",
            "unidad_superior_id": ESTADO["desp"],
        },
    )
    assert resp.status_code == 201, resp.text
    ESTADO["da"] = resp.json()["id"]

    resp = mundo.post(
        f"{E}/{ANIO}/unidades",
        "ua",
        mundo.company_a,
        {
            "codigo": "SEDE",
            "denominacion": "Sede principal",
            "tipo": "SEDE",
            "vigente_desde": f"{ANIO}-03-01",
        },
    )
    assert resp.status_code == 201, resp.text
    ESTADO["sede"] = resp.json()["id"]
    ESTADO["sede_version"] = resp.json()["version"]

    _acto_estructura(mundo, mundo.company_a, ESTADO["est_anio"])
    resp = mundo.client.post(
        f"/api/v1{E}/{ANIO}/publicar",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "1"},
    )
    assert resp.status_code == 200, resp.text

    resp = mundo.get(c(ANIO), "ua", mundo.company_a)
    assert resp.status_code == 200, resp.text
    assert resp.json() == {
        "estructura": {"ejercicio": ANIO, "estado": "VIGENTE", "version": 2},
        "items": [],
        "total": 0,
    }


def test_gc03_crear(mundo, gobierno):
    """GC-03: crea cargos en una estructura vigente."""
    resp = mundo.post(
        c(ANIO),
        "ua",
        mundo.company_a,
        {
            "codigo": "dir-adm",
            "denominacion": "Director de Administración",
            "unidad_id": ESTADO["da"],
            "vigente_desde": f"{ANIO}-01-01",
        },
    )
    assert resp.status_code == 201, resp.text
    dir_cargo = resp.json()
    assert dir_cargo["codigo"] == "DIR-ADM"
    assert dir_cargo["estado"] == "BORRADOR"
    assert dir_cargo["version"] == 1
    assert dir_cargo["unidad_id"] == ESTADO["da"]
    assert dir_cargo["unidad_codigo"] == "DA-01"
    assert dir_cargo["unidad_denominacion"] == "Dirección de Administración"
    assert dir_cargo["competencias"] == []
    assert dir_cargo["documento_vinculado"] is False
    assert dir_cargo["faltantes_para_activar"] == ["COMPETENCIAS", "DOCUMENTO_ACTO"]
    assert dir_cargo["vigente_desde"] == f"{ANIO}-01-01"
    assert dir_cargo["vigente_hasta"] is None
    assert dir_cargo["activado_en"] is None
    ESTADO["dir"] = dir_cargo["id"]

    resp = mundo.post(
        c(ANIO),
        "ua",
        mundo.company_a,
        {
            "codigo": "JEF-TES",
            "denominacion": "Jefe de Tesorería",
            "unidad_id": ESTADO["da"],
            "vigente_desde": f"{ANIO}-01-01",
        },
    )
    assert resp.status_code == 201, resp.text
    ESTADO["jef"] = resp.json()["id"]

    resp = mundo.post(
        c(ANIO),
        "ua",
        mundo.company_a,
        {
            "codigo": "ANA-01",
            "denominacion": "Analista de Presupuesto",
            "unidad_id": ESTADO["desp"],
            "vigente_desde": f"{ANIO}-01-01",
        },
    )
    assert resp.status_code == 201, resp.text
    ESTADO["ana"] = resp.json()["id"]

    resp = mundo.post(
        c(ANIO),
        "ua",
        mundo.company_a,
        {
            "codigo": "SUP-SEDE",
            "denominacion": "Supervisor de Sede",
            "unidad_id": ESTADO["sede"],
            "vigente_desde": f"{ANIO}-03-01",
        },
    )
    assert resp.status_code == 201, resp.text
    ESTADO["sup"] = resp.json()["id"]

    assert len(_eventos(mundo, "GOV_POSITION_CREATED", mundo.company_a)) == 4

    resp = mundo.get(c(ANIO), "ua", mundo.company_a)
    assert resp.status_code == 200, resp.text
    cuerpo = resp.json()
    assert cuerpo["total"] == 4
    assert [item["codigo"] for item in cuerpo["items"]] == [
        "ANA-01",
        "DIR-ADM",
        "JEF-TES",
        "SUP-SEDE",
    ]


def test_gc04_validacion_cargo(mundo, gobierno):
    """GC-04: valida campos del cargo y reglas de negocio de creación."""
    base = {
        "codigo": "VAL-01",
        "denominacion": "Cargo de Validación",
        "unidad_id": ESTADO["da"],
        "vigente_desde": f"{ANIO}-01-01",
    }

    resp = mundo.post(c(ANIO), "ua", mundo.company_a, {**base, "codigo": "?"})
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_ERROR"
    assert "codigo" in resp.json()["field_errors"]

    resp = mundo.post(c(ANIO), "ua", mundo.company_a, {**base, "denominacion": "  "})
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_ERROR"
    assert "denominacion" in resp.json()["field_errors"]

    resp = mundo.post(
        c(ANIO),
        "ua",
        mundo.company_a,
        {**base, "vigente_desde": f"{ANTERIOR}-12-31"},
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_ERROR"
    assert "vigente_desde" in resp.json()["field_errors"]

    resp = mundo.post(c(ANIO), "ua", mundo.company_a, {**base, "nivel": 3})
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_ERROR"
    assert "nivel" in resp.json()["field_errors"]

    cuerpo_sin_unidad = {
        "codigo": "VAL-01",
        "denominacion": "Cargo de Validación",
        "vigente_desde": f"{ANIO}-01-01",
    }
    resp = mundo.post(c(ANIO), "ua", mundo.company_a, cuerpo_sin_unidad)
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_ERROR"
    assert "unidad_id" in resp.json()["field_errors"]

    resp = mundo.post(
        c(ANIO),
        "ua",
        mundo.company_a,
        {**base, "unidad_id": ESTADO["sede"], "vigente_desde": f"{ANIO}-02-01"},
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_ERROR"
    assert "vigente_desde" in resp.json()["field_errors"]

    resp = mundo.post(
        c(ANIO),
        "ua",
        mundo.company_a,
        {**base, "unidad_id": str(uuid4())},
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "GOV_POSITION_INVALID_UNIT"

    resp = mundo.post(c(ANIO), "ua", mundo.company_a, {**base, "codigo": "DIR-ADM"})
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "GOV_POSITION_CODE_DUPLICATE"

    resp = mundo.get(c(ANIO), "ua", mundo.company_a)
    assert resp.status_code == 200, resp.text
    assert resp.json()["total"] == 4


def test_gc05_competencias_borrador(mundo, gobierno):
    """GC-05: otorga competencias sobre un cargo en borrador."""
    dir_id = ESTADO["dir"]
    resp = mundo.client.post(
        f"/api/v1{c(ANIO)}/{dir_id}/competencias",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "1"},
        json={
            "accion": "APROBAR",
            "materia": "CONTRATACIONES",
            "tipo_limite": "MONTO",
            "monto": "50000.00",
            "moneda": "USD",
            "fundamento": "Reglamento interno, art. 12",
        },
    )
    assert resp.status_code == 201, resp.text
    cuerpo = resp.json()
    assert cuerpo["version"] == 2
    comp_aprobar = next(
        comp
        for comp in cuerpo["competencias"]
        if comp["accion"] == "APROBAR" and comp["materia"] == "CONTRATACIONES"
    )
    assert comp_aprobar["tipo_limite"] == "MONTO"
    assert comp_aprobar["monto"] == "50000.00"
    assert comp_aprobar["moneda"] == "USD"
    assert comp_aprobar["fundamento"] == "Reglamento interno, art. 12"
    ESTADO["comp_aprobar"] = comp_aprobar["id"]

    resp = mundo.client.post(
        f"/api/v1{c(ANIO)}/{dir_id}/competencias",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "2"},
        json={
            "accion": "FIRMAR",
            "materia": "TESORERIA",
            "tipo_limite": "SIN_LIMITE",
        },
    )
    assert resp.status_code == 201, resp.text
    cuerpo = resp.json()
    assert cuerpo["version"] == 3
    comp_firmar = next(
        comp
        for comp in cuerpo["competencias"]
        if comp["accion"] == "FIRMAR" and comp["materia"] == "TESORERIA"
    )
    assert comp_firmar["monto"] is None
    assert comp_firmar["moneda"] is None
    ESTADO["comp_firmar"] = comp_firmar["id"]

    resp = mundo.client.post(
        f"/api/v1{c(ANIO)}/{dir_id}/competencias",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "3"},
        json={
            "accion": "APROBAR",
            "materia": "CONTRATACIONES",
            "tipo_limite": "MONTO",
            "monto": "1.00",
            "moneda": "VES",
        },
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "GOV_COMPETENCY_DUPLICATE"

    resp = mundo.get(f"{c(ANIO)}/{dir_id}", "ua", mundo.company_a)
    assert resp.status_code == 200, resp.text
    cuerpo = resp.json()
    assert cuerpo["version"] == 3
    assert cuerpo["faltantes_para_activar"] == ["DOCUMENTO_ACTO"]

    assert len(_eventos(mundo, "GOV_COMPETENCY_GRANTED", mundo.company_a)) == 2


def test_gc06_vectores_limite(mundo, gobierno):
    """GC-06: valida vectores de límite y acepta límites válidos."""
    jef_id = ESTADO["jef"]
    base = {
        "accion": "REGISTRAR",
        "materia": "CONTABILIDAD",
        "tipo_limite": "MONTO",
        "monto": "100.00",
        "moneda": "VES",
    }

    casos_invalidos = [
        {**base, "monto": 100},
        {**base, "monto": "0"},
        {**base, "monto": "0.00"},
        {**base, "monto": "-5.00"},
        {**base, "monto": "1.234"},
        {**base, "monto": "12345678901234567.00"},
        {**base, "monto": "1e5"},
        {**base, "monto": " 100.00"},
        {**base, "monto": "1.000,00"},
        {k: v for k, v in base.items() if k != "monto"},
        {k: v for k, v in base.items() if k != "moneda"},
        {**base, "moneda": "GBP"},
        {"accion": "REGISTRAR", "materia": "CONTABILIDAD", "tipo_limite": "SIN_LIMITE", "monto": "10.00"},
        {"accion": "REGISTRAR", "materia": "CONTABILIDAD", "tipo_limite": "SIN_LIMITE", "moneda": "VES"},
        {**base, "accion": "BORRAR"},
        {**base, "materia": "NOMINA"},
        {**base, "tipo_limite": "PORCENTAJE"},
        {**base, "x": 1},
    ]
    for cuerpo in casos_invalidos:
        resp = mundo.client.post(
            f"/api/v1{c(ANIO)}/{jef_id}/competencias",
            headers={**mundo.como("ua", mundo.company_a), "If-Match": "1"},
            json=cuerpo,
        )
        assert resp.status_code == 422, f"{cuerpo} -> {resp.text}"
        assert resp.json()["code"] == "VALIDATION_ERROR", f"{cuerpo} -> {resp.text}"

    resp = mundo.get(f"{c(ANIO)}/{jef_id}", "ua", mundo.company_a)
    assert resp.status_code == 200, resp.text
    cuerpo = resp.json()
    assert cuerpo["version"] == 1
    assert cuerpo["competencias"] == []

    resp = mundo.client.post(
        f"/api/v1{c(ANIO)}/{jef_id}/competencias",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "1"},
        json={**base, "monto": "0.01"},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["version"] == 2
    assert any(comp["monto"] == "0.01" for comp in resp.json()["competencias"])

    resp = mundo.client.post(
        f"/api/v1{c(ANIO)}/{jef_id}/competencias",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "2"},
        json={
            "accion": "CUSTODIAR",
            "materia": "BIENES",
            "tipo_limite": "MONTO",
            "monto": "9999999999999999.99",
            "moneda": "EUR",
        },
    )
    assert resp.status_code == 201, resp.text
    cuerpo = resp.json()
    assert cuerpo["version"] == 3
    assert any(
        comp["monto"] == "9999999999999999.99"
        for comp in cuerpo["competencias"]
    )

    resp = mundo.client.post(
        f"/api/v1{c(ANIO)}/{jef_id}/competencias",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "3"},
        json={
            "accion": "AUDITAR",
            "materia": "EXPEDIENTE",
            "tipo_limite": "MONTO",
            "monto": "1500",
            "moneda": "VES",
        },
    )
    assert resp.status_code == 201, resp.text
    cuerpo = resp.json()
    assert cuerpo["version"] == 4
    assert any(comp["monto"] == "1500.00" for comp in cuerpo["competencias"])

    with mundo.factory() as db:
        competencia = db.scalar(
            select(GovernmentPositionCompetency).where(
                GovernmentPositionCompetency.position_id == jef_id,
                GovernmentPositionCompetency.action == "CUSTODIAR",
            )
        )
        assert competencia is not None
        assert competencia.limit_amount == Decimal("9999999999999999.99")
        assert competencia.limit_currency == "EUR"
        assert competencia.limit_type == "MONTO"

    resp = mundo.get(f"{c(ANIO)}/{jef_id}", "ua", mundo.company_a)
    assert resp.status_code == 200, resp.text
    assert resp.json()["version"] == 4


def test_gc07_if_match(mundo, gobierno):
    """GC-07: exige If-Match y rechaza versiones obsoletas."""
    dir_id = ESTADO["dir"]
    resp = mundo.client.post(
        f"/api/v1{c(ANIO)}/{dir_id}/competencias",
        headers=mundo.como("ua", mundo.company_a),
        json={
            "accion": "PAGAR",
            "materia": "TESORERIA",
            "tipo_limite": "SIN_LIMITE",
        },
    )
    assert resp.status_code == 428, resp.text
    assert resp.json()["code"] == "GOV_POSITION_IF_MATCH_REQUIRED"

    resp = mundo.client.post(
        f"/api/v1{c(ANIO)}/{dir_id}/competencias",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "1"},
        json={
            "accion": "PAGAR",
            "materia": "TESORERIA",
            "tipo_limite": "SIN_LIMITE",
        },
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "GOV_POSITION_STALE"
    assert resp.json()["details"]["version_actual"] == 3

    resp = mundo.client.patch(
        f"/api/v1{c(ANIO)}/{dir_id}",
        headers=mundo.como("ua", mundo.company_a),
        json={"denominacion": "X cargo"},
    )
    assert resp.status_code == 428, resp.text
    assert resp.json()["code"] == "GOV_POSITION_IF_MATCH_REQUIRED"

    resp = mundo.get(f"{c(ANIO)}/{dir_id}", "ua", mundo.company_a)
    assert resp.status_code == 200, resp.text
    assert resp.json()["version"] == 3


def test_gc08_faltantes(mundo, gobierno):
    """GC-08: exige requisitos completos antes de activar."""
    dir_id = ESTADO["dir"]
    resp = mundo.client.post(
        f"/api/v1{c(ANIO)}/{dir_id}/activar",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "3"},
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "GOV_POSITION_INCOMPLETE"
    assert resp.json()["details"]["faltantes"] == ["DOCUMENTO_ACTO"]

    ana_id = ESTADO["ana"]
    resp = mundo.client.post(
        f"/api/v1{c(ANIO)}/{ana_id}/activar",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "1"},
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "GOV_POSITION_INCOMPLETE"
    assert resp.json()["details"]["faltantes"] == ["COMPETENCIAS", "DOCUMENTO_ACTO"]

    resp = mundo.get(f"{c(ANIO)}/{dir_id}", "ua", mundo.company_a)
    assert resp.status_code == 200, resp.text
    assert resp.json()["version"] == 3
    assert resp.json()["estado"] == "BORRADOR"


def test_gc09_documento_de_otra_empresa(mundo, gobierno):
    """GC-09: un vínculo de A a un documento de B no cuenta."""
    dir_id = ESTADO["dir"]
    with mundo.factory() as db:
        tipo = DocumentType(
            company_id=mundo.company_b,
            code="GOV-AJENO-C",
            name="Acto ajeno",
        )
        db.add(tipo)
        db.flush()
        doc = Document(
            company_id=mundo.company_b,
            document_type_id=tipo.id,
            title="Documento de B",
            status="ACTIVE",
        )
        db.add(doc)
        db.flush()
        db.add(
            DocumentLink(
                document_id=doc.id,
                company_id=mundo.company_a,
                document_type_id=tipo.id,
                resource_type="GovernmentPosition",
                resource_id=dir_id,
            )
        )
        db.commit()

    resp = mundo.get(f"{c(ANIO)}/{dir_id}", "ua", mundo.company_a)
    assert resp.status_code == 200, resp.text
    cuerpo = resp.json()
    assert cuerpo["documento_vinculado"] is False
    assert "DOCUMENTO_ACTO" in cuerpo["faltantes_para_activar"]


def test_gc10_activar(mundo, gobierno):
    """GC-10: activa cargos con requisitos completos."""
    dir_id = ESTADO["dir"]
    _acto_cargo(mundo, mundo.company_a, dir_id)

    resp = mundo.get(f"{c(ANIO)}/{dir_id}", "ua", mundo.company_a)
    assert resp.status_code == 200, resp.text
    cuerpo = resp.json()
    assert cuerpo["documento_vinculado"] is True
    assert cuerpo["faltantes_para_activar"] == []

    resp = mundo.client.post(
        f"/api/v1{c(ANIO)}/{dir_id}/activar",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "3"},
    )
    assert resp.status_code == 200, resp.text
    cuerpo = resp.json()
    assert cuerpo["estado"] == "VIGENTE"
    assert cuerpo["version"] == 4
    assert cuerpo["activado_en"] is not None

    assert len(_eventos(mundo, "GOV_POSITION_ACTIVATED", mundo.company_a)) == 1

    resp = mundo.client.post(
        f"/api/v1{c(ANIO)}/{dir_id}/activar",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "4"},
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "GOV_POSITION_INVALID_STATE"

    jef_id = ESTADO["jef"]
    _acto_cargo(mundo, mundo.company_a, jef_id)
    resp = mundo.client.post(
        f"/api/v1{c(ANIO)}/{jef_id}/activar",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "4"},
    )
    assert resp.status_code == 200, resp.text
    cuerpo = resp.json()
    assert cuerpo["estado"] == "VIGENTE"
    assert cuerpo["version"] == 5
    ESTADO["jef_version"] = 5


def test_gc11_cambios_vigor(mundo, gobierno):
    """GC-11: controla cambios sobre un cargo vigente."""
    dir_id = ESTADO["dir"]
    resp = mundo.client.patch(
        f"/api/v1{c(ANIO)}/{dir_id}",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "4"},
        json={"denominacion": "Director General de Administración"},
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "GOV_POSITION_REASON_REQUIRED"

    resp = mundo.client.patch(
        f"/api/v1{c(ANIO)}/{dir_id}",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "4"},
        json={"denominacion": "Director General de Administración", "motivo": "x"},
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "GOV_POSITION_REASON_REQUIRED"

    resp = mundo.client.patch(
        f"/api/v1{c(ANIO)}/{dir_id}",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "4"},
        json={"codigo": "DIR-ADM2", "motivo": "Cambio de código"},
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "GOV_POSITION_FIELD_LOCKED"
    assert resp.json()["details"]["campos"] == ["codigo"]

    resp = mundo.client.patch(
        f"/api/v1{c(ANIO)}/{dir_id}",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "4"},
        json={"vigente_desde": f"{ANIO}-02-01", "motivo": "Cambio de inicio"},
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "GOV_POSITION_FIELD_LOCKED"
    assert resp.json()["details"]["campos"] == ["vigente_desde"]

    resp = mundo.client.patch(
        f"/api/v1{c(ANIO)}/{dir_id}",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "4"},
        json={"denominacion": "Director de Administración", "motivo": "Sin cambio real"},
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "GOV_POSITION_NO_CHANGES"

    resp = mundo.client.patch(
        f"/api/v1{c(ANIO)}/{dir_id}",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "4"},
        json={"unidad_id": str(uuid4()), "motivo": "Traslado inválido"},
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "GOV_POSITION_INVALID_UNIT"

    resp = mundo.client.patch(
        f"/api/v1{c(ANIO)}/{dir_id}",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "4"},
        json={
            "denominacion": "Director General de Administración",
            "motivo": "Reorganización aprobada",
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["version"] == 5

    resp = mundo.client.patch(
        f"/api/v1{c(ANIO)}/{dir_id}",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "5"},
        json={"unidad_id": ESTADO["desp"], "motivo": "Traslado al despacho"},
    )
    assert resp.status_code == 200, resp.text
    cuerpo = resp.json()
    assert cuerpo["unidad_codigo"] == "DESP"
    assert cuerpo["version"] == 6

    eventos = _eventos(mundo, "GOV_POSITION_UPDATED", mundo.company_a)
    assert len(eventos) == 2
    primero = eventos[0]
    assert primero.reason == "Reorganización aprobada"
    assert primero.before["denominacion"] == "Director de Administración"
    assert primero.after["denominacion"] == "Director General de Administración"


def test_gc12_cambiar_limite(mundo, gobierno):
    """GC-12: modifica y retira competencias con reglas de negocio."""
    dir_id = ESTADO["dir"]
    comp_id = ESTADO["comp_aprobar"]
    ruta_competencia = f"/api/v1{c(ANIO)}/{dir_id}/competencias/{comp_id}"

    resp = mundo.client.patch(
        ruta_competencia,
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "6"},
        json={
            "tipo_limite": "MONTO",
            "monto": "75000.00",
            "moneda": "USD",
            "fundamento": "Reglamento interno, art. 12",
        },
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "GOV_POSITION_REASON_REQUIRED"

    resp = mundo.client.patch(
        ruta_competencia,
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "6"},
        json={
            "tipo_limite": "MONTO",
            "monto": "75000.00",
            "moneda": "USD",
            "fundamento": "Reglamento interno, art. 12",
            "motivo": "Ajuste del límite aprobado",
        },
    )
    assert resp.status_code == 200, resp.text
    cuerpo = resp.json()
    assert cuerpo["version"] == 7
    comp = next(cp for cp in cuerpo["competencias"] if cp["id"] == comp_id)
    assert comp["monto"] == "75000.00"

    resp = mundo.client.patch(
        ruta_competencia,
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "7"},
        json={
            "tipo_limite": "MONTO",
            "monto": "75000.00",
            "moneda": "USD",
            "fundamento": "Reglamento interno, art. 12",
            "motivo": "Ajuste del límite aprobado",
        },
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "GOV_COMPETENCY_NO_CHANGES"

    resp = mundo.client.patch(
        ruta_competencia,
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "7"},
        json={"tipo_limite": "SIN_LIMITE", "monto": "5.00", "motivo": "Incoherente"},
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_ERROR"

    resp = mundo.client.patch(
        ruta_competencia,
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "7"},
        json={"accion": "PAGAR", "tipo_limite": "SIN_LIMITE", "motivo": "No se acepta"},
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_ERROR"
    assert "accion" in resp.json()["field_errors"]

    resp = mundo.client.patch(
        f"/api/v1{c(ANIO)}/{dir_id}/competencias/{uuid4()}",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "7"},
        json={"tipo_limite": "SIN_LIMITE", "motivo": "No existe nada"},
    )
    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == "GOV_COMPETENCY_NOT_FOUND"

    eventos = _eventos(mundo, "GOV_COMPETENCY_CHANGED", mundo.company_a)
    assert len(eventos) == 1
    evento = eventos[0]
    assert evento.before["monto"] == "50000.00"
    assert evento.after["monto"] == "75000.00"
    assert evento.reason == "Ajuste del límite aprobado"

    resp = mundo.get(f"{c(ANIO)}/{dir_id}", "ua", mundo.company_a)
    assert resp.status_code == 200, resp.text
    assert resp.json()["version"] == 7


def test_gc13_autoridad_preparador(mundo, gobierno):
    """GC-13: un usuario con view+edit no puede cambiar la autoridad de un cargo vigente."""
    dir_id = ESTADO["dir"]
    desp_id = ESTADO["desp"]

    with mundo.factory() as db:
        usuario = identity_service.create_user(
            db,
            tenant_id=mundo.t1,
            username="cargoprep",
            email="cargoprep@example.test",
            password=PASSWORD,
            created_by=None,
        )
        rol = Role(
            code="R_CARGO_PREP",
            name="Preparador de cargos",
            tenant_id=mundo.t1,
            protected=False,
            status="ACTIVE",
        )
        db.add(rol)
        db.flush()
        for accion in ("view", "edit"):
            permiso = db.scalar(
                select(Permission).where(
                    Permission.resource == "gobierno_cargos",
                    Permission.action == accion,
                )
            )
            db.add(RolePermission(role_id=rol.id, permission_id=permiso.id))
        db.add(UserRole(user_id=usuario.id, role_id=rol.id, company_id=None))
        db.add(UserScope(user_id=usuario.id, company_id=mundo.company_a))
        db.commit()

    resp = mundo.client.post(
        f"/api/v1{c(ANIO)}/{dir_id}/competencias",
        headers={**mundo.como("cargoprep", mundo.company_a), "If-Match": "7"},
        json={
            "accion": "SOLICITAR",
            "materia": "PRESUPUESTO",
            "tipo_limite": "SIN_LIMITE",
            "motivo": "Nueva competencia",
        },
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "GOV_POSITION_AUTHORITY_REQUIRED"

    resp = mundo.client.patch(
        f"/api/v1{c(ANIO)}/{dir_id}/competencias/{ESTADO['comp_aprobar']}",
        headers={**mundo.como("cargoprep", mundo.company_a), "If-Match": "7"},
        json={
            "tipo_limite": "MONTO",
            "monto": "90000.00",
            "moneda": "USD",
            "motivo": "Subir el límite",
        },
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "GOV_POSITION_AUTHORITY_REQUIRED"

    resp = mundo.client.post(
        f"/api/v1{c(ANIO)}/{dir_id}/competencias/{ESTADO['comp_firmar']}/retirar",
        headers={**mundo.como("cargoprep", mundo.company_a), "If-Match": "7"},
        json={"motivo": "Retirar la firma"},
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "GOV_POSITION_AUTHORITY_REQUIRED"

    resp = mundo.client.post(
        f"/api/v1{c(ANIO)}/{ESTADO['ana']}/activar",
        headers={**mundo.como("cargoprep", mundo.company_a), "If-Match": "1"},
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "PERMISSION_DENIED"

    resp = mundo.client.post(
        f"/api/v1{c(ANIO)}/{dir_id}/desactivar",
        headers={**mundo.como("cargoprep", mundo.company_a), "If-Match": "7"},
        json={"fecha": f"{ANIO}-12-31", "motivo": "No debería"},
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "PERMISSION_DENIED"

    resp = mundo.client.patch(
        f"/api/v1{c(ANIO)}/{dir_id}",
        headers={**mundo.como("cargoprep", mundo.company_a), "If-Match": "7"},
        json={
            "denominacion": "Director General de Administración y Finanzas",
            "motivo": "Cambio de denominación",
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["version"] == 8

    resp = mundo.post(
        c(ANIO),
        "cargoprep",
        mundo.company_a,
        {
            "codigo": "PREP-01",
            "denominacion": "Cargo preparado",
            "unidad_id": desp_id,
            "vigente_desde": f"{ANIO}-01-01",
        },
    )
    assert resp.status_code == 201, resp.text
    ESTADO["prep"] = resp.json()["id"]

    resp = mundo.client.post(
        f"/api/v1{c(ANIO)}/{ESTADO['prep']}/competencias",
        headers={**mundo.como("cargoprep", mundo.company_a), "If-Match": "1"},
        json={
            "accion": "PAGAR",
            "materia": "TESORERIA",
            "tipo_limite": "MONTO",
            "monto": "100.00",
            "moneda": "VES",
        },
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["version"] == 2

    resp = mundo.get(f"{c(ANIO)}/{dir_id}", "ua", mundo.company_a)
    assert resp.status_code == 200, resp.text
    cuerpo = resp.json()
    assert cuerpo["version"] == 8
    assert len(cuerpo["competencias"]) == 2
    comp_aprobar = next(
        comp
        for comp in cuerpo["competencias"]
        if comp["id"] == ESTADO["comp_aprobar"]
    )
    assert comp_aprobar["monto"] == "75000.00"

    assert len(_eventos(mundo, "GOV_COMPETENCY_GRANTED", mundo.company_a)) == 6


def test_gc14_agregar_retirar_vigor(mundo, gobierno):
    """GC-14: agrega y retira competencias de un cargo vigente con reglas completas."""
    dir_id = ESTADO["dir"]
    jef_id = ESTADO["jef"]

    resp = mundo.client.post(
        f"/api/v1{c(ANIO)}/{dir_id}/competencias",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "8"},
        json={
            "accion": "SOLICITAR",
            "materia": "PRESUPUESTO",
            "tipo_limite": "SIN_LIMITE",
        },
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "GOV_POSITION_REASON_REQUIRED"

    resp = mundo.client.post(
        f"/api/v1{c(ANIO)}/{dir_id}/competencias",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "8"},
        json={
            "accion": "SOLICITAR",
            "materia": "PRESUPUESTO",
            "tipo_limite": "SIN_LIMITE",
            "motivo": "Competencia otorgada por resolución",
        },
    )
    assert resp.status_code == 201, resp.text
    cuerpo = resp.json()
    assert cuerpo["version"] == 9
    assert len(cuerpo["competencias"]) == 3
    comp_solicitar = next(
        comp
        for comp in cuerpo["competencias"]
        if comp["accion"] == "SOLICITAR"
    )
    ESTADO["comp_solicitar"] = comp_solicitar["id"]

    resp = mundo.client.post(
        f"/api/v1{c(ANIO)}/{dir_id}/competencias/{ESTADO['comp_solicitar']}/retirar",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "9"},
        json={},
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "GOV_POSITION_REASON_REQUIRED"

    resp = mundo.client.post(
        f"/api/v1{c(ANIO)}/{dir_id}/competencias/{ESTADO['comp_solicitar']}/retirar",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "9"},
        json={"motivo": "Competencia retirada por resolución"},
    )
    assert resp.status_code == 200, resp.text
    cuerpo = resp.json()
    assert cuerpo["version"] == 10
    assert len(cuerpo["competencias"]) == 2
    assert all(comp["accion"] != "SOLICITAR" for comp in cuerpo["competencias"])

    eventos = _eventos(mundo, "GOV_COMPETENCY_REVOKED", mundo.company_a)
    assert len(eventos) == 1
    assert eventos[0].before["accion"] == "SOLICITAR"
    assert eventos[0].reason == "Competencia retirada por resolución"

    resp = mundo.get(f"{c(ANIO)}/{jef_id}", "ua", mundo.company_a)
    assert resp.status_code == 200, resp.text
    comp_ids = [comp["id"] for comp in resp.json()["competencias"]]
    assert len(comp_ids) == 3

    resp = mundo.client.post(
        f"/api/v1{c(ANIO)}/{jef_id}/competencias/{comp_ids[0]}/retirar",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "5"},
        json={"motivo": "Retiro por reorganización"},
    )
    assert resp.status_code == 200, resp.text

    resp = mundo.client.post(
        f"/api/v1{c(ANIO)}/{jef_id}/competencias/{comp_ids[1]}/retirar",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "6"},
        json={"motivo": "Retiro por reorganización"},
    )
    assert resp.status_code == 200, resp.text

    resp = mundo.client.post(
        f"/api/v1{c(ANIO)}/{jef_id}/competencias/{comp_ids[2]}/retirar",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "7"},
        json={"motivo": "Retiro por reorganización"},
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "GOV_COMPETENCY_LAST"

    resp = mundo.client.post(
        f"/api/v1{c(ANIO)}/{jef_id}/competencias/{uuid4()}/retirar",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "7"},
        json={"motivo": "No existe nada"},
    )
    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == "GOV_COMPETENCY_NOT_FOUND"

    resp = mundo.get(f"{c(ANIO)}/{jef_id}", "ua", mundo.company_a)
    assert resp.status_code == 200, resp.text
    cuerpo = resp.json()
    assert cuerpo["version"] == 7
    assert len(cuerpo["competencias"]) == 1


def test_gc15_historial(mundo, gobierno):
    """GC-15: expone el historial de versiones de un cargo."""
    dir_id = ESTADO["dir"]
    resp = mundo.get(f"{c(ANIO)}/{dir_id}/versiones", "ua", mundo.company_a)
    assert resp.status_code == 200, resp.text
    cuerpo = resp.json()
    items = cuerpo["items"]
    assert cuerpo["total"] == 10
    assert [item["version"] for item in items] == list(range(1, 11))
    assert items[0]["datos"]["competencias"] == []
    assert items[0]["datos"]["estado"] == "BORRADOR"
    assert {
        "codigo",
        "denominacion",
        "unidad_id",
        "unidad_codigo",
        "estado",
        "vigente_desde",
        "vigente_hasta",
        "competencias",
    } <= set(items[0]["datos"])
    assert items[3]["estado"] == "VIGENTE"
    assert items[4]["motivo"] == "Reorganización aprobada"
    assert len(items[-1]["datos"]["competencias"]) == 2


def test_gc16_desactivar(mundo, gobierno):
    """GC-16: desactiva un cargo vigente y bloquea escrituras posteriores."""
    sup_id = ESTADO["sup"]
    jef_id = ESTADO["jef"]

    resp = mundo.client.post(
        f"/api/v1{c(ANIO)}/{sup_id}/desactivar",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "1"},
        json={"fecha": f"{ANIO}-12-31", "motivo": "No aplica aquí"},
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "GOV_POSITION_INVALID_STATE"

    resp = mundo.client.post(
        f"/api/v1{c(ANIO)}/{jef_id}/desactivar",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "7"},
        json={"fecha": f"{SIGUIENTE}-01-01", "motivo": "Supresión del cargo"},
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_ERROR"
    assert "fecha" in resp.json()["field_errors"]

    resp = mundo.client.post(
        f"/api/v1{c(ANIO)}/{jef_id}/desactivar",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "7"},
        json={"fecha": f"{ANTERIOR}-12-31", "motivo": "Supresión del cargo"},
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_ERROR"
    assert "fecha" in resp.json()["field_errors"]

    resp = mundo.client.post(
        f"/api/v1{c(ANIO)}/{jef_id}/desactivar",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "7"},
        json={"fecha": f"{ANIO}-12-31"},
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "GOV_POSITION_REASON_REQUIRED"

    resp = mundo.client.post(
        f"/api/v1{c(ANIO)}/{jef_id}/desactivar",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "7"},
        json={"fecha": f"{ANIO}-12-31", "motivo": "Supresión del cargo"},
    )
    assert resp.status_code == 200, resp.text
    cuerpo = resp.json()
    assert cuerpo["estado"] == "INACTIVO"
    assert cuerpo["vigente_hasta"] == f"{ANIO}-12-31"
    assert cuerpo["version"] == 8

    resp = mundo.client.patch(
        f"/api/v1{c(ANIO)}/{jef_id}",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "8"},
        json={"denominacion": "Otro nombre", "motivo": "No debería"},
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "GOV_POSITION_INVALID_STATE"

    resp = mundo.client.post(
        f"/api/v1{c(ANIO)}/{jef_id}/competencias",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "8"},
        json={
            "accion": "PAGAR",
            "materia": "TESORERIA",
            "tipo_limite": "SIN_LIMITE",
            "motivo": "No debería",
        },
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "GOV_POSITION_INVALID_STATE"

    eventos = _eventos(mundo, "GOV_POSITION_DEACTIVATED", mundo.company_a)
    assert len(eventos) == 1
    assert eventos[0].reason == "Supresión del cargo"


def test_gc17_eliminar(mundo, gobierno):
    """GC-17: elimina solo cargos en borrador y protege vínculos documentales."""
    ana_id = ESTADO["ana"]
    sup_id = ESTADO["sup"]
    dir_id = ESTADO["dir"]

    resp = mundo.client.delete(
        f"/api/v1{c(ANIO)}/{ana_id}",
        headers=mundo.como("ua", mundo.company_a),
    )
    assert resp.status_code == 428, resp.text
    assert resp.json()["code"] == "GOV_POSITION_IF_MATCH_REQUIRED"

    resp = mundo.client.delete(
        f"/api/v1{c(ANIO)}/{ana_id}",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "1"},
    )
    assert resp.status_code == 204, resp.text

    resp = mundo.get(f"{c(ANIO)}/{ana_id}", "ua", mundo.company_a)
    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == "GOV_POSITION_NOT_FOUND"

    with mundo.factory() as db:
        assert (
            db.scalar(
                select(GovernmentPositionCompetency).where(
                    GovernmentPositionCompetency.position_id == ana_id
                )
            )
            is None
        )
        assert (
            db.scalar(
                select(GovernmentPositionVersion).where(
                    GovernmentPositionVersion.position_id == ana_id
                )
            )
            is None
        )

    eventos = _eventos(mundo, "GOV_POSITION_DELETED", mundo.company_a)
    assert len(eventos) == 1

    _acto_cargo(mundo, mundo.company_a, sup_id)
    resp = mundo.client.delete(
        f"/api/v1{c(ANIO)}/{sup_id}",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "1"},
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "GOV_POSITION_HAS_DOCUMENTS"

    resp = mundo.client.delete(
        f"/api/v1{c(ANIO)}/{dir_id}",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "10"},
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "GOV_POSITION_INVALID_STATE"


def test_gc18_unidad_con_cargos(mundo, gobierno):
    """GC-18: una unidad con cargos no puede desactivarse ni eliminarse."""
    sede_id = ESTADO["sede"]
    resp = mundo.get(f"{E}/{ANIO}", "ua", mundo.company_a)
    assert resp.status_code == 200, resp.text
    version_sede = next(
        unidad["version"]
        for unidad in resp.json()["unidades"]
        if unidad["id"] == sede_id
    )

    resp = mundo.client.post(
        f"/api/v1{E}/{ANIO}/unidades/{sede_id}/desactivar",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(version_sede)},
        json={"fecha": f"{ANIO}-12-31", "motivo": "Cierre de la sede"},
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "GOV_UNIT_HAS_POSITIONS"

    resp = mundo.get(f"{E}/{ANIO}", "ua", mundo.company_a)
    assert resp.status_code == 200, resp.text
    unidad_sede = next(
        unidad
        for unidad in resp.json()["unidades"]
        if unidad["id"] == sede_id
    )
    assert unidad_sede["estado"] == "ACTIVA"


def test_gc19_csv(mundo, gobierno):
    """GC-19: exporta cargos y competencias a CSV normalizado."""
    resp = mundo.get(f"{c(ANIO)}/exportar", "ua", mundo.company_a)
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("text/csv")
    assert f"cargos-{ANIO}.csv" in resp.headers["content-disposition"]

    filas = list(csv_reader(StringIO(resp.text)))
    cabecera = [
        "codigo_cargo",
        "denominacion",
        "codigo_unidad",
        "estado",
        "vigente_desde",
        "vigente_hasta",
        "accion",
        "materia",
        "tipo_limite",
        "monto",
        "moneda",
        "fundamento",
    ]
    assert filas[0] == cabecera
    assert [fila[0] for fila in filas[1:]] == [
        "DIR-ADM",
        "DIR-ADM",
        "JEF-TES",
        "PREP-01",
        "SUP-SEDE",
    ]
    assert filas[1] == [
        "DIR-ADM",
        "Director General de Administración y Finanzas",
        "DESP",
        "VIGENTE",
        f"{ANIO}-01-01",
        "",
        "APROBAR",
        "CONTRATACIONES",
        "MONTO",
        "75000.00",
        "USD",
        "Reglamento interno, art. 12",
    ]
    assert filas[2] == [
        "DIR-ADM",
        "Director General de Administración y Finanzas",
        "DESP",
        "VIGENTE",
        f"{ANIO}-01-01",
        "",
        "FIRMAR",
        "TESORERIA",
        "SIN_LIMITE",
        "",
        "",
        "",
    ]
    assert filas[3][3] == "INACTIVO"
    assert filas[3][5] == f"{ANIO}-12-31"
    assert filas[5] == [
        "SUP-SEDE",
        "Supervisor de Sede",
        "SEDE",
        "BORRADOR",
        f"{ANIO}-03-01",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
    ]

    eventos = _eventos(mundo, "GOV_POSITIONS_EXPORTED", mundo.company_a)
    assert eventos[-1].after["filas"] == 5


def test_gc20_copia(mundo, gobierno):
    """GC-20: copia cargos vigentes a un ejercicio nuevo."""
    resp = mundo.post(
        E,
        "ua",
        mundo.company_a,
        {"ejercicio": SIGUIENTE, "copiar_de": ANIO},
    )
    assert resp.status_code == 201, resp.text
    ESTADO["est_sig"] = resp.json()["id"]
    desp_sig = next(
        unidad["id"]
        for unidad in resp.json()["unidades"]
        if unidad["codigo"] == "DESP"
    )
    ESTADO["desp_sig"] = desp_sig

    resp = mundo.get(c(SIGUIENTE), "ua", mundo.company_a)
    assert resp.status_code == 200, resp.text
    cuerpo = resp.json()
    assert cuerpo["total"] == 1
    cargo = cuerpo["items"][0]
    assert cargo["codigo"] == "DIR-ADM"
    assert cargo["estado"] == "BORRADOR"
    assert cargo["version"] == 1
    assert cargo["unidad_codigo"] == "DESP"
    assert cargo["unidad_id"] == desp_sig
    assert cargo["unidad_id"] != ESTADO["desp"]
    assert cargo["vigente_desde"] == f"{SIGUIENTE}-01-01"
    assert cargo["documento_vinculado"] is False
    assert cargo["faltantes_para_activar"] == [
        "ESTRUCTURA_VIGENTE",
        "DOCUMENTO_ACTO",
    ]
    assert sorted(
        (k["accion"], k["materia"], k["tipo_limite"], k["monto"], k["moneda"])
        for k in cargo["competencias"]
    ) == [
        ("APROBAR", "CONTRATACIONES", "MONTO", "75000.00", "USD"),
        ("FIRMAR", "TESORERIA", "SIN_LIMITE", None, None),
    ]

    resp = mundo.get(
        f"{c(SIGUIENTE)}/{cargo['id']}/versiones",
        "ua",
        mundo.company_a,
    )
    assert resp.status_code == 200, resp.text
    cuerpo = resp.json()
    assert cuerpo["total"] == 1
    assert cuerpo["items"][0]["motivo"] == f"Copia del ejercicio {ANIO}"

    eventos = _eventos(mundo, "GOV_STRUCTURE_CREATED", mundo.company_a)
    assert eventos[-1].after["cargos_copiados"] == 1


def test_gc21_ejercicio_cerrado(mundo, gobierno):
    """GC-21: una estructura cerrada impide toda escritura de cargos."""
    resp = mundo.post(E, "ua", mundo.company_a, {"ejercicio": ANTERIOR})
    assert resp.status_code == 201, resp.text
    est_ant = resp.json()["id"]

    resp = mundo.post(
        f"{E}/{ANTERIOR}/unidades",
        "ua",
        mundo.company_a,
        {"codigo": "U-ANT", "denominacion": "Unidad anterior", "tipo": "ORGANO"},
    )
    assert resp.status_code == 201, resp.text
    u_ant = resp.json()["id"]
    u_ant_version = resp.json()["version"]

    resp = mundo.post(
        c(ANTERIOR),
        "ua",
        mundo.company_a,
        {
            "codigo": "CAR-ANT",
            "denominacion": "Cargo del ejercicio anterior",
            "unidad_id": u_ant,
        },
    )
    assert resp.status_code == 201, resp.text
    car_ant = resp.json()["id"]
    assert resp.json()["vigente_desde"] == f"{ANTERIOR}-01-01"

    resp = mundo.client.post(
        f"/api/v1{c(ANTERIOR)}/{car_ant}/competencias",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "1"},
        json={
            "accion": "PAGAR",
            "materia": "TESORERIA",
            "tipo_limite": "MONTO",
            "monto": "1000.00",
            "moneda": "VES",
        },
    )
    assert resp.status_code == 201, resp.text

    resp = mundo.client.post(
        f"/api/v1{c(ANTERIOR)}/{car_ant}/activar",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "2"},
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "GOV_POSITION_INCOMPLETE"
    assert resp.json()["details"]["faltantes"] == [
        "ESTRUCTURA_VIGENTE",
        "DOCUMENTO_ACTO",
    ]

    resp = mundo.client.delete(
        f"/api/v1{E}/{ANTERIOR}/unidades/{u_ant}",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(u_ant_version)},
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "GOV_UNIT_HAS_POSITIONS"

    _acto_estructura(mundo, mundo.company_a, est_ant)
    resp = mundo.client.post(
        f"/api/v1{E}/{ANTERIOR}/publicar",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "1"},
    )
    assert resp.status_code == 200, resp.text

    _acto_cargo(mundo, mundo.company_a, car_ant)
    resp = mundo.client.post(
        f"/api/v1{c(ANTERIOR)}/{car_ant}/activar",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "2"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["estado"] == "VIGENTE"
    assert resp.json()["version"] == 3

    resp = mundo.client.post(
        f"/api/v1{E}/{ANTERIOR}/cerrar",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "2"},
    )
    assert resp.status_code == 200, resp.text

    resp = mundo.post(
        c(ANTERIOR),
        "ua",
        mundo.company_a,
        {
            "codigo": "CAR-NUEVO",
            "denominacion": "Cargo nuevo",
            "unidad_id": u_ant,
        },
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "GOV_STRUCTURE_CLOSED"

    resp = mundo.client.patch(
        f"/api/v1{c(ANTERIOR)}/{car_ant}",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "3"},
        json={"denominacion": "Otro", "motivo": "No debería"},
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "GOV_STRUCTURE_CLOSED"

    resp = mundo.client.post(
        f"/api/v1{c(ANTERIOR)}/{car_ant}/competencias",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "3"},
        json={
            "accion": "FIRMAR",
            "materia": "TESORERIA",
            "tipo_limite": "SIN_LIMITE",
            "motivo": "No debería",
        },
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "GOV_STRUCTURE_CLOSED"

    resp = mundo.client.post(
        f"/api/v1{c(ANTERIOR)}/{car_ant}/desactivar",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "3"},
        json={"fecha": f"{ANTERIOR}-12-31", "motivo": "No debería"},
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "GOV_STRUCTURE_CLOSED"

    resp = mundo.get(c(ANTERIOR), "ua", mundo.company_a)
    assert resp.status_code == 200, resp.text
    cuerpo = resp.json()
    assert cuerpo["estructura"]["estado"] == "CERRADA"
    assert cuerpo["items"][0]["estado"] == "VIGENTE"


def test_gc22_consulta(mundo, gobierno):
    """GC-22: un usuario con solo view consulta pero no escribe."""
    dir_id = ESTADO["dir"]
    desp_id = ESTADO["desp"]

    with mundo.factory() as db:
        usuario = identity_service.create_user(
            db,
            tenant_id=mundo.t1,
            username="cargoconsulta",
            email="cargoconsulta@example.test",
            password=PASSWORD,
            created_by=None,
        )
        rol = Role(
            code="R_CARGO_CONSULTA",
            name="Consulta de cargos",
            tenant_id=mundo.t1,
            protected=False,
            status="ACTIVE",
        )
        db.add(rol)
        db.flush()
        permiso = db.scalar(
            select(Permission).where(
                Permission.resource == "gobierno_cargos",
                Permission.action == "view",
            )
        )
        db.add(RolePermission(role_id=rol.id, permission_id=permiso.id))
        db.add(UserRole(user_id=usuario.id, role_id=rol.id, company_id=None))
        db.add(UserScope(user_id=usuario.id, company_id=mundo.company_a))
        db.commit()

    resp = mundo.get(c(ANIO), "cargoconsulta", mundo.company_a)
    assert resp.status_code == 200, resp.text
    resp = mundo.get(f"{c(ANIO)}/{dir_id}", "cargoconsulta", mundo.company_a)
    assert resp.status_code == 200, resp.text
    resp = mundo.get(
        f"{c(ANIO)}/{dir_id}/versiones",
        "cargoconsulta",
        mundo.company_a,
    )
    assert resp.status_code == 200, resp.text
    resp = mundo.get(f"{c(ANIO)}/exportar", "cargoconsulta", mundo.company_a)
    assert resp.status_code == 200, resp.text

    resp = mundo.post(
        c(ANIO),
        "cargoconsulta",
        mundo.company_a,
        {"codigo": "NO-01", "denominacion": "No debería", "unidad_id": desp_id},
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "PERMISSION_DENIED"

    resp = mundo.client.patch(
        f"/api/v1{c(ANIO)}/{dir_id}",
        headers={**mundo.como("cargoconsulta", mundo.company_a), "If-Match": "10"},
        json={"denominacion": "No", "motivo": "No debería"},
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "PERMISSION_DENIED"

    resp = mundo.client.post(
        f"/api/v1{c(ANIO)}/{ESTADO['sup']}/activar",
        headers={**mundo.como("cargoconsulta", mundo.company_a), "If-Match": "1"},
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "PERMISSION_DENIED"

    resp = mundo.client.post(
        f"/api/v1{c(ANIO)}/{dir_id}/competencias",
        headers={**mundo.como("cargoconsulta", mundo.company_a), "If-Match": "10"},
        json={
            "accion": "PAGAR",
            "materia": "TESORERIA",
            "tipo_limite": "SIN_LIMITE",
            "motivo": "No debería",
        },
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "PERMISSION_DENIED"


def test_gc23_aislamiento(mundo, gobierno):
    """GC-23: aísla cargos y unidades entre empresas y tenants."""
    _ente(mundo, mundo.company_b, "ACTIVO")
    resp = mundo.post(E, "ub", mundo.company_b, {"ejercicio": ANIO})
    assert resp.status_code == 201, resp.text

    resp = mundo.post(
        f"{E}/{ANIO}/unidades",
        "ub",
        mundo.company_b,
        {"codigo": "B-01", "denominacion": "Unidad de B", "tipo": "ORGANO"},
    )
    assert resp.status_code == 201, resp.text

    resp = mundo.get(c(ANIO), "ub", mundo.company_a)
    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == "COMPANY_NOT_FOUND"

    resp = mundo.get(c(ANIO), "uc", mundo.company_a, tenant="T2")
    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == "COMPANY_NOT_FOUND"

    dir_id = ESTADO["dir"]
    resp = mundo.get(f"{c(ANIO)}/{dir_id}", "uab", mundo.company_b)
    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == "GOV_POSITION_NOT_FOUND"

    resp = mundo.get(f"{c(ANIO)}/{dir_id}/versiones", "uab", mundo.company_b)
    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == "GOV_POSITION_NOT_FOUND"

    resp = mundo.client.patch(
        f"/api/v1{c(ANIO)}/{dir_id}",
        headers={**mundo.como("uab", mundo.company_b), "If-Match": "10"},
        json={"denominacion": "Intruso", "motivo": "No debería"},
    )
    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == "GOV_POSITION_NOT_FOUND"

    resp = mundo.client.post(
        f"/api/v1{c(ANIO)}/{dir_id}/competencias",
        headers={**mundo.como("uab", mundo.company_b), "If-Match": "10"},
        json={
            "accion": "PAGAR",
            "materia": "TESORERIA",
            "tipo_limite": "SIN_LIMITE",
            "motivo": "No debería",
        },
    )
    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == "GOV_POSITION_NOT_FOUND"

    resp = mundo.post(
        c(ANIO),
        "uab",
        mundo.company_b,
        {
            "codigo": "B-CAR",
            "denominacion": "Cargo de B",
            "unidad_id": ESTADO["da"],
        },
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "GOV_POSITION_INVALID_UNIT"

    resp = mundo.get(f"{c(ANIO)}/exportar", "ub", mundo.company_b)
    assert resp.status_code == 200, resp.text
    filas = list(csv_reader(StringIO(resp.text)))
    assert len(filas) == 1

    resp = mundo.get(f"{c(ANIO)}/{dir_id}", "ua", mundo.company_a)
    assert resp.status_code == 200, resp.text
    cuerpo = resp.json()
    assert cuerpo["denominacion"] == "Director General de Administración y Finanzas"
    assert cuerpo["version"] == 10


def test_gc24_rutas(mundo, gobierno):
    """GC-24: expone exactamente el conjunto esperado de rutas de cargos."""
    rutas = {}
    orden = []
    for ruta in mundo.client.app.routes:
        path = getattr(ruta, "path", "")
        if path.startswith("/api/v1/gobierno/estructuras/{ejercicio}/cargos"):
            metodos = set(getattr(ruta, "methods", None) or set()) - {
                "HEAD",
                "OPTIONS",
            }
            rutas.setdefault(path, set()).update(metodos)
            orden.append(path)

    esperado = {
        "/api/v1/gobierno/estructuras/{ejercicio}/cargos": {"GET", "POST"},
        "/api/v1/gobierno/estructuras/{ejercicio}/cargos/exportar": {"GET"},
        "/api/v1/gobierno/estructuras/{ejercicio}/cargos/{cargo_id}": {
            "GET",
            "PATCH",
            "DELETE",
        },
        "/api/v1/gobierno/estructuras/{ejercicio}/cargos/{cargo_id}/activar": {
            "POST"
        },
        "/api/v1/gobierno/estructuras/{ejercicio}/cargos/{cargo_id}/desactivar": {
            "POST"
        },
        "/api/v1/gobierno/estructuras/{ejercicio}/cargos/{cargo_id}/competencias": {
            "POST"
        },
        "/api/v1/gobierno/estructuras/{ejercicio}/cargos/{cargo_id}/competencias/{competencia_id}": {
            "PATCH"
        },
        "/api/v1/gobierno/estructuras/{ejercicio}/cargos/{cargo_id}/competencias/{competencia_id}/retirar": {
            "POST"
        },
        "/api/v1/gobierno/estructuras/{ejercicio}/cargos/{cargo_id}/versiones": {
            "GET"
        },
    }
    assert rutas == esperado
    for metodos in rutas.values():
        assert "PUT" not in metodos

    assert orden.index(
        "/api/v1/gobierno/estructuras/{ejercicio}/cargos/exportar"
    ) < orden.index(
        "/api/v1/gobierno/estructuras/{ejercicio}/cargos/{cargo_id}"
    )


@pytest.mark.parametrize(
    "estructura_vigente, competencias, documento, esperado",
    [
        (False, 0, False, ["ESTRUCTURA_VIGENTE", "COMPETENCIAS", "DOCUMENTO_ACTO"]),
        (True, 1, True, []),
        (True, 0, True, ["COMPETENCIAS"]),
        (False, 2, True, ["ESTRUCTURA_VIGENTE"]),
        (True, 3, False, ["DOCUMENTO_ACTO"]),
    ],
)
def test_gc25_faltantes_cargo(
    estructura_vigente,
    competencias,
    documento,
    esperado,
):
    """GC-25: calcula correctamente los faltantes para activar."""
    from app.modules.government.service_cargos import faltantes_para_activar

    assert (
        faltantes_para_activar(estructura_vigente, competencias, documento)
        == esperado
    )


def test_gc26_restricciones_bd(mundo, gobierno):
    """GC-26: impone restricciones de base de datos en competencias y cargos."""
    dir_id = ESTADO["dir"]

    with mundo.factory() as db:
        with pytest.raises(IntegrityError):
            db.add(
                GovernmentPositionCompetency(
                    position_id=dir_id,
                    company_id=mundo.company_a,
                    action="PAGAR",
                    subject="TESORERIA",
                    limit_type="MONTO",
                    limit_amount=None,
                    limit_currency="USD",
                )
            )
            db.flush()
        db.rollback()

    with mundo.factory() as db:
        with pytest.raises(IntegrityError):
            db.add(
                GovernmentPositionCompetency(
                    position_id=dir_id,
                    company_id=mundo.company_a,
                    action="PAGAR",
                    subject="TESORERIA",
                    limit_type="SIN_LIMITE",
                    limit_amount=Decimal("1.00"),
                    limit_currency=None,
                )
            )
            db.flush()
        db.rollback()

    with mundo.factory() as db:
        with pytest.raises(IntegrityError):
            db.add(
                GovernmentPositionCompetency(
                    position_id=dir_id,
                    company_id=mundo.company_a,
                    action="PAGAR",
                    subject="TESORERIA",
                    limit_type="MONTO",
                    limit_amount=Decimal("0"),
                    limit_currency="VES",
                )
            )
            db.flush()
        db.rollback()


    with mundo.factory() as db:
        unidad_desp_sig = db.scalar(
            select(GovernmentUnit.id).where(
                GovernmentUnit.structure_id == ESTADO["est_sig"],
                GovernmentUnit.code == "DESP",
            )
        )
        with pytest.raises(IntegrityError):
            db.add(
                GovernmentPosition(
                    structure_id=ESTADO["est_anio"],
                    company_id=mundo.company_a,
                    unit_id=unidad_desp_sig,
                    code="BD-01",
                    name="Prueba de base",
                    status="BORRADOR",
                    valid_from=hoy_de_negocio().replace(month=1, day=1),
                    version=1,
                )
            )
            db.flush()
        db.rollback()


def test_gc27_unidad_inactiva(mundo, gobierno):
    """GC-27: un cargo no se registra ni se traslada a una unidad INACTIVA."""
    resp = mundo.post(
        f"{E}/{ANIO}/unidades",
        "ua",
        mundo.company_a,
        {
            "codigo": "INA-01",
            "denominacion": "Unidad que se suprime",
            "tipo": "DEPENDENCIA",
            "motivo": "Alta para la prueba",
        },
    )
    assert resp.status_code == 201, resp.text
    unidad = resp.json()
    unidad_id = unidad["id"]
    resp = mundo.client.post(
        f"/api/v1{E}/{ANIO}/unidades/{unidad_id}/desactivar",
        headers={
            **mundo.como("ua", mundo.company_a),
            "If-Match": str(unidad["version"]),
        },
        json={"fecha": f"{ANIO}-12-31", "motivo": "Supresión de la unidad"},
    )
    assert resp.status_code == 200, resp.text
    resp = mundo.client.post(
        f"/api/v1{c(ANIO)}",
        headers=mundo.como("ua", mundo.company_a),
        json={
            "codigo": "INA-CAR",
            "denominacion": "Cargo en unidad inactiva",
            "unidad_id": unidad_id,
            "vigente_desde": f"{ANIO}-01-01",
        },
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "GOV_POSITION_INVALID_UNIT"
    resp = mundo.client.patch(
        f"/api/v1{c(ANIO)}/{ESTADO['dir']}",
        headers={
            **mundo.como("ua", mundo.company_a),
            "If-Match": "10",
        },
        json={
            "unidad_id": unidad_id,
            "motivo": "Traslado a unidad inactiva",
        },
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "GOV_POSITION_INVALID_UNIT"
    resp = mundo.client.get(
        f"/api/v1{c(ANIO)}/{ESTADO['dir']}",
        headers=mundo.como("ua", mundo.company_a),
    )
    assert resp.status_code == 200, resp.text
    cargo = resp.json()
    assert cargo["version"] == 10
    assert cargo["unidad_codigo"] == "DESP"
