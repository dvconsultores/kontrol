# Tarjeta de prueba de la dueña · Límite monetario de la autoridad (PROC-08)

- **Dónde:** Menú › Gobierno › Expedientes de contratación › un expediente › sección **Decisión**.
- **Quién:** un usuario con «Decisión: ver» y «Decisión: decidir» (pide MFA).
- **Qué demuestra:** el límite de un cargo **no es informativo**. KONTROL impide adjudicar por encima del límite y no permite saltarse el bloqueo; con una autoridad suficiente, sí se adjudica.

## Preparación (datos sintéticos, una vez)

1. En **Gobierno › Cargos**, deja dos cargos con la competencia «Aprobar · Contrataciones»:
   - **Cargo A**, con límite **50000.00 USD**;
   - **Cargo B**, **sin límite**.
2. En **Gobierno › Actos**, emite un acto particular «Aprobar · Contrataciones» de cada cargo.
3. En un expediente de concurso, recibe y abre las ofertas. En la oferta R-0001 declara el monto (PROC-06) en USD: 43103.46 + 6896.55 = **50000.01**.
4. Concluye la evaluación y emite la recomendación con R-0001 como opción 1.

## Pasos

| N.º | Acción | Resultado esperado |
|---|---|---|
| 1 | En Decisión, elige el acto del **Cargo A** y «Adjudicada» | Panel **Control del límite de autoridad**: 50000.01 · USD · Cargo A · 50000.00 USD · **Excede el límite**, con el mensaje en rojo |
| 2 | Escribe la motivación, pulsa «Registrar decisión» y después «Confirmar decisión» | Aviso: «El total declarado de la oferta (50000.01 USD) excede el límite de aprobación de Cargo A (50000.00 USD)…». No se registra nada y no hay opción de continuar |
| 3 | Pulsa «Cancelar» y elige el acto del **Cargo B** | El panel muestra «Sin límite» en el límite y en el resultado |
| 4 | Registra y confirma | «Decisión registrada»: DEC-01 Adjudicada, con el acto del Cargo B |
| 5 | Abre la cronología del expediente | Aparece la adjudicación |
| 6 | Abre la bitácora o la auditoría | «Adjudicación bloqueada por el límite de la autoridad», con acto, oferta y causal, **sin importes**. Después, «Decisión del procedimiento emitida» |
| 7 | (Opcional) Repite con un cargo cuyo límite esté en **EUR** | «No comparable por moneda». Al confirmar: «No puede verificarse el límite de esta autoridad porque la oferta y el límite están expresados en monedas diferentes.» |
| 8 | (Opcional) Una oferta **sin monto** con el Cargo A | «Monto no declarado» y bloqueo. Con el Cargo B se adjudica |
| 9 | (Opcional) Si el resultado es «Desierta», con cualquier cargo | No se compara ningún monto |
| 10 | Prueba en el móvil (390 o 320 px) | El panel se ve en una columna, sin desplazamiento horizontal |

## Límites declarados (no son fallos)

- **Sin conversión de moneda.** Para eso hace falta una autoridad de tasas con procedencia verificable (TRE-09 todavía no existe).
- **Adjudicación parcial:** no existe (OBS-PROC08-PARCIAL-01).
- **Base de la garantía de mantenimiento:** sigue abierta (OQ-OMA-02, jurídica).
- **PROC-09:** sigue bloqueado.
- **Ofertas antiguas sin monto:** solo las adjudica una autoridad sin límite, porque el monto ya no puede declararse después de concluir la evaluación.

`OWNER_ACCEPTED`: NO. Solo la dueña lo concede.
