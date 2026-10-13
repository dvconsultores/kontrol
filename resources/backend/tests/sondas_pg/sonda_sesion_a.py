"""Sonda A: dos pruebas sobre `sesion_de_prueba`; la primera escribe y confirma, la segunda debe partir de cero."""
from sonda_sesion import escribir_y_confirmar, informar


def test_1_escribe_y_confirma(sesion_de_prueba):
    informar(__name__, sesion_de_prueba, prueba=1)
    escribir_y_confirmar(sesion_de_prueba, "marcador-a1")


def test_2_parte_de_cero(sesion_de_prueba):
    informar(__name__, sesion_de_prueba, prueba=2)
    escribir_y_confirmar(sesion_de_prueba, "marcador-a2")
