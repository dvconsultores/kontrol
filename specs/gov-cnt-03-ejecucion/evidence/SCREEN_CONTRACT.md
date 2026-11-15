# Contrato de pantalla · CNT-03

**Ruta:** `/gobierno/contratos/{id}/ejecucion`. Se llega desde el enlace «Ejecución del contrato» de la ficha CNT-01, solo con el contrato FORMALIZADO. En el catálogo de autoridad se registra como `gobierno_contratos:view`, con alcance empresa.

| Sección (h2, `section[aria-labelledby]`) | Contenido | Acciones (con `gobierno_contratos:execute`) |
|---|---|---|
| Resumen de la ejecución | Monto original y efectivo, valuado conformado y presentado, saldo, facturado, inicio, fin efectivo, supervisor, hitos cumplidos, entregables pendientes, estado y tipo | Descargar CSV |
| Inicio de la ejecución | Fecha, supervisor, acta y observación | Registrar inicio (solo el supervisor) |
| Hitos | Tabla HIT-NN con monto, %, obligatorio, cumplido · REC, valuado y facturado | Registrar hito; Anular (motivo) |
| Entregables | Tabla ENT-NN con situación y entregas ENT-NN/k | Registrar entregable; Registrar entrega; Conformar o Rechazar (supervisor) |
| Valuaciones | Tabla VAL-NN con período, monto, estado, acumulado y reparos | Presentar valuación; Conformar o Reparar (supervisor); Anular |
| Recepciones | Tabla REC-NN con tipo, hitos, supervisor, representante y fin de garantía | Acta de terminación (obras); Registrar recepción (PARCIAL, PROVISIONAL o DEFINITIVA según el flujo); Anular parcial |
| Facturas / cuentas vinculadas | Aviso «no genera causado…»; tabla FAC-NN | Vincular factura (supervisor); Anular |
| Cronología | Tabla de hechos ordenados | — |
| Cierre operativo | Fecha, aprobador, acta de aprobación, evaluación y supervisor | Cerrar ejecución |

- **Formularios:** FormField con un solo control y `htmlFor`. Cada formalización pasa por un ConfirmationDialog («Confirmar») y tiene MFA por la política SENSITIVE. El éxito se anuncia con `role="status"` y el error con `role="alert"`, mostrando el mensaje de la API.
- **Tablas:** cada una va dentro de `div role="region" tabIndex=0 class="relative overflow-x-auto"` con `caption` sr-only. `relative` es lo que impide que el sr-only desborde.
- **Responsive:** 1280, 390 y 320 px sin desbordamiento horizontal.
- **Accesibilidad:** Axe sin violaciones serias ni críticas, a 1280, 390 y 320 (E2E).
