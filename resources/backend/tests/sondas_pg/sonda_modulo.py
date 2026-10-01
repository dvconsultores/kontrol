"""Sonda: fixture de módulo, como `_mundo` y `_app_client`. Un schema para todas sus pruebas."""
import pytest
from conftest import make_engine
from sqlalchemy import text


@pytest.fixture(scope="module")
def motor():
    motor = make_engine()
    with motor.begin() as conn:
        conn.execute(text("create table sonda (n int)"))
    return motor


def test_escribe(motor):
    with motor.begin() as conn:
        conn.execute(text("insert into sonda values (1)"))


def test_lee_lo_que_escribio_la_anterior(motor):
    with motor.connect() as conn:
        assert conn.execute(text("select count(*) from sonda")).scalar_one() == 1
