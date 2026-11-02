"""Suite de backend para DOC04-T001: notificación de actos administrativos particulares.

Especifica el contrato del módulo `app.modules.government` para notificaciones
antes de que el código de producción exista.
"""
from csv import reader as csv_reader
from datetime import UTC, datetime, timedelta
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
    GovernmentEntity,
    GovernmentNotification,
    GovernmentNotificationAttempt,
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
A = "/gobierno/actos"
N = "/gobierno/notificaciones"
ESTADO = {}


def c(ej, anio=None):
    return f"/gobierno/estructuras/{ej}/cargos" if anio is None else f"/gobierno/estructuras/{anio}/cargos"


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


def _doc_con_version(mundo, company_id, *, resource_id) -> str:
    """Crea StoredFile + DocumentVersion ACTIVE + Document ACTIVE vinculado al acto."""
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


def _doc_notificacion(mundo, company_id, *, notificacion_id) -> str:
    """Igual que _doc_con_version pero vinculado a GovernmentNotification."""
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
            original_name="notificacion.pdf",
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
            title="Documento de notificación con versión",
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
                resource_type="GovernmentNotification",
                resource_id=notificacion_id,
            )
        )
        db.commit()
        return str(doc.id)


def _cuerpo(**cambios) -> dict:
    """Cuerpo base válido de alta de acto con el cargo DIR-ADM de company_a."""
    cuerpo = {
        "tipo": "RESOLUCION",
        "numero": "DA-001-NOTIF",
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


def _acto_emitido(mundo, numero, caracter="PARTICULAR", *, fecha=None) -> dict:
    """Crea y emite un acto; devuelve el acto emitido."""
    cuerpo = _cuerpo(
        numero=numero,
        caracter=caracter,
    )
    if caracter == "GENERAL":
        cuerpo["destinatario"] = None
    if fecha is not None:
        cuerpo["fecha"] = fecha.isoformat()
    resp = mundo.post(A, "ua", mundo.company_a, cuerpo)
    assert resp.status_code == 201, resp.text
    acto = resp.json()
    acto_id = acto["id"]
    doc = _doc_con_version(mundo, mundo.company_a, resource_id=acto_id)
    resp = mundo.client.post(
        f"/api/v1{A}/{acto_id}/emitir",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(acto["version"])},
        json={"documento_acto_id": doc},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _destinatario(**cambios) -> dict:
    """Cuerpo válido de destinatario para la notificación."""
    cuerpo = {
        "tipo_persona": "NATURAL",
        "nombre": "Pedro Pérez",
        "identificacion": "V-12345678",
        "domicilio": "Calle 1, casa 2, Caracas",
        "recursos": "Recurso de reconsideración ante el mismo órgano en 15 días hábiles (LOPA art. 94)",
    }
    cuerpo.update(cambios)
    return cuerpo


def _crear_usuario_rol(mundo, username, email, resource, actions):
    """Crea un usuario con rol y scope para company_a; devuelve el id."""
    with mundo.factory() as db:
        usuario = identity_service.create_user(
            db,
            tenant_id=mundo.t1,
            username=username,
            email=email,
            password=PASSWORD,
            created_by=None,
        )
        rol = Role(
            code=f"R_{resource}_NOTIF",
            name=f"Rol {resource}",
            tenant_id=mundo.t1,
            protected=False,
            status="ACTIVE",
        )
        db.add(rol)
        db.flush()
        for accion in actions:
            permiso = db.scalar(
                select(Permission).where(
                    Permission.resource == resource,
                    Permission.action == accion,
                )
            )
            db.add(RolePermission(role_id=rol.id, permission_id=permiso.id))
        db.add(UserRole(user_id=usuario.id, role_id=rol.id, company_id=None))
        db.add(UserScope(user_id=usuario.id, company_id=mundo.company_a))
        db.commit()
        return usuario.id


@pytest.fixture(autouse=True)
def preparar_cargo_dir_adm(mundo, gobierno):
    """Prepara ente, estructura, unidad y cargo DIR-ADM de company_a una sola vez (como GA-02 de DOC-02)."""
    if "dir_adm" in ESTADO:
        return
    _ente(mundo, mundo.company_a, "ACTIVO")
    resp = mundo.post("/gobierno/estructuras", "ua", mundo.company_a, {"ejercicio": ANIO})
    assert resp.status_code == 201, resp.text
    estructura_id = resp.json()["id"]
    resp = mundo.post(
        f"/gobierno/estructuras/{ANIO}/unidades",
        "ua",
        mundo.company_a,
        {"codigo": "DA-01", "denominacion": "Dirección de Administración", "tipo": "UNIDAD_ADMINISTRATIVA"},
    )
    assert resp.status_code == 201, resp.text
    unidad_id = resp.json()["id"]
    _publicar_estructura(mundo, mundo.company_a, estructura_id, "ua")
    cargo = _crear_cargo_y_competencias(
        mundo,
        mundo.company_a,
        unidad_id,
        "DIR-ADM",
        "Director de Administración",
        [("APROBAR", "CONTRATACIONES")],
    )
    ESTADO["dir_adm"] = cargo["id"]

def test_gn01_lista_y_modulo(mundo, gobierno):
    """GN-01: lista por año y validación de anio."""
    resp = mundo.get(f"{N}?anio={ANIO}", "ua", mundo.company_a)
    assert resp.status_code == 200, resp.text
    datos = resp.json()
    assert set(datos) == {"anio", "items", "total"}
    assert datos["anio"] == ANIO

    resp = mundo.get(N, "ua", mundo.company_a)
    assert resp.status_code == 422, resp.text


def test_gn02_alta(mundo, gobierno):
    """GN-02: alta de notificación y efectos sobre el acto."""
    acto = _acto_emitido(mundo, f"NT-002-{ANIO}")
    acto_id = acto["id"]

    resp = mundo.post(
        N,
        "ua",
        mundo.company_a,
        {
            "acto_id": acto_id,
            **_destinatario(identificacion="v 12.345.678"),
        },
    )
    assert resp.status_code == 201, resp.text
    notificacion = resp.json()
    assert notificacion["estado"] == "PENDIENTE"
    assert notificacion["identificacion"] == "V-12345678"
    assert notificacion["version"] == 1
    assert notificacion["intentos"] == []

    assert len(_eventos(mundo, "GOV_NOTIFICATION_CREATED", mundo.company_a)) >= 1

    resp = mundo.get(f"{A}/{acto_id}", "ua", mundo.company_a)
    assert resp.status_code == 200, resp.text
    acto_actualizado = resp.json()
    assert acto_actualizado["notificaciones"] == {
        "total": 1,
        "notificadas": 0,
        "pendientes": 1,
    }


def test_gn03_rechazos_de_alta(mundo, gobierno):
    """GN-03: validaciones y conflictos en alta."""
    acto_general = _acto_emitido(mundo, f"NT-003-G-{ANIO}", caracter="GENERAL")
    resp = mundo.post(
        N,
        "ua",
        mundo.company_a,
        {"acto_id": acto_general["id"], **_destinatario()},
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "GOV_NOTIFICATION_ACT_NOT_PARTICULAR"

    acto_borrador = mundo.post(A, "ua", mundo.company_a, _cuerpo(numero=f"NT-003-B-{ANIO}"))
    assert acto_borrador.status_code == 201, acto_borrador.text
    acto_borrador = acto_borrador.json()
    resp = mundo.post(
        N,
        "ua",
        mundo.company_a,
        {"acto_id": acto_borrador["id"], **_destinatario()},
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "GOV_NOTIFICATION_ACT_NOT_EMITTED"

    acto = _acto_emitido(mundo, f"NT-003-{ANIO}")
    acto_id = acto["id"]
    resp = mundo.post(
        N,
        "ua",
        mundo.company_a,
        {"acto_id": acto_id, **_destinatario(identificacion="V12345678")},
    )
    assert resp.status_code == 201, resp.text

    resp = mundo.post(
        N,
        "ua",
        mundo.company_a,
        {"acto_id": acto_id, **_destinatario(identificacion="V12345678")},
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "GOV_NOTIFICATION_RECIPIENT_DUPLICATE"

    resp = mundo.post(
        N,
        "ua",
        mundo.company_a,
        {"acto_id": acto_id, **_destinatario(identificacion="12")},
    )
    assert resp.status_code == 422, resp.text
    assert "identificacion" in resp.json()["field_errors"]

    resp = mundo.post(
        N,
        "ua",
        mundo.company_a,
        {
            "acto_id": acto_id,
            **_destinatario(
                apoderado_nombre="Luis Gómez",
                apoderado_identificacion=None,
            ),
        },
    )
    assert resp.status_code == 422, resp.text


def test_gn04_correccion(mundo, gobierno):
    """GN-04: corrección con concurrencia optimista y sin cambios."""
    acto = _acto_emitido(mundo, f"NT-004-{ANIO}")
    resp = mundo.post(
        N,
        "ua",
        mundo.company_a,
        {"acto_id": acto["id"], **_destinatario()},
    )
    assert resp.status_code == 201, resp.text
    notificacion = resp.json()
    notificacion_id = notificacion["id"]

    resp = mundo.client.patch(
        f"/api/v1{N}/{notificacion_id}",
        headers=mundo.como("ua", mundo.company_a),
        json={"domicilio": "Nueva dirección"},
    )
    assert resp.status_code == 428, resp.text

    resp = mundo.client.patch(
        f"/api/v1{N}/{notificacion_id}",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "0"},
        json={"domicilio": "Nueva dirección"},
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "GOV_NOTIFICATION_STALE"

    resp = mundo.client.patch(
        f"/api/v1{N}/{notificacion_id}",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "1"},
        json={"domicilio": "Nueva dirección"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["version"] == 2
    assert resp.json()["domicilio"] == "Nueva dirección"

    resp = mundo.client.patch(
        f"/api/v1{N}/{notificacion_id}",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "2"},
        json={"domicilio": "Nueva dirección"},
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "GOV_NOTIFICATION_NO_CHANGES"


def test_gn05_validaciones_del_intento(mundo, gobierno):
    """GN-05: validaciones de documentos, fecha y receptor."""
    acto = _acto_emitido(mundo, f"NT-005-{ANIO}")
    resp = mundo.post(
        N,
        "ua",
        mundo.company_a,
        {"acto_id": acto["id"], **_destinatario()},
    )
    assert resp.status_code == 201, resp.text
    notificacion = resp.json()
    notificacion_id = notificacion["id"]
    notificacion_version = notificacion["version"]

    oficio = _doc_notificacion(mundo, mundo.company_a, notificacion_id=notificacion_id)
    constancia = _doc_notificacion(mundo, mundo.company_a, notificacion_id=notificacion_id)

    resp = mundo.client.post(
        f"/api/v1{N}/{notificacion_id}/intentos",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(notificacion_version)},
        json={
            "medio": "PERSONAL",
            "resultado": "ENTREGADA",
            "fecha": HOY.isoformat(),
            "documento_oficio_id": str(uuid4()),
            "documento_id": constancia,
            "receptor_nombre": "María Gil",
            "receptor_identificacion": "V-7654321",
        },
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "GOV_NOTIFICATION_INVALID_DOCUMENT"

    resp = mundo.client.post(
        f"/api/v1{N}/{notificacion_id}/intentos",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(notificacion_version)},
        json={
            "medio": "PERSONAL",
            "resultado": "ENTREGADA",
            "fecha": HOY.isoformat(),
            "documento_oficio_id": oficio,
            "documento_id": oficio,
            "receptor_nombre": "María Gil",
            "receptor_identificacion": "V-7654321",
        },
    )
    assert resp.status_code == 422, resp.text
    assert "documento_id" in resp.json()["field_errors"]

    resp = mundo.client.post(
        f"/api/v1{N}/{notificacion_id}/intentos",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(notificacion_version)},
        json={
            "medio": "PERSONAL",
            "resultado": "ENTREGADA",
            "fecha": HOY.isoformat(),
            "documento_oficio_id": oficio,
            "documento_id": constancia,
            "receptor_nombre": "María Gil",
            "receptor_identificacion": "V-7654321",
        },
    )
    assert resp.status_code == 200, resp.text


    resp = mundo.client.post(
        f"/api/v1{N}/{notificacion_id}/intentos",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(notificacion_version)},
        json={
            "medio": "PERSONAL",
            "resultado": "ENTREGADA",
            "fecha": HOY.isoformat(),
            "documento_oficio_id": oficio,
            "documento_id": constancia,
            "receptor_nombre": "María Gil",
            "receptor_identificacion": "V-7654321",
        },
    )
    assert resp.status_code == 409, resp.text


def test_gn05b_validaciones_fecha_y_receptor(mundo, gobierno):
    """GN-05 continuación: fecha anterior/futura y ENTREGADA sin receptor."""
    acto = _acto_emitido(mundo, f"NT-005-B-{ANIO}", fecha=HOY)
    resp = mundo.post(
        N,
        "ua",
        mundo.company_a,
        {"acto_id": acto["id"], **_destinatario()},
    )
    assert resp.status_code == 201, resp.text
    notificacion = resp.json()
    notificacion_id = notificacion["id"]
    notificacion_version = notificacion["version"]

    oficio = _doc_notificacion(mundo, mundo.company_a, notificacion_id=notificacion_id)
    constancia = _doc_notificacion(mundo, mundo.company_a, notificacion_id=notificacion_id)

    # fecha anterior a la del acto
    resp = mundo.client.post(
        f"/api/v1{N}/{notificacion_id}/intentos",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(notificacion_version)},
        json={
            "medio": "PERSONAL",
            "resultado": "ENTREGADA",
            "fecha": (HOY - timedelta(days=1)).isoformat(),
            "documento_oficio_id": oficio,
            "documento_id": constancia,
            "receptor_nombre": "María Gil",
            "receptor_identificacion": "V-7654321",
        },
    )
    assert resp.status_code == 422, resp.text
    assert "fecha" in resp.json()["field_errors"]

    # fecha futura
    resp = mundo.client.post(
        f"/api/v1{N}/{notificacion_id}/intentos",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(notificacion_version)},
        json={
            "medio": "PERSONAL",
            "resultado": "ENTREGADA",
            "fecha": (HOY + timedelta(days=1)).isoformat(),
            "documento_oficio_id": oficio,
            "documento_id": constancia,
            "receptor_nombre": "María Gil",
            "receptor_identificacion": "V-7654321",
        },
    )
    assert resp.status_code == 422, resp.text
    assert "fecha" in resp.json()["field_errors"]

    # ENTREGADA sin receptor
    resp = mundo.client.post(
        f"/api/v1{N}/{notificacion_id}/intentos",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(notificacion_version)},
        json={
            "medio": "PERSONAL",
            "resultado": "ENTREGADA",
            "fecha": HOY.isoformat(),
            "documento_oficio_id": oficio,
            "documento_id": constancia,
        },
    )
    assert resp.status_code == 422, resp.text


def test_gn06_entrega_personal_unica(mundo, gobierno):
    """GN-06: entrega personal con un único destinatario y eficacia."""
    acto = _acto_emitido(mundo, f"NT-006-{ANIO}")
    acto_id = acto["id"]
    resp = mundo.post(
        N,
        "ua",
        mundo.company_a,
        {"acto_id": acto_id, **_destinatario()},
    )
    assert resp.status_code == 201, resp.text
    notificacion = resp.json()
    notificacion_id = notificacion["id"]

    oficio = _doc_notificacion(mundo, mundo.company_a, notificacion_id=notificacion_id)
    recibo = _doc_notificacion(mundo, mundo.company_a, notificacion_id=notificacion_id)

    resp = mundo.client.post(
        f"/api/v1{N}/{notificacion_id}/intentos",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "1"},
        json={
            "medio": "PERSONAL",
            "resultado": "ENTREGADA",
            "fecha": HOY.isoformat(),
            "documento_oficio_id": oficio,
            "documento_id": recibo,
            "receptor_nombre": "María Gil",
            "receptor_identificacion": "V-7654321",
        },
    )
    assert resp.status_code == 200, resp.text
    notificacion = resp.json()
    assert notificacion["estado"] == "NOTIFICADA"
    assert notificacion["fecha_notificacion"] == HOY.isoformat()
    assert notificacion["medio_notificacion"] == "PERSONAL"
    assert len(notificacion["intentos"]) == 1

    resp = mundo.get(f"{A}/{acto_id}", "ua", mundo.company_a)
    assert resp.status_code == 200, resp.text
    acto = resp.json()
    assert acto["estado"] == "EFICAZ"
    assert acto["fecha_eficacia"] == HOY.isoformat()
    assert acto["medio"] == "PERSONAL"
    assert acto["documento_eficacia_id"] == recibo

    assert len(_eventos(mundo, "GOV_NOTIFICATION_DELIVERED", mundo.company_a)) >= 1
    assert len(_eventos(mundo, "GOV_ACT_EFFECTIVENESS_RECORDED", mundo.company_a)) >= 1

    with mundo.factory() as db:
        for documento_id in (oficio, recibo):
            link = db.scalar(
                select(DocumentLink).where(
                    DocumentLink.document_id == documento_id,
                    DocumentLink.resource_type == "GovernmentNotification",
                    DocumentLink.resource_id == notificacion_id,
                )
            )
            assert link is not None
            assert link.is_frozen is True


def test_gn07_dos_destinatarios_prensa(mundo, gobierno):
    """GN-07: prensa tras intento fallido con dos destinatarios."""
    acto = _acto_emitido(mundo, f"NT-007-{ANIO}")
    acto_id = acto["id"]
    resp = mundo.post(
        N,
        "ua",
        mundo.company_a,
        {"acto_id": acto_id, **_destinatario(nombre="Destinatario uno", identificacion="V-11111111")},
    )
    assert resp.status_code == 201, resp.text
    d1 = resp.json()
    d1_id = d1["id"]

    resp = mundo.post(
        N,
        "ua",
        mundo.company_a,
        {"acto_id": acto_id, **_destinatario(nombre="Destinatario dos", identificacion="V-22222222")},
    )
    assert resp.status_code == 201, resp.text
    d2 = resp.json()
    d2_id = d2["id"]

    oficio_d1 = _doc_notificacion(mundo, mundo.company_a, notificacion_id=d1_id)
    recibo_d1 = _doc_notificacion(mundo, mundo.company_a, notificacion_id=d1_id)
    resp = mundo.client.post(
        f"/api/v1{N}/{d1_id}/intentos",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "1"},
        json={
            "medio": "PERSONAL",
            "resultado": "ENTREGADA",
            "fecha": HOY.isoformat(),
            "documento_oficio_id": oficio_d1,
            "documento_id": recibo_d1,
            "receptor_nombre": "Receptor D1",
            "receptor_identificacion": "V-33333333",
        },
    )
    assert resp.status_code == 200, resp.text

    resp = mundo.get(f"{A}/{acto_id}", "ua", mundo.company_a)
    acto = resp.json()
    assert acto["estado"] == "EMITIDO"
    assert acto["notificaciones"] == {"total": 2, "notificadas": 1, "pendientes": 1}

    oficio_d2 = _doc_notificacion(mundo, mundo.company_a, notificacion_id=d2_id)
    ejemplar = _doc_notificacion(mundo, mundo.company_a, notificacion_id=d2_id)

    resp = mundo.client.post(
        f"/api/v1{N}/{d2_id}/intentos",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "1"},
        json={
            "medio": "PRENSA",
            "resultado": "PUBLICADA",
            "fecha": HOY.isoformat(),
            "documento_oficio_id": oficio_d2,
            "documento_id": ejemplar,
            "diario": "Diario de prueba",
            "referencia": "Ed. 123",
        },
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "GOV_NOTIFICATION_PRESS_REQUIRES_FAILED_ATTEMPT"

    constancia = _doc_notificacion(mundo, mundo.company_a, notificacion_id=d2_id)
    resp = mundo.client.post(
        f"/api/v1{N}/{d2_id}/intentos",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "1"},
        json={
            "medio": "PERSONAL",
            "resultado": "FALLIDA",
            "fecha": HOY.isoformat(),
            "documento_oficio_id": oficio_d2,
            "documento_id": constancia,
            "motivo_fallo": "Domicilio cerrado",
        },
    )
    assert resp.status_code == 200, resp.text
    d2 = resp.json()
    assert d2["estado"] == "PENDIENTE"
    assert d2["puede_publicar_en_prensa"] is True

    resp = mundo.client.post(
        f"/api/v1{N}/{d2_id}/intentos",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(d2["version"])},
        json={
            "medio": "PRENSA",
            "resultado": "PUBLICADA",
            "fecha": HOY.isoformat(),
            "documento_oficio_id": oficio_d2,
            "documento_id": ejemplar,
            "diario": "Diario de prueba",
            "referencia": "Ed. 123",
        },
    )
    assert resp.status_code == 200, resp.text
    d2 = resp.json()
    fecha_prensa = (HOY + timedelta(days=15)).isoformat()
    assert d2["estado"] == "NOTIFICADA"
    assert d2["fecha_notificacion"] == fecha_prensa

    resp = mundo.get(f"{A}/{acto_id}", "ua", mundo.company_a)
    acto = resp.json()
    assert acto["estado"] == "EFICAZ"
    assert acto["fecha_eficacia"] == fecha_prensa
    assert acto["medio"] == "PRENSA"
    assert acto["referencia_publicacion"] == "Diario de prueba · Ed. 123"


def test_gn08_inmutabilidad(mundo, gobierno):
    """GN-08: una notificación NOTIFICADA es de solo lectura."""
    acto = _acto_emitido(mundo, f"NT-008-{ANIO}")
    acto_id = acto["id"]
    resp = mundo.post(
        N,
        "ua",
        mundo.company_a,
        {"acto_id": acto_id, **_destinatario()},
    )
    assert resp.status_code == 201, resp.text
    notificacion = resp.json()
    notificacion_id = notificacion["id"]

    version_actual = mundo.get(f"{N}/{notificacion_id}", "ua", mundo.company_a).json()["version"]
    oficio = _doc_notificacion(mundo, mundo.company_a, notificacion_id=notificacion_id)
    recibo = _doc_notificacion(mundo, mundo.company_a, notificacion_id=notificacion_id)
    resp = mundo.client.post(
        f"/api/v1{N}/{notificacion_id}/intentos",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(version_actual)},
        json={
            "medio": "PERSONAL",
            "resultado": "ENTREGADA",
            "fecha": HOY.isoformat(),
            "documento_oficio_id": oficio,
            "documento_id": recibo,
            "receptor_nombre": "María Gil",
            "receptor_identificacion": "V-7654321",
        },
    )
    assert resp.status_code == 200, resp.text

    version_actual = mundo.get(f"{N}/{notificacion_id}", "ua", mundo.company_a).json()["version"]
    oficio2 = _doc_notificacion(mundo, mundo.company_a, notificacion_id=notificacion_id)
    recibo2 = _doc_notificacion(mundo, mundo.company_a, notificacion_id=notificacion_id)
    resp = mundo.client.post(
        f"/api/v1{N}/{notificacion_id}/intentos",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(version_actual)},
        json={
            "medio": "PERSONAL",
            "resultado": "ENTREGADA",
            "fecha": HOY.isoformat(),
            "documento_oficio_id": oficio2,
            "documento_id": recibo2,
            "receptor_nombre": "María Gil",
            "receptor_identificacion": "V-7654321",
        },
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] in ("GOV_NOTIFICATION_INVALID_STATE", "GOV_NOTIFICATION_ACT_NOT_EMITTED")

    version_actual = mundo.get(f"{N}/{notificacion_id}", "ua", mundo.company_a).json()["version"]
    resp = mundo.client.post(
        f"/api/v1{N}/{notificacion_id}/anular",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(version_actual)},
        json={"motivo": "Intento de anular"},
    )
    assert resp.status_code == 409, resp.text

    version_actual = mundo.get(f"{N}/{notificacion_id}", "ua", mundo.company_a).json()["version"]
    resp = mundo.client.patch(
        f"/api/v1{N}/{notificacion_id}",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(version_actual)},
        json={"domicilio": "Cambio"},
    )
    assert resp.status_code == 409, resp.text


def test_gn09_anulacion_que_completa(mundo, gobierno):
    """GN-09: anulación que completa la eficacia."""
    acto = _acto_emitido(mundo, f"NT-009-{ANIO}")
    acto_id = acto["id"]
    resp = mundo.post(
        N,
        "ua",
        mundo.company_a,
        {"acto_id": acto_id, **_destinatario(nombre="Destinatario uno", identificacion="V-11111111")},
    )
    assert resp.status_code == 201, resp.text
    d1 = resp.json()
    d1_id = d1["id"]

    resp = mundo.post(
        N,
        "ua",
        mundo.company_a,
        {"acto_id": acto_id, **_destinatario(nombre="Destinatario dos", identificacion="V-22222222")},
    )
    assert resp.status_code == 201, resp.text
    d2 = resp.json()
    d2_id = d2["id"]

    oficio = _doc_notificacion(mundo, mundo.company_a, notificacion_id=d1_id)
    recibo = _doc_notificacion(mundo, mundo.company_a, notificacion_id=d1_id)
    resp = mundo.client.post(
        f"/api/v1{N}/{d1_id}/intentos",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "1"},
        json={
            "medio": "PERSONAL",
            "resultado": "ENTREGADA",
            "fecha": HOY.isoformat(),
            "documento_oficio_id": oficio,
            "documento_id": recibo,
            "receptor_nombre": "Receptor D1",
            "receptor_identificacion": "V-33333333",
        },
    )
    assert resp.status_code == 200, resp.text

    resp = mundo.get(f"{N}/{d2_id}", "ua", mundo.company_a)
    d2 = resp.json()
    # anular sin motivo
    resp = mundo.client.post(
        f"/api/v1{N}/{d2_id}/anular",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(d2["version"])},
        json={},
    )
    assert resp.status_code == 422, resp.text

    # anulación válida
    resp = mundo.client.post(
        f"/api/v1{N}/{d2_id}/anular",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(d2["version"])},
        json={"motivo": "Registrado por error"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["estado"] == "ANULADA"

    resp = mundo.get(f"{A}/{acto_id}", "ua", mundo.company_a)
    acto = resp.json()
    assert acto["estado"] == "EFICAZ"
    assert acto["fecha_eficacia"] == HOY.isoformat()

    # acto ya eficaz: nuevo alta rechazada
    otrod2 = _destinatario(nombre="Destinatario tres", identificacion="V-44444444")
    resp = mundo.post(N, "ua", mundo.company_a, {"acto_id": acto_id, **otrod2})
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "GOV_NOTIFICATION_ACT_NOT_EMITTED"


def test_gn10_acto_revocado(mundo, gobierno):
    """GN-10: un acto revocado no admite intentos."""
    acto = _acto_emitido(mundo, f"NT-010-{ANIO}")
    acto_id = acto["id"]
    resp = mundo.post(
        N,
        "ua",
        mundo.company_a,
        {"acto_id": acto_id, **_destinatario()},
    )
    assert resp.status_code == 201, resp.text
    notificacion = resp.json()
    notificacion_id = notificacion["id"]

    referencia = _acto_emitido(mundo, f"NT-010-R-{ANIO}", caracter="GENERAL")
    resp = mundo.client.post(
        f"/api/v1{A}/{acto_id}/revocar",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(acto["version"])},
        json={"acto_id_referencia": referencia["id"], "motivo": "Revocación de prueba"},
    )
    assert resp.status_code == 200, resp.text

    oficio = _doc_notificacion(mundo, mundo.company_a, notificacion_id=notificacion_id)
    recibo = _doc_notificacion(mundo, mundo.company_a, notificacion_id=notificacion_id)
    resp = mundo.client.post(
        f"/api/v1{N}/{notificacion_id}/intentos",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "1"},
        json={
            "medio": "PERSONAL",
            "resultado": "ENTREGADA",
            "fecha": HOY.isoformat(),
            "documento_oficio_id": oficio,
            "documento_id": recibo,
            "receptor_nombre": "María Gil",
            "receptor_identificacion": "V-7654321",
        },
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "GOV_NOTIFICATION_ACT_NOT_EMITTED"


def test_gn11_doc02_eficacia(mundo, gobierno):
    """GN-11: POST /eficacia rechaza actos PARTICULARES."""
    acto = _acto_emitido(mundo, f"NT-011-{ANIO}")
    resp = mundo.client.post(
        f"/api/v1{A}/{acto['id']}/eficacia",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(acto["version"])},
        json={
            "medio": "PERSONAL",
            "fecha": HOY.isoformat(),
            "documento_eficacia_id": _doc_con_version(
                mundo, mundo.company_a, resource_id=acto["id"]
            ),
        },
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "GOV_ACT_NOTIFICATION_REQUIRED"


def test_gn12_historial(mundo, gobierno):
    """GN-12: historial de versiones de la notificación de prensa."""
    acto = _acto_emitido(mundo, f"NT-012-{ANIO}")
    resp = mundo.post(
        N,
        "ua",
        mundo.company_a,
        {"acto_id": acto["id"], **_destinatario(nombre="Destinatario Dos", identificacion="V-22222222")},
    )
    assert resp.status_code == 201, resp.text
    d2 = resp.json()
    d2_id = d2["id"]

    oficio = _doc_notificacion(mundo, mundo.company_a, notificacion_id=d2_id)
    constancia = _doc_notificacion(mundo, mundo.company_a, notificacion_id=d2_id)
    resp = mundo.client.post(
        f"/api/v1{N}/{d2_id}/intentos",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "1"},
        json={
            "medio": "PERSONAL",
            "resultado": "FALLIDA",
            "fecha": HOY.isoformat(),
            "documento_oficio_id": oficio,
            "documento_id": constancia,
            "motivo_fallo": "Domicilio cerrado",
        },
    )
    assert resp.status_code == 200, resp.text
    d2 = resp.json()

    ejemplar = _doc_notificacion(mundo, mundo.company_a, notificacion_id=d2_id)
    resp = mundo.client.post(
        f"/api/v1{N}/{d2_id}/intentos",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(d2["version"])},
        json={
            "medio": "PRENSA",
            "resultado": "PUBLICADA",
            "fecha": HOY.isoformat(),
            "documento_oficio_id": oficio,
            "documento_id": ejemplar,
            "diario": "Diario de prueba",
            "referencia": "Ed. 123",
        },
    )
    assert resp.status_code == 200, resp.text

    resp = mundo.get(f"{N}/{d2_id}/versiones", "ua", mundo.company_a)
    assert resp.status_code == 200, resp.text
    datos = resp.json()
    assert datos["total"] == 3
    estados = [item["estado"] for item in datos["items"]]
    assert estados == ["PENDIENTE", "PENDIENTE", "NOTIFICADA"]
    motivos = [item["motivo"] or "" for item in datos["items"]]
    assert "Intento fallido" in motivos[1]
    assert "Publicación en prensa" in motivos[2]


def test_gn13_csv(mundo, gobierno):
    """GN-13: exportación CSV y evento de auditoría."""
    acto = _acto_emitido(mundo, f"NT-013-{ANIO}")
    acto_id = acto["id"]
    resp = mundo.post(
        N,
        "ua",
        mundo.company_a,
        {"acto_id": acto_id, **_destinatario()},
    )
    assert resp.status_code == 201, resp.text

    antes = len(_eventos(mundo, "GOV_NOTIFICATIONS_EXPORTED", mundo.company_a))
    resp = mundo.client.get(
        f"/api/v1{N}/exportar?anio={ANIO}",
        headers=mundo.como("ua", mundo.company_a),
    )
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("text/csv")
    assert f"notificaciones-{ANIO}.csv" in resp.headers.get(
        "content-disposition", ""
    )
    contenido = resp.text
    lector = list(csv_reader(StringIO(contenido)))
    assert len(lector) >= 2
    assert lector[0]
    assert len(_eventos(mundo, "GOV_NOTIFICATIONS_EXPORTED", mundo.company_a)) == antes + 1


def test_gn14_permisos(mundo, gobierno):
    """GN-14: permisos view/edit/record."""
    _crear_usuario_rol(
        mundo,
        "notipreparador",
        "notipreparador@example.test",
        "gobierno_notificaciones",
        ("view", "edit"),
    )
    _crear_usuario_rol(
        mundo,
        "noticonsulta",
        "noticonsulta@example.test",
        "gobierno_notificaciones",
        ("view",),
    )

    # noticonsulta GET lista OK pero POST denegado
    resp = mundo.get(f"{N}?anio={ANIO}", "noticonsulta", mundo.company_a)
    assert resp.status_code == 200, resp.text

    acto = _acto_emitido(mundo, f"NT-014-{ANIO}")
    resp = mundo.post(
        N,
        "noticonsulta",
        mundo.company_a,
        {"acto_id": acto["id"], **_destinatario()},
    )
    assert resp.status_code == 403, resp.text

    # notipreparador crea, pero su intento está denegado
    resp = mundo.post(
        N,
        "notipreparador",
        mundo.company_a,
        {"acto_id": acto["id"], **_destinatario()},
    )
    assert resp.status_code == 201, resp.text
    notificacion = resp.json()
    notificacion_id = notificacion["id"]

    oficio = _doc_notificacion(mundo, mundo.company_a, notificacion_id=notificacion_id)
    recibo = _doc_notificacion(mundo, mundo.company_a, notificacion_id=notificacion_id)
    resp = mundo.client.post(
        f"/api/v1{N}/{notificacion_id}/intentos",
        headers={**mundo.como("notipreparador", mundo.company_a), "If-Match": "1"},
        json={
            "medio": "PERSONAL",
            "resultado": "ENTREGADA",
            "fecha": HOY.isoformat(),
            "documento_oficio_id": oficio,
            "documento_id": recibo,
            "receptor_nombre": "María Gil",
            "receptor_identificacion": "V-7654321",
        },
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "PERMISSION_DENIED"


def test_gn15_aislamiento(mundo, gobierno):
    """GN-15: aislamiento entre empresas."""
    acto = _acto_emitido(mundo, f"NT-015-{ANIO}")
    resp = mundo.post(
        N,
        "ua",
        mundo.company_a,
        {"acto_id": acto["id"], **_destinatario()},
    )
    assert resp.status_code == 201, resp.text
    notificacion = resp.json()
    notificacion_id = notificacion["id"]

    resp = mundo.get(f"{N}/{notificacion_id}", "ub", mundo.company_b)
    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == "GOV_NOTIFICATION_NOT_FOUND"

    resp = mundo.client.patch(
        f"/api/v1{N}/{notificacion_id}",
        headers={**mundo.como("ub", mundo.company_b), "If-Match": "1"},
        json={"domicilio": "Cambio"},
    )
    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == "GOV_NOTIFICATION_NOT_FOUND"

    oficio = _doc_notificacion(mundo, mundo.company_b, notificacion_id=notificacion_id)
    constancia = _doc_notificacion(mundo, mundo.company_b, notificacion_id=notificacion_id)
    resp = mundo.client.post(
        f"/api/v1{N}/{notificacion_id}/intentos",
        headers={**mundo.como("ub", mundo.company_b), "If-Match": "1"},
        json={
            "medio": "PERSONAL",
            "resultado": "ENTREGADA",
            "fecha": HOY.isoformat(),
            "documento_oficio_id": oficio,
            "documento_id": constancia,
            "receptor_nombre": "María Gil",
            "receptor_identificacion": "V-7654321",
        },
    )
    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == "GOV_NOTIFICATION_NOT_FOUND"

    resp = mundo.get(f"{N}?anio={ANIO}", "ub", mundo.company_b)
    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == "GOV_ENTITY_NOT_FOUND"
    assert notificacion_id not in resp.text

    resp = mundo.post(
        N,
        "ub",
        mundo.company_b,
        {"acto_id": acto["id"], **_destinatario()},
    )
    assert resp.status_code == 404, resp.text


def test_gn16_mfa(mundo, gobierno):
    """GN-16: clasificación MFA."""
    assert classify({"gobierno_notificaciones:view"}) == STANDARD
    assert classify({"gobierno_notificaciones:edit"}) == SENSITIVE
    assert classify({"gobierno_notificaciones:record"}) == SENSITIVE


def test_gn17_constancia_repetida(mundo, gobierno):
    """GN-17: constancia repetida en una misma notificación."""
    acto = _acto_emitido(mundo, f"NT-017-{ANIO}")
    resp = mundo.post(
        N,
        "ua",
        mundo.company_a,
        {"acto_id": acto["id"], **_destinatario()},
    )
    assert resp.status_code == 201, resp.text
    notificacion = resp.json()
    notificacion_id = notificacion["id"]

    oficio = _doc_notificacion(mundo, mundo.company_a, notificacion_id=notificacion_id)
    constancia = _doc_notificacion(mundo, mundo.company_a, notificacion_id=notificacion_id)
    resp = mundo.client.post(
        f"/api/v1{N}/{notificacion_id}/intentos",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "1"},
        json={
            "medio": "PERSONAL",
            "resultado": "FALLIDA",
            "fecha": HOY.isoformat(),
            "documento_oficio_id": oficio,
            "documento_id": constancia,
            "motivo_fallo": "Domicilio cerrado",
        },
    )
    assert resp.status_code == 200, resp.text
    notificacion = resp.json()

    resp = mundo.client.post(
        f"/api/v1{N}/{notificacion_id}/intentos",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(notificacion["version"])},
        json={
            "medio": "PERSONAL",
            "resultado": "FALLIDA",
            "fecha": HOY.isoformat(),
            "documento_oficio_id": oficio,
            "documento_id": constancia,
            "motivo_fallo": "Otro intento",
        },
    )
    assert resp.status_code == 422, resp.text
    assert "documento_id" in resp.json()["field_errors"]


def test_gn18_concurrencia(mundo, gobierno):
    """GN-18: concurrencia en intentos con la misma versión."""
    acto = _acto_emitido(mundo, f"NT-018-{ANIO}")
    resp = mundo.post(
        N,
        "ua",
        mundo.company_a,
        {"acto_id": acto["id"], **_destinatario()},
    )
    assert resp.status_code == 201, resp.text
    notificacion = resp.json()
    notificacion_id = notificacion["id"]

    oficio = _doc_notificacion(mundo, mundo.company_a, notificacion_id=notificacion_id)
    recibo1 = _doc_notificacion(mundo, mundo.company_a, notificacion_id=notificacion_id)
    recibo2 = _doc_notificacion(mundo, mundo.company_a, notificacion_id=notificacion_id)

    intento = {
        "medio": "PERSONAL",
        "resultado": "ENTREGADA",
        "fecha": HOY.isoformat(),
        "documento_oficio_id": oficio,
        "receptor_nombre": "María Gil",
        "receptor_identificacion": "V-7654321",
    }
    r1 = mundo.client.post(
        f"/api/v1{N}/{notificacion_id}/intentos",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "1"},
        json={**intento, "documento_id": recibo1},
    )
    assert r1.status_code == 200, r1.text

    r2 = mundo.client.post(
        f"/api/v1{N}/{notificacion_id}/intentos",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": "1"},
        json={**intento, "documento_id": recibo2},
    )
    assert r2.status_code == 409, r2.text
    assert r2.json()["code"] in ("GOV_NOTIFICATION_STALE", "GOV_NOTIFICATION_INVALID_STATE")

    resp = mundo.get(f"{N}/{notificacion_id}", "ua", mundo.company_a)
    notificacion = resp.json()
    assert len([i for i in notificacion["intentos"] if i["resultado"] == "ENTREGADA"]) == 1


def test_gn19_restricciones_bd(mundo, gobierno):
    """GN-19: restricciones de integridad en la base de datos."""
    acto = _acto_emitido(mundo, f"NT-019-{ANIO}")
    acto_id = acto["id"]

    with mundo.factory() as db:
        # NOTIFICADA sin fecha
        with pytest.raises(IntegrityError, match="ck_gov_notifications_notificada_fechada"):
            notif = GovernmentNotification(
                company_id=mundo.company_a,
                act_id=acto_id,
                tipo_persona="NATURAL",
                nombre="Sin fecha",
                identificacion="V-12345678",
                identificacion_clave="V12345678",
                domicilio="Calle 1",
                recursos="Recursos",
                status="NOTIFICADA",
                fecha_notificacion=None,
                medio_notificacion=None,
                version=1,
            )
            db.add(notif)
            db.commit()
        db.rollback()

    with mundo.factory() as db:
        # apoderado incompleto
        with pytest.raises(IntegrityError, match="ck_gov_notifications_apoderado_completo"):
            notif = GovernmentNotification(
                company_id=mundo.company_a,
                act_id=acto_id,
                tipo_persona="NATURAL",
                nombre="Apoderado incompleto",
                identificacion="V-87654321",
                identificacion_clave="V87654321",
                domicilio="Calle 2",
                recursos="Recursos",
                apoderado_nombre="Solo nombre",
                apoderado_identificacion=None,
                status="PENDIENTE",
                version=1,
            )
            db.add(notif)
            db.commit()
        db.rollback()

    with mundo.factory() as db:
        # attempt PRENSA ENTREGADA
        notif = GovernmentNotification(
            company_id=mundo.company_a,
            act_id=acto_id,
            tipo_persona="NATURAL",
            nombre="Para intento",
            identificacion="V-11111111",
            identificacion_clave="V11111111",
            domicilio="Calle 3",
            recursos="Recursos",
            status="PENDIENTE",
            version=1,
        )
        db.add(notif)
        db.flush()
        with pytest.raises(IntegrityError, match="ck_gov_notification_attempts_medio_resultado"):
            attempt = GovernmentNotificationAttempt(
                company_id=mundo.company_a,
                notification_id=notif.id,
                numero=1,
                medio="PRENSA",
                resultado="ENTREGADA",
                fecha=HOY,
                documento_id=_doc_notificacion(mundo, mundo.company_a, notificacion_id=str(notif.id)),
                receptor_nombre="Receptor prensa",
                receptor_identificacion="V-55555555",
            )
            db.add(attempt)
            db.commit()
        db.rollback()

    with mundo.factory() as db:
        # ENTREGADA sin receptor
        notif2 = GovernmentNotification(
            company_id=mundo.company_a,
            act_id=acto_id,
            tipo_persona="NATURAL",
            nombre="Otro receptor",
            identificacion="V-22222222",
            identificacion_clave="V22222222",
            domicilio="Calle 4",
            recursos="Recursos",
            status="PENDIENTE",
            version=1,
        )
        db.add(notif2)
        db.flush()
        with pytest.raises(IntegrityError, match="ck_gov_notification_attempts_entregada_receptor"):
            attempt = GovernmentNotificationAttempt(
                company_id=mundo.company_a,
                notification_id=notif2.id,
                numero=1,
                medio="PERSONAL",
                resultado="ENTREGADA",
                fecha=HOY,
                documento_id=_doc_notificacion(mundo, mundo.company_a, notificacion_id=str(notif2.id)),
                receptor_nombre=None,
                receptor_identificacion=None,
            )
            db.add(attempt)
            db.commit()
        db.rollback()

    with mundo.factory() as db:
        # duplicado no anulado
        notif3 = GovernmentNotification(
            company_id=mundo.company_a,
            act_id=acto_id,
            tipo_persona="NATURAL",
            nombre="Duplicado",
            identificacion="V-33333333",
            identificacion_clave="V33333333",
            domicilio="Calle 5",
            recursos="Recursos",
            status="PENDIENTE",
            version=1,
        )
        db.add(notif3)
        db.flush()
        with pytest.raises(IntegrityError, match="uq_gov_notifications_act_destinatario"):
            duplicado = GovernmentNotification(
                company_id=mundo.company_a,
                act_id=acto_id,
                tipo_persona="NATURAL",
                nombre="Duplicado 2",
                identificacion="V-33333333",
                identificacion_clave="V33333333",
                domicilio="Calle 6",
                recursos="Recursos",
                status="PENDIENTE",
                version=1,
            )
            db.add(duplicado)
            db.commit()
        db.rollback()


def test_gn20_catalogo(mundo, gobierno):
    """GN-20: códigos de auditoría en el catálogo."""
    esperados = {
        "GOV_NOTIFICATION_CREATED",
        "GOV_NOTIFICATION_UPDATED",
        "GOV_NOTIFICATION_CANCELLED",
        "GOV_NOTIFICATION_DELIVERED",
        "GOV_NOTIFICATION_ATTEMPT_FAILED",
        "GOV_NOTIFICATION_PUBLISHED",
        "GOV_NOTIFICATIONS_EXPORTED",
    }
    catalogo = {code for code, _ in catalog()}
    assert esperados.issubset(catalogo)


def test_gn21_recursos_obligatorios(mundo, gobierno):
    """GN-21: los recursos que proceden son obligatorios al crear (LOPA art. 73)."""
    acto = _acto_emitido(mundo, f"NT-021-{ANIO}")

    resp = mundo.post(N, "ua", mundo.company_a, {"acto_id": acto["id"], **_destinatario(recursos="")})
    assert resp.status_code == 422
    assert "recursos" in resp.json()["field_errors"]

    resp = mundo.post(N, "ua", mundo.company_a, {"acto_id": acto["id"], **_destinatario(recursos="x" * 2001)})
    assert resp.status_code == 422
    assert "recursos" in resp.json()["field_errors"]

    resp = mundo.post(N, "ua", mundo.company_a, {"acto_id": acto["id"], **_destinatario(recursos="  No proceden recursos  ")})
    assert resp.status_code == 201
    assert resp.json()["recursos"] == "No proceden recursos"
