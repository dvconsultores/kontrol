# CIERRE · REP-10 Reporte de control interno (IR §12) · 2026-11-12

```text
PRODUCT_STATUS=OWNER_UAT_READY  OWNER_UAT_ACCESSIBLE=YES  OWNER_ACCEPTED=NO
MENÚ=Gobierno › Reporte de control interno
MIGRACIÓN=0 (solo lectura; cabeza Alembic sin cambios: 0102_gov_ctl09_actas)
CAPACIDAD=gobierno_auditoria:view (+ gobierno_hallazgos:view para la sección de hallazgos); sin capacidad nueva
CATÁLOGO DE AUDITORÍA=486 -> 487 (GOV_INTERNAL_CONTROL_REPORT_EXPORTED)
DEEPSEEK_CALLS=10 (8 + 2 autorizadas por la dueña) · COSTE≈0,058 USD · CLAUDE_SEMANTIC_*_WRITTEN=0
COMMITS=57b1f9f (feature) + fd6bf6f (E2E y evidencia); HEAD == origin/develop
GOBIERNO=269/1275 compuertas · 26/122 OWNER_UAT_READY · 0 OWNER_ACCEPTED
```

## Selección

No quedaba ningún P0 elegible: todos dependen de presupuesto, contratos, pagos, contabilidad, bienes, almacén, calendario o fuente legal.

- **CNT-01:** exige monto (OBS-PROC08-MONTO-01 OPEN) y fuente presupuestaria (BUD BLOCKED).
- **PROC-11:** le faltan 3 de los 5 roles.

Entre los P1, REP-10 consolida cuatro procesos reales (CTL-01, ORG-06, CTL-10 y CTL-06). REP-09 se descartó porque duplica casi por completo el listado de CTL-05.

## Pruebas

| Comprobación | Resultado |
|---|---|
| PG REP-10 (rp01..rp10) + catálogo + instantáneas | 23/23 |
| ruff / mypy | limpio / 154 = línea base Enterprise (0 nuevos) |
| Vitest completo (Node 22) | 1942/1942 (+8) |
| tsc, eslint, build | verde |
| E2E REP-10 aislada | 1/1, repetida 3/3 y 6/6 con 6 workers junto a CTL-06 y CTL-03 |
| E2E canónica | mismo conjunto rojo que la línea base y las inestables por carga ya clasificadas en CTL-09; la roja de REP-10 (carrera en el paso responsive) quedó corregida con C7 y verificada bajo carga |
| PG completa con analizador | 20 rojas, todas preexistentes en `3cf7ed0` (ver abajo): `NEW_BACKEND_FAILURES=0` |
| OpenAPI | solo altas: `/gobierno/control-interno/reporte` y `/reporte.csv` |
| UAT | HUMO-UAT-01 1/1 en el commit publicado, HTTP 200 en http://localhost:15773/ |

**Las 20 rojas de la PG completa, todas preexistentes:**
- 6 de la línea base conocida: spec019_receipt ×2, runner de integridad, N10, pip check y guardia de datetime.
- 14 de PROC-08/PROC-10, que fallan igual en `3cf7ed0`. El ayudante `tests/proc08_ayudantes.py` envía la fecha del acto en UTC, y entre las 20:00 y las 24:00 de Caracas esa fecha es «futura» para la API. Se registra como **OBS-PROC08-TZ-01** (prueba dependiente de la hora; no se absorbe).

## Producto

- **Contenido:** conflictos SoD con regla, proceso, acción intentada y acción previa; bloqueos de identidad con su motivo; bloqueos de cierre con política, acción y controles pendientes; hallazgos por estado y riesgo; acciones correctivas vencidas según R14, con responsable y días de atraso.
- **Enlaces:** a la bitácora y al hallazgo.
- **Overrides y operaciones duplicadas:** declarados con su motivo.
- **Exportación:** CSV completo del período, auditado.
- **Período:** por fecha de negocio. Con un 422, los filtros y los datos anteriores siguen visibles y el mensaje aparece junto a «Desde».

## Observaciones abiertas

- **OBS-PROC08-TZ-01 (nueva, MEDIUM):** pruebas PG de PROC-08/PROC-10 dependientes de la hora (fecha UTC frente a fecha de negocio).
- **OBS-REP10-HALLAZGOS-01 (LOW):** el motivo sin permiso muestra el código de capacidad (`gobierno_hallazgos:view`) entre paréntesis. Conviene un texto solo humano.
- Se mantienen PROC09=BLOCKED, OBS-PROC08-MONTO-01, OBS-PROC08-PARCIAL-01, OBS-CTL09-PLAZOS-01 y OBS-CTL09-A11Y-01 (LOW; REP-10 no tocó la ficha de CTL-09).
