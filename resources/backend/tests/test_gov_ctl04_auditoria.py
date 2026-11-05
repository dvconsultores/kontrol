"""Suite de backend para CTL-04 (GOV-CTL-005): API read-only de auditoría de Gobierno.

Especifica el contrato del módulo `app.modules.government` antes de que exista la API.
Hoy todas las pruebas fallan con 404 en las rutas nuevas (rojo esperado).
"""
import random
from csv import reader as csv_reader
from datetime import UTC, datetime
from io import StringIO
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError

from app.modules.audit.models import AuditEvent
from app.modules.government.models import (
    GovernmentEntity,
    GovernmentPosition,
    GovernmentStructure,
    GovernmentUnit,
)
from app.modules.identity_access import service as identity_service
from app.modules.identity_access.mfa_policy import STANDARD, classify
from app.modules.identity_access.models import (
    Permission,
    Role,
    RolePermission,
    User,
    UserRole,
    UserScope,
)
from app.modules.licensing import service as licensing_service
from app.modules.licensing.models import LicenseEntitlementSnapshot
from app.modules.setup.api import CATALOGO_DE_PERMISOS
from app.shared.audit_catalog import catalog
from app.shared.clock import hoy_de_negocio
from tests.conftest_multicompany import PASSWORD

pytest_plugins = ("tests.conftest_multicompany",)

ANIO = hoy_de_negocio().year
ANT = ANIO - 1
A = "/gobierno/auditoria"
TZ_CARACAS = ZoneInfo("America/Caracas")


def _fecha_ant(mes, dia, hora=15, minuto=0):
    return datetime(ANT, mes, dia, hora, minuto, tzinfo=UTC)


@pytest.fixture
def gobierno(mundo):
    """Garantiza el entitlement `gobierno` en la snapshot sincronizada."""
    with mundo.factory() as db:
        inst = licensing_service.get_installation(db)
        snapshot = db.scalar(
            select(LicenseEntitlementSnapshot).where(
                LicenseEntitlementSnapshot.installation_id == inst.installation_uuid,
                LicenseEntitlementSnapshot.version == "ctl04-test",
            )
        )
        if snapshot is None:
            snapshot = LicenseEntitlementSnapshot(
                installation_id=inst.installation_uuid,
                modules={"gobierno": True},
                version="ctl04-test",
                taken_at=datetime.now(UTC),
            )
            db.add(snapshot)
        else:
            snapshot.modules = {"gobierno": True}
        db.commit()


def _evento(
    db,
    *,
    company_id,
    user_id,
    action,
    entity_type,
    entity_id,
    event_time,
    request_id,
    reason,
    after=None,
    evidence=None,
    tenant_id=None,
):
    evento = AuditEvent(
        tenant_id=tenant_id,
        company_id=company_id,
        user_id=user_id,
        session_id=uuid4(),
        request_id=request_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before=None,
        after=after,
        source="API",
        reason=reason,
        evidence=evidence,
        ip="127.0.0.1",
        event_time=event_time,
    )
    db.add(evento)
    return evento


@pytest.fixture(scope="module")
def poblacion(mundo):
    """Crea con modelos los datos de Gobierno y los eventos de auditoría."""
    with mundo.factory() as db:
        ua = db.scalar(
            select(User).where(User.username == "ua", User.tenant_id == mundo.t1)
        )
        ub = db.scalar(
            select(User).where(User.username == "ub", User.tenant_id == mundo.t1)
        )
        uc = db.scalar(
            select(User).where(User.username == "uc", User.tenant_id == mundo.t2)
        )

        tenant_a = mundo.t1
        tenant_b = mundo.t2
        company_a = mundo.company_a
        company_b = mundo.company_b
        company_c = mundo.company_c

        # Objetos de Gobierno reales en company_a.
        ente = GovernmentEntity(
            company_id=company_a,
            denominacion="Ente activo CTL-04",
            status="ACTIVO",
            version=1,
            activated_at=datetime.now(UTC),
        )
        db.add(ente)
        db.flush()

        estructura = GovernmentStructure(
            company_id=company_a,
            entity_id=ente.id,
            exercise=ANT,
            status="VIGENTE",
            version=1,
            published_at=datetime(ANT, 1, 1, 12, 0, tzinfo=TZ_CARACAS),
        )
        db.add(estructura)
        db.flush()

        unidad = GovernmentUnit(
            company_id=company_a,
            structure_id=estructura.id,
            parent_id=None,
            code="UNIDAD",
            name="Unidad CTL-04",
            unit_type="UNIDAD_ADMINISTRATIVA",
            status="ACTIVA",
            valid_from=datetime(ANT, 1, 1, tzinfo=TZ_CARACAS).date(),
            version=1,
        )
        db.add(unidad)
        db.flush()

        cargo = GovernmentPosition(
            company_id=company_a,
            structure_id=estructura.id,
            unit_id=unidad.id,
            code="AUD-01",
            name="Cargo auditoría",
            status="VIGENTE",
            valid_from=datetime(ANT, 1, 1, tzinfo=TZ_CARACAS).date(),
            activated_at=datetime.now(UTC),
            version=1,
        )
        db.add(cargo)
        db.flush()
        db.commit()

        eventos = [
            _evento(
                db,
                company_id=company_a,
                user_id=ua.id,
                tenant_id=tenant_a,
                action="GOV_ENTITY_ACTIVATED",
                entity_type="GovernmentEntity",
                entity_id=ente.id,
                event_time=_fecha_ant(1, 10),
                request_id="req-01",
                reason="Motivo 1",
            ),
            _evento(
                db,
                company_id=company_a,
                user_id=ua.id,
                tenant_id=tenant_a,
                action="GOV_STRUCTURE_PUBLISHED",
                entity_type="GovernmentStructure",
                entity_id=estructura.id,
                event_time=_fecha_ant(1, 12),
                request_id="req-02",
                reason="Motivo 2",
            ),
        ]
        for n in range(3, 9):
            entity_id = cargo.id if n == 3 else str(uuid4())
            eventos.append(
                _evento(
                    db,
                    company_id=company_a,
                    user_id=ua.id,
                    tenant_id=tenant_a,
                    action="GOV_POSITION_CREATED",
                    entity_type="GovernmentPosition",
                    entity_id=entity_id,
                    event_time=_fecha_ant(2, n),
                    request_id=f"req-{n:02d}",
                    reason=f"Motivo {n}",
                    after={
                        "codigo": f"AUD-{n:02d}",
                        "estado": "BORRADOR",
                        "password": "secreto",
                    },
                )
            )
        eventos.extend(
            [
                _evento(
                    db,
                    company_id=company_a,
                    user_id=ua.id,
                    tenant_id=tenant_a,
                    action="GOV_ACT_CREATED",
                    entity_type="GovernmentAct",
                    entity_id=str(uuid4()),
                    event_time=_fecha_ant(3, 1),
                    request_id="req-09",
                    reason="Motivo 9",
                ),
                _evento(
                    db,
                    company_id=company_a,
                    user_id=ua.id,
                    tenant_id=tenant_a,
                    action="GOV_NOTIFICATION_DELIVERED",
                    entity_type="GovernmentNotification",
                    entity_id=str(uuid4()),
                    event_time=_fecha_ant(3, 2),
                    request_id="req-10",
                    reason="Motivo 10",
                    after={
                        "documento_id": "uuidA",
                        "documento_oficio_id": "uuidB",
                        "fecha": f"{ANT}-03-02",
                    },
                ),
                _evento(
                    db,
                    company_id=company_a,
                    user_id=ua.id,
                    tenant_id=tenant_a,
                    action="GOV_POSITION_CREATED",
                    entity_type="GovernmentPosition",
                    entity_id=str(uuid4()),
                    event_time=datetime(ANT, 4, 1, 3, 30, tzinfo=UTC),
                    request_id="req-11",
                    reason="Motivo 11",
                ),
                _evento(
                    db,
                    company_id=company_a,
                    user_id=ua.id,
                    tenant_id=tenant_a,
                    action="GOV_ACT_CREATED",
                    entity_type="GovernmentAct",
                    entity_id=str(uuid4()),
                    event_time=_fecha_ant(4, 15),
                    request_id="req-12",
                    reason="Revisión ESPECIAL",
                ),
                # Evento privado: no debe aparecer.
                _evento(
                    db,
                    company_id=company_a,
                    user_id=ua.id,
                    tenant_id=tenant_a,
                    action="ACTIVATE",
                    entity_type="warehouse",
                    entity_id=str(uuid4()),
                    event_time=_fecha_ant(4, 16),
                    request_id="req-privado",
                    reason="Motivo privado",
                ),
                # Otra empresa.
                _evento(
                    db,
                    company_id=company_b,
                    user_id=ub.id,
                    tenant_id=tenant_a,
                    action="GOV_ACT_CREATED",
                    entity_type="GovernmentAct",
                    entity_id=str(uuid4()),
                    event_time=_fecha_ant(4, 17),
                    request_id="req-b",
                    reason="Motivo b",
                ),
                # Otro tenant.
                _evento(
                    db,
                    company_id=company_c,
                    user_id=uc.id,
                    tenant_id=tenant_b,
                    action="GOV_ACT_CREATED",
                    entity_type="GovernmentAct",
                    entity_id=str(uuid4()),
                    event_time=_fecha_ant(4, 18),
                    request_id="req-c",
                    reason="Motivo c",
                ),
                # Sin empresa.
                _evento(
                    db,
                    company_id=None,
                    user_id=ua.id,
                    tenant_id=tenant_a,
                    action="GOV_ACT_CREATED",
                    entity_type="GovernmentAct",
                    entity_id=str(uuid4()),
                    event_time=_fecha_ant(4, 19),
                    request_id="req-null",
                    reason="Motivo null",
                ),
            ]
        )

        for evento in eventos:
            db.add(evento)
        db.commit()

        return {
            "ente_id": ente.id,
            "estructura_id": estructura.id,
            "unidad_id": unidad.id,
            "cargo_id": cargo.id,
            "eventos": [e.id for e in eventos],
            "eventos_gobierno": [
                e.id for e in eventos if e.company_id == company_a and e.action != "ACTIVATE"
            ],
        }


@pytest.fixture
def permiso_auditoria(mundo):
    """Garantiza permisos de Gobierno y usuarios para las pruebas."""
    with mundo.factory() as db:
        permisos = {}
        for action in ("view", "sample"):
            permiso = db.scalar(
                select(Permission).where(
                    Permission.resource == "gobierno_auditoria",
                    Permission.action == action,
                )
            )
            if permiso is None:
                permiso = Permission(resource="gobierno_auditoria", action=action)
                db.add(permiso)
                db.flush()
            permisos[action] = permiso
        db.commit()
        return permisos


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


class TestGovCtl04Auditoria:
    def test_GX01_modulo_apagado_403(self, mundo, gobierno, poblacion):
        """GX-01: módulo apagado → 403 MODULE_NOT_ENTITLED."""
        with mundo.factory() as db:
            inst = licensing_service.get_installation(db)
            snapshot = db.scalar(
                select(LicenseEntitlementSnapshot).where(
                    LicenseEntitlementSnapshot.installation_id == inst.installation_uuid,
                    LicenseEntitlementSnapshot.version == "ctl04-test",
                )
            )
            original = snapshot.modules
            snapshot.modules = {}
            db.commit()

        try:
            response = mundo.get(f"{A}/filtros", "ua", mundo.company_a)
            assert response.status_code == 403, response.text
            assert response.json()["code"] == "MODULE_NOT_ENTITLED"
        finally:
            with mundo.factory() as db:
                snapshot = db.scalar(
                    select(LicenseEntitlementSnapshot).where(
                        LicenseEntitlementSnapshot.installation_id == inst.installation_uuid,
                        LicenseEntitlementSnapshot.version == "ctl04-test",
                    )
                )
                snapshot.modules = original
                db.commit()

    def test_GX02_filtros(self, mundo, gobierno, poblacion, permiso_auditoria):
        """GX-02: filtros devuelve los 7 procesos y acciones solo de Gobierno."""
        response = mundo.get(f"{A}/filtros", "ua", mundo.company_a, tenant="T1")
        assert response.status_code == 200
        data = response.json()
        assert [p["codigo"] for p in data["procesos"]] == [
            "ORG-01",
            "ORG-02",
            "ORG-03",
            "ORG-07",
            "DOC-02",
            "DOC-04",
            "CTL-04",
            "CTL-06",
            "DOC-08",
            "CTL-01",
            "TRE-01",
            "TRE-02",
        ]
        acciones = {a["codigo"] for a in data["acciones"]}
        assert "GOV_POSITION_CREATED" in acciones
        assert "ACTIVATE" not in acciones
        assert all(
            catalog()[(a["codigo"], a["entidad"])].owner_module == "government"
            for a in data["acciones"]
        )

    def test_GX03_poblacion_company_a(self, mundo, gobierno, poblacion, permiso_auditoria):
        """GX-03: población de company_a: total 12, sin privado/otra empresa/sin empresa/otro tenant; orden desc."""
        response = mundo.get(
            f"{A}/eventos?por_pagina=200", "ua", mundo.company_a, tenant="T1"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 12
        assert len(data["items"]) == 12
        assert data["items"][0]["motivo"] == "Revisión ESPECIAL"
        fechas = [item["fecha"] for item in data["items"]]
        assert fechas == sorted(fechas, reverse=True)

    def test_GX04_filtros_eventos(self, mundo, gobierno, poblacion, permiso_auditoria):
        """GX-04: filtros de eventos y validaciones."""
        # proceso ORG-03
        response = mundo.get(
            f"{A}/eventos?proceso=ORG-03", "ua", mundo.company_a, tenant="T1"
        )
        assert response.status_code == 200
        assert response.json()["total"] == 7
        # acción
        response = mundo.get(
            f"{A}/eventos?accion=GOV_ACT_CREATED", "ua", mundo.company_a, tenant="T1"
        )
        assert response.status_code == 200
        assert response.json()["total"] == 2
        # usuario
        response = mundo.get(
            f"{A}/eventos?usuario=ua", "ua", mundo.company_a, tenant="T1"
        )
        assert response.status_code == 200
        assert response.json()["total"] == 12
        response = mundo.get(
            f"{A}/eventos?usuario=nadie", "ua", mundo.company_a, tenant="T1"
        )
        assert response.status_code == 200
        assert response.json()["total"] == 0
        # texto
        response = mundo.get(
            f"{A}/eventos?texto=especial", "ua", mundo.company_a, tenant="T1"
        )
        assert response.status_code == 200
        assert response.json()["total"] == 1
        assert response.json()["items"][0]["motivo"] == "Revisión ESPECIAL"
        # día civil de Caracas
        response = mundo.get(
            f"{A}/eventos?desde={ANT}-03-31&hasta={ANT}-03-31",
            "ua",
            mundo.company_a,
            tenant="T1",
        )
        assert response.status_code == 200
        assert response.json()["total"] == 1
        assert response.json()["items"][0]["request_id"] == "req-11"
        # desde > hasta
        response = mundo.get(
            f"{A}/eventos?desde={ANT}-04-02&hasta={ANT}-04-01",
            "ua",
            mundo.company_a,
            tenant="T1",
        )
        assert response.status_code == 422
        assert response.json()["code"] == "INVALID_DATE_RANGE"
        # proceso inválido
        response = mundo.get(
            f"{A}/eventos?proceso=XYZ", "ua", mundo.company_a, tenant="T1"
        )
        assert response.status_code == 422
        # acción privada
        response = mundo.get(
            f"{A}/eventos?accion=ACTIVATE", "ua", mundo.company_a, tenant="T1"
        )
        assert response.status_code == 422
        # paginación
        response = mundo.get(
            f"{A}/eventos?por_pagina=10&pagina=2", "ua", mundo.company_a, tenant="T1"
        )
        assert response.status_code == 200
        assert response.json()["total"] == 12
        assert len(response.json()["items"]) == 2

    def test_GX05_detalle_evento(self, mundo, gobierno, poblacion, permiso_auditoria):
        """GX-05: detalle de eventos con safe_details, documentos y objeto."""
        with mundo.factory() as db:
            e03 = db.scalar(
                select(AuditEvent).where(AuditEvent.request_id == "req-03")
            )
            e04 = db.scalar(
                select(AuditEvent).where(AuditEvent.request_id == "req-04")
            )
            e10 = db.scalar(
                select(AuditEvent).where(AuditEvent.request_id == "req-10")
            )
            e01 = db.scalar(
                select(AuditEvent).where(AuditEvent.request_id == "req-01")
            )

        response = mundo.get(f"{A}/eventos/{e03.id}", "ua", mundo.company_a, tenant="T1")
        assert response.status_code == 200
        data = response.json()
        assert "password" not in data["detalle"]["after"]
        assert data["detalle"]["after"]["codigo"] == "AUD-03"
        assert data["objeto"]["tipo"] == "GovernmentPosition"
        assert data["objeto"]["ruta"] == f"/gobierno/cargos/{ANT}/{poblacion['cargo_id']}"
        assert data["objeto"]["capacidad"] == "gobierno_cargos:view"

        response = mundo.get(f"{A}/eventos/{e04.id}", "ua", mundo.company_a, tenant="T1")
        assert response.status_code == 200
        assert response.json()["objeto"] is None

        response = mundo.get(f"{A}/eventos/{e10.id}", "ua", mundo.company_a, tenant="T1")
        assert response.status_code == 200
        assert sorted(response.json()["documentos"]) == ["uuidA", "uuidB"]

        response = mundo.get(f"{A}/eventos/{e01.id}", "ua", mundo.company_a, tenant="T1")
        assert response.status_code == 200
        assert response.json()["objeto"]["ruta"] == "/gobierno/ente"

    def test_GX06_evento_no_encontrado(self, mundo, gobierno, poblacion, permiso_auditoria):
        """GX-06: 404 GOV_AUDIT_EVENT_NOT_FOUND para eventos fuera del alcance."""
        with mundo.factory() as db:
            ids = {
                "privado": db.scalar(
                    select(AuditEvent.id).where(AuditEvent.request_id == "req-privado")
                ),
                "company_b": db.scalar(
                    select(AuditEvent.id).where(AuditEvent.request_id == "req-b")
                ),
                "company_c": db.scalar(
                    select(AuditEvent.id).where(AuditEvent.request_id == "req-c")
                ),
                "sin_empresa": db.scalar(
                    select(AuditEvent.id).where(AuditEvent.request_id == "req-null")
                ),
            }
        for key in ("privado", "company_b", "company_c", "sin_empresa"):
            response = mundo.get(
                f"{A}/eventos/{ids[key]}", "ua", mundo.company_a, tenant="T1"
            )
            assert response.status_code == 404
            assert response.json()["code"] == "GOV_AUDIT_EVENT_NOT_FOUND"

        response = mundo.get(
            f"{A}/eventos/{uuid4()}", "ua", mundo.company_a, tenant="T1"
        )
        assert response.status_code == 404
        assert response.json()["code"] == "GOV_AUDIT_EVENT_NOT_FOUND"

    def test_GX07_muestra_todas(self, mundo, gobierno, poblacion, permiso_auditoria):
        """GX-07: TODAS con filtros {proceso: ORG-03}."""
        body = {
            "titulo": "Muestra TODAS ORG-03",
            "criterio": "Criterio de la muestra TODAS",
            "justificacion": "Justificación de la muestra TODAS",
            "metodo": "TODAS",
            "filtros": {"proceso": "ORG-03"},
            "semilla": None,
            "tamano": None,
            "eventos": None,
        }
        response = mundo.post(f"{A}/muestras", "ua", mundo.company_a, body, tenant="T1")
        assert response.status_code == 201
        data = response.json()
        assert data["tamano"] == 7
        assert data["poblacion"] == 7
        assert data["semilla"] is None
        assert data["registrada_por"] == "ua"
        assert data["metodo"] == "TODAS"
        assert data["codigo"].startswith(f"MU-{ANIO}-")
        # eventos en orden ASC según la población ordenada por event_time ASC, id ASC
        with mundo.factory() as db:
            eventos = list(
                db.scalars(
                    select(AuditEvent)
                    .where(
                        AuditEvent.action == "GOV_POSITION_CREATED",
                        AuditEvent.company_id == mundo.company_a,
                    )
                    .order_by(AuditEvent.event_time.asc(), AuditEvent.id.asc())
                )
            )
        assert [e["request_id"] for e in data["eventos"]] == [
            e.request_id for e in eventos
        ]
        # evento de auditoría registrado
        with mundo.factory() as db:
            count = db.scalar(
                select(func.count())
                .select_from(AuditEvent)
                .where(
                    AuditEvent.action == "GOV_AUDIT_SAMPLE_CREATED",
                    AuditEvent.company_id == mundo.company_a,
                )
            )
        assert count == 1

    def test_GX08_muestra_especifica(self, mundo, gobierno, poblacion, permiso_auditoria):
        """GX-08: ESPECIFICA con ids fuera de población y vacío."""
        with mundo.factory() as db:
            e01 = db.scalar(
                select(AuditEvent).where(AuditEvent.request_id == "req-01")
            )
            e09 = db.scalar(
                select(AuditEvent).where(AuditEvent.request_id == "req-09")
            )
            eb = db.scalar(select(AuditEvent).where(AuditEvent.request_id == "req-b"))

        body = {
            "titulo": "Muestra específica",
            "criterio": "Criterio específico",
            "justificacion": "Justificación específica",
            "metodo": "ESPECIFICA",
            "filtros": {},
            "eventos": [str(e09.id), str(e01.id)],
        }
        response = mundo.post(f"{A}/muestras", "ua", mundo.company_a, body, tenant="T1")
        assert response.status_code == 201
        assert [e["request_id"] for e in response.json()["eventos"]] == [
            "req-01",
            "req-09",
        ]

        body["eventos"] = [str(e01.id), str(eb.id)]
        response = mundo.post(f"{A}/muestras", "ua", mundo.company_a, body, tenant="T1")
        assert response.status_code == 422
        assert response.json()["code"] == "GOV_AUDIT_EVENT_OUTSIDE_POPULATION"

        body["eventos"] = []
        response = mundo.post(f"{A}/muestras", "ua", mundo.company_a, body, tenant="T1")
        assert response.status_code == 422

    def test_GX09_muestra_aleatoria(self, mundo, gobierno, poblacion, permiso_auditoria):
        """GX-09: ALEATORIA determinística y validaciones."""
        with mundo.factory() as db:
            eventos = list(
                db.scalars(
                    select(AuditEvent)
                    .where(
                        AuditEvent.company_id == mundo.company_a,
                        AuditEvent.request_id.in_([f"req-{n:02d}" for n in range(1, 13)]),
                    )
                    .order_by(AuditEvent.event_time.asc(), AuditEvent.id.asc())
                )
            )
        assert len(eventos) == 12
        seleccion = sorted(random.Random(12345).sample(range(12), 3))
        ids_esperados = [eventos[i].id for i in seleccion]

        body = {
            "titulo": "Muestra aleatoria",
            "criterio": "Criterio aleatorio",
            "justificacion": "Justificación aleatoria",
            "metodo": "ALEATORIA",
            "filtros": {"desde": f"{ANT}-01-01", "hasta": f"{ANT}-12-31"},
            "semilla": 12345,
            "tamano": 3,
        }
        response = mundo.post(f"{A}/muestras", "ua", mundo.company_a, body, tenant="T1")
        assert response.status_code == 201
        assert response.json()["semilla"] == 12345
        assert response.json()["poblacion"] == 12
        assert [e["id"] for e in response.json()["eventos"]] == ids_esperados

        # Repetir con la misma semilla y filtros → mismos ids
        response2 = mundo.post(f"{A}/muestras", "ua", mundo.company_a, body, tenant="T1")
        assert response2.status_code == 201
        assert [e["id"] for e in response2.json()["eventos"]] == ids_esperados

        # Sin semilla → el sistema genera una entera 1..999999999
        body_sin = dict(body)
        body_sin.pop("semilla")
        response = mundo.post(
            f"{A}/muestras", "ua", mundo.company_a, body_sin, tenant="T1"
        )
        assert response.status_code == 201
        semilla = response.json()["semilla"]
        assert isinstance(semilla, int)
        assert 1 <= semilla <= 999999999

        # Tamaño 0 y 13
        for tamano in (0, 13):
            body_bad = dict(body)
            body_bad["tamano"] = tamano
            response = mundo.post(
                f"{A}/muestras", "ua", mundo.company_a, body_bad, tenant="T1"
            )
            assert response.status_code == 422
            assert response.json()["code"] == "GOV_AUDIT_INVALID_SAMPLE_SIZE"

        # Semilla 0
        body_bad = dict(body)
        body_bad["semilla"] = 0
        response = mundo.post(
            f"{A}/muestras", "ua", mundo.company_a, body_bad, tenant="T1"
        )
        assert response.status_code == 422

    def test_GX10_validaciones_muestra(self, mundo, gobierno, poblacion, permiso_auditoria):
        """GX-10: validaciones de creación de muestra."""
        base = {
            "titulo": "Título válido",
            "criterio": "Criterio válido",
            "justificacion": "Justificación válida",
            "metodo": "TODAS",
            "filtros": {},
        }
        # criterio corto
        body = dict(base)
        body["criterio"] = "12345"
        response = mundo.post(f"{A}/muestras", "ua", mundo.company_a, body, tenant="T1")
        assert response.status_code == 422

        # sin justificación
        body = dict(base)
        body.pop("justificacion")
        response = mundo.post(f"{A}/muestras", "ua", mundo.company_a, body, tenant="T1")
        assert response.status_code == 422

        # título corto
        body = dict(base)
        body["titulo"] = "ab"
        response = mundo.post(f"{A}/muestras", "ua", mundo.company_a, body, tenant="T1")
        assert response.status_code == 422

        # población vacía
        body = dict(base)
        body["filtros"] = {"usuario": "nadie"}
        response = mundo.post(f"{A}/muestras", "ua", mundo.company_a, body, tenant="T1")
        assert response.status_code == 422
        assert response.json()["code"] == "GOV_AUDIT_EMPTY_POPULATION"

        # método inválido
        body = dict(base)
        body["metodo"] = "OTRO"
        response = mundo.post(f"{A}/muestras", "ua", mundo.company_a, body, tenant="T1")
        assert response.status_code == 422

    def test_GX11_listar_y_detalle_muestras(self, mundo, gobierno, poblacion, permiso_auditoria):
        """GX-11: listar y detalle de muestras con aislamiento por empresa."""
        # Crea una muestra con ub
        body_ub = {
            "titulo": "Muestra de company_b",
            "criterio": "Criterio de company_b",
            "justificacion": "Justificación de company_b",
            "metodo": "TODAS",
            "filtros": {},
        }
        response = mundo.post(
            f"{A}/muestras", "ub", mundo.company_b, body_ub, tenant="T1"
        )
        assert response.status_code == 201
        muestra_b_id = response.json()["id"]

        # Lista con ua
        response = mundo.get(f"{A}/muestras", "ua", mundo.company_a, tenant="T1")
        assert response.status_code == 200
        items = response.json()["items"]
        assert items, "debe existir al menos una muestra de ua"
        assert "eventos" not in items[0]
        # La más reciente primero (al menos la última creada por ua está delante de la de company_b)
        ids_ua = [item["id"] for item in items]
        assert muestra_b_id not in ids_ua

        # Detalle de la muestra de GX-07 (la primera creada por ua)
        primer_id = ids_ua[0]
        response = mundo.get(
            f"{A}/muestras/{primer_id}", "ua", mundo.company_a, tenant="T1"
        )
        assert response.status_code == 200
        assert "eventos" in response.json()

        # Muestra de company_b pedida por ua
        response = mundo.get(
            f"{A}/muestras/{muestra_b_id}", "ua", mundo.company_a, tenant="T1"
        )
        assert response.status_code == 404
        assert response.json()["code"] == "GOV_AUDIT_SAMPLE_NOT_FOUND"

    def test_GX12_csv_muestra(self, mundo, gobierno, poblacion, permiso_auditoria):
        """GX-12: exportación CSV con metadatos y tabla."""
        response = mundo.get(f"{A}/muestras", "ua", mundo.company_a, tenant="T1")
        primer_id = next(
            m["id"]
            for m in response.json()["items"]
            if m["titulo"] == "Muestra TODAS ORG-03"
        )
        response = mundo.get(
            f"{A}/muestras/{primer_id}/exportar", "ua", mundo.company_a, tenant="T1"
        )
        assert response.status_code == 200
        content_disposition = response.headers.get("content-disposition", "")
        # El filename debe ser muestra-<codigo>.csv; obtener el codigo desde la respuesta no es posible,
        # así que validamos que exista content-disposition con .csv.
        assert ".csv" in content_disposition
        csv_texto = response.text
        assert "# metodo: TODAS" in csv_texto
        assert "# criterio:" in csv_texto
        cabecera = "orden,fecha,proceso,accion,accion_etiqueta,entidad,entidad_id,usuario,motivo,request_id,detalle"
        assert cabecera in csv_texto
        filas = list(csv_reader(StringIO(csv_texto)))
        for fila in filas:
            if fila and fila[0] == "orden":
                cabecera_idx = filas.index(fila)
                break
        else:
            raise AssertionError("No se encontró la cabecera de la tabla CSV")
        # 7 filas de datos para la muestra TODAS de GX-07
        filas_datos = [f for f in filas[cabecera_idx + 1 :] if f and f[0] != "#"]
        assert len(filas_datos) == 7

        with mundo.factory() as db:
            count = db.scalar(
                select(func.count())
                .select_from(AuditEvent)
                .where(
                    AuditEvent.action == "GOV_AUDIT_SAMPLE_EXPORTED",
                    AuditEvent.company_id == mundo.company_a,
                )
            )
        assert count == 1

    def test_GX13_inmutabilidad(self, mundo, gobierno, poblacion, permiso_auditoria):
        """GX-13: PATCH/PUT/DELETE → 405 y UPDATE/DELETE directos lanzan excepción."""
        response = mundo.get(f"{A}/muestras", "ua", mundo.company_a, tenant="T1")
        muestra_id = response.json()["items"][0]["id"]

        for method in ("PATCH", "PUT", "DELETE"):
            response = mundo.client.request(
                method,
                f"/api/v1{A}/muestras/{muestra_id}",
                headers=mundo.como("ua", mundo.company_a),
            )
            assert response.status_code == 405

        with pytest.raises(DBAPIError):
            with mundo.factory() as db:
                db.execute(text("UPDATE gov_audit_samples SET titulo='x'"))
                db.commit()
            db.rollback()

        with pytest.raises(DBAPIError):
            with mundo.factory() as db:
                db.execute(text("DELETE FROM gov_audit_sample_items"))
                db.commit()

        # Nada cambia
        with mundo.factory() as db:
            count = db.scalar(
                select(func.count()).select_from(text("gov_audit_samples"))
            )
        assert count >= 1

    def test_GX14_solo_lectura(self, mundo, gobierno, poblacion, permiso_auditoria):
        """GX-14: las rutas de lectura no modifican audit_events ni gov_positions."""
        with mundo.factory() as db:
            audits_before = db.scalar(
                select(func.count())
                .select_from(AuditEvent)
                .where(
                    AuditEvent.company_id == mundo.company_a,
                    AuditEvent.action.like("GOV\\_%", escape="\\"),
                )
            )
            positions_before = db.scalar(
                select(func.count()).select_from(GovernmentPosition)
            )

        mundo.get(f"{A}/filtros", "ua", mundo.company_a, tenant="T1")
        mundo.get(f"{A}/eventos", "ua", mundo.company_a, tenant="T1")
        with mundo.factory() as db:
            evento = db.scalar(
                select(AuditEvent).where(AuditEvent.request_id == "req-01")
            )
        if evento:
            response = mundo.get(
                f"{A}/eventos/{evento.id}", "ua", mundo.company_a, tenant="T1"
            )
            assert response.status_code == 200

        with mundo.factory() as db:
            audits_after = db.scalar(
                select(func.count())
                .select_from(AuditEvent)
                .where(
                    AuditEvent.company_id == mundo.company_a,
                    AuditEvent.action.like("GOV\\_%", escape="\\"),
                )
            )
            positions_after = db.scalar(
                select(func.count()).select_from(GovernmentPosition)
            )
        assert audits_before == audits_after
        assert positions_before == positions_after

    def test_GX15_permisos(self, mundo, gobierno, poblacion, permiso_auditoria):
        """GX-15: permisos de lectura y alcance de auditoría."""
        _crear_usuario_con_permiso(
            mundo,
            "audsolo",
            "gobierno_auditoria",
            "view",
            mundo.company_a,
        )

        response = mundo.get(f"{A}/eventos", "audsolo", mundo.company_a, tenant="T1")
        assert response.status_code == 200

        response = mundo.post(
            f"{A}/muestras",
            "audsolo",
            mundo.company_a,
            {
                "titulo": "Sin permiso",
                "criterio": "Criterio sin permiso",
                "justificacion": "Justificación sin permiso",
                "metodo": "TODAS",
                "filtros": {},
            },
            tenant="T1",
        )
        assert response.status_code == 403

        _crear_usuario_con_permiso(mundo, "bitacora", "audit", "view", mundo.company_a)

        response = mundo.get(f"{A}/eventos", "bitacora", mundo.company_a, tenant="T1")
        assert response.status_code == 403

        # audsolo no accede a /audit/events
        response = mundo.get("/audit/events", "audsolo", mundo.company_a, tenant="T1")
        assert response.status_code == 403

        # Rol protegido ADMIN sin empresa no accede
        with mundo.factory() as db:
            admin = identity_service.create_user(
                db,
                tenant_id=mundo.t1,
                username="adminrol",
                email="adminrol@example.test",
                password=PASSWORD,
                created_by=None,
            )
            rol_admin = db.scalar(
                select(Role).where(Role.code == "ADMIN", Role.company_id.is_(None))
            )
            db.add(
                UserRole(
                    user_id=admin.id,
                    role_id=rol_admin.id,
                    company_id=None,
                )
            )
            db.add(UserScope(user_id=admin.id, company_id=mundo.company_a))
            db.commit()

        response = mundo.get(f"{A}/eventos", "adminrol", None, tenant="T1")
        assert response.status_code == 403

    def test_GX16_mfa_y_catalogo(self):
        """GX-16: MFA STANDARD y catálogo de permisos."""
        assert classify({"gobierno_auditoria:view"}) == STANDARD
        assert classify({"gobierno_auditoria:sample"}) == STANDARD
        assert CATALOGO_DE_PERMISOS["gobierno_auditoria"] == ["view", "sample"]

    def test_GX17_csv_muestra_aleatoria(self, mundo, gobierno, poblacion, permiso_auditoria):
        """GX-17: el CSV de una muestra ALEATORIA declara su método y su semilla."""
        response = mundo.get(f"{A}/muestras", "ua", mundo.company_a, tenant="T1")
        muestra_id = next(
            m["id"]
            for m in response.json()["items"]
            if m["metodo"] == "ALEATORIA" and m["semilla"] == 12345
        )
        response = mundo.get(
            f"{A}/muestras/{muestra_id}/exportar", "ua", mundo.company_a, tenant="T1"
        )
        assert response.status_code == 200
        csv_texto = response.text
        assert "# metodo: ALEATORIA" in csv_texto
        assert "# semilla: 12345" in csv_texto
        assert "# metodo: TODAS" not in csv_texto
