# ADR-D0-007 — Gobierno fiscal: separación entre decisión de software e interpretación tributaria

| Campo | Valor |
|---|---|
| ID | D0-07 |
| Estado | **APPROVED** (arquitectura de gobierno) · **LEGAL_VALIDATION_PENDING** (todos los valores) |
| Fecha | 2026-08-29 |
| Responsable | Arquitecto empresarial · Abogado tributario · Contador público · Especialista en homologación |
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

> **R-D0-07-5.** Está prohibido afirmar «KONTROL cumple SENIAT» u «homologado» sin el acto formal
> de la Spec 056. La afirmación es un entregable regulado, no una descripción de funcionalidad
> (Constitución P19, P20 y Vol. 1 §5).

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
- [ ] Ningún texto del producto afirma homologación sin acto formal.

## Preguntas pendientes

**LEGAL_VALIDATION_REQUIRED** — OQ-08: las 24 reglas. **Ninguna puede resolverla el equipo de
software.** Requieren abogado tributario venezolano y contador público sobre el ejercicio vigente.

## Estado final

**APPROVED** para el gobierno; los valores quedan formalmente fuera del alcance del software.
Clasificación de cierre: **LEGAL_VALIDATION_PENDING**.
