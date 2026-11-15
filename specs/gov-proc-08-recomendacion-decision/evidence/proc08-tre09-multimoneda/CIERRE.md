# CIERRE · delta X08 PROC-08 × TRE-09 multimoneda (2026-11-15)

```text
ENTRY=945bec7  CODE=d6bd284  MERGE_P2=851b136 (origin 0ccdab7, CNT-01)  FIX_INTEGRACION=2b06a6a
ROUTING_PATH=B (CNT-01 no publicado al entrar; P2 lo publicó durante el ciclo)
ALEMBIC: 0114_gov_tre09_tasas -> 0115_gov_cnt01_contratos (P2) -> 0116_gov_proc08_conversion   ALEMBIC_HEAD_COUNT=1
PROC08_CROSS_CURRENCY=COMPLETE   FUNCTIONAL_GAP_CLOSED=1   PROCESS_ROW_COUNT_CHANGE=0
GOV_GATES_PASSED 389 (379 + 10 de CNT-01 por P2; P1 +0)   OWNER_UAT_READY 38 de 122 (37 + CNT-01 por P2; P1 +0)   OWNER_ACCEPTED=0
DEEPSEEK_CALLS=7 (tope 8)   23.727 in / 20.185 out · USD 0,027773   OWNER_EXCEPTION_USED=0
RATE_SELECTION=APROBADA con max(fecha_efectiva) <= acto.fecha   VED->VES no es FX   NEW_VED_WRITES=0
P1_TOUCH_CNT01=0 (solo se devolvió la etiqueta MONEDA_DISTINTA que CNT-01 lee)   CLAUDE_SEMANTIC_*_WRITTEN=0
SNAT_TOUCHED=0  PRODUCTION_TOUCHED=0  SECRET_EXPOSURE=0
```

## Qué cambia para el usuario

En Contrataciones › expediente › «Recomendación y decisión», si la oferta y el límite del cargo que firma el acto (ORG-03 APROBAR×CONTRATACIONES) están en monedas distintas:

- el control usa la tasa oficial BCV **aprobada** en TRE-09 vigente a la fecha del acto;
- compara en VES exactos, sin redondeo;
- muestra la tasa, la fecha, la fuente y los dos equivalentes.

Si no hay tasa aprobada, la adjudicación se bloquea con «Sin tasa oficial aprobada» (422 `GOV_OFFICIAL_RATE_REQUIRED`) y remite a Tesorería › Tasas oficiales. La decisión emitida guarda la conversión como instantánea inmutable y la ficha la muestra como «Conversión de autoridad de DEC-NN». Con la misma moneda no se consulta ninguna tasa.

## Pruebas

| Prueba | Resultado |
|---|---|
| PG test_gov_proc08_multimoneda (sin tasa, tasa anulada en carrera, vector exacto 1000.01 USD × 36.123456789012, dos monedas extranjeras, misma moneda, vista previa, tasa sustituida, adjudicación concurrente, aislamiento) | 9/9 |
| PG dirigida antes de la fusión (multimoneda, límite AAL, decisión, recomendación, TRE-09) | 46/46 |
| PG completa con analizador, una vez (antes de la fusión) | 5487 / 83 / 18. 36 = línea base; 47 por la ventana de medianoche de Caracas (la corrida empezó a las 23:50 −04). Reejecutadas: 45/47 sueltas y el módulo DOC-02 completo 36/36 (sus 2 dependen del orden del módulo). **NEW_BACKEND_FAILURES=0** |
| PG dirigida tras la fusión (PROC-08, CNT-01, TRE-09, cabezas, ISO, catálogo de auditoría, MFA, delegación) | 224 passed; 6 CNT-01 rojas por `MONEDA_DISTINTA` (regresión de fusión) → C7 → CNT-01 + PROC-08 34/34; las otras 2 (n10, runner) son línea base |
| E2E gobierno-decision + gobierno-contratos, árbol integrado, sin reintentos | 2/2 |
| Vitest con Node 22, árbol integrado | 2064/2064 |
| tsc, eslint, build | limpios |
| mypy | 157, igual que a la entrada |
| ruff | limpio |
| Alembic en base nueva (integrado) | upgrade, downgrade a 0115_gov_cnt01_contratos, upgrade; una sola cabeza 0116 |
| OpenAPI | sin cambios (las respuestas no tienen response_model) |
| Axe | panel de control y ficha a 1280, 390 y 320 px sin violaciones serias nuevas |

## Concurrencia

- Tasa sustituida tras la vista previa: el emitir reevalúa con la tasa vigente.
- Tasa anulada antes del commit: bloquea.
- Adjudicación concurrente: una sola decisión.
- Límite cambiado: se evalúa la competencia vigente en el momento de emitir.

La instantánea queda protegida por el guard `kontrol_gov_decision_guard` de PostgreSQL, que compara la fila completa.

## Integración con P2

Durante el ciclo, P2 publicó CNT-01 con la migración 0115. La integración fue una fusión ordinaria, sin rebase:

- la migración de P1 se reencadenó a 0116;
- `evaluar_limite` conserva la lógica multimoneda;
- `clasificar_monto` y CNT-01 quedan intactos;
- la regresión de etiqueta se corrigió con C7 (DeepSeek, una línea).

El firmante de CNT-01 sigue bloqueando cuando las monedas son distintas: es una decisión de P2 (OBS-CNT01-FX-01, abierta para P2).

## Observaciones

- OBS-CAT-NOTREADY-01: **CERRADA** (delta marginal; filas PROC-03/06/07/08/10).
- OBS-SUITE-MEDIANOCHE-01 (nueva, entorno): una PG completa que cruza la medianoche de Caracas produce falsos rojos de fecha. Hay que lanzarla fuera de 20:00–24:00 −04 o atribuir con reejecución.
- OBS-CNT01-FX-01 (nueva, P2): CNT-01 no usa TRE-09 para el límite del firmante.

## UAT

- La pila sin Docker se levantó desde el HEAD publicado 81f0d7c, con el árbol integrado con CNT-01: frontend en 16573, backend en 19400 y central en 19410. PILA UAT LISTA.
- El humo HUMO-UAT-01 pasó 1/1. OWNER_UAT_ACCESSIBLE=YES.
- Siguen vivas las pilas 15873 a 16473. La pila de P2 (8000/5173) no se tocó.
- Tarjeta: `OWNER_UAT_CARD.md`. Las credenciales no se registran.
