# `/speckit.analyze` — SPEC 011 · UNIDADES, PRESENTACIONES Y CONVERSIONES

Fecha: **2026-08-30** · Rama `develop` · Análisis documental.
**No se escribió código productivo. No se creó ninguna migración. No se ejecutó
`/speckit.implement`.** La cadena Alembic sigue en `0018`.

---

## 1. Cadena comparada

`Constitución v1.1` → `ADR vigentes` → `baseline` → `D0` → `G0` → `spec.md` →
`clarifications.md` → `research.md` → `plan.md` → `data-model.md` → `contracts/`
→ `wireframes/` → `checklist.md` → `tasks.md` → `acceptance-criteria.md` →
`test-plan.md` → `risk-register.md` → `traceability-matrix.md` →
`transaction-uom-impact-matrix.md` → `legacy-uom-migration-matrix.md`.

## 2. Artefactos — 16/16

Los 15 exigidos por §113, más este informe. Todos completos.

## 3. Coherencia — verificada por comando

| Comprobación | Resultado |
|---|---|
| Requisitos funcionales sin tarea | **0** de 75 |
| Requisitos no funcionales sin tarea | **0** de 8 |
| Criterios de aceptación sin tarea | **0** de 40 |
| Tareas sin requisito ni criterio | **0** de 99 |
| Códigos de error: contrato ↔ criterios | **15 ↔ 15**, coincidentes |
| Documentos normativos citados que no existen | **0** |
| Colisión entre identificadores de regla y de riesgo | **0** — reglas `R-011-n`, riesgos `RSK-011-nn` |

La matriz se **genera por script** desde los artefactos: ninguna columna se
escribe a mano, de modo que no puede envejecer sin que se note.

## 4. Estado actual encontrado — el hallazgo que define la Spec

Auditoría del código real, no de los nombres:

| Métrica | Valor |
|---|---:|
| Tablas con columna de cantidad | **23** |
| Líneas de documento transaccional | **21** |
| Que conservan `uom_id` | **2**, ambas *nullable* |
| Que conservan `presentation_id` | **0** |
| Que conservan factor de conversión | **0** |
| Que conservan cantidad base | **0** |
| Columnas de cantidad o factor en `Float` | **31** |
| Columnas de cantidad o factor en `Numeric` | **0** |
| Lógica de conversión en la aplicación | **Ninguna** |

Y, verificado línea a línea:

- `inventory/service.py:382` escribe `unit_id=None` **de forma literal**.
- `unit_conversions` tiene un `POST` que la escribe y **nada** que la lea.
- `presentations` **no tiene un solo endpoint**: no hay forma de crear una.
- `catalog_items.base_unit_id` es *nullable* y no participa en ningún cálculo.
- `sales_invoice_lines.base_fiscal` es base imponible en **moneda**, no cantidad
  base. No existe una sola cantidad base en el esquema.

Es el **patrón Sucursales** en su forma más cara: tres maestros construidos,
cero transacciones que los usen.

## 5. Contradicciones detectadas y resueltas

### C-01 · Identificador de regla sin enunciado — **RESUELTA**

`R-011-3` se citaba en `data-model.md`, `risk-register.md` y `spec.md` sin estar
definida en ninguna parte, y la numeración saltaba de 3 a 9 sin razón. Se
definieron formalmente `R-011-3` (unidad base inmutable con historial) y
`R-011-4` (factor 1 como conclusión), y se renumeró la antigua `R-011-9`. Las
cuatro reglas tienen ahora enunciado en `spec.md` §6.

### C-02 · Tensión aparente entre `ADR-D0-009` y el encargo — **RESUELTA, sin enmienda**

El ADR autoriza rellenar el histórico con «unidad base y factor 1, marcadas
`LEGACY_ASSUMED_BASE`». El encargo prohíbe suponer factor 1 indiscriminadamente.

No hay contradicción: el propio ADR escribe **«es una suposición, y queda
registrada como tal»**. Esta Spec lo hace verificable, aplicando la disciplina de
clases que no existía cuando el ADR se aprobó:

| El ADR dice | 011 lo refina en |
|---|---|
| Rellenar con la unidad base del producto | Solo si el producto **tiene** unidad base → clase A |
| Marcar `LEGACY_ASSUMED_BASE` | Se conserva, más `LEGACY_RECONSTRUCTED`, `LEGACY_UNRESOLVED`, `LEGACY_UNVERSIONED` |
| «Si alguna línea se registró en otra presentación, es irrecuperable» | **Se demuestra que no pudo ocurrir** |

Ninguna de las cinco reglas del ADR cambia. **No procede enmienda.**

### C-03 · Riesgo de sobreingeniería — **RESUELTA**

Alias de unidad, peso variable y presentaciones genéricas reutilizables se
evaluaron y se descartaron del MVP como `FUTURE_CAPABILITY`, comprobando que el
modelo no los bloquea. Una presentación genérica sin factor no aporta nada: el
factor pertenece al par producto-presentación.

**Contradicciones sin resolver: 0.**

## 6. Hallazgo probatorio sobre la migración

La pregunta que gobierna todo el backfill es si alguna línea histórica pudo
registrarse en una presentación distinta de la base. La respuesta se **demuestra**,
no se supone:

| Comprobación | Resultado |
|---|---|
| ¿Endpoint que cree presentaciones? | **No existe** |
| ¿Migración o seed que las inserte? | **Ninguna**: `0002` solo crea la tabla |
| ¿Alguna línea con `presentation_id`? | **0 de 21** |

No existiendo camino alguno por el que una presentación pudiera crearse ni
referenciarse, **ninguna línea pudo expresarse en una presentación**. Esto no
convierte el factor 1 en un valor seguro por defecto —sigue sin decirnos *qué
unidad* era— pero acota drásticamente el riesgo y hace que la clase A sea una
conclusión y no una comodidad.

## 7. Conformidad constitucional

| Principio | Veredicto | Evidencia |
|---|---|---|
| P2 autorización expresa | ✅ | Ciclo documental; se detiene antes de implementar |
| P3 trazabilidad | ✅ | 0 huérfanos en las cuatro direcciones |
| P4 núcleo fiscal separado | ✅ | No se toca el motor fiscal; la factura conserva su snapshot |
| **P5 dato histórico protegido** | ✅ **eje** | `base_quantity` congelada; clase D no se toca; `quantity` original intacta |
| **P6 backend es la autoridad** | ✅ | `base_quantity` siempre recalculada; la vista previa no vincula |
| P8 sin negocio en código | ✅ | Catálogo de unidades **vacío**; ninguna unidad codificada |
| P11 accesibilidad y responsive | ✅ | NFR-011-04/05 |
| P13 integridad transaccional | ✅ | `NUMERIC`, `factor > 0`, sin solapamiento |
| P18 sin modales complejos | ✅ | Presentaciones en página completa |
| **P21 paridad del motor** | ✅ | PostgreSQL 18.x en toda la evidencia |
| **P22 autoridad única** | ✅ **eje** | Un solo motor de conversión; AC-011-34 lo verifica |
| **P23 captura temprana** | ✅ **eje** | F4 antes que F6; la unidad no se recupera después |

**0 violaciones. 0 enmiendas requeridas.**

## 8. Scope creep

| Comprobación | Resultado |
|---|---|
| Tareas de put-away, picking, recepción, facturación o precios | **0** |
| Migraciones creadas en esta fase | **0** — la cadena sigue en `0018` |
| Código productivo modificado | **0** |
| Specs ajenas implementadas | **0** |

011 **modifica columnas estructurales compartidas** de tres dominios —es
inevitable para preservar la unidad— pero **no implementa sus procesos**.

## 9. Ambigüedades y escalados

**Bloqueantes: 0.** Ocho de las nueve preguntas clave del §97 se resolvieron con
autoridad existente. Se escala **una**, sin bloquear:

- **ESC-011-01** — umbral a partir del cual el backfill fiscal debe abortar. Es
  decisión de producto y de riesgo fiscal, no técnica. Se implementa configurable
  con valor por defecto **1**, la opción más conservadora, y se ajusta sin cambio
  de esquema.

## 10. Duplicidad de autoridad

**0.** La conversión tendrá un solo motor (P22). No se crea sistema propio de
permisos, auditoría ni aprobaciones. `barcodes` no se toca.

## 11. Riesgos

17 riesgos, todos con mitigación. Tres **críticos**: pérdida de significado
histórico por tardar, backfill que inventa historia, y alteración de un documento
fiscal emitido.

El dominante, **RSK-011-01**, es de naturaleza distinta a los demás: no es un
riesgo de la implementación sino el riesgo de **tardar**. Cada día sin capturar
la unidad añade líneas que ninguna migración futura podrá reparar, porque el dato
no se perdió: nunca se capturó.

## 12. Veredicto

| Criterio (§109) | Resultado |
|---|---|
| Modelo de UOM cerrado | ✅ |
| Unidad base cerrada | ✅ obligatoria en productos, bloqueada con historial |
| Presentaciones cerradas | ✅ factor en el par producto-presentación |
| Conversiones cerradas | ✅ física y comercial separadas |
| Versionado cerrado | ✅ por vigencia, sin solapamiento |
| Snapshot cerrado | ✅ se fija al emitir |
| Redondeo cerrado | ✅ un solo lugar |
| Modelo decimal cerrado | ✅ `NUMERIC(18,6)`; 0 `Float` |
| Mutación de unidad base resuelta | ✅ R-011-3 |
| Impacto transaccional completo | ✅ 21 líneas clasificadas, 17 `MUST_HAVE_NOW` |
| Migración legada diseñada | ✅ cuatro clases, con bloqueo fiscal |
| No se inventan datos | ✅ clase C queda nula y marcada |
| PostgreSQL planificado | ✅ 18.x |
| API definida | ✅ 15 códigos de error |
| UI definida | ✅ 7 wireframes |
| Permisos y auditoría definidos | ✅ sin sistemas paralelos |
| Tests definidos | ✅ 12 secciones |
| Contradicciones | ✅ **0** |
| Requisitos huérfanos | ✅ **0** |
| Tareas huérfanas | ✅ **0** |

**APTA PARA IMPLEMENTACIÓN.**

Condiciones cuando se autorice: orden **F1→F2→F3→F4→F5→F6→F7→F8→F9**, con **F4
antes que F6** por P23; migraciones separadas (esquema, tipo, columnas, datos);
las columnas nacen *nullable* y solo pasan a `NOT NULL` cuando el reporte de
backfill demuestre 0 líneas sin resolver.
