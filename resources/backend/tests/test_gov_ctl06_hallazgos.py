"""Suite de backend para CTL-06 (GOV-CTL-008): hallazgos y acciones correctivas.

Especifica el contrato del módulo `app.modules.government` antes de que exista la API.
Hoy todas las pruebas fallan con 404 en las rutas nuevas o ImportError de modelos (rojo esperado).
"""
import re
from datetime import UTC, datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import func, select

from app.modules.audit.models import AuditEvent
from app.modules.documents.models import (
    Document,
    DocumentLink,
    DocumentType,
    DocumentVersion,
    StoredFile,
)
from app.modules.government.models import (
    GovernmentAuditSample,
    GovernmentAuditSampleItem,
    GovernmentEntity,
    GovernmentPosition,
    GovernmentStructure,
    GovernmentUnit,
)
from app.modules.identity_access import service as identity_service
from app.modules.identity_access.mfa_policy import SENSITIVE, STANDARD, classify
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
from app.shared.clock import hoy_de_negocio
from tests.conftest_multicompany import PASSWORD

pytest_plugins = ("tests.conftest_multicompany",)

ANIO = hoy_de_negocio().year
H = "/gobierno/hallazgos"
TZ_CARACAS = ZoneInfo("America/Caracas")


@pytest.fixture
def gobierno(mundo):
    """Garantiza el entitlement `gobierno` en la snapshot sincronizada."""
    with mundo.factory() as db:
        inst = licensing_service.get_installation(db)
        snapshot = db.scalar(
            select(LicenseEntitlementSnapshot).where(
                LicenseEntitlementSnapshot.installation_id == inst.installation_uuid,
                LicenseEntitlementSnapshot.version == "ctl06-test",
            )
        )
        if snapshot is None:
            snapshot = LicenseEntitlementSnapshot(
                installation_id=inst.installation_uuid,
                modules={"gobierno": True},
                version="ctl06-test",
                taken_at=datetime.now(UTC),
            )
            db.add(snapshot)
        else:
            snapshot.modules = {"gobierno": True}
        db.commit()


@pytest.fixture(scope="module")
def siembra(mundo):
    """Crea con modelos los datos de Gobierno, cargos y muestras para CTL-06."""
    with mundo.factory() as db:
        ua = db.scalar(
            select(User).where(User.username == "ua", User.tenant_id == mundo.t1)
        )
        ub = db.scalar(
            select(User).where(User.username == "ub", User.tenant_id == mundo.t1)
        )

        tenant_a = mundo.t1
        company_a = mundo.company_a
        company_b = mundo.company_b

        ente_a = GovernmentEntity(
            company_id=company_a,
            denominacion="Ente activo CTL-06",
            status="ACTIVO",
            version=1,
            activated_at=datetime.now(UTC),
        )
        db.add(ente_a)
        db.flush()

        estructura_a = GovernmentStructure(
            company_id=company_a,
            entity_id=ente_a.id,
            exercise=ANIO,
            status="VIGENTE",
            version=1,
            published_at=datetime(ANIO, 1, 1, 12, 0, tzinfo=TZ_CARACAS),
        )
        db.add(estructura_a)
        db.flush()

        estructura_a_ant = GovernmentStructure(
            company_id=company_a,
            entity_id=ente_a.id,
            exercise=ANIO - 1,
            status="VIGENTE",
            version=1,
            published_at=datetime(ANIO - 1, 1, 1, 12, 0, tzinfo=TZ_CARACAS),
        )
        db.add(estructura_a_ant)
        db.flush()

        unidad_a = GovernmentUnit(
            company_id=company_a,
            structure_id=estructura_a.id,
            parent_id=None,
            code="UNIDAD-A",
            name="Unidad CTL-06 A",
            unit_type="UNIDAD_ADMINISTRATIVA",
            status="ACTIVA",
            valid_from=datetime(ANIO, 1, 1, tzinfo=TZ_CARACAS).date(),
            version=1,
        )
        db.add(unidad_a)
        db.flush()

        unidad_a_ant = GovernmentUnit(
            company_id=company_a,
            structure_id=estructura_a_ant.id,
            parent_id=None,
            code="UNIDAD-ANT",
            name="Unidad CTL-06 Ant",
            unit_type="UNIDAD_ADMINISTRATIVA",
            status="ACTIVA",
            valid_from=datetime(ANIO - 1, 1, 1, tzinfo=TZ_CARACAS).date(),
            version=1,
        )
        db.add(unidad_a_ant)
        db.flush()

        cargo_vig = GovernmentPosition(
            company_id=company_a,
            structure_id=estructura_a.id,
            unit_id=unidad_a.id,
            code="C-VIG",
            name="Cargo Vigente",
            status="VIGENTE",
            valid_from=datetime(ANIO, 1, 1, tzinfo=TZ_CARACAS).date(),
            activated_at=datetime.now(UTC),
            version=1,
        )
        db.add(cargo_vig)
        db.flush()

        cargo_bor = GovernmentPosition(
            company_id=company_a,
            structure_id=estructura_a.id,
            unit_id=unidad_a.id,
            code="C-BOR",
            name="Cargo Borrador",
            status="BORRADOR",
            valid_from=datetime(ANIO, 1, 1, tzinfo=TZ_CARACAS).date(),
            activated_at=datetime.now(UTC),
            version=1,
        )
        db.add(cargo_bor)
        db.flush()

        cargo_ant = GovernmentPosition(
            company_id=company_a,
            structure_id=estructura_a_ant.id,
            unit_id=unidad_a_ant.id,
            code="C-ANT",
            name="Cargo Año Anterior",
            status="VIGENTE",
            valid_from=datetime(ANIO - 1, 1, 1, tzinfo=TZ_CARACAS).date(),
            activated_at=datetime.now(UTC),
            version=1,
        )
        db.add(cargo_ant)
        db.flush()

        ente_b = GovernmentEntity(
            company_id=company_b,
            denominacion="Ente activo CTL-06 B",
            status="ACTIVO",
            version=1,
            activated_at=datetime.now(UTC),
        )
        db.add(ente_b)
        db.flush()

        estructura_b = GovernmentStructure(
            company_id=company_b,
            entity_id=ente_b.id,
            exercise=ANIO,
            status="VIGENTE",
            version=1,
            published_at=datetime(ANIO, 1, 1, 12, 0, tzinfo=TZ_CARACAS),
        )
        db.add(estructura_b)
        db.flush()

        unidad_b = GovernmentUnit(
            company_id=company_b,
            structure_id=estructura_b.id,
            parent_id=None,
            code="UNIDAD-B",
            name="Unidad CTL-06 B",
            unit_type="UNIDAD_ADMINISTRATIVA",
            status="ACTIVA",
            valid_from=datetime(ANIO, 1, 1, tzinfo=TZ_CARACAS).date(),
            version=1,
        )
        db.add(unidad_b)
        db.flush()

        cargo_otra = GovernmentPosition(
            company_id=company_b,
            structure_id=estructura_b.id,
            unit_id=unidad_b.id,
            code="C-OTRA",
            name="Cargo Otra Empresa",
            status="VIGENTE",
            valid_from=datetime(ANIO, 1, 1, tzinfo=TZ_CARACAS).date(),
            activated_at=datetime.now(UTC),
            version=1,
        )
        db.add(cargo_otra)
        db.flush()

        muestra_a = GovernmentAuditSample(
            tenant_id=tenant_a,
            company_id=company_a,
            codigo=f"MU-{ANIO}-0901",
            titulo="Muestra de auditoría CTL-06 A",
            criterio="Criterio de muestra A",
            justificacion="Justificación de muestra A",
            metodo="TODAS",
            semilla=None,
            tamano=2,
            poblacion=2,
            filtros={},
            created_by=ua.id,
        )
        db.add(muestra_a)
        db.flush()

        muestra_b = GovernmentAuditSample(
            tenant_id=tenant_a,
            company_id=company_b,
            codigo=f"MU-{ANIO}-0902",
            titulo="Muestra de auditoría CTL-06 B",
            criterio="Criterio de muestra B",
            justificacion="Justificación de muestra B",
            metodo="TODAS",
            semilla=None,
            tamano=2,
            poblacion=2,
            filtros={},
            created_by=ub.id,
        )
        db.add(muestra_b)
        db.flush()

        eventos_a = []
        for i in range(2):
            evento = AuditEvent(
                tenant_id=tenant_a,
                company_id=company_a,
                user_id=ua.id,
                session_id=uuid4(),
                request_id=uuid4(),
                action="GOV_POSITION_CREATED",
                entity_type="GovernmentPosition",
                entity_id=uuid4(),
                before=None,
                after=None,
                source="API",
                reason="Siembra CTL-06 muestra A",
                evidence=None,
                ip="127.0.0.1",
                event_time=datetime.now(UTC),
            )
            db.add(evento)
            db.flush()
            item = GovernmentAuditSampleItem(
                sample_id=muestra_a.id,
                company_id=company_a,
                audit_event_id=evento.id,
                orden=i + 1,
            )
            db.add(item)
            eventos_a.append(evento.id)

        eventos_b = []
        for i in range(2):
            evento = AuditEvent(
                tenant_id=tenant_a,
                company_id=company_b,
                user_id=ub.id,
                session_id=uuid4(),
                request_id=uuid4(),
                action="GOV_POSITION_CREATED",
                entity_type="GovernmentPosition",
                entity_id=uuid4(),
                before=None,
                after=None,
                source="API",
                reason="Siembra CTL-06 muestra B",
                evidence=None,
                ip="127.0.0.1",
                event_time=datetime.now(UTC),
            )
            db.add(evento)
            db.flush()
            item = GovernmentAuditSampleItem(
                sample_id=muestra_b.id,
                company_id=company_b,
                audit_event_id=evento.id,
                orden=i + 1,
            )
            db.add(item)
            eventos_b.append(evento.id)

        db.commit()

        return {
            "cargo_vigente": cargo_vig.id,
            "cargo_borrador": cargo_bor.id,
            "cargo_anterior": cargo_ant.id,
            "cargo_otra": cargo_otra.id,
            "muestra_a": muestra_a.id,
            "muestra_b": muestra_b.id,
            "partidas_a": eventos_a,
            "partidas_b": eventos_b,
        }


def _cuerpo_independiente(**cambios):
    """Cuerpo válido para un hallazgo de origen INDEPENDIENTE."""
    cuerpo = {
        "titulo": "Hallazgo independiente de prueba",
        "condicion": "La condición observada es una condición de prueba.",
        "criterio": "El criterio normativo es un criterio de prueba.",
        "causa": "La causa identificada es una causa de prueba.",
        "efecto": "El efecto identificado es un efecto de prueba.",
        "riesgo": "MEDIO",
        "origen": "INDEPENDIENTE",
        "origen_descripcion": "Origen independiente válido de prueba.",
    }
    cuerpo.update(cambios)
    return cuerpo


def _cuerpo_muestra(muestra_id, partidas, **cambios):
    """Cuerpo válido para un hallazgo de origen MUESTRA."""
    cuerpo = {
        "titulo": "Hallazgo por muestra de prueba",
        "condicion": "La condición observada es una condición de prueba.",
        "criterio": "El criterio normativo es un criterio de prueba.",
        "causa": "La causa identificada es una causa de prueba.",
        "efecto": "El efecto identificado es un efecto de prueba.",
        "riesgo": "BAJO",
        "origen": "MUESTRA",
        "muestra_id": muestra_id,
        "partidas": partidas,
    }
    cuerpo.update(cambios)
    return cuerpo


def _post(mundo, ruta, usuario, empresa, cuerpo, version=None):
    """POST con alcance y cabecera If-Match opcional."""
    headers = mundo.como(usuario, empresa)
    if version is not None:
        headers["If-Match"] = str(version)
    return mundo.client.post(f"/api/v1{ruta}", headers=headers, json=cuerpo)


def _hallazgo_con_recomendacion(mundo, siembra):
    """Crea un hallazgo independiente y una recomendación; devuelve el DETALLE."""
    cuerpo = _cuerpo_independiente()
    response = _post(mundo, H, "ua", mundo.company_a, cuerpo)
    assert response.status_code == 201, response.text
    hallazgo = response.json()
    response = _post(
        mundo,
        f"{H}/{hallazgo['id']}/recomendaciones",
        "ua",
        mundo.company_a,
        {"texto": "Recomendación de prueba válida."},
        version=1,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _hallazgo_en_remediacion(mundo, siembra):
    """Crea un hallazgo independiente y lo lleva hasta remediación; devuelve el DETALLE final."""
    cuerpo = _cuerpo_independiente()
    response = _post(mundo, H, "ua", mundo.company_a, cuerpo)
    assert response.status_code == 201, response.text
    detalle = response.json()

    response = _post(
        mundo,
        f"{H}/{detalle['id']}/recomendaciones",
        "ua",
        mundo.company_a,
        {"texto": "Recomendación para remediar el hallazgo."},
        version=detalle["version"],
    )
    assert response.status_code == 201, response.text
    detalle = response.json()

    response = _post(
        mundo,
        f"{H}/{detalle['id']}/acciones",
        "ua",
        mundo.company_a,
        {
            "recomendacion_id": detalle["recomendaciones"][0]["id"],
            "descripcion": "Acción correctiva para remediar.",
            "cargo_id": siembra["cargo_vigente"],
            "fecha_objetivo": (hoy_de_negocio() + timedelta(days=30)).isoformat(),
        },
        version=detalle["version"],
    )
    assert response.status_code == 201, response.text
    detalle = response.json()

    response = _post(
        mundo,
        f"{H}/{detalle['id']}/plan",
        "ua",
        mundo.company_a,
        {},
        version=detalle["version"],
    )
    assert response.status_code == 200, response.text
    detalle = response.json()

    response = _post(
        mundo,
        f"{H}/{detalle['id']}/ejecucion",
        "ua",
        mundo.company_a,
        {},
        version=detalle["version"],
    )
    assert response.status_code == 200, response.text
    return response.json()


def _doc_vinculado(mundo, company_id, accion_id) -> str:
    """Crea StoredFile + DocumentVersion ACTIVE + Document ACTIVE vinculado a una acción correctiva."""
    with mundo.factory() as db:
        tipo = db.scalar(
            select(DocumentType).where(
                DocumentType.company_id == company_id,
                DocumentType.code == "GOV-HALLAZGO",
            )
        )
        if tipo is None:
            tipo = DocumentType(
                company_id=company_id,
                code="GOV-HALLAZGO",
                name="Evidencia de acción correctiva",
            )
            db.add(tipo)
            db.flush()
        stored = StoredFile(
            company_id=company_id,
            original_name="evidencia.pdf",
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
            title="Evidencia de acción correctiva",
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
                resource_type="GovernmentCorrectiveAction",
                resource_id=accion_id,
            )
        )
        db.commit()
        return str(doc.id)


def _crear_usuario_con_permisos(mundo, username, permisos, company_id):
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

        for resource, action in permisos:
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


class TestGovCtl06Hallazgos:
    def test_GH6_01_modulo_apagado_403(self, mundo, gobierno, siembra):
        """GH6-01: módulo apagado → GET H con "ua" en company_a: 403 MODULE_NOT_ENTITLED."""
        with mundo.factory() as db:
            inst = licensing_service.get_installation(db)
            snapshot = db.scalar(
                select(LicenseEntitlementSnapshot).where(
                    LicenseEntitlementSnapshot.installation_id == inst.installation_uuid,
                    LicenseEntitlementSnapshot.version == "ctl06-test",
                )
            )
            original = snapshot.modules
            snapshot.modules = {}
            db.commit()

        try:
            response = mundo.get(H, "ua", mundo.company_a)
            assert response.status_code == 403, response.text
            assert response.json()["code"] == "MODULE_NOT_ENTITLED"
        finally:
            with mundo.factory() as db:
                snapshot = db.scalar(
                    select(LicenseEntitlementSnapshot).where(
                        LicenseEntitlementSnapshot.installation_id == inst.installation_uuid,
                        LicenseEntitlementSnapshot.version == "ctl06-test",
                    )
                )
                snapshot.modules = original
                db.commit()

    def test_GH6_02_catalogo_y_mfa(self):
        """GH6-02: catálogo y MFA de los tres permisos (sin red)."""
        assert "gobierno_hallazgos" in CATALOGO_DE_PERMISOS
        assert sorted(CATALOGO_DE_PERMISOS["gobierno_hallazgos"]) == ["manage", "verify", "view"]
        assert classify(["gobierno_hallazgos:view"]) == STANDARD
        assert classify(["gobierno_hallazgos:manage"]) == STANDARD
        assert classify(["gobierno_hallazgos:verify"]) == SENSITIVE

    def test_GH6_03_alta_independiente(self, mundo, gobierno, siembra):
        """GH6-03: alta INDEPENDIENTE por "ua" en company_a → 201 y auditoría."""
        cuerpo = _cuerpo_independiente()
        response = _post(mundo, H, "ua", mundo.company_a, cuerpo)
        assert response.status_code == 201, response.text
        detalle = response.json()

        assert detalle["codigo"].startswith(f"HA-{ANIO}-")
        assert re.fullmatch(r"HA-\d{4}-\d{4}", detalle["codigo"])
        assert detalle["estado"] == "ABIERTO"
        assert detalle["version"] == 1
        assert detalle["muestra"] is None
        assert detalle["partidas"] == []

        with mundo.factory() as db:
            evento = db.scalar(
                select(AuditEvent).where(
                    AuditEvent.action == "GOV_FINDING_CREATED",
                    AuditEvent.entity_type == "GovernmentFinding",
                    AuditEvent.entity_id == detalle["id"],
                    AuditEvent.company_id == mundo.company_a,
                )
            )
            assert evento is not None

    def test_GH6_04_independiente_validacion_422(self, mundo, gobierno, siembra):
        """GH6-04: INDEPENDIENTE sin origen_descripcion o con muestra_id → 422 VALIDATION_ERROR."""
        cuerpo = _cuerpo_independiente()
        cuerpo.pop("origen_descripcion")
        response = _post(mundo, H, "ua", mundo.company_a, cuerpo)
        assert response.status_code == 422, response.text
        assert response.json()["code"] == "VALIDATION_ERROR"

        cuerpo = _cuerpo_independiente(muestra_id=siembra["muestra_a"])
        response = _post(mundo, H, "ua", mundo.company_a, cuerpo)
        assert response.status_code == 422, response.text
        assert response.json()["code"] == "VALIDATION_ERROR"

    def test_GH6_05_muestra_valida(self, mundo, gobierno, siembra):
        """GH6-05: MUESTRA válida → 201 con muestra y partida; no cambian items."""
        with mundo.factory() as db:
            antes = db.scalar(
                select(func.count()).select_from(GovernmentAuditSampleItem).where(
                    GovernmentAuditSampleItem.sample_id == siembra["muestra_a"]
                )
            )

        cuerpo = _cuerpo_muestra(siembra["muestra_a"], [siembra["partidas_a"][0]])
        response = _post(mundo, H, "ua", mundo.company_a, cuerpo)
        assert response.status_code == 201, response.text
        detalle = response.json()

        assert detalle["muestra"]["codigo"] == f"MU-{ANIO}-0901"
        assert detalle["partidas"] == [siembra["partidas_a"][0]]

        with mundo.factory() as db:
            despues = db.scalar(
                select(func.count()).select_from(GovernmentAuditSampleItem).where(
                    GovernmentAuditSampleItem.sample_id == siembra["muestra_a"]
                )
            )
            assert despues == antes

    def test_GH6_06_muestra_ajena_o_partida_invalida(self, mundo, gobierno, siembra):
        """GH6-06: muestra de otra empresa o partida ajena → 422 GOV_FINDING_SOURCE_INVALID."""
        cuerpo = _cuerpo_muestra(siembra["muestra_b"], [siembra["partidas_b"][0]])
        response = _post(mundo, H, "ua", mundo.company_a, cuerpo)
        assert response.status_code == 422, response.text
        assert response.json()["code"] == "GOV_FINDING_SOURCE_INVALID"

        cuerpo = _cuerpo_muestra(siembra["muestra_a"], [siembra["partidas_b"][0]])
        response = _post(mundo, H, "ua", mundo.company_a, cuerpo)
        assert response.status_code == 422, response.text
        assert response.json()["code"] == "GOV_FINDING_SOURCE_INVALID"

    def test_GH6_07_condicion_corta_y_riesgo_invalido(self, mundo, gobierno, siembra):
        """GH6-07: condicion de 5 caracteres y riesgo CRITICO → 422 VALIDATION_ERROR."""
        cuerpo = _cuerpo_independiente(condicion="corta")
        response = _post(mundo, H, "ua", mundo.company_a, cuerpo)
        assert response.status_code == 422, response.text
        assert response.json()["code"] == "VALIDATION_ERROR"

        cuerpo = _cuerpo_independiente(riesgo="CRITICO")
        response = _post(mundo, H, "ua", mundo.company_a, cuerpo)
        assert response.status_code == 422, response.text
        assert response.json()["code"] == "VALIDATION_ERROR"

    def test_GH6_08_recomendaciones_optimismo(self, mundo, gobierno, siembra):
        """GH6-08: recomendaciones exigen If-Match; sin él → 428; versión vieja → 409."""
        cuerpo = _cuerpo_independiente()
        response = _post(mundo, H, "ua", mundo.company_a, cuerpo)
        assert response.status_code == 201, response.text
        hallazgo = response.json()

        response = _post(
            mundo,
            f"{H}/{hallazgo['id']}/recomendaciones",
            "ua",
            mundo.company_a,
            {"texto": "Primera recomendación válida de prueba."},
        )
        assert response.status_code == 428, response.text
        assert response.json()["code"] == "GOV_FINDING_IF_MATCH_REQUIRED"

        response = _post(
            mundo,
            f"{H}/{hallazgo['id']}/recomendaciones",
            "ua",
            mundo.company_a,
            {"texto": "Primera recomendación válida de prueba."},
            version=1,
        )
        assert response.status_code == 201, response.text
        detalle = response.json()
        assert detalle["version"] == 2
        assert len(detalle["recomendaciones"]) == 1
        assert detalle["recomendaciones"][0]["orden"] == 1

        response = _post(
            mundo,
            f"{H}/{hallazgo['id']}/recomendaciones",
            "ua",
            mundo.company_a,
            {"texto": "Segunda recomendación válida de prueba."},
            version=1,
        )
        assert response.status_code == 409, response.text
        assert response.json()["code"] == "GOV_FINDING_STALE"

        response = _post(
            mundo,
            f"{H}/{hallazgo['id']}/recomendaciones",
            "ua",
            mundo.company_a,
            {"texto": "Segunda recomendación válida de prueba."},
            version=2,
        )
        assert response.status_code == 201, response.text
        detalle = response.json()
        assert len(detalle["recomendaciones"]) == 2
        assert detalle["recomendaciones"][1]["orden"] == 2

    def test_GH6_09_accion_con_cargo_vigente(self, mundo, gobierno, siembra):
        """GH6-09: acción con cargo vigente → 201 con instantánea del cargo."""
        detalle = _hallazgo_con_recomendacion(mundo, siembra)
        recomendacion_id = detalle["recomendaciones"][0]["id"]
        version = detalle["version"]

        fecha_objetivo = (hoy_de_negocio() + timedelta(days=30)).strftime("%Y-%m-%d")
        response = _post(
            mundo,
            f"{H}/{detalle['id']}/acciones",
            "ua",
            mundo.company_a,
            {
                "recomendacion_id": recomendacion_id,
                "descripcion": "Acción correctiva válida de prueba.",
                "cargo_id": siembra["cargo_vigente"],
                "fecha_objetivo": fecha_objetivo,
            },
            version=version,
        )
        assert response.status_code == 201, response.text
        detalle = response.json()
        accion = detalle["acciones"][0]

        assert accion["estado"] == "PENDIENTE"
        assert accion["porcentaje"] == 0
        assert accion["cargo_codigo"] == "C-VIG"
        assert accion["cargo_denominacion"] == "Cargo Vigente"
        assert accion["unidad_nombre"] == "Unidad CTL-06 A"
        assert accion["ejercicio"] == ANIO
        assert accion["fecha_objetivo"] == fecha_objetivo

    def test_GH6_10_responsable_invalido(self, mundo, gobierno, siembra):
        """GH6-10: cargo borrador, año anterior u otra empresa → 422 GOV_FINDING_RESPONSIBLE_INVALID."""
        fecha_objetivo = (hoy_de_negocio() + timedelta(days=15)).strftime("%Y-%m-%d")

        for cargo_id in [siembra["cargo_borrador"], siembra["cargo_anterior"], siembra["cargo_otra"]]:
            detalle = _hallazgo_con_recomendacion(mundo, siembra)
            recomendacion_id = detalle["recomendaciones"][0]["id"]
            version = detalle["version"]

            response = _post(
                mundo,
                f"{H}/{detalle['id']}/acciones",
                "ua",
                mundo.company_a,
                {
                    "recomendacion_id": recomendacion_id,
                    "descripcion": f"Acción inválida con cargo {cargo_id}.",
                    "cargo_id": cargo_id,
                    "fecha_objetivo": fecha_objetivo,
                },
                version=version,
            )
            assert response.status_code == 422, response.text
            assert response.json()["code"] == "GOV_FINDING_RESPONSIBLE_INVALID"

    def test_GH6_11_fecha_pasada_y_recomendacion_ajena(self, mundo, gobierno, siembra):
        """GH6-11: fecha ayer → 422 GOV_FINDING_TARGET_DATE_INVALID; recomendación ajena → 422 GOV_FINDING_RECOMMENDATION_INVALID."""
        detalle_1 = _hallazgo_con_recomendacion(mundo, siembra)
        detalle_2 = _hallazgo_con_recomendacion(mundo, siembra)

        fecha_ayer = (hoy_de_negocio() - timedelta(days=1)).strftime("%Y-%m-%d")
        response = _post(
            mundo,
            f"{H}/{detalle_1['id']}/acciones",
            "ua",
            mundo.company_a,
            {
                "recomendacion_id": detalle_1["recomendaciones"][0]["id"],
                "descripcion": "Acción con fecha pasada de prueba.",
                "cargo_id": siembra["cargo_vigente"],
                "fecha_objetivo": fecha_ayer,
            },
            version=detalle_1["version"],
        )
        assert response.status_code == 422, response.text
        assert response.json()["code"] == "GOV_FINDING_TARGET_DATE_INVALID"

        fecha_futura = (hoy_de_negocio() + timedelta(days=10)).strftime("%Y-%m-%d")
        response = _post(
            mundo,
            f"{H}/{detalle_1['id']}/acciones",
            "ua",
            mundo.company_a,
            {
                "recomendacion_id": detalle_2["recomendaciones"][0]["id"],
                "descripcion": "Acción con recomendación ajena de prueba.",
                "cargo_id": siembra["cargo_vigente"],
                "fecha_objetivo": fecha_futura,
            },
            version=detalle_1["version"],
        )
        assert response.status_code == 422, response.text
        assert response.json()["code"] == "GOV_FINDING_RECOMMENDATION_INVALID"

    def test_GH6_12_plan_incompleto_y_estado_posterior(self, mundo, gobierno, siembra):
        """GH6-12: plan sin acción → 409 GOV_FINDING_PLAN_INCOMPLETE; tras acción → 200 PLAN_DE_ACCION; escritura posterior → 409."""
        detalle = _hallazgo_con_recomendacion(mundo, siembra)
        hallazgo_id = detalle["id"]
        recomendacion_id = detalle["recomendaciones"][0]["id"]
        version = detalle["version"]

        response = _post(mundo, f"{H}/{hallazgo_id}/plan", "ua", mundo.company_a, {}, version=version)
        assert response.status_code == 409, response.text
        assert response.json()["code"] == "GOV_FINDING_PLAN_INCOMPLETE"

        fecha_objetivo = (hoy_de_negocio() + timedelta(days=20)).strftime("%Y-%m-%d")
        response = _post(
            mundo,
            f"{H}/{hallazgo_id}/acciones",
            "ua",
            mundo.company_a,
            {
                "recomendacion_id": recomendacion_id,
                "descripcion": "Acción para completar el plan correctivo.",
                "cargo_id": siembra["cargo_vigente"],
                "fecha_objetivo": fecha_objetivo,
            },
            version=version,
        )
        assert response.status_code == 201, response.text
        detalle = response.json()
        version = detalle["version"]
        hallazgo_id = detalle["id"]

        response = _post(mundo, f"{H}/{hallazgo_id}/plan", "ua", mundo.company_a, {}, version=version)
        assert response.status_code == 200, response.text
        detalle = response.json()
        assert detalle["estado"] == "PLAN_DE_ACCION"
        version = detalle["version"]
        hallazgo_id = detalle["id"]

        response = _post(
            mundo,
            f"{H}/{hallazgo_id}/recomendaciones",
            "ua",
            mundo.company_a,
            {"texto": "Recomendación posterior al plan de prueba."},
            version=version,
        )
        assert response.status_code == 409, response.text
        assert response.json()["code"] == "GOV_FINDING_INVALID_STATE"

        tipos = [fila["tipo"] for fila in detalle["historia"]]
        assert tipos == ["CREADO", "RECOMENDACION", "ACCION", "PLAN"]

    def test_GH6_13_cargos_responsables(self, mundo, gobierno, siembra):
        """GH6-13: GET H/cargos-responsables contiene el vigente y excluye borrador, anterior y otra empresa."""
        response = mundo.get(f"{H}/cargos-responsables", "ua", mundo.company_a)
        assert response.status_code == 200, response.text

        ids = {item["id"] for item in response.json()["items"]}
        assert siembra["cargo_vigente"] in ids
        assert siembra["cargo_borrador"] not in ids
        assert siembra["cargo_anterior"] not in ids
        assert siembra["cargo_otra"] not in ids
