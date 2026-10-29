"""Escáner de solo lectura para invariantes de alcance entre filas relacionadas.

Comprueba que las relaciones entre filas no cruzan empresas ni tenants salvo
donde el modelo lo permite explícitamente. No escribe nunca en la base de
datos.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import sys
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.engine import Connection, create_engine
from sqlalchemy.sql import Subquery

from app.core.database import Base, init_models
from app.core.scope import Scope, declared_scope, scope_authority


@dataclasses.dataclass(frozen=True)
class Violacion:
    """Una arista o columna que incumple un invariante de alcance."""

    tabla: str
    columna: str
    padre: str
    clase: str  # "CROSS_COMPANY" | "CROSS_TENANT"
    filas: int
    ejemplos: tuple[str, ...]


@dataclasses.dataclass(frozen=True)
class Informe:
    """Resultado de un escaneo de alcance."""

    aristas_comprobadas: int
    violaciones: tuple[Violacion, ...]
    filas_globales: dict[str, int]
    roles_de_instalacion_personalizados: int | None

    @property
    def limpio(self) -> bool:
        return not self.violaciones


def _modelos() -> list[Any]:
    return [m.class_ for m in Base.registry.mappers]


def _modelo_de_tabla() -> dict[str, Any]:
    return {m.__table__.name: m for m in _modelos()}


def _autoridad(cls: Any) -> tuple[str, str] | None:
    texto = scope_authority(cls)
    if not texto:
        return None
    col, tabla = texto.split("→", 1)
    return col.strip(), tabla.strip()


def _empresa_de(
    nombre: str,
    modelos: dict[str, Any],
    profundidad: int = 0,
    rol: str = "",
) -> Subquery | None:
    if profundidad > 5:
        return None
    cls = modelos.get(nombre)
    if cls is None:
        return None
    t = cls.__table__
    if "company_id" in t.c:
        return (
            select(t.c.id.label("id"), t.c.company_id.label("company_id"))
            .select_from(t)
            .subquery(f"emp_{rol}_{nombre}_{profundidad}")
        )
    autoridad = _autoridad(cls)
    if autoridad:
        col, padre = autoridad
        if padre == nombre:
            return None
        p = _empresa_de(padre, modelos, profundidad + 1, rol)
        if p is None:
            return None
        return (
            select(t.c.id.label("id"), p.c.company_id.label("company_id"))
            .select_from(t.join(p, t.c[col] == p.c.id))
            .subquery(f"emp_{rol}_{nombre}_{profundidad}")
        )
    return None


def _tenant_de(
    nombre: str,
    modelos: dict[str, Any],
    profundidad: int = 0,
    rol: str = "",
) -> Subquery | None:
    if profundidad > 5:
        return None
    cls = modelos.get(nombre)
    if cls is None:
        return None
    t = cls.__table__
    if nombre == "tenants":
        return (
            select(t.c.id.label("id"), t.c.id.label("tenant_id"))
            .select_from(t)
            .subquery(f"ten_{rol}_{nombre}_{profundidad}")
        )
    if "tenant_id" in t.c:
        return (
            select(t.c.id.label("id"), t.c.tenant_id.label("tenant_id"))
            .select_from(t)
            .subquery(f"ten_{rol}_{nombre}_{profundidad}")
        )
    if nombre == "companies":
        return None
    e = _empresa_de(nombre, modelos, profundidad + 1, rol)
    if e is not None:
        companies = modelos["companies"].__table__
        return (
            select(t.c.id.label("id"), companies.c.tenant_id.label("tenant_id"))
            .select_from(
                t.join(e, t.c.id == e.c.id).join(
                    companies, companies.c.id == e.c.company_id
                )
            )
            .subquery(f"ten_{rol}_{nombre}_{profundidad}")
        )
    autoridad = _autoridad(cls)
    if autoridad:
        col, padre = autoridad
        if padre == nombre:
            return None
        p = _tenant_de(padre, modelos, profundidad + 1, rol)
        if p is None:
            return None
        return (
            select(t.c.id.label("id"), p.c.tenant_id.label("tenant_id"))
            .select_from(t.join(p, t.c[col] == p.c.id))
            .subquery(f"ten_{rol}_{nombre}_{profundidad}")
        )
    return None


def _aristas(modelos: dict[str, Any]) -> list[tuple[str, str, str]]:
    resultado: list[tuple[str, str, str]] = []
    for cls in modelos.values():
        t = cls.__table__
        alcance_hija = declared_scope(cls)
        if alcance_hija is None:
            continue
        autoridad = _autoridad(cls)
        for fk in t.foreign_keys:
            col = fk.parent.name
            if autoridad and col == autoridad[0]:
                continue
            padre_tabla = fk.column.table.name
            padre_cls = modelos.get(padre_tabla)
            if padre_cls is None or declared_scope(padre_cls) is None:
                continue
            resultado.append((t.name, col, padre_tabla))
    return resultado


def _ids_ejemplo(consulta: Select[Any], conn: Connection) -> tuple[str, ...]:
    ordenada = consulta.order_by(consulta.selected_columns[0]).limit(5)
    filas = conn.execute(ordenada).all()
    return tuple(str(fila[0]) for fila in filas)


def _contar(consulta: Select[Any], conn: Connection) -> int:
    sub = consulta.subquery()
    return conn.execute(select(func.count()).select_from(sub)).scalar_one()


def escanear(conn: Connection) -> Informe:
    """Ejecuta el escaneo de invariantes de alcance sobre la conexión dada."""
    dialecto = conn.dialect.name
    if dialecto == "postgresql":
        conn.exec_driver_sql("SET TRANSACTION READ ONLY")

    init_models()
    modelos = _modelo_de_tabla()
    violaciones: list[Violacion] = []
    aristas_comprobadas = 0

    for tabla_hija, columna, tabla_padre in _aristas(modelos):
        hija_cls = modelos[tabla_hija]
        padre_cls = modelos[tabla_padre]
        alcance_hija = declared_scope(hija_cls)
        alcance_padre = declared_scope(padre_cls)
        if alcance_hija is None or alcance_padre is None:
            continue

        arista_company = (
            alcance_hija == Scope.COMPANY and alcance_padre == Scope.COMPANY
        )
        if arista_company:
            eh = _empresa_de(tabla_hija, modelos, rol="h")
            ep = _empresa_de(tabla_padre, modelos, rol="p")
            if eh is None or ep is None:
                continue
            hijos = modelos[tabla_hija].__table__.alias("hijos")
            companies = modelos["companies"].__table__
            ch = companies.alias("ch")
            cp = companies.alias("cp")
            base = (
                select(eh.c.id.label("id"))
                .select_from(
                    hijos.join(eh, hijos.c.id == eh.c.id)
                    .join(ep, hijos.c[columna] == ep.c.id)
                    .join(ch, ch.c.id == eh.c.company_id)
                    .join(cp, cp.c.id == ep.c.company_id)
                )
                .where(eh.c.company_id != ep.c.company_id)
            )
            consulta_tenant = base.where(ch.c.tenant_id != cp.c.tenant_id)
            consulta_company = base.where(ch.c.tenant_id == cp.c.tenant_id)

            filas_tenant = _contar(consulta_tenant, conn)
            if filas_tenant > 0:
                violaciones.append(
                    Violacion(
                        tabla=tabla_hija,
                        columna=columna,
                        padre=tabla_padre,
                        clase="CROSS_TENANT",
                        filas=filas_tenant,
                        ejemplos=_ids_ejemplo(consulta_tenant, conn),
                    )
                )
            filas_company = _contar(consulta_company, conn)
            if filas_company > 0:
                violaciones.append(
                    Violacion(
                        tabla=tabla_hija,
                        columna=columna,
                        padre=tabla_padre,
                        clase="CROSS_COMPANY",
                        filas=filas_company,
                        ejemplos=_ids_ejemplo(consulta_company, conn),
                    )
                )
            aristas_comprobadas += 1
        else:
            if alcance_hija in (Scope.GLOBAL, Scope.INSTALLATION):
                continue
            th = _tenant_de(tabla_hija, modelos, rol="th")
            tp = _tenant_de(tabla_padre, modelos, rol="tp")
            if th is None or tp is None:
                continue
            hijos = modelos[tabla_hija].__table__.alias("hijos")
            consulta = (
                select(th.c.id.label("id"))
                .select_from(
                    hijos.join(th, hijos.c.id == th.c.id).join(
                        tp, hijos.c[columna] == tp.c.id
                    )
                )
                .where(th.c.tenant_id != tp.c.tenant_id)
            )
            filas = _contar(consulta, conn)
            if filas > 0:
                violaciones.append(
                    Violacion(
                        tabla=tabla_hija,
                        columna=columna,
                        padre=tabla_padre,
                        clase="CROSS_TENANT",
                        filas=filas,
                        ejemplos=_ids_ejemplo(consulta, conn),
                    )
                )
            aristas_comprobadas += 1

    filas_globales: dict[str, int] = {}
    for nombre, cls in modelos.items():
        if declared_scope(cls) != Scope.COMPANY:
            continue
        t = cls.__table__
        if "company_id" not in t.c or not t.c.company_id.nullable:
            continue
        total = conn.execute(
            select(func.count()).select_from(t).where(t.c.company_id.is_(None))
        ).scalar_one()
        if total > 0:
            filas_globales[nombre] = total

    roles = modelos.get("roles")
    if roles is not None and "tenant_id" in roles.__table__.c:
        t = roles.__table__
        roles_personalizados = conn.execute(
            select(func.count())
            .select_from(t)
            .where(t.c.tenant_id.is_(None), t.c.protected.is_(False))
        ).scalar_one()
    else:
        roles_personalizados = None

    return Informe(
        aristas_comprobadas=aristas_comprobadas,
        violaciones=tuple(violaciones),
        filas_globales=filas_globales,
        roles_de_instalacion_personalizados=roles_personalizados,
    )


def _resumen(informe: Informe) -> str:
    lineas = [f"Aristas comprobadas: {informe.aristas_comprobadas}"]
    if informe.violaciones:
        lineas.append("Violaciones:")
        for v in informe.violaciones:
            lineas.append(
                f"  {v.tabla}.{v.columna} → {v.padre} [{v.clase}] "
                f"filas={v.filas} ejemplos={','.join(v.ejemplos)}"
            )
    else:
        lineas.append("Sin violaciones de alcance.")
    if informe.filas_globales:
        lineas.append("Filas globales (company_id nulo):")
        for tabla, total in sorted(informe.filas_globales.items()):
            lineas.append(f"  {tabla}: {total}")
    if informe.roles_de_instalacion_personalizados is not None:
        lineas.append(
            "Roles de instalación personalizados: "
            f"{informe.roles_de_instalacion_personalizados}"
        )
    return "\n".join(lineas)


def main(argv: list[str] | None = None) -> int:
    """Punto de entrada de la CLI del escáner de alcance."""
    parser = argparse.ArgumentParser(
        prog="python -m app.ops.scope_scan", allow_abbrev=False
    )
    parser.add_argument("--json", action="store_true", dest="como_json")
    args = parser.parse_args(argv)

    url = os.environ.get("KONTROL_SCAN_DB_URL")
    if not url:
        print(
            "Falta la variable de entorno KONTROL_SCAN_DB_URL.",
            file=sys.stderr,
        )
        return 2

    init_models()
    engine = create_engine(url)
    try:
        with engine.connect() as conn:
            informe = escanear(conn)
    finally:
        engine.dispose()

    if args.como_json:
        print(json.dumps(dataclasses.asdict(informe), ensure_ascii=False))
    else:
        print(_resumen(informe))
    return 1 if informe.violaciones else 0


if __name__ == "__main__":
    raise SystemExit(main())
