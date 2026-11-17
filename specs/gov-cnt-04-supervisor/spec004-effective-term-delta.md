# Delta · CNT-04-EFFECTIVE-TERM-01 · plazo vigente en la supervisión (2026-11-16)

**Spec dueña:** `specs/gov-cnt-04-supervisor` (GOV-CNT-004).
**Origen:** defecto P0 de `GOV-PARAMETERIZATION-AUDIT-01`.
**Autorización:** el encargo «P2 — CNT-04-EFFECTIVE-TERM-01».
**Evidencia:** `evidence/effective-term/`.

## Defecto

`designar()` tomaba como límite superior de la fecha efectiva `GovernmentContract.fecha_fin`, que es el fin original de CNT-01. Ignoraba las prórrogas formalizadas en CNT-02.

Ejemplo: un contrato que termina el 30/06, con una prórroga formalizada hasta el 30/09, rechazaba una designación desde el 15/07.

La ficha de supervisión también exponía el fin original como `contrato.fecha_fin`.

## Causa raíz

- La proyección del plazo vigente ya existía: es `_vigente_a` de CNT-02, envuelta por `terminos_efectivos`. Sin embargo, vivía en `service_contratos_ejecucion` (CNT-03).
- CNT-03 importa `service_contratos_supervision` (`supervisor_en`). Si supervisión importaba ejecución, se formaba un ciclo de imports.
- Por eso CNT-04 leía el campo crudo del contrato.

## Requisitos

- **FR-ET-01:** una sola autoridad de términos contractuales efectivos. `terminos_efectivos` pasa a `service_contratos_terminos.py`, que depende solo del contrato, de las modificaciones formalizadas de CNT-02 y del reloj de negocio. CNT-03, CNT-04, CNT-07 y CNT-09 la importan de ahí. Su contrato no cambia: `monto`, `moneda`, `fecha_inicio`, `fecha_fin`, `fuente`, `modificacion` y `monto_original`.
- **FR-ET-02:** en `designar()`, `maximo = terminos_efectivos(db, contrato, desde)["fecha_fin"]`, o hoy si el contrato no tiene fin. El corte es la fecha efectiva `desde`, no hoy:
  - una prórroga programada que ya rige en `desde` cuenta;
  - una que aún no rige no cuenta;
  - los borradores no cuentan;
  - las modificaciones descartadas tampoco.
- **FR-ET-03:** el control del plazo no sustituye al de la situación jurídica. `exigir_vigente_en(desde)` (CNT-07) sigue aplicándose después del rango, y una terminación eficaz bloquea aunque haya prórroga.
- **FR-ET-04:** `GET …/supervision` expone, en `contrato`, `fecha_fin_original`, `fecha_fin_vigente`, `fuente_plazo` (`CNT01_ORIGINAL` | `CNT02_MODIFICACION`) y `modificacion_plazo`, todos calculados a hoy. La clave ambigua `fecha_fin` se retira; su único consumidor era la pantalla.
- **FR-ET-05:** la pantalla muestra «Plazo del contrato»:
  - «Fin del plazo vigente»;
  - «Según» («Contrato original» o «Modificación <código>»);
  - «Fin original», solo si difiere del vigente.

## Fuera de alcance

- La adopción del motor de procesos y del motor normativo.
- El refactor de hardcode de CNT-04. Su clasificación de auditoría sigue en REFACTOR_HARDCODED_POLICY.

## Restricciones

- Sin migración.
- Sin cambio de esquema.
- Sin código específico de ningún tenant.
- El plazo es un dato transaccional del contrato. Las reglas que permiten cambiarlo siguen siendo de CNT-02.

## Gate

| Comprobación | Resultado |
|---|---|
| BLOCKER | 0 |
| CRITICAL | 0 |
| CONTRADICTIONS | 0 |
| OWNER CONFLICT | 0 |
| MATERIAL OQ | 0 |
| UNKNOWN | 0 |
| Trazabilidad | FR-ET-01..05 → T001..T004, 100 % |

## Tareas

| Tarea | Ejecutor | Modelo | Sensible | Egreso | Ficheros | Prueba | Hecho cuando |
|---|---|---|---|---|---|---|---|
| T001 · autoridad neutral y uso en CNT-04 | DEEPSEEK | v4-pro | NO | SAFE | `service_contratos_terminos.py` (nuevo); `service_contratos_ejecucion.py`, `_alertas.py`, `_terminacion.py` y `_supervision.py` | PG de CNT-02/03/04/07/08/09 | Una sola `def terminos_efectivos`; ruff limpio |
| T002 · pruebas PG | DEEPSEEK | v4-pro | NO | SAFE | `tests/test_gov_cnt04_plazo_efectivo.py` | Las 9 pruebas | 9/9 y mutaciones muertas |
| T003 · pantalla y Vitest | DEEPSEEK | v4-pro | NO | SAFE | `contratos/api.ts`, `SupervisionContrato.tsx` y su prueba | Vitest | Casos original, prorrogado, sin fin, cargando y error |
| T004 · E2E de la dueña | DEEPSEEK | v4-pro | NO | SAFE | `e2e/gobierno-contratos-plazo-supervision.spec.ts`, `e2e/helpers/contratos.ts` | `qa/e2e-run.py --con-analizador` | 1/1, 1280/390/320, Axe |

`RETRY_MAX` es 2 en las cuatro tareas.
