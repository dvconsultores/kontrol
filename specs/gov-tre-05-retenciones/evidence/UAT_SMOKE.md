# TRE-05 · Humo UAT (TRE-05-ACCESSIBLE-01, 2026-11-20)

- **Commit:** `291375a`, publicado en `origin/develop`. Cabeza de migración `0129_gov_tre05_retencion`.
- **Cambio en el humo** (dentro del ciclo, escrito por DeepSeek en la llamada 39):
  - capacidad `gobierno_retenciones:view` para el usuario sintético de consulta;
  - 2 pantallas nuevas en `PANTALLAS`: `/gobierno/tesoreria/retenciones` con h1 «Retenciones» y `/gobierno/tesoreria/politicas-retencion` con h1 «Políticas de retención».
- **Recorrido** (HUMO-UAT-01, proyecto `humo-uat`, fuera de la canónica):
  1. login real del usuario sintético;
  2. empresa D1;
  3. clic en el enlace del menú lateral;
  4. ruta esperada y h1 exacto;
  5. sin «Sin acceso».
  - Al terminar, retira el rol. No toca el MFA de `admin` ni de `admintenant`.

## Corridas

| Corrida | Árbol | Resultado |
|---|---|---|
| `r20261120t210601…` (efímera) | `3525609` (antes del arreglo SQLite) | 1/1, limpieza LIMPIA |
| pila de prueba de la dueña (`--orden` con espera) | worktree de `291375a` | 1/1 (`humo rc=0`) |

## Pila de prueba de la dueña

- **Mecanismo:** sin Docker. Worktree `uat/wt-291375a` con `qa/e2e-run.py --con-analizador --orden`, que deja una base efímera propia, migrada y sembrada.
  - Puertos: frontend 17273, backend 19940 y autoridad central 19950.
  - No había otra pila UAT viva y no se tocaron recursos ajenos.
- **Sin sesión:** `/login` responde 200. `GET /api/v1/gobierno/tesoreria/retenciones/liquidaciones` y `GET …/politicas` responden 401, tanto en directo como a través de Vite.
- **Acceso de la dueña:** `UAT_CREDENTIAL_HANDOFF=LOCAL_SECURE_FILE`, con permisos 600. No se imprime ni entra en Git, y se borra al detener la pila.
- **Parada:** crear el fichero de parada de la pila. El arnés borra la base y libera los puertos.

```ini
TRE05_SMOKE_SCREEN_WITHHOLDINGS=PASS
TRE05_SMOKE_SCREEN_POLICIES=PASS
OWNER_UAT_READY=YES
OWNER_UAT_ACCESSIBLE=YES
OWNER_ACCEPTED=NO   # solo la dueña
```
