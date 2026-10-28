# OBS-TIME-01 · medición del reloj del anfitrión (solo lectura) · 2026-10-28

## Medición

```
date      : 2026-10-28 00:55:39 CET +0100
date -u   : 2026-10-27 23:55:39
TZ        : (sin definir) · /etc/localtime → Europe/Amsterdam · NTPSynchronized=yes
Python    : now(UTC)=2026-10-27T23:55:39Z · Caracas=2026-10-27T19:55:39-04:00 · tzdata del sistema 2026e · paquete tzdata: ausente
PG de QA  : arrancado con -c timezone=UTC · SHOW TimeZone = UTC
run_id    : qa/e2e_nombres.nuevo_run_id → UTC por diseño
```

## Desvíos registrados en qa/backend-runs (desvío = pared − monotónico)

| run_id | desvío (s) | salto | anomalía de duración |
|---|---:|---|---|
| r20261015t052736p1571081n164db4 | 25917.4 | True | SIN_REFERENCIA |
| r20261015t130044p1720481n48bb06 | 1550.7 | True | SIN_REFERENCIA |
| r20261021t000203p1340791n7dd88f | 9398.9 | True | NORMAL |
| r20261021t215524p1084935nb1ba71 | 2571.8 | True | NORMAL |
| r20261024t105229p1123760n322c4a | 3414.9 | True | NORMAL |
| r20261027t003429p2502723na7e941 | 1359.9 | True | NORMAL |

Corrida 02B (`r20261027t003429…`): pared 3431,0 s, monotónico 2071,1 s, desvío 1359,9 s; el muestreador (intervalo 30 s) registró **70** muestras ≈ 2100 s monotónicos → el proceso no corrió durante el desvío: **suspensión del equipo** (CLOCK_MONOTONIC no cuenta la suspensión).

## Clasificación

| Observación | Clase | Acción |
|---|---|---|
| run_id «≈22:00» frente a `date` «22:52» (02E) | EXPLAINED: el run_id es UTC y `date`/vitest, CET (+1 h) | Ninguna |
| Desvíos de 1360–25 917 s con `salto=true` | HOST_ONLY: suspensiones | Ninguna sobre el equipo (sin sudo, sin tocar NTP) |
| El resumen de la suite decía «anomalía: NORMAL» sin mencionar el salto | **QA_CLASSIFIER_DEFECT** | Corregido (C03-T07): el resumen dice `salto de reloj: SÍ/NO` y, con salto, que la duración monotónica sigue siendo válida; pruebas O12-21/22, rojo 2/22 → verde 22/22 |

**OBS_TIME_01_STATUS = QA_CLASSIFIER_DEFECT (corregido) · impacto de producto: ninguno.** Las pruebas del producto no dependen del reloj del anfitrión: congelan el instante en `app.shared.clock.instante_actual` o lo pasan por parámetro.
