from datetime import date, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.core.company_context import CompanyContext
from app.core.errors import ConflictError
from app.modules.government import service_contratos_supervision
from app.modules.government.models import (
    GovernmentContractSupervisorAssignment,
    GovernmentOfficial,
    GovernmentProcurementFileEvent,
)
from app.modules.government.service_contratos_supervision import designar
from app.modules.identity_access.mfa_policy import SENSITIVE, classify
from app.modules.identity_access.models import User
from app.modules.organization.models import Company
from app.modules.setup.api import CATALOGO_DE_PERMISOS
from tests.concurrency import carrera
from tests.org04_ayudantes import acto_eficaz, crear_funcionario, titular_activo
from tests.org06_guarda import cuenta_con_permisos
from tests.proc08_ayudantes import cargo_contrataciones
from tests.test_gov_bud01_ejercicio import ONLY_PG
from tests.test_gov_cnt01_contratos import C, _cargo_firmante, _preparado
from tests.test_gov_ctl01_reglas import cerrar_regla, eventos, regla_vigente
from tests.test_gov_ctl06_hallazgos import _post
from tests.test_gov_proc10_garantias import HOY

pytest_plugins = (
    "tests.conftest_multicompany",
    "tests.test_gov_ctl06_hallazgos",
    "tests.org04_ayudantes",
)

S = "/supervision"


def _formalizado(mundo, ocupacion):
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
    return {"contrato": r.json(), "exp": prep["exp"]}


def _supervisor(mundo, ocupacion):
    asig, _ = titular_activo(mundo, ocupacion)
    return {
        "funcionario_id": asig["funcionario"]["id"],
        "asignacion_id": asig["id"],
        "nombre": asig["funcionario"]["nombre"],
    }


def _acto_designante(mundo, ocupacion):
    return acto_eficaz(mundo, cargo_contrataciones(mundo, ocupacion), fecha=HOY)


def _designar(mundo, cid, sup, acto_id, desde, motivo=None, sustituye_id=None, usuario="ua"):
    cuerpo = {
        "funcionario_id": sup["funcionario_id"],
        "asignacion_id": sup["asignacion_id"],
        "acto_id": acto_id,
        "desde": desde.isoformat(),
        "motivo": motivo,
        "sustituye_id": sustituye_id,
    }
    return _post(mundo, f"{C}/{cid}{S}/designaciones", usuario, mundo.company_a, cuerpo)


@ONLY_PG
def test_vector_a_designacion_inicial(mundo, gobierno, ocupacion):
    f = _formalizado(mundo, ocupacion)
    cid = f["contrato"]["id"]
    sup = _supervisor(mundo, ocupacion)
    acto_id = _acto_designante(mundo, ocupacion)

    r = mundo.get(f"{C}/{cid}{S}", "ua", mundo.company_a)
    assert r.status_code == 200
    body = r.json()
    assert body["vigente"] is None
    assert body["historia"] == []
    assert body["puede_designar"] is True

    r = _designar(mundo, cid, sup, acto_id, HOY)
    assert r.status_code == 201
    vigente = r.json()["vigente"]
    assert vigente["referencia"] == "SUP-01"
    assert vigente["estado"] == "VIGENTE"
    assert vigente["funcionario"]["nombre"] == sup["nombre"]
    assert "*" in vigente["funcionario"]["documento"]
    assert vigente["cargo"]["nombre"]
    assert vigente["unidad"]["nombre"]
    assert vigente["acto"]["etiqueta"].startswith("Resolución N.º")
    assert vigente["desde"] == HOY.isoformat()
    assert vigente["hasta"] is None

    r = mundo.get(f"{C}/{cid}{S}/en?fecha={HOY.isoformat()}", "ua", mundo.company_a)
    assert r.status_code == 200
    assert r.json()["supervisor"]["id"] == vigente["id"]

    evs = eventos(mundo, "GOV_CONTRACT_SUPERVISOR_ASSIGNED", f["exp"]["id"])
    assert len(evs) == 1
    assert evs[0].after["designacion"] == "SUP-01"

    with mundo.factory() as db:
        f_ev = db.scalars(
            select(GovernmentProcurementFileEvent).where(
                GovernmentProcurementFileEvent.file_id == f["exp"]["id"],
                GovernmentProcurementFileEvent.clase == "CONTRATO",
            )
        ).all()
        assert any(e.titulo.startswith("Supervisor de ") for e in f_ev)


@ONLY_PG
def test_vector_b_contrato_borrador(mundo, gobierno, ocupacion):
    prep = _preparado(mundo, ocupacion)
    cid = prep["contrato"]["id"]
    sup = _supervisor(mundo, ocupacion)
    acto_id = _acto_designante(mundo, ocupacion)

    r = _designar(mundo, cid, sup, acto_id, HOY)
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_CONTRACT_SUPERVISOR_CONTRACT_NOT_FORMALIZED"

    r = _designar(mundo, "ffffffff-ffff-ffff-ffff-ffffffffffff", sup, acto_id, HOY)
    assert r.status_code == 404


@ONLY_PG
def test_vector_c_sin_ocupacion_vigente(mundo, gobierno, ocupacion):
    f = _formalizado(mundo, ocupacion)
    cid = f["contrato"]["id"]
    _otro_sup = _supervisor(mundo, ocupacion)
    funcionario = crear_funcionario(mundo)
    acto_id = _acto_designante(mundo, ocupacion)

    sup = {
        "funcionario_id": funcionario["id"],
        "asignacion_id": _otro_sup["asignacion_id"],
        "nombre": funcionario["nombre"],
    }
    r = _designar(mundo, cid, sup, acto_id, HOY)
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_CONTRACT_SUPERVISOR_OCCUPATION_INVALID"

    evs = eventos(mundo, "GOV_CONTRACT_SUPERVISOR_BLOCKED", f["exp"]["id"])
    assert len(evs) >= 1
    assert any(e.after["causal"] == "GOV_CONTRACT_SUPERVISOR_OCCUPATION_INVALID" for e in evs)


@ONLY_PG
def test_vector_d_acto_no_eficaz_y_sin_autoridad(mundo, gobierno, ocupacion):
    f = _formalizado(mundo, ocupacion)
    cid = f["contrato"]["id"]
    sup = _supervisor(mundo, ocupacion)

    cargo_firma = _cargo_firmante(mundo, ocupacion, "SIN_LIMITE")
    acto_emitido = acto_eficaz(mundo, cargo_firma, fecha=HOY, status="EMITIDO")
    r = _designar(mundo, cid, sup, acto_emitido, HOY)
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_CONTRACT_SUPERVISOR_ACT_INVALID"

    acto_sin_autoridad = acto_eficaz(mundo, cargo_firma, fecha=HOY)
    r = _designar(mundo, cid, sup, acto_sin_autoridad, HOY)
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_CONTRACT_SUPERVISOR_ACT_AUTHORITY_INVALID"

    r = mundo.get(f"{C}/{cid}{S}", "ua", mundo.company_a)
    assert r.json()["historia"] == []


@ONLY_PG
def test_vector_e_aislamiento(mundo, gobierno, ocupacion):
    f = _formalizado(mundo, ocupacion)
    cid = f["contrato"]["id"]
    sup = _supervisor(mundo, ocupacion)
    acto_id = _acto_designante(mundo, ocupacion)

    r = mundo.get(f"{C}/{cid}{S}", "ua", mundo.company_b)
    assert r.status_code == 404

    with mundo.factory() as db:
        f_b = GovernmentOfficial(
            company_id=mundo.company_b,
            codigo=f"FB-{uuid4().hex[:8]}",
            nombre="Funcionario de otra empresa",
            tipo_documento="V",
            numero_documento=f"{uuid4().int % 10**8:08d}",
            estado="ACTIVO",
        )
        db.add(f_b)
        db.commit()
        fb_id = str(f_b.id)

    sup_b = {
        "funcionario_id": fb_id,
        "asignacion_id": sup["asignacion_id"],
        "nombre": "Funcionario de otra empresa",
    }
    r = _designar(mundo, cid, sup_b, acto_id, HOY)
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_CONTRACT_SUPERVISOR_OFFICIAL_INVALID"


@ONLY_PG
def test_vector_f_sustitucion_e_historia(mundo, gobierno, ocupacion, monkeypatch):
    f = _formalizado(mundo, ocupacion)
    cid = f["contrato"]["id"]
    sup_a = _supervisor(mundo, ocupacion)
    acto_a = _acto_designante(mundo, ocupacion)

    r = _designar(mundo, cid, sup_a, acto_a, HOY)
    assert r.status_code == 201
    asignacion_a = r.json()["vigente"]

    monkeypatch.setattr(
        service_contratos_supervision, "hoy_de_negocio", lambda: HOY + timedelta(days=10)
    )

    acto_b = acto_eficaz(mundo, cargo_contrataciones(mundo, ocupacion), fecha=HOY)

    r = _designar(
        mundo,
        cid,
        sup_a,
        acto_b,
        HOY,
        motivo="Traslado",
        sustituye_id=asignacion_a["id"],
    )
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_CONTRACT_SUPERVISOR_DATE_INVALID"

    r = _designar(
        mundo,
        cid,
        sup_a,
        acto_b,
        HOY + timedelta(days=5),
        motivo=None,
        sustituye_id=asignacion_a["id"],
    )
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_CONTRACT_SUPERVISOR_REASON_REQUIRED"

    r = _designar(
        mundo,
        cid,
        sup_a,
        acto_a,
        HOY + timedelta(days=5),
        motivo="Traslado",
        sustituye_id=asignacion_a["id"],
    )
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_CONTRACT_SUPERVISOR_ACT_REUSED"

    r = _designar(
        mundo,
        cid,
        sup_a,
        acto_b,
        HOY + timedelta(days=5),
        motivo="Traslado",
        sustituye_id=None,
    )
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_CONTRACT_SUPERVISOR_STALE"

    sup_b = _supervisor(mundo, ocupacion)
    r = _designar(
        mundo,
        cid,
        sup_b,
        acto_b,
        HOY + timedelta(days=5),
        motivo="Traslado del funcionario",
        sustituye_id=asignacion_a["id"],
    )
    assert r.status_code == 201
    vigente = r.json()["vigente"]
    assert vigente["referencia"] == "SUP-02"
    assert vigente["sustituye"] == "SUP-01"
    assert vigente["estado"] == "VIGENTE"

    r = mundo.get(f"{C}/{cid}{S}", "ua", mundo.company_a)
    body = r.json()
    historia = body["historia"]
    assert [h["referencia"] for h in historia] == ["SUP-02", "SUP-01"]
    assert historia[1]["estado"] == "SUSTITUIDA"
    assert historia[1]["hasta"] == (HOY + timedelta(days=4)).isoformat()

    evs = eventos(mundo, "GOV_CONTRACT_SUPERVISOR_REPLACED", f["exp"]["id"])
    assert any(e.after["sustituye"] == "SUP-01" for e in evs)


@ONLY_PG
def test_vector_h_supervisor_en_fecha(mundo, gobierno, ocupacion, monkeypatch):
    f = _formalizado(mundo, ocupacion)
    cid = f["contrato"]["id"]
    sup_a = _supervisor(mundo, ocupacion)
    acto_a = _acto_designante(mundo, ocupacion)

    r = _designar(mundo, cid, sup_a, acto_a, HOY)
    assert r.status_code == 201
    asignacion_a = r.json()["vigente"]

    monkeypatch.setattr(
        service_contratos_supervision, "hoy_de_negocio", lambda: HOY + timedelta(days=10)
    )
    acto_b = acto_eficaz(mundo, cargo_contrataciones(mundo, ocupacion), fecha=HOY)
    sup_b = _supervisor(mundo, ocupacion)
    r = _designar(
        mundo,
        cid,
        sup_b,
        acto_b,
        HOY + timedelta(days=5),
        motivo="Traslado del funcionario",
        sustituye_id=asignacion_a["id"],
    )
    assert r.status_code == 201

    r = mundo.get(
        f"{C}/{cid}{S}/en?fecha={(HOY + timedelta(days=2)).isoformat()}",
        "ua",
        mundo.company_a,
    )
    assert r.status_code == 200
    assert r.json()["supervisor"]["id"] == asignacion_a["id"]

    r = mundo.get(
        f"{C}/{cid}{S}/en?fecha={(HOY + timedelta(days=5)).isoformat()}",
        "ua",
        mundo.company_a,
    )
    assert r.status_code == 200
    assert r.json()["supervisor"]["referencia"] == "SUP-02"

    r = mundo.get(
        f"{C}/{cid}{S}/en?fecha={(HOY - timedelta(days=1)).isoformat()}",
        "ua",
        mundo.company_a,
    )
    assert r.status_code == 200
    assert r.json()["supervisor"] is None

    r = mundo.get(f"{C}/{cid}{S}", "ua", mundo.company_a)
    historia = r.json()["historia"]
    sustituida = next(h for h in historia if h["referencia"] == "SUP-01")
    for campo in ["funcionario", "cargo", "acto", "desde"]:
        assert sustituida[campo] == asignacion_a[campo]


@ONLY_PG
def test_vector_g_concurrencia(mundo, gobierno, ocupacion):
    f = _formalizado(mundo, ocupacion)
    cid = f["contrato"]["id"]
    sup = _supervisor(mundo, ocupacion)
    acto_id = _acto_designante(mundo, ocupacion)
    cuerpo = {
        "funcionario_id": sup["funcionario_id"],
        "asignacion_id": sup["asignacion_id"],
        "acto_id": acto_id,
        "desde": HOY,
        "motivo": None,
        "sustituye_id": None,
    }

    with mundo.factory() as db:
        uid = db.scalar(select(User.id).where(User.username == "ua"))

        def op(s):
            ctx = CompanyContext(
                tenant_id=mundo.t1,
                company_id=mundo.company_a,
                company=s.get(Company, mundo.company_a),
                user_id=uid,
            )
            return designar(s, ctx, cid, cuerpo)

        r1, r2 = carrera(mundo.factory, op, op)

    resultados = [r for r in (r1, r2) if isinstance(r, dict)]
    errores = [r for r in (r1, r2) if isinstance(r, ConflictError)]
    assert len(resultados) == 1
    assert len(errores) == 1
    assert errores[0].code in (
        "GOV_CONTRACT_SUPERVISOR_STALE",
        "GOV_CONTRACT_SUPERVISOR_CONFLICT",
    )

    with mundo.factory() as db:
        filas = db.scalars(
            select(GovernmentContractSupervisorAssignment).where(
                GovernmentContractSupervisorAssignment.contract_id == cid,
                GovernmentContractSupervisorAssignment.estado == "VIGENTE",
            )
        ).all()
        assert len(filas) == 1


@ONLY_PG
def test_inmutable_en_base(mundo, gobierno, ocupacion, monkeypatch):
    f = _formalizado(mundo, ocupacion)
    cid = f["contrato"]["id"]
    sup_a = _supervisor(mundo, ocupacion)
    acto_a = _acto_designante(mundo, ocupacion)

    r = _designar(mundo, cid, sup_a, acto_a, HOY)
    assert r.status_code == 201
    asignacion_a = r.json()["vigente"]

    monkeypatch.setattr(
        service_contratos_supervision, "hoy_de_negocio", lambda: HOY + timedelta(days=10)
    )
    acto_b = acto_eficaz(mundo, cargo_contrataciones(mundo, ocupacion), fecha=HOY)
    sup_b = _supervisor(mundo, ocupacion)
    r = _designar(
        mundo,
        cid,
        sup_b,
        acto_b,
        HOY + timedelta(days=5),
        motivo="Traslado del funcionario",
        sustituye_id=asignacion_a["id"],
    )
    assert r.status_code == 201
    asignacion_b = r.json()["vigente"]

    intentos = [
        f"UPDATE gov_contract_supervisors SET cargo_nombre = 'X' WHERE id = '{asignacion_a['id']}'",
        f"UPDATE gov_contract_supervisors SET estado = 'VIGENTE', hasta = NULL, sustituida_por_id = NULL WHERE id = '{asignacion_a['id']}'",
        f"DELETE FROM gov_contract_supervisors WHERE id = '{asignacion_b['id']}'",
        "TRUNCATE gov_contract_supervisors",
    ]
    for sql in intentos:
        with mundo.factory() as db:
            with pytest.raises(DBAPIError):
                db.execute(text(sql))
                db.commit()
            db.rollback()


@ONLY_PG
def test_permisos_mfa_y_sod(mundo, gobierno, ocupacion):
    assert classify("gobierno_contratos:assign_supervisor") == SENSITIVE
    assert "assign_supervisor" in CATALOGO_DE_PERMISOS["gobierno_contratos"]

    cuenta_con_permisos(mundo, "cnt04_lector", [("gobierno_contratos", "view")])

    f = _formalizado(mundo, ocupacion)
    cid = f["contrato"]["id"]
    r = mundo.get(f"{C}/{cid}{S}", "cnt04_lector", mundo.company_a)
    assert r.status_code == 200

    sup = _supervisor(mundo, ocupacion)
    acto_id = _acto_designante(mundo, ocupacion)
    r = _designar(mundo, cid, sup, acto_id, HOY, usuario="cnt04_lector")
    assert r.status_code == 403

    regla = regla_vigente(
        mundo,
        proceso="PROC-03",
        accion_a="PROC03_CONTRATO_FORMALIZAR",
        accion_b="PROC03_SUPERVISOR_DESIGNAR",
    )
    try:
        r = _designar(mundo, cid, sup, acto_id, HOY)
        assert r.status_code == 409
        assert r.json()["code"] == "GOV_SOD_CONFLICT"
    finally:
        cerrar_regla(mundo, regla)


@ONLY_PG
def test_opciones(mundo, gobierno, ocupacion):
    f = _formalizado(mundo, ocupacion)
    cid = f["contrato"]["id"]
    sup = _supervisor(mundo, ocupacion)
    acto_id = _acto_designante(mundo, ocupacion)

    cargo_firma = _cargo_firmante(mundo, ocupacion, "SIN_LIMITE")
    acto_emitido = acto_eficaz(mundo, cargo_firma, fecha=HOY, status="EMITIDO")
    acto_eficaz_sin_aprobar = acto_eficaz(mundo, cargo_firma, fecha=HOY)
    sin_ocupacion = crear_funcionario(mundo)

    r = _designar(mundo, cid, sup, acto_id, HOY)
    assert r.status_code == 201

    r = mundo.get(f"{C}/{cid}{S}/opciones?fecha={HOY.isoformat()}", "ua", mundo.company_a)
    assert r.status_code == 200
    body = r.json()

    funcionarios = {fn["id"]: fn for fn in body["funcionarios"]}
    assert sup["funcionario_id"] in funcionarios
    assert any(
        o["asignacion_id"] == sup["asignacion_id"]
        for o in funcionarios[sup["funcionario_id"]]["ocupaciones"]
    )

    actos = {a["id"] for a in body["actos"]}
    assert acto_id in actos
    assert acto_emitido not in actos
    assert acto_eficaz_sin_aprobar not in actos
    assert sin_ocupacion["id"] not in funcionarios


@ONLY_PG
def test_designacion_programada(mundo, gobierno, ocupacion):
    f = _formalizado(mundo, ocupacion)
    cid = f["contrato"]["id"]

    a = _designar(
        mundo,
        cid,
        _supervisor(mundo, ocupacion),
        _acto_designante(mundo, ocupacion),
        HOY,
    )
    assert a.status_code == 201
    a_json = a.json()
    vigente = a_json["vigente"]
    assert vigente["situacion"] == "EN_EJERCICIO"

    b = _designar(
        mundo,
        cid,
        _supervisor(mundo, ocupacion),
        _acto_designante(mundo, ocupacion),
        HOY + timedelta(days=5),
        motivo="Cambio programado",
        sustituye_id=vigente["id"],
    )
    assert b.status_code == 201
    cuerpo = b.json()
    assert cuerpo["vigente"]["id"] == vigente["id"]
    assert cuerpo["programada"]["referencia"] == "SUP-02"
    assert cuerpo["programada"]["situacion"] == "PROGRAMADA"
    assert cuerpo["ultima_id"] == cuerpo["programada"]["id"]
    sup01 = next(item for item in cuerpo["historia"] if item["referencia"] == "SUP-01")
    assert sup01["estado"] == "SUSTITUIDA"
    assert sup01["hasta"] == (HOY + timedelta(days=4)).isoformat()

    en_hoy = mundo.get(f"{C}/{cid}{S}/en?fecha={HOY.isoformat()}", "ua", mundo.company_a).json()["supervisor"]
    assert en_hoy["referencia"] == "SUP-01"
    en_futuro = mundo.get(f"{C}/{cid}{S}/en?fecha={(HOY + timedelta(days=5)).isoformat()}", "ua", mundo.company_a).json()["supervisor"]
    assert en_futuro["referencia"] == "SUP-02"

    fecha_fin = date.fromisoformat(f["contrato"]["fecha_fin"])
    fuera = _designar(
        mundo,
        cid,
        _supervisor(mundo, ocupacion),
        _acto_designante(mundo, ocupacion),
        fecha_fin + timedelta(days=1),
        motivo="Fuera de rango",
        sustituye_id=cuerpo["ultima_id"],
    )
    assert fuera.status_code == 422
    assert fuera.json()["code"] == "GOV_CONTRACT_SUPERVISOR_DATE_INVALID"
