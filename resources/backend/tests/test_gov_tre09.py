"""TRE-09 · Pruebas PostgreSQL: tasas oficiales BCV, consumidor BUD-08, normalización VES/VED."""

from __future__ import annotations

import threading
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.core.company_context import CompanyContext
from app.modules.audit.models import AuditEvent
from app.modules.government.service_tasas import verificar_limite
from app.modules.identity_access.mfa_policy import SENSITIVE, classify
from app.modules.identity_access.models import User
from app.modules.organization.models import Company
from app.modules.setup.api import CATALOGO_DE_PERMISOS
from app.shared.clock import hoy_de_negocio
from tests.org04_ayudantes import ANIO, nuevo_cargo
from tests.org06_guarda import cuenta_con_permisos
from tests.test_gov_bud01_ejercicio import ONLY_PG, P, _aprobar, _completo, _documento
from tests.test_gov_bud08 import _cargo_comprometer, _cdp, _comprometer
from tests.test_gov_ctl06_hallazgos import _post
from tests.test_gov_doc08_paquete import _doc_real

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos", "tests.org04_ayudantes")

T = "/gobierno/tesoreria/tasas"
REF = "BCV · tipo de cambio oficial de referencia"

_ESTADO: dict[str, dict] = {}


def _preparar(mundo, ocupacion) -> dict:
    """Prepara el escenario base una sola vez; caché de módulo."""
    if "s" in _ESTADO:
        return _ESTADO["s"]

    # 1) Moneda funcional VED en company_a
    with mundo.factory() as db:
        db.execute(
            text("UPDATE companies SET functional_currency = 'VED' WHERE id = :c"),
            {"c": mundo.company_a},
        )
        db.commit()

    # 2) Cuentas con permisos
    cuenta_con_permisos(mundo, "capt_t09", [("gobierno_tasas", "view"), ("gobierno_tasas", "manage")])
    cuenta_con_permisos(mundo, "aprob_t09", [("gobierno_tasas", "view"), ("gobierno_tasas", "approve")])
    cuenta_con_permisos(mundo, "compr_t09", [("gobierno_presupuesto", "view"), ("gobierno_presupuesto", "commit")])
    cuenta_con_permisos(mundo, "solo_ver_t09", [("gobierno_tasas", "view")])

    # 3) Ejercicio completo con partidas adicionales
    detalle = _completo(mundo, ANIO)
    assert detalle["moneda_funcional"] == "VES"  # Vector G

    year_id = detalle["id"]
    version = detalle["version"]

    # Partidas EGRESO 402-405
    partidas_ids: dict[str, str] = {}
    for codigo in ["402", "403", "404", "405"]:
        respuesta = _post(
            mundo,
            f"{P}/{year_id}/clasificador/partidas",
            "ua",
            mundo.company_a,
            {
                "tipo": "EGRESO",
                "codigo": codigo,
                "denominacion": f"Partida {codigo}",
                "nivel": 1,
                "codigo_padre": None,
                "vigente_desde": None,
                "vigente_hasta": None,
            },
            version=version,
        )
        assert respuesta.status_code == 201, respuesta.text
        version = respuesta.json()["version"]

    # Fuente F01
    respuesta = _post(
        mundo,
        f"{P}/{year_id}/fuentes",
        "ua",
        mundo.company_a,
        {
            "codigo": "F01",
            "denominacion": "Ingresos propios",
            "procedencia": "Ordenanza municipal de ingresos",
        },
        version=version,
    )
    assert respuesta.status_code == 201, respuesta.text
    version = respuesta.json()["version"]

    # Ids de partidas y fuentes desde GET
    partidas_resp = mundo.get(f"{P}/{year_id}/clasificador/partidas", "ua", mundo.company_a)
    assert partidas_resp.status_code == 200
    for partida in partidas_resp.json()["items"]:
        partidas_ids[partida["codigo"]] = partida["id"]
    fuentes_resp = mundo.get(f"{P}/{year_id}/fuentes", "ua", mundo.company_a)
    assert fuentes_resp.status_code == 200
    fuente_id = next(f["id"] for f in fuentes_resp.json()["items"] if f["codigo"] == "F01")

    # Ingreso 301 por 8,000,000.00
    respuesta = _post(
        mundo,
        f"{P}/{year_id}/presupuesto-aprobado/ingresos",
        "ua",
        mundo.company_a,
        {"partida_id": partidas_ids["301"], "monto": "8000000.00"},
        version=version,
    )
    assert respuesta.status_code == 201, respuesta.text
    version = respuesta.json()["version"]

    detalle_get = mundo.get(f"{P}/{year_id}", "ua", mundo.company_a)
    assert detalle_get.status_code == 200
    categoria_01_02 = next(
        c["id"] for c in detalle_get.json()["categorias"] if c["codigo_completo"] == "01.02"
    )

    # Créditos 01.02 × {402,403,404,405} × F01 por 2,000,000.00
    creditos_ids: dict[str, str] = {}
    for codigo in ["402", "403", "404", "405"]:
        respuesta = _post(
            mundo,
            f"{P}/{year_id}/presupuesto-aprobado/creditos",
            "ua",
            mundo.company_a,
            {
                "categoria_id": categoria_01_02,
                "partida_id": partidas_ids[codigo],
                "fuente_id": fuente_id,
                "monto": "2000000.00",
            },
            version=version,
        )
        assert respuesta.status_code == 201, respuesta.text
        version = respuesta.json()["version"]
        for credito in respuesta.json()["creditos"]:
            if credito["partida"]["codigo"] == codigo:
                creditos_ids[codigo] = credito["id"]
                break

    # Aprobar ejercicio
    detalle = mundo.get(f"{P}/{year_id}", "ua", mundo.company_a).json()
    _aprobar(mundo, detalle)

    # 4) Ejercicio heredado VED
    with mundo.factory() as db:
        db.execute(
            text("UPDATE gov_budget_years SET moneda_funcional = 'VED' WHERE id = :y"),
            {"y": year_id},
        )
        db.commit()

    # 5) Estado base
    s = {
        "year_id": year_id,
        "creditos": creditos_ids,
        "firmante": nuevo_cargo(mundo, ocupacion),
        "sin_limite": _cargo_comprometer(mundo, ocupacion, "SIN_LIMITE", None, None),
        "lim_usd": _cargo_comprometer(mundo, ocupacion, "MONTO", "500.00", "USD"),
        "lim_ves": _cargo_comprometer(mundo, ocupacion, "MONTO", "450000.00", "VES"),
        "lim_eur": _cargo_comprometer(mundo, ocupacion, "MONTO", "500.00", "EUR"),
        "soporte": _documento(mundo, year_id),
    }
    _ESTADO["s"] = s
    return s


def _tasa(mundo, moneda: str, fecha: date, valor: str, usuario: str = "capt_t09") -> dict:
    """Crea una tasa BORRADOR y devuelve su json."""
    r = mundo.post(
        T,
        usuario,
        mundo.company_a,
        {
            "moneda": moneda,
            "fecha_efectiva": fecha.isoformat(),
            "valor": valor,
            "fuente_referencia": REF,
            "publicada_en": None,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def _evidencia(mundo, tasa_id: int) -> None:
    """Vincula un documento real a la tasa."""
    doc = _doc_real(mundo, mundo.company_a, None, f"bcv-{tasa_id}".encode(), "bcv")
    r = mundo.post(
        f"/documentos/{doc}/vinculos",
        "ua",
        mundo.company_a,
        {"resource_type": "GovernmentOfficialExchangeRate", "resource_id": tasa_id},
    )
    assert r.status_code == 200, r.text


def _aprobar_tasa(mundo, tasa_id: int, usuario: str = "aprob_t09"):
    """Aprueba una tasa."""
    return _post(mundo, f"{T}/{tasa_id}/aprobar", usuario, mundo.company_a, {})


def _vigente(mundo, moneda: str, fecha: date, valor: str) -> dict:
    """Crea evidencia y aprueba; devuelve el json aprobado."""
    t = _tasa(mundo, moneda, fecha, valor)
    _evidencia(mundo, t["id"])
    r = _aprobar_tasa(mundo, t["id"])
    assert r.status_code == 200, r.text
    return r.json()


@ONLY_PG
def test_ciclo_de_vida_maker_checker_y_validaciones(mundo, gobierno, ocupacion):
    _preparar(mundo, ocupacion)
    hoy = hoy_de_negocio()
    fecha = hoy - timedelta(days=30)

    # Crear USD
    t = _tasa(mundo, "USD", fecha, "905.12345678")
    assert t["estado"] == "BORRADOR"
    assert t["version"] == 1
    assert Decimal(t["valor"]) == Decimal("905.12345678")
    assert t["fuente"] == "BCV"
    assert t["moneda_cotizacion"] == "VES"

    # Repetir -> DRAFT_EXISTS
    r = mundo.post(
        T,
        "capt_t09",
        mundo.company_a,
        {
            "moneda": "USD",
            "fecha_efectiva": fecha.isoformat(),
            "valor": "906",
            "fuente_referencia": REF,
            "publicada_en": None,
        },
    )
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_OFFICIAL_RATE_DRAFT_EXISTS"

    # Aprobar sin evidencia -> EVIDENCE_REQUIRED
    r = _aprobar_tasa(mundo, t["id"])
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_OFFICIAL_RATE_EVIDENCE_REQUIRED"

    # Vincular evidencia
    _evidencia(mundo, t["id"])

    # Aprobar con capt_t09 -> 403
    r = _aprobar_tasa(mundo, t["id"], usuario="capt_t09")
    assert r.status_code == 403

    # EUR creada por "ua", evidencia, aprobar por él mismo -> MAKER_CHECKER
    t_eur = _tasa(mundo, "EUR", fecha, "1000", usuario="ua")
    _evidencia(mundo, t_eur["id"])
    r = _aprobar_tasa(mundo, t_eur["id"], usuario="ua")
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_OFFICIAL_RATE_MAKER_CHECKER"
    # La EUR queda BORRADOR
    r = mundo.get(f"{T}/{t_eur['id']}", "aprob_t09", mundo.company_a)
    assert r.status_code == 200
    assert r.json()["estado"] == "BORRADOR"

    # aprob_t09 aprueba la USD
    r = _aprobar_tasa(mundo, t["id"])
    assert r.status_code == 200
    aprobada = r.json()
    assert aprobada["estado"] == "APROBADA"
    assert aprobada["aprobada_por"] == "aprob_t09"
    assert len(aprobada["evidencia_sha256"]) == 64

    # Repetir aprobación -> NOT_DRAFT
    r = _aprobar_tasa(mundo, t["id"])
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_OFFICIAL_RATE_NOT_DRAFT"

    # Crear otra USD hoy-30 -> ALREADY_APPROVED
    r = mundo.post(
        T,
        "capt_t09",
        mundo.company_a,
        {
            "moneda": "USD",
            "fecha_efectiva": fecha.isoformat(),
            "valor": "907",
            "fuente_referencia": REF,
            "publicada_en": None,
        },
    )
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_OFFICIAL_RATE_ALREADY_APPROVED"

    # Corrección
    r = _post(
        mundo,
        f"{T}/{t['id']}/correccion",
        "capt_t09",
        mundo.company_a,
        {
            "valor": "906",
            "fuente_referencia": REF,
            "publicada_en": None,
            "motivo": "Corrección del valor publicado por el BCV",
        },
    )
    assert r.status_code == 201
    t2 = r.json()
    assert t2["estado"] == "BORRADOR"
    assert t2["version"] == 2
    assert t2["sustituye_id"] == t["id"]

    # Evidencia y aprobación de la corrección
    _evidencia(mundo, t2["id"])
    r = _aprobar_tasa(mundo, t2["id"])
    assert r.status_code == 200
    assert r.json()["estado"] == "APROBADA"

    # GET v1 -> SUSTITUIDA
    r = mundo.get(f"{T}/{t['id']}", "aprob_t09", mundo.company_a)
    assert r.status_code == 200
    assert r.json()["estado"] == "SUSTITUIDA"
    assert r.json()["sustituida_en"] is not None

    # GET v2 -> historia [1, 2]
    r = mundo.get(f"{T}/{t2['id']}", "aprob_t09", mundo.company_a)
    assert r.status_code == 200
    assert [h["version"] for h in r.json()["historia"]] == [1, 2]

    # Corrección sobre v1 -> NOT_APPROVED
    r = _post(
        mundo,
        f"{T}/{t['id']}/correccion",
        "capt_t09",
        mundo.company_a,
        {"valor": "907", "fuente_referencia": REF, "publicada_en": None, "motivo": "Intento sobre sustituida"},
    )
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_OFFICIAL_RATE_NOT_APPROVED"

    # Validaciones 422
    casos_invalidos = [
        {"moneda": "VED", "fecha_efectiva": fecha.isoformat(), "valor": "900", "fuente_referencia": REF, "publicada_en": None},
        {"moneda": "VES", "fecha_efectiva": fecha.isoformat(), "valor": "900", "fuente_referencia": REF, "publicada_en": None},
        {"moneda": "USD", "fecha_efectiva": (fecha + timedelta(days=1)).isoformat(), "valor": "0", "fuente_referencia": REF, "publicada_en": None},
        {"moneda": "USD", "fecha_efectiva": (fecha + timedelta(days=2)).isoformat(), "valor": "1.0000000000001", "fuente_referencia": REF, "publicada_en": None},
        {"moneda": "USD", "fecha_efectiva": (fecha + timedelta(days=3)).isoformat(), "valor": "900", "fuente_referencia": "corto", "publicada_en": None},
        {"moneda": "USD", "fecha_efectiva": fecha.isoformat(), "valor": "900", "fuente_referencia": REF, "publicada_en": (fecha + timedelta(days=1)).isoformat()},
    ]
    for cuerpo in casos_invalidos:
        r = mundo.post(T, "capt_t09", mundo.company_a, cuerpo)
        assert r.status_code == 422
        assert r.json()["code"] == "VALIDATION_ERROR"

    # GET T?moneda=USD
    r = mundo.get(f"{T}?moneda=USD", "aprob_t09", mundo.company_a)
    assert r.status_code == 200
    items = r.json()["items"]
    assert all(i["moneda"] == "USD" for i in items)
    ids_usd = {i["id"] for i in items}
    assert t["id"] in ids_usd
    assert t2["id"] in ids_usd

    # GET T?estado=SUSTITUIDA
    r = mundo.get(f"{T}?estado=SUSTITUIDA", "aprob_t09", mundo.company_a)
    assert r.status_code == 200
    ids_sust = {i["id"] for i in r.json()["items"]}
    assert t["id"] in ids_sust
    assert t2["id"] not in ids_sust


@ONLY_PG
def test_vectores_a_b_usd_contra_ves(mundo, gobierno, ocupacion):
    s = _preparar(mundo, ocupacion)
    hoy = hoy_de_negocio()
    _vigente(mundo, "USD", hoy - timedelta(days=10), "900")

    cdp = _cdp(mundo, s, "402", "1000000.00")

    # Dentro del límite
    r = _comprometer(mundo, s, [{"certificado_id": cdp["id"], "monto": "450000.00"}], cargo=s["lim_usd"], usuario="compr_t09")
    assert r.status_code == 201, r.text
    cuerpo = r.json()
    assert cuerpo["moneda"] == "VES"
    conv = cuerpo["conversion"]
    assert conv["requiere_conversion"] is True
    assert conv["moneda_operacion"] == "VES"
    assert conv["moneda_limite"] == "USD"
    assert conv["tasas"][0]["moneda"] == "USD"
    assert Decimal(conv["tasas"][0]["valor"]) == Decimal("900")
    assert conv["tasas"][0]["fecha_efectiva"] == (hoy - timedelta(days=10)).isoformat()
    assert conv["tasas"][0]["fuente"] == "BCV"
    assert Decimal(conv["total_ves"]) == Decimal("450000")
    assert Decimal(conv["limite_ves"]) == Decimal("450000")
    assert conv["dentro_del_limite"] is True

    # Excede
    r = _comprometer(mundo, s, [{"certificado_id": cdp["id"], "monto": "450000.01"}], cargo=s["lim_usd"], usuario="compr_t09")
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_BUDGET_COMMITMENT_AUTHORITY_AMOUNT_EXCEEDED"
    assert "conversion" in r.json()["details"]

    # Vista previa dentro
    r = mundo.get(
        f"{P}/{s['year_id']}/compromisos/verificacion-limite?autoridad_cargo_id={s['lim_usd']}&total=450000.00",
        "compr_t09",
        mundo.company_a,
    )
    assert r.status_code == 200
    assert r.json()["verificacion"]["resultado"] == "DENTRO_DEL_LIMITE"

    # Vista previa excede
    r = mundo.get(
        f"{P}/{s['year_id']}/compromisos/verificacion-limite?autoridad_cargo_id={s['lim_usd']}&total=450000.01",
        "compr_t09",
        mundo.company_a,
    )
    assert r.status_code == 200
    assert r.json()["verificacion"]["resultado"] == "EXCEDE_LIMITE"


@ONLY_PG
def test_vector_f_ved_heredado_sin_tasa(mundo, gobierno, ocupacion):
    s = _preparar(mundo, ocupacion)
    cdp = _cdp(mundo, s, "403", "1000000.00")

    r = _comprometer(mundo, s, [{"certificado_id": cdp["id"], "monto": "450000.00"}], cargo=s["lim_ves"], usuario="compr_t09")
    assert r.status_code == 201, r.text
    assert r.json()["conversion"] is None

    r = _comprometer(mundo, s, [{"certificado_id": cdp["id"], "monto": "450000.01"}], cargo=s["lim_ves"], usuario="compr_t09")
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_BUDGET_COMMITMENT_AUTHORITY_AMOUNT_EXCEEDED"


@ONLY_PG
def test_vectores_d_e_sin_tasa_bloquea(mundo, gobierno, ocupacion):
    s = _preparar(mundo, ocupacion)
    hoy = hoy_de_negocio()
    _vigente(mundo, "EUR", hoy + timedelta(days=1), "1100")

    cdp = _cdp(mundo, s, "404", "1000000.00")

    n_antes = len(mundo.get(f"{P}/{s['year_id']}/compromisos", "compr_t09", mundo.company_a).json()["items"])

    r = _comprometer(mundo, s, [{"certificado_id": cdp["id"], "monto": "10.00"}], cargo=s["lim_eur"], usuario="compr_t09")
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_OFFICIAL_RATE_REQUIRED"
    detalles = r.json()["details"]
    assert detalles["monedas_sin_tasa"] == ["EUR"]
    assert detalles["fecha"] == hoy.isoformat()
    assert detalles["moneda_operacion"] == "VES"
    assert detalles["moneda_limite"] == "EUR"

    # Vista previa
    r = mundo.get(
        f"{P}/{s['year_id']}/compromisos/verificacion-limite?autoridad_cargo_id={s['lim_eur']}&total=10.00",
        "compr_t09",
        mundo.company_a,
    )
    assert r.status_code == 200
    assert r.json()["verificacion"]["resultado"] == "SIN_TASA"

    n_despues = len(mundo.get(f"{P}/{s['year_id']}/compromisos", "compr_t09", mundo.company_a).json()["items"])
    assert n_despues == n_antes


@ONLY_PG
def test_vector_c_eur_contra_usd_exacto(mundo, gobierno, ocupacion):
    _preparar(mundo, ocupacion)
    hoy = hoy_de_negocio()
    _vigente(mundo, "EUR", hoy - timedelta(days=5), "1000")

    with mundo.factory() as db:
        uid = db.execute(select(User.id).where(User.username == "ua")).scalar_one()
        s = db
        ctx = CompanyContext(
            tenant_id=mundo.t1,
            company_id=mundo.company_a,
            company=s.get(Company, mundo.company_a),
            user_id=uid,
        )

        res = verificar_limite(
            db, ctx, "USD", Decimal("90000.00"), Decimal("81000.00"), "EUR", hoy,
            bloquear=False, exigir=True,
        )
        assert res["dentro_del_limite"] is True
        assert Decimal(res["total_ves"]) == Decimal("81000000")
        assert Decimal(res["limite_ves"]) == Decimal("81000000")

        res = verificar_limite(
            db, ctx, "USD", Decimal("90000.01"), Decimal("81000.00"), "EUR", hoy,
            bloquear=False, exigir=True,
        )
        assert res["dentro_del_limite"] is False

        res = verificar_limite(
            db, ctx, "VED", Decimal("10"), Decimal("10"), "VES", hoy,
            bloquear=False, exigir=True,
        )
        assert res["requiere_conversion"] is False


@ONLY_PG
def test_vectores_i_j_correccion_y_anulacion(mundo, gobierno, ocupacion):
    s = _preparar(mundo, ocupacion)
    hoy = hoy_de_negocio()
    fecha = hoy - timedelta(days=10)

    # Buscar la tasa USD aprobada de hoy-10 (creada en test 2)
    r = mundo.get(f"{T}?moneda=USD&estado=APROBADA", "aprob_t09", mundo.company_a)
    assert r.status_code == 200
    tasa_usd = next(i for i in r.json()["items"] if i["fecha_efectiva"] == fecha.isoformat())
    assert Decimal(tasa_usd["valor"]) == Decimal("900")
    assert tasa_usd["version"] == 1

    # Corrección a 1000
    r = _post(
        mundo,
        f"{T}/{tasa_usd['id']}/correccion",
        "capt_t09",
        mundo.company_a,
        {"valor": "1000", "fuente_referencia": REF, "publicada_en": None, "motivo": "Actualización del tipo de cambio"},
    )
    assert r.status_code == 201
    t2 = r.json()
    assert t2["version"] == 2
    _evidencia(mundo, t2["id"])
    r = _aprobar_tasa(mundo, t2["id"])
    assert r.status_code == 200

    # El compromiso del test 2 conserva la tasa antigua
    comps = mundo.get(f"{P}/{s['year_id']}/compromisos", "compr_t09", mundo.company_a).json()["items"]
    comp_antiguo = next(
        c
        for c in comps
        if c["conversion"] and Decimal(c["conversion"]["total_ves"]) == Decimal("450000")
    )
    assert Decimal(comp_antiguo["conversion"]["tasas"][0]["valor"]) == Decimal("900")

    # Nuevo compromiso usa la versión 2
    cdp = _cdp(mundo, s, "405", "1000000.00")
    r = _comprometer(mundo, s, [{"certificado_id": cdp["id"], "monto": "500000.00"}], cargo=s["lim_usd"], usuario="compr_t09")
    assert r.status_code == 201, r.text
    conv = r.json()["conversion"]
    assert Decimal(conv["tasas"][0]["valor"]) == Decimal("1000")
    assert conv["tasas"][0]["version"] == 2

    # Anular la v2 de hoy-10
    r = _post(mundo, f"{T}/{t2['id']}/anular", "aprob_t09", mundo.company_a, {"motivo": "Tasa incorrecta publicada"})
    assert r.status_code == 200
    assert r.json()["estado"] == "ANULADA"

    # Anular la USD de hoy-30
    r = mundo.get(f"{T}?moneda=USD&estado=APROBADA", "aprob_t09", mundo.company_a)
    assert r.status_code == 200
    tasa_30 = next(i for i in r.json()["items"] if i["fecha_efectiva"] == (hoy - timedelta(days=30)).isoformat())
    r = _post(mundo, f"{T}/{tasa_30['id']}/anular", "aprob_t09", mundo.company_a, {"motivo": "Anulación por auditoría"})
    assert r.status_code == 200
    assert r.json()["estado"] == "ANULADA"

    # Compromiso sin tasa
    r = _comprometer(mundo, s, [{"certificado_id": cdp["id"], "monto": "10.00"}], cargo=s["lim_usd"], usuario="compr_t09")
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_OFFICIAL_RATE_REQUIRED"

    # Segunda anulación -> NOT_ACTIVE
    r = _post(mundo, f"{T}/{t2['id']}/anular", "aprob_t09", mundo.company_a, {"motivo": "Intento de anular de nuevo"})
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_OFFICIAL_RATE_NOT_ACTIVE"

    # Anular la EUR en BORRADOR de hoy-30
    r = mundo.get(f"{T}?moneda=EUR&estado=BORRADOR", "aprob_t09", mundo.company_a)
    assert r.status_code == 200
    tasa_eur = next(i for i in r.json()["items"] if i["fecha_efectiva"] == (hoy - timedelta(days=30)).isoformat())
    r = _post(mundo, f"{T}/{tasa_eur['id']}/anular", "aprob_t09", mundo.company_a, {"motivo": "Anulación de borrador EUR"})
    assert r.status_code == 200
    assert r.json()["estado"] == "ANULADA"


@ONLY_PG
def test_concurrencia(mundo, gobierno, ocupacion):
    s = _preparar(mundo, ocupacion)
    hoy = hoy_de_negocio()

    # Crear USD hoy-60 con evidencia (BORRADOR)
    t = _tasa(mundo, "USD", hoy - timedelta(days=60), "1500")
    _evidencia(mundo, t["id"])

    h_aprob = mundo.como("aprob_t09", mundo.company_a)
    h_capt = mundo.como("capt_t09", mundo.company_a)
    h_compr = mundo.como("compr_t09", mundo.company_a)

    barrera = threading.Barrier(2, timeout=30)
    resultados: list[int] = []

    def aprobar():
        barrera.wait()
        r = mundo.client.post(
            f"/api/v1{T}/{t['id']}/aprobar",
            headers=h_aprob,
            json={},
        )
        resultados.append(r.status_code)

    hilos = [threading.Thread(target=aprobar) for _ in range(2)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    assert sorted(resultados) == [200, 409]

    # Corrección concurrente
    resultados_corr: list[int] = []
    barrera2 = threading.Barrier(2, timeout=30)

    def corregir():
        barrera2.wait()
        r = mundo.client.post(
            f"/api/v1{T}/{t['id']}/correccion",
            headers=h_capt,
            json={"valor": "2000", "fuente_referencia": REF, "publicada_en": None, "motivo": "Corrección concurrente"},
        )
        resultados_corr.append(r.status_code)

    hilos = [threading.Thread(target=corregir) for _ in range(2)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    assert sorted(resultados_corr) == [201, 409]

    # Buscar la corrección creada
    r = mundo.get(f"{T}?moneda=USD&estado=BORRADOR", "capt_t09", mundo.company_a)
    assert r.status_code == 200
    t2 = next(i for i in r.json()["items"] if i["sustituye_id"] == t["id"])
    _evidencia(mundo, t2["id"])

    # Concurrente: aprobar corrección vs compromiso
    cdp_carrera = _cdp(mundo, s, "405", "1000000.00")
    barrera3 = threading.Barrier(2, timeout=30)
    resultado_aprob: list[int] = []
    resultado_comp: list[int] = []

    def aprobar_corr():
        barrera3.wait()
        r = mundo.client.post(
            f"/api/v1{T}/{t2['id']}/aprobar",
            headers=h_aprob,
            json={},
        )
        resultado_aprob.append(r.status_code)

    def comprometer():
        barrera3.wait()
        r = mundo.client.post(
            f"/api/v1{P}/{s['year_id']}/compromisos",
            headers=h_compr,
            json={
                "concepto": "Orden de compra de material médico",
                "autoridad_cargo_id": s["lim_usd"],
                "soporte_documento_id": s["soporte"],
                "lineas": [{"certificado_id": cdp_carrera["id"], "monto": "1000.00"}],
            },
        )
        resultado_comp.append(r.status_code)

    hilos = [
        threading.Thread(target=aprobar_corr),
        threading.Thread(target=comprometer),
    ]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    assert resultado_aprob[0] == 200
    assert resultado_comp[0] == 201

    # Verificar el compromiso
    comps = mundo.get(f"{P}/{s['year_id']}/compromisos", "compr_t09", mundo.company_a).json()["items"]
    comp = next(
        c
        for c in comps
        if c["conversion"] and Decimal(c["conversion"]["total"]) == Decimal("1000.00")
    )
    tasa_comp = comp["conversion"]["tasas"][0]
    assert (tasa_comp["version"], Decimal(tasa_comp["valor"])) in {
        (1, Decimal("1500")),
        (2, Decimal("2000")),
    }


@ONLY_PG
def test_aislamiento(mundo, gobierno, ocupacion):
    _preparar(mundo, ocupacion)
    hoy = hoy_de_negocio()

    # Una tasa de A
    t = _tasa(mundo, "USD", hoy - timedelta(days=75), "1300")

    # GET como ub en company_b -> 404 NOT_FOUND
    r = mundo.get(f"{T}/{t['id']}", "ub", mundo.company_b)
    assert r.status_code == 404
    assert r.json()["code"] == "GOV_OFFICIAL_RATE_NOT_FOUND"

    # POST aprobar como ub -> 404
    r = _post(mundo, f"{T}/{t['id']}/aprobar", "ub", mundo.company_b, {})
    assert r.status_code == 404
    assert r.json()["code"] == "GOV_OFFICIAL_RATE_NOT_FOUND"

    # GET T como ua con company_b -> 404 COMPANY_NOT_FOUND
    r = mundo.get(T, "ua", mundo.company_b)
    assert r.status_code == 404
    assert r.json()["code"] == "COMPANY_NOT_FOUND"


@ONLY_PG
def test_permisos_mfa_y_catalogo(mundo, gobierno, ocupacion):
    _preparar(mundo, ocupacion)

    # solo_ver_t09 GET T -> 200
    r = mundo.get(T, "solo_ver_t09", mundo.company_a)
    assert r.status_code == 200

    # solo_ver_t09 POST T -> 403
    r = mundo.post(
        T,
        "solo_ver_t09",
        mundo.company_a,
        {"moneda": "USD", "fecha_efectiva": hoy_de_negocio().isoformat(), "valor": "900", "fuente_referencia": REF, "publicada_en": None},
    )
    assert r.status_code == 403

    # capt_t09 POST aprobar -> 403
    t = _tasa(mundo, "USD", hoy_de_negocio() - timedelta(days=90), "1400")
    r = _aprobar_tasa(mundo, t["id"], usuario="capt_t09")
    assert r.status_code == 403

    # MFA
    assert classify(["gobierno_tasas:approve"]) == SENSITIVE

    # Catálogo
    assert CATALOGO_DE_PERMISOS["gobierno_tasas"] == ["view", "manage", "approve"]


@ONLY_PG
def test_inmutable_en_base(mundo, gobierno, ocupacion):
    _preparar(mundo, ocupacion)

    with pytest.raises(DBAPIError):
        with mundo.factory() as db:
            db.execute(
                text("UPDATE gov_official_exchange_rates SET valor = 1 WHERE company_id = :c"),
                {"c": mundo.company_a},
            )
            db.commit()

    with pytest.raises(DBAPIError):
        with mundo.factory() as db:
            db.execute(
                text("DELETE FROM gov_official_exchange_rates WHERE company_id = :c"),
                {"c": mundo.company_a},
            )
            db.commit()


@ONLY_PG
def test_auditoria(mundo, gobierno, ocupacion):
    _preparar(mundo, ocupacion)

    with mundo.factory() as db:
        eventos = db.execute(
            select(AuditEvent).where(
                AuditEvent.entity_type == "GovernmentOfficialExchangeRate",
                AuditEvent.company_id == mundo.company_a,
            )
        ).scalars().all()

    acciones = {e.action for e in eventos}
    assert "GOV_OFFICIAL_RATE_CREATED" in acciones
    assert "GOV_OFFICIAL_RATE_APPROVED" in acciones
    assert "GOV_OFFICIAL_RATE_SUPERSEDED" in acciones
    assert "GOV_OFFICIAL_RATE_ANNULLED" in acciones


@ONLY_PG
def test_bud01_normaliza_y_org03_rechaza_ved(mundo, gobierno, ocupacion):
    _preparar(mundo, ocupacion)

    # BUD-01 normaliza VED -> VES
    r = _post(mundo, P, "ua", mundo.company_a, {"anio": ANIO - 1})
    assert r.status_code == 201, r.text
    assert r.json()["moneda_funcional"] == "VES"

    # ORG-03 rechaza límite en VED
    with pytest.raises(DBAPIError):
        _cargo_comprometer(mundo, ocupacion, "MONTO", "10.00", "VED")
