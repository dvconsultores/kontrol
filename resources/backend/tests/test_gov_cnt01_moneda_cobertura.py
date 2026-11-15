"""Delta CNT-01 · moneda canónica, firmante multimoneda con TRE-09 y cobertura frente a compromisos BUD-08."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.modules.government.models import (
    GovernmentBudgetCertificate,
    GovernmentBudgetCommitment,
    GovernmentBudgetCommitmentLine,
    GovernmentContract,
    GovernmentContractBudgetAllocation,
)
from app.modules.identity_access.models import User
from tests.org04_ayudantes import nuevo_cargo
from tests.test_gov_bud01_ejercicio import ONLY_PG
from tests.test_gov_cnt01_contratos import (
    C,
    _cargo_firmante,
    _cdp,
    _crear,
    _ficha,
    _mundo_contrato,
    _patch,
    _post,
    _put,
)
from tests.test_gov_proc08_multimoneda import _tasa
from tests.test_gov_proc10_garantias import HOY, _doc

pytest_plugins = (
    "tests.conftest_multicompany",
    "tests.test_gov_ctl06_hallazgos",
    "tests.org04_ayudantes",
)


def _compromiso(
    mundo,
    ocupacion,
    cdp_id: str,
    monto: str,
    expediente_id: str | None,
    doc_id: str,
    moneda: str = "USD",
) -> str:
    cargo = nuevo_cargo(mundo, ocupacion)
    with mundo.factory() as db:
        cdp = db.get(GovernmentBudgetCertificate, cdp_id)
        uid = db.scalar(select(User.id).where(User.username == "ua"))
        numero = (
            db.scalar(
                select(GovernmentBudgetCommitment.numero)
                .where(GovernmentBudgetCommitment.year_id == cdp.year_id)
                .order_by(GovernmentBudgetCommitment.numero.desc())
                .limit(1)
            )
            or 0
        ) + 1
        k = GovernmentBudgetCommitment(
            year_id=cdp.year_id,
            company_id=mundo.company_a,
            numero=numero,
            codigo=f"CMP-{numero:05d}-{uuid4().hex[:6]}"[:20],
            estado="VIGENTE",
            moneda=moneda,
            fecha=HOY,
            concepto="Compromiso de prueba para CNT-01",
            expediente_referencia="EXP-PRUEBA",
            procurement_file_id=expediente_id,
            autoridad_cargo_id=cargo,
            autoridad_cargo_codigo="C",
            autoridad_cargo_nombre="Cargo",
            autoridad_unidad="Unidad",
            autoridad_funcionario_id=None,
            autoridad_funcionario_nombre=None,
            limite_tipo="SIN_LIMITE",
            limite_monto=None,
            limite_moneda=None,
            soporte_documento_id=doc_id,
            soporte_sha256="0" * 64,
            emitido_por=uid,
            emitido_en=datetime.now(UTC),
            snapshot={},
            huella="0" * 64,
            documento_storage_key="cmp/prueba.pdf",
            documento_sha256="0" * 64,
            documento_tamano=1,
            documento_nombre="cmp.pdf",
            created_by=uid,
        )
        db.add(k)
        db.flush()
        db.add(
            GovernmentBudgetCommitmentLine(
                commitment_id=k.id,
                year_id=cdp.year_id,
                company_id=mundo.company_a,
                certificate_id=cdp_id,
                credit_id=cdp.credit_id,
                linea=1,
                monto=Decimal(monto),
                created_by=uid,
            )
        )
        db.commit()
        return str(k.id)


def _borrador_listo(
    mundo, ocupacion, moneda: str, cdp_moneda: str, total: str = "50000.00"
) -> dict[str, Any]:
    m = _mundo_contrato(mundo, ocupacion, total=total, moneda=moneda)
    r = _crear(mundo, m["exp"]["id"])
    assert r.status_code == 201
    cid = r.json()["id"]
    doc_id, _ = _doc(mundo, m["exp"], "doc-contrato")
    r = _patch(
        mundo,
        cid,
        {
            "tipo": "CONTRATO",
            "fecha_inicio": HOY.isoformat(),
            "fecha_fin": (HOY + timedelta(days=180)).isoformat(),
            "referencia_instrumento": "CT-INSTR-001",
            "documento_id": doc_id,
        },
        r.json()["version"],
    )
    assert r.status_code == 200
    cdp = _cdp(
        mundo,
        ocupacion,
        total,
        moneda=cdp_moneda,
        expediente_id=m["exp"]["id"],
    )
    r = _put(
        mundo,
        cid,
        "/cobertura",
        {"asignaciones": [{"certificado_id": cdp, "monto": total}]},
        r.json()["version"],
    )
    assert r.status_code == 200
    return {
        "exp": m["exp"],
        "ofertas": m["ofertas"],
        "contrato": r.json(),
        "cdp": cdp,
    }


@pytest.mark.usefixtures("gobierno")
@ONLY_PG
class TestGovCnt01MonedaCobertura:
    def test_cdp_ved_cubre_contrato_ves(self, mundo, gobierno, ocupacion):
        s = _borrador_listo(mundo, ocupacion, moneda="VES", cdp_moneda="VED")
        cid = s["contrato"]["id"]
        assert s["contrato"]["moneda"] == "VES"
        assert s["contrato"]["moneda_oferta"] == "VES"
        with mundo.factory() as db:
            alloc = db.scalar(
                select(GovernmentContractBudgetAllocation).where(
                    GovernmentContractBudgetAllocation.contract_id == cid
                )
            )
            assert alloc is not None
            assert alloc.moneda == "VES"
        firmante = _cargo_firmante(mundo, ocupacion, "SIN_LIMITE")
        ficha = _ficha(mundo, cid).json()
        r = _post(
            mundo,
            f"{C}/{cid}/formalizar",
            "ua",
            mundo.company_a,
            {"firmante_cargo_id": firmante},
            version=ficha["version"],
        )
        assert r.status_code == 200
        with mundo.factory() as db:
            gc = db.get(GovernmentContract, cid)
            assert gc.moneda == "VES"
            assert gc.snapshot["moneda"] == "VES"
            assert gc.snapshot["moneda_oferta"] == "VES"

    def test_firmante_usd_sobre_contrato_ves(
        self, mundo, gobierno, ocupacion
    ):
        s = _borrador_listo(mundo, ocupacion, moneda="VES", cdp_moneda="VES")
        cid = s["contrato"]["id"]
        f1000 = _cargo_firmante(mundo, ocupacion, "MONTO", "1000.00", "USD")
        ficha = _ficha(mundo, cid).json()
        firmante_opcion = next(
            f
            for f in ficha["opciones"]["firmantes"]
            if f["cargo_id"] == f1000
        )
        assert firmante_opcion["control"]["estado"] == "SIN_TASA"
        r = _post(
            mundo,
            f"{C}/{cid}/formalizar",
            "ua",
            mundo.company_a,
            {"firmante_cargo_id": f1000},
            version=ficha["version"],
        )
        assert r.status_code == 422
        assert r.json()["code"] == "GOV_OFFICIAL_RATE_REQUIRED"
        assert r.json()["details"]["monedas_sin_tasa"] == ["USD"]
        _tasa(mundo, s["ofertas"][0]["id"], "USD", "40", 1)
        ficha = _ficha(mundo, cid).json()
        r = _post(
            mundo,
            f"{C}/{cid}/formalizar",
            "ua",
            mundo.company_a,
            {"firmante_cargo_id": f1000},
            version=ficha["version"],
        )
        assert r.status_code == 409
        assert r.json()["code"] == "GOV_CONTRACT_SIGNER_AMOUNT_EXCEEDED"
        assert r.json()["details"]["conversion"] is not None
        f2000 = _cargo_firmante(mundo, ocupacion, "MONTO", "2000.00", "USD")
        ficha = _ficha(mundo, cid).json()
        r = _post(
            mundo,
            f"{C}/{cid}/formalizar",
            "ua",
            mundo.company_a,
            {"firmante_cargo_id": f2000},
            version=ficha["version"],
        )
        assert r.status_code == 200
        conversion = r.json()["firmante"]["conversion"]
        assert conversion["tasas"][0]["moneda"] == "USD"

    def test_cdp_comprometida_por_el_mismo_expediente(
        self, mundo, gobierno, ocupacion
    ):
        m = _mundo_contrato(mundo, ocupacion)
        r = _crear(mundo, m["exp"]["id"])
        assert r.status_code == 201
        cid = r.json()["id"]
        doc_id, _ = _doc(mundo, m["exp"], "doc-contrato")
        r = _patch(
            mundo,
            cid,
            {
                "tipo": "CONTRATO",
                "fecha_inicio": HOY.isoformat(),
                "fecha_fin": (HOY + timedelta(days=180)).isoformat(),
                "referencia_instrumento": "CT-INSTR-001",
                "documento_id": doc_id,
            },
            r.json()["version"],
        )
        assert r.status_code == 200
        cdp = _cdp(
            mundo, ocupacion, "50000.00", expediente_id=m["exp"]["id"]
        )
        doc_c, _ = _doc(mundo, m["exp"], "soporte-compromiso")
        _compromiso(mundo, ocupacion, cdp, "30000.00", m["exp"]["id"], doc_c)
        ficha = _ficha(mundo, cid).json()
        elegible = next(
            c for c in ficha["opciones"]["certificados_elegibles"] if c["id"] == cdp
        )
        assert elegible["saldo_libre"] == "50000.00"
        r = _put(
            mundo,
            cid,
            "/cobertura",
            {"asignaciones": [{"certificado_id": cdp, "monto": "50000.00"}]},
            ficha["version"],
        )
        assert r.status_code == 200
        firmante = _cargo_firmante(mundo, ocupacion, "SIN_LIMITE")
        ficha = _ficha(mundo, cid).json()
        r = _post(
            mundo,
            f"{C}/{cid}/formalizar",
            "ua",
            mundo.company_a,
            {"firmante_cargo_id": firmante},
            version=ficha["version"],
        )
        assert r.status_code == 200

    def test_cdp_sin_expediente_comprometida(
        self, mundo, gobierno, ocupacion
    ):
        m = _mundo_contrato(mundo, ocupacion)
        r = _crear(mundo, m["exp"]["id"])
        assert r.status_code == 201
        cid = r.json()["id"]
        doc_id, _ = _doc(mundo, m["exp"], "doc-contrato")
        r = _patch(
            mundo,
            cid,
            {
                "tipo": "CONTRATO",
                "fecha_inicio": HOY.isoformat(),
                "fecha_fin": (HOY + timedelta(days=180)).isoformat(),
                "referencia_instrumento": "CT-INSTR-001",
                "documento_id": doc_id,
            },
            r.json()["version"],
        )
        assert r.status_code == 200
        cdp_libre = _cdp(mundo, ocupacion, "50000.00", expediente_id=None)
        doc_c = _doc(mundo, m["exp"], "soporte-compromiso")[0]
        _compromiso(mundo, ocupacion, cdp_libre, "20000.00", None, doc_c)
        ficha = _ficha(mundo, cid).json()
        elegible = next(
            c
            for c in ficha["opciones"]["certificados_elegibles"]
            if c["id"] == cdp_libre
        )
        assert elegible["saldo_libre"] == "30000.00"
        r = _put(
            mundo,
            cid,
            "/cobertura",
            {"asignaciones": [{"certificado_id": cdp_libre, "monto": "50000.00"}]},
            ficha["version"],
        )
        assert r.status_code == 422
        assert r.json()["code"] == "GOV_CONTRACT_CERTIFICATE_INVALID"
        cdp_exp = _cdp(
            mundo, ocupacion, "20000.00", expediente_id=m["exp"]["id"]
        )
        ficha = _ficha(mundo, cid).json()
        r = _put(
            mundo,
            cid,
            "/cobertura",
            {
                "asignaciones": [
                    {"certificado_id": cdp_libre, "monto": "30000.00"},
                    {"certificado_id": cdp_exp, "monto": "20000.00"},
                ]
            },
            ficha["version"],
        )
        assert r.status_code == 200

    def test_compromisos_del_expediente_superan_el_contrato(
        self, mundo, gobierno, ocupacion
    ):
        s = _borrador_listo(mundo, ocupacion, moneda="USD", cdp_moneda="USD")
        doc_c = _doc(mundo, s["exp"], "soporte-compromiso")[0]
        _compromiso(
            mundo,
            ocupacion,
            s["cdp"],
            "60000.00",
            s["exp"]["id"],
            doc_c,
        )
        ficha = _ficha(mundo, s["contrato"]["id"]).json()
        assert any("superan el monto" in p for p in ficha["pendientes"])
        firmante = _cargo_firmante(mundo, ocupacion, "SIN_LIMITE")
        r = _post(
            mundo,
            f"{C}/{s['contrato']['id']}/formalizar",
            "ua",
            mundo.company_a,
            {"firmante_cargo_id": firmante},
            version=ficha["version"],
        )
        assert r.status_code == 409
        assert r.json()["code"] == "GOV_CONTRACT_COMMITMENT_EXCEEDS_AMOUNT"

    def test_compromisos_en_otra_moneda_no_comparables(
        self, mundo, gobierno, ocupacion
    ):
        s = _borrador_listo(mundo, ocupacion, moneda="USD", cdp_moneda="USD")
        doc_c = _doc(mundo, s["exp"], "soporte-compromiso")[0]
        _compromiso(
            mundo,
            ocupacion,
            s["cdp"],
            "100.00",
            s["exp"]["id"],
            doc_c,
            moneda="EUR",
        )
        firmante = _cargo_firmante(mundo, ocupacion, "SIN_LIMITE")
        ficha = _ficha(mundo, s["contrato"]["id"]).json()
        r = _post(
            mundo,
            f"{C}/{s['contrato']['id']}/formalizar",
            "ua",
            mundo.company_a,
            {"firmante_cargo_id": firmante},
            version=ficha["version"],
        )
        assert r.status_code == 409
        assert r.json()["code"] == "GOV_CONTRACT_COMMITMENT_NOT_COMPARABLE"

    def test_reclamo_global_de_una_cdp(self, mundo, gobierno, ocupacion):
        cdp_libre = _cdp(mundo, ocupacion, "50000.00", expediente_id=None)
        m_a = _mundo_contrato(mundo, ocupacion)
        r = _crear(mundo, m_a["exp"]["id"])
        assert r.status_code == 201
        cid_a = r.json()["id"]
        doc_id, _ = _doc(mundo, m_a["exp"], "doc-a")
        r = _patch(
            mundo,
            cid_a,
            {
                "tipo": "CONTRATO",
                "fecha_inicio": HOY.isoformat(),
                "fecha_fin": (HOY + timedelta(days=180)).isoformat(),
                "referencia_instrumento": "CT-INSTR-001",
                "documento_id": doc_id,
            },
            r.json()["version"],
        )
        assert r.status_code == 200
        r = _put(
            mundo,
            cid_a,
            "/cobertura",
            {"asignaciones": [{"certificado_id": cdp_libre, "monto": "50000.00"}]},
            r.json()["version"],
        )
        assert r.status_code == 200
        firmante = _cargo_firmante(mundo, ocupacion, "SIN_LIMITE")
        ficha_a = _ficha(mundo, cid_a).json()
        r = _post(
            mundo,
            f"{C}/{cid_a}/formalizar",
            "ua",
            mundo.company_a,
            {"firmante_cargo_id": firmante},
            version=ficha_a["version"],
        )
        assert r.status_code == 200
        m_b = _mundo_contrato(mundo, ocupacion)
        r = _crear(mundo, m_b["exp"]["id"])
        assert r.status_code == 201
        cid_b = r.json()["id"]
        doc_id, _ = _doc(mundo, m_b["exp"], "doc-b")
        r = _patch(
            mundo,
            cid_b,
            {
                "tipo": "CONTRATO",
                "fecha_inicio": HOY.isoformat(),
                "fecha_fin": (HOY + timedelta(days=180)).isoformat(),
                "referencia_instrumento": "CT-INSTR-001",
                "documento_id": doc_id,
            },
            r.json()["version"],
        )
        assert r.status_code == 200
        ficha_b = r.json()
        ids = [c["id"] for c in ficha_b["opciones"]["certificados_elegibles"]]
        assert cdp_libre not in ids
        r = _put(
            mundo,
            cid_b,
            "/cobertura",
            {"asignaciones": [{"certificado_id": cdp_libre, "monto": "1.00"}]},
            ficha_b["version"],
        )
        assert r.status_code == 422
        assert r.json()["code"] == "GOV_CONTRACT_CERTIFICATE_INVALID"
