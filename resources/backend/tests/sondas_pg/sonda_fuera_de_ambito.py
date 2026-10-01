"""Sonda: un motor creado al importar el módulo, fuera de toda fixture."""
from conftest import make_engine
from sqlalchemy import text

MOTOR = make_engine()


def test_usa_el_motor_del_modulo():
    with MOTOR.connect() as conn:
        assert conn.execute(text("select 1")).scalar_one() == 1
