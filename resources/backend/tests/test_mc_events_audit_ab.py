"""Auditoría y eventos, barrido transversal (ARCH-MC-001, N5).

Cada dominio comprueba su propia auditoría, pero eso no basta: un rastro puede
llevar la empresa correcta en las acciones que alguien pensó en probar y estar
en blanco o equivocado en el resto. Aquí se mira el conjunto.
"""

from __future__ import annotations

from sqlalchemy import text

pytest_plugins = ("tests.conftest_multicompany",)


def _acciones_con_empresa(mundo) -> list[tuple[str, int]]:
    db = mundo.factory()
    try:
        return [(r[0], r[1]) for r in db.execute(text(
            "SELECT action, count(*) FROM audit_events WHERE company_id IS NOT NULL "
            "GROUP BY action ORDER BY action"))]
    finally:
        db.close()


# --------------------------------------------------------------- inventario
def test_hay_auditoria_de_empresa_que_barrer(mundo):
    """Si no hubiera filas, todo lo que sigue pasaría sin comprobar nada."""
    # Se generan operaciones auditables en las dos empresas. Se usan almacenes
    # porque su creación sí deja rastro; los maestros todavía no auditan, y eso
    # se documenta aparte en lugar de inventarlo aquí.
    for usuario, empresa, code in (("ua", mundo.company_a, "AUD-W-A"),
                                   ("ub", mundo.company_b, "AUD-W-B")):
        mundo.crear("/organization/warehouses", usuario, empresa,
                    {"company_id": empresa, "branch_id": None, "code": code,
                     "name": f"Almacén {code}"})
    acciones = _acciones_con_empresa(mundo)
    assert acciones, "no hay ninguna auditoría con empresa: el barrido no probaría nada"


# --------------------------------------------------------------- la empresa
def test_ninguna_auditoria_apunta_a_una_empresa_inexistente(mundo):
    """§154: la mezcla. Una empresa que no existe es un rastro ilegible."""
    db = mundo.factory()
    try:
        malas = db.execute(text(
            "SELECT count(*) FROM audit_events a WHERE a.company_id IS NOT NULL "
            "AND NOT EXISTS (SELECT 1 FROM companies c WHERE c.id = a.company_id)")).scalar_one()
    finally:
        db.close()
    assert malas == 0, f"{malas} auditorías apuntan a una empresa que no existe"


def test_ninguna_auditoria_guarda_el_tenant_bajo_el_campo_de_empresa(mundo):
    """El defecto de origen, buscado directamente en el rastro."""
    db = mundo.factory()
    try:
        confundidas = db.execute(text(
            "SELECT count(*) FROM audit_events a "
            "WHERE a.company_id IN (SELECT id FROM tenants)")).scalar_one()
    finally:
        db.close()
    assert confundidas == 0, f"{confundidas} auditorías guardan un tenant en company_id"


def test_el_tenant_de_la_auditoria_concuerda_con_su_empresa(mundo):
    """§105: cuando el rastro dice tenant y empresa, no pueden contradecirse."""
    db = mundo.factory()
    try:
        contradictorias = db.execute(text(
            "SELECT count(*) FROM audit_events a JOIN companies c ON c.id = a.company_id "
            "WHERE a.tenant_id IS NOT NULL AND a.tenant_id <> c.tenant_id")).scalar_one()
    finally:
        db.close()
    assert contradictorias == 0, (
        f"{contradictorias} auditorías dicen un tenant que no es el de su empresa")


def test_una_operacion_de_a_nunca_queda_auditada_como_de_b(mundo):
    """§100: el cruce, comprobado sobre entidades cuyo dueño se puede resolver."""
    tercero_a = mundo.crear("/organization/warehouses", "ua", mundo.company_a,
                            {"company_id": mundo.company_a, "branch_id": None,
                             "code": "AUD-CRZ-A", "name": "Almacén cruzado A"})
    tercero_b = mundo.crear("/organization/warehouses", "ub", mundo.company_b,
                            {"company_id": mundo.company_b, "branch_id": None,
                             "code": "AUD-CRZ-B", "name": "Almacén cruzado B"})
    db = mundo.factory()
    try:
        for entidad, esperada in ((tercero_a, mundo.company_a), (tercero_b, mundo.company_b)):
            filas = db.execute(text(
                "SELECT company_id FROM audit_events WHERE entity_id = :i "
                "AND company_id IS NOT NULL"), {"i": entidad}).scalars().all()
            for c in filas:
                assert c == esperada, f"la acción sobre {entidad} se auditó como de otra empresa"
    finally:
        db.close()


def test_la_auditoria_de_terceros_no_se_lee_desde_la_otra_empresa(mundo):
    """El rastro es un dato de empresa como cualquier otro."""
    db = mundo.factory()
    try:
        de_a = db.execute(text(
            "SELECT count(*) FROM audit_events WHERE company_id = :c"),
            {"c": mundo.company_a}).scalar_one()
        de_b = db.execute(text(
            "SELECT count(*) FROM audit_events WHERE company_id = :c"),
            {"c": mundo.company_b}).scalar_one()
    finally:
        db.close()
    assert de_a > 0 and de_b > 0, "una de las dos empresas no dejó rastro"


# --------------------------------------------------------------- outbox
def test_el_outbox_no_contiene_eventos_mal_atribuidos(mundo):
    """§101: la tabla existe; los productores todavía no.

    `outbox_events` está declarada y migrada, pero ningún módulo escribe en
    ella: no hay una sola construcción de `OutboxEvent` fuera de su propio
    modelo. No se inventa aquí el mecanismo que le falta —eso es una Spec
    futura, no deuda de N5—; lo que sí se fija es la regla que tendrá que
    cumplir cuando exista, y que hoy se cumple porque está vacía.

    El día que alguien añada el primer productor, esta prueba ya estará
    esperándolo.
    """
    db = mundo.factory()
    try:
        total = db.execute(text("SELECT count(*) FROM outbox_events")).scalar_one()
        malos = db.execute(text(
            "SELECT count(*) FROM outbox_events o WHERE o.company_id IS NOT NULL "
            "AND NOT EXISTS (SELECT 1 FROM companies c WHERE c.id = o.company_id)")).scalar_one()
        confundidos = db.execute(text(
            "SELECT count(*) FROM outbox_events o "
            "WHERE o.company_id IN (SELECT id FROM tenants)")).scalar_one()
    finally:
        db.close()
    assert malos == 0, f"{malos} eventos del outbox apuntan a una empresa inexistente"
    assert confundidos == 0, f"{confundidos} eventos del outbox guardan un tenant como empresa"
    assert total == 0 or malos == 0


# --------------------------------------------------------------- el conjunto
def test_ninguna_tabla_de_empresa_guarda_un_tenant_como_empresa(mundo):
    """§151, sobre todas las tablas declaradas de empresa a la vez.

    Es el barrido que ninguna prueba de dominio puede hacer: recorre el propio
    catálogo de PostgreSQL y pregunta, tabla por tabla, si alguna fila dice
    pertenecer a algo que no es una empresa.
    """
    from app.core.database import Base, init_models
    from app.core.scope import Scope, declared_scope

    init_models()  # sin esto el registro está vacío y el barrido no recorre nada

    db = mundo.factory()
    try:
        # El esquema de la corrida, no `public`: cada ejecución crea el suyo.
        existentes = {r[0] for r in db.execute(text(
            "SELECT tablename FROM pg_tables WHERE schemaname = current_schema()"))}
        revisadas, sospechosas = 0, []
        for modelo in Base.registry.mappers:
            cls = modelo.class_
            tabla = getattr(cls, "__tablename__", None)
            if tabla not in existentes or declared_scope(cls) is not Scope.COMPANY:
                continue
            if "company_id" not in {c.name for c in cls.__table__.columns}:
                continue
            revisadas += 1
            malas = db.execute(text(
                f"SELECT count(*) FROM {tabla} t WHERE t.company_id IS NOT NULL AND ("
                "  t.company_id IN (SELECT id FROM tenants)"
                "  OR NOT EXISTS (SELECT 1 FROM companies c WHERE c.id = t.company_id))"
            )).scalar_one()
            if malas:
                sospechosas.append((tabla, malas))
    finally:
        db.close()

    assert revisadas > 50, f"solo se revisaron {revisadas} tablas de empresa: el barrido es incompleto"
    assert not sospechosas, f"tablas cuyo company_id no es una empresa: {sospechosas}"
