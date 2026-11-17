"""Pruebas de cobertura SoD entre productores de eventos y consumidores (CTL-07 y REP-10)."""

import json
import os
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.modules.audit.models import AuditEvent
from app.modules.government.models import GovernmentSoDRule
from app.modules.government.service_sod_eventos import (
    ACCIONES_SOD,
    PRODUCTORES,
    es_bloqueo_sod,
)
from app.shared.audit import record_audit
from app.shared.audit_catalog import catalog
from app.shared.clock import hoy_de_negocio
from tests import test_gov_bud08 as bud08
from tests.test_gov_ctl07_alertas import _alertas, _revisar, _uid
from tests.test_gov_proc11_sod_funciones import (
    _cerrar_reglas_al_terminar,  # noqa: F401
)
from tests.test_gov_proc11_sod_funciones import (
    test_bloqueo_al_asumir_funcion_incompatible as _bloqueo_proc11,
)

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos", "tests.org04_ayudantes")

pytestmark = pytest.mark.skipif(
    not os.environ.get("KONTROL_TEST_DB_URL", "").startswith("postgresql"),
    reason="GOV-SOD-COVERAGE-01 se verifica sobre PostgreSQL",
)

A = "/gobierno/control/alertas"
R = "/gobierno/control-interno/reporte"


@pytest.fixture(autouse=True)
def _limpiar_estado_bud08():
    bud08._ESTADO.clear()
    yield


def _sembrar(
    mundo,
    accion,
    entity_type,
    entity_id,
    after,
    *,
    empresa=None,
    tenant_id=None,
    usuario="uab",
):
    with mundo.factory() as db:
        evento = record_audit(
            db,
            action=accion,
            entity_type=entity_type,
            entity_id=entity_id,
            tenant_id=tenant_id or mundo.t1,
            company_id=empresa or mundo.company_a,
            user_id=_uid(mundo, usuario),
            after=after,
        )
        db.commit()
        return str(evento.id)


def _tres(mundo, marca, **kw):
    """Siembra un evento de cada productor SoD y devuelve acción -> evento_id."""
    ids = {}
    ids["GOV_SOD_CONFLICT_BLOCKED"] = _sembrar(
        mundo,
        "GOV_SOD_CONFLICT_BLOCKED",
        "GovernmentSoDRule",
        str(uuid4()),
        {
            "regla_codigo": f"SOD-{marca}",
            "regla_version": 1,
            "proceso": "DOC-02",
            "accion": "DOC02_EDITAR",
            "accion_previa": "DOC02_REGISTRAR",
            "objeto_tipo": "GovernmentAct",
            "objeto_id": str(uuid4()),
        },
        **kw,
    )
    ids["GOV_SOD_ROLE_CONFLICT_BLOCKED"] = _sembrar(
        mundo,
        "GOV_SOD_ROLE_CONFLICT_BLOCKED",
        "GovernmentProcurementFile",
        str(uuid4()),
        {
            "regla_codigo": f"SODF-{marca}",
            "regla_version": 2,
            "funcion": "SOLICITANTE",
            "funcion_previa": "RECEPTOR",
            "expediente_id": str(uuid4()),
            "expediente_numero": f"EX-{marca}",
            "actor": "uab",
        },
        **kw,
    )
    ids["GOV_BUDGET_COMMITMENT_SOD_BLOCKED"] = _sembrar(
        mundo,
        "GOV_BUDGET_COMMITMENT_SOD_BLOCKED",
        "GovernmentBudgetYear",
        str(uuid4()),
        {
            "anio": 2026,
            "certificados": [f"CDP-{marca}"],
            "regla": "Quien certifica no compromete",
        },
        **kw,
    )
    return ids


def _eventos_ids(data: dict) -> list[str]:
    return [e["evento_id"] for e in data.get("eventos", [])]


def test_autoridad_y_catalogo():
    assert set(ACCIONES_SOD) == {
        "GOV_SOD_CONFLICT_BLOCKED",
        "GOV_SOD_ROLE_CONFLICT_BLOCKED",
        "GOV_BUDGET_COMMITMENT_SOD_BLOCKED",
    }
    for accion in ACCIONES_SOD:
        assert es_bloqueo_sod(accion) is True
    assert es_bloqueo_sod("GOV_SOD_RULE_CREATED") is False
    assert es_bloqueo_sod(None) is False

    mapeo = catalog()
    entity_by_action = {
        "GOV_SOD_CONFLICT_BLOCKED": "GovernmentSoDRule",
        "GOV_SOD_ROLE_CONFLICT_BLOCKED": "GovernmentProcurementFile",
        "GOV_BUDGET_COMMITMENT_SOD_BLOCKED": "GovernmentBudgetYear",
    }
    for accion, entity_type in entity_by_action.items():
        spec = mapeo.get((accion, entity_type))
        assert spec is not None
        assert spec.code == accion
        assert spec.entity_type == entity_type
        assert spec.transaction_class == "REJECTION"
    bloqueadas = {
        spec.code
        for spec in mapeo.values()
        if "SOD" in spec.code and spec.code.endswith("_BLOCKED") and spec.transaction_class == "REJECTION"
    }
    assert bloqueadas == set(PRODUCTORES)


def test_sin_listas_divergentes():
    raiz = Path(__file__).resolve().parents[1] / "app"
    acciones = set(ACCIONES_SOD)
    permitidos = {
        "service_sod_eventos.py",
        "service_sod.py",
        "service_identidad.py",
        "service_sod_funciones.py",
        "service_presupuesto_compromiso.py",
        "audit_catalog_entries.py",
    }
    encontrados = set()
    for ruta in raiz.rglob("*.py"):
        texto = ruta.read_text(encoding="utf-8")
        if any(accion in texto for accion in acciones):
            encontrados.add(ruta.name)
    assert encontrados <= permitidos
    for ruta in (
        raiz / "modules" / "government" / "service_alertas.py",
        raiz / "modules" / "government" / "service_reporte_control.py",
    ):
        texto = ruta.read_text(encoding="utf-8")
        for accion in acciones:
            assert accion not in texto


def test_ctl07_tres_productores_visibles(mundo, gobierno):
    marca = uuid4().hex[:8]
    ids = _tres(mundo, marca)

    def alertas(usuario, empresa=None):
        return _alertas(mundo, usuario, empresa)

    data = alertas("ua")
    por_clave = {a["clave"]: a for a in data["alertas"]}
    assert data["aviso"] == "Una alerta es una señal para revisar; no es una acusación ni una conclusión."
    for accion, evento_id in ids.items():
        alerta = por_clave.get(f"AUTOAPROBACION:{evento_id}")
        assert alerta is not None, f"falta alerta para {accion}"
        assert alerta["tipo_etiqueta"] == "Segregación de funciones"
    assert por_clave[f"AUTOAPROBACION:{ids['GOV_SOD_CONFLICT_BLOCKED']}"]["titulo"] == (
        "Intento bloqueado por segregación de funciones"
    )
    assert por_clave[f"AUTOAPROBACION:{ids['GOV_SOD_ROLE_CONFLICT_BLOCKED']}"]["titulo"] == (
        "Intento bloqueado por funciones incompatibles"
    )
    assert por_clave[f"AUTOAPROBACION:{ids['GOV_BUDGET_COMMITMENT_SOD_BLOCKED']}"]["titulo"] == (
        "Intento bloqueado por segregación de funciones"
    )
    bad = por_clave[f"AUTOAPROBACION:{ids['GOV_BUDGET_COMMITMENT_SOD_BLOCKED']}"]
    assert "intentó registrar un compromiso después de haber emitido o firmado la certificación" in bad["detalle"]
    assert f"CDP-{marca}" in bad["detalle"]
    assert "La regla «Quien certifica no compromete» lo bloqueó." in bad["detalle"]
    sujetos_dict = {s["etiqueta"]: s["valor"] for s in bad["sujetos"]}
    assert sujetos_dict.get("Regla") == "Quien certifica no compromete"
    assert sujetos_dict.get("Ejercicio") == "2026"
    assert f"CDP-{marca}" in sujetos_dict.get("Certificaciones", "")
    proc = por_clave[f"AUTOAPROBACION:{ids['GOV_SOD_ROLE_CONFLICT_BLOCKED']}"]
    sujetos_proc = {s["etiqueta"]: s["valor"] for s in proc["sujetos"]}
    assert sujetos_proc.get("Expediente") == f"EX-{marca}"
    for alerta in data["alertas"]:
        assert alerta["es_sujeto"] is False
    data_uab = alertas("uab")
    for evento_id in ids.values():
        alerta_uab = next((a for a in data_uab["alertas"] if a["clave"] == f"AUTOAPROBACION:{evento_id}"), None)
        assert alerta_uab is not None
        assert alerta_uab["es_sujeto"] is True


def test_bud08_entity_id_no_es_regla(mundo, gobierno):
    marca = uuid4().hex[:8]
    with mundo.factory() as db:
        regla = GovernmentSoDRule(
            tenant_id=mundo.t1,
            company_id=mundo.company_a,
            codigo=f"R{marca}",
            nombre=f"Regla trampa {marca}",
            descripcion="Regla para verificar resolución por entity_id",
            proceso="DOC-02",
            accion_a="DOC02_EDITAR",
            accion_b="DOC02_REGISTRAR",
            vigente_desde=hoy_de_negocio(),
            estado="BORRADOR",
            created_by=_uid(mundo, "ua"),
        )
        db.add(regla)
        db.commit()
        db.refresh(regla)
        regla_id = str(regla.id)

    ids = {}
    ids["GOV_BUDGET_COMMITMENT_SOD_BLOCKED"] = _sembrar(
        mundo,
        "GOV_BUDGET_COMMITMENT_SOD_BLOCKED",
        "GovernmentBudgetYear",
        regla_id,
        {
            "anio": 2026,
            "certificados": [f"CDP-{marca}"],
            "regla": "Quien certifica no compromete",
        },
    )
    ids["GOV_SOD_ROLE_CONFLICT_BLOCKED"] = _sembrar(
        mundo,
        "GOV_SOD_ROLE_CONFLICT_BLOCKED",
        "GovernmentProcurementFile",
        regla_id,
        {
            "regla_codigo": f"SODF-{marca}",
            "regla_version": 2,
            "funcion": "SOLICITANTE",
            "funcion_previa": "RECEPTOR",
            "expediente_id": str(uuid4()),
            "expediente_numero": f"EX-{marca}",
            "actor": "uab",
        },
    )
    ids["GOV_SOD_CONFLICT_BLOCKED"] = _sembrar(
        mundo,
        "GOV_SOD_CONFLICT_BLOCKED",
        "GovernmentSoDRule",
        regla_id,
        {
            "regla_codigo": f"SOD-{marca}",
            "regla_version": 1,
            "proceso": "DOC-02",
            "accion": "DOC02_EDITAR",
            "accion_previa": "DOC02_REGISTRAR",
            "objeto_tipo": "GovernmentAct",
            "objeto_id": str(uuid4()),
        },
    )

    hoy = hoy_de_negocio()
    resp = mundo.get(f"{R}?desde={hoy.isoformat()}&hasta={hoy.isoformat()}", "ua", mundo.company_a)
    assert resp.status_code == 200, resp.text
    data = resp.json()["conflictos_sod"]
    eventos = {e["evento_id"]: e for e in data["eventos"]}

    ev = eventos.get(ids["GOV_BUDGET_COMMITMENT_SOD_BLOCKED"])
    assert ev is not None
    assert ev["regla_nombre"] == "Quien certifica no compromete"
    assert ev["regla_codigo"] is None

    ev = eventos.get(ids["GOV_SOD_ROLE_CONFLICT_BLOCKED"])
    assert ev is not None
    assert ev["regla_nombre"] == f"SODF-{marca}"
    assert ev["regla_codigo"] == f"SODF-{marca}"

    ev = eventos.get(ids["GOV_SOD_CONFLICT_BLOCKED"])
    assert ev is not None
    assert ev["regla_nombre"] == f"Regla trampa {marca}"
    assert ev["regla_codigo"] == f"SOD-{marca}"


def test_ctl07_clave_estable_y_revision(mundo, gobierno):
    marca = uuid4().hex[:8]
    ids = _tres(mundo, marca)
    clave_bud = f"AUTOAPROBACION:{ids['GOV_BUDGET_COMMITMENT_SOD_BLOCKED']}"
    r = _revisar(mundo, clave_bud)
    assert r.status_code >= 200 and r.status_code < 300, r.text
    data = _alertas(mundo, "ua")
    estados = {a["clave"]: a["estado"] for a in data["alertas"]}
    assert estados.get(clave_bud) == "REVISADA"
    assert estados.get(f"AUTOAPROBACION:{ids['GOV_SOD_CONFLICT_BLOCKED']}") == "PENDIENTE"
    assert estados.get(f"AUTOAPROBACION:{ids['GOV_SOD_ROLE_CONFLICT_BLOCKED']}") == "PENDIENTE"


def test_rep10_total_y_agrupacion(mundo, gobierno):
    hoy = hoy_de_negocio()
    url = f"{R}?desde={hoy.isoformat()}&hasta={hoy.isoformat()}"
    antes_resp = mundo.get(url, "ua", mundo.company_a)
    assert antes_resp.status_code == 200, antes_resp.text
    antes = antes_resp.json()["conflictos_sod"]
    marca = uuid4().hex[:8]
    ids = _tres(mundo, marca)
    despues_resp = mundo.get(url, "ua", mundo.company_a)
    assert despues_resp.status_code == 200, despues_resp.text
    despues = despues_resp.json()["conflictos_sod"]

    assert despues["total"] == antes["total"] + 3

    def por_tipo(datos):
        return {f["tipo_conflicto"]: f["total"] for f in datos["por_tipo"]}

    def por_proceso(datos):
        return {f["proceso"]: f["total"] for f in datos["por_proceso"]}

    tipos_antes = por_tipo(antes)
    tipos_despues = por_tipo(despues)
    for tipo in ("INCOMPATIBLE_ACTIONS", "INCOMPATIBLE_FUNCTIONS", "SEGREGATION_OF_DUTIES"):
        assert tipos_despues.get(tipo, 0) == tipos_antes.get(tipo, 0) + 1

    procesos_antes = por_proceso(antes)
    procesos_despues = por_proceso(despues)
    for proceso in ("DOC-02", "PROC-11", "BUD-08"):
        assert procesos_despues.get(proceso, 0) == procesos_antes.get(proceso, 0) + 1

    por_regla = {(f["regla_codigo"], f["regla_nombre"]): f for f in despues["por_regla"]}
    fila_ctl = por_regla.get((f"SOD-{marca}", f"SOD-{marca}"))
    assert fila_ctl is not None
    assert fila_ctl["tipo_conflicto"] == "INCOMPATIBLE_ACTIONS"
    assert fila_ctl["total"] == 1
    fila_proc = por_regla.get((f"SODF-{marca}", f"SODF-{marca}"))
    assert fila_proc is not None
    assert fila_proc["proceso"] == "PROC-11"
    assert fila_proc["total"] == 1

    eventos = {e["evento_id"]: e for e in despues["eventos"]}
    assert ids["GOV_SOD_CONFLICT_BLOCKED"] in eventos
    assert eventos[ids["GOV_SOD_CONFLICT_BLOCKED"]]["tipo_conflicto"] == "INCOMPATIBLE_ACTIONS"
    assert eventos[ids["GOV_SOD_CONFLICT_BLOCKED"]]["proceso"] == "DOC-02"
    assert ids["GOV_SOD_ROLE_CONFLICT_BLOCKED"] in eventos
    assert eventos[ids["GOV_SOD_ROLE_CONFLICT_BLOCKED"]]["tipo_conflicto"] == "INCOMPATIBLE_FUNCTIONS"
    assert eventos[ids["GOV_SOD_ROLE_CONFLICT_BLOCKED"]]["proceso"] == "PROC-11"
    assert ids["GOV_BUDGET_COMMITMENT_SOD_BLOCKED"] in eventos
    ev = eventos[ids["GOV_BUDGET_COMMITMENT_SOD_BLOCKED"]]
    assert ev["tipo_conflicto"] == "SEGREGATION_OF_DUTIES"
    assert ev["proceso"] == "BUD-08"
    assert ev["regla_codigo"] is None
    assert ev["recurso_etiqueta"] == "Ejercicio 2026"
    assert ev["accion_etiqueta"] == "Registrar un compromiso"


def test_rep10_periodo(mundo, gobierno):
    hoy = hoy_de_negocio()
    marca = uuid4().hex[:8]
    ids = _tres(mundo, marca)

    url_hoy = f"{R}?desde={hoy.isoformat()}&hasta={hoy.isoformat()}"
    data = mundo.get(url_hoy, "ua", mundo.company_a).json()["conflictos_sod"]
    ids_en_eventos = set(_eventos_ids(data))
    assert set(ids.values()) <= ids_en_eventos

    lejano_desde = hoy - timedelta(days=10)
    lejano_hasta = hoy - timedelta(days=1)
    url_lejano = f"{R}?desde={lejano_desde.isoformat()}&hasta={lejano_hasta.isoformat()}"
    data_lejano = mundo.get(url_lejano, "ua", mundo.company_a).json()["conflictos_sod"]
    ids_lejano = set(_eventos_ids(data_lejano))
    assert ids_lejano.isdisjoint(set(ids.values()))

    futuro_desde = hoy + timedelta(days=1)
    futuro_hasta = hoy + timedelta(days=3)
    url_futuro = f"{R}?desde={futuro_desde.isoformat()}&hasta={futuro_hasta.isoformat()}"
    data_futuro = mundo.get(url_futuro, "ua", mundo.company_a).json()["conflictos_sod"]
    ids_futuro = set(_eventos_ids(data_futuro))
    assert ids_futuro.isdisjoint(set(ids.values()))


def test_aislamiento_empresa_y_tenant(mundo, gobierno):
    marca_a = uuid4().hex[:8]
    ids_a = _tres(mundo, marca_a)

    texto_reporte_ub = json.dumps(
        mundo.get(
            f"{R}?desde={hoy_de_negocio().isoformat()}&hasta={hoy_de_negocio().isoformat()}",
            "ub",
            mundo.company_b,
        ).json()
    )
    for evento_id in ids_a.values():
        assert evento_id not in texto_reporte_ub
    assert marca_a not in texto_reporte_ub

    datos_alertas_ub = _alertas(mundo, "ub", mundo.company_b)
    for evento_id in ids_a.values():
        assert f"AUTOAPROBACION:{evento_id}" not in json.dumps(datos_alertas_ub)
    assert marca_a not in json.dumps(datos_alertas_ub)

    hoy = hoy_de_negocio()
    resp_uc_reporte = mundo.get(f"{R}?desde={hoy.isoformat()}&hasta={hoy.isoformat()}", "uc", mundo.company_c, tenant="T2")
    assert resp_uc_reporte.status_code == 200, resp_uc_reporte.text
    texto_reporte_uc = json.dumps(resp_uc_reporte.json())
    for evento_id in ids_a.values():
        assert evento_id not in texto_reporte_uc
    assert marca_a not in texto_reporte_uc

    resp_uc_alertas = mundo.get(A, "uc", mundo.company_c, tenant="T2")
    assert resp_uc_alertas.status_code == 200, resp_uc_alertas.text
    texto_alertas_uc = json.dumps(resp_uc_alertas.json())
    for evento_id in ids_a.values():
        assert f"AUTOAPROBACION:{evento_id}" not in texto_alertas_uc
    assert marca_a not in texto_alertas_uc

    marca_b = uuid4().hex[:8]
    ids_b = _tres(mundo, marca_b, empresa=mundo.company_b, usuario="ub")
    resp_ua_reporte = mundo.get(
        f"{R}?desde={hoy.isoformat()}&hasta={hoy.isoformat()}",
        "ua",
        mundo.company_a,
    )
    texto_reporte_ua = json.dumps(resp_ua_reporte.json())
    for evento_id in ids_b.values():
        assert evento_id not in texto_reporte_ua
    assert marca_b not in texto_reporte_ua
    datos_ua_alertas = _alertas(mundo, "ua", mundo.company_a)
    for evento_id in ids_b.values():
        assert f"AUTOAPROBACION:{evento_id}" not in json.dumps(datos_ua_alertas)
    assert marca_b not in json.dumps(datos_ua_alertas)


def test_rep10_csv_incluye_los_tres(mundo, gobierno):
    hoy = hoy_de_negocio()
    marca = uuid4().hex[:8]
    _tres(mundo, marca)
    resp = mundo.get(f"{R}.csv?desde={hoy.isoformat()}&hasta={hoy.isoformat()}", "ua", mundo.company_a)
    assert resp.status_code == 200, resp.text
    texto = resp.text
    assert "Fecha,Usuario,Regla,Proceso,Acción intentada,Acción previa,Tipo de conflicto,Recurso" in texto
    assert f"SOD-{marca}" in texto
    assert f"SODF-{marca}" in texto
    assert "Quien certifica no compromete" in texto
    assert "Segregación de funciones" in texto
    assert "Funciones incompatibles" in texto
    assert "Ejercicio 2026" in texto


def test_bud08_productor_real(mundo, gobierno, ocupacion):
    s = bud08._preparar(mundo, ocupacion)
    cdp = bud08._cdp(mundo, s, "407", "300.00")
    r = bud08._comprometer(
        mundo,
        s,
        [{"certificado_id": cdp["id"], "monto": "10.00"}],
        usuario="ua",
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_SOD_CONFLICT"

    with mundo.factory() as db:
        evento = db.execute(
            select(AuditEvent)
            .where(
                AuditEvent.action == "GOV_BUDGET_COMMITMENT_SOD_BLOCKED",
                AuditEvent.entity_id == s["year_id"],
                AuditEvent.company_id == mundo.company_a,
            )
            .order_by(AuditEvent.event_time.desc())
            .limit(1)
        ).scalar_one()
        evento_id = str(evento.id)

    data = _alertas(mundo, "ua")
    alerta = next((a for a in data["alertas"] if a["clave"] == f"AUTOAPROBACION:{evento_id}"), None)
    assert alerta is not None
    assert cdp["codigo"] in alerta["detalle"]

    hoy = hoy_de_negocio()
    data_reporte = mundo.get(
        f"{R}?desde={hoy.isoformat()}&hasta={hoy.isoformat()}",
        "ua",
        mundo.company_a,
    ).json()["conflictos_sod"]
    ev = next((e for e in data_reporte["eventos"] if e["evento_id"] == evento_id), None)
    assert ev is not None
    assert ev["tipo_conflicto"] == "SEGREGATION_OF_DUTIES"
    assert ev["proceso"] == "BUD-08"


def test_proc11_productor_real(mundo, gobierno, ocupacion):
    _bloqueo_proc11(mundo, gobierno, ocupacion)
    with mundo.factory() as db:
        evento = db.execute(
            select(AuditEvent)
            .where(
                AuditEvent.action == "GOV_SOD_ROLE_CONFLICT_BLOCKED",
                AuditEvent.company_id == mundo.company_a,
            )
            .order_by(AuditEvent.event_time.desc())
            .limit(1)
        ).scalar_one()
        evento_id = str(evento.id)

    data = _alertas(mundo, "ua")
    alerta = next((a for a in data["alertas"] if a["clave"] == f"AUTOAPROBACION:{evento_id}"), None)
    assert alerta is not None
    assert alerta["titulo"] == "Intento bloqueado por funciones incompatibles"

    hoy = hoy_de_negocio()
    data_reporte = mundo.get(
        f"{R}?desde={hoy.isoformat()}&hasta={hoy.isoformat()}",
        "ua",
        mundo.company_a,
    ).json()["conflictos_sod"]
    ev = next((e for e in data_reporte["eventos"] if e["evento_id"] == evento_id), None)
    assert ev is not None
    assert ev["proceso"] == "PROC-11"
    assert ev["tipo_conflicto"] == "INCOMPATIBLE_FUNCTIONS"
    assert ev["regla_nombre"] == "Receptor no evalúa"
