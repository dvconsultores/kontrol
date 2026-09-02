# INFORME DE ANÁLISIS — SPEC 012

`/speckit.analyze 012` · 2026-08-30

Comparación de: Constitución v1.1 → ADR → D0 → G0 → baseline → GAP → roadmap →
spec → clarify → research → plan → data model → contracts → wireframes →
checklist → tasks → acceptance → test plan → risk → traceability → matriz de
legado.

---

## 1. Cobertura

| Métrica | Valor |
|---|---:|
| Requisitos funcionales | 47 |
| Requisitos no funcionales | 6 |
| Criterios de aceptación | 45 |
| Tareas | 83 |
| **FR sin tarea ni criterio** | **0** |
| **NFR sin tarea ni criterio** | **0** |
| **Criterios sin tarea** | **0** |
| **Tareas sin requisito** | **0** |

Verificado por script, no a mano.

## 2. Coherencia con la Constitución

| Principio | Verificación | Estado |
|---|---|---|
| **P5** · histórico protegido | `FR-012-006`, `FR-012-061`, `AC-012-26/27` | ✅ |
| **P6** · el backend manda | `FR-012-021`, `T-012-032`, `T-012-065` | ✅ |
| **P8** · nada hardcodeado | `FR-012-022/032`, `NFR-012-05`, `AC-012-01/02/03` | ✅ |
| **P13** · integridad transaccional | `T-012-051` — snapshot en la misma transacción | ✅ |
| **P17/P22** · autoridad única | `FR-012-014`; convergencia exige 0 cálculos fuera de `pricing.py` | ✅ |
| **P18** · sin modales complejos | `NFR-012-04`, `T-012-088` | ✅ |
| **P21** · paridad del motor | `NFR-012-02`, `T-012-078`, `AC-012-41` | ✅ |
| **P23** · captura temprana | F6 antes que F7; `FR-012-060/063` | ✅ |

## 3. Coherencia con `ADR-D0-005`

Las siete decisiones del ADR están trazadas en §5 de la matriz. **Ninguna se
re-decide.** La alternativa B (motor de reglas versionado con snapshot) es la
que la Spec implementa; A y C siguen descartadas.

| Decisión del ADR | Requisito que la ejecuta |
|---|---|
| Precedencia configurable | `FR-012-010`, `FR-012-011` |
| Desempate determinista o error | `FR-012-012`, `FR-012-013` |
| `PaymentTerm` maestro | `FR-012-030`..`032` |
| Condición ≠ crédito | `FR-012-052` |
| Snapshot con su versión | `FR-012-060` |
| El maestro no reescribe historia | `FR-012-061`, `FR-012-062` |
| Comisiones reservadas | `FR-012-090`, `FR-012-091` |

## 4. Fronteras verificadas

| Frontera | Cómo se garantiza |
|---|---|
| `CommercialZone` ≠ `WarehouseZone` | `FR-012-041`, `AC-012-31`: tablas distintas, **sin FK entre ellas** |
| Moneda: sin catálogo paralelo | `AC-012-32`: se referencia `currencies` |
| Condición de pago ≠ método de pago | `AC-012-33` |
| Aprobaciones: sin vía paralela | `CL-012-09`, `AC-012-23`: se consume el motor 045 |
| Unidades: sin motor paralelo | `FR-012-004`: se usa el de la Spec 011 |
| Permisos y auditoría | `AC-012-34`: se usan los existentes |
| Eventos | `AC-012-35`: 012 **no** emite |

## 5. Contradicciones detectadas

**Ninguna** entre spec, plan, modelo, contratos, tareas y criterios.

Dos incoherencias **externas** encontradas durante el análisis, ambas corregidas
en su artefacto, no aquí:

| Hallazgo | Dónde | Estado |
|---|---|---|
| Cinco Specs mal numeradas en la matriz de consumidoras de 046 | `document-consumer-contract-matrix.md` | Corregido en `docs/roadmap/046-dependency-closeout.md` |
| Se afirmaba que a Tesorería le faltaba su modelo de pago | `SPEC_046_FINAL_CLOSEOUT.md` | Corregido: `ap_payments` existe |

## 6. Riesgo dominante

`R-012-1`: **que 012 acabe siendo un CRUD** y el precio se siga tecleando.

Es el riesgo real, no un riesgo técnico. Se contiene con tres criterios que no
se pueden aprobar por inspección visual:

- `AC-012-12` — reordenar la precedencia **cambia** el precio resuelto.
- `AC-012-26` — editar la lista **no** cambia un documento aprobado.
- `AC-012-17` — sin lista aplicable, **no hay precio**, no hay cero.

Si las tres pasan, la Spec hizo su trabajo.

## 7. La pregunta abierta de negocio

`OQ-06` (`BUSINESS_VALIDATION_REQUIRED` en `ADR-D0-005`) sigue sin responder:
orden de precedencia definitivo, límites de descuento por rol, alcance de
comisiones y política de crédito.

**No bloquea.** Y no por conveniencia: porque `P8` obliga a que todos esos
valores sean **dato configurable**. La Spec especifica la capacidad de
configurarlos y los catálogos nacen vacíos, exactamente como hizo 046 con los
tipos documentales.

Lo que `OQ-06` debe confirmar son los valores que **cargará el cliente**, no el
diseño del sistema.

> Con una excepción que conviene decir en voz alta: si la respuesta de negocio
> fuera «la precedencia debe venir fija en el software», eso sería una violación
> de `P8` y obligaría a reabrir `ADR-D0-005`. Esta Spec no la aceptaría en
> silencio.

## 8. Deuda que 012 no resuelve

| Deuda | Dueño |
|---|---|
| Cálculo y liquidación de comisiones | `FUTURE CAPABILITY` |
| Exposición crediticia en tiempo real | Spec 030 |
| Precio de compra negociado | Spec 016 |
| Motor de promociones | Fuera del alcance por decisión del ADR |

## 9. Veredicto

**`SPEC 012 APTA PARA IMPLEMENTACIÓN`**

0 BLOCKER · 0 CRITICAL · 0 contradicciones internas · 0 requisitos huérfanos ·
0 criterios sin tarea · 0 tareas sin requisito · autoridad `ADR-D0-005`
respetada sin re-decidir · fronteras con 008, 011, 045 y 046 verificadas ·
`OQ-06` abierta y **no bloqueante** por diseño.

**No se implementa.** Requiere autorización expresa.

---

# ANALYZE — ACTUALIZACIÓN DOCUMENTAL POSTERIOR A ARCH-MC-001

| Categoría | Resultado |
|---|---:|
| BLOCKER | 0 |
| CRITICAL | 0 |
| CONTRADICCIONES | 0 |
| REQUISITOS HUÉRFANOS | 0 |
| TAREAS HUÉRFANAS | 0 |
| PREGUNTAS ABIERTAS MATERIALES | 0 |
| CAMBIOS EN CÓDIGO PRODUCTIVO | 0 |

## Lo que el análisis encontró antes de aplicar el delta

No fueron cero. Se resolvieron dentro de este ciclo y por eso el cuadro está a
cero.

| Hallazgo | Tipo | Resolución |
|---|---|---|
| `spec.md` decía nueve entidades y `data-model.md` describía once | CONTRADICCIÓN | Reconciliado en once; `PriceRule` retirada |
| `POST /precio/resolver` recibía la empresa en el cuerpo | CRITICAL | Retirada; la pone `CompanyContext` |
| `POST /descuento/validar` igual | CRITICAL | Ídem |
| `category_id` referenciaba una tabla inexistente | CONTRADICCIÓN | Es `taxonomy_nodes`, de empresa |
| El alcance de la unidad se trataba como empresa sin excepción | CONTRADICCIÓN | La unidad de plataforma lleva empresa nula |
| Ninguna entidad declaraba `__scope__` ni `__scope_authority__` | BLOCKER | Las once lo declaran |
| Las rutas hijas no tenían contrato de validación del padre | BLOCKER | `nested-resource-security-contract.md` |
| La unicidad no declaraba su alcance | CRITICAL | Por empresa en las once |
| `OQ-06` figuraba como pregunta abierta sin clasificar | CIFRA OBSOLETA | `CONFIGURABLE_AT_RUNTIME` |

## Lo que el análisis buscó y no encontró

Entidad sin alcance, entidad sin autoridad, maestro de empresa sin
`CompanyContext`, ruta anidada sin validación del padre, unicidad sin alcance,
contradicción sobre el alcance de Producto, de Tercero, de Moneda o de Tasa,
duplicación de la autoridad de unidades o de presentación, un segundo motor de
aprobación, valores comerciales codificados, mutación del histórico, ambigüedad
en el versionado, desajuste con OpenAPI, requisitos diseñados sobre arquitectura
superada, tarea de producción accidental, migración productiva accidental e
implementación de código accidental.

## `OQ-06`

Reclasificada como `CONFIGURABLE_AT_RUNTIME`, no como pregunta abierta material.
El detalle y su política por defecto están en `clarifications.md`.

---

# ANALYZE — CICLO DE IMPLEMENTACIÓN

| Categoría | Resultado |
|---|---:|
| BLOCKER | 0 |
| CRITICAL | 0 |
| CONTRADICCIONES | 0 |
| REQUISITOS HUÉRFANOS | 0 |
| TAREAS HUÉRFANAS | 0 |
| PREGUNTAS ABIERTAS MATERIALES | 0 |

## Antes de implementar

Las once entidades coincidían en `spec.md`, `data-model.md` y
`commercial-scope-matrix.md`. Ninguna decisión material nueva apareció: el ciclo
documental anterior las había cerrado todas, y `OQ-06` seguía clasificada como
configuración.

## Lo que la implementación encontró

Ninguno contradice ARCH-MC-001, y ninguno era una decisión comercial nueva.

| Hallazgo | Tipo | Resolución |
|---|---|---|
| La exclusión vivía solo en la migración; la prueba pasaba sin comprobar nada | CRITICAL propio | Declarada también en el ORM, con `btree_gist` en `before_create` |
| Un código duplicado terminaba en `500` | CRITICAL propio | El choque llega al `commit` y se traduce en `409` |
| Un solape de vigencias terminaba en `500` | CRITICAL propio | Ídem, con su motivo propio |
| La prueba de clave foránea fallaba por la restricción de «uno de los dos» | PRUEBA INVÁLIDA | Se usa un artículo real: falla por el motivo correcto |
| Una prueba se saltaba por falta de nodo de taxonomía | SALTO QUE ESCONDE | Se siembra el nodo; ningún salto nuevo |

Los tres primeros son la misma lección de N7 vista desde dentro: una restricción
que la base impone y la aplicación no traduce protege el dato y miente al
usuario.

## Lo que se buscó y no se encontró

Entidad sin alcance, empresa directa sin FK, derivada con `company_id`
redundante, ruta hija sin validación del padre, empresa desde el cuerpo,
respaldo Tenant→Company, alcance contradicho de Producto, Tercero o Moneda,
unidad de plataforma rota, unicidad sin alcance, precedencia codificada, un
segundo motor de aprobación, coma flotante monetaria, consulta de frontend sin
empresa y prueba negativa que falla por el motivo equivocado.
