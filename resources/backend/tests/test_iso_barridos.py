"""
Barridos de aislamiento para TODAS las rutas de empresa.

Demuestran dos propiedades frente al mundo hostil:

1. IDOR/BOLA: sustituir los ids de una ruta de empresa por ids de otras
   empresas (mismo tenant u otro tenant) no devuelve datos (2xx) ni filtra
   centinelas en la respuesta.
2. Fugas de listas/búsquedas: los endpoints GET de empresa sin parámetros de
   ruta nunca devuelven datos de otras empresas, ni siquiera al preguntar por
   el centinela de una empresa ajena con el parámetro ``q``.

Extensión futura: para añadir más orígenes basta con ampliar ``ORIGENES``;
   el recorrido no cambia.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Sequence
from itertools import product
from typing import Any

from fastapi.routing import APIRoute

from app.core.company_context import get_company_context

pytest_plugins = ("tests.hostil_mundo",)

ORIGENES: tuple[str, ...] = ("A2", "B1")

PERMITIDAS_2XX: dict[tuple[str, str], str] = {}


def _depende_de_company_context(route: APIRoute) -> bool:
    """True si `route.dependant` depende (directa o indirectamente) de get_company_context."""

    def hay_contexto(dep: Any, vistos: set[int] | None = None) -> bool:
        if vistos is None:
            vistos = set()
        if id(dep) in vistos:
            return False
        vistos.add(id(dep))
        if dep.call is get_company_context:
            return True
        return any(hay_contexto(sub, vistos) for sub in dep.dependencies)

    return hay_contexto(route.dependant)


def _rutas_empresa(app: Any) -> list[APIRoute]:
    """Todas las rutas de la app que dependen del contexto de empresa."""
    return [
        r
        for r in app.routes
        if isinstance(r, APIRoute) and _depende_de_company_context(r)
    ]


def _sin_api_v1(path: str) -> str:
    """Quita el prefijo /api/v1 de una ruta FastAPI."""
    if path.startswith("/api/v1"):
        return path[len("/api/v1"):] or "/"
    return path


def _ids_para_parametro(nombre: str, recursos: dict[str, dict[str, str]], origen: str) -> tuple[str, ...]:
    """Ids candidatos para un parámetro de ruta según su nombre y su origen."""
    clave = nombre[:-3] if nombre.endswith("_id") else nombre
    if clave in recursos[origen]:
        return (recursos[origen][clave],)
    return tuple(recursos[origen].values())


def _rutas_ids_ajenos(rutas_empresa: list[APIRoute]) -> tuple[list[APIRoute], list[tuple[str, str]]]:
    """Rutas de empresa cuyos parámetros de ruta son todos *_id/id.

    Devuelve (rutas_candidatas, omitidas) con omitidas como (método, ruta).
    """
    candidatas: list[APIRoute] = []
    omitidas: list[tuple[str, str]] = []
    for ruta in rutas_empresa:
        nombres = [p.name for p in ruta.dependant.path_params]
        if not nombres:
            continue
        if all(n == "id" or n.endswith("_id") for n in nombres):
            candidatas.append(ruta)
        else:
            for metodo in sorted(ruta.methods or []):
                omitidas.append((metodo, _sin_api_v1(ruta.path)))
    return candidatas, omitidas


def test_barrido_ids_ajenos(mundo_hostil: Any) -> None:
    """Sustituye todos los ids de ruta por ids de otras empresas y comprueba que no hay fuga."""
    rutas = _rutas_empresa(mundo_hostil.client.app)
    rutas_ids, omitidas = _rutas_ids_ajenos(rutas)

    huella_antes = mundo_hostil.huella()

    hallazgos: list[str] = []
    n_peticiones = 0
    for ruta in rutas_ids:
        nombres = [p.name for p in ruta.dependant.path_params]
        for metodo in sorted(ruta.methods or []):
            for origen in ORIGENES:
                ids = [_ids_para_parametro(n, mundo_hostil.recursos, origen) for n in nombres]
                combinaciones: Iterable[Sequence[str]] = product(*ids)
                for combinacion in list(combinaciones)[:30]:
                    n_peticiones += 1
                    ruta_rellena = _sin_api_v1(ruta.path).format(
                        **dict(zip(nombres, combinacion, strict=True))
                    )
                    respuesta = mundo_hostil.pedir(
                        "a1_op",
                        metodo,
                        ruta_rellena,
                        empresa=mundo_hostil.empresas["A1"],
                        json={} if metodo in {"POST", "PUT", "PATCH"} else None,
                    )
                    fugas = mundo_hostil.fugas("a1_op", respuesta.text)
                    if 200 <= respuesta.status_code < 300 or fugas:
                        hallazgos.append(
                            f"{metodo} {ruta_rellena} | origen={origen} | "
                            f"estado={respuesta.status_code} | fugas={fugas if fugas else '-'} | "
                            f"texto={respuesta.text[:120]!r}"
                        )

    huella_despues = mundo_hostil.huella()
    cambiadas = [k for k in huella_antes if huella_antes[k] != huella_despues.get(k)]
    if cambiadas:
        hallazgos.insert(
            0,
            "INMUTABILIDAD ROTA en tablas: " + ", ".join(sorted(cambiadas)),
        )

    print(
        f"[barrido IDs] rutas={len(rutas_ids)} peticiones={n_peticiones} "
        f"omitidas={len(omitidas)} (otro parámetro no *_id/id)"
    )
    if omitidas:
        print("[barrido IDs] omitidas:", omitidas)
    assert not hallazgos, "Barrido IDs ajenos - hallazgos:\n" + "\n".join(hallazgos)


def test_barrido_listas_sin_fugas(mundo_hostil: Any) -> None:
    """GET de empresa sin parámetros de ruta: ni listado ni búsqueda devuelven datos ajenos."""
    hallazgos: list[str] = []
    rutas = _rutas_empresa(mundo_hostil.client.app)
    for ruta in rutas:
        if "GET" not in (ruta.methods or set()):
            continue
        if ruta.dependant.path_params:
            continue

        nombres_query = {p.name for p in ruta.dependant.query_params}
        ruta_limpia = _sin_api_v1(ruta.path)

        for actor, empresa, origen_centinelas in (
            ("a1_op", mundo_hostil.empresas["A1"], "B1"),
            ("b1_op", mundo_hostil.empresas["B1"], "A1"),
        ):
            respuesta = mundo_hostil.pedir(actor, "GET", ruta_limpia, empresa=empresa)
            fugas = mundo_hostil.fugas(actor, respuesta.text)
            if fugas:
                hallazgos.append(
                    f"GET {ruta_limpia} | actor={actor} | sin parámetros | "
                    f"estado={respuesta.status_code} | fugas={fugas} | "
                    f"texto={respuesta.text[:120]!r}"
                )

            if "q" in nombres_query:
                centinela = next(iter(sorted(mundo_hostil.centinelas[origen_centinelas])))
                respuesta = mundo_hostil.pedir(
                    actor,
                    "GET",
                    ruta_limpia,
                    empresa=empresa,
                    params={"q": centinela},
                )
                fugas = mundo_hostil.fugas(actor, respuesta.text)
                if fugas:
                    hallazgos.append(
                        f"GET {ruta_limpia}?q={centinela!r} | actor={actor} | "
                        f"estado={respuesta.status_code} | fugas={fugas} | "
                        f"texto={respuesta.text[:120]!r}"
                    )

    print(f"[barrido listas] hallazgos={len(hallazgos)}")
    assert not hallazgos, "Barrido listas - hallazgos:\n" + "\n".join(hallazgos)


def test_barrido_cabecera_manipulada(mundo_hostil: Any) -> None:
    """ISO-CAB-01: la cabecera X-Kontrol-Company propone la empresa, pero el servidor resuelve y valida.

    Una empresa de otro tenant o del mismo tenant sin UserScope del actor debe devolver 404
    COMPANY_NOT_FOUND antes de validar cuerpo, consulta o ruta. Este barrido hostil recorre todas
    las rutas de empresa manipulando la cabecera para verificar el aislamiento ruta por ruta.
    """
    casos = [
        ("a1_op", "A2"),
        ("a1_op", "B1"),
        ("b1_op", "A1"),
        ("admin_a", "B1"),
        ("admin_b", "A1"),
    ]
    rutas = _rutas_empresa(mundo_hostil.client.app)
    huella_antes = mundo_hostil.huella()
    hallazgos: list[str] = []
    peticiones = 0
    recuento: dict[tuple[int, str | None], int] = {}

    for actor, empresa_caso in casos:
        for ruta in rutas:
            for metodo in sorted(ruta.methods or []):
                # Rellenar parámetros de ruta con UUID cero para ids y "x" para el resto.
                params_ruta: dict[str, str] = {}
                for param in ruta.dependant.path_params:
                    nombre = param.name
                    if nombre == "id" or nombre.endswith("_id"):
                        params_ruta[nombre] = "00000000-0000-0000-0000-000000000000"
                    else:
                        params_ruta[nombre] = "x"
                ruta_formateada = _sin_api_v1(ruta.path).format(**params_ruta)
                json_body = {} if metodo in {"POST", "PUT", "PATCH"} else None

                # Petición (a): empresa ajena del caso.
                respuesta_a = mundo_hostil.pedir(
                    actor,
                    metodo,
                    ruta_formateada,
                    empresa=mundo_hostil.empresas[empresa_caso],
                    json=json_body,
                )
                peticiones += 1

                # Petición (b): empresa inexistente, UUID nuevo por petición.
                respuesta_b = mundo_hostil.pedir(
                    actor,
                    metodo,
                    ruta_formateada,
                    empresa=str(uuid.uuid4()),
                    json=json_body,
                )
                peticiones += 1

                try:
                    cuerpo_a = respuesta_a.json()
                except ValueError:
                    cuerpo_a = None
                try:
                    cuerpo_b = respuesta_b.json()
                except ValueError:
                    cuerpo_b = None

                codigo_a = cuerpo_a.get("code") if isinstance(cuerpo_a, dict) else None
                codigo_b = cuerpo_b.get("code") if isinstance(cuerpo_b, dict) else None

                estado_a = respuesta_a.status_code
                estado_b = respuesta_b.status_code

                recuento[(estado_a, codigo_a)] = recuento.get((estado_a, codigo_a), 0) + 1

                # Hallazgo si (a) es 2xx.
                if 200 <= estado_a < 300:
                    hallazgos.append(
                        f"{metodo} {ruta.path} | caso={actor}->{empresa_caso} | "
                        f"estado={estado_a} | code={codigo_a!r} | "
                        f"texto={respuesta_a.text[:120]!r}"
                    )
                    continue

                # Hallazgo si el par (estado, code) de (a) difiere del de (b).
                if (estado_a, codigo_a) != (estado_b, codigo_b):
                    hallazgos.append(
                        f"{metodo} {ruta.path} | caso={actor}->{empresa_caso} | "
                        f"par_a=({estado_a}, {codigo_a!r}) | par_b=({estado_b}, {codigo_b!r}) | "
                        f"texto_a={respuesta_a.text[:120]!r} | texto_b={respuesta_b.text[:120]!r}"
                    )
                    continue

                # Hallazgo si (estado, code) de (a) no está en el conjunto permitido.
                if (estado_a, codigo_a) not in {
                    (404, "COMPANY_NOT_FOUND"),
                    (403, "PERMISSION_DENIED"),
                }:
                    hallazgos.append(
                        f"{metodo} {ruta.path} | caso={actor}->{empresa_caso} | "
                        f"estado={estado_a} | code={codigo_a!r} | "
                        f"texto={respuesta_a.text[:120]!r}"
                    )
                    continue

                # Sin fugas de empresas no visibles.
                fugas = mundo_hostil.fugas(actor, respuesta_a.text)
                if fugas:
                    hallazgos.append(
                        f"{metodo} {ruta.path} | caso={actor}->{empresa_caso} | "
                        f"estado={estado_a} | fugas={fugas} | "
                        f"texto={respuesta_a.text[:120]!r}"
                    )

    # CONTROL: rutas GET sin parámetros de ruta con la propia empresa no deben devolver COMPANY_NOT_FOUND.
    for ruta in rutas:
        if "GET" not in (ruta.methods or set()):
            continue
        if ruta.dependant.path_params:
            continue
        ruta_formateada = _sin_api_v1(ruta.path)
        respuesta = mundo_hostil.pedir(
            "a1_op",
            "GET",
            ruta_formateada,
            empresa=mundo_hostil.empresas["A1"],
        )
        peticiones += 1
        try:
            cuerpo = respuesta.json()
        except ValueError:
            cuerpo = None
        codigo = cuerpo.get("code") if isinstance(cuerpo, dict) else None
        if codigo == "COMPANY_NOT_FOUND":
            hallazgos.append(
                f"CONTROL GET {ruta.path} | caso=a1_op->A1 | "
                f"estado={respuesta.status_code} | code={codigo!r} | "
                f"texto={respuesta.text[:120]!r}"
            )

    huella_despues = mundo_hostil.huella()
    if huella_antes != huella_despues:
        cambiadas = [k for k in huella_antes if huella_antes[k] != huella_despues.get(k)]
        hallazgos.append(
            "INMUTABILIDAD ROTA en tablas: " + ", ".join(sorted(cambiadas))
        )

    print(
        f"[barrido cabecera] rutas={len(rutas)} peticiones={peticiones} "
        f"casos={len(casos)} hallazgos={len(hallazgos)} recuento={recuento}"
    )
    assert not hallazgos, "Barrido cabecera - hallazgos:\n" + "\n".join(hallazgos)
