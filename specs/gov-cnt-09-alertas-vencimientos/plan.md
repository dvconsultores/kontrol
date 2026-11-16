# Plan · CNT-09 Alertas de vencimientos

## Constitution Gate

```text
GOV_CNT_010_CLEAR=1
CONTRACT_EXPIRY_SOURCE_CLEAR=1   (terminos_efectivos → fecha_fin)
GUARANTEE_EXPIRY_SOURCE_CLEAR=1  (GovernmentGuaranteeInstrument.vigente_hasta, estado REGISTRADA)
MILESTONE_DUE_SOURCE_CLEAR=1     (fecha_prevista; VIGENTE y no cumplido)
DELIVERABLE_DUE_SOURCE_CLEAR=1   (fecha_vencimiento; VIGENTE y sin entrega CONFORME)
CNT02_EFFECTIVE_TERMS_REUSED=1   CNT03_REUSED=1   PROC10_REUSED=1 (_vigencia + DIAS_POR_VENCER)   SPEC047_REUSED=1
ALERT_POLICY_CLEAR=1   DUE_TODAY_CLEAR=1   OVERDUE_CLEAR=1
ADVANCE_WARNING_POLICY_CLEAR=1   (solo configuración institucional; por defecto, ninguna)
GUARANTEE_15_DAY_RULE_CLEAR=1    (importada, no copiada)
SIGNATURE_BUSINESS_DAY_ALERT=DEFERRED_BY_CALENDAR_AUTHORITY
ALERT_DOES_NOT_DECIDE=1   ALERT_DOES_NOT_MUTATE_SOURCE=1
P1_P2_OVERLAP=0 (no toca CNT-08)   MATERIAL_DECISION_REQUIRED=0
CONSTITUTION_GATE=PASS
```

**Decisiones de diseño (de Claude, dentro de lo que fija el encargo):**
- **PDD-CNT09-01. Por qué una tabla de política propia.** `NotificationRule.reminder_offset_minutes` solo admite `effect = TASK`; usarla para ALERT alteraría la Spec 047. Por eso se crea una tabla mínima, que solo decide cuándo CNT-09 llama a `crear_alerta`.
- **PDD-CNT09-02. Severidades:**

  | Fase | Contrato, hito o entregable | Garantía |
  |---|---|---|
  | UPCOMING | INFO | WARNING (la semántica «por vencer» de PROC-10) |
  | DUE_TODAY | WARNING | WARNING |
  | OVERDUE | CRITICAL | CRITICAL |

  Son operativas, no jurídicas.
- **PDD-CNT09-03. Origen de las alertas.** Las de contrato, hito y entregable tienen como `source_id` el contrato, para que la ficha las reúna. Las de garantía tienen como `source_id` el expediente de PROC-10, que es donde se gestionan.
- **PDD-CNT09-04. Reaparición.** Una clave RESUELTA no se reabre. Si la condición vuelve (por ejemplo, se anula la recepción parcial y el hito queda otra vez pendiente), se crea `…:r<n>`, una clave nueva y determinista.

## Modelo

Tabla `gov_contract_alert_policies` (`GovernmentContractAlertPolicy`, Scope.COMPANY):

| Columna | Tipo | Restricción |
|---|---|---|
| `id` | — | UUIDMixin, TimestampMixin |
| `company_id` | FK companies | — |
| `fuente` | String(12) | IN (CONTRATO, HITO, ENTREGABLE) |
| `activo` | bool | — |
| `dias_anticipacion` | int | 1–365 |
| `actualizado_por` | String(36) | — |
| — | — | UNIQUE(company_id, fuente) |

Migración `0120_gov_cnt09_alertas`, sobre `0119_gov_cnt03_ejecucion` (sin permisos nuevos). Tras el merge ordinario con el CNT-08 de P2 (que publicó `0120_gov_cnt08_expediente`), la migración, aún sin publicar, se reencadenó como `0121_gov_cnt09_alertas` sobre `0120_gov_cnt08_expediente`.

## Servicio `service_contratos_alertas.py`

- Constantes: los 4 `SOURCE_TYPE_*`, las route keys, `CATEGORIA_*` (`gov.contract.deadline`, `gov.guarantee.deadline`, `gov.milestone.deadline`, `gov.deliverable.deadline`) y `SEVERIDADES`.
- `fase(fecha, hoy, dias_anticipacion) -> str | None` y `fase_garantia(instrumento, hoy) -> str | None`, que llama a `service_garantias._vigencia`.
- `condiciones(db, company_id, hoy) -> list[Efecto]`: las alertas deseadas, construidas con las autoridades de origen.
- `reconciliar(db, company_id, hoy, momento, correlation_id) -> tuple[int, int]` (creadas, resueltas):
  - crea las deseadas, con el sufijo `:r<n>` si la clave base ya está RESUELTA;
  - resuelve las ACTIVE de los 4 `source_type` cuya clave base no está deseada.
- `detectar(contexto) -> Resultado`: el manejador del planificador. Recorre por empresa las que tienen contratos FORMALIZADO o garantías REGISTRADA, con una sesión y un commit por empresa.
- `alertas_del_contrato(db, ctx, user, contrato_id, estado)` y `politicas(db, ctx)` / `guardar_politicas(db, ctx, user, filas)`.

## API (`api_contratos_alertas.py`)

| Método y ruta | Permiso |
|---|---|
| `GET /gobierno/contratos/{contrato_id}/alertas?status=ACTIVE` | `gobierno_contratos:view` |
| `GET /gobierno/contratos-alertas/politicas` | `gobierno_contratos:view` |
| `PUT /gobierno/contratos-alertas/politicas` | `notificaciones:configure` (escritura) |

Todas las rutas llevan `require_module("gobierno")`.

## Cableado

- `scheduler/registry.py`: el manejador nuevo.
- `notifications/catalogo.py`: los 4 ORIGENES.
- `notifications/messages.py`: 12 claves (4 tipos × 3 fases).
- `main.py`: el router nuevo.
- `audit_catalog_entries.py`: GOV_CONTRACT_ALERT_POLICY_UPDATED (catálogo 574 → 575).
- Fijaciones de cabeza → 0120.

## Frontend

- `notificaciones/api.ts`: ENLACES `gov_contract`, `gov_contract_execution` y `gov_procurement_file`.
- `i18n/es.ts`: las categorías nuevas.
- `AlertasPage`: filtros por severidad y por origen.
- `contratos/AlertasContrato.tsx`: embebido en `ContratoPage` cuando el contrato está FORMALIZADO; muestra «Alertas activas: N», la lista y un enlace a `/alertas`.
- `contratos/AlertasPoliticaPage.tsx` en `/gobierno/contratos-alertas`: política editable con `notificaciones:configure` y explicación de las reglas fijas. Va en el menú «Gobierno · Contratos › Alertas de vencimiento» y en PANTALLAS.

## E2E

En `gobierno-contratos.spec.ts`, dentro del tramo CNT-03:
1. Hito y entregable con fecha de hoy.
2. Tick del planificador.
3. `/alertas` muestra las alertas de CNT-09, con su enlace a la ejecución.
4. La ficha del contrato muestra «Alertas activas».
5. Se conforma la entrega y se recibe el hito; tick; las alertas quedan RESUELTAS.
6. El estado del contrato, del hito y del entregable no cambió por CNT-09.

Se comprueba a 1280/390/320 y con Axe.

## Llamadas a DeepSeek previstas (deepseek-v4-pro; objetivo 3–5, tope 8)

| Llamada | Alcance |
|---|---|
| D1 | Backend: modelo, migración, servicio, API, cableado y fijaciones |
| D2 | Pruebas PG |
| D3 | Frontend y Vitest |
| D4 | E2E |
| D5–D8 | Reserva para correcciones |
