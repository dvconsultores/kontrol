"""Ejecutor del preflight multiempresa (ARCH-MC-001, fase N4).

Recorre las tablas de alcance de empresa, clasifica sus filas y produce el
informe. **No modifica nada**: ni una fila, ni el esquema, ni la versión de
Alembic. Se comprueba al final comparando conteos antes y después.
"""

from __future__ import annotations

import json
from dataclasses import asdict

from sqlalchemy import create_engine, text

from app.core.database import init_models
from app.core.mc.preflight import (
    CRITICOS,
    MC,
    Plan,
    autoridades_de,
    clasificar_tabla,
    historia_de_empresas,
)
from app.core.scope import Scope, declared_scope


def _modelos():
    import importlib
    import pkgutil

    import app.modules as M

    salida = {}
    for m in pkgutil.iter_modules(M.__path__):
        try:
            mod = importlib.import_module(f"app.modules.{m.name}.models")
        except Exception:  # noqa: BLE001
            continue
        for o in vars(mod).values():
            t = getattr(o, "__tablename__", None)
            if t and getattr(o, "__module__", "") == mod.__name__:
                salida[t] = (m.name, o)
    return salida


def planes() -> list[Plan]:
    """Tablas que necesitan reconstruir su empresa, con sus rutas."""
    init_models()
    modelos = _modelos()
    con_empresa = {t for t, (_, o) in modelos.items()
                   if "company_id" in o.__table__.c}
    salida = []
    for tabla, (modulo, modelo) in sorted(modelos.items()):
        if declared_scope(modelo) is not Scope.COMPANY:
            continue
        if "company_id" not in modelo.__table__.c:
            continue          # derivada: no tiene columna que reconstruir
        if modelo.__table__.c["company_id"].foreign_keys:
            continue          # ya correcta
        salida.append(Plan(tabla=tabla, modulo=modulo,
                           criticidad=CRITICOS.get(modulo),
                           autoridades=autoridades_de(modelo.__table__, con_empresa)))
    return salida


def _conteos(cx, tablas):
    return {t: cx.execute(text(f"SELECT count(*) FROM {t}")).scalar_one() for t in tablas}


def ejecutar(url: str, *, forzar_solo_lectura: bool = True) -> dict:
    """Ejecuta el preflight y devuelve el informe. **Cero escrituras.**

    La garantía es de dos capas y a propósito:

    1. Este ejecutor solo emite `SELECT`.
    2. La transacción se declara `READ ONLY` en PostgreSQL, de modo que un
       `UPDATE` accidental sería rechazado por el motor.

    Confiar solo en la primera sería confiar en la disciplina del código. Sobre
    una copia de datos reales eso no basta.
    """
    ps = planes()
    e = create_engine(url, future=True)
    with e.connect() as cx:
        if forzar_solo_lectura:
            cx.execute(text("SET TRANSACTION READ ONLY"))
        tablas = [p.tabla for p in ps]
        antes = _conteos(cx, tablas)
        alembic_antes = cx.execute(text("SELECT version_num FROM alembic_version")).scalar_one()

        historia = historia_de_empresas(cx)
        empresas = {str(r[0]) for r in cx.execute(text("SELECT id FROM companies")).all()}
        tenants = {str(r[0]) for r in cx.execute(text("SELECT id FROM tenants")).all()}

        resultados = [clasificar_tabla(cx, p, historia, empresas, tenants) for p in ps]

        despues = _conteos(cx, tablas)
        alembic_despues = cx.execute(text("SELECT version_num FROM alembic_version")).scalar_one()

    total = {c.value: 0 for c in MC}
    for r in resultados:
        for k, v in r.por_clase.items():
            total[k] = total.get(k, 0) + v

    return {
        "tablas": len(ps),
        "filas": sum(r.filas for r in resultados),
        "total": total,
        "resultados": [asdict(r) for r in resultados],
        "tenants": len(tenants),
        "empresas": len(empresas),
        "cero_escrituras": {
            "conteos_iguales": antes == despues,
            "alembic_igual": alembic_antes == alembic_despues,
            "alembic": alembic_antes,
        },
    }


if __name__ == "__main__":       # pragma: no cover
    import sys

    print(json.dumps(ejecutar(sys.argv[1]), ensure_ascii=False, default=str))
