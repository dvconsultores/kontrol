# CNT-08 · Ficha de pantalla

## Rutas

| Pantalla | Ruta | Cómo se llega | Permiso |
|---|---|---|---|
| Expedientes contractuales | `/gobierno/expedientes-contractuales` | Menú › Gobierno · Contratos › **Expedientes contractuales** | `gobierno_contratos:view` |
| Expediente contractual | `/gobierno/contratos/:contratoId/expediente` | Desde la lista, o desde la ficha del contrato formalizado › enlace **Expediente contractual** | `gobierno_contratos:view` |

## Expedientes contractuales (lista)

- **Filtros:** código, expediente de contratación, contratista, tipo de instrumento, vigencia, supervisor, desde y hasta. Botones «Buscar» y «Limpiar».
- **Columnas:**
  - contrato (enlace), contratista, objeto;
  - monto vigente, vigencia, supervisor;
  - expediente de contratación y fecha de formalización;
  - último paquete y su verificación;
  - última actuación.
- **Paginación:** 25 por página, con «Anterior», «Siguiente» y «Mostrando X–Y de Z».

## Expediente contractual

- Es de solo lectura; cada acción se hace en la pantalla dueña.
- Navegación interna a 14 secciones:

| N.º | Sección | Contenido |
|---|---|---|
| 1 | Resumen | Monto y plazo originales y vigentes, vigencia, supervisor, cobertura y ejecución |
| 2 | Origen de contratación | Expediente PROC-03 y oferta adjudicada |
| 3 | Adjudicación | Decisión, acto y cargo |
| 4 | Presupuesto | CDP, asignaciones, compromisos, control y una nota sin efectos |
| 5 | Instrumento contractual | Condiciones originales frente a vigentes |
| 6 | Garantías | Instrumentos PROC-10 y sus eventos |
| 7 | Modificaciones | Historial de CNT-02 |
| 8 | Supervisión | Vigente, programada, historia y consulta por fecha |
| 9 | Ejecución | Fuentes futuras con mensaje honesto, sin decir nunca «no hubo» |
| 10 | Actos y documentos | Actos DOC-02 e índice documental con descarga por la autoridad |
| 11 | Cronología | Filtros por proceso y fechas, paginada |
| 12 | Auditoría | Requiere `gobierno_auditoria:view` |
| 13 | Integridad | Botón «Comprobar huellas» |
| 14 | Exportaciones | Generar con propósito, lista de paquetes, descarga y verificación por subida |

- No se muestra ningún UUID como dato principal; las huellas van abreviadas, con el valor completo en `title`.
- Las tablas desplazables son regiones enfocables con `aria-label`.
- Funciona a 1280, 390 y 320 px sin desbordamiento horizontal.

## Ficha del contrato (CNT-01)

En un contrato formalizado se añade el enlace **Expediente contractual**, junto a «Modificaciones (n)».
