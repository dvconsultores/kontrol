# MATRIZ DE TRAZABILIDAD — SPEC 012

Derivada por script de `spec.md`, `tasks.md` y `acceptance-criteria.md`.
No se escribe a mano.

## 1. Cobertura — verificada por comando

| Métrica | Valor |
|---|---:|
| Requisitos funcionales | 47 |
| Requisitos no funcionales | 6 |
| Criterios de aceptación | 45 |
| Tareas | 83 |
| **Requisitos funcionales sin tarea ni criterio** | **0** |
| **Requisitos no funcionales sin tarea ni criterio** | **0** |
| **Criterios sin tarea que los cubra** | **0** |
| **Tareas sin requisito ni criterio** | **0** |

## 2. Requisito funcional → tarea

| Requisito | Enunciado | Tareas |
|---|---|---|
| FR-012-001 | `PriceList` por empresa, con moneda tomada del maestro monetario existente y s | T-012-006, T-012-010, T-012-061 |
| FR-012-002 | `PriceListVersion` con `valid_from` / `valid_to`; **una lista nunca se edita e | T-012-011, T-012-018 |
| FR-012-003 | `PriceListItem` por producto o categoría, con presentación y rango de volumen | T-012-013 |
| FR-012-004 | El precio se expresa en la unidad y presentación de la Spec 011; el factor se  | T-012-013, T-012-027 |
| FR-012-005 | Dos versiones de la misma lista **no** pueden solapar vigencia | T-012-012 |
| FR-012-006 | Una versión referenciada por un documento aprobado **no se borra ni se altera* | T-012-019, T-012-015 |
| FR-012-007 | Estados de versión: `DRAFT`, `ACTIVE`, `SUPERSEDED`, `ARCHIVED` | T-012-011 |
| FR-012-008 | La lista declara su **fuente**: quién la cargó y de dónde | T-012-016 |
| FR-012-010 | La precedencia es **dato configurable por empresa**, no código (`R-D0-05-1`) | T-012-021 |
| FR-012-011 | KONTROL entrega el orden por defecto documentado en `ADR-D0-005`, reordenable, | T-012-022 |
| FR-012-012 | Empate de precedencia: se resuelve por vigencia más reciente y, a igualdad, me | T-012-023 |
| FR-012-013 | Un empate **irresoluble** se reporta como error de configuración; **jamás** se | T-012-024 |
| FR-012-014 | `resolve_price(...)` es la **única** autoridad de precio del sistema | T-012-020 |
| FR-012-015 | La resolución devuelve el precio **y** la versión que lo produjo | T-012-025 |
| FR-012-016 | Sin lista aplicable, la resolución **no inventa** un precio: lo declara ausent | T-012-026 |
| FR-012-020 | Descuento de **línea** y de **documento** son entidades distintas | T-012-030 |
| FR-012-021 | `DiscountPolicy` define el máximo por rol, producto o categoría | T-012-030, T-012-032 |
| FR-012-022 | **Ningún porcentaje viene de fábrica.** El catálogo nace vacío | T-012-031 |
| FR-012-023 | Superar el límite **genera solicitud de aprobación** (Spec 045); no bloquea | T-012-033 |
| FR-012-024 | La acumulación es configurable; las incompatibilidades se declaran | T-012-034 |
| FR-012-025 | Todo descuento registra la política, su versión y el nivel de autorización | T-012-035 |
| FR-012-030 | `PaymentTerm` es maestro, **nunca** una cadena (`R-D0-05-3`) | T-012-001, T-012-060 |
| FR-012-031 | Estructura: días, cuotas, porcentajes, desplazamiento del vencimiento, contado | T-012-001 |
| FR-012-032 | El catálogo **nace vacío**: «contado» y «30 días» son datos de cada empresa | T-012-002 |
| FR-012-033 | Aplicable a cliente y a proveedor, sin duplicar el maestro | T-012-043 |
| FR-012-040 | `CommercialZone` es **territorio de ventas**, entidad distinta de `WarehouseZo | T-012-003 |
| FR-012-041 | Prohibido reutilizar la tabla de zona física por compartir el nombre «zona» | T-012-004 |
| FR-012-042 | `SalesChannel` como maestro; nace vacío | T-012-005 |
| FR-012-043 | La zona puede tener vendedor y ruta asignados | T-012-003 |
| FR-012-050 | El cliente puede tener lista, condición, zona, canal y vendedor **por referenc | T-012-040 |
| FR-012-051 | **No se duplica** `Party` ni `Customer`: se extiende con FK | T-012-040 |
| FR-012-052 | `CreditPolicy` es distinta de la condición de pago (`R-D0-05-4`) | T-012-041 |
| FR-012-053 | El bloqueo comercial conserva motivo, autor y fecha | T-012-042 |
| FR-012-060 | Al aprobarse un documento se congela: precio, descuento, política y versión, c | T-012-050, T-012-051, T-012-056 |
| FR-012-061 | Modificar un maestro **nunca** altera un documento aprobado (`R-D0-05-6`) | T-012-052 |
| FR-012-062 | La reconstrucción histórica se hace **desde el snapshot**, jamás recalculando | T-012-053 |
| FR-012-063 | `pricing_source` distingue precio resuelto, precio manual justificado y legado | T-012-054 |
| FR-012-070 | Contrato `resolve_price` para 029 / 034, sin implementar sus procesos | T-012-062 |
| FR-012-071 | Contrato de validación de descuento para 029, que dispara 045 | T-012-063 |
| FR-012-072 | Contrato de condición y crédito para 030 / 037 | T-012-041 |
| FR-012-073 | 012 **no** emite eventos ni notifica | T-012-067 |
| FR-012-080 | Las cadenas actuales se **anotan y conservan** en `legacy_value`; no se borran | T-012-044 |
| FR-012-081 | Una cadena ambigua **no** se convierte automáticamente: se marca para revisión | T-012-092 |
| FR-012-082 | Los documentos históricos **no reciben snapshot inventado**: `pricing_source = | T-012-093 |
| FR-012-083 | La migración informa cuántas cadenas hay de cada clase y **no crea ningún maes | T-012-090 |
| FR-012-090 | `SalesCommissionPolicy` queda **reservado** en el modelo, sin implementar | T-012-102 |
| FR-012-091 | 012 **no** calcula comisión ni toca nómina | T-012-102 |

## 3. Requisito no funcional → tarea

| Requisito | Enunciado | Tareas |
|---|---|---|
| NFR-012-01 | Resolver un precio no debe requerir recorrer todas las versiones: índice por l | T-012-017 |
| NFR-012-02 | Aceptación sobre **PostgreSQL 18.x** real (`P21`) | T-012-078 |
| NFR-012-03 | WCAG 2.2 AA sin violaciones serias; sin desbordamiento horizontal entre 320 y  | T-012-087, T-012-099 |
| NFR-012-04 | Pantallas completas, no modales para formularios complejos (`P18`, `ADR-015`) | T-012-088 |
| NFR-012-05 | **0 valores comerciales codificados**: verificable por comando | T-012-076 |
| NFR-012-06 | Todo importe en `Numeric`, jamás `float` (lección de la Spec 011) | T-012-076 |

## 4. Criterio de aceptación → tarea

| Criterio | Enunciado | Tareas |
|---|---|---|
| AC-012-01 | Una instalación recién creada tiene **0** condiciones de pago, **0** zonas, ** | T-012-002, T-012-086 |
| AC-012-02 | `grep` de porcentajes, plazos o nombres de lista en el código del módulo devue | T-012-076 |
| AC-012-03 | La precedencia por defecto vive en **tabla**, no en código, y se puede reorden | T-012-021 |
| AC-012-04 | Una `DiscountPolicy` sin `max_percent` no impone límite ni pide aprobación | T-012-031 |
| AC-012-05 | Crear una versión asigna correlativo **del servidor**; el del cliente se ignor | T-012-014 |
| AC-012-06 | Activar una versión que solapa vigencia con otra devuelve **409** | T-012-012 |
| AC-012-07 | Editar los ítems de una versión `ACTIVE` se rechaza; hay que crear otra versió | T-012-018 |
| AC-012-08 | Borrar una versión referenciada por un documento devuelve **409** con el númer | T-012-015 |
| AC-012-09 | Archivar una versión **conserva** sus ítems | T-012-019 |
| AC-012-10 | Un precio se declara sobre una presentación; sin ella, no se acepta | T-012-013 |
| AC-012-11 | Con lista específica del cliente y lista general vigentes, gana la del cliente | T-012-020, T-012-070, T-012-095 |
| AC-012-12 | Reordenando la precedencia y repitiendo la consulta, **cambia el resultado** — | T-012-022 |
| AC-012-13 | La respuesta incluye siempre `price_source_version_id` | T-012-025, T-012-095 |
| AC-012-14 | Dos reglas de igual precedencia y distinta vigencia: gana la más reciente | T-012-023 |
| AC-012-15 | Dos reglas de igual precedencia y misma vigencia: gana el menor precio | T-012-023 |
| AC-012-16 | Empate irresoluble → **422 `PRICE_PRECEDENCE_TIE`** con los candidatos | T-012-024 |
| AC-012-17 | Sin lista aplicable → `resolved:false`, `unit_price:null`. **Nunca** cero | T-012-026, T-012-071 |
| AC-012-18 | El precio se resuelve en la presentación pedida, convirtiendo con el motor de  | T-012-027 |
| AC-012-19 | Un rango de volumen aplica solo dentro de su rango | T-012-028 |
| AC-012-20 | La resolución de una empresa **nunca** ve listas de otra | T-012-029, T-012-073 |
| AC-012-21 | Descuento bajo el límite: `allowed:true`, sin aprobación | T-012-075 |
| AC-012-22 | Descuento sobre el límite: `allowed:false`, `requires_approval:true`, **sin bl | T-012-033, T-012-097 |
| AC-012-23 | 012 **no** crea la solicitud: la abre el consumidor con el motor 045 | T-012-033 |
| AC-012-24 | Descuento de línea y de documento se evalúan con políticas distintas | T-012-034 |
| AC-012-25 | Políticas incompatibles declaradas no se acumulan | T-012-034 |
| AC-012-26 | Aprobado un documento, **editar la lista no cambia** su precio | T-012-052, T-012-072, T-012-096 |
| AC-012-27 | Aprobado un documento, **crear una versión nueva no cambia** su precio | T-012-052 |
| AC-012-28 | El documento aprobado conserva la versión que produjo el precio y permite expl | T-012-053 |
| AC-012-29 | `pricing_source` distingue `RESOLVED`, `MANUAL_JUSTIFIED` y `LEGACY_FREETEXT` | T-012-054 |
| AC-012-30 | Un precio manual exige justificación; no se acepta en silencio | T-012-055 |
| AC-012-31 | `CommercialZone` y `WarehouseZone` son tablas distintas, **sin FK entre ellas* | T-012-004 |
| AC-012-32 | No existe un catálogo de monedas propio: se referencia `currencies` | T-012-010 |
| AC-012-33 | Condición de pago y método de pago siguen siendo cosas distintas | T-012-043 |
| AC-012-34 | 012 no crea permisos, auditoría ni aprobaciones propias | T-012-066 |
| AC-012-35 | 012 no emite eventos | T-012-067 |
| AC-012-36 | La migración de anotación crea **0** maestros y modifica **0** columnas hereda | T-012-090 |
| AC-012-37 | Una cadena ambigua queda `MANUAL_REVIEW_REQUIRED`, no convertida | T-012-092 |
| AC-012-38 | El texto original se conserva íntegro en `legacy_value` | T-012-044 |
| AC-012-39 | Los documentos históricos quedan `LEGACY_FREETEXT`, **sin snapshot inventado** | T-012-093 |
| AC-012-40 | La migración informa el recuento por clase y es reversible sin pérdida | T-012-090 |
| AC-012-41 | Toda la aceptación se ejecuta sobre **PostgreSQL 18.x** | T-012-078 |
| AC-012-42 | Ningún importe usa `float` | T-012-076 |
| AC-012-43 | Sin violaciones serias de WCAG 2.2 AA en las cinco pantallas | T-012-099 |
| AC-012-44 | Sin desbordamiento horizontal entre 320 y 1440 | T-012-099 |
| AC-012-45 | Cross-browser en Chromium, Firefox y WebKit | T-012-098 |

## 5. Autoridad → requisito

| Autoridad | Requisitos |
|---|---|
| `ADR-D0-005` R-D0-05-1 · precedencia como dato | FR-012-010, FR-012-011 |
| `ADR-D0-005` R-D0-05-2 · desempate determinista | FR-012-012, FR-012-013 |
| `ADR-D0-005` R-D0-05-3 · `PaymentTerm` maestro | FR-012-030, FR-012-031, FR-012-032 |
| `ADR-D0-005` R-D0-05-4 · condición ≠ crédito | FR-012-052 |
| `ADR-D0-005` R-D0-05-5 · snapshot con su versión | FR-012-060 |
| `ADR-D0-005` R-D0-05-6 · el maestro no reescribe historia | FR-012-061, FR-012-062 |
| `ADR-D0-005` §Comisiones · FUTURE CAPABILITY | FR-012-090, FR-012-091 |
| Constitución P8 · nada hardcodeado | FR-012-022, FR-012-032, NFR-012-05 |
| Constitución P5 · histórico protegido | FR-012-006, FR-012-061 |
| Constitución P6 · el backend es autoridad | FR-012-021 |
| Constitución P13 · integridad transaccional | FR-012-060 |
| Constitución P17/P22 · autoridad única | FR-012-014 |
| Constitución P21 · paridad del motor | NFR-012-02 |
| Constitución P23 · captura temprana | FR-012-060, FR-012-063 |
| Spec 011 · unidad y presentación | FR-012-004 |
| Spec 045 · motor de aprobaciones | FR-012-023 |
| Spec 008 · zona física ≠ zona comercial | FR-012-040, FR-012-041 |

## 6. Cadena prevista: requisito → diseño → tarea → prueba

| Bloque | Diseño | Tareas | Prueba prevista |
|---|---|---|---|
| Maestros base | `data-model.md` §1-3 | T-012-001..006 | Unidad + catálogo vacío |
| Listas y versiones | `data-model.md` §4-6 | T-012-010..019 | Integración sobre PostgreSQL |
| Resolución | `plan.md` §1 F3 | T-012-020..029 | Suite de precedencia |
| Descuentos | `data-model.md` §8 | T-012-030..035 | Límite y aprobación vía 045 |
| Cliente y crédito | `data-model.md` §9-10 | T-012-040..044 | Extensión sin duplicar |
| Snapshot | `data-model.md` §11 | T-012-050..056 | Inmutabilidad ante cambio |
| API | `contracts/api-contracts.md` | T-012-060..067 | Contrato OpenAPI |
| Frontend | `wireframes/` | T-012-080..088 | E2E, axe, responsive |
| Legado | `legacy-commercial-data-migration-matrix.md` | T-012-090..094 | Fixture de seis clases |
| Consumidoras | `commercial-master-impact-matrix.md` | T-012-100 | Verificación por contrato |
