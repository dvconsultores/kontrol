"""Suite de backend para DOC02-T001a1: actos administrativos (primer tercio).

Especifica el contrato del módulo `app.modules.government` para actos
administrativos antes de que el código de producción exista.
"""
from csv import reader as csv_reader
from datetime import UTC, date, datetime, timedelta
from io import StringIO
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.modules.audit.models import AuditEvent
from app.modules.documents.models import (
    Document,
    DocumentLink,
    DocumentType,
    DocumentVersion,
    StoredFile,
)
from app.modules.government.models import (
    GovernmentAct,
    GovernmentEntity,
)
from app.modules.identity_access import service as identity_service
from app.modules.identity_access.mfa_policy import (
    SENSITIVE,
    STANDARD,
    classify,
)
from app.modules.identity_access.models import (
    Permission,
    Role,
    RolePermission,
    UserRole,
    UserScope,
)
from app.modules.licensing import service as licensing_service
from app.modules.licensing.models import LicenseEntitlementSnapshot
from app.shared.audit_catalog import catalog
from app.shared.clock import hoy_de_negocio
from tests.conftest_multicompany import PASSWORD

pytest_plugins = ("tests.conftest_multicompany",)

HOY = hoy_de_negocio()
ANIO = HOY.year
ANTERIOR = ANIO - 1
A = "/gobierno/actos"
ESTADO = {}


def c(ej):
    return f"/gobierno/estructuras/{ej}/cargos"


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


def _doc_activo(mundo, company_id, *, resource_id=None, status="ACTIVE") -> str:
    """Crea un Document ACTIVE sin versión; opcionalmente lo vincula al acto."""
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
                name="Documento del acto administrativo",
            )
            db.add(tipo)
            db.flush()
        doc = Document(
            company_id=company_id,
            document_type_id=tipo.id,
            title="Documento del acto administrativo",
            status=status,
        )
        db.add(doc)
        db.flush()
        if resource_id is not None:
            db.add(
                DocumentLink(
                    document_id=doc.id,
                    company_id=company_id,
                    document_type_id=tipo.id,
                    resource_type="GovernmentAct",
                    resource_id=resource_id,
                )
            )
        db.commit()
        return str(doc.id)


def _doc_con_version(mundo, company_id, *, resource_id) -> str:
    """Crea StoredFile + DocumentVersion ACTIVE + Document ACTIVE vinculado."""
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
                name="Documento del acto administrativo",
            )
            db.add(tipo)
            db.flush()
        stored = StoredFile(
            company_id=company_id,
            original_name="acto.pdf",
            mime_type="application/pdf",
            size=1024,
            sha256=uuid4().hex,
            storage_key=uuid4().hex,
            storage_provider="FILESYSTEM",
            security_status="CLEAN",
            status="AVAILABLE",
            uploaded_at=datetime.now(UTC),
        )
        db.add(stored)
        db.flush()
        doc = Document(
            company_id=company_id,
            document_type_id=tipo.id,
            title="Documento del acto con versión",
            status="ACTIVE",
        )
        db.add(doc)
        db.flush()
        version = DocumentVersion(
            document_id=doc.id,
            company_id=company_id,
            version_number=1,
            stored_file_id=stored.id,
            sha256=stored.sha256,
            status="ACTIVE",
        )
        db.add(version)
        db.flush()
        doc.current_version_id = version.id
        db.add(
            DocumentLink(
                document_id=doc.id,
                company_id=company_id,
                document_type_id=tipo.id,
                resource_type="GovernmentAct",
                resource_id=resource_id,
            )
        )
        db.commit()
        return str(doc.id)


def _cuerpo(**cambios) -> dict:
    """Cuerpo base válido de alta con el cargo DIR-ADM de company_a."""
    cuerpo = {
        "tipo": "RESOLUCION",
        "numero": "DA-001-ACTOS",
        "fecha": HOY.isoformat(),
        "lugar": "Caracas",
        "cargo_id": ESTADO["dir_adm"],
        "competencia": {"accion": "APROBAR", "materia": "CONTRATACIONES"},
        "fundamento_competencia": "Reglamento interno, art. 12",
        "funcionario": "Ana Pérez",
        "titularidad": "TITULAR",
        "caracter": "PARTICULAR",
        "destinatario": "Proveedor Ejemplo, C.A.",
        "asunto": "Adjudicación de servicio",
        "hechos": "Hechos de prueba",
        "fundamentos": "Fundamentos de prueba",
        "decision": "Decisión de prueba",
    }
    cuerpo.update(cambios)
    return cuerpo


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


def _publicar_estructura(mundo, company_id, estructura_id, usuario) -> None:
    """Vincula el acto de la estructura y la publica con If-Match 1."""
    _acto_estructura(mundo, company_id, estructura_id)
    resp = mundo.client.post(
        f"/api/v1/gobierno/estructuras/{ANIO}/publicar",
        headers={**mundo.como(usuario, company_id), "If-Match": "1"},
    )
    assert resp.status_code == 200, resp.text


def _crear_cargo_y_competencias(
    mundo,
    company_id,
    unidad_id,
    codigo,
    denominacion,
    competencias,
    *,
    usuario="ua",
    activar=True,
):
    """Crea un cargo, añade competencias en cadena y opcionalmente lo activa."""
    resp = mundo.post(
        c(ANIO),
        usuario,
        company_id,
        {
            "codigo": codigo,
            "denominacion": denominacion,
            "unidad_id": unidad_id,
            "vigente_desde": f"{ANIO}-01-01",
        },
    )
    assert resp.status_code == 201, resp.text
    cargo = resp.json()
    position_id = cargo["id"]
    version = cargo["version"]

    for accion, materia in competencias:
        resp = mundo.client.post(
            f"/api/v1{c(ANIO)}/{position_id}/competencias",
            headers={**mundo.como(usuario, company_id), "If-Match": str(version)},
            json={
                "accion": accion,
                "materia": materia,
                "tipo_limite": "SIN_LIMITE",
            },
        )
        assert resp.status_code == 201, resp.text
        version = resp.json()["version"]

    _acto_cargo(mundo, company_id, position_id)
    if activar:
        resp = mundo.client.post(
            f"/api/v1{c(ANIO)}/{position_id}/activar",
            headers={**mundo.como(usuario, company_id), "If-Match": str(version)},
        )
        assert resp.status_code == 200, resp.text
        return resp.json()
    return cargo


def test_ga01_modulo_y_consulta(mundo, gobierno):
    """GA-01: sin ente 404; sin módulo 403; sin anio 422; query extra 422."""
    resp = mundo.get(f"{A}?anio={ANIO}", "ua", mundo.company_a)
    assert resp.status_code == 404, resp.text
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
        resp = mundo.get(f"{A}?anio={ANIO}", "ua", mundo.company_a)
        assert resp.status_code == 403, resp.text
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

    resp = mundo.get(A, "ua", mundo.company_a)
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_ERROR"

    resp = mundo.get(f"{A}?anio={ANIO}&x=1", "ua", mundo.company_a)
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "UNKNOWN_QUERY_PARAMETER"


def test_ga02_preparacion(mundo, gobierno):
    """GA-02: prepara ente, estructura, unidades, cargos y autoridades."""
    _ente(mundo, mundo.company_a, "ACTIVO")

    resp = mundo.post("/gobierno/estructuras", "ua", mundo.company_a, {"ejercicio": ANIO})
    assert resp.status_code == 201, resp.text
    ESTADO["est_anio"] = resp.json()["id"]

    resp = mundo.post(
        f"/gobierno/estructuras/{ANIO}/unidades",
        "ua",
        mundo.company_a,
        {"codigo": "DA-01", "denominacion": "Dirección de Administración", "tipo": "UNIDAD_ADMINISTRATIVA"},
    )
    assert resp.status_code == 201, resp.text
    ESTADO["da"] = resp.json()["id"]

    _publicar_estructura(mundo, mundo.company_a, ESTADO["est_anio"], "ua")

    cargo = _crear_cargo_y_competencias(
        mundo,
        mundo.company_a,
        ESTADO["da"],
        "DIR-ADM",
        "Director de Administración",
        [
            ("APROBAR", "CONTRATACIONES"),
            ("FIRMAR", "TESORERIA"),
        ],
    )
    ESTADO["dir_adm"] = cargo["id"]

    cargo_borrador = _crear_cargo_y_competencias(
        mundo,
        mundo.company_a,
        ESTADO["da"],
        "JEF-COM",
        "Jefe de Compras",
        [],
        activar=False,
    )
    ESTADO["jef_com"] = cargo_borrador["id"]

    resp = mundo.get(f"{A}/autoridades?fecha={HOY.isoformat()}", "ua", mundo.company_a)
    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    dir_items = [i for i in items if i["codigo"] == "DIR-ADM"]
    assert len(dir_items) == 1
    competencias = {(c["accion"], c["materia"]) for c in dir_items[0]["competencias"]}
    assert competencias == {("APROBAR", "CONTRATACIONES"), ("FIRMAR", "TESORERIA")}
    assert "JEF-COM" not in [i["codigo"] for i in items]

    resp = mundo.get(f"{A}?anio={ANIO}", "ua", mundo.company_a)
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"anio": ANIO, "items": [], "total": 0}

    ESTADO["ids_a"] = []


def test_ga03_alta_completa_particular(mundo, gobierno):
    """GA-03: alta completa de acto PARTICULAR."""
    cuerpo = _cuerpo(numero=f"DA-001-{ANIO}")
    antes = len(_eventos(mundo, "GOV_ACT_CREATED", mundo.company_a))
    resp = mundo.post(A, "ua", mundo.company_a, cuerpo)
    assert resp.status_code == 201, resp.text
    assert len(_eventos(mundo, "GOV_ACT_CREATED", mundo.company_a)) == antes + 1

    acto = resp.json()
    ESTADO["particular"] = acto["id"]
    ESTADO["particular_version"] = acto["version"]
    ESTADO["ids_a"].append(acto["id"])

    assert acto["estado"] == "BORRADOR"
    assert acto["version"] == 1
    assert acto["faltantes_para_emitir"] == ["DOCUMENTO_ACTO"]
    assert acto["cargo"]["codigo"] == "DIR-ADM"
    assert acto["cargo"]["unidad_codigo"] == "DA-01"
    assert acto["competencia"] == {"accion": "APROBAR", "materia": "CONTRATACIONES"}

    with mundo.factory() as db:
        from app.modules.government.models import GovernmentActVersion

        filas = list(
            db.scalars(
                select(GovernmentActVersion).where(
                    GovernmentActVersion.act_id == acto["id"]
                )
            )
        )
        assert len(filas) == 1
        assert filas[0].version == 1


def test_ga04_borrador_minimo(mundo, gobierno):
    """GA-04: borrador mínimo y faltantes según simple_tramite/caracter."""
    base_sin = {
        "tipo": "RESOLUCION",
        "numero": f"DA-002-{ANIO}",
        "fecha": HOY.isoformat(),
        "lugar": "Caracas",
        "cargo_id": ESTADO["dir_adm"],
        "competencia": {"accion": "APROBAR", "materia": "CONTRATACIONES"},
        "fundamento_competencia": "Reglamento interno, art. 12",
        "funcionario": "Ana Pérez",
        "titularidad": "TITULAR",
        "caracter": "PARTICULAR",
        "asunto": "Borrador mínimo",
    }
    resp = mundo.post(A, "ua", mundo.company_a, base_sin)
    assert resp.status_code == 201, resp.text
    acto = resp.json()
    ESTADO["borrador_minimo"] = acto["id"]
    ESTADO["borrador_minimo_version"] = acto["version"]
    ESTADO["ids_a"].append(acto["id"])
    assert acto["faltantes_para_emitir"] == [
        "DOCUMENTO_ACTO",
        "HECHOS",
        "FUNDAMENTOS",
        "DECISION",
        "DESTINATARIO",
    ]

    resp = mundo.post(
        A,
        "ua",
        mundo.company_a,
        _cuerpo(
            numero=f"DA-003-{ANIO}",
            simple_tramite=True,
            hechos=None,
            fundamentos=None,
            decision=None,
            destinatario=None,
        ),
    )
    assert resp.status_code == 201, resp.text
    acto = resp.json()
    ESTADO["ids_a"].append(acto["id"])
    assert acto["faltantes_para_emitir"] == ["DOCUMENTO_ACTO", "DECISION", "DESTINATARIO"]

    resp = mundo.post(
        A,
        "ua",
        mundo.company_a,
        _cuerpo(
            numero=f"DA-004-{ANIO}",
            caracter="GENERAL",
            destinatario=None,
            hechos=None,
            fundamentos=None,
            decision=None,
        ),
    )
    assert resp.status_code == 201, resp.text
    acto = resp.json()
    ESTADO["ids_a"].append(acto["id"])
    assert acto["faltantes_para_emitir"] == [
        "DOCUMENTO_ACTO",
        "HECHOS",
        "FUNDAMENTOS",
        "DECISION",
    ]


def test_ga05_validacion_campos(mundo, gobierno):
    """GA-05: validación de campos uno a uno y alta DELEGACION completa."""
    casos = [
        ({"tipo": "ACUERDO"}, "tipo"),
        ({"tipo": "OTRA_DECISION"}, "denominacion_tipo"),
        ({"denominacion_tipo": "X"}, "denominacion_tipo"),
        ({"numero": ""}, "numero"),
        ({"numero": "a" * 61}, "numero"),
        ({"fecha": (HOY + timedelta(days=1)).isoformat()}, "fecha"),
        ({"lugar": "C"}, "lugar"),
        ({"fundamento_competencia": "abc"}, "fundamento_competencia"),
        ({"funcionario": "Al"}, "funcionario"),
        ({"titularidad": "INTERINO"}, "titularidad"),
        (
            {
                "titularidad": "DELEGACION",
                "delegacion_fecha": HOY.isoformat(),
            },
            "delegacion_numero",
        ),
        (
            {
                "titularidad": "DELEGACION",
                "delegacion_numero": "R-07",
            },
            "delegacion_fecha",
        ),
        (
            {"delegacion_numero": "R-07"},
            "delegacion_numero",
        ),
        (
            {
                "titularidad": "DELEGACION",
                "delegacion_numero": "R-07",
                "delegacion_fecha": (HOY + timedelta(days=1)).isoformat(),
            },
            "delegacion_fecha",
        ),
        ({"simple_tramite": True, "caracter": "GENERAL"}, "simple_tramite"),
        ({"caracter": "MIXTO"}, "caracter"),
        ({"asunto": "ab"}, "asunto"),
        ({"hechos": "h" * 8001}, "hechos"),
        ({"decision": "d" * 8001}, "decision"),
        ({"estado": "X"}, "estado"),
    ]
    for i, (cambios, campo) in enumerate(casos, start=10):
        cuerpo = _cuerpo(numero=f"DA-{i:03d}-{ANIO}")
        cuerpo.update(cambios)
        resp = mundo.post(A, "ua", mundo.company_a, cuerpo)
        assert resp.status_code == 422, resp.text
        assert campo in resp.json()["field_errors"], resp.text

    resp = mundo.post(
        A,
        "ua",
        mundo.company_a,
        _cuerpo(
            numero=f"DA-030-{ANIO}",
            titularidad="DELEGACION",
            delegacion_numero="R-07",
            delegacion_fecha=HOY.isoformat(),
        ),
    )
    assert resp.status_code == 201, resp.text
    ESTADO["ids_a"].append(resp.json()["id"])


def test_ga06_autoridad_y_competencia(mundo, gobierno):
    """GA-06: autoridad inválida y competencia fuera del cargo."""
    resp = mundo.post(
        A, "ua", mundo.company_a, _cuerpo(cargo_id=ESTADO["jef_com"], numero=f"DA-031-{ANIO}")
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "GOV_ACT_INVALID_AUTHORITY"

    _ente(mundo, mundo.company_b, "ACTIVO")
    resp = mundo.post(
        "/gobierno/estructuras", "ub", mundo.company_b, {"ejercicio": ANIO}
    )
    assert resp.status_code == 201, resp.text
    est_b = resp.json()["id"]

    resp = mundo.post(
        f"/gobierno/estructuras/{ANIO}/unidades",
        "ub",
        mundo.company_b,
        {"codigo": "DB-01", "denominacion": "Dirección B", "tipo": "UNIDAD_ADMINISTRATIVA"},
    )
    assert resp.status_code == 201, resp.text
    unidad_b = resp.json()["id"]

    _publicar_estructura(mundo, mundo.company_b, est_b, "ub")

    cargo_b = _crear_cargo_y_competencias(
        mundo,
        mundo.company_b,
        unidad_b,
        "DIR-B",
        "Director B",
        [("FIRMAR", "TESORERIA")],
        usuario="ub",
    )
    cargo_b_id = cargo_b["id"]

    resp = mundo.post(
        A, "ua", mundo.company_a, _cuerpo(cargo_id=cargo_b_id, numero=f"DA-032-{ANIO}")
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "GOV_ACT_INVALID_AUTHORITY"

    resp = mundo.post(
        A, "ua", mundo.company_a, _cuerpo(cargo_id=str(uuid4()), numero=f"DA-033-{ANIO}")
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "GOV_ACT_INVALID_AUTHORITY"

    resp = mundo.post(
        A,
        "ua",
        mundo.company_a,
        _cuerpo(
            cargo_id=ESTADO["dir_adm"],
            numero=f"DA-034-{ANIO}",
            fecha=f"{ANTERIOR}-01-01",
        ),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "GOV_ACT_INVALID_AUTHORITY"

    resp = mundo.post(
        A,
        "ua",
        mundo.company_a,
        _cuerpo(
            cargo_id=ESTADO["dir_adm"],
            numero=f"DA-035-{ANIO}",
            competencia={"accion": "PAGAR", "materia": "TESORERIA"},
        ),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "GOV_ACT_INVALID_COMPETENCY"

    resp = mundo.post(
        A,
        "ua",
        mundo.company_a,
        _cuerpo(
            cargo_id=ESTADO["dir_adm"],
            numero=f"DA-036-{ANIO}",
            competencia={"accion": "VOLAR", "materia": "TESORERIA"},
        ),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_ERROR"


def test_ga07_numero_duplicado(mundo, gobierno):
    """GA-07: duplicado de número según tipo y denominación_tipo."""
    resp = mundo.post(
        A,
        "ua",
        mundo.company_a,
        _cuerpo(numero=f" da-001-{ANIO} "),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "GOV_ACT_NUMBER_DUPLICATE"

    resp = mundo.post(
        A,
        "ua",
        mundo.company_a,
        _cuerpo(tipo="PROVIDENCIA", numero=f"da-001-{ANIO}"),
    )
    assert resp.status_code == 201, resp.text
    ESTADO["ids_a"].append(resp.json()["id"])

    resp = mundo.post(
        A,
        "ua",
        mundo.company_a,
        _cuerpo(
            tipo="OTRA_DECISION",
            denominacion_tipo="Punto de cuenta",
            numero="1",
        ),
    )
    assert resp.status_code == 201, resp.text
    ESTADO["ids_a"].append(resp.json()["id"])

    resp = mundo.post(
        A,
        "ua",
        mundo.company_a,
        _cuerpo(
            tipo="OTRA_DECISION",
            denominacion_tipo="Memorando",
            numero="1",
        ),
    )
    assert resp.status_code == 201, resp.text
    ESTADO["ids_a"].append(resp.json()["id"])

    resp = mundo.post(
        A,
        "ua",
        mundo.company_a,
        _cuerpo(
            tipo="OTRA_DECISION",
            denominacion_tipo="punto de cuenta",
            numero="1",
        ),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "GOV_ACT_NUMBER_DUPLICATE"


def test_ga08_listar(mundo, gobierno):
    """GA-08: listado con total igual a los creados y claves de resumen."""
    resp = mundo.get(f"{A}?anio={ANIO}", "ua", mundo.company_a)
    assert resp.status_code == 200, resp.text
    cuerpo = resp.json()
    assert cuerpo["total"] == len(ESTADO["ids_a"])
    claves_resumen = {
        "id",
        "tipo",
        "denominacion_tipo",
        "numero",
        "fecha",
        "cargo_codigo",
        "cargo_denominacion",
        "unidad_codigo",
        "caracter",
        "asunto",
        "estado",
        "fecha_eficacia",
    }
    for item in cuerpo["items"]:
        assert set(item.keys()) == claves_resumen

    resp = mundo.get(f"{A}?anio={ANIO - 1}", "ua", mundo.company_a)
    assert resp.status_code == 200, resp.text
    assert resp.json()["total"] == 0

    resp = mundo.get(f"{A}?anio={ANIO}", "ub", mundo.company_b)
    assert resp.status_code == 200, resp.text
    ids_b = {item["id"] for item in resp.json()["items"]}
    assert ids_b.isdisjoint(ESTADO["ids_a"])


def test_ga09_obtener_acto(mundo, gobierno):
    """GA-09: obtener acto por id con claves de ActoOut; id inexistente y ajeno → 404."""
    resp = mundo.get(f"{A}/{ESTADO['particular']}", "ua", mundo.company_a)
    assert resp.status_code == 200, resp.text
    acto = resp.json()
    claves_out = {
        "id",
        "tipo",
        "denominacion_tipo",
        "numero",
        "fecha",
        "lugar",
        "cargo",
        "competencia",
        "fundamento_competencia",
        "funcionario",
        "titularidad",
        "delegacion_numero",
        "delegacion_fecha",
        "caracter",
        "simple_tramite",
        "destinatario",
        "asunto",
        "hechos",
        "fundamentos",
        "decision",
        "estado",
        "faltantes_para_emitir",
        "documento_acto_id",
        "medio",
        "referencia_publicacion",
        "fecha_publicacion_notificacion",
        "documento_eficacia_id",
        "fecha_eficacia",
        "revocado_por",
        "anulado_por",
        "revoca_a",
        "anula_a",
        "version",
        "emitido_en",
        "emitido_por",
        "creado_en",
    }
    assert set(acto.keys()) == claves_out

    resp = mundo.get(f"{A}/{uuid4()}", "ua", mundo.company_a)
    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == "GOV_ACT_NOT_FOUND"

    resp = mundo.get(f"{A}/{ESTADO['particular']}", "ub", mundo.company_b)
    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == "GOV_ACT_NOT_FOUND"


def test_ga10_modificar_borrador(mundo, gobierno):
    """GA-10: PATCH de borrador exige If-Match; If-Match viejo → 409 STALE; actualiza y audita."""
    acto_id = ESTADO["particular"]
    version_actual = ESTADO["particular_version"]

    resp = mundo.client.patch(
        f"/api/v1{A}/{acto_id}",
        headers=mundo.como("ua", mundo.company_a),
        json={"asunto": "Sin If-Match"},
    )
    assert resp.status_code == 428, resp.text
    assert resp.json()["code"] == "GOV_ACT_IF_MATCH_REQUIRED"

    resp = mundo.client.patch(
        f"/api/v1{A}/{acto_id}",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "99"},
        json={"asunto": "If-Match viejo"},
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "GOV_ACT_STALE"

    antes = len(_eventos(mundo, "GOV_ACT_UPDATED", mundo.company_a))
    nuevo_asunto = "Adjudicación de servicio actualizada"
    resp = mundo.client.patch(
        f"/api/v1{A}/{acto_id}",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(version_actual)},
        json={"asunto": nuevo_asunto},
    )
    assert resp.status_code == 200, resp.text
    acto = resp.json()
    assert acto["asunto"] == nuevo_asunto
    assert acto["version"] == version_actual + 1
    ESTADO["particular_version"] = acto["version"]
    assert len(_eventos(mundo, "GOV_ACT_UPDATED", mundo.company_a)) == antes + 1

    resp = mundo.client.patch(
        f"/api/v1{A}/{acto_id}",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(acto["version"])},
        json={"asunto": nuevo_asunto},
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "GOV_ACT_NO_CHANGES"

    resp = mundo.client.patch(
        f"/api/v1{A}/{acto_id}",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(acto["version"])},
        json={"cargo_id": ESTADO["jef_com"]},
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "GOV_ACT_INVALID_AUTHORITY"


def test_ga11_eliminar_borrador_con_y_sin_documentos(mundo, gobierno):
    """GA-11: borrador con documento vinculado no se elimina; sin documento se elimina con If-Match."""
    acto_con_doc = ESTADO["particular"]
    version_con_doc = ESTADO["particular_version"]
    _doc_activo(mundo, mundo.company_a, resource_id=acto_con_doc)

    resp = mundo.client.delete(
        f"/api/v1{A}/{acto_con_doc}",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(version_con_doc)},
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "GOV_ACT_HAS_DOCUMENTS"

    borrador_para_borrar = _cuerpo(numero=f"DA-099-{ANIO}")
    resp = mundo.post(A, "ua", mundo.company_a, borrador_para_borrar)
    assert resp.status_code == 201, resp.text
    acto_a_borrar = resp.json()
    ESTADO["ids_a"].append(acto_a_borrar["id"])
    version_a_borrar = acto_a_borrar["version"]

    resp = mundo.client.delete(
        f"/api/v1{A}/{acto_a_borrar['id']}",
        headers=mundo.como("ua", mundo.company_a),
    )
    assert resp.status_code == 428, resp.text
    assert resp.json()["code"] == "GOV_ACT_IF_MATCH_REQUIRED"

    antes = len(_eventos(mundo, "GOV_ACT_DELETED", mundo.company_a))
    resp = mundo.client.delete(
        f"/api/v1{A}/{acto_a_borrar['id']}",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(version_a_borrar)},
    )
    assert resp.status_code == 204, resp.text
    assert len(_eventos(mundo, "GOV_ACT_DELETED", mundo.company_a)) == antes + 1
    ESTADO["ids_a"].remove(acto_a_borrar["id"])

    resp = mundo.get(f"{A}/{acto_a_borrar['id']}", "ua", mundo.company_a)
    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == "GOV_ACT_NOT_FOUND"


def test_ga12_emitir_con_faltantes(mundo, gobierno):
    """GA-12: emitir borrador mínimo con documento vinculado → 422 INCOMPLETE con faltantes exactos; sin If-Match → 428."""
    acto_id = ESTADO["borrador_minimo"]
    version_actual = ESTADO["borrador_minimo_version"]
    doc_id = _doc_activo(mundo, mundo.company_a, resource_id=acto_id)

    resp = mundo.client.post(
        f"/api/v1{A}/{acto_id}/emitir",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(version_actual)},
        json={"documento_acto_id": doc_id},
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "GOV_ACT_INCOMPLETE"
    assert resp.json()["details"]["faltantes"] == ["HECHOS", "FUNDAMENTOS", "DECISION", "DESTINATARIO"]

    resp = mundo.client.post(
        f"/api/v1{A}/{acto_id}/emitir",
        headers=mundo.como("ua", mundo.company_a),
        json={"documento_acto_id": doc_id},
    )
    assert resp.status_code == 428, resp.text
    assert resp.json()["code"] == "GOV_ACT_IF_MATCH_REQUIRED"


def test_ga13_emitir_con_documento_invalido(mundo, gobierno):
    """GA-13: emitir acto completo con documento no vinculado, ajeno o DRAFT → 422 INVALID_DOCUMENT."""
    acto_id = ESTADO["particular"]
    version_actual = ESTADO["particular_version"]

    doc_no_vinculado = _doc_activo(mundo, mundo.company_a)
    resp = mundo.client.post(
        f"/api/v1{A}/{acto_id}/emitir",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(version_actual)},
        json={"documento_acto_id": doc_no_vinculado},
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "GOV_ACT_INVALID_DOCUMENT"

    doc_empresa_b = _doc_activo(mundo, mundo.company_b)
    resp = mundo.client.post(
        f"/api/v1{A}/{acto_id}/emitir",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(version_actual)},
        json={"documento_acto_id": doc_empresa_b},
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "GOV_ACT_INVALID_DOCUMENT"

    doc_draft = _doc_activo(mundo, mundo.company_a, resource_id=acto_id, status="DRAFT")
    resp = mundo.client.post(
        f"/api/v1{A}/{acto_id}/emitir",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(version_actual)},
        json={"documento_acto_id": doc_draft},
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "GOV_ACT_INVALID_DOCUMENT"


def test_ga14_emitir_particular_y_congelar_vinculo(mundo, gobierno):
    """GA-14: emitir PARTICULAR con documento ACTIVE con versión; congela DocumentLink y bloquea cambios posteriores."""
    acto_id = ESTADO["particular"]
    version_actual = ESTADO["particular_version"]
    doc_con_version = _doc_con_version(mundo, mundo.company_a, resource_id=acto_id)

    antes = len(_eventos(mundo, "GOV_ACT_ISSUED", mundo.company_a))
    resp = mundo.client.post(
        f"/api/v1{A}/{acto_id}/emitir",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(version_actual)},
        json={"documento_acto_id": doc_con_version},
    )
    assert resp.status_code == 200, resp.text
    acto = resp.json()
    assert acto["estado"] == "EMITIDO"
    assert acto["version"] == version_actual + 1
    assert acto["documento_acto_id"] == doc_con_version
    assert acto["emitido_en"] is not None
    assert acto["fecha_eficacia"] is None
    ESTADO["particular_emitido"] = acto_id
    ESTADO["doc_particular"] = doc_con_version
    ESTADO["particular_version"] = acto["version"]
    assert len(_eventos(mundo, "GOV_ACT_ISSUED", mundo.company_a)) == antes + 1

    with mundo.factory() as db:
        link = db.scalar(
            select(DocumentLink).where(
                DocumentLink.document_id == doc_con_version,
                DocumentLink.resource_type == "GovernmentAct",
                DocumentLink.resource_id == acto_id,
            )
        )
        assert link is not None
        assert link.is_frozen is True
        assert link.frozen_version_id is not None
        documento = db.get(Document, doc_con_version)
        assert link.frozen_version_id == documento.current_version_id
        link_id = str(link.id)

    resp = mundo.client.patch(
        f"/api/v1{A}/{acto_id}",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(acto["version"])},
        json={"asunto": "Modificación tras emitir"},
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "GOV_ACT_INVALID_STATE"

    resp = mundo.client.delete(
        f"/api/v1{A}/{acto_id}",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(acto["version"])},
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "GOV_ACT_INVALID_STATE"

    resp = mundo.client.delete(
        f"/api/v1/documentos/vinculos/{link_id}",
        headers=mundo.como("ua", mundo.company_a),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "LINK_FROZEN"


def test_ga15_emitir_interno(mundo, gobierno):
    """GA-15: emitir INTERNO sin destinatario; fecha_eficacia opcional y validada."""
    cuerpo_interno = _cuerpo(
        tipo="RESOLUCION",
        numero=f"DA-100-{ANIO}",
        caracter="INTERNO",
        destinatario=None,
    )
    resp = mundo.post(A, "ua", mundo.company_a, cuerpo_interno)
    assert resp.status_code == 201, resp.text
    acto_interno = resp.json()
    ESTADO["ids_a"].append(acto_interno["id"])
    version_interno = acto_interno["version"]

    doc_interno = _doc_con_version(mundo, mundo.company_a, resource_id=acto_interno["id"])
    antes = len(_eventos(mundo, "GOV_ACT_ISSUED", mundo.company_a))
    resp = mundo.client.post(
        f"/api/v1{A}/{acto_interno['id']}/emitir",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(version_interno)},
        json={"documento_acto_id": doc_interno},
    )
    assert resp.status_code == 200, resp.text
    acto_emitido = resp.json()
    assert acto_emitido["estado"] == "EFICAZ"
    assert acto_emitido["fecha_eficacia"] == acto_interno["fecha"]
    assert acto_emitido["version"] == version_interno + 1
    ESTADO["interno"] = acto_interno["id"]
    ESTADO["interno_version"] = acto_emitido["version"]
    assert len(_eventos(mundo, "GOV_ACT_ISSUED", mundo.company_a)) == antes + 1

    # Otro INTERNO con fecha_eficacia anterior a su fecha → 422
    cuerpo_interno_2 = _cuerpo(
        tipo="RESOLUCION",
        numero=f"DA-101-{ANIO}",
        caracter="INTERNO",
        destinatario=None,
    )
    resp = mundo.post(A, "ua", mundo.company_a, cuerpo_interno_2)
    assert resp.status_code == 201, resp.text
    acto_interno_2 = resp.json()
    ESTADO["ids_a"].append(acto_interno_2["id"])
    doc_interno_2 = _doc_con_version(mundo, mundo.company_a, resource_id=acto_interno_2["id"])
    fecha_anterior = (HOY - timedelta(days=1)).isoformat()
    resp = mundo.client.post(
        f"/api/v1{A}/{acto_interno_2['id']}/emitir",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(acto_interno_2["version"])},
        json={"documento_acto_id": doc_interno_2, "fecha_eficacia": fecha_anterior},
    )
    assert resp.status_code == 422, resp.text
    assert "fecha_eficacia" in resp.json()["field_errors"]

    # Otro INTERNO con fecha_eficacia HOY + 30 días → 200 EFICAZ
    cuerpo_interno_3 = _cuerpo(
        tipo="RESOLUCION",
        numero=f"DA-102-{ANIO}",
        caracter="INTERNO",
        destinatario=None,
    )
    resp = mundo.post(A, "ua", mundo.company_a, cuerpo_interno_3)
    assert resp.status_code == 201, resp.text
    acto_interno_3 = resp.json()
    ESTADO["ids_a"].append(acto_interno_3["id"])
    doc_interno_3 = _doc_con_version(mundo, mundo.company_a, resource_id=acto_interno_3["id"])
    fecha_futura = (HOY + timedelta(days=30)).isoformat()
    resp = mundo.client.post(
        f"/api/v1{A}/{acto_interno_3['id']}/emitir",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(acto_interno_3["version"])},
        json={"documento_acto_id": doc_interno_3, "fecha_eficacia": fecha_futura},
    )
    assert resp.status_code == 200, resp.text
    acto_emitido_3 = resp.json()
    assert acto_emitido_3["estado"] == "EFICAZ"
    assert acto_emitido_3["fecha_eficacia"] == fecha_futura


def _assert_acto_error(resp, expected_status, expected_code):
    assert resp.status_code == expected_status, resp.text
    body = resp.json()
    assert body["code"] == expected_code, body


def test_ga16_eficacia_particular_personal(mundo, gobierno):
    """GA-16: eficacia PARTICULAR personal (acto EMITIDO de GA-14)."""
    acto_id = ESTADO["particular"]
    version = ESTADO["particular_version"]
    doc_acto = ESTADO["doc_particular"]

    # soporte = el mismo documento del acto → 422 GOV_ACT_INVALID_DOCUMENT
    resp = mundo.client.post(
        f"/api/v1{A}/{acto_id}/eficacia",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(version)},
        json={
            "medio": "PERSONAL",
            "fecha": HOY.isoformat(),
            "documento_eficacia_id": doc_acto,
        },
    )
    _assert_acto_error(resp, 422, "GOV_ACT_INVALID_DOCUMENT")

    # medio GACETA → 422 GOV_ACT_INVALID_MEDIUM (carácter PARTICULAR)
    resp = mundo.client.post(
        f"/api/v1{A}/{acto_id}/eficacia",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(version)},
        json={
            "medio": "GACETA",
            "referencia": "Gaceta Oficial Nº 2.345",
            "fecha": HOY.isoformat(),
            "documento_eficacia_id": ESTADO["doc_particular"],
        },
    )
    _assert_acto_error(resp, 422, "GOV_ACT_INVALID_MEDIUM")

    # fecha = día anterior a la fecha del acto → 422
    resp = mundo.client.post(
        f"/api/v1{A}/{acto_id}/eficacia",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(version)},
        json={
            "medio": "PERSONAL",
            "fecha": (HOY - timedelta(days=1)).isoformat(),
            "documento_eficacia_id": _doc_con_version(
                mundo, mundo.company_a, resource_id=acto_id
            ),
        },
    )
    assert resp.status_code == 422, resp.text

    # fecha = HOY+1 → 422
    resp = mundo.client.post(
        f"/api/v1{A}/{acto_id}/eficacia",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(version)},
        json={
            "medio": "PERSONAL",
            "fecha": (HOY + timedelta(days=1)).isoformat(),
            "documento_eficacia_id": _doc_con_version(
                mundo, mundo.company_a, resource_id=acto_id
            ),
        },
    )
    assert resp.status_code == 422, resp.text

    # con un segundo documento ACTIVE vinculado al acto (con DocumentVersion real)
    doc_eficacia = _doc_con_version(mundo, mundo.company_a, resource_id=acto_id)

    # medio PERSONAL, fecha HOY → 200, EFICAZ
    resp = mundo.client.post(
        f"/api/v1{A}/{acto_id}/eficacia",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(version)},
        json={
            "medio": "PERSONAL",
            "fecha": HOY.isoformat(),
            "documento_eficacia_id": doc_eficacia,
        },
    )
    assert resp.status_code == 200, resp.text
    acto = resp.json()
    assert acto["estado"] == "EFICAZ"
    assert acto["fecha_eficacia"] == HOY.isoformat()
    assert acto["medio"] == "PERSONAL"
    assert acto["documento_eficacia_id"] == doc_eficacia
    assert acto["version"] == version + 1
    ESTADO["particular_version"] = acto["version"]
    ESTADO["particular_eficaz"] = acto
    ESTADO["particular_eficaz_version"] = acto["version"]
    ESTADO["particular_eficaz_doc"] = doc_eficacia

    # en BD solo los DocumentLink con versión quedan congelados
    with mundo.factory() as db:
        link_states = list(
            db.scalars(
                select(DocumentLink.is_frozen).where(
                    DocumentLink.company_id == mundo.company_a,
                    DocumentLink.resource_type == "GovernmentAct",
                    DocumentLink.resource_id == acto_id,
                    DocumentLink.document_id.in_(
                        [ESTADO["doc_particular"], doc_eficacia]
                    ),
                )
            )
        )
        assert len(link_states) == 2
        assert all(link_states)

    # evento GOV_ACT_EFFECTIVENESS_RECORDED
    antes = len(_eventos(mundo, "GOV_ACT_EFFECTIVENESS_RECORDED", mundo.company_a))
    assert antes == 1, antes

    # repetir → 409 GOV_ACT_INVALID_STATE
    resp = mundo.client.post(
        f"/api/v1{A}/{acto_id}/eficacia",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(acto["version"])},
        json={
            "medio": "PERSONAL",
            "fecha": HOY.isoformat(),
            "documento_eficacia_id": doc_eficacia,
        },
    )
    _assert_acto_error(resp, 409, "GOV_ACT_INVALID_STATE")


def test_ga17_eficacia_particular_prensa(mundo, gobierno):
    """GA-17: eficacia PARTICULAR por prensa (actos nuevos, emitidos en la prueba)."""
    # acto particular 1: PRENSA sin referencia → 422
    resp = mundo.post(
        A,
        "ua",
        mundo.company_a,
        _cuerpo(numero="DA-301-" + str(ANIO)),
    )
    assert resp.status_code == 201, resp.text
    acto1 = resp.json()
    ESTADO["ids_a"].append(acto1["id"])
    version1 = acto1["version"]

    doc1 = _doc_con_version(mundo, mundo.company_a, resource_id=acto1["id"])
    resp = mundo.client.post(
        f"/api/v1{A}/{acto1['id']}/emitir",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(version1)},
        json={"documento_acto_id": doc1},
    )
    assert resp.status_code == 200, resp.text
    version1 = resp.json()["version"]

    resp = mundo.client.post(
        f"/api/v1{A}/{acto1['id']}/eficacia",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(version1)},
        json={
            "medio": "PRENSA",
            "fecha": HOY.isoformat(),
            "documento_eficacia_id": doc1,
        },
    )
    assert resp.status_code == 422, resp.text

    # soporte válido distinto del documento del acto
    doc_soporte1 = _doc_con_version(mundo, mundo.company_a, resource_id=acto1["id"])

    # con referencia y fecha HOY → 200, fecha_eficacia == HOY + 15 días
    resp = mundo.client.post(
        f"/api/v1{A}/{acto1['id']}/eficacia",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(version1)},
        json={
            "medio": "PRENSA",
            "referencia": "Diario Ejemplo",
            "fecha": HOY.isoformat(),
            "documento_eficacia_id": doc_soporte1,
        },
    )
    assert resp.status_code == 200, resp.text
    acto1_eficaz = resp.json()
    assert acto1_eficaz["estado"] == "EFICAZ"
    assert acto1_eficaz["fecha_eficacia"] == (
        HOY + timedelta(days=15)
    ).isoformat()
    version1 = acto1_eficaz["version"]

    # tercer acto: PRENSA con fecha_eficacia explícita = HOY + 10 → 422
    resp = mundo.post(
        A,
        "ua",
        mundo.company_a,
        _cuerpo(numero="DA-302-" + str(ANIO)),
    )
    assert resp.status_code == 201, resp.text
    acto3 = resp.json()
    ESTADO["ids_a"].append(acto3["id"])
    version3 = acto3["version"]
    doc3 = _doc_con_version(mundo, mundo.company_a, resource_id=acto3["id"])
    resp = mundo.client.post(
        f"/api/v1{A}/{acto3['id']}/emitir",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(version3)},
        json={"documento_acto_id": doc3},
    )
    assert resp.status_code == 200, resp.text
    version3 = resp.json()["version"]
    doc_soporte3 = _doc_con_version(mundo, mundo.company_a, resource_id=acto3["id"])
    fechas = [
        (HOY + timedelta(days=10), 422),
        (HOY + timedelta(days=20), 200),
    ]
    for fecha_eficacia, expected in fechas:
        resp = mundo.client.post(
            f"/api/v1{A}/{acto3['id']}/eficacia",
            headers={**mundo.como("ua", mundo.company_a), "If-Match": str(version3)},
            json={
                "medio": "PRENSA",
                "referencia": "Diario Ejemplo",
                "fecha": HOY.isoformat(),
                "documento_eficacia_id": doc_soporte3,
                "fecha_eficacia": fecha_eficacia.isoformat(),
            },
        )
        if expected == 200:
            assert resp.status_code == 200, resp.text
            assert resp.json()["fecha_eficacia"] == fecha_eficacia.isoformat()
            version3 = resp.json()["version"]
        else:
            assert resp.status_code == 422, resp.text


def test_ga18_eficacia_general(mundo, gobierno):
    """GA-18: eficacia GENERAL (actos nuevos GENERAL completos y emitidos)."""
    # acto general 1: PERSONAL → 422 GOV_ACT_INVALID_MEDIUM
    resp = mundo.post(
        A,
        "ua",
        mundo.company_a,
        _cuerpo(
            numero="DA-303-" + str(ANIO),
            caracter="GENERAL",
            destinatario=None,
        ),
    )
    assert resp.status_code == 201, resp.text
    acto_g1 = resp.json()
    ESTADO["ids_a"].append(acto_g1["id"])
    version_g1 = acto_g1["version"]
    doc_g1 = _doc_con_version(mundo, mundo.company_a, resource_id=acto_g1["id"])
    resp = mundo.client.post(
        f"/api/v1{A}/{acto_g1['id']}/emitir",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(version_g1)},
        json={"documento_acto_id": doc_g1},
    )
    assert resp.status_code == 200, resp.text
    version_g1 = resp.json()["version"]
    doc_soporte_g1 = _doc_con_version(mundo, mundo.company_a, resource_id=acto_g1["id"])

    resp = mundo.client.post(
        f"/api/v1{A}/{acto_g1['id']}/eficacia",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(version_g1)},
        json={
            "medio": "PERSONAL",
            "fecha": HOY.isoformat(),
            "documento_eficacia_id": doc_soporte_g1,
        },
    )
    _assert_acto_error(resp, 422, "GOV_ACT_INVALID_MEDIUM")

    # GACETA sin referencia → 422
    resp = mundo.client.post(
        f"/api/v1{A}/{acto_g1['id']}/eficacia",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(version_g1)},
        json={
            "medio": "GACETA",
            "fecha": HOY.isoformat(),
            "documento_eficacia_id": doc_soporte_g1,
        },
    )
    assert resp.status_code == 422, resp.text

    # GACETA con referencia "Gaceta Oficial Nº 1.234" y fecha HOY → 200, eficaz HOY
    resp = mundo.client.post(
        f"/api/v1{A}/{acto_g1['id']}/eficacia",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(version_g1)},
        json={
            "medio": "GACETA",
            "referencia": "Gaceta Oficial Nº 1.234",
            "fecha": HOY.isoformat(),
            "documento_eficacia_id": doc_soporte_g1,
        },
    )
    assert resp.status_code == 200, resp.text
    acto_g1_eficaz = resp.json()
    assert acto_g1_eficaz["estado"] == "EFICAZ"
    assert acto_g1_eficaz["fecha_eficacia"] == HOY.isoformat()

    # otro GENERAL con fecha_eficacia explícita anterior a la publicación → 422
    resp = mundo.post(
        A,
        "ua",
        mundo.company_a,
        _cuerpo(
            numero="DA-304-" + str(ANIO),
            caracter="GENERAL",
            destinatario=None,
        ),
    )
    assert resp.status_code == 201, resp.text
    acto_g2 = resp.json()
    ESTADO["ids_a"].append(acto_g2["id"])
    version_g2 = acto_g2["version"]
    doc_g2 = _doc_con_version(mundo, mundo.company_a, resource_id=acto_g2["id"])
    resp = mundo.client.post(
        f"/api/v1{A}/{acto_g2['id']}/emitir",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(version_g2)},
        json={"documento_acto_id": doc_g2},
    )
    assert resp.status_code == 200, resp.text
    version_g2 = resp.json()["version"]
    doc_soporte_g2 = _doc_con_version(mundo, mundo.company_a, resource_id=acto_g2["id"])

    resp = mundo.client.post(
        f"/api/v1{A}/{acto_g2['id']}/eficacia",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(version_g2)},
        json={
            "medio": "GACETA",
            "referencia": "Gaceta Oficial Nº 1.235",
            "fecha": HOY.isoformat(),
            "documento_eficacia_id": doc_soporte_g2,
            "fecha_eficacia": (HOY - timedelta(days=1)).isoformat(),
        },
    )
    assert resp.status_code == 422, resp.text


def test_ga19_eficacia_estado_indebido(mundo, gobierno):
    """GA-19: eficacia en estado indebido."""
    for acto_id, version_key in [
        (ESTADO["interno"], "interno_version"),
    ]:
        doc = _doc_con_version(mundo, mundo.company_a, resource_id=acto_id)
        resp = mundo.client.post(
            f"/api/v1{A}/{acto_id}/eficacia",
            headers={
                **mundo.como("ua", mundo.company_a),
                "If-Match": str(ESTADO[version_key]),
            },
            json={
                "medio": "PERSONAL",
                "fecha": HOY.isoformat(),
                "documento_eficacia_id": doc,
            },
        )
        _assert_acto_error(resp, 409, "GOV_ACT_INVALID_STATE")

    borrador_id = ESTADO["borrador_minimo"]
    resp = mundo.client.post(
        f"/api/v1{A}/{borrador_id}/eficacia",
        headers={
            **mundo.como("ua", mundo.company_a),
            "If-Match": str(ESTADO["borrador_minimo_version"]),
        },
        json={
            "medio": "PERSONAL",
            "fecha": HOY.isoformat(),
            "documento_eficacia_id": _doc_con_version(
                mundo, mundo.company_a, resource_id=borrador_id
            ),
        },
    )
    _assert_acto_error(resp, 409, "GOV_ACT_INVALID_STATE")


def test_ga20_corregir_error_material(mundo, gobierno):
    """GA-20: corregir error material."""
    borrador_id = ESTADO["borrador_minimo"]
    resp = mundo.client.post(
        f"/api/v1{A}/{borrador_id}/corregir",
        headers={
            **mundo.como("ua", mundo.company_a),
            "If-Match": str(ESTADO["borrador_minimo_version"]),
        },
        json={"asunto": "Asunto corregido del borrador", "motivo": "Error material"},
    )
    _assert_acto_error(resp, 409, "GOV_ACT_INVALID_STATE")

    acto = ESTADO["particular_eficaz"]
    acto_id = acto["id"]
    version = ESTADO["particular_eficaz_version"]
    asunto_original = acto["asunto"]
    asunto_nuevo = "Adjudicación del servicio de limpieza"
    motivo = "Error material en el asunto"

    resp = mundo.client.post(
        f"/api/v1{A}/{acto_id}/corregir",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(version)},
        json={"asunto": asunto_nuevo, "motivo": motivo},
    )
    assert resp.status_code == 200, resp.text
    corregido = resp.json()
    assert corregido["estado"] == "EFICAZ"
    assert corregido["version"] == version + 1
    assert corregido["asunto"] == asunto_nuevo
    ESTADO["particular_version"] = corregido["version"]
    ESTADO["particular_eficaz_version"] = corregido["version"]
    ESTADO["particular_eficaz"] = corregido

    eventos = _eventos(mundo, "GOV_ACT_CORRECTED", mundo.company_a)
    ultimo = eventos[-1]
    assert "asunto" in ultimo.before
    assert ultimo.before["asunto"] == asunto_original
    assert ultimo.after["asunto"] == asunto_nuevo
    assert ultimo.reason == motivo

    # sin motivo → 422
    resp = mundo.client.post(
        f"/api/v1{A}/{acto_id}/corregir",
        headers={
            **mundo.como("ua", mundo.company_a),
            "If-Match": str(corregido["version"]),
        },
        json={"asunto": "Otro asunto"},
    )
    assert resp.status_code == 422, resp.text

    # campo no corregible {numero} → 422, esquema estricto
    resp = mundo.client.post(
        f"/api/v1{A}/{acto_id}/corregir",
        headers={
            **mundo.como("ua", mundo.company_a),
            "If-Match": str(corregido["version"]),
        },
        json={"numero": "X", "motivo": "..."},
    )
    assert resp.status_code == 422, resp.text

    # repetir el mismo asunto → 422 GOV_ACT_NO_CHANGES
    resp = mundo.client.post(
        f"/api/v1{A}/{acto_id}/corregir",
        headers={
            **mundo.como("ua", mundo.company_a),
            "If-Match": str(corregido["version"]),
        },
        json={"asunto": asunto_nuevo, "motivo": motivo},
    )
    _assert_acto_error(resp, 422, "GOV_ACT_NO_CHANGES")

    # la última GovernmentActVersion tiene reason == el motivo
    with mundo.factory() as db:
        from app.modules.government.models import GovernmentActVersion

        ultima_version = db.scalar(
            select(GovernmentActVersion)
            .where(GovernmentActVersion.act_id == acto_id)
            .order_by(GovernmentActVersion.version.desc())
            .limit(1)
        )
        assert ultima_version is not None
        assert ultima_version.reason == motivo


def test_ga21_revocar(mundo, gobierno):
    """GA-21: revocar (objetivo: acto EFICAZ de GA-16)."""
    objetivo = ESTADO["particular_eficaz"]
    objetivo_id = objetivo["id"]
    objetivo_version = ESTADO["particular_eficaz_version"]

    # referencia: un nuevo acto RESOLUCION emitido en la prueba
    resp = mundo.post(
        A,
        "ua",
        mundo.company_a,
        _cuerpo(
            numero="DA-201-" + str(ANIO),
            caracter="GENERAL",
            destinatario=None,
        ),
    )
    assert resp.status_code == 201, resp.text
    revocatorio = resp.json()
    ESTADO["ids_a"].append(revocatorio["id"])
    revocatorio_id = revocatorio["id"]
    revocatorio_version = revocatorio["version"]
    doc_rev = _doc_con_version(mundo, mundo.company_a, resource_id=revocatorio_id)
    resp = mundo.client.post(
        f"/api/v1{A}/{revocatorio_id}/emitir",
        headers={
            **mundo.como("ua", mundo.company_a),
            "If-Match": str(revocatorio_version),
        },
        json={"documento_acto_id": doc_rev},
    )
    assert resp.status_code == 200, resp.text
    revocatorio = resp.json()
    revocatorio_version = revocatorio["version"]

    # referencia = el propio acto → 422 GOV_ACT_INVALID_REFERENCE
    resp = mundo.client.post(
        f"/api/v1{A}/{objetivo_id}/revocar",
        headers={
            **mundo.como("ua", mundo.company_a),
            "If-Match": str(objetivo_version),
        },
        json={"acto_id_referencia": objetivo_id, "motivo": "Revocación"},
    )
    _assert_acto_error(resp, 422, "GOV_ACT_INVALID_REFERENCE")

    # referencia = un BORRADOR → 422
    resp = mundo.client.post(
        f"/api/v1{A}/{objetivo_id}/revocar",
        headers={
            **mundo.como("ua", mundo.company_a),
            "If-Match": str(objetivo_version),
        },
        json={
            "acto_id_referencia": ESTADO["borrador_minimo"],
            "motivo": "Revocación",
        },
    )
    _assert_acto_error(resp, 422, "GOV_ACT_INVALID_REFERENCE")

    # referencia = uuid4 → 422
    resp = mundo.client.post(
        f"/api/v1{A}/{objetivo_id}/revocar",
        headers={
            **mundo.como("ua", mundo.company_a),
            "If-Match": str(objetivo_version),
        },
        json={"acto_id_referencia": str(uuid4()), "motivo": "Revocación"},
    )
    _assert_acto_error(resp, 422, "GOV_ACT_INVALID_REFERENCE")

    # sin motivo → 422
    resp = mundo.client.post(
        f"/api/v1{A}/{objetivo_id}/revocar",
        headers={
            **mundo.como("ua", mundo.company_a),
            "If-Match": str(objetivo_version),
        },
        json={"acto_id_referencia": revocatorio_id},
    )
    assert resp.status_code == 422, resp.text

    # correcto → 200 REVOCADO
    resp = mundo.client.post(
        f"/api/v1{A}/{objetivo_id}/revocar",
        headers={
            **mundo.como("ua", mundo.company_a),
            "If-Match": str(objetivo_version),
        },
        json={"acto_id_referencia": revocatorio_id, "motivo": "Revocación"},
    )
    assert resp.status_code == 200, resp.text
    revocado = resp.json()
    assert revocado["estado"] == "REVOCADO"
    assert revocado["revocado_por"] == {
        "id": revocatorio["id"],
        "tipo": revocatorio["tipo"],
        "numero": revocatorio["numero"],
        "fecha": revocatorio["fecha"],
    }
    ESTADO["particular_version"] = revocado["version"]
    ESTADO["particular_eficaz_version"] = revocado["version"]
    ESTADO["particular_revocado"] = revocado
    ESTADO["revocatorio"] = revocatorio

    # GET del revocatorio → revoca_a contiene al revocado
    resp = mundo.get(
        f"{A}/{revocatorio_id}",
        "ua",
        mundo.company_a,
    )
    assert resp.status_code == 200, resp.text
    assert {"id": objetivo_id, "tipo": objetivo["tipo"], "numero": objetivo["numero"]} in resp.json()["revoca_a"]

    # evento GOV_ACT_REVOKED
    assert len(_eventos(mundo, "GOV_ACT_REVOKED", mundo.company_a)) == 1

    # luego corregir el revocado → 409 GOV_ACT_INVALID_STATE
    resp = mundo.client.post(
        f"/api/v1{A}/{objetivo_id}/corregir",
        headers={
            **mundo.como("ua", mundo.company_a),
            "If-Match": str(revocado["version"]),
        },
        json={"asunto": "No debería", "motivo": "Intento"},
    )
    _assert_acto_error(resp, 409, "GOV_ACT_INVALID_STATE")

    # revocarlo otra vez → 409 GOV_ACT_INVALID_STATE
    resp = mundo.client.post(
        f"/api/v1{A}/{objetivo_id}/revocar",
        headers={
            **mundo.como("ua", mundo.company_a),
            "If-Match": str(revocado["version"]),
        },
        json={"acto_id_referencia": revocatorio_id, "motivo": "Otra vez"},
    )
    _assert_acto_error(resp, 409, "GOV_ACT_INVALID_STATE")


def test_ga22_nulidad(mundo, gobierno):
    """GA-22: nulidad (objetivo: el INTERNO de GA-15; referencia: otro acto emitido)."""
    objetivo_id = ESTADO["interno"]
    objetivo_version = ESTADO["interno_version"]
    objetivo = mundo.get(
        f"{A}/{objetivo_id}",
        "ua",
        mundo.company_a,
    ).json()

    resp = mundo.post(
        A,
        "ua",
        mundo.company_a,
        _cuerpo(
            numero="DA-202-" + str(ANIO),
            caracter="GENERAL",
            destinatario=None,
        ),
    )
    assert resp.status_code == 201, resp.text
    declarativo = resp.json()
    ESTADO["ids_a"].append(declarativo["id"])
    doc_decl = _doc_con_version(
        mundo, mundo.company_a, resource_id=declarativo["id"]
    )
    declarativo_version = declarativo["version"]
    resp = mundo.client.post(
        f"/api/v1{A}/{declarativo['id']}/emitir",
        headers={
            **mundo.como("ua", mundo.company_a),
            "If-Match": str(declarativo_version),
        },
        json={"documento_acto_id": doc_decl},
    )
    assert resp.status_code == 200, resp.text
    declarativo = resp.json()

    resp = mundo.client.post(
        f"/api/v1{A}/{objetivo_id}/anular",
        headers={
            **mundo.como("ua", mundo.company_a),
            "If-Match": str(objetivo_version),
        },
        json={"acto_id_referencia": declarativo["id"], "motivo": "Nulidad"},
    )
    assert resp.status_code == 200, resp.text
    nulo = resp.json()
    assert nulo["estado"] == "NULO"
    assert nulo["anulado_por"] == {
        "id": declarativo["id"],
        "tipo": declarativo["tipo"],
        "numero": declarativo["numero"],
        "fecha": declarativo["fecha"],
    }

    resp = mundo.get(
        f"{A}/{declarativo['id']}",
        "ua",
        mundo.company_a,
    )
    assert resp.status_code == 200, resp.text
    assert {"id": objetivo_id, "tipo": objetivo["tipo"], "numero": objetivo["numero"]} in resp.json()["anula_a"]

    assert len(_eventos(mundo, "GOV_ACT_NULLIFIED", mundo.company_a)) == 1

    # anular de nuevo → 409
    resp = mundo.client.post(
        f"/api/v1{A}/{objetivo_id}/anular",
        headers={
            **mundo.como("ua", mundo.company_a),
            "If-Match": str(nulo["version"]),
        },
        json={"acto_id_referencia": declarativo["id"], "motivo": "Otra vez"},
    )
    _assert_acto_error(resp, 409, "GOV_ACT_INVALID_STATE")


def test_ga23_historial(mundo, gobierno):
    """GA-23: historial del acto revocado."""
    acto_id = ESTADO["particular_revocado"]["id"]
    resp = mundo.get(
        f"{A}/{acto_id}/versiones",
        "ua",
        mundo.company_a,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    items = body["items"]
    assert [item["version"] for item in items] == list(range(1, len(items) + 1))
    estados = [item["estado"] for item in items]
    for esperado in ("BORRADOR", "EMITIDO", "EFICAZ", "REVOCADO"):
        assert esperado in estados
    for item in items:
        assert "motivo" in item
        assert "actor" in item
        assert "creado_en" in item
        assert "instantanea" in item


def test_ga24_csv(mundo, gobierno):
    """GA-24: CSV exporta los actos del año con cabecera y evento de auditoría."""
    antes = len(_eventos(mundo, "GOV_ACTS_EXPORTED", mundo.company_a))
    resp = mundo.get(f"{A}/exportar?anio={ANIO}", "ua", mundo.company_a)
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("text/csv")
    assert f"actos-{ANIO}.csv" in resp.headers["content-disposition"]

    filas = list(csv_reader(StringIO(resp.text)))
    cabecera = [
        "numero",
        "tipo",
        "denominacion_tipo",
        "fecha",
        "lugar",
        "caracter",
        "asunto",
        "cargo",
        "unidad",
        "competencia",
        "funcionario",
        "titularidad",
        "destinatario",
        "estado",
        "fecha_eficacia",
        "revocado_por",
        "anulado_por",
    ]
    assert filas[0] == cabecera

    resp_anio = mundo.get(f"{A}?anio={ANIO}", "ua", mundo.company_a)
    assert resp_anio.status_code == 200, resp_anio.text
    esperados = {item["numero"] for item in resp_anio.json()["items"]}
    assert esperados, resp_anio.text
    filas_csv = {fila[0] for fila in filas[1:]}
    assert esperados <= filas_csv
    assert len(_eventos(mundo, "GOV_ACTS_EXPORTED", mundo.company_a)) == antes + 1


def test_ga25_permisos(mundo, gobierno):
    """GA-25: consulta solo view y registrador view+edit no emiten ni revocan."""
    ya_usuario = None
    with mundo.factory() as db:
        ya_usuario = identity_service.create_user(
            db,
            tenant_id=mundo.t1,
            username="actoconsulta",
            email="actoconsulta@example.test",
            password=PASSWORD,
            created_by=None,
        )
        rol_consulta = Role(
            code="R_ACTO_VIEW",
            name="Consulta de actos",
            tenant_id=mundo.t1,
            protected=False,
            status="ACTIVE",
        )
        db.add(rol_consulta)
        db.flush()
        for accion in ("view",):
            permiso = db.scalar(
                select(Permission).where(
                    Permission.resource == "gobierno_actos",
                    Permission.action == accion,
                )
            )
            db.add(RolePermission(role_id=rol_consulta.id, permission_id=permiso.id))
        db.add(UserRole(user_id=ya_usuario.id, role_id=rol_consulta.id, company_id=None))
        db.add(UserScope(user_id=ya_usuario.id, company_id=mundo.company_a))

        ya_registrador = identity_service.create_user(
            db,
            tenant_id=mundo.t1,
            username="actoregistrador",
            email="actoregistrador@example.test",
            password=PASSWORD,
            created_by=None,
        )
        rol_registrador = Role(
            code="R_ACTO_EDIT",
            name="Registrador de actos",
            tenant_id=mundo.t1,
            protected=False,
            status="ACTIVE",
        )
        db.add(rol_registrador)
        db.flush()
        for accion in ("view", "edit"):
            permiso = db.scalar(
                select(Permission).where(
                    Permission.resource == "gobierno_actos",
                    Permission.action == accion,
                )
            )
            db.add(RolePermission(role_id=rol_registrador.id, permission_id=permiso.id))
        db.add(UserRole(user_id=ya_registrador.id, role_id=rol_registrador.id, company_id=None))
        db.add(UserScope(user_id=ya_registrador.id, company_id=mundo.company_a))
        db.commit()

    resp = mundo.get(f"{A}?anio={ANIO}", "actoconsulta", mundo.company_a)
    assert resp.status_code == 200, resp.text
    resp = mundo.get(f"{A}/{ESTADO['particular']}", "actoconsulta", mundo.company_a)
    assert resp.status_code == 200, resp.text

    resp = mundo.post(f"{A}", "actoconsulta", mundo.company_a, _cuerpo())
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "PERMISSION_DENIED"

    numero_registrador = f"DA-410-{ANIO}"
    resp = mundo.post(
        f"{A}",
        "actoregistrador",
        mundo.company_a,
        _cuerpo(numero=numero_registrador),
    )
    assert resp.status_code == 201, resp.text
    acto = resp.json()
    ESTADO["ids_a"].append(acto["id"])
    assert acto["estado"] == "BORRADOR"
    version = acto["version"]

    resp = mundo.client.patch(
        f"/api/v1{A}/{acto['id']}",
        headers={**mundo.como("actoregistrador", mundo.company_a), "If-Match": str(version)},
        json={"asunto": "Asunto corregido por registrador"},
    )
    assert resp.status_code == 200, resp.text
    version = resp.json()["version"]

    doc_id = _doc_con_version(mundo, mundo.company_a, resource_id=acto["id"])
    resp = mundo.client.post(
        f"/api/v1{A}/{acto['id']}/emitir",
        headers={**mundo.como("actoregistrador", mundo.company_a), "If-Match": str(version)},
        json={"documento_acto_id": doc_id, "fecha_eficacia": HOY.isoformat()},
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "PERMISSION_DENIED"

    numero_emitido = f"DA-411-{ANIO}"
    resp = mundo.post(
        f"{A}",
        "ua",
        mundo.company_a,
        _cuerpo(numero=numero_emitido),
    )
    assert resp.status_code == 201, resp.text
    acto_emitido = resp.json()
    ESTADO["ids_a"].append(acto_emitido["id"])
    version_emitido = acto_emitido["version"]

    doc_emitido = _doc_con_version(mundo, mundo.company_a, resource_id=acto_emitido["id"])
    resp = mundo.client.post(
        f"/api/v1{A}/{acto_emitido['id']}/emitir",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(version_emitido)},
        json={"documento_acto_id": doc_emitido},
    )
    assert resp.status_code == 200, resp.text
    version_emitido = resp.json()["version"]

    resp = mundo.client.post(
        f"/api/v1{A}/{acto_emitido['id']}/revocar",
        headers={**mundo.como("actoregistrador", mundo.company_a), "If-Match": str(version_emitido)},
        json={
            "acto_id_referencia": acto_emitido["id"],
            "motivo": "No debería poder revocar",
        },
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "PERMISSION_DENIED"

    resp = mundo.get(f"{A}/exportar?anio={ANIO}", "actoregistrador", mundo.company_a)
    assert resp.status_code == 200, resp.text


def test_ga26_aislamiento(mundo, gobierno):
    """GA-26: empresas distintas no ven actos y no usan autoridades ajenas."""
    resp = mundo.get(f"{A}/{ESTADO['particular']}", "ub", mundo.company_b)
    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == "GOV_ACT_NOT_FOUND"

    resp = mundo.get(f"{A}?anio={ANIO}", "ub", mundo.company_b)
    assert resp.status_code == 200, resp.text
    ids_b = {item["id"] for item in resp.json()["items"]}
    assert set(ESTADO["ids_a"]).isdisjoint(ids_b)

    resp = mundo.post(
        f"{A}",
        "ub",
        mundo.company_b,
        _cuerpo(numero=f"DA-420-{ANIO}"),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "GOV_ACT_INVALID_AUTHORITY"

    resp = mundo.get(f"{A}/{ESTADO['particular']}", "uc", mundo.company_c, tenant="T2")
    assert resp.status_code in (403, 404), resp.text
    assert "Codigo" not in resp.text


def test_ga27_rutas(mundo, gobierno):
    """GA-27: expone exactamente las 13 operaciones de la API de actos."""
    rutas = {}
    for ruta in mundo.client.app.routes:
        path = getattr(ruta, "path", "")
        if path.startswith("/api/v1/gobierno/actos"):
            metodos = set(getattr(ruta, "methods", None) or set()) - {
                "HEAD",
                "OPTIONS",
            }
            rutas.setdefault(path, set()).update(metodos)

    esperado = {
        "/api/v1/gobierno/actos": {"GET", "POST"},
        "/api/v1/gobierno/actos/exportar": {"GET"},
        "/api/v1/gobierno/actos/autoridades": {"GET"},
        "/api/v1/gobierno/actos/{acto_id}": {"GET", "PATCH", "DELETE"},
        "/api/v1/gobierno/actos/{acto_id}/emitir": {"POST"},
        "/api/v1/gobierno/actos/{acto_id}/eficacia": {"POST"},
        "/api/v1/gobierno/actos/{acto_id}/corregir": {"POST"},
        "/api/v1/gobierno/actos/{acto_id}/revocar": {"POST"},
        "/api/v1/gobierno/actos/{acto_id}/anular": {"POST"},
        "/api/v1/gobierno/actos/{acto_id}/versiones": {"GET"},
    }
    assert rutas == esperado

    resp = mundo.get(f"{A}/exportar?anio={ANIO}", "ua", mundo.company_a)
    assert resp.status_code != 404 or resp.json().get("code") != "GOV_ACT_NOT_FOUND"


def test_ga28_restricciones_bd(mundo, gobierno):
    """GA-28: integridad de base de datos para GovernmentAct."""
    base = {
        "company_id": mundo.company_a,
        "tipo": "RESOLUCION",
        "denominacion_tipo": "",
        "denominacion_clave": "",
        "numero": f"DA-430-{ANIO}",
        "numero_clave": f"DA-430-{ANIO}",
        "fecha": HOY,
        "lugar": "Caracas",
        "cargo_id": ESTADO["dir_adm"],
        "competencia_accion": "APROBAR",
        "competencia_materia": "CONTRATACIONES",
        "fundamento_competencia": "Reglamento interno, art. 12",
        "funcionario": "Ana Pérez",
        "titularidad": "TITULAR",
        "caracter": "PARTICULAR",
        "simple_tramite": False,
        "asunto": "Asunto de integridad",
        "status": "BORRADOR",
        "version": 1,
    }
    with mundo.factory() as db:
        acto = GovernmentAct(**base)
        db.add(acto)
        db.commit()

    EMITIDO = {
        "documento_acto_id": ESTADO["doc_particular"],
        "emitido_en": datetime.now(UTC),
    }

    casos = {
        "tipo_invalido": (
            {"tipo": "ACUERDO"},
            "ck_gov_acts_tipo",
        ),
        "denominacion_vacia": (
            {"tipo": "OTRA_DECISION", "denominacion_tipo": ""},
            "ck_gov_acts_denominacion",
        ),
        "denominacion_sobrante": (
            {"denominacion_tipo": "Resolución"},
            "ck_gov_acts_denominacion",
        ),
        "delegacion_sin_fecha": (
            {"titularidad": "DELEGACION", "delegacion_numero": "D-1"},
            "ck_gov_acts_delegacion",
        ),
        "simple_tramite_general": (
            {"caracter": "GENERAL", "simple_tramite": True},
            "ck_gov_acts_simple_tramite",
        ),
        "competencia_invalida": (
            {"competencia_accion": "VOLAR"},
            "ck_gov_acts_competencia_accion",
        ),
        "emitido_sin_documento": (
            {"status": "EMITIDO"},
            "ck_gov_acts_emitido_documentado",
        ),
        "eficaz_sin_fecha": (
            {**EMITIDO, "status": "EFICAZ"},
            "ck_gov_acts_eficaz_fechado",
        ),
        "fecha_eficacia_anterior": (
            {"fecha_eficacia": HOY - timedelta(days=1)},
            "ck_gov_acts_eficacia_no_retroactiva",
        ),
        "revocado_sin_referencia": (
            {**EMITIDO, "status": "REVOCADO"},
            "ck_gov_acts_revocado_referenciado",
        ),
        "nulo_sin_referencia": (
            {**EMITIDO, "status": "NULO"},
            "ck_gov_acts_nulo_referenciado",
        ),
        "version_cero": (
            {"version": 0},
            "ck_gov_acts_version",
        ),
    }

    for nombre, (cambios, restriccion) in casos.items():
        datos = {**base, **cambios}
        datos["numero"] = f"{base['numero']}-{nombre}"
        datos["numero_clave"] = datos["numero"]
        with mundo.factory() as db:
            acto = GovernmentAct(**datos)
            db.add(acto)
            with pytest.raises(IntegrityError, match=restriccion):
                db.commit()
            db.rollback()

    with mundo.factory() as db:
        acto = GovernmentAct(**base)
        db.add(acto)
        with pytest.raises(IntegrityError, match="uq_gov_acts_numero"):
            db.commit()
        db.rollback()


def test_ga29_mfa(mundo, gobierno):
    """GA-29: políticas MFA para permisos de actos administrativos."""
    vista = classify({"gobierno_actos:view"})
    assert vista == STANDARD

    edicion = classify({"gobierno_actos:edit"})
    assert edicion == SENSITIVE

    emision = classify({"gobierno_actos:issue"})
    assert emision == SENSITIVE

    anulacion = classify({"gobierno_actos:annul"})
    assert anulacion == SENSITIVE


def test_ga30_catalogo_auditoria(mundo, gobierno):
    """GA-30: acciones de auditoría de actos están en el catálogo."""
    acciones_esperadas = {
        "GOV_ACT_CREATED",
        "GOV_ACT_UPDATED",
        "GOV_ACT_DELETED",
        "GOV_ACT_ISSUED",
        "GOV_ACT_EFFECTIVENESS_RECORDED",
        "GOV_ACT_CORRECTED",
        "GOV_ACT_REVOKED",
        "GOV_ACT_NULLIFIED",
        "GOV_ACTS_EXPORTED",
    }
    codigos = {code for code, _entity in catalog()}
    assert acciones_esperadas <= codigos


def test_ga31_concurrencia(mundo, gobierno):
    """GA-31: If-Match duplicado produce GOV_ACT_STALE y una sola versión."""
    resp = mundo.post(
        f"{A}",
        "ua",
        mundo.company_a,
        _cuerpo(numero=f"DA-450-{ANIO}"),
    )
    assert resp.status_code == 201, resp.text
    acto = resp.json()
    ESTADO["ids_a"].append(acto["id"])
    version_inicial = acto["version"]

    doc_id = _doc_con_version(mundo, mundo.company_a, resource_id=acto["id"])
    payload = {"documento_acto_id": doc_id}

    resp = mundo.client.post(
        f"/api/v1{A}/{acto['id']}/emitir",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(version_inicial)},
        json=payload,
    )
    assert resp.status_code == 200, resp.text
    version_emitida = resp.json()["version"]
    assert resp.json()["estado"] == "EMITIDO"

    resp = mundo.client.post(
        f"/api/v1{A}/{acto['id']}/emitir",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(version_inicial)},
        json=payload,
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "GOV_ACT_STALE"

    resp = mundo.get(f"{A}/{acto['id']}", "ua", mundo.company_a)
    assert resp.status_code == 200, resp.text
    assert resp.json()["estado"] == "EMITIDO"
    assert resp.json()["version"] == version_emitida

    resp = mundo.get(f"{A}/{acto['id']}/versiones", "ua", mundo.company_a)
    assert resp.status_code == 200, resp.text
    emisiones = [
        item
        for item in resp.json()["items"]
        if item["estado"] == "EMITIDO"
    ]
    assert len(emisiones) == 1


def test_ga32_escritura_de_otra_empresa(mundo, gobierno):
    """GA-32: PATCH/DELETE de empresa ajena devuelven 404 y no alteran el acto."""
    resp = mundo.client.post(
        f"/api/v1{A}",
        headers=mundo.como("ua", mundo.company_a),
        json=_cuerpo(numero=f"DA-456-{ANIO}"),
    )
    assert resp.status_code == 201, resp.text
    acto = resp.json()
    ESTADO["ids_a"].append(acto["id"])
    acto_id = acto["id"]
    version = acto["version"]

    resp = mundo.client.patch(
        f"/api/v1{A}/{acto_id}",
        headers={
            **mundo.como("ub", mundo.company_b),
            "If-Match": str(version),
        },
        json={"asunto": "Intento ajeno"},
    )
    _assert_acto_error(resp, 404, "GOV_ACT_NOT_FOUND")

    resp = mundo.client.delete(
        f"/api/v1{A}/{acto_id}",
        headers={
            **mundo.como("ub", mundo.company_b),
            "If-Match": str(version),
        },
    )
    _assert_acto_error(resp, 404, "GOV_ACT_NOT_FOUND")

    resp = mundo.get(f"{A}/{acto_id}", "ua", mundo.company_a)
    assert resp.status_code == 200, resp.text
    cuerpo_actual = resp.json()
    assert cuerpo_actual["asunto"] == _cuerpo()["asunto"]
    assert cuerpo_actual["version"] == version


def test_ga33_particular_no_admite_eficacia_al_emitir(mundo, gobierno):
    """GA-33: un acto PARTICULAR no puede emitirse con fecha_eficacia."""
    resp = mundo.client.post(
        f"/api/v1{A}",
        headers=mundo.como("ua", mundo.company_a),
        json=_cuerpo(numero=f"DA-451-{ANIO}"),
    )
    assert resp.status_code == 201, resp.text
    acto = resp.json()
    ESTADO["ids_a"].append(acto["id"])
    acto_id = acto["id"]
    doc = _doc_con_version(mundo, mundo.company_a, resource_id=acto_id)

    resp = mundo.client.post(
        f"/api/v1{A}/{acto_id}/emitir",
        headers={
            **mundo.como("ua", mundo.company_a),
            "If-Match": str(acto["version"]),
        },
        json={"documento_acto_id": doc, "fecha_eficacia": HOY.isoformat()},
    )
    _assert_acto_error(resp, 422, "VALIDATION_ERROR")
    assert "fecha_eficacia" in resp.json()["field_errors"], resp.json()

    resp = mundo.get(f"{A}/{acto_id}", "ua", mundo.company_a)
    assert resp.status_code == 200, resp.text
    assert resp.json()["estado"] == "BORRADOR"


def test_ga34_referencia_anterior_al_acto(mundo, gobierno):
    """GA-34: una referencia con fecha anterior a la del acto es inválida."""
    assert HOY > date(ANIO, 1, 1), "la prueba necesita un día de negocio posterior al 1 de enero"

    resp = mundo.client.post(
        f"/api/v1{A}",
        headers=mundo.como("ua", mundo.company_a),
        json=_cuerpo(
            numero=f"DA-452-{ANIO}",
            caracter="GENERAL",
            destinatario=None,
            fecha=date(ANIO, 1, 1).isoformat(),
        ),
    )
    assert resp.status_code == 201, resp.text
    referencia = resp.json()
    ESTADO["ids_a"].append(referencia["id"])
    doc_ref = _doc_con_version(mundo, mundo.company_a, resource_id=referencia["id"])
    resp = mundo.client.post(
        f"/api/v1{A}/{referencia['id']}/emitir",
        headers={
            **mundo.como("ua", mundo.company_a),
            "If-Match": str(referencia["version"]),
        },
        json={"documento_acto_id": doc_ref},
    )
    assert resp.status_code == 200, resp.text

    resp = mundo.client.post(
        f"/api/v1{A}",
        headers=mundo.como("ua", mundo.company_a),
        json=_cuerpo(
            numero=f"DA-453-{ANIO}",
            caracter="GENERAL",
            destinatario=None,
        ),
    )
    assert resp.status_code == 201, resp.text
    objetivo = resp.json()
    ESTADO["ids_a"].append(objetivo["id"])
    doc_obj = _doc_con_version(mundo, mundo.company_a, resource_id=objetivo["id"])
    resp = mundo.client.post(
        f"/api/v1{A}/{objetivo['id']}/emitir",
        headers={
            **mundo.como("ua", mundo.company_a),
            "If-Match": str(objetivo["version"]),
        },
        json={"documento_acto_id": doc_obj},
    )
    assert resp.status_code == 200, resp.text
    objetivo = resp.json()

    resp = mundo.client.post(
        f"/api/v1{A}/{objetivo['id']}/revocar",
        headers={
            **mundo.como("ua", mundo.company_a),
            "If-Match": str(objetivo["version"]),
        },
        json={"acto_id_referencia": referencia["id"], "motivo": "Revocación"},
    )
    _assert_acto_error(resp, 422, "GOV_ACT_INVALID_REFERENCE")


def test_ga35_revocar_exige_annul(mundo, gobierno):
    """GA-35: revocar exige permiso annul; sin él devuelve 403 por permiso."""
    with mundo.factory() as db:
        ya_emisor = identity_service.create_user(
            db,
            tenant_id=mundo.t1,
            username="actoemisor",
            email="actoemisor@example.test",
            password=PASSWORD,
            created_by=None,
        )
        rol_emisor = Role(
            code="R_ACTO_ISSUE",
            name="Emisor de actos",
            tenant_id=mundo.t1,
            protected=False,
            status="ACTIVE",
        )
        db.add(rol_emisor)
        db.flush()
        for accion in ("view", "edit", "issue"):
            permiso = db.scalar(
                select(Permission).where(
                    Permission.resource == "gobierno_actos",
                    Permission.action == accion,
                )
            )
            db.add(RolePermission(role_id=rol_emisor.id, permission_id=permiso.id))
        db.add(UserRole(user_id=ya_emisor.id, role_id=rol_emisor.id, company_id=None))
        db.add(UserScope(user_id=ya_emisor.id, company_id=mundo.company_a))
        db.commit()

    resp = mundo.client.post(
        f"/api/v1{A}",
        headers=mundo.como("ua", mundo.company_a),
        json=_cuerpo(
            numero=f"DA-454-{ANIO}",
            caracter="GENERAL",
            destinatario=None,
        ),
    )
    assert resp.status_code == 201, resp.text
    objetivo = resp.json()
    ESTADO["ids_a"].append(objetivo["id"])
    doc_obj = _doc_con_version(mundo, mundo.company_a, resource_id=objetivo["id"])
    resp = mundo.client.post(
        f"/api/v1{A}/{objetivo['id']}/emitir",
        headers={
            **mundo.como("ua", mundo.company_a),
            "If-Match": str(objetivo["version"]),
        },
        json={"documento_acto_id": doc_obj},
    )
    assert resp.status_code == 200, resp.text
    objetivo = resp.json()

    resp = mundo.client.post(
        f"/api/v1{A}",
        headers=mundo.como("ua", mundo.company_a),
        json=_cuerpo(
            numero=f"DA-455-{ANIO}",
            caracter="GENERAL",
            destinatario=None,
        ),
    )
    assert resp.status_code == 201, resp.text
    referencia = resp.json()
    ESTADO["ids_a"].append(referencia["id"])
    doc_ref = _doc_con_version(mundo, mundo.company_a, resource_id=referencia["id"])
    resp = mundo.client.post(
        f"/api/v1{A}/{referencia['id']}/emitir",
        headers={
            **mundo.como("ua", mundo.company_a),
            "If-Match": str(referencia["version"]),
        },
        json={"documento_acto_id": doc_ref},
    )
    assert resp.status_code == 200, resp.text

    resp = mundo.client.post(
        f"/api/v1{A}/{objetivo['id']}/revocar",
        headers={
            **mundo.como("actoemisor", mundo.company_a),
            "If-Match": str(objetivo["version"]),
        },
        json={"acto_id_referencia": referencia["id"], "motivo": "Revocación"},
    )
    _assert_acto_error(resp, 403, "PERMISSION_DENIED")

    resp = mundo.client.post(
        f"/api/v1{A}/{objetivo['id']}/revocar",
        headers={
            **mundo.como("ua", mundo.company_a),
            "If-Match": str(objetivo["version"]),
        },
        json={"acto_id_referencia": referencia["id"], "motivo": "Revocación"},
    )
    assert resp.status_code == 200, resp.text


def test_ga36_csv_filtra_por_anio(mundo, gobierno):
    """GA-36: exportar filtra por año; sin datos en el año previo solo cabecera."""
    resp = mundo.get(f"{A}/exportar?anio={ANIO - 1}", "ua", mundo.company_a)
    assert resp.status_code == 200, resp.text
    filas_previo = list(csv_reader(StringIO(resp.text)))
    assert len(filas_previo) == 1, filas_previo

    resp = mundo.get(f"{A}/exportar?anio={ANIO}", "ua", mundo.company_a)
    assert resp.status_code == 200, resp.text
    filas_actual = list(csv_reader(StringIO(resp.text)))
    assert len(filas_actual) > 1, filas_actual
