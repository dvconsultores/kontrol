# TAREAS — SPEC 012

Tareas concretas y trazables. No existe una tarea «implementar maestros
comerciales».

## F1 · Maestros base

| ID | Tarea | Req. | Est. |
|---|---|---|---|
| T-012-001 | `PaymentTerm` con los cuatro tipos y el desplazamiento de vencimiento | FR-012-030, FR-012-031 | L |
| T-012-002 | El catálogo de condiciones **nace vacío** | FR-012-032, AC-012-01 | S |
| T-012-003 | `CommercialZone` con jerarquía y vendedor | FR-012-040, FR-012-043 | M |
| T-012-004 | Separación verificable de `WarehouseZone` | FR-012-041, AC-012-31 | S |
| T-012-005 | `SalesChannel` | FR-012-042 | S |
| T-012-006 | Migración `00XX_commercial_model` | FR-012-001..042 | L |

## F2 · Listas de precios

| ID | Tarea | Req. | Est. |
|---|---|---|---|
| T-012-010 | `PriceList` con moneda referenciada al maestro existente | FR-012-001, AC-012-32 | M |
| T-012-011 | `PriceListVersion` con vigencia y estados | FR-012-002, FR-012-007 | L |
| T-012-018 | Una versión `ACTIVE` no se edita: hay que crear otra | FR-012-002, AC-012-07 | M |
| T-012-019 | Archivar conserva los ítems de la versión | FR-012-006, AC-012-09 | S |
| T-012-012 | Restricción **en base** de no solapamiento | FR-012-005, AC-012-06 | L |
| T-012-013 | `PriceListItem` por producto o categoría, con presentación y volumen | FR-012-003, FR-012-004, AC-012-10 | L |
| T-012-014 | Correlativo de versión asignado por el servidor | AC-012-05 | M |
| T-012-015 | Versión referenciada: ni se borra ni se altera | FR-012-006, AC-012-08 | M |
| T-012-016 | Campo de fuente de la lista | FR-012-008 | S |
| T-012-017 | Índices de resolución | NFR-012-01 | M |

## F3 · Resolución — autoridad única, antes que la API

| ID | Tarea | Req. | Est. |
|---|---|---|---|
| T-012-020 | `pricing.py` como **única** autoridad de precio | FR-012-014, AC-012-11 | XL |
| T-012-021 | `PricePrecedence` como tabla por empresa | FR-012-010, AC-012-03 | L |
| T-012-022 | Siembra del orden por defecto del ADR, **editable** | FR-012-011, AC-012-12 | M |
| T-012-023 | Desempate por vigencia y por menor precio | FR-012-012, AC-012-14, AC-012-15 | M |
| T-012-024 | Empate irresoluble → error de configuración | FR-012-013, AC-012-16 | M |
| T-012-025 | La respuesta incluye la versión que produjo el precio | FR-012-015, AC-012-13 | M |
| T-012-026 | Sin lista aplicable: se declara ausente, **no se inventa** | FR-012-016, AC-012-17 | M |
| T-012-027 | Conversión de presentación con el motor de la Spec 011 | FR-012-004, AC-012-18 | L |
| T-012-028 | Rango de volumen | AC-012-19 | M |
| T-012-029 | Aislamiento multiempresa en la resolución | AC-012-20 | M |

## F4 · Descuentos

| ID | Tarea | Req. | Est. |
|---|---|---|---|
| T-012-030 | `DiscountPolicy` de línea y de documento | FR-012-020, FR-012-021 | L |
| T-012-031 | **Ningún porcentaje de fábrica** | FR-012-022, AC-012-04 | S |
| T-012-032 | Validación en backend; la UI no decide | FR-012-021, P6 | M |
| T-012-033 | Superar el límite abre solicitud con el motor 045 | FR-012-023, AC-012-22, AC-012-23 | L |
| T-012-034 | Acumulación e incompatibilidades | FR-012-024, AC-012-24, AC-012-25 | M |
| T-012-035 | Registro de política, versión y nivel de autorización | FR-012-025 | M |

## F5 · Cliente y crédito

| ID | Tarea | Req. | Est. |
|---|---|---|---|
| T-012-040 | `CustomerCommercialTerms` que **extiende**, no duplica | FR-012-050, FR-012-051 | L |
| T-012-041 | `CreditPolicy` distinta de la condición de pago | FR-012-052, FR-012-072 | M |
| T-012-042 | Bloqueo con motivo, autor y fecha | FR-012-053 | S |
| T-012-043 | Condición de pago del proveedor sin duplicar el maestro | FR-012-033, AC-012-33 | M |
| T-012-044 | Migración `00XX_commercial_customer_fk`, conservando el texto | FR-012-080, AC-012-38 | L |

## F6 · Snapshot — antes que la API

| ID | Tarea | Req. | Est. |
|---|---|---|---|
| T-012-050 | Columnas de snapshot en las líneas de venta y compra | FR-012-060 | L |
| T-012-051 | Escritura del snapshot en la **misma transacción** que aprueba | FR-012-060, P13 | L |
| T-012-052 | Editar el maestro no altera lo aprobado | FR-012-061, AC-012-26, AC-012-27 | L |
| T-012-053 | Reconstrucción **desde el snapshot**, nunca recalculando | FR-012-062, AC-012-28 | M |
| T-012-054 | `pricing_source` con sus tres valores | FR-012-063, AC-012-29 | M |
| T-012-055 | Precio manual con justificación obligatoria | AC-012-30 | M |
| T-012-056 | Migración `00XX_commercial_snapshot_columns` | FR-012-060 | M |

## F7 · API

| ID | Tarea | Req. | Est. |
|---|---|---|---|
| T-012-060 | Endpoints de los maestros base | FR-012-030..042 | L |
| T-012-061 | Endpoints de lista, versión e ítems | FR-012-001..008 | L |
| T-012-062 | `POST /precio/resolver` | FR-012-070 | L |
| T-012-063 | `POST /descuento/validar` | FR-012-071 | M |
| T-012-064 | Los 7 códigos de error del contrato | contratos §5 | M |
| T-012-065 | `allowed_actions` calculado en backend | P6 | M |
| T-012-066 | Permisos `comercial:*` con la convención de la Spec 003 | AC-012-34 | S |
| T-012-067 | **012 no emite eventos** | FR-012-073, AC-012-35 | XS |

## F8 · Pruebas de backend

| ID | Tarea | Req. | Est. |
|---|---|---|---|
| T-012-070 | Unidad: precedencia, desempate, empate irresoluble | AC-012-11..16 | XL |
| T-012-071 | Unidad: sin lista, volumen, presentación | AC-012-17..19 | L |
| T-012-072 | Integración: snapshot inmutable ante cambio del maestro | AC-012-26..28 | L |
| T-012-073 | Multiempresa en la resolución | AC-012-20 | M |
| T-012-074 | Concurrencia: dos versiones activándose a la vez | R-012-12 | L |
| T-012-075 | Descuento: límite, aprobación, acumulación | AC-012-21..25 | L |
| T-012-076 | `0 float` y `0 valores codificados`, por comando | AC-012-02, AC-012-42, NFR-012-05, NFR-012-06 | S |
| T-012-077 | Regresión de `sales`, `purchasing`, `master_data` | plan §3 | L |
| T-012-078 | Toda la aceptación sobre **PostgreSQL 18.x** | NFR-012-02, AC-012-41 | M |

## F9 · Frontend

| ID | Tarea | Req. | Est. |
|---|---|---|---|
| T-012-080 | Tipos TypeScript del modelo comercial | — | S |
| T-012-081 | Pantalla de listas con filtros | wireframes §1 | L |
| T-012-082 | Detalle con historial de versiones sin edición | wireframes §2 | L |
| T-012-083 | Condiciones de pago con formulario que cambia con el tipo | wireframes §3 | L |
| T-012-084 | Zonas y canales | wireframes §4 | M |
| T-012-085 | Políticas de descuento y crédito | wireframes §5 | L |
| T-012-086 | Estados vacíos honestos | AC-012-01 | S |
| T-012-087 | Rutas y entrada de menú | NFR-012-03 | S |
| T-012-088 | Pantallas completas, sin modales para formularios complejos | NFR-012-04 | M |

## F10 · Legado, E2E y cierre

| ID | Tarea | Req. | Est. |
|---|---|---|---|
| T-012-090 | Migración de anotación con sus invariantes y aborto | FR-012-083, AC-012-36, AC-012-40 | L |
| T-012-091 | Clasificación de las 7 columnas | matriz legado §2 | M |
| T-012-092 | Ambiguo → revisión manual, nunca conversión | FR-012-081, AC-012-37 | M |
| T-012-093 | `LEGACY_FREETEXT` en documentos históricos | FR-012-082, AC-012-39 | M |
| T-012-094 | Fixture legado con las seis clases | matriz legado §3 | L |
| T-012-095 | E2E: crear lista, resolver precio, ver origen | AC-012-11, AC-012-13 | XL |
| T-012-096 | E2E: cambiar el maestro no altera lo aprobado | AC-012-26 | L |
| T-012-097 | E2E: descuento excesivo abre aprobación | AC-012-22 | L |
| T-012-098 | Cross-browser | AC-012-45 | M |
| T-012-099 | axe WCAG 2.2 AA y responsive en 6 viewports | AC-012-43, AC-012-44, NFR-012-03 | M |
| T-012-100 | Verificación de las 8 Specs consumidoras | matriz de impacto | M |
| T-012-101 | `/speckit.converge 012` y cierre | — | M |
| T-012-102 | `SalesCommissionPolicy` **reservada** en el modelo, sin implementar y sin cálculo | FR-012-090, FR-012-091 | S |

## Resumen

| Fase | Tareas | Carga | Nota |
|---|---:|---|---|
| F1 Maestros base | 6 | L | Independientes |
| F2 Listas | 10 | XL | La vigencia es el núcleo |
| F3 Resolución | 10 | **XL** | Donde vive el valor; **antes que la API** |
| F4 Descuentos | 6 | L | Consume el motor 045 |
| F5 Cliente y crédito | 5 | L | Extiende, no duplica |
| F6 Snapshot | 7 | **XL** | **Antes que la API** por `P23` |
| F7 API | 8 | L | — |
| F8 Pruebas | 9 | XL | La precedencia es una suite |
| F9 Frontend | 9 | L | Cinco pantallas |
| F10 Legado y cierre | 13 | XL | El legado se anota, no se inventa |
| **Total** | **83** | — | — |

---

# TAREAS — ACTUALIZACIÓN DOCUMENTAL POSTERIOR A ARCH-MC-001

Todas documentales. Ninguna toca `resources/`.

| Id | Tarea | Estado |
|---|---|---|
| T-012-RV-001 | Inventariar los modelos comerciales vigentes | Hecha — ninguno existe |
| T-012-RV-002 | Verificar el alcance de Tercero | Hecha — COMPANY |
| T-012-RV-003 | Verificar el alcance de Producto | Hecha — COMPANY |
| T-012-RV-004 | Verificar Moneda y Tasa de cambio | Hecha — COMPANY las dos |
| T-012-RV-005 | Clasificar las entidades de 012 | Hecha — 11, 0 indeterminadas |
| T-012-RV-006 | Definir las rutas de autoridad | Hecha — 3 derivadas |
| T-012-RV-007 | Actualizar el alcance en `data-model.md` | Hecha — §14 |
| T-012-RV-008 | Definir la unicidad por empresa | Hecha |
| T-012-RV-009 | Definir `PriceList` | Hecha |
| T-012-RV-010 | Definir `PriceListVersion` | Hecha |
| T-012-RV-011 | Definir el alcance derivado de `PriceListItem` | Hecha |
| T-012-RV-012 | Definir `DiscountPolicy` | Hecha |
| T-012-RV-013 | Definir las condiciones comerciales | Hecha |
| T-012-RV-014 | Resolver el propietario de `PaymentTerm` | Hecha — la 012 |
| T-012-RV-015 | Resolver el propietario de comisiones | Hecha — la 012, reservado |
| T-012-RV-016 | Reconciliar unidades | Hecha — con unidad de plataforma |
| T-012-RV-017 | Reconciliar presentación | Hecha |
| T-012-RV-018 | Definir el versionado | Hecha — `price-list-versioning-contract.md` |
| T-012-RV-019 | Definir el congelado histórico | Hecha |
| T-012-RV-020 | Definir la seguridad de rutas hijas | Hecha — `nested-resource-security-contract.md` |
| T-012-RV-021 | Definir el ataque por identificador de padre | Hecha — N-01 a N-09 |
| T-012-RV-022 | Definir los contratos de `CompanyContext` | Hecha — §0 de los contratos |
| T-012-RV-023 | Definir permisos | Hecha — seis |
| T-012-RV-024 | Definir la integración de aprobación | Hecha — Spec 045 |
| T-012-RV-025 | Definir auditoría | Hecha |
| T-012-RV-026 | Definir contratos OpenAPI | Hecha |
| T-012-RV-027 | Definir el contrato de empresa del frontend | Hecha |
| T-012-RV-028 | Definir el plan de migraciones futuro | Hecha — ola 16 |
| T-012-RV-029 | Definir pruebas de integridad en PostgreSQL | Hecha — B-01 a B-10 |
| T-012-RV-030 | Definir la matriz A/B/C | Hecha — C-01 a C-04 |
| T-012-RV-031 | Reconciliar requisitos | Hecha — 50 nuevos |
| T-012-RV-032 | Reconciliar criterios de aceptación | Hecha |
| T-012-RV-033 | Reconciliar checklist | Hecha |
| T-012-RV-034 | Reconciliar trazabilidad | Hecha |
| T-012-RV-035 | Aplicar el delta documental | Hecha |
| T-012-RV-036 | Convergencia documental | Hecha |
| T-012-RV-037 | Veredicto de disponibilidad | Hecha |

## Tareas retiradas

Ninguna de las tareas anteriores estaba diseñada sobre arquitectura superada:
la Spec 012 nunca llegó a implementarse, así que sus tareas describen trabajo
futuro y siguen siendo válidas. Lo que cambió es el **contrato** que ese trabajo
debe cumplir, y eso vive en los requisitos, no en las tareas.

---

# TAREAS — IMPLEMENTACIÓN

| Id | Tarea | Estado |
|---|---|---|
| T-012-I-001 | Precheck y baseline | Hecha — 166 modelos, 39 migraciones, árbol limpio |
| T-012-I-002 | Enumerar las 11 entidades | Hecha — documental = modelo |
| T-012-I-003..008 | Esquema, FK, unicidad, índices | Hecha — `0040`, `0041` |
| T-012-I-009 | Declaración de alcance en el ORM | Hecha — 8 + 3 |
| T-012-I-010..012 | Listas, versiones e ítems | Hecha |
| T-012-I-013..015 | Descuentos, crédito, condiciones, precedencia | Hecha |
| T-012-I-016..018 | Producto, Tercero, taxonomía | Hecha |
| T-012-I-019..020 | Unidad y presentación | Hecha — con unidad de plataforma |
| T-012-I-021..022 | Moneda y tasa | Hecha — se referencian, no se duplican |
| T-012-I-023..024 | Resolutores de precio y descuento | Hecha |
| T-012-I-025 | Precedencia configurable | Hecha |
| T-012-I-026 | Integración de aprobación | Hecha — señal a la 045, sin motor propio |
| T-012-I-027..028 | Permisos y auditoría | Hecha |
| T-012-I-029..030 | API y OpenAPI | Hecha — 22/22 con cabecera |
| T-012-I-031..035 | Frontend, aislamiento y formulario | Hecha |
| T-012-I-036..039 | Seguridad de rutas hijas y SQL hostil | Hecha |
| T-012-I-040..041 | Catálogo e instalación limpia | Hecha |
| T-012-I-042..048 | Regresiones | Hecha |
| T-012-I-049 | Actualizar artefactos | Hecha |
| T-012-I-050 | `/speckit.converge SPEC012` | Hecha |
