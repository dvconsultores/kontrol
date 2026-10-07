# ADR-D0-007 — Gobierno fiscal: separación entre decisión de software e interpretación tributaria

| Campo | Valor |
|---|---|
| ID | D0-07 |
| Estado | **APPROVED** (arquitectura de gobierno) · **LEGAL_VALIDATION_PENDING / NARROWED** (todos los valores; **`HOMOLOGATION_REQUIREMENT_REMOVED`** el 2026-10-07) |
| Fecha | 2026-08-29 |
| Responsable | Arquitecto empresarial · Abogado tributario · Contador público · Especialista fiscal en facturación |
| Specs afectadas | **039, 040, 041, 042, 043** · 014, 027, 028, 034, 037, 056 |

## Problema

El motor fiscal está implementado —reglas versionadas, numeración atómica, hash, libros
reconstruibles— pero **sin un solo valor oficial cargado y sin revisión profesional**. El riesgo no
es que falte código: es que alguien confunda «el mecanismo funciona» con «la norma se cumple».

## Por qué debe decidirse ahora

Sin una frontera explícita, la presión de entregar empuja a que un desarrollador escriba una
alícuota «provisional» en una migración de seed. A partir de ese momento el sistema afirma algo
tributario que nadie validó, y la afirmación se propaga a facturas, libros y declaraciones.

## Principio rector

> **R-D0-07-1.** El equipo de software decide **el mecanismo**. El equipo tributario decide **el
> contenido**. Ningún rol puede invadir al otro.

| Decide software (APPROVED aquí) | Decide el profesional tributario |
|---|---|
| Que las reglas se versionan con vigencia y fuente | Cuál es la alícuota vigente |
| Que un documento emitido es inmutable | Qué documento corresponde a cada operación |
| Que el correlativo y el número de control se asignan atómicamente | Qué formato y qué autorización aplican |
| Que el libro se reconstruye desde eventos | Qué columnas exige la norma |
| Que existe estado `LEGAL_VALIDATION_REQUIRED` | Cuándo una regla puede salir de ese estado |
| Que la retención se calcula sobre una base declarada | Qué concepto, porcentaje, mínimo y sustraendo aplican |

## Reglas de gobierno

> **R-D0-07-2.** Ninguna alícuota, porcentaje, unidad tributaria, concepto, mínimo, sustraendo,
> plazo ni fecha fiscal puede existir en el código, en una migración, en un seed ni en un valor por
> defecto. Todos son **datos** de `TaxRuleVersion` con fuente legal, Gaceta, artículo, vigencia
> desde/hasta, versión y estado.

> **R-D0-07-3.** Toda regla nace en estado `LEGAL_VALIDATION_REQUIRED`. Solo un profesional
> identificado puede promoverla a `VALIDATED`, y la promoción queda auditada con quién, cuándo y
> contra qué fuente.

> **R-D0-07-4.** El sistema **no puede emitir** un documento fiscal aplicando una regla que no esté
> `VALIDATED` y vigente. No hay modo permisivo ni bandera de desarrollo que lo eluda en producción.

> **R-D0-07-5.** Está prohibido afirmar «KONTROL cumple SENIAT» u «homologado». La homologación del
> software bajo SNAT/2024/000121 **dejó de existir** (derogada por SNAT/2026/00084, G.O. N.º 43.435,
> 12-08-2026); lo que la Spec 056 produce es una **validación de cumplimiento fiscal** contra la
> normativa vigente, con evidencia, y así se declara. La afirmación de cumplimiento es un entregable
> regulado, no una descripción de funcionalidad (Constitución P19, P20 y Vol. 1 §5).

> **R-D0-07-6.** Una regla derogada **no se borra ni se reescribe**: se cierra su vigencia. Los
> documentos emitidos bajo ella conservan su snapshot y siguen siendo reconstruibles (P4, P5).

## Matriz de validación

Las 24 reglas y su estado se detallan en `D0-fiscal-validation-matrix.md`. Resumen:

| Grupo | Reglas | Estado |
|---|---|---|
| IVA (alícuotas, exento, exonerado, no sujeto) | 4 | LEGAL_VALIDATION_REQUIRED |
| Retención de IVA | 3 | LEGAL_VALIDATION_REQUIRED |
| ISLR y Decreto 1.808 | 4 | LEGAL_VALIDATION_REQUIRED |
| IGTF | 2 | LEGAL_VALIDATION_REQUIRED |
| Documentos, correlativos y control | 5 | Mecanismo APPROVED · formato LEGAL_VALIDATION_REQUIRED |
| Libros y cierres | 3 | Mecanismo APPROVED · formato LEGAL_VALIDATION_REQUIRED |
| Regulatorio (SICA/SIGESAI/SACS) | 3 | LEGAL_VALIDATION_REQUIRED |

**Ninguna en `VALIDATED`.**

## Impacto

| Dimensión | Impacto |
|---|---|
| Frontend | Indicador visible del estado de validación de cada regla; bloqueo de emisión con regla no validada |
| Backend | Verificación de estado `VALIDATED` en el punto de cálculo; sin ruta alternativa |
| Base de datos | `TaxRuleVersion` gana estado de validación, validador y fecha |
| Integraciones | Ninguna (P20: sin integración oficial sin convenio) |
| QA | QA fiscal verifica el **mecanismo**; la conformidad normativa es revisión profesional, no prueba automatizada |
| Seguridad | Promover una regla es una operación privilegiada y auditada |
| Fiscal | Es el objeto de la decisión |

## Migración / compatibilidad

**`SAFE_MIGRATION`** — las reglas hoy cargadas (si las hay) pasan a `LEGAL_VALIDATION_REQUIRED`.
Esto puede **detener emisiones en entornos de prueba**, y es el comportamiento correcto: hoy esas
emisiones se apoyan en valores que nadie validó.

## Criterios de aceptación

- [ ] Búsqueda de alícuotas y porcentajes fiscales en el código: cero coincidencias.
- [ ] Emitir con regla no `VALIDATED` es imposible en producción (probado).
- [ ] Promover una regla exige profesional identificado y queda auditado.
- [ ] Derogar cierra vigencia sin alterar documentos históricos (probado).
- [ ] Ningún texto del producto afirma homologación ni cumplimiento SENIAT; la validación de la Spec 056 se declara como validación, con su evidencia.

## Preguntas pendientes

**LEGAL_VALIDATION_REQUIRED** — OQ-08: las 24 reglas. **Ninguna puede resolverla el equipo de
software.** Requieren abogado tributario venezolano y contador público sobre el ejercicio vigente.

## Actualización 2026-10-07 — derogatoria de SNAT/2024/000121

| | |
|---|---|
| `LEGAL_REFERENCE` | Providencia Administrativa SNAT/2026/00084 |
| `OFFICIAL_GAZETTE` / `DATE` | G.O. N.º 43.435 · 12-08-2026 |
| `REPEALED_RULE` | SNAT/2024/000121 (G.O. N.º 43.032, 19-12-2024): requisitos de los proveedores de sistemas informáticos para la emisión de facturas y otros documentos fiscales (homologación) |
| `SOURCE` / `VERIFIED` | Nota de Actualidad Corporativa STL de PwC Venezuela (14-08-2026), sumario de la G.O. 43.435 (IUSDATA), Acceso a la Justicia · **VERIFIED** por documentación jurídica fiable; el texto íntegro de la Gaceta no está incorporado al repositorio (`docs/evidence/master-57-reconciliation/referencia-legal.md`) |

**Qué cambia:** la parte de D0-07 asociada a la homologación/autorización del proveedor y del software
(OQ-09 en su mitad de «plazo de homologación», rol «especialista en homologación», acto formal externo
de la Spec 056) **se retira como bloqueo vigente** (`HOMOLOGATION_REQUIREMENT_REMOVED`). **Qué no
cambia:** las 24 reglas siguen `LEGAL_VALIDATION_REQUIRED`; las obligaciones de factura, IVA, ISLR,
IGTF, documentos fiscales, numeración y control, contingencia, libros y cierres siguen vigentes y
siguen exigiendo validación profesional; R-D0-07-2..4 y R-D0-07-6 no se tocan; ninguna Spec fiscal se
declara completa por esta derogatoria. La derogatoria dejó, según las mismas fuentes, un vacío a la
espera de nuevos lineamientos: si el SENIAT dictara un régimen nuevo, se incorporará como norma
vigente en la matriz, no como reaparición de la 121.

## Estado final

**APPROVED** para el gobierno; los valores quedan formalmente fuera del alcance del software.
Clasificación de cierre: **LEGAL_VALIDATION_PENDING / NARROWED** (homologación retirada; validación de
reglas pendiente).
