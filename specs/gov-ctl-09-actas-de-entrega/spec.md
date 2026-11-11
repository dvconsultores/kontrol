# Spec · CTL-09 Actas de entrega por cambio de responsable o autoridad (GOV-CTL-011, P0)

**Actores:** quien entrega (saliente), quien recibe y la UAI. **Fuentes:** FUENTES.md. **Decisiones:** DECISIONES.md.

## Historias

- **US1 · Elaborar el acta.**
  - Se elige la ocupación saliente (ORG-04) y quien recibe, con la modalidad (art. 8 o art. 9), el motivo, el fundamento legal, el lugar y la fecha de corte.
  - El acta nace con su catálogo de anexos. Los generables vienen ya resueltos con datos del corte.
  - Los demás se resuelven con documentos o con la constancia del art. 19.
- **US2 · Suscribir.**
  - Con todos los anexos obligatorios resueltos, se suscribe: se fija la fecha y los errores u omisiones (art. 20).
  - El acta queda congelada, con huella, y el PDF se puede descargar.
  - Un dato posterior no cambia el acta suscrita.
- **US3 · Después de suscribir.**
  - Se registra la remisión a la UAI (art. 21).
  - El receptor añade observaciones (art. 22).
  - La UAI registra su informe de verificación (art. 23). No lo puede registrar quien suscribió ni el saliente o el receptor.
- **US4 · Consulta.** Listado con filtros (estado, texto, ámbito, fechas), ficha, historial e integridad (la huella del snapshot y la del PDF).

## Requisitos funcionales

| Id | Requisito |
|---|---|
| FR-01 | **Alta:** valida que la ocupación sea del ente y de un estado válido, que el receptor sea un funcionario del ente distinto del saliente y que, en la modalidad del art. 9, haya 2 testigos y un auditor. El corte cae dentro de la vigencia de la ocupación. Hay una sola acta por ocupación. |
| FR-02 | Edición de la cabecera solo en BORRADOR, con If-Match. |
| FR-03 | Resolución de los anexos (generado, documentos del acta o constancia) en BORRADOR. |
| FR-04 | **Suscribir** exige anexos completos y congela el snapshot y el PDF, que se descarga con sus bytes guardados. |
| FR-05 | Remisión a la UAI, observaciones del receptor y verificación con maker-checker. |
| FR-06 | Listado paginado (≤50) con filtros en el servidor. Aislamiento: otro ente responde 404. |
| FR-07 | Capacidades view, manage y verify. Auditoría en la bitácora. |
| FR-08 | **Interfaz:** menú Gobierno › Actas de entrega; listado, alta, ficha (cabecera, anexos con AdjuntosPanel, suscripción, después de la suscripción e historial); responsive a 1280/390/320 y WCAG 2.2 AA. |

## Fuera de alcance

- Inventario de bienes, plan operativo, presupuesto y contratos como datos propios. Esos anexos van por documento o constancia.
- El cálculo de plazos en días hábiles.
- La firma electrónica.
