# CTL-09-DELIVERY-ACT-POLICY · Cierre

## PRODUCT COMPLETENESS GATE

- **WHERE_IS_IT_IN_MENU:**
  - Gobierno › «Políticas de actas» (nueva): lista, ficha, formulario, nueva versión, activar y cerrar;
  - Gobierno › «Actas de entrega» › «Nueva acta» (sección «Regla aplicada», aviso del art. 17 y testigos exigidos);
  - Gobierno › «Actas de entrega» › ficha del acta («Regla aplicada», «Anexos exigidos» con su fuente, «Responsables», «Plazos» y la regla congelada al suscribir).
- **WHAT_CAN_USER_DO:**
  - crear, editar, activar y cerrar políticas de actas con versiones e historia inmutable;
  - consultar el catálogo legal N34 (arts. 11 a 17, con fuente y vigencia);
  - declarar los supuestos de los arts. 12 a 17 para la entidad o para unidades concretas (OD-AE-01). Sin declaración solo rige el art. 11;
  - añadir requisitos documentales con su evidencia, exigir testigos en la entrega, fijar plazos internos (nunca mayores que el legal), definir el patrón de numeración con vista previa (por defecto AE-{ANIO}-{NUMERO:4}, OD-AE-04) y el código del cargo de máxima autoridad (D-AE-14);
  - levantar actas que exigen solo los anexos de la regla aplicable. Un ente municipal que no declaró el art. 17 ya no recibe A17 (defecto P0 corregido) y ve un aviso, sin automatismo (OD-AE-02);
  - resolver anexos con un documento o con la constancia del art. 19, ver a los responsables resueltos con ORG-04 y los plazos con su estado;
  - suscribir el acta: la regla queda congelada. Las actas previas conservan la regla HISTORICA, sin backfill.
- **OWNER_UAT_READY:** YES. La tarjeta está en `OWNER_UAT_CARD.md`.
- **PRODUCT_STATUS:** OWNER_UAT_READY · CURRENT_PRODUCT_DEFECT=NO en CTL-09 (antes YES, P0). OWNER_ACCEPTED=NO: solo la dueña lo concede.
- **MISSING_GATES:** ninguno del ciclo.

## Cambio

- **Migración:** `0127_gov_handover_policy` (sobre `0126_gov_assignment_policy`), sin backfill.
  - Tablas: `gov_handover_policies` (una sola VIGENTE por empresa, índice único parcial), `_bindings`, `_requirements`, `_deadlines` y `_history` (inmutable en PG).
  - En las actas: `policy_id`, `policy_version` y `regla`, protegidas por el disparador.
  - En los anexos: `origen`, `supuesto`, `fuente`, `evidencia`, `declaracion` y `document_type_id`.
  - Permisos `gobierno_actas:configure` (MFA estándar) y `gobierno_actas:activate` (MFA sensible).
- **Autoridad única:** `service_actas_regla.py` (DELIVERY_ACT_POLICY_AUTHORITIES=1). Crear, editar, anexos, suscripción, PDF, ficha y la ruta nueva `GET /gobierno/actas-entrega/regla` la consumen. Se eliminaron `ANEXOS_CATALOGO`, `ANEXOS_MUNICIPALES` y la inferencia por nivel.
- **ORG-04:** el saliente debe ejercer el día del corte, y la relación del receptor (SUCESOR o DESIGNADO) sale de la ocupación de cargos. No hay una segunda autoridad.
- **SoD:** sin cambios. Configurar y activar se separan por permisos (D-AE-12); CTL-01 sigue siendo la única autoridad de SoD.
- **Fuente normativa:** copia oficial de N34 custodiada en `requerimientos/gobierno/normativa-n34/` (SHA-256 en `N34_VALIDATION.md`).
- **Hardcode:** ZERO_INSTITUTIONAL_HARDCODE=1, NAGUANAGUA_SPECIFIC_CODE=0, HARDCODED_A17_GLOBAL=0 (ver `HARDCODE_AUDIT.md`).

## Evidencia

| Prueba | Resultado |
|---|---|
| PG del ciclo (`test_gov_ctl09_politica.py` y `test_gov_ctl09_actas.py`) | 22/22 |
| P0 reproducido | `test_p0_instituto_municipal_no_recibe_a17` falla contra `service_actas.py` de b65d5982 y pasa con el nuevo |
| Mutaciones M1–M10 | 10/10 muertas (ver `ATTEMPT_LOG.md`) |
| Migración | Una sola cabeza, `0127_gov_handover_policy`. Upgrade, downgrade y upgrade en PG, RC=0 |
| Vitest completo | 2498/2498 (227 ficheros) |
| typecheck · lint · build | OK |
| ruff | limpio |
| mypy | 157 de línea base; 0 en ficheros del ciclo |
| OpenAPI | Solo cambios del alcance: 11 rutas nuevas, ninguna inesperada; fixtures regeneradas |
| E2E `gobierno-actas-politica.spec.ts` (real, sin mocks) | 1/1. Cubre: política creada y activada, P0 (ente municipal sin art. 17), A17 aplicable que bloquea y luego deja suscribir, versión congelada y responsabilidad ORG-04. Axe 0 serious/critical en 1280, 390 y 320 |
| E2E de regresión de CTL-09 | 1/1 |
| Humo UAT (`--project=humo-uat`) | PASS, con «Políticas de actas» y «Políticas de asignación» |

### PG completa

Corrida de 22:33 (18/11) a 01:46 (19/11) −04, sobre b65d5982 más los cambios del ciclo: 5795 pasadas, 18 omitidas y 34 fallidas.

- **NEW_FAILURE (1), corregido:**
  - `test_uom_architecture::test_no_queda_unit_id_none_literal` señaló el literal `unit_id=None` en `service_actas_politicas.py`.
  - Corrección: `instantanea()` recibe `unit_id` como parámetro opcional y el detalle de la política no lo pasa para el ámbito ENTE. No se añadió ninguna exención a la guardia.
  - Repetición: la guardia, doc02, CTL-09 y las políticas dieron 69/69, y ruff quedó limpio.
- **BASELINE_FAILURE (4)**, los mismos que en el cierre de ORG-04, ajenos al ciclo, y fallan igual al repetirlos:
  - `test_n10_convergence` (`import_*.created_by`);
  - `test_naive_datetime_input` (`abierta_en` de PROC-07);
  - `test_spec019_receipt` ×2.
- **BASELINE_FAILURE por la franja horaria (29), deuda conocida GOV_TEST_UTC_DATE / OBS-PG-MIDNIGHT-CROSSING-01:**
  - la corrida pasó por la franja de 20:00 a 24:00 −04, en la que la fecha UTC y la local no coinciden;
  - mensajes: «La vigencia no puede empezar antes de hoy» (SoD de CTL-10, ORG-06, PROC-02/03/08/10/11, TRE-01/02/03) y validaciones de fecha (201 o 200 donde se esperaba 422);
  - `test_iso_barridos::test_barrido_cabecera_manipulada` (401 AUTH_INVALID_TOKEN, caducidad de sesión durante la franja) también pasa al repetirlo;
  - repetidos a las 01:46, con ambas fechas iguales: pasan todos. Los dos de `test_gov_doc02_actos`, que dependen del orden, pasan con el módulo completo (69/69 en la repetición conjunta);
  - ninguno toca código del ciclo.
- **ENVIRONMENT_FAILURE:** 0. Esta vez el catálogo de `ktest` no se dañó: 0 apariciones de `UniqueViolation` u `opclass` y 0 esquemas `t_*` al terminar. No se recurrió a OBS-PG-KTEST-CATALOG-DAMAGE-01.

## Integración con P1

- `git fetch`: `origin/develop` sigue en b65d5982, así que no hubo nada que fusionar.
- P1_P2_FUNCTIONAL_OVERLAP=0.

## SHAs

- Código del ciclo: 420592ab = FINAL_CODE_CERTIFIED_SHA (sin fusión: P1 no avanzó).
- FINAL_DOCUMENTATION_SHA es el commit que añade este documento.
- CODE_DIFF_BETWEEN_THEM=0: el commit de documentación solo toca `specs/` y `docs/roadmap/`.

## DeepSeek

- `deepseek-v4-pro`: 15 llamadas de un tope de 16 (OD-AE-05), 9 reintentos, 107.990 tokens de entrada y 94.550 de salida, $0,129234. OWNER_EXCEPTION_USED=0.
- El detalle, las reclasificaciones (T07 a Claude) y todo el trabajo de Claude, declarado, están en `ATTEMPT_LOG.md`.

## Auditoría de parametrización

- CTL-09 pasa de CURRENT_PRODUCT_DEFECT YES a NO, y de P0 a P1.
- Recuento: P0=2 (BUD-01 y BUD-05, sin defecto vigente), P1=30 y CURRENT_PRODUCT_DEFECTS=4 (ORG-07, BUD-02, CTL-02 y CTL-04, todos P1).
- FUTURE_ARCHITECTURE_REFACTOR=STILL_PENDING.
- NEXT_CANDIDATE: ORG-07, defecto vigente en la matriz de autoridad. Alternativa: BUD-01 o BUD-05, P0 por arquitectura.

## Deudas

**Nuevas:**

- OBS-AE-DISTRITAL-01: KONTROL no modela el nivel DISTRITAL; el art. 17 solo se admite en entes MUNICIPALES.
- OBS-AE-ART12-ANEXOS-01: los anexos del art. 12 remiten al Reglamento Nº 1 de la LOAFSP, que no está custodiado (MATERIAL_NORMATIVE_UNKNOWN). El ente los define como requisitos.
- OBS-AE-CALENDARIO-HABIL-01: los plazos legales en días hábiles son informativos mientras no exista un calendario hábil oficial (DOC-03).

**Heredadas (se conservan):**

- OBS-PG-KTEST-CATALOG-DAMAGE-01 (no se reprodujo en este ciclo)
- OBS-PG-MIDNIGHT-CROSSING-01 (se reprodujo, ver arriba)
- OBS-AP-AUTORIZACION-REFERENCIA-UNICA-01
- OBS-PROC02-SELF-ACTIVATION-CTL01-01
- OBS-CP-REGLA-VISIBLE-SOLO-EN-FORMULARIOS-01
- OBS-E2E-CNT01-REAUTH-300S-01
- OBS-PG-MFA-REPLAY-FLAKY-01
- OBS-UAT-HUMO-CLAMAV-MARGEN-01
