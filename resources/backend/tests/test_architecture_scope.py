"""Pruebas de arquitectura del alcance canónico (ARCH-MC-001, ADR-D0-014).

Estas pruebas existen para que el defecto no pueda volver. No comprueban un
comportamiento: comprueban que el código no pueda volver a mentir sobre a quién
pertenece un dato.

Fallan en construcción, no en ejecución.
"""

from __future__ import annotations

import ast
import pathlib
import re
from pathlib import Path

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


def test_la_empresa_en_una_tabla_de_tenant_es_un_estrechamiento():
    """Una tabla de tenant **sí** puede llevar `company_id`, con dos condiciones.

    La versión anterior de esta prueba lo prohibía salvo para cuatro tablas
    permitidas a mano, y la lista se quedó corta: seis más lo llevan con pleno
    sentido. Un rol puede valer en todo el tenant o solo en una empresa; una
    moneda puede ser nacional o propia; un registro de idempotencia puede
    acotarse. En todos esos casos la empresa **estrecha** el alcance, no lo
    define.

    Lo que sí debe cumplirse, y es lo que se comprueba:

    - la columna admite nulo, porque el nulo significa «todas» y sin él no
      habría estrechamiento posible;
    - y referencia a `companies`, porque una empresa nula significa todas pero
      una empresa inventada no significa nada.

    El segundo punto lo destapó N7: nueve de estas columnas no referenciaban
    nada, y quedaron fuera de la primera tanda de claves foráneas precisamente
    porque se clasificó por alcance del modelo.
    """
    problemas = []
    for m in MODELOS:
        if declared_scope(m) is not Scope.TENANT or "company_id" not in m.__table__.c:
            continue
        col = m.__table__.c["company_id"]
        if not col.nullable:
            problemas.append(f"{m.__tablename__}: obligatoria, no es un estrechamiento")
        if {f.column.table.name for f in col.foreign_keys} != {"companies"}:
            problemas.append(f"{m.__tablename__}: sin referencia a companies")
    assert problemas == [], "\n  ".join(["empresa mal declarada en tablas de tenant:", *problemas])


# ===================================================================== N5
# Dos familias que buscan por estructura lo que ninguna prueba de dominio ve:
# rutas que cargan una entidad de empresa sin comprobar la empresa, y rutas que
# dejan al cliente decidir en qué empresa escribe.
#
# Se apoyan en el AST y en las dependencias declaradas, no en comentarios ni en
# nombres: un comentario se puede escribir y seguir teniendo el defecto.

_MODULOS_DE_NEGOCIO = (
    "approvals", "documents", "fiscal", "inventory", "master_data",
    "organization", "purchasing", "regulatory", "reporting", "sales", "treasury",
)


def _archivos_de_api() -> list[Path]:
    raiz = Path(__file__).resolve().parents[1] / "app" / "modules"
    return [f for m in _MODULOS_DE_NEGOCIO for f in sorted((raiz / m).glob("*api*.py"))]


def _rutas(arbol: ast.Module) -> list[ast.FunctionDef]:
    fuera = []
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.FunctionDef):
            continue
        for dec in nodo.decorator_list:
            objetivo = dec.func if isinstance(dec, ast.Call) else dec
            if (isinstance(objetivo, ast.Attribute) and isinstance(objetivo.value, ast.Name)
                    and objetivo.value.id == "router"):
                fuera.append(nodo)
                break
    return fuera


def _recibe_contexto(fn: ast.FunctionDef) -> bool:
    for arg in list(fn.args.args) + list(fn.args.kwonlyargs):
        anotacion = getattr(arg, "annotation", None)
        if isinstance(anotacion, ast.Name) and anotacion.id == "CompanyContext":
            return True
    return False


def test_ninguna_ruta_de_empresa_carga_una_entidad_sin_acotarla():
    """Familia 1 — la clase de defecto que `deactivate_party` estrenó.

    Aquella ruta no confundía el tenant con la empresa: sencillamente **no
    comparaba nada**, y por eso el barrido de N2 —que buscaba el patrón
    `company_id = tenant_id`— no podía verla. Desactivaba un tercero de
    cualquier empresa y respondía 200.

    Esta prueba busca la forma estructural del defecto: una ruta que recibe un
    identificador por la URL y carga la entidad con `db.get(...)`, sin que en
    todo el cuerpo aparezca el contexto de empresa.
    """
    culpables: list[str] = []
    for archivo in _archivos_de_api():
        arbol = ast.parse(archivo.read_text())
        for fn in _rutas(arbol):
            nombres = {a.arg for a in fn.args.args}
            if not any(n.endswith("_id") for n in nombres):
                continue
            carga = any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                        and n.func.attr == "get" and isinstance(n.func.value, ast.Name)
                        and n.func.value.id == "db" for n in ast.walk(fn))
            if not carga:
                continue
            usa_ctx = any(isinstance(n, ast.Name) and n.id == "ctx" for n in ast.walk(fn))
            if not (usa_ctx or _recibe_contexto(fn)):
                culpables.append(f"{archivo.parent.name}/{archivo.name}::{fn.name}")
    assert not culpables, (
        "rutas que cargan una entidad por id sin contexto de empresa:\n  "
        + "\n  ".join(culpables))


def test_ninguna_ruta_deja_que_el_cuerpo_elija_la_empresa():
    """Familia 2 — la vulnerabilidad que se demostró en la Spec 045.

    Operando en la empresa A se declaraba la empresa B en el cuerpo y la
    política quedaba guardada en B: el cliente elegía dónde escribir. Desde otro
    tenant se podía escribir dentro de este.

    Aquí se busca cualquier ruta que pase `body.company_id` a un servicio o a un
    modelo sin haberlo contrastado antes con el contexto validado.
    """
    culpables: list[str] = []
    for archivo in _archivos_de_api():
        texto = archivo.read_text()
        arbol = ast.parse(texto)
        for fn in _rutas(arbol):
            usos = [n for n in ast.walk(fn)
                    if isinstance(n, ast.Attribute) and n.attr == "company_id"
                    and isinstance(n.value, ast.Name) and n.value.id == "body"]
            if not usos:
                continue
            cuerpo = ast.get_source_segment(texto, fn) or ""
            contrastado = ("_empresa(ctx" in cuerpo
                           or "!= ctx.company_id" in cuerpo
                           or "== ctx.company_id" in cuerpo)
            if not contrastado:
                culpables.append(f"{archivo.parent.name}/{archivo.name}::{fn.name}")
    assert not culpables, (
        "rutas donde el cuerpo puede imponer la empresa:\n  " + "\n  ".join(culpables))
