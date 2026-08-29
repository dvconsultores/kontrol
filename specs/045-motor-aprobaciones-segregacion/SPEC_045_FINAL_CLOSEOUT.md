# SPEC 045 — FINAL CLOSEOUT

| Campo | Valor |
|---|---|
| Spec | `045-motor-aprobaciones-segregacion` |
| Fecha | 2026-08-29 · Rama `develop` |
| Entorno de validación | **PostgreSQL 16.2 real** · Chromium · Firefox · WebKit |
| Reproducible con | `qa/pg-provision.sh` · `qa/pg-migration-validation.sh` · `qa/pg-e2e-seed.py` |

## 1. Estado

**SPEC 045 COMPLETE_100.**

Los cuatro hallazgos que pertenecían a 045 quedan resueltos con evidencia sobre
el motor de producción. Los tres restantes están formalmente diferidos a las
Specs 046, 047 y 054, con contrato listo y sin dejar roto ningún requisito.

## 2. PostgreSQL

| Aspecto | Resultado |
|---|---|
| Versión | PostgreSQL 16.2 real (no SQLite, no `--sql`) |
| Instancia | `localhost:55432`, UTF8, timezone UTC, roles `kontrol_migrator` / `kontrol_app` |
| Migración limpia | ✔ `upgrade head` completo, 153 tablas |
| Upgrade desde pre-045 | ✔ con datos representativos |
| Paridad de esquema | ✔ **0 drift de 045**; 18 elementos preexistentes, de los que 3 son reales (Spec 010) |
| Suite completa | ✔ **276/276** |
| **Resultado** | **PASS** |

Desviación declarada: ADR-D0-001 fija PostgreSQL **18.x**; se validó sobre
**16.2**, la versión que empaqueta `pgserver`. Es PostgreSQL real y cubre todo lo
que SQLite ocultaba (FK, `Numeric`, `timestamptz`, `FOR UPDATE`, índices
parciales, MVCC). La diferencia de versión mayor queda registrada.

## 3. Migraciones

| Aspecto | Resultado |
|---|---|
| `0015` esquema | ✔ 8 tablas + renombrado de la legada, con constraints e índices |
| `0016` datos | ✔ permisos + histórico; idempotente |
| Renombrado regulatorio | ✔ 4 filas legadas íntegras; PK e índices renombrados; sin shadow table |
| Datos | ✔ **pérdida 0**; 3 migradas, 1 omitida por referencia colgante y conservada |
| FK e índices | ✔ sin colisión |
| **Resultado** | **PASS** |

## 4. Backend

Módulo `approvals`: 8 tablas, 22 endpoints, motor de evaluación, ciclo completo,
delegaciones y eventos. No importa ningún módulo de dominio. `ruff` y `mypy`
limpios sobre 75 archivos.

## 5. Frontend

4 rutas y 1 panel embebible. `tsc` ✔, `eslint --max-warnings 0` ✔, `vitest`
**217** ✔, build **377,33 KB** (gzip 115,26 KB) con code-splitting por ruta.
Configuración en pantalla completa; modal solo para confirmación breve.

## 6. Cuatro dominios integrados

| Dominio | Integración | Regresión SQLite | Regresión PostgreSQL |
|---|---|---|---|
| Purchasing | requisición y orden | ✔ | ✔ |
| Inventory | ajustes y conteos | ✔ | ✔ |
| Sales | crédito | ✔ | ✔ |
| Regulatory | flujo en ejecución + histórico | ✔ | ✔ |

`test_no_domain_keeps_its_own_approval_logic` cubre los cuatro y comprueba que
ningún módulo declare modelo de política propio. **No se excluye ninguno.**

## 7. E2E

11 escenarios contra frontend real → API real → backend real → PostgreSQL real.
**11/11 PASS.** El flujo principal configura la política **desde la interfaz**:
proceso, regla, dos niveles, simulación previa y activación.

## 8. Concurrencia

Dos decisiones simultáneas sobre el mismo paso → una prospera, la otra 409, y
queda **una sola** decisión registrada. Verificado sobre PostgreSQL, donde
`SELECT … FOR UPDATE` sí actúa. **PASS**

## 9. Idempotencia

Doble envío simultáneo → una sola solicitud, mismo identificador. El índice único
parcial garantiza la integridad y el servicio traduce la colisión en respuesta
idempotente. **PASS**

## 10. If-Match

Versión válida → 200. Versión obsoleta → 409 `APPROVAL_STEP_VERSION_CONFLICT`.
Sin cabecera → funciona, y las llamadas existentes no se ven afectadas. **PASS**

## 11. Seguridad

401 sin sesión · 403 sin permiso · 403 sin elegibilidad · segregación · prohibición
de autoaprobación · la delegación no elude la segregación · solicitudes obsoletas
no resolubles · sin replay · sin escalada. Todo en backend. **PASS**

## 12. Multiempresa

Empresa A no ve ni resuelve nada de B: políticas, bandeja, reglas e historial
filtrados por `company_id` en API y en consulta. **PASS**

## 13. Auditoría

`AuditEvent` append-only con actor, empresa, entidad, acción, antes/después,
motivo y la delegación con la que se ejerció. Verificado en E2E. **PASS**

## 14. Eventos

6 tipos en `approval_events`: `requested`, `step_opened`, `decided`, `resolved`,
`obsolete`, `step_expired`. El motor emite; no notifica. **PASS**

## 15. Cross-browser

```
CHROMIUM: PASS   E2E 11/11 · axe 22/22
FIREFOX:  PASS   E2E 11/11 · axe 22/22
WEBKIT:   PASS   E2E 11/11 · axe 22/22
```

WebKit no es Safari real; se reporta como WebKit. Edge y Opera no disponibles.

## 16. Responsive

Rutas de 045: **18/18 PASS**, 0 scroll horizontal en 6 viewports.
22 violaciones en 15 rutas **preexistentes**, escaladas y no corregidas aquí.

## 17. Accesibilidad

axe WCAG 2.2 AA: **22/22 en tres motores**, 0 violaciones serias o críticas.
Seis defectos reales corregidos, ninguno introducido por 045.

## 18. Regresión

Cinco componentes compartidos modificados (`ConfirmationDialog`, `apiFetch`,
`DataTable`, `Sidebar`, `Topbar`) con regresión específica. Cuatro dominios sin
cambio de expectativa. **PASS**

## 19. Dependencias externas

| Spec | Qué queda | Contrato | ¿Bloquea 045? |
|---|---|---|---|
| **046** | Adjuntar archivos de evidencia | ✔ `AttachmentLink` | No |
| **047** | Notificación activa | ✔ 6 eventos | No |
| **054** | Plataforma general de QA | n/a | No |

## 20. Trazabilidad

40 FR + 7 NFR · 65 tareas `DONE` · 24 criterios cubiertos ·
**0 requisitos sin tarea · 0 tareas sin requisito · 0 requisitos sin prueba.**

## 21. Resultado de `/speckit.converge 045`

**Converge.** 0 brechas internas de 045.

## 22. Blockers

**0.**

## 23. Critical

**0 en 045.** Se detectó y corrigió un BLOCKER **de producto ajeno a 045**: las
migraciones `0012`/`0014` referenciaban 7 columnas inexistentes y **la cadena
nunca había podido aplicarse sobre PostgreSQL**. Sin corregirlo, 045 no podía
cerrarse. Escalado a la Spec 012.

## 24. Veredicto

# SPEC 045 COMPLETE_100

Cumple los 30 criterios del §46. Las dependencias diferidas a 046, 047 y 054 no
pertenecen al alcance implementable de 045, tienen contrato listo, están trazadas
y no dejan roto ningún requisito actual.
