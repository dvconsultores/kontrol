"""Mensajes de la Spec 047: clave estable + parámetros → texto (FR-047-050..053).

# Spec 047 · Mensajes y localización

La base guarda **la clave y sus parámetros**; el texto se deriva en cada lectura.
Así una notificación de hoy podrá leerse en otro idioma mañana sin tocar su fila,
y corregir una redacción no reescribe la historia (OQ-047-02).

- Catálogo `es` en V1. `en` está **DEFERRED**: no hay traducciones parciales.
- La sustitución es propia, `{nombre}` y nada más. No se usa `str.format`, que
  admite `{x.atributo}` y `{x[0]}`: un parámetro nunca ejecuta nada.
- Los parámetros son escalares. Un importe viaja como cadena.
- Un parámetro sobrante se ignora siempre, de forma determinista.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

IDIOMA_POR_DEFECTO = "es"
#: Idiomas con catálogo. Añadir `en` es añadir su catálogo aquí: ni migración ni
#: cambio de contrato de la API.
IDIOMAS = ("es",)

MESSAGE_KEY_UNKNOWN = "MESSAGE_KEY_UNKNOWN"
MESSAGE_PARAM_MISSING = "MESSAGE_PARAM_MISSING"
MESSAGE_PARAM_INVALID = "MESSAGE_PARAM_INVALID"

_VARIABLE = re.compile(r"\{([a-z_][a-z0-9_]*)\}")
_ESCALARES = (str, int, bool, type(None))


@dataclass(frozen=True)
class Plantilla:
    texto: str
    parametros: frozenset[str]


def _p(texto: str) -> Plantilla:
    return Plantilla(texto, frozenset(_VARIABLE.findall(texto)))


CATALOGOS: dict[str, dict[str, Plantilla]] = {
    "es": {
        # -- hechos de la Spec 045 --------------------------------------------
        "approval.step_opened.notification": _p(
            "Hay una aprobación de {process_type} pendiente en el nivel {level_order}."),
        "approval.step_opened.task": _p(
            "Atender la aprobación de {process_type} en el nivel {level_order}."),
        "approval.step_opened.alert": _p(
            "Se abrió una aprobación de {process_type} en el nivel {level_order}."),
        "approval.step_expired.notification": _p(
            "Venció el plazo de la aprobación de {process_type} en el nivel {level_order}."),
        "approval.step_expired.task": _p(
            "Revisar la aprobación vencida de {process_type} en el nivel {level_order}."),
        "approval.step_expired.alert": _p(
            "Aprobación de {process_type} vencida en el nivel {level_order}."),
        "replenishment.need_detected.alert": _p(
            "{product_code} · {product_name} requiere reposición en el almacén {warehouse_code}."),
        # -- efectos del planificador -----------------------------------------
        "task.reminder.notification": _p(
            "Tienes una tarea pendiente cuyo plazo está por vencer o ya venció."),
        "task.escalation.notification": _p(
            "Una tarea de tu empresa está vencida y requiere atención."),
        # -- errores de la API de la 047 ----------------------------------------
        "error.notification_not_found": _p("La notificación no existe."),
        "error.task_not_found": _p("La tarea no existe."),
        "error.task_already_closed": _p("La tarea ya está cerrada."),
        "error.task_version_conflict": _p(
            "La tarea cambió mientras la editabas. Recarga y vuelve a intentarlo."),
        "error.task_not_actionable": _p("No puedes actuar sobre esta tarea."),
        "error.task_assignee_not_in_company": _p(
            "La persona elegida no tiene acceso a esta empresa."),
        "error.task_reason_required": _p("Debes indicar el motivo."),
        "error.task_if_match_required": _p(
            "Falta la versión de la tarea (cabecera If-Match)."),
        "error.notification_mandatory": _p(
            "Esta notificación es obligatoria y no puede desactivarse."),
        "error.channel_unavailable": _p("Ese canal no está disponible en esta instalación."),
        "error.notification_rule_code_taken": _p("Ya existe una regla con ese código."),
        "error.notification_rule_invalid": _p("La regla no es válida."),
        "error.permission_required": _p("No tienes permiso para esta operación."),
        "error.notification_rule_not_found": _p("La regla no existe."),
        "error.task_priority_code_taken": _p("Ya existe una prioridad con ese código."),
        "error.task_priority_not_found": _p("La prioridad indicada no existe."),
        "error.message_invalid": _p("El mensaje no cumple su contrato ({code})."),
    },
}


class MensajeInvalido(ValueError):
    """La clave o sus parámetros no cumplen el contrato del catálogo."""

    def __init__(self, codigo: str, clave: str) -> None:
        super().__init__(f"{codigo}: {clave}")
        self.codigo = codigo
        self.clave = clave


@dataclass(frozen=True)
class Renderizado:
    text: str | None
    render_error: str | None


def _catalogo(idioma: str | None) -> dict[str, Plantilla]:
    return CATALOGOS.get(idioma or IDIOMA_POR_DEFECTO) or CATALOGOS[IDIOMA_POR_DEFECTO]


def validar(clave: str, parametros: Any, idioma: str | None = None) -> None:
    """Lanza `MensajeInvalido` si la clave no existe o sus parámetros no bastan."""
    plantilla = _catalogo(idioma).get(clave)
    if plantilla is None:
        raise MensajeInvalido(MESSAGE_KEY_UNKNOWN, clave)
    if not isinstance(parametros, dict):
        raise MensajeInvalido(MESSAGE_PARAM_INVALID, clave)
    for nombre in plantilla.parametros:
        if nombre not in parametros:
            raise MensajeInvalido(MESSAGE_PARAM_MISSING, clave)
        if not isinstance(parametros[nombre], _ESCALARES):
            raise MensajeInvalido(MESSAGE_PARAM_INVALID, clave)


def renderizar(clave: str, parametros: Any, idioma: str | None = None) -> Renderizado:
    """Texto visible, o el error controlado que impide componerlo. Nunca la clave cruda."""
    try:
        validar(clave, parametros, idioma)
    except MensajeInvalido as e:
        return Renderizado(text=None, render_error=e.codigo)
    plantilla = _catalogo(idioma)[clave]

    def valor(m: re.Match[str]) -> str:
        v = parametros[m.group(1)]
        return "—" if v is None else str(v)

    return Renderizado(text=_VARIABLE.sub(valor, plantilla.texto), render_error=None)


def texto(clave: str, **parametros: Any) -> str:
    """Texto de un mensaje propio del código (errores). Una clave rota es un defecto."""
    r = renderizar(clave, parametros)
    if r.text is None:
        raise MensajeInvalido(r.render_error or MESSAGE_KEY_UNKNOWN, clave)
    return r.text
