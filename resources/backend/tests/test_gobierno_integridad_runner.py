import importlib.util
import os
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text

pytest_plugins = ("tests.conftest_multicompany",)

pytestmark = pytest.mark.skipif(
    not os.environ.get("KONTROL_TEST_DB_URL", "").startswith("postgresql"),
    reason="gobierno_integridad runner requiere PostgreSQL",
)

RUNNER_PATH = Path(__file__).resolve().parents[3] / "qa" / "gobierno_integridad.py"

spec = importlib.util.spec_from_file_location("gobierno_integridad", RUNNER_PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

IDS_ESPERADOS = {
    *[f"C{i}" for i in range(1, 21)],
    *[f"M{i}" for i in range(1, 9)],
    *[f"H{i}" for i in range(1, 14)],
    *[f"P{i}" for i in range(1, 9)],
    *[f"S{i}" for i in range(1, 10)],
    *[f"T{i}" for i in range(1, 18)],
    *[f"K{i}" for i in range(1, 13)],
    *[f"CC{i}" for i in range(1, 10)],
    *[f"OC{i}" for i in range(1, 23)],
    *[f"ID{i}" for i in range(1, 19)],
}


def test_controles_tienen_ids_unicos_y_grupos_exactos():
    controles = mod.controles()

    ids = [control[1] for control in controles]
    assert len(ids) == 136
    assert len(ids) == len(set(ids))
    assert set(ids) == IDS_ESPERADOS

    grupos = {control[0] for control in controles}
    assert grupos == {
        "ORG-02/ORG-03/ORG-07",
        "CTL-04/CTL-06/DOC-08/CTL-01",
        "TRE-01",
        "TRE-02",
        "CTL-10",
        "ORG-04",
        "ORG-06",
    }


def test_ejecutar_controles_sin_errores_contra_esquema_real(mundo):
    db = mundo.factory()
    try:
        conn = db.connection()
        resultado = mod.ejecutar(conn)
        controles = resultado["controles"]

        assert resultado["info"], "sin recuentos informativos"
        assert all(isinstance(valor, int) for valor in resultado["info"].values())
        assert len(controles) == 136
        for control in controles:
            assert control["error"] is None, f"{control['id']}: {control['error']}"
            assert isinstance(control["violaciones"], int)
            assert control["violaciones"] >= 0
    finally:
        db.rollback()
        db.close()


def _violacion_control(conn, controles, control_id):
    sql = next(control[3] for control in controles if control[1] == control_id)
    return conn.execute(text(sql)).scalar_one()


def test_controles_detectan_violaciones_sod_y_muestra_sin_historia_ni_auditoria(mundo):
    db = mundo.factory()
    conn = db.connection()
    controles = mod.controles()
    tenant_id = mundo.t1
    company_id = mundo.company_a

    try:
        antes = {
            control_id: _violacion_control(conn, controles, control_id)
            for control_id in ("S4", "S5", "M4", "M7")
        }

        conn.execute(
            text(
                """
                INSERT INTO gov_sod_rules (
                    id, tenant_id, company_id, codigo, nombre, descripcion, proceso,
                    accion_a, accion_b, bidireccional, alcance, modo, vigente_desde,
                    estado, version, created_at, updated_at
                ) VALUES (
                    :id, :tenant_id, :company_id, 'SOD-2099-9999', 'Regla sintética',
                    'Regla sintética de control', 'CTL-06', 'CTL06_REGISTRAR',
                    'CTL06_RECOMENDAR', false, 'MISMO_OBJETO', 'BLOQUEAR', CURRENT_DATE,
                    'BORRADOR', 1, now(), now()
                )
                """
            ),
            {
                "id": str(uuid4()),
                "tenant_id": tenant_id,
                "company_id": company_id,
            },
        )

        conn.execute(
            text(
                """
                INSERT INTO gov_audit_samples (
                    id, tenant_id, company_id, codigo, titulo, criterio, justificacion,
                    metodo, semilla, tamano, poblacion, filtros, created_at, updated_at
                ) VALUES (
                    :id, :tenant_id, :company_id, 'MU-2099-9999', 'Muestra sintética',
                    'criterio', 'justificación', 'TODAS', NULL, 1, 1, '{}', now(), now()
                )
                """
            ),
            {
                "id": str(uuid4()),
                "tenant_id": tenant_id,
                "company_id": company_id,
            },
        )

        despues = {
            control_id: _violacion_control(conn, controles, control_id)
            for control_id in ("S4", "S5", "M4", "M7")
        }

        for control_id in ("S4", "S5", "M4", "M7"):
            assert despues[control_id] == antes[control_id] + 1, control_id
    finally:
        db.rollback()
        db.close()
