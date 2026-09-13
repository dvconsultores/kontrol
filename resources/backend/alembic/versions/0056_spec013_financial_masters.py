"""Spec 013 — la tasa deja de ser un número suelto y pasa a tener par, fuente y procedencia.

La Spec 038 dejó de inventar tasas. Al hacerlo destapó que **nadie las
registra**, y de paso que lo poco que había no se sostenía:

- dos monedas «USD» podían convivir en una empresa, y la resolución elegía una
  al azar con un `.first()` sin orden declarado;
- dos tasas del mismo día convivían, y el desempate lo decidía PostgreSQL;
- una fila de `exchange_rates` no decía contra qué moneda cotizaba: lo suponía
  el código, con `("VED", "VES")` escrito dentro del dominio.

Esta migración es aditiva sobre `exchange_rates` **a propósito**:
`treasury_rate_snapshots.exchange_rate_id` apunta a esa tabla, y crear un
modelo paralelo dejaría la reproducibilidad histórica de la 038 apuntando a un
muerto.

Dos operaciones tocan datos existentes, y ninguna inventa nada:

1. **Fusión de monedas duplicadas.** Sobrevive la más antigua; las demás quedan
   marcadas `MERGED` —no se borran— y las referencias de tasas y listas de
   precio se repuntan a la superviviente. Sin esto el índice único no entra.

2. **Relleno del par.** `base` es la moneda de la fila; `quote` es la moneda
   funcional **que la empresa ya declara** en `companies.functional_currency`.
   Es lo que el código suponía; ahora queda escrito. Si esa moneda no tenía
   fila de maestro, se crea: sin ella el par no es expresable.

Revision ID: 0056_spec013_masters
Revises: 0055_spec038_treasury
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0056_spec013_masters"
down_revision = "0055_spec038_treasury"
branch_labels = None
depends_on = None

_TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    # ----------------------------------------------------------------- #
    # 1 · Fuentes de tasa. Sin tipos cableados: `source_type` es texto del
    #     maestro, no un enum del código, porque la lista de fuentes de un
    #     país no la decide el programa.
    # ----------------------------------------------------------------- #
    op.create_table(
        "exchange_rate_sources",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False, index=True),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("source_type", sa.String(32), nullable=False, server_default="MANUAL"),
        sa.Column("authority_reference", sa.String(500), nullable=True),
        sa.Column("provider_code", sa.String(64), nullable=True),
        sa.Column("allows_manual", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("status", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("last_sync_at", _TS, nullable=True),
        sa.Column("last_success_at", _TS, nullable=True),
        sa.Column("last_error", sa.String(1000), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("created_at", _TS, nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", _TS, nullable=False, server_default=sa.text("now()")),
    )
    op.create_unique_constraint("uq_rate_sources_company_code", "exchange_rate_sources",
                                ["company_id", "code"])

    # ----------------------------------------------------------------- #
    # 2 · Política de **resolución**. Distinta de `treasury_fx_policies`, que
    #     es la de operación y es de la Spec 038: aquélla decide si se puede
    #     convertir; ésta, cómo se obtiene la tasa.
    #
    #     Nace denegando inversión y triangulación. Derivar una tasa es tomar
    #     una decisión económica, y eso no lo decide el código.
    # ----------------------------------------------------------------- #
    op.create_table(
        "exchange_rate_policies",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False, index=True),
        sa.Column("policy_code", sa.String(64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("allow_inversion", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("allow_triangulation", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("triangulation_currency", sa.String(8), nullable=True),
        #: Nulo = sin tope. Es el comportamiento de hoy, declarado en vez de
        #: implícito: sin política, la tasa más reciente anterior sirve.
        sa.Column("max_age_days", sa.Integer(), nullable=True),
        sa.Column("carry_forward", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("require_rate_approval", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        #: La escala de la tasa es del maestro, no del código. 6 es lo que
        #: `Numeric(14, 6)` viene aplicando; queda declarado, no cableado.
        sa.Column("rate_scale", sa.Integer(), nullable=False, server_default="6"),
        sa.Column("authority_reference", sa.String(500), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="DRAFT"),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("created_at", _TS, nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", _TS, nullable=False, server_default=sa.text("now()")),
    )
    op.create_unique_constraint("uq_rate_policies_company_code_version", "exchange_rate_policies",
                                ["company_id", "policy_code", "version"])

    # ----------------------------------------------------------------- #
    # 3 · Lotes de importación. El hash del contenido es lo que hace que
    #     reimportar el mismo fichero no duplique nada.
    # ----------------------------------------------------------------- #
    op.create_table(
        "exchange_rate_import_batches",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False, index=True),
        sa.Column("source_id", sa.String(36), sa.ForeignKey("exchange_rate_sources.id"), nullable=False),
        sa.Column("rate_type", sa.String(32), nullable=True),
        sa.Column("filename", sa.String(300), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("imported_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rejected_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(32), nullable=False, server_default="COMPLETED"),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("created_at", _TS, nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", _TS, nullable=False, server_default=sa.text("now()")),
    )
    op.create_unique_constraint("uq_rate_import_company_hash", "exchange_rate_import_batches",
                                ["company_id", "content_hash"])

    # ----------------------------------------------------------------- #
    # 4 · Fusión de monedas duplicadas. Antes del índice único, porque si no
    #     el índice no entra; y sin borrar, porque una moneda duplicada puede
    #     tener historia colgando.
    # ----------------------------------------------------------------- #
    op.execute("""
        WITH ganadoras AS (
            SELECT DISTINCT ON (company_id, code) company_id, code, id
            FROM currencies WHERE status = 'ACTIVE'
            ORDER BY company_id, code, created_at, id
        ),
        perdedoras AS (
            SELECT c.id AS vieja, g.id AS nueva
            FROM currencies c JOIN ganadoras g
              ON g.company_id = c.company_id AND g.code = c.code
            WHERE c.status = 'ACTIVE' AND c.id <> g.id
        )
        UPDATE exchange_rates r SET currency_id = p.nueva
        FROM perdedoras p WHERE r.currency_id = p.vieja
    """)
    op.execute("""
        WITH ganadoras AS (
            SELECT DISTINCT ON (company_id, code) company_id, code, id
            FROM currencies WHERE status = 'ACTIVE'
            ORDER BY company_id, code, created_at, id
        ),
        perdedoras AS (
            SELECT c.id AS vieja, g.id AS nueva
            FROM currencies c JOIN ganadoras g
              ON g.company_id = c.company_id AND g.code = c.code
            WHERE c.status = 'ACTIVE' AND c.id <> g.id
        )
        UPDATE price_lists l SET currency_id = p.nueva
        FROM perdedoras p WHERE l.currency_id = p.vieja
    """)
    op.execute("""
        WITH ganadoras AS (
            SELECT DISTINCT ON (company_id, code) company_id, code, id
            FROM currencies WHERE status = 'ACTIVE'
            ORDER BY company_id, code, created_at, id
        )
        UPDATE currencies c SET status = 'MERGED'
        FROM ganadoras g
        WHERE g.company_id = c.company_id AND g.code = c.code
          AND c.status = 'ACTIVE' AND c.id <> g.id
    """)
    # Único **parcial**: una moneda desactivada no impide registrar otra con el
    # mismo código, que es lo que hace falta para rehabilitar historia.
    op.execute("""
        CREATE UNIQUE INDEX uq_currencies_company_code_active
        ON currencies (company_id, code) WHERE status = 'ACTIVE'
    """)

    # ----------------------------------------------------------------- #
    # 5 · La observación canónica. `currency_id` y `rate_date` se conservan:
    #     son la clave foránea viva de la 038 y el camino de lectura de lo ya
    #     escrito.
    # ----------------------------------------------------------------- #
    for columna in [
        sa.Column("base_currency_id", sa.String(36),
                                       sa.ForeignKey("currencies.id"), nullable=True),
        sa.Column("quote_currency_id", sa.String(36),
                                        sa.ForeignKey("currencies.id"), nullable=True),
        sa.Column("source_id", sa.String(36),
                                sa.ForeignKey("exchange_rate_sources.id"), nullable=True),
        sa.Column("rate_type", sa.String(32), nullable=False,
                                server_default="REFERENCE"),
        sa.Column("effective_at", _TS, nullable=True),
        sa.Column("published_at", _TS, nullable=True),
        sa.Column("observed_at", _TS, nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("supersedes_id", sa.String(36), nullable=True),
        sa.Column("provider_observation_id", sa.String(200), nullable=True),
        sa.Column("import_batch_id", sa.String(36),
                                      sa.ForeignKey("exchange_rate_import_batches.id"), nullable=True),
        sa.Column("source_reference", sa.String(500), nullable=True),
        sa.Column("authority_reference", sa.String(500), nullable=True),
        sa.Column("entered_by", sa.String(36), nullable=True),
        sa.Column("approved_by", sa.String(36), nullable=True),
        sa.Column("reason", sa.String(1000), nullable=True),
    ]:
        op.add_column("exchange_rates", columna)

    # ----------------------------------------------------------------- #
    # 6 · Relleno. La moneda funcional que la empresa declara necesita fila de
    #     maestro para que el par sea expresable; si no la tiene, se crea.
    # ----------------------------------------------------------------- #
    op.execute("""
        INSERT INTO currencies (id, company_id, code, name, decimal_places, status,
                                created_by, created_at, updated_at)
        SELECT md5(random()::text || clock_timestamp()::text)::uuid::text,
               c.id, c.functional_currency, c.functional_currency, 2, 'ACTIVE',
               'migration:0056', now(), now()
        FROM companies c
        WHERE c.functional_currency IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM currencies u
                          WHERE u.company_id = c.id AND u.code = c.functional_currency
                            AND u.status = 'ACTIVE')
    """)
    # Fuente por omisión para lo ya escrito: dice de dónde vino sin fingir que
    # alguien la eligió. El texto libre que traía la fila se conserva aparte.
    op.execute("""
        INSERT INTO exchange_rate_sources (id, company_id, code, name, source_type,
                                           authority_reference, allows_manual, priority,
                                           status, created_by, created_at, updated_at)
        SELECT md5(random()::text || clock_timestamp()::text)::uuid::text,
               c.id, 'LEGACY', 'Origen anterior a la Spec 013', 'MANUAL',
               'Sin fuente declarada: las filas anteriores solo traían texto libre',
               true, 900, 'ACTIVE', 'migration:0056', now(), now()
        FROM companies c
        WHERE EXISTS (SELECT 1 FROM exchange_rates r WHERE r.company_id = c.id)
    """)
    op.execute("""
        UPDATE exchange_rates r
        SET base_currency_id = r.currency_id,
            quote_currency_id = f.id,
            source_id = s.id,
            source_reference = r.source,
            effective_at = (r.rate_date::timestamp AT TIME ZONE 'UTC'),
            observed_at = r.created_at
        FROM companies c
        JOIN currencies f ON f.company_id = c.id AND f.code = c.functional_currency
                         AND f.status = 'ACTIVE'
        JOIN exchange_rate_sources s ON s.company_id = c.id AND s.code = 'LEGACY'
        WHERE r.company_id = c.id
    """)
    # Una tasa cuya moneda **es** la funcional no es una cotización de mercado:
    # es la identidad, y no debe quedar como observación par-a-par.
    op.execute("""
        UPDATE exchange_rates SET status = 'IDENTITY'
        WHERE base_currency_id = quote_currency_id
    """)

    # Observaciones repetidas en las mismas coordenadas: existen porque nunca
    # hubo unicidad, y la fusión de monedas del paso 4 ha juntado algunas más.
    # No se borra ninguna: se les aplica la regla del propio modelo —la última
    # sucede a la anterior— que es exactamente para lo que está `supersedes_id`.
    op.execute("""
        WITH ordenadas AS (
            SELECT id, created_at,
                   ROW_NUMBER() OVER (w) AS n,
                   COUNT(*) OVER (PARTITION BY company_id, base_currency_id,
                                  quote_currency_id, source_id, rate_type,
                                  effective_at, version) AS total,
                   LAG(id) OVER (w) AS anterior
            FROM exchange_rates
            WHERE status <> 'IDENTITY'
            WINDOW w AS (PARTITION BY company_id, base_currency_id, quote_currency_id,
                         source_id, rate_type, effective_at, version
                         ORDER BY created_at, id)
        )
        UPDATE exchange_rates r
        SET status = CASE WHEN o.n < o.total THEN 'SUPERSEDED' ELSE r.status END,
            supersedes_id = CASE WHEN o.n = o.total THEN o.anterior ELSE r.supersedes_id END
        FROM ordenadas o
        WHERE r.id = o.id AND o.total > 1
    """)

    # Delta dirigido a la Spec 038: si la política llega a permitir derivar una
    # tasa, la instantánea tiene que decirlo. Sin esto, reconstruir la operación
    # afirmaría «usó la tasa 40» cuando usó 0,025.
    op.add_column("treasury_rate_snapshots",
                  sa.Column("derivation", sa.String(32), nullable=True))
    op.add_column("treasury_rate_snapshots",
                  sa.Column("derived_from", sa.String(500), nullable=True))

    op.create_check_constraint("ck_exchange_rates_rate_positive", "exchange_rates", "rate > 0")
    op.create_index("ix_exchange_rates_effective_at", "exchange_rates", ["effective_at"])
    op.execute("""
        CREATE UNIQUE INDEX uq_exchange_rates_observation
        ON exchange_rates (company_id, base_currency_id, quote_currency_id,
                           source_id, rate_type, effective_at, version)
        WHERE status <> 'SUPERSEDED'
    """)


def downgrade() -> None:
    op.drop_column("treasury_rate_snapshots", "derived_from")
    op.drop_column("treasury_rate_snapshots", "derivation")
    op.execute("DROP INDEX IF EXISTS uq_exchange_rates_observation")
    op.drop_index("ix_exchange_rates_effective_at", table_name="exchange_rates")
    op.drop_constraint("ck_exchange_rates_rate_positive", "exchange_rates", type_="check")
    for nombre in ["reason", "approved_by", "entered_by", "authority_reference",
                   "source_reference", "import_batch_id", "provider_observation_id",
                   "supersedes_id", "version", "status", "observed_at", "published_at",
                   "effective_at", "rate_type", "source_id", "quote_currency_id",
                   "base_currency_id"]:
        op.drop_column("exchange_rates", nombre)
    op.execute("DROP INDEX IF EXISTS uq_currencies_company_code_active")
    op.drop_table("exchange_rate_import_batches")
    op.drop_table("exchange_rate_policies")
    op.drop_table("exchange_rate_sources")
    # La fusión de duplicados y las monedas funcionales creadas **no** se
    # deshacen: deshacerlas volvería a partir historia que ya quedó unida, y
    # una bajada de esquema no es una máquina del tiempo de los datos.
