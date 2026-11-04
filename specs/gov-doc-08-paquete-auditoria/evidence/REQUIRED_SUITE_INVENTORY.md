# GOV-DOC-08 · inventario de suites exigidas

Creado al certificar (2026-11-04). Ejecución: Claude. Código y pruebas: DeepSeek, auditados por Claude.

| # | Suite | Orden / método | Resultado |
|---|---|---|---|
| 1 | Rama única y reconciliación | `git fetch`; ramas remotas; HEAD == origin | PASS · solo `develop`; HEAD == origin/develop == `6afd8d0` al empezar |
| 2 | Requisito de Gobierno | GOV-DOC-010 → spec §1–§10; prueba de bloqueo material | PASS · OD-DOC08-01..04 de la dueña; DOC01/DOC05/DOC06_REQUIRED = 0; MATERIAL_BLOCKER = 0 |
| 3 | Normativa | N18, N21, N22 (vía GOV-DOC-010) | PASS (diseño). Ninguna fija formato ni algoritmo. Sin afirmaciones de cumplimiento jurídico. Huella ≠ firma |
| 4 | RED primero | las 5 suites `tests/test_gov_doc08_*.py` sobre un worktree de `6afd8d0` | PASS (RED) · fallan al recolectar (`ImportError: service_paquetes`): el producto no existía |
| 5 | BD dirigida | migración 0071 subir / bajar / subir en base efímera | PASS · cabeza única `0071_gov_doc08_paquetes`; 2 tablas, 6 disparadores, 2 permisos; base eliminada |
| 6 | API dirigida | `tests/test_gov_doc08_{paquete,contenido,verificacion,alcance,integridad}.py` | PASS · 37/37 en PostgreSQL (DP-01..08, DC-01..08, DV-01..12, DA-01..09) |
| 7 | Inclusión de documentos (OD-DOC08-01/03) | DP-01, DA-01, DA-02, DC-04 | PASS · incluidos solo los legibles y entregables. Excluidos con motivo SIN_PERMISO o NO_DISPONIBLE, sin título. Copia exacta en el ZIP |
| 8 | Huellas y manifiesto | DC-01..DC-03, DC-08 | PASS · sha256 por fichero, del manifiesto y del ZIP. `SHA256SUMS` coherente. Huella registrada == huella descargada |
| 9 | Referencias cruzadas | DC-05, DC-07 | PASS · evento → objeto → documentos; documento → referencias; hallazgo → partidas, acciones y cargo. Detalle seguro sin `ip`, `user_agent` ni `session_id` |
| 10 | Verificación | DV-01..DV-12 | PASS · VÁLIDO (idéntico o recomprimido), INVÁLIDO (alterado, CRC, manifiesto, inesperado, no registrado, otra empresa), INCOMPLETO, VERSIÓN NO SOPORTADA. ZIP inseguro → 422 |
| 11 | Alcance y permisos | DA-01..DA-03, DP-08 | PASS · otra empresa u otro tenant → 404. Sin `generate` → 403. La descarga exige leer cada documento incluido (403 GOV_PACKAGE_DOCUMENTS_FORBIDDEN) |
| 12 | Inmutabilidad y almacenamiento | DA-04, DA-05 (PostgreSQL) | PASS · UPDATE y DELETE rechazados en paquetes y verificaciones. Almacenamiento alterado → 500 STORAGE_HASH_MISMATCH |
| 13 | Idempotencia y límites | DP-04, DP-05, DA-06 | PASS · la misma clave devuelve el mismo paquete; con otra muestra → 409. Límite superado → 422 GOV_PACKAGE_TOO_LARGE |
| 14 | Muestra inmutable | DA-07 | PASS · las partidas y la definición de la muestra no cambian al generar |
| 15 | Auditoría | catálogo 282 → 286 (CATB-03); espejo `catalogo.md` v2026-11-04.2; DP-07, DV-01, DV-09 | PASS · 4 acciones `gov-doc-08`. La clave `bytes`, prohibida, se renombró a `tamano_bytes` |
| 16 | Integración con CTL-04 | GX-02; `_objeto_desde_evento` | PASS · proceso «DOC-08 · Paquetes de auditoría» en la población; rastreo de `GovernmentAuditPackage` |
| 17 | Regla documental de la Spec 046 | `documents.service.puede_leer_archivo` + suites de documentos | PASS · 410 pasan / 1 saltada en PostgreSQL tras la refactorización. Misma regla para la descarga y para el paquete |
| 18 | Mutaciones de negocio | `mutar_ctl04.py` sobre `mutantes.json` | PASS · 17 mutantes: 17 KILLED (2 tras la segunda tanda), 0 equivalentes, 0 supervivientes (`MUTATIONS.md`) |
| 19 | PostgreSQL completo | `qa/suite_tiempos.py --motor postgres --con-analizador` | PASS · `r20261104t160619p3595683nec507a`: 4320 passed / 0 failed / 18 skipped · NORMAL, sin salto de reloj |
| 20 | SQLite completo | `qa/suite_tiempos.py --motor sqlite --con-analizador` | PASS · `r20261104t160604p3595532n08e19b`: 2789 passed / 0 failed / 1549 skipped · NORMAL |
| 21 | vitest · tsc · eslint · build | `node …` | PASS · vitest 1092/1092 (105 ficheros; CTL-06: 1066 → **+26**) · tsc 0 · eslint 0 · build correcto |
| 22 | ruff · mypy sin errores nuevos | `.venv/bin/ruff check .` · `.venv/bin/mypy app` | PASS · ruff limpio; mypy 154 = línea base |
| 23 | OpenAPI | contraste con `6afd8d0` | PASS · 7 operaciones nuevas, 18 esquemas nuevos, 0 cambiados, 0 retirados |
| 24 | Guarda de puertas de UI | `src/tests/gate-coverage.test.ts` | PASS · `VerificarPaquete` lleva su puerta (`gobierno_paquetes:view`) |
| 25 | E2E de DOC-08 ×3 + humo | `qa/e2e-run.py --con-analizador -- e2e/gobierno-paquetes.spec.ts e2e/uat-humo-gobierno.spec.ts --project=chromium --project=firefox --project=webkit --project=humo-uat` | PASS · `r20261104t155125p3409670n998830`: 10/10 (DOC8-E2E-01..03 × 3 navegadores + HUMO-UAT-01 con 9 pantallas); limpieza LIMPIA |
| 26 | Regresión de Gobierno ×3 + humo + base | `--orden e2e_y_base_doc08.sh` | PASS · `r20261104t165814p28831n96483e`: 150/150 (ORG-01/02/03/07, DOC-02/04, CTL-04, CTL-06, DOC-08) + humo 1/1 |
| 27 | Base tras la E2E | `scope_scan` + `integridad_doc08` (C, M, H1–H13, P1–P8) | PASS · sin violaciones de alcance; integridad 0 (6 paquetes, 6 verificaciones) |
| 28 | E2E canónica | `qa/e2e-run.py --con-analizador` | PASS · `r20261104t171630p80660nc24bc3`: 438/438 (435 de la línea base + 3 de DOC-08 en chromium); 0 reintentos; limpieza LIMPIA |
| 29 | Accesibilidad y responsive | axe a 1280, 768 y 320 en DOC8-E2E-03 (S1, S2 y S3) | PASS · sin violaciones serias; sin desbordamiento a 320 px |
| 30 | Ficha de pantallas | `DOC08_SCREEN_FORM_MATRIX.md` | PASS · 3 pantallas + panel + ficha de muestra; 2 formularios de escritura; 0 faltantes |
| 31 | Tarjeta UAT | `OWNER_UAT_CARD.md` | PASS · 10 pasos y negativas a–d |
| 32 | Humo UAT en la pila relanzada | HUMO-UAT-01 en 18100/15273/18110 | ver `UAT_SMOKE.md` |
| 33 | Convergencia | spec, plan y tasks contra el código | PASS · 0 hallazgos; `tasks.md` sin fase de convergencia nueva |
| 34 | Secretos | escaneo del diff | PASS · el diff no contiene contraseñas, claves, tokens, URL con credenciales ni rutas de usuario. El SNAT protegido queda fuera del commit |
| 35 | Residuos | corridas, puertos y bases efímeras | PASS · puertos E2E libres. Sin bases de corrida huérfanas (la única viva es la pila UAT previa, que se releva al cierre). El worktree RED se retira |

**Hallazgos de QA del ciclo, todos corregidos dentro del ciclo**
- Errores de encargo de Claude (10, detallados en `tasks.md`).
- Defectos del ejecutor, rechazados y reintentados dentro del máximo de 2.
- Un hueco real de prueba destapado por las mutaciones: DOC8-M17, reforzado.

Ninguno llegó al producto final.

**Deudas abiertas no tocadas:** FIND-CTL04-02 (LOW, preexistente), FIND-CTL04-03 (LOW, observación) y FIND-ORG07-02 (LOW).
