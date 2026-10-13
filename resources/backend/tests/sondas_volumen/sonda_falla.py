"""Sonda que falla: escribe su clave y después revienta a propósito; el volumen debe desaparecer igual."""
from informar import escenario


def test_escribe_su_clave_y_falla(volumen_de_instalacion):
    escenario(__name__, volumen_de_instalacion)
    raise AssertionError("fallo deliberado de la sonda")
