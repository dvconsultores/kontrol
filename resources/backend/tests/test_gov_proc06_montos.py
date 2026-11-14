import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.core.company_context import CompanyContext
from app.core.errors import ConflictError
from app.modules.audit.models import AuditEvent
from app.modules.government.models import (
    GovernmentProcurementFileEvent,
    GovernmentProcurementOfferAmount,
    GovernmentProcurementOfferDocument,
)
from app.modules.government.schemas_ofertas import MontoEntrada
from app.modules.government.service_ofertas_montos import declarar_monto
from app.modules.identity_access.models import User
from app.modules.organization.models import Company
from tests.concurrency import carrera
from tests.org06_guarda import cuenta_con_permisos
from tests.proc08_ayudantes import _recibir_oferta, evaluacion_concluida
from tests.test_gov_ctl06_hallazgos import _post
from tests.test_gov_doc08_paquete import _doc_real
from tests.test_gov_proc03_expedientes import E, _crear, _patch
from tests.test_gov_proc06_ofertas import _recibir
from tests.test_gov_proc07_evaluacion import (
    _abrir_ofertas,
    _crear_criterios_contrato,
    _crear_matriz,
    _preparar,
)
from tests.test_gov_proc10_garantias import HOY, _adjudicado, _doc, _emisor, _gar, _post_g

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos", "tests.org04_ayudantes")


def _abiertas(mundo, ocupacion, n=2) -> tuple[dict, list[dict]]:
    exp, comision = _preparar(mundo, ocupacion)
    matriz = _crear_matriz(mundo, exp)
    estado, matriz_version, criterios = _crear_criterios_contrato(mundo, exp, matriz)
    r = _post(
        mundo,
        f"{E}/{exp['id']}/evaluacion/matriz/bloquear",
        "ua",
        mundo.company_a,
        {},
        version=matriz_version,
    )
    assert r.status_code == 200
    ofertas = []
    for i in range(n):
        doc_id = _doc_real(mundo, mundo.company_a, None, f"oferta-{i}".encode(), f"oferta-{i}.pdf")
        r = mundo.post(
            f"/documentos/{doc_id}/vinculos",
            "ua",
            mundo.company_a,
            {"resource_type": "GovernmentProcurementFile", "resource_id": exp["id"]},
        )
        assert r.status_code == 200
        exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
        oferta = _recibir_oferta(mundo, exp, "ua", mundo.company_a, f"Oferente {i + 1}", doc_id)
        ofertas.append(oferta)
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    estado_apertura, exp = _abrir_ofertas(mundo, exp, comision, ofertas)
    return exp, ofertas


def _insertar_monto(mundo, oferta_id, neto, tributos, total, moneda="VES"):
    with mundo.factory() as db:
        row = db.scalars(
            select(GovernmentProcurementOfferDocument).where(
                GovernmentProcurementOfferDocument.offer_id == oferta_id
            )
        ).first()
        uid = db.scalar(select(User.id).where(User.username == "ua"))
        amount = GovernmentProcurementOfferAmount(
            company_id=mundo.company_a,
            offer_id=oferta_id,
            version=1,
            moneda=moneda,
            monto_sin_iva=Decimal(neto),
            tributos=Decimal(tributos),
            total_con_tributos=Decimal(total),
            soporte_tipo="DOCUMENTO_OFERTA",
            soporte_document_id=row.document_id,
            soporte_version_id=row.document_version_id,
            soporte_sha256=row.sha256,
            motivo=None,
            reemplaza_id=None,
            registrada_por=uid,
            registrada_en=datetime.now(UTC),
            created_by=uid,
        )
        db.add(amount)
        db.commit()
        return amount.id


def test_sellada_sin_apertura(mundo, gobierno, ocupacion):
    """Una oferta confidencial sin abrir no permite declarar monto."""
    exp, comision = _preparar(mundo, ocupacion)
    doc_id = _doc_real(mundo, mundo.company_a, None, b"documento", "doc.pdf")
    r = mundo.post(
        f"/documentos/{doc_id}/vinculos",
        "ua",
        mundo.company_a,
        {"resource_type": "GovernmentProcurementFile", "resource_id": exp["id"]},
    )
    assert r.status_code == 200
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    oferta = _recibir_oferta(mundo, exp, "ua", mundo.company_a, "Oferente 1", doc_id)
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    r = mundo.get(f"{E}/{exp['id']}/ofertas", "ua", mundo.company_a)
    assert r.status_code == 200
    item = next(o for o in r.json()["items"] if o["id"] == oferta["id"])
    assert item["monto_estado"] == "SELLADO"
    assert item["monto"] is None
    assert item["monto_bloqueo"] is not None
    r = mundo.get(f"{E}/{exp['id']}/ofertas/{oferta['id']}", "ua", mundo.company_a)
    assert r.status_code == 200
    assert r.json()["soportes_monto"] == []
    r = _post(
        mundo,
        f"{E}/{exp['id']}/ofertas/{oferta['id']}/montos",
        "ua",
        mundo.company_a,
        {
            "moneda": "VES",
            "monto_sin_iva": "1000.00",
            "tributos": "160.00",
            "total_con_tributos": "1160.00",
            "soporte_tipo": "ACTA_APERTURA",
            "soporte_documento_id": doc_id,
            "motivo": None,
            "version_anterior": None,
        },
        version=exp["version"],
    )
    assert r.status_code == 409
    assert "GOV_OFFER_AMOUNT_SEALED" in r.text


def test_declarar_y_corregir(mundo, gobierno, ocupacion):
    """Declarar y corregir un monto de oferta abierta."""
    exp, ofertas = _abiertas(mundo, ocupacion)
    r = mundo.get(f"{E}/{exp['id']}/ofertas/{ofertas[0]['id']}", "ua", mundo.company_a)
    assert r.status_code == 200
    detalle = r.json()
    tipos = {s["tipo"] for s in detalle["soportes_monto"]}
    assert tipos == {"DOCUMENTO_OFERTA", "ACTA_APERTURA"}
    soporte = next(s for s in detalle["soportes_monto"] if s["tipo"] == "DOCUMENTO_OFERTA")
    r = _post(
        mundo,
        f"{E}/{exp['id']}/ofertas/{ofertas[0]['id']}/montos",
        "ua",
        mundo.company_a,
        {
            "moneda": "VES",
            "monto_sin_iva": "1000.00",
            "tributos": "160.00",
            "total_con_tributos": "1160.00",
            "soporte_tipo": "DOCUMENTO_OFERTA",
            "soporte_documento_id": soporte["documento_id"],
            "motivo": None,
            "version_anterior": None,
        },
        version=exp["version"],
    )
    assert r.status_code == 201
    monto = r.json()["monto"]
    assert monto["version"] == 1
    assert monto["suma_coincide"] is True
    assert monto["diferencia"] == "0.00"
    assert r.json()["monto_estado"] == "DECLARADO"
    exp_nuevo = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    assert exp_nuevo["version"] == exp["version"] + 1
    r = _post(
        mundo,
        f"{E}/{exp['id']}/ofertas/{ofertas[0]['id']}/montos",
        "ua",
        mundo.company_a,
        {
            "moneda": "VES",
            "monto_sin_iva": "1000.00",
            "tributos": "160.00",
            "total_con_tributos": "1170.00",
            "soporte_tipo": "ACTA_APERTURA",
            "soporte_documento_id": next(
                s for s in detalle["soportes_monto"] if s["tipo"] == "ACTA_APERTURA"
            )["documento_id"],
            "motivo": "Error de transcripción del total",
            "version_anterior": 1,
        },
        version=exp_nuevo["version"],
    )
    assert r.status_code == 201
    monto = r.json()["monto"]
    assert monto["version"] == 2
    assert monto["suma_coincide"] is False
    assert monto["diferencia"] == "10.00"
    assert monto["motivo"] == "Error de transcripción del total"
    historial = r.json()["montos_historial"]
    assert len(historial) == 2
    assert historial[0]["total_con_tributos"] == "1170.00"
    assert historial[1]["total_con_tributos"] == "1160.00"


def test_rechazos_no_escriben(mundo, gobierno, ocupacion):
    """Validaciones rechazan sin escribir y la corrección exige versión vigente."""
    exp, ofertas = _abiertas(mundo, ocupacion)
    detalle = mundo.get(
        f"{E}/{exp['id']}/ofertas/{ofertas[0]['id']}", "ua", mundo.company_a
    ).json()
    soporte = next(s for s in detalle["soportes_monto"] if s["tipo"] == "DOCUMENTO_OFERTA")
    soporte_otro = next(
        s
        for s in mundo.get(
            f"{E}/{exp['id']}/ofertas/{ofertas[1]['id']}", "ua", mundo.company_a
        ).json()["soportes_monto"]
        if s["tipo"] == "DOCUMENTO_OFERTA"
    )

    def post_monto(cuerpo, version):
        return _post(
            mundo,
            f"{E}/{exp['id']}/ofertas/{ofertas[0]['id']}/montos",
            "ua",
            mundo.company_a,
            cuerpo,
            version=version,
        )

    r = post_monto(
        {
            "moneda": "COP",
            "monto_sin_iva": "1000.00",
            "tributos": "160.00",
            "total_con_tributos": "1160.00",
            "soporte_tipo": "DOCUMENTO_OFERTA",
            "soporte_documento_id": soporte["documento_id"],
            "motivo": None,
            "version_anterior": None,
        },
        exp["version"],
    )
    assert r.status_code == 422
    assert 'field_errors' in r.json() and "moneda" in r.json()["field_errors"]

    r = post_monto(
        {
            "moneda": "VES",
            "monto_sin_iva": "1000.00",
            "tributos": "160.00",
            "total_con_tributos": "1160.00",
            "soporte_tipo": "DOCUMENTO_OFERTA",
            "soporte_documento_id": soporte_otro["documento_id"],
            "motivo": None,
            "version_anterior": None,
        },
        exp["version"],
    )
    assert r.status_code == 422
    assert "soporte_documento_id" in r.json()["field_errors"]

    r = post_monto(
        {
            "moneda": "VES",
            "monto_sin_iva": 1000.0,
            "tributos": "160.00",
            "total_con_tributos": "1160.00",
            "soporte_tipo": "DOCUMENTO_OFERTA",
            "soporte_documento_id": soporte["documento_id"],
            "motivo": None,
            "version_anterior": None,
        },
        exp["version"],
    )
    assert r.status_code == 422

    r = post_monto(
        {
            "moneda": "VES",
            "monto_sin_iva": "1000.00",
            "tributos": "160.00",
            "total_con_tributos": "0",
            "soporte_tipo": "DOCUMENTO_OFERTA",
            "soporte_documento_id": soporte["documento_id"],
            "motivo": None,
            "version_anterior": None,
        },
        exp["version"],
    )
    assert r.status_code == 422

    r = post_monto(
        {
            "moneda": "VES",
            "monto_sin_iva": "1000.00",
            "tributos": "-1",
            "total_con_tributos": "1160.00",
            "soporte_tipo": "DOCUMENTO_OFERTA",
            "soporte_documento_id": soporte["documento_id"],
            "motivo": None,
            "version_anterior": None,
        },
        exp["version"],
    )
    assert r.status_code == 422

    r = _post(
        mundo,
        f"{E}/{exp['id']}/ofertas/{ofertas[0]['id']}/montos",
        "ua",
        mundo.company_a,
        {
            "moneda": "VES",
            "monto_sin_iva": "1000.00",
            "tributos": "160.00",
            "total_con_tributos": "1160.00",
            "soporte_tipo": "DOCUMENTO_OFERTA",
            "soporte_documento_id": soporte["documento_id"],
            "motivo": None,
            "version_anterior": None,
        },
        version=None,
    )
    assert r.status_code == 428

    r = post_monto(
        {
            "moneda": "VES",
            "monto_sin_iva": "1000.00",
            "tributos": "160.00",
            "total_con_tributos": "1160.00",
            "soporte_tipo": "DOCUMENTO_OFERTA",
            "soporte_documento_id": soporte["documento_id"],
            "motivo": None,
            "version_anterior": 5,
        },
        exp["version"],
    )
    assert r.status_code == 409
    assert "GOV_OFFER_AMOUNT_STALE" in r.text

    det = mundo.get(f"{E}/{exp['id']}/ofertas/{ofertas[0]['id']}", "ua", mundo.company_a).json()
    assert det["monto_estado"] == "NO_DECLARADO"
    assert det["montos_historial"] == []

    r = post_monto(
        {
            "moneda": "VES",
            "monto_sin_iva": "1000.00",
            "tributos": "160.00",
            "total_con_tributos": "1160.00",
            "soporte_tipo": "DOCUMENTO_OFERTA",
            "soporte_documento_id": soporte["documento_id"],
            "motivo": None,
            "version_anterior": None,
        },
        exp["version"],
    )
    assert r.status_code == 201
    exp_nuevo = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()

    r = post_monto(
        {
            "moneda": "VES",
            "monto_sin_iva": "1000.00",
            "tributos": "160.00",
            "total_con_tributos": "1160.00",
            "soporte_tipo": "DOCUMENTO_OFERTA",
            "soporte_documento_id": soporte["documento_id"],
            "motivo": "corto",
            "version_anterior": 1,
        },
        exp_nuevo["version"],
    )
    assert r.status_code == 422
    assert "motivo" in r.json()["field_errors"]

    r = post_monto(
        {
            "moneda": "VES",
            "monto_sin_iva": "1000.00",
            "tributos": "160.00",
            "total_con_tributos": "1160.00",
            "soporte_tipo": "DOCUMENTO_OFERTA",
            "soporte_documento_id": soporte["documento_id"],
            "motivo": "Corrección del monto declarado",
            "version_anterior": 7,
        },
        exp_nuevo["version"],
    )
    assert r.status_code == 409
    assert "GOV_OFFER_AMOUNT_STALE" in r.text

    r = post_monto(
        {
            "moneda": "VES",
            "monto_sin_iva": "1000.00",
            "tributos": "160.00",
            "total_con_tributos": "1160.00",
            "soporte_tipo": "DOCUMENTO_OFERTA",
            "soporte_documento_id": soporte["documento_id"],
            "motivo": "Corrección del monto declarado",
            "version_anterior": 1,
        },
        exp["version"],
    )
    assert r.status_code == 409
    assert "GOV_PROCUREMENT_FILE_STALE" in r.text

    det = mundo.get(f"{E}/{exp['id']}/ofertas/{ofertas[0]['id']}", "ua", mundo.company_a).json()
    assert len(det["montos_historial"]) == 1


def test_calificacion_no_aplica(mundo, gobierno, ocupacion):
    """Una oferta de calificación no admite monto de oferta."""
    exp, comision = _preparar(mundo, ocupacion)
    matriz = _crear_matriz(mundo, exp)
    estado, matriz_version, criterios = _crear_criterios_contrato(mundo, exp, matriz)
    r = _post(
        mundo,
        f"{E}/{exp['id']}/evaluacion/matriz/bloquear",
        "ua",
        mundo.company_a,
        {},
        version=matriz_version,
    )
    assert r.status_code == 200
    doc_id = _doc_real(mundo, mundo.company_a, None, b"calificacion", "cal.pdf")
    r = mundo.post(
        f"/documentos/{doc_id}/vinculos",
        "ua",
        mundo.company_a,
        {"resource_type": "GovernmentProcurementFile", "resource_id": exp["id"]},
    )
    assert r.status_code == 200
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    oferta = _recibir(
        mundo, exp, "ua", mundo.company_a, [doc_id], tipo_sobre="CALIFICACION"
    )
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    estado_apertura, exp = _abrir_ofertas(mundo, exp, comision, [oferta])
    r = mundo.get(f"{E}/{exp['id']}/ofertas/{oferta['id']}", "ua", mundo.company_a)
    assert r.status_code == 200
    assert r.json()["monto_estado"] == "NO_APLICA"
    r = _post(
        mundo,
        f"{E}/{exp['id']}/ofertas/{oferta['id']}/montos",
        "ua",
        mundo.company_a,
        {
            "moneda": "VES",
            "monto_sin_iva": "1000.00",
            "tributos": "160.00",
            "total_con_tributos": "1160.00",
            "soporte_tipo": "ACTA_APERTURA",
            "soporte_documento_id": doc_id,
            "motivo": None,
            "version_anterior": None,
        },
        version=exp["version"],
    )
    assert r.status_code == 422
    assert "GOV_OFFER_AMOUNT_NOT_APPLICABLE" in r.text


def test_cerrado_tras_evaluacion(mundo, gobierno, ocupacion):
    """No se puede declarar monto tras evaluación concluida."""
    exp, comision, ofertas = evaluacion_concluida(mundo, ocupacion, n=1)
    r = mundo.get(f"{E}/{exp['id']}/ofertas/{ofertas[0]['id']}", "ua", mundo.company_a)
    assert r.status_code == 200
    assert "La evaluación está concluida" in r.json()["monto_bloqueo"]
    soporte = next(s for s in r.json()["soportes_monto"] if s["tipo"] == "ACTA_APERTURA")
    r = _post(
        mundo,
        f"{E}/{exp['id']}/ofertas/{ofertas[0]['id']}/montos",
        "ua",
        mundo.company_a,
        {
            "moneda": "VES",
            "monto_sin_iva": "1000.00",
            "tributos": "160.00",
            "total_con_tributos": "1160.00",
            "soporte_tipo": "ACTA_APERTURA",
            "soporte_documento_id": soporte["documento_id"],
            "motivo": None,
            "version_anterior": None,
        },
        version=exp["version"],
    )
    assert r.status_code == 409
    assert "GOV_OFFER_AMOUNT_CLOSED" in r.text


def test_sin_sello_desde_recepcion(mundo, gobierno, ocupacion):
    """Una oferta no confidencial permite declarar sin apertura."""
    exp = _crear(mundo, ocupacion)
    doc_id = _doc_real(mundo, mundo.company_a, None, b"sin-sello", "sin-sello.pdf")
    r = mundo.post(
        f"/documentos/{doc_id}/vinculos",
        "ua",
        mundo.company_a,
        {"resource_type": "GovernmentProcurementFile", "resource_id": exp["id"]},
    )
    assert r.status_code == 200
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    r = _patch(
        mundo,
        exp,
        modalidad_declarada="CONSULTA_PRECIOS",
        modalidad_fundamento="fundamento",
        modalidad_fuente="fuente",
    )
    assert r.status_code == 200
    exp = r.json()
    oferta = _recibir(
        mundo,
        exp,
        "ua",
        mundo.company_a,
        [doc_id],
        confidencial=False,
        motivo_sin_sello="No se sella porque es consulta",
    )
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    r = mundo.get(f"{E}/{exp['id']}/ofertas/{oferta['id']}", "ua", mundo.company_a)
    assert r.status_code == 200
    det = r.json()
    assert det["monto_estado"] == "NO_DECLARADO"
    assert [s["tipo"] for s in det["soportes_monto"]] == ["DOCUMENTO_OFERTA"]
    soporte = det["soportes_monto"][0]
    r = _post(
        mundo,
        f"{E}/{exp['id']}/ofertas/{oferta['id']}/montos",
        "ua",
        mundo.company_a,
        {
            "moneda": "VES",
            "monto_sin_iva": "1000.00",
            "tributos": "160.00",
            "total_con_tributos": "1160.00",
            "soporte_tipo": "DOCUMENTO_OFERTA",
            "soporte_documento_id": soporte["documento_id"],
            "motivo": None,
            "version_anterior": None,
        },
        version=exp["version"],
    )
    assert r.status_code == 201
    assert r.json()["monto_estado"] == "DECLARADO"


def test_aislamiento(mundo, gobierno, ocupacion):
    """Otra empresa no puede leer ni declarar el monto."""
    exp, ofertas = _abiertas(mundo, ocupacion)
    r = mundo.get(f"{E}/{exp['id']}/ofertas/{ofertas[0]['id']}", "ub", mundo.company_b)
    assert r.status_code == 404
    r = _post(
        mundo,
        f"{E}/{exp['id']}/ofertas/{ofertas[0]['id']}/montos",
        "ub",
        mundo.company_b,
        {
            "moneda": "VES",
            "monto_sin_iva": "1000.00",
            "tributos": "160.00",
            "total_con_tributos": "1160.00",
            "soporte_tipo": "DOCUMENTO_OFERTA",
            "soporte_documento_id": "sin-soporte",
            "motivo": None,
            "version_anterior": None,
        },
        version=exp["version"],
    )
    assert r.status_code == 404
    r = mundo.get(f"{E}/{exp['id']}/ofertas/{ofertas[0]['id']}", "ua", mundo.company_a)
    assert r.status_code == 200
    assert r.json()["monto_estado"] == "NO_DECLARADO"


def test_permiso(mundo, gobierno, ocupacion):
    """Sin permiso de amount no se puede declarar."""
    exp, ofertas = _abiertas(mundo, ocupacion)
    cuenta_con_permisos(
        mundo,
        "solo_ofertas_ver",
        [("gobierno_ofertas", "view"), ("gobierno_expedientes", "view")],
    )
    r = _post(
        mundo,
        f"{E}/{exp['id']}/ofertas/{ofertas[0]['id']}/montos",
        "solo_ofertas_ver",
        mundo.company_a,
        {
            "moneda": "VES",
            "monto_sin_iva": "1000.00",
            "tributos": "160.00",
            "total_con_tributos": "1160.00",
            "soporte_tipo": "DOCUMENTO_OFERTA",
            "soporte_documento_id": "sin-soporte",
            "motivo": None,
            "version_anterior": None,
        },
        version=exp["version"],
    )
    assert r.status_code == 403
    r = mundo.get(f"{E}/{exp['id']}/ofertas", "solo_ofertas_ver", mundo.company_a)
    assert r.status_code == 200


def test_carrera_de_declaraciones(mundo, gobierno, ocupacion):
    """Dos declaraciones concurrentes con la misma versión dejan una fila."""
    exp, ofertas = _abiertas(mundo, ocupacion)
    oferta = ofertas[0]
    det = mundo.get(f"{E}/{exp['id']}/ofertas/{oferta['id']}", "ua", mundo.company_a).json()
    soporte = next(s for s in det["soportes_monto"] if s["tipo"] == "DOCUMENTO_OFERTA")
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    with mundo.factory() as db:
        uid = db.scalar(select(User.id).where(User.username == "ua"))

    def _ctx(s):
        return CompanyContext(
            tenant_id=mundo.t1,
            company_id=mundo.company_a,
            company=s.get(Company, mundo.company_a),
            user_id=uid,
        )

    def primero(s):
        entrada = MontoEntrada.model_validate(
            {
                "moneda": "VES",
                "monto_sin_iva": "1000.00",
                "tributos": "160.00",
                "total_con_tributos": "1160.00",
                "soporte_tipo": "DOCUMENTO_OFERTA",
                "soporte_documento_id": soporte["documento_id"],
                "motivo": None,
                "version_anterior": None,
            }
        )
        declarar_monto(s, _ctx(s), exp["id"], oferta["id"], entrada, exp["version"])

    def segundo(s):
        entrada = MontoEntrada.model_validate(
            {
                "moneda": "VES",
                "monto_sin_iva": "1000.00",
                "tributos": "160.00",
                "total_con_tributos": "1160.00",
                "soporte_tipo": "DOCUMENTO_OFERTA",
                "soporte_documento_id": soporte["documento_id"],
                "motivo": None,
                "version_anterior": None,
            }
        )
        declarar_monto(s, _ctx(s), exp["id"], oferta["id"], entrada, exp["version"])

    r1, r2 = carrera(mundo.factory, primero, segundo)
    assert isinstance(r2, ConflictError)
    with mundo.factory() as db:
        rows = db.query(GovernmentProcurementOfferAmount).filter_by(offer_id=oferta["id"]).all()
        assert len(rows) == 1


def test_inmutable_en_postgresql(mundo, gobierno, ocupacion):
    """UPDATE y DELETE sobre montos fallan en PostgreSQL."""
    exp, ofertas = _abiertas(mundo, ocupacion)
    oferta = ofertas[0]
    det = mundo.get(f"{E}/{exp['id']}/ofertas/{oferta['id']}", "ua", mundo.company_a).json()
    soporte = next(s for s in det["soportes_monto"] if s["tipo"] == "DOCUMENTO_OFERTA")
    r = _post(
        mundo,
        f"{E}/{exp['id']}/ofertas/{oferta['id']}/montos",
        "ua",
        mundo.company_a,
        {
            "moneda": "VES",
            "monto_sin_iva": "1000.00",
            "tributos": "160.00",
            "total_con_tributos": "1160.00",
            "soporte_tipo": "DOCUMENTO_OFERTA",
            "soporte_documento_id": soporte["documento_id"],
            "motivo": None,
            "version_anterior": None,
        },
        version=exp["version"],
    )
    assert r.status_code == 201
    with mundo.factory() as db:
        with pytest.raises(DBAPIError) as exc_info:
            db.execute(
                text("UPDATE gov_procurement_offer_amounts SET motivo = 'x' WHERE offer_id = :o"),
                {"o": oferta["id"]},
            )
        assert "GOV_OFFER_AMOUNT_IMMUTABLE" in str(exc_info.value)
        db.rollback()
        with pytest.raises(DBAPIError) as exc_info:
            db.execute(
                text("DELETE FROM gov_procurement_offer_amounts WHERE offer_id = :o"),
                {"o": oferta["id"]},
            )
        assert "GOV_OFFER_AMOUNT_IMMUTABLE" in str(exc_info.value)
        db.rollback()


def test_cronologia_y_auditoria_sin_importes(mundo, gobierno, ocupacion):
    """La cronología y auditoría jamás registran importes."""
    exp, ofertas = _abiertas(mundo, ocupacion)
    oferta = ofertas[0]
    det = mundo.get(f"{E}/{exp['id']}/ofertas/{oferta['id']}", "ua", mundo.company_a).json()
    soporte = next(s for s in det["soportes_monto"] if s["tipo"] == "DOCUMENTO_OFERTA")
    r = _post(
        mundo,
        f"{E}/{exp['id']}/ofertas/{oferta['id']}/montos",
        "ua",
        mundo.company_a,
        {
            "moneda": "VES",
            "monto_sin_iva": "1000.00",
            "tributos": "160.00",
            "total_con_tributos": "1160.00",
            "soporte_tipo": "DOCUMENTO_OFERTA",
            "soporte_documento_id": soporte["documento_id"],
            "motivo": None,
            "version_anterior": None,
        },
        version=exp["version"],
    )
    assert r.status_code == 201
    exp_nuevo = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    r = _post(
        mundo,
        f"{E}/{exp['id']}/ofertas/{oferta['id']}/montos",
        "ua",
        mundo.company_a,
        {
            "moneda": "VES",
            "monto_sin_iva": "1000.00",
            "tributos": "160.00",
            "total_con_tributos": "1170.00",
            "soporte_tipo": "ACTA_APERTURA",
            "soporte_documento_id": next(
                s for s in det["soportes_monto"] if s["tipo"] == "ACTA_APERTURA"
            )["documento_id"],
            "motivo": "Corrección del monto declarado",
            "version_anterior": 1,
        },
        version=exp_nuevo["version"],
    )
    assert r.status_code == 201
    with mundo.factory() as db:
        rows = (
            db.query(GovernmentProcurementFileEvent)
            .filter(
                GovernmentProcurementFileEvent.file_id == exp["id"],
                GovernmentProcurementFileEvent.titulo.like("Monto %"),
            )
            .order_by(GovernmentProcurementFileEvent.secuencia)
            .all()
        )
        assert [row.titulo for row in rows] == ["Monto declarado R-0001", "Monto corregido R-0001"]
        assert all("1160" not in row.titulo + (row.detalle or "") for row in rows)
        assert all("1000" not in row.titulo + (row.detalle or "") for row in rows)
        eventos = (
            db.query(AuditEvent)
            .filter(
                AuditEvent.entity_id == exp["id"],
                AuditEvent.action.in_(
                    [
                        "GOV_PROCUREMENT_OFFER_AMOUNT_DECLARED",
                        "GOV_PROCUREMENT_OFFER_AMOUNT_CORRECTED",
                    ]
                ),
            )
            .all()
        )
        assert len(eventos) == 2
        assert all("1160" not in json.dumps(e.after) for e in eventos)
        assert all("1000" not in json.dumps(e.after) for e in eventos)


def test_consumidores_rep03_y_proc08(mundo, gobierno, ocupacion):
    """REP-03 y PROC-08 exponen el monto declarado."""
    exp, ofertas, acto = _adjudicado(mundo, ocupacion)
    _insertar_monto(mundo, ofertas[0]["id"], "1000.00", "160.00", "1160.00")
    r = mundo.get("/gobierno/contrataciones/reporte", "ua", mundo.company_a)
    assert r.status_code == 200
    data = r.json()
    assert data["monto"]["disponible"] is True
    assert data["monto"]["por_moneda"] == [
        {
            "moneda": "VES",
            "total_con_tributos": "1160.00",
            "monto_sin_iva": "1000.00",
            "adjudicaciones": 1,
        }
    ]
    assert data["monto"]["adjudicaciones_con_monto"] == 1
    r = mundo.get("/gobierno/contrataciones/reporte.csv", "ua", mundo.company_a)
    assert r.status_code == 200
    assert "Monto declarado de las ofertas adjudicadas" in r.text
    r = mundo.get(f"{E}/{exp['id']}/decision", "ua", mundo.company_a)
    assert r.status_code == 200
    items = {item["id"]: item for item in r.json()["ofertas"]}
    assert items[ofertas[0]["id"]]["monto"]["total_con_tributos"] == "1160.00"
    assert items[ofertas[1]["id"]]["monto"] is None


def test_proc10_bandas_de_la_oferta(mundo, gobierno, ocupacion):
    """PROC-10 evalúa la banda de la oferta según el monto declarado."""
    exp, ofertas, acto = _adjudicado(mundo, ocupacion)
    for oferta in ofertas:
        _insertar_monto(mundo, oferta["id"], "1000.00", "160.00", "1160.00")
    doc_id, exp = _doc(mundo, exp, "requisito.pdf")
    r = _post_g(
        mundo,
        exp,
        "/requisitos",
        {
            "regla_codigo": "MANT-OFERTA-1",
            "porcentaje": "2.50",
            "fundamento": "Pliego, cláusula 12",
            "documento_id": doc_id,
        },
    )
    assert r.status_code == 201
    requisito = r.json()["requisitos"][0]
    emisores = []
    for i in range(3):
        emisor = _emisor(mundo, f"Emisor {i + 1}", f"J-{uuid4().hex[:8]}")
        emisores.append(emisor)
    montos = ["29.00", "25.00", "24.99"]
    for i, oferta in enumerate(ofertas):
        doc_id, exp = _doc(mundo, exp, f"garantia-{i + 1}.pdf")
        r = _post_g(
            mundo,
            exp,
            "",
            {
                "requisito_id": requisito["id"],
                "oferta_id": oferta["id"],
                "emisor_id": emisores[i]["id"],
                "referencia_emisor": f"FZ-000{i + 1}",
                "monto": montos[i],
                "moneda": "VES",
                "fecha_emision": HOY.isoformat(),
                "vigente_desde": HOY.isoformat(),
                "vigente_hasta": (HOY + timedelta(days=30)).isoformat(),
                "documento_id": doc_id,
            },
        )
        assert r.status_code == 201
        estado = r.json()
        assert "garantias" in estado
        criterios = {c["criterio"]: c for c in _gar(estado, f"GAR-0{i + 1}")["criterios"]}
        if i == 0:
            assert criterios["Monto"]["resultado"] == "CUMPLE"
            assert criterios["Moneda"]["resultado"] == "CUMPLE"
        elif i == 1:
            assert criterios["Monto"]["resultado"] == "NO_EVALUABLE"
            assert "la regla no precisa la base" in criterios["Monto"]["detalle"]
        else:
            assert criterios["Monto"]["resultado"] == "NO_CUMPLE"
