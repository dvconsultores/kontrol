# Data Model: CTL-10

Tablas de alcance empresa, solo `gov_*`. Sin dinero. Sin FK compuestas con `company_id`, por norma: la empresa cruzada se valida en el servicio. Migración `0075_gov_ctl10_cierres`.

## gov_closure_policies (Política)
`tenant_id`, `company_id`, `codigo` `PC-###` por empresa (hasta 10), `nombre` (3–200), `accion_cierre` ORG02_CERRAR_ESTRUCTURA|TRE02_CERRAR_PROGRAMA, `fundamento` (≥10, hasta 1000), `estado` BORRADOR|VIGENTE|RETIRADA, `vigente_desde` (fecha), `vigente_hasta` (nulo), `activada_por`, `activada_en`, `retirada_por`, `retirada_en`, `motivo_retiro`, `version`, `created_by`, marcas de tiempo.

Únicos: empresa + código. Índice único parcial: empresa + accion_cierre donde estado = VIGENTE. Checks: VIGENTE exige `activada_por` y `activada_en`; RETIRADA exige (`retirada_por`, `retirada_en`, `motivo_retiro`); `activada_*` puede ser nulo en una RETIRADA que nunca fue vigente; `vigente_hasta` ≥ `vigente_desde`. Disparador: VIGENTE o RETIRADA no editables en contenido ni borrables; solo las transiciones a RETIRADA (desde BORRADOR o VIGENTE) con sus campos de retiro. Sin borrado.

## gov_closure_controls (Control)
`tenant_id`, `company_id`, `policy_id`, `tipo` HALLAZGOS_ABIERTOS|ACTOS_SIN_EFICACIA, `riesgo_minimo` ALTO|MEDIO|BAJO (obligatorio si HALLAZGOS_ABIERTOS, nulo si ACTOS_SIN_EFICACIA), `materialidad` (10–500), autoría. Único: policy + tipo. Disparador: sin alta, cambio ni baja si la política no está en BORRADOR.

## gov_closure_policy_history (Historia)
`tenant_id`, `company_id`, `policy_id`, `evento` CREADA|ACTUALIZADA|CONTROL_ANADIDO|CONTROL_RETIRADO|ACTIVADA|RETIRADA, `detalle` JSON sin dinero ni ejecutable, `usuario`, `instante`. Inmutable por disparador (sin UPDATE ni DELETE).

## Estados

| Desde | Acción | Capacidad | Condición | A | Motivo | Auditoría | MFA | Reversible |
|---|---|---|---|---|---|---|---|---|
| — | Crear | manage | datos válidos | BORRADOR | — | GOV_CLOSURE_POLICY_CREATED | no | retirar |
| BORRADOR | Editar | manage | If-Match | igual | — | _UPDATED | no | sí |
| BORRADOR | Añadir control | manage | tipo no repetido | igual | — | _CONTROL_ADDED | no | quitar |
| BORRADOR | Quitar control | manage | If-Match | igual | — | _CONTROL_REMOVED | no | añadir |
| BORRADOR | Activar | activate | ≥1 control; sin otra VIGENTE para la acción | VIGENTE | — | _ACTIVATED | sí | retirar |
| BORRADOR | Retirar | activate | — | RETIRADA | 10–500 | _RETIRED | sí | no |
| VIGENTE | Retirar | activate | — | RETIRADA | 10–500 | _RETIRED | sí | no |

Efectiva hoy: VIGENTE, `vigente_desde` ≤ hoy y (`vigente_hasta` nulo o ≥ hoy), fecha civil de Caracas.

## Pendientes por tipo (consulta fija, al evaluar)
- HALLAZGOS_ABIERTOS: `gov_findings` de la empresa con `estado <> 'CERRADO'` y `riesgo` ≥ `riesgo_minimo` (orden ALTO > MEDIO > BAJO). Muestra: `codigo`, `titulo`, `/gobierno/hallazgos/{id}`.
- ACTOS_SIN_EFICACIA: `gov_acts` de la empresa con `status = 'EMITIDO'` y `fecha` dentro del año del ejercicio. Muestra: `numero`, `asunto`, `/gobierno/actos/{id}`.
