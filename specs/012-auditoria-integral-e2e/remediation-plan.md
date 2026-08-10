# Spec 012 — Plan de Remediación (remediation-plan.md)

No implementado aún. Pendiente de **autorización expresa**.
Cada corrección debe convertirse en tarea Spec (con su evidencia).

## Ola 0 — Bloqueantes
- (No hay BLOCKER confirmado en esta pasada. Re-evaluar tras validaciones de seguridad/backup/fiscal.)

## Ola 1 — Completitud estructural (errores tipo "Sucursales")
| Tarea | Hallazgo | Descripción | Severidad |
|---|---|---|---|
| T-01 | F-01 | Implementar página+ruta **Usuarios** (`/seguridad/usuarios`) consumiendo `GET/POST /users` + auditoría/permisos | HIGH |
| T-02 | F-02 | Implementar página+ruta **Roles/Permisos** (`/seguridad/roles`) + endpoints backend de gestión de roles (hoy inexistentes) | HIGH |
| T-03 | F-05 | Implementar **Establecimientos** (menú+ruta+página sobre `/organization/establishments`) para completar cadena Org | MEDIUM |
| T-04 | F-05 | Implementar **Ubicaciones** (sobre `/organization/locations`) | MEDIUM |

## Ola 2 — Datos y precisión
| Tarea | Hallazgo | Descripción | Severidad |
|---|---|---|---|
| T-05 | F-03 | Migrar dinero/tasas de `Float` → `Numeric(scale=2)`/Decimal (58 columnas) con backfill y revisión de redondeo | MEDIUM |
| T-06 | F-07 | Verificar timezone de `DateTime` en PostgreSQL real (Alembic + ORM) y corregir drift si existe | MEDIUM |

## Ola 3 — Interfaces faltantes (API sin UI)
| Tarea | Hallazgo | Descripción |
|---|---|---|
| T-07 | F-04 | Clasificar los 117 endpoints sin consumidor: `DOCUMENTED_FUTURE_SCOPE` vs brecha; construir UI para los obligatorios (movements/balances, perfiles fiscales, sessions) |

## Ola 4 — Puertas permanentes (evitar regresión tipo Sucursales)
| Tarea | Descripción |
|---|---|
| T-08 | **Test de completitud del menú** (Gate 1/2/3): todo `to:` del Sidebar debe existir en router y la página debe poder importarse. Falla el build/CI si no. |
| T-09 | **Test de completitud de rutas** (Gate 3/4): cada página debe llamar endpoints existentes en OpenAPI (contract). |
| T-10 | **E2E de procesos críticos** (Gate 6): Empresa→Sucursal→Establecimiento→Almacén, Ventas, Compras, Fiscal (emitir→consultar→editar). |
| T-11 | **Crawler de rutas** (no destructivo): login QA → recorrer menú → sin 404/500/errores de consola. |

## Ola 5 — Validaciones pendientes (ambiente autorizado)
| Tarea | Descripción |
|---|---|
| T-12 | Matriz de navegadores reales (Safari/Opera/Samsung) + responsive + axe accesibilidad |
| T-13 | Seguridad (OWASP, tenant isolation, IDOR) en ambiente controlado |
| T-14 | Backup→restore probado (base vacía reconstruida) |
| T-15 | Rendimiento con dataset representativo |
| T-16 | Auditoría fiscal (IVA/ISLR/IGTF/retensiones/números de control) contra normativa + validación de inmutabilidad de documentos |

## Orden sugerido
Ola 1 (T-01..T-04) → T-08..T-11 (puertas) → Ola 2 (T-05,T-06) → Ola 3 (T-07) → Ola 5 (T-12..T-16).
