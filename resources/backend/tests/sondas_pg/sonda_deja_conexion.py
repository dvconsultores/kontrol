"""Sonda: una prueba que abre una sesión y no la cierra nunca."""
import pytest
from conftest import make_engine
from sqlalchemy import text
from sqlalchemy.orm import Session

#: La sesión se guarda aquí para que nadie la recoja: la conexión sigue abierta al acabar la prueba.
OLVIDADAS: list[Session] = []


@pytest.fixture
def motor():
    return make_engine()


def test_deja_una_conexion_abierta(motor):
    sesion = Session(motor)
    sesion.execute(text("create table sonda (n int)"))
    OLVIDADAS.append(sesion)
