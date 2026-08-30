"""Alcance canónico de las entidades persistentes (ADR-D0-014, ARCH-MC-001).

La cadena de KONTROL es `Installation → Tenant → Company → Branch → operación`.
Antes de esta remediación, 90 columnas llamadas `company_id` guardaban el
`tenant_id`: el nombre decía una cosa y el dato era otra. Este módulo existe para
que eso no pueda volver a ocurrir en silencio.

Cada modelo declara su alcance. Los que no llevan columna de ámbito propia
declaran la **ruta obligatoria** por la que se llega a su empresa. Una ruta que
puede ser nula no es una ruta: sería una conjetura con sintaxis de garantía.
"""

from __future__ import annotations

from enum import Enum


class Scope(str, Enum):
    """Alcance de una entidad persistente. No existe `UNKNOWN` a propósito."""

    #: Igual para toda instalación; no pertenece a nadie.
    GLOBAL = "GLOBAL"
    #: De la instalación: licencia, homologación, versión fiscal.
    INSTALLATION = "INSTALLATION"
    #: Del tenant, compartido por todas sus empresas.
    TENANT = "TENANT"
    #: De una empresa jurídica concreta.
    COMPANY = "COMPANY"
    #: De una sucursal.
    BRANCH = "BRANCH"


class ScopedModel:
    """Mezcla declarativa. No añade columnas: solo obliga a decir la verdad.

    - `__scope__` es obligatorio en todo modelo persistente.
    - `__scope_authority__` solo en los que **no** llevan columna propia: dice
      por qué relación se alcanza la empresa, en la forma `"columna → tabla"`.
    """

    __scope__: Scope
    __scope_authority__: str | None = None


def declared_scope(model: type) -> Scope | None:
    return getattr(model, "__scope__", None)


def scope_authority(model: type) -> str | None:
    return getattr(model, "__scope_authority__", None)
