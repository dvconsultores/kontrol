# CIERRE · BUD-08 compromiso presupuestario (2026-11-15)

```text
ENTRY=efcf4b2  CODE=6da5b20 (sin merge: origin/develop no avanzó)
ALEMBIC: 0112_gov_bud06_certificacion -> 0113_gov_bud08_compromiso   ALEMBIC_HEAD_COUNT=1
BUD-08=OWNER_UAT_READY (10/10, REPORTING NOT_APPLICABLE)   GOV-BUD-012 PASS
CANONICAL_GATE_UNIVERSE=1342   N/A 71 -> 72   APLICABLES 1271 -> 1270   GATES_REMOVED=0
GOV_GATES_PASSED 359 -> 369   OWNER_UAT_READY 35 -> 36 de 122   OWNER_ACCEPTED=0
DEEPSEEK_CALLS=9 (tope 8; 9.ª autorizada por la dueña, solo este ciclo)   61.465 in / 55.752 out · USD 0,0752
COMPROMISO_WITHOUT_CERTIFICATE=0  EDITABLE_BALANCE=0  BUD07/09/10/11_IMPLEMENTED=0
CLAUDE_SEMANTIC_*_WRITTEN=0   SNAT_TOUCHED=0  PRODUCTION_TOUCHED=0  SECRET_EXPOSURE=0
```

## Pruebas

| Prueba | Resultado |
|---|---|
| PG test_gov_bud08: vectores A–J, consumo parcial y total, sobregiro, concurrencia, SoD, autoridad, límite y moneda, soporte, anulación total, CDP en uso, inmutabilidad, aislamiento, MFA | 13/13 |
| PG dirigida (BUD-01..06 y fijaciones) | 217 passed |
| PG completa con analizador, una vez | 5510 passed / 37 failed / 18 skipped (entrada: 5498 / 36 / 18) |
| Fallo nuevo `test_iso_barridos::test_barrido_cabecera_manipulada` | 403 MODULE_NOT_ENTITLED en lugar de 404 COMPANY_NOT_FOUND en las 4 rutas GET. Corregido por C9 |
| Reverificación tras C9: test_iso_barridos, BUD-08 y BUD-06 | 26/26 |
| mypy | 157, igual que a la entrada |
| ruff (ficheros del ciclo) | limpio |
| Vitest con Node 22 | 2036/2036 (entrada 2030) |
| tsc, eslint, build | limpios |
| E2E gobierno-presupuesto-compromiso (sin reintentos) | 1/1 |
| Familia E2E de presupuesto | 5/5 |
| Axe | 1280, 390 y 320 px sin violaciones serias |
| Alembic en base nueva | upgrade, downgrade a 0112 y upgrade; una sola cabeza |

**Los 36 rojos restantes** coinciden uno a uno con la línea base reproducida en un worktree de efcf4b2. NEW_BACKEND_FAILURES=0 tras C9.

## Fórmula y reglas verificadas

- DISPONIBLE = CRÉDITO − Σ REMANENTE(CDP vigentes) − Σ COMPROMISOS vigentes. Cada monto se descuenta una sola vez.
- Situación derivada del CDP: DISPONIBLE, PARCIALMENTE_CONSUMIDA o AGOTADA.
- Un CDP con consumo no se anula: 409 GOV_BUDGET_CERTIFICATE_IN_USE.
- Compromiso CP-AAAA-NNNN, VIGENTE→ANULADO, solo anulación total con motivo. Triggers PG de inmutabilidad.
- Autoridad: COMPROMETER×PRESUPUESTO (ORG-03/04/06/07), con límite por operación en la misma moneda y sin conversión.
- SoD (CTL-01): quien certifica no compromete; responde 409 GOV_SOD_CONFLICT y queda en auditoría.
- Permiso `gobierno_presupuesto:commit` SENSITIVE (MFA).

## UAT

- Pila sin Docker desde el HEAD publicado 6da5b20: frontend en el puerto 16373 (backend 19200, central 19210). PILA UAT LISTA; HTTP 200.
- Humo UAT HUMO-UAT-01: 1/1. OWNER_UAT_ACCESSIBLE=YES.
- Siguen vivas las pilas 15873, 15973, 16073, 16173 y 16273.
- Credenciales: no se registran.

## Observaciones abiertas

- **OBS-BUD08-VES-VED** (decisión de la dueña). ORG-03 limita las monedas de competencia a VES/USD/EUR, y la moneda funcional por defecto del ente es VED. Un ente en VED no puede comprometer contra un límite monetario: el bloqueo es seguro por defecto y no hay conversión. Hay que decidir si se añade VED a ORG-03 o si se normaliza.
- OBS-BUD34-E2E-PARALELO sigue abierta. Es anterior a este ciclo.

## Siguiente

BUD-09 (causado) o BUD-10 (modificaciones), según dependencias. BUD-07 (precompromiso o reserva) está bloqueado por N37.
