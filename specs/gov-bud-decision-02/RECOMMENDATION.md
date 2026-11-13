# RECOMMENDATION · D-GOV-02 (de Claude; **no equivale a aprobación**)

```text
CLAUDE_RECOMMENDED_OPTION=A (presupuesto aprobado + ejecución completa; formulación en una fase posterior)
UNLOCK_VALUE=5 YES + 3 PARTIAL de los 11 que citan D-GOV-02; 11 P0 alcanzables con la cadena BUD-01..06, 08, 10..12 y REQ-02
RISKS=ver abajo
```

## WHY: los 10 criterios del encargo

| # | Criterio | A |
|---|---|---|
| 1 | Cumplir el alcance v1.0 | El IR §15 plantea exactamente esta alternativa como forma válida de arrancar. Todos los P0 de ejecución (GOV-BUD-008..017) quedan en el alcance |
| 2 | Presupuesto antes del gasto | Sí: aprobado → disponibilidad → compromiso (LOPPM 242: ningún gasto sin previsión) |
| 3 | Desbloquear la mayor cantidad de P0 | 6 P0 directos (4 YES y 2 PARTIAL) + 5 P0 aguas abajo. B no desbloquea más hoy, porque su parte adicional sigue esperando N08 y N37 |
| 4 | No construir un SIGECOF completo | Sin formulación, formularios ONAPRE ni contabilidad |
| 5 | No cerrar la arquitectura futura | La formulación entra después como versiones previas del mismo presupuesto |
| 6 | Parametrización municipal | Niveles programáticos, límites de traspaso y rectificación, y precompromiso, por ente y ejercicio |
| 7 | Catálogos versionados | Clasificador por ejercicio con procedencia (edición, fecha y documento), sin precargar |
| 8 | Exactitud monetaria | `NUMERIC` / `Decimal`, sin redondeos compensados |
| 9 | Auditoría histórica | Ledger append-only; aprobado inmutable; cada modificación con su acto (CTL-02, DOC-02, DOC-08) |
| 10 | Nada de Naguanagua como regla universal | Las reglas salen de la LOPPM (nacional). Lo de Naguanagua (ordenanza, límites) es dato |

## Riesgos

- **R1:** el catálogo N10 no está custodiado. Mitigación: lo importa el ente con procedencia (D02-B = 1). Si la dueña prefiere esperar la copia oficial (D02-B = 2), BUD-02 queda solo como modelo y el aprobado no puede cargarse hasta tenerla.
- **R2:** la ordenanza de presupuesto de Naguanagua no está en custodia. Bajo A no bloquea la construcción, porque es dato del ente. Sí bloquea la **prueba de la dueña con datos reales**: la UAT usa datos sintéticos.
- **R3:** el asiento contable del causado depende de D-GOV-04 y N36. El momento presupuestario se registra igual.
- **R4:** el «pagado» espera a TRE-04 (PAGADOR UNAVAILABLE_UNTIL_GOV_TRE_004). El ledger lo prevé, pero no lo inventa.
