"""Fronteras de propiedad entre Specs, para los guardias de arquitectura.

**Invariante transversal de arquitectura.** Las Specs son fronteras semánticas,
no posiciones accidentales dentro de un archivo. Un guardia que delimite el
código de una Spec debe reconocer explícitamente al dueño siguiente mediante un
marcador estable —cabecera de Spec, módulo o namespace— y nunca inferir la
frontera por la siguiente función o clase.

Esto no es una regla de estilo: es la corrección de un defecto que se repitió
cinco veces en el tramo 031→035. La última vez, el guardia de la Spec 034
delimitaba su bloque como «desde mi cabecera hasta `def create_shipment(`». Al
implementar la 035 se añadieron delante de esa función cuatro auxiliares
legítimos del despacho —`_live_shipment`, `_require_vehicle`, `_require_driver`
y `_lineas_consolidadas`— y el guardia los contó como código de la 034,
acusándola de haber absorbido el despacho. El código de negocio era correcto; la
frontera del test, no.

Aquí viven las tres formas de recortar que los guardias necesitan, y ninguna
depende del nombre de una función de implementación:

- `bloque_de_spec`   — todo el código de una Spec, entre cabeceras de sección.
- `cuerpo_de_simbolo` — el cuerpo de **una** función o clase concreta.
- `cuerpo_de_ruta`   — el cuerpo de **un** manejador de ruta concreto.

Las dos últimas sí terminan en el siguiente símbolo, y eso es correcto: el
cuerpo de una función acaba donde empieza la siguiente. Lo que está prohibido es
usar ese corte para decidir **de quién es** el código.
"""

from __future__ import annotations

import re

#: Una cabecera de sección: la línea de banda, el título y su explicación. El
#: fichero las escribe con guiones o con iguales; las dos valen.
_BANDA = re.compile(r"^# (?:-{10,}|={10,}) #$", re.M)

#: El título de una Spec dentro de una cabecera: «# Spec 034 · …» o «# Spec 030 — …».
#: El separador es parte del marcador: sin él, una línea de prosa que empiece por
#: «# Spec 032. Los permisos…» se leería como una cabecera y la frontera sería
#: ambigua justo donde tiene que ser exacta.
_TITULO_SPEC = re.compile(r"^# Spec (\d{3}) *[·—-] ", re.M)


def _secciones(fuente: str) -> list[tuple[int, int]]:
    """Los tramos entre bandas, en orden. Cada uno abarca su cabecera y su código."""
    inicios = [m.start() for m in _BANDA.finditer(fuente)]
    tramos: list[tuple[int, int]] = []
    for i, inicio in enumerate(inicios):
        # La banda de cierre de una cabecera no abre sección: se reconoce porque
        # entre ella y la anterior solo hay comentarios.
        anterior = tramos[-1] if tramos else None
        if anterior and _solo_comentarios(fuente[anterior[0]:inicio]):
            tramos[-1] = (anterior[0], inicios[i + 1] if i + 1 < len(inicios) else len(fuente))
            continue
        tramos.append((inicio, inicios[i + 1] if i + 1 < len(inicios) else len(fuente)))
    return tramos


def _solo_comentarios(texto: str) -> bool:
    return all(not x.strip() or x.strip().startswith("#") for x in texto.splitlines())


def bloque_de_spec(fuente: str, spec: str) -> str:
    """El código que pertenece a una Spec, delimitado por marcadores semánticos.

    Empieza en la cabecera de esa Spec y termina donde empieza la sección
    siguiente, sea de otra Spec o no. No mira ninguna `def` ni ninguna `class`,
    así que añadir, mover o renombrar funciones dentro de una sección no cambia
    de quién es el código.
    """
    for inicio, fin in _secciones(fuente):
        m = _TITULO_SPEC.search(fuente, inicio, fin)
        if m and m.group(1) == spec and m.start() < fuente.find("\n", inicio) + 4000:
            return fuente[inicio:fin]
    raise AssertionError(
        f"no hay cabecera de sección para la Spec {spec}: la frontera tiene que "
        "ser un marcador estable, no la siguiente función")


def cuerpo_de_simbolo(fuente: str, inicio: str) -> str:
    """El cuerpo de **una** función o clase, sin docstring ni comentarios.

    Un guardia que mirase el texto entero fallaría por la explicación de lo que
    prohíbe, que es justo donde esos nombres tienen que aparecer.
    """
    pos = fuente.index(inicio)
    resto = fuente[pos:]
    siguiente = min((x for x in (resto.find("\ndef ", 1), resto.find("\nclass ", 1)) if x > 0),
                    default=-1)
    return _limpio(resto if siguiente < 0 else resto[:siguiente])


def cuerpo_de_ruta(fuente: str, decorador: str) -> str:
    """El cuerpo de **un** manejador de ruta, hasta el decorador siguiente."""
    pos = fuente.index(decorador)
    resto = fuente[pos:]
    siguiente = resto.find("\n@router.", 1)
    return _limpio(resto if siguiente < 0 else resto[:siguiente])


def _limpio(texto: str) -> str:
    sin_doc = re.sub(r'"""..*?"""', "", texto, flags=re.S)
    return "\n".join(x for x in sin_doc.splitlines() if not x.strip().startswith("#"))


def limpio(texto: str) -> str:
    """Público: el mismo saneado, para guardias que recortan por su cuenta."""
    return _limpio(texto)
