# CONVERGENCIA — 004-COMPRAS-CUENTAS-POR-PAGAR

| Campo | Valor |
|---|---|
| Iniciativa | 004-compras-cuentas-por-pagar |
| Versión | 1.0 |
| Ruta | `specs/004-compras-cuentas-por-pagar/convergence.md` |

## 1. Propósito

Registrar brechas y nuevas tareas tras la implementación. `/speckit.converge` se ejecuta al cierre.

## 2. Brechas identificadas

| ID | Brecha | Acción | Responsable | Estado |
|---|---|---|---|---|
| CVG-004-01 | Umbrales de aprobación por monto/categoría por empresa | Decisión de negocio (CL-004-11) | Compras | Pendiente |
| CVG-004-02 | Tolerancias de recepción/sobrefacturación por empresa | Decisión (CL-004-12) | Compras | Pendiente |
| CVG-004-03 | Motor fiscal de retenciones (cálculo completo IVA/ISLR/IGTF) | Spec 007 | Fiscal | Pendiente (007) |
| CVG-004-04 | Conciliación bancaria de pagos | Spec 006 (tesorería) | Tesorería | Pendiente (006) |
| CVG-004-05 | Contrato `Payment`/`Application` consumido por 006 | Integración 006 | Arquitecto | Pendiente (006) |

## 3. Implementado (004)

| Elemento | Estado |
|---|---|
| Modelos (21 tablas) + migración `0004_compras` | ✔ |
| Requisición (flujo + aprobación) | ✔ |
| Cotizaciones y comparación | ✔ |
| Órdenes de compra (máquina de estados + aprobación por regla) | ✔ |
| Recepción → **invoca el motor de 003** (lotes/seriales/calidad/costos) | ✔ |
| Factura del proveedor (duplicidad + estados + reverso) | ✔ |
| Conciliación triple (orden/recepción/factura) | ✔ |
| Devoluciones y nota de crédito del proveedor | ✔ |
| CxP: open items, pagos (idempotencia), aplicaciones atómicas, anticipos, programación, aging | ✔ |
| Retención estructural referida a reglas versionadas | ✔ |
| API `/purchasing/*` (32 endpoints) | ✔ |
| Frontend: requisiciones, órdenes, recepciones, facturas, CxP | ✔ |

## 4. Validación local

| Compuerta | Resultado |
|---|---|
| Backend pytest | ✔ 74/74 (incluye 17 de compras) |
| Backend ruff | ✔ limpio (incluye migración) |
| Backend mypy | ✔ 60 archivos, 0 issues |
| Alembic | ✔ head `0004_compras` (upgrade/downgrade) |
| OpenAPI | ✔ 32 endpoints `/purchasing/*` (96 rutas totales) |
| Frontend tsc / eslint | ✔ limpios |
| Frontend vitest / build | ✔ 16/16 · build OK |

## 5. Estado

| Elemento | Estado |
|---|---|
| Fase documental | ✔ |
| Implementación | ✔ (sujeta a 001 certificada + 002/003 implementados + autorización expresa) |
| Certificación (Docker/CI/legal, integración 005/006/007) | Pendiente — depende de 001 certificada y de Specs 005/006/007 |

---

# CONVERGENCIA — SPEC 019 · RECEPCIÓN FÍSICA

## Puerta

| Criterio | Exigido | Resultado |
|---|---|---|
| Constitution Gate | PASS | PASS (14 validaciones) |
| BLOCKER · CRITICAL · CONTRADICTIONS | 0 · 0 · 0 | 0 · 0 · 0 |
| Requisitos huérfanos · Tareas huérfanas | 0 · 0 | 0 · 0 |
| OQ material | 0 | 0 |
| Trazabilidad | 100 % | 100 % (32 datos trazados uno a uno) |
| Etapas de 019 cubiertas | todas | **8 de 8** |
| Backend | 0 fallos | **871 pruebas · 863 pasadas · 8 saltadas (S3) · 0 fallos · 0 errores** |
| — nuevas de esta Spec | — | **37** (18 funcionales, 13 estructurales, 6 de migración) |
| Frontend | verde | 283/283 · `tsc` · ESLint · build |
| E2E | verde | 6/6 en Chromium, Firefox y WebKit · axe 22/22 · rutas 1/1 |
| Responsive | sin regresión | 194/216, **los 22 casos idénticos** a la auditoría anterior; ninguno en recepciones |
| Instalación limpia | verde | subir a cabeza, bajar la `0044`, volver a subir |
| Deuda interna P0 | 0 | 0 |

## Lo que cambió de verdad

Antes, la recepción era contable: sabía de qué orden venía, qué producto y cuánto, y nada más. No
sabía cuándo llegó el camión, cuántos bultos bajaron, contra qué se comparó lo recibido, qué se vio
al abrir las cajas ni en qué presentación venía la mercancía. Todo eso solo existe mientras el
camión está en el muelle.

Y había algo peor, que el checkpoint operativo había señalado como riesgo futuro y resultó ser un
defecto vivo: **el saldo de inventario se acumulaba con la cantidad tecleada**. El movimiento
calculaba y guardaba bien la cantidad base; la línea siguiente sumaba al saldo el número que el
usuario había escrito. Como la interfaz de recepción no admitía presentaciones, en la recepción no
se notaba. Pero la API de movimientos sí las admitía, así que cualquier entrada con presentación
llevaba tiempo dejando el inventario corto. Dos cajas de doce sumaban dos.

Ahora la recepción registra el arribo con su hora y su responsable, la descarga programada, los
bultos declarados y los contados, las cuatro comparaciones documentales con su resultado, la
inspección con su momento y sus notas, el estado físico de cada línea con la cantidad dañada y su
descripción, el sobrante observado, y la unidad y presentación con las que llegó, con el factor
congelado. Al aceptar, el asiento entra en cantidad base y se emite el acta.

## Sobre la corrección en el motor de inventario

Una línea, en `record_movement`, para que el saldo acumule la cantidad base en vez de la tecleada.
Es capacidad de la Spec 023 y la autorización pedía no absorber su motor, pero también exigía que el
movimiento de 019 usara la cantidad base, y eso no se puede cumplir sin ella. Se hizo la corrección
mínima que el propio encargo contempla y se deja registrada aquí con su dueño. Sin presentación el
factor es 1 y las dos cantidades coinciden, de modo que ningún llamante anterior cambia de
comportamiento; la regresión completa lo confirma.

## Fronteras, medidas y no declaradas

Aceptar una recepción no crea preparación, no asigna ubicación, no abre incidencia y no escribe
ningún estado de mercancía nuevo. Las cuatro cosas están probadas, no afirmadas. El invariante que
el checkpoint operativo dejó escrito —almacén conocido, ubicación nula entre recibir y ubicar— se
preserva y ahora tiene una prueba que lo sostiene.

## Deuda

**Interna de la Spec 019: ninguna P0.** Anotado para otras Specs: el expediente de la incidencia es
de la 020, la liberación formal y los estados no vendibles del saldo son de la 021 con capacidad de
la 023, y la zona temporal de recepción es de la 022.

## Veredicto

`SPEC 019 — COMPLETE / CONVERGED`

---

# CONVERGENCIA — SPEC 020 · INCIDENCIAS DE RECEPCIÓN

## Puerta

| Criterio | Exigido | Resultado |
|---|---|---|
| Constitution Gate | PASS | PASS (12 validaciones) |
| BLOCKER · CRITICAL · CONTRADICTIONS | 0 · 0 · 0 | 0 · 0 · 0 |
| Requisitos huérfanos · Tareas huérfanas | 0 · 0 | 0 · 0 |
| OQ material | 0 | 0 |
| Trazabilidad | 100 % | 100 % |
| Etapas de 020 cubiertas | 3 de 3 | 3 de 3 |
| Backend | 0 fallos | **920 · 912 pasadas · 8 saltadas declaradas · 0 fallos · 0 errores** |
| — nuevas de esta Spec | — | **47** (24 funcionales, 14 estructurales, 9 de migración e integridad) |
| Frontend | verde | 285/285 · `tsc` · ESLint · build |
| E2E | verde | **86 pasadas · 16 fallos ajenos** en 13 suites × 3 navegadores. Los 16 son previos: los mismos 7 casos fallan idénticos en el árbol anterior a esta Spec, verificado en copia limpia de `409b945`. Dos suites del arnés N6 no corren en esta pila |
| Instalación limpia | verde | subir a cabeza, bajar la `0045`, volver a subir |
| Deuda interna P0 | 0 | 0 |

## Lo que cambió de verdad

Antes, una recepción con diez unidades dañadas solo sabía decir `quantity_rejected = 10`. Sin tipo,
sin evidencia, sin responsable y sin tratamiento. La diferencia existía como número y desaparecía
como hecho.

Ahora la diferencia se registra con su tipo —uno de los cinco del proceso—, apunta a la línea que la
Spec 019 ya describió, lleva su cantidad en unidad base, se le adjunta evidencia por el gestor
documental, se escala a Compras dejando constancia de cuándo y de quién, y se cierra con uno de los
cuatro tratamientos del contrato, con motivo. El ajuste autorizado pasa antes por el motor de
aprobaciones, porque el proceso lo declara control crítico.

## Lo que se descartó, que fue lo más útil

El checkpoint sugería revisar trece candidatos a tipo de incidencia. Ocho no lo eran: empaque,
presentación, lote, serial y vencimiento son datos que la Spec 019 captura; calidad es el veredicto
`quality_status`; y rechazo y cuarentena son tratamientos. Implementarlos habría creado un segundo
lugar donde vive lo que ya vive en la recepción, que es justo el patrón que las Specs 029, 030 y 019
vinieron cerrando.

## La frontera con la Spec 021, medida

Registrar el tratamiento no es ejecutarlo. Una prueba lo comprueba: resolver una incidencia no crea
movimientos, no cambia saldos y no escribe estados de mercancía. Lo que la 020 entrega es un
resultado estructurado —tipo, línea, cantidad base y tratamiento— que la 021 podrá consumir sin
interpretar texto libre. Su otro bloqueo, la capacidad de la Spec 023 para escribir estados no
vendibles, sigue exactamente donde estaba.

## Deuda

**Interna: ninguna P0.** La Spec 021 sigue esperando dos cosas: esta capacidad, que ya tiene, y que
el motor de saldos aprenda a escribir estados de mercancía no vendibles, que es de la Spec 023.

## Veredicto

`SPEC 020 — COMPLETE / CONVERGED`

## Los tres fallos y los dos defectos que aparecieron después de la primera regresión

Ninguno se ocultó y ninguno se dio por bueno sin causa.

| Qué apareció | Por qué | Desenlace |
|---|---|---|
| 3 fallos en el guardia del registro documental | Registrar `ReceiptIncident` como tipo vinculable cambia una cardinalidad fija y exige una semilla real por tipo | Cardinalidad actualizada y semilla añadida: una incidencia documental de verdad, no una fila mínima |
| La tabla migrada rechazaba todo insert | `created_at` sin `server_default`; el ORM no lo pone desde Python | Migración corregida y prueba nueva que inserta con el ORM contra la tabla de Alembic |
| 15 selectores con nombre accesible distinto del visible | El `aria-label` pisaba la asociación de `FormField` | Retirados los quince en cinco páginas; el nombre accesible es la etiqueta |
| 1 fallo del recorrido de rutas en WebKit | La pila e2e se levantó sin `KONTROL_COOKIE_SECURE=false`; WebKit rechaza la cookie sobre HTTP | Configuración de la pila, no del producto: corregida, 27/27 en los tres navegadores |
| 16 fallos en aprobaciones, unidades y almacenes | Ajenos a esta Spec | Verificados idénticos en copia limpia del árbol anterior. **No se tocaron**: son de las Specs 045, 011 y 008 |

## Un hallazgo que no es de esta Spec y conviene no perder

`approvals.spec.ts` comprueba que la bandeja filtrada con `company_id=empresa-inexistente` devuelve
cero. El endpoint **no declara** ese parámetro: FastAPI lo ignora y la empresa sale del contexto,
que es justo lo que el contrato de alcance exige. La aserción solo pasaba cuando la bandeja estaba
vacía por otras razones, así que nunca comprobó lo que dice comprobar.

Se deja anotado y **no se corrige aquí**: es prueba de la Spec 045, y arreglarla desde la 020 sería
tocar lo que esta Spec declaró fuera de alcance. Importa porque una prueba falsa de aislamiento
entre empresas es peor que ninguna: da por cubierta una frontera que nadie está vigilando.


---

## Sello de evidencia posterior al cierre — 2026-09-04

La evidencia que se perdió con el reinicio del entorno se rehízo entera: PostgreSQL 18.6 y ClamAV
1.4.3 reprovisionados, backend **920 · 912 · 8 saltadas · 0 fallos**, frontend 285/285 con `tsc`,
ESLint y build, y una e2e **completa** de 297 ejecuciones en tres navegadores —incluidas las dos
suites del arnés N6 sobre su propia base, que nunca se habían corrido y pasan las 75—.

Los 65 fallos se reprodujeron uno a uno contra `409b945`, el árbol anterior a esta Spec, que falla
**77** en esas mismas siete suites. Regresiones nuevas de la 020: **cero**. Y trece casos que
fallaban antes ahora pasan, casi todos de accesibilidad, por el arreglo de los quince `aria-label`
que esta Spec destapó.

`SPEC 020 — COMPLETE / CONVERGED / EVIDENCE SEALED`. Detalle en `spec020-evidence-seal.md`.
