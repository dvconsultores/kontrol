"""Smoke no destructivo de la UAT viva.

Realiza lecturas, login con MFA y cierre de sesión. Nunca escribe datos de
negocio. Uso: python3 deploy/uat/smoke.py [--solo-health] https://<dominio>
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import ssl
import struct
import sys
import time
import urllib.error
import urllib.request
from typing import Any


def _pedir(
    metodo: str,
    url: str,
    cuerpo: dict[str, Any] | None = None,
    token: str | None = None,
    empresa: str | None = None,
) -> tuple[int, dict[str, Any] | str]:
    """Envía una petición HTTPS y devuelve (código, cuerpo)."""
    datos: bytes | None = None
    cabeceras = {"User-Agent": "kontrol-uat-smoke"}

    if cuerpo is not None:
        datos = json.dumps(cuerpo).encode("utf-8")
        cabeceras["Content-Type"] = "application/json"

    if token is not None:
        cabeceras["Authorization"] = f"Bearer {token}"

    if empresa is not None:
        cabeceras["X-Kontrol-Company"] = empresa

    peticion = urllib.request.Request(
        url, data=datos, headers=cabeceras, method=metodo
    )
    contexto = ssl.create_default_context()

    try:
        with urllib.request.urlopen(
            peticion, timeout=20, context=contexto
        ) as respuesta:
            contenido = respuesta.read().decode("utf-8")
            if respuesta.headers.get("Content-Type", "").startswith(
                "application/json"
            ):
                try:
                    return respuesta.status, json.loads(contenido)
                except json.JSONDecodeError:
                    return respuesta.status, contenido
            return respuesta.status, contenido
    except urllib.error.HTTPError as error:
        contenido = error.read().decode("utf-8")
        if error.headers.get("Content-Type", "").startswith("application/json"):
            try:
                return error.code, json.loads(contenido)
            except json.JSONDecodeError:
                return error.code, contenido
        return error.code, contenido


def totp(secreto_b32: str, instante: float | None = None) -> str:
    """Genera un código TOTP RFC 6238, HMAC-SHA1, 6 dígitos."""
    if instante is None:
        instante = time.time()
    contador = int(instante) // 30
    secreto_normalizado = secreto_b32.replace(" ", "").upper()
    secreto_normalizado += "=" * ((8 - len(secreto_normalizado) % 8) % 8)
    clave = base64.b32decode(secreto_normalizado)
    contador_bytes = struct.pack(">Q", contador)
    digesto = hmac.new(clave, contador_bytes, hashlib.sha1).digest()
    desplazamiento = digesto[-1] & 0x0F
    codigo_binario = struct.unpack(">I", digesto[desplazamiento : desplazamiento + 4])[0]
    codigo_binario &= 0x7FFFFFFF
    return f"{codigo_binario % 1_000_000:06d}"


def main() -> int:
    """Ejecuta las comprobaciones del smoke."""
    solo_health = "--solo-health" in sys.argv
    argumentos = [a for a in sys.argv[1:] if a != "--solo-health"]

    if len(argumentos) != 1:
        print("Uso: python3 deploy/uat/smoke.py [--solo-health] https://<dominio>")
        return 1

    base = argumentos[0].rstrip("/")

    comprobaciones: list[tuple[str, bool, str]] = []

    estado, cuerpo_spa = _pedir("GET", f"{base}/", None, None, None)
    ok_spa = estado == 200 and isinstance(cuerpo_spa, str) and '<div id="root"' in cuerpo_spa
    comprobaciones.append(
        ("SPA", ok_spa, "la raíz no responde con el HTML de la SPA" if not ok_spa else "")
    )

    estado, _ = _pedir("GET", f"{base}/healthz", None, None, None)
    ok_healthz = estado == 200
    comprobaciones.append(("healthz", ok_healthz, "" if ok_healthz else "healthz no responde 200"))

    estado, cuerpo_live = _pedir("GET", f"{base}/api/v1/health/live", None, None, None)
    ok_live = (
        estado == 200
        and isinstance(cuerpo_live, dict)
        and cuerpo_live.get("status") == "ok"
    )
    comprobaciones.append(("live", ok_live, "" if ok_live else "live no responde ok"))

    estado, cuerpo_ready = _pedir("GET", f"{base}/api/v1/health/ready", None, None, None)
    ok_ready = (
        estado == 200
        and isinstance(cuerpo_ready, dict)
        and cuerpo_ready.get("status") == "ok"
        and cuerpo_ready.get("database") == "ok"
    )
    comprobaciones.append(("ready", ok_ready, "" if ok_ready else "ready no responde ok"))

    for nombre, ok, motivo in comprobaciones:
        if ok:
            print(f"OK {nombre}")
        else:
            print(f"FALLA {nombre}: {motivo}")
            return 1

    if solo_health:
        print("PASS")
        return 0

    variables = [
        "UAT_SMOKE_TENANT",
        "UAT_SMOKE_USERNAME",
        "UAT_SMOKE_PASSWORD",
        "UAT_SMOKE_TOTP_SECRET",
    ]
    credenciales_presentes = all(os.getenv(nombre) for nombre in variables)
    rutas_definidas = bool(os.getenv("UAT_SMOKE_PATHS", "").strip())

    if not credenciales_presentes or not rutas_definidas:
        if os.getenv("UAT_REQUIRE_AUTH_SMOKE", "true") == "false":
            print("AVISO smoke autenticado omitido")
            print("MANUAL_PENDING")
            return 0
        ausentes = [nombre for nombre in variables if not os.getenv(nombre)]
        if not rutas_definidas:
            ausentes.append("UAT_SMOKE_PATHS")
        print(f"FALLA faltan credenciales de smoke: {', '.join(ausentes)}")
        return 1

    tenant = os.environ["UAT_SMOKE_TENANT"]
    username = os.environ["UAT_SMOKE_USERNAME"]
    password = os.environ["UAT_SMOKE_PASSWORD"]
    totp_secret = os.environ["UAT_SMOKE_TOTP_SECRET"]
    company_id = os.getenv("UAT_SMOKE_COMPANY_ID")

    estado_login, cuerpo_login = _pedir(
        "POST",
        f"{base}/api/v1/auth/login",
        {"tenant_code": tenant, "username": username, "password": password},
        None,
        None,
    )

    if estado_login != 200 or not isinstance(cuerpo_login, dict):
        print("FALLA login: no se obtuvo una respuesta JSON válida")
        return 1

    estado_auth = cuerpo_login.get("status")
    challenge_token = cuerpo_login.get("challenge_token")

    if estado_auth == "AUTHENTICATED":
        print("FALLA login: el usuario de smoke debe tener MFA")
        return 1

    if estado_auth == "MFA_ENROLLMENT_REQUIRED":
        print("FALLA login: el usuario de smoke requiere inscripción de MFA")
        return 1

    if estado_auth != "MFA_REQUIRED" or not isinstance(challenge_token, str):
        print("FALLA login: no se solicitó MFA")
        return 1

    codigo = totp(totp_secret)
    estado_mfa, cuerpo_mfa = _pedir(
        "POST",
        f"{base}/api/v1/auth/mfa/verify",
        {"challenge_token": challenge_token, "code": codigo},
        None,
        None,
    )

    if estado_mfa != 200 or not isinstance(cuerpo_mfa, dict):
        print("FALLA mfa/verify: no se obtuvo una respuesta JSON válida")
        return 1

    if cuerpo_mfa.get("status") != "AUTHENTICATED":
        print("FALLA mfa/verify: no se autenticó")
        return 1

    access_token = cuerpo_mfa.get("access_token")
    if not isinstance(access_token, str):
        print("FALLA mfa/verify: no incluye access_token")
        return 1

    estado_me, cuerpo_me = _pedir(
        "GET", f"{base}/api/v1/auth/me", None, access_token, company_id
    )

    permisos: list[str] = []
    if estado_me == 200 and isinstance(cuerpo_me, dict):
        permisos = [
            str(p)
            for p in cuerpo_me.get("permissions", [])
            if isinstance(p, str)
        ]

    if estado_me != 200 or not any(p.startswith("gobierno") for p in permisos):
        print("FALLA auth/me: no responde 200 o no tiene permisos de gobierno")
        return 1

    rutas = [
        f"/api/v1{ruta.strip()}"
        for ruta in os.environ["UAT_SMOKE_PATHS"].split(",")
        if ruta.strip().startswith("/") and ruta.strip()
    ]

    for ruta in rutas:
        estado_ruta, _ = _pedir(
            "GET", f"{base}{ruta}", None, access_token, company_id
        )
        if estado_ruta != 200:
            print(f"FALLA ruta {ruta}: responde {estado_ruta}")
            return 1

    estado_logout, _ = _pedir(
        "POST", f"{base}/api/v1/auth/logout", None, access_token, company_id
    )
    if estado_logout != 200:
        print(f"FALLA logout: responde {estado_logout}")
        return 1

    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
