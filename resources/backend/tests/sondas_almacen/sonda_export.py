"""Sonda de exportación: escribe una exportación con la marca de segundo que recibe (`KONTROL_SONDA_MARCA`)."""
import os

from informar import exportar_con_marca


def test_exporta_con_la_marca_recibida():
    exportar_con_marca(__name__, os.environ["KONTROL_SONDA_MARCA"])
