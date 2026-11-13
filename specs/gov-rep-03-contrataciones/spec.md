# Spec · REP-03 Reporte de contrataciones (IR §12, P1)

## Fuentes

- IR v1.0 §12: «Contrataciones por modalidad, estado, unidad, proveedor, monto, desviaciones y tiempos.»
- Datos de procesos ya construidos:
  - PROC-03 expediente (modalidad declarada, tipo, unidad, estado, fecha de inicio, cierre, hitos con fecha prevista y real);
  - PROC-06 ofertas (oferente nombre y documento);
  - PROC-07 hitos de recepción y evaluación concluidas;
  - PROC-08 decisión VIGENTE (resultado y oferta adjudicada).

## Historia

Como **unidad contratante** o **Control Interno** quiero ver, para un período, cuántos expedientes de contratación hay
por modalidad, estado, tipo y unidad; quiénes ofertaron y a quién se adjudicó; cuánto tardó cada fase; y qué hitos se
cumplieron tarde o están vencidos. Así detecto cuellos de botella y desviaciones, y lo exporto.

## Requisitos

- **FR-01** Menú Gobierno › Contrataciones › «Reporte de contrataciones». Capacidad `gobierno_expedientes:view`.
- **FR-02** Período por **fecha de inicio** del expediente (`desde`, `hasta`, fecha de negocio).
  - Por defecto: del 1 de enero del año de negocio a hoy.
  - `desde > hasta` → 422 `INVALID_DATE_RANGE`.
- **FR-03** Totales del período y desglose por modalidad (incluida «Sin modalidad declarada»), estado, tipo de contratación y unidad.
- **FR-04** Proveedores: por oferente (documento y nombre), número de ofertas presentadas y de adjudicaciones VIGENTES. Orden: adjudicaciones desc, luego ofertas desc.
- **FR-05** Resultados de la decisión VIGENTE por expediente (ADJUDICADA, DESIERTA, TERMINADA, NULIDAD, Sin decisión).
- **FR-06** Tiempos en días naturales por expediente y promedio por modalidad:
  - inicio → recepción concluida;
  - recepción → evaluación concluida;
  - evaluación → decisión vigente;
  - inicio → cierre.

  Solo cuentan los expedientes con ambos extremos.
- **FR-07** Desviaciones de hitos (fecha prevista frente a fecha real), excluyendo NO_APLICA:
  - cumplidos a tiempo;
  - cumplidos con atraso (días);
  - vencidos sin cumplir (fecha prevista < hoy, PREVISTO; días de atraso a hoy).

  Lista de los 50 hitos con más atraso, con enlace al expediente.
- **FR-08** Monto: declarado «No disponible: las ofertas y las decisiones no registran monto (OBS-PROC08-MONTO-01)». No se calcula ni se estima.
- **FR-09** Exportación CSV de todas las secciones, auditada como `GOV_PROCUREMENT_REPORT_EXPORTED` (`filas`, `filtros`).
- **FR-10** Aislamiento por tenant y empresa. 403 sin capacidad o con el módulo apagado.

## Criterios de aceptación

- **AC-01** Un expediente del período aparece en los totales y en su modalidad, estado, tipo y unidad. Fuera del período no aparece.
- **AC-02** Un oferente con una oferta y una adjudicación VIGENTE muestra 1 oferta y 1 adjudicación. Una decisión ANULADA no cuenta.
- **AC-03** Un hito con fecha prevista pasada y PREVISTO aparece como vencido con sus días. Un CUMPLIDO tarde aparece con su atraso.
- **AC-04** La exportación descarga el CSV y registra el evento de auditoría.
- **AC-05** Otra empresa no ve nada del ente.
- **AC-06** La pantalla funciona a 1280, 390 y 320 px sin desbordamiento ni violaciones serias de Axe.

## Fuera de alcance

- Monto, que depende de OBS-PROC08-MONTO-01 y queda OPEN.
- Contratos (CNT-*).
- Alertas de fraccionamiento (REQ-04).
