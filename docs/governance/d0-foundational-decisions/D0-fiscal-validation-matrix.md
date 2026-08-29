# MATRIZ DE VALIDACIÓN FISCAL

> Deriva de `ADR-D0-007` y `POL-D0-006`.
> **Ninguna regla está `VALIDATED`.** El software no puede promoverlas.
> «Parametrizable» = el valor vive en `TaxRuleVersion`. «Hardcode permitido» = **NO en todos los casos**.

| # | Regla | Fuente documental | Vigencia | Parametrizable | Hardcode | Revisión requerida | Estado |
|---|---|---|---|:--:|:--:|---|---|
| F-01 | Alícuota general de IVA | Ley del IVA · G.O. 6.507 Ext. | Por determinar | Sí | **No** | Abogado tributario + contador | LEGAL_VALIDATION_REQUIRED |
| F-02 | Alícuota reducida y adicional de IVA | Ley del IVA · providencias | Por determinar | Sí | **No** | Abogado tributario | LEGAL_VALIDATION_REQUIRED |
| F-03 | Clasificación exento / exonerado / no sujeto | Ley del IVA · decretos de exoneración | Por determinar | Sí | **No** | Abogado tributario | LEGAL_VALIDATION_REQUIRED |
| F-04 | Determinación del hecho imponible y su fecha | Ley del IVA · COT | Por determinar | Sí | **No** | Abogado tributario | LEGAL_VALIDATION_REQUIRED |
| F-05 | Condición de agente de retención de IVA | SNAT/2015 y sucesivas | Por determinar | Sí | **No** | Abogado tributario | LEGAL_VALIDATION_REQUIRED |
| F-06 | Porcentaje de retención de IVA (75 % / 100 % u otro) | Providencia vigente | Por determinar | Sí | **No** | Abogado tributario | LEGAL_VALIDATION_REQUIRED |
| F-07 | Comprobante de retención de IVA: formato y plazo de entrega | Providencia vigente | Por determinar | Sí | **No** | Contador público | LEGAL_VALIDATION_REQUIRED |
| F-08 | Conceptos de retención de ISLR y sus códigos | **Decreto 1.808** | Por determinar | Sí | **No** | Abogado tributario | LEGAL_VALIDATION_REQUIRED |
| F-09 | Porcentajes, mínimos y sustraendos de ISLR | **Decreto 1.808** | Por determinar | Sí | **No** | Abogado tributario + contador | LEGAL_VALIDATION_REQUIRED |
| F-10 | Base de cálculo de ISLR según residencia y domicilio | Ley de ISLR · G.O. 6.210 Ext. | Por determinar | Sí | **No** | Abogado tributario | LEGAL_VALIDATION_REQUIRED |
| F-11 | Unidad tributaria aplicable y su conversión | Providencia vigente | Por determinar | Sí | **No** | Contador público | LEGAL_VALIDATION_REQUIRED |
| F-12 | Hecho generador del IGTF | Ley de Reforma del IGTF · G.O. 6.687 Ext. | Por determinar | Sí | **No** | Abogado tributario | LEGAL_VALIDATION_REQUIRED |
| F-13 | Alícuota y base del IGTF por medio de pago | Ley IGTF · providencias | Por determinar | Sí | **No** | Abogado tributario | LEGAL_VALIDATION_REQUIRED |
| F-14 | Modalidad de facturación autorizada (forma libre computarizada) | SNAT/2011/00071 y sucesivas | Por determinar | Sí | **No** | Especialista en homologación | LEGAL_VALIDATION_REQUIRED |
| F-15 | Formato y contenido obligatorio de la factura | SNAT/2011/00071 | Por determinar | Sí | **No** | Contador + homologación | LEGAL_VALIDATION_REQUIRED |
| F-16 | Requisitos de la nota de crédito y de débito | SNAT/2011/00071 | Por determinar | Sí | **No** | Contador público | LEGAL_VALIDATION_REQUIRED |
| F-17 | Estructura del número de control y su autorización | SNAT/2011/00071 | Por determinar | Sí | **No** | Especialista en homologación | LEGAL_VALIDATION_REQUIRED |
| F-18 | Reglas de correlativo, series y lotes de imprenta | Providencia vigente | Por determinar | Sí | **No** | Contador + homologación | LEGAL_VALIDATION_REQUIRED |
| F-19 | Columnas y formato del libro de ventas | Ley del IVA · reglamento | Por determinar | Sí | **No** | Contador público | LEGAL_VALIDATION_REQUIRED |
| F-20 | Columnas y formato del libro de compras | Ley del IVA · reglamento | Por determinar | Sí | **No** | Contador público | LEGAL_VALIDATION_REQUIRED |
| F-21 | Plazos de cierre y de declaración | COT · calendario fiscal | Por determinar | Sí | **No** | Contador público | LEGAL_VALIDATION_REQUIRED |
| F-22 | Procedimiento de contingencia de facturación | Providencia vigente | Por determinar | Sí | **No** | Homologación | LEGAL_VALIDATION_REQUIRED |
| F-23 | Requisitos de guía SICA / SUNAGRO | Expediente SICA · manuales | Por determinar | Sí | **No** | Especialista SICA | LEGAL_VALIDATION_REQUIRED |
| F-24 | Requisitos de SIGESAI / INSAI y de SACS | Manuales INSAI · normativa SACS | Por determinar | Sí | **No** | Especialistas SIGESAI y SACS | LEGAL_VALIDATION_REQUIRED |

## Resumen

| Estado | Cantidad |
|---|---:|
| VALIDATED | **0** |
| LEGAL_VALIDATION_REQUIRED | **24** |

## Lo que sí queda decidido por arquitectura

El **mecanismo** que soporta las 24 reglas está aprobado y no requiere validación tributaria:

- Versionado con fuente, Gaceta, artículo, vigencia desde/hasta y estado.
- Snapshot de la regla aplicada en cada documento emitido.
- Asignación atómica de correlativo y número de control.
- Inmutabilidad del documento emitido; corrección solo por nota, anulación o reverso vinculado.
- Reconstrucción de libros desde documentos y eventos.
- Bloqueo de emisión con regla no validada.

## Advertencia de gobierno

Que el mecanismo funcione y las pruebas pasen **no significa cumplimiento normativo**. La única
evidencia admisible de conformidad es la revisión profesional de cada regla y, para declarar
homologación, el acto formal de la Spec 056.
