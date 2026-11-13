# Condición del proceso (§3) — bitácora de intentos

- **Encargo:** `SPEC018_ESTADOS_SECCION_3`, 2026-11-11. Ejecutado el 2026-11-12.
- **Entrada:** HEAD `7fcb491` = `origin/develop`; Alembic `0103_receipt_putaway_link` (una sola cabeza).
- **Delta:** `../../spec018-process-condition-delta.md`.

## Intentos

| # | Intento | Resultado |
|---|---|---|
| 1 | Reconocer la autoridad y el estado real: guardias 019–022, `resultado_de_incidencias` (020), `CONFIRMATION_DONE` (021), `_logistics_detail` (018) | La condición es derivable: recepción + confirmación + incidencias vivas. `MIGRATION_REQUIRED=0` |
| 2 | Backend: `purchasing/process_condition.py` con precedencia fija, una consulta por lote; `process_condition` en el listado y el detalle de Recepciones y en `logistics.receipts[]` del expediente | Verde en PostgreSQL |
| 3 | Pruebas dirigidas (11) y guardia estructural (10) | 21/21 PASS |
| 4 | Frontend: componente `CondicionDelProceso`, tipos y las dos pantallas | Vitest 4/4; compras 132/132; typecheck, lint y build limpios |
| 5 | E2E canónica sobre PostgreSQL efímero | Primer intento sin analizador: la carga documental exige `scan_required` y falla cerrada (`SCAN_FAILED`), que es el comportamiento correcto del producto. Se provisionó ClamAV real sin privilegios (`qa/clamav_qa.py provisionar`, preflight en verde) y se repitió con `--con-analizador` |
| 6 | Responsive a 320: se añadió el bloque que comprueba el expediente y Recepciones en el ancho mínimo | Ver resultado en `EVIDENCE.md` |

## Decisiones de diseño tomadas en el ciclo

- **La condición no se persiste.** Cualquier columna se desincronizaría con las incidencias y con la confirmación, que son de otras Specs.
- **Un solo criterio de bloqueo:** estado de incidencia distinto de `RESUELTA` y `ANULADA`, el mismo que consume `INCIDENTS_UNRESOLVED`. No se activan `INCIDENT_OPEN`/`INCIDENT_CLOSE`.
- **Anulada y rechazada no tienen condición** (`null`): no son una cuarta condición y su estado documental ya se muestra.
- **El texto humano lo publica el backend** (`label`, `reason`); React no traduce códigos.
