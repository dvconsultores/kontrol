# Matriz de opciones (dos decisiones distintas)

## Decisión 1 · OBS-08: contrato de motor de las seis carreras

| Opción | Qué | Autoridad | Veredicto |
|---|---|---|---|
| B | marcador canónico `skipif(not PG, reason=… FR-046-115, conc-046; P21)` **solo** en las seis carreras; cobertura no concurrente intacta en SQLite | **existe**: FR-046-115, `conc-046-concurrent-version-delta.md` («PostgreSQL decide», G-CONC-046-06), docstring de `tests/concurrency.py`, P21, precedentes (`test_license_import_race.py`) | **implementada en este ciclo** (no resuelve el analizador) |
| D | marcar PostgreSQL-only toda la seguridad documental | ninguna; SQLite sí cubre lo no concurrente | descartada |
| sustituto SQLite de `carrera` | reescribir la carrera con `motor_para_hilos` | el contrato no lo pide y no sería fiel (sin bloqueo de índice) | descartada |

## Decisión 2 · ENTORNO-SIN-CLAMSCAN: analizador real en QA

| Opción | Fidelidad | Certifica SCAN_FAILED/CLEAN/EICAR | Corre las 6 carreras | Complejidad CI/local | Firmas | Tiempo | Imagen | Sin red | Mantenimiento | Autoridad hoy |
|---|---|---|---|---|---|---|---|---|---|---|
| **A · ClamAV real en el QA canónico** (paquete o prefijo de usuario + `KONTROL_CLAMSCAN_PATH`/`KONTROL_CLAMAV_DB`, juego de firmas fijado) | alta | sí (los tres caminos) | sí, en PostgreSQL | media (privilegios o guion de extracción; documentar) | `.cvd` versionados + política de refresco | +3–9 min backend; +~15 s por carga E2E | +~335 MB | con firmas versionadas, sí | media | **no** (CL-046-09 lo hace configurable; closeout lo usó sin guion) |
| B · mantener declarado | — | solo el falso seguro | no | nula | — | — | — | — | nula | sí (estado actual: `ENTORNO-SIN-CLAMSCAN` OPEN, skips con nombre) |
| C · falso `CLEAN` en capas no de integración + ClamAV real en una integración dedicada | media (riesgo de deriva falso↔real) | integración sí; unidad no | sí (integración) | media/alta (dos capas, dos mundos) | ídem A | menor en unidad | ídem A | ídem | alta | **no**: §159 y el closeout rechazan dobles como evidencia; no hay capa «unidad» separada en 046 |
| D · todo PostgreSQL-only | — | no resuelve el analizador | — | — | — | — | — | — | — | descartada |

`CAN_EXISTING_CONTRACT_RESOLVE_POLICY_WITHOUT_OWNER`: **decisión 1: YES** · **decisión 2: NO** → STOP para la 2.
