# PROC-08 · Delta «Límite monetario de la autoridad» (OQ-OMA-01, parte de autoridad de OBS-PROC08-MONTO-01)

- **Autorización.** Encargo de la dueña «P2 · PROC-08 · CONTROL DE LÍMITE MONETARIO DE AUTORIDAD», del 2026-11-14.
- **Decisión que lo habilita.** `OQ-OMA-01 = BLOCK_WITH_DECLARED_TOTAL_SAME_CURRENCY`, cerrada por la dueña en ese mismo encargo.
- **Spec dueña.** PROC-08. El delta sustituye PDD-PROC08-13 («Límites de monto: no aplican»).
- **Evidencia.** `evidence/limite-monto/`.

## Qué podrá hacer el usuario que antes no podía

Al adjudicar, la sección Decisión muestra, para el acto y la oferta elegidos:
- el monto declarado de la oferta y su moneda;
- la autoridad efectiva, es decir, el cargo que dicta el acto;
- su límite de aprobación;
- el resultado de la validación.

Si la autoridad no alcanza, KONTROL **bloquea** la adjudicación con un mensaje comprensible. El usuario no puede saltarse el bloqueo: tiene que usar el acto de una autoridad con límite suficiente.

## Requisitos

| Id | Requisito |
|---|---|
| AAL-01 | **Alcance.** El control solo se aplica al resultado `ADJUDICADA` y a la oferta realmente adjudicada (`oferta_id` de la opción en orden de prelación) |
| AAL-02 | **Monto que manda.** `total_con_tributos` de la versión vigente del monto declarado (PROC-06 OMA). Nunca el monto sin IVA, una suma recalculada, el presupuesto, la garantía ni una estimación |
| AAL-03 | **Actor efectivo.** El usuario que registra, con la guarda funcional vigente (`exigir_autoridad_funcional`, ORG-06/07). No cambia |
| AAL-04 | **Cargo efectivo.** `acto.cargo_id`, el cargo emisor del acto DOC-02 que sostiene la decisión. Se usa la misma fecha que PROC-08 ya usa para validar la autoridad: `acto.fecha` |
| AAL-05 | **Competencia efectiva.** La competencia `APROBAR` × `CONTRATACIONES` de ese cargo en vigor en `acto.fecha` (`competencias_en_vigor`, ORG-03/07), la misma que valida `_autoridad_valida`. La delegación (ORG-04) copia el límite del cargo delegante, así que no hay otro límite |
| AAL-06 | **Sin límite.** `tipo_limite = SIN_LIMITE` → PASS, aunque la oferta no tenga monto. No se inventa un máximo |
| AAL-07 | **Misma moneda.** `tipo_limite = MONTO` y misma moneda: PASS si `total_con_tributos ≤ limit_amount`. Comparación `Decimal` exacta, sin redondeo |
| AAL-08 | **Exceso.** `total_con_tributos > limit_amount` → **409 `GOV_DECISION_AUTHORITY_AMOUNT_EXCEEDED`**. El mensaje nombra el monto, la moneda, el límite, la moneda del límite y el cargo. No se escribe nada |
| AAL-09 | **Moneda distinta.** → **409 `GOV_DECISION_AUTHORITY_CURRENCY_MISMATCH`**: «No puede verificarse el límite de esta autoridad porque la oferta y el límite están expresados en monedas diferentes.» No se convierte la moneda ni se consulta ninguna tasa |
| AAL-10 | **Sin monto.** `MONTO` y una oferta sin monto declarado → **409 `GOV_DECISION_OFFER_AMOUNT_REQUIRED`**. No se asume 0 ni se hace backfill. El monto ya no puede declararse (la evaluación está concluida, OMA-06), así que solo puede adjudicar una autoridad sin límite |
| AAL-11 | **Sin override.** No existe campo, permiso ni confirmación que salte el bloqueo |
| AAL-12 | **Otros resultados.** `DESIERTA`, `TERMINADA` y `NULIDAD` no se comparan |
| AAL-13 | **Confidencialidad.** PROC-08 opera tras la evaluación, así que el monto ya es legible. La auditoría y la cronología **no** llevan importes; el mensaje de error, que solo ve el usuario autorizado, sí |
| AAL-14 | **Concurrencia.** La decisión ya bloquea el expediente (If-Match + `FOR UPDATE`). Además, el control bloquea la fila de la estructura del cargo, la misma que bloquea ORG-03 al editar un cargo, y lee el límite y el monto dentro de esa transacción. La vista previa no autoriza nada: el backend recalcula siempre |
| AAL-15 | **Pantalla, E2E y UAT.** Panel «Control del límite de autoridad» con los 5 datos, sin UUID. E2E del recorrido bloqueo → autoridad suficiente → adjudicación, con Axe a 1280, 390 y 320. Tarjeta de la dueña |

**Auditoría del bloqueo.** Es un rechazo material de autoridad y sigue el patrón de las guardas (`GOV_IDENTITY_GUARD_BLOCKED`, `GOV_MATERIAL_CLOSE_BLOCKED`): `record_audit_after_rollback` con la acción nueva `GOV_PROCUREMENT_DECISION_AUTHORITY_BLOCKED` (SECURITY / REJECTION). El detalle lleva acto, oferta, causal (el código) y resultado, **sin importes**. El catálogo pasa de 526 a 527 entradas.

**Permiso.** Se reutiliza `gobierno_decision:decide`, que ya es SENSITIVE y pide MFA. No hay permiso nuevo.

## Estados de la vista previa

| Estado | Etiqueta | ¿Permite? |
|---|---|---|
| `DENTRO_LIMITE` | Dentro del límite | Sí |
| `SIN_LIMITE` | Sin límite | Sí |
| `EXCEDE_LIMITE` | Excede el límite | No (AAL-08) |
| `MONEDA_DISTINTA` | No comparable por moneda | No (AAL-09) |
| `MONTO_NO_DECLARADO` | Monto no declarado | No (AAL-10) |
| `SIN_COMPETENCIA` | Sin competencia vigente | No. Ya lo rechaza `GOV_DECISION_INVALID_ACT`; solo se muestra |

## Decisiones de diseño (Claude; reversibles; ninguna material)

| Id | Decisión | Por qué |
|---|---|---|
| OD-AAL-01 | Un solo módulo, `service_decision_limite.py`, que usan a la vez la vista previa y la ejecución | La misma regla en los dos sitios; sin segundo motor ni tabla nueva |
| OD-AAL-02 | La vista previa viaja en `actos_elegibles[].control_monto` del GET de decisión | No hay endpoint paralelo de «validar monto» |
| OD-AAL-03 | Los 3 errores son 409 `ConflictError` con `details` | Son conflictos con la autoridad institucional vigente |
| OD-AAL-04 | Bloqueo `FOR UPDATE` de `gov_structures` del cargo | Es el mismo bloqueo que toma `cargo_para_escribir` (ORG-03), así que serializa el cambio de límite con la decisión |
| OD-AAL-05 | El botón no se desactiva por la vista previa | El backend es la autoridad. El usuario intenta y recibe el bloqueo comprensible (recorrido del sponsor, pasos 5 y 6) |

## Fuera de alcance

- **OQ-OMA-02** (jurídica): sigue abierta.
- **PROC-09:** sigue BLOCKED.
- **OBS-PROC08-PARCIAL-01:** sigue abierta. No se construye adjudicación por línea, parcial ni con varios adjudicatarios.
- **Conversión de moneda:** queda para cuando exista una autoridad de tasas con procedencia verificable. TRE-09 todavía no existe.

## Constitution Gate

```text
OQ_OMA_01=CLOSED
OFFER_TOTAL_AUTHORITY_CLEAR=1
COMPETENCY_AUTHORITY_CLEAR=1 (competencias_en_vigor del cargo del acto)
EFFECTIVE_DATE_CLEAR=1 (acto.fecha, la misma de _autoridad_valida)
SAME_CURRENCY_RULE_CLEAR=1
OVER_LIMIT_RULE_CLEAR=1
CURRENCY_MISMATCH_RULE_CLEAR=1
LEGACY_RULE_CLEAR=1
MIGRATION_REQUIRED=0
MATERIAL_DECISION_REQUIRED=0
CONSTITUTION_GATE=PASS
```

## Plan

| Capa | Ficheros |
|---|---|
| Servicio | `service_decision_limite.py`, nuevo: `competencia_aprobar_contrataciones`, `evaluar_limite` y `exigir_limite` |
| Ejecución | `service_decision_resolver.registrar_decision`, en la rama ADJUDICADA, tras validar la opción |
| Vista previa | `service_decision._parte_decision`: `limite` y `control_monto` en cada acto elegible |
| Auditoría | Entrada `GOV_PROCUREMENT_DECISION_AUTHORITY_BLOCKED` en el catálogo y su recuento (526→527) |
| Frontend | `ExpedienteDecision.tsx`, panel «Control del límite de autoridad», con su Vitest |
| Pruebas | `test_gov_proc08_limite_monto.py`, nuevo: los 7 casos, concurrencia, auditoría, vista previa y aislamiento |
| E2E | `helpers/gobierno.ts` (límite opcional en `cargoVigenteApi` y `declararMontoApi`), el recorrido en `gobierno-decision.spec.ts` y el monto en `gobierno-garantias.spec.ts`, porque su cargo tiene un límite de 50000 USD |

Sin migración, sin tabla nueva y sin endpoint nuevo. Llamadas previstas a DeepSeek: 4 (backend, pruebas, frontend y E2E).
