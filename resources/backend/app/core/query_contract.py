"""Contrato estricto de parámetros de consulta para la API.

Rechaza con 422 cualquier parámetro de consulta (`?clave=valor`) que no esté
declarado en la ruta resuelta por FastAPI. El conjunto permitido se deriva del
contrato real de la aplicación y se precalcula al arrancar, sin listas manuales
por ruta.

El verificador se instala al final de las dependencias de cada ruta: la
autenticación, los permisos y el contexto de empresa se evalúan antes; la
verificación ocurre antes de validar valores y de ejecutar el endpoint.
No se usan ni se ecoan los valores enviados por el cliente.
"""

# SIN `from __future__ import annotations`: FastAPI resuelve la firma del
# `__call__` de una instancia sin `__globals__`; con anotaciones en texto,
# `request: Request` se tomaría por un parámetro de consulta.
from fastapi import Depends, FastAPI, Request
from fastapi.dependencies.utils import get_parameterless_sub_dependant
from fastapi.routing import APIRoute, RouteContext

from app.core.errors import KontrolError
from app.core.route_contexts import contextos_de_api

CODIGO = "UNKNOWN_QUERY_PARAMETER"
MENSAJE = "La consulta incluye parámetros que esta operación no admite."
MENSAJE_CAMPO = "Parámetro no admitido por esta operación."


def parametros_de_consulta_declarados(ruta: APIRoute | RouteContext) -> frozenset[str]:
    """Devuelve los alias de consulta de la ruta y de todas sus subdependencias.

    Recorre el árbol `Dependant` que FastAPI construye, sin depender de ayudantes
    internos de aplanado. Un alias repetido cuenta una sola vez.
    """
    alias: set[str] = set()
    pendientes = [ruta.dependant]
    while pendientes:
        actual = pendientes.pop()
        alias.update(parametro.alias for parametro in actual.query_params)
        pendientes.extend(actual.dependencies)
    return frozenset(alias)


class VerificadorDeConsulta:
    """Dependencia que rechaza parámetros de consulta no declarados en la ruta."""

    __slots__ = ("permitidos",)

    def __init__(self, permitidos: frozenset[str]) -> None:
        self.permitidos = permitidos

    async def __call__(self, request: Request) -> None:
        desconocidos = sorted(set(request.query_params.keys()) - self.permitidos)
        if desconocidos:
            raise KontrolError(
                CODIGO,
                MENSAJE,
                field_errors={f"query.{n}": [MENSAJE_CAMPO] for n in desconocidos},
                details={"unknown_query_parameters": desconocidos},
                status_code=422,
            )


def instalar_contrato_de_consulta(app: FastAPI, prefijo: str) -> None:
    """Instala el verificador en todas las rutas API bajo el prefijo indicado.

    FastAPI incluye los routers de forma perezosa y sirve cada ruta desde su contexto
    efectivo, por lo que el verificador se añade a `contexto.dependant`. Debe llamarse
    después de incluir el último router: añadir rutas a un router después reconstruye sus
    contextos y perdería el verificador. GUARD-Q-01 lo protege.
    """
    for contexto in contextos_de_api(app):
        ruta = contexto.path
        if ruta is None or not (ruta == prefijo or ruta.startswith(prefijo + "/")):
            continue

        dependant = contexto.dependant
        if dependant.dependencies and isinstance(
            dependant.dependencies[-1].call, VerificadorDeConsulta
        ):
            continue

        permitidos = parametros_de_consulta_declarados(contexto)
        dependant.dependencies.append(
            get_parameterless_sub_dependant(
                depends=Depends(VerificadorDeConsulta(permitidos)),
                path=contexto.path_format or ruta,
            )
        )
