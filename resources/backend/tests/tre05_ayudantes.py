"""Ayudantes compartidos para las pruebas TRE-05 · Retención de Tesorería."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select

from app.modules.government.models import GovernmentOfficialExchangeRate
from app.modules.identity_access.models import User
from app.shared.clock import hoy_de_negocio
from tests import test_gov_bud08 as _bud08
from tests import test_gov_bud09_causado as _bud09
from tests.org04_ayudantes import D
from tests.org06_guarda import cuenta_con_permisos
from tests.test_gov_bud09_causado import _preparar
from tests.test_gov_tre03_orden_pago import _CUENTAS_T03, _get_op, _post_op
from tests.test_gov_tre04_pago import (
    _CUENTAS_T04,
    _aprobar,
    _cargo,
    _cuenta,
    _cuentas_t04,
    _enviar,
    _medio,
    _orden_emitida,
    _pago,
    _politica_pago,
    _registrar,
)

R = "/gobierno/tesoreria/retenciones"
_CUENTAS_T05: dict[int, None] = {}


def aislar_caches() -> None:
    """Limpia los caches compartidos de los módulos de presupuesto y tesorería."""
    _bud08._ESTADO.clear()
    _bud09._CUENTAS.clear()
    _bud09._TIPO_SOPORTE.clear()
    _CUENTAS_T03.clear()
    _CUENTAS_T04.clear()
    _CUENTAS_T05.clear()


def cuentas_t05(mundo) -> None:
    if id(mundo) in _CUENTAS_T05:
        return
    _cuentas_t04(mundo)
    cuenta_con_permisos(
        mundo,
        "rt_mk",
        [
            ("gobierno_retenciones", "view"),
            ("gobierno_retenciones", "manage"),
            ("gobierno_retenciones", "calculate"),
            ("gobierno_retenciones", "policy"),
            ("gobierno_pagos", "view"),
        ],
    )
    cuenta_con_permisos(
        mundo,
        "rt_ck",
        [
            ("gobierno_retenciones", "view"),
            ("gobierno_retenciones", "approve"),
            ("gobierno_retenciones", "cancel"),
            ("gobierno_pagos", "view"),
        ],
    )
    cuenta_con_permisos(mundo, "rt_ver", [("gobierno_retenciones", "view")])
    _CUENTAS_T05[id(mundo)] = None


def concepto(mundo, clase="TRIBUTARIA", serie=None) -> dict:
    codigo = "C" + uuid4().hex[:8].upper()
    cuerpo = {
        "tipo": "CONCEPTO",
        "codigo": codigo,
        "nombre": f"Concepto {codigo}",
        "clase": clase,
    }
    if serie is not None:
        cuerpo["serie_comprobante"] = serie
    r = _post_op(mundo, f"{R}/catalogo", "rt_mk", cuerpo)
    assert r.status_code == 201, r.text
    return r.json()


def condicion(mundo) -> dict:
    codigo = "K" + uuid4().hex[:8].upper()
    cuerpo = {
        "tipo": "CONDICION",
        "codigo": codigo,
        "nombre": f"Condición {codigo}",
    }
    r = _post_op(mundo, f"{R}/catalogo", "rt_mk", cuerpo)
    assert r.status_code == 201, r.text
    return r.json()


def regla(concepto: dict, orden=1, tasa="5", **kw) -> dict:
    base = {
        "orden": orden,
        "concept_id": concepto["id"],
        "base_tipo": "MONTO_BRUTO",
        "tasa": tasa,
        "umbral_tipo": "NINGUNO",
        "condiciones_exigidas": [],
        "exclusiones": [],
        "tipos_persona": None,
        "exige_comprobante": False,
    }
    base.update(kw)
    return base


def politica_ret(mundo, moneda: str, reglas: list[dict], activar=True, **cambios) -> dict:
    codigo = "P" + uuid4().hex[:8].upper()
    cuerpo = {
        "codigo": codigo,
        "nombre": f"Política {codigo}",
        "moneda": moneda,
        "fuente_descripcion": "Acto del ente de prueba",
        "fuente_referencia": "Art. 1",
        "aprobador_competencia_accion": "APROBAR",
        "aprobador_competencia_materia": "TESORERIA",
        "vigente_desde": D(1, 1).isoformat(),
        "reglas": reglas,
    }
    cuerpo.update(cambios)
    r = _post_op(mundo, f"{R}/politicas", "rt_mk", cuerpo)
    assert r.status_code == 201, r.text
    politica = r.json()
    if not activar:
        return politica
    r = _post_op(
        mundo,
        f"{R}/politicas/{politica['id']}/activar",
        "rt_mk",
        {"fundamento": "Fundamento de activación de más de veinte caracteres."},
        version=politica["version"],
    )
    assert r.status_code == 200, r.text
    return r.json()


def beneficiario(tipo="JURIDICA", condiciones=(), nombre="Proveedor de prueba S.A.") -> dict:
    return {
        "nombre": nombre,
        "identificacion_fiscal": "J-12345678-9" if tipo == "JURIDICA" else "V-12345678",
        "tipo_persona": tipo,
        "condiciones": list(condiciones),
    }


def pago_listo(mundo, ocupacion, monto="100.00", autorizado=False) -> dict:
    cuentas_t05(mundo)
    s = _preparar(mundo, ocupacion)
    orden = _orden_emitida(mundo, s, ocupacion, monto=monto)
    medio = _medio(mundo)
    politica_pago = _politica_pago(mundo, [medio["id"]], s["moneda"])
    cuenta = _cuenta(mundo, ocupacion, s["moneda"])
    r_pago = _pago(mundo, orden, politica_pago, cuenta, medio, monto)
    assert r_pago.status_code in (200, 201), r_pago.text
    pago = r_pago.json()
    if autorizado:
        r_enviar = _enviar(mundo, pago, usuario="mk_t04")
        assert r_enviar.status_code == 200, r_enviar.text
        pago = r_enviar.json()
        cargo = _cargo(mundo, ocupacion)
        r_aprobar = _aprobar(mundo, pago, cargo, usuario="ck_t04")
        assert r_aprobar.status_code == 200, r_aprobar.text
        pago = r_aprobar.json()
    return {
        "s": s,
        "orden": orden,
        "medio": medio,
        "politica_pago": politica_pago,
        "cuenta": cuenta,
        "pago": pago,
    }


def calcular(mundo, pago: dict, politica: dict, conceptos: list[str], benef: dict | None = None, usuario="rt_mk"):
    cuerpo = {
        "policy_id": politica["id"],
        "conceptos": conceptos,
        "beneficiario": benef or beneficiario(),
    }
    return _post_op(mundo, f"{R}/pagos/{pago['id']}/liquidacion", usuario, cuerpo)


def cargo_aprobador(mundo, ocupacion, accion="APROBAR", materia="TESORERIA") -> str:
    return _cargo(mundo, ocupacion, accion, materia)


def aprobar_liq(mundo, liq: dict, cargo: str, usuario="rt_ck"):
    return _post_op(
        mundo,
        f"{R}/liquidaciones/{liq['id']}/aprobar",
        usuario,
        {"cargo_id": cargo},
        version=liq["version"],
    )


def pago_actual(mundo, pago_id: str) -> dict:
    r = _get_op(mundo, f"/gobierno/tesoreria/pagos/{pago_id}", usuario="mk_t04")
    assert r.status_code == 200, r.text
    return r.json()


def registrar_pago(mundo, pago_id: str, referencia: str):
    pago = pago_actual(mundo, pago_id)
    return _registrar(mundo, pago, referencia)


def tasa_aprobada(mundo, s, moneda="USD", valor="40.00") -> str:
    with mundo.factory() as db:
        user = db.scalar(select(User).where(User.username == "ua"))
        tasa = GovernmentOfficialExchangeRate(
            company_id=mundo.company_a,
            moneda=moneda,
            moneda_cotizacion="VES",
            fecha_efectiva=hoy_de_negocio() - timedelta(days=1),
            fuente="BCV",
            fuente_referencia="BCV de prueba",
            version=1,
            valor=Decimal(valor),
            estado="APROBADA",
            capturada_por=user.id,
            capturada_en=datetime.now(UTC),
            created_by=user.id,
            aprobada_por="00000000-0000-0000-0000-0000000000a1",
            aprobada_en=datetime.now(UTC),
            evidencia_documento_id=s["soporte"],
            evidencia_sha256="0" * 64,
        )
        db.add(tasa)
        db.commit()
        db.refresh(tasa)
        return str(tasa.id)
