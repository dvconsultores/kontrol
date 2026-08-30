"""Pruebas de arquitectura del alcance canónico (ARCH-MC-001, ADR-D0-014).

Estas pruebas existen para que el defecto no pueda volver. No comprueban un
comportamiento: comprueban que el código no pueda volver a mentir sobre a quién
pertenece un dato.

Fallan en construcción, no en ejecución.
"""

from __future__ import annotations

import pathlib
import re

from app.core.database import init_models
from app.core.scope import Scope, declared_scope, scope_authority

RAIZ = pathlib.Path(__file__).resolve().parent.parent / "app"
init_models()


def _modelos():
    import importlib
    import pkgutil

    import app.modules as M

    salida = []
    for m in pkgutil.iter_modules(M.__path__):
        try:
            mod = importlib.import_module(f"app.modules.{m.name}.models")
        except Exception:  # noqa: BLE001
            continue
        for o in vars(mod).values():
            if getattr(o, "__tablename__", None) and getattr(o, "__module__", "") == mod.__name__:
                salida.append(o)
    return salida


MODELOS = _modelos()


# --------------------------------------------------------------------------
def test_all_persistent_models_have_declared_scope():
    """Ninguna entidad persistente sin alcance. No existe `UNKNOWN`."""
    sin = [m.__tablename__ for m in MODELOS if declared_scope(m) is None]
    assert sin == [], f"{len(sin)} modelos sin `__scope__`: {sin[:15]}"


def test_derived_scopes_use_non_nullable_fk_path():
    """Una ruta que puede ser nula no es una ruta.

    Si un modelo declara autoridad, la columna que la implementa debe existir,
    ser clave foránea y **no** admitir nulos. Con una FK anulable, la fila puede
    quedarse sin dueño, que es exactamente lo que esta remediación cierra.
    """
    malos = []
    for m in MODELOS:
        ruta = scope_authority(m)
        if not ruta:
            continue
        col = ruta.split("→")[0].strip()
        c = m.__table__.c.get(col)
        if c is None:
            malos.append(f"{m.__tablename__}: la columna «{col}» no existe")
        elif not c.foreign_keys:
            malos.append(f"{m.__tablename__}.{col}: sin clave foránea")
        elif c.nullable:
            malos.append(f"{m.__tablename__}.{col}: **anulable**")
    assert malos == [], "rutas de derivación inválidas:\n  " + "\n  ".join(malos)


def test_models_without_scope_column_declare_authority():
    """Si no lleva columna de ámbito, tiene que decir por dónde se llega."""
    malos = []
    for m in MODELOS:
        s = declared_scope(m)
        cols = set(m.__table__.c.keys())
        if s is Scope.COMPANY and "company_id" not in cols and not scope_authority(m):
            malos.append(m.__tablename__)
    assert malos == [], f"de empresa, sin columna ni autoridad: {malos}"


# --------------------------------------------------------------------------
_ASIGNA_TENANT = re.compile(
    r"company_id\s*=\s*(?:actor|user|current_user|self\.user)\.tenant_id")
_COMPARA_TENANT = re.compile(
    r"\.company_id\s*==\s*(?:actor|user|current_user)\.tenant_id")


def _fuentes():
    for p in RAIZ.rglob("*.py"):
        if "__pycache__" in p.parts:
            continue
        yield p


def test_no_company_scope_writer_uses_tenant_id():
    """Ningún servicio asigna el tenant a una propiedad llamada `company_id`.

    Es el patrón que produjo el defecto: 100 apariciones cuando se auditó.
    """
    hallazgos = []
    for p in _fuentes():
        for n, linea in enumerate(p.read_text().splitlines(), 1):
            if _ASIGNA_TENANT.search(linea):
                hallazgos.append(f"{p.relative_to(RAIZ.parent)}:{n}")
    assert hallazgos == [], (
        f"{len(hallazgos)} escrituras asignan `tenant_id` a `company_id`:\n  "
        + "\n  ".join(hallazgos[:25]))


def test_no_company_scope_reader_compares_tenant_id():
    """Y ninguna consulta filtra la empresa comparándola con el tenant."""
    hallazgos = []
    for p in _fuentes():
        for n, linea in enumerate(p.read_text().splitlines(), 1):
            if _COMPARA_TENANT.search(linea):
                hallazgos.append(f"{p.relative_to(RAIZ.parent)}:{n}")
    assert hallazgos == [], (
        f"{len(hallazgos)} lecturas comparan `company_id` con `tenant_id`:\n  "
        + "\n  ".join(hallazgos[:25]))


# --------------------------------------------------------------------------
def test_company_id_always_references_company():
    """Si la columna se llama `company_id`, apunta a `companies`."""
    malos = []
    for m in MODELOS:
        c = m.__table__.c.get("company_id")
        if c is None:
            continue
        destinos = {f.column.table.name for f in c.foreign_keys}
        if destinos != {"companies"}:
            malos.append(f"{m.__tablename__}.company_id → {destinos or 'sin FK'}")
    assert malos == [], (
        f"{len(malos)} columnas `company_id` sin FK a `companies`:\n  "
        + "\n  ".join(malos[:25]))


def test_tenant_id_always_references_tenant():
    """Y si se llama `tenant_id`, apunta a `tenants`."""
    malos = []
    for m in MODELOS:
        c = m.__table__.c.get("tenant_id")
        if c is None:
            continue
        destinos = {f.column.table.name for f in c.foreign_keys}
        if destinos != {"tenants"}:
            malos.append(f"{m.__tablename__}.tenant_id → {destinos or 'sin FK'}")
    assert malos == [], (
        f"{len(malos)} columnas `tenant_id` sin FK a `tenants`:\n  "
        + "\n  ".join(malos[:25]))


def test_no_model_declares_scope_it_cannot_honour():
    """Coherencia: quien dice ser del tenant no puede llevar `company_id` propio
    salvo que esa columna designe de verdad una empresa (alcance del usuario)."""
    permitidos = {"user_roles", "user_scopes", "audit_events", "roles"}
    malos = [
        m.__tablename__ for m in MODELOS
        if declared_scope(m) is Scope.TENANT
        and "company_id" in m.__table__.c
        and m.__tablename__ not in permitidos
    ]
    assert malos == [], f"declaran TENANT pero llevan `company_id`: {malos}"
