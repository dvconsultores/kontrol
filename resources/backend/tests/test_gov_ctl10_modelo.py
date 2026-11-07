import os
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from alembic.config import Config
from alembic.script import ScriptDirectory
from app.modules.government.models import (
    GovernmentClosureControl,
    GovernmentClosurePolicy,
    GovernmentClosurePolicyHistory,
)
from app.modules.identity_access.mfa_policy import SENSITIVE, STANDARD, classify
from app.modules.setup.api import CATALOGO_DE_PERMISOS
from tests.ctl10_ayudantes import (
    anadir_control,
    crear_politica,
    politica_vigente,
    politicas_limpias,  # noqa: F401
)

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos")

ACCION = "ORG02_CERRAR_ESTRUCTURA"
ACCION_ALT = "TRE02_CERRAR_PROGRAMA"
HALLAZGOS = "HALLAZGOS_ABIERTOS"
ACTOS = "ACTOS_SIN_EFICACIA"


def test_pm01_cabeza_migracion():
    """pm01: la cabeza de Alembic contiene la migración 0075_gov_ctl10_cierres."""
    raiz = Path(__file__).resolve().parents[1]
    configuracion = Config(str(raiz / "alembic.ini"))
    configuracion.set_main_option("script_location", str(raiz / "alembic"))
    script = ScriptDirectory.from_config(configuracion)
    cabeza = script.get_current_head()
    assert cabeza is not None
    assert "0075_gov_ctl10_cierres" in cabeza


def test_pm02_catalogo_permisos():
    """pm02: el catálogo expone gobierno_cierre y clasifica activate como sensible."""
    permisos = CATALOGO_DE_PERMISOS["gobierno_cierre"]
    assert permisos == ["view", "manage", "activate"]
    assert classify(["gobierno_cierre:activate"]) == SENSITIVE
    assert classify(["gobierno_cierre:view"]) == STANDARD
    assert classify(["gobierno_cierre:manage"]) == STANDARD


def test_pm03_columnas_modelo():
    """pm03: las clases ORM declaran las columnas del modelo de cierres."""
    columnas_politica = set(GovernmentClosurePolicy.__table__.columns.keys())
    for columna in (
        "tenant_id",
        "company_id",
        "codigo",
        "nombre",
        "accion_cierre",
        "fundamento",
        "estado",
        "vigente_desde",
        "vigente_hasta",
        "activada_por",
        "activada_en",
        "retirada_por",
        "retirada_en",
        "motivo_retiro",
        "version",
        "created_by",
    ):
        assert columna in columnas_politica, columna

    columnas_control = set(GovernmentClosureControl.__table__.columns.keys())
    for columna in ("tenant_id", "company_id", "policy_id", "tipo", "riesgo_minimo", "materialidad"):
        assert columna in columnas_control, columna

    columnas_historia = set(GovernmentClosurePolicyHistory.__table__.columns.keys())
    for columna in ("tenant_id", "company_id", "policy_id", "evento", "detalle", "usuario", "instante"):
        assert columna in columnas_historia, columna


def _requiere_postgresql():
    if not os.environ.get("KONTROL_TEST_DB_URL", "").startswith("postgresql"):
        pytest.skip("solo PostgreSQL")


def _controles_por_tipo(mundo, policy_id):
    with mundo.factory() as db:
        filas = db.execute(
            text(
                "SELECT id, tipo FROM gov_closure_controls WHERE policy_id = :id"
            ),
            {"id": policy_id},
        ).all()
    return {fila.tipo: fila.id for fila in filas}


def test_pm04_riesgo_minimo_nulo_hallazgos(mundo, gobierno):
    """pm04: HALLAZGOS_ABIERTOS no admite riesgo_minimo nulo."""
    _requiere_postgresql()
    politica = crear_politica(mundo, accion_cierre=ACCION_ALT)
    politica = anadir_control(mundo, politica, HALLAZGOS, riesgo_minimo="ALTO")
    controles = _controles_por_tipo(mundo, politica["id"])
    control_id = controles[HALLAZGOS]
    with mundo.factory() as db, pytest.raises(DBAPIError):
        db.execute(
            text("UPDATE gov_closure_controls SET riesgo_minimo = NULL WHERE id = :id"),
            {"id": control_id},
        )
        db.flush()


def test_pm05_riesgo_minimo_no_nulo_actos(mundo, gobierno):
    """pm05: ACTOS_SIN_EFICACIA no admite riesgo_minimo no nulo."""
    _requiere_postgresql()
    politica = crear_politica(mundo, accion_cierre=ACCION_ALT)
    politica = anadir_control(mundo, politica, ACTOS)
    controles = _controles_por_tipo(mundo, politica["id"])
    control_id = controles[ACTOS]
    with mundo.factory() as db, pytest.raises(DBAPIError):
        db.execute(
            text("UPDATE gov_closure_controls SET riesgo_minimo = 'ALTO' WHERE id = :id"),
            {"id": control_id},
        )
        db.flush()


def test_pm06_tipo_invalido_rechazado(mundo, gobierno):
    """pm06: el tipo de control sólo admite los valores del modelo."""
    _requiere_postgresql()
    politica = crear_politica(mundo, accion_cierre=ACCION_ALT)
    politica = anadir_control(mundo, politica, ACTOS)
    controles = _controles_por_tipo(mundo, politica["id"])
    control_id = controles[ACTOS]
    with mundo.factory() as db, pytest.raises(DBAPIError):
        db.execute(
            text("UPDATE gov_closure_controls SET tipo = 'OTRO' WHERE id = :id"),
            {"id": control_id},
        )
        db.flush()


def test_pm07_segunda_vigente_rechazada(mundo, gobierno):
    """pm07: sólo puede haber una política VIGENTE por acción de cierre."""
    _requiere_postgresql()
    politica_vigente(mundo, ACCION_ALT, HALLAZGOS, riesgo_minimo="ALTO")
    otra = crear_politica(mundo, accion_cierre=ACCION_ALT)
    with mundo.factory() as db, pytest.raises(DBAPIError):
        db.execute(
            text("UPDATE gov_closure_policies SET estado = 'VIGENTE' WHERE id = :id"),
            {"id": otra["id"]},
        )
        db.flush()


def test_pm08_vigente_hasta_anterior_rechazada(mundo, gobierno):
    """pm08: vigente_hasta no puede ser anterior a vigente_desde."""
    _requiere_postgresql()
    politica = crear_politica(mundo, accion_cierre=ACCION_ALT)
    with mundo.factory() as db, pytest.raises(DBAPIError):
        db.execute(
            text(
                "UPDATE gov_closure_policies "
                "SET vigente_hasta = vigente_desde - INTERVAL '1 day' WHERE id = :id"
            ),
            {"id": politica["id"]},
        )
        db.flush()


def test_pm09_materialidad_vigente_rechazada(mundo, gobierno):
    """pm09: no se puede cambiar la materialidad de un control de política VIGENTE."""
    _requiere_postgresql()
    vigente = politica_vigente(mundo, ACCION_ALT, HALLAZGOS, riesgo_minimo="ALTO")
    controles = _controles_por_tipo(mundo, vigente["id"])
    control_id = controles[HALLAZGOS]
    with mundo.factory() as db, pytest.raises(DBAPIError):
        db.execute(
            text("UPDATE gov_closure_controls SET materialidad = materialidad || ' extra' WHERE id = :id"),
            {"id": control_id},
        )


def test_pm10_delete_control_vigente_rechazado(mundo, gobierno):
    """pm10: no se puede borrar un control de política VIGENTE."""
    _requiere_postgresql()
    vigente = politica_vigente(mundo, ACCION_ALT, HALLAZGOS, riesgo_minimo="ALTO")
    controles = _controles_por_tipo(mundo, vigente["id"])
    control_id = controles[HALLAZGOS]
    with mundo.factory() as db, pytest.raises(DBAPIError):
        db.execute(
            text("DELETE FROM gov_closure_controls WHERE id = :id"),
            {"id": control_id},
        )


def test_pm11_delete_politica_vigente_rechazado(mundo, gobierno):
    """pm11: no se puede borrar una política VIGENTE."""
    _requiere_postgresql()
    vigente = politica_vigente(mundo, ACCION_ALT, HALLAZGOS, riesgo_minimo="ALTO")
    with mundo.factory() as db, pytest.raises(DBAPIError):
        db.execute(
            text("DELETE FROM gov_closure_policies WHERE id = :id"),
            {"id": vigente["id"]},
        )


def test_pm12_fundamento_vigente_rechazado(mundo, gobierno):
    """pm12: no se puede cambiar el fundamento de una política VIGENTE."""
    _requiere_postgresql()
    vigente = politica_vigente(mundo, ACCION_ALT, HALLAZGOS, riesgo_minimo="ALTO")
    with mundo.factory() as db, pytest.raises(DBAPIError):
        db.execute(
            text("UPDATE gov_closure_policies SET fundamento = fundamento || ' extra' WHERE id = :id"),
            {"id": vigente["id"]},
        )


def test_pm13_historia_inmutable(mundo, gobierno):
    """pm13: la historia de políticas es inmutable."""
    _requiere_postgresql()
    politica = crear_politica(mundo, accion_cierre=ACCION_ALT)
    with mundo.factory() as db:
        historia_id = db.scalar(
            text(
                "SELECT id FROM gov_closure_policy_history WHERE policy_id = :id LIMIT 1"
            ),
            {"id": politica["id"]},
        )
    assert historia_id is not None

    with mundo.factory() as db, pytest.raises(DBAPIError):
        db.execute(
            text("UPDATE gov_closure_policy_history SET evento = 'ACTUALIZADA' WHERE id = :id"),
            {"id": historia_id},
        )
        db.flush()

    with mundo.factory() as db, pytest.raises(DBAPIError):
        db.execute(
            text("DELETE FROM gov_closure_policy_history WHERE id = :id"),
            {"id": historia_id},
        )
        db.flush()


def test_pm14_materialidad_borrador_aceptada(mundo, gobierno):
    """pm14: en BORRADOR la materialidad del control puede actualizarse."""
    _requiere_postgresql()
    politica = crear_politica(mundo, accion_cierre=ACCION_ALT)
    politica = anadir_control(mundo, politica, HALLAZGOS, riesgo_minimo="ALTO")
    controles = _controles_por_tipo(mundo, politica["id"])
    control_id = controles[HALLAZGOS]
    with mundo.factory() as db:
        db.execute(
            text("UPDATE gov_closure_controls SET materialidad = materialidad || ' extra' WHERE id = :id"),
            {"id": control_id},
        )
        db.flush()
        db.commit()
