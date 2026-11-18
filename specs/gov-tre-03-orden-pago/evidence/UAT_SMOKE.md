# TRE-03 · Humo UAT (TRE-03-ACCESSIBLE-01, 2026-11-18)

- **Commit:** `a9bae79` (publicado en `origin/develop`). Solo cambia `resources/frontend/e2e/uat-humo-gobierno.spec.ts` y la nota de ACCESSIBLE en la matriz. No cambian el producto, el backend ni las migraciones; la cabeza sigue en `0125_gov_tre03_orden_pago`.
- **Cambio en el humo** (DeepSeek, 1 llamada, 3/3 bloques aplicados tal cual):
  - capacidad `gobierno_ordenes_pago:view` añadida al usuario sintético de consulta;
  - 2 pantallas añadidas a `PANTALLAS`:
    - `/gobierno/tesoreria/ordenes-pago` → h1 «Órdenes de pago»;
    - `/gobierno/tesoreria/politicas-orden-pago` → h1 «Políticas de orden de pago».
  - El humo recorre ahora 32 pantallas (antes, 30).
- **Recorrido** (HUMO-UAT-01, proyecto `humo-uat`, fuera de la canónica):
  1. login real del usuario sintético;
  2. empresa D1;
  3. clic en el enlace del menú lateral;
  4. ruta esperada;
  5. h1 exacto;
  6. sin «Sin acceso» y sin «El módulo de Gobierno no está habilitado».
  - Un estado vacío es válido: no se crean órdenes ni políticas.
  - Al terminar, se retira el rol del usuario sintético en el `finally`.
  - No toca el MFA de `admin` ni de `admintenant`.
- **Por qué detecta la falta de acceso:** sin permiso, la lista de órdenes no pinta su h1 y la de políticas pinta «Sin acceso». Cualquiera de los dos casos hace fallar la aserción.

## Corridas

| Corrida | Árbol | Resultado |
|---|---|---|
| `r20261118t161454…` (efímera, `qa/e2e-run.py --con-analizador -- e2e/uat-humo-gobierno.spec.ts --project=humo-uat`) | WIP sobre `02d6b68` | 1/1, limpieza LIMPIA |
| `r20261118t161711…` (pila de prueba de la dueña, `--orden` con espera) | worktree de `a9bae79` | 1/1 (`humo rc=0`) |

## Pila de prueba de la dueña

- **Mecanismo:** sin Docker. Worktree `uat/wt-a9bae79` con `qa/e2e-run.py --con-analizador --orden`, que deja una base efímera propia, migrada y sembrada. Puertos: frontend 17073, backend 19900, autoridad central 19910.
- **Relevo:** las pilas anteriores cayeron con el reinicio de la estación. No había conexiones vivas que respetar.
- **Sin login:** `/login` → 200. `GET /api/v1/gobierno/tesoreria/politicas-orden-pago` y `GET …/ordenes-pago/configuracion` sin sesión → 401.
- **Acceso de la dueña:** UAT_CREDENTIAL_HANDOFF = LOCAL_SECURE_FILE, con permisos 600. No se imprime ni entra en Git, y se borra al detener la pila.
- **Parada:** crear el fichero de parada de la pila. El arnés borra la base y libera los puertos.

TRE03_SMOKE_SCREEN_ORDER_LIST = PASS · TRE03_SMOKE_SCREEN_POLICY_LIST = PASS · OWNER_UAT_READY = YES · OWNER_UAT_ACCESSIBLE = YES · OWNER_ACCEPTED = NO (solo la dueña).
