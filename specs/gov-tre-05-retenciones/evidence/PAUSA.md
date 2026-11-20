# TRE-05 · Pausa 2 (2026-11-20)

**Decisión de la dueña:** pausar para trasladarse. El ciclo **no está publicado** (sin push). `OWNER_UAT_READY` está declarado en las matrices locales, pero falta la certificación final antes de publicarlo.

## Dónde está el trabajo

- **Worktree:** `~/.cache/kontrol-qa/ctl05` (desacoplado).
- **Commits locales sobre `9f2c3dd`** (ninguno publicado):
  - `c0d454f` — feat TRE-05;
  - `9f1cdb8` — fusión ordinaria con `origin/develop` (CTL-02 «autoridad canónica de procesos», P2, sin migración);
  - `2496901` — fix: proceso TRE-05 en `procesos.py` y rutas literales para QC-02;
  - el commit «docs» de esta pausa.
- **Migración:** `0129_gov_tre05_retencion` sobre `0128_gov_tre04_pago`; una cabeza. Sin publicar.
- **DeepSeek:** 46 de 47 llamadas (topes de la dueña: 40 → 43 → 45 → 47). Queda 1 de reserva. Detalle en `ATTEMPT_LOG.md`.

## Medido (en verde)

- **Backend:** TRE-05 31/31 en PG. CTL-02/CTL-04 40/40 en PG tras la fusión. ruff limpio.
- **Frontend:** tsc 0, eslint 0, Vitest completo **2567/2567** (Node 22), build OK.
- **E2E `gobierno-retenciones`:** **6/6 PASS**, con Axe a 1280/390/320 en las 4 pantallas. Corrida `r20261120t045932…`, anterior a la llamada 46 (rutas literales) y a la fusión con P2.
- **Mutaciones M1–M10:** **10/10 KILLED** (`~/.cache/kontrol-qa/herramientas/tre05/mutar.py`).
- **OpenAPI frente a origin:** 24 rutas nuevas, 0 retiradas. Solo cambian los 4 esquemas SoD y las 2 operaciones SoD, por el proceso TRE-05.
- **Hardcode:** PASS. Cero alícuotas, umbrales y conceptos en el código. `LEGAL_MANDATORY` aparece solo como guarda de rechazo. La migración solo siembra permisos.
- **Fixtures del frontend:** regenerados con `qa/fixtures_de_frontend.py`.
- **Documentación:**
  - matrices de completitud (48/122, 496/1268), reauditoría de bloqueados y catálogo UAT, sin commit hasta esta pausa;
  - `OWNER_UAT_CARD.md` A–H.

## Retoma 1 (2026-11-20, 13:27 -05) y pausa 3

- Sin cambios en `origin/develop` (`b726c1d`).
- PG QA estaba caída: se levantó con `start` y `mkdb ktest`.
- **Migración 0129** probada en una base PG propia (`kmig0129`, ya borrada): sube, baja a `0128_gov_tre04_pago` y vuelve a subir; una sola cabeza.
- La PG completa se relanzó y **se volvió a detener** por un nuevo traslado. Sigue pendiente.

## Pendiente al retomar, en orden

1. `git fetch`. Si P2 avanzó, fusión ordinaria y revisión de las migraciones (la 0129 no está publicada y puede reencadenarse).
2. **PG completa:** `qa/suite_tiempos.py --motor postgres --con-analizador`, con `KONTROL_PG_BIN_DIR`. Se detuvo a propósito por el traslado. Exigir NEW_FAILURE=0 y atribuir con un worktree de origin.
3. **E2E de retenciones** otra vez, tras la fusión y la llamada 46. Después, el **humo** `uat-humo-gobierno.spec.ts --project=humo-uat`.
4. Escribir `CIERRE.md`, `UAT_SMOKE.md` y la sección de estado en `tasks.md`.
5. Cerrar: commit, push a `origin/develop`, build-dev, pila UAT y humo ACCESSIBLE. Al final, el informe con `[FINAL ANALYZE]`.

## Antes de reanudar la PG

- PG QA: `bash qa/pg-provision.sh start` y `mkdb ktest`, desde `/home/maria/Projectos/Kontrol`.
- Ojo con el reloj tras el traslado (ver la memoria «Reloj, red y memoria del equipo»).
