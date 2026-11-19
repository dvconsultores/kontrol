"""TRE-04 · Pago con maker-checker (GOV-TRE-004/005/010) — pruebas backend."""
from __future__ import annotations

import threading
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.modules.audit.models import AuditEvent
from app.modules.government.models import (
    GovernmentBank,
    GovernmentBankAccount,
    GovernmentBankAccountAuthorization,
    GovernmentPosition,
    GovernmentPositionCompetency,
    GovernmentPositionVersion,
)
from app.modules.identity_access.mfa_policy import SENSITIVE, classify
from app.modules.identity_access.models import User, UserScope
from app.modules.organization.models import Company
from app.shared.clock import hoy_de_negocio
from tests import test_gov_bud08 as _bud08
from tests import test_gov_bud09_causado as _bud09
from tests.org04_ayudantes import D, _codigo, acto_eficaz
from tests.org06_guarda import cuenta_con_permisos
from tests.test_gov_bud01_ejercicio import ONLY_PG
from tests.test_gov_bud09_causado import _preparar
from tests.test_gov_tre03_orden_pago import (
    _CUENTAS_T03,
    _anular,
    _borrador,
    _cargo_ordenar,
    _causado_formalizado,
    _cuentas_t03,
    _emitir,
    _get_op,
    _politica_op,
    _post_op,
    _put_op,
)

pytest_plugins = (
    "tests.conftest_multicompany",
    "tests.test_gov_ctl06_hallazgos",
    "tests.org04_ayudantes",
)

T = "/gobierno/tesoreria"
_CUENTAS_T04: dict[int, None] = {}


@pytest.fixture(scope="module", autouse=True)
def _aislar_caches():
    _bud08._ESTADO.clear()
    _bud09._CUENTAS.clear()
    _bud09._TIPO_SOPORTE.clear()
    _CUENTAS_T03.clear()
    _CUENTAS_T04.clear()
    yield
    _bud08._ESTADO.clear()
    _bud09._CUENTAS.clear()
    _bud09._TIPO_SOPORTE.clear()
    _CUENTAS_T03.clear()
    _CUENTAS_T04.clear()


def _cuentas_t04(mundo) -> None:
    if id(mundo) in _CUENTAS_T04:
        return
    _cuentas_t03(mundo)
    cuenta_con_permisos(
        mundo,
        "mk_t04",
        [
            ("gobierno_pagos", "view"),
            ("gobierno_pagos", "manage"),
            ("gobierno_pagos", "execute"),
            ("gobierno_pagos", "cancel"),
            ("gobierno_pagos", "policy"),
            ("gobierno_ordenes_pago", "view"),
        ],
    )
    cuenta_con_permisos(
        mundo,
        "ck_t04",
        [("gobierno_pagos", "view"), ("gobierno_pagos", "authorize")],
    )
    cuenta_con_permisos(
        mundo,
        "ck2_t04",
        [("gobierno_pagos", "view"), ("gobierno_pagos", "authorize")],
    )
    cuenta_con_permisos(mundo, "ver_t04", [("gobierno_pagos", "view")])
    _CUENTAS_T04[id(mundo)] = None


def _cargo(
    mundo,
    ocupacion,
    accion="PAGAR",
    materia="TESORERIA",
    tipo_limite="SIN_LIMITE",
    monto=None,
    moneda=None,
) -> str:
    structure_id = ocupacion["estructura"]
    unit_id = ocupacion["unidad_raiz"]
    with mundo.factory() as db:
        cargo = GovernmentPosition(
            company_id=mundo.company_a,
            structure_id=structure_id,
            unit_id=unit_id,
            code=_codigo("T4"),
            name=f"Cargo TRE-04 {_codigo('N')}",
            status="VIGENTE",
            valid_from=D(1, 1),
            activated_at=datetime.now(UTC),
            version=1,
        )
        db.add(cargo)
        db.flush()

        comp = GovernmentPositionCompetency(
            position_id=cargo.id,
            company_id=mundo.company_a,
            action=accion,
            subject=materia,
            limit_type=tipo_limite,
            limit_amount=monto,
            limit_currency=moneda,
            basis="Fundamento de prueba TRE-04",
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
                        "accion": accion,
                        "materia": materia,
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


def _orden_emitida(mundo, s, ocupacion, monto="100.00") -> dict:
    causado = _causado_formalizado(mundo, s, monto=monto)
    politica = _politica_op(mundo)
    cargo = _cargo_ordenar(mundo, ocupacion)
    r = _borrador(
        mundo, s, politica, [{"cause_id": causado["id"], "monto": monto}], cargo
    )
    assert r.status_code == 201, r.text
    emitida = _emitir(mundo, r.json())
    assert emitida.status_code == 200, emitida.text
    return emitida.json()


def _cuenta(mundo, ocupacion, moneda) -> str:
    with mundo.factory() as db:
        company = db.get(Company, mundo.company_a)
        bank = GovernmentBank(
            tenant_id=company.tenant_id,
            company_id=mundo.company_a,
            codigo=uuid4().hex[:4],
            nombre=f"Banco {_codigo('N')}",
            estado="ACTIVO",
        )
        db.add(bank)
        db.flush()

        cargo_id = _cargo(mundo, ocupacion)
        acto_id = acto_eficaz(mundo, cargo_id)
        cuenta_bancaria = GovernmentBankAccount(
            tenant_id=company.tenant_id,
            company_id=mundo.company_a,
            codigo=_codigo("C"),
            denominacion=f"Cuenta {_codigo('N')}",
            bank_id=bank.id,
            tipo="CORRIENTE",
            numero=str(uuid4().int)[:20].zfill(20),
            moneda=moneda,
            vigente_desde=D(1, 1),
            estado="VIGENTE",
            acto_id=acto_id,
            activada_en=datetime.now(UTC),
            activada_por=None,
        )
        db.add(cuenta_bancaria)
        db.commit()
        return str(cuenta_bancaria.id)


def _firmante(mundo, cuenta_id, cargo_id) -> None:
    with mundo.factory() as db:
        firma = GovernmentBankAccountAuthorization(
            account_id=cuenta_id,
            company_id=mundo.company_a,
            position_id=cargo_id,
            cargo_codigo=_codigo("F"),
            cargo_denominacion="Firmante TRE-04",
            cargo_unidad="Unidad TRE-04",
            acto_alta_id=acto_eficaz(mundo, cargo_id),
            vigente_desde=D(1, 1),
        )
        db.add(firma)
        db.commit()


def _medio(mundo, **cambios) -> dict:
    cuerpo = {
        "codigo": "M" + uuid4().hex[:8].upper(),
        "nombre": "Medio de prueba",
        "vigente_desde": D(1, 1).isoformat(),
        "exige_referencia": True,
        "referencia_unica": True,
        "fundamento": "Fundamento de prueba del medio",
    }
    cuerpo.update(cambios)
    r = _post_op(mundo, f"{T}/medios-pago", "mk_t04", cuerpo)
    assert r.status_code == 201, r.text
    return r.json()


def _politica_pago(
    mundo, medios, moneda, bandas=None, activar=True, **cambios
) -> dict:
    if bandas is None:
        bandas = [
            {
                "monto_desde": "0",
                "monto_hasta": None,
                "requisitos": [
                    {"accion": "PAGAR", "materia": "TESORERIA", "cantidad": 1}
                ],
            }
        ]
    cuerpo = {
        "codigo": "PP" + uuid4().hex[:10].upper(),
        "nombre": "Política de pago TRE-04",
        "moneda": moneda,
        "permite_pago_parcial": True,
        "preparador_competencia_accion": None,
        "preparador_competencia_materia": None,
        "exige_cargo_autorizado_cuenta": False,
        "control_duplicado": "BLOQUEAR",
        "vigente_desde": D(1, 1).isoformat(),
        "fundamento": "Fundamento de prueba de política de pago TRE-04",
        "tipo_regla": "INSTITUTIONAL_POLICY",
        "medios": medios,
        "bandas": bandas,
        "documentos": [],
    }
    cuerpo.update(cambios)
    r = _post_op(mundo, f"{T}/politicas-pago", "mk_t04", cuerpo)
    assert r.status_code == 201, r.text
    politica = r.json()
    if activar:
        r2 = _post_op(
            mundo,
            f"{T}/politicas-pago/{politica['id']}/activar",
            "mk_t04",
            {"fundamento": "Fundamento de activación de política de pago TRE-04"},
            version=politica["version"],
        )
        assert r2.status_code == 200, r2.text
        return r2.json()
    return politica


def _pago(
    mundo, orden, politica, cuenta, medio, monto, usuario="mk_t04", **cambios
):
    cuerpo = {
        "order_id": orden["id"],
        "policy_id": politica["id"],
        "account_id": cuenta,
        "method_id": medio["id"],
        "monto": monto,
        "fecha_pago": hoy_de_negocio().isoformat(),
        "concepto": "Pago de prueba TRE-04",
    }
    cuerpo.update(cambios)
    return _post_op(mundo, f"{T}/pagos", usuario, cuerpo)


def _enviar(mundo, pago, usuario="mk_t04", **cuerpo):
    return _post_op(
        mundo,
        f"{T}/pagos/{pago['id']}/enviar",
        usuario,
        cuerpo,
        version=pago["version"],
    )


def _aprobar(
    mundo, pago, cargo, indice=0, usuario="ck_t04", documentos=None
):
    cuerpo = {"cargo_id": cargo, "requisito_indice": indice}
    if documentos is not None:
        cuerpo["documentos"] = documentos
    return _post_op(
        mundo,
        f"{T}/pagos/{pago['id']}/aprobar",
        usuario,
        cuerpo,
        version=pago["version"],
    )


def _rechazar(mundo, pago, cargo, usuario="ck_t04"):
    return _post_op(
        mundo,
        f"{T}/pagos/{pago['id']}/rechazar",
        usuario,
        {"cargo_id": cargo, "motivo": "Motivo de rechazo TRE-04"},
        version=pago["version"],
    )


def _registrar(
    mundo,
    pago,
    referencia,
    usuario="mk_t04",
    fecha_valor=None,
    documentos=None,
    idempotency_key=None,
):
    cuerpo = {"referencia_externa": referencia, "fecha_valor": fecha_valor if fecha_valor is not None else hoy_de_negocio().isoformat()}
    if documentos is not None:
        cuerpo["documentos"] = documentos
    if idempotency_key is not None:
        cuerpo["idempotency_key"] = idempotency_key
    return _post_op(
        mundo,
        f"{T}/pagos/{pago['id']}/registrar",
        usuario,
        cuerpo,
        version=pago["version"],
    )


def _anular_pago(mundo, pago, usuario="mk_t04"):
    return _post_op(
        mundo,
        f"{T}/pagos/{pago['id']}/anular",
        usuario,
        {"motivo": "Motivo de anulación TRE-04", "documentos": []},
        version=pago["version"],
    )


def _pagado(mundo, orden_id) -> dict:
    r = _get_op(mundo, f"{T}/ordenes-pago/{orden_id}", "mk_t04")
    assert r.status_code == 200, r.text
    return r.json()


def test_t04_01_crear_politica(mundo, gobierno, ocupacion):
    _cuentas_t04(mundo)
    s = _preparar(mundo, ocupacion)
    r = _post_op(
        mundo,
        f"{T}/politicas-pago",
        "mk_t04",
        {
            "codigo": "PP" + uuid4().hex[:10].upper(),
            "nombre": "Política TRE-04 creada",
            "moneda": s["moneda"],
            "permite_pago_parcial": True,
            "preparador_competencia_accion": "PAGAR",
            "preparador_competencia_materia": "TESORERIA",
            "exige_cargo_autorizado_cuenta": False,
            "control_duplicado": "BLOQUEAR",
            "vigente_desde": D(1, 1).isoformat(),
            "fundamento": "Fundamento de prueba de política de pago TRE-04",
            "tipo_regla": "INSTITUTIONAL_POLICY",
            "medios": [],
            "bandas": [],
            "documentos": [],
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["estado"] == "BORRADOR"
    assert body["numero_version"] == 1
    with mundo.factory() as db:
        evento = db.scalar(
            select(AuditEvent).where(
                AuditEvent.action == "GOV_PAYMENT_POLICY_CREATED",
                AuditEvent.entity_id == body["id"],
            )
        )
        assert evento is not None


def test_t04_02_activar_politica(mundo, gobierno, ocupacion):
    _cuentas_t04(mundo)
    s = _preparar(mundo, ocupacion)
    medio = _medio(mundo)
    politica = _politica_pago(mundo, [medio["id"]], s["moneda"])
    assert politica["estado"] == "VIGENTE"
    assert politica["numero_version"] == 1

    sin_medios = _politica_pago(
        mundo, [], s["moneda"], activar=False, codigo="PP" + uuid4().hex[:10].upper()
    )
    r = _post_op(
        mundo,
        f"{T}/politicas-pago/{sin_medios['id']}/activar",
        "mk_t04",
        {"fundamento": "Fundamento de activación TRE-04"},
        version=sin_medios["version"],
    )
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "GOV_PAYMENT_POLICY_METHODS_REQUIRED"

    bandas_invalidas = [
        {"monto_desde": "0", "monto_hasta": "100", "requisitos": [{"accion": "PAGAR", "materia": "TESORERIA", "cantidad": 1}]},
        {
            "monto_desde": "200",
            "monto_hasta": None,
            "requisitos": [
                {"accion": "PAGAR", "materia": "TESORERIA", "cantidad": 1}
            ],
        },
    ]
    r = _post_op(
        mundo,
        f"{T}/politicas-pago",
        "mk_t04",
        {
            "codigo": "PP" + uuid4().hex[:10].upper(),
            "nombre": "Política TRE-04 con bandas",
            "moneda": s["moneda"],
            "permite_pago_parcial": True,
            "preparador_competencia_accion": "PAGAR",
            "preparador_competencia_materia": "TESORERIA",
            "exige_cargo_autorizado_cuenta": False,
            "control_duplicado": "BLOQUEAR",
            "vigente_desde": D(1, 1).isoformat(),
            "fundamento": "Fundamento de prueba TRE-04",
            "tipo_regla": "INSTITUTIONAL_POLICY",
            "medios": [medio["id"]],
            "bandas": bandas_invalidas,
            "documentos": [],
        },
    )
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "GOV_PAYMENT_POLICY_BANDS_INVALID"


def test_t04_03_cerrar_politica(mundo, gobierno, ocupacion):
    _cuentas_t04(mundo)
    s = _preparar(mundo, ocupacion)
    medio = _medio(mundo)
    politica = _politica_pago(mundo, [medio["id"]], s["moneda"])
    r = _post_op(
        mundo,
        f"{T}/politicas-pago/{politica['id']}/cerrar",
        "mk_t04",
        {"motivo": "Motivo de cierre TRE-04"},
        version=politica["version"],
    )
    assert r.status_code == 200, r.text
    cerrada = r.json()
    assert cerrada["estado"] == "CERRADA"

    r2 = _put_op(
        mundo,
        f"{T}/politicas-pago/{politica['id']}",
        "mk_t04",
        {"nombre": "Nueva edición TRE-04"},
        cerrada["version"],
    )
    assert r2.status_code == 409, r2.text
    assert r2.json()["code"] == "GOV_PAYMENT_POLICY_NOT_DRAFT"


def test_t04_04_nueva_version_politica(mundo, gobierno, ocupacion):
    _cuentas_t04(mundo)
    s = _preparar(mundo, ocupacion)
    medio = _medio(mundo)
    politica = _politica_pago(mundo, [medio["id"]], s["moneda"])
    r = _post_op(
        mundo,
        f"{T}/politicas-pago/{politica['id']}/nueva-version",
        "mk_t04",
        {},
    )
    assert r.status_code == 201, r.text
    v2 = r.json()
    assert v2["codigo"] == politica["codigo"]
    assert v2["numero_version"] == 2
    assert v2["estado"] == "BORRADOR"
    assert [m["id"] for m in v2["medios"]] == [medio["id"]]
    assert len(v2["bandas"]) == len(politica["bandas"])

    r2 = _post_op(
        mundo,
        f"{T}/politicas-pago/{politica['id']}/nueva-version",
        "mk_t04",
        {},
    )
    assert r2.status_code == 409, r2.text
    assert r2.json()["code"] == "GOV_PAYMENT_POLICY_DRAFT_EXISTS"

    vigente_desde = (datetime.now(UTC).date() + timedelta(days=1)).isoformat()
    r3 = _put_op(
        mundo,
        f"{T}/politicas-pago/{v2['id']}",
        "mk_t04",
        {"vigente_desde": vigente_desde},
        v2["version"],
    )
    assert r3.status_code == 200, r3.text
    v2_actualizada = r3.json()
    r4 = _post_op(
        mundo,
        f"{T}/politicas-pago/{v2_actualizada['id']}/activar",
        "mk_t04",
        {"fundamento": "Fundamento de activación v2 TRE-04"},
        version=v2_actualizada["version"],
    )
    assert r4.status_code == 200, r4.text
    assert r4.json()["estado"] == "VIGENTE"
    detalle_v1 = _get_op(mundo, f"{T}/politicas-pago/{politica['id']}", "mk_t04")
    assert detalle_v1.status_code == 200, detalle_v1.text
    assert detalle_v1.json()["estado"] == "CERRADA"


def test_t04_05_aislamiento_politicas_medios(mundo, gobierno, ocupacion):
    _cuentas_t04(mundo)
    s = _preparar(mundo, ocupacion)
    medio = _medio(mundo)
    politica = _politica_pago(mundo, [medio["id"]], s["moneda"])

    r = mundo.client.get(
        f"/api/v1{T}/politicas-pago",
        headers=mundo.como("ub", mundo.company_b),
    )
    assert r.status_code == 200, r.text
    assert politica["id"] not in [p["id"] for p in r.json()]

    r2 = mundo.client.get(
        f"/api/v1{T}/medios-pago",
        headers=mundo.como("ub", mundo.company_b),
    )
    assert r2.status_code == 200, r2.text
    assert medio["id"] not in [m["id"] for m in r2.json()]

    r3 = mundo.client.get(
        f"/api/v1{T}/politicas-pago/{politica['id']}",
        headers=mundo.como("ub", mundo.company_b),
    )
    assert r3.status_code == 404, r3.text

    r4 = mundo.client.get(
        f"/api/v1{T}/medios-pago/{medio['id']}",
        headers=mundo.como("ub", mundo.company_b),
    )
    assert r4.status_code == 404, r4.text


def test_t04_06_aislamiento_empresa_pagos(mundo, gobierno, ocupacion):
    _cuentas_t04(mundo)
    s = _preparar(mundo, ocupacion)
    orden = _orden_emitida(mundo, s, ocupacion)
    medio = _medio(mundo)
    politica = _politica_pago(mundo, [medio["id"]], s["moneda"])
    cuenta = _cuenta(mundo, ocupacion, s["moneda"])
    r = _pago(mundo, orden, politica, cuenta, medio, "40.00")
    assert r.status_code == 201, r.text
    pago = r.json()

    with mundo.factory() as db:
        mk = db.scalar(select(User).where(User.username == "mk_t04"))
        db.add(UserScope(user_id=mk.id, company_id=mundo.company_b))
        ck = db.scalar(select(User).where(User.username == "ck_t04"))
        db.add(UserScope(user_id=ck.id, company_id=mundo.company_b))
        db.commit()

    rutas = [
        ("GET", f"{T}/pagos/{pago['id']}", "mk_t04", None, None),
        (
            "PUT",
            f"{T}/pagos/{pago['id']}",
            "mk_t04",
            {"concepto": "Edición otra empresa"},
            pago["version"],
        ),
        ("POST", f"{T}/pagos/{pago['id']}/enviar", "mk_t04", {}, pago["version"]),
        (
            "POST",
            f"{T}/pagos/{pago['id']}/aprobar",
            "ck_t04",
            {"cargo_id": "cargo", "requisito_indice": 0},
            pago["version"],
        ),
        (
            "POST",
            f"{T}/pagos/{pago['id']}/registrar",
            "mk_t04",
            {"referencia_externa": "REF-OTRA-EMP", "fecha_valor": hoy_de_negocio().isoformat()},
            pago["version"],
        ),
        (
            "POST",
            f"{T}/pagos/{pago['id']}/anular",
            "mk_t04",
            {"motivo": "Motivo de anulacion valido", "documentos": []},
            pago["version"],
        ),
    ]
    for metodo, ruta, usuario, cuerpo, version in rutas:
        headers = mundo.como(usuario, mundo.company_b)
        if version is not None:
            headers["If-Match"] = str(version)
        if metodo == "GET":
            resp = mundo.client.get(f"/api/v1{ruta}", headers=headers)
        elif metodo == "PUT":
            resp = mundo.client.put(f"/api/v1{ruta}", headers=headers, json=cuerpo)
        else:
            resp = mundo.client.post(f"/api/v1{ruta}", headers=headers, json=cuerpo)
        assert resp.status_code == 404, (ruta, resp.text)


def test_t04_07_medio_permitido(mundo, gobierno, ocupacion):
    _cuentas_t04(mundo)
    s = _preparar(mundo, ocupacion)
    orden = _orden_emitida(mundo, s, ocupacion)
    medio = _medio(mundo)
    politica = _politica_pago(mundo, [medio["id"]], s["moneda"])
    cuenta = _cuenta(mundo, ocupacion, s["moneda"])
    r = _pago(mundo, orden, politica, cuenta, medio, "40.00")
    assert r.status_code == 201, r.text
    pago = r.json()
    r2 = _enviar(mundo, pago)
    assert r2.status_code == 200, r2.text
    assert r2.json()["estado"] == "PENDIENTE_AUTORIZACION"


def test_t04_08_medio_no_permitido(mundo, gobierno, ocupacion):
    _cuentas_t04(mundo)
    s = _preparar(mundo, ocupacion)
    orden = _orden_emitida(mundo, s, ocupacion)
    medio_permitido = _medio(mundo)
    medio_no_permitido = _medio(mundo)
    politica = _politica_pago(mundo, [medio_permitido["id"]], s["moneda"])
    cuenta = _cuenta(mundo, ocupacion, s["moneda"])
    r = _pago(mundo, orden, politica, cuenta, medio_no_permitido, "40.00")
    assert r.status_code == 201, r.text
    pago = r.json()
    r2 = _enviar(mundo, pago)
    assert r2.status_code == 422, r2.text
    assert r2.json()["code"] == "GOV_PAYMENT_METHOD_NOT_ALLOWED"


def test_t04_09_cuenta_origen(mundo, gobierno, ocupacion):
    _cuentas_t04(mundo)
    s = _preparar(mundo, ocupacion)
    orden = _orden_emitida(mundo, s, ocupacion)
    medio = _medio(mundo)
    politica = _politica_pago(mundo, [medio["id"]], s["moneda"])
    moneda_extra = "USD" if s["moneda"] != "USD" else "EUR"
    cuenta_otra_moneda = _cuenta(mundo, ocupacion, moneda_extra)
    r = _pago(mundo, orden, politica, cuenta_otra_moneda, medio, "40.00")
    assert r.status_code == 201, r.text
    pago = r.json()
    r2 = _enviar(mundo, pago)
    assert r2.status_code == 422, r2.text
    assert r2.json()["code"] == "GOV_PAYMENT_ACCOUNT_INVALID"

    cuenta_inactiva = _cuenta(mundo, ocupacion, s["moneda"])
    with mundo.factory() as db:
        cuenta_bd = db.get(GovernmentBankAccount, cuenta_inactiva)
        cuenta_bd.estado = "INACTIVA"
        db.commit()
    r3 = _pago(mundo, orden, politica, cuenta_inactiva, medio, "40.00")
    assert r3.status_code == 201, r3.text
    pago_inactiva = r3.json()
    r4 = _enviar(mundo, pago_inactiva)
    assert r4.status_code == 422, r4.text
    assert r4.json()["code"] == "GOV_PAYMENT_ACCOUNT_INVALID"


def test_t04_10_moneda_politica(mundo, gobierno, ocupacion):
    _cuentas_t04(mundo)
    s = _preparar(mundo, ocupacion)
    orden = _orden_emitida(mundo, s, ocupacion)
    medio = _medio(mundo)
    moneda_distinta = "USD" if s["moneda"] != "USD" else "EUR"
    politica = _politica_pago(mundo, [medio["id"]], moneda_distinta)
    cuenta = _cuenta(mundo, ocupacion, s["moneda"])
    r = _pago(mundo, orden, politica, cuenta, medio, "40.00")
    assert r.status_code == 201, r.text
    pago = r.json()
    r2 = _enviar(mundo, pago)
    assert r2.status_code == 422, r2.text
    assert r2.json()["code"] == "GOV_PAYMENT_POLICY_NOT_APPLICABLE"


def test_t04_11_borrador_no_consume(mundo, gobierno, ocupacion):
    _cuentas_t04(mundo)
    s = _preparar(mundo, ocupacion)
    orden = _orden_emitida(mundo, s, ocupacion)
    medio = _medio(mundo)
    politica = _politica_pago(mundo, [medio["id"]], s["moneda"])
    cuenta = _cuenta(mundo, ocupacion, s["moneda"])
    r = _pago(mundo, orden, politica, cuenta, medio, "40.00")
    assert r.status_code == 201, r.text
    pago = r.json()

    pagado = _pagado(mundo, orden["id"])
    assert pagado["monto_pagado"] == "0.00"
    assert pagado["monto_en_tramite"] == "0.00"
    assert pagado["pendiente_de_pagar"] == "100.00"

    detalle = _get_op(mundo, f"{T}/pagos/{pago['id']}", "mk_t04")
    assert detalle.status_code == 200, detalle.text
    assert detalle.json()["orden"]["disponible_para_pago"] == "100.00"


def test_t04_12_enviar_pendiente_autorizacion(mundo, gobierno, ocupacion):
    _cuentas_t04(mundo)
    s = _preparar(mundo, ocupacion)
    orden = _orden_emitida(mundo, s, ocupacion)
    medio = _medio(mundo)
    politica = _politica_pago(mundo, [medio["id"]], s["moneda"])
    cuenta = _cuenta(mundo, ocupacion, s["moneda"])
    r = _pago(mundo, orden, politica, cuenta, medio, "40.00")
    assert r.status_code == 201, r.text
    pago = r.json()
    r2 = _enviar(mundo, pago)
    assert r2.status_code == 200, r2.text
    enviado = r2.json()
    assert enviado["estado"] == "PENDIENTE_AUTORIZACION"
    assert enviado["codigo"]
    assert enviado["regla"]["numero_version"] == 1
    assert enviado["aprobaciones_requeridas"] == 1

    pagado = _pagado(mundo, orden["id"])
    assert pagado["monto_en_tramite"] == "40.00"

    with mundo.factory() as db:
        evento = db.scalar(
            select(AuditEvent).where(
                AuditEvent.action == "GOV_PAYMENT_SUBMITTED",
                AuditEvent.entity_id == pago["id"],
            )
        )
        assert evento is not None


def test_t04_13_maker_no_se_autoaprueba(mundo, gobierno, ocupacion):
    _cuentas_t04(mundo)
    s = _preparar(mundo, ocupacion)
    cuenta_con_permisos(
        mundo,
        "mkck_t04",
        [
            ("gobierno_pagos", "view"),
            ("gobierno_pagos", "manage"),
            ("gobierno_pagos", "authorize"),
        ],
    )
    orden = _orden_emitida(mundo, s, ocupacion)
    medio = _medio(mundo)
    politica = _politica_pago(mundo, [medio["id"]], s["moneda"])
    cuenta = _cuenta(mundo, ocupacion, s["moneda"])
    r = _pago(
        mundo, orden, politica, cuenta, medio, "40.00", usuario="mkck_t04"
    )
    assert r.status_code == 201, r.text
    pago = r.json()
    r2 = _enviar(mundo, pago, usuario="mkck_t04")
    assert r2.status_code == 200, r2.text
    enviado = r2.json()
    cargo_pagar = _cargo(mundo, ocupacion)
    r3 = _aprobar(
        mundo, enviado, cargo_pagar, usuario="mkck_t04"
    )
    assert r3.status_code == 409, r3.text
    assert r3.json()["code"] == "GOV_PAYMENT_MAKER_CHECKER"
    detalle = _get_op(mundo, f"{T}/pagos/{pago['id']}", "mkck_t04")
    assert detalle.status_code == 200, detalle.text
    assert detalle.json()["estado"] == "PENDIENTE_AUTORIZACION"


def test_t04_14_autoridad_checker(mundo, gobierno, ocupacion):
    _cuentas_t04(mundo)
    s = _preparar(mundo, ocupacion)
    orden = _orden_emitida(mundo, s, ocupacion)
    medio = _medio(mundo)
    politica = _politica_pago(mundo, [medio["id"]], s["moneda"])
    cuenta = _cuenta(mundo, ocupacion, s["moneda"])
    r = _pago(mundo, orden, politica, cuenta, medio, "40.00")
    assert r.status_code == 201, r.text
    pago = r.json()
    r2 = _enviar(mundo, pago)
    assert r2.status_code == 200, r2.text
    enviado = r2.json()

    cargo_sin_competencia = _cargo(mundo, ocupacion, accion="REGISTRAR")
    r3 = _aprobar(mundo, enviado, cargo_sin_competencia)
    assert r3.status_code == 422, r3.text
    assert r3.json()["code"] == "GOV_PAYMENT_AUTHORITY_INVALID"

    cargo_pagar = _cargo(mundo, ocupacion)
    r4 = _aprobar(mundo, enviado, cargo_pagar)
    assert r4.status_code == 200, r4.text
    assert r4.json()["estado"] == "AUTORIZADO"


def test_t04_15_un_checker(mundo, gobierno, ocupacion):
    _cuentas_t04(mundo)
    s = _preparar(mundo, ocupacion)
    orden = _orden_emitida(mundo, s, ocupacion)
    medio = _medio(mundo)
    politica = _politica_pago(mundo, [medio["id"]], s["moneda"])
    cuenta = _cuenta(mundo, ocupacion, s["moneda"])
    r = _pago(mundo, orden, politica, cuenta, medio, "40.00")
    assert r.status_code == 201, r.text
    pago = r.json()
    r2 = _enviar(mundo, pago)
    assert r2.status_code == 200, r2.text
    enviado = r2.json()
    cargo_pagar = _cargo(mundo, ocupacion)
    r3 = _aprobar(mundo, enviado, cargo_pagar, usuario="ck_t04")
    assert r3.status_code == 200, r3.text
    aprobado = r3.json()
    assert aprobado["estado"] == "AUTORIZADO"

    r4 = _aprobar(mundo, aprobado, cargo_pagar, usuario="ck2_t04")
    assert r4.status_code == 409, r4.text
    assert r4.json()["code"] == "GOV_PAYMENT_NOT_PENDING"


def test_t04_16_multi_checker(mundo, gobierno, ocupacion):
    _cuentas_t04(mundo)
    s = _preparar(mundo, ocupacion)
    orden = _orden_emitida(mundo, s, ocupacion)
    medio = _medio(mundo)
    politica = _politica_pago(
        mundo,
        [medio["id"]],
        s["moneda"],
        bandas=[
            {
                "monto_desde": "0",
                "monto_hasta": None,
                "requisitos": [
                    {"accion": "PAGAR", "materia": "TESORERIA", "cantidad": 2}
                ],
            }
        ],
    )
    cuenta = _cuenta(mundo, ocupacion, s["moneda"])
    r = _pago(mundo, orden, politica, cuenta, medio, "40.00")
    assert r.status_code == 201, r.text
    pago = r.json()
    r2 = _enviar(mundo, pago)
    assert r2.status_code == 200, r2.text
    enviado = r2.json()
    assert enviado["aprobaciones_requeridas"] == 2

    cargo_a = _cargo(mundo, ocupacion)
    r3 = _aprobar(mundo, enviado, cargo_a, indice=0, usuario="ck_t04")
    assert r3.status_code == 200, r3.text
    tras_primera = r3.json()
    assert tras_primera["estado"] == "PENDIENTE_AUTORIZACION"
    assert tras_primera["aprobaciones_requeridas"] == 2

    r4 = _aprobar(mundo, tras_primera, cargo_a, indice=0, usuario="ck2_t04")
    assert r4.status_code == 409, r4.text
    assert r4.json()["code"] == "GOV_PAYMENT_CARGO_ALREADY_USED"

    cargo_b = _cargo(mundo, ocupacion)
    r5 = _aprobar(mundo, tras_primera, cargo_b, indice=0, usuario="ck2_t04")
    assert r5.status_code == 200, r5.text
    aprobado = r5.json()
    assert aprobado["estado"] == "AUTORIZADO"
    assert aprobado["aprobaciones_requeridas"] == 2


def test_t04_17_umbral_por_monto(mundo, gobierno, ocupacion):
    _cuentas_t04(mundo)
    s = _preparar(mundo, ocupacion)
    orden = _orden_emitida(mundo, s, ocupacion, monto="300.00")
    medio = _medio(mundo)
    politica = _politica_pago(
        mundo,
        [medio["id"]],
        s["moneda"],
        bandas=[
            {
                "monto_desde": "0",
                "monto_hasta": "100",
                "requisitos": [
                    {"accion": "PAGAR", "materia": "TESORERIA", "cantidad": 1}
                ],
            },
            {
                "monto_desde": "100",
                "monto_hasta": None,
                "requisitos": [
                    {"accion": "PAGAR", "materia": "TESORERIA", "cantidad": 1},
                    {"accion": "FIRMAR", "materia": "TESORERIA", "cantidad": 1},
                ],
            },
        ],
    )
    cuenta = _cuenta(mundo, ocupacion, s["moneda"])

    r = _pago(mundo, orden, politica, cuenta, medio, "50.00")
    assert r.status_code == 201, r.text
    pago50 = r.json()
    r2 = _enviar(mundo, pago50)
    assert r2.status_code == 200, r2.text
    enviado50 = r2.json()
    assert enviado50["aprobaciones_requeridas"] == 1
    assert enviado50["regla"]["banda"]["orden"] == 1

    r3 = _pago(mundo, orden, politica, cuenta, medio, "150.00")
    assert r3.status_code == 201, r3.text
    pago150 = r3.json()
    r4 = _enviar(mundo, pago150)
    assert r4.status_code == 200, r4.text
    enviado150 = r4.json()
    assert enviado150["aprobaciones_requeridas"] == 2
    assert enviado150["regla"]["banda"]["orden"] == 2

    cargo_pagar = _cargo(mundo, ocupacion)
    cargo_firmar = _cargo(mundo, ocupacion, accion="FIRMAR")
    r5 = _aprobar(mundo, enviado150, cargo_pagar, indice=1, usuario="ck_t04")
    assert r5.status_code == 422, r5.text
    assert r5.json()["code"] == "GOV_PAYMENT_AUTHORITY_INVALID"

    r6 = _aprobar(mundo, enviado150, cargo_pagar, indice=0, usuario="ck_t04")
    assert r6.status_code == 200, r6.text
    tras_primera = r6.json()
    r7 = _aprobar(mundo, tras_primera, cargo_firmar, indice=1, usuario="ck2_t04")
    assert r7.status_code == 200, r7.text
    assert r7.json()["estado"] == "AUTORIZADO"


def test_t04_18_pago_parcial(mundo, gobierno, ocupacion):
    _cuentas_t04(mundo)
    s = _preparar(mundo, ocupacion)
    orden = _orden_emitida(mundo, s, ocupacion)
    medio = _medio(mundo)
    politica = _politica_pago(
        mundo, [medio["id"]], s["moneda"], permite_pago_parcial=False
    )
    cuenta = _cuenta(mundo, ocupacion, s["moneda"])

    r = _pago(mundo, orden, politica, cuenta, medio, "40.00")
    assert r.status_code == 201, r.text
    pago_parcial = r.json()
    r2 = _enviar(mundo, pago_parcial)
    assert r2.status_code == 422, r2.text
    assert r2.json()["code"] == "GOV_PAYMENT_PARTIAL_NOT_ALLOWED"

    r3 = _pago(mundo, orden, politica, cuenta, medio, "100.00")
    assert r3.status_code == 201, r3.text
    pago_completo = r3.json()
    r4 = _enviar(mundo, pago_completo)
    assert r4.status_code == 200, r4.text
    assert r4.json()["estado"] == "PENDIENTE_AUTORIZACION"


def test_t04_19_multiples_pagos(mundo, gobierno, ocupacion):
    _cuentas_t04(mundo)
    s = _preparar(mundo, ocupacion)
    orden = _orden_emitida(mundo, s, ocupacion)
    medio = _medio(mundo)
    politica = _politica_pago(
        mundo, [medio["id"]], s["moneda"], control_duplicado="ADVERTIR"
    )
    cuenta = _cuenta(mundo, ocupacion, s["moneda"])
    cargo_pagar = _cargo(mundo, ocupacion)

    r1 = _pago(mundo, orden, politica, cuenta, medio, "40.00")
    assert r1.status_code == 201, r1.text
    pago1 = r1.json()
    r2 = _enviar(mundo, pago1)
    assert r2.status_code == 200, r2.text
    r3 = _aprobar(mundo, r2.json(), cargo_pagar, usuario="ck_t04")
    assert r3.status_code == 200, r3.text
    r4 = _registrar(mundo, r3.json(), "REF-T04-1")
    assert r4.status_code == 200, r4.text

    r5 = _pago(mundo, orden, politica, cuenta, medio, "30.00")
    assert r5.status_code == 201, r5.text
    pago2 = r5.json()
    r6 = _enviar(mundo, pago2)
    assert r6.status_code == 200, r6.text
    r7 = _aprobar(mundo, r6.json(), cargo_pagar, usuario="ck_t04")
    assert r7.status_code == 200, r7.text
    r8 = _registrar(mundo, r7.json(), "REF-T04-2")
    assert r8.status_code == 200, r8.text

    r9 = _pago(mundo, orden, politica, cuenta, medio, "30.00")
    assert r9.status_code == 201, r9.text
    pago3 = r9.json()
    r10 = _enviar(mundo, pago3)
    assert r10.status_code == 409, r10.text
    assert r10.json()["code"] == "GOV_PAYMENT_DUPLICATE_CONFIRMATION_REQUIRED"

    r11 = _enviar(
        mundo,
        pago3,
        confirmar_duplicado=True,
        motivo_duplicado="Segundo pago de la cuota acordada",
    )
    assert r11.status_code == 200, r11.text
    r12 = _aprobar(mundo, r11.json(), cargo_pagar, usuario="ck_t04")
    assert r12.status_code == 200, r12.text
    r13 = _registrar(mundo, r12.json(), "REF-T04-3")
    assert r13.status_code == 200, r13.text

    pagado = _pagado(mundo, orden["id"])
    assert pagado["monto_pagado"] == "100.00"
    assert pagado["pendiente_de_pagar"] == "0.00"


def test_t04_20_sobrepago(mundo, gobierno, ocupacion):
    _cuentas_t04(mundo)
    s = _preparar(mundo, ocupacion)
    orden = _orden_emitida(mundo, s, ocupacion)
    medio = _medio(mundo)
    politica = _politica_pago(mundo, [medio["id"]], s["moneda"])
    cuenta = _cuenta(mundo, ocupacion, s["moneda"])
    cargo_pagar = _cargo(mundo, ocupacion)

    r = _pago(mundo, orden, politica, cuenta, medio, "70.00")
    assert r.status_code == 201, r.text
    pago70 = r.json()
    r2 = _enviar(mundo, pago70)
    assert r2.status_code == 200, r2.text
    r3 = _aprobar(mundo, r2.json(), cargo_pagar, usuario="ck_t04")
    assert r3.status_code == 200, r3.text
    r4 = _registrar(mundo, r3.json(), "REF-T04-70")
    assert r4.status_code == 200, r4.text

    r5 = _pago(mundo, orden, politica, cuenta, medio, "31.00")
    assert r5.status_code == 201, r5.text
    r6 = _enviar(mundo, r5.json())
    assert r6.status_code == 409, r6.text
    assert r6.json()["code"] == "GOV_PAYMENT_OVERPAYMENT"

    r7 = _pago(mundo, orden, politica, cuenta, medio, "30.00")
    assert r7.status_code == 201, r7.text
    r8 = _enviar(mundo, r7.json())
    assert r8.status_code == 200, r8.text
    assert r8.json()["estado"] == "PENDIENTE_AUTORIZACION"


@pytest.mark.parametrize("solo_pg", [True])
def test_t04_21_concurrencia_real(mundo, gobierno, ocupacion, solo_pg):
    if not ONLY_PG:
        pytest.skip("Solo PostgreSQL")
    _cuentas_t04(mundo)
    s = _preparar(mundo, ocupacion)
    orden = _orden_emitida(mundo, s, ocupacion)
    medio = _medio(mundo)
    politica = _politica_pago(mundo, [medio["id"]], s["moneda"])
    cuenta = _cuenta(mundo, ocupacion, s["moneda"])

    r1 = _pago(mundo, orden, politica, cuenta, medio, "70.00")
    assert r1.status_code == 201, r1.text
    pago_a = r1.json()
    politica_b = _politica_pago(mundo, [medio["id"]], s["moneda"])
    r2 = _pago(mundo, orden, politica_b, cuenta, medio, "70.00")
    assert r2.status_code == 201, r2.text
    pago_b = r2.json()

    barrier = threading.Barrier(2)
    resultados: list[int] = []
    codigos: list[str] = []

    cabeceras = mundo.como("mk_t04", mundo.company_a)

    def enviar_en_hilo(pago):
        barrier.wait()
        resp = mundo.client.post(
            f"/api/v1{T}/pagos/{pago['id']}/enviar",
            headers={**cabeceras, "If-Match": str(pago["version"])},
            json={},
        )
        resultados.append(resp.status_code)
        if resp.status_code == 409:
            codigos.append(resp.json().get("code"))

    h1 = threading.Thread(target=enviar_en_hilo, args=(pago_a,))
    h2 = threading.Thread(target=enviar_en_hilo, args=(pago_b,))
    h1.start()
    h2.start()
    h1.join()
    h2.join()

    assert sorted(resultados) == [200, 409]
    assert codigos == ["GOV_PAYMENT_OVERPAYMENT"]
    pagado = _pagado(mundo, orden["id"])
    assert pagado["monto_en_tramite"] == "70.00"


def test_t04_22_referencia_duplicada(mundo, gobierno, ocupacion):
    _cuentas_t04(mundo)
    s = _preparar(mundo, ocupacion)
    orden_a = _orden_emitida(mundo, s, ocupacion)
    orden_b = _orden_emitida(mundo, s, ocupacion)
    medio_unico = _medio(mundo, exige_referencia=True, referencia_unica=True)
    politica = _politica_pago(mundo, [medio_unico["id"]], s["moneda"])
    cuenta = _cuenta(mundo, ocupacion, s["moneda"])
    cargo_pagar = _cargo(mundo, ocupacion)

    r = _pago(mundo, orden_a, politica, cuenta, medio_unico, "40.00")
    assert r.status_code == 201, r.text
    pago_a = r.json()
    r2 = _enviar(mundo, pago_a)
    assert r2.status_code == 200, r2.text
    r3 = _aprobar(mundo, r2.json(), cargo_pagar, usuario="ck_t04")
    assert r3.status_code == 200, r3.text
    r4 = _registrar(mundo, r3.json(), "REF-T04-1")
    assert r4.status_code == 200, r4.text

    r5 = _pago(mundo, orden_b, politica, cuenta, medio_unico, "40.00")
    assert r5.status_code == 201, r5.text
    pago_b = r5.json()
    r6 = _enviar(mundo, pago_b)
    assert r6.status_code == 200, r6.text
    r7 = _aprobar(mundo, r6.json(), cargo_pagar, usuario="ck_t04")
    assert r7.status_code == 200, r7.text
    r8 = _registrar(mundo, r7.json(), "ref-t04-1")
    assert r8.status_code == 409, r8.text
    assert r8.json()["code"] == "GOV_PAYMENT_DUPLICATE_REFERENCE"

    medio_no_unico = _medio(
        mundo, exige_referencia=True, referencia_unica=False
    )
    politica2 = _politica_pago(mundo, [medio_no_unico["id"]], s["moneda"])
    r9 = _pago(mundo, orden_b, politica2, cuenta, medio_no_unico, "30.00")
    assert r9.status_code == 201, r9.text
    pago_c = r9.json()
    r10 = _enviar(mundo, pago_c)
    assert r10.status_code == 200, r10.text
    r11 = _aprobar(mundo, r10.json(), cargo_pagar, usuario="ck_t04")
    assert r11.status_code == 200, r11.text
    r12 = _registrar(mundo, r11.json(), "ref-t04-1")
    assert r12.status_code == 200, r12.text


def test_t04_23_documentos(mundo, gobierno, ocupacion):
    _cuentas_t04(mundo)
    s = _preparar(mundo, ocupacion)
    orden = _orden_emitida(mundo, s, ocupacion)
    medio = _medio(mundo)
    tipo_soporte = _bud09._TIPO_SOPORTE["tipo"]
    politica = _politica_pago(
        mundo,
        [medio["id"]],
        s["moneda"],
        documentos=[
            {
                "etapa": "PREPARAR",
                "document_type_id": tipo_soporte,
                "obligatorio": True,
            }
        ],
    )
    cuenta = _cuenta(mundo, ocupacion, s["moneda"])

    r = _pago(mundo, orden, politica, cuenta, medio, "40.00")
    assert r.status_code == 201, r.text
    pago = r.json()
    r2 = _put_op(
        mundo,
        f"{T}/pagos/{pago['id']}",
        "mk_t04",
        {"documentos": []},
        pago["version"],
    )
    assert r2.status_code == 200, r2.text
    pago_sin_docs = r2.json()
    r3 = _enviar(mundo, pago_sin_docs)
    assert r3.status_code == 422, r3.text
    assert r3.json()["code"] == "GOV_PAYMENT_DOCUMENT_MISSING"

    doc_id = s["soporte"]
    r4 = _put_op(
        mundo,
        f"{T}/pagos/{pago['id']}",
        "mk_t04",
        {"documentos": [doc_id]},
        pago_sin_docs["version"],
    )
    assert r4.status_code == 200, r4.text
    pago_con_doc = r4.json()
    r5 = _enviar(mundo, pago_con_doc)
    assert r5.status_code == 200, r5.text
    detalle = _get_op(mundo, f"{T}/pagos/{pago['id']}", "mk_t04")
    assert detalle.status_code == 200, detalle.text
    assert any(
        d["etapa"] == "PREPARAR"
        for d in detalle.json()["documentos"]
    )


def test_t04_24_mfa(mundo, gobierno, ocupacion):
    _cuentas_t04(mundo)
    _preparar(mundo, ocupacion)
    assert classify({"gobierno_pagos:authorize"}) == SENSITIVE
    assert classify({"gobierno_pagos:execute"}) == SENSITIVE
    assert classify({"gobierno_pagos:cancel"}) == SENSITIVE
    assert classify({"gobierno_pagos:policy"}) == SENSITIVE
    assert classify({"gobierno_pagos:view"}) != SENSITIVE
    assert classify({"gobierno_pagos:manage"}) != SENSITIVE


def test_t04_25_registrar(mundo, gobierno, ocupacion):
    _cuentas_t04(mundo)
    s = _preparar(mundo, ocupacion)
    orden = _orden_emitida(mundo, s, ocupacion)
    medio = _medio(mundo, exige_referencia=True)
    politica = _politica_pago(mundo, [medio["id"]], s["moneda"])
    cuenta = _cuenta(mundo, ocupacion, s["moneda"])
    cargo_pagar = _cargo(mundo, ocupacion)

    r = _pago(mundo, orden, politica, cuenta, medio, "40.00")
    assert r.status_code == 201, r.text
    pago = r.json()

    r2 = _enviar(mundo, pago)
    assert r2.status_code == 200, r2.text
    r3 = _aprobar(mundo, r2.json(), cargo_pagar, usuario="ck_t04")
    assert r3.status_code == 200, r3.text
    autorizado = r3.json()

    r4 = _registrar(mundo, autorizado, None)
    assert r4.status_code == 422, r4.text
    assert r4.json()["code"] == "GOV_PAYMENT_REFERENCE_REQUIRED"

    manana = (datetime.now(UTC).date() + timedelta(days=1)).isoformat()
    r5 = _registrar(mundo, autorizado, "REF-T04-25", fecha_valor=manana)
    assert r5.status_code == 422, r5.text
    assert r5.json()["code"] == "GOV_PAYMENT_VALUE_DATE_INVALID"

    r6 = _registrar(
        mundo,
        autorizado,
        "REF-T04-25",
        fecha_valor=hoy_de_negocio().isoformat(),
    )
    assert r6.status_code == 200, r6.text
    registrado = r6.json()
    assert registrado["estado"] == "REGISTRADO"
    pagado = _pagado(mundo, orden["id"])
    assert pagado["monto_pagado"] == "40.00"

    r7 = _pago(mundo, orden, politica, cuenta, medio, "30.00")
    assert r7.status_code == 201, r7.text
    pendiente = r7.json()
    r8 = _enviar(mundo, pendiente)
    assert r8.status_code == 200, r8.text
    r9 = _registrar(mundo, r8.json(), "REF-SIN-AUTORIZAR")
    assert r9.status_code == 409, r9.text
    assert r9.json()["code"] == "GOV_PAYMENT_NOT_AUTHORIZED"


def test_t04_26_historia(mundo, gobierno, ocupacion):
    _cuentas_t04(mundo)
    s = _preparar(mundo, ocupacion)
    orden = _orden_emitida(mundo, s, ocupacion)
    medio = _medio(mundo)
    politica = _politica_pago(mundo, [medio["id"]], s["moneda"])
    cuenta = _cuenta(mundo, ocupacion, s["moneda"])
    cargo_pagar = _cargo(mundo, ocupacion)

    r = _pago(mundo, orden, politica, cuenta, medio, "40.00")
    assert r.status_code == 201, r.text
    pago = r.json()
    r2 = _enviar(mundo, pago)
    assert r2.status_code == 200, r2.text
    r3 = _aprobar(mundo, r2.json(), cargo_pagar, usuario="ck_t04")
    assert r3.status_code == 200, r3.text
    r4 = _registrar(mundo, r3.json(), "REF-T04-26")
    assert r4.status_code == 200, r4.text

    detalle = _get_op(mundo, f"{T}/pagos/{pago['id']}", "mk_t04")
    assert detalle.status_code == 200, detalle.text
    eventos = [h["evento"] for h in detalle.json()["historia"]]
    assert eventos == ["CREADO", "ENVIADO", "AUTORIZADO", "REGISTRADO"]


def test_t04_27_auditoria(mundo, gobierno, ocupacion):
    _cuentas_t04(mundo)
    s = _preparar(mundo, ocupacion)
    orden = _orden_emitida(mundo, s, ocupacion)
    medio = _medio(mundo)
    politica = _politica_pago(mundo, [medio["id"]], s["moneda"])
    cuenta = _cuenta(mundo, ocupacion, s["moneda"])
    cargo_pagar = _cargo(mundo, ocupacion)

    r = _pago(mundo, orden, politica, cuenta, medio, "40.00")
    assert r.status_code == 201, r.text
    pago = r.json()
    r2 = _enviar(mundo, pago)
    assert r2.status_code == 200, r2.text
    r3 = _aprobar(mundo, r2.json(), cargo_pagar, usuario="ck_t04")
    assert r3.status_code == 200, r3.text
    r4 = _registrar(mundo, r3.json(), "REF-T04-27")
    assert r4.status_code == 200, r4.text

    with mundo.factory() as db:
        acciones = set(
            db.scalars(
                select(AuditEvent.action).where(
                    AuditEvent.entity_id == pago["id"]
                )
            ).all()
        )
        assert "GOV_PAYMENT_CREATED" in acciones
        assert "GOV_PAYMENT_SUBMITTED" in acciones
        assert "GOV_PAYMENT_APPROVED" in acciones
        assert "GOV_PAYMENT_EXECUTED" in acciones


def test_t04_28_version_congelada(mundo, gobierno, ocupacion):
    _cuentas_t04(mundo)
    s = _preparar(mundo, ocupacion)
    orden = _orden_emitida(mundo, s, ocupacion)
    medio = _medio(mundo)
    politica_v1 = _politica_pago(mundo, [medio["id"]], s["moneda"])
    cuenta = _cuenta(mundo, ocupacion, s["moneda"])
    cargo_pagar = _cargo(mundo, ocupacion)

    r = _pago(mundo, orden, politica_v1, cuenta, medio, "40.00")
    assert r.status_code == 201, r.text
    pago_a = r.json()
    r2 = _enviar(mundo, pago_a)
    assert r2.status_code == 200, r2.text
    enviado_a = r2.json()
    assert enviado_a["regla"]["numero_version"] == 1

    r3 = _post_op(
        mundo,
        f"{T}/politicas-pago/{politica_v1['id']}/nueva-version",
        "mk_t04",
        {},
    )
    assert r3.status_code == 201, r3.text
    v2 = r3.json()
    hoy = hoy_de_negocio()
    if hoy == D(1, 1):
        pytest.skip("La fecha de negocio coincide con el inicio del ejercicio")
    r4 = _put_op(
        mundo,
        f"{T}/politicas-pago/{v2['id']}",
        "mk_t04",
        {"vigente_desde": hoy.isoformat()},
        v2["version"],
    )
    assert r4.status_code == 200, r4.text
    v2_actualizada = r4.json()
    r5 = _post_op(
        mundo,
        f"{T}/politicas-pago/{v2_actualizada['id']}/activar",
        "mk_t04",
        {"fundamento": "Fundamento de activación v2 TRE-04"},
        version=v2_actualizada["version"],
    )
    assert r5.status_code == 200, r5.text

    r6 = _aprobar(mundo, enviado_a, cargo_pagar, usuario="ck_t04")
    assert r6.status_code == 200, r6.text
    r7 = _registrar(mundo, r6.json(), "REF-T04-28-A")
    assert r7.status_code == 200, r7.text

    r8 = _pago(mundo, orden, r5.json(), cuenta, medio, "30.00")
    assert r8.status_code == 201, r8.text
    pago_b = r8.json()
    r9 = _enviar(mundo, pago_b)
    assert r9.status_code == 200, r9.text
    assert r9.json()["regla"]["numero_version"] == 2


def test_t04_29_frontera_tre03(mundo, gobierno, ocupacion):
    _cuentas_t04(mundo)
    s = _preparar(mundo, ocupacion)
    orden = _orden_emitida(mundo, s, ocupacion)
    medio = _medio(mundo)
    politica = _politica_pago(mundo, [medio["id"]], s["moneda"])
    cuenta = _cuenta(mundo, ocupacion, s["moneda"])

    r = _pago(mundo, orden, politica, cuenta, medio, "40.00")
    assert r.status_code == 201, r.text
    pago = r.json()
    r2 = _enviar(mundo, pago)
    assert r2.status_code == 200, r2.text

    cargo_tre03 = _cargo_ordenar(mundo, ocupacion)
    r3 = _anular(mundo, orden, cargo_tre03, usuario="ord_t03")
    assert r3.status_code == 409, r3.text
    assert r3.json()["code"] == "GOV_PAYMENT_ORDER_HAS_PAYMENTS"

    orden_borrador = _borrador(
        mundo,
        s,
        _politica_op(mundo),
        [{"cause_id": _causado_formalizado(mundo, s, monto="100.00")["id"], "monto": "100.00"}],
        _cargo_ordenar(mundo, ocupacion),
    )
    assert orden_borrador.status_code == 201, orden_borrador.text
    borrador = orden_borrador.json()
    r4 = _pago(mundo, borrador, politica, cuenta, medio, "40.00")
    assert r4.status_code == 422, r4.text
    assert r4.json()["code"] == "GOV_PAYMENT_ORDER_NOT_PAYABLE"


def test_t04_30_frontera_tre07(mundo, gobierno, ocupacion):
    _cuentas_t04(mundo)
    s = _preparar(mundo, ocupacion)
    orden = _orden_emitida(mundo, s, ocupacion)
    medio = _medio(mundo)
    politica = _politica_pago(mundo, [medio["id"]], s["moneda"])
    cuenta = _cuenta(mundo, ocupacion, s["moneda"])
    cargo_pagar = _cargo(mundo, ocupacion)

    r = _pago(mundo, orden, politica, cuenta, medio, "40.00")
    assert r.status_code == 201, r.text
    pago = r.json()
    r2 = _enviar(mundo, pago)
    assert r2.status_code == 200, r2.text
    r3 = _aprobar(mundo, r2.json(), cargo_pagar, usuario="ck_t04")
    assert r3.status_code == 200, r3.text
    r4 = _registrar(mundo, r3.json(), "REF-T04-30")
    assert r4.status_code == 200, r4.text
    registrado = r4.json()

    r5 = _anular_pago(mundo, registrado)
    assert r5.status_code == 409, r5.text
    assert r5.json()["code"] == "GOV_PAYMENT_NOT_CANCELLABLE"

    r6 = _pago(mundo, orden, politica, cuenta, medio, "30.00")
    assert r6.status_code == 201, r6.text
    r7 = _enviar(mundo, r6.json())
    assert r7.status_code == 200, r7.text
    pendiente = r7.json()
    r8 = _anular_pago(mundo, pendiente, usuario="mk_t04")
    assert r8.status_code == 200, r8.text
    anulado = r8.json()
    assert anulado["estado"] == "ANULADO"
    pagado = _pagado(mundo, orden["id"])
    assert pagado["monto_en_tramite"] == "0.00"


@ONLY_PG
def test_t04_30b_pago_no_se_borra(mundo, gobierno, ocupacion):
    _cuentas_t04(mundo)
    s = _preparar(mundo, ocupacion)
    orden = _orden_emitida(mundo, s, ocupacion)
    medio = _medio(mundo)
    politica = _politica_pago(mundo, [medio["id"]], s["moneda"])
    cuenta = _cuenta(mundo, ocupacion, s["moneda"])

    r = _pago(mundo, orden, politica, cuenta, medio, "40.00")
    assert r.status_code == 201, r.text
    pago = r.json()

    with mundo.factory() as db:
        with pytest.raises(DBAPIError):
            db.execute(
                text("DELETE FROM gov_payments WHERE id = :id"),
                {"id": pago["id"]},
            )
            db.commit()


def test_t04_31_idempotencia(mundo, gobierno, ocupacion):
    _cuentas_t04(mundo)
    s = _preparar(mundo, ocupacion)
    orden = _orden_emitida(mundo, s, ocupacion)
    medio = _medio(mundo)
    politica = _politica_pago(mundo, [medio["id"]], s["moneda"])
    cuenta = _cuenta(mundo, ocupacion, s["moneda"])
    clave = "IDEM-" + uuid4().hex

    r1 = _pago(
        mundo,
        orden,
        politica,
        cuenta,
        medio,
        "40.00",
        idempotency_key=clave,
    )
    assert r1.status_code == 201, r1.text
    pago1 = r1.json()

    r2 = _pago(
        mundo,
        orden,
        politica,
        cuenta,
        medio,
        "40.00",
        idempotency_key=clave,
    )
    assert r2.status_code in (200, 201), r2.text
    pago2 = r2.json()
    assert pago2["id"] == pago1["id"]

    with mundo.factory() as db:
        total = db.scalar(
            select(text("count(*)")).select_from(text("gov_payments"))
            .where(text("idempotency_key = :clave"))
            .params(clave=clave)
        )
        assert total == 1
