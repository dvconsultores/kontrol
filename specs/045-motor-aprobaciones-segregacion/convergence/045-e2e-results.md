# RESULTADOS E2E — SPEC 045 (CVG-045-03)

`resources/frontend/e2e/approvals.spec.ts` · **11 escenarios**
Frontend real → API real → backend real → **PostgreSQL 16.2 real**. El motor no se mockea.

| # | Escenario | Cubre | Resultado |
|---|---|---|---|
| 1 | Configurar → solicitar → bandeja → aprobar 2 niveles → historial | §12 completo | **PASS** |
| 2 | Rechazo con motivo obligatorio | §13 | **PASS** |
| 3 | Devolución para corrección y reenvío | §14 | **PASS** |
| 4 | Segregación: el creador no puede aprobar ni ve acciones | §15 | **PASS** |
| 5 | Usuario sin sesión: 401 del backend | §16 | **PASS** |
| 6 | Solicitud obsoleta tras cambiar el documento | §17 | **PASS** |
| 7 | `If-Match` con versión obsoleta → 409; sin `If-Match` → compatible | §18 | **PASS** |
| 8 | Idempotencia: doble envío simultáneo → una sola solicitud | §19 | **PASS** |
| 9 | Concurrencia: aprobar y rechazar a la vez → una decisión | §20 | **PASS** |
| 10 | Multiempresa: no se ven solicitudes de otra empresa | §37 | **PASS** |
| 11 | Eventos de dominio emitidos | §22 | **PASS** |

## Flujo principal, paso a paso (§12)

1-8. Login, empresa activa, **política creada íntegramente desde la interfaz**:
tipo de proceso, código, nombre, regla con condición y operador, dos niveles con
resolutor y cuórum, **simulación previa** (`Requiere 2 niveles`) y activación.
9-12. Solicitud creada; el motor resuelve la política; aparece en la bandeja
filtrada por proceso, con el botón de aprobación visible.
13-18. Nivel 1 aprobado con `If-Match` → abre nivel 2 → aprobado → `APPROVED`.
19-22. El documento origen puede continuar (`blocks_advance=false`,
`is_approved=true`); el historial conserva los 2 pasos; `AuditEvent` registra
`APPROVAL_REQUESTED` y `APPROVAL_APPROVE`; la consulta posterior persiste.

## Cross-browser (CVG-045-06)

| Navegador | E2E 045 | axe WCAG 2.2 AA |
|---|---|---|
| **Chromium** | **11/11 PASS** | **22/22 PASS** |
| **Firefox** | **11/11 PASS** | **22/22 PASS** |
| **WebKit** | **11/11 PASS** | **22/22 PASS** |

> **WebKit no es Safari real.** Se reporta como WebKit, conforme al §25: no se
> afirma cobertura de Safari en dispositivo.

## Nota metodológica

Los escenarios navegan por **SPA (clic en el menú)**, no con `page.goto`: una
carga completa pierde el access token, que vive en memoria (ADR-004), y el guard
redirige a `/` mientras restaura la sesión. Esto es lo que hacía que la
instrumentación previa del proyecto midiera la página de inicio (CVG-045-07).
