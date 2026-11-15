import itertools
from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError

from app.core.company_context import CompanyContext
from app.core.errors import ConflictError, KontrolError
from app.modules.government import service_contratos_ejecucion, service_contratos_supervision
from app.modules.government.models import GovernmentBudgetCommitment, GovernmentContractValuation
from app.modules.government.service_contratos_ejecucion import presentar_valuacion, registrar_recepcion
from app.modules.identity_access.mfa_policy import SENSITIVE, classify
from app.modules.identity_access.models import User
from app.modules.organization.models import Company
from app.modules.setup.api import CATALOGO_DE_PERMISOS
from tests.concurrency import carrera
from tests.org06_ayudantes import cuerpo_vinculo, vinculo_activo
from tests.org06_guarda import cuenta_con_permisos
from tests.proc08_ayudantes import cargo_contrataciones
from tests.test_gov_bud01_ejercicio import ONLY_PG
from tests.test_gov_cnt01_contratos import C
from tests.test_gov_cnt04_supervisor import _acto_designante, _designar, _formalizado, _supervisor
from tests.test_gov_ctl01_reglas import cerrar_regla, eventos, regla_vigente
from tests.test_gov_ctl06_hallazgos import _post
from tests.test_gov_proc10_garantias import HOY, _doc

pytest_plugins = (
    "tests.conftest_multicompany",
    "tests.test_gov_ctl06_hallazgos",
    "tests.org04_ayudantes",
)

E = "/ejecucion"
_N = itertools.count(1)


def _uid(mundo, nombre="ua") -> str:
    with mundo.factory() as db:
        return db.scalar(select(User.id).where(User.username == nombre))


def _listo(mundo, ocupacion) -> dict:
    f = _formalizado(mundo, ocupacion)
    sup = _supervisor(mundo, ocupacion)
    acto = _acto_designante(mundo, ocupacion)
    r = _designar(mundo, f["contrato"]["id"], sup, acto, HOY)
    assert r.status_code == 201
    designacion_id = r.json()["vigente"]["id"]

    nombre = f"cnt03_sup_{next(_N)}"
    sup_uid = cuenta_con_permisos(
        mundo,
        nombre,
        [("gobierno_contratos", "view"), ("gobierno_contratos", "execute")],
    )
    vinculo_activo(mundo, cuerpo_vinculo(sup_uid, sup["funcionario_id"]))
    return {
        "cid": f["contrato"]["id"],
        "exp": f["exp"],
        "sup": sup,
        "f": f,
        "usuario": nombre,
        "designacion_id": designacion_id,
    }


def _d(mundo, exp, nombre):
    doc_id, _ = _doc(mundo, exp, nombre)
    return doc_id


def _p(mundo, cid, sufijo, cuerpo, usuario):
    return _post(mundo, f"{C}/{cid}{E}{sufijo}", usuario, mundo.company_a, cuerpo)


@ONLY_PG
def test_recorrido_bienes_completo(mundo, gobierno, ocupacion):
    datos = _listo(mundo, ocupacion)
    cid, exp = datos["cid"], datos["exp"]
    with mundo.factory() as db:
        antes = db.scalar(select(func.count()).select_from(GovernmentBudgetCommitment))

    r = mundo.get(f"{C}/{cid}{E}", datos["usuario"], mundo.company_a)
    assert r.status_code == 200
    assert r.json()["resumen"]["estado_ejecucion"] == "SIN_INICIAR"
    assert r.json()["acciones"]["iniciar"] is True

    r = _p(mundo, cid, "/inicio", {"fecha": HOY.isoformat(), "documento_id": _d(mundo, exp, "inicio")}, datos["usuario"])
    assert r.status_code == 201
    assert r.json()["resumen"]["estado_ejecucion"] == "EN_EJECUCION"
    assert eventos(mundo, "GOV_CONTRACT_EXEC_STARTED", exp["id"])

    r = _p(
        mundo,
        cid,
        "/hitos",
        {
            "descripcion": "Primera entrega",
            "fecha_prevista": HOY.isoformat(),
            "monto_previsto": "20000.00",
            "obligatorio": True,
        },
        datos["usuario"],
    )
    assert r.status_code == 201
    hito = next(h["id"] for h in r.json()["hitos"] if h["descripcion"] == "Primera entrega")

    r = _p(
        mundo,
        cid,
        "/entregables",
        {
            "descripcion": "Lote 1",
            "fecha_vencimiento": HOY.isoformat(),
            "obligatorio": True,
            "hito_id": hito,
        },
        datos["usuario"],
    )
    assert r.status_code == 201
    ent = next(e["id"] for e in r.json()["entregables"] if e["descripcion"] == "Lote 1")
    assert r.json()["hitos"][0]["cumplido"] is False

    r = _p(
        mundo,
        cid,
        f"/entregables/{ent}/entregas",
        {"fecha_entrega": HOY.isoformat(), "documento_id": _d(mundo, exp, "entrega1")},
        datos["usuario"],
    )
    assert r.status_code == 201
    entrega = next(e for e in r.json()["entregables"] if e["id"] == ent)["entregas"][-1]["id"]

    r = _p(
        mundo,
        cid,
        f"/entregas/{entrega}/revision",
        {"resultado": "CONFORME", "fecha_revision": HOY.isoformat()},
        datos["usuario"],
    )
    assert r.status_code == 201

    r = _p(
        mundo,
        cid,
        "/valuaciones",
        {
            "hito_id": hito,
            "periodo_desde": HOY.isoformat(),
            "periodo_hasta": HOY.isoformat(),
            "fecha": HOY.isoformat(),
            "monto": "15000.00",
            "documento_id": _d(mundo, exp, "val1"),
        },
        datos["usuario"],
    )
    assert r.status_code == 201
    val = next(
        v["id"]
        for v in r.json()["valuaciones"]
        if v["monto"] == "15000.00" and v["estado"] == "PRESENTADA"
    )

    r = _p(
        mundo,
        cid,
        f"/valuaciones/{val}/resolucion",
        {"resultado": "CONFORMADA", "fecha_conformidad": HOY.isoformat()},
        datos["usuario"],
    )
    assert r.status_code == 201
    assert r.json()["valuaciones"][0]["acumulado"] == "15000.00"
    assert r.json()["resumen"]["saldo"] == "35000.00"
    assert eventos(mundo, "GOV_CONTRACT_EXEC_VALUATION_CONFORMED", exp["id"])

    r = _p(
        mundo,
        cid,
        "/recepciones",
        {
            "tipo": "PARCIAL",
            "fecha": HOY.isoformat(),
            "documento_id": _d(mundo, exp, "rec1"),
            "hito_ids": [hito],
        },
        datos["usuario"],
    )
    assert r.status_code == 201
    recepcion = next(x for x in r.json()["recepciones"] if x["tipo"] == "PARCIAL")
    assert recepcion["referencia"] == "REC-01"
    assert next(h for h in r.json()["hitos"] if h["id"] == hito)["cumplido"] is True
    assert eventos(mundo, "GOV_CONTRACT_EXEC_RECEIPT_RECORDED", exp["id"])

    r = _p(
        mundo,
        cid,
        "/facturas",
        {
            "numero_documento": "F-0001",
            "fecha": HOY.isoformat(),
            "monto": "15000.00",
            "hito_id": hito,
            "recepcion_id": recepcion["id"],
            "documento_id": _d(mundo, exp, "fac1"),
            "fecha_conformidad": HOY.isoformat(),
        },
        datos["usuario"],
    )
    assert r.status_code == 201
    assert r.json()["resumen"]["facturado"] == "15000.00"
    assert eventos(mundo, "GOV_CONTRACT_EXEC_INVOICE_LINKED", exp["id"])

    r = _p(
        mundo,
        cid,
        "/recepciones",
        {"tipo": "DEFINITIVA", "fecha": HOY.isoformat(), "documento_id": _d(mundo, exp, "def1")},
        datos["usuario"],
    )
    assert r.status_code == 201

    r = _p(
        mundo,
        cid,
        "/cierre",
        {
            "fecha": HOY.isoformat(),
            "documento_id": _d(mundo, exp, "cierre1"),
            "evaluacion_documento_id": _d(mundo, exp, "eval1"),
        },
        datos["usuario"],
    )
    assert r.status_code == 201
    assert r.json()["resumen"]["estado_ejecucion"] == "CERRADA"
    assert r.json()["cierre"]["aprobador_tipo"] in ("COMISION", "UNIDAD_CONTRATANTE")
    assert eventos(mundo, "GOV_CONTRACT_EXEC_CLOSED", exp["id"])

    r = _p(
        mundo,
        cid,
        "/hitos",
        {
            "descripcion": "Despues cierre",
            "fecha_prevista": HOY.isoformat(),
            "monto_previsto": "10.00",
            "obligatorio": False,
        },
        datos["usuario"],
    )
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_CONTRACT_EXEC_CLOSED"

    with mundo.factory() as db:
        despues = db.scalar(select(func.count()).select_from(GovernmentBudgetCommitment))
    assert antes == despues


@ONLY_PG
def test_precondiciones(mundo, gobierno, ocupacion):
    datos = _listo(mundo, ocupacion)
    cid, exp = datos["cid"], datos["exp"]

    r = _p(
        mundo,
        cid,
        "/valuaciones",
        {
            "hito_id": "x",
            "periodo_desde": HOY.isoformat(),
            "periodo_hasta": HOY.isoformat(),
            "fecha": HOY.isoformat(),
            "monto": "1.00",
            "documento_id": _d(mundo, exp, "val-pre"),
        },
        datos["usuario"],
    )
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_CONTRACT_EXEC_NOT_STARTED"

    r = _p(
        mundo,
        cid,
        "/inicio",
        {"fecha": (HOY + timedelta(days=1)).isoformat(), "documento_id": _d(mundo, exp, "ini-mal")},
        datos["usuario"],
    )
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_CONTRACT_EXEC_DATE_INVALID"

    doc_inicio = _d(mundo, exp, "ini-ok")
    r = _p(mundo, cid, "/inicio", {"fecha": HOY.isoformat(), "documento_id": doc_inicio}, datos["usuario"])
    assert r.status_code == 201

    r = _p(
        mundo,
        cid,
        "/inicio",
        {"fecha": HOY.isoformat(), "documento_id": _d(mundo, exp, "ini-dupl")},
        datos["usuario"],
    )
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_CONTRACT_EXEC_ALREADY_STARTED"

    r = _p(
        mundo,
        cid,
        "/hitos",
        {
            "descripcion": "Hito doc",
            "fecha_prevista": HOY.isoformat(),
            "monto_previsto": "10.00",
            "obligatorio": False,
        },
        datos["usuario"],
    )
    assert r.status_code == 201
    hito = next(h["id"] for h in r.json()["hitos"] if h["descripcion"] == "Hito doc")

    r = _p(
        mundo,
        cid,
        "/valuaciones",
        {
            "hito_id": hito,
            "periodo_desde": HOY.isoformat(),
            "periodo_hasta": HOY.isoformat(),
            "fecha": HOY.isoformat(),
            "monto": "1.00",
            "documento_id": doc_inicio,
        },
        datos["usuario"],
    )
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_CONTRACT_EXEC_DOCUMENT_INVALID"


@ONLY_PG
def test_conformidad_solo_del_supervisor(mundo, gobierno, ocupacion):
    f = _formalizado(mundo, ocupacion)
    sup = _supervisor(mundo, ocupacion)
    acto = _acto_designante(mundo, ocupacion)
    _designar(mundo, f["contrato"]["id"], sup, acto, HOY)

    r = _p(
        mundo,
        f["contrato"]["id"],
        "/inicio",
        {"fecha": HOY.isoformat(), "documento_id": _d(mundo, f["exp"], "ini-403")},
        "ua",
    )
    assert r.status_code == 403
    assert r.json()["code"] == "GOV_CONTRACT_EXEC_NOT_SUPERVISOR"
    assert eventos(mundo, "GOV_CONTRACT_EXEC_BLOCKED", f["exp"]["id"])

    f2 = _formalizado(mundo, ocupacion)
    r = _p(
        mundo,
        f2["contrato"]["id"],
        "/inicio",
        {"fecha": HOY.isoformat(), "documento_id": _d(mundo, f2["exp"], "ini-sin-sup")},
        "ua",
    )
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_CONTRACT_EXEC_NO_SUPERVISOR"


@ONLY_PG
def test_supervisor_a_la_fecha_del_hecho(mundo, gobierno, ocupacion, monkeypatch):
    datos = _listo(mundo, ocupacion)
    cid, exp = datos["cid"], datos["exp"]
    r = _p(
        mundo,
        cid,
        "/inicio",
        {"fecha": HOY.isoformat(), "documento_id": _d(mundo, exp, "ini-4")},
        datos["usuario"],
    )
    assert r.status_code == 201
    r = _p(
        mundo,
        cid,
        "/hitos",
        {
            "descripcion": "Hito para valuar",
            "fecha_prevista": HOY.isoformat(),
            "monto_previsto": "50000.00",
            "obligatorio": True,
        },
        datos["usuario"],
    )
    assert r.status_code == 201
    hito = next(h["id"] for h in r.json()["hitos"] if h["descripcion"] == "Hito para valuar")

    monkeypatch.setattr(
        service_contratos_ejecucion,
        "hoy_de_negocio",
        lambda: HOY + timedelta(days=10),
    )
    monkeypatch.setattr(
        service_contratos_supervision,
        "hoy_de_negocio",
        lambda: HOY + timedelta(days=10),
    )

    sup_b = _supervisor(mundo, ocupacion)
    r = _designar(
        mundo,
        cid,
        sup_b,
        _acto_designante(mundo, ocupacion),
        HOY + timedelta(days=5),
        motivo="Traslado",
        sustituye_id=datos["designacion_id"],
    )
    assert r.status_code == 201

    r = _p(
        mundo,
        cid,
        "/valuaciones",
        {
            "hito_id": hito,
            "periodo_desde": HOY.isoformat(),
            "periodo_hasta": (HOY + timedelta(days=3)).isoformat(),
            "fecha": (HOY + timedelta(days=3)).isoformat(),
            "monto": "1000.00",
            "documento_id": _d(mundo, exp, "val-a"),
        },
        datos["usuario"],
    )
    assert r.status_code == 201
    val_a = next(
        v["id"] for v in r.json()["valuaciones"] if v["fecha"] == (HOY + timedelta(days=3)).isoformat()
    )
    r = _p(
        mundo,
        cid,
        f"/valuaciones/{val_a}/resolucion",
        {"resultado": "CONFORMADA", "fecha_conformidad": (HOY + timedelta(days=4)).isoformat()},
        datos["usuario"],
    )
    assert r.status_code == 201

    r = _p(
        mundo,
        cid,
        "/valuaciones",
        {
            "hito_id": hito,
            "periodo_desde": (HOY + timedelta(days=4)).isoformat(),
            "periodo_hasta": (HOY + timedelta(days=6)).isoformat(),
            "fecha": (HOY + timedelta(days=6)).isoformat(),
            "monto": "1000.00",
            "documento_id": _d(mundo, exp, "val-b"),
        },
        datos["usuario"],
    )
    assert r.status_code == 201
    val_b = next(
        v["id"] for v in r.json()["valuaciones"] if v["fecha"] == (HOY + timedelta(days=6)).isoformat()
    )
    r = _p(
        mundo,
        cid,
        f"/valuaciones/{val_b}/resolucion",
        {"resultado": "CONFORMADA", "fecha_conformidad": (HOY + timedelta(days=6)).isoformat()},
        datos["usuario"],
    )
    assert r.status_code == 403
    assert r.json()["code"] == "GOV_CONTRACT_EXEC_NOT_SUPERVISOR"


@ONLY_PG
def test_tope_de_valuaciones(mundo, gobierno, ocupacion):
    datos = _listo(mundo, ocupacion)
    cid, exp = datos["cid"], datos["exp"]
    _p(mundo, cid, "/inicio", {"fecha": HOY.isoformat(), "documento_id": _d(mundo, exp, "ini-5")}, datos["usuario"])

    r = _p(
        mundo,
        cid,
        "/hitos",
        {"descripcion": "H", "fecha_prevista": HOY.isoformat(), "obligatorio": True},
        datos["usuario"],
    )
    assert r.status_code == 201
    hito = next(h["id"] for h in r.json()["hitos"] if h["descripcion"] == "H")

    r = _p(
        mundo,
        cid,
        "/valuaciones",
        {
            "hito_id": hito,
            "periodo_desde": HOY.isoformat(),
            "periodo_hasta": HOY.isoformat(),
            "fecha": HOY.isoformat(),
            "monto": "60000.00",
            "documento_id": _d(mundo, exp, "val-60"),
        },
        datos["usuario"],
    )
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_CONTRACT_EXEC_VALUATION_EXCEEDS_CONTRACT"
    assert eventos(mundo, "GOV_CONTRACT_EXEC_BLOCKED", exp["id"])

    r = _p(
        mundo,
        cid,
        "/valuaciones",
        {
            "hito_id": hito,
            "periodo_desde": HOY.isoformat(),
            "periodo_hasta": HOY.isoformat(),
            "fecha": HOY.isoformat(),
            "monto": "30000.00",
            "documento_id": _d(mundo, exp, "val-30"),
        },
        datos["usuario"],
    )
    assert r.status_code == 201
    val = next(
        v["id"] for v in r.json()["valuaciones"] if v["monto"] == "30000.00" and v["estado"] == "PRESENTADA"
    )

    r = _p(
        mundo,
        cid,
        "/valuaciones",
        {
            "hito_id": hito,
            "periodo_desde": HOY.isoformat(),
            "periodo_hasta": HOY.isoformat(),
            "fecha": HOY.isoformat(),
            "monto": "25000.00",
            "documento_id": _d(mundo, exp, "val-25"),
        },
        datos["usuario"],
    )
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_CONTRACT_EXEC_VALUATION_EXCEEDS_CONTRACT"

    r = _p(mundo, cid, f"/valuaciones/{val}/anular", {"motivo": "Error"}, datos["usuario"])
    assert r.status_code == 201

    r = _p(
        mundo,
        cid,
        "/valuaciones",
        {
            "hito_id": hito,
            "periodo_desde": HOY.isoformat(),
            "periodo_hasta": HOY.isoformat(),
            "fecha": HOY.isoformat(),
            "monto": "25000.00",
            "documento_id": _d(mundo, exp, "val-25b"),
        },
        datos["usuario"],
    )
    assert r.status_code == 201


@ONLY_PG
def test_factura_requiere_recepcion_y_tope(mundo, gobierno, ocupacion):
    datos = _listo(mundo, ocupacion)
    cid, exp = datos["cid"], datos["exp"]
    _p(mundo, cid, "/inicio", {"fecha": HOY.isoformat(), "documento_id": _d(mundo, exp, "ini-6")}, datos["usuario"])

    r = _p(
        mundo,
        cid,
        "/hitos",
        {"descripcion": "A", "fecha_prevista": HOY.isoformat(), "monto_previsto": "10000.00", "obligatorio": True},
        datos["usuario"],
    )
    assert r.status_code == 201
    r = _p(
        mundo,
        cid,
        "/hitos",
        {"descripcion": "B", "fecha_prevista": HOY.isoformat(), "monto_previsto": "10000.00", "obligatorio": True},
        datos["usuario"],
    )
    assert r.status_code == 201
    hito_a = next(h["id"] for h in r.json()["hitos"] if h["descripcion"] == "A")
    hito_b = next(h["id"] for h in r.json()["hitos"] if h["descripcion"] == "B")

    r = _p(
        mundo,
        cid,
        "/valuaciones",
        {
            "hito_id": hito_a,
            "periodo_desde": HOY.isoformat(),
            "periodo_hasta": HOY.isoformat(),
            "fecha": HOY.isoformat(),
            "monto": "10000.00",
            "documento_id": _d(mundo, exp, "val-a-10"),
        },
        datos["usuario"],
    )
    assert r.status_code == 201
    val = next(
        v["id"] for v in r.json()["valuaciones"] if v["monto"] == "10000.00" and v["estado"] == "PRESENTADA"
    )
    _p(
        mundo,
        cid,
        f"/valuaciones/{val}/resolucion",
        {"resultado": "CONFORMADA", "fecha_conformidad": HOY.isoformat()},
        datos["usuario"],
    )

    r = _p(
        mundo,
        cid,
        "/recepciones",
        {
            "tipo": "PARCIAL",
            "fecha": HOY.isoformat(),
            "documento_id": _d(mundo, exp, "rec-b"),
            "hito_ids": [hito_b],
        },
        datos["usuario"],
    )
    assert r.status_code == 201
    rec_b = next(x for x in r.json()["recepciones"] if x["tipo"] == "PARCIAL")

    r = _p(
        mundo,
        cid,
        "/facturas",
        {
            "numero_documento": "F-x",
            "fecha": HOY.isoformat(),
            "monto": "10000.00",
            "hito_id": hito_a,
            "recepcion_id": rec_b["id"],
            "documento_id": _d(mundo, exp, "fac-x"),
            "fecha_conformidad": HOY.isoformat(),
        },
        datos["usuario"],
    )
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_CONTRACT_EXEC_RECEIPT_INVALID"

    r = _p(
        mundo,
        cid,
        "/recepciones",
        {
            "tipo": "PARCIAL",
            "fecha": HOY.isoformat(),
            "documento_id": _d(mundo, exp, "rec-a"),
            "hito_ids": [hito_a],
        },
        datos["usuario"],
    )
    assert r.status_code == 201
    rec_a = next(x for x in r.json()["recepciones"] if x["tipo"] == "PARCIAL" and hito_a in x["hito_ids"])

    r = _p(
        mundo,
        cid,
        "/facturas",
        {
            "numero_documento": "F-exc",
            "fecha": HOY.isoformat(),
            "monto": "12000.00",
            "hito_id": hito_a,
            "recepcion_id": rec_a["id"],
            "documento_id": _d(mundo, exp, "fac-exc"),
            "fecha_conformidad": HOY.isoformat(),
        },
        datos["usuario"],
    )
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_CONTRACT_EXEC_INVOICE_EXCEEDS_VALUED"

    r = _p(
        mundo,
        cid,
        "/facturas",
        {
            "numero_documento": "F-1",
            "fecha": HOY.isoformat(),
            "monto": "10000.00",
            "hito_id": hito_a,
            "recepcion_id": rec_a["id"],
            "documento_id": _d(mundo, exp, "fac-1"),
            "fecha_conformidad": HOY.isoformat(),
        },
        datos["usuario"],
    )
    assert r.status_code == 201

    r = _p(
        mundo,
        cid,
        "/facturas",
        {
            "numero_documento": "F-1",
            "fecha": HOY.isoformat(),
            "monto": "10000.00",
            "hito_id": hito_a,
            "recepcion_id": rec_a["id"],
            "documento_id": _d(mundo, exp, "fac-1-dup"),
            "fecha_conformidad": HOY.isoformat(),
        },
        datos["usuario"],
    )
    assert r.status_code in (409, 422)
    assert r.json()["code"] in ("GOV_CONTRACT_EXEC_INVOICE_DUPLICATE", "GOV_CONTRACT_EXEC_INVOICE_EXCEEDS_VALUED")

    r = _p(mundo, cid, f"/recepciones/{rec_a['id']}/anular", {"motivo": "Prueba"}, datos["usuario"])
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_CONTRACT_EXEC_IN_USE"


@ONLY_PG
def test_flujo_obras_con_garantia(mundo, gobierno, ocupacion, monkeypatch):
    datos = _listo(mundo, ocupacion)
    cid, exp = datos["cid"], datos["exp"]

    with mundo.factory() as db:
        db.execute(
            text("UPDATE gov_procurement_files SET tipo_contratacion = 'OBRAS' WHERE id = :id"),
            {"id": exp["id"]},
        )
        db.commit()

    _p(mundo, cid, "/inicio", {"fecha": HOY.isoformat(), "documento_id": _d(mundo, exp, "ini-7")}, datos["usuario"])

    r = _p(
        mundo,
        cid,
        "/hitos",
        {
            "descripcion": "Hito obras",
            "fecha_prevista": HOY.isoformat(),
            "monto_previsto": "50000.00",
            "obligatorio": True,
        },
        datos["usuario"],
    )
    assert r.status_code == 201
    hito = next(h["id"] for h in r.json()["hitos"] if h["descripcion"] == "Hito obras")

    r = _p(
        mundo,
        cid,
        "/recepciones",
        {
            "tipo": "PARCIAL",
            "fecha": HOY.isoformat(),
            "documento_id": _d(mundo, exp, "rec-par-7"),
            "hito_ids": [hito],
        },
        datos["usuario"],
    )
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_CONTRACT_EXEC_RECEIPT_TYPE_INVALID"

    r = _p(
        mundo,
        cid,
        "/recepciones",
        {
            "tipo": "PROVISIONAL",
            "fecha": HOY.isoformat(),
            "documento_id": _d(mundo, exp, "rec-prov-7"),
            "representante_cargo_id": cargo_contrataciones(mundo, ocupacion),
            "fin_garantia": (HOY + timedelta(days=30)).isoformat(),
        },
        datos["usuario"],
    )
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_CONTRACT_EXEC_RECEIPT_NOT_READY"

    r = _p(
        mundo,
        cid,
        "/terminacion",
        {"fecha": HOY.isoformat(), "documento_id": _d(mundo, exp, "term-7")},
        datos["usuario"],
    )
    assert r.status_code == 201

    r = _p(
        mundo,
        cid,
        "/recepciones",
        {
            "tipo": "PROVISIONAL",
            "fecha": HOY.isoformat(),
            "documento_id": _d(mundo, exp, "rec-prov-7"),
            "representante_cargo_id": cargo_contrataciones(mundo, ocupacion),
            "fin_garantia": (HOY + timedelta(days=30)).isoformat(),
        },
        datos["usuario"],
    )
    assert r.status_code == 201

    r = _p(
        mundo,
        cid,
        "/recepciones",
        {
            "tipo": "DEFINITIVA",
            "fecha": HOY.isoformat(),
            "documento_id": _d(mundo, exp, "def-7"),
            "representante_cargo_id": cargo_contrataciones(mundo, ocupacion),
        },
        datos["usuario"],
    )
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_CONTRACT_EXEC_WARRANTY_PENDING"

    monkeypatch.setattr(
        service_contratos_ejecucion,
        "hoy_de_negocio",
        lambda: HOY + timedelta(days=31),
    )
    monkeypatch.setattr(
        service_contratos_supervision,
        "hoy_de_negocio",
        lambda: HOY + timedelta(days=31),
    )

    r = _p(
        mundo,
        cid,
        "/recepciones",
        {
            "tipo": "DEFINITIVA",
            "fecha": (HOY + timedelta(days=31)).isoformat(),
            "documento_id": _d(mundo, exp, "def-7b"),
            "representante_cargo_id": cargo_contrataciones(mundo, ocupacion),
        },
        datos["usuario"],
    )
    assert r.status_code == 201


@ONLY_PG
def test_concurrencia_valuaciones(mundo, gobierno, ocupacion):
    datos = _listo(mundo, ocupacion)
    cid, exp = datos["cid"], datos["exp"]
    _p(mundo, cid, "/inicio", {"fecha": HOY.isoformat(), "documento_id": _d(mundo, exp, "ini-8")}, datos["usuario"])

    r = _p(
        mundo,
        cid,
        "/hitos",
        {"descripcion": "H8", "fecha_prevista": HOY.isoformat(), "obligatorio": True},
        datos["usuario"],
    )
    assert r.status_code == 201
    hito = next(h["id"] for h in r.json()["hitos"] if h["descripcion"] == "H8")

    d1 = _d(mundo, exp, "val-8a")
    d2 = _d(mundo, exp, "val-8b")
    uid = _uid(mundo, datos["usuario"])

    def ctx_de(s):
        return CompanyContext(
            tenant_id=mundo.t1,
            company_id=mundo.company_a,
            company=s.get(Company, mundo.company_a),
            user_id=uid,
        )

    def op1(s):
        return presentar_valuacion(
            s,
            ctx_de(s),
            cid,
            {
                "hito_id": hito,
                "periodo_desde": HOY,
                "periodo_hasta": HOY,
                "fecha": HOY,
                "monto": Decimal("30000.00"),
                "documento_id": d1,
            },
        )

    def op2(s):
        return presentar_valuacion(
            s,
            ctx_de(s),
            cid,
            {
                "hito_id": hito,
                "periodo_desde": HOY,
                "periodo_hasta": HOY,
                "fecha": HOY,
                "monto": Decimal("30000.00"),
                "documento_id": d2,
            },
        )

    r1, r2 = carrera(mundo.factory, op1, op2)
    ok = sum(isinstance(r, dict) for r in (r1, r2))
    assert ok == 1
    err = next(r for r in (r1, r2) if isinstance(r, KontrolError))
    assert err.code == "GOV_CONTRACT_EXEC_VALUATION_EXCEEDS_CONTRACT"

    with mundo.factory() as db:
        suma = db.scalar(
            select(func.coalesce(func.sum(GovernmentContractValuation.monto), 0)).where(
                GovernmentContractValuation.contract_id == cid,
                GovernmentContractValuation.estado == "PRESENTADA",
            )
        )
        assert Decimal(suma) <= Decimal("50000.00")


@ONLY_PG
def test_concurrencia_definitiva(mundo, gobierno, ocupacion):
    datos = _listo(mundo, ocupacion)
    cid, exp = datos["cid"], datos["exp"]
    _p(mundo, cid, "/inicio", {"fecha": HOY.isoformat(), "documento_id": _d(mundo, exp, "ini-9")}, datos["usuario"])

    d1 = _d(mundo, exp, "def-9a")
    d2 = _d(mundo, exp, "def-9b")
    uid = _uid(mundo, datos["usuario"])

    def ctx_de(s):
        return CompanyContext(
            tenant_id=mundo.t1,
            company_id=mundo.company_a,
            company=s.get(Company, mundo.company_a),
            user_id=uid,
        )

    def op1(s):
        return registrar_recepcion(
            s,
            ctx_de(s),
            cid,
            {
                "tipo": "DEFINITIVA",
                "fecha": HOY,
                "documento_id": d1,
                "observacion": None,
                "hito_ids": [],
                "representante_cargo_id": None,
                "fin_garantia": None,
            },
        )

    def op2(s):
        return registrar_recepcion(
            s,
            ctx_de(s),
            cid,
            {
                "tipo": "DEFINITIVA",
                "fecha": HOY,
                "documento_id": d2,
                "observacion": None,
                "hito_ids": [],
                "representante_cargo_id": None,
                "fin_garantia": None,
            },
        )

    r1, r2 = carrera(mundo.factory, op1, op2)
    ok = sum(isinstance(r, dict) for r in (r1, r2))
    assert ok == 1
    err = next(r for r in (r1, r2) if isinstance(r, ConflictError))
    assert err.code == "GOV_CONTRACT_EXEC_CONFLICT"


@ONLY_PG
def test_inmutable_en_base(mundo, gobierno, ocupacion):
    datos = _listo(mundo, ocupacion)
    cid, exp = datos["cid"], datos["exp"]
    _p(mundo, cid, "/inicio", {"fecha": HOY.isoformat(), "documento_id": _d(mundo, exp, "ini-10")}, datos["usuario"])

    r = _p(
        mundo,
        cid,
        "/hitos",
        {"descripcion": "H10", "fecha_prevista": HOY.isoformat(), "obligatorio": True},
        datos["usuario"],
    )
    assert r.status_code == 201
    hito = next(h["id"] for h in r.json()["hitos"] if h["descripcion"] == "H10")

    r = _p(
        mundo,
        cid,
        "/valuaciones",
        {
            "hito_id": hito,
            "periodo_desde": HOY.isoformat(),
            "periodo_hasta": HOY.isoformat(),
            "fecha": HOY.isoformat(),
            "monto": "1000.00",
            "documento_id": _d(mundo, exp, "val-10"),
        },
        datos["usuario"],
    )
    assert r.status_code == 201
    val = next(
        v["id"] for v in r.json()["valuaciones"] if v["monto"] == "1000.00" and v["estado"] == "PRESENTADA"
    )
    _p(
        mundo,
        cid,
        f"/valuaciones/{val}/resolucion",
        {"resultado": "CONFORMADA", "fecha_conformidad": HOY.isoformat()},
        datos["usuario"],
    )

    sqls = [
        "UPDATE gov_contract_execution_acts SET observacion='X'",
        f"DELETE FROM gov_contract_milestones WHERE contract_id='{cid}'",
        f"UPDATE gov_contract_valuations SET monto = 1 WHERE contract_id='{cid}'",
        f"UPDATE gov_contract_valuations SET estado = 'PRESENTADA' WHERE contract_id='{cid}'",
        "TRUNCATE gov_contract_invoices",
    ]
    for sql in sqls:
        with mundo.factory() as db:
            with pytest.raises(DBAPIError):
                db.execute(text(sql))
                db.commit()
            db.rollback()


@ONLY_PG
def test_aislamiento(mundo, gobierno, ocupacion):
    datos = _listo(mundo, ocupacion)
    r = mundo.get(f"{C}/{datos['cid']}{E}", "ua", mundo.company_b)
    assert r.status_code == 404


@ONLY_PG
def test_permisos_mfa_y_sod(mundo, gobierno, ocupacion):
    assert classify("gobierno_contratos:execute") == SENSITIVE
    assert "execute" in CATALOGO_DE_PERMISOS["gobierno_contratos"]

    lectura_id = cuenta_con_permisos(mundo, "cnt03_lector", [("gobierno_contratos", "view")])
    assert lectura_id

    datos = _listo(mundo, ocupacion)
    cid = datos["cid"]

    r = mundo.get(f"{C}/{cid}{E}", "cnt03_lector", mundo.company_a)
    assert r.status_code == 200

    r = _p(
        mundo,
        cid,
        "/inicio",
        {"fecha": HOY.isoformat(), "documento_id": _d(mundo, datos["exp"], "ini-12")},
        "cnt03_lector",
    )
    assert r.status_code == 403

    regla = regla_vigente(
        mundo,
        proceso="PROC-03",
        accion_a="PROC03_EJEC_INICIAR",
        accion_b="PROC03_EJEC_CONFORMAR",
    )
    try:
        r = _p(
            mundo,
            cid,
            "/inicio",
            {"fecha": HOY.isoformat(), "documento_id": _d(mundo, datos["exp"], "ini-12b")},
            datos["usuario"],
        )
        assert r.status_code == 201

        r = _p(
            mundo,
            cid,
            "/hitos",
            {"descripcion": "H12", "fecha_prevista": HOY.isoformat(), "obligatorio": True},
            datos["usuario"],
        )
        assert r.status_code == 201
        hito = next(h["id"] for h in r.json()["hitos"] if h["descripcion"] == "H12")

        r = _p(
            mundo,
            cid,
            "/entregables",
            {
                "descripcion": "E12",
                "fecha_vencimiento": HOY.isoformat(),
                "obligatorio": True,
                "hito_id": hito,
            },
            datos["usuario"],
        )
        assert r.status_code == 201
        ent = next(e["id"] for e in r.json()["entregables"] if e["descripcion"] == "E12")

        r = _p(
            mundo,
            cid,
            f"/entregables/{ent}/entregas",
            {"fecha_entrega": HOY.isoformat(), "documento_id": _d(mundo, datos["exp"], "e12-1")},
            datos["usuario"],
        )
        assert r.status_code == 201
        entrega = next(e for e in r.json()["entregables"] if e["id"] == ent)["entregas"][-1]["id"]

        r = _p(
            mundo,
            cid,
            f"/entregas/{entrega}/revision",
            {"resultado": "CONFORME", "fecha_revision": HOY.isoformat()},
            datos["usuario"],
        )
        assert r.status_code == 409
        assert r.json()["code"] == "GOV_SOD_CONFLICT"
    finally:
        cerrar_regla(mundo, regla)


@ONLY_PG
def test_entregas_y_anulaciones(mundo, gobierno, ocupacion):
    datos = _listo(mundo, ocupacion)
    cid, exp = datos["cid"], datos["exp"]
    _p(mundo, cid, "/inicio", {"fecha": HOY.isoformat(), "documento_id": _d(mundo, exp, "ini-13")}, datos["usuario"])

    r = _p(
        mundo,
        cid,
        "/hitos",
        {"descripcion": "H13", "fecha_prevista": HOY.isoformat(), "obligatorio": True},
        datos["usuario"],
    )
    assert r.status_code == 201
    hito = next(h["id"] for h in r.json()["hitos"] if h["descripcion"] == "H13")

    r = _p(
        mundo,
        cid,
        "/entregables",
        {
            "descripcion": "E13",
            "fecha_vencimiento": HOY.isoformat(),
            "obligatorio": True,
            "hito_id": hito,
        },
        datos["usuario"],
    )
    assert r.status_code == 201
    ent = next(e["id"] for e in r.json()["entregables"] if e["descripcion"] == "E13")

    r = _p(
        mundo,
        cid,
        f"/entregables/{ent}/entregas",
        {"fecha_entrega": HOY.isoformat(), "documento_id": _d(mundo, exp, "e13-1")},
        datos["usuario"],
    )
    assert r.status_code == 201
    entrega = next(e for e in r.json()["entregables"] if e["id"] == ent)["entregas"][-1]["id"]

    r = _p(
        mundo,
        cid,
        f"/entregables/{ent}/entregas",
        {"fecha_entrega": HOY.isoformat(), "documento_id": _d(mundo, exp, "e13-1b")},
        datos["usuario"],
    )
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_CONTRACT_EXEC_SUBMISSION_OPEN"

    r = _p(
        mundo,
        cid,
        f"/entregas/{entrega}/revision",
        {"resultado": "RECHAZADA", "fecha_revision": HOY.isoformat()},
        datos["usuario"],
    )
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_CONTRACT_EXEC_REASON_REQUIRED"

    r = _p(
        mundo,
        cid,
        f"/entregas/{entrega}/revision",
        {"resultado": "RECHAZADA", "fecha_revision": HOY.isoformat(), "observacion": "Incompleto"},
        datos["usuario"],
    )
    assert r.status_code == 201

    r = _p(
        mundo,
        cid,
        f"/entregables/{ent}/entregas",
        {"fecha_entrega": HOY.isoformat(), "documento_id": _d(mundo, exp, "e13-2")},
        datos["usuario"],
    )
    assert r.status_code == 201
    entrega2 = next(e for e in r.json()["entregables"] if e["id"] == ent)["entregas"][-1]["id"]

    r = _p(
        mundo,
        cid,
        f"/entregas/{entrega2}/revision",
        {"resultado": "CONFORME", "fecha_revision": HOY.isoformat()},
        datos["usuario"],
    )
    assert r.status_code == 201

    r = _p(
        mundo,
        cid,
        f"/entregables/{ent}/entregas",
        {"fecha_entrega": HOY.isoformat(), "documento_id": _d(mundo, exp, "e13-3")},
        datos["usuario"],
    )
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_CONTRACT_EXEC_SUBMISSION_INVALID"

    r = _p(mundo, cid, f"/entregables/{ent}/anular", {"motivo": "Usado"}, datos["usuario"])
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_CONTRACT_EXEC_IN_USE"

    r = _p(
        mundo,
        cid,
        "/hitos",
        {"descripcion": "H13b", "fecha_prevista": HOY.isoformat(), "obligatorio": False},
        datos["usuario"],
    )
    assert r.status_code == 201
    hito_anular = next(h["id"] for h in r.json()["hitos"] if h["descripcion"] == "H13b")

    r = _p(mundo, cid, f"/hitos/{hito_anular}/anular", {"motivo": "No aplica"}, datos["usuario"])
    assert r.status_code == 201
    assert next(h for h in r.json()["hitos"] if h["id"] == hito_anular)["estado"] == "ANULADO"


@ONLY_PG
def test_reporte_csv(mundo, gobierno, ocupacion):
    datos = _listo(mundo, ocupacion)
    cid, exp = datos["cid"], datos["exp"]
    _p(mundo, cid, "/inicio", {"fecha": HOY.isoformat(), "documento_id": _d(mundo, exp, "ini-14")}, datos["usuario"])

    r = mundo.get(f"{C}/{cid}{E}/reporte.csv", "ua", mundo.company_a)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert r.text.splitlines()[0] == "fecha,tipo,referencia,titulo,monto,moneda,estado"
