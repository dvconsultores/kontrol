# OWNER UAT CARD · REP-10 «Reporte de control interno» (IR §12)

```
MÓDULO: Gobierno · REPORTE: REP-10 Control interno
ESTADO: OWNER_UAT_READY (pendiente de su prueba; OWNER_ACCEPTED solo lo da usted)
MENÚ:   Gobierno › Reporte de control interno (debajo de «Separación técnica y funcional»)
FUENTE: Ingeniería de Requerimientos v1.0 §12 «Reportes y tableros mínimos»

ROLES:
  - Ver el reporte y exportarlo: gobierno_auditoria:view (Control Interno; la misma capacidad de la bitácora).
  - Ver además la sección de hallazgos: gobierno_hallazgos:view. Sin ella, la sección lo indica y no muestra datos.

QUÉ ES Y QUÉ NO ES:
  Es un reporte de SOLO LECTURA que reúne, en un período, lo que ya registran otros procesos: conflictos de segregación de
  funciones bloqueados (CTL-01), rechazos por identidad institucional (ORG-06), cierres bloqueados por controles materiales
  (CTL-10) y hallazgos con sus acciones correctivas vencidas (CTL-06). No crea datos ni acusa a nadie.
  Overrides: «No aplica» (en Gobierno los controles de segregación solo bloquean; no hay excepción ni dispensa).
  Operaciones duplicadas: «No disponible» hasta que existan órdenes de pago y pagos.

USE SOLO DATOS SINTÉTICOS.
```

## Pasos

1. **Abrir.** Gobierno › Reporte de control interno.
   - Esperado: el período por defecto (1 de enero → hoy), cuatro tarjetas de totales y las secciones.
2. **Provocar un conflicto real (opcional).**
   - Con una regla de segregación activa (Gobierno › Segregación de funciones), intente editar un acto que usted mismo registró: la operación queda bloqueada.
   - Vuelva al reporte: el conflicto aparece en «Conflictos recientes», con la regla y la acción intentada.
3. **Ir al detalle.** Pulse «Ver en la bitácora» en una fila.
   - Esperado: se abre el evento en la bitácora institucional.
4. **Hallazgos.** Con hallazgos cuyas acciones correctivas tengan la fecha objetivo vencida, la tabla «Acciones vencidas» las lista con el responsable (cargo y unidad), el avance y los días de atraso. El enlace del hallazgo abre su ficha.
5. **Período.** Cambie «Desde» y «Hasta» y pulse «Aplicar».
   - Negativa: si «Desde» es posterior a «Hasta», el mensaje aparece junto al campo y los filtros siguen disponibles para corregirlo.
6. **Exportar.** Pulse «Exportar CSV».
   - Esperado: se descarga el archivo con todas las secciones del período y la exportación queda registrada en la bitácora.
7. **Permisos.** Con una cuenta que solo tenga `gobierno_auditoria:view`, la sección de hallazgos dice que no tiene permiso.
8. **Teléfono.** A 390 o 320 px la página se lee sin desplazamiento horizontal (las tablas se desplazan dentro de su caja).

## Lo que queda fuera (no es un defecto de esta entrega)

- **Operaciones duplicadas:** requieren Pagos (TRE-03 / TRE-04).
- **Overrides:** no existen por diseño.
- **Alertas automáticas de operaciones atípicas:** son CTL-07.
