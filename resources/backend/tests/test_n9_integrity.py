"""Integridad del binario y congelado histórico (ARCH-MC-001, fase N9).

Dos cosas que solo se pueden comprobar rompiéndolas a propósito: que un objeto
alterado en el almacenamiento no se entregue como si nada, y que un vínculo
congelado siga apuntando a la versión que se aprobó aunque después haya otras.
"""

from __future__ import annotations

import io
import os
from pathlib import Path

import pytest
from sqlalchemy import text

pytest_plugins = ("tests.conftest_multicompany",)


def _pg(mundo) -> None:
    if "postgresql" not in os.environ.get("KONTROL_TEST_DB_URL", ""):
        pytest.skip("La integridad documental se verifica sobre PostgreSQL")


def _documento_con_archivo(mundo, usuario, empresa, marca, contenido=b"%PDF-1.4 original"):
    tipo = mundo.crear("/documentos/tipos", usuario, empresa, {
        "code": f"N9I-{marca}", "name": f"Tipo {marca}",
        "allowed_mime_types": ["application/pdf"], "scan_required": False})
    doc = mundo.crear("/documentos", usuario, empresa,
                      {"document_type_id": tipo, "title": f"Documento {marca}"})
    r = mundo.client.post(f"/api/v1/documentos/{doc}/versiones",
                          headers=mundo.como(usuario, empresa),
                          files={"file": (f"{marca}.pdf", io.BytesIO(contenido),
                                          "application/pdf")})
    assert r.status_code in (200, 201), r.text
    return doc, r.json()


def test_un_objeto_alterado_no_se_entrega_como_si_nada(mundo):
    """Se altera el binario en el almacenamiento, por detrás del sistema.

    El hash quedó registrado al subirlo. Entregar el contenido nuevo bajo ese
    hash sería servir una cosa diciendo que es otra — y en un sistema documental
    eso es exactamente lo que no puede pasar.
    """
    _pg(mundo)
    doc, _ = _documento_con_archivo(mundo, "ua", mundo.company_a, "ALT")

    # Se descarga bien antes de tocarlo: si no, lo de después no probaría nada.
    r = mundo.client.get(f"/api/v1/documentos/{doc}/descargar",
                         headers=mundo.como("ua", mundo.company_a))
    assert r.status_code == 200, f"no se pudo descargar el original: {r.text}"

    db = mundo.factory()
    try:
        clave = db.execute(text(
            "SELECT sf.storage_key FROM stored_files sf "
            "JOIN document_versions dv ON dv.stored_file_id = sf.id "
            "WHERE dv.document_id = :d ORDER BY dv.version_number DESC LIMIT 1"),
            {"d": doc}).scalar_one()
    finally:
        db.close()

    from app.modules.documents.storage import get_storage

    almacen = get_storage()
    raiz = getattr(almacen, "root", None) or getattr(almacen, "_root", None)
    if raiz is None:
        pytest.skip("el proveedor de almacenamiento no expone su raíz en este entorno")
    ruta = Path(raiz) / clave
    assert ruta.exists(), f"el objeto no está donde dice el almacenamiento: {ruta}"
    ruta.write_bytes(b"%PDF-1.4 CONTENIDO SUSTITUIDO")

    r = mundo.client.get(f"/api/v1/documentos/{doc}/descargar",
                         headers=mundo.como("ua", mundo.company_a))
    assert r.status_code == 500, (
        f"se entregó un objeto alterado con estado {r.status_code}")
    assert r.json()["code"] == "STORAGE_HASH_MISMATCH"


def test_el_binario_ausente_tampoco_se_entrega_en_silencio(mundo):
    """Un hash sin binario no es un documento (R-046-5)."""
    _pg(mundo)
    doc, _ = _documento_con_archivo(mundo, "ua", mundo.company_a, "AUS")
    db = mundo.factory()
    try:
        clave = db.execute(text(
            "SELECT sf.storage_key FROM stored_files sf "
            "JOIN document_versions dv ON dv.stored_file_id = sf.id "
            "WHERE dv.document_id = :d ORDER BY dv.version_number DESC LIMIT 1"),
            {"d": doc}).scalar_one()
    finally:
        db.close()

    from app.modules.documents.storage import get_storage

    almacen = get_storage()
    raiz = getattr(almacen, "root", None) or getattr(almacen, "_root", None)
    if raiz is None:
        pytest.skip("el proveedor de almacenamiento no expone su raíz en este entorno")
    (Path(raiz) / clave).unlink()

    r = mundo.client.get(f"/api/v1/documentos/{doc}/descargar",
                         headers=mundo.como("ua", mundo.company_a))
    assert r.status_code == 500
    assert r.json()["code"] == "STORAGE_OBJECT_MISSING"


def test_el_vinculo_congelado_sigue_apuntando_a_la_version_aprobada(mundo):
    """El congelado es lo que hace que una aprobación signifique algo.

    Si al mirar una solicitud aprobada se resolviera la versión **actual**, se
    estaría diciendo que se aprobó un documento que nadie aprobó.
    """
    _pg(mundo)
    doc, v1 = _documento_con_archivo(mundo, "ua", mundo.company_a, "FRZ",
                                     b"%PDF-1.4 version uno")
    version_uno = v1.get("version_id") or v1.get("id")

    db = mundo.factory()
    try:
        from tests.n9_resource_seeds import sembrar

        solicitud = sembrar(db, "ApprovalRequest", mundo.company_a, "FRZ")
        db.commit()
    finally:
        db.close()

    r = mundo.post(f"/documentos/{doc}/vinculos", "ua", mundo.company_a, {
        "resource_type": "ApprovalRequest", "resource_id": solicitud,
        "role": "EVIDENCIA"})
    assert r.status_code == 200, r.text

    # El congelado lo dispara el **consumidor** cuando su entidad se vuelve
    # inmutable: 046 ofrece la capacidad, 045 decide cuándo. Es el contrato de
    # `CVG-045-04` y se ejercita por esa vía, no por una bandera en el vínculo.
    db = mundo.factory()
    try:
        from app.modules.documents import service as documentos

        congelados = documentos.freeze_links(
            db, resource_type="ApprovalRequest", resource_id=solicitud, actor=None)
        db.commit()
    finally:
        db.close()
    assert len(congelados) == 1, "el consumidor no consiguió congelar el vínculo"

    # Llega una versión nueva. El vínculo no debe seguirla.
    r = mundo.client.post(f"/api/v1/documentos/{doc}/versiones",
                          headers=mundo.como("ua", mundo.company_a),
                          files={"file": ("v2.pdf", io.BytesIO(b"%PDF-1.4 version dos"),
                                          "application/pdf")})
    assert r.status_code in (200, 201), r.text

    db = mundo.factory()
    try:
        congelada = db.execute(text(
            "SELECT frozen_version_id FROM document_links WHERE resource_id = :r"),
            {"r": solicitud}).scalar_one()
        versiones = db.execute(text(
            "SELECT count(*) FROM document_versions WHERE document_id = :d"),
            {"d": doc}).scalar_one()
    finally:
        db.close()

    assert versiones == 2, "la segunda versión no se creó: la prueba no demuestra nada"
    assert congelada is not None, "el vínculo no congeló ninguna versión"
    assert str(congelada) == str(version_uno), (
        "el vínculo congelado se movió a la versión nueva: el histórico se reinterpretó")
