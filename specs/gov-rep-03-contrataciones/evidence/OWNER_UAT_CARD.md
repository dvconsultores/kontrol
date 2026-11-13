# OWNER UAT CARD · REP-03 «Reporte de contrataciones» (IR §12)

```
MÓDULO: Gobierno · CONTRATACIONES: REP-03 Reporte de contrataciones
MENÚ:   Gobierno › Contrataciones › Reporte de contrataciones (debajo de «Funciones incompatibles»)
ROL:    gobierno_expedientes:view (la misma capacidad que la consulta de expedientes)
QUÉ ES: un reporte de SOLO LECTURA sobre los expedientes reales (PROC-03), sus ofertas (PROC-06), la evaluación (PROC-07) y la
        decisión vigente (PROC-08). No crea ni modifica nada.
MONTO:  «No disponible»: las ofertas y las decisiones no registran monto (OBS-PROC08-MONTO-01). No se estima.
USE SOLO DATOS SINTÉTICOS.
```

## Pasos

1. **Abrir.** Gobierno › Contrataciones › Reporte de contrataciones.
   - Esperado: el período por defecto (1 de enero → hoy), el resumen (Expedientes, Abiertos, Cerrados, Descartados) y las secciones.
2. **Distribución.** Las tablas «Por modalidad», «Por estado», «Por tipo de contratación», «Por unidad» y «Resultado de la decisión» cuentan los expedientes con fecha de inicio en el período.
3. **Proveedores.** Si hay ofertas recibidas, la tabla muestra cada oferente con sus ofertas y adjudicaciones (solo la decisión vigente).
4. **Tiempos.** Días promedio por modalidad entre inicio, recepción, evaluación, decisión y cierre («—» si aún no hay datos).
5. **Desviaciones.**
   - Abra un expediente y agregue un hito con fecha prevista de ayer. Vuelva al reporte: el hito aparece como «Vencido» con 1 día de atraso, y el número del expediente enlaza a su ficha.
6. **Período.** Cambie «Desde» y «Hasta» y pulse «Aplicar».
   - Negativa: si «Desde» es posterior a «Hasta», el mensaje aparece junto al campo y los filtros siguen disponibles.
7. **Exportar.** Pulse «Exportar CSV».
   - Esperado: se descarga el archivo con todas las secciones y la exportación queda registrada en la bitácora.
8. **Teléfono.** A 390 o 320 px, la página se lee sin desplazamiento horizontal.

## Fuera de alcance

- **Monto:** OBS-PROC08-MONTO-01.
- **Contratos y alertas de fraccionamiento:** dependen de presupuesto y requisiciones, que no existen aún en Gobierno.
