from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.core.company_context import CompanyContext
from app.core.errors import ConflictError
from app.modules.documents.service import documento_sellado
from app.modules.government.models import (
    GovernmentBudgetCertificate,
    GovernmentPosition,
    GovernmentPositionCompetency,
    GovernmentPositionVersion,
    GovernmentProcurementFile,
    GovernmentProcurementFileEvent,
    GovernmentProcurementOffer,
)
from app.modules.government.service_contratos import crear, formalizar
from app.modules.identity_access.mfa_policy import SENSITIVE, classify
from app.modules.identity_access.models import User
from app.modules.organization.models import Company
from app.modules.setup.api import CATALOGO_DE_PERMISOS
from tests.concurrency import carrera
from tests.org04_ayudantes import ANIO, _codigo, nuevo_cargo
from tests.org06_guarda import cuenta_con_permisos
from tests.proc08_ayudantes import acto_decision, cargo_contrataciones
from tests.test_gov_bud01_ejercicio import ONLY_PG, P, _aprobar, _completo
from tests.test_gov_ctl01_reglas import cerrar_regla, eventos, regla_vigente
from tests.test_gov_ctl06_hallazgos import _post
from tests.test_gov_proc03_expedientes import E
from tests.test_gov_proc06_montos import _insertar_monto
from tests.test_gov_proc10_garantias import HOY, _adjudicado, _doc, _emisor, _exp, _post_g

pytest_plugins = (
    "tests.conftest_multicompany",
    "tests.test_gov_ctl06_hallazgos",
    "tests.org04_ayudantes",
)

C = "/gobierno/contratos"

_PRESUPUESTO: dict[int, dict] = {}


def _presupuesto(mundo) -> dict:
    if id(mundo) in _PRESUPUESTO:
        return _PRESUPUESTO[id(mundo)]

    detalle = _completo(mundo, ANIO)
    r = _post(
        mundo,
        f"{P}/{detalle['id']}/fuentes",
        "ua",
        mundo.company_a,
        {
            "codigo": "F01",
            "denominacion": "Ingresos propios",
            "procedencia": "Ordenanza municipal de ingresos",
        },
        version=detalle["version"],
    )
    assert r.status_code == 201
    detalle["version"] = r.json()["version"]

    partidas_resp = mundo.get(
        f"{P}/{detalle['id']}/clasificador/partidas", "ua", mundo.company_a
    )
    partidas = {
        item["codigo"]: item["id"] for item in partidas_resp.json()["items"]
    }
    assert "301" in partidas
    assert "401.01" in partidas

    fuente_items = mundo.get(
        f"{P}/{detalle['id']}/fuentes", "ua", mundo.company_a
    ).json()["items"]
    fuente_id = next(item["id"] for item in fuente_items if item["codigo"] == "F01")

    r = _post(
        mundo,
        f"{P}/{detalle['id']}/presupuesto-aprobado/ingresos",
        "ua",
        mundo.company_a,
        {"partida_id": partidas["301"], "monto": "10000.00"},
        version=detalle["version"],
    )
    assert r.status_code == 201
    detalle["version"] = r.json()["version"]

    detalle_resp = mundo.get(f"{P}/{detalle['id']}", "ua", mundo.company_a).json()
    categoria = next(
        item
        for item in detalle_resp["categorias"]
        if item["codigo_completo"] == "01.02"
    )

    r = _post(
        mundo,
        f"{P}/{detalle['id']}/presupuesto-aprobado/creditos",
        "ua",
        mundo.company_a,
        {
            "categoria_id": categoria["id"],
            "partida_id": partidas["401.01"],
            "fuente_id": fuente_id,
            "monto": "10000.00",
        },
        version=detalle["version"],
    )
    assert r.status_code == 201
    detalle["version"] = r.json()["version"]

    resp_json = r.json()
    credito_id = next(
        c["id"]
        for c in resp_json.get("creditos", [])
        if c.get("partida", {}).get("codigo") == "401.01"
    )

    _aprobar(mundo, mundo.get(f"{P}/{detalle['id']}", "ua", mundo.company_a).json())

    resultado = {"year_id": detalle["id"], "credito_id": credito_id}
    _PRESUPUESTO[id(mundo)] = resultado
    return resultado


def _cdp(
    mundo,
    ocupacion,
    monto: str,
    moneda: str = "USD",
    estado: str = "VIGENTE",
    expediente_id: str | None = None,
) -> str:
    pres = _presupuesto(mundo)
    cargo_id = nuevo_cargo(mundo, ocupacion)
    with mundo.factory() as db:
        uid = db.scalar(select(User.id).where(User.username == "ua"))
        numero = (
            db.scalar(
                select(GovernmentBudgetCertificate.numero).where(
                    GovernmentBudgetCertificate.company_id == mundo.company_a,
                    GovernmentBudgetCertificate.year_id == pres["year_id"],
                ).order_by(GovernmentBudgetCertificate.numero.desc()).limit(1)
            )
            or 0
        ) + 1
        cert = GovernmentBudgetCertificate(
            year_id=pres["year_id"],
            company_id=mundo.company_a,
            credit_id=pres["credito_id"],
            numero=numero,
            codigo=f"CDP-{ANIO}-{numero:04d}",
            estado=estado,
            monto=Decimal(monto),
            saldo_antes=Decimal(monto),
            saldo_despues=Decimal("0.00"),
            moneda=moneda,
            fecha=HOY,
            concepto="Adquisición de prueba",
            expediente_referencia="EXP-PRUEBA",
            procurement_file_id=expediente_id,
            firmante_cargo_id=cargo_id,
            firmante_cargo_codigo="C",
            firmante_cargo_nombre="Cargo",
            firmante_unidad="Unidad",
            firmante_funcionario_id=None,
            firmante_funcionario_nombre=None,
            emitida_por=uid,
            emitida_en=datetime.now(UTC),
            snapshot={},
            huella="0" * 64,
            documento_storage_key="cdp/prueba.pdf",
            documento_sha256="0" * 64,
            documento_tamano=1,
            documento_nombre="cdp.pdf",
        )
        db.add(cert)
        db.commit()
        return str(cert.id)


def _anular_cdp(mundo, cdp_id: str) -> None:
    with mundo.factory() as db:
        cert = db.get(GovernmentBudgetCertificate, cdp_id)
        uid = db.scalar(select(User.id).where(User.username == "ua"))
        cert.estado = "ANULADA"
        cert.anulada_por = uid
        cert.anulada_en = datetime.now(UTC)
        cert.motivo_anulacion = "Anulación de prueba"
        db.commit()


def _cargo_firmante(
    mundo,
    ocupacion,
    tipo_limite: str,
    monto: str | None = None,
    moneda: str | None = None,
) -> str:
    with mundo.factory() as db:
        cargo = GovernmentPosition(
            company_id=mundo.company_a,
            structure_id=ocupacion["estructura"],
            unit_id=ocupacion["unidad_raiz"],
            code=_codigo("C"),
            name=f"Firmante {_codigo('N')}",
            status="VIGENTE",
            valid_from=datetime(2024, 1, 1),
            activated_at=datetime.now(UTC),
            version=1,
        )
        db.add(cargo)
        db.flush()
        db.add(
            GovernmentPositionCompetency(
                position_id=cargo.id,
                company_id=mundo.company_a,
                action="FIRMAR",
                subject="CONTRATACIONES",
                limit_type=tipo_limite,
                limit_amount=Decimal(monto) if monto else None,
                limit_currency=moneda,
                basis="Fundamento de prueba",
            )
        )
        db.add(
            GovernmentPositionVersion(
                position_id=cargo.id,
                structure_id=ocupacion["estructura"],
                company_id=mundo.company_a,
                version=1,
                status="VIGENTE",
                snapshot={
                    "competencias": [
                        {
                            "accion": "FIRMAR",
                            "materia": "CONTRATACIONES",
                            "tipo_limite": tipo_limite,
                            "monto": monto,
                            "moneda": moneda,
                        }
                    ]
                },
                reason=None,
                actor_id=None,
            )
        )
        db.commit()
        return str(cargo.id)


def _mundo_contrato(mundo, ocupacion, total: str = "50000.00", moneda: str = "USD") -> dict:
    exp, ofertas, acto = _adjudicado(mundo, ocupacion)
    total_decimal = Decimal(total)
    neto = (total_decimal * Decimal("100") / Decimal("116")).quantize(Decimal("0.01"))
    tributos = (total_decimal - neto).quantize(Decimal("0.01"))
    _insertar_monto(
        mundo,
        ofertas[0]["id"],
        f"{neto:.2f}",
        f"{tributos:.2f}",
        total,
        moneda=moneda,
    )
    return {"exp": exp, "ofertas": ofertas, "acto": acto}


def _crear(mundo, exp_id, usuario: str = "ua", empresa=None) -> Any:
    return _post(mundo, C, usuario, empresa or mundo.company_a, {"expediente_id": exp_id})


def _ficha(mundo, cid: str) -> Any:
    return mundo.get(f"{C}/{cid}", "ua", mundo.company_a)


def _patch(mundo, cid: str, cuerpo: dict, version: int, usuario: str = "ua") -> Any:
    headers = mundo.como(usuario, mundo.company_a)
    headers["If-Match"] = str(version)
    return mundo.client.patch(f"/api/v1{C}/{cid}", headers=headers, json=cuerpo)


def _put(mundo, cid: str, sufijo: str, cuerpo: dict, version: int, usuario: str = "ua") -> Any:
    headers = mundo.como(usuario, mundo.company_a)
    headers["If-Match"] = str(version)
    return mundo.client.put(f"/api/v1{C}/{cid}{sufijo}", headers=headers, json=cuerpo)


def _preparado(mundo, ocupacion, cdp_montos=("30000.00", "20000.00")) -> dict:
    m = _mundo_contrato(mundo, ocupacion)
    exp = m["exp"]
    ofertas = m["ofertas"]
    r = _crear(mundo, exp["id"])
    assert r.status_code == 201
    contrato = r.json()

    doc_id, exp_actualizado = _doc(mundo, exp, "documento-contrato")
    r = _patch(
        mundo,
        contrato["id"],
        {
            "tipo": "CONTRATO",
            "fecha_inicio": HOY.isoformat(),
            "fecha_fin": (HOY + timedelta(days=180)).isoformat(),
            "referencia_instrumento": "CT-INSTR-001",
            "documento_id": doc_id,
        },
        contrato["version"],
    )
    assert r.status_code == 200
    contrato = r.json()

    cdps = []
    for monto in cdp_montos:
        cdp_id = _cdp(mundo, ocupacion, monto, moneda="USD", expediente_id=exp["id"])
        cdps.append(cdp_id)

    r = _put(
        mundo,
        contrato["id"],
        "/cobertura",
        {
            "asignaciones": [
                {"certificado_id": cdp_id, "monto": monto}
                for cdp_id, monto in zip(cdps, cdp_montos, strict=True)
            ]
        },
        contrato["version"],
    )
    assert r.status_code == 200
    contrato = r.json()

    return {"exp": exp, "ofertas": ofertas, "contrato": contrato, "cdps": cdps}


def _garantia_fiel(mundo, exp: dict, oferta: dict) -> str:
    emisor = _emisor(mundo, "Emisor Garantía", f"J-{uuid4().hex[:8]}")
    d1, exp = _doc(mundo, exp, f"req-{uuid4().hex[:6]}")
    r = _post_g(mundo, exp, "/requisitos", {"regla_codigo": "FIEL-1", "porcentaje": "20", "fundamento": "Pliego, cláusula 20", "documento_id": d1})
    assert r.status_code == 201, r.text
    requisito = r.json()["requisitos"][0]
    d2, exp = _doc(mundo, exp, f"gar-{uuid4().hex[:6]}")
    r = _post_g(mundo, exp, "", {"requisito_id": requisito["id"], "oferta_id": oferta["id"], "emisor_id": emisor["id"], "referencia_emisor": "FC-0001", "monto": "10000.00", "moneda": "USD", "fecha_emision": HOY.isoformat(), "vigente_desde": HOY.isoformat(), "vigente_hasta": (HOY + timedelta(days=365)).isoformat(), "documento_id": d2})
    assert r.status_code == 201, r.text
    garantia = next(g for g in r.json()["garantias"] if g["referencia"] == "GAR-01")
    return garantia["id"]


@pytest.mark.usefixtures("gobierno")
@ONLY_PG
class TestGovCnt01Contratos:
    def test_vector_a_formaliza_el_contrato(self, mundo, gobierno, ocupacion):
        m = _mundo_contrato(mundo, ocupacion)
        exp = m["exp"]
        ofertas = m["ofertas"]
        r = _crear(mundo, exp["id"])
        assert r.status_code == 201
        contrato = r.json()
        assert contrato["estado"] == "BORRADOR"
        assert contrato["codigo"] is None
        assert contrato["monto"] == "50000.00"
        assert contrato["moneda"] == "USD"

        with mundo.factory() as db:
            oferta_db = db.get(GovernmentProcurementOffer, ofertas[0]["id"])
            exp_db = db.get(GovernmentProcurementFile, exp["id"])
            assert contrato["contratista"]["nombre"] == oferta_db.oferente_nombre
            assert contrato["contratista"]["documento"] == oferta_db.oferente_documento
            assert contrato["objeto"] == exp_db.objeto
        assert contrato["pendientes"] != []
        assert contrato["puede_formalizar"] is False

        doc_id, _ = _doc(mundo, exp, "documento-contrato")
        r = _patch(
            mundo,
            contrato["id"],
            {
                "tipo": "CONTRATO",
                "fecha_inicio": HOY.isoformat(),
                "fecha_fin": (HOY + timedelta(days=180)).isoformat(),
                "referencia_instrumento": "CT-INSTR-001",
                "documento_id": doc_id,
            },
            contrato["version"],
        )
        assert r.status_code == 200
        contrato = r.json()

        cdp1 = _cdp(mundo, ocupacion, "30000.00", moneda="USD", expediente_id=exp["id"])
        cdp2 = _cdp(mundo, ocupacion, "20000.00", moneda="USD", expediente_id=exp["id"])
        r = _put(
            mundo,
            contrato["id"],
            "/cobertura",
            {
                "asignaciones": [
                    {"certificado_id": cdp1, "monto": "30000.00"},
                    {"certificado_id": cdp2, "monto": "20000.00"},
                ]
            },
            contrato["version"],
        )
        assert r.status_code == 200
        contrato = r.json()
        assert contrato["cobertura"]["completa"] is True

        garantia_id = _garantia_fiel(mundo, exp, ofertas[0])
        ficha = _ficha(mundo, contrato["id"]).json()
        assert any(
            g["instrumento_id"] == garantia_id
            for g in ficha["opciones"]["garantias_elegibles"]
        )
        r = _put(
            mundo,
            contrato["id"],
            "/garantias",
            {"instrumento_ids": [garantia_id]},
            ficha["version"],
        )
        assert r.status_code == 200
        contrato = r.json()
        assert len(contrato["garantias"]) == 1

        firmante = _cargo_firmante(mundo, ocupacion, "SIN_LIMITE")
        ficha = _ficha(mundo, contrato["id"]).json()
        assert any(
            f["cargo_id"] == firmante and f["control"]["permite"] is True
            for f in ficha["opciones"]["firmantes"]
        )

        r = _post(
            mundo,
            f"{C}/{contrato['id']}/formalizar",
            "ua",
            mundo.company_a,
            {"firmante_cargo_id": firmante},
            version=ficha["version"],
        )
        assert r.status_code == 200
        contrato = r.json()
        assert contrato["estado"] == "FORMALIZADO"
        assert contrato["codigo"].startswith("CT-")
        assert "-" in contrato["codigo"]
        assert len(contrato["huella"]) == 64
        assert contrato["firmante"]["cargo"] != ""
        assert contrato["opciones"] is None
        assert contrato["pendientes"] == []

        with mundo.factory() as db:
            cert = db.get(GovernmentBudgetCertificate, cdp1)
            assert cert.estado == "VIGENTE"
            assert str(cert.monto) == "30000.00"
            assert documento_sellado(db, doc_id) is True
            assert (
                db.scalar(
                    select(GovernmentProcurementFileEvent).where(
                        GovernmentProcurementFileEvent.file_id == exp["id"],
                        GovernmentProcurementFileEvent.clase == "CONTRATO",
                    )
                )
                is not None
            )
        assert len(eventos(mundo, "GOV_CONTRACT_FORMALIZED", exp["id"])) == 1
        assert "monto" not in eventos(mundo, "GOV_CONTRACT_FORMALIZED", exp["id"])[0].after
        assert len(eventos(mundo, "GOV_CONTRACT_DRAFT_CREATED", exp["id"])) == 1

        r = _post(
            mundo,
            f"{C}/{contrato['id']}/formalizar",
            "ua",
            mundo.company_a,
            {"firmante_cargo_id": firmante},
            version=contrato["version"],
        )
        assert r.status_code == 409
        assert r.json()["code"] == "GOV_CONTRACT_ALREADY_FORMALIZED"

        r = _patch(
            mundo,
            contrato["id"],
            {"referencia_instrumento": "OTRO"},
            contrato["version"],
        )
        assert r.status_code == 409
        assert r.json()["code"] == "GOV_CONTRACT_ALREADY_FORMALIZED"

        r = _crear(mundo, exp["id"])
        assert r.status_code == 409
        assert r.json()["code"] == "GOV_CONTRACT_ALREADY_EXISTS"

    def test_vector_b_adjudicacion_no_vigente(self, mundo, gobierno, ocupacion):
        prep = _preparado(mundo, ocupacion)
        exp = prep["exp"]
        contrato = prep["contrato"]

        dec_resp = mundo.get(f"{E}/{exp['id']}/decision", "ua", mundo.company_a).json()
        recomendacion_id = dec_resp["recomendacion_vigente"]["id"]
        cargo = cargo_contrataciones(mundo, ocupacion)
        acto = acto_decision(mundo, cargo)
        r = _post(
            mundo,
            f"{E}/{exp['id']}/decision/decisiones",
            "ua",
            mundo.company_a,
            {
                "resultado": "TERMINADA",
                "recomendacion_id": recomendacion_id,
                "acto_id": acto["id"],
                "motivacion": "Terminación del procedimiento",
            },
            version=_exp(mundo, exp)["version"],
        )
        assert r.status_code == 201

        ficha = _ficha(mundo, contrato["id"]).json()
        assert ficha["decision"]["vigente"] is False

        firmante = _cargo_firmante(mundo, ocupacion, "SIN_LIMITE")
        r = _post(
            mundo,
            f"{C}/{contrato['id']}/formalizar",
            "ua",
            mundo.company_a,
            {"firmante_cargo_id": firmante},
            version=ficha["version"],
        )
        assert r.status_code == 409
        assert r.json()["code"] == "GOV_CONTRACT_AWARD_NOT_CURRENT"

        r = _patch(
            mundo,
            contrato["id"],
            {"referencia_instrumento": "OTRO"},
            ficha["version"],
        )
        assert r.status_code == 409
        assert r.json()["code"] == "GOV_CONTRACT_AWARD_NOT_CURRENT"

        r = _crear(mundo, exp["id"])
        assert r.status_code == 409
        assert r.json()["code"] == "GOV_CONTRACT_AWARD_REQUIRED"

    def test_vector_c_el_monto_del_cliente_se_ignora(self, mundo, gobierno, ocupacion):
        m = _mundo_contrato(mundo, ocupacion)
        exp = m["exp"]
        r = _post(
            mundo,
            C,
            "ua",
            mundo.company_a,
            {
                "expediente_id": exp["id"],
                "monto": "40000.00",
                "moneda": "EUR",
                "contratista_nombre": "Otro",
            },
        )
        assert r.status_code == 201
        contrato = r.json()
        assert contrato["monto"] == "50000.00"
        assert contrato["moneda"] == "USD"

        with mundo.factory() as db:
            oferta = db.get(GovernmentProcurementOffer, m["ofertas"][0]["id"])
            assert contrato["contratista"]["nombre"] == oferta.oferente_nombre

        r = _patch(mundo, contrato["id"], {"monto": "40000.00"}, contrato["version"])
        assert r.status_code == 200
        assert r.json()["monto"] == "50000.00"

    def test_vector_d_cobertura_insuficiente(self, mundo, gobierno, ocupacion):
        prep = _preparado(mundo, ocupacion, cdp_montos=("40000.00",))
        contrato = prep["contrato"]
        firmante = _cargo_firmante(mundo, ocupacion, "SIN_LIMITE")
        r = _post(
            mundo,
            f"{C}/{contrato['id']}/formalizar",
            "ua",
            mundo.company_a,
            {"firmante_cargo_id": firmante},
            version=contrato["version"],
        )
        assert r.status_code == 409
        assert r.json()["code"] == "GOV_CONTRACT_COVERAGE_INSUFFICIENT"
        assert r.json()["details"]["cubierto"] == "40000.00"

        cdp_grande = _cdp(mundo, ocupacion, "60000.00", moneda="USD", expediente_id=prep["exp"]["id"])
        r = _put(
            mundo,
            contrato["id"],
            "/cobertura",
            {"asignaciones": [{"certificado_id": cdp_grande, "monto": "60000.00"}]},
            contrato["version"],
        )
        assert r.status_code == 422
        assert r.json()["code"] == "GOV_CONTRACT_INVALID"

        r = _put(
            mundo,
            contrato["id"],
            "/cobertura",
            {"asignaciones": [{"certificado_id": cdp_grande, "monto": "0"}]},
            contrato["version"],
        )
        assert r.status_code == 422

    def test_vector_e_cdp_anulada(self, mundo, gobierno, ocupacion):
        prep = _preparado(mundo, ocupacion)
        contrato = prep["contrato"]
        _anular_cdp(mundo, prep["cdps"][0])
        firmante = _cargo_firmante(mundo, ocupacion, "SIN_LIMITE")
        r = _post(
            mundo,
            f"{C}/{contrato['id']}/formalizar",
            "ua",
            mundo.company_a,
            {"firmante_cargo_id": firmante},
            version=contrato["version"],
        )
        assert r.status_code == 409
        assert r.json()["code"] == "GOV_CONTRACT_CERTIFICATE_NOT_ACTIVE"

        r = _put(
            mundo,
            contrato["id"],
            "/cobertura",
            {"asignaciones": [{"certificado_id": prep["cdps"][0], "monto": "30000.00"}]},
            contrato["version"],
        )
        assert r.status_code == 422
        assert r.json()["code"] == "GOV_CONTRACT_CERTIFICATE_INVALID"

    def test_vector_f_autoridad_insuficiente(self, mundo, gobierno, ocupacion):
        prep = _preparado(mundo, ocupacion)
        contrato = prep["contrato"]
        firmante_bajo = _cargo_firmante(mundo, ocupacion, "MONTO", "40000.00", "USD")
        r = _post(
            mundo,
            f"{C}/{contrato['id']}/formalizar",
            "ua",
            mundo.company_a,
            {"firmante_cargo_id": firmante_bajo},
            version=contrato["version"],
        )
        assert r.status_code == 409
        assert r.json()["code"] == "GOV_CONTRACT_SIGNER_AMOUNT_EXCEEDED"

        ficha = _ficha(mundo, contrato["id"]).json()
        assert ficha["estado"] == "BORRADOR"
        bloqueados = eventos(mundo, "GOV_CONTRACT_SIGNER_BLOCKED", prep["exp"]["id"])
        assert len(bloqueados) == 1
        assert "monto" not in bloqueados[0].after
        assert bloqueados[0].after["causal"] == "GOV_CONTRACT_SIGNER_AMOUNT_EXCEEDED"

        firmante_exacto = _cargo_firmante(mundo, ocupacion, "MONTO", "50000.00", "USD")
        ficha = _ficha(mundo, contrato["id"]).json()
        firmante_info = next(
            f for f in ficha["opciones"]["firmantes"] if f["cargo_id"] == firmante_exacto
        )
        assert firmante_info["control"]["estado"] == "DENTRO_LIMITE"

        cargo_sin_permiso = cargo_contrataciones(mundo, ocupacion)
        r = _post(
            mundo,
            f"{C}/{contrato['id']}/formalizar",
            "ua",
            mundo.company_a,
            {"firmante_cargo_id": cargo_sin_permiso},
            version=ficha["version"],
        )
        assert r.status_code == 422
        assert r.json()["code"] == "GOV_CONTRACT_SIGNER_INVALID"

        r = _post(
            mundo,
            f"{C}/{contrato['id']}/formalizar",
            "ua",
            mundo.company_a,
            {"firmante_cargo_id": firmante_exacto},
            version=ficha["version"],
        )
        assert r.status_code == 200
        assert r.json()["estado"] == "FORMALIZADO"

    def test_vector_g_moneda_distinta(self, mundo, gobierno, ocupacion):
        prep = _preparado(mundo, ocupacion)
        contrato = prep["contrato"]
        firmante_eur = _cargo_firmante(mundo, ocupacion, "MONTO", "50000.00", "EUR")
        r = _post(
            mundo,
            f"{C}/{contrato['id']}/formalizar",
            "ua",
            mundo.company_a,
            {"firmante_cargo_id": firmante_eur},
            version=contrato["version"],
        )
        assert r.status_code == 422
        assert r.json()["code"] == "GOV_OFFICIAL_RATE_REQUIRED"

        cdp_eur = _cdp(mundo, ocupacion, "50000.00", moneda="EUR", expediente_id=prep["exp"]["id"])
        r = _put(
            mundo,
            contrato["id"],
            "/cobertura",
            {"asignaciones": [{"certificado_id": cdp_eur, "monto": "50000.00"}]},
            contrato["version"],
        )
        assert r.status_code == 422
        assert r.json()["code"] == "GOV_CONTRACT_CERTIFICATE_INVALID"

        otro = _mundo_contrato(mundo, ocupacion)
        cdp_otro = _cdp(mundo, ocupacion, "50000.00", moneda="USD", expediente_id=otro["exp"]["id"])
        r = _put(
            mundo,
            contrato["id"],
            "/cobertura",
            {"asignaciones": [{"certificado_id": cdp_otro, "monto": "50000.00"}]},
            contrato["version"],
        )
        assert r.status_code == 422
        assert r.json()["code"] == "GOV_CONTRACT_CERTIFICATE_INVALID"

    def test_vector_h_doble_creacion_y_doble_formalizacion(self, mundo, gobierno, ocupacion):
        m = _mundo_contrato(mundo, ocupacion)
        exp_id = m["exp"]["id"]
        with mundo.factory() as db:
            uid = db.scalar(select(User.id).where(User.username == "ua"))

        def operacion_crear(s):
            ctx = CompanyContext(
                tenant_id=mundo.t1,
                company_id=mundo.company_a,
                company=s.get(Company, mundo.company_a),
                user_id=uid,
            )
            user = s.get(User, uid)
            return crear(s, ctx, user, {"expediente_id": exp_id})

        r1, r2 = carrera(mundo.factory, operacion_crear, operacion_crear)
        fichas = [r for r in (r1, r2) if isinstance(r, dict)]
        errores = [r for r in (r1, r2) if isinstance(r, ConflictError)]
        assert len(fichas) == 1
        assert len(errores) == 1
        assert errores[0].code == "GOV_CONTRACT_ALREADY_EXISTS"

        prep = _preparado(mundo, ocupacion)
        contrato = prep["contrato"]
        firmante = _cargo_firmante(mundo, ocupacion, "SIN_LIMITE")
        version = contrato["version"]
        cid = contrato["id"]

        def operacion_formalizar(s):
            ctx = CompanyContext(
                tenant_id=mundo.t1,
                company_id=mundo.company_a,
                company=s.get(Company, mundo.company_a),
                user_id=uid,
            )
            user = s.get(User, uid)
            return formalizar(s, ctx, user, cid, version, {"firmante_cargo_id": firmante})

        r1, r2 = carrera(mundo.factory, operacion_formalizar, operacion_formalizar)
        fichas = [r for r in (r1, r2) if isinstance(r, dict)]
        errores = [r for r in (r1, r2) if isinstance(r, ConflictError)]
        assert len(fichas) == 1
        assert fichas[0]["estado"] == "FORMALIZADO"
        assert len(errores) == 1
        assert errores[0].code in ("GOV_CONTRACT_STALE", "GOV_CONTRACT_ALREADY_FORMALIZED")

    def test_vector_i_aislamiento(self, mundo, gobierno, ocupacion):
        m = _mundo_contrato(mundo, ocupacion)
        r = _crear(mundo, m["exp"]["id"])
        assert r.status_code == 201
        contrato = r.json()

        r = mundo.get(f"{C}/{contrato['id']}", "ub", mundo.company_b)
        assert r.status_code == 404
        assert r.json()["code"] == "GOV_CONTRACT_NOT_FOUND"

        r = _post(
            mundo,
            C,
            "ub",
            mundo.company_b,
            {"expediente_id": m["exp"]["id"]},
        )
        assert r.status_code == 404
        assert r.json()["code"] == "GOV_PROCUREMENT_FILE_NOT_FOUND"

        r = mundo.get(C, "ub", mundo.company_b)
        assert r.status_code == 200
        ids = [item["id"] for item in r.json()["items"]]
        assert contrato["id"] not in ids

    def test_inmutable_en_base(self, mundo, gobierno, ocupacion):
        prep = _preparado(mundo, ocupacion)
        contrato = prep["contrato"]
        firmante = _cargo_firmante(mundo, ocupacion, "SIN_LIMITE")
        r = _post(
            mundo,
            f"{C}/{contrato['id']}/formalizar",
            "ua",
            mundo.company_a,
            {"firmante_cargo_id": firmante},
            version=contrato["version"],
        )
        assert r.status_code == 200
        formalizado = r.json()

        with mundo.factory() as db:
            with pytest.raises(DBAPIError):
                db.execute(
                    text(
                        "UPDATE gov_contracts SET referencia_instrumento = 'X' "
                        "WHERE id = :id"
                    ),
                    {"id": formalizado["id"]},
                )
                db.commit()
            db.rollback()

            with pytest.raises(DBAPIError):
                db.execute(
                    text("DELETE FROM gov_contracts WHERE id = :id"),
                    {"id": formalizado["id"]},
                )
                db.commit()
            db.rollback()

            with pytest.raises(DBAPIError):
                db.execute(
                    text(
                        "DELETE FROM gov_contract_budget_allocations "
                        "WHERE contract_id = :id"
                    ),
                    {"id": formalizado["id"]},
                )
                db.commit()
            db.rollback()

        m2 = _mundo_contrato(mundo, ocupacion)
        r = _crear(mundo, m2["exp"]["id"])
        assert r.status_code == 201
        borrador = r.json()
        with mundo.factory() as db:
            with pytest.raises(DBAPIError):
                db.execute(
                    text("UPDATE gov_contracts SET monto = 1 WHERE id = :id"),
                    {"id": borrador["id"]},
                )
                db.commit()
            db.rollback()

    def test_permisos_mfa_y_ctl01(self, mundo, gobierno, ocupacion):
        assert classify("gobierno_contratos:formalize") == SENSITIVE
        assert CATALOGO_DE_PERMISOS["gobierno_contratos"] == [
            "view",
            "manage",
            "formalize",
            "assign_supervisor",
            "execute",
        ]

        cuenta_con_permisos(mundo, "cnt_lector", [("gobierno_contratos", "view")])
        m = _mundo_contrato(mundo, ocupacion)
        r = _crear(mundo, m["exp"]["id"], usuario="cnt_lector")
        assert r.status_code == 403

        regla = regla_vigente(
            mundo,
            proceso="PROC-03",
            accion_a="PROC03_RESOLVER",
            accion_b="PROC03_CONTRATO_FORMALIZAR",
        )
        try:
            prep = _preparado(mundo, ocupacion)
            firmante = _cargo_firmante(mundo, ocupacion, "SIN_LIMITE")
            r = _post(
                mundo,
                f"{C}/{prep['contrato']['id']}/formalizar",
                "ua",
                mundo.company_a,
                {"firmante_cargo_id": firmante},
                version=prep["contrato"]["version"],
            )
            assert r.status_code == 409
            assert r.json()["code"] == "GOV_SOD_CONFLICT"
        finally:
            cerrar_regla(mundo, regla)

    def test_lista_y_mensajes(self, mundo, gobierno, ocupacion):
        m1 = _mundo_contrato(mundo, ocupacion)
        c1 = _crear(mundo, m1["exp"]["id"])
        assert c1.status_code == 201
        contrato1 = c1.json()

        m2 = _mundo_contrato(mundo, ocupacion)
        c2 = _crear(mundo, m2["exp"]["id"])
        assert c2.status_code == 201
        contrato2 = c2.json()

        r = mundo.get(C, "ua", mundo.company_a)
        assert r.status_code == 200
        items = r.json()["items"]
        assert any(x["id"] == contrato1["id"] for x in items)
        assert any(x["id"] == contrato2["id"] for x in items)
        for item in items:
            if item["id"] in (contrato1["id"], contrato2["id"]):
                assert item["identificacion"].startswith("Borrador · ")

        prep = _preparado(mundo, ocupacion)
        firmante = _cargo_firmante(mundo, ocupacion, "SIN_LIMITE")
        r = _post(
            mundo,
            f"{C}/{prep['contrato']['id']}/formalizar",
            "ua",
            mundo.company_a,
            {"firmante_cargo_id": firmante},
            version=prep["contrato"]["version"],
        )
        assert r.status_code == 200

        r = mundo.get(f"{C}?estado=FORMALIZADO", "ua", mundo.company_a)
        assert r.status_code == 200
        assert all(item["estado"] == "FORMALIZADO" for item in r.json()["items"])

    def test_sin_monto_no_se_prepara(self, mundo, gobierno, ocupacion):
        exp, _, _ = _adjudicado(mundo, ocupacion)
        r = _crear(mundo, exp["id"])
        assert r.status_code == 422
        assert r.json()["code"] == "GOV_CONTRACT_OFFER_AMOUNT_REQUIRED"
