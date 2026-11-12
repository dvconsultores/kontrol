# Spec · REP-10 Reporte de control interno (IR §12, P1)

## Historia

Como **Control Interno** quiero ver, para un período, en una sola pantalla del menú de Gobierno, los conflictos de
segregación de funciones bloqueados, los rechazos por identidad institucional, los cierres bloqueados por controles
materiales y el estado de los hallazgos con sus acciones correctivas (en especial las vencidas), y exportarlo, para
vigilar el sistema de control interno sin recorrer cuatro módulos.

## Requisitos

- **FR-01** Menú Gobierno › «Reporte de control interno»; capacidad `gobierno_auditoria:view`.
- **FR-02** Filtro de período (`desde`, `hasta`, fecha de negocio); por defecto 1 de enero del año de negocio → hoy;
  `desde > hasta` → 422 `INVALID_DATE_RANGE`.
- **FR-03** Conflictos SoD del período: total, desglose por regla (código, nombre, proceso) y los 50 más recientes
  (fecha, usuario, regla, proceso, acción intentada, acción previa, enlace a la bitácora).
- **FR-04** Bloqueos de identidad institucional del período: total, desglose por motivo (etiqueta humana) y los 50 más
  recientes (fecha, usuario, motivo, enlace).
- **FR-05** Bloqueos de cierre del período: total, desglose por política y acción de cierre, y los 50 más recientes
  (fecha, usuario, política, acción, controles pendientes, enlace).
- **FR-06** Hallazgos (estado actual): conteo por estado y por riesgo; acciones correctivas por estado; lista de
  acciones vencidas (regla R14) con hallazgo, acción, cargo y unidad responsables, fecha objetivo, avance y días de
  atraso; enlace al hallazgo. Requiere además `gobierno_hallazgos:view`; si falta, la sección lo dice.
- **FR-07** Overrides y operaciones duplicadas: declaradas con su motivo (PDD-REP10-05).
- **FR-08** Exportar CSV con las secciones y el período; auditado `GOV_INTERNAL_CONTROL_REPORT_EXPORTED`.
- **FR-09** Aislamiento por ente (tenant y empresa); sin capacidad → 403; módulo apagado → 403.

## Criterios de aceptación

- **AC-01** Un conflicto SoD bloqueado en el período aparece en la sección y en el total; fuera del período no.
- **AC-02** Una acción correctiva con fecha objetivo pasada y no completada aparece como vencida con sus días de atraso.
- **AC-03** Un usuario con `gobierno_auditoria:view` sin `gobierno_hallazgos:view` ve las secciones de eventos y la de
  hallazgos como «sin permiso», sin datos de hallazgos.
- **AC-04** Otra empresa no ve los eventos ni los hallazgos del ente.
- **AC-05** La exportación descarga un CSV y deja un evento de auditoría con el número de filas y los filtros.
- **AC-06** La pantalla funciona a 1280, 390 y 320 px sin desbordamiento y sin violaciones serias de Axe.

## Fuera de alcance

Overrides (no existen por diseño), operaciones duplicadas (sin pagos), alertas automáticas (CTL-07).
