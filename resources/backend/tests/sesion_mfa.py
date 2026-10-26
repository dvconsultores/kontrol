"""Arnés de sesión para las suites amplias ajenas al MFA.

Recorre el ciclo MFA real por la API (alta por desafío o verificación TOTP)
cuando un login devuelve `MFA_ENROLLMENT_REQUIRED` o `MFA_REQUIRED`. Los
secretos TOTP viven solo en memoria del proceso; no hay atajos del producto.
Las pruebas MFA dedicadas no usan este arnés.

El registro en memoria sigue a la base de datos (motor): sobrevive a un
"reinicio" que crea otra aplicación sobre la misma base; una base nueva
empieza vacía.
"""

from __future__ import annotations

import inspect
import weakref
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from mfa_apoyo import codigo_totp

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

_REGISTROS: weakref.WeakKeyDictionary[Engine, dict[tuple[str, str], dict]] = (
    weakref.WeakKeyDictionary()
)


class RelojDeSuite:
    """Reloj monótono de suite que sustituye a `app.core.clock.now`.

    El desfase solo crece cuando hace falta un paso TOTP nuevo para un usuario,
    de modo que nunca hay esperas ni pasos repetidos.
    """

    def __init__(self) -> None:
        self._desfase = timedelta(0)

    def ahora(self) -> datetime:
        return datetime.now(UTC) + self._desfase

    def paso_libre(self, ultimo_paso: int | None) -> int:
        paso = int(self.ahora().timestamp()) // 30
        if ultimo_paso is not None and paso <= ultimo_paso:
            objetivo = (ultimo_paso + 1) * 30
            self._desfase += timedelta(seconds=objetivo - self.ahora().timestamp())
        return int(self.ahora().timestamp()) // 30


def _reloj_activo():
    """Devuelve el objeto de reloj instalado en `app.core.clock.now`.

    Si es `RelojDeSuite` devuelve esa instancia; si es un `RelojMfa` devuelve
    ese otro objeto, que expone `ahora()` y `siguiente_paso()`.
    """
    import app.core.clock

    reloj = getattr(app.core.clock.now, "__self__", None)
    return reloj


def _motor(client) -> Engine:
    """Motor de base de datos al que apunta la aplicación bajo prueba."""
    from app.core.database import get_db

    proveedor = client.app.dependency_overrides.get(get_db, get_db)
    obtenido = proveedor()
    if inspect.isgenerator(obtenido):
        try:
            db = next(obtenido)
        finally:
            obtenido.close()
    else:
        db = obtenido
    return db.get_bind()


def _registro(client) -> dict[tuple[str, str], dict]:
    """Registro en memoria por base de datos (motor): sobrevive a un "reinicio"
    que crea otra aplicación sobre la misma base; una base nueva empieza vacía.
    """
    return _REGISTROS.setdefault(_motor(client), {})


def _paso_nuevo(ultimo: int | None) -> int:
    reloj = _reloj_activo()
    if isinstance(reloj, RelojDeSuite):
        return reloj.paso_libre(ultimo)
    paso = int(reloj.ahora().timestamp()) // 30
    if ultimo is not None and paso <= ultimo:
        while paso <= ultimo:
            reloj.siguiente_paso()
            paso = int(reloj.ahora().timestamp()) // 30
    return paso


def _instante_del_paso(paso: int) -> datetime:
    return _reloj_activo().ahora()


def login_completo(client, url: str, **kwargs):
    """Sustituto directo de `client.post(url, **kwargs)` para el login.

    Si la respuesta no exige MFA, se devuelve tal cual. Si exige alta o
    verificación TOTP, se completa el ciclo real por la API y se devuelve la
    respuesta final del producto.
    """
    r = client.post(url, **kwargs)
    cuerpo_respuesta = r.json()
    if r.status_code != 200 or cuerpo_respuesta.get("status") not in {
        "MFA_REQUIRED",
        "MFA_ENROLLMENT_REQUIRED",
    }:
        return r

    cuerpo = kwargs["json"]
    tenant = cuerpo["tenant_code"]
    usuario = cuerpo["username"]
    prefijo = url.rsplit("/auth/login", 1)[0]
    registro = _registro(client)
    clave_registro = (tenant, usuario)

    if cuerpo_respuesta.get("status") == "MFA_ENROLLMENT_REQUIRED":
        challenge_token = cuerpo_respuesta["challenge_token"]
        r = client.post(
            f"{prefijo}/auth/mfa/enrollment",
            json={"challenge_token": challenge_token},
        )
        assert r.status_code == 200, r.text
        clave = r.json()["manual_key"]
        paso = _paso_nuevo(None)
        codigo = codigo_totp(clave, _instante_del_paso(paso))
        r = client.post(
            f"{prefijo}/auth/mfa/enrollment/confirm",
            json={"challenge_token": challenge_token, "code": codigo},
        )
        registro[clave_registro] = {"clave_manual": clave, "ultimo_paso": paso}
        return r

    # MFA_REQUIRED
    if clave_registro not in registro:
        raise AssertionError(
            "el usuario tiene factor de otra ejecución; el arnés solo conoce "
            "los factores dados de alta en este proceso"
        )
    challenge_token = cuerpo_respuesta["challenge_token"]
    item = registro[clave_registro]
    paso = _paso_nuevo(item["ultimo_paso"])
    codigo = codigo_totp(item["clave_manual"], _instante_del_paso(paso))
    r = client.post(
        f"{prefijo}/auth/mfa/verify",
        json={"challenge_token": challenge_token, "code": codigo},
    )
    item["ultimo_paso"] = paso
    return r


def cabeceras(
    client,
    tenant_code: str,
    username: str,
    password: str,
    url: str = "/api/v1/auth/login",
) -> dict[str, str]:
    """Inicia sesión con el ciclo MFA real y devuelve la cabecera Authorization."""
    r = login_completo(
        client,
        url,
        json={"tenant_code": tenant_code, "username": username, "password": password},
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
