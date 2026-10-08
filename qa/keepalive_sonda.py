"""Sonda del keep-alive HTTP de un servidor (`BACKEND-KEEPALIVE-5S`, Spec 054, apoyo 052).

Mide lo que la deuda describe y nada más: cuánto conserva el servidor una conexión persistente
ociosa. Abre `conexiones` sockets HTTP/1.1, envía una petición por cada uno, espera `ocio` segundos
con los sockets abiertos y vuelve a pedir por **la misma** conexión. Si el servidor la cerró en el
ocio, la segunda petición falla (`ConnectionResetError`, `RemoteDisconnected`, `BadStatusLine`) o
no responde. Un cliente que conserva sus conexiones exactamente lo mismo que el servidor —el agente
de Node, 5 s— pierde la carrera en el instante del cierre: es el `ECONNRESET` de las corridas E2E.

Uso: `python qa/keepalive_sonda.py --url http://127.0.0.1:8000/api/v1/health/live --ocio 5.3 --conexiones 20`
"""

from __future__ import annotations

import argparse
import http.client
import json
import sys
import time
from dataclasses import dataclass
from urllib.parse import urlsplit

__all__ = ["Medicion", "sondear"]


@dataclass(frozen=True)
class Medicion:
    conexiones: int
    ocio_segundos: float
    reutilizadas: int  # segunda petición respondida por la misma conexión
    cerradas: int  # el servidor cerró la conexión durante el ocio
    errores: tuple[str, ...]

    @property
    def fallan(self) -> int:
        return self.conexiones - self.reutilizadas


def _pedir(conexion: http.client.HTTPConnection, ruta: str) -> None:
    conexion.request("GET", ruta, headers={"Connection": "keep-alive"})
    respuesta = conexion.getresponse()
    respuesta.read()
    if respuesta.status != 200:
        raise RuntimeError(f"HTTP {respuesta.status}")


def sondear(url: str, *, ocio: float, conexiones: int, limite: float = 10.0) -> Medicion:
    """Abre todas las conexiones, pide una vez por cada una, espera `ocio` y vuelve a pedir."""
    partes = urlsplit(url)
    if partes.hostname is None:
        raise ValueError("la URL necesita host")
    puerto = partes.port or (443 if partes.scheme == "https" else 80)
    ruta = partes.path or "/"
    sockets = [http.client.HTTPConnection(partes.hostname, puerto, timeout=limite) for _ in range(conexiones)]
    for s in sockets:
        _pedir(s, ruta)  # la primera siempre responde: la conexión acaba de abrirse
    time.sleep(ocio)
    reutilizadas, errores = 0, []
    for s in sockets:
        try:
            _pedir(s, ruta)
            reutilizadas += 1
        except (ConnectionResetError, BrokenPipeError, http.client.RemoteDisconnected, http.client.BadStatusLine, TimeoutError, OSError) as exc:
            errores.append(type(exc).__name__)
        finally:
            s.close()
    return Medicion(conexiones=conexiones, ocio_segundos=ocio, reutilizadas=reutilizadas, cerradas=conexiones - reutilizadas, errores=tuple(errores))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="keepalive_sonda", description=__doc__.splitlines()[0])
    parser.add_argument("--url", required=True)
    parser.add_argument("--ocio", type=float, default=5.3, help="segundos de inactividad entre las dos peticiones")
    parser.add_argument("--conexiones", type=int, default=20)
    args = parser.parse_args(argv)
    medicion = sondear(args.url, ocio=args.ocio, conexiones=args.conexiones)
    print(json.dumps({"url": args.url, "ocio_s": medicion.ocio_segundos, "conexiones": medicion.conexiones, "reutilizadas": medicion.reutilizadas,
                      "cerradas_por_el_servidor": medicion.cerradas, "errores": sorted(set(medicion.errores))}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
