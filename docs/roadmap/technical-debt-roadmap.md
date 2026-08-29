# DEUDA TÉCNICA

| ID | Categoría | Deuda | Severidad | Spec | Riesgo si no se paga |
|---|---|---|---|---|---|
| DT-01 | Estructural | `SalesInvoice` sin FK a `sales_orders` | BLOCKER | 034 | Cada factura emitida sin vínculo es histórico irrecuperable |
| DT-02 | Estructural | Líneas de documento sin `uom_id`/`presentation_id` | CRITICAL | 011 | Todo documento histórico queda sin la dimensión; backfill imposible |
| DT-03 | Estructural | `location_id` nullable y nunca escrito | CRITICAL | 022, 023 | El Kardex histórico no tendrá ubicación; reconstrucción imposible |
| DT-04 | Estructural | `cost_center_id` como `String(36)` sin tabla ni FK | HIGH | 007 | Datos sucios que habrá que normalizar con migración de datos |
| DT-05 | Estructural | `price_list`/`zone`/`payment_term` como texto libre | HIGH | 012 | Idem; además viola P8 |
| DT-06 | Backend | `organization` y `master_data` sin auditoría | HIGH | 006, 051 | Vacío permanente en el rastro de auditoría; no reconstruible |
| DT-07 | DB | 2 tablas muertas (`outbox_events`, `feature_flags`) | LOW | 048, 001 | Confunden el inventario; decidir usar o retirar |
| DT-08 | DB | `alembic check` nunca ejecutado contra PostgreSQL | BLOCKER | 001, 052 | Drift silencioso descubierto en producción |
| DT-09 | DB | 36 columnas de cantidad en `Float` | LOW | ADR-012 | Aceptado por ADR; revisar si aparecen cantidades fraccionarias finas |
| DT-10 | Infra | `KONTROL_IMAGE_TAG` con default `latest` | MEDIUM | 052 | Viola P14; despliegue no reproducible |
| DT-11 | Infra | Backup/restore nunca ejecutado | BLOCKER | 053 | Sin garantía de recuperación; RPO/RTO indefinidos |
| DT-12 | Infra | `report_jobs` ejecutado en proceso, sin cola | MEDIUM | 048, 050 | Reportes grandes bloquean el worker web |
| DT-13 | QA | 0 pruebas de página frontend | HIGH | 054 | Las 77 pantallas solo están cubiertas por el crawler (200 OK), no por comportamiento |
| DT-14 | QA | Rendimiento medido sobre base vacía | MEDIUM | 054 | N+1 e índices faltantes invisibles |
| DT-15 | Seguridad | Sin SBOM | MEDIUM | 055 | Sin inventario de dependencias para respuesta a CVE |
| DT-16 | Seguridad | Sin rate limiting global (solo lockout de login) | MEDIUM | 055 | Superficie de abuso en el resto de la API |
| DT-17 | Frontend | Sin protección de cambios sin guardar | MEDIUM | 005 | Pérdida de trabajo del usuario; exigido por Vol. 2 §2 |
| DT-18 | Documental | 4 documentos de estado desfasados | MEDIUM | 054 | El expediente se contradice; riesgo en auditoría externa |

## Orden de pago recomendado

1. **DT-08, DT-11** (Ola 0) — sin PostgreSQL real ninguna otra evidencia es válida.
2. **DT-06, DT-18** (Ola 0) — cierran afirmaciones falsas ya publicadas.
3. **DT-01, DT-02, DT-03** (Olas 1-2) — **cuanto más tarde, más documentos históricos quedan sin la dimensión**. Es deuda que se encarece cada día de operación.
4. **DT-04, DT-05** (Ola 2) — normalizar antes de que crezca el volumen.
5. Resto según ola correspondiente.

## Nota sobre DT-01/02/03

Estas tres son las únicas deudas del listado cuyo coste **crece con el tiempo de operación**.
Una FK añadida hoy admite backfill; añadida tras un año de facturación deja un hueco histórico
permanente. Deben tratarse con prioridad superior a su severidad nominal.
