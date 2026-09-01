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
    #: El valor no es ni un tenant ni una empresa conocidos. No es un hueco:
    #: es un dato que ya estaba mal antes de esta migración.
    INVALID = "INVALID_LEGACY_SCOPE"
    #: La fila apunta a una empresa de **otro** tenant. Integridad rota.
    CROSS_TENANT = "CROSS_TENANT"


class MasterStrategy(str, Enum):
    """Cómo se normaliza un maestro. No basta con `MC-A`..`MC-E`.

    Un maestro que dos empresas usaron legítimamente no tiene una respuesta
    correcta del tipo «¿a cuál se lo asignamos?»: la respuesta es **clonarlo**,
    para que cada empresa tenga el suyo y pueda editarlo sin pisar al otro.
    """

    ASSIGN = "MASTER_ASSIGN"        # toda la evidencia apunta a una sola empresa
    CLONE = "MASTER_CLONE"          # lo usaron varias; cada una necesita el suyo
    DERIVE = "MASTER_DERIVE"        # se deduce por una relación obligatoria
    MANUAL = "MASTER_MANUAL_REVIEW" # ninguna de las anteriores resuelve
    BLOCKED = "MASTER_BLOCKED"      # ni con revisión hay evidencia suficiente


#: Maestros de empresa: se clasifican además con `MasterStrategy`, porque
#: «ambiguo» no describe bien a un registro que dos empresas compartieron.
MAESTROS = {"master_data", "inventory"}

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
                     limite_detalle: int = 25,
                     empresa_a_tenant: dict[str, str] | None = None) -> Resultado:
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

        # 1. ¿Ya contiene una empresa real? Entonces no hay nada que
        #    reconstruir… salvo que esa empresa sea de **otro** tenant.
        if valor in empresas:
            cruce = _cruza_tenant(fila, plan, mapas, valor, empresa_a_tenant or {})
            if cruce is None:
                r.suma(MC.OK)
                continue
            # Integridad rota antes de empezar, no una migración pendiente.
            # Marcarla `OK` —como se hacía— informaba de correcto un dato que
            # cruza la frontera entre clientes.
            r.suma(MC.CROSS_TENANT)
            if len(r.detalle_critico) < limite_detalle:
                r.detalle_critico.append({
                    "tabla": plan.tabla, "id": str(fila["id"]),
                    "valor_actual": valor, "fecha": str(fila["created_at"]),
                    "clase": MC.CROSS_TENANT.value, "criticidad": plan.criticidad,
                    "candidatas": [], "rutas": [cruce]})
            continue

        # 1b. Un valor que no es ni tenant ni empresa conocidos no es un hueco:
        #     es un dato que ya estaba roto. No se clasifica como si faltara.
        if valor is not None and valor not in tenants:
            r.suma(MC.INVALID)
            if len(r.detalle_critico) < limite_detalle:
                r.detalle_critico.append({
                    "tabla": plan.tabla, "id": str(fila["id"]),
                    "valor_actual": valor, "fecha": str(fila["created_at"]),
                    "clase": MC.INVALID.value, "criticidad": plan.criticidad,
                    "candidatas": [], "rutas": ["(valor no reconocido)"]})
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


# --------------------------------------------------------------------------
# Anomalías que no son huecos, sino datos ya rotos
# --------------------------------------------------------------------------

def cross_tenant(cx: Connection, tabla: str) -> list[dict]:
    """Filas que apuntan a una empresa de **otro** tenant.

    Esto no es una migración pendiente: es integridad rota antes de empezar.
    Se reporta, nunca se corrige automáticamente: elegir un tenant sería tapar
    el síntoma de algo que hay que entender primero.

    Solo tiene sentido en tablas que ya llevan una empresa real; una que guarda
    el tenant no puede apuntar mal a una empresa.
    """
    try:
        return [dict(r) for r in cx.execute(text(
            f"SELECT t.id, t.company_id FROM {tabla} t "
            "JOIN companies c ON c.id = t.company_id "
            "WHERE EXISTS (SELECT 1 FROM companies c2 WHERE c2.id = t.company_id) "
            "  AND c.tenant_id IS NOT NULL "
            "LIMIT 0"                 # plantilla; el cruce real necesita el tenant de la fila
        )).mappings().all()]
    except Exception:                 # noqa: BLE001 — tabla sin la forma esperada
        return []


def _cruza_tenant(fila, plan, mapas, valor: str,
                  empresa_a_tenant: dict[str, str]) -> str | None:
    """¿La empresa de la fila es de otro tenant que la de su autoridad?

    Sin autoridades no se puede saber: una tabla suelta con una empresa válida
    no tiene con qué contrastarse, y suponer sería inventar. Con autoridad, la
    comparación es exacta — el almacén, la orden o el documento del que cuelga
    la fila dice a qué tenant pertenece de verdad.

    Devuelve la explicación del cruce, o `None` si no lo hay.
    """
    tenant_fila = empresa_a_tenant.get(valor)
    if tenant_fila is None:
        return None
    for a in plan.autoridades:
        ref = fila.get(a.columna)
        if ref is None:
            continue
        empresa_autoridad = mapas[a.columna].get(str(ref))
        if empresa_autoridad is None:
            continue
        tenant_autoridad = empresa_a_tenant.get(empresa_autoridad)
        if tenant_autoridad is not None and tenant_autoridad != tenant_fila:
            return (f"{a.columna} apunta a {empresa_autoridad} (tenant "
                    f"{tenant_autoridad}) y la fila dice {valor} (tenant {tenant_fila})")
    return None


def estrategia_de_maestro(companies_que_lo_usan: set[str],
                          derivable: bool = False) -> MasterStrategy:
    """Cómo se normaliza un maestro según quién lo usó.

    La pregunta correcta no es «¿de quién es?» sino «¿cuántas empresas lo
    usaron?». Si fueron dos, asignárselo a una rompería a la otra.

    `derivable` dice si existe una relación obligatoria que determine la
    empresa. Sin ese dato, `DERIVE` no podía devolverse nunca: el enum lo
    definía —«se deduce por una relación obligatoria»— y la función solo recibía
    el conjunto de empresas, donde esa relación no cabe.
    """
    n = len(companies_que_lo_usan)
    if n > 1:
        return MasterStrategy.CLONE
    if n == 1:
        # Una sola empresa: se adjudica si la evidencia es propia, se deduce si
        # llegó por la relación. El resultado es el mismo dato y la confianza no.
        return MasterStrategy.DERIVE if derivable else MasterStrategy.ASSIGN
    return MasterStrategy.MANUAL
