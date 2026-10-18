# T09 · `qa/compose_qa.py` — guion de evidencia runtime de la composición (orquestado: Claude brief → DeepSeek código → Claude audita)
Objetivo: que la evidencia `OBS09_EXTERNAL_DOCKER_EVIDENCE` (R1) se obtenga con una sola orden en el equipo no productivo con
Docker: `python3 qa/compose_qa.py [--puerto 18000]` desde la raíz del repositorio en `6ed13d1` o posterior.
| Campo | Valor |
|---|---|
| TASK_ID | T09-COMPOSE-QA (+ subtareas T09b-PS-ARGS, T09c-MUTANTES tras reclasificación) |
| BRIEF | contrato cerrado por Claude: override de Compose aislado (`qa/compose.obs09.yaml`: base PostgreSQL efímera, nombres/red propios de la corrida, backend solo en loopback, clamd sin puertos), módulo con `Docker` inyectable, `esperar()` con plazo monotónico (único `sleep`), inspección de contenedores reales, `clamdscan --version`/PING/límites runtime, F01–F04 por el backend (sin reiniciarlo), limpieza en `finally`, bloque de evidencia saneado, `aprobado()` con todos los criterios de cierre; 14 pruebas con dobles (`DockerFalso`, `BackendFalso`) |
| ROUTES_ALLOWED | `qa/compose_qa.py`, `qa/compose.obs09.yaml`, `resources/backend/tests/test_compose_qa.py`, `.gitignore` (línea `qa/compose-runs/`), `docs/evidence/docker-validation-checklist.md` (párrafo «Automatizado») |
| ROUTES_FORBIDDEN | `resources/backend/app/**`, `compose.yaml`, `Dockerfile.*`, `deploy/**`, `.env*` |
| EGRESS_CHECK | ENV_FILES=0 SECRETS=0 PROD_URLS=0 TOKENS=0 PRIVATE_KEYS=0 REAL_PII=0 (todas las cadenas del override son sintéticas de QA y están marcadas como tales) |
| DEEPSEEK_CALL | 4 llamadas: intento 1 (`deepseek-v4-pro`, 10 155/16 092 tokens, $0,0184) · corrección 1 (`pro`, 18 111/15 657, $0,0215) · corrección 2 (`pro`, 8 262/5 859, $0,0086) · T09b (`flash`, 595/407, $0,0002) · T09c (`flash`, 1 936/1 739, $0,0007) → **$0,0494** |
| RETRY_COUNT | 2 (máximo) en T09; agotados → reclasificación en T09b (una línea del doble) y T09c (tres pruebas reforzadas) |
| AUDIT_RESULT | intento 1 REJECT (ruff ×7, límites de `clamd.conf` leídos por «=», pruebas con el doble sin envolver, `esperar` sin plazo monotónico) · corrección 1 REJECT (módulo limpio; el doble no casaba con `image inspect … --format`, `run --rm --entrypoint sh <tag>` ni con los argumentos de `compose` tras el override → 3 fallos y 3 cuelgues) · corrección 2 REJECT (una rama: `ps -q <servicio>` leído en `args[1]`) · T09b PASS · T09c PASS |
| APPLIED | sí, tal cual (sin retoques de Claude): 5 ficheros |
| CERTIFIED | ruff limpio · mypy limpio · 14/14 pruebas en 2,1 s · override YAML válido · `qa/compose-runs/` ignorado |
## Mutaciones sobre `qa/compose_qa.py` (GOOD→PASS, MUTATED→FAIL, RESTORED→PASS; guion `<scratch>/o9/t09m/mutar.py`)
| Id | Mutación | Detectada por |
|---|---|---|
| M-01 | `esperar()` deja de comprobar la condición tras vencer el plazo | cq2_11 (tras T09c) |
| M-02 | `esperar()` sin pausa entre sondeos | cq2_14 |
| M-03 | límites de clamd separados por «=» | cq2_06, cq2_13 |
| M-04 | 1M = 1 000 000 | cq2_07 |
| M-05 | el contrato de tamaño ignora `MaxFileSize` | cq2_07 |
| M-06 | puerto publicado de clamd nunca detectado | cq2_05 |
| M-07 | `CLAMD_INTERNAL_ONLY` ignora puertos | cq2_05 |
| M-08 | la limpieza no baja la composición | cq2_12, cq2_13 |
| M-09 | la limpieza no borra las imágenes efímeras | cq2_12, cq2_13 (tras T09c) |
| M-10 | sin Docker se construye igual | cq2_01 (la corrida ya no termina: fallo) |
| M-11 | sin cabecera `X-Kontrol-Company` | cq2_09, cq2_13 |
| M-12 | F03 sin parar clamd | cq2_08, cq2_13 |
| M-13 | reinicio del backend en la recuperación | cq2_08 |
| M-14 | `CLAMSCAN=1` leído como 0 | cq2_03 (tras T09c) |
| M-15 | montajes leídos de `Source` | cq2_04, cq2_13 |
| M-16 | cabeceras de sección con corchetes | cq2_10, cq2_14 |
**16/16 detectadas** (13 en la primera pasada; M-01, M-09 y M-14 tras reforzar las pruebas por T09c); restauración idéntica tras cada una.
