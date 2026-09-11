"""Invariante transversal: las fronteras entre Specs son semánticas.

> Las Specs son fronteras semánticas, no posiciones accidentales dentro de un
> archivo. Los architecture guards deben reconocer explícitamente al owner
> siguiente mediante un marcador estable de Spec, módulo o namespace, y nunca
> inferir la frontera por la siguiente función o clase.

Esto no es un requisito de negocio: es una invariante de los tests de
arquitectura. Se escribe porque el mismo defecto se repitió cinco veces en el
tramo 031→035 y la quinta llegó hasta la regresión completa
(`test_spec034_architecture.py::test_facturar_no_despacha`), acusando a la Spec
034 de absorber el despacho cuando lo único que había pasado es que la 035 puso
cuatro auxiliares legítimos delante de `create_shipment`.

Las pruebas de aquí no miran el producto: miran a los guardias.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from tests.spec_blocks import bloque_de_spec, cuerpo_de_ruta, cuerpo_de_simbolo

TESTS = Path(__file__).resolve().parent
RAIZ = TESTS.parent / "app"
TRAMO = ("031", "032", "033", "034", "035", "036")
GUARDIAS = [TESTS / f"test_spec{n}_architecture.py" for n in TRAMO]

#: Una fuente de mentira con la forma exacta del defecto: dos Specs seguidas y,
#: entre la cabecera de la segunda y su función pública, auxiliares suyos.
FUENTE = '''\
# --------------------------------------------------------------------------- #
# Spec 034 · liberación y facturación
# --------------------------------------------------------------------------- #
def request_billing():
    return "factura"


# --------------------------------------------------------------------------- #
# Spec 035 · despacho, transporte y regulación
# --------------------------------------------------------------------------- #
def _live_shipment():
    return "shipment vivo"


def _require_vehicle():
    return "vehiculo"


def create_shipment():
    return "shipment"
'''


def test_la_frontera_semantica_no_absorbe_los_auxiliares_del_dueno_siguiente():
    """El caso exacto que falló: helpers de la 035 antes de `create_shipment`."""
    b034 = bloque_de_spec(FUENTE, "034")
    for ajeno in ("_live_shipment", "_require_vehicle", "create_shipment", "shipment"):
        assert ajeno not in b034, f"la 034 absorbió {ajeno}"
    assert "request_billing" in b034, "la 034 perdió su propio código"

    b035 = bloque_de_spec(FUENTE, "035")
    for propio in ("_live_shipment", "_require_vehicle", "create_shipment"):
        assert propio in b035, f"la 035 perdió {propio}"
    assert "request_billing" not in b035, "la 035 absorbió la facturación"


def test_la_estrategia_posicional_anterior_si_habria_fallado():
    """Sin esta comprobación no se sabe que la nueva arregla algo.

    Es la mutación del arreglo: se reconstruye a mano el recorte viejo —«desde
    mi cabecera hasta `def create_shipment(`»— y se comprueba que sí se traga
    los auxiliares. Si algún día alguien vuelve a ese recorte, esta prueba
    documenta exactamente qué vuelve a romperse.
    """
    posicional = FUENTE[FUENTE.index("# Spec 034"):FUENTE.index("def create_shipment(")]
    assert "_live_shipment" in posicional, (
        "la reconstrucción del defecto ya no reproduce el defecto: revísala antes "
        "de fiarte de que la frontera nueva arregla algo")
    assert "_live_shipment" not in bloque_de_spec(FUENTE, "034")


def test_la_frontera_no_depende_del_nombre_ni_del_sitio_de_la_funcion_publica():
    """Renombrarla o moverla no puede ensanchar el bloque de la Spec anterior."""
    renombrada = FUENTE.replace("create_shipment", "registrar_salida_fisica")
    b034 = bloque_de_spec(renombrada, "034")
    assert "registrar_salida_fisica" not in b034 and "_live_shipment" not in b034

    # Y movida: la función pública pasa a ser la primera de su sección.
    movida = FUENTE.replace('''def _live_shipment():
    return "shipment vivo"


def _require_vehicle():
    return "vehiculo"


def create_shipment():
    return "shipment"
''', '''def create_shipment():
    return "shipment"


def _live_shipment():
    return "shipment vivo"
''')
    b034 = bloque_de_spec(movida, "034")
    assert "create_shipment" not in b034 and "_live_shipment" not in b034
    assert "create_shipment" in bloque_de_spec(movida, "035")


def test_sin_marcador_estable_el_guardia_se_niega_a_adivinar():
    """Si falta la cabecera, la frontera **no** se infiere: se falla y se dice."""
    sin_cabecera = FUENTE.replace("# Spec 035 · despacho, transporte y regulación",
                                  "# Despacho")
    with pytest.raises(AssertionError, match="marcador estable"):
        bloque_de_spec(sin_cabecera, "035")


# --------------------------------------------------------------------------- #
# La clase de defecto, no solo el caso
# --------------------------------------------------------------------------- #
#: Dos cosas prohibidas, y solo dos: recortar a mano el texto de un módulo, y
#: localizar una frontera por el símbolo siguiente. Comparar posiciones dentro de
#: un cuerpo ya extraído —«esto se comprueba antes que aquello»— es legítimo y no
#: entra aquí: no decide de quién es el código.
_FUENTES = "SALES|SALES_API|MODELOS|MODELS|INV|MIGRACION|CATALOGO|fuente"
_A_MANO = re.compile(
    rf"""\b(?:{_FUENTES})\s*\[
      | \.(?:index|find|split)\(\s*["'](?:def\ |class\ |@router)
    """, re.X)


@pytest.mark.parametrize("guardia", GUARDIAS, ids=[g.name for g in GUARDIAS])
def test_ningun_guardia_del_tramo_recorta_por_su_cuenta(guardia: Path):
    """La clase entera del defecto, no solo el caso que falló.

    Un guardia que llame a `.index(` sobre el código fuente está decidiendo una
    frontera a mano, y ahí es donde han nacido las cinco veces. Las tres formas
    legítimas de recortar viven en el helper compartido y ninguna depende del
    nombre de una función de implementación.
    """
    codigo = "\n".join(x for x in guardia.read_text().splitlines()
                       if not x.strip().startswith("#"))
    encontrado = _A_MANO.search(codigo)
    assert encontrado is None, (
        f"{guardia.name} delimita a mano («{encontrado.group(0) if encontrado else ''}»): "
        "usa bloque_de_spec / cuerpo_de_simbolo / cuerpo_de_ruta")


@pytest.mark.parametrize("spec", TRAMO)
def test_cada_spec_del_tramo_tiene_su_cabecera_en_servicio_y_api(spec: str):
    """Sin marcador no hay frontera, y sin frontera vuelve la adivinanza."""
    for modulo in ("service.py", "api.py"):
        fuente = (RAIZ / "modules" / "sales" / modulo).read_text()
        bloque = bloque_de_spec(fuente, spec)
        assert bloque.strip(), f"{modulo}: la Spec {spec} tiene cabecera pero no código"


def test_las_cabeceras_son_unicas_y_no_colisionan():
    """Dos cabeceras de la misma Spec harían la frontera ambigua."""
    for modulo in ("service.py", "api.py"):
        fuente = (RAIZ / "modules" / "sales" / modulo).read_text()
        for spec in TRAMO:
            n = len(re.findall(rf"^# Spec {spec} *[·—-] ", fuente, re.M))
            assert n == 1, f"{modulo}: la Spec {spec} tiene {n} cabeceras"


def test_las_tres_formas_de_recortar_hacen_lo_que_dicen():
    """El helper compartido, probado por sí mismo."""
    assert "request_billing" in cuerpo_de_simbolo(FUENTE, "def request_billing(")
    assert "create_shipment" not in cuerpo_de_simbolo(FUENTE, "def _live_shipment(")

    api = '''\
@router.get("/uno")
def uno():
    return 1


@router.get("/dos")
def dos():
    return 2
'''
    assert "return 1" in cuerpo_de_ruta(api, '@router.get("/uno")')
    assert "return 2" not in cuerpo_de_ruta(api, '@router.get("/uno")')
