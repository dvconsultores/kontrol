import io
import re
import zipfile
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.modules.audit.models import AuditEvent
from app.modules.documents.models import (
    Document,
    DocumentLink,
    DocumentType,
    DocumentVersion,
    StoredFile,
)
from app.modules.documents.storage import generate_storage_key, get_storage
from app.modules.licensing import service as licensing_service
from app.modules.licensing.models import LicenseEntitlementSnapshot
from app.shared.clock import hoy_de_negocio
from tests.test_gov_ctl06_hallazgos import (
    H,
    _crear_usuario_con_permisos,
    _doc_vinculado,
    _hallazgo_en_remediacion,
    _post,
)

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos")

P = "/gobierno/paquetes"
M = "/gobierno/auditoria/muestras"
PROPOSITO = "Revisión de control fiscal externo del ejercicio en curso"


def _doc_real(mundo, company_id: str, accion_id: str | None, datos: bytes, nombre: str) -> str:
    """Documento ACTIVO con binario REAL en el almacenamiento y limpio; vinculado a la acción si se indica."""
    with mundo.factory() as db:
        tipo = (
            db.query(DocumentType)
            .filter(DocumentType.company_id == company_id, DocumentType.code == "GOV-PAQ")
            .first()
        )
        if tipo is None:
            tipo = DocumentType(
                company_id=company_id,
                code="GOV-PAQ",
                name="Evidencia de paquete",
            )
            db.add(tipo)
            db.flush()

        clave = generate_storage_key(company_id)
        tamano, sha = get_storage().put(clave, io.BytesIO(datos))
        stored = StoredFile(
            company_id=company_id,
            original_name=nombre,
            mime_type="application/pdf",
            size=tamano,
            sha256=sha,
            storage_key=clave,
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
            title=f"Documento {nombre}",
            status="ACTIVE",
        )
        db.add(doc)
        db.flush()

        version = DocumentVersion(
            document_id=doc.id,
            company_id=company_id,
            version_number=1,
            stored_file_id=stored.id,
            sha256=sha,
            status="ACTIVE",
        )
        db.add(version)
        db.flush()
        doc.current_version_id = version.id

        if accion_id:
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


def _evento(mundo, accion: str, entidad_id: str) -> str:
    """Id del último AuditEvent de esa acción y entidad."""
    with mundo.factory() as db:
        evento = (
            db.query(AuditEvent)
            .filter(AuditEvent.action == accion, AuditEvent.entity_id == entidad_id)
            .order_by(AuditEvent.event_time.desc())
            .first()
        )
        return str(evento.id)


def _generar(
    mundo,
    muestra_id: str,
    usuario: str = "ua",
    empresa: str | None = None,
    proposito: str = PROPOSITO,
    clave: str | None = None,
):
    headers = mundo.como(usuario, empresa or mundo.company_a)
    if clave:
        headers["Idempotency-Key"] = clave
    return mundo.client.post(
        f"/api/v1{M}/{muestra_id}/paquetes",
        headers=headers,
        json={"proposito": proposito},
    )


def _abrir_zip(datos: bytes) -> zipfile.ZipFile:
    return zipfile.ZipFile(io.BytesIO(datos))


def _activar_gobierno(mundo) -> None:
    """Habilita el módulo «gobierno» en la licencia de la instalación (como el fixture `gobierno` de CTL-06)."""
    with mundo.factory() as db:
        inst = licensing_service.get_installation(db)
        snapshot = db.scalar(
            select(LicenseEntitlementSnapshot).where(
                LicenseEntitlementSnapshot.installation_id == inst.installation_uuid,
                LicenseEntitlementSnapshot.version == "ctl06-test",
            )
        )
        if snapshot is None:
            db.add(LicenseEntitlementSnapshot(installation_id=inst.installation_uuid, modules={"gobierno": True},
                                              version="ctl06-test", taken_at=datetime.now(UTC)))
        else:
            snapshot.modules = {"gobierno": True}
        db.commit()


@pytest.fixture(scope="module")
def escenario(mundo, siembra):
    """Muestra con evidencia documental y un hallazgo originado en ella (empresa A)."""
    _activar_gobierno(mundo)
    f0 = _hallazgo_en_remediacion(mundo, siembra)
    accion0 = f0["acciones"][0]["id"]

    d1_datos = b"%PDF-1.4 evidencia D1 DOC-08 " * 40
    d1 = _doc_real(
        mundo,
        mundo.company_a,
        accion0,
        d1_datos,
        "evidencia-d1.pdf",
    )

    r = _post(
        mundo,
        f"{H}/{f0['id']}/acciones/{accion0}/avances",
        "ua",
        mundo.company_a,
        {
            "nota": "Avance total con su evidencia documental.",
            "porcentaje": 100,
            "documento_id": d1,
        },
        version=f0["version"],
    )
    assert r.status_code in (200, 201), r.text

    ev_progreso = _evento(
        mundo,
        "GOV_CORRECTIVE_ACTION_PROGRESS_RECORDED",
        f0["id"],
    )
    ev_creado = _evento(mundo, "GOV_FINDING_CREATED", f0["id"])

    cuerpo_muestra = {
        "titulo": "Muestra DOC-08",
        "criterio": "Avances de acciones correctivas",
        "justificacion": "Paquete para control fiscal externo",
        "metodo": "ESPECIFICA",
        "filtros": {},
        "eventos": [ev_progreso, ev_creado],
    }
    muestra_id = mundo.crear(M, "ua", mundo.company_a, cuerpo_muestra)
    muestra2_id = mundo.crear(
        M,
        "ua",
        mundo.company_a,
        {
            **cuerpo_muestra,
            "titulo": "Muestra DOC-08 bis",
            "eventos": [ev_creado],
        },
    )

    r = mundo.post(
        H,
        "ua",
        mundo.company_a,
        {
            "titulo": "Hallazgo de la muestra DOC-08",
            "condicion": "Condición observada en la muestra.",
            "criterio": "Criterio normativo aplicable.",
            "causa": "Causa identificada en la revisión.",
            "efecto": "Efecto sobre el control interno.",
            "riesgo": "MEDIO",
            "origen": "MUESTRA",
            "muestra_id": muestra_id,
            "partidas": [ev_progreso],
        },
    )
    assert r.status_code == 201, r.text
    f1 = r.json()

    r = _post(
        mundo,
        f"{H}/{f1['id']}/recomendaciones",
        "ua",
        mundo.company_a,
        {"texto": "Recomendación del hallazgo DOC-08."},
        version=f1["version"],
    )
    assert r.status_code == 201, r.text
    f1 = r.json()

    r = _post(
        mundo,
        f"{H}/{f1['id']}/acciones",
        "ua",
        mundo.company_a,
        {
            "recomendacion_id": f1["recomendaciones"][0]["id"],
            "descripcion": "Acción correctiva del hallazgo DOC-08.",
            "cargo_id": siembra["cargo_vigente"],
            "fecha_objetivo": (hoy_de_negocio() + timedelta(days=30)).isoformat(),
        },
        version=f1["version"],
    )
    assert r.status_code == 201, r.text
    f1 = r.json()
    accion1 = f1["acciones"][0]["id"]

    d3_datos = b"%PDF-1.4 evidencia D3 DOC-08 " * 30
    d3 = _doc_real(
        mundo,
        mundo.company_a,
        accion1,
        d3_datos,
        "evidencia-d3.pdf",
    )
    d2 = _doc_vinculado(mundo, mundo.company_a, accion1)

    return {
        "muestra_id": muestra_id,
        "muestra2_id": muestra2_id,
        "hallazgo_id": f1["id"],
        "hallazgo_codigo": f1["codigo"],
        "accion_id": accion1,
        "ev_progreso": ev_progreso,
        "ev_creado": ev_creado,
        "d1": d1,
        "d2": d2,
        "d3": d3,
        "d1_datos": d1_datos,
        "d3_datos": d3_datos,
    }


class TestGovDoc08Paquete:
    def test_dp01_vista_previa(self, mundo, gobierno, escenario):
        r = mundo.client.get(
            f"/api/v1{M}/{escenario['muestra_id']}/paquete/vista-previa",
            headers=mundo.como("ua", mundo.company_a),
        )
        assert r.status_code == 200, r.text
        cuerpo = r.json()

        assert cuerpo["eventos"] == 2
        assert cuerpo["documentos_incluidos"] == 2
        assert cuerpo["documentos_excluidos"] == 1
        assert cuerpo["hallazgos"] == 1
        assert cuerpo["bytes_estimados"] == len(escenario["d1_datos"]) + len(escenario["d3_datos"])
        assert cuerpo["excede_limite"] is False
        assert cuerpo["paquetes_previos"] == 0

        por_id = {d["id"]: d for d in cuerpo["documentos"]}

        d1 = por_id[escenario["d1"]]
        assert d1["estado"] == "INCLUIDO"
        assert d1["motivo"] is None
        assert d1["version"] == 1
        assert re.fullmatch(r"[0-9a-f]{64}", d1["sha256"])
        assert d1["bytes"] == len(escenario["d1_datos"])
        assert list(d1["referencias"]) == [
            {"tipo": "evento", "id": escenario["ev_progreso"]}
        ]

        d3 = por_id[escenario["d3"]]
        assert d3["estado"] == "INCLUIDO"
        assert d3["motivo"] is None
        assert d3["version"] == 1
        assert re.fullmatch(r"[0-9a-f]{64}", d3["sha256"])
        assert list(d3["referencias"]) == [
            {"tipo": "accion_correctiva", "id": escenario["accion_id"]}
        ]

        d2 = por_id[escenario["d2"]]
        assert d2["estado"] == "EXCLUIDO"
        assert d2["motivo"] == "NO_DISPONIBLE"
        assert d2["sha256"] is None
        assert d2["version"] is None
        assert d2["bytes"] is None

        assert {"eventos": 500, "documentos": 200, "bytes": 262144000} == cuerpo["limites"]
        assert cuerpo["motivo_limite"] is None
        assert cuerpo["muestra"]["id"] == escenario["muestra_id"]

    def test_dp02_generar(self, mundo, gobierno, escenario):
        r = _generar(mundo, escenario["muestra_id"])
        assert r.status_code == 201, r.text
        paquete = r.json()

        assert re.match(r"^PA-\d{4}-\d{4}$", paquete["codigo"])
        assert paquete["numero_generacion"] == 1
        assert re.fullmatch(r"[0-9a-f]{64}", paquete["huella_paquete"])
        assert re.fullmatch(r"[0-9a-f]{64}", paquete["huella_manifiesto"])
        assert paquete["eventos"] == 2
        assert paquete["documentos_incluidos"] == 2
        assert paquete["documentos_excluidos"] == 1
        assert paquete["hallazgos"] == 1
        assert paquete["proposito"] == PROPOSITO
        assert paquete["nombre_archivo"] == f"paquete-{paquete['codigo']}.zip"
        assert (
            paquete["contenido"]["hallazgos"][0]["codigo"]
            == escenario["hallazgo_codigo"]
        )
        assert paquete["verificaciones"] == []
        for documento in paquete["contenido"]["documentos"]:
            assert "nombre_original" not in documento

    def test_dp03_validacion(self, mundo, gobierno, escenario):
        r = _generar(mundo, escenario["muestra_id"], proposito="corto")
        assert r.status_code == 422

        r = _generar(mundo, str(uuid4()))
        assert r.status_code == 404
        assert r.json()["code"] == "GOV_AUDIT_SAMPLE_NOT_FOUND"

    def test_dp04_idempotencia(self, mundo, gobierno, escenario):
        clave = uuid4().hex
        r1 = _generar(mundo, escenario["muestra_id"], clave=clave)
        assert r1.status_code == 201, r1.text
        id1 = r1.json()["id"]

        r2 = _generar(mundo, escenario["muestra_id"], clave=clave)
        assert r2.status_code == 200, r2.text
        assert r2.json()["id"] == id1

        r3 = _generar(mundo, escenario["muestra2_id"], clave=clave)
        assert r3.status_code == 409, r3.text
        assert r3.json()["code"] == "GOV_PACKAGE_IDEMPOTENCY_CONFLICT"

    def test_dp05_nueva_generacion_sin_clave(self, mundo, gobierno, escenario):
        primero = _generar(mundo, escenario["muestra_id"])
        assert primero.status_code == 201, primero.text
        segundo = _generar(mundo, escenario["muestra_id"])
        assert segundo.status_code == 201, segundo.text

        assert segundo.json()["numero_generacion"] > primero.json()["numero_generacion"]
        assert segundo.json()["codigo"] != primero.json()["codigo"]

    def test_dp06_listado_y_detalle(self, mundo, gobierno, escenario):
        _generar(mundo, escenario["muestra_id"])
        _generar(mundo, escenario["muestra_id"])

        r = mundo.client.get(
            f"/api/v1{P}?muestra_id={escenario['muestra_id']}",
            headers=mundo.como("ua", mundo.company_a),
        )
        assert r.status_code == 200, r.text
        items = r.json()["items"]
        assert r.json()["total"] >= 2
        for item in items:
            assert item["muestra_id"] == escenario["muestra_id"]
            assert re.match(r"^MU-", item["muestra_codigo"])

        paquete_id = items[0]["id"]
        r = mundo.client.get(
            f"/api/v1{P}/{paquete_id}",
            headers=mundo.como("ua", mundo.company_a),
        )
        assert r.status_code == 200, r.text
        detalle = r.json()
        assert detalle["muestra_titulo"] == "Muestra DOC-08"
        assert detalle["archivos"] >= 6

    def test_dp07_auditoria(self, mundo, gobierno, escenario):
        r = _generar(mundo, escenario["muestra_id"])
        assert r.status_code == 201, r.text
        paquete = r.json()

        with mundo.factory() as db:
            evento = (
                db.query(AuditEvent)
                .filter(
                    AuditEvent.action == "GOV_AUDIT_PACKAGE_GENERATED",
                    AuditEvent.entity_type == "GovernmentAuditPackage",
                    AuditEvent.entity_id == paquete["id"],
                )
                .order_by(AuditEvent.event_time.desc())
                .first()
            )
            assert evento is not None
            assert evento.after["huella_paquete"] == paquete["huella_paquete"]
            assert evento.after["documentos_excluidos"] == 1

    def test_dp08_permisos(self, mundo, gobierno, escenario):
        _crear_usuario_con_permisos(
            mundo,
            "paq_view",
            [("gobierno_paquetes", "view")],
            mundo.company_a,
        )
        r = _generar(mundo, escenario["muestra_id"], usuario="paq_view")
        assert r.status_code == 403

        r = mundo.client.get(
            f"/api/v1{M}/{escenario['muestra_id']}/paquete/vista-previa",
            headers=mundo.como("paq_view", mundo.company_a),
        )
        assert r.status_code == 200

        _crear_usuario_con_permisos(
            mundo,
            "paq_none",
            [("documentos", "view")],
            mundo.company_a,
        )
        r = mundo.client.get(
            f"/api/v1{M}/{escenario['muestra_id']}/paquete/vista-previa",
            headers=mundo.como("paq_none", mundo.company_a),
        )
        assert r.status_code == 403
