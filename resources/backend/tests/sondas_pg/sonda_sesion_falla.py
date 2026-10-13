"""Sonda que falla: escribe, confirma y revienta; el schema del módulo debe soltarse igual y no quedar nada."""
from sonda_sesion import escribir_y_confirmar, informar


def test_escribe_confirma_y_falla(sesion_de_prueba):
    informar(__name__, sesion_de_prueba, prueba=1)
    escribir_y_confirmar(sesion_de_prueba, "marcador-f")
    raise AssertionError("fallo deliberado de la sonda")


def test_despues_del_fallo_parte_de_cero(sesion_de_prueba):
    informar(__name__, sesion_de_prueba, prueba=2)
