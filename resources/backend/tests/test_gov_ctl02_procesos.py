"""CTL-02 · Resolución canónica de procesos en la bitácora (CTL-02-AUDIT-PROCESS-RESOLUTION).

Los eventos se emiten con `record_audit` y acciones reales del catálogo: la resolución depende
solo del par (acción, entidad) y de la metadata del catálogo, y el contexto institucional lo
calcula el proveedor de contexto a partir del actor.
"""

import csv
import io
import uuid

import pytest
from sqlalchemy import select

from app.modules.identity_access.models import User
from app.shared.audit import record_audit
from tests.org06_ayudantes import cuerpo_vinculo, titular_activo, vinculo_activo
from tests.org06_guarda import cuenta_con_permisos
from tests.test_gov_ctl06_hallazgos import _crear_usuario_con_permisos

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos", "tests.org04_ayudantes")
B = "/api/v1/gobierno/bitacora"
A = "/api/v1/gobierno/auditoria"

# (proceso esperado, módulo esperado, acción real del catálogo, entidad)
ANTES_HUERFANOS = [
    ("BUD-06", "BUD", "GOV_BUDGET_CERTIFICATE_ISSUED", "GovernmentBudgetYear"),
    ("BUD-08", "BUD", "GOV_BUDGET_COMMITMENT_ISSUED", "GovernmentBudgetYear"),
    ("CNT-01", "CNT", "GOV_CONTRACT_DRAFT_CREATED", "GovernmentProcurementFile"),
    ("CTL-07", "CTL", "GOV_ATYPICAL_ALERT_REVIEWED", "GovernmentAtypicalAlertReview"),
    ("PROC-11", "PROC", "GOV_SOD_ROLE_RULE_CREATED", "GovernmentSoDRoleRule"),
    ("REP-03", "REP", "GOV_PROCUREMENT_REPORT_EXPORTED", "GovernmentProcurementFile"),
    ("REP-10", "REP", "GOV_INTERNAL_CONTROL_REPORT_EXPORTED", "GovernmentEntity"),
    ("TRE-09", "TRE", "GOV_OFFICIAL_RATE_CREATED", "GovernmentOfficialExchangeRate"),
]
YA_CORRECTOS = [
    ("ORG-01", "ORG", "GOV_ENTITY_CREATED", "GovernmentEntity"),
    ("DOC-02", "DOC", "GOV_ACT_CORRECTED", "GovernmentAct"),
    ("PROC-03", "PROC", "GOV_PROCUREMENT_FILE_CREATED", "GovernmentProcurementFile"),
    ("TRE-01", "TRE", "GOV_BANK_CREATED", "GovernmentBank"),
    ("CTL-06", "CTL", "GOV_FINDING_CREATED", "GovernmentFinding"),
]


def _auditor(mundo, nombre, company=None, sample=False):
    permisos = [("gobierno_auditoria", "view")] + ([("gobierno_auditoria", "sample")] if sample else [])
    if company is None:
        cuenta_con_permisos(mundo, nombre, permisos)
        return mundo.como(nombre, mundo.company_a)
    _crear_usuario_con_permisos(mundo, nombre, permisos, company)
    return mundo.como(nombre, company)


def _emitir(mundo, action, entity_type, *, company=None, user_id=None, request_id=None):
    company = company or mundo.company_a
    with mundo.factory() as db:
        evento = record_audit(
            db,
            action=action,
            entity_type=entity_type,
            entity_id=str(uuid.uuid4()),
            company_id=company,
            user_id=user_id,
            request_id=request_id or f"ctl02p-{uuid.uuid4().hex[:12]}",
        )
        db.commit()
        return str(evento.id), evento.request_id


def _item(mundo, h, evento_id, accion):
    r = mundo.client.get(B, headers=h, params={"accion": accion, "por_pagina": 50})
    assert r.status_code == 200, r.text
    return next(i for i in r.json()["items"] if i["id"] == evento_id)


# 1-9 · Eventos antes huérfanos y eventos que ya resolvían bien.


def test_ctl02_p01_defecto_bud08_sin_proceso(mundo, gobierno):
    """Contra 9f2c3dde falla: el evento de BUD-08 sale con proceso vacío y el owner_spec como nombre."""
    evento_id, _ = _emitir(mundo, "GOV_BUDGET_COMMITMENT_ISSUED", "GovernmentBudgetYear")
    h = _auditor(mundo, "ctl02p_01")
    item = _item(mundo, h, evento_id, "GOV_BUDGET_COMMITMENT_ISSUED")
    assert item["proceso"] == "BUD-08"
    assert item["proceso_nombre"] == "Compromiso presupuestario"


@pytest.mark.parametrize(("codigo", "modulo", "accion", "entidad"), ANTES_HUERFANOS + YA_CORRECTOS)
def test_ctl02_p02_proceso_y_modulo_en_lista_y_detalle(mundo, gobierno, codigo, modulo, accion, entidad):
    from app.modules.government import procesos

    evento_id, _ = _emitir(mundo, accion, entidad)
    h = _auditor(mundo, f"ctl02p_02_{codigo.lower().replace('-', '')}")
    item = _item(mundo, h, evento_id, accion)
    assert item["proceso"] == codigo
    assert item["proceso_nombre"] == procesos.nombre_de(codigo)
    assert item["modulo"] == modulo
    assert item["modulo_nombre"] == procesos.modulo_nombre(modulo)
    d = mundo.client.get(f"{B}/{evento_id}", headers=h)
    assert d.status_code == 200, d.text
    assert (d.json()["proceso"], d.json()["modulo"]) == (codigo, modulo)


# 10-12 · Clases de evento y guardia del catálogo.


def test_ctl02_p03_clases_plataforma_autenticacion_y_sistema():
    from app.modules.government import procesos
    from app.shared.audit_catalog import catalog

    plataforma = next(s for s in catalog().values() if s.owner_module == "master_data")
    r = procesos.resolver_proceso(plataforma.code, plataforma.entity_type)
    assert (r.clase, r.codigo, r.modulo) == (procesos.CLASE_PLATAFORMA, None, None)

    r = procesos.resolver_proceso("LOGIN_SUCCESS", "User")
    assert (r.clase, r.codigo) == (procesos.CLASE_AUTENTICACION, None)

    r = procesos.resolver_proceso("ACCION_INEXISTENTE", "Nada")
    assert (r.clase, r.codigo, r.fuente) == (procesos.CLASE_SISTEMA, None, procesos.FUENTE_SIN_REGISTRO)

    r = procesos.resolver_proceso("GOV_BUDGET_COMMITMENT_ISSUED", "GovernmentBudgetYear")
    assert (r.clase, r.codigo, r.fuente) == (procesos.CLASE_PROCESO, "BUD-08", procesos.FUENTE_CATALOGO)


def test_ctl02_p04_autenticacion_en_la_bitacora_sin_proceso_por_diseno(mundo, gobierno, ocupacion):
    asig, _ = titular_activo(mundo, ocupacion)
    user_id = cuenta_con_permisos(mundo, "ctl02p_04", [("gobierno_ocupacion", "view")])
    vinculo_activo(mundo, cuerpo_vinculo(user_id, asig["funcionario"]["id"]))
    with mundo.factory() as db:
        user = db.execute(select(User).where(User.username == "ctl02p_04")).scalar_one()
        record_audit(
            db, action="LOGIN_SUCCESS", entity_type="User", entity_id=str(user.id),
            tenant_id=str(user.tenant_id), user_id=str(user.id), ip="10.0.0.1",
        )
        db.commit()
    h = _auditor(mundo, "ctl02p_04_aud")
    r = mundo.client.get(B, headers=h, params={"accion": "LOGIN_SUCCESS", "usuario": "ctl02p_04"})
    item = r.json()["items"][0]
    assert (item["proceso"], item["proceso_nombre"]) == ("AUTENTICACION", "Autenticación")
    assert item["modulo"] is None


def test_ctl02_p05_guardia_todo_evento_de_gobierno_resuelve_su_proceso():
    """UNMAPPED_PROCESS_EVENTS_GUARD: un evento de Gobierno nuevo sin proceso registrado falla aquí."""
    from app.modules.government import procesos
    from app.shared.audit_catalog import catalog

    sin_proceso = []
    for spec in catalog().values():
        r = procesos.resolver_proceso(spec.code, spec.entity_type)
        if spec.owner_module == procesos.MODULO_GOBIERNO and spec.code not in procesos.ACCIONES_AUTENTICACION:
            if r.clase != procesos.CLASE_PROCESO or r.codigo is None:
                sin_proceso.append((spec.code, spec.entity_type, spec.owner_spec))
        else:
            assert r.clase != procesos.CLASE_PROCESO, (spec.code, spec.entity_type)
    assert sin_proceso == [], f"Eventos de Gobierno sin proceso registrado en procesos.py: {sin_proceso}"


def test_ctl02_p06_guardia_registro_coherente_con_catalogo_y_roadmap():
    """Cada proceso tiene eventos, una sola Spec dueña por owner_spec y existe en la matriz del roadmap."""
    from pathlib import Path

    from app.modules.government import procesos
    from app.shared.audit_catalog import catalog

    owner_specs = [o for p in procesos.PROCESOS for o in p.owner_specs]
    assert len(owner_specs) == len(set(owner_specs))
    codigos = [p.codigo for p in procesos.PROCESOS]
    assert len(codigos) == len(set(codigos))
    usados = {s.owner_spec for s in catalog().values() if s.owner_module == procesos.MODULO_GOBIERNO}
    assert set(owner_specs) - usados == set(), "Procesos registrados sin ningún evento en el catálogo"
    modulos = {m.codigo for m in procesos.MODULOS}
    assert {p.modulo for p in procesos.PROCESOS} <= modulos

    matriz = Path(__file__).resolve().parents[3] / (
        "docs/roadmap/government-product-completeness/GOVERNMENT_PRODUCT_COMPLETENESS_MATRIX.csv"
    )
    with matriz.open(encoding="utf-8-sig") as f:
        del_roadmap = {fila["PROCESS_ID"] for fila in csv.DictReader(f)}
    assert set(codigos) - del_roadmap == set(), "Procesos que no existen en la matriz del roadmap"


def test_ctl02_p07_sod_y_rep10_usan_la_misma_autoridad():
    """CTL-07 / REP-10: los adaptadores SoD etiquetan con el nombre de la autoridad de procesos."""
    from app.modules.government import procesos
    from app.modules.government.service_reporte_control import _etiqueta_proceso as etiqueta_rep10
    from app.modules.government.service_sod_eventos import PRODUCTORES, _etiqueta_proceso

    for adaptador in PRODUCTORES.values():
        if adaptador.proceso is not None:
            assert _etiqueta_proceso(adaptador.proceso, "") == procesos.nombre_de(adaptador.proceso)
            assert adaptador.proceso_etiqueta == procesos.nombre_de(adaptador.proceso)
    for codigo in ("BUD-08", "PROC-11", "TRE-09", "CTL-07"):
        assert etiqueta_rep10(codigo) == procesos.nombre_de(codigo)


# 13-14 · Aislamiento.


def test_ctl02_p08_aislamiento_de_empresa_y_tenant(mundo, gobierno):
    evento_b, _ = _emitir(mundo, "GOV_OFFICIAL_RATE_CREATED", "GovernmentOfficialExchangeRate", company=mundo.company_b)
    h_a = _auditor(mundo, "ctl02p_08_a")
    r = mundo.client.get(B, headers=h_a, params={"accion": "GOV_OFFICIAL_RATE_CREATED", "por_pagina": 50})
    assert evento_b not in [i["id"] for i in r.json()["items"]]
    assert mundo.client.get(f"{B}/{evento_b}", headers=h_a).status_code == 404
    r = mundo.client.get(f"{A}/eventos", headers=h_a, params={"proceso": "TRE-09", "por_pagina": 50})
    assert r.status_code == 200, r.text
    assert evento_b not in [i["id"] for i in r.json()["items"]]

    h_b = _auditor(mundo, "ctl02p_08_b", company=mundo.company_b)
    item = _item(mundo, h_b, evento_b, "GOV_OFFICIAL_RATE_CREATED")
    assert item["proceso"] == "TRE-09"


# 15-16 · Filtros (bitácora y CTL-04) y exportación.


def test_ctl02_p09_filtros_aceptan_todo_proceso_canonico(mundo, gobierno):
    from app.modules.government import procesos

    evento_id, _ = _emitir(mundo, "GOV_BUDGET_COMMITMENT_ISSUED", "GovernmentBudgetYear")
    h = _auditor(mundo, "ctl02p_09")
    f = mundo.client.get(f"{A}/filtros", headers=h).json()
    assert [p["codigo"] for p in f["procesos"]] == [p.codigo for p in procesos.PROCESOS]
    assert {a["proceso"] for a in f["acciones"]} >= {"BUD-08", "TRE-09", "CNT-01", "REP-10"}
    assert "" not in {a["proceso"] for a in f["acciones"]}

    # CTL-04: el filtro por proceso acepta BUD-08 (antes GOV_AUDIT_INVALID_FILTER).
    r = mundo.client.get(f"{A}/eventos", headers=h, params={"proceso": "BUD-08", "por_pagina": 50})
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    assert evento_id in [i["id"] for i in items]
    assert {i["proceso"] for i in items} == {"BUD-08"}
    r = mundo.client.get(f"{A}/eventos", headers=h, params={"proceso": "XYZ-99"})
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_AUDIT_INVALID_FILTER"

    bf = mundo.client.get(f"{B}/filtros", headers=h).json()
    assert "" not in {a["proceso"] for a in bf["acciones"]}


def test_ctl02_p10_exportacion_con_el_mismo_proceso_que_la_pantalla(mundo, gobierno):
    evento_id, request_id = _emitir(mundo, "GOV_CONTRACT_DRAFT_CREATED", "GovernmentProcurementFile")
    h = _auditor(mundo, "ctl02p_10", sample=True)
    cuerpo = {
        "titulo": "Muestra CNT-01",
        "criterio": "Contratos del período",
        "justificacion": "Verificar la clasificación del proceso",
        "metodo": "TODAS",
        "filtros": {"proceso": "CNT-01"},
        "semilla": None,
        "tamano": None,
        "eventos": None,
    }
    r = mundo.client.post(f"{A}/muestras", headers=h, json=cuerpo)
    assert r.status_code == 201, r.text
    muestra = r.json()
    assert {e["proceso"] for e in muestra["eventos"]} == {"CNT-01"}
    csv_r = mundo.client.get(f"{A}/muestras/{muestra['id']}/exportar", headers=h)
    assert csv_r.status_code == 200
    filas = list(csv.reader(io.StringIO(csv_r.text)))
    cabecera = next(i for i, fila in enumerate(filas) if fila and fila[0] == "orden")
    columnas = filas[cabecera]
    datos = [dict(zip(columnas, fila, strict=False)) for fila in filas[cabecera + 1 :] if fila]
    fila = next(d for d in datos if d["request_id"] == request_id)
    pantalla = _item(mundo, h, evento_id, "GOV_CONTRACT_DRAFT_CREATED")
    assert fila["proceso"] == pantalla["proceso"] == "CNT-01"


# 17-20 · Correlación, actor, autoridad y unidad se conservan.


def test_ctl02_p11_actor_autoridad_unidad_y_correlacion(mundo, gobierno, ocupacion):
    asig, cargo = titular_activo(mundo, ocupacion)
    oficial = asig["funcionario"]["id"]
    user_id = cuenta_con_permisos(mundo, "ctl02p_11", [("gobierno_ocupacion", "view")])
    vinculo_activo(mundo, cuerpo_vinculo(user_id, oficial))
    evento_id, request_id = _emitir(
        mundo, "GOV_OFFICIAL_RATE_APPROVED", "GovernmentOfficialExchangeRate", user_id=user_id
    )
    h = _auditor(mundo, "ctl02p_11_aud")
    r = mundo.client.get(B, headers=h, params={"request_id": request_id})
    assert r.status_code == 200
    (item,) = r.json()["items"]
    assert item["id"] == evento_id
    assert item["proceso"] == "TRE-09"
    assert item["usuario"] == "ctl02p_11"
    assert item["funcionario"]
    assert item["cargos"]
    assert item["unidades"]
    assert item["request_id"] == request_id
    d = mundo.client.get(f"{B}/{evento_id}", headers=h).json()
    assert d["contexto"]["funcionario"]["id"] == oficial
    assert d["contexto"]["ocupaciones"][0]["cargo_id"] == cargo
    unidad = d["contexto"]["ocupaciones"][0]["unidad_id"]
    r = mundo.client.get(B, headers=h, params={"unidad_id": unidad, "accion": "GOV_OFFICIAL_RATE_APPROVED"})
    assert evento_id in [i["id"] for i in r.json()["items"]]
