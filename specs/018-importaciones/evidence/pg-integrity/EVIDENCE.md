# Evidencia · IMP-PG-INTEGRITY-01

**Fecha:** 2026-11-09. **Datos:** sintéticos, en bases PostgreSQL efímeras de QA.

| Campo | Valor |
|---|---|
| DATABASE_ENGINE | PostgreSQL 16.2, binario fijado por hash en `qa/postgres_qa.json` |
| SCHEMA_SOURCE | Migraciones de Alembic, desde base vacía |
| BROWSER | Google Chrome (`channel: chrome`), con `qa/e2e-run.py --con-analizador` |
| NO_MODEL_CREATE_ALL | 1 en la E2E. Las pruebas de backend siguen usando `create_all` (`tests/conftest.py`); por eso la prueba de migración crea su propia base con Alembic |

## Defectos reales sobre PostgreSQL

| Defecto | Efecto | Corrección |
|---|---|---|
| `created_at` y `updated_at` sin default en 5 tablas publicadas y 1 local | Crear un expediente daba 500 | Migración `0086_importaciones_timestamps`; `0087_importaciones_gastos` nace correcta |
| `created_by` no se registraba en seguimiento, enlaces financieros ni correcciones, y es `NOT NULL` en la base | Registrar seguimiento, anticipo o corrección daba 500. Sobre SQLite el autor salía «desconocido» | El servicio registra el actor |
| Ayudantes de prueba con ids inexistentes | 12 pruebas no llegaban al producto sobre PostgreSQL | Datos sintéticos válidos |
| `lib/format.ts` importaba los índices completos de `date-fns` | Carga de ~1,8 s en Vitest | Importa `date-fns/format` y `date-fns/locale/es` |
| `importaciones.test.tsx` medía la transformación de módulos. También fallaba en lo publicado con la suite completa | Prueba roja bajo carga | Precarga de los módulos en la preparación, sin cambiar esperas |
| Notificaciones arriba, sin tope de altura y translúcidas | En teléfono cubrían la pantalla | Abajo, tope de 40vh, scroll propio y fondo opaco. **Queda deuda, ver abajo** |
| Costos decía que faltaba una decisión de la dueña, ya tomada | Mensaje falso | «Distribución aún no disponible» |

## Resultados en el árbol final

| Puerta | Resultado |
|---|---|
| Migración sobre PostgreSQL: upgrade, downgrade, upgrade, con fila previa | PASS; la fila conserva sus fechas |
| `alembic upgrade 0084…:head --sql` | PASS |
| Backend dirigido sobre PostgreSQL | 146 de 146, 0 omitidas |
| Backend dirigido sobre SQLite | 146: 133 pasan, 13 omitidas por exigir PostgreSQL |
| Vitest completo | 1832 de 1832 |
| TSC, ESLint (`--max-warnings 0`), build, Ruff | Limpios |
| mypy | 154, igual a la línea base; 0 en `imports` |
| E2E canónica, Chrome, PostgreSQL, 1280 px | PASS, 53,6 s, 0 respuestas 500 |

La E2E recorre un solo expediente: alta, negociación, orden, documentos, anticipo, agente, seguimiento, corrección, despacho, arribo, recepción, incidencia, confirmación de inventario, ubicación («Recibida y ubicada»), y después gastos: rechazo sin tasa, registro, tasa histórica, consulta, anulación con motivo e historial. Capa de costo en USD visible para una orden USD.

Vector observado: `1.250,50 × 36,125 = 45.174,31`. Es evidencia, no está en el código.

## Teléfono: alcance exacto

Corrida en Chrome sobre PostgreSQL a 390 y 320 px: PASS, con `scrollWidth == clientWidth` en las 7 pantallas medidas. **Se hizo con una copia de diagnóstico de la E2E**, no con la spec real, que usa el enlace del menú lateral y no cierra notificaciones. La copia abre el menú con su botón, cierra las notificaciones antes de cada clic y acota un selector. Prueba que el flujo es posible en un teléfono, no que sea cómodo.

## Deuda abierta

- **IMP-MOBILE-NOTIF-01:** cada acción deja una notificación persistente (FR-008). En teléfono, apiladas abajo, tapan los botones del pie hasta cerrarlas a mano. La corrección propuesta por DeepSeek dejaba visible la más antigua, no la más reciente, y se rechazó con el presupuesto agotado.
- **IMP-CONFIRM-UUID-01:** Inventario → Confirmación muestra el id técnico recortado en la columna Producto. Corregirlo exige exponer el nombre en la API de conciliación.
- **Sin verificar en navegador:** elegir documento de soporte y gasto con factura vinculada. El contrato y las pruebas de API los cubren; la E2E no.
- `created_by` queda `NOT NULL` en la base y anulable en el modelo; `import_corrections.version` es `INTEGER` en la base y `BIGINT` en el modelo. Sin efecto funcional hoy.
