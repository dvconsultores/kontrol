"""Clasificador y preflight del backfill multiempresa (ARCH-MC-001, fase N4).

**No escribe nada.** Lee, clasifica y reporta. Puede ejecutarse contra producción
sin riesgo y tantas veces como haga falta: el resultado es determinista para una
misma base.

Su única razón de ser es poder responder, antes de tocar un dato, a qué empresa
pertenece cada fila y —sobre todo— **cuáles no se pueden saber**. Una fila cuya
pertenencia no se deduce no se rellena: se declara.

La regla que gobierna todo esto: *no se inventa empresa*.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from sqlalchemy import text
from sqlalchemy.engine import Connection


class MC(str, Enum):
    """Clases de reconstrucción. El orden es de mayor a menor certeza."""

    A = "MC-A"   # determinista: el tenant tuvo una sola empresa en el intervalo
    B = "MC-B"   # reconstruible: una ruta histórica única lo dice
    C = "MC-C"   # ambigua: más de una empresa posible
    D = "MC-D"   # sin evidencia
    E = "MC-E"   # sin evidencia **y** crítica: fiscal, financiera o de inventario
    OK = "OK"    # ya contiene una empresa real; no hay nada que reconstruir


#: Dominios cuyo dato no admite una empresa inventada. Una fila sin evidencia
#: aquí no es un hueco: es un libro fiscal, un saldo o un pago sin dueño.
CRITICOS = {
    "fiscal": "fiscal",
    "treasury": "financiero",
    "purchasing": "financiero",
    "sales": "financiero",
    "inventory": "inventario",
}


@dataclass
class Autoridad:
    """Una ruta por la que una fila puede alcanzar su empresa."""

    columna: str
    tabla_destino: str
    nombre: str


@dataclass
class Plan:
    """Cómo se clasificaría y rellenaría una tabla. Solo describe; no ejecuta."""

    tabla: str
    modulo: str
    criticidad: str | None
    autoridades: list[Autoridad] = field(default_factory=list)


@dataclass
class Resultado:
    tabla: str
    modulo: str
    filas: int = 0
    por_clase: dict[str, int] = field(default_factory=dict)
    conflictos: list[str] = field(default_factory=list)
    detalle_critico: list[dict] = field(default_factory=list)

    def suma(self, clase: MC, n: int = 1) -> None:
        self.por_clase[clase.value] = self.por_clase.get(clase.value, 0) + n


# --------------------------------------------------------------------------
# Historia de empresas por tenant
# --------------------------------------------------------------------------

def historia_de_empresas(cx: Connection) -> dict[str, list[tuple[str, datetime | None]]]:
    """Empresas de cada tenant con su fecha de creación, en orden."""
    filas = cx.execute(text(
        "SELECT tenant_id, id, created_at FROM companies ORDER BY tenant_id, created_at")).all()
    salida: dict[str, list[tuple[str, datetime | None]]] = {}
    for tenant, cid, creada in filas:
        salida.setdefault(tenant, []).append((cid, creada))
    return salida


def empresa_unica_en(historia: list[tuple[str, datetime | None]],
                     momento: datetime | None) -> str | None:
    """La única empresa que existía en ese instante, si fue una sola.

    **No** se responde con el número de empresas de hoy. Un tenant que hoy tiene
    una pudo tener dos el año pasado, y rellenar por el recuento actual
    atribuiría facturas a la empresa equivocada con toda la apariencia de ser
    correcta.
    """
    if not historia:
        return None
    if momento is None:
        # Sin fecha no se puede acotar el intervalo: solo vale si el tenant
        # nunca tuvo más de una.
        return historia[0][0] if len(historia) == 1 else None
    existentes = [cid for cid, creada in historia
                  if creada is None or creada <= momento]
    if len(existentes) == 1:
        return existentes[0]
    return None


# --------------------------------------------------------------------------
# Descubrimiento de autoridades de derivación
# --------------------------------------------------------------------------

def autoridades_de(tabla_meta, tablas_con_empresa: set[str]) -> list[Autoridad]:
    """Rutas por las que una fila puede alcanzar su empresa.

    Solo se admiten claves foráneas **obligatorias** hacia una tabla que sepa su
    empresa. Una relación que puede faltar no es una ruta: sería una conjetura
    con sintaxis de garantía.
    """
    rutas: list[Autoridad] = []
    for col in tabla_meta.c:
        if col.nullable or col.name in ("company_id", "tenant_id"):
            continue
        for fk in col.foreign_keys:
            destino = fk.column.table.name
            if destino in tablas_con_empresa:
                rutas.append(Autoridad(col.name, destino, f"{col.name} → {destino}"))
    return rutas


# --------------------------------------------------------------------------
# Clasificación de una tabla
# --------------------------------------------------------------------------

def clasificar_tabla(cx: Connection, plan: Plan, historia: dict,
                     empresas: set[str], tenants: set[str],
                     limite_detalle: int = 25) -> Resultado:
    """Clasifica cada fila de una tabla. **Sin escribir.**"""
    r = Resultado(tabla=plan.tabla, modulo=plan.modulo)

    columnas = [c["name"] for c in _columnas(cx, plan.tabla)]
    tiene_fecha = "created_at" in columnas
    sel_fecha = ", created_at" if tiene_fecha else ", NULL AS created_at"
    sel_rutas = "".join(f", {a.columna}" for a in plan.autoridades)

    filas = cx.execute(text(
        f"SELECT id, company_id{sel_fecha}{sel_rutas} FROM {plan.tabla}")).mappings().all()
    r.filas = len(filas)
    if not filas:
        return r

    # Empresa de cada autoridad, resuelta en bloque: nada de una consulta por fila.
    mapas: dict[str, dict[str, str]] = {}
    for a in plan.autoridades:
        mapas[a.columna] = {
            str(k): str(v) for k, v in cx.execute(text(
                f"SELECT id, company_id FROM {a.tabla_destino}")).all() if v is not None}

    for fila in filas:
        valor = str(fila["company_id"]) if fila["company_id"] is not None else None

        # 1. ¿Ya contiene una empresa real? Entonces no hay nada que reconstruir.
        if valor in empresas:
            r.suma(MC.OK)
            continue

        # 2. Derivación por autoridad: la evidencia del dominio pesa más que el
        #    recuento de empresas del tenant.
        candidatas = set()
        for a in plan.autoridades:
            ref = fila.get(a.columna)
            if ref is not None:
                emp = mapas[a.columna].get(str(ref))
                if emp:
                    candidatas.add(emp)

        if len(candidatas) == 1:
            r.suma(MC.B)
            continue
        if len(candidatas) > 1:
            # Dos autoridades que dicen empresas distintas. No se elige una: el
            # conflicto puede estar delatando un dato ya corrupto.
            r.suma(MC.C)
            if len(r.conflictos) < limite_detalle:
                r.conflictos.append(
                    f"{plan.tabla}#{fila['id']}: autoridades discrepan {sorted(candidatas)}")
            continue

        # 3. Determinismo por intervalo, solo si el valor es un tenant conocido.
        if valor in tenants:
            unica = empresa_unica_en(historia.get(valor, []), fila["created_at"])
            if unica:
                r.suma(MC.A)
                continue
            posibles = len(historia.get(valor, []))
            clase = MC.C if posibles > 1 else MC.D
        else:
            clase = MC.D

        if clase in (MC.C, MC.D) and plan.criticidad:
            clase = MC.E

        r.suma(clase)
        if clase in (MC.C, MC.D, MC.E) and len(r.detalle_critico) < limite_detalle:
            r.detalle_critico.append({
                "tabla": plan.tabla, "id": str(fila["id"]),
                "valor_actual": valor, "fecha": str(fila["created_at"]),
                "clase": clase.value, "criticidad": plan.criticidad,
                "candidatas": sorted(historia.get(valor, [])) and
                              [c for c, _ in historia.get(valor, [])],
                "rutas": [a.nombre for a in plan.autoridades] or ["(ninguna)"],
            })
    return r


def _columnas(cx: Connection, tabla: str) -> list[dict]:
    return [{"name": r[0]} for r in cx.execute(text(
        "SELECT column_name FROM information_schema.columns WHERE table_name = :t"),
        {"t": tabla}).all()]
