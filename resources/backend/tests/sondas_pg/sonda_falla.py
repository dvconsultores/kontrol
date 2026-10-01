"""Sonda: una prueba que falla, una fixture que revienta después de crear su motor, y una que pasa."""
import pytest
from conftest import make_engine
from sqlalchemy import text


@pytest.fixture
def motor():
    return make_engine()


@pytest.fixture
def motor_que_revienta():
    make_engine()
    raise RuntimeError("la fixture falla después de crear el motor")


def test_falla_a_proposito(motor):
    with motor.begin() as conn:
        conn.execute(text("create table sonda (n int)"))
    raise AssertionError("fallo deliberado de la sonda")


def test_su_fixture_revienta(motor_que_revienta):
    raise AssertionError("no debe llegar a ejecutarse")


def test_pasa(motor):
    with motor.connect() as conn:
        assert conn.execute(text("select 1")).scalar_one() == 1
