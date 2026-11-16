# Tarjeta de prueba de la dueña · CNT-09 Alertas de vencimientos

**Dónde está:**
- Menú › **Alertas** (la bandeja de siempre, con el filtro «Origen»);
- la ficha de cada contrato formalizado › sección «Alertas de vencimiento»;
- Menú › Gobierno · Contratos › **Alertas de vencimiento**, para el preaviso institucional.

**Qué hace y qué no:** la alerta informa. No aprueba, no prorroga, no conforma, no recibe, no paga y no cierra; tampoco cambia el contrato, el hito, el entregable ni la garantía. Las alertas se generan en cada ciclo del planificador.

| # | Paso | Resultado esperado |
|---|---|---|
| 1 | En un contrato formalizado e iniciado, registre un hito y un entregable con fecha de hoy | — |
| 2 | Espere el ciclo del planificador y abra Alertas; filtre por Origen «Hitos de contrato» | «El hito HIT-01 del contrato … vence hoy (…)», con la severidad «Advertencia» escrita |
| 3 | Pulse «Abrir origen» | Abre la ejecución del contrato |
| 4 | Abra la ficha del contrato | «Alertas de vencimiento» con «Alertas activas: 2», el hito y el entregable |
| 5 | Registre la entrega **sin** conformarla y espere el ciclo | La alerta del entregable sigue activa |
| 6 | Conforme la entrega con la cuenta del supervisor y espere el ciclo | La alerta del entregable pasa a «Resuelta» y no se borra |
| 7 | Registre la recepción parcial con el hito y espere el ciclo | La alerta del hito queda «Resuelta» y no hay activas |
| 8 | En Gobierno · Contratos › Alertas de vencimiento, active el preaviso de Contratos con N días (requiere configurar notificaciones) | «Preaviso guardado». Los contratos que venzan en N días o menos generan «vence el …» (Informativa) |
| 9 | Formalice una prórroga (CNT-02) | La alerta calculada con la fecha anterior queda «Resuelta»; la nueva fecha se evalúa con su propia ventana |
| 10 | Registre una garantía que venza en 15 días o menos | «La garantía … vence el …» (Advertencia), con la regla de PROC-10 |
| 11 | Renueve esa garantía | La alerta de la anterior queda «Resuelta» |
| 12 | Con una cuenta sin permiso de contratos | No ve las alertas de contratos en la bandeja |

**Reglas fijas:**
- sin preaviso configurado, contratos, hitos y entregables solo avisan el día del vencimiento y cuando ya vencieron;
- las garantías avisan desde 15 días antes;
- el plazo de firma en días hábiles no genera alertas, porque no hay calendario hábil institucional.

Credenciales: no se registran. La aceptación (OWNER_ACCEPTED) solo la da usted.
