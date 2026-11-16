from datetime import timedelta
from uuid import uuid4

from app.modules.government import service_garantias
from app.modules.government.models import (
    GovernmentBudgetCommitment,
    GovernmentContract,
    GovernmentContractDeliverable,
    GovernmentContractMilestone,
    GovernmentGuaranteeInstrument,
)
from app.modules.government.service_contratos_alertas import (
    ROUTE_EJECUCION,
    SOURCE_CONTRATO,
    SOURCE_ENTREGABLE,
    SOURCE_GARANTIA,
    SOURCE_HITO,
    SOURCES,
    clave,
    fase,
    fase_garantia,
    reconciliar,
)
from app.modules.notifications.models import Alert
from app.modules.scheduler.registry import manejadores
from app.modules.scheduler.service import tick
from app.shared.clock import instante_actual
from tests.concurrency import carrera
from tests.org06_guarda import cuenta_con_permisos
from tests.test_gov_bud01_ejercicio import ONLY_PG
from tests.test_gov_cnt01_contratos import C, _cargo_firmante
from tests.test_gov_cnt02_modificaciones import FIN, _formalizar_m, _nueva, _patch_m
from tests.test_gov_cnt03_ejecucion import _d, _listo, _p
from tests.test_gov_ctl01_reglas import eventos
from tests.test_gov_proc10_garantias import (
    HOY,
    _adjudicado,
    _doc,
    _emisor,
    _gar,
    _post_g,
)

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos", "tests.org04_ayudantes")


def _rec(mundo, hoy):
    db = mundo.factory()
    try:
        creadas, resueltas = reconciliar(db, mundo.company_a, hoy, instante_actual(), None)
        db.commit()
        return creadas, resueltas
    finally:
        db.close()


def _alertas(mundo, source_id=None, empresa=None):
    empresa = empresa or mundo.company_a
    db = mundo.factory()
    try:
        q = (
            db.query(Alert)
            .filter(Alert.company_id == empresa, Alert.source_type.in_(SOURCES))
        )
        if source_id is not None:
            q = q.filter(Alert.source_id == source_id)
        filas = q.order_by(Alert.created_at, Alert.id).all()
        return [{"id": a.id, "status": a.status, "source_type": a.source_type,
                 "source_id": a.source_id, "source_item_id": a.source_item_id,
                 "severity": a.severity, "dedupe_key": a.dedupe_key,
                 "resolved_at": a.resolved_at} for a in filas]
    finally:
        db.close()


def _activas(mundo, source_id=None, empresa=None):
    return [a for a in _alertas(mundo, source_id, empresa) if a["status"] == "ACTIVE"]


def _sin_preaviso(mundo):
    r = mundo.put_json("/gobierno/contratos-alertas/politicas", "ua", mundo.company_a,
                       {"items": [{"fuente": "CONTRATO", "activo": False, "dias_anticipacion": None},
                                  {"fuente": "HITO", "activo": False, "dias_anticipacion": None},
                                  {"fuente": "ENTREGABLE", "activo": False, "dias_anticipacion": None}]})
    assert r.status_code == 200, r.text


def _iniciado(mundo, ocupacion):
    datos = _listo(mundo, ocupacion)
    r = _p(mundo, datos["cid"], "/inicio",
           {"fecha": HOY.isoformat(), "documento_id": _d(mundo, datos["exp"], "inicio")}, datos["usuario"])
    assert r.status_code == 201, r.text
    return datos


@ONLY_PG
def test_fase_y_fase_garantia_unitarias(monkeypatch):
    hoy = HOY
    assert fase(hoy + timedelta(days=1), hoy, None) is None
    assert fase(hoy + timedelta(days=3), hoy, 3) == "UPCOMING"
    assert fase(hoy + timedelta(days=4), hoy, 3) is None
    assert fase(hoy, hoy, 3) == "DUE_TODAY"
    assert fase(hoy - timedelta(days=1), hoy, 3) == "OVERDUE"

    inst = GovernmentGuaranteeInstrument(estado="REGISTRADA", vigente_desde=hoy - timedelta(days=30),
                                         vigente_hasta=hoy + timedelta(days=16))
    assert fase_garantia(inst, hoy) is None
    inst.vigente_hasta = hoy + timedelta(days=15)
    assert fase_garantia(inst, hoy) == "UPCOMING"
    inst.vigente_hasta = hoy
    assert fase_garantia(inst, hoy) == "DUE_TODAY"
    inst.vigente_hasta = hoy - timedelta(days=1)
    assert fase_garantia(inst, hoy) == "OVERDUE"
    inst.estado = "RENOVADA"
    assert fase_garantia(inst, hoy) is None

    monkeypatch.setattr(service_garantias, "DIAS_POR_VENCER", 3)
    inst = GovernmentGuaranteeInstrument(estado="REGISTRADA", vigente_desde=hoy - timedelta(days=30),
                                         vigente_hasta=hoy + timedelta(days=4))
    assert fase_garantia(inst, hoy) is None
    inst.vigente_hasta = hoy + timedelta(days=3)
    assert fase_garantia(inst, hoy) == "UPCOMING"


@ONLY_PG
def test_hito_y_entregable_vencen_hoy_sin_efectos_y_se_resuelven(mundo, gobierno, ocupacion):
    _sin_preaviso(mundo)
    datos = _iniciado(mundo, ocupacion)
    cid = datos["cid"]
    exp = datos["exp"]

    r = _p(mundo, cid, "/hitos", {"descripcion": "Primera entrega", "fecha_prevista": HOY.isoformat(),
                                  "monto_previsto": "20000.00", "obligatorio": True}, datos["usuario"])
    assert r.status_code == 201, r.text
    hito = next(h["id"] for h in r.json()["hitos"] if h["descripcion"] == "Primera entrega")

    r = _p(mundo, cid, "/entregables", {"descripcion": "Lote 1", "fecha_vencimiento": HOY.isoformat(),
                                        "obligatorio": True, "hito_id": hito}, datos["usuario"])
    assert r.status_code == 201, r.text
    ent = next(e["id"] for e in r.json()["entregables"] if e["descripcion"] == "Lote 1")

    db = mundo.factory()
    try:
        foto = (
            db.query(GovernmentContract).filter(GovernmentContract.id == cid).one().version,
            db.query(GovernmentContractMilestone).filter(GovernmentContractMilestone.id == hito).one().estado,
            db.query(GovernmentContractDeliverable).filter(GovernmentContractDeliverable.id == ent).one().estado,
            db.query(GovernmentBudgetCommitment).count(),
        )
    finally:
        db.close()

    _rec(mundo, HOY)
    activas = _activas(mundo, cid)
    assert len(activas) == 2
    por_tipo = {a["source_type"]: a for a in activas}
    assert por_tipo[SOURCE_HITO]["source_item_id"] == hito
    assert por_tipo[SOURCE_HITO]["severity"] == "WARNING"
    assert por_tipo[SOURCE_HITO]["dedupe_key"] == clave("milestone", hito, HOY, "DUE_TODAY")
    assert por_tipo[SOURCE_HITO]["source_id"] == cid
    assert por_tipo[SOURCE_ENTREGABLE]["source_item_id"] == ent
    assert SOURCE_CONTRATO not in por_tipo

    _rec(mundo, HOY)
    assert len(_alertas(mundo, cid)) == 2

    db = mundo.factory()
    try:
        foto2 = (
            db.query(GovernmentContract).filter(GovernmentContract.id == cid).one().version,
            db.query(GovernmentContractMilestone).filter(GovernmentContractMilestone.id == hito).one().estado,
            db.query(GovernmentContractDeliverable).filter(GovernmentContractDeliverable.id == ent).one().estado,
            db.query(GovernmentBudgetCommitment).count(),
        )
    finally:
        db.close()
    assert foto == foto2

    r = _p(mundo, cid, f"/entregables/{ent}/entregas",
           {"fecha_entrega": HOY.isoformat(), "documento_id": _d(mundo, exp, "entrega1")}, datos["usuario"])
    assert r.status_code == 201, r.text
    entrega = next(e for e in r.json()["entregables"] if e["id"] == ent)["entregas"][-1]["id"]

    _rec(mundo, HOY)
    assert any(a["source_type"] == SOURCE_ENTREGABLE and a["status"] == "ACTIVE" for a in _alertas(mundo, cid))

    r = _p(mundo, cid, f"/entregas/{entrega}/revision",
           {"resultado": "CONFORME", "fecha_revision": HOY.isoformat()}, datos["usuario"])
    assert r.status_code == 201, r.text
    _rec(mundo, HOY)
    assert any(a["source_type"] == SOURCE_ENTREGABLE and a["status"] == "RESOLVED"
               and a["resolved_at"] is not None for a in _alertas(mundo, cid))
    assert any(a["source_type"] == SOURCE_HITO and a["status"] == "ACTIVE" for a in _alertas(mundo, cid))

    r = _p(mundo, cid, "/recepciones", {"tipo": "PARCIAL", "fecha": HOY.isoformat(),
                                        "documento_id": _d(mundo, exp, "recepcion1"), "hito_ids": [hito]},
           datos["usuario"])
    assert r.status_code == 201, r.text
    _rec(mundo, HOY)
    assert any(a["source_type"] == SOURCE_HITO and a["status"] == "RESOLVED" for a in _alertas(mundo, cid))
    assert len(_alertas(mundo, cid)) == 2
    assert len(_activas(mundo, cid)) == 0


@ONLY_PG
def test_politica_de_preaviso_y_fases(mundo, gobierno, ocupacion):
    _sin_preaviso(mundo)
    datos = _iniciado(mundo, ocupacion)
    cid = datos["cid"]

    r = _p(mundo, cid, "/hitos", {"descripcion": "Primera entrega", "fecha_prevista": (HOY + timedelta(days=5)).isoformat(),
                                  "monto_previsto": "20000.00", "obligatorio": True}, datos["usuario"])
    assert r.status_code == 201, r.text
    hito = next(h["id"] for h in r.json()["hitos"] if h["descripcion"] == "Primera entrega")

    _rec(mundo, HOY)

    cuerpo = {"items": [{"fuente": "HITO", "activo": True, "dias_anticipacion": 7}]}
    r = mundo.put_json("/gobierno/contratos-alertas/politicas", "ua", mundo.company_a, cuerpo)
    assert r.status_code == 200, r.text
    assert r.json()["items"][1] == {"fuente": "HITO", "activo": True, "dias_anticipacion": 7}
    assert eventos(mundo, "GOV_CONTRACT_ALERT_POLICY_UPDATED", mundo.company_a)

    _rec(mundo, HOY)
    a = _activas(mundo, cid)[0]
    assert a["dedupe_key"] == clave("milestone", hito, HOY + timedelta(days=5), "UPCOMING")
    assert a["severity"] == "INFO"

    _rec(mundo, HOY + timedelta(days=5))
    aa = _alertas(mundo, cid)
    assert any(x["dedupe_key"] == clave("milestone", hito, HOY + timedelta(days=5), "UPCOMING")
               and x["status"] == "RESOLVED" for x in aa)
    assert any(x["dedupe_key"] == clave("milestone", hito, HOY + timedelta(days=5), "DUE_TODAY")
               and x["status"] == "ACTIVE" and x["severity"] == "WARNING" for x in aa)

    _rec(mundo, HOY + timedelta(days=6))
    aa = _alertas(mundo, cid)
    assert any(x["dedupe_key"] == clave("milestone", hito, HOY + timedelta(days=5), "OVERDUE")
               and x["status"] == "ACTIVE" and x["severity"] == "CRITICAL" for x in aa)
    assert len(aa) == 3

    cuerpo_bad = {"items": [{"fuente": "HITO", "activo": True, "dias_anticipacion": 7},
                            {"fuente": "HITO", "activo": True, "dias_anticipacion": 7}]}
    r = mundo.put_json("/gobierno/contratos-alertas/politicas", "ua", mundo.company_a, cuerpo_bad)
    assert r.status_code == 422
    assert r.json().get("code") == "GOV_CONTRACT_ALERT_POLICY_INVALID"

    cuerpo_bad = {"items": [{"fuente": "HITO", "activo": True}]}
    r = mundo.put_json("/gobierno/contratos-alertas/politicas", "ua", mundo.company_a, cuerpo_bad)
    assert r.status_code == 422
    assert r.json().get("code") == "GOV_CONTRACT_ALERT_POLICY_INVALID"

    cuerpo_bad = {"items": [{"fuente": "HITO", "activo": True, "dias_anticipacion": 0}]}
    r = mundo.put_json("/gobierno/contratos-alertas/politicas", "ua", mundo.company_a, cuerpo_bad)
    assert r.status_code == 422

    cuenta_con_permisos(mundo, "cnt09_lector", [("gobierno_contratos", "view")])
    r = mundo.get("/gobierno/contratos-alertas/politicas", "cnt09_lector", mundo.company_a)
    assert r.status_code == 200
    assert r.json()["garantias_dias_por_vencer"] == 15
    r = mundo.put_json("/gobierno/contratos-alertas/politicas", "cnt09_lector", mundo.company_a, cuerpo)
    assert r.status_code == 403


@ONLY_PG
def test_prorroga_cnt02_resuelve_y_recalcula(mundo, gobierno, ocupacion):
    _sin_preaviso(mundo)
    datos = _listo(mundo, ocupacion)
    cid = datos["cid"]
    exp = datos["exp"]

    r = mundo.put_json("/gobierno/contratos-alertas/politicas", "ua", mundo.company_a,
                       {"items": [{"fuente": "CONTRATO", "activo": True, "dias_anticipacion": 180}]})
    assert r.status_code == 200, r.text

    _rec(mundo, HOY)
    a = _activas(mundo, cid)[0]
    assert a["source_type"] == SOURCE_CONTRATO
    assert a["dedupe_key"] == clave("contract", cid, FIN, "UPCOMING")
    assert a["severity"] == "INFO"

    b = _nueva(mundo, cid, "PRORROGA")
    assert b.status_code == 201, b.text
    mid = b.json()["id"]
    r = _patch_m(mundo, cid, mid, {"fecha_instrumento": HOY.isoformat(), "vigente_desde": HOY.isoformat(),
                                   "motivo": "Solicitud justificada del contratista",
                                   "referencia_instrumento": "INSTR-MOD-01",
                                   "documento_id": _d(mundo, exp, "doc-prorroga"),
                                   "nueva_fecha_fin": (FIN + timedelta(days=30)).isoformat()}, b.json()["version"])
    assert r.status_code == 200, r.text
    firmante = _cargo_firmante(mundo, ocupacion, "SIN_LIMITE")
    r = _formalizar_m(mundo, cid, mid, firmante, r.json()["version"])
    assert r.status_code == 200, r.text

    _rec(mundo, HOY)
    assert not _activas(mundo, cid)
    assert any(a["status"] == "RESOLVED" and a["dedupe_key"] == clave("contract", cid, FIN, "UPCOMING")
               for a in _alertas(mundo, cid))

    _rec(mundo, HOY + timedelta(days=30))
    a = _activas(mundo, cid)[0]
    assert a["dedupe_key"] == clave("contract", cid, FIN + timedelta(days=30), "UPCOMING")


@ONLY_PG
def test_garantia_por_vencer_y_renovada(mundo, gobierno, ocupacion):
    _sin_preaviso(mundo)
    exp, ofertas, acto = _adjudicado(mundo, ocupacion)
    emisor = _emisor(mundo, "Aseguradora Uno", f"J-{uuid4().hex[:8]}")
    d1, exp = _doc(mundo, exp, "req1")
    r = _post_g(mundo, exp, "/requisitos", {"regla_codigo": "MANT-FIJO-1", "monto_fijo": "1000.00", "moneda": "VES",
                                            "vigencia_minima_hasta": (HOY + timedelta(days=60)).isoformat(),
                                            "fundamento": "Pliego, cláusula 12", "documento_id": d1})
    assert r.status_code == 201, r.text
    estado = r.json()
    d2, exp = _doc(mundo, exp, "gar1")
    r = _post_g(mundo, exp, "", {"requisito_id": estado["requisitos"][0]["id"], "oferta_id": ofertas[1]["id"],
                                 "emisor_id": emisor["id"], "referencia_emisor": "FZ-0001", "monto": "1000.00",
                                 "moneda": "VES", "fecha_emision": HOY.isoformat(), "vigente_desde": HOY.isoformat(),
                                 "vigente_hasta": (HOY + timedelta(days=10)).isoformat(), "documento_id": d2})
    assert r.status_code == 201, r.text
    g1 = _gar(r.json(), "GAR-01")

    _rec(mundo, HOY)
    a = _activas(mundo, exp["id"])[0]
    assert a["source_type"] == SOURCE_GARANTIA
    assert a["severity"] == "WARNING"
    assert a["source_id"] == exp["id"]
    assert a["source_item_id"] == g1["id"]
    assert a["dedupe_key"] == clave("guarantee", g1["id"], HOY + timedelta(days=10), "UPCOMING")

    d3, exp = _doc(mundo, exp, "ren1")
    r = _post_g(mundo, exp, f"/{g1['id']}/renovar", {"vigente_hasta": (HOY + timedelta(days=90)).isoformat(),
                                                     "documento_id": d3, "motivo": "Prórroga de la oferta (LCP art. 71)"})
    assert r.status_code == 201, r.text
    g2 = _gar(r.json(), "GAR-02")

    _rec(mundo, HOY)
    assert not _activas(mundo, exp["id"])
    assert any(a["status"] == "RESOLVED" for a in _alertas(mundo, exp["id"]))

    _rec(mundo, HOY + timedelta(days=80))
    a = _activas(mundo, exp["id"])[0]
    assert a["source_item_id"] == g2["id"]

    r = mundo.get(f"/gobierno/contrataciones/expedientes/{exp['id']}/garantias", "ua", mundo.company_a)
    assert r.status_code == 200, r.text
    g1_api = _gar(r.json(), "GAR-01")
    g2_api = _gar(r.json(), "GAR-02")
    assert g1_api["estado"] == "RENOVADA"
    assert g2_api["estado"] == "REGISTRADA"


@ONLY_PG
def test_planificador_tick_doble_sin_duplicados(mundo, gobierno, ocupacion):
    _sin_preaviso(mundo)
    datos = _iniciado(mundo, ocupacion)
    cid = datos["cid"]
    r = _p(mundo, cid, "/hitos", {"descripcion": "Primera entrega", "fecha_prevista": HOY.isoformat(),
                                  "monto_previsto": "20000.00", "obligatorio": True}, datos["usuario"])
    assert r.status_code == 201, r.text
    hito = next(h["id"] for h in r.json()["hitos"] if h["descripcion"] == "Primera entrega")

    m = next(x for x in manejadores() if x.code == "gov_contract_deadline_alerts")
    assert m.owner_spec == "CNT09"

    ahora = instante_actual()
    tick(mundo.factory, now=ahora, manejadores=(m,))
    tick(mundo.factory, now=ahora, manejadores=(m,))

    activas = [a for a in _activas(mundo, cid) if a["source_type"] == SOURCE_HITO and a["source_item_id"] == hito]
    assert len(activas) == 1


@ONLY_PG
def test_reconciliacion_concurrente_una_sola_alerta(mundo, gobierno, ocupacion):
    _sin_preaviso(mundo)
    datos = _iniciado(mundo, ocupacion)
    cid = datos["cid"]
    r = _p(mundo, cid, "/hitos", {"descripcion": "Primera entrega", "fecha_prevista": HOY.isoformat(),
                                  "monto_previsto": "20000.00", "obligatorio": True}, datos["usuario"])
    assert r.status_code == 201, r.text
    hito = next(h["id"] for h in r.json()["hitos"] if h["descripcion"] == "Primera entrega")

    ahora = instante_actual()
    r1, r2 = carrera(mundo.factory,
                     lambda s: reconciliar(s, mundo.company_a, HOY, ahora, None),
                     lambda s: reconciliar(s, mundo.company_a, HOY, ahora, None))
    assert not isinstance(r2, Exception)
    filas = [a for a in _alertas(mundo, cid) if a["dedupe_key"] == clave("milestone", hito, HOY, "DUE_TODAY")]
    assert len(filas) == 1


@ONLY_PG
def test_contexto_del_contrato_aislamiento_y_bandeja(mundo, gobierno, ocupacion):
    _sin_preaviso(mundo)
    datos = _iniciado(mundo, ocupacion)
    cid = datos["cid"]
    r = _p(mundo, cid, "/hitos", {"descripcion": "Primera entrega", "fecha_prevista": HOY.isoformat(),
                                  "monto_previsto": "20000.00", "obligatorio": True}, datos["usuario"])
    assert r.status_code == 201, r.text
    hito = next(h["id"] for h in r.json()["hitos"] if h["descripcion"] == "Primera entrega")
    _rec(mundo, HOY)

    r = mundo.get(f"{C}/{cid}/alertas", datos["usuario"], mundo.company_a)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["contrato_id"] == cid
    assert body["activas"] == 1
    assert body["items"][0]["link"]["route_key"] == ROUTE_EJECUCION
    assert "HIT-01" in body["items"][0]["message"]["text"]

    r = mundo.get(f"{C}/{cid}/alertas", "ua", mundo.company_b)
    assert r.status_code == 404

    r = mundo.get("/alerts?source_type=GovernmentContractMilestone&status=ACTIVE", "ua", mundo.company_a)
    assert r.status_code == 200
    assert any(i["link"]["source_item_id"] == hito for i in r.json()["items"])

    r = mundo.get("/alerts?source_type=GovernmentContractMilestone&status=ACTIVE", "ua", mundo.company_b)
    assert r.status_code == 404

    cuenta_con_permisos(mundo, "cnt09_sinctr", [("alertas", "view")])
    r = mundo.get("/alerts?status=ACTIVE", "cnt09_sinctr", mundo.company_a)
    assert r.status_code == 200
    assert not any(i["link"]["source_type"] in
                   ("GovernmentContract", "GovernmentContractMilestone", "GovernmentContractDeliverable")
                   for i in r.json()["items"])

    r = mundo.get(f"{C}/{cid}/alertas?estado=RESOLVED", datos["usuario"], mundo.company_a)
    assert r.status_code == 200
    assert r.json()["items"] == []
    r = mundo.get(f"{C}/{cid}/alertas?estado=ALL", datos["usuario"], mundo.company_a)
    assert r.status_code == 200
    assert len(r.json()["items"]) == 1
