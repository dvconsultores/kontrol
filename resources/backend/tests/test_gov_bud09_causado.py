"""BUD-09 · Causados presupuestarios (GOV-BUD-013)."""

from __future__ import annotations

import re
import threading
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.core.company_context import CompanyContext
from app.core.errors import KontrolError
from app.modules.audit.models import AuditEvent
from app.modules.documents.models import Document, DocumentType
from app.modules.government import service_presupuesto_causado
from app.modules.government.models import (
    GovernmentPosition,
    GovernmentPositionCompetency,
    GovernmentPositionVersion,
)
from app.modules.identity_access.mfa_policy import SENSITIVE, classify
from app.modules.identity_access.models import User
from app.modules.organization.models import Company
from app.modules.setup.api import CATALOGO_DE_PERMISOS
from app.shared.clock import hoy_de_negocio
from tests.org04_ayudantes import ANIO, D, _codigo
from tests.org06_guarda import cuenta_con_permisos
from tests.test_gov_bud01_ejercicio import ONLY_PG, P, _completo, _documento
from tests.test_gov_bud08 import _cdp, _comprometer
from tests.test_gov_ctl01_reglas import activar_regla, cerrar_regla, crear_regla
from tests.test_gov_ctl06_hallazgos import _post

pytest_plugins = (
    "tests.conftest_multicompany",
    "tests.test_gov_ctl06_hallazgos",
    "tests.org04_ayudantes",
)

CAUSADOS = "/gobierno/presupuesto/causados"
POLITICAS = "/gobierno/presupuesto/politicas-causado"

_CUENTAS: dict[int, None] = {}


def _get(mundo, ruta, usuario="caus_b09", empresa=None):
    return mundo.get(ruta, usuario, empresa or mundo.company_a)


def _put(mundo, ruta, usuario, cuerpo, version, empresa=None):
    return mundo.client.put(
        f"/api/v1{ruta}",
        headers={
            **mundo.como(usuario, empresa or mundo.company_a),
            "If-Match": str(version),
        },
        json=cuerpo,
    )


def _put_sin_version(mundo, ruta, usuario, cuerpo, empresa=None):
    return mundo.client.put(
        f"/api/v1{ruta}",
        headers=mundo.como(usuario, empresa or mundo.company_a),
        json=cuerpo,
    )


def _cuentas(mundo) -> None:
    if id(mundo) in _CUENTAS:
        return
    cuenta_con_permisos(
        mundo,
        "caus_b09",
        [("gobierno_presupuesto", "view"), ("gobierno_presupuesto", "cause")],
    )
    cuenta_con_permisos(mundo, "solo_ver_b09", [("gobierno_presupuesto", "view")])
    cuenta_con_permisos(
        mundo,
        "compcaus_b09",
        [
            ("gobierno_presupuesto", "view"),
            ("gobierno_presupuesto", "commit"),
            ("gobierno_presupuesto", "cause"),
        ],
    )
    _CUENTAS[id(mundo)] = None


def _cargo_causar(mundo, ocupacion, tipo_limite="SIN_LIMITE", monto=None, moneda=None) -> str:
    """Crea un cargo con competencia CAUSAR × PRESUPUESTO con límite dado."""
    structure_id = ocupacion["estructura"]
    unit_id = ocupacion["unidad_raiz"]
    with mundo.factory() as db:
        cargo = GovernmentPosition(
            company_id=mundo.company_a,
            structure_id=structure_id,
            unit_id=unit_id,
            code=_codigo("K"),
            name=f"Cargo causar {_codigo('N')}",
            status="VIGENTE",
            valid_from=D(1, 1),
            valid_to=None,
            activated_at=datetime.now(UTC),
            version=1,
        )
        db.add(cargo)
        db.flush()

        comp = GovernmentPositionCompetency(
            position_id=cargo.id,
            company_id=mundo.company_a,
            action="CAUSAR",
            subject="PRESUPUESTO",
            limit_type=tipo_limite,
            limit_amount=monto,
            limit_currency=moneda,
            basis="Fundamento de prueba",
        )
        db.add(comp)

        version = GovernmentPositionVersion(
            position_id=cargo.id,
            structure_id=structure_id,
            company_id=mundo.company_a,
            version=1,
            status="VIGENTE",
            snapshot={
                "competencias": [
                    {
                        "accion": "CAUSAR",
                        "materia": "PRESUPUESTO",
                        "tipo_limite": tipo_limite,
                        "monto": monto,
                        "moneda": moneda,
                    }
                ]
            },
            reason=None,
            actor_id=None,
        )
        db.add(version)
        db.commit()
        return str(cargo.id)


_TIPO_SOPORTE: dict[str, str] = {}


def _politica(
    mundo,
    tipo_gasto: str | None = None,
    disparador="DOCUMENTARY",
    documentos=None,
    **cambios,
) -> dict:
    if tipo_gasto is None:
        tipo_gasto = "G" + uuid4().hex[:10].upper()
    cuerpo = {
        "codigo": "P" + uuid4().hex[:12].upper(),
        "tipo_gasto": tipo_gasto,
        "nombre": "Política de causado de prueba",
        "disparador": disparador,
        "requiere_recepcion": False,
        "requiere_valuacion": False,
        "requiere_conformidad": False,
        "competencia_accion": "CAUSAR",
        "competencia_materia": "PRESUPUESTO",
        "vigente_desde": hoy_de_negocio().isoformat(),
    }
    if documentos is None and disparador == "DOCUMENTARY" and "tipo" in _TIPO_SOPORTE:
        documentos = [
            {
                "document_type_id": _TIPO_SOPORTE["tipo"],
                "obligatorio": True,
                "etapa": "FORMALIZACION",
            }
        ]
    cuerpo.update(cambios)
    if documentos is not None:
        cuerpo["documentos"] = documentos
    r = _post(mundo, POLITICAS, "ua", mundo.company_a, cuerpo)
    assert r.status_code == 201, r.text
    return r.json()


def _activar_politica(mundo, politica) -> dict:
    r = _post(
        mundo,
        f"{POLITICAS}/{politica['id']}/activar",
        "ua",
        mundo.company_a,
        {"fundamento": "Fundamento suficiente para activar política de causado"},
        version=politica["version"],
    )
    assert r.status_code == 200, r.text
    return r.json()


def _linea(mundo, s, compromiso_id) -> str:
    r = _get(
        mundo,
        f"{P}/{s['year_id']}/causados/opciones?compromiso_id={compromiso_id}",
    )
    assert r.status_code == 200, r.text
    for compromiso in r.json()["compromisos"]:
        if compromiso["id"] == compromiso_id:
            return str(compromiso["lineas"][0]["id"])
    raise AssertionError("Compromiso no encontrado en opciones")


def _causar(mundo, s, compromiso, cargo, politica, monto="30.00", **cambios) -> dict:
    cuerpo = {
        "compromiso_id": compromiso["id"],
        "politica_id": politica["id"],
        "fecha_efectiva": hoy_de_negocio().isoformat(),
        "concepto": "Causado de prueba para BUD-09",
        "autoridad_cargo_id": cargo,
        "lineas": [
            {"linea_compromiso_id": _linea(mundo, s, compromiso["id"]), "monto": monto}
        ],
        "evidencias": [{"tipo": "DOCUMENT", "id": s["soporte"]}],
    }
    cuerpo.update(cambios)
    r = _post(mundo, f"{P}/{s['year_id']}/causados", "caus_b09", mundo.company_a, cuerpo)
    assert r.status_code == 201, r.text
    return r.json()


def _causar_sin_assert(mundo, s, compromiso, cargo, politica, monto="30.00", **cambios):
    cuerpo = {
        "compromiso_id": compromiso["id"],
        "politica_id": politica["id"],
        "fecha_efectiva": hoy_de_negocio().isoformat(),
        "concepto": "Causado de prueba sin assert",
        "autoridad_cargo_id": cargo,
        "lineas": [
            {"linea_compromiso_id": _linea(mundo, s, compromiso["id"]), "monto": monto}
        ],
        "evidencias": [],
    }
    cuerpo.update(cambios)
    return _post(mundo, f"{P}/{s['year_id']}/causados", "caus_b09", mundo.company_a, cuerpo)


def _borrador_documental(mundo, s, compromiso, cargo, politica, evidencia):
    return _causar(mundo, s, compromiso, cargo, politica, evidencias=[evidencia])


def _detalle(mundo, causado_id):
    r = _get(mundo, f"{CAUSADOS}/{causado_id}")
    assert r.status_code == 200, r.text
    return r.json()


def _formalizado(mundo, causado_id, version):
    r = _post(
        mundo,
        f"{CAUSADOS}/{causado_id}/formalizar",
        "caus_b09",
        mundo.company_a,
        {},
        version=version,
    )
    assert r.status_code == 200, r.text
    return r.json()


def _documento_nuevo_tipo(mundo) -> str:
    with mundo.factory() as db:
        tipo = DocumentType(
            company_id=mundo.company_a,
            code=f"B09-{_codigo('T')}",
            name=f"Tipo documental BUD-09 {_codigo('N')}",
            status="ACTIVE",
        )
        db.add(tipo)
        db.commit()
        return str(tipo.id)


def _tipo_documento_soporte(mundo, documento_id) -> str:
    with mundo.factory() as db:
        documento = db.get(Document, documento_id)
        assert documento is not None
        return str(documento.document_type_id)


def _eventos(mundo, accion, entity_id):
    with mundo.factory() as db:
        rows = db.execute(
            select(AuditEvent)
            .where(
                AuditEvent.company_id == mundo.company_a,
                AuditEvent.entity_id == entity_id,
                AuditEvent.action == accion,
            )
            .order_by(AuditEvent.created_at)
        ).scalars().all()
        return rows


def _opciones_compromiso(mundo, s, compromiso_id):
    r = _get(
        mundo,
        f"{P}/{s['year_id']}/causados/opciones?compromiso_id={compromiso_id}",
    )
    assert r.status_code == 200, r.text
    for compromiso in r.json()["compromisos"]:
        if compromiso["id"] == compromiso_id:
            return compromiso["lineas"]
    raise AssertionError("Compromiso no encontrado en opciones")


def _preparar(mundo, ocupacion):
    from tests.test_gov_bud08 import _preparar as _preparar_bud08

    s = _preparar_bud08(mundo, ocupacion)
    s["cargo_causar"] = _cargo_causar(mundo, ocupacion)
    _TIPO_SOPORTE["tipo"] = _tipo_documento_soporte(mundo, s["soporte"])
    return s


def test_b09_01_politica(mundo, gobierno, ocupacion):
    _cuentas(mundo)
    r_vacia = _get(mundo, POLITICAS, usuario="ub", empresa=mundo.company_b)
    assert r_vacia.status_code == 200
    assert r_vacia.json() == []

    politica = _politica(mundo, disparador="VALUATION_APPROVED")
    assert politica["estado"] == "BORRADOR"
    assert len(_eventos(mundo, "GOV_BUDGET_CAUSING_POLICY_CREATED", politica["id"])) >= 1

    actualizada = _put(
        mundo,
        f"{POLITICAS}/{politica['id']}",
        "ua",
        {
            "codigo": politica["codigo"],
            "tipo_gasto": politica["tipo_gasto"],
            "nombre": "Actualizada",
            "disparador": politica["disparador"],
            "requiere_recepcion": False,
            "requiere_valuacion": False,
            "requiere_conformidad": False,
            "competencia_accion": "CAUSAR",
            "competencia_materia": "PRESUPUESTO",
            "vigente_desde": hoy_de_negocio().isoformat(),
        },
        politica["version"],
    )
    assert actualizada.status_code == 200, actualizada.text
    assert actualizada.json()["version"] == politica["version"] + 1

    sin_fundamento = _post(mundo, f"{POLITICAS}/{politica['id']}/activar", "ua", mundo.company_a, {})
    assert sin_fundamento.status_code == 422
    assert "code" in sin_fundamento.json()

    activada = _activar_politica(mundo, actualizada.json())
    assert activada["estado"] == "VIGENTE"

    put_vigente = _put(
        mundo,
        f"{POLITICAS}/{politica['id']}",
        "ua",
        {
            "codigo": politica["codigo"],
            "tipo_gasto": politica["tipo_gasto"],
            "nombre": "Otra",
            "disparador": politica["disparador"],
            "requiere_recepcion": False,
            "requiere_valuacion": False,
            "requiere_conformidad": False,
            "competencia_accion": "CAUSAR",
            "competencia_materia": "PRESUPUESTO",
            "vigente_desde": hoy_de_negocio().isoformat(),
        },
        activada["version"],
    )
    assert put_vigente.status_code == 409
    assert put_vigente.json()["code"] == "GOV_BUDGET_CAUSING_POLICY_NOT_DRAFT"

    solapada = _politica(
        mundo,
        tipo_gasto=politica["tipo_gasto"],
        disparador="VALUATION_APPROVED",
    )
    r_solape = _post(
        mundo,
        f"{POLITICAS}/{solapada['id']}/activar",
        "ua",
        mundo.company_a,
        {"fundamento": "Fundamento suficiente para solapar"},
        version=solapada["version"],
    )
    assert r_solape.status_code == 409
    assert r_solape.json()["code"] == "GOV_BUDGET_CAUSING_POLICY_OVERLAP"

    cerrada = _post(
        mundo,
        f"{POLITICAS}/{politica['id']}/cerrar",
        "ua",
        mundo.company_a,
        {"motivo": "Fin de prueba"},
        version=activada["version"],
    )
    assert cerrada.status_code == 200, cerrada.text
    assert cerrada.json()["estado"] == "CERRADA"


def test_b09_02_configuracion(mundo, gobierno, ocupacion):
    _cuentas(mundo)
    r = _get(mundo, f"{CAUSADOS}/configuracion", usuario="ua")
    assert r.status_code == 200, r.text
    assert r.json()["configurado"] is False
    assert r.json()["patron"] == "{ANIO}-{NUMERO:5}"

    for patron in ("SIN-NUMERO", "{NUMERO:2}"):
        r_inv = _put(mundo, f"{CAUSADOS}/configuracion", "ua", {"patron": patron}, 0)
        assert r_inv.status_code == 422, r_inv.text
        assert r_inv.json()["code"] == "GOV_BUDGET_CAUSE_PATTERN_INVALID"

    r_ok = _put(
        mundo,
        f"{CAUSADOS}/configuracion",
        "ua",
        {"patron": "OBL/{ANIO}/{NUMERO:4}"},
        0,
    )
    assert r_ok.status_code == 200, r_ok.text

    s = _preparar(mundo, ocupacion)
    cdp = _cdp(mundo, s, "402", "100.00")
    r = _comprometer(mundo, s, [{"certificado_id": cdp["id"], "monto": "100.00"}])
    assert r.status_code == 201, r.text
    compromiso = r.json()
    cargo = _cargo_causar(mundo, ocupacion)
    politica = _politica(mundo)
    politica = _activar_politica(mundo, politica)
    causado = _causar(mundo, s, compromiso, cargo, politica)
    formalizado = _formalizado(mundo, causado["id"], causado["version"])
    assert re.match(r"OBL/\d+/0001$", formalizado["codigo"]), formalizado["codigo"]


def test_b09_03_crear_borrador_documental(mundo, gobierno, ocupacion):
    _cuentas(mundo)
    s = _preparar(mundo, ocupacion)
    r = _comprometer(
        mundo,
        s,
        [{"certificado_id": _cdp(mundo, s, "402", "100.00")["id"], "monto": "100.00"}],
    )
    compromiso = r.json()
    cargo = _cargo_causar(mundo, ocupacion)
    tipo_soporte = _tipo_documento_soporte(mundo, s["soporte"])
    politica = _politica(
        mundo,
        disparador="DOCUMENTARY",
        documentos=[
            {
                "document_type_id": tipo_soporte,
                "obligatorio": True,
                "etapa": "FORMALIZACION",
            }
        ],
    )
    politica = _activar_politica(mundo, politica)
    evidencia = {"tipo": "DOCUMENT", "id": _documento(mundo, s["year_id"])}

    causado = _borrador_documental(mundo, s, compromiso, cargo, politica, evidencia)
    assert causado["estado"] == "BORRADOR"
    assert causado["codigo"] is None
    assert causado["monto"] == "30.00"
    assert causado["moneda"] == s["moneda"]
    assert causado["historia"][0]["evento"] == "PREPARADO"
    assert len(_eventos(mundo, "GOV_BUDGET_CAUSE_DRAFT_CREATED", causado["id"])) >= 1


def test_b09_04_editar_borrador(mundo, gobierno, ocupacion):
    _cuentas(mundo)
    s = _preparar(mundo, ocupacion)
    r = _comprometer(
        mundo,
        s,
        [{"certificado_id": _cdp(mundo, s, "403", "100.00")["id"], "monto": "100.00"}],
    )
    compromiso = r.json()
    cargo = _cargo_causar(mundo, ocupacion)
    politica = _politica(mundo)
    politica = _activar_politica(mundo, politica)
    causado = _causar(mundo, s, compromiso, cargo, politica)

    sin_version = _put_sin_version(
        mundo,
        f"{CAUSADOS}/{causado['id']}",
        "caus_b09",
        {
            "compromiso_id": causado["compromiso"]["id"],
            "politica_id": causado["politica"]["id"],
            "fecha_efectiva": causado["fecha_efectiva"],
            "concepto": "Sin version",
            "autoridad_cargo_id": cargo,
            "lineas": [
                {
                    "linea_compromiso_id": causado["lineas"][0]["linea_compromiso_id"],
                    "monto": "30.00",
                }
            ],
            "evidencias": [],
        },
    )
    assert sin_version.status_code == 428

    vieja = _put(
        mundo,
        f"{CAUSADOS}/{causado['id']}",
        "caus_b09",
        {
            "compromiso_id": causado["compromiso"]["id"],
            "politica_id": causado["politica"]["id"],
            "fecha_efectiva": causado["fecha_efectiva"],
            "concepto": "Version vieja",
            "autoridad_cargo_id": cargo,
            "lineas": [
                {
                    "linea_compromiso_id": causado["lineas"][0]["linea_compromiso_id"],
                    "monto": "30.00",
                }
            ],
            "evidencias": [],
        },
        causado["version"] - 1,
    )
    assert vieja.status_code == 409
    assert vieja.json()["code"] == "GOV_BUDGET_CAUSE_STALE"

    correcta = _put(
        mundo,
        f"{CAUSADOS}/{causado['id']}",
        "caus_b09",
        {
            "compromiso_id": causado["compromiso"]["id"],
            "politica_id": causado["politica"]["id"],
            "fecha_efectiva": causado["fecha_efectiva"],
            "concepto": "Concepto editado correctamente",
            "autoridad_cargo_id": cargo,
            "lineas": [
                {
                    "linea_compromiso_id": causado["lineas"][0]["linea_compromiso_id"],
                    "monto": "30.00",
                }
            ],
            "evidencias": [],
        },
        causado["version"],
    )
    assert correcta.status_code == 200, correcta.text
    assert correcta.json()["version"] == causado["version"] + 1


def test_b09_05_formalizar_parcial(mundo, gobierno, ocupacion):
    _cuentas(mundo)
    s = _preparar(mundo, ocupacion)
    r = _comprometer(
        mundo,
        s,
        [{"certificado_id": _cdp(mundo, s, "404", "100.00")["id"], "monto": "100.00"}],
    )
    compromiso = r.json()
    cargo = _cargo_causar(mundo, ocupacion)
    politica = _politica(mundo)
    politica = _activar_politica(mundo, politica)
    causado = _causar(mundo, s, compromiso, cargo, politica, monto="30.00")

    formalizado = _formalizado(mundo, causado["id"], causado["version"])
    assert formalizado["estado"] == "FORMALIZADO"
    assert formalizado["codigo"]
    assert formalizado["numero"]
    assert re.fullmatch(r"[0-9a-f]{64}", formalizado["huella"])
    assert formalizado["lineas"][0]["pendiente_tras"] == "70.00"
    assert len(_eventos(mundo, "GOV_BUDGET_CAUSE_FORMALIZED", causado["id"])) >= 1
    assert any(h["evento"] == "FORMALIZADO" for h in formalizado["historia"])
    assert formalizado["registrado_en"] != formalizado["fecha_efectiva"]


def test_b09_06_multiples_parciales(mundo, gobierno, ocupacion):
    _cuentas(mundo)
    s = _preparar(mundo, ocupacion)
    r = _comprometer(
        mundo,
        s,
        [{"certificado_id": _cdp(mundo, s, "405", "100.00")["id"], "monto": "100.00"}],
    )
    compromiso = r.json()
    cargo = _cargo_causar(mundo, ocupacion)
    politica = _politica(mundo)
    politica = _activar_politica(mundo, politica)

    c1 = _causar(mundo, s, compromiso, cargo, politica, monto="30.00")
    c2 = _causar(mundo, s, compromiso, cargo, politica, monto="40.00")
    _formalizado(mundo, c1["id"], c1["version"])
    _formalizado(mundo, c2["id"], c2["version"])

    c3 = _causar_sin_assert(mundo, s, compromiso, cargo, politica, monto="31.00")
    assert c3.status_code == 422
    assert c3.json()["code"] == "GOV_BUDGET_CAUSE_OVER_COMMITMENT"

    c4 = _causar(mundo, s, compromiso, cargo, politica, monto="30.00")
    formalizado = _formalizado(mundo, c4["id"], c4["version"])
    assert formalizado["lineas"][0]["pendiente_tras"] == "0.00"


@ONLY_PG
def test_b09_07_concurrencia(mundo, gobierno, ocupacion):
    _cuentas(mundo)
    s = _preparar(mundo, ocupacion)
    r = _comprometer(
        mundo,
        s,
        [{"certificado_id": _cdp(mundo, s, "402", "100.00")["id"], "monto": "100.00"}],
    )
    compromiso = r.json()
    cargo = _cargo_causar(mundo, ocupacion)
    politica = _politica(mundo)
    politica = _activar_politica(mundo, politica)

    c1 = _causar(mundo, s, compromiso, cargo, politica, monto="60.00")
    c2 = _causar(mundo, s, compromiso, cargo, politica, monto="60.00")
    versiones = [c1["version"], c2["version"]]
    ids = [c1["id"], c2["id"]]

    barrera = threading.Barrier(2, timeout=30)
    resultados: list[int] = []
    cuerpos: list[dict] = []
    ganadores: list[str] = []

    cabeceras = mundo.como("caus_b09", mundo.company_a)

    def formalizar(causado_id, version):
        barrera.wait()
        r = mundo.client.post(
            f"/api/v1{CAUSADOS}/{causado_id}/formalizar",
            headers={**cabeceras, "If-Match": str(version)},
        )
        resultados.append(r.status_code)
        cuerpos.append(r.json())
        if r.status_code == 200:
            ganadores.append(causado_id)

    hilos = [
        threading.Thread(target=formalizar, args=(ids[i], versiones[i]))
        for i in range(2)
    ]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(timeout=35)

    assert sorted(resultados) == [200, 422]
    assert "GOV_BUDGET_CAUSE_OVER_COMMITMENT" in {
        cuerpo.get("code") for cuerpo in cuerpos if cuerpo.get("code")
    }

    assert len(ganadores) == 1
    ganador_id = ganadores[0]
    detalle = _detalle(mundo, ganador_id)
    assert detalle["lineas"][0]["pendiente_tras"] == "40.00"


def test_b09_08_compromiso_invalido(mundo, gobierno, ocupacion):
    _cuentas(mundo)
    s = _preparar(mundo, ocupacion)
    cargo = _cargo_causar(mundo, ocupacion)
    politica = _politica(mundo)
    politica = _activar_politica(mundo, politica)

    r = _post(
        mundo,
        f"{P}/{s['year_id']}/causados",
        "caus_b09",
        mundo.company_a,
        {
            "compromiso_id": str(uuid4()),
            "politica_id": politica["id"],
            "fecha_efectiva": hoy_de_negocio().isoformat(),
            "concepto": "Compromiso inexistente",
            "autoridad_cargo_id": cargo,
            "lineas": [{"linea_compromiso_id": str(uuid4()), "monto": "30.00"}],
            "evidencias": [],
        },
    )
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_BUDGET_CAUSE_COMMITMENT_INVALID"

    cdp = _cdp(mundo, s, "403", "100.00")
    r_compromiso = _comprometer(
        mundo,
        s,
        [{"certificado_id": cdp["id"], "monto": "100.00"}],
    )
    compromiso = r_compromiso.json()
    anulacion = _post(
        mundo,
        f"{P}/{s['year_id']}/compromisos/{compromiso['id']}/anular",
        "compr_b08",
        mundo.company_a,
        {"motivo": "Anulación de prueba"},
    )
    assert anulacion.status_code == 200, anulacion.text
    r = _causar_sin_assert(mundo, s, compromiso, cargo, politica)
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_BUDGET_CAUSE_COMMITMENT_INVALID"


def test_b09_09_aislamiento(mundo, gobierno, ocupacion):
    _cuentas(mundo)
    s = _preparar(mundo, ocupacion)
    r = _comprometer(
        mundo,
        s,
        [{"certificado_id": _cdp(mundo, s, "404", "100.00")["id"], "monto": "100.00"}],
    )
    compromiso = r.json()
    cargo = _cargo_causar(mundo, ocupacion)
    politica = _politica(mundo)
    politica = _activar_politica(mundo, politica)
    causado = _causar(mundo, s, compromiso, cargo, politica)

    r_get = _get(mundo, f"{CAUSADOS}/{causado['id']}", usuario="ub", empresa=mundo.company_b)
    assert r_get.status_code == 404

    cuerpo_ajeno = {
        "compromiso_id": compromiso["id"],
        "politica_id": politica["id"],
        "fecha_efectiva": hoy_de_negocio().isoformat(),
        "concepto": "Causado ajeno",
        "autoridad_cargo_id": cargo,
        "lineas": [{"linea_compromiso_id": str(uuid4()), "monto": "10.00"}],
        "evidencias": [],
    }
    r_post = _post(
        mundo,
        f"{P}/{s['year_id']}/causados",
        "ub",
        mundo.company_b,
        cuerpo_ajeno,
    )
    assert r_post.status_code != 201


def test_b09_10_autoridad(mundo, gobierno, ocupacion):
    _cuentas(mundo)
    s = _preparar(mundo, ocupacion)
    r = _comprometer(
        mundo,
        s,
        [{"certificado_id": _cdp(mundo, s, "405", "100.00")["id"], "monto": "100.00"}],
    )
    compromiso = r.json()
    politica = _politica(mundo)
    politica = _activar_politica(mundo, politica)

    cargo_causar = _cargo_causar(mundo, ocupacion)
    cargo_comprometer = s["sin_limite"]

    b1 = _causar(mundo, s, compromiso, None, politica, monto="10.00")
    r1 = _post(mundo, f"{CAUSADOS}/{b1['id']}/formalizar", "caus_b09", mundo.company_a, {}, version=b1["version"])
    assert r1.status_code == 422, r1.text
    assert r1.json()["code"] == "GOV_BUDGET_CAUSE_AUTHORITY_INVALID"

    b2 = _causar(mundo, s, compromiso, cargo_comprometer, politica, monto="10.00")
    r2 = _post(mundo, f"{CAUSADOS}/{b2['id']}/formalizar", "caus_b09", mundo.company_a, {}, version=b2["version"])
    assert r2.status_code == 422, r2.text
    assert r2.json()["code"] == "GOV_BUDGET_CAUSE_AUTHORITY_INVALID"

    b3 = _causar(mundo, s, compromiso, cargo_causar, politica, monto="10.00")
    formalizado = _formalizado(mundo, b3["id"], b3["version"])
    assert formalizado["estado"] == "FORMALIZADO"


def test_b09_11_sod(mundo, gobierno, ocupacion):
    _cuentas(mundo)
    s = _preparar(mundo, ocupacion)
    cdp = _cdp(mundo, s, "406", "100.00")
    r = _comprometer(
        mundo,
        s,
        [{"certificado_id": cdp["id"], "monto": "100.00"}],
        usuario="compcaus_b09",
    )
    assert r.status_code == 201, r.text
    compromiso = r.json()
    cargo = _cargo_causar(mundo, ocupacion)
    politica = _politica(mundo)
    politica = _activar_politica(mundo, politica)
    causado = _causar(mundo, s, compromiso, cargo, politica, monto="30.00")

    regla = crear_regla(
        mundo,
        proceso="BUD-09",
        accion_a="BUD09_COMPROMETER",
        accion_b="BUD09_CAUSAR",
        nombre="SoD BUD-09",
    )
    regla = activar_regla(mundo, regla)

    try:
        r_conflicto = _post(
            mundo,
            f"{CAUSADOS}/{causado['id']}/formalizar",
            "compcaus_b09",
            mundo.company_a,
            {},
            version=causado["version"],
        )
        assert r_conflicto.status_code == 409
        assert r_conflicto.json()["code"] == "GOV_SOD_CONFLICT"

        detalle = _detalle(mundo, causado["id"])
        r_otro = _post(
            mundo,
            f"{CAUSADOS}/{causado['id']}/formalizar",
            "caus_b09",
            mundo.company_a,
            {},
            version=detalle["version"],
        )
        assert r_otro.status_code == 200, r_otro.text
    finally:
        cerrar_regla(mundo, regla)


def test_b09_12_documento_exigido(mundo, gobierno, ocupacion):
    _cuentas(mundo)
    s = _preparar(mundo, ocupacion)
    r = _comprometer(
        mundo,
        s,
        [{"certificado_id": _cdp(mundo, s, "402", "100.00")["id"], "monto": "100.00"}],
    )
    compromiso = r.json()
    cargo = _cargo_causar(mundo, ocupacion)

    tipo_soporte = _tipo_documento_soporte(mundo, s["soporte"])
    tipo_nuevo = _documento_nuevo_tipo(mundo)

    politica = _politica(
        mundo,
        disparador="DOCUMENTARY",
        documentos=[
            {"document_type_id": tipo_soporte, "obligatorio": True, "etapa": "FORMALIZACION"},
            {"document_type_id": tipo_nuevo, "obligatorio": True, "etapa": "FORMALIZACION"},
        ],
    )
    politica = _activar_politica(mundo, politica)

    causado = _causar(
        mundo,
        s,
        compromiso,
        cargo,
        politica,
        evidencias=[{"tipo": "DOCUMENT", "id": s["soporte"]}],
    )
    r = _post(
        mundo,
        f"{CAUSADOS}/{causado['id']}/formalizar",
        "caus_b09",
        mundo.company_a,
        {},
        version=causado["version"],
    )
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_BUDGET_CAUSE_DOCUMENTS_MISSING"


def test_b09_13_evidencia_exigida(mundo, gobierno, ocupacion):
    _cuentas(mundo)
    s = _preparar(mundo, ocupacion)
    r = _comprometer(
        mundo,
        s,
        [{"certificado_id": _cdp(mundo, s, "403", "100.00")["id"], "monto": "100.00"}],
    )
    compromiso = r.json()
    cargo = _cargo_causar(mundo, ocupacion)

    politica = _politica(mundo, disparador="VALUATION_APPROVED", documentos=[])
    politica = _activar_politica(mundo, politica)
    causado = _causar(mundo, s, compromiso, cargo, politica, evidencias=[])
    r = _post(
        mundo,
        f"{CAUSADOS}/{causado['id']}/formalizar",
        "caus_b09",
        mundo.company_a,
        {},
        version=causado["version"],
    )
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_BUDGET_CAUSE_EVIDENCE_MISSING"

    r_evidencia_invalida = _causar_sin_assert(
        mundo,
        s,
        compromiso,
        cargo,
        politica,
        evidencias=[{"tipo": "DOCUMENT", "id": str(uuid4())}],
    )
    assert r_evidencia_invalida.status_code == 422
    assert r_evidencia_invalida.json()["code"] == "GOV_BUDGET_CAUSE_EVIDENCE_INVALID"


def test_b09_14_fecha_efectiva(mundo, gobierno, ocupacion):
    _cuentas(mundo)
    s = _preparar(mundo, ocupacion)
    r = _comprometer(
        mundo,
        s,
        [{"certificado_id": _cdp(mundo, s, "404", "100.00")["id"], "monto": "100.00"}],
    )
    compromiso = r.json()
    cargo = _cargo_causar(mundo, ocupacion)
    politica = _politica(mundo)
    politica = _activar_politica(mundo, politica)

    hoy = hoy_de_negocio()
    fechas_invalidas = [
        hoy + timedelta(days=1),
        date(hoy.year - 1, 12, 31),
        hoy - timedelta(days=1),
    ]
    for fecha in fechas_invalidas:
        r_causado = _causar_sin_assert(
            mundo,
            s,
            compromiso,
            cargo,
            politica,
            fecha_efectiva=fecha.isoformat(),
        )
        assert r_causado.status_code == 422, r_causado.text
        assert r_causado.json()["code"] == "GOV_BUDGET_CAUSE_DATE_INVALID"


def test_b09_15_permisos(mundo, gobierno, ocupacion):
    _cuentas(mundo)
    s = _preparar(mundo, ocupacion)
    r = _comprometer(
        mundo,
        s,
        [{"certificado_id": _cdp(mundo, s, "405", "100.00")["id"], "monto": "100.00"}],
    )
    compromiso = r.json()
    cargo = _cargo_causar(mundo, ocupacion)
    politica = _politica(mundo)
    politica = _activar_politica(mundo, politica)

    cuerpo = {
        "compromiso_id": compromiso["id"],
        "politica_id": politica["id"],
        "fecha_efectiva": hoy_de_negocio().isoformat(),
        "concepto": "Sin permiso cause",
        "autoridad_cargo_id": cargo,
        "lineas": [
            {
                "linea_compromiso_id": _linea(mundo, s, compromiso["id"]),
                "monto": "10.00",
            }
        ],
        "evidencias": [],
    }
    r_403 = _post(
        mundo,
        f"{P}/{s['year_id']}/causados",
        "solo_ver_b09",
        mundo.company_a,
        cuerpo,
    )
    assert r_403.status_code == 403

    assert "cause" in CATALOGO_DE_PERMISOS["gobierno_presupuesto"]
    assert "cause_policy" in CATALOGO_DE_PERMISOS["gobierno_presupuesto"]
    assert classify(["gobierno_presupuesto:cause"]) == SENSITIVE
    assert classify(["gobierno_presupuesto:cause_policy"]) == SENSITIVE


def test_b09_16_anular(mundo, gobierno, ocupacion):
    _cuentas(mundo)
    s = _preparar(mundo, ocupacion)
    r = _comprometer(
        mundo,
        s,
        [{"certificado_id": _cdp(mundo, s, "406", "100.00")["id"], "monto": "100.00"}],
    )
    compromiso = r.json()
    cargo = _cargo_causar(mundo, ocupacion)
    politica = _politica(mundo)
    politica = _activar_politica(mundo, politica)
    causado = _causar(mundo, s, compromiso, cargo, politica, monto="30.00")
    formalizado = _formalizado(mundo, causado["id"], causado["version"])

    r_anular_compromiso = _post(
        mundo,
        f"{P}/{s['year_id']}/compromisos/{compromiso['id']}/anular",
        "compr_b08",
        mundo.company_a,
        {"motivo": "Intento con causado"},
    )
    assert r_anular_compromiso.status_code == 409
    assert r_anular_compromiso.json()["code"] == "GOV_BUDGET_COMMITMENT_HAS_CAUSES"

    r_sin_motivo = _post(
        mundo,
        f"{CAUSADOS}/{causado['id']}/anular",
        "caus_b09",
        mundo.company_a,
        {},
        version=formalizado["version"],
    )
    assert r_sin_motivo.status_code == 422

    r_anular = _post(
        mundo,
        f"{CAUSADOS}/{causado['id']}/anular",
        "caus_b09",
        mundo.company_a,
        {"motivo": "Anulación correcta"},
        version=formalizado["version"],
    )
    assert r_anular.status_code == 200, r_anular.text
    assert r_anular.json()["estado"] == "ANULADO"

    lineas = _opciones_compromiso(mundo, s, compromiso["id"])
    assert Decimal(lineas[0]["pendiente"]) == Decimal("100.00")

    borrador = _causar(mundo, s, compromiso, cargo, politica, monto="10.00")
    r_anular_borrador = _post(
        mundo,
        f"{CAUSADOS}/{borrador['id']}/anular",
        "caus_b09",
        mundo.company_a,
        {"motivo": "Borrador no formalizado"},
        version=borrador["version"],
    )
    assert r_anular_borrador.status_code == 409
    assert r_anular_borrador.json()["code"] == "GOV_BUDGET_CAUSE_NOT_FORMALIZED"


@ONLY_PG
def test_b09_17_inmutable(mundo, gobierno, ocupacion):
    _cuentas(mundo)
    s = _preparar(mundo, ocupacion)
    r = _comprometer(
        mundo,
        s,
        [{"certificado_id": _cdp(mundo, s, "407", "100.00")["id"], "monto": "100.00"}],
    )
    compromiso = r.json()
    cargo = _cargo_causar(mundo, ocupacion)
    politica = _politica(mundo)
    politica = _activar_politica(mundo, politica)
    causado = _causar(mundo, s, compromiso, cargo, politica, monto="30.00")
    formalizado = _formalizado(mundo, causado["id"], causado["version"])

    causa_id = formalizado["id"]
    linea_id = formalizado["lineas"][0]["linea_compromiso_id"]
    company_id = mundo.company_a
    commitment_line_id = linea_id

    with mundo.factory() as db:
        with pytest.raises(DBAPIError) as exc:
            db.execute(
                text("UPDATE gov_budget_causes SET monto = 1 WHERE id = :i"),
                {"i": causa_id},
            )
            db.commit()
        assert "GOV_BUDGET_CAUSE_IMMUTABLE" in str(exc.value)
        db.rollback()

        with pytest.raises(DBAPIError) as exc:
            db.execute(
                text("DELETE FROM gov_budget_causes WHERE id = :i"),
                {"i": causa_id},
            )
            db.commit()
        assert "GOV_BUDGET_CAUSE_IMMUTABLE" in str(exc.value)
        db.rollback()

        with pytest.raises(DBAPIError) as exc:
            db.execute(
                text(
                    "INSERT INTO gov_budget_cause_lines "
                    "(id, cause_id, company_id, commitment_line_id, monto, created_at, updated_at) "
                    "VALUES (:id, :c, :e, :l, 1, now(), now())"
                ),
                {
                    "id": str(uuid4()),
                    "c": causa_id,
                    "e": company_id,
                    "l": commitment_line_id,
                },
            )
            db.commit()
        assert "IMMUTABLE" in str(exc.value)
        db.rollback()


def test_b09_18_controles(mundo, gobierno, ocupacion):
    _cuentas(mundo)
    s = _preparar(mundo, ocupacion)
    r = _comprometer(
        mundo,
        s,
        [{"certificado_id": _cdp(mundo, s, "402", "100.00")["id"], "monto": "100.00"}],
    )
    compromiso = r.json()
    cargo = _cargo_causar(mundo, ocupacion)

    tipo_soporte = _tipo_documento_soporte(mundo, s["soporte"])
    politica_doc = _politica(
        mundo,
        disparador="DOCUMENTARY",
        documentos=[
            {
                "document_type_id": tipo_soporte,
                "obligatorio": True,
                "etapa": "FORMALIZACION",
            }
        ],
    )
    politica_doc = _activar_politica(mundo, politica_doc)

    sin_evidencia = _causar(mundo, s, compromiso, cargo, politica_doc, evidencias=[])
    r_controles_sin = _get(mundo, f"{CAUSADOS}/{sin_evidencia['id']}/controles")
    assert r_controles_sin.status_code == 200, r_controles_sin.text
    controles_sin = {c["codigo"]: c for c in r_controles_sin.json()["controles"]}
    assert controles_sin["DOCUMENTOS"]["cumplido"] is False
    assert controles_sin["EVIDENCIA_DISPARADOR"]["cumplido"] is False
    assert all(
        c["cumplido"]
        for c in controles_sin.values()
        if c["codigo"] not in {"DOCUMENTOS", "EVIDENCIA_DISPARADOR"}
    )

    con_evidencia = _causar(
        mundo,
        s,
        compromiso,
        cargo,
        politica_doc,
        evidencias=[{"tipo": "DOCUMENT", "id": s["soporte"]}],
    )
    r_controles_con = _get(mundo, f"{CAUSADOS}/{con_evidencia['id']}/controles")
    assert r_controles_con.status_code == 200, r_controles_con.text
    controles_con = r_controles_con.json()["controles"]
    assert any(c["codigo"] == "DOCUMENTOS" for c in controles_con)
    assert all(c["cumplido"] for c in controles_con)


def test_b09_19_listado_filtros_csv(mundo, gobierno, ocupacion):
    _cuentas(mundo)
    s = _preparar(mundo, ocupacion)
    r = _comprometer(
        mundo,
        s,
        [{"certificado_id": _cdp(mundo, s, "403", "100.00")["id"], "monto": "100.00"}],
    )
    compromiso = r.json()
    cargo = _cargo_causar(mundo, ocupacion)
    politica = _politica(mundo)
    politica = _activar_politica(mundo, politica)
    causado = _causar(
        mundo,
        s,
        compromiso,
        cargo,
        politica,
        monto="30.00",
        concepto="CONCEPTO FILTRO Q",
    )
    _formalizado(mundo, causado["id"], causado["version"])

    r_filtro = _get(
        mundo,
        f"{P}/{s['year_id']}/causados?estado=FORMALIZADO",
    )
    assert r_filtro.status_code == 200, r_filtro.text
    assert causado["id"] in {x["id"] for x in r_filtro.json()["items"]}

    r_q = _get(mundo, f"{P}/{s['year_id']}/causados?q=FILTRO")
    assert r_q.status_code == 200, r_q.text
    assert any("FILTRO" in x["concepto"] for x in r_q.json()["items"])

    r_csv = mundo.client.get(
        f"/api/v1{P}/{s['year_id']}/causados/reporte.csv",
        headers=mundo.como("caus_b09", mundo.company_a),
    )
    assert r_csv.status_code == 200, r_csv.text
    assert "text/csv" in r_csv.headers.get("content-type", "")
    primera = r_csv.content.decode("utf-8-sig").splitlines()[0]
    assert primera.startswith("Código;Fecha efectiva;Compromiso")


def test_b09_20_opciones(mundo, gobierno, ocupacion):
    _cuentas(mundo)
    s = _preparar(mundo, ocupacion)
    r = _comprometer(
        mundo,
        s,
        [{"certificado_id": _cdp(mundo, s, "404", "100.00")["id"], "monto": "100.00"}],
    )
    compromiso = r.json()
    _cargo_causar(mundo, ocupacion)
    politica = _politica(mundo)
    politica = _activar_politica(mundo, politica)

    r_opciones = _get(mundo, f"{P}/{s['year_id']}/causados/opciones")
    assert r_opciones.status_code == 200, r_opciones.text
    payload = r_opciones.json()
    assert compromiso["id"] in {x["id"] for x in payload["compromisos"]}
    assert politica["id"] in {x["id"] for x in payload["politicas"]}

    r_con = _get(
        mundo,
        f"{P}/{s['year_id']}/causados/opciones?compromiso_id={compromiso['id']}",
    )
    assert r_con.status_code == 200, r_con.text
    documentos = r_con.json()["documentos"]
    assert any(d.get("id") == s["soporte"] for d in documentos)


def test_b09_21_ejercicio_no_aprobado(mundo, gobierno, ocupacion):
    _cuentas(mundo)
    detalle = _completo(mundo, ANIO - 1)
    r = _post(
        mundo,
        f"{P}/{detalle['id']}/causados",
        "caus_b09",
        mundo.company_a,
        {
            "compromiso_id": "00000000-0000-0000-0000-000000000000",
            "politica_id": "00000000-0000-0000-0000-000000000000",
            "fecha_efectiva": hoy_de_negocio().isoformat(),
            "concepto": "Causado en ejercicio no aprobado",
            "autoridad_cargo_id": "00000000-0000-0000-0000-000000000000",
            "lineas": [
                {
                    "linea_compromiso_id": "00000000-0000-0000-0000-000000000000",
                    "monto": "10.00",
                }
            ],
            "evidencias": [],
        },
    )
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_BUDGET_YEAR_INVALID_STATE"


def test_b09_22_frontera_tre03(mundo, gobierno, ocupacion):
    _cuentas(mundo)
    s = _preparar(mundo, ocupacion)
    r = _comprometer(
        mundo,
        s,
        [{"certificado_id": _cdp(mundo, s, "405", "100.00")["id"], "monto": "100.00"}],
    )
    compromiso = r.json()
    cargo = _cargo_causar(mundo, ocupacion)
    politica = _politica(mundo)
    politica = _activar_politica(mundo, politica)
    causado = _causar(mundo, s, compromiso, cargo, politica, monto="30.00")
    formalizado = _formalizado(mundo, causado["id"], causado["version"])

    assert formalizado["monto_ordenado"] == "0.00"
    assert formalizado["pendiente_de_ordenar"] == formalizado["monto"]

    with mundo.factory() as db:
        empresa = db.get(Company, mundo.company_a)
        user_id = db.scalar(
            select(User.id).where(User.username == "caus_b09")
        )
        ctx = CompanyContext(
            tenant_id=empresa.tenant_id,
            company_id=mundo.company_a,
            company=empresa,
            user_id=user_id,
        )
        filas = service_presupuesto_causado.obligaciones_pendientes_de_ordenar(
            db,
            ctx,
            s["year_id"],
        )
        assert any(
            f["id"] == formalizado["id"]
            and f["pendiente_de_ordenar"] == formalizado["monto"]
            and f["monto_ordenado"] == "0.00"
            for f in filas
        )


def test_b09_23_render_patron():
    from app.modules.government.service_presupuesto_causado import _render_patron

    assert _render_patron("OBL/{ANIO}/{NUMERO:4}", 2026, 7) == "OBL/2026/0007"


def test_b09_24_validar_patron():
    from app.modules.government.service_presupuesto_causado import _validar_patron

    validos = ["{ANIO}-{NUMERO:5}", "OBL/{ANIO}/{NUMERO:4}", "{NUMERO:6}-AB"]
    for patron in validos:
        _validar_patron(patron)

    invalidos = [
        "SIN-NUMERO",
        "{NUMERO:2}-ABCDE",
        "{ANIO}{ANIO}-{NUMERO:4}",
        "{NUMERO:9}-ABCD",
        "{NUMERO}-ABCDE",
        "A B-{NUMERO:4}",
    ]
    for patron in invalidos:
        with pytest.raises(KontrolError) as exc:
            _validar_patron(patron)
        assert exc.value.code == "GOV_BUDGET_CAUSE_PATTERN_INVALID"


def test_b09_25_recepcion_exigida(mundo, gobierno, ocupacion):
    _cuentas(mundo)
    s = _preparar(mundo, ocupacion)
    r = _comprometer(
        mundo,
        s,
        [{"certificado_id": _cdp(mundo, s, "403", "100.00")["id"], "monto": "100.00"}],
    )
    compromiso = r.json()
    cargo = _cargo_causar(mundo, ocupacion)

    politica = _politica(mundo, disparador="VALUATION_APPROVED", documentos=[], requiere_recepcion=True)
    politica = _activar_politica(mundo, politica)
    causado = _causar(mundo, s, compromiso, cargo, politica, evidencias=[])
    r = _post(
        mundo,
        f"{CAUSADOS}/{causado['id']}/formalizar",
        "caus_b09",
        mundo.company_a,
        {},
        version=causado["version"],
    )
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_BUDGET_CAUSE_EVIDENCE_MISSING"
    assert "Falta CONTRACT_RECEIPT" in r.json()["field_errors"]["evidencias"]

    r = _get(mundo, f"{CAUSADOS}/{causado['id']}/controles")
    assert r.status_code == 200
    cuerpo = r.json()
    controles = cuerpo["controles"] if isinstance(cuerpo, dict) else cuerpo
    assert any(control["cumplido"] is False for control in controles)
