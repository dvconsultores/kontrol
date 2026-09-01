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


def _garantizadas_en(cx) -> set[str]:
    """Tablas cuya `company_id` ya tiene dueño garantizado **en ese destino**.

    Se le pregunta al catálogo de la base que se va a analizar, no al modelo de
    la versión que ejecuta el análisis. Son cosas distintas: una instalación
    anterior a N7 no tiene esas claves foráneas por mucho que el código actual
    sí las declare.
    """
    filas = cx.execute(text("""
        SELECT con.conrelid::regclass::text
        FROM pg_constraint con
        JOIN unnest(con.conkey) WITH ORDINALITY k(attnum, ord) ON true
        JOIN pg_attribute a ON a.attrelid = con.conrelid AND a.attnum = k.attnum
        WHERE con.contype = 'f' AND a.attname = 'company_id'
          AND con.connamespace = current_schema()::regnamespace
    """)).scalars().all()
    return {f.split(".")[-1].strip('"') for f in filas}


def planes(cx=None) -> list[Plan]:
    """Tablas que necesitan reconstruir su empresa, con sus rutas.

    El **alcance** viene de los modelos: qué entidad es de empresa y por qué
    autoridad deriva es semántica del dominio, y no cambia entre versiones.

    Lo que sí cambia entre versiones es qué garantiza el esquema, y por eso se
    le pregunta al esquema. Sin conexión se responde sobre el modelo vigente,
    que es lo que interesa al comprobar la instalación propia; con conexión se
    responde sobre el destino, que es lo que necesita una actualización desde
    una versión anterior.

    Antes se decidía siempre por el modelo vigente. Tras N7, donde todas las
    columnas tienen clave foránea, eso hacía que el clasificador respondiera
    «no hay nada que revisar» a cualquier base, incluida una heredada llena de
    filas que sí había que revisar.
    """
    init_models()
    modelos = _modelos()
    con_empresa = {t for t, (_, o) in modelos.items()
                   if "company_id" in o.__table__.c}
    garantizadas = _garantizadas_en(cx) if cx is not None else None
    salida = []
    for tabla, (modulo, modelo) in sorted(modelos.items()):
        if declared_scope(modelo) is not Scope.COMPANY:
            continue
        if "company_id" not in modelo.__table__.c:
            continue          # derivada: no tiene columna que reconstruir
        if garantizadas is None:
            if modelo.__table__.c["company_id"].foreign_keys:
                continue      # ya correcta en el modelo vigente
        elif tabla in garantizadas:
            continue          # ya correcta en el destino
        salida.append(Plan(tabla=tabla, modulo=modulo,
                           criticidad=CRITICOS.get(modulo),
                           autoridades=autoridades_de(modelo.__table__, con_empresa)))
    return salida


def _estrategias_de_maestro(cx, planes_, empresa_a_tenant: dict) -> dict:
    """Estrategia recomendada para cada maestro, por tabla.

    Se calcula **durante la corrida**. Antes existía la función y nadie la
    llamaba: `MAESTROS` estaba definido y sin usar, así que las cuatro
    estrategias eran nombres en un enum y no una capacidad ejecutable.

    Solo recomienda. El preflight no asigna, no clona y no deriva: eso es
    trabajo de una migración, que es otra cosa y necesita autorización propia.
    """
    from app.core.mc.preflight import MAESTROS, estrategia_de_maestro

    salida: dict[str, dict] = {}
    for plan in planes_:
        if plan.modulo not in MAESTROS:
            continue
        # Se distingue la evidencia **directa** —la propia fila dice de quién
        # es— de la **derivada** —hay que ir por la relación—. Mezclarlas haría
        # que `DERIVE` no apareciera nunca: en cuanto la relación resuelve la
        # empresa, el conjunto deja de estar vacío y la respuesta sería
        # `ASSIGN`, que dice otra cosa. La diferencia importa para quien luego
        # decide: adjudicar es un dato, deducir es una inferencia.
        directas: dict[str, set[str]] = {}
        derivadas: dict[str, set[str]] = {}
        filas = cx.execute(text(f"SELECT id, company_id FROM {plan.tabla}")).all()
        for fid, valor in filas:
            directas.setdefault(str(fid), set())
            derivadas.setdefault(str(fid), set())
            if valor is not None and str(valor) in empresa_a_tenant:
                directas[str(fid)].add(str(valor))
        for a in plan.autoridades:
            try:
                refs = cx.execute(text(
                    f"SELECT t.id, d.company_id FROM {plan.tabla} t "
                    f"JOIN {a.tabla_destino} d ON d.id = t.{a.columna}")).all()
            except Exception:                       # noqa: BLE001
                continue
            for fid, emp in refs:
                if emp is not None:
                    derivadas.setdefault(str(fid), set()).add(str(emp))

        conteo: dict[str, int] = {}
        for fid, propias in directas.items():
            porRelacion = derivadas.get(fid, set())
            if propias:
                e = estrategia_de_maestro(propias)
            else:
                e = estrategia_de_maestro(porRelacion, derivable=bool(porRelacion))
            conteo[e.value] = conteo.get(e.value, 0) + 1
        if conteo:
            salida[plan.tabla] = conteo
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
    e = create_engine(url, future=True)
    with e.connect() as cx:
        if forzar_solo_lectura:
            cx.execute(text("SET TRANSACTION READ ONLY"))
        # El conjunto de trabajo se decide contra **este** destino, no contra el
        # modelo de la versión que ejecuta el análisis.
        ps = planes(cx)
        tablas = [p.tabla for p in ps]
        antes = _conteos(cx, tablas)
        alembic_antes = cx.execute(text("SELECT version_num FROM alembic_version")).scalar_one()

        historia = historia_de_empresas(cx)
        empresas = {str(r[0]) for r in cx.execute(text("SELECT id FROM companies")).all()}
        tenants = {str(r[0]) for r in cx.execute(text("SELECT id FROM tenants")).all()}
        # A qué tenant pertenece cada empresa: sin esto no se puede saber si una
        # fila con empresa válida cruza la frontera entre clientes.
        empresa_a_tenant = {str(cid): str(t) for t, ids in historia.items()
                            for cid, _ in ids}

        resultados = [clasificar_tabla(cx, p, historia, empresas, tenants,
                                       empresa_a_tenant=empresa_a_tenant) for p in ps]
        maestros = _estrategias_de_maestro(cx, ps, empresa_a_tenant)

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
        "maestros": maestros,
        "cero_escrituras": {
            "conteos_iguales": antes == despues,
            "alembic_igual": alembic_antes == alembic_despues,
            "alembic": alembic_antes,
        },
    }


if __name__ == "__main__":       # pragma: no cover
    import sys

    print(json.dumps(ejecutar(sys.argv[1]), ensure_ascii=False, default=str))
