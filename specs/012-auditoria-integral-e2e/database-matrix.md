# Spec 012 — Matriz de Base de Datos (database-matrix.md)

Fuente: `evidence/database-schema-audit.json`.

## Resumen
| Ítem | Valor |
|---|---|
| Tablas | 144 |
| Columnas | 1.678 |
| Issues detectados | 58 (solo dinero `Float`) |

## Hallazgos
| Tipo | Cantidad | Detalle |
|---|---|---|
| `FLOAT` para dinero/tasas | 58 | `ap_payments.amount`, `bank_transactions.amount`, `rate_snapshot`, `tax_calculations.amount/rate`, tesorería, etc. → **riesgo de precisión fiscal (F-03)** |
| `DATETIME` "naive" | 334 | **No concluyente en SQLite** (falso positivo del dialecto); verificar en PostgreSQL (F-07) |
| Identificadores numéricos (RIF/cédula/teléfono/serial) | 0 | ✔ se almacenan como texto |
| Dinero representado correctamente (`Numeric`) | 0 | ningún campo de dinero usa `Numeric` (todas `Float`) |

## Nota
- Todas las tablas con `TimestampMixin` (created_at/updated_at) y claves UUID.
- No se ejecutó `alembic upgrade head` sobre PostgreSQL real → drift ORM↔DB pendiente de verificar.
