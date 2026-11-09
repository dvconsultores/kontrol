# Evidencia · Reporte formal de diferencias

**Fecha:** 2026-11-09. **Iniciativa:** `SPEC018_REPORTE_FORMAL_DIFERENCIAS`. **Datos:** sintéticos.

| Campo | Valor |
|---|---|
| DATABASE_ENGINE | PostgreSQL 16.2 de QA |
| SCHEMA_SOURCE | Alembic, base nueva, cabeza `0090_import_difference_report` (`alembic heads` = 1) |
| BROWSER | Google Chrome, `qa/e2e-run.py --con-analizador` (base efímera por corrida) |

## Pruebas del backend (`tests/test_importaciones_difference_report.py`)

PostgreSQL: 13 de 13. SQLite: 12 de 12 y 1 omitida (la concurrencia exige PostgreSQL).

| Escenario | Qué demuestra |
|---|---|
| a · Emisión | Estado previo «sin reporte»; referencia `DIF-nnnnnn-R1`, revisión 1, línea con diferencia de cantidad e incidencia FALTANTE; emisor con nombre de usuario, nunca UUID; estado posterior «emitido» |
| b · PDF | `application/pdf`, `%PDF-` y `%%EOF`; sha256 igual al guardado; versión en línea para imprimir; dos descargas, dos eventos `IMPORT_DIFFERENCE_REPORT_DOWNLOADED` |
| c · Doble emisión | Mismo estado: 409 `DIFFERENCE_REPORT_UNCHANGED`, sin segunda fila |
| d · Revisión | Estado «nueva revisión»; emitir sobre un estado viejo da 409 `DIFFERENCE_REPORT_STALE`; R2 vinculada a R1 con el mismo correlativo; las líneas e incidencias de R1 no cambian; un evento `IMPORT_DIFFERENCE_REPORT_REISSUED`; historial con R2 como vigente |
| e · Sin diferencias | Estado «Sin diferencias»; emitir da 422 `DIFFERENCE_REPORT_NO_DIFFERENCES`, sin fila |
| f · Diferencia documental | Una incidencia documental sin línea ni cantidad basta para emitir |
| g · Solo observadas | Una diferencia observada en la línea, sin incidencia, cuenta como diferencia |
| h · Permisos | Rol de solo lectura: consulta y descarga sí, emisión 403 |
| i · Aislamiento | Recepción de otro expediente, reporte y PDF ajenos, expediente de otra empresa: 404 con su código |
| j · Evidencia | Sin documentos, evidencia vacía; un documento vinculado a la incidencia abre nueva revisión y aparece con tipo, código y título |
| k · Desde Recepciones | El listado por recepción devuelve el expediente y sus reportes |
| l · Integridad | Un PDF alterado en el almacenamiento no se entrega: `STORAGE_HASH_MISMATCH` |
| m · Concurrencia | Dos emisiones simultáneas: exactamente una se consolida y la otra recibe conflicto |

La emisión de la revisión 1 (`IMPORT_DIFFERENCE_REPORT_ISSUED`) la registra el servicio y la acción está en el catálogo, pero ninguna prueba del ciclo afirma ese evento: brecha de prueba declarada.

## Resto de puertas

| Puerta | Resultado |
|---|---|
| Alembic | upgrade, downgrade a `0089_fusion_gov_landed` y upgrade: PASS en PostgreSQL |
| Guardas (catálogo 422, cabeza, migraciones, instantáneas del frontend, landed cost, costos) | 68 de 68 en PostgreSQL |
| Convergencia ORM/base (`test_n10_convergence`) | Las cuatro tablas nuevas convergen. La prueba sigue fallando por seis tablas de importaciones anteriores (`created_by`), igual que en `HEAD` previo: deuda fuera de alcance |
| Regresión completa del backend en PostgreSQL | 5073 pasadas. 72 fallos y 8 errores, ninguno de este ciclo: fallaban igual en `HEAD` previo o eran del entorno de la corrida (sin `caplog`, sin `pg_dump`, sin analizador) |
| E2E Chrome (`importaciones.spec.ts`, paso 4.5: R1, PDF, impresión, R2, historial y Recepciones) | PASS a 1280, 390 y 320 px; limpieza LIMPIA |
| Axe WCAG 2.2 AA en los cuatro estados de la región | 0 violaciones a 1280 y 320 px (sonda local, fuera del repositorio) |
| Desborde horizontal | Ninguno a 390 y 320 px en los cuatro estados |
| Frontend | TSC, ESLint (0 avisos), Vitest 1846 de 1846, build |
| Backend estático | Ruff limpio; mypy 154, igual a la línea base |

## Defectos reales encontrados y corregidos

- **Estado viejo en pantalla.** Tras resolver una incidencia y volver al expediente, la región decía «Sin diferencias»: React Query servía la caché (30 s). Corregido con `refetchOnMount: "always"`, el patrón del detalle del expediente. Lo destapó la E2E real, no Vitest.
- **Fechas en SQLite.** Las fechas de escalamiento y resolución viajaban como texto ISO a columnas `DateTime`. Corregido en el servicio.
- **ORM y base.** Las cuatro tablas nuevas heredaban `created_by` anulable, contra el `NOT NULL` de la migración. Corregido en el modelo.
- **Selectores.** El selector de la E2E, que dictó Claude en el brief, coincidía con dos secciones. Sustituido por rol y nombre accesible; la sección de Recepciones recibió nombre accesible.
