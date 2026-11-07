"""Catálogo cerrado de auditoría (FR-001-257, FR-001-258, FR-001-259,
FR-001-260, FR-001-265).

OD-AUD-04: el catálogo es cerrado y la validación falla cerrada. OD-AUD-08/09:
el detalle es mínimo, sin firmas de amenaza ni contenido sensible.

La clave de una entrada es el par (acción, entidad): existen códigos genéricos
históricos que solo se distinguen por la entidad sobre la que actúan.
"""

from __future__ import annotations

import functools
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

CATALOG_VERSION = "2026-11-07.2"
RETENTION_PRESERVE = "PRESERVE_UNTIL_RETENTION_POLICY_RATIFIED"
SCOPES = frozenset({"COMPANY", "TENANT"})
SECURITY_CLASSES = frozenset(
    {
        "SECURITY",
        "AUTHORITY",
        "FINANCIAL",
        "FISCAL",
        "REGULATORY",
        "DOCUMENT",
        "MASTER_DATA",
        "OPERATIONAL",
    }
)
TRANSACTION_CLASSES = frozenset(
    {"BUSINESS_COMMIT", "REJECTION", "SECURITY_DENIAL"}
)
LIFECYCLES = frozenset({"ACTIVE", "DEPRECATED", "LEGACY"})
EMISSIONS = frozenset({"STATIC", "DYNAMIC", "MIGRATION", "SETUP", "RESERVED"})
FORBIDDEN_DETAIL_KEYS = frozenset(
    {
        "password",
        "password_hash",
        "new_password",
        "current_password",
        "token",
        "access_token",
        "refresh_token",
        "reset_token",
        "secret",
        "totp_secret",
        "mfa_secret",
        "otp",
        "otp_code",
        "totp_code",
        "recovery_code",
        "recovery_codes",
        "authorization",
        "bearer",
        "cookie",
        "api_key",
        "private_key",
        "signature",
        "threat_name",
        "malware_signature",
        "content",
        "file_content",
        "raw",
        "bytes",
        "body",
        "storage_key",
        "path",
        "file_path",
        "local_path",
        "temp_path",
        "url",
        "temporary_url",
        "presigned_url",
        "original_name",
        "filename",
    }
)
UNCATALOGUED_SCOPE = "UNCATALOGUED"


def keys(*names: str) -> frozenset[str]:
    """Devuelve `frozenset(names)` para escribir entradas de forma concisa."""
    return frozenset(names)


@dataclass(frozen=True)
class AuditActionSpec:
    """Entrada del catálogo cerrado de auditoría."""

    code: str
    entity_type: str
    owner_module: str
    owner_spec: str
    scope: str
    security_class: str
    transaction_class: str
    detail_keys: frozenset[str]
    label: str
    lifecycle: str = "ACTIVE"
    emission: str = "STATIC"
    emitted_by: str = ""
    tenant_required: bool = True
    retention: str = RETENTION_PRESERVE

    @property
    def key(self) -> tuple[str, str]:
        return (self.code, self.entity_type)


class AuditContractError(ValueError):
    """Error de contrato de auditoría con código estable."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(f"{code}: {message}")


def _validate_entry(entry: AuditActionSpec) -> None:
    """Valida una entrada; lanza `ValueError` con la clave en el mensaje."""
    clave = entry.key
    if entry.scope not in SCOPES:
        raise ValueError(f"Clave {clave!r}: scope {entry.scope!r} no válido")
    if entry.security_class not in SECURITY_CLASSES:
        raise ValueError(
            f"Clave {clave!r}: security_class {entry.security_class!r} no válida"
        )
    if entry.transaction_class not in TRANSACTION_CLASSES:
        raise ValueError(
            f"Clave {clave!r}: transaction_class {entry.transaction_class!r} "
            "no válida"
        )
    if entry.lifecycle not in LIFECYCLES:
        raise ValueError(
            f"Clave {clave!r}: lifecycle {entry.lifecycle!r} no válido"
        )
    if entry.emission not in EMISSIONS:
        raise ValueError(
            f"Clave {clave!r}: emission {entry.emission!r} no válida"
        )
    if not entry.label or not entry.label.strip():
        raise ValueError(f"Clave {clave!r}: label vacío")
    detail_lower = {nombre.lower() for nombre in entry.detail_keys}
    if detail_lower & FORBIDDEN_DETAIL_KEYS:
        raise ValueError(
            f"Clave {clave!r}: detail_keys contiene claves prohibidas"
        )
    if entry.emission != "STATIC" and not entry.emitted_by:
        raise ValueError(
            f"Clave {clave!r}: emisión {entry.emission!r} sin emitted_by"
        )
    if entry.scope == "COMPANY" and not entry.tenant_required:
        raise ValueError(
            f"Clave {clave!r}: entrada COMPANY siempre requiere tenant"
        )


def build_catalog(
    entries: Iterable[AuditActionSpec],
) -> Mapping[tuple[str, str], AuditActionSpec]:
    """Construye un catálogo inmutable validando todas sus entradas."""
    result: dict[tuple[str, str], AuditActionSpec] = {}
    for entry in entries:
        clave = entry.key
        if clave in result:
            raise ValueError(f"Clave {clave!r}: entrada duplicada")
        _validate_entry(entry)
        result[clave] = entry
    return MappingProxyType(result)


@functools.cache
def catalog() -> Mapping[tuple[str, str], AuditActionSpec]:
    """Devuelve el catálogo real del sistema.

    El módulo `audit_catalog_entries` lo crea otra tarea; se importa dentro de
    la función para no inyectar dependencias de módulo en la carga inicial.
    """
    from app.shared.audit_catalog_entries import ENTRIES

    return build_catalog(ENTRIES)


def lookup(
    action: str,
    entity_type: str,
    *,
    catalog_map: Mapping[tuple[str, str], AuditActionSpec] | None = None,
) -> AuditActionSpec | None:
    """Busca una entrada del catálogo; `catalog_map` para pruebas."""
    mapa = catalog_map if catalog_map is not None else catalog()
    return mapa.get((action, entity_type))


def _contains_forbidden(value: object) -> bool:
    """Recorre recursivamente en busca de claves o valores binarios prohibidos."""
    if isinstance(value, dict):
        for clave, elemento in value.items():
            if isinstance(clave, str) and clave.lower() in FORBIDDEN_DETAIL_KEYS:
                return True
            if _contains_forbidden(elemento):
                return True
    elif isinstance(value, list | tuple | set):
        for elemento in value:
            if _contains_forbidden(elemento):
                return True
    elif isinstance(value, bytes | bytearray | memoryview):
        return True
    return False


def _validate_section(
    nombre: str, seccion: object, detail_keys: frozenset[str]
) -> None:
    """Valida una sección a nivel de primer nivel y de contenido prohibido."""
    if seccion is None:
        return
    if not isinstance(seccion, dict):
        raise AuditContractError(
            "AUDIT_DETAIL_NOT_OBJECT",
            f"La sección {nombre} debe ser un objeto",
        )
    if _contains_forbidden(seccion):
        raise AuditContractError(
            "AUDIT_DETAIL_FORBIDDEN",
            f"La sección {nombre} contiene claves o valores prohibidos",
        )
    for clave in seccion:
        if clave not in detail_keys:
            raise AuditContractError(
                "AUDIT_DETAIL_KEY_NOT_ALLOWED",
                f"La sección {nombre} incluye la clave no permitida {clave!r}",
            )


def validate_event(
    *,
    action: str,
    entity_type: str,
    tenant_id: str | None,
    company_id: str | None,
    before: object,
    after: object,
    evidence: object,
    catalog_map: Mapping[tuple[str, str], AuditActionSpec] | None = None,
) -> AuditActionSpec:
    """Valida un evento antes de persistirlo; falla cerrada."""
    entry = lookup(action, entity_type, catalog_map=catalog_map)
    if entry is None:
        raise AuditContractError(
            "AUDIT_ACTION_UNCATALOGUED",
            f"Acción no catalogada: {action}/{entity_type}",
        )
    if entry.lifecycle == "LEGACY":
        raise AuditContractError(
            "AUDIT_ACTION_LEGACY",
            f"Acción legacy solo interpreta historia: {action}/{entity_type}",
        )
    if entry.scope == "COMPANY" and (company_id is None or company_id == ""):
        raise AuditContractError(
            "AUDIT_COMPANY_REQUIRED",
            f"La acción {action}/{entity_type} requiere empresa",
        )
    if entry.scope == "TENANT" and company_id is not None:
        raise AuditContractError(
            "AUDIT_SCOPE_MISMATCH",
            f"La acción {action}/{entity_type} no admite empresa",
        )
    if (tenant_id is None or tenant_id == "") and entry.tenant_required:
        raise AuditContractError(
            "AUDIT_TENANT_REQUIRED",
            f"La acción {action}/{entity_type} requiere tenant",
        )
    _validate_section("before", before, entry.detail_keys)
    _validate_section("after", after, entry.detail_keys)
    _validate_section("evidence", evidence, entry.detail_keys)
    return entry


def _safe_value(value: object) -> object:
    """Proyecta un valor para lectura eliminando contenido prohibido."""
    if isinstance(value, dict):
        result: dict[str, object] = {}
        for clave, elemento in value.items():
            if isinstance(clave, str) and clave.lower() in FORBIDDEN_DETAIL_KEYS:
                continue
            result[clave] = _safe_value(elemento)
        return result
    if isinstance(value, list | tuple):
        return [_safe_value(elemento) for elemento in value]
    if isinstance(value, set | frozenset):
        return [_safe_value(elemento) for elemento in value]
    if isinstance(value, bytes | bytearray | memoryview):
        return "[binario omitido]"
    return value


def _safe_section(
    seccion: object, detail_keys: frozenset[str]
) -> dict[str, object] | None:
    """Filtra una sección a nivel de primer nivel y proyecta valores seguros."""
    if not isinstance(seccion, dict):
        return None
    result: dict[str, object] = {}
    for clave, valor in seccion.items():
        if clave not in detail_keys:
            continue
        result[clave] = _safe_value(valor)
    if not result:
        return None
    return result


def safe_details(
    action: str,
    entity_type: str,
    before: object,
    after: object,
    evidence: object,
    *,
    catalog_map: Mapping[tuple[str, str], AuditActionSpec] | None = None,
) -> dict[str, dict[str, object]]:
    """Proyecta el detalle para lectura (filas actuales e históricas)."""
    entry = lookup(action, entity_type, catalog_map=catalog_map)
    if entry is None:
        return {}
    resultado: dict[str, dict[str, object]] = {}
    secciones = (
        ("before", before),
        ("after", after),
        ("evidence", evidence),
    )
    for nombre, seccion in secciones:
        filtrada = _safe_section(seccion, entry.detail_keys)
        if filtrada is not None:
            resultado[nombre] = filtrada
    return resultado


def scope_of(
    action: str,
    entity_type: str,
    *,
    catalog_map: Mapping[tuple[str, str], AuditActionSpec] | None = None,
) -> str:
    """Devuelve el scope de una entrada o `UNCATALOGUED_SCOPE`."""
    entry = lookup(action, entity_type, catalog_map=catalog_map)
    if entry is None:
        return UNCATALOGUED_SCOPE
    return entry.scope


def label_of(
    action: str,
    entity_type: str,
    *,
    catalog_map: Mapping[tuple[str, str], AuditActionSpec] | None = None,
) -> str:
    """Devuelve la etiqueta de una entrada o la propia acción si no existe."""
    entry = lookup(action, entity_type, catalog_map=catalog_map)
    if entry is None:
        return action
    return entry.label


def public_actions(
    *,
    catalog_map: Mapping[tuple[str, str], AuditActionSpec] | None = None,
) -> list[dict[str, str]]:
    """Proyección pública del catálogo, sin claves sensibles ni internas."""
    mapa = catalog_map if catalog_map is not None else catalog()
    acciones: list[dict[str, str]] = []
    for entrada in mapa.values():
        acciones.append(
            {
                "code": entrada.code,
                "entity_type": entrada.entity_type,
                "label": entrada.label,
                "scope": entrada.scope,
                "lifecycle": entrada.lifecycle,
            }
        )
    acciones.sort(key=lambda item: (item["code"], item["entity_type"]))
    return acciones
