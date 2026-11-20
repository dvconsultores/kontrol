# TRE-05 · Pausa (2026-11-20)

**Decisión de la dueña:** pausar con WIP local, sin push. El ciclo **no está certificado**. `OWNER_UAT_READY=NO`.

## Dónde está el trabajo

- **Worktree:** `~/.cache/kontrol-qa/ctl05`, desacoplado de `origin/develop`.
  - Base `9f2c3dd`. Commit WIP local: ver `git log -1` en el worktree.
  - **No publicado.**
- **Migración:** `0129_gov_tre05_retencion`, sobre `0128_gov_tre04_pago`; una cabeza.
  - No publicada, así que aún puede cambiarse.
  - Si P2 publica antes otra `0129`, hay que reencadenar.
- **DeepSeek:** 31 de 40 llamadas, 0,247421 USD. Detalle en `ATTEMPT_LOG.md`.

## Qué funciona (medido)

- **Backend**, con ruff limpio y mypy en 157 (línea base, 0 nuevos):
  - modelos, guardas PG, permisos, MFA, auditoría (15 eventos) y CTL-01 TRE-05;
  - políticas versionadas;
  - motor;
  - liquidación con maker-checker;
  - comprobantes con instantánea y PDF;
  - integración TRE-04.
- **Pruebas backend:** 28/31 en verde en PG con el fixture de ámbito módulo, antes de la llamada 29.
  - En verde: cálculo, umbral MONTO y MULTIPLO_TASA, exclusiones, varias reglas, bruto/neto, Decimal, moneda, ajuste, aprobación y autoridad, MFA, CTL-01, comprobante exigido, numeración, instantánea y PDF, anulación y sustitución, guardas PG e integración TRE-04.
- **Frontend:** tsc 0 y eslint limpio. Incluye:
  - políticas (lista, catálogo, numeración, ficha con editor de reglas);
  - la sección «Retenciones» en el detalle del pago;
  - la página «Retenciones» con pestañas liquidaciones y comprobantes;
  - el menú y las pantallas.

## Defectos pendientes, en orden de resolución

1. **Fixture de pruebas backend (error del encargo de Claude, llamada 29).**
   - El problema: `_aislar_caches_*` pasó a ámbito de función y limpia también las cachés de usuarios. Resultado: `ConflictError: Ya existe un usuario` en 28/31.
   - Qué hacer: volver a `scope="module"` en los dos ficheros.
   - Pendiente después: el caso 14 falla dentro de la suite porque el compromiso BUD-08 da 422 al acumular pagos del módulo. La salida es repartir los pagos o mover el caso 14 a su propio módulo (`tests/test_gov_tre05_retencion_c.py`) con su propio mundo.
   - Pendientes 27 y 28: con PFIX-6 ya aplicado, deberían pasar; hay que medirlo.
   - E741: renombrar las variables `l` del caso 14.
2. **Vitest: 8/24.**
   - `PoliticasRetencion.test.tsx`: los botones «Catálogo», «Alta de concepto» y «Guardar» no existen.
     - En la lista, el catálogo y la numeración son secciones de la misma página; los botones reales son «Añadir concepto», «Añadir condición» y «Guardar patrón».
     - Falta `afterEach` en el import.
     - `ApiError` se construye como `new ApiError(status, {code, message, field_errors})`; hay que mirar la firma en `src/api/client.ts`.
   - `Retenciones.test.tsx`:
     - las listas devuelven arrays, no `{items, total}`;
     - el ifMatch es `String(version)` (p. ej. "1"), no "N";
     - el botón de ajuste y el de confirmación de diálogos usan los rótulos reales de `ConfirmationDialog` (`confirmLabel`).
3. **E2E, sin empezar** (§49–§55): principal, varias reglas, umbral, exclusión, versión congelada, comprobante; Axe a 1280/390/320. Seguir el patrón de `e2e/gobierno-pagos.spec.ts` y `e2e/helpers/pagos.ts`.
4. **Humo UAT:** añadir `gobierno_retenciones:view` y las rutas `/gobierno/tesoreria/retenciones` («Retenciones») y `/gobierno/tesoreria/politicas-retencion` («Políticas de retención») a `e2e/uat-humo-gobierno.spec.ts`.
5. **Cierre:**
   - mutaciones M1–M10;
   - OpenAPI;
   - auditoría de hardcode;
   - fixtures del frontend (`qa/fixtures_de_frontend.py`);
   - PG dirigida y PG completa;
   - integración con P2;
   - tarjeta de la dueña;
   - matrices y DAG;
   - commit, push y build-dev;
   - pila UAT;
   - CIERRE.md.

## Observaciones

- **OBS-TRE05-DOC-01:** `GovernmentWithholdingReceipt.document_id` existe pero no se usa. El PDF se genera bajo demanda desde la instantánea, con huella verificada.
- **OBS-TRE05-AUDIT-01:** `GOV_WITHHOLDING_SETTINGS_UPDATED` usa `entity_id = company_id`; el patrón TRE-04 podría preferir el id de la fila.
- **Calidad de DeepSeek en este ciclo:** formatos alterados, atributos inexistentes y entregas parciales. Con dos ficheros pedidos, solo devuelve el primero. Los encargos que mejor funcionaron fueron de un solo fichero, con las líneas exactas y los errores medidos.
