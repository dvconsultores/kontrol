"""Fixture legado hostil para el preflight de N4 (ARCH-MC-001).

Construye a propósito una base con la forma que tendría una instalación
anterior a esta remediación: `company_id` guardando el identificador del
**tenant**, más los casos difíciles que el clasificador tiene que distinguir sin
adivinar.

Existía como sandbox de una sesión anterior y se perdió al borrarse el
directorio temporal, con lo que las pruebas del fixture pasaron a saltarse. Un
fixture hostil que no se puede reconstruir no es un fixture: es un recuerdo.
Esto lo convierte en artefacto.

Casos que siembra, y por qué cada uno es difícil:

- **MC-A** — tenant que solo tuvo una empresa en el instante de la fila. Se
  resuelve por intervalo temporal, no por el recuento de hoy: un tenant que hoy
  tiene una pudo tener dos el año pasado.
- **MC-B** — saldo de inventario sin empresa propia, deducible por su almacén.
  La evidencia del dominio pesa más que el recuento.
- **MC-C** — fila creada **después** de que el tenant tuviera dos empresas.
  Ambigua: hay dos candidatas y ninguna razón para preferir una.
- **MC-E** — serie fiscal ambigua. En fiscal no basta con decir «ambiguo»:
  atribuir una serie a la empresa equivocada emite facturas a nombre de otro
  contribuyente, así que sube a crítica y bloquea.
- **MC-D** — sin evidencia y en dominio **no crítico**. Un tenant sin ninguna
  empresa: no hay nada de donde deducir, y anotarlo es todo lo que se puede
  hacer. `NON_RECONSTRUCTIBLE`.
- **INVALID_LEGACY_SCOPE** — el valor no es ni un tenant ni una empresa. No es
  un hueco esperando la migración: ya estaba roto antes de empezar, y
  clasificarlo como «sin evidencia» lo escondería entre los reconstruibles.
- **CROSS_TENANT** — la fila lleva una empresa **real**, pero de otro cliente
  que el que dice su autoridad. Integridad rota entre instalaciones, no una
  migración pendiente.
- **Estrategias de maestro** — un artículo usado por una sola empresa
  (`ASSIGN`), otro usado por dos (`CLONE`), otro sin uso pero con relación
  obligatoria (`DERIVE`) y otro sin nada (`MANUAL_REVIEW`).
- **OK** — fila que ya tenía su empresa. No se reclasifica.

Uso:

    KONTROL_LEGACY_URL=postgresql://usuario@host:puerto/kontrol_legacy \\
        python qa/n4-legacy-hostile-seed.py
"""

from __future__ import annotations

import os
import sys
import uuid
from datetime import UTC, datetime, timedelta

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "resources", "backend"))

URL = os.environ.get(
    "KONTROL_LEGACY_URL",
    "postgresql://kontrol_migrator@127.0.0.1:55418/kontrol_legacy")
BASE = URL.rsplit("/", 1)[1]
ADMIN = URL.rsplit("/", 1)[0] + "/postgres"

AYER = datetime.now(UTC) - timedelta(days=400)
HOY = datetime.now(UTC)


def _recrear_base() -> None:
    c = psycopg2.connect(ADMIN)
    c.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = c.cursor()
    cur.execute(f"DROP DATABASE IF EXISTS {BASE}")
    cur.execute(f"CREATE DATABASE {BASE}")
    c.close()


def _esquema_legado() -> None:
    """Esquema hasta `0032`: el estado anterior a las claves foráneas de N7.

    Se detiene ahí a propósito. Una instalación heredada no tiene las
    restricciones que N7 añadió, y sembrar sobre el esquema final haría que la
    base rechazara justamente las filas inválidas que hacen falta.
    """
    from alembic import command
    from alembic.config import Config

    # La URL se impone por entorno: `alembic/env.py` la lee de ahí, y el valor
    # del fichero apunta al host de compose.
    os.environ["KONTROL_DB_URL"] = URL.replace("postgresql://", "postgresql+psycopg2://")
    cfg = Config(os.path.join(RAIZ, "resources", "backend", "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(RAIZ, "resources", "backend", "alembic"))
    command.upgrade(cfg, "0032_mc_expand_tenant_scoped")


def sembrar() -> dict[str, str]:
    _recrear_base()
    _esquema_legado()

    c = psycopg2.connect(URL)
    cur = c.cursor()
    ids: dict[str, str] = {}

    inst = str(uuid.uuid4())
    cur.execute("SELECT column_name FROM information_schema.columns "
                "WHERE table_name='installations' AND is_nullable='NO' AND column_default IS NULL")
    cols = {"id": inst, "installation_uuid": str(uuid.uuid4())}
    for (col,) in cur.fetchall():
        cols.setdefault(col, "ACTIVE")
    cur.execute(f"INSERT INTO installations ({','.join(cols)}) "
                f"VALUES ({','.join(['%s'] * len(cols))})", list(cols.values()))

    # --- Tenant monoempresa: todo lo suyo es determinista.
    t_uno = str(uuid.uuid4())
    cur.execute("INSERT INTO tenants (id, installation_id, code, name, plan, status, created_at) "
                "VALUES (%s,%s,'LEG-UNO','Legado monoempresa','MONO_COMPANY','ACTIVE',%s)",
                (t_uno, inst, AYER))
    c_uno = str(uuid.uuid4())
    cur.execute("INSERT INTO companies (id, tenant_id, code, legal_name, rif, legal_type, "
                " functional_currency, status, created_at) "
                "VALUES (%s,%s,'U1','Unica CA','J-10000000-1','JURIDICA','VED','ACTIVE',%s)",
                (c_uno, t_uno, AYER))

    # --- Tenant que creció: una empresa al principio, dos después.
    t_dos = str(uuid.uuid4())
    cur.execute("INSERT INTO tenants (id, installation_id, code, name, plan, status, created_at) "
                "VALUES (%s,%s,'LEG-DOS','Legado que creció','MULTI_COMPANY','ACTIVE',%s)",
                (t_dos, inst, AYER))
    c_vieja, c_nueva = str(uuid.uuid4()), str(uuid.uuid4())
    cur.execute("INSERT INTO companies (id, tenant_id, code, legal_name, rif, legal_type, "
                " functional_currency, status, created_at) "
                "VALUES (%s,%s,'V1','Vieja CA','J-20000000-2','JURIDICA','VED','ACTIVE',%s)",
                (c_vieja, t_dos, AYER))
    cur.execute("INSERT INTO companies (id, tenant_id, code, legal_name, rif, legal_type, "
                " functional_currency, status, created_at) "
                "VALUES (%s,%s,'N1','Nueva CA','J-30000000-3','JURIDICA','VED','ACTIVE',%s)",
                (c_nueva, t_dos, HOY - timedelta(days=30)))

    # --- parties: el defecto histórico y una fila ya correcta.
    #     La del tenant monoempresa es MC-A; la posterior a la segunda empresa,
    #     MC-C; la que ya tenía empresa, OK.
    def _party(company_valor, code, cuando):
        pid = str(uuid.uuid4())
        cur.execute("INSERT INTO parties (id, company_id, code, name, person_type, roles, "
                    " status, created_at) VALUES (%s,%s,%s,%s,'JURIDICA','[]','ACTIVE',%s)",
                    (pid, company_valor, code, f"Tercero {code}", cuando))
        return pid

    ids["party_mc_a"] = _party(t_uno, "LEG-A", AYER + timedelta(days=1))
    ids["party_mc_c"] = _party(t_dos, "LEG-C", HOY - timedelta(days=1))
    ids["party_ok"] = _party(c_uno, "LEG-OK", HOY)

    # --- inventory_balances: sin empresa deducible por fecha, pero con almacén.
    #     El almacén sí sabe de quién es, y esa evidencia manda.
    alm = str(uuid.uuid4())
    cur.execute("INSERT INTO warehouses (id, company_id, code, name, warehouse_type, status, created_at) "
                "VALUES (%s,%s,'ALM-L','Almacen legado','PHYSICAL','ACTIVE',%s)",
                (alm, c_vieja, AYER))
    prod = str(uuid.uuid4())
    cur.execute("INSERT INTO catalog_items (id, company_id, code, name, item_type, status, created_at) "
                "VALUES (%s,%s,'SKU-L','Articulo legado','PRODUCT','ACTIVE',%s)",
                (prod, c_vieja, AYER))
    ids["balance_mc_b"] = str(uuid.uuid4())
    cur.execute("INSERT INTO inventory_balances (id, company_id, warehouse_id, product_id, "
                " created_at) VALUES (%s,%s,%s,%s,%s)",
                (ids["balance_mc_b"], t_dos, alm, prod, HOY))

    # --- MC-D: sin evidencia, en dominio no crítico.
    #     Un tenant sin ninguna empresa. No hay intervalo del que deducir ni
    #     autoridad de la que derivar: lo único honesto es anotarlo.
    t_vacio = str(uuid.uuid4())
    cur.execute("INSERT INTO tenants (id, installation_id, code, name, plan, status, created_at) "
                "VALUES (%s,%s,'LEG-CERO','Legado sin empresas','MONO_COMPANY','ACTIVE',%s)",
                (t_vacio, inst, AYER))
    ids["party_mc_d"] = _party(t_vacio, "LEG-D", HOY)

    # --- INVALID_LEGACY_SCOPE: ni tenant ni empresa. Ya estaba roto.
    ids["party_invalid"] = _party(str(uuid.uuid4()), "LEG-INV", HOY)

    # --- CROSS_TENANT: empresa real, pero de otro cliente que su almacén.
    #     El saldo dice pertenecer a la empresa única del primer tenant y cuelga
    #     de un almacén del segundo. Ninguna de las dos referencias está mal por
    #     separado; lo que está mal es la combinación.
    ids["balance_cross_tenant"] = str(uuid.uuid4())
    cur.execute("INSERT INTO inventory_balances (id, company_id, warehouse_id, product_id, "
                " created_at) VALUES (%s,%s,%s,%s,%s)",
                (ids["balance_cross_tenant"], c_uno, alm, prod, HOY))

    # --- Maestros: un artículo por empresa y uno compartido por dos.
    #     `catalog_items` es de `master_data`, que no es dominio crítico.
    for marca, empresa in (("MSTR-ASSIGN", c_vieja), ("MSTR-SOLO", c_uno)):
        cur.execute("INSERT INTO catalog_items (id, company_id, code, name, item_type, "
                    " status, created_at) VALUES (%s,%s,%s,%s,'PRODUCT','ACTIVE',%s)",
                    (str(uuid.uuid4()), empresa, marca, f"Articulo {marca}", AYER))
    # Uno sin empresa reconocible y sin relación: manual.
    ids["item_manual"] = str(uuid.uuid4())
    cur.execute("INSERT INTO catalog_items (id, company_id, code, name, item_type, "
                " status, created_at) VALUES (%s,%s,'MSTR-MANUAL','Articulo sin dueño',"
                "'PRODUCT','ACTIVE',%s)", (ids["item_manual"], t_dos, AYER))

    # --- MASTER_CLONE: un maestro que dos empresas del **mismo** tenant usaron.
    #     El saldo referencia un almacén de una empresa y un artículo de la
    #     otra: dos evidencias legítimas que apuntan a empresas distintas.
    #     Adjudicárselo a una rompería a la otra, así que la respuesta es
    #     clonarlo. Dentro del mismo tenant a propósito: si cruzara clientes
    #     sería CROSS_TENANT, que es otra cosa.
    prod_nueva = str(uuid.uuid4())
    cur.execute("INSERT INTO catalog_items (id, company_id, code, name, item_type, "
                " status, created_at) VALUES (%s,%s,'MSTR-CLONE','Articulo compartido',"
                "'PRODUCT','ACTIVE',%s)", (prod_nueva, c_nueva, HOY))
    tipo_vieja = str(uuid.uuid4())
    cur.execute("INSERT INTO movement_types (id, company_id, code, name, direction, "
                " affects_balance, status, created_at) "
                "VALUES (%s,%s,'MT-CLONE','Entrada compartida','IN',true,'ACTIVE',%s)",
                (tipo_vieja, c_vieja, HOY))
    ids["movimiento_clone"] = str(uuid.uuid4())
    # La empresa lleva el identificador del **tenant**, que es la forma del
    # defecto heredado: sin evidencia propia, se resuelve por las relaciones.
    # Y las dos relaciones apuntan a empresas distintas del mismo tenant.
    cur.execute("INSERT INTO inventory_movements (id, company_id, warehouse_id, product_id, "
                " movement_type_id, quantity, occurred_at, currency, status, created_at) "
                "VALUES (%s,%s,%s,%s,%s,1,%s,'VED','POSTED',%s)",
                (ids["movimiento_clone"], t_dos, alm, prod_nueva, tipo_vieja, HOY, HOY))

    # --- fiscal_number_series: ambigua y crítica. Una serie mal atribuida
    #     emite facturas a nombre de otro contribuyente.
    ids["serie_mc_e"] = str(uuid.uuid4())
    cur.execute("INSERT INTO fiscal_number_series (id, company_id, document_type, next_number, "
                " lock_version, created_at) VALUES (%s,%s,'INVOICE',1,0,%s)",
                (ids["serie_mc_e"], t_dos, HOY))
    ids["serie_mc_a"] = str(uuid.uuid4())
    cur.execute("INSERT INTO fiscal_number_series (id, company_id, document_type, next_number, "
                " lock_version, created_at) VALUES (%s,%s,'INVOICE',1,0,%s)",
                (ids["serie_mc_a"], t_uno, AYER + timedelta(days=2)))

    c.commit()

    # Comprobación de la propia siembra: una prueba que corre sobre un fixture
    # vacío pasa sin comprobar nada, y eso ya ocurrió una vez en este proyecto.
    for etiqueta, consulta, parametros in (
            ("MC-D", "SELECT count(*) FROM parties WHERE company_id = %s", (t_vacio,)),
            ("INVALID", "SELECT count(*) FROM parties WHERE code = 'LEG-INV'", ()),
            ("CROSS_TENANT", "SELECT count(*) FROM inventory_balances WHERE id = %s",
             (ids["balance_cross_tenant"],)),
            ("maestros", "SELECT count(*) FROM catalog_items", ()),
            ("MASTER_CLONE", "SELECT count(*) FROM inventory_movements WHERE id = %s",
             (ids["movimiento_clone"],))):
        cur.execute(consulta, parametros)
        n = cur.fetchone()[0]
        if n == 0:
            raise AssertionError(f"la semilla de {etiqueta} no se creó: el fixture no es hostil")

    cur.execute("SELECT count(*) FROM parties")
    print(f"  terceros sembrados      : {cur.fetchone()[0]}")
    cur.execute("SELECT count(*) FROM companies")
    print(f"  empresas                : {cur.fetchone()[0]}")
    cur.execute("SELECT count(*) FROM tenants")
    print(f"  tenants                 : {cur.fetchone()[0]}")
    c.close()
    return ids


if __name__ == "__main__":
    ids = sembrar()
    print(f"OK fixture legado hostil en {BASE}")
    for k, v in ids.items():
        print(f"    {k:16} {v}")
