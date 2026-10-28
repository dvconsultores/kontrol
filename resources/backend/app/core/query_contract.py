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
from fastapi.dependencies.utils import get_flat_dependant, get_parameterless_sub_dependant
from fastapi.routing import APIRoute

from app.core.errors import KontrolError

CODIGO = "UNKNOWN_QUERY_PARAMETER"
MENSAJE = "La consulta incluye parámetros que esta operación no admite."
MENSAJE_CAMPO = "Parámetro no admitido por esta operación."


def parametros_de_consulta_declarados(ruta: APIRoute) -> frozenset[str]:
    """Devuelve los alias de los parámetros de consulta declarados por la ruta."""
    return frozenset(
        p.alias for p in get_flat_dependant(ruta.dependant, skip_repeats=True).query_params
    )


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
    """Instala el verificador en todas las rutas API bajo el prefijo indicado."""
    for ruta in app.routes:
        if not isinstance(ruta, APIRoute):
            continue
        if not (ruta.path == prefijo or ruta.path.startswith(prefijo + "/")):
            continue

        if ruta.dependant.dependencies and isinstance(
            ruta.dependant.dependencies[-1].call, VerificadorDeConsulta
        ):
            continue

        permitidos = parametros_de_consulta_declarados(ruta)
        ruta.dependant.dependencies.append(
            get_parameterless_sub_dependant(
                depends=Depends(VerificadorDeConsulta(permitidos)),
                path=ruta.path_format,
            )
        )
