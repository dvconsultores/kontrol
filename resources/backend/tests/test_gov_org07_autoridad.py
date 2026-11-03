"""Suite de backend para ORG-07 (GOV-ORG-010): API de solo lectura de la matriz de autoridad.

Especifica el contrato del módulo `app.modules.government` antes de que exista la API.
Hoy todas las pruebas fallan con 404 en las rutas nuevas (rojo esperado).
"""
from copy import deepcopy
from csv import reader as csv_reader
from datetime import UTC, date, datetime
from decimal import Decimal
from io import StringIO
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select

from app.modules.audit.models import AuditEvent
from app.modules.documents.models import Document, DocumentLink, DocumentType
from app.modules.government.models import (
    GovernmentEntity,
    GovernmentPosition,
    GovernmentPositionCompetency,
    GovernmentPositionVersion,
    GovernmentStructure,
    GovernmentUnit,
)
from app.modules.identity_access import service as identity_service
from app.modules.identity_access.mfa_policy import STANDARD, classify
from app.modules.identity_access.models import (
    Permission,
    Role,
    RolePermission,
    UserRole,
    UserScope,
)
from app.modules.licensing import service as licensing_service
from app.modules.licensing.models import LicenseEntitlementSnapshot
from app.modules.setup.api import CATALOGO_DE_PERMISOS
from app.shared.clock import hoy_de_negocio
from tests.conftest_multicompany import PASSWORD

pytest_plugins = ("tests.conftest_multicompany",)

ANIO = hoy_de_negocio().year
ANTERIOR = ANIO - 1
SIGUIENTE = ANIO + 1
A = "/gobierno/autoridad"
TZ_CARACAS = ZoneInfo("America/Caracas")
ESTADO: dict = {}


def _u(ej):
    return f"{A}/{ej}"


@pytest.fixture
def gobierno(mundo):
    """Garantiza el entitlement `gobierno` en la snapshot sincronizada."""
    with mundo.factory() as db:
        inst = licensing_service.get_installation(db)
        snapshot = db.scalar(
            select(LicenseEntitlementSnapshot).where(
                LicenseEntitlementSnapshot.installation_id == inst.installation_uuid,
                LicenseEntitlementSnapshot.version == "org07-test",
            )
        )
        if snapshot is None:
            snapshot = LicenseEntitlementSnapshot(
                installation_id=inst.installation_uuid,
                modules={"gobierno": True},
                version="org07-test",
                taken_at=datetime.now(UTC),
            )
            db.add(snapshot)
        else:
            snapshot.modules = {"gobierno": True}
        db.commit()


def _ente(mundo, company_id):
    """Crea un GovernmentEntity ACTIVO para la empresa."""
    with mundo.factory() as db:
        ente = GovernmentEntity(
            company_id=company_id,
            denominacion=f"Ente activo {company_id}",
            status="ACTIVO",
            version=1,
            activated_at=datetime.now(UTC),
        )
        db.add(ente)
        db.commit()
        return ente.id


def _doc_tipo(mundo, company_id, code, name):
    with mundo.factory() as db:
        tipo = db.scalar(
            select(DocumentType).where(
                DocumentType.company_id == company_id,
                DocumentType.code == code,
            )
        )
        if tipo is None:
            tipo = DocumentType(company_id=company_id, code=code, name=name)
            db.add(tipo)
            db.commit()
        return tipo.id


def _documento(mundo, company_id, title, status="ACTIVE"):
    with mundo.factory() as db:
        tipo_id = _doc_tipo(mundo, company_id, "GOV-AUT", "Acto de matriz de autoridad")
        doc = Document(
            company_id=company_id,
            document_type_id=tipo_id,
            title=title,
            status=status,
        )
        db.add(doc)
        db.commit()
        return doc.id


def _vincula_acto(mundo, company_id, position_id, document_id):
    with mundo.factory() as db:
        tipo_id = _doc_tipo(mundo, company_id, "GOV-AUT", "Acto de matriz de autoridad")
        db.add(
            DocumentLink(
                document_id=document_id,
                company_id=company_id,
                document_type_id=tipo_id,
                resource_type="GovernmentPosition",
                resource_id=position_id,
            )
        )
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


def _crear_estructura(
    mundo,
    company_id,
    ente_id,
    ejercicio,
    status,
    *,
    published=True,
    closed=False,
):
    """Crea una estructura para una empresa y ejercicio."""
    with mundo.factory() as db:
        estructura = GovernmentStructure(
            company_id=company_id,
            entity_id=ente_id,
            exercise=ejercicio,
            status=status,
            version=1,
        )
        if published:
            estructura.published_at = datetime(ejercicio, 1, 1, 12, 0, tzinfo=TZ_CARACAS)
        if closed:
            estructura.closed_at = datetime(ejercicio, 12, 31, 12, 0, tzinfo=TZ_CARACAS)
        db.add(estructura)
        db.flush()
        db.commit()
        return estructura.id


def _unidad(mundo, company_id, structure_id, code, name, parent_id=None, valid_from=None):
    with mundo.factory() as db:
        unidad = GovernmentUnit(
            company_id=company_id,
            structure_id=structure_id,
            parent_id=parent_id,
            code=code,
            name=name,
            unit_type="UNIDAD_ADMINISTRATIVA",
            status="ACTIVA",
            valid_from=date(ANIO, 1, 1) if valid_from is None else valid_from,
            version=1,
        )
        db.add(unidad)
        db.commit()
        return unidad.id


def _version_snapshot(
    *,
    codigo,
    denominacion,
    unidad_id,
    unidad_codigo,
    estado,
    vigente_desde,
    vigente_hasta,
    competencias,
):
    return {
        "codigo": codigo,
        "denominacion": denominacion,
        "unidad_id": unidad_id,
        "unidad_codigo": unidad_codigo,
        "estado": estado,
        "vigente_desde": vigente_desde,
        "vigente_hasta": vigente_hasta,
        "competencias": competencias,
    }


def _competencia(
    *,
    action,
    subject,
    limit_type,
    amount=None,
    currency=None,
    basis=None,
):
    return {
        "accion": action,
        "materia": subject,
        "tipo_limite": limit_type,
        "monto": amount,
        "moneda": currency,
        "fundamento": basis,
    }


def _crear_cargo_y_versiones(
    mundo,
    *,
    company_id,
    structure_id,
    unit_id,
    code,
    denominacion,
    status,
    valid_from,
    valid_to,
    versiones,
):
    """Crea un cargo con sus versiones y devuelve position_id y sus ids de competencia."""
    with mundo.factory() as db:
        cargo = GovernmentPosition(
            company_id=company_id,
            structure_id=structure_id,
            unit_id=unit_id,
            code=code,
            name=denominacion,
            status=status,
            valid_from=valid_from,
            valid_to=valid_to,
            activated_at=datetime.now(UTC),
            version=len(versiones),
        )
        db.add(cargo)
        db.commit()
        cargo_id = cargo.id

        ultima_version = versiones[-1] if versiones else None
        competencias_ids = {}
        for numero, version in enumerate(versiones, start=1):
            db.add(
                GovernmentPositionVersion(
                    position_id=cargo_id,
                    structure_id=structure_id,
                    company_id=company_id,
                    version=numero,
                    status=version["status"],
                    snapshot=version["snapshot"],
                    reason=version.get("reason"),
                    actor_id=None,
                    created_at=version["created_at"],
                )
            )
            db.commit()

        # Materializa las competencias SOLO de la última versión (estado actual del cargo).
        if ultima_version is not None and ultima_version["status"] == cargo.status:
            for item in ultima_version["snapshot"]["competencias"]:
                competencia = GovernmentPositionCompetency(
                    position_id=cargo_id,
                    company_id=company_id,
                    action=item["accion"],
                    subject=item["materia"],
                    limit_type=item["tipo_limite"],
                    limit_amount=(
                        None if item["monto"] is None else Decimal(item["monto"])
                    ),
                    limit_currency=item["moneda"],
                    basis=item["fundamento"],
                )
                db.add(competencia)
                db.commit()
                competencias_ids[item["accion"]] = competencia.id

        return cargo_id, competencias_ids


@pytest.fixture(scope="module")
def matriz(mundo):
    """Crea directamente con modelos los datos de prueba de la matriz."""
    ANIO = hoy_de_negocio().year
    tz = TZ_CARACAS

    ente_a = _ente(mundo, mundo.company_a)
    ente_b = _ente(mundo, mundo.company_b)

    str_a = _crear_estructura(
        mundo, mundo.company_a, ente_a, ANIO, "VIGENTE", published=True
    )
    str_a_anterior = _crear_estructura(
        mundo,
        mundo.company_a,
        ente_a,
        ANIO - 1,
        "CERRADA",
        published=True,
        closed=True,
    )
    str_b = _crear_estructura(
        mundo, mundo.company_b, ente_b, ANIO, "VIGENTE", published=True
    )

    desp_id = _unidad(mundo, mundo.company_a, str_a, "DESP", "Despacho")
    dir_adm_id = _unidad(
        mundo, mundo.company_a, str_a, "DIR-ADM", "Dirección de Administración", desp_id
    )
    coord_id = _unidad(
        mundo, mundo.company_a, str_a, "COORD", "Coordinación de Compras", dir_adm_id
    )
    otra_id = _unidad(mundo, mundo.company_a, str_a, "OTRA", "Unidad suelta")

    unidad_b_id = _unidad(mundo, mundo.company_b, str_b, "B-UNI", "Unidad B")

    # Cargo DIR-ADM
    dir_cargo, _ = _crear_cargo_y_versiones(
        mundo,
        company_id=mundo.company_a,
        structure_id=str_a,
        unit_id=dir_adm_id,
        code="DIR-ADM",
        denominacion="Director de Administración",
        status="VIGENTE",
        valid_from=datetime(ANIO, 1, 1, tzinfo=tz),
        valid_to=None,
        versiones=[
            {
                "status": "BORRADOR",
                "created_at": datetime(ANIO, 1, 2, 12, 0, tzinfo=tz),
                "snapshot": _version_snapshot(
                    codigo="DIR-ADM",
                    denominacion="Director de Administración",
                    unidad_id=str(dir_adm_id),
                    unidad_codigo="DIR-ADM",
                    estado="BORRADOR",
                    vigente_desde=f"{ANIO}-01-01",
                    vigente_hasta=None,
                    competencias=[],
                ),
            },
            {
                "status": "VIGENTE",
                "created_at": datetime(ANIO, 1, 10, 12, 0, tzinfo=tz),
                "snapshot": _version_snapshot(
                    codigo="DIR-ADM",
                    denominacion="Director de Administración",
                    unidad_id=str(dir_adm_id),
                    unidad_codigo="DIR-ADM",
                    estado="VIGENTE",
                    vigente_desde=f"{ANIO}-01-01",
                    vigente_hasta=None,
                    competencias=[
                        _competencia(
                            action="APROBAR",
                            subject="CONTRATACIONES",
                            limit_type="MONTO",
                            amount="1000000.00",
                            currency="VES",
                            basis="Reglamento interno, art. 12",
                        )
                    ],
                ),
            },
            {
                "status": "VIGENTE",
                "created_at": datetime(ANIO, 1, 20, 12, 0, tzinfo=tz),
                "reason": "Amplía el límite",
                "snapshot": _version_snapshot(
                    codigo="DIR-ADM",
                    denominacion="Director de Administración",
                    unidad_id=str(dir_adm_id),
                    unidad_codigo="DIR-ADM",
                    estado="VIGENTE",
                    vigente_desde=f"{ANIO}-01-01",
                    vigente_hasta=None,
                    competencias=[
                        _competencia(
                            action="APROBAR",
                            subject="CONTRATACIONES",
                            limit_type="MONTO",
                            amount="1500000.00",
                            currency="VES",
                            basis="Reglamento interno, art. 12",
                        ),
                        _competencia(
                            action="FIRMAR",
                            subject="EXPEDIENTE",
                            limit_type="SIN_LIMITE",
                        ),
                    ],
                ),
            },
        ],
    )

    doc_dir = _documento(mundo, mundo.company_a, "Resolución DA-001", status="ACTIVE")
    doc_revocado = _documento(
        mundo, mundo.company_a, "Resolución revocada", status="REVOKED"
    )
    _vincula_acto(mundo, mundo.company_a, dir_cargo, doc_dir)
    _vincula_acto(mundo, mundo.company_a, dir_cargo, doc_revocado)

    # Cargo JEF-COMP
    jef_cargo, _ = _crear_cargo_y_versiones(
        mundo,
        company_id=mundo.company_a,
        structure_id=str_a,
        unit_id=coord_id,
        code="JEF-COMP",
        denominacion="Jefe de Compras",
        status="VIGENTE",
        valid_from=datetime(ANIO, 2, 1, tzinfo=tz),
        valid_to=None,
        versiones=[
            {
                "status": "BORRADOR",
                "created_at": datetime(ANIO, 1, 15, 12, 0, tzinfo=tz),
                "snapshot": _version_snapshot(
                    codigo="JEF-COMP",
                    denominacion="Jefe de Compras",
                    unidad_id=str(coord_id),
                    unidad_codigo="COORD",
                    estado="BORRADOR",
                    vigente_desde=f"{ANIO}-02-01",
                    vigente_hasta=None,
                    competencias=[],
                ),
            },
            {
                "status": "VIGENTE",
                "created_at": datetime(ANIO, 3, 1, 12, 0, tzinfo=tz),
                "reason": "Registro retroactivo",
                "snapshot": _version_snapshot(
                    codigo="JEF-COMP",
                    denominacion="Jefe de Compras",
                    unidad_id=str(coord_id),
                    unidad_codigo="COORD",
                    estado="VIGENTE",
                    vigente_desde=f"{ANIO}-02-01",
                    vigente_hasta=None,
                    competencias=[
                        _competencia(
                            action="PAGAR",
                            subject="TESORERIA",
                            limit_type="MONTO",
                            amount="500000.00",
                            currency="VES",
                        )
                    ],
                ),
            },
        ],
    )

    # Cargo SUP
    sup_cargo, _ = _crear_cargo_y_versiones(
        mundo,
        company_id=mundo.company_a,
        structure_id=str_a,
        unit_id=desp_id,
        code="SUP",
        denominacion="Supervisor de Bienes",
        status="INACTIVO",
        valid_from=datetime(ANIO, 1, 1, tzinfo=tz),
        valid_to=datetime(ANIO, 3, 31, tzinfo=tz),
        versiones=[
            {
                "status": "VIGENTE",
                "created_at": datetime(ANIO, 1, 5, 12, 0, tzinfo=tz),
                "snapshot": _version_snapshot(
                    codigo="SUP",
                    denominacion="Supervisor de Bienes",
                    unidad_id=str(desp_id),
                    unidad_codigo="DESP",
                    estado="VIGENTE",
                    vigente_desde=f"{ANIO}-01-01",
                    vigente_hasta=None,
                    competencias=[
                        _competencia(
                            action="CUSTODIAR",
                            subject="BIENES",
                            limit_type="SIN_LIMITE",
                        )
                    ],
                ),
            },
            {
                "status": "INACTIVO",
                "created_at": datetime(ANIO, 4, 2, 12, 0, tzinfo=tz),
                "snapshot": _version_snapshot(
                    codigo="SUP",
                    denominacion="Supervisor de Bienes",
                    unidad_id=str(desp_id),
                    unidad_codigo="DESP",
                    estado="INACTIVO",
                    vigente_desde=f"{ANIO}-01-01",
                    vigente_hasta=f"{ANIO}-03-31",
                    competencias=[
                        _competencia(
                            action="CUSTODIAR",
                            subject="BIENES",
                            limit_type="SIN_LIMITE",
                        )
                    ],
                ),
            },
        ],
    )

    # Cargo BOR (borrador, nunca aparece)
    bor_cargo, _ = _crear_cargo_y_versiones(
        mundo,
        company_id=mundo.company_a,
        structure_id=str_a,
        unit_id=otra_id,
        code="BOR",
        denominacion="Cargo en borrador",
        status="BORRADOR",
        valid_from=datetime(ANIO, 1, 1, tzinfo=tz),
        valid_to=None,
        versiones=[
            {
                "status": "BORRADOR",
                "created_at": datetime(ANIO, 1, 2, 12, 0, tzinfo=tz),
                "snapshot": _version_snapshot(
                    codigo="BOR",
                    denominacion="Cargo en borrador",
                    unidad_id=str(otra_id),
                    unidad_codigo="OTRA",
                    estado="BORRADOR",
                    vigente_desde=f"{ANIO}-01-01",
                    vigente_hasta=None,
                    competencias=[
                        _competencia(
                            action="AUDITAR",
                            subject="PRESUPUESTO",
                            limit_type="SIN_LIMITE",
                        )
                    ],
                ),
            }
        ],
    )

    # Cargo de empresa B
    b_cargo, _ = _crear_cargo_y_versiones(
        mundo,
        company_id=mundo.company_b,
        structure_id=str_b,
        unit_id=unidad_b_id,
        code="B-CARGO",
        denominacion="Cargo B",
        status="VIGENTE",
        valid_from=datetime(ANIO, 1, 1, tzinfo=tz),
        valid_to=None,
        versiones=[
            {
                "status": "VIGENTE",
                "created_at": datetime(ANIO, 1, 2, 12, 0, tzinfo=tz),
                "snapshot": _version_snapshot(
                    codigo="B-CARGO",
                    denominacion="Cargo B",
                    unidad_id=str(unidad_b_id),
                    unidad_codigo="B-UNI",
                    estado="VIGENTE",
                    vigente_desde=f"{ANIO}-01-01",
                    vigente_hasta=None,
                    competencias=[
                        _competencia(
                            action="APROBAR",
                            subject="PRESUPUESTO",
                            limit_type="SIN_LIMITE",
                        )
                    ],
                ),
            }
        ],
    )

    # Cargo de ejercicio anterior
    ant_uni_id = _unidad(
        mundo,
        mundo.company_a,
        str_a_anterior,
        "ANT-UNI",
        "Unidad del ejercicio anterior",
        valid_from=date(ANIO - 1, 1, 1),
    )
    ant_cargo, _ = _crear_cargo_y_versiones(
        mundo,
        company_id=mundo.company_a,
        structure_id=str_a_anterior,
        unit_id=ant_uni_id,
        code="ANT-01",
        denominacion="Cargo anterior",
        status="VIGENTE",
        valid_from=date(ANIO - 1, 1, 1),
        valid_to=None,
        versiones=[
            {
                "status": "VIGENTE",
                "created_at": datetime(ANIO - 1, 1, 2, 12, 0, tzinfo=tz),
                "snapshot": _version_snapshot(
                    codigo="ANT-01",
                    denominacion="Cargo anterior",
                    unidad_id=str(ant_uni_id),
                    unidad_codigo="ANT-UNI",
                    estado="VIGENTE",
                    vigente_desde=f"{ANIO-1}-01-01",
                    vigente_hasta=None,
                    competencias=[
                        _competencia(
                            action="APROBAR",
                            subject="PRESUPUESTO",
                            limit_type="SIN_LIMITE",
                        )
                    ],
                ),
            }
        ],
    )

    ESTADO.update(
        {
            "dir": str(dir_cargo),
            "jef": str(jef_cargo),
            "sup": str(sup_cargo),
            "b_cargo": str(b_cargo),
            "ant": str(ant_cargo),
            "desp": str(desp_id),
            "dir_adm": str(dir_adm_id),
            "coord": str(coord_id),
            "otra": str(otra_id),
            "doc_dir": str(doc_dir),
            "bor": str(bor_cargo),
        }
    )

    return ESTADO


@pytest.fixture
def _permiso_autoridad_view(mundo):
    """Crea el permiso `gobierno_autoridad:view` si no existe para mantener GM-16 válida."""
    with mundo.factory() as db:
        permiso = db.scalar(
            select(Permission).where(
                Permission.resource == "gobierno_autoridad",
                Permission.action == "view",
            )
        )
        if permiso is None:
            permiso = Permission(resource="gobierno_autoridad", action="view")
            db.add(permiso)
            db.commit()
        return permiso.id


def _crear_usuario_con_permiso(mundo, username, resource, action, company_id):
    with mundo.factory() as db:
        usuario = identity_service.create_user(
            db,
            tenant_id=mundo.t1,
            username=username,
            email=f"{username}@example.test",
            password=PASSWORD,
            created_by=None,
        )
        rol = Role(
            code=f"R_{username.upper()}",
            name=username,
            tenant_id=mundo.t1,
            protected=False,
            status="ACTIVE",
        )
        db.add(rol)
        db.flush()

        permiso = db.scalar(
            select(Permission).where(
                Permission.resource == resource,
                Permission.action == action,
            )
        )
        if permiso is None:
            permiso = Permission(resource=resource, action=action)
            db.add(permiso)
            db.flush()

        db.add(RolePermission(role_id=rol.id, permission_id=permiso.id))
        db.add(UserRole(user_id=usuario.id, role_id=rol.id, company_id=None))
        db.add(UserScope(user_id=usuario.id, company_id=company_id))
        db.commit()


def test_gm01_modulo(mundo, gobierno):
    """GM-01: sin `gobierno` en la snapshot → 403 MODULE_NOT_ENTITLED."""
    with mundo.factory() as db:
        inst = licensing_service.get_installation(db)
        snapshot = db.scalar(
            select(LicenseEntitlementSnapshot).where(
                LicenseEntitlementSnapshot.installation_id == inst.installation_uuid,
                LicenseEntitlementSnapshot.version == "org07-test",
            )
        )
        original = snapshot.modules
        snapshot.modules = {}
        db.commit()

    try:
        resp = mundo.get(_u(ANIO), "ua", mundo.company_a)
        assert resp.status_code == 403, resp.text
        assert resp.json()["code"] == "MODULE_NOT_ENTITLED"
    finally:
        with mundo.factory() as db:
            snapshot = db.scalar(
                select(LicenseEntitlementSnapshot).where(
                    LicenseEntitlementSnapshot.installation_id == inst.installation_uuid,
                    LicenseEntitlementSnapshot.version == "org07-test",
                )
            )
            snapshot.modules = original
            db.commit()


def test_gm02_ejercicios(mundo, gobierno, matriz):
    """GM-02: ejercicios devuelve estructuras de la empresa del contexto en orden descendente."""
    resp = mundo.get(f"{A}/ejercicios", "ua", mundo.company_a)
    assert resp.status_code == 200, resp.text
    assert resp.json()["items"] == [
        {"ejercicio": ANIO, "estado": "VIGENTE"},
        {"ejercicio": ANIO - 1, "estado": "CERRADA"},
    ]

    resp = mundo.get(f"{A}/ejercicios", "ub", mundo.company_b)
    assert resp.status_code == 200, resp.text
    assert resp.json()["items"] == [{"ejercicio": ANIO, "estado": "VIGENTE"}]


def test_gm03_filtros(mundo, gobierno, matriz):
    """GM-03: filtros devuelve unidades y cargos VIGENTE/INACTIVO."""
    resp = mundo.get(f"{A}/{ANIO}/filtros", "ua", mundo.company_a)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert [u["ruta"] for u in body["unidades"]] == [
        "DESP",
        "DESP › DIR-ADM",
        "DESP › DIR-ADM › COORD",
        "OTRA",
    ]
    assert [c["codigo"] for c in body["cargos"]] == ["DIR-ADM", "JEF-COMP", "SUP"]


def test_gm04_corte_15_enero(mundo, gobierno, matriz):
    """GM-04: al 15/1 entran SUP y DIR-ADM con la versión 2."""
    resp = mundo.get(
        f"{A}/{ANIO}?fecha={ANIO}-01-15",
        "ua",
        mundo.company_a,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body["items"]) == 2
    filas = {(f["cargo_codigo"], f["accion"], f["materia"]): f for f in body["items"]}
    assert ("SUP", "CUSTODIAR", "BIENES") in filas
    fila = filas[("DIR-ADM", "APROBAR", "CONTRATACIONES")]
    assert fila["monto"] == "1000000.00"
    assert fila["version"]["version"] == 2
    assert ("DIR-ADM", "FIRMAR", "EXPEDIENTE") not in filas
    assert ("JEF-COMP", "PAGAR", "TESORERIA") not in filas
    assert body["total"] == 2
    assert body["cargos"] == 2


def test_gm05_corte_15_febrero(mundo, gobierno, matriz):
    """GM-05: al 15/2 salen 4 filas en el orden fijo y JEF-COMP usa su primera versión VIGENTE."""
    resp = mundo.get(
        f"{A}/{ANIO}?fecha={ANIO}-02-15",
        "ua",
        mundo.company_a,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 4
    assert body["cargos"] == 3
    assert [f["id"] for f in body["items"]] == [
        f"{ESTADO['sup']}:CUSTODIAR:BIENES",
        f"{ESTADO['dir']}:APROBAR:CONTRATACIONES",
        f"{ESTADO['dir']}:FIRMAR:EXPEDIENTE",
        f"{ESTADO['jef']}:PAGAR:TESORERIA",
    ]
    dir_aprobar = body["items"][1]
    assert dir_aprobar["monto"] == "1500000.00"
    assert dir_aprobar["version"]["version"] == 3
    assert dir_aprobar["version"]["motivo"] == "Amplía el límite"
    dir_firmar = body["items"][2]
    assert dir_firmar["tipo_limite"] == "SIN_LIMITE"
    assert dir_firmar["monto"] is None
    assert dir_firmar["moneda"] is None
    jef = body["items"][3]
    assert jef["version"]["version"] == 2


def test_gm06_corte_15_abril(mundo, gobierno, matriz):
    """GM-06: al 15/4 el cargo SUP ya no entra porque finalizó el 31/3."""
    resp = mundo.get(
        f"{A}/{ANIO}?fecha={ANIO}-04-15",
        "ua",
        mundo.company_a,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 3
    assert all(f["cargo_codigo"] != "SUP" for f in body["items"])


def test_gm07_sin_fecha_y_ejercicio_cerrado(mundo, gobierno, matriz):
    """GM-07: sin fecha se usa hoy para el año en curso y 31/12 para ejercicios anteriores."""
    resp = mundo.get(f"{A}/{ANIO}", "ua", mundo.company_a)
    assert resp.status_code == 200, resp.text
    assert resp.json()["fecha"] == f"{ANIO}-{hoy_de_negocio():%m}-{hoy_de_negocio():%d}"

    resp = mundo.get(f"{A}/{ANIO - 1}", "ua", mundo.company_a)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["fecha"] == f"{ANIO-1}-12-31"
    assert body["estructura"]["estado"] == "CERRADA"
    assert any(f["cargo_codigo"] == "ANT-01" for f in body["items"])


def test_gm08_fechas_invalidas_y_sin_estructura(mundo, gobierno, matriz):
    """GM-08: fecha fuera del ejercicio → 422; estructura inexistente → 404."""
    for fecha in [f"{ANIO+1}-01-01", f"{ANIO-1}-12-31"]:
        resp = mundo.get(
            f"{A}/{ANIO}?fecha={fecha}",
            "ua",
            mundo.company_a,
        )
        assert resp.status_code == 422, resp.text
        body = resp.json()
        assert body["code"] == "GOV_AUTHORITY_DATE_OUT_OF_EXERCISE"
        assert "fecha" in body["field_errors"]

    resp = mundo.get(f"{A}/{ANIO+5}", "ua", mundo.company_a)
    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == "GOV_STRUCTURE_NOT_FOUND"


def test_gm09_filtros(mundo, gobierno, matriz):
    """GM-09: filtros del contrato incluyen subunidades y validan catálogo y estructura."""
    resp = mundo.get(
        f"{A}/{ANIO}?fecha={ANIO}-02-15&accion=PAGAR",
        "ua",
        mundo.company_a,
    )
    assert resp.status_code == 200, resp.text
    assert [f["cargo_codigo"] for f in resp.json()["items"]] == ["JEF-COMP"]

    resp = mundo.get(
        f"{A}/{ANIO}?fecha={ANIO}-02-15&materia=EXPEDIENTE",
        "ua",
        mundo.company_a,
    )
    assert resp.status_code == 200, resp.text
    assert [f["cargo_codigo"] for f in resp.json()["items"]] == ["DIR-ADM"]

    resp = mundo.get(
        f"{A}/{ANIO}?fecha={ANIO}-02-15&cargo_id={ESTADO['dir']}",
        "ua",
        mundo.company_a,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["total"] == 2

    resp = mundo.get(
        f"{A}/{ANIO}?fecha={ANIO}-02-15&unidad_id={ESTADO['dir_adm']}",
        "ua",
        mundo.company_a,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["total"] == 3

    resp = mundo.get(
        f"{A}/{ANIO}?fecha={ANIO}-02-15&unidad_id={ESTADO['otra']}",
        "ua",
        mundo.company_a,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["total"] == 0

    resp = mundo.get(
        f"{A}/{ANIO}?fecha={ANIO}-02-15&unidad_id={ESTADO['b_cargo']}",
        "ua",
        mundo.company_a,
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "GOV_AUTHORITY_INVALID_FILTER"

    resp = mundo.get(
        f"{A}/{ANIO}?fecha={ANIO}-02-15&cargo_id=999999",
        "ua",
        mundo.company_a,
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "GOV_AUTHORITY_INVALID_FILTER"

    resp = mundo.get(
        f"{A}/{ANIO}?fecha={ANIO}-02-15&accion=VOLAR",
        "ua",
        mundo.company_a,
    )
    assert resp.status_code == 422, resp.text


def test_gm10_texto(mundo, gobierno, matriz):
    """GM-10: el filtro texto busca en cargos, unidades y fundamento sin distinguir mayúsculas."""
    resp = mundo.get(
        f"{A}/{ANIO}?fecha={ANIO}-02-15&texto=compras",
        "ua",
        mundo.company_a,
    )
    assert resp.status_code == 200, resp.text
    assert [f["cargo_codigo"] for f in resp.json()["items"]] == ["JEF-COMP"]

    resp = mundo.get(
        f"{A}/{ANIO}?fecha={ANIO}-02-15&texto=ART. 12",
        "ua",
        mundo.company_a,
    )
    assert resp.status_code == 200, resp.text
    assert len(resp.json()["items"]) == 1
    assert resp.json()["items"][0]["accion"] == "APROBAR"

    resp = mundo.get(
        f"{A}/{ANIO}?fecha={ANIO}-02-15&texto=inexistente",
        "ua",
        mundo.company_a,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["total"] == 0


def test_gm11_campos_fila(mundo, gobierno, matriz):
    """GM-11: la fila APROBAR a 15/2 tiene todos los campos del contrato."""
    resp = mundo.get(
        f"{A}/{ANIO}?fecha={ANIO}-02-15&accion=APROBAR&materia=CONTRATACIONES",
        "ua",
        mundo.company_a,
    )
    assert resp.status_code == 200, resp.text
    fila = resp.json()["items"][0]
    assert fila["id"] == f"{ESTADO['dir']}:APROBAR:CONTRATACIONES"
    assert fila["cargo_codigo"] == "DIR-ADM"
    assert fila["cargo_denominacion"] == "Director de Administración"
    assert fila["unidad_codigo"] == "DIR-ADM"
    assert fila["unidad_denominacion"] == "Dirección de Administración"
    assert fila["ruta_unidad"] == "DESP › DIR-ADM"
    assert fila["tipo_limite"] == "MONTO"
    assert fila["moneda"] == "VES"
    assert fila["fundamento"] == "Reglamento interno, art. 12"
    assert fila["vigente_desde"] == f"{ANIO}-01-01"
    assert fila["vigente_hasta"] is None
    assert fila["estado_cargo"] == "VIGENTE"
    assert fila["acto_soporte"] == ["Resolución DA-001"]
    assert fila["origen"] == "CARGO"
    assert fila["version"]["registrada_en"] is not None


def test_gm12_paginacion(mundo, gobierno, matriz):
    """GM-12: paginación válida funciona y valores inválidos devuelven 422."""
    resp = mundo.get(
        f"{A}/{ANIO}?fecha={ANIO}-02-15&por_pagina=10&pagina=1",
        "ua",
        mundo.company_a,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body["items"]) == 4
    assert body["total"] == 4
    assert body["pagina"] == 1
    assert body["por_pagina"] == 10

    resp = mundo.get(
        f"{A}/{ANIO}?fecha={ANIO}-02-15&por_pagina=10&pagina=2",
        "ua",
        mundo.company_a,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["items"] == []
    assert resp.json()["total"] == 4

    for query in ["pagina=0", "por_pagina=9", "por_pagina=201"]:
        resp = mundo.get(
            f"{A}/{ANIO}?fecha={ANIO}-02-15&{query}",
            "ua",
            mundo.company_a,
        )
        assert resp.status_code == 422, resp.text


def test_gm13_detalle(mundo, gobierno, matriz):
    """GM-13: detalle del cargo con versión vigente, acto y versiones ascendentes."""
    resp = mundo.get(
        f"{A}/{ANIO}/cargos/{ESTADO['dir']}",
        "ua",
        mundo.company_a,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    cargo = body["cargo"]
    assert cargo["ruta_unidad"] == "DESP › DIR-ADM"
    assert body["acto_soporte"] == [
        {"documento_id": ESTADO["doc_dir"], "titulo": "Resolución DA-001"}
    ]
    assert [v["version"] for v in body["versiones"]] == [1, 2, 3]
    assert all("estado" in v for v in body["versiones"])
    assert all("competencias" in v for v in body["versiones"])

    resp = mundo.get(
        f"{A}/{ANIO}/cargos/{ESTADO['ant']}",
        "ua",
        mundo.company_a,
    )
    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == "GOV_POSITION_NOT_FOUND"

    resp = mundo.get(
        f"{A}/{ANIO}/cargos/{ESTADO['b_cargo']}",
        "ua",
        mundo.company_a,
    )
    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == "GOV_POSITION_NOT_FOUND"

    resp = mundo.get(
        f"{A}/{ANIO}/cargos/{ESTADO['bor']}",
        "ua",
        mundo.company_a,
    )
    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == "GOV_POSITION_NOT_FOUND"


def test_gm14_csv(mundo, gobierno, matriz):
    """GM-14: exportar CSV con cabecera exacta, datos de APROBAR y evento de auditoría."""
    antes = len(_eventos(mundo, "GOV_AUTHORITY_MATRIX_EXPORTED", mundo.company_a))
    resp = mundo.get(
        f"{A}/{ANIO}/exportar?fecha={ANIO}-02-15&accion=APROBAR",
        "ua",
        mundo.company_a,
    )
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("text/csv")
    assert (
        resp.headers["content-disposition"]
        == f'attachment; filename="autoridad-{ANIO}-{ANIO}-02-15.csv"'
    )
    filas = list(csv_reader(StringIO(resp.text)))
    assert filas[0] == [
        "fecha_corte",
        "codigo_unidad",
        "unidad",
        "ruta_unidad",
        "codigo_cargo",
        "denominacion_cargo",
        "estado_cargo",
        "vigente_desde",
        "vigente_hasta",
        "accion",
        "materia",
        "tipo_limite",
        "monto",
        "moneda",
        "fundamento",
        "acto_soporte",
        "version_cargo",
        "origen",
    ]
    assert len(filas) == 2
    datos = filas[1]
    assert datos[0] == f"{ANIO}-02-15"
    assert datos[4] == "DIR-ADM"
    assert datos[9] == "APROBAR"
    assert datos[12] == "1500000.00"
    assert datos[15] == "Resolución DA-001"
    assert datos[16] == "3"
    assert datos[17] == "CARGO"

    despues = _eventos(mundo, "GOV_AUTHORITY_MATRIX_EXPORTED", mundo.company_a)
    assert len(despues) == antes + 1
    evento = despues[-1]
    after = evento.after
    assert after["filas"] == 1
    assert after["fecha"] == f"{ANIO}-02-15"
    assert after["filtros"]["accion"] == "APROBAR"


def test_gm15_sin_escrituras(mundo, gobierno, matriz):
    """GM-15: la API de autoridad es de solo lectura, escrituras → 405."""
    headers = mundo.como("ua", mundo.company_a)

    for method in ["post", "patch"]:
        call = getattr(mundo.client, method)
        resp = call(
            f"/api/v1{A}/{ANIO}",
            headers=headers,
            json={},
        )
        assert resp.status_code == 405, resp.text

    resp = mundo.client.delete(
        f"/api/v1{A}/{ANIO}",
        headers=headers,
    )
    assert resp.status_code == 405, resp.text


def test_gm16_permisos(mundo, gobierno, matriz, _permiso_autoridad_view):
    """GM-16: el permiso `gobierno_autoridad:view` habilita la consulta y no permite cargos."""
    _crear_usuario_con_permiso(
        mundo,
        "autconsulta",
        "gobierno_autoridad",
        "view",
        mundo.company_a,
    )
    _crear_usuario_con_permiso(
        mundo,
        "cargosolo",
        "gobierno_cargos",
        "view",
        mundo.company_a,
    )

    for ruta in [
        f"{A}/ejercicios",
        f"{A}/{ANIO}/filtros",
        f"{A}/{ANIO}",
        f"{A}/{ANIO}/exportar",
        f"{A}/{ANIO}/cargos/{ESTADO['dir']}",
    ]:
        resp = mundo.get(ruta, "autconsulta", mundo.company_a)
        assert resp.status_code == 200, resp.text

    resp = mundo.get(
        f"/gobierno/estructuras/{ANIO}/cargos",
        "autconsulta",
        mundo.company_a,
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "PERMISSION_DENIED"

    resp = mundo.get(f"{A}/{ANIO}", "cargosolo", mundo.company_a)
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "PERMISSION_DENIED"

    resp = mundo.get(f"{A}/ejercicios", "cargosolo", mundo.company_a)
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "PERMISSION_DENIED"

    resp = mundo.get(f"{A}/{ANIO}/exportar", "cargosolo", mundo.company_a)
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "PERMISSION_DENIED"


def test_gm17_aislamiento(mundo, gobierno, matriz):
    """GM-17: cada empresa solo ve su matriz."""
    resp = mundo.get(f"{A}/{ANIO}", "ub", mundo.company_b)
    assert resp.status_code == 200, resp.text
    assert [f["cargo_codigo"] for f in resp.json()["items"]] == ["B-CARGO"]

    resp = mundo.get(
        f"{A}/{ANIO}",
        "ua",
        mundo.company_b,
    )
    assert resp.status_code != 200

    resp = mundo.get(
        f"{A}/{ANIO}",
        "uc",
        mundo.company_c,
        tenant="T2",
    )
    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == "GOV_STRUCTURE_NOT_FOUND"


def test_gm18_mfa_y_catalogo(mundo, gobierno, matriz):
    """GM-18: MFA classify y catálogo de permisos incluyen `gobierno_autoridad:view`."""
    assert classify({"gobierno_autoridad:view"}) == STANDARD
    assert CATALOGO_DE_PERMISOS["gobierno_autoridad"] == ["view"]

    with mundo.factory() as db:
        rol = db.scalar(
            select(Role).where(Role.code == "FUNCIONAL_COMPLETO")
        )
        assert rol is not None
        permiso = db.scalar(
            select(Permission).where(
                Permission.resource == "gobierno_autoridad",
                Permission.action == "view",
            )
        )
        assert permiso is not None
        existe = db.scalar(
            select(RolePermission.id).where(
                RolePermission.role_id == rol.id,
                RolePermission.permission_id == permiso.id,
            )
        )
        assert existe is not None


def test_gm19_sin_cache(mundo, gobierno, matriz):
    """GM-19: sin caché, la versión vigente a hoy cambia, pero la fecha 15/2 no."""
    if hoy_de_negocio() < date(ANIO, 1, 21):
        pytest.skip("GM-19 solo aplica desde el 21/1 del año en curso")

    with mundo.factory() as db:
        cargo = db.get(GovernmentPosition, ESTADO["dir"])
        ultima = db.execute(
            select(GovernmentPositionVersion)
            .where(GovernmentPositionVersion.position_id == ESTADO["dir"])
            .order_by(GovernmentPositionVersion.version.desc())
        ).scalars().first()

        snapshot = deepcopy(ultima.snapshot)
        for competencia in snapshot.get("competencias", []):
            if competencia.get("accion") == "APROBAR":
                competencia["monto"] = "2000000.00"

        db.add(
            GovernmentPositionVersion(
                position_id=ESTADO["dir"],
                structure_id=ultima.structure_id,
                company_id=ultima.company_id,
                version=ultima.version + 1,
                status="VIGENTE",
                snapshot=snapshot,
                reason="Nuevo límite",
                actor_id=None,
                created_at=datetime.now(UTC),
            )
        )

        competencia = db.execute(
            select(GovernmentPositionCompetency)
            .where(
                GovernmentPositionCompetency.position_id == ESTADO["dir"],
                GovernmentPositionCompetency.action == "APROBAR",
            )
        ).scalar_one()
        competencia.limit_amount = Decimal("2000000.00")

        cargo.version = ultima.version + 1
        db.commit()

    resp = mundo.get(
        f"{A}/{ANIO}?accion=APROBAR",
        "ua",
        mundo.company_a,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    fila_dir_adm = next(
        fila for fila in body["items"] if fila["cargo_codigo"] == "DIR-ADM"
    )
    assert fila_dir_adm["monto"] == "2000000.00"
    assert fila_dir_adm["version"]["version"] == 4

    resp = mundo.get(
        f"{A}/{ANIO}?accion=APROBAR&fecha={ANIO}-02-15",
        "ua",
        mundo.company_a,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    fila_dir_adm = next(
        fila for fila in body["items"] if fila["cargo_codigo"] == "DIR-ADM"
    )
    assert fila_dir_adm["monto"] == "1500000.00"
    assert fila_dir_adm["version"]["version"] == 3


def test_gm20_filtro_ajeno_sin_cargos(mundo, gobierno, matriz):
    """GM-20: filtros ajenos también se validan en estructuras sin cargos."""
    with mundo.factory() as db:
        ente_a = db.scalar(
            select(GovernmentEntity).where(
                GovernmentEntity.company_id == mundo.company_a
            )
        )
        db.add(
            GovernmentStructure(
                company_id=mundo.company_a,
                entity_id=ente_a.id,
                exercise=ANIO + 2,
                status="BORRADOR",
                version=1,
            )
        )
        db.commit()

    resp = mundo.get(f"{A}/{ANIO + 2}?unidad_id={ESTADO['desp']}", "ua", mundo.company_a)
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "GOV_AUTHORITY_INVALID_FILTER"

    resp = mundo.get(f"{A}/{ANIO + 2}", "ua", mundo.company_a)
    assert resp.status_code == 200, resp.text
    assert resp.json()["total"] == 0


def test_gm21_orden_denominacion_y_estado(mundo, gobierno, matriz):
    """GM-21: el orden de ACCIONES es por materia; denominación de la versión en vigor y estado del cargo actual."""
    with mundo.factory() as db:
        ente_a = db.scalar(
            select(GovernmentEntity).where(GovernmentEntity.company_id == mundo.company_a)
        )
    nueva_estructura = _crear_estructura(
        mundo,
        mundo.company_a,
        ente_a.id,
        ANIO + 3,
        "VIGENTE",
        published=True,
    )
    unidad_ord = _unidad(
        mundo,
        company_id=mundo.company_a,
        structure_id=nueva_estructura,
        code="ORD",
        name="Unidad ORD",
        valid_from=date(ANIO + 3, 1, 1),
    )
    pos_ord, competencias = _crear_cargo_y_versiones(
        mundo,
        company_id=mundo.company_a,
        structure_id=nueva_estructura,
        unit_id=unidad_ord,
        code="ORD-01",
        denominacion="Nombre actual",
        status="INACTIVO",
        valid_from=date(ANIO + 3, 1, 1),
        valid_to=date(ANIO + 3, 12, 31),
        versiones=[
            {
                "status": "VIGENTE",
                "created_at": datetime(ANIO, 1, 10, 12, 0, tzinfo=TZ_CARACAS),
                "snapshot": _version_snapshot(
                    codigo="ORD-01",
                    denominacion="Nombre de la versión",
                    unidad_id=str(unidad_ord),
                    unidad_codigo="ORD",
                    estado="VIGENTE",
                    vigente_desde=f"{ANIO + 3}-01-01",
                    vigente_hasta=f"{ANIO + 3}-12-31",
                    competencias=[
                        _competencia(
                            action="FIRMAR",
                            subject="PRESUPUESTO",
                            limit_type="SIN_LIMITE",
                        ),
                        _competencia(
                            action="APROBAR",
                            subject="EXPEDIENTE",
                            limit_type="SIN_LIMITE",
                        ),
                    ],
                ),
            },
            {
                "status": "INACTIVO",
                "reason": "Cargo suprimido",
                "created_at": datetime(ANIO + 3, 7, 1, 12, 0, tzinfo=TZ_CARACAS),
                "snapshot": _version_snapshot(
                    codigo="ORD-01",
                    denominacion="Nombre actual",
                    unidad_id=str(unidad_ord),
                    unidad_codigo="ORD",
                    estado="INACTIVO",
                    vigente_desde=f"{ANIO + 3}-01-01",
                    vigente_hasta=f"{ANIO + 3}-12-31",
                    competencias=[
                        _competencia(
                            action="FIRMAR",
                            subject="PRESUPUESTO",
                            limit_type="SIN_LIMITE",
                        ),
                        _competencia(
                            action="APROBAR",
                            subject="EXPEDIENTE",
                            limit_type="SIN_LIMITE",
                        ),
                    ],
                ),
            },
        ],
    )
    assert pos_ord and competencias

    resp = mundo.get(
        f"{A}/{ANIO + 3}?fecha={ANIO + 3}-06-01",
        "ua",
        mundo.company_a,
    )
    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    assert [f["accion"] for f in items] == ["APROBAR", "FIRMAR"]
    assert all(f["cargo_denominacion"] == "Nombre de la versión" for f in items)
    assert all(f["estado_cargo"] == "INACTIVO" for f in items)
    assert all(f["version"]["version"] == 1 for f in items)
