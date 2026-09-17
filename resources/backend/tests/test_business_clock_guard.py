"""Guarda de la fecha de negocio (Spec 001 · POLICY-CLOCK-LOCAL).

No prohíbe `date.today()` en el repositorio: hay sitios donde leer el día civil del
proceso es correcto —un guion de mantenimiento, una prueba que documenta su propio
reloj—. Lo prohíbe **en la lógica de negocio del backend**, que es donde preguntarlo
significaba operar en el día equivocado durante cuatro horas diarias.

Se mira el árbol sintáctico, no el texto: así no la engaña un comentario ni la rompe
un cambio de formato.
"""

from __future__ import annotations

import ast
import pathlib

#: Dónde vive la lógica de negocio que no puede leer el reloj del proceso.
AMBITO = ("app/modules", "app/core", "app/shared")

#: Excepciones justificadas. Vacía a propósito: si alguna vez hace falta una, que se
#: escriba aquí con su motivo y quede a la vista de la siguiente persona.
PERMITIDOS: dict[str, str] = {}

RAIZ = pathlib.Path(__file__).resolve().parents[1]

#: Lo que se persigue: el día civil del proceso, por cualquiera de sus nombres.
LECTURAS_LOCALES = {
    ("date", "today"),
    ("datetime", "today"),
    ("datetime", "utcnow"),
}


def _lecturas(fichero: pathlib.Path) -> list[tuple[int, str]]:
    arbol = ast.parse(fichero.read_text(encoding="utf-8"), filename=str(fichero))
    encontradas: list[tuple[int, str]] = []
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.Call) or not isinstance(nodo.func, ast.Attribute):
            continue
        objeto = nodo.func.value
        if isinstance(objeto, ast.Name) and (objeto.id, nodo.func.attr) in LECTURAS_LOCALES:
            encontradas.append((nodo.lineno, f"{objeto.id}.{nodo.func.attr}()"))
        # `datetime.now()` sin argumentos es hora local; con `UTC` es un instante.
        if (isinstance(objeto, ast.Name) and objeto.id == "datetime"
                and nodo.func.attr == "now" and not nodo.args and not nodo.keywords):
            encontradas.append((nodo.lineno, "datetime.now() sin zona"))
    return encontradas


def test_la_logica_de_negocio_no_lee_el_reloj_del_proceso():
    ofensas: list[str] = []
    for carpeta in AMBITO:
        for fichero in sorted((RAIZ / carpeta).rglob("*.py")):
            relativo = fichero.relative_to(RAIZ).as_posix()
            for linea, que in _lecturas(fichero):
                if PERMITIDOS.get(relativo):
                    continue
                ofensas.append(f"{relativo}:{linea} usa {que}")

    assert ofensas == [], (
        "la fecha de negocio se pide a `app.shared.clock.hoy_de_negocio()`, no al reloj "
        "del proceso (Spec 001 · POLICY-CLOCK-LOCAL):\n  " + "\n  ".join(ofensas))


def test_el_ayudante_existe_y_es_la_unica_fuente():
    """Si alguien retira el ayudante, esto lo dice antes que veintiséis fallos sueltos."""
    from app.shared import clock

    assert hasattr(clock, "hoy_de_negocio") and hasattr(clock, "ahora_de_negocio")
    modulos = [f.relative_to(RAIZ).as_posix()
               for carpeta in ("app/modules",)
               for f in (RAIZ / carpeta).rglob("*.py")
               if "hoy_de_negocio" in f.read_text(encoding="utf-8")]
    assert len(modulos) >= 8, f"el ayudante dejó de usarse donde debía: {modulos}"
