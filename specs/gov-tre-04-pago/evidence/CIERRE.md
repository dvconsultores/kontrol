# TRE-04 · Cierre (2026-11-19)

- **Entrada:** `250227c`, cabeza `0125_gov_tre03_orden_pago`.
- **Salida:** cabeza `0127_gov_tre04_pago` (una sola), sobre `0126_gov_assignment_policy` de P2.
- **Paralelo (P2):** P2 publicó ORG-04 «política de asignación» (`3c27ad6`, `298f7df`, `b65d598`) durante la pausa.
  - Se integró con una fusión ordinaria (`b3e980e`) sobre el commit local de TRE-04 (`5787d3b`).
  - Hubo 6 conflictos, todos de fijaciones. Claude tomó el lado propio con git y movió la migración a `0127` con `git mv`; DeepSeek la reencadenó y sumó las fijaciones (INT).
  - ORG-04 cambia cómo se crean las ocupaciones; la resolución de autoridad (`exigir_autoridad_funcional`) no cambia, así que el checker de TRE-04 la reutiliza sin una versión paralela.
- **DeepSeek:** 33 llamadas (tope 12 → 20 → 28 → 32 → 33, ampliado por la dueña). Coste: 0,269202 USD. Ver `ATTEMPT_LOG.md`.

## Qué se entregó

- **Menú:** Gobierno · Tesorería › **Pagos** y **Políticas de pago**.
- **Pantallas:**
  - lista de pagos con filtros y CSV;
  - nuevo/editar pago, con el saldo de la orden;
  - detalle con regla congelada, autorizaciones «N de M», controles, documentos, historia y fronteras;
  - políticas de pago, con medios del ente, numeración y ficha con bandas, requisitos y documentos por etapa: activar, cerrar y crear nueva versión.
- **API:** 19 rutas nuevas bajo `/gobierno/tesoreria` y esquemas Pydantic propios. OpenAPI frente a `origin/develop`: 0 retiradas; solo cambian los 4 esquemas SoD y las 2 operaciones SoD que los usan, por el proceso `TRE-04`.
- **Migración:** `0127_gov_tre04_pago`, con 11 tablas y disparadores PG:
  - pago inmutable fuera de las transiciones;
  - REGISTRADO, RECHAZADO y ANULADO terminales;
  - aprobaciones, documentos e historias append-only.
- **Permisos:** `gobierno_pagos`, con view, manage, authorize, execute, cancel y policy. MFA (SENSITIVE) en authorize, execute, cancel y policy. Catálogo: 190 permisos.
- **Saldo único:** `proyeccion_obligaciones.py` es la única autoridad.
  - `montos_pagados` suma los pagos REGISTRADO;
  - `montos_en_tramite` suma PENDIENTE y AUTORIZADO;
  - `pendiente_de_pagar` y `disponible_para_pago` se derivan de ambos.
  - TRE-03 deja de calcular localmente.
- **Estados del pago:**
  - BORRADOR, que no consume y es editable;
  - PENDIENTE_AUTORIZACION y AUTORIZADO, que reservan;
  - REGISTRADO, que consume;
  - RECHAZADO y ANULADO, que liberan.
  - Solo el borrador se edita.
- **Maker-checker:** invariante de plataforma (N05 A; GOV-TRE-004), comparada por identidad (`usuarios_equivalentes`). Los checkers deben ser personas y cargos distintos.
- **Autoridad del checker:**
  - el cargo tiene la competencia del requisito de la banda en vigor;
  - autoridad funcional ORG-06/ORG-04;
  - límite de la competencia (TRE-09);
  - opcionalmente, que el cargo sea firmante autorizado de la cuenta TRE-01.
- **Bandas por monto:** contiguas desde 0, en la moneda de la política, con requisitos `{acción, materia, cantidad}` del catálogo ORG-03. Se exigen todas las aprobaciones, en cualquier orden.
- **Duplicados, en tres niveles:**
  1. idempotencia en crear y en registrar;
  2. referencia externa única por (ente, medio), si el medio lo exige, en el servicio y con índice único parcial;
  3. duplicado funcional (misma orden e importe): BLOQUEAR, o ADVERTIR con confirmación y motivo.
- **Concurrencia:** `FOR UPDATE` sobre la orden en enviar, aprobar, registrar y anular. Dos envíos de 70 sobre 100 nunca suman 140, y la prueba exige el código `GOV_PAYMENT_OVERPAYMENT`.
- **Moneda:** la del pago, la orden, la política y la cuenta deben coincidir. No hay conversión.
- **Fronteras:**
  - el registro es de un pago ejecutado externamente (`BANK_API_INTEGRATION=OUT_OF_SCOPE`);
  - TRE-05 retenciones, TRE-06 conciliación, TRE-07 reverso de pagos ejecutados y ACC contabilidad quedan fuera;
  - TRE-03: una orden con pagos registrados o en trámite no se anula (409).
- **CTL-01:** proceso `TRE-04` (TRE04_ORDENAR → TRE04_AUTORIZAR). Es un conflicto distinto del maker-checker, así que no se duplican eventos.
- **Auditoría (CTL-02):** 15 eventos `GOV_PAYMENT_*`. Catálogo: 628.
- **Cero hardcode institucional:** medios, bandas, cantidades, competencias, documentos, pago parcial, duplicado funcional y numeración son datos del ente. N37 queda representado como datos versionados con procedencia (`N37_VALIDATION.md`).

## Evidencia (árbol final)

| Puerta | Resultado |
|---|---|
| Pruebas TRE-04 (PG) | 32/32. También 32/32 con `autoflush=False`, la condición de producción (parche temporal del conftest, restaurado) |
| PG dirigida (§58: TRE-01..04, BUD-08/09, ORG-03/04/06, CTL-01/02, MFA, auditoría, delegación, OpenAPI, N9, alcance) | 742/742 |
| Integración con P2 (guardas, TRE-03/04 y ORG-04 de P2) | 371/371 |
| Mutaciones M1–M10 (§47), árbol final | 10/10 muertas |
| Vitest completo (Node 22) | 2500/2500 (226 ficheros) |
| tsc / eslint / build | 0 / 0 / OK |
| ruff / mypy | OK / 157 (línea base, 0 nuevos) |
| E2E `gobierno-pagos` (`r20261119t022815…`) | 7/7, limpieza LIMPIA: principal UI con maker y checker en sesiones distintas, Axe y responsive a 1280/390/320; maker-checker negativo; pagos múltiples 40/30/30; sobrepago 31 sobre 30; referencia duplicada; bandas por monto; versión congelada (prueba 07 sin `skip`: `r20261119t053354…`) |
| Regresión E2E TRE-03 + TRE-01 (`r20261119t024027…`) | 5/5, limpieza LIMPIA |
| Humo UAT (`r20261119t023238…`) | 1/1: 34 pantallas, con «Pagos» y «Políticas de pago» |
| Migración | Una cabeza (`0127`). La cadena 0126 → 0127 sube, baja y vuelve a subir en una base PG propia, ya borrada. CHECK de la base migrada = CHECK de los modelos |
| OpenAPI frente a origin | 19 rutas nuevas, 0 retiradas, 0 cambios inesperados |
| Auditoría de hardcode (§61) | PASS: 0 medios, 0 cargos, 0 cifras y 0 reglas bancarias en el código. `PAGAR × TESORERIA × 1` es el valor inicial editable de una banda nueva en la ficha (vocabulario ORG-03) |
| PG completa (§59) | Ver la sección «PG completa» |

## Defectos de producto que la E2E real destapó y que se corrigieron

1. **Monedas:** la migración inventaba `MONEDAS_LIMITE = ("EUR","USD","MXN")` (FIX-2). Las pruebas backend crean el esquema desde los modelos y no lo veían.
2. **Sesiones:** `get_session_factory()` usa `autoflush=False` y el mundo de pruebas usa autoflush. En producción, la autorización nunca se completaba y los documentos recién guardados no contaban (FIX-6).
3. **Contrato del detalle:** `controles` salía como lista y `preparador` como `null`, y la pantalla del borrador se rompía (FIX-7).
4. **Opciones:** `opciones_pago?order_id=` validaba todos los documentos de la empresa y respondía 422 (FIX-5).
5. **Diálogo de aprobar:** los requisitos pendientes leían `regla.bandas` en lugar de `regla.banda`, así que el diálogo no tenía opciones (VT-r2).

## Deudas y observaciones

- **OBS-TEST-AUTOFLUSH-01** (transversal, fuera del alcance de TRE-04): `tests/conftest_multicompany.py` crea sesiones con autoflush y producción no. Cualquier módulo que consulte tras un `db.add` sin `flush` pasa las pruebas y falla en uso real. Se recomienda alinear la fábrica de pruebas con la de producción en un ciclo propio.
- **OBS-TRE04-ARNES-01:** el título del humo sigue diciendo «catorce pantallas» (recorre 34). Heredado y fuera de alcance.
- **SOD-WARN-MODE-01:** heredada; solo BLOCK.

## DAG

- **`DIRECTLY_UNLOCKED`** (pasan a BUILDABLE_NOW):
  - TRE-05 (conserva su puerta legal N38);
  - TRE-06, TRE-07, TRE-08 y TRE-10;
  - CNT-05 y BUD-12.
- **`TRANSITIVELY_UNLOCKED`:** ninguno.
  - REP-06 espera a TRE-06; REP-01 a BUD-10; ACC-05 a ACC-02; PROC-12 a REQ-01, PROC-01 y PROC-04.
  - INT-02 sigue EXTERNAL_INTEGRATION_PENDING.

## Métricas

- `OWNER_UAT_READY`: 46 → **47** de 122 (38,52 %).
- Puertas de la matriz: 474 → **485** de 1268.
- `OWNER_ACCEPTED=NO`: solo lo concede la dueña.
