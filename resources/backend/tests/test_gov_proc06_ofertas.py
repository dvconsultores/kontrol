from datetime import UTC, datetime
from io import BytesIO
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.modules.audit.models import AuditEvent
from app.modules.documents.models import Document, DocumentLink, DocumentVersion, StoredFile
from app.modules.documents.service import puede_leer_archivo
from app.modules.documents.storage import generate_storage_key, get_storage
from app.modules.government.models import GovernmentProcurementOfferDocument
from app.modules.identity_access.authority import capabilities_in_company
from app.modules.identity_access.models import User
from tests.org04_ayudantes import crear_funcionario
from tests.org06_guarda import cuenta_con_permisos
from tests.test_gov_ctl01_reglas import cerrar_regla, regla_vigente
from tests.test_gov_ctl06_hallazgos import _post
from tests.test_gov_doc08_paquete import _abrir_zip, _doc_real, _evento, _generar
from tests.test_gov_proc03_expedientes import E, _crear, _cron, _patch

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos", "tests.org04_ayudantes")

CARACAS = ZoneInfo("America/Caracas")


def _body_oferta(funcionario_id, doc_ids=None, **overrides):
    body = {
        "oferente_nombre": "Proveedor Uno",
        "oferente_documento": "abc-123 456",
        "representante": "Representante Uno",
        "tipo_sobre": "UNICO",
        "canal": "MEDIO_ELECTRONICO",
        "recibida_en": datetime.now(UTC).isoformat(),
        "funcionario_id": funcionario_id,
        "confidencial": True,
        "documento_ids": doc_ids or [],
    }
    body.update(overrides)
    return body


def _recibir(mundo, expediente, usuario, empresa, doc_ids=None, status_esperado=201, **overrides):
    funcionario = crear_funcionario(mundo, usuario=usuario, empresa=empresa)
    body = _body_oferta(funcionario["id"], doc_ids=doc_ids, **overrides)
    url = f"{E}/{expediente['id']}/ofertas"
    r = _post(mundo, url, usuario, empresa, body, version=expediente["version"])
    assert r.status_code == status_esperado, r.text
    return r.json()


def test_oferta_completa(mundo, gobierno, ocupacion):
    """Crear oferta, documento congelado y sellado, lista, detalle, cronología sin título, pendiente, auditoría."""
    exp = _crear(mundo, ocupacion)
    doc_id = _doc_real(mundo, mundo.company_a, None, b"contenido original", "sellado")
    r = mundo.post(f"/documentos/{doc_id}/vinculos", "ua", mundo.company_a, {
        "resource_type": "GovernmentProcurementFile",
        "resource_id": exp["id"],
    })
    assert r.status_code == 200, r.text
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()

    oferta = _recibir(mundo, exp, "ua", mundo.company_a, [doc_id])

    assert oferta["referencia"] == "R-0001"
    assert oferta["oferente_documento"] == "ABC123456"
    assert oferta["identidad_etiqueta"] == "Identidad declarada, sin validar en RNC/SNC"
    assert oferta["situacion"] == "PENDIENTE_APERTURA"
    assert oferta["confidencial"] is True
    assert oferta["confidencialidad_etiqueta"] == "Sellada hasta la apertura"
    assert oferta["fundamento_confidencialidad"] == "Modalidad sin declarar: se protege hasta la apertura"
    assert oferta["documentos_total"] == 1
    assert oferta["integridad"] == "VERIFICADA"
    assert len(oferta["documentos"]) == 1
    assert oferta["documentos"][0]["documento_id"] is None
    assert oferta["documentos"][0]["titulo"] is None

    lista = mundo.get(f"{E}/{exp['id']}/ofertas", "ua", mundo.company_a).json()
    assert lista["total"] == 1
    assert lista["items"][0]["referencia"] == "R-0001"
    assert lista["recepcion_concluida_en"] is None
    assert lista["puede_recibir_sin_sello"] is False
    assert lista["aviso_identidad"] == "Identidad declarada, sin validar en RNC/SNC"

    detalle = mundo.get(f"{E}/{exp['id']}/ofertas/{oferta['id']}", "ua", mundo.company_a).json()
    assert detalle["referencia"] == "R-0001"
    assert detalle["documentos"][0]["documento_id"] is None

    cron = _cron(mundo, exp["id"])
    for item in cron["items"]:
        if "OFERTA" in item.get("clase_evento", ""):
            assert "Documento sellado" not in item.get("titulo", "")
            assert "Documento sellado" not in item.get("detalle", "")

    exp_detalle = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    pendientes = [p for p in exp_detalle.get("pendientes", [])]
    assert any(p.get("codigo") == "APERTURA_PENDIENTE" and p.get("texto", "").startswith("Pendiente de apertura") for p in pendientes)
    assert exp_detalle["ofertas_total"] == 1
    assert exp_detalle["ofertas_selladas"] == 1

    with mundo.factory() as s:
        eventos = s.query(AuditEvent).filter(AuditEvent.action == "GOV_PROCUREMENT_OFFER_RECEIVED").all()
        assert any("R-0001" in str(e.after) for e in eventos)


def test_seguridad_material_documento(mundo, gobierno, ocupacion):
    """Antes y después: rutas documentales y biblioteca."""
    exp = _crear(mundo, ocupacion)
    doc_id = _doc_real(mundo, mundo.company_a, None, b"contenido real", "material")
    r = mundo.post(f"/documentos/{doc_id}/vinculos", "ua", mundo.company_a, {
        "resource_type": "GovernmentProcurementFile",
        "resource_id": exp["id"],
        "role": "material",
    })
    assert r.status_code == 200, r.text

    nombre = f"cuenta_material_proc06_{uuid4().hex[:8]}"
    user_id = cuenta_con_permisos(mundo, nombre, [
        ("documentos", "view"),
        ("documentos", "edit"),
        ("documentos", "upload"),
        ("documentos", "download"),
        ("documentos", "link"),
        ("documentos", "deactivate"),
        ("documentos", "delete"),
        ("gobierno_expedientes", "view"),
    ])
    cabeceras = mundo.como(nombre, mundo.company_a)

    # ANTES
    r = mundo.client.get(f"/api/v1/documentos/{doc_id}", headers=cabeceras)
    assert r.status_code == 200, r.text
    r = mundo.client.get(f"/api/v1/documentos/{doc_id}/descargar", headers=cabeceras)
    assert r.status_code == 200, r.text
    assert r.content == b"contenido real"
    r = mundo.client.get(f"/api/v1/documentos/{doc_id}/preview", headers=cabeceras)
    assert r.status_code == 200, r.text
    r = mundo.client.get(f"/api/v1/documentos/{doc_id}/versiones", headers=cabeceras)
    assert r.status_code == 200, r.text
    versiones = r.json()
    version_id = versiones[0]["id"]
    r = mundo.client.get(f"/api/v1/documentos/{doc_id}/versiones/{version_id}/descargar", headers=cabeceras)
    assert r.status_code == 200, r.text
    r = mundo.client.get("/api/v1/documentos?q=Documento+material", headers=cabeceras)
    assert r.status_code == 200, r.text
    biblioteca = r.json()
    assert biblioteca["total"] == 1
    r = mundo.client.get(
        f"/api/v1/documentos/por-recurso/GovernmentProcurementFile/{exp['id']}",
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text
    por_recurso = r.json()
    assert len(por_recurso) == 1
    link_id = por_recurso[0]["link"]["id"]
    assert por_recurso[0]["link"]["is_frozen"] is False

    # Crear vínculo adicional sobre el mismo expediente
    r = mundo.client.post(
        f"/api/v1/documentos/{doc_id}/vinculos", headers=cabeceras,
        json={"resource_type": "GovernmentProcurementFile", "resource_id": exp["id"], "role": "otro"},
    )
    assert r.status_code == 200, r.text
    vinculo_extra = r.json()
    r = mundo.client.delete(f"/api/v1/documentos/vinculos/{vinculo_extra['id']}", headers=cabeceras)
    assert r.status_code == 200, r.text

    with mundo.factory() as s:
        company = mundo.company_a
        doc = s.get(Document, doc_id)
        user = s.get(User, user_id)
        assert puede_leer_archivo(s, doc, company, capabilities_in_company(s, user, company)) is True

    # DESPUÉS
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    _recibir(mundo, exp, "ua", mundo.company_a, [doc_id])

    r = mundo.client.get(f"/api/v1/documentos/{doc_id}", headers=cabeceras)
    assert r.status_code == 404, r.text
    r = mundo.client.get(f"/api/v1/documentos/{doc_id}/descargar", headers=cabeceras)
    assert r.status_code == 404, r.text
    r = mundo.client.get(f"/api/v1/documentos/{doc_id}/preview", headers=cabeceras)
    assert r.status_code == 404, r.text
    r = mundo.client.get(f"/api/v1/documentos/{doc_id}/versiones", headers=cabeceras)
    assert r.status_code == 404, r.text
    r = mundo.client.get(f"/api/v1/documentos/{doc_id}/versiones/{version_id}/descargar", headers=cabeceras)
    assert r.status_code == 404, r.text
    r = mundo.client.post(
        f"/api/v1/documentos/{doc_id}/versiones", headers=cabeceras,
        files={"file": ("oferta.pdf", b"bytes version 1", "application/pdf")},
    )
    assert r.status_code == 404, r.text
    r = mundo.client.patch(f"/api/v1/documentos/{doc_id}", headers=cabeceras, json={"title": "otro"})
    assert r.status_code == 404, r.text
    r = mundo.client.post(f"/api/v1/documentos/{doc_id}/archive", headers=cabeceras)
    assert r.status_code == 404, r.text
    r = mundo.client.delete(f"/api/v1/documentos/{doc_id}", headers=cabeceras)
    assert r.status_code == 404, r.text
    r = mundo.client.post(
        f"/api/v1/documentos/{doc_id}/vinculos", headers=cabeceras,
        json={"resource_type": "GovernmentProcurementFile", "resource_id": exp["id"], "role": "otro"},
    )
    assert r.status_code == 404, r.text
    r = mundo.client.delete(f"/api/v1/documentos/vinculos/{link_id}", headers=cabeceras)
    assert r.status_code == 404, r.text

    r = mundo.client.get("/api/v1/documentos?q=Documento+material", headers=cabeceras)
    assert r.status_code == 200, r.text
    biblioteca = r.json()
    assert biblioteca["total"] == 0
    r = mundo.client.get(
        f"/api/v1/documentos/por-recurso/GovernmentProcurementFile/{exp['id']}",
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text
    por_recurso = r.json()
    assert len(por_recurso) == 0

    with mundo.factory() as s:
        company = mundo.company_a
        doc = s.get(Document, doc_id)
        user = s.get(User, user_id)
        assert puede_leer_archivo(s, doc, company, capabilities_in_company(s, user, company)) is False


def test_folio_rechaza_documento_sellado_y_documento_foliado(mundo, gobierno, ocupacion):
    """El sellado no se puede foliar; un documento foliado no se recibe."""
    exp = _crear(mundo, ocupacion)
    doc_sellado = _doc_real(mundo, mundo.company_a, None, b"para sellar", "folio_sellado")
    r = mundo.post(f"/documentos/{doc_sellado}/vinculos", "ua", mundo.company_a, {
        "resource_type": "GovernmentProcurementFile",
        "resource_id": exp["id"],
    })
    assert r.status_code == 200, r.text
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    _recibir(mundo, exp, "ua", mundo.company_a, [doc_sellado])

    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    r = _post(mundo, f"{E}/{exp['id']}/folios", "ua", mundo.company_a, {
        "clase": "SOLICITUD",
        "documento_id": doc_sellado,
        "acto_id": None,
        "hito_id": None,
        "reservado": False,
        "motivo_reserva": None,
    }, version=exp["version"])
    assert r.status_code == 422, r.text
    assert "documento_id" in r.json().get("field_errors", {})

    doc_foliado = _doc_real(mundo, mundo.company_a, None, b"folio previo", "folio_previo")
    r = mundo.post(f"/documentos/{doc_foliado}/vinculos", "ua", mundo.company_a, {
        "resource_type": "GovernmentProcurementFile",
        "resource_id": exp["id"],
    })
    assert r.status_code == 200, r.text
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    r = _post(mundo, f"{E}/{exp['id']}/folios", "ua", mundo.company_a, {
        "clase": "SOLICITUD",
        "documento_id": doc_foliado,
        "acto_id": None,
        "hito_id": None,
        "reservado": False,
        "motivo_reserva": None,
    }, version=exp["version"])
    assert r.status_code == 200, r.text

    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    funcionario = crear_funcionario(mundo, usuario="ua", empresa=mundo.company_a)
    r = _post(mundo, f"{E}/{exp['id']}/ofertas", "ua", mundo.company_a,
              _body_oferta(funcionario["id"], [doc_foliado], oferente_documento="ABC123"), version=exp["version"])
    assert r.status_code == 422, r.text
    assert "documento_ids" in r.json().get("field_errors", {})


def test_paquete(mundo, gobierno, ocupacion):
    """Antes: paquete incluye documento; después: 403 en descarga y manifiesto, sin bytes."""
    exp = _crear(mundo, ocupacion)
    doc_id = _doc_real(mundo, mundo.company_a, None, b"bytes del paquete", "paquete")
    r = mundo.post(f"/documentos/{doc_id}/vinculos", "ua", mundo.company_a, {
        "resource_type": "GovernmentProcurementFile",
        "resource_id": exp["id"],
    })
    assert r.status_code == 200, r.text
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    evento_id = _evento(mundo, "GOV_PROCUREMENT_FILE_CREATED", exp["id"])

    muestra = mundo.crear("/gobierno/auditoria/muestras", "ua", mundo.company_a, {
        "titulo": "Muestra ofertas",
        "criterio": "Para validar paquete",
        "justificacion": "Prueba de seguridad documental",
        "metodo": "ESPECIFICA",
        "filtros": {},
        "eventos": [evento_id],
    })
    _resp = _generar(mundo, muestra)
    assert _resp.status_code == 201
    paquete_id = _resp.json()["id"]
    antes = mundo.get(f"/gobierno/paquetes/{paquete_id}", "ua", mundo.company_a).json()
    assert antes["documentos_incluidos"] == 1
    r = mundo.get(f"/gobierno/paquetes/{paquete_id}/descargar", "ua", mundo.company_a)
    assert r.status_code == 200, r.text
    zip_bytes = r.content
    with _abrir_zip(zip_bytes) as zf:
        nombres = zf.namelist()
        assert any(b"bytes del paquete" in zf.read(n) for n in nombres)

    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    _recibir(mundo, exp, "ua", mundo.company_a, [doc_id])

    r = mundo.get(f"/gobierno/paquetes/{paquete_id}/descargar", "ua", mundo.company_a)
    assert r.status_code == 403, r.text
    r = mundo.get(f"/gobierno/paquetes/{paquete_id}/manifiesto", "ua", mundo.company_a)
    assert r.status_code == 403, r.text
    detalle = mundo.get(f"/gobierno/paquetes/{paquete_id}", "ua", mundo.company_a).json()
    assert "paquete" not in detalle.get("titulo", "")

    muestra2 = mundo.crear("/gobierno/auditoria/muestras", "ua", mundo.company_a, {
        "titulo": "Muestra post sello",
        "criterio": "Sin documentos",
        "justificacion": "Prueba de sello",
        "metodo": "ESPECIFICA",
        "filtros": {},
        "eventos": [evento_id],
    })
    _resp = _generar(mundo, muestra2)
    assert _resp.status_code == 201
    paquete_id2 = _resp.json()["id"]
    detalle2 = mundo.get(f"/gobierno/paquetes/{paquete_id2}", "ua", mundo.company_a).json()
    assert detalle2["documentos_incluidos"] == 0
    r = mundo.get(f"/gobierno/paquetes/{paquete_id2}/descargar", "ua", mundo.company_a)
    assert r.status_code == 200, r.text
    zip_bytes2 = r.content
    with _abrir_zip(zip_bytes2) as zf:
        for miembro in zf.namelist():
            assert b"bytes del paquete" not in zf.read(miembro)


def test_congelacion(mundo, gobierno, ocupacion):
    """El vínculo congelado se mantiene en la versión original; la descarga congelada da los bytes originales."""
    exp = _crear(mundo, ocupacion)
    doc_id = _doc_real(mundo, mundo.company_a, None, b"bytes originales", "congelado")
    r = mundo.post(f"/documentos/{doc_id}/vinculos", "ua", mundo.company_a, {
        "resource_type": "GovernmentProcurementFile",
        "resource_id": exp["id"],
    })
    assert r.status_code == 200, r.text
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()

    r = _patch(mundo, exp, modalidad_declarada="CONSULTA_PRECIOS", modalidad_fundamento="fundamento", modalidad_fuente="fuente")
    exp = r.json()
    assert exp["modalidad_declarada"] == "CONSULTA_PRECIOS"

    oferta = _recibir(mundo, exp, "ua", mundo.company_a, [doc_id],
                      confidencial=False, motivo_sin_sello="No se sella porque es consulta")
    assert oferta["confidencial"] is False
    assert oferta["fundamento_confidencialidad"] == "No se sella porque es consulta"
    assert oferta["documentos"][0]["documento_id"] == doc_id
    assert oferta["documentos"][0]["titulo"] == "Documento congelado"

    # Subir versión 2 por base de datos
    with mundo.factory() as s:
        doc = s.get(Document, doc_id)
        v1 = s.query(DocumentVersion).filter(DocumentVersion.document_id == doc_id).order_by(DocumentVersion.version_number).first()
        v1.status = "SUPERSEDED"
        contenido_v2 = b"bytes version 2"
        clave_v2 = generate_storage_key(mundo.company_a)
        tamano_v2, sha_v2 = get_storage().put(clave_v2, BytesIO(contenido_v2))
        stored_v2 = StoredFile(
            company_id=mundo.company_a,
            original_name="version2.pdf",
            mime_type="application/pdf",
            size=tamano_v2,
            sha256=sha_v2,
            storage_key=clave_v2,
            storage_provider="FILESYSTEM",
            security_status="CLEAN",
            status="AVAILABLE",
            uploaded_at=datetime.now(UTC),
        )
        s.add(stored_v2)
        s.flush()
        version_v2 = DocumentVersion(
            document_id=doc_id,
            company_id=mundo.company_a,
            version_number=2,
            stored_file_id=stored_v2.id,
            sha256=sha_v2,
            status="ACTIVE",
        )
        s.add(version_v2)
        s.flush()
        doc.current_version_id = version_v2.id
        s.commit()
        version_id2 = version_v2.id

    with mundo.factory() as s:
        doc = s.get(Document, doc_id)
        v1 = s.query(DocumentVersion).filter(DocumentVersion.document_id == doc_id).order_by(DocumentVersion.version_number).first()
        v2 = s.get(DocumentVersion, version_id2)
        assert v1.version_number == 1
        assert v2.version_number == 2
        assert doc.current_version_id == v2.id
        v1_stored = s.get(StoredFile, v1.stored_file_id)
        assert v1_stored.sha256 == oferta["documentos"][0]["huella"]

    detalle = mundo.get(f"{E}/{exp['id']}/ofertas/{oferta['id']}", "ua", mundo.company_a).json()
    assert detalle["documentos"][0]["version_numero"] == 1
    assert detalle["integridad"] == "VERIFICADA"

    with mundo.factory() as s:
        v1 = s.query(DocumentVersion).filter(DocumentVersion.document_id == doc_id).order_by(DocumentVersion.version_number).first()
        version_id_1 = v1.id

    r = mundo.get(f"/documentos/{doc_id}/versiones/{version_id_1}/descargar", "ua", mundo.company_a)
    assert r.status_code == 200, r.text
    assert r.content == b"bytes originales"

    # Intentar borrar el vínculo congelado
    with mundo.factory() as s:
        link = s.query(DocumentLink).filter(
            DocumentLink.document_id == doc_id,
            DocumentLink.resource_type == "GovernmentProcurementFile",
            DocumentLink.resource_id == exp["id"],
        ).first()
        r = mundo.client.delete(f"/api/v1/documentos/vinculos/{link.id}", headers=mundo.como("ua", mundo.company_a))
        assert r.status_code == 409, r.text
        assert r.json()["code"] == "LINK_FROZEN"


def test_integridad_alterada_y_sin_archivo(mundo, gobierno, ocupacion):
    """ALTERADA por StoredFile corrupto; SIN_ARCHIVO para sobre físico sin documentos."""
    exp = _crear(mundo, ocupacion)
    doc_id = _doc_real(mundo, mundo.company_a, None, b"integridad", "integridad")
    r = mundo.post(f"/documentos/{doc_id}/vinculos", "ua", mundo.company_a, {
        "resource_type": "GovernmentProcurementFile",
        "resource_id": exp["id"],
    })
    assert r.status_code == 200, r.text
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    oferta = _recibir(mundo, exp, "ua", mundo.company_a, [doc_id])

    with mundo.factory() as s:
        row = s.query(GovernmentProcurementOfferDocument).filter(
            GovernmentProcurementOfferDocument.offer_id == oferta["id"]
        ).first()
        version = s.get(DocumentVersion, row.document_version_id)
        stored = s.get(StoredFile, version.stored_file_id)
        stored.sha256 = "0" * 64
        s.commit()

    detalle = mundo.get(f"{E}/{exp['id']}/ofertas/{oferta['id']}", "ua", mundo.company_a).json()
    assert detalle["integridad"] == "ALTERADA"
    assert detalle["documentos"][0]["integridad"] == "ALTERADA"

    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    oferta_fisica = _recibir(mundo, exp, "ua", mundo.company_a, None,
                             canal="ACTO_PUBLICO", condicion_sobre="Sobre cerrado",
                             tipo_sobre="CALIFICACION")
    assert oferta_fisica["integridad"] == "SIN_ARCHIVO"
    assert oferta_fisica["documentos_total"] == 0


def test_negativos_materiales(mundo, gobierno, ocupacion):
    """Otra empresa, sin permisos, duplicado, versión vieja, sin If-Match, concurso sin sello, SoD."""
    exp = _crear(mundo, ocupacion)
    r = mundo.get(f"{E}/{exp['id']}/ofertas", "ub", mundo.company_b)
    assert r.status_code == 404, r.text

    doc_otro = _doc_real(mundo, mundo.company_b, None, b"otro", "otro")
    r = _post(mundo, f"{E}/{exp['id']}/ofertas", "ua", mundo.company_a,
              _body_oferta(crear_funcionario(mundo, usuario="ua", empresa=mundo.company_a)["id"], [doc_otro]), version=exp["version"])
    assert r.status_code == 422, r.text
    assert "documento_ids" in r.json().get("field_errors", {})

    cuenta = f"sin_permisos_proc06_{uuid4().hex[:8]}"
    cuenta_con_permisos(mundo, cuenta, [("gobierno_expedientes", "view")])
    r = mundo.get(f"{E}/{exp['id']}/ofertas", cuenta, mundo.company_a)
    assert r.status_code == 403, r.text
    r = _post(mundo, f"{E}/{exp['id']}/ofertas", cuenta, mundo.company_a,
              _body_oferta(crear_funcionario(mundo, usuario="ua", empresa=mundo.company_a)["id"], []), version=exp["version"])
    assert r.status_code == 403, r.text

    doc_id = _doc_real(mundo, mundo.company_a, None, b"duplicado", "duplicado")
    r = mundo.post(f"/documentos/{doc_id}/vinculos", "ua", mundo.company_a, {
        "resource_type": "GovernmentProcurementFile",
        "resource_id": exp["id"],
    })
    assert r.status_code == 200, r.text
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    _recibir(mundo, exp, "ua", mundo.company_a, [doc_id],
             oferente_documento="abc-123")
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    r = _post(mundo, f"{E}/{exp['id']}/ofertas", "ua", mundo.company_a,
              _body_oferta(crear_funcionario(mundo, usuario="ua", empresa=mundo.company_a)["id"], [], oferente_documento="ABC123", canal="ACTO_PUBLICO", condicion_sobre="texto sobre"),
              version=exp["version"])
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_PROCUREMENT_OFFER_DUPLICATE"

    r = _post(mundo, f"{E}/{exp['id']}/ofertas", "ua", mundo.company_a,
              _body_oferta(crear_funcionario(mundo, usuario="ua", empresa=mundo.company_a)["id"], []), version=exp["version"] - 1)
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_PROCUREMENT_FILE_STALE"

    r = mundo.post(f"{E}/{exp['id']}/ofertas", "ua", mundo.company_a,
                   _body_oferta(crear_funcionario(mundo, usuario="ua", empresa=mundo.company_a)["id"], []))
    assert r.status_code == 428, r.text

    # Concurso sin sello
    exp_concurso = _crear(mundo, ocupacion)
    exp_concurso = _patch(mundo, exp_concurso, modalidad_declarada="CONCURSO_ABIERTO", modalidad_fundamento="fundamento", modalidad_fuente="fuente").json()
    r = _post(mundo, f"{E}/{exp_concurso['id']}/ofertas", "ua", mundo.company_a,
              _body_oferta(crear_funcionario(mundo, usuario="ua", empresa=mundo.company_a)["id"], [], confidencial=False, canal="ACTO_PUBLICO", condicion_sobre="texto sobre"),
              version=exp_concurso["version"])
    assert r.status_code == 422, r.text
    assert "confidencial" in r.json().get("field_errors", {})

    # SoD
    regla = regla_vigente(mundo, proceso="PROC-03", accion_a="PROC03_REGISTRAR", accion_b="PROC03_RECIBIR")
    try:
        exp_sod = _crear(mundo, ocupacion)
        exp_sod = mundo.get(f"{E}/{exp_sod['id']}", "ua", mundo.company_a).json()
        r = _post(mundo, f"{E}/{exp_sod['id']}/ofertas", "ua", mundo.company_a,
                  _body_oferta(crear_funcionario(mundo, usuario="ua", empresa=mundo.company_a)["id"], []), version=exp_sod["version"])
        assert r.status_code == 409, r.text
        assert r.json()["code"] == "GOV_SOD_CONFLICT"
    finally:
        cerrar_regla(mundo, regla)


def test_update_sql_offer_immutable(mundo, gobierno, ocupacion):
    """UPDATE por SQL de oferta falla en postgresql."""
    exp = _crear(mundo, ocupacion)
    doc_id = _doc_real(mundo, mundo.company_a, None, b"sql", "sql")
    r = mundo.post(f"/documentos/{doc_id}/vinculos", "ua", mundo.company_a, {
        "resource_type": "GovernmentProcurementFile",
        "resource_id": exp["id"],
    })
    assert r.status_code == 200, r.text
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    oferta = _recibir(mundo, exp, "ua", mundo.company_a, [doc_id])

    with mundo.factory() as s:
        if s.get_bind().dialect.name != "postgresql":
            pytest.skip("Requiere postgresql para validar el trigger de inmutabilidad")
        with pytest.raises(DBAPIError):
            s.execute(text("UPDATE gov_procurement_offers SET oferente_nombre='hack' WHERE id=:id"), {"id": oferta["id"]})
            s.commit()
        s.rollback()
