# Tareas · GOV-0-02 Estructura organizativa por ejercicio

Todo el código lo escribe DeepSeek con un encargo de Claude; Claude audita, aplica, prueba y certifica. `RETRY_MAX: 2`. `EGRESS_SAFE`: sí (datos sintéticos; contraseñas solo de la constante del mundo de pruebas).

## Phase 1: Corte vertical

- [x] T001 [RED] Suite de backend `tests/test_gov0_estructura.py`: ejercicio, apertura (vacía y copia), unidades, jerarquía (autorreferencia, ciclo, padre ajeno/otro ejercicio/inactivo), código duplicado, máquina de estados, acto, motivo, campos bloqueados, desactivación, eliminación, versiones/historial, `If-Match`, CSV, auditoría, permisos, módulo, aislamiento · EXECUTOR DEEPSEEK · MODEL pro · SECURITY_SENSITIVE sí · DONE_WHEN falla en rojo sin el código
- [x] T002 Modelos y migración 0064 (`GovernmentStructure`, `GovernmentUnit`, `GovernmentUnitVersion`; FK compuesta; CHECKs; concesión a FUNCIONAL_COMPLETO) · DEEPSEEK · pro
- [x] T003 Esquemas y servicio de dominio (`schemas_estructura.py`, `service_estructura.py`) · DEEPSEEK · pro
- [x] T004 API (`api_estructura.py`) y registros (router, permisos, `ResourceKind`, 8 acciones de auditoría + espejo, MFA) · DEEPSEEK · pro/flash
- [x] T005 Guardas y contratos: cabeza 0064, CATB-03, DC-T01, MFA-G00b, N9 (cardinalidad y semilla), instantáneas del frontend (herramienta) · DEEPSEEK + herramienta
- [x] T006 Frontend: contrato (`api.ts`), rutas y `pantallas.ts`, entrada de menú, GOV0-UI-01 en la compuerta; páginas de ejercicios y de estructura, formulario de unidad, desactivación, eliminación, historial, acto, poner en vigor, cerrar, exportar · DEEPSEEK · pro
- [x] T007 Pruebas de frontend (vitest): menú, compuerta, estados, acciones por estado y capacidad, formulario y errores · DEEPSEEK · pro
- [x] T008 E2E `e2e/gobierno-estructura.spec.ts` (login → menú → proceso completo; negativos; axe 1280/320) + regresión de ORG-01 y GOV0-UI-01 · DEEPSEEK · pro
- [x] T009 Mutaciones de negocio (herramienta de Claude) · CLAUDE · n-a
- [x] T010 Certificación: suites PG/SQLite, frontend (tsc, eslint, vitest, build), E2E ×3 navegadores y canónica, base tras la E2E, OpenAPI, residuos, tarjeta UAT, métricas · CLAUDE · n-a

## Phase 2: Correcciones de la ejecución (ciclo GOV-0-FUNCTIONAL-02)

Cada una con su encargo autocontenido, auditoría de Claude y prueba mínima tras aplicar. Reintentos por subtarea: máximo 2.

- [x] T001b Datos de prueba de T001 (DA con nombre igual a su PATCH; CG1 fechada; `If-Match` viejo en el cierre) · DEEPSEEK · reintento 2 de T001
- [x] T001c GS-27: un vínculo de B a un documento de A no cuenta (mata el mutante OB20) · DEEPSEEK · flash · 0 reintentos
- [x] T003a/T003b Esquemas y servicio partidos en dos encargos (validadores; 13 errores de mypy por ids UUID) · DEEPSEEK · 2 reintentos cada uno
- [x] T005c Arnés del barrido de aislamiento: refresco de reautenticación por ruta (`hostil_mundo.refrescar_reautenticacion`); el barrido supera los 300 s de `REAUTH_MAX_AGE` con las rutas nuevas · DEEPSEEK
- [x] T006a..T006d Frontend partido en cuatro encargos (contrato y registros; página de ejercicios; componentes; página de estructura) · DEEPSEEK · pro
- [x] T005c-r1 Reloj del arnés: `refrescar_reautenticacion` sella con `app.core.clock.now()` (el `RelojDeSuite` que otras pruebas adelantan), no con `datetime.now(UTC)`; el barrido pasaba aislado y fallaba en la suite completa de PostgreSQL · DEEPSEEK · flash · 0 reintentos
- [x] T006e Fechas de negocio: `hoyDeNegocio()` en lugar de `new Date().getFullYear()` (guarda ADR-020) · DEEPSEEK
- [x] T006f Tres defectos hallados por la E2E real: (1) `NotificationContext` nunca olvidaba un aviso descartado y ocultaba el segundo «Unidad registrada» (FR-001-063: sin duplicados *a la vez*); (2) `useModuloGobierno` con clave separada por empresa: al elegir empresa la barra superior decía «Empresa activa» en Gobierno (GOV0-UI-01); (3) desbordamiento a 320 px por los `sr-only` absolutos de la tabla (contenedor `relative`) · DEEPSEEK · 1 reintento (dato muerto)
- [x] T006g Vigencia con fechas civiles: `formatearFechaDeNegocio` (ADR-020) en lugar de `formatearFecha` (instante UTC pintado en Caracas, un día antes); prueba GES-10 y mutante GF15 · DEEPSEEK · flash · 0 reintentos
- [x] T007a Pruebas de página: 1 reintento (import, texto exacto, nombres accesibles reales, botón del diálogo)
- [x] T007b Pruebas de componentes: 1 reintento (`vigente_hasta` en los datos tipados)
- [x] T008 E2E: 2 reintentos (esperas de red con expresión regular, rótulos exactos, ruta de navegación, constantes compartidas; celda «Cerrada», import sin uso y tiempo de las pruebas con analizador real)

## Phase 3: Convergence

- [x] T011 Add backend test GS-28: GET, publicar and unidades on a non-existent exercise return 404 `GOV_STRUCTURE_NOT_FOUND` per spec §8 op. 3 (partial)
- [x] T012 Add backend test GS-29: PATCH of a unit with no effective change returns 422 `GOV_UNIT_NO_CHANGES` without a new version or audit event per spec §8 op. 8 (partial)
- [x] T013 Point the plan's Constitution gate at `evidence/SCREEN_FORM_COMPLETENESS.md` (the cited `ORG02_SCREEN_FORM_MATRIX.md` does not exist) per plan: Constitution gate (partial)
