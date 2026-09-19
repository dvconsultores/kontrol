# SPEC 007 · Delta dirigida — SEED-EMPRESA-CODIGO-NO-UNICO · **SE DETIENE EN CLARIFY**

**Fecha** 2026-09-19 · **Dueña** SPEC007 — Organización (`specs/001-fundacion`) ·
**Apoyo** SPEC052 (migración, si algún día procede) y SPEC054 (donde se encontró) ·
**Base** `2d3da4d` · **Rama** `develop`

## 1. Checkpoint

| Comprobación | Valor |
|---|---|
| `EXPECTED_HEAD` | `2d3da4d` |
| `ACTUAL_HEAD` | `2d3da4d` — **coincide** |
| `ACTUAL_BRANCH` | `develop` |
| `COMMITS_AFTER_2D3DA4D` | **0** |
| Árbol | limpio salvo los dos artefactos de auditoría sin seguimiento, **preservados** |

## 2. Veredicto, por delante

**`SEED-EMPRESA-CODIGO-NO-UNICO` — BLOCKED BY NEW MATERIAL DECISION.**

No se crea la restricción. No se escribe migración. No se toca el modelo. El motivo no es
que falte trabajo: es que **falta una decisión que no me corresponde tomar**, y el propio
encargo lo prohíbe expresamente —«NO inventar `UNIQUE(tenant_id, code)` solo porque parece
razonable»—.

Lo que sí queda hecho es todo lo que permite decidir en una lectura.

## 3. El registro de la deuda estaba escrito sobre una suposición mía

La deuda dice: «`companies` no tiene índice único sobre `(tenant_id, code)` … **la identidad
de empresa descansa en la disciplina de cada guion, no en el motor**». La escribí yo durante
`N6-MULTICOMPANY-STARTUP`, y da por hecho que esa identidad existe.

Medido: **no existe**. En ningún sitio.

## 4. La identidad de `Company`, buscada donde tenía que estar

| Dónde se buscó | Qué dice |
|---|---|
| `specs/001-fundacion/data-model.md:31` | Enumera los campos de `Company` — «id, tenant_id, code, legal_name, trade_name, rif, …» — y **no declara unicidad de ninguno** |
| `specs/001-fundacion/spec.md` | Ningún `FR-001-*` menciona unicidad del código de empresa |
| `specs/001-fundacion/contracts/api-contracts.md:50` | «`GET/POST /api/v1/organization/companies` · Listar/crear empresa». Sin contrato de duplicado |
| Unicidad de RIF en las specs | Existe, pero es de **terceros**: `Unique (company_id, tax_id, role)` en la Spec 002. No es de empresas |
| Pruebas del repositorio | **Ninguna** afirma unicidad del código de empresa |

## 5. Y buscada también en lo que el producto hace

| Comprobación | Resultado medido |
|---|---|
| Restricción en PostgreSQL | **No existe**: `companies` solo tiene `pk_companies`, `ix_companies_rif`, `ix_companies_tenant_id` y la clave foránea al tenant |
| Restricción en el ORM | **No existe**: `Company` no declara `__table_args__` |
| ¿Existió antes y se perdió? | **No**: `0001_fundacion.py:70-71` creó esos dos índices y nunca una unicidad |
| ¿El producto resuelve empresas por código? | **Nunca**: cero apariciones de `Company.code ==` en todo `app/`. La empresa viaja por `id` en `X-Kontrol-Company`, y unas cien tablas la referencian por `id` |
| `tenant_id` | `NOT NULL` — no hay empresas sin tenant, así que el problema de los nulos de PostgreSQL **no aplica aquí** |
| `create_company` | `app/modules/organization/api.py:95-116`: **no comprueba duplicados**. No hay ni siquiera el `consultar → insertar` que tenían los tipos de movimiento |

### La conducta real, medida contra el servidor

Cuatro altas seguidas en el mismo tenant, con datos de sonda que después se retiraron:

```
alta con código SONDA        -> 200
alta con el MISMO código     -> 200      ← dos empresas con el mismo código
alta con 'sonda'             -> 200      ← se guarda tal cual, sin normalizar
alta con ' SONDA '           -> 200      ← se guarda con los espacios
```

En la base quedaron cuatro filas con los códigos `SONDA`, `SONDA`, `sonda` y ` SONDA `.
**El producto trata el código de empresa como una etiqueta de texto libre**, no como un
identificador: no lo normaliza, no lo compara, no lo exige único y no lo usa para
encontrar nada.

### Hermanos del mismo módulo

| Entidad | ¿Unicidad de código? |
|---|---|
| `Tenant` | **No** |
| `Company` | **No** |
| `Branch` | **No** |
| `Warehouse` y por debajo (`zone_types`, `location_types`, zonas, pasillos, racks, niveles, ubicaciones) | **Sí**, `(padre, code)` |

El patrón existe, pero **empieza en el almacén**. Los tres niveles de arriba de la jerarquía
organizacional no lo tienen. Eso admite dos lecturas —omisión o decisión— y la evidencia
física no distingue entre ellas.

## 6. Auditoría de duplicados

| Base | Empresas | Grupos duplicados | Filas duplicadas |
|---|---|---|---|
| `keu` (la única existente en este entorno) | 3 | **0** | **0** |

`DUPLICATE_GROUPS = 0`. Conviene decir el alcance con honestidad: en este entorno no hay
bases de clientes, así que la auditoría cubre lo que hay. Una instalación real tendría que
repetirla antes de cualquier migración.

## 7. `/speckit.clarify` — la pregunta que detiene el ciclo

> **¿Es el código de empresa un identificador dentro de su tenant, o una etiqueta?**

No es una pregunta retórica, porque las dos respuestas tienen consecuencias reales:

**Si es identificador** —`(tenant_id, code)` único—, entonces hay trabajo: índice único,
migración, auditoría de duplicados en cada instalación, contrato de duplicado en la API
(que hoy no existe: `create_company` ni siquiera devuelve un conflicto), traducción de la
colisión, y decidir qué pasa con una empresa `INACTIVE` que ocupa un código. También
habría que decidir si `sonda` y `SONDA` son el mismo código, porque hoy no lo son.

**Si es etiqueta**, no hay defecto que corregir: el producto ya se comporta así, la deuda se
cierra como **no aplicable** y lo único que queda es dejar escrito que el código no
identifica, para que nadie vuelva a construir encima de esa suposición —como hice yo en
N6—.

Lo que **no** es defendible es crear la restricción por parecerse a los almacenes. Añadirla
cambiaría una conducta que hoy es legítima: quien tenga dos empresas con el mismo código
—hoy permitido— no podría seguir operando tras una actualización, y ninguna Spec le avisó
de que eso estuviera prohibido.

| Clasificación | Valor |
|---|---|
| `COMPANY_IDENTITY_CONTRACT_DEFECT` | **No se puede afirmar**: no hay contrato que incumplir |
| `DB_CONSTRAINT_DEFECT` | **Indeterminado**, depende de la respuesta |
| `COMPANY_DUPLICATE_DATA` | **0** |
| `MATERIAL_DECISION_REQUIRED` | **1** ← el bloqueo |
| `OWNER_IDENTITY_CONFLICT` · `UNKNOWN` | **0** · **0** |

## 8. Lo que se deja preparado para quien decida

Si la respuesta es «identificador», este análisis ya deja resuelto:

- **Dueña**: SPEC007, con SPEC052 para la migración y SPEC054 para las semillas.
- **Identidad candidata**: `(tenant_id, code)`, con `tenant_id NOT NULL` —así que basta una
  `UNIQUE` normal; no hacen falta índices parciales ni trucos con nulos—.
- **Nombre según convención del repositorio**: `uq_companies_tenant_code`.
- **Duplicados que bloquearían la migración**: 0 en este entorno; hay que repetir la
  auditoría por instalación.
- **Lo que además haría falta y hoy no existe**: un contrato de duplicado en
  `POST /organization/companies`, porque sin él la colisión saldría como 500 —el mismo
  defecto que se cerró en `INV-MOVTYPE-CARRERA`, y el patrón seguro ya está en el
  repositorio: savepoint, `es_violacion_unica` y conflicto de dominio—.
- **Decisiones adicionales que arrastra**: mayúsculas/minúsculas, espacios, y si una empresa
  inactiva sigue ocupando su código.

## 9. Lo que NO se ha hecho, a propósito

- No se ha creado ninguna restricción ni índice.
- No se ha escrito ninguna migración: **migraciones = 0**, cabeza sigue `0057_spec047_notifications`.
- No se ha tocado el modelo, la ruta, ni las semillas.
- No se ha borrado, fusionado ni renombrado ningún dato.
- No se ha absorbido `MOVTYPE-GLOBAL-SIN-UNICIDAD`, que es la misma pregunta en otra tabla.

Los datos de sonda creados para medir se retiraron y se verificó que la base del E2E quedó
como estaba: `D1`, `D2`, `E1`, cero duplicados. Las suites de empresa siguen verdes
(**29/29**: N6 multiempresa, N6 accesibilidad y el ayudante de empresa).

## 10. Estado

| Cosa | Estado |
|---|---|
| `SEED-EMPRESA-CODIGO-NO-UNICO` | **OPEN** → reclasificada `MATERIAL_DECISION_REQUIRED`, dueña **SPEC007** |
| Producto · esquema · migraciones | 0 · sin cambios · 0 |
| `MATERIAL OQ` | **1**, y es el bloqueo |
| `UNKNOWN` | **0** |

**VEREDICTO: CASO D — `SEED-EMPRESA-CODIGO-NO-UNICO` BLOCKED BY NEW MATERIAL DECISION.**
