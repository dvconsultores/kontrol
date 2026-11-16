# CNT-07 · Cierre (2026-11-16)

- **Entrada:** `e758ada9`, cabeza `0121_gov_cnt09_alertas`.
- **Salida:** cabeza `0122_gov_cnt07_terminacion` (una sola).
- **Paralelo:** P1 publicó MANUAL_LICENSE_ACTIVATION_AND_GOVERNMENT_PROFILE (`e3f84126`, 4 commits) y después OWNER-UAT-LICENSE-PROFILE-MENU-01 (`3cb3046a`, 3 commits). Se fusionó de forma ordinaria en `2e6c5504`, sin conflictos y sin migraciones de P1. En `main.py` se conservan su frontera `require_enterprise_surface` y el router de CNT-07, que queda fuera de ella, como los demás de Gobierno. Su `Sidebar` también se conserva. La segunda fusión (`26e23ecb`) llevó `approvals_router` detrás de la frontera ENTERPRISE, que CNT-07 no usa, y añadió `superficies.ts`, donde `gobierno` es GOVERNMENT. Tras ella pasaron la PG dirigida (CNT-07, licencias, OpenAPI, delegación y aprobaciones, 80/80), Vitest de perfil, menú, contratos y expediente (110/110), tsc, lint y ruff. Solape funcional 0.

## Qué se entregó

- **Terminación, resolución o rescisión** (`/gobierno/contratos/:id/terminacion`), solo para contratos formalizados.
- **Catálogo cerrado de figuras de la LCP art. 145**, leído de N11/N12/N25 (`FUENTES.md`). Ninguna figura es inventada; la caducidad, por ejemplo, responde 422.
  - Causales tasadas por figura; LCP 155.9 aplica solo a obras.
- **Requisitos verificados en el servidor:**
  - motivación (LOPA 9);
  - acto DOC-02 particular y eficaz, emitido con la competencia APROBAR × CONTRATACIONES;
  - notificación DOC-04 al contratista y a los garantes;
  - acto de apertura notificado en la rescisión imputable;
  - documento del acuerdo en el mutuo acuerdo;
  - conclusión autorizada;
  - ausencia de hechos de ejecución posteriores a la eficacia.
- **Fechas separadas:** la del acto, la de eficacia (la notificación DOC-04) y la del registro.
- **Una extinción por contrato**, garantizada por dos índices únicos parciales, `FOR UPDATE` e `If-Match`. Una vez formalizada, el trigger `kontrol_gov_contract_termination_guard` la hace inmutable.
- **Situación por fecha** (`situacion_contractual.py`): VIGENTE o EXTINGUIDO a partir de la fecha de eficacia. El contrato de CNT-01 no se reescribe y no existe un estado programado.
- **Guardas posteriores a la eficacia:**
  - CNT-03: iniciar, hito, entregable, entrega, valuación por `periodo_hasta` y terminación de obra;
  - CNT-04: designación;
  - CNT-02: formalizar una modificación.
- **Consecuencias informativas:**
  - monto vigente, lo valuado conformado, el saldo no ejecutado y el saldo de CNT-03;
  - la regla de la indemnización, sin calcularla (CONSECUENCIA_PENDIENTE_CNT06);
  - los compromisos de BUD-08 y las garantías de PROC-10.
  - No anula compromisos, no crea pagos y no ejecuta garantías.
- **Integraciones:**
  - CNT-09 deja de alertar sobre un contrato extinguido y reconcilia sus alertas;
  - en CNT-08, la sección 10 (15 en total), la cronología (TERMINACION_APERTURA y TERMINACION_FORMALIZADA), el JSON, el manifiesto y el paquete;
  - la ficha de CNT-01 muestra «Extinguido (figura)».
- **Reporte CSV** filtrado por figura y por fechas de eficacia.
- **Permiso `gobierno_contratos:terminate`** (SENSITIVE, con MFA).
- **Auditoría y SoD:** 5 eventos y 2 acciones SoD. Otra empresa recibe 404.

## Evidencia

| Puerta | Resultado |
|---|---|
| PG dirigida CNT-07 | 19/19 |
| Mutaciones | 8/8 muertas (M1–M8, `ATTEMPT_LOG.md`) |
| PG completa sobre el árbol final (`f154ff14`) | 5685 pruebas: 5662 pasan, 18 se saltan y 5 fallan. Cuatro son de la línea base (`n10` por `import_*.created_by`, `naive_datetime` y `spec019` ×2). La quinta, `test_delegation_ceiling::test_dc_t01`, contaba 174 permisos: el ciclo añade `terminate` y son 175. Se corrigió el recuento, como en CNT-03/04, y el fichero pasó 19/19 en PG. **NEW_BACKEND_FAILURES=0** tras la corrección |
| PG completa sobre el árbol final convergido (`2e6c5504`, con P1) | 5709 pruebas: 5686 pasan, 18 se saltan y 5 fallan. Cuatro son de la línea base. La quinta, `test_gov_tre02_seguridad::test_sg14`, fue `MFA_CODE_ALREADY_USED`: el arnés reutilizó un TOTP dentro de su ventana. Al repetir el fichero pasó 16/16 dos veces (OBS-PG-MFA-REPLAY-FLAKY-01). **NEW_BACKEND_FAILURES=0** |
| Árbol fusionado: tsc, lint, build, ruff y mypy | OK; mypy en su línea base (157) |
| Vitest completo (árbol fusionado) | 209 ficheros, 2310/2310 |
| Alembic (ida, vuelta a 0121 e ida) | OK; `heads` = `0122_gov_cnt07_terminacion`; n10 solo con las diferencias de la línea base `import_*` |
| Vitest completo (árbol final) | 203 ficheros, 2142/2142 |
| typecheck, lint y build | OK |
| E2E del sponsor CNT-07 | 1/1 (3,4 min): 15 pasos, negativos (duplicado 409, sin permiso, otra empresa 404), 1280/390/320 y Axe sin «serious» ni «critical» |
| E2E de regresión (contratos, modificaciones, expediente y terminación) | 4/4 antes de la fusión (16,2 min) y 4/4 sobre el árbol fusionado (17,1 min) |
| Humo de la UAT (pila nueva, `kuat`, licencia VALID) | 1/1 (3,6 min) en `2e6c5504` y 1/1 (3,6 min) en `26e23ecb`, el código final, ambos al primer intento. Antes, en `f154ff14`, hubo tres intentos fallidos: dos por errores del arnés de Claude (la variable de la base con otro nombre y la clave MFA borrada tras el alta) y uno por agotarse a los 15 s al subir un documento (`OBS-UAT-HUMO-CLAMAV-MARGEN-01`) |
| Catálogo de auditoría | 584 (+5 GOV_CONTRACT_TERMINATION_*) |

Las sondas E2E destaparon dos defectos de producto, corregidos en R5:

- la página pedía `formalize` en lugar de `terminate`;
- a 320 px había desbordamiento: un texto `sr-only` estaba dentro de un envoltorio con desplazamiento que no era `relative`.

## Deudas

- **OQ-CNT07-01 (nueva, abierta):**
  - no está decidido qué consecuencia tiene que el acto base se revoque o se declare nulo después de formalizar;
  - la pantalla lo señala con `role="alert"`, pero la actuación formalizada no cambia;
  - corresponde a la dueña.
- **C07-24 (observación):** el requisito DOCUMENTO_ACUERDO del mutuo acuerdo se exige en el servicio, pero no tiene una prueba PG propia.
- **OBS-PG-MFA-REPLAY-FLAKY-01** (nueva, no bloqueante): en la PG completa, un inicio de sesión de prueba puede reutilizar el código TOTP dentro de su ventana de 30 s. Ajena a CNT-07.
- **OBS-UAT-HUMO-CLAMAV-MARGEN-01** (nueva, no bloqueante):
  - en frío, un `clamscan` tarda unos 9 s en esta máquina y el `actionTimeout` del humo es de 15 s;
  - si dos cargas coinciden, la petición puede agotarse;
  - la E2E canónica no se vio afectada;
  - el arreglo sería un analizador residente o un margen mayor.
- **Heredadas sin absorber:**
  - OBS-E2E-COLAPSAR-320-01, OBS-DOC-SELLO-ENTREGA-01 y OBS-CNT01-DOC-SELLADO-01;
  - OQ-CNT02-01/02/03, OBS-CNT02-LIBERACION-01 y OBS-CNT01D-01/02;
  - OBS-VITEST-ASYNCBUTTON-FLAKY: no reapareció;
  - OBS_PROC08_PARCIAL_01 y OQ_OMA_02;
  - REQ01_BLOCKED_N37, CNT06_BLOCKED_N38, BUD09_BLOCKED_N36 y TRE04_BLOCKED_N37.

## DeepSeek

Ver `ATTEMPT_LOG.md`:

- 14 llamadas a `deepseek-v4-pro`: 13 con respuesta y 1 fallo de transporte;
- 6 reintentos semánticos;
- coste de $0,089646;
- la dueña amplió el tope dos veces (OWNER_EXCEPTION_USED=2), y quedó una llamada de reserva sin usar.

Claude no escribió producto, pruebas, E2E ni migración, salvo las siete correcciones documentadas.

## Estado

- **Producto:** OWNER_UAT_READY (11/11). Matriz: 44/122 listos para la dueña y 452/1268 puertas.
- **Pendiente:** OWNER_ACCEPTED=NO.
