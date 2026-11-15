"""CNT-02 · adendas, prórrogas, modificaciones y variaciones versionadas (GOV-CNT-002)."""

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
    GovernmentBudgetCommitment,
    GovernmentBudgetCommitmentLine,
    GovernmentContractAmendment,
    GovernmentProcurementFileEvent,
)
from app.modules.government.service_contratos_modificaciones import (
    crear as crear_modificacion,
)
from app.modules.government.service_contratos_modificaciones import (
    formalizar as formalizar_modificacion,
)
from app.modules.identity_access.models import User
from tests.concurrency import carrera
from tests.org04_ayudantes import nuevo_cargo
from tests.org06_guarda import cuenta_con_permisos
from tests.test_gov_bud01_ejercicio import ONLY_PG
from tests.test_gov_cnt01_contratos import (
    C,
    _cargo_firmante,
    _cdp,
    _ficha,
    _mundo_contrato,
    _post,
    _preparado,
)
from tests.test_gov_ctl01_reglas import cerrar_regla, eventos, regla_vigente
from tests.test_gov_proc08_multimoneda import _tasa
from tests.test_gov_proc10_garantias import HOY, _doc

pytest_plugins = (
    "tests.conftest_multicompany",
    "tests.test_gov_ctl06_hallazgos",
    "tests.org04_ayudantes",
)

FIN = HOY + timedelta(days=180)


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
            concepto="Compromiso de prueba para CNT-02",
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


def M(cid: str) -> str:
    return f"{C}/{cid}/modificaciones"


def _formalizado(mundo, ocupacion) -> dict[str, Any]:
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
    return {
        "exp": prep["exp"],
        "ofertas": prep["ofertas"],
        "contrato": r.json(),
        "cdps": prep["cdps"],
    }


def _nueva(mundo, cid, tipo, usuario="ua"):
    return _post(mundo, M(cid), usuario, mundo.company_a, {"tipo": tipo})


def _patch_m(mundo, cid, mid, cuerpo, version):
    headers = mundo.como("ua", mundo.company_a)
    if version is not None:
        headers["If-Match"] = str(version)
    return mundo.client.patch(f"/api/v1{M(cid)}/{mid}", json=cuerpo, headers=headers)


def _put_m(mundo, cid, mid, asignaciones, version):
    headers = mundo.como("ua", mundo.company_a)
    if version is not None:
        headers["If-Match"] = str(version)
    return mundo.client.put(
        f"/api/v1{M(cid)}/{mid}/cobertura",
        json={"asignaciones": asignaciones},
        headers=headers,
    )


def _formalizar_m(
    mundo, cid, mid, firmante, version, usuario="ua"
):
    return _post(
        mundo,
        f"{M(cid)}/{mid}/formalizar",
        usuario,
        mundo.company_a,
        {"firmante_cargo_id": firmante},
        version=version,
    )


def _delete_m(mundo, cid, mid, version):
    headers = mundo.como("ua", mundo.company_a)
    if version is not None:
        headers["If-Match"] = str(version)
    return mundo.client.delete(f"/api/v1{M(cid)}/{mid}", headers=headers)


def _ficha_m(mundo, cid, mid):
    return mundo.get(M(cid) + f"/{mid}", "ua", mundo.company_a)


def _historia(mundo, cid, fecha=None):
    ruta = M(cid)
    if fecha is not None:
        ruta += f"?fecha={fecha.isoformat()}"
    return mundo.get(ruta, "ua", mundo.company_a)


def _lista(mundo, f, cid, tipo, cambios, doc_nombre):
    r = _nueva(mundo, cid, tipo)
    assert r.status_code == 201
    doc_id, _ = _doc(mundo, f["exp"], doc_nombre)
    cuerpo = {
        "fecha_instrumento": HOY.isoformat(),
        "vigente_desde": HOY.isoformat(),
        "motivo": "Solicitud justificada del contratista",
        "referencia_instrumento": "INSTR-MOD-01",
        "documento_id": doc_id,
        **cambios,
    }
    r = _patch_m(mundo, cid, r.json()["id"], cuerpo, r.json()["version"])
    assert r.status_code == 200
    return r.json()


@pytest.mark.usefixtures("gobierno")
@ONLY_PG
class TestGovCnt02Modificaciones:
    def test_prorroga_y_original_intacto(self, mundo, gobierno, ocupacion):
        f = _formalizado(mundo, ocupacion)
        cid = f["contrato"]["id"]
        antes = _ficha(mundo, cid).json()
        r = _nueva(mundo, cid, "PRORROGA")
        assert r.status_code == 201
        b = r.json()
        assert b["estado"] == "BORRADOR"
        assert b["codigo"] is None
        assert b["base"]["monto"] == "50000.00"
        assert b["base"]["fecha_fin"] == FIN.isoformat()
        assert b["puede_formalizar"] is False
        assert b["pendientes"]
        doc_id, _ = _doc(mundo, f["exp"], "doc-prorroga")
        cuerpo = {
            "fecha_instrumento": HOY.isoformat(),
            "vigente_desde": HOY.isoformat(),
            "motivo": "Solicitud justificada del contratista",
            "referencia_instrumento": "INSTR-MOD-01",
            "documento_id": doc_id,
            "nueva_fecha_fin": (FIN + timedelta(days=30)).isoformat(),
        }
        r = _patch_m(mundo, cid, b["id"], cuerpo, b["version"])
        assert r.status_code == 200
        b = r.json()
        assert b["pendientes"] == []
        assert b["puede_formalizar"] is True
        firmante = _cargo_firmante(mundo, ocupacion, "SIN_LIMITE")
        r = _formalizar_m(mundo, cid, b["id"], firmante, b["version"])
        assert r.status_code == 200
        m = r.json()
        assert m["estado"] == "FORMALIZADA"
        assert m["codigo"] == f"{antes['codigo']}/PR-001"
        assert len(m["huella"]) == 64
        expected_fin = (FIN + timedelta(days=30)).isoformat()
        assert m["base"]["fecha_fin"] == FIN.isoformat()
        assert m["propuesta"]["fecha_fin_nueva"] == expected_fin
        despues = _ficha(mundo, cid).json()
        assert despues["fecha_fin"] == antes["fecha_fin"]
        assert despues["monto"] == antes["monto"]
        assert despues["huella"] == antes["huella"]
        assert despues["modificaciones"]["cantidad"] == 1
        assert despues["modificaciones"]["vigente"]["fecha_fin"] == expected_fin
        h = _historia(mundo, cid).json()
        assert h["original"]["fecha_fin"] == FIN.isoformat()
        assert h["vigente"]["fecha_fin"] == expected_fin
        assert len(h["historial"]) == 1
        assert h["historial"][0]["plazo"] == {
            "anterior": FIN.isoformat(),
            "nuevo": expected_fin,
        }
        assert h["historial"][0]["monto"] is None
        with mundo.factory() as db:
            assert documento_sellado(db, doc_id) is True
        assert (
            len(eventos(mundo, "GOV_CONTRACT_AMENDMENT_FORMALIZED", f["exp"]["id"]))
            == 1
        )
        assert (
            len(eventos(mundo, "GOV_CONTRACT_AMENDMENT_DRAFT_CREATED", f["exp"]["id"]))
            == 1
        )
        with mundo.factory() as db:
            ev = db.scalar(
                select(GovernmentProcurementFileEvent).where(
                    GovernmentProcurementFileEvent.file_id == f["exp"]["id"],
                    GovernmentProcurementFileEvent.clase == "CONTRATO",
                    GovernmentProcurementFileEvent.titulo.like("Prórroga%"),
                )
            )
            assert ev is not None
            assert ev.titulo.startswith("Prórroga")

    def test_aumento_exige_cobertura_exacta(self, mundo, gobierno, ocupacion):
        f = _formalizado(mundo, ocupacion)
        cid = f["contrato"]["id"]
        b = _lista(
            mundo, f, cid, "ADENDA", {"delta_monto": "10000.00"}, "doc-adenda"
        )
        assert b["propuesta"]["monto_nuevo"] == "60000.00"
        assert b["cobertura"]["requerida_adicional"] == "10000.00"
        assert b["puede_formalizar"] is False
        firmante = _cargo_firmante(mundo, ocupacion, "SIN_LIMITE")
        r = _formalizar_m(mundo, cid, b["id"], firmante, b["version"])
        assert r.status_code == 409
        assert r.json()["code"] == "GOV_CONTRACT_AMENDMENT_COVERAGE_INSUFFICIENT"
        cdp3 = _cdp(
            mundo, ocupacion, "15000.00", expediente_id=f["exp"]["id"]
        )
        r = _put_m(
            mundo,
            cid,
            b["id"],
            [{"certificado_id": cdp3, "monto": "15000.00"}],
            b["version"],
        )
        assert r.status_code == 422
        assert r.json()["code"] == "GOV_CONTRACT_AMENDMENT_COVERAGE_EXCEEDS"
        b = _ficha_m(mundo, cid, b["id"]).json()
        r = _put_m(
            mundo,
            cid,
            b["id"],
            [{"certificado_id": cdp3, "monto": "10000.00"}],
            b["version"],
        )
        assert r.status_code == 200
        assert r.json()["cobertura"]["completa"] is True
        b = r.json()
        r = _formalizar_m(mundo, cid, b["id"], firmante, b["version"])
        assert r.status_code == 200
        assert r.json()["codigo"].endswith("/AD-001")
        h = _historia(mundo, cid).json()
        assert h["historial"][0]["monto"] == {
            "anterior": "50000.00",
            "delta": "10000.00",
            "nuevo": "60000.00",
        }
        with mundo.factory() as db:
            cdp = db.get(GovernmentBudgetCertificate, cdp3)
            codigo = cdp.codigo
        assert h["historial"][0]["cobertura_adicional"] == [
            {"codigo": codigo, "monto": "10000.00"}
        ]
        assert h["vigente"]["monto"] == "60000.00"
        assert _ficha(mundo, cid).json()["monto"] == "50000.00"
        r = _nueva(mundo, cid, "ADENDA")
        assert r.status_code == 201
        b2 = r.json()
        elegible = next(
            c for c in b2["opciones"]["certificados_elegibles"] if c["id"] == cdp3
        )
        assert elegible["saldo_libre"] == "5000.00"
        r = _patch_m(
            mundo,
            cid,
            b2["id"],
            {"delta_monto": "0.001"},
            b2["version"],
        )
        assert r.status_code == 422
        assert r.json()["code"] == "GOV_CONTRACT_AMENDMENT_INVALID"
        r = _patch_m(
            mundo,
            cid,
            b2["id"],
            {"delta_monto": "0"},
            b2["version"],
        )
        assert r.status_code == 422
        assert r.json()["code"] == "GOV_CONTRACT_AMENDMENT_INVALID"

    def test_reduccion_bloqueada_por_compromisos(
        self, mundo, gobierno, ocupacion
    ):
        f = _formalizado(mundo, ocupacion)
        cid = f["contrato"]["id"]
        doc_id, _ = _doc(mundo, f["exp"], "soporte-compromiso")
        _compromiso(mundo, ocupacion, f["cdps"][0], "45000.00", f["exp"]["id"], doc_id)
        b = _lista(
            mundo,
            f,
            cid,
            "MODIFICACION",
            {"delta_monto": "-10000.00"},
            "doc-reduccion",
        )
        assert any("superan el monto" in p for p in b["pendientes"])
        firmante = _cargo_firmante(mundo, ocupacion, "SIN_LIMITE")
        r = _formalizar_m(mundo, cid, b["id"], firmante, b["version"])
        assert r.status_code == 409
        assert r.json()["code"] == "GOV_CONTRACT_COMMITMENT_EXCEEDS_AMOUNT"
        r = _patch_m(
            mundo,
            cid,
            b["id"],
            {"delta_monto": "-5000.00"},
            b["version"],
        )
        assert r.status_code == 200
        b = r.json()
        r = _formalizar_m(mundo, cid, b["id"], firmante, b["version"])
        assert r.status_code == 200
        assert r.json()["propuesta"]["monto_nuevo"] == "45000.00"

    def test_autoridad_contra_monto_efectivo_nuevo(
        self, mundo, gobierno, ocupacion
    ):
        f = _formalizado(mundo, ocupacion)
        cid = f["contrato"]["id"]
        b = _lista(
            mundo, f, cid, "ADENDA", {"delta_monto": "10000.00"}, "doc-adenda"
        )
        cdp3 = _cdp(mundo, ocupacion, "10000.00", expediente_id=f["exp"]["id"])
        r = _put_m(
            mundo,
            cid,
            b["id"],
            [{"certificado_id": cdp3, "monto": "10000.00"}],
            b["version"],
        )
        assert r.status_code == 200
        b = r.json()
        f55 = _cargo_firmante(mundo, ocupacion, "MONTO", "55000.00", "USD")
        r = _formalizar_m(mundo, cid, b["id"], f55, b["version"])
        assert r.status_code == 409
        assert r.json()["code"] == "GOV_CONTRACT_SIGNER_AMOUNT_EXCEEDED"
        assert (
            len(
                eventos(
                    mundo,
                    "GOV_CONTRACT_AMENDMENT_SIGNER_BLOCKED",
                    f["exp"]["id"],
                )
            )
            == 1
        )
        f60 = _cargo_firmante(mundo, ocupacion, "MONTO", "60000.00", "USD")
        b = _ficha_m(mundo, cid, b["id"]).json()
        r = _formalizar_m(mundo, cid, b["id"], f60, b["version"])
        assert r.status_code == 200

    def test_firmante_multimoneda_tre09(self, mundo, gobierno, ocupacion):
        f = _formalizado(mundo, ocupacion)
        cid = f["contrato"]["id"]
        b = _lista(
            mundo,
            f,
            cid,
            "PRORROGA",
            {"nueva_fecha_fin": (FIN + timedelta(days=10)).isoformat()},
            "doc-prorroga",
        )
        feur = _cargo_firmante(mundo, ocupacion, "MONTO", "100000.00", "EUR")
        r = _formalizar_m(mundo, cid, b["id"], feur, b["version"])
        assert r.status_code == 422
        assert r.json()["code"] == "GOV_OFFICIAL_RATE_REQUIRED"
        assert "EUR" in r.json()["details"]["monedas_sin_tasa"]
        _tasa(mundo, f["ofertas"][0]["id"], "USD", "40", 1)
        _tasa(mundo, f["ofertas"][0]["id"], "EUR", "44", 1)
        b = _ficha_m(mundo, cid, b["id"]).json()
        r = _formalizar_m(mundo, cid, b["id"], feur, b["version"])
        assert r.status_code == 200
        conversion = r.json()["firmante"]["conversion"]
        assert conversion is not None
        assert len(conversion["tasas"]) == 2
        assert "total_ves" in conversion
        assert "limite_ves" in conversion

    def test_reglas_de_fechas_plazo_y_cambio(
        self, mundo, gobierno, ocupacion
    ):
        f = _formalizado(mundo, ocupacion)
        cid = f["contrato"]["id"]
        r = _nueva(mundo, cid, "PRORROGA")
        assert r.status_code == 201
        b = r.json()
        doc_id, _ = _doc(mundo, f["exp"], "doc-reglas")
        base_cuerpo = {
            "fecha_instrumento": HOY.isoformat(),
            "vigente_desde": HOY.isoformat(),
            "motivo": "Solicitud justificada del contratista",
            "referencia_instrumento": "INSTR-MOD-01",
            "documento_id": doc_id,
        }
        r = _patch_m(mundo, cid, b["id"], base_cuerpo, b["version"])
        assert r.status_code == 200
        b = r.json()
        firmante = _cargo_firmante(mundo, ocupacion, "SIN_LIMITE")
        r = _formalizar_m(mundo, cid, b["id"], firmante, b["version"])
        assert r.status_code == 422
        assert r.json()["code"] == "GOV_CONTRACT_AMENDMENT_INCOMPLETE"
        assert "nueva_fecha_fin" in r.json()["field_errors"]
        r = _patch_m(
            mundo,
            cid,
            b["id"],
            {"nueva_fecha_fin": FIN.isoformat()},
            b["version"],
        )
        assert r.status_code == 200
        b = r.json()
        r = _formalizar_m(mundo, cid, b["id"], firmante, b["version"])
        assert r.status_code == 422
        assert r.json()["code"] == "GOV_CONTRACT_AMENDMENT_TERM_INVALID"
        r = _patch_m(
            mundo,
            cid,
            b["id"],
            {
                "nueva_fecha_fin": (FIN + timedelta(days=5)).isoformat(),
                "vigente_desde": (HOY - timedelta(days=1)).isoformat(),
            },
            b["version"],
        )
        assert r.status_code == 422
        assert r.json()["code"] == "GOV_CONTRACT_AMENDMENT_DATE_INVALID"
        r = _patch_m(
            mundo,
            cid,
            b["id"],
            {
                "fecha_instrumento": (HOY + timedelta(days=1)).isoformat(),
                "vigente_desde": (HOY + timedelta(days=1)).isoformat(),
            },
            b["version"],
        )
        assert r.status_code == 200
        b = r.json()
        r = _formalizar_m(
            mundo, cid, b["id"], _cargo_firmante(mundo, ocupacion, "SIN_LIMITE"), b["version"]
        )
        assert r.status_code == 422
        assert r.json()["code"] == "GOV_CONTRACT_AMENDMENT_DATE_INVALID"
        r = _delete_m(mundo, cid, b["id"], b["version"])
        assert r.status_code == 204
        b2 = _lista(mundo, f, cid, "ADENDA", {}, "doc-cambio")
        r = _formalizar_m(mundo, cid, b2["id"], firmante, b2["version"])
        assert r.status_code == 422
        assert r.json()["code"] == "GOV_CONTRACT_AMENDMENT_NO_CHANGE"
        r = _patch_m(
            mundo,
            cid,
            b2["id"],
            {"condiciones": "Se sustituye la cláusula de entregas parciales"},
            b2["version"],
        )
        assert r.status_code == 200
        b2 = r.json()
        r = _formalizar_m(mundo, cid, b2["id"], firmante, b2["version"])
        assert r.status_code == 200
        m = r.json()
        assert m["propuesta"]["monto_nuevo"] == "50000.00"
        assert m["propuesta"]["fecha_fin_nueva"] == FIN.isoformat()

    def test_borrador_unico_descartar_y_contrato_no_formalizado(
        self, mundo, gobierno, ocupacion
    ):
        prep = _preparado(mundo, ocupacion)
        r = _nueva(mundo, prep["contrato"]["id"], "ADENDA")
        assert r.status_code == 409
        assert r.json()["code"] == "GOV_CONTRACT_NOT_FORMALIZED"
        f = _formalizado(mundo, ocupacion)
        cid = f["contrato"]["id"]
        r = _nueva(mundo, cid, "OTRO")
        assert r.status_code == 422
        assert r.json()["code"] == "GOV_CONTRACT_AMENDMENT_INVALID"
        r = _nueva(mundo, cid, "ADENDA")
        assert r.status_code == 201
        b = r.json()
        r = _nueva(mundo, cid, "VARIACION")
        assert r.status_code == 409
        assert r.json()["code"] == "GOV_CONTRACT_AMENDMENT_DRAFT_EXISTS"
        h = _historia(mundo, cid).json()
        assert h["borrador"]["id"] == b["id"]
        assert h["puede_crear"] is False
        r = _delete_m(mundo, cid, b["id"], None)
        assert r.status_code == 428
        assert r.json()["code"] == "GOV_CONTRACT_AMENDMENT_IF_MATCH_REQUIRED"
        r = _delete_m(mundo, cid, b["id"], b["version"])
        assert r.status_code == 204
        assert (
            len(
                eventos(
                    mundo,
                    "GOV_CONTRACT_AMENDMENT_DRAFT_DISCARDED",
                    f["exp"]["id"],
                )
            )
            == 1
        )
        r = _nueva(mundo, cid, "VARIACION")
        assert r.status_code == 201

    def test_historia_lineal_y_proyeccion(self, mundo, gobierno, ocupacion):
        f = _formalizado(mundo, ocupacion)
        cid = f["contrato"]["id"]
        m1 = _lista(
            mundo,
            f,
            cid,
            "PRORROGA",
            {"nueva_fecha_fin": (FIN + timedelta(days=30)).isoformat()},
            "doc-prorroga",
        )
        firmante = _cargo_firmante(mundo, ocupacion, "SIN_LIMITE")
        r = _formalizar_m(mundo, cid, m1["id"], firmante, m1["version"])
        assert r.status_code == 200
        m1 = r.json()
        m2 = _lista(
            mundo,
            f,
            cid,
            "ADENDA",
            {
                "condiciones": "Cambio de lugar de entrega",
                "vigente_desde": (HOY + timedelta(days=10)).isoformat(),
            },
            "doc-adenda",
        )
        r = _formalizar_m(mundo, cid, m2["id"], firmante, m2["version"])
        assert r.status_code == 200
        m2 = r.json()
        assert m1["codigo"].endswith("/PR-001")
        assert m2["codigo"].endswith("/AD-002")
        with mundo.factory() as db:
            a2 = db.get(GovernmentContractAmendment, m2["id"])
            a1 = db.get(GovernmentContractAmendment, m1["id"])
            assert str(a2.previous_amendment_id) == m1["id"]
            assert a1.numero == 1
            assert a2.numero == 2
        h = _historia(mundo, cid, fecha=HOY).json()
        assert h["vigente"]["modificacion_codigo"] == m1["codigo"]
        assert h["vigente"]["programadas"] == [m2["codigo"]]
        h = _historia(
            mundo, cid, fecha=HOY + timedelta(days=10)
        ).json()
        assert h["vigente"]["modificacion_codigo"] == m2["codigo"]
        b = _lista(
            mundo,
            f,
            cid,
            "ADENDA",
            {
                "condiciones": "Otro cambio",
                "vigente_desde": (HOY + timedelta(days=5)).isoformat(),
            },
            "doc-adenda2",
        )
        r = _formalizar_m(mundo, cid, b["id"], firmante, b["version"])
        assert r.status_code == 422
        assert r.json()["code"] == "GOV_CONTRACT_AMENDMENT_DATE_INVALID"

    def test_concurrencia(self, mundo, gobierno, ocupacion):
        f = _formalizado(mundo, ocupacion)
        cid = f["contrato"]["id"]
        with mundo.factory() as db:
            uid = db.scalar(select(User.id).where(User.username == "ua"))

        def operacion_crear(s):
            ctx = CompanyContext(
                tenant_id=mundo.t1,
                company_id=mundo.company_a,
                company=None,
                user_id=uid,
            )
            user = s.get(User, uid)
            return crear_modificacion(
                s, ctx, user, cid, {"tipo": "ADENDA"}
            )

        r1, r2 = carrera(mundo.factory, operacion_crear, operacion_crear)
        fichas = [r for r in (r1, r2) if isinstance(r, dict)]
        errores = [r for r in (r1, r2) if isinstance(r, ConflictError)]
        assert len(fichas) == 1
        assert len(errores) == 1
        assert errores[0].code == "GOV_CONTRACT_AMENDMENT_DRAFT_EXISTS"
        b = fichas[0]
        r = _delete_m(mundo, cid, b["id"], b["version"])
        assert r.status_code == 204
        b = _lista(
            mundo,
            f,
            cid,
            "PRORROGA",
            {"nueva_fecha_fin": (FIN + timedelta(days=20)).isoformat()},
            "doc-prorroga-con",
        )
        firmante = _cargo_firmante(mundo, ocupacion, "SIN_LIMITE")
        version = b["version"]
        mid = b["id"]

        def operacion_formalizar(s):
            ctx = CompanyContext(
                tenant_id=mundo.t1,
                company_id=mundo.company_a,
                company=None,
                user_id=uid,
            )
            user = s.get(User, uid)
            return formalizar_modificacion(
                s, ctx, user, cid, mid, version, {"firmante_cargo_id": firmante}
            )

        r1, r2 = carrera(mundo.factory, operacion_formalizar, operacion_formalizar)
        fichas = [r for r in (r1, r2) if isinstance(r, dict)]
        errores = [r for r in (r1, r2) if isinstance(r, ConflictError)]
        assert len(fichas) == 1
        assert fichas[0]["estado"] == "FORMALIZADA"
        assert len(errores) == 1
        assert errores[0].code in (
            "GOV_CONTRACT_AMENDMENT_STALE",
            "GOV_CONTRACT_AMENDMENT_ALREADY_FORMALIZED",
        )

    def test_inmutable_en_base(self, mundo, gobierno, ocupacion):
        f = _formalizado(mundo, ocupacion)
        cid = f["contrato"]["id"]
        b = _lista(
            mundo, f, cid, "ADENDA", {"delta_monto": "10000.00"}, "doc-inm"
        )
        cdp3 = _cdp(mundo, ocupacion, "10000.00", expediente_id=f["exp"]["id"])
        r = _put_m(
            mundo,
            cid,
            b["id"],
            [{"certificado_id": cdp3, "monto": "10000.00"}],
            b["version"],
        )
        assert r.status_code == 200
        b = r.json()
        firmante = _cargo_firmante(mundo, ocupacion, "SIN_LIMITE")
        r = _formalizar_m(mundo, cid, b["id"], firmante, b["version"])
        assert r.status_code == 200
        mid = r.json()["id"]
        with mundo.factory() as db:
            with pytest.raises(DBAPIError):
                db.execute(
                    text(
                        "UPDATE gov_contract_amendments SET motivo = 'X' "
                        "WHERE id = :id"
                    ),
                    {"id": mid},
                )
                db.commit()
            db.rollback()
            with pytest.raises(DBAPIError):
                db.execute(
                    text(
                        "DELETE FROM gov_contract_amendments WHERE id = :id"
                    ),
                    {"id": mid},
                )
                db.commit()
            db.rollback()
            with pytest.raises(DBAPIError):
                db.execute(
                    text(
                        "DELETE FROM gov_contract_amendment_allocations "
                        "WHERE amendment_id = :id"
                    ),
                    {"id": mid},
                )
                db.commit()
            db.rollback()
            with pytest.raises(DBAPIError):
                db.execute(
                    text(
                        "UPDATE gov_contracts SET fecha_fin = fecha_fin + 1 "
                        "WHERE id = :id"
                    ),
                    {"id": cid},
                )
                db.commit()
            db.rollback()
        r = _nueva(mundo, cid, "VARIACION")
        assert r.status_code == 201
        borrador = r.json()
        bid = borrador["id"]
        with mundo.factory() as db:
            with pytest.raises(DBAPIError):
                db.execute(
                    text(
                        "UPDATE gov_contract_amendments SET moneda = 'EUR' "
                        "WHERE id = :id"
                    ),
                    {"id": bid},
                )
                db.commit()
            db.rollback()

    def test_aislamiento_permisos_y_sod(self, mundo, gobierno, ocupacion):
        f = _formalizado(mundo, ocupacion)
        cid = f["contrato"]["id"]
        r = mundo.get(M(cid), "ub", mundo.company_b)
        assert r.status_code == 404
        assert r.json()["code"] == "GOV_CONTRACT_NOT_FOUND"
        r = _post(mundo, M(cid), "ub", mundo.company_b, {"tipo": "ADENDA"})
        assert r.status_code == 404
        b = _lista(
            mundo, f, cid, "PRORROGA", {}, "doc-aisla"
        )
        r = mundo.get(M(cid) + f"/{b['id']}", "ub", mundo.company_b)
        assert r.status_code == 404
        cuenta_con_permisos(mundo, "mod_lector", [("gobierno_contratos", "view")])
        r = _nueva(mundo, cid, "ADENDA", usuario="mod_lector")
        assert r.status_code == 403
        r = _delete_m(mundo, cid, b["id"], b["version"])
        assert r.status_code == 204
        regla = regla_vigente(
            mundo,
            proceso="PROC-03",
            accion_a="PROC03_MODIFICACION_PREPARAR",
            accion_b="PROC03_MODIFICACION_FORMALIZAR",
        )
        try:
            b2 = _lista(
                mundo,
                f,
                cid,
                "PRORROGA",
                {"nueva_fecha_fin": (FIN + timedelta(days=15)).isoformat()},
                "doc-sod",
            )
            firmante = _cargo_firmante(mundo, ocupacion, "SIN_LIMITE")
            r = _formalizar_m(mundo, cid, b2["id"], firmante, b2["version"])
            assert r.status_code == 409
            assert r.json()["code"] == "GOV_SOD_CONFLICT"
        finally:
            cerrar_regla(mundo, regla)

    def test_cdp_ajena_y_moneda(self, mundo, gobierno, ocupacion):
        f = _formalizado(mundo, ocupacion)
        cid = f["contrato"]["id"]
        b = _lista(
            mundo, f, cid, "ADENDA", {"delta_monto": "10000.00"}, "doc-cdp"
        )
        otro = _mundo_contrato(mundo, ocupacion)
        cdp_otro = _cdp(
            mundo, ocupacion, "10000.00", expediente_id=otro["exp"]["id"]
        )
        r = _put_m(
            mundo,
            cid,
            b["id"],
            [{"certificado_id": cdp_otro, "monto": "10000.00"}],
            b["version"],
        )
        assert r.status_code == 422
        assert r.json()["code"] == "GOV_CONTRACT_CERTIFICATE_INVALID"
        cdp_eur = _cdp(
            mundo,
            ocupacion,
            "10000.00",
            moneda="EUR",
            expediente_id=f["exp"]["id"],
        )
        r = _put_m(
            mundo,
            cid,
            b["id"],
            [{"certificado_id": cdp_eur, "monto": "10000.00"}],
            b["version"],
        )
        assert r.status_code == 422
        assert r.json()["code"] == "GOV_CONTRACT_CERTIFICATE_INVALID"
