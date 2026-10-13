# Frecuencia histórica de la firma «estado de empresa no determinable»

| Registro | Valor |
|---|---|
| Corridas en `qa/e2e-runs/` | 105 |
| `TOTAL_OCCURRENCES` | **3** pruebas en **1** corrida (`r20261013t151632…`, 2026-10-13) |
| `SUITES` | `approvals.spec.ts:496`, `empresa-helper.spec.ts:28`, `empresa-helper.spec.ts:45` |
| `SAME_SIGNATURE` | 3/3 (mismo diagnóstico `activar=0 compuerta=0`, con `activa`/`desactivar` ya en 1 en el diagnóstico) |
| `DIFFERENT_ROOT_CAUSES` | 0 entre estas tres. No se mezclan con `ERR_NETWORK_CHANGED`, página en blanco ni módulo abortado (E2E-PANTALLA-SIN-PINTAR), que tienen otras firmas |
| Contexto | túnel VPN presente; tres proyectos de navegador en paralelo; sin errores en `backend.log` |
