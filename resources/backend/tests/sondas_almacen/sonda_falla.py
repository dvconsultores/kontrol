"""Sonda que falla a propósito después de escribir: la raíz del proceso debe desaparecer igual."""
from informar import escenario


def test_escribe_y_falla():
    escenario(__name__)
    raise AssertionError("fallo deliberado de la sonda")
