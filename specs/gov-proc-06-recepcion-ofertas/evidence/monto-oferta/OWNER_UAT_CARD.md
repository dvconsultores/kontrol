# Tarjeta de prueba de la dueña · Monto de la oferta (PROC-06)

- **Dónde:** Menú › Gobierno › Expedientes de contratación › un expediente › sección **Ofertas** › «Ver detalle» de una oferta › **Monto declarado**.
- **Quién:** un usuario con «Ofertas: ver» y «Ofertas: declarar monto» (pide MFA). Para ver el monto en la decisión, además «Decisión: ver».
- **Qué demuestra:** KONTROL registra el monto que **declara la oferta**, con su soporte, sin inventarlo ni recalcularlo. Respeta el sello hasta la apertura, guarda cada corrección con motivo y lo muestra en la decisión, el reporte y las garantías.

## Preparación (una vez)

1. Un expediente de concurso con comisión, matriz bloqueada y **dos ofertas selladas**, cada una con su documento.
2. Antes de abrirlas, mira la sección Ofertas: en «Monto» aparece «Sellada: el monto se registra después de la apertura».
3. Concluye la recepción y abre las dos ofertas en acto, con el acta.

## Pasos

| N.º | Acción | Resultado esperado |
|---|---|---|
| 1 | En la oferta R-0001, pulsa «Ver detalle» | Bloque «Monto declarado»: «No declarado» y el botón **Declarar monto** |
| 2 | Pulsa «Declarar monto» | Formulario con Moneda (VES, USD, EUR), Monto del objeto sin IVA, Tributos, Total con tributos y Documento soporte (el documento de la oferta o el acta de apertura) |
| 3 | Escribe 1000.00, 160.00 y 1160.00 en VES, elige el documento de la oferta y pulsa «Registrar monto» | El resumen muestra «1160.00 VES (total con tributos)». El bloque muestra los 4 datos, el soporte y quién lo registró y cuándo |
| 4 | Pulsa «Corregir monto», cambia el total a 1170.00 y elige el acta | «Registrar monto» sigue inactivo hasta escribir un motivo de 10 caracteres o más |
| 5 | Escribe el motivo «Error de transcripción del total» y registra | Total 1170.00 VES. Aviso: «La suma declarada no coincide con el total (diferencia 10.00 VES).» KONTROL no lo corrige. **Historial del monto** con las 2 versiones y el motivo |
| 6 | Intenta poner un importe con letras o en otra moneda (por ejemplo, COP) | Se rechaza con el mensaje en el campo, y no se guarda nada |
| 7 | Concluye la evaluación (PROC-07) y vuelve a la oferta | «La evaluación está concluida: el monto ya no se registra ni se corrige». No hay botón |
| 8 | Abre la sección Decisión | «Ofertas evaluadas» tiene la columna **Monto declarado**: «1170.00 VES» y, en la otra oferta, «No declarado» |
| 9 | Tras adjudicar, abre Gobierno › Reporte de contrataciones | La sección «Monto» muestra la tabla por moneda (total con tributos, monto sin IVA y adjudicaciones), las adjudicaciones sin monto y la nota. También aparece en el CSV |
| 10 | En Garantías, registra un requisito «Mantenimiento: porcentaje de la oferta» del 2,50 % y una garantía de 29.25 VES sobre esa oferta | Criterio «Monto»: **Cumple**. Con 25.00 dice **No evaluable** y lo explica: la regla no precisa si la base incluye los tributos. Con 24.99, **No cumple** |
| 11 | Abre la cronología del expediente y la bitácora | «Monto declarado R-0001» y «Monto corregido R-0001», **sin importes** |
| 12 | Prueba en el móvil (390 o 320 px) | Sin desplazamiento horizontal |

## Límites declarados (no son fallos)

- **PROC-08 no valida límites de autoridad por monto.** Falta la regla de comparación con el límite del cargo (OQ-OMA-01, decisión de la dueña).
- **PROC-10 evalúa por bandas** mientras no se precise si el «porcentaje de la oferta presentada» incluye tributos (OQ-OMA-02, jurídica).
- **PROC-09 (responsabilidad social) sigue bloqueado.** Faltan la U.T., el porcentaje vigente, el alcance y las exclusiones (OQ-PROC09-02..04). Este ciclo solo cerró la dependencia del monto.
- **Ofertas antiguas:** quedan «No declarado»; se completan solo si su evaluación sigue abierta. No se inventa ningún monto.
- **REP-03 suma la oferta adjudicada completa.** La adjudicación parcial sigue abierta (OBS-PROC08-PARCIAL-01).

`OWNER_ACCEPTED`: NO. Solo la dueña lo concede.
