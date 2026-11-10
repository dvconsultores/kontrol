# PROC-09 · Contrato de campos (2026-11-11)

Qué datos exige la norma para determinar la aplicabilidad y controlar el compromiso, y si la plataforma ya tiene su autoridad.
No se implementa nada mientras el gate siga BLOCKED (`DECISIONES.md`).

## Aplicabilidad (por oferta)

| Dato | Fuente legal | Autoridad en la plataforma | Estado |
|---|---|---|---|
| Monto total de la oferta, incluidos los tributos | LCP art. 31; RLCP art. 34 | Ninguna: la oferta de PROC-06 no registra monto | FALTA (OBS-PROC08-MONTO-01, OQ-PROC09-01) |
| Valor de la unidad tributaria a la fecha relevante | LCP art. 31; regla de umbrales de la biblioteca | Ninguna; fuente N38 en clase C | FALTA (OQ-PROC09-02) |
| Fecha relevante de la comparación (recepción de la oferta) | LCP art. 31 («ofertas cuyo monto…») | `recibida_en` de la oferta (PROC-06) | DISPONIBLE |
| Contratación entre órganos y entes del Estado, o selección encomendada a ellos | RLCP art. 3 | Ninguna: la oferta no registra la naturaleza del oferente | FALTA |
| Servicio laboral excluido de las modalidades | RLCP art. 40 | Ninguna | FALTA |
| Empresa extranjera sin filial, prestación fuera del país, sin oferta nacional suficiente | RLCP art. 48 | Ninguna | FALTA |
| Empresa extranjera con filial y ejecución en el territorio | RLCP art. 49 | Ninguna | FALTA |
| Regla aplicada (fuente, artículo, Gaceta, vigencia, versión) | Biblioteca N11/N12 | Patrón de catálogo versionado de PROC-10 (`garantias_reglas`) | REUTILIZABLE |

Resultado esperado de la evaluación, una vez disponibles los datos: `APLICA`, `NO_APLICA` (con la exclusión y su artículo),
`NO_DETERMINABLE` (con los datos que faltan), nunca un valor por omisión.

## Compromiso (oferente y adjudicatario)

| Dato | Fuente legal | Autoridad | Estado |
|---|---|---|---|
| Declaración jurada con el compromiso ofrecido, como documento | RLCP art. 38; LCP art. 76 num. 8 | Documentos (Spec 046) vinculados a la oferta, patrón de PROC-06 | REUTILIZABLE |
| Modalidad o modalidades del compromiso (seis de la definición) | LCP art. 6 num. 24; RLCP art. 41 | Catálogo cerrado por fuente | DISEÑABLE |
| Descripción del proyecto social o aporte y comunidad beneficiada | LCP art. 32; RLCP arts. 41 y 45 | Texto con soporte | DISEÑABLE |
| Porcentaje exigido | LCP art. 31 frente a RLCP art. 35 | — | BLOQUEADO (OQ-PROC09-03) |
| Base de cálculo: monto del objeto del contrato sin IVA | RLCP art. 91 | Ninguna (contrato no existe; la oferta no registra monto) | FALTA (CNT-01 / OQ-PROC09-01) |
| Plazo del proyecto social, menor que el del contrato | RLCP art. 36 | Contrato (CNT-01) | FALTA |
| Cumplimiento antes del cierre administrativo | LCP arts. 32 y 118 num. 3 | Administración del contrato (CNT-03, CNT-08) | FALTA |
| Unidad técnica de seguimiento | RLCP art. 44 | Estructura y cargos (ORG-02, ORG-03) | DISPONIBLE |
| Publicación de la adjudicación con el compromiso | RLCP art. 42 | Decisión de PROC-08 (sin publicación web) | PARCIAL |
