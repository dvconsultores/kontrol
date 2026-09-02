"""Arquitectura de los maestros comerciales — Spec 012.

Fallan en construcción, no en ejecución. Las guardas generales de
`test_architecture_scope.py` ya cubren el alcance declarado, las rutas
derivadas y las rutas que reciben un id sin ver el contexto; aquí se comprueba
lo propio de esta Spec.
"""

from __future__ import annotations

import inspect

from app.core.database import Base, init_models
from app.core.scope import Scope, declared_scope, scope_authority

init_models()

#: Las once, tal como las fija `commercial-scope-matrix.md`.
DIRECTAS = {
    "payment_terms", "commercial_zones", "sales_channels", "price_lists",
    "price_precedence", "discount_policies", "credit_policies",
    "sales_commission_policies",
}
DERIVADAS = {
    "price_list_versions": "price_list_id → price_lists",
    "price_list_items": "version_id → price_list_versions",
    "customer_commercial_terms": "customer_id → customers",
}


def _modelos_comerciales():
    return [m.class_ for m in Base.registry.mappers
            if m.class_.__module__.endswith("commercial.models")]


def test_existen_las_once_entidades():
    tablas = {m.__tablename__ for m in _modelos_comerciales()}
    esperadas = DIRECTAS | set(DERIVADAS)
    assert tablas == esperadas, (
        f"faltan: {sorted(esperadas - tablas)} · sobran: {sorted(tablas - esperadas)}")


def test_las_once_son_de_empresa():
    otras = [m.__tablename__ for m in _modelos_comerciales()
             if declared_scope(m) is not Scope.COMPANY]
    assert otras == [], (
        f"maestros comerciales que no son de empresa: {otras}. Dos empresas del mismo "
        "grupo tienen precios y plazos distintos; una entidad de tenant lo desmentiría")


def test_las_ocho_directas_llevan_su_empresa_con_referencia_real():
    malos = []
    for m in _modelos_comerciales():
        if m.__tablename__ not in DIRECTAS:
            continue
        col = m.__table__.c.get("company_id")
        if col is None:
            malos.append(f"{m.__tablename__}: sin `company_id`")
        elif col.nullable:
            malos.append(f"{m.__tablename__}.company_id: anulable")
        elif {f.column.table.name for f in col.foreign_keys} != {"companies"}:
            malos.append(f"{m.__tablename__}.company_id: sin referencia a `companies`")
    assert malos == [], "\n  ".join(["empresas directas mal declaradas:", *malos])


def test_las_tres_derivadas_declaran_su_ruta_y_no_duplican_la_empresa():
    malos = []
    for m in _modelos_comerciales():
        tabla = m.__tablename__
        if tabla not in DERIVADAS:
            continue
        if scope_authority(m) != DERIVADAS[tabla]:
            malos.append(f"{tabla}: ruta «{scope_authority(m)}», se esperaba «{DERIVADAS[tabla]}»")
        if "company_id" in m.__table__.c:
            malos.append(f"{tabla}: lleva `company_id` redundante")
    assert malos == [], "\n  ".join(["rutas derivadas mal declaradas:", *malos])


def test_la_unicidad_de_los_maestros_directos_incluye_la_empresa():
    """Dos empresas del mismo grupo pueden usar el mismo código."""
    malos = []
    for m in _modelos_comerciales():
        if m.__tablename__ not in DIRECTAS:
            continue
        uniques = [c for c in m.__table__.constraints
                   if c.__class__.__name__ == "UniqueConstraint"]
        for u in uniques:
            if "company_id" not in {c.name for c in u.columns}:
                malos.append(f"{m.__tablename__}.{u.name}: no incluye la empresa")
    assert malos == [], "\n  ".join(["unicidad sin alcance de empresa:", *malos])


def test_ningun_importe_es_de_coma_flotante():
    """`NFR-012-06`. La Spec 011 dejó cara esta lección."""
    from sqlalchemy import Float

    malos = []
    for m in _modelos_comerciales():
        for col in m.__table__.columns:
            if isinstance(col.type, Float):
                malos.append(f"{m.__tablename__}.{col.name}")
    assert malos == [], f"columnas en coma flotante: {malos}"


def test_ningun_esquema_de_entrada_acepta_la_empresa():
    """El cuerpo nunca decide la empresa.

    Se mira el módulo entero: si un esquema nuevo la declarara, esta prueba lo
    dice antes de que llegue a producción. Es la vulnerabilidad que la Spec 045
    estrenó y que el contrato documental retiró de los dos resolutores.
    """
    from pydantic import BaseModel

    from app.modules.commercial import api

    culpables = []
    for nombre, objeto in vars(api).items():
        if not (inspect.isclass(objeto) and issubclass(objeto, BaseModel)):
            continue
        if "company_id" in getattr(objeto, "model_fields", {}):
            culpables.append(nombre)
    assert culpables == [], (
        f"esquemas de entrada que declaran la empresa: {culpables}. La pone `CompanyContext`")


def test_los_esquemas_de_entrada_prohiben_campos_desconocidos():
    """No basta con no declararla: hay que rechazarla.

    Con `extra='ignore'`, un cuerpo con `company_id` pasaría inadvertido y el
    cliente creería estar operando donde no está.
    """
    from pydantic import BaseModel

    from app.modules.commercial import api

    permisivos = []
    for nombre, objeto in vars(api).items():
        if not (inspect.isclass(objeto) and issubclass(objeto, BaseModel)):
            continue
        if nombre in ("BaseModel", "Estricto"):
            continue
        if objeto.model_config.get("extra") != "forbid":
            permisivos.append(nombre)
    assert permisivos == [], f"esquemas que aceptan campos desconocidos: {permisivos}"
