"""Sonda: se ejecuta después de `sonda_modulo.py` en la misma corrida.

Si el schema del módulo anterior siguiera vivo, aquí se verían dos: el suyo y el de esta prueba.
"""
import pytest
from conftest import make_engine
from contar import schemas_vivos_de_este_proceso


@pytest.fixture
def motor():
    return make_engine()


def test_el_schema_del_modulo_anterior_ya_no_existe(motor):
    assert schemas_vivos_de_este_proceso() == 1
