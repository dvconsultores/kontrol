"""Sonda A: un módulo que, como los mundos reales, escribe su clave de instalación en el volumen y la relee."""
import os

from informar import CLAVE, escenario, huella, informar


def test_escribe_su_clave(volumen_de_instalacion):
    escenario(__name__, volumen_de_instalacion)


def test_la_relee_y_sigue_siendo_la_suya(volumen_de_instalacion):
    informar(__name__ + ":relectura", huella=huella(os.path.join(volumen_de_instalacion, CLAVE)))
