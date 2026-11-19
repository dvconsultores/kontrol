# TRE-04 · Humo UAT (TRE-04-ACCESSIBLE-01, 2026-11-19)

- **Commit:** `ff647fd` (publicado en `origin/develop`), cabeza `0128_gov_tre04_pago`.
- **Cambio en el humo** (dentro del ciclo, escrito por DeepSeek):
  - capacidad `gobierno_pagos:view` añadida al usuario sintético de consulta;
  - 2 pantallas añadidas a `PANTALLAS`:
    - `/gobierno/tesoreria/pagos` → h1 «Pagos»;
    - `/gobierno/tesoreria/politicas-pago` → h1 «Políticas de pago».
  - Con las de CTL-09 que trajo P2, el humo tiene 36 entradas. El título de la prueba sigue diciendo «catorce» (texto histórico, sin efecto).
- **Recorrido** (HUMO-UAT-01, proyecto `humo-uat`, fuera de la canónica):
  1. login real del usuario sintético;
  2. empresa D1;
  3. clic en el enlace del menú lateral;
  4. ruta esperada;
  5. h1 exacto;
  6. sin «Sin acceso» y sin «El módulo de Gobierno no está habilitado».
  - Un estado vacío es válido.
  - Al terminar, se retira el rol en el `finally`.
  - No toca el MFA de `admin` ni de `admintenant`.

## Corridas

| Corrida | Árbol | Resultado |
|---|---|---|
| `r20261119t023238…` (efímera) | WIP sobre `b3e980e` | 1/1, limpieza LIMPIA |
| `r20261119t155030…` (efímera) | árbol fusionado con CTL-09 (= `ff647fd`) | 1/1, limpieza LIMPIA |
| `r20261119t155324p578265ne55ab9…` (pila de prueba de la dueña, `--orden` con espera) | worktree de `ff647fd` | 1/1 (`humo rc=0`) |

## Pila de prueba de la dueña

- **Mecanismo:** sin Docker. Worktree `uat/wt-ff647fd` con `qa/e2e-run.py --con-analizador --orden`, que deja una base efímera propia, migrada y sembrada.
  - Puertos: frontend 17173, backend 19920, autoridad central 19930.
  - No había otra pila UAT viva; no se tocaron recursos ajenos.
- **Sin login:** `/login` → 200. `GET /api/v1/gobierno/tesoreria/pagos` y `GET …/politicas-pago` sin sesión → 401 (directo y a través de Vite).
- **Acceso de la dueña:** UAT_CREDENTIAL_HANDOFF = LOCAL_SECURE_FILE, con permisos 600. No se imprime ni entra en Git, y se borra al detener la pila.
- **Parada:** crear el fichero de parada de la pila. El arnés borra la base y libera los puertos.

TRE04_SMOKE_SCREEN_PAYMENTS = PASS · TRE04_SMOKE_SCREEN_POLICIES = PASS · OWNER_UAT_READY = YES · OWNER_UAT_ACCESSIBLE = YES · OWNER_ACCEPTED = NO (solo la dueña).
