# CTL-07 · Contrato de pantalla

- **Ruta:** `/gobierno/control/alertas`. Menú: **Gobierno → Alertas de operaciones atípicas**. Requisito: `gobierno_alertas:view`.

## Contenido, de arriba abajo

1. Cabecera: migas «Gobierno / Alertas de operaciones atípicas» y título.
2. Aviso (`role="note"`): «Una alerta es una señal para revisar; no es una acusación ni una conclusión.»
3. **Tipos de alerta** (tabla con nombre accesible «Tipos de alerta»):
   - columnas Tipo, Detección, Pendientes y Total;
   - «Disponible» o «No disponible»;
   - si no está disponible, el motivo y «Requiere: …».
4. **Filtros:** «Tipo» (Todos + los 3 disponibles) y «Estado» (Todas, Pendientes, Revisadas).
5. **Alertas** (lista con nombre accesible «Alertas»). Cada alerta muestra:
   - tipo, fecha y título, con el detalle debajo;
   - sujetos como «Etiqueta: valor»;
   - insignia «Pendiente» o «Revisada».
   - Si está revisada: «Revisada por X el F: Resultado. Observación», y «Ya no se detecta» si aplica.
   - Si queda pendiente y el usuario tiene `gobierno_alertas:review`: botón «Revisar» que abre un formulario en línea con:
     - grupo de opciones «Resultado» (Sin observación, Requiere seguimiento);
     - área «Observación» (10 a 2000 caracteres);
     - botones «Registrar revisión» y «Cancelar».
   - Con «Requiere seguimiento» revisada, enlace «Registrar hallazgo» a `/gobierno/hallazgos/nuevo`.
6. **Estados:** cargando, error con reintento, «Sin alertas» con los filtros aplicados.

## Reglas

- Sin UUID, sin JSON y sin códigos crudos; los códigos de tipo y de resultado siempre con etiqueta humana.
- Los errores del backend se muestran con su mensaje.
- Nada de color como único indicador.
