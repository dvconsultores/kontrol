"""Visión única de las rutas efectivas. FastAPI incluye los routers de forma perezosa y `app.routes` no expone
las rutas incluidas; todo consumidor del routing de la aplicación debe pasar por aquí."""

from collections.abc import Iterator

from fastapi import FastAPI
from fastapi.routing import APIRoute, RouteContext, iter_route_contexts


def contextos_de_api(app: FastAPI) -> Iterator[RouteContext]:
    """Itera los RouteContext de las rutas API efectivas de la aplicación."""
    for contexto in iter_route_contexts(app.routes):
        if isinstance(contexto.original_route, APIRoute):
            yield contexto
