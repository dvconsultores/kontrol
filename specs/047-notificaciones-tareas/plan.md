# `/speckit.plan` — SPEC 047 · NOTIFICACIONES, TAREAS Y ALERTAS

> Recalculado el 2026-09-14 con OQ-047-01 y OQ-047-02 cerradas.

## 1. Arquitectura

```
temporizador systemd (host del cliente)
  └─ python kontrol.py scheduler-tick
       └─ docker compose exec -T backend python -m app.modules.scheduler tick
            ├─ pg_try_advisory_lock (conexión dedicada) ── ocupado → SKIPPED_OVERLAP
            ├─ scheduler_runs / scheduler_handler_runs
            └─ registro de manejadores (orden fijo)
                 1. approval_step_expiration   dueña 045 · DESHABILITADO (CL-047-14)
                 2. approval_event_intake      dueña 047 · DRAIN
                 3. task_reminders             dueña 047 · LATEST_WINDOW
                 4. task_escalations           dueña 047 · EFFECT_ONCE
                 5. notification_delivery      dueña 047 · DUE_RETRY

approval_events ─► intake ─► reglas de la empresa ─► publish()
                                                   ├─ notifications + recipients (+ deliveries)
                                                   ├─ tasks + candidates + task_events
                                                   └─ alerts
API /notifications /tasks /alerts ─► visibilidad revalidada ─► mensaje renderizado (es)
Frontend: campana (sondeo) · centro · tareas · detalle · alertas · reglas · preferencias
```

| Elemento | Decisión | Base |
|---|---|---|
| Módulos | `app/modules/scheduler` (marco) y `app/modules/notifications` (dominio), ambos de la 047, con cabeceras `# Spec 047 ·` para `bloque_de_spec` | P22 · §104 |
| Bloqueo | `pg_try_advisory_lock` en conexión dedicada | `research.md` §1 |
| Idempotencia | `dedupe_key` + restricción única + `es_violacion_unica` | `research.md` §2 · P25 |
| Recuperación | Política declarada por manejador | `research.md` §3 |
| Actor | `actor_type` `SYSTEM`/`USER`; auditoría `source="SCHEDULER"` | FR-047-045 |
| Empresa | Cada manejador agrupa por empresa y pasa un contexto explícito a cada efecto | FR-047-046 |
| Reloj | `now` inyectado; con zona obligatoria | NFR-047-01 |
| Mensajes | `messages.py`: catálogo `es`, contrato de parámetros, renderizador propio | FR-047-050..053 |
| Visibilidad | Destinatario o candidato + empresa del contexto + permiso del origen | FR-047-014 |
| Permisos | `notificaciones`, `tareas`, `alertas` en el catálogo y en la migración | CL-047-05 |
| Entrega externa | Registro de proveedores vacío en producción; pruebas con proveedor falso en la frontera | CL-047-08 |
| Despliegue | `scripts/scheduler/*.service|*.timer`, `scripts/install-scheduler.sh`, `kontrol.py scheduler-tick` | ADR-D0-015 |
| Frontend | `src/i18n` (`t()` + catálogo `es`), `src/modules/notificaciones/*`, campana en `Topbar` | FR-047-051/053 |

## 2. Olas

| Ola | Contenido | Estado |
|---|---|---|
| W01 | Inventario | **HECHA** |
| W02 | Mapa de dueñas | **HECHA** |
| W03 | Contrato de eventos | **HECHA** en diseño — CL-047-07, FR-047-054 |
| W04 | Núcleo de notificación | **HECHA** — T047-030, 031 |
| W05 | Estado por destinatario | **HECHA** — T047-033 |
| W06 | Núcleo de tareas | **HECHA** — T047-040 |
| W07 | Asignación e historial | **HECHA** — T047-041, 042 |
| W08 | Alertas | **HECHA** — T047-050 |
| W09 | Idempotencia | **HECHA** — T047-031, 032 |
| W10 | Seguridad multiempresa | **HECHA** — T047-062, 090 |
| W11 | Permisos | **HECHA** — T047-063 |
| W12 | Vencimientos y zona | **HECHA** — T047-044 |
| W13 | Preferencias | **HECHA** — T047-034 |
| W14 | Frontera externa | **HECHA** — T047-035 |
| W15 | Planificador y recordatorios | **HECHA** — T047-010..014, 045 |
| W16 | Escaladas | **HECHA** — T047-046 |
| W17 | API y OpenAPI | **HECHA** — T047-060..067 |
| W18 | Centro de notificaciones | **HECHA** — T047-082 |
| W19 | Tareas en el frontend | **HECHA** — T047-083, 084 |
| W20 | Alertas en el frontend | **HECHA** — T047-085 |
| W21 | Campana y contadores | **HECHA** — T047-081 |
| W22 | Paginación | **HECHA** — T047-060, 094 |
| W23 | Auditoría y observabilidad | **HECHA** — T047-064, 065 |
| W24 | Hostiles | **HECHA** — T047-090 |
| W25 | Concurrencia real | **HECHA** — T047-091 |
| W26 | Mutaciones M047-01..19 | **HECHA** — T047-092 |
| W27 | Migración | **HECHA** — T047-070, 071 |
| W28 | Instalación limpia | **HECHA** — T047-072 |
| W29 | Regresión cruzada 045 | **HECHA** — T047-095 |
| W30 | E2E en tres navegadores | **HECHA** — T047-100 |
| W31 | Regresión completa | **HECHA** — T047-101 |
| W32 | Analyze final | **HECHA** — T047-102 |
| W33 | Trazabilidad final | **HECHA** — T047-102 |
| W34 | Convergencia | **HECHA** — T047-102 |
| W35 | Máster 56 | **HECHA** — T047-110 |
| W36 | Revalidar solo la 049 | **HECHA** — T047-111 |

## 3. CONSTITUTION GATE — recalculado

`PASS` = cumplido en diseño y sin decisión pendiente. `EVIDENCIA REQUERIDA` =
diseño cumplido; solo se certifica con la ejecución.

| Puerta | Diseño | Evidencia |
|---|---|---|
| G047-01 Spec 047 existente | **PASS** | — |
| G047-02 Sin Spec paralela | **PASS** | — |
| G047-03 Sin aprobación duplicada | **PASS** — CL-047-02 enmendada, R-047-11 | ✔ ejecutada — flujo I |
| G047-04 Sin integración duplicada | **PASS** — CL-047-08 | ✔ ejecutada — guarda |
| G047-05 Sin planificador duplicado | **PASS** — ADR-D0-015, uno solo | ✔ ejecutada — guarda |
| G047-06 Sin robar reglas | **PASS** | ✔ ejecutada — M047-05 |
| G047-07 Autoridad del contexto | **PASS** | ✔ ejecutada — hostiles |
| G047-08 Lectura por destinatario | **PASS** | ✔ ejecutada — M047-04 |
| G047-09 Idempotencia | **PASS** — claves en `research.md` §2 | ✔ ejecutada — M047-01, 08, 14 |
| G047-10 Completar ≠ ejecutar | **PASS** | ✔ ejecutada — M047-05 |
| G047-11 Fallo externo no destruye | **PASS** | ✔ ejecutada — M047-06 |
| G047-12 Historial | **PASS** | ✔ ejecutada — M047-09 |
| G047-13 Sin cruce de empresa | **PASS** | ✔ ejecutada — M047-03, 11, 17 |
| G047-14 Sin cruce de tenant | **PASS** | ✔ ejecutada — M047-02 |
| G047-15 IDOR | **PASS** | ✔ ejecutada — M047-07 |
| G047-16 Permisos canónicos | **PASS** — CL-047-05 | ✔ ejecutada |
| G047-17 Zona horaria | **PASS** | ✔ ejecutada — M047-10 |
| G047-18 Paridad ORM ↔ Alembic | **PASS** en diseño | ✔ ejecutada |
| G047-19 Sin 500 en carreras | **PASS** en diseño | ✔ ejecutada — M047-12 |
| G047-20 Dashboard solo consume | **PASS** | ✔ ejecutada — flujo K de la 049 |
| G047-21 ADR aprobado y referenciado | **PASS** — ADR-D0-015 `APPROVED · ACTIVE` | ✔ ejecutada — guarda |
| G047-22 Sin cola, worker, daemon ni bucle | **PASS** | ✔ ejecutada — guarda |
| G047-23 Solapamiento sin efectos duplicados | **PASS** | ✔ ejecutada — M047-13 |
| G047-24 Recuperación sin tormenta | **PASS** | ✔ ejecutada — M047-15 |
| G047-25 Clave de mensaje como autoridad | **PASS** | ✔ ejecutada — M047-18, 19 |
| G047-26 Cadenas visibles fuera de catálogo = 0 | **PASS** | ✔ ejecutada — guardas |

**26 PASS en diseño · 0 CONDICIONADAS · 26 con evidencia de ejecución** (`convergence.md` §3, §4, §7).
La puerta autorizó `/speckit.implement` y la convergencia tiene sus 26 evidencias.

## 4. Riesgos

| ID | Riesgo | Mitigación |
|---|---|---|
| RK-047-01 | Segunda bandeja de aprobaciones | R-047-11; la tarea enlaza a la bandeja |
| RK-047-02 | Tick largo solapado con el siguiente | Bloqueo + `SKIPPED_OVERLAP` |
| RK-047-03 | Contadores lentos | Agregados SQL con índices; volumen > 100 |
| RK-047-04 | Confundir avisos de interfaz con notificaciones | CL-047-12 |
| RK-047-05 | Consumir auditoría como contrato | CL-047-07: no se consume |
| RK-047-06 | Habilitar el vencimiento de la 045 y atascar solicitudes | CL-047-14 |
| RK-047-07 | Tormenta retroactiva al crear una regla | CL-047-17 |
