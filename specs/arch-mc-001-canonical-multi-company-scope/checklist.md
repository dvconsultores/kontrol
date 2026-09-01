# CHECKLIST — ARCH-MC-001

## Antes de implementar

- [ ] Decisión de producto confirmada: **multiempresa por tenant**. No se re-pregunta.
- [ ] ADR de alcance canónico aprobado.
- [ ] Las 166 tablas clasificadas; **0 sin clasificar**.
- [ ] Las 36 derivadas verifican FK **obligatoria**.
- [ ] `OQ-MC-01` respondida antes de tocar los catálogos afectados.
- [ ] Transporte del contexto decidido y razonado (cabecera).
- [ ] PostgreSQL 18.6 y ClamAV reaprovisionados.

## Durante

- [ ] N1 antes que N2; N2 antes que N3.
- [ ] Ninguna hija se migra antes que su cabecera.
- [ ] Ninguna migración crea empresas por su cuenta.
- [ ] Ninguna columna heredada se borra antes de verificar.
- [ ] El informe previo se ejecuta sin escribir.
- [ ] Un crítico no reconstruible detiene la migración.
- [ ] Ningún escritor sigue poniendo `tenant_id` en `company_id`.

## Antes de declarar COMPLETE_100

- [ ] Los 66 criterios, con prueba que los ejecuta.
- [ ] Suite completa sobre **PostgreSQL 18.x**.
- [ ] Fixture de dos empresas en todos los dominios P0.
- [ ] Las 17 columnas `company_id` con FK pasan a ser **todas**.
- [ ] `grep` de `company_id = actor.tenant_id` devuelve **0**.
- [ ] Series fiscales, números de control y libros separados por empresa.
- [ ] Un pago de A no se aplica a una factura de B.
- [ ] Las existencias de A y B no se mezclan.
- [ ] Manipular el navegador no da acceso a otra empresa.
- [ ] Dos pestañas operan en empresas distintas sin contaminarse.
- [ ] Los 19 tipos de la Spec 046 probados; `STILL_BLOCKED_BY_046` = 0.
- [ ] `REM-046-001` cerrado y 046 convergida.
- [ ] 008, 011, 045 y 046 en regresión completa.
- [ ] Regresión global con **0 fallos**; ningún escenario multiempresa omitido.
- [ ] Ninguna columna de transición sobrevive.
- [ ] **Sin deuda interna diferida** (§227).

---

# N7 — LISTA DE COMPROBACIÓN

Medido contra el catálogo de PostgreSQL 18.6, no contra el ORM.

| # | Comprobación | Estado |
|---|---|---|
| 1 | Inventario de claves foráneas de empresa completo | ✅ 101 tablas |
| 2 | Inventario de claves foráneas de tenant completo | ✅ 14 tablas |
| 3 | Inventario de claves foráneas de sucursal completo | ✅ |
| 4 | Inventario de claves de padre completo | ✅ 242 claves |
| 5 | Restricciones de unicidad revisadas | ✅ 31, no 13 |
| 6 | Rutas derivadas revisadas | ✅ 35, no 36 |
| 7 | Rutas derivadas anulables = 0 | ✅ ya cumplido |
| 8 | Claves foráneas huérfanas = 0 | ⬜ tras migrar |
| 9 | Claves con destino equivocado = 0 | ⬜ tras migrar |
| 10 | Colisiones de unicidad = 0 | ⬜ tras probar |
| 11 | Incoherencia empresa/tenant = 0 | ⬜ |
| 12 | Incoherencia empresa/sucursal = 0 | ⬜ |
| 13 | Incoherencia empresa/almacén = 0 | ⬜ |
| 14 | Incoherencia empresa/cuenta bancaria = 0 | ⬜ |
| 15 | Restricciones fiscales definidas | ✅ en el plan |
| 16 | Restricciones financieras definidas | ✅ |
| 17 | Restricciones de inventario definidas | ✅ |
| 18 | Alcance de numeraciones definido | ✅ §17 de aclaraciones |
| 19 | Alcance de idempotencia definido | ✅ empresa |
| 20 | Orden de migraciones definido | ✅ 0033→0037 |
| 21 | Estrategia de instalación limpia definida | ✅ |
| 22 | Estrategia de SQL sin conexión definida | ✅ |
| 23 | Fixture hostil definido | ✅ debe fallar |
| 24 | Pruebas de corrupción por SQL directo definidas | ✅ 11 casos |
| 25 | Regresión de N5 definida | ✅ las once |
| 26 | Regresión de N6 definida | ✅ |
| 27 | Rojos esperados de N8 separados | ✅ |
| 28 | Requisitos N7 sin criterio de aceptación = 0 | ✅ 30 FR, 6 NFR, 10 AC |

---

# N8 — LISTA DE COMPROBACIÓN

| # | Comprobación | Estado |
|---|---|---|
| 1 | Inventario de `legacy_scope_id` | ✅ 80 tablas, solo en migraciones |
| 2 | Inventario de `scope_backfill_class` | ✅ ídem |
| 3 | Lecturas en runtime antes de borrar | ✅ **0** |
| 4 | Escrituras en runtime antes de borrar | ✅ **0** |
| 5 | Inventario de lectura doble | ✅ 0 |
| 6 | Inventario de escritura doble | ✅ 0 |
| 7 | Inventario de repliegue tenant→empresa | ✅ **1 encontrado** |
| 8 | Inventario de ayudantes de compatibilidad | ✅ el mismo |
| 9 | Inventario de cargas útiles heredadas | ✅ 0 |
| 10 | Contrato de la cabecera definido | ✅ opcional, con semántica |
| 11 | Omisión con una empresa | ✅ definida |
| 12 | Obligatoriedad con varias | ✅ definida |
| 13 | Empresa inválida o inactiva | ✅ definida |
| 14 | Compatibilidad del clasificador diseñada | ✅ desacoplar `planes()` |
| 15 | Fixture hostil preservado | ✅ como artefacto reproducible |
| 16 | `MC-A`…`MC-E` preservadas | ⬜ tras verificar |
| 17 | `INVALID_LEGACY_SCOPE` preservada | ⬜ |
| 18 | `CROSS_TENANT` preservada | ⬜ |
| 19 | Semántica de nulos globales | ✅ matriz de 11 filas |
| 20 | 16 skips auditados | ✅ 4 categorías |
| 21 | Requisito de N8 oculto por skip | ✅ **2 encontrados y resueltos** |
| 22 | Alineación ORM/esquema/API | ⬜ tras implementar |
| 23 | Regresiones N5/N6/N7 planificadas | ✅ |

---

# N8 — SELLO FINAL DE EVIDENCIA

Auditoría de las 23 pruebas de N4 frente a lo que el sello exige.

| Caso | Prueba existente | ¿Ejecución real? | Brecha |
|---|---|---|---|
| `MC-A` | `test_clasifica_los_cinco_casos_del_legado` | Sí, sobre el fixture | — |
| `MC-B` | `test_el_saldo_se_deriva_por_su_almacen` | Sí | — |
| `MC-C` | `test_clasifica_los_cinco_casos_del_legado` | Sí | — |
| `MC-D` | **ninguna** | — | **Falta semilla y prueba** |
| `MC-E` | `test_la_serie_fiscal_ambigua_se_marca_critica_no_ambigua` | Sí | — |
| `INVALID_LEGACY_SCOPE` | `test_un_valor_que_no_es_tenant_ni_empresa_no_es_un_hueco` | **No**: solo compara el valor del enum | **Falta ejecución** |
| `CROSS_TENANT` | Misma prueba, misma limitación | **No** | **Falta ejecución** |
| `MASTER_ASSIGN` | `test_un_maestro_compartido_se_clona_no_se_adjudica` | **No**: llamada directa con conjuntos sintéticos | **Falta fixture y ejecución** |
| `MASTER_CLONE` | Ídem | **No** | Ídem |
| `MASTER_DERIVE` | `test_las_cinco_estrategias_de_maestro_existen` | **No**: solo comprueba que el enum existe | Ídem |
| `MASTER_MANUAL_REVIEW` | Ídem | **No** | Ídem |

## Dos defectos reales que la auditoría destapó

**`CROSS_TENANT` no se emite nunca.** Una fila cuya empresa existe pero pertenece
a **otro** tenant entra por la primera rama del clasificador —«¿ya contiene una
empresa real? entonces no hay nada que reconstruir»— y se marca `OK`. Una
integridad rota se informa como correcta.

La función `cross_tenant()` existe, pero tiene `LIMIT 0` y un comentario que la
declara plantilla. Nadie la llama.

**Las estrategias de maestro no se calculan durante una corrida.** `MAESTROS`
está definido y no se usa; `estrategia_de_maestro` no la invoca el ejecutor. Y
`MASTER_DERIVE` no puede devolverse: la función recibe solo el conjunto de
empresas, y «se deduce por una relación obligatoria» no cabe en ese dato.

| # | Comprobación del sello | Estado |
|---|---|---|
| 1 | Semilla de `MC-D` | ⬜ |
| 2 | Ejecución de `INVALID_LEGACY_SCOPE` | ⬜ |
| 3 | Ejecución de `CROSS_TENANT` | ⬜ (requiere corregir el clasificador) |
| 4 | Estrategias calculadas en la corrida | ⬜ |
| 5 | `MASTER_DERIVE` con condición de disparo | ⬜ |
| 6 | Cero escrituras por caso | ⬜ |
| 7 | Repetibilidad por caso | ⬜ |
| 8 | Aserción de existencia de cada semilla | ⬜ |
| 9 | `INVALID` y `CROSS_TENANT` no degradan a `MC-D` | ⬜ |

---

# N9 — LISTA DE COMPROBACIÓN

| # | Comprobación | Estado |
|---|---|---|
| 1 | Cardinalidad esperada confirmada | ✅ 19 + 4 = **23** |
| 2 | Nombres exactos confirmados | ✅ |
| 3 | Entidad real por tipo | ✅ verificado en el modelo |
| 4 | Clave primaria por tipo | ✅ `id` en los 23 |
| 5 | Alcance por tipo | ✅ empresa directa |
| 6 | Autoridad de empresa | ✅ `company_id` con clave foránea |
| 7 | Permiso por tipo | ✅ |
| 8–11 | `Payment`, `BankTransaction`, `CashSession`, `Reconciliation` mapeados | ✅ |
| 12 | 23 fixtures reales planificados | ⬜ |
| 13 | 23 pruebas de alcance propio | ⬜ |
| 14 | Bloqueo entre empresas | ⬜ |
| 15 | Bloqueo entre tenants | ⬜ |
| 16 | Vincular y desvincular | ⬜ |
| 17 | Metadatos, descarga, previsualización, versiones | ⬜ |
| 18 | Congelado e invariancia | ⬜ |
| 19 | Ficheros, hash, objeto alterado | ⬜ |
| 20 | ClamAV limpio, EICAR, escáner ausente | ⬜ |
| 21 | Clasificación de S3 | ✅ `FR-046-032` es **P1** |
| 22 | Dueño de la retención | ✅ `FR-046-065` es **P1** |
| 23 | Integración con 045 | ✅ `CVG-045-04 RESOLVED_BY_SPEC_046` |
| 24 | Matriz de consumidores rehecha | ⬜ |
| 25 | Reconciliación de artefactos de 046 | ⬜ |
| 26 | Regresiones N5–N8 | ⬜ |
| 27 | N10 y Spec 012 excluidos | ✅ |
