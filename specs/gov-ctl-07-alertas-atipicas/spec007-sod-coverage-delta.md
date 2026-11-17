# Delta · GOV-SOD-COVERAGE-01 · cobertura canónica de bloqueos SoD (2026-11-17)

- **Spec dueña:** `specs/gov-ctl-07-alertas-atipicas` (GOV-CTL-009).
- **Spec afectada:** `specs/gov-rep-10-control-interno`, con un puntero en `spec010-sod-coverage-pointer.md`.
- **Origen:** defectos P0 de `GOV-PARAMETERIZATION-AUDIT-01` en CTL-07 y REP-10.
- **Autorización:** el encargo «P2 — GOV-SOD-COVERAGE-01».
- **Evidencia:** `evidence/sod-coverage/`.

## Defecto

Hoy hay tres productores de bloqueos por segregación de funciones:

| Acción | Productor | `entity_id` | `after` |
|---|---|---|---|
| `GOV_SOD_CONFLICT_BLOCKED` | CTL-01, matriz por acción (`service_sod`), y ORG-06 (`service_identidad`) | `GovernmentSoDRule.id` | `regla_codigo`, `regla_version`, `proceso`, `accion`, `accion_previa`, `objeto_*` |
| `GOV_SOD_ROLE_CONFLICT_BLOCKED` | PROC-11, funciones incompatibles (`service_sod_funciones`) | expediente | `regla_codigo`, `regla_version`, `funcion`, `funcion_previa`, `expediente_id`, `expediente_numero`, `actor` |
| `GOV_BUDGET_COMMITMENT_SOD_BLOCKED` | BUD-08, quien certifica no compromete (`service_presupuesto_compromiso`) | ejercicio | `anio`, `certificados`, `regla` (texto) |

Los consumidores mantienen listas parciales propias:

- `service_alertas.ACCIONES_SOD` omite BUD-08;
- `service_reporte_control._seccion_conflictos_sod` solo lee CTL-01.

## Causa raíz

No existe una autoridad que diga qué eventos de auditoría son bloqueos SoD y cómo leerlos. Cada consumidor repite la lista y la interpretación de `after` y `entity_id`. Por eso un productor nuevo queda invisible.

## Requisitos

- **FR-SC-01 · Autoridad única.** Se crea el módulo nuevo `service_sod_eventos.py`. Es el único sitio que conoce las acciones de bloqueo SoD:
  - mantiene un registro de productores (acción → adaptador) y expone `ACCIONES_SOD`;
  - `consultar()` filtra por tenant, empresa y, opcionalmente, por el intervalo semiabierto `[inicio, fin)`;
  - `normalizar()` devuelve la proyección canónica.

  Un productor nuevo se añade con un solo registro. Ni CTL-07 ni REP-10 nombran acciones SoD.
- **FR-SC-02 · Proyección canónica.** Cada evento normalizado lleva los campos siguientes:

  | Campo | Contenido |
  |---|---|
  | `evento_id`, `fecha`, `accion_auditoria` | Identificación del evento |
  | `proceso`, `proceso_etiqueta` | Proceso de origen |
  | `regla_codigo`, `regla_nombre`, `regla_version` | Regla aplicada |
  | `tipo_conflicto`, `tipo_conflicto_etiqueta` | Clase de conflicto |
  | `usuario_id`, `usuario` | Actor; `usuario` es `None` si no se conoce |
  | `recurso_tipo`, `recurso_id`, `recurso_etiqueta` | Objeto afectado |
  | `operacion_etiqueta`, `operacion_previa_etiqueta` | Las dos operaciones en conflicto |
  | `titulo`, `detalle`, `sujetos` | Texto para la alerta |
  | `evidencia` | Datos funcionales del productor |

  La interpretación por productor es esta:

  - **CTL-01:**
    - la regla se resuelve por `entity_id` contra `GovernmentSoDRule` de la misma empresa; el nombre se toma de la regla y, si no existe, es el código;
    - el proceso es `after.proceso` o el de la regla;
    - el tipo es `INCOMPATIBLE_ACTIONS` («Acciones incompatibles»);
    - las etiquetas de operación usan `etiqueta_de`, con «Operación de <proceso>» como respaldo;
    - el detalle no cambia.
  - **PROC-11:**
    - `entity_id` es el expediente, nunca la regla;
    - el nombre de la regla se resuelve contra `GovernmentSoDRoleRule` por `(empresa, regla_codigo)` y, si no existe, es el código;
    - el proceso es `PROC-11`;
    - el tipo es `INCOMPATIBLE_FUNCTIONS` («Funciones incompatibles»);
    - el recurso es `EXPEDIENTE` con su número;
    - el detalle no cambia.
  - **BUD-08:**
    - `entity_id` es el ejercicio, nunca una regla;
    - `regla_codigo` es `None` y `regla_nombre` es `after.regla`;
    - el proceso es `BUD-08`;
    - el tipo es `SEGREGATION_OF_DUTIES` («Segregación de funciones»);
    - el recurso es `BUDGET_YEAR` («Ejercicio <año>»);
    - la evidencia lleva `anio` y `certificados`.

  La etiqueta de proceso sale de `service_auditoria.PROCESOS`. Si el proceso no figura allí, se usa la etiqueta propia del adaptador. Completar `PROCESOS` es la deuda CTL-02 y queda fuera de alcance.
- **FR-SC-03 · CTL-07.**
  - `_autoaprobaciones` consume la autoridad: los tres productores generan alerta.
  - La clave sigue siendo `AUTOAPROBACION:<audit_event_id>`, estable y compatible con las revisiones existentes. El código interno de tipo `AUTOAPROBACION` no cambia.
  - Su etiqueta visible pasa a «Segregación de funciones», con una descripción que no presenta todo conflicto como autoaprobación.
  - El aviso se conserva.
- **FR-SC-04 · REP-10.**
  - `conflictos_sod` consume la autoridad y su total cuenta los tres productores, dentro del período, el tenant y la empresa.
  - `por_regla` agrupa por regla, proceso y tipo, y añade `tipo_conflicto` y `tipo_conflicto_etiqueta`. Se añaden también `por_proceso` y `por_tipo`.
  - Cada evento añade `proceso`, `tipo_conflicto`, `tipo_conflicto_etiqueta` y `recurso_etiqueta`. `regla_codigo` puede ser `null`.
  - El CSV incluye los tres tipos: la columna «Regla» muestra el código o, si no hay, el nombre, y se añaden «Tipo de conflicto» y «Recurso».
  - El período se mantiene `[inicio del día desde, fin del día hasta)`.
- **FR-SC-05 · Pantalla REP-10.**
  - El tipo de `regla_codigo` pasa a `string | null`.
  - Sin código, la pantalla muestra solo el nombre de la regla.
  - La tabla por regla muestra el tipo de conflicto.

  CTL-07 no cambia en la pantalla: el texto le llega del backend.
- **FR-SC-06 · Contrato de no divergencia.**
  - Ningún módulo de `app/`, salvo la autoridad, los cuatro productores y el catálogo de auditoría, contiene literales de acciones SoD de bloqueo.
  - Toda entrada del catálogo de auditoría con `SOD` en el código, sufijo `_BLOCKED` y clase `REJECTION` está registrada en la autoridad, y viceversa.

## Clasificación de plataforma y política

| Elemento | Naturaleza |
|---|---|
| `EVENT_TAXONOMY` | PLATFORM_INVARIANT: vocabulario de auditoría de plataforma |
| `RULE_CONFIGURATION` | DOMAIN/TENANT POLICY: cada dominio la define y la versiona (CTL-01, PROC-11, BUD-08) |

Este ciclo no cambia cómo se aplican las reglas.

## Fuera de alcance

- El motor de procesos.
- La clasificación arquitectónica de CTL-07 y REP-10.
- Completar `PROCESOS` (CTL-02).
- Dar un código de regla a BUD-08.

## Restricciones

- Sin migración ni cambio de esquema: `MIGRATION_REQUIRED=0`.
- Sin código específico de ningún tenant.
- Sin cambios en los productores.

## Gate

| Comprobación | Resultado |
|---|---|
| BLOCKER | 0 |
| CRITICAL | 0 |
| CONTRADICTIONS | 0 |
| OWNER CONFLICT | 0 |
| MATERIAL OQ | 0 |
| UNKNOWN | 0 |
| Trazabilidad | FR-SC-01..06 → T001..T004, 100 % |

## Tareas

| Tarea | Ejecutor | Modelo | Sensible | Egreso | Ficheros | Prueba | Hecho cuando |
|---|---|---|---|---|---|---|---|
| T001 · autoridad y consumidores | DEEPSEEK | v4-pro | NO | SAFE | `service_sod_eventos.py` (nuevo); `service_alertas.py`; `service_reporte_control.py` | PG de CTL-07, REP-10, PROC-11, BUD-08 y CTL-01 | Una sola lista SoD; ruff y mypy limpios en los ficheros |
| T002 · pruebas PG | DEEPSEEK | v4-pro | NO | SAFE | `tests/test_gov_sod_cobertura.py` (nuevo) | Las pruebas nuevas | Todas pasan y las mutaciones mueren |
| T003 · pantalla REP-10 y Vitest | DEEPSEEK | v4-pro | NO | SAFE | `ReporteControlInternoPage.tsx` y su prueba | Vitest | Casos sin código de regla y tipo visible |
| T004 · E2E y Axe 1280 de CNT-04 | DEEPSEEK | v4-pro | NO | SAFE | `e2e/gobierno-sod-cobertura.spec.ts` (nuevo); `e2e/gobierno-contratos-plazo-supervision.spec.ts` | `qa/e2e-run.py --con-analizador` | 1/1 en cada spec; Axe a 1280, 390 y 320 |

`RETRY_MAX` es 2.
