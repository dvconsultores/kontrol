# CIERRE · BUD-01 + BUD-02 (2026-11-13)

```text
ENTRY=9dba4d8  FINAL=4b251a5 (+ commit de documentos)  ALEMBIC_HEAD=0107_gov_bud01_ejercicio (encadenada tras 0106_open_supply_by_warehouse de P2)
D_GOV_02=CLOSED A/1/1/1   HARDCODED_ONAPRE_CODES=0   FULL_FORMULATION_V1=0   PRECOMMITMENT_DEFAULT_ENABLED=0
BUD-01=OWNER_UAT_READY (10/10)   BUD-02=10/11 (REPORTS: consulta en pantalla sin exportación; decisión de la dueña)
GOV_GATES 289 -> 309 / 1275   OWNER_UAT_READY 28 -> 29 / 122   OWNER_ACCEPTED=0
```

## Pruebas

| Prueba | Resultado |
|---|---|
| PG enfocada (BUD + catálogo + N9 + 12 constantes) | 110/110 |
| PG completa (antes del merge con P2) | 5391 passed / 48 failed |
| mypy | 157 = entrada |
| ruff | limpio |
| Vitest con Node 22 (tras el merge) | 1985/1985 |
| tsc, eslint, build | limpios |
| E2E gobierno-presupuesto (Chrome, sin reintentos) | 1/1 y 2/2 con 4 workers |
| Axe | 1280, 390 y 320 px sin violaciones serias |
| Alembic en PG | fresh, downgrade y upgrade correctos; una sola cabeza |
| Humo UAT | 1/1, incluye «Ejercicios presupuestarios» |

**Los 48 rojos de la PG completa:**

- 36 son los mismos de la entrada (30 de pg_dump por entorno, QA_PGDUMP_ENV_DEBT).
- 12 eran constantes fijadas (cabeza, recuentos de MFA y catálogo de permisos). Se atribuyeron en un worktree de 9dba4d8, se corrigieron con C9/C10 y hoy pasan: NEW_BACKEND_FAILURES=0.

## UAT

- Pila sin Docker: `qa/e2e-run.py --orden` desde el HEAD publicado 4b251a5, frontend en el puerto 15973.
- La pila de REP-03 (15873) sigue viva.
- Credenciales: no se registran.

## Decisiones de diseño tomadas por Claude (no materiales)

- **PDD-BUD12-01:** contrato de estados LOPPM. RECONDUCIDO → APROBADO se difiere a BUD-05.
- **PDD-BUD12-02:** reconducción definitiva como dato calculado (art. 236).
- **PDD-BUD12-03:** fotografía canónica con huella sha256.
- **MFA:** según el patrón real de TRE-02: approve y close en SENSITIVE (exigen MFA); view y manage en STANDARD.

## Pendiente para la dueña

- **BUD-02 REPORTS:** reclasificar como NOT_APPLICABLE (GOV-BUD-002 no pide reporte; REP-01/BUD-13 son los reportes presupuestarios), o pedir una exportación CSV del clasificador.
