# `/speckit.converge` — SPEC 047 · NOTIFICACIONES, TAREAS Y ALERTAS

> 2026-09-14, sobre `370e10a` más el cambio de la 047. PostgreSQL 16.2 (`pgserver`):
> `ENVIRONMENT_BASELINE_DEVIATION` declarada frente al objetivo 18.6.

## 1. Veredicto

**`SPEC047 — COMPLETE / CONVERGED`**

Las dos preguntas materiales se cerraron por decisión del owner (`clarifications.md` §4),
el planificador tiene ADR aprobado (`ADR-D0-015`) y todas las puertas del §103 tienen
evidencia de ejecución. Un defecto ajeno queda registrado con su dueña (§6).

## 2. Qué se construyó

| Pieza | Artefactos |
|---|---|
| Planificador de plataforma | `app/modules/scheduler/` (tick, registro de manejadores, orden `python -m app.modules.scheduler tick`), `kontrol.py scheduler-tick`, `scripts/scheduler/*.service/.timer`, `scripts/install-scheduler.sh` |
| Notificaciones, tareas y alertas | `app/modules/notifications/` (modelos, servicio, consumo de `approval_events`, recordatorios, escaladas, frontera de entrega, API) |
| Mensajes | `messages.py` (clave + parámetros, catálogo `es`, `en` DEFERRED) · `src/i18n/` |
| Esquema | `0057_spec047_notifications`: 13 tablas aditivas, permisos `notificaciones`, `tareas`, `alertas` |
| Frontend | campana en `Topbar`, centro, tareas, detalle, alertas, reglas y preferencias en `src/modules/notificaciones/` |
| QA | 6 ficheros `tests/test_spec047_*.py`, vitest, `e2e/notifications.spec.ts`, `qa/spec047-e2e-seed.py` |

Volumen frente a `370e10a`: 68 ficheros · +7 936 / −532 (backend 2 949, pruebas de
backend 1 530, frontend 2 138).

## 3. Evidencia de ejecución

| Puerta | Resultado |
|---|---|
| Pruebas dirigidas de la 047 (backend) | **85** casos, verdes dentro de la regresión |
| Regresión completa del backend, sola | **1495 total · 1487 pasan · 8 saltos S3 · 0 fallos · 0 errores · 0 advertencias** (30 min 55 s) |
| Saltos inesperados | **0** (los 8 son `test_documents_storage.py`, S3 externo) |
| Vitest | **349 / 349** |
| TypeScript · ESLint · build | exit **0** · **0** · **0** |
| Ruff | **0** |
| Instalación limpia (P24) | base nueva → **57 migraciones** → `0057` → siembra → 13 tablas → 6 permisos de ADMIN → tick con salida 0 |
| Ida, vuelta y nueva ida | verde (`test_zz_la_migracion_se_deshace_y_se_rehace`) |
| Paridad ORM ↔ migración ↔ PostgreSQL | **0** diferencias en unicidades, `CHECK`, índices, claves foráneas y nulabilidad de las 13 tablas; N10 verde en la regresión |
| E2E cadena canónica, instalación limpia | **243 / 243** (81 × Chromium, Firefox, WebKit) |
| E2E de la 047 | **21 / 21** (7 × tres navegadores) |
| Trazas y 5xx en el backend durante el E2E | **0** |
| Ticks en la base del E2E | 176 `COMPLETED` · 2 `SKIPPED_OVERLAP` |
| Mutaciones | **19 / 19 caen** (§4) |

## 4. Mutaciones (P27)

| ID | Defecto introducido | Prueba que cae |
|---|---|---|
| M047-01 | clave del hecho aleatoria | `test_el_mismo_hecho_no_duplica_ni_repetido_ni_tras_perder_el_recibo` |
| M047-02 | sin guarda de tenant en destinatarios | `test_un_usuario_de_otro_tenant_nunca_llega_a_destinatario` |
| M047-03 | sin guarda de empresa en la lista | `test_flujo_l_la_notificacion_de_a_no_existe_en_el_contexto_de_b` |
| M047-04 | lectura global | `test_flujo_g_cada_destinatario_tiene_su_propio_estado_de_lectura` |
| M047-05 | completar aprueba el paso | `test_flujo_i_completar_la_tarea_no_aprueba_nada` |
| M047-06 | el fallo externo borra la interna | `test_flujo_k_el_fallo_del_canal_externo_no_toca_la_notificacion_interna` |
| M047-07 | se ignora el permiso del origen | `test_flujo_j_sin_permiso_del_origen_el_item_no_existe_para_el_usuario` |
| M047-08b | clave de tarea aleatoria | `test_repetir_el_hecho_no_duplica_la_tarea` |
| M047-09 | reasignar borra el historial | `test_flujo_h_asignar_reasignar_y_completar_conserva_todo_el_historial` |
| M047-10 | reloj sin zona aceptado | `test_un_reloj_sin_zona_se_rechaza` |
| M047-11 | contador con otra empresa | `test_flujo_l_la_notificacion_de_a_no_existe_en_el_contexto_de_b` |
| M047-12 | la colisión única escapa | `test_dos_publicaciones_forzadas_del_mismo_hecho_no_duplican_ni_revientan` |
| M047-13 | sin bloqueo de solapamiento | `test_flujo_b_un_tick_solapado_se_registra_y_no_ejecuta_nada` |
| M047-14 | clave aleatoria por tick | `test_flujo_a_un_recordatorio_se_emite_una_sola_vez_aunque_el_tick_se_repita` |
| M047-15 | recuperación ventana a ventana | `test_flujo_c_tras_48_horas_sin_ticks_solo_se_emite_la_ventana_vigente` |
| M047-16 | temporizador con SQL | `test_el_temporizador_solo_invoca_la_orden_canonica` |
| M047-17 | efecto en otra empresa | `test_cada_efecto_se_crea_en_la_empresa_de_su_tarea` |
| M047-18 | clave desconocida cruda | `test_una_clave_desconocida_es_un_error_controlado_y_nunca_la_clave_cruda` |
| M047-19 | texto compuesto como autoridad | `test_flujo_f_cambiar_la_redaccion_no_toca_la_fila` |

Cada una terminó con código 1 por fallo de aserción, sin errores de colección, y el
fuente se restauró comprobando su huella. **M047-08 original fue inválida**: metía el
id del hecho en la clave, y perder el recibo reprocesa el mismo hecho con el mismo id,
así que no había defecto que detectar. Se sustituyó por M047-08b. Detalle en
`evidence/mutaciones-M047-01-19.json` y `evidence/mutacion-M047-08b.json`.

## 5. Incidencias del ciclo y su clasificación

| Incidencia | Clasificación | Resolución |
|---|---|---|
| Los `CHECK` de la migración salían con doble prefijo y uno truncado (Alembic aplica la convención del ORM) | `NEW_REGRESSION_SPEC047` | Sufijo en la migración; paridad a 0 antes de las pruebas |
| La guarda N10 falló al lanzar un subconjunto de guardas | orden de invocación | Pasa sola y en la regresión canónica |
| La guarda de cadenas visibles leía `=> apiFetch<…>` como texto JSX | `TEST_DEFECT` (047) | Expresión corregida sin debilitarla |
| M047-08 sobrevivió | mutación inválida (P27) | Sustituida por M047-08b |
| Añadir D2 al tenant del E2E rompió pruebas de otras Specs que crean usuarios sin alcance | `NEW_REGRESSION_SPEC047` (herramienta de QA) | La siembra de la 047 corre después de la cadena canónica, en tramo propio |
| **La campana quedaba en 0**: `AppShell` retira las consultas de empresa en un efecto del padre, que corre después de la petición de la campana persistente | `NEW_REGRESSION_SPEC047` (producto) | La campana se vuelve a construir si el shell retira su consulta; prueba vitest que falló antes del arreglo y pasa después |
| La primera captura de diagnóstico componía el mensaje antes de esperar | `TEST_DEFECT` (047) | Captura síncrona, mensaje al fallar |
| La prueba de aislamiento buscaba D2 con el administrador, que la siembra limita a D1 | `TEST_DEFECT` (047) | D2 se busca con el usuario de la ejecución |
| La espera de la paginación miraba una sola página de 100 | `TEST_DEFECT` (047) | Recorre todas las páginas |
| `approvals.spec.ts`: flujo principal y multiempresa | `PREEXISTING` · `TEST_DEFECT` · dueña 045 | §6 |
| Un `pytest` de otro proyecto (`GlobalAvicola`) corría en la máquina | `EXTERNAL_ENVIRONMENT` | No se tocó; la guarda del orquestador se restringió a KONTROL |
| PostgreSQL 16.2 en lugar de 18.6 | `ENVIRONMENT_BASELINE_DEVIATION` | Declarada |

**UNKNOWN = 0.**

## 6. Deuda ajena registrada — no corregida

| Hallazgo | Dueña | Evidencia |
|---|---|---|
| `e2e/approvals.spec.ts · uiLogin` busca «Activar» por subcadena y pulsa «Desactivar» cuando la empresa ya se resolvió sola (desde N6, `aa4604f`); el escenario multiempresa espera 0 con un `company_id` que la ruta ignora y hereda lo que dejó pendiente el anterior | 045 | Falla igual con el frontend de `370e10a`, anterior a la 047 (`evidence/e2e-resumen.txt`) |
| `GET /approvals/inbox` pagina con `limit`/`offset` y filtra en Python los pasos de todas las empresas | 045 | `analysis-report.md` §B.4 |
| Un paso `EXPIRED` no vuelve a `IN_REVIEW`; el manejador de vencimiento queda deshabilitado | 045 | CL-047-14 |
| Correo, push y SMS sin proveedor | 048 | CL-047-08 |

## 7. Puerta del §103

| Condición | Estado |
|---|---|
| OQ-047-01 y OQ-047-02 cerradas · Material OQ 0 | ✔ |
| ADR del planificador `APPROVED · ACTIVE` y citado | ✔ `ADR-D0-015` · guarda |
| Planificador implementado · cola 0 · worker residente 0 | ✔ guardas de arquitectura |
| Efectos duplicados por solapamiento, reintento o recuperación: 0 | ✔ M047-13, 14, 15 |
| Núcleos de notificación, tarea y alerta | ✔ |
| Persistencia por `message_key` · catálogo `es` · `en` DEFERRED | ✔ |
| Cadenas visibles nuevas fuera de catálogo: 0 | ✔ guardas backend y vitest |
| Duplicación de aprobación, proveedor, planificador o reglas: 0 | ✔ |
| Cruce de empresa, de tenant e IDOR: 0 | ✔ M047-02, 03, 07, 11, 17 |
| 500 en carreras: 0 | ✔ carreras forzadas · M047-12 |
| Deriva ORM ↔ Alembic en el alcance tocado: 0 | ✔ |
| Backend: 0 fallos · 0 errores · 0 saltos inesperados | ✔ |
| Frontend y build | ✔ |
| E2E | ✔ 243 + 21 |
| Mutaciones significativas y restauradas | ✔ 19 |
| UNKNOWN 0 · trazabilidad 100 % | ✔ `traceability-matrix.md` |
