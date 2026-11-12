import os
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.modules.audit.models import AuditEvent
from app.modules.government.models import GovernmentCorrectiveAction
from app.modules.identity_access.models import User
from app.shared.audit import record_audit
from app.shared.clock import hoy_de_negocio
from tests.n9_resource_seeds import sembrar
from tests.org06_guarda import cuenta_con_permisos

pytestmark = pytest.mark.skipif(
    not os.environ.get("KONTROL_TEST_DB_URL", "").startswith("postgresql"),
    reason="Requiere PostgreSQL",
)
pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos")
R = "/gobierno/control-interno/reporte"


def _uid(db, username: str) -> str:
    return str(db.execute(select(User).where(User.username == username)).scalar_one().id)


def _sembrar_sod(mundo, codigo: str, proceso: str = "DOC-02") -> str:
    with mundo.factory() as db:
        uid = _uid(db, "ua")
        objeto_id = str(uuid4())
        record_audit(
            db,
            action="GOV_SOD_CONFLICT_BLOCKED",
            entity_type="GovernmentSoDRule",
            entity_id=str(uuid4()),
            tenant_id=mundo.t1,
            company_id=mundo.company_a,
            user_id=uid,
            after={
                "regla_codigo": codigo,
                "regla_version": 1,
                "proceso": proceso,
                "accion": "DOC02_EDITAR",
                "accion_previa": "DOC02_REGISTRAR",
                "objeto_tipo": "GovernmentAct",
                "objeto_id": objeto_id,
                "evento_previo_id": None,
            },
        )
        db.commit()
        return objeto_id


def _sembrar_identidad(mundo) -> None:
    with mundo.factory() as db:
        uid = _uid(db, "ua")
        record_audit(
            db,
            action="GOV_IDENTITY_GUARD_BLOCKED",
            entity_type="GovernmentIdentityPolicy",
            entity_id=str(uuid4()),
            tenant_id=mundo.t1,
            company_id=mundo.company_a,
            user_id=uid,
            after={"operacion": "GOV_IDENTITY_LINK_REQUIRED", "accion": "x"},
        )
        db.commit()


def _sembrar_cierre(mundo) -> None:
    with mundo.factory() as db:
        uid = _uid(db, "ua")
        record_audit(
            db,
            action="GOV_MATERIAL_CLOSE_BLOCKED",
            entity_type="GovernmentClosurePolicy",
            entity_id=str(uuid4()),
            tenant_id=mundo.t1,
            company_id=mundo.company_a,
            user_id=uid,
            after={
                "politica_codigo": "PC-1",
                "politica_version": 1,
                "accion_cierre": "ORG02_CERRAR_ESTRUCTURA",
                "objeto_tipo": "GovernmentStructure",
                "objeto_id": str(uuid4()),
                "objeto_codigo": "E-1",
                "ejercicio": 2026,
                "controles": [{"tipo": "HALLAZGOS_ABIERTOS", "pendientes": 2}],
                "total": 2,
            },
        )
        db.commit()


def _sembrar_accion_vencida(mundo) -> str:
    with mundo.factory() as db:
        aid = sembrar(db, "GovernmentCorrectiveAction", mundo.company_a, uuid4().hex)
        db.commit()
        a = db.get(GovernmentCorrectiveAction, aid)
        a.fecha_objetivo = hoy_de_negocio() - timedelta(days=3)
        db.commit()
        return str(a.finding_id)


def test_rp01_estructura_y_periodo_por_defecto(mundo, gobierno):
    hoy = hoy_de_negocio()
    resp = mundo.get(R, "ua", mundo.company_a)
    assert resp.status_code == 200
    data = resp.json()
    assert data["periodo"]["desde"] == f"{hoy.year}-01-01"
    assert data["periodo"]["hasta"] == hoy.isoformat()
    assert data["overrides"]["disponible"] is False
    assert (
        data["overrides"]["motivo"]
        == "No aplica: en Gobierno los controles de segregación de funciones solo bloquean; no existe excepción ni dispensa (CTL-01)."
    )
    assert data["operaciones_duplicadas"]["disponible"] is False
    assert (
        data["operaciones_duplicadas"]["motivo"]
        == "No disponible: requiere órdenes de pago y pagos (TRE-03, TRE-04), que aún no existen en Gobierno."
    )


def test_rp02_sod_sembrado_y_periodo_antiguo(mundo, gobierno):
    codigo = f"REG-{uuid4().hex[:8]}"
    _sembrar_sod(mundo, codigo)
    hoy = hoy_de_negocio()
    resp = mundo.get(R, "ua", mundo.company_a)
    assert resp.status_code == 200
    data = resp.json()
    eventos = data["conflictos_sod"]["eventos"]
    encontrados = [e for e in eventos if e["regla_codigo"] == codigo]
    assert encontrados
    ev = encontrados[0]
    assert ev["regla_nombre"] == codigo
    assert ev["accion_etiqueta"] == "Editar el borrador del acto"
    assert ev["usuario"] == "ua"
    reglas = [r for r in data["conflictos_sod"]["por_regla"] if r["regla_codigo"] == codigo]
    assert reglas and reglas[0]["proceso"] == "DOC-02"

    antiguo = (hoy - timedelta(days=400)).isoformat()
    resp_ant = mundo.get(f"{R}?desde={antiguo}&hasta={antiguo}", "ua", mundo.company_a)
    assert resp_ant.status_code == 200
    assert resp_ant.json()["conflictos_sod"]["total"] == 0


def test_rp03_total_real_mayor_50(mundo, gobierno):
    codigo = f"REG-{uuid4().hex[:8]}"
    for _ in range(51):
        _sembrar_sod(mundo, codigo)
    resp = mundo.get(R, "ua", mundo.company_a)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["conflictos_sod"]["eventos"]) == 50
    regla = next(r for r in data["conflictos_sod"]["por_regla"] if r["regla_codigo"] == codigo)
    assert regla["total"] == 51


def test_rp04_identidad_y_cierre(mundo, gobierno):
    _sembrar_identidad(mundo)
    _sembrar_cierre(mundo)
    resp = mundo.get(R, "ua", mundo.company_a)
    assert resp.status_code == 200
    data = resp.json()

    identidad = data["bloqueos_identidad"]["eventos"]
    assert any(
        e["etiqueta"] == "Su cuenta no tiene un vínculo institucional vigente en este ente"
        for e in identidad
    )

    cierre = data["bloqueos_cierre"]["eventos"]
    assert any(e["politica_codigo"] == "PC-1" and e["accion_etiqueta"] == "Cerrar estructura" for e in cierre)
    evento_cierre = next(e for e in cierre if e["politica_codigo"] == "PC-1")
    assert evento_cierre["controles"][0]["etiqueta"] == "Hallazgos abiertos"


def test_rp05_accion_vencida(mundo, gobierno):
    hallazgo_id = _sembrar_accion_vencida(mundo)
    resp = mundo.get(R, "ua", mundo.company_a)
    assert resp.status_code == 200
    data = resp.json()
    vencidas = data["hallazgos"]["acciones_vencidas"]
    assert any(a["hallazgo_id"] == hallazgo_id and a["dias_atraso"] == 3 for a in vencidas)
    assert set(data["hallazgos"]["acciones_por_estado"].keys()) == {"PENDIENTE", "EN_CURSO", "COMPLETADA"}


def test_rp06_permisos(mundo, gobierno):
    nombre_solo_auditoria = f"uaud-{uuid4().hex[:8]}"
    cuenta_con_permisos(mundo, nombre_solo_auditoria, [("gobierno_auditoria", "view")])
    resp = mundo.get(R, nombre_solo_auditoria, mundo.company_a)
    assert resp.status_code == 200
    data = resp.json()
    assert data["hallazgos"]["disponible"] is False
    assert data["hallazgos"]["acciones_vencidas"] == []

    nombre_solo_hallazgos = f"uhall-{uuid4().hex[:8]}"
    cuenta_con_permisos(mundo, nombre_solo_hallazgos, [("gobierno_hallazgos", "view")])
    resp_hall = mundo.get(R, nombre_solo_hallazgos, mundo.company_a)
    assert resp_hall.status_code == 403


def test_rp07_aislamiento(mundo, gobierno):
    codigo = f"REG-{uuid4().hex[:8]}"
    _sembrar_sod(mundo, codigo)
    hallazgo_id = _sembrar_accion_vencida(mundo)
    resp = mundo.get(R, "ub", mundo.company_b)
    assert resp.status_code == 200
    data = resp.json()
    assert all(e["regla_codigo"] != codigo for e in data["conflictos_sod"]["eventos"])
    assert all(a["hallazgo_id"] != hallazgo_id for a in data["hallazgos"]["acciones_vencidas"])


def test_rp08_csv(mundo, gobierno):
    codigo = f"REG-{uuid4().hex[:8]}"
    _sembrar_sod(mundo, codigo)
    _sembrar_accion_vencida(mundo)
    resp = mundo.get(f"{R}.csv", "ua", mundo.company_a)
    assert resp.status_code == 200
    assert resp.headers["Content-Type"].startswith("text/csv")
    texto = resp.text
    assert "Conflicto SoD" in texto
    assert "Acción intentada" in texto
    assert "Días de atraso" in texto

    with mundo.factory() as db:
        evento = db.execute(
            select(AuditEvent).where(
                AuditEvent.action == "GOV_INTERNAL_CONTROL_REPORT_EXPORTED",
                AuditEvent.company_id == mundo.company_a,
            )
        ).scalars().first()
        assert evento is not None
        assert evento.after["filas"] >= 1
        assert set(evento.after["filtros"].keys()) == {"desde", "hasta"}


def test_rp09_desde_mayor_hasta(mundo, gobierno):
    hoy = hoy_de_negocio()
    desde = hoy.isoformat()
    hasta = (hoy - timedelta(days=1)).isoformat()
    resp = mundo.get(f"{R}?desde={desde}&hasta={hasta}", "ua", mundo.company_a)
    assert resp.status_code == 422
    assert resp.json()["code"] == "INVALID_DATE_RANGE"


def test_rp10_recientes_primeros_50(mundo, gobierno):
    codigo = f"REG-{uuid4().hex[:8]}"
    primer_objeto_id: str | None = None
    for i in range(51):
        objeto_id = _sembrar_sod(mundo, codigo)
        if i == 0:
            primer_objeto_id = objeto_id
    assert primer_objeto_id is not None

    with mundo.factory() as db:
        eventos = db.execute(
            select(AuditEvent).where(
                AuditEvent.action == "GOV_SOD_CONFLICT_BLOCKED",
                AuditEvent.company_id == mundo.company_a,
            )
        ).scalars().all()
        primer_evento = next(
            e for e in eventos
            if (e.after or {}).get("objeto_id") == primer_objeto_id
        )
        assert primer_evento is not None
        primer_evento_id = str(primer_evento.id)

    resp = mundo.get(R, "ua", mundo.company_a)
    assert resp.status_code == 200
    data = resp.json()
    regla = next(r for r in data["conflictos_sod"]["por_regla"] if r["regla_codigo"] == codigo)
    assert regla["total"] == 51
    assert len(data["conflictos_sod"]["eventos"]) == 50
    assert all(e["evento_id"] != primer_evento_id for e in data["conflictos_sod"]["eventos"])
