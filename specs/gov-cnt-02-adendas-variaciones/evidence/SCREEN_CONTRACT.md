# CNT-02 · Ficha de pantalla

## Rutas

| Pantalla | Ruta | Cómo se llega |
|---|---|---|
| Modificaciones del contrato | `/gobierno/contratos/:contratoId/modificaciones` | Gobierno · Contratos › Contratos y órdenes › contrato formalizado › enlace **Modificaciones (n)** |
| Modificación (borrador o formalizada) | `/gobierno/contratos/:contratoId/modificaciones/:modificacionId` | Desde el historial («Ver ficha de …»), desde «Continuar el borrador» o al crear una nueva |

Las dos rutas requieren `gobierno_contratos:view` con alcance de empresa (`pantallas.ts`). El menú no cambia: la entrada sigue siendo «Contratos y órdenes».

## Modificaciones del contrato

- **Condiciones originales:** monto, plazo y huella del contrato, con el aviso «El contrato original no se modifica».
- **Condiciones vigentes al <fecha>:** monto, fin del plazo y la modificación que las fija, más las programadas.
- **Historial:** «Contrato original» seguido de cada instrumento con:
  - tipo y código, vigencia y fecha;
  - cambios de plazo, monto y condiciones;
  - motivo, autoridad, documento y huella;
  - cobertura adicional;
  - enlace a su ficha.
- **Nueva modificación** (con «gestionar»): selector del tipo y botón. Si ya hay un borrador, aparece «Continuar el borrador (…)». Si no se puede crear, se explica el motivo.

## Modificación

- **Cambio propuesto o formalizado:** monto vigente antes, monto efectivo nuevo, fin anterior y fin nuevo.
- **Datos de la modificación:**
  - tipo, fecha del instrumento y vigente desde;
  - motivo, nueva fecha de fin y cambio de monto;
  - condiciones modificadas, referencia y documento (elegido por título y versión).
- **Cobertura adicional:** lo requerido y lo asignado, y una tabla de las CDP elegibles con su saldo libre. No consume la CDP.
- **Compromisos presupuestarios:** solo en reducciones.
- **Formalización:**
  - pendientes y cargo firmante;
  - control del límite: resultado, mensaje y conversión TRE-09;
  - diálogo de confirmación.
- **Descartar borrador:** con confirmación.
- **Formalizada:** solo lectura, con código, documento («Ver documento»), firmante, límite, conversión y huella.
- No se muestra ningún UUID.
- Las tablas desplazables son regiones enfocables.
- Funciona a 1280, 390 y 320 px sin desbordamiento horizontal.

## Ficha del contrato (CNT-01)

En un contrato formalizado se añadieron:
- «Condiciones vigentes» y el enlace **Modificaciones (n)**;
- en el firmante, «Límite verificado con tasa oficial BCV: … VES frente a … VES» cuando hubo conversión.
