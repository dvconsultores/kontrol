"""Catálogo de operaciones de la API: qué capacidades declara cada (método, ruta) y con qué alcance se evalúan
(COMPANY: depende de get_company_context; TENANT: require_tenant_permission; GLOBAL: el resto). Lo consume la UI para no mantener un
modelo de permisos propio (Spec 003, ADR-018). Es metadato de la API, igual para todos los usuarios."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from app.core.company_context import get_company_context
from app.core.route_contexts import contextos_de_api

_CATALOGOS: dict[int, list[dict[str, Any]]] = {}


def _recorrer(dependant: Any, permisos: set[str], marcas: set[str]) -> None:
    """Junta los permisos declarados y las marcas de alcance de un árbol de dependencias."""
    if dependant is None:
        return
    permiso = getattr(dependant.call, "kontrol_permission", None)
    if permiso is not None:
        permisos.add(permiso)
    if getattr(dependant.call, "kontrol_scope", None) == "TENANT":
        marcas.add("TENANT")
    if dependant.call is get_company_context:
        marcas.add("COMPANY")
    for dep in getattr(dependant, "dependencies", []) or []:
        _recorrer(dep, permisos, marcas)


def catalogo_de_operaciones(app: FastAPI) -> list[dict[str, Any]]:
    if id(app) in _CATALOGOS:
        return _CATALOGOS[id(app)]

    operaciones: list[dict[str, Any]] = []

    for contexto in contextos_de_api(app):
        permisos: set[str] = set()
        marcas: set[str] = set()
        _recorrer(contexto.dependant, permisos, marcas)
        tenant = "TENANT" in marcas
        empresa = "COMPANY" in marcas

        metodos = sorted(set(contexto.methods or ()) - {"HEAD", "OPTIONS"})
        scope = "TENANT" if tenant else ("COMPANY" if empresa else "GLOBAL")
        for m in metodos:
            operaciones.append(
                {
                    "method": m,
                    "path": contexto.path,
                    "capabilities": sorted(permisos),
                    "scope": scope,
                }
            )

    operaciones.sort(key=lambda x: (x["path"], x["method"]))
    _CATALOGOS[id(app)] = operaciones
    return operaciones
