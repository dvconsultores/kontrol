"""Sonda: fixture por prueba, como las trece suites `db_session`. Todo pasa.

Cada prueba comprueba además que su schema es el único de este proceso que existe: el de la
prueba anterior ya se soltó, no se quedó esperando al final del módulo.
"""
import os

import pytest
from conftest import make_engine
from sqlalchemy import text


@pytest.fixture
def motor():
    return make_engine()


@pytest.mark.parametrize("n", [1, 2, 3])
def test_usa_su_propio_schema(motor, n):
    with motor.begin() as conn:
        conn.execute(text("create table sonda (n int)"))
        conn.execute(text("insert into sonda values (:n)"), {"n": n})
        assert conn.execute(text("select count(*) from sonda")).scalar_one() == 1
    if os.environ.get("KONTROL_TEST_DB_URL"):
        from contar import schemas_vivos_de_este_proceso

        assert schemas_vivos_de_este_proceso() == 1
