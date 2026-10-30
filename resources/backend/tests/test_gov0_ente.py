"""Suite de backend para GOV0-T001: Configurar el ente.

Especifica el contrato del módulo `app.modules.government` antes de que exista.
"""
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.modules.audit.models import AuditEvent
from app.modules.documents.models import Document, DocumentLink, DocumentType
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

BASE = {
    "denominacion": "Alcaldía del Municipio Demo",
    "siglas": "AMD",
    "rif": "G-20000000-0",
    "nivel_territorial": "MUNICIPAL",
    "forma_organizativa": "ADMINISTRACION_CENTRAL",
    "entidad_federal": "Lara",
    "municipio": "Iribarren",
    "acto_tipo": "ORDENANZA",
    "acto_numero": "1",
    "acto_fecha": "2020-01-15",
    "acto_publicacion": "Gaceta Municipal N.º 1 del 15/01/2020",
}


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


def _documento_activo(mundo, company_id, entity_id) -> str:
    """Inserta un documento ACTIVE vinculado al ente y devuelve su id."""
    with mundo.factory() as db:
        tipo = db.scalar(
            select(DocumentType).where(
                DocumentType.company_id == company_id,
                DocumentType.code == "GOV-ACTO",
            )
        )
        if tipo is None:
            tipo = DocumentType(
                company_id=company_id,
                code="GOV-ACTO",
                name="Acto de creación del ente",
            )
            db.add(tipo)
            db.flush()
        doc = Document(
            company_id=company_id,
            document_type_id=tipo.id,
            title="Acto de creación",
            status="ACTIVE",
        )
        db.add(doc)
        db.flush()
        db.add(
            DocumentLink(
                document_id=doc.id,
                company_id=company_id,
                document_type_id=tipo.id,
                resource_type="GovernmentEntity",
                resource_id=entity_id,
            )
        )
        db.commit()
        return str(doc.id)


def _contar_eventos(mundo, action, company_id) -> int:
    """Cuenta eventos de auditoría de una acción en una empresa."""
    with mundo.factory() as db:
        return db.scalar(
            select(func.count())
            .select_from(AuditEvent)
            .where(
                AuditEvent.action == action,
                AuditEvent.company_id == company_id,
            )
        )


def _ultimo_evento(mundo, action, company_id):
    """Devuelve el último evento de auditoría de una acción en una empresa."""
    with mundo.factory() as db:
        return db.scalar(
            select(AuditEvent)
            .where(
                AuditEvent.action == action,
                AuditEvent.company_id == company_id,
            )
            .order_by(AuditEvent.event_time.desc())
            .limit(1)
        )


def test_ge01_modulo_habilitado_y_entitlement(mundo, gobierno):
    """GE-01: el módulo responde habilitado y sin entitlement devuelve 403."""
    resp = mundo.get("/gobierno/modulo", "ua", mundo.company_a)
    assert resp.status_code == 200
    assert resp.json() == {"habilitado": True}

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
        resp = mundo.get("/gobierno/modulo", "ua", mundo.company_a)
        assert resp.status_code == 200
        assert resp.json() == {"habilitado": False}

        resp = mundo.get("/gobierno/ente", "ua", mundo.company_a)
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


def test_ge02_vacio(mundo, gobierno):
    """GE-02: sin ente configurado, GET devuelve 404 GOV_ENTITY_NOT_FOUND."""
    resp = mundo.get("/gobierno/ente", "ua", mundo.company_a)
    assert resp.status_code == 404
    assert resp.json()["code"] == "GOV_ENTITY_NOT_FOUND"


def test_ge03_alta_en_borrador(mundo, gobierno):
    """GE-03: el alta mínima crea un ente BORRADOR versión 1 con faltantes."""
    resp = mundo.post(
        "/gobierno/ente",
        "ua",
        mundo.company_a,
        {"denominacion": BASE["denominacion"]},
    )
    assert resp.status_code == 201
    cuerpo = resp.json()
    assert cuerpo["estado"] == "BORRADOR"
    assert cuerpo["version"] == 1
    assert cuerpo["documento_vinculado"] is False
    faltantes = cuerpo["faltantes_para_activar"]
    for codigo in (
        "NIVEL_TERRITORIAL",
        "FORMA_ORGANIZATIVA",
        "ACTO_TIPO",
        "ACTO_NUMERO",
        "ACTO_FECHA",
        "ACTO_PUBLICACION",
        "DOCUMENTO_ACTO",
    ):
        assert codigo in faltantes
    assert _contar_eventos(mundo, "GOV_ENTITY_CREATED", mundo.company_a) == 1


def test_ge04_duplicado(mundo, gobierno):
    """GE-04: un segundo alta en la misma empresa devuelve 409."""
    resp = mundo.post(
        "/gobierno/ente",
        "ua",
        mundo.company_a,
        {"denominacion": "Otro ente"},
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "GOV_ENTITY_ALREADY_EXISTS"


def test_ge05_validacion(mundo, gobierno):
    """GE-05: cuerpos inválidos devuelven 422 y no crean ente en B."""
    casos = [
        ({"denominacion": "   "}, "denominacion"),
        ({"denominacion": "Ente de validación", "rif": "123"}, "rif"),
        (
            {"denominacion": "Ente de validación", "nivel_territorial": "PLANETARIO"},
            "nivel_territorial",
        ),
        (
            {
                "denominacion": "Ente de validación",
                "acto_fecha": (hoy_de_negocio() + timedelta(days=1)).isoformat(),
            },
            "acto_fecha",
        ),
        (
            {"denominacion": "Ente de validación", "tenant_id": "intruso"},
            "tenant_id",
        ),
    ]
    for cuerpo, campo in casos:
        resp = mundo.post("/gobierno/ente", "ub", mundo.company_b, cuerpo)
        assert resp.status_code == 422, f"cuerpo aceptado: {cuerpo} -> {resp.json()}"
        assert resp.json()["code"] == "VALIDATION_ERROR", (
            f"código inesperado para {cuerpo}: {resp.json()}"
        )
        assert campo in resp.json()["field_errors"], (
            f"campo {campo!r} no rechazado en {cuerpo}: {resp.json()}"
        )

    resp = mundo.get("/gobierno/ente", "ub", mundo.company_b)
    assert resp.status_code == 404
    assert resp.json()["code"] == "GOV_ENTITY_NOT_FOUND"


def test_ge06_if_match_en_borrador(mundo, gobierno):
    """GE-06: PATCH exige If-Match y versión vigente; edición incrementa versión."""
    resp = mundo.get("/gobierno/ente", "ua", mundo.company_a)
    ente = resp.json()
    version = ente["version"]

    resp = mundo.client.patch(
        "/api/v1/gobierno/ente",
        headers=mundo.como("ua", mundo.company_a),
        json={"siglas": "AMD2"},
    )
    assert resp.status_code == 428
    assert resp.json()["code"] == "GOV_ENTITY_IF_MATCH_REQUIRED"

    resp = mundo.client.patch(
        "/api/v1/gobierno/ente",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "99"},
        json={"siglas": "AMD2"},
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "GOV_ENTITY_STALE"

    cuerpo = {k: v for k, v in BASE.items() if k != "denominacion"}
    resp = mundo.client.patch(
        "/api/v1/gobierno/ente",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(version)},
        json=cuerpo,
    )
    assert resp.status_code == 200
    assert resp.json()["version"] == version + 1
    assert _contar_eventos(mundo, "GOV_ENTITY_UPDATED", mundo.company_a) == 1


def test_ge07_activacion(mundo, gobierno):
    """GE-07: activar incompleto falla; con documento vinculado activa."""
    resp = mundo.get("/gobierno/ente", "ua", mundo.company_a)
    ente = resp.json()
    version = ente["version"]

    resp = mundo.client.post(
        "/api/v1/gobierno/ente/activar",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(version)},
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "GOV_ENTITY_INCOMPLETE"
    assert resp.json()["details"]["faltantes"] == ["DOCUMENTO_ACTO"]

    _documento_activo(mundo, mundo.company_a, ente["id"])

    resp = mundo.client.post(
        "/api/v1/gobierno/ente/activar",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(version)},
    )
    assert resp.status_code == 200
    cuerpo = resp.json()
    assert cuerpo["estado"] == "ACTIVO"
    assert cuerpo["activado_en"] is not None
    assert cuerpo["documento_vinculado"] is True
    assert _contar_eventos(mundo, "GOV_ENTITY_ACTIVATED", mundo.company_a) == 1


@pytest.mark.parametrize(
    "datos, documento, esperados, no_esperados, exactos",
    [
        (BASE, True, [], [], []),
        (
            {**BASE, "forma_organizativa": "INSTITUTO_PUBLICO"},
            True,
            ["ORGANO_ADSCRIPCION"],
            [],
            None,
        ),
        (
            {**BASE, "nivel_territorial": "ESTADAL", "municipio": None, "entidad_federal": None},
            True,
            ["ENTIDAD_FEDERAL"],
            ["MUNICIPIO"],
            None,
        ),
        (
            {**BASE, "nivel_territorial": "NACIONAL", "municipio": None, "entidad_federal": None},
            True,
            [],
            ["ENTIDAD_FEDERAL", "MUNICIPIO"],
            None,
        ),
        (BASE, False, [], [], ["DOCUMENTO_ACTO"]),
    ],
)
def test_ge08_faltantes_unidad(datos, documento, esperados, no_esperados, exactos):
    """GE-08: la función pura de faltantes respeta las reglas de completitud."""
    from app.modules.government.service import faltantes_para_activar

    resultado = faltantes_para_activar(datos, documento)
    if exactos is not None:
        assert resultado == exactos
    for codigo in esperados:
        assert codigo in resultado
    for codigo in no_esperados:
        assert codigo not in resultado


def test_ge09_modificacion_del_activo(mundo, gobierno):
    """GE-09: en ACTIVO el motivo es obligatorio y no se puede dejar incompleto."""
    resp = mundo.get("/gobierno/ente", "ua", mundo.company_a)
    ente = resp.json()
    version = ente["version"]

    resp = mundo.client.patch(
        "/api/v1/gobierno/ente",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(version)},
        json={"siglas": "AMDEMO"},
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "GOV_ENTITY_REASON_REQUIRED"

    resp = mundo.client.patch(
        "/api/v1/gobierno/ente",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(version)},
        json={"siglas": "AMDEMO", "motivo": "x"},
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "GOV_ENTITY_REASON_REQUIRED"

    resp = mundo.client.patch(
        "/api/v1/gobierno/ente",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(version)},
        json={"siglas": "AMDEMO", "motivo": "Error material en las siglas"},
    )
    assert resp.status_code == 200
    cuerpo = resp.json()
    assert cuerpo["version"] == version + 1
    assert cuerpo["siglas"] == "AMDEMO"

    evento = _ultimo_evento(mundo, "GOV_ENTITY_UPDATED", mundo.company_a)
    assert evento.reason == "Error material en las siglas"

    version = cuerpo["version"]
    resp = mundo.client.patch(
        "/api/v1/gobierno/ente",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(version)},
        json={"acto_numero": None, "motivo": "Prueba de incompleto"},
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "GOV_ENTITY_INCOMPLETE"

    resp = mundo.get("/gobierno/ente", "ua", mundo.company_a)
    assert resp.json()["acto_numero"] == BASE["acto_numero"]


def test_ge10_doble_activacion(mundo, gobierno):
    """GE-10: activar un ente ya ACTIVO devuelve 409 GOV_ENTITY_INVALID_STATE."""
    resp = mundo.get("/gobierno/ente", "ua", mundo.company_a)
    ente = resp.json()
    resp = mundo.client.post(
        "/api/v1/gobierno/ente/activar",
        headers={
            **mundo.como("ua", mundo.company_a),
            "If-Match": str(ente["version"]),
        },
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "GOV_ENTITY_INVALID_STATE"


def test_ge11_historial(mundo, gobierno):
    """GE-11: el historial lista todas las versiones y no expone mutaciones."""
    resp = mundo.get("/gobierno/ente/versiones", "ua", mundo.company_a)
    assert resp.status_code == 200
    cuerpo = resp.json()
    assert cuerpo["total"] == 4
    items = cuerpo["items"]
    assert [item["version"] for item in items] == [1, 2, 3, 4]
    ultimo = items[-1]
    assert ultimo["motivo"] == "Error material en las siglas"
    assert ultimo["datos"]["siglas"] == "AMDEMO"

    rutas_prohibidas = {"PUT", "PATCH", "DELETE"}
    for ruta in mundo.client.app.routes:
        if ruta.path.startswith("/api/v1/gobierno/ente/versiones"):
            assert ruta.methods.isdisjoint(rutas_prohibidas)


def test_ge12_permisos(mundo, gobierno):
    """GE-12: un usuario con permiso de solo lectura no puede editar ni activar."""
    with mundo.factory() as db:
        usuario = identity_service.create_user(
            db,
            tenant_id=mundo.t1,
            username="gobconsulta",
            email="gobconsulta@example.test",
            password=PASSWORD,
            created_by=None,
        )
        rol = Role(
            code="R_GOV_CONSULTA",
            name="Consulta Gobierno",
            tenant_id=mundo.t1,
            protected=False,
            status="ACTIVE",
        )
        db.add(rol)
        db.flush()
        permiso = db.scalar(
            select(Permission).where(
                Permission.resource == "gobierno_ente",
                Permission.action == "view",
            )
        )
        db.add(RolePermission(role_id=rol.id, permission_id=permiso.id))
        db.add(UserRole(user_id=usuario.id, role_id=rol.id, company_id=None))
        db.add(UserScope(user_id=usuario.id, company_id=mundo.company_a))
        db.commit()

    resp = mundo.get("/gobierno/ente", "gobconsulta", mundo.company_a)
    assert resp.status_code == 200

    resp = mundo.get("/gobierno/ente", "ua", mundo.company_a)
    version = resp.json()["version"]

    resp = mundo.client.patch(
        "/api/v1/gobierno/ente",
        headers={
            **mundo.como("gobconsulta", mundo.company_a),
            "If-Match": str(version),
        },
        json={"siglas": "NO", "motivo": "No debería poder"},
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "PERMISSION_DENIED"

    resp = mundo.client.post(
        "/api/v1/gobierno/ente/activar",
        headers={
            **mundo.como("gobconsulta", mundo.company_a),
            "If-Match": str(version),
        },
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "PERMISSION_DENIED"

    resp = mundo.get("/gobierno/ente/versiones", "gobconsulta", mundo.company_a)
    assert resp.status_code == 200


def test_ge13_aislamiento(mundo, gobierno):
    """GE-13: cada empresa y tenant ve únicamente su propio ente."""
    resp = mundo.get("/gobierno/ente", "ub", mundo.company_a)
    assert resp.status_code == 404
    assert resp.json()["code"] == "COMPANY_NOT_FOUND"

    resp = mundo.get("/gobierno/ente", "uc", mundo.company_a, tenant="T2")
    assert resp.status_code == 404
    assert resp.json()["code"] == "COMPANY_NOT_FOUND"

    resp = mundo.get("/gobierno/ente", "uab", mundo.company_b)
    assert resp.status_code == 404
    assert resp.json()["code"] == "GOV_ENTITY_NOT_FOUND"

    resp = mundo.post(
        "/gobierno/ente",
        "uab",
        mundo.company_b,
        {"denominacion": "Instituto Municipal Demo"},
    )
    assert resp.status_code == 201

    resp = mundo.get("/gobierno/ente", "ua", mundo.company_a)
    assert resp.json()["siglas"] == "AMDEMO"


def test_ge14_documento_ajeno(mundo, gobierno):
    """GE-14: un documento de otra empresa no satisface DOCUMENTO_ACTO."""
    resp = mundo.get("/gobierno/ente", "uab", mundo.company_b)
    ente_b = resp.json()
    _documento_activo(mundo, mundo.company_a, ente_b["id"])

    resp = mundo.get("/gobierno/ente", "uab", mundo.company_b)
    cuerpo = resp.json()
    assert cuerpo["documento_vinculado"] is False
    assert "DOCUMENTO_ACTO" in cuerpo["faltantes_para_activar"]
