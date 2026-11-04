# Tareas · GOV-CTL-06 Hallazgos, recomendaciones y planes de acción correctiva (CTL-06, GOV-CTL-008)

- Todo el código lo escribe DeepSeek con un encargo de Claude; Claude audita, aplica, prueba y certifica.
- `RETRY_MAX: 2`.
- `EGRESS_SAFE`: sí. Datos sintéticos; sin contraseñas ni rutas del equipo en los encargos.

## Phase 0: Preflight

- [x] T000 Suite PostgreSQL completa con analizador sobre `8b7675d` (certificación final de CTL-04) · CLAUDE · n-a

## Phase 1: Corte vertical

- [x] T001 [RED] Suite `tests/test_gov_ctl06_hallazgos.py` (GH6-…), en dos tandas:
  - (a) alta, origen, responsable, plan y concurrencia;
  - (b) avances, evidencia, presentación, verificación, maker-checker, devolución, historia, CSV, alcance y permisos.
  - · DEEPSEEK · pro · SECURITY_SENSITIVE sí
- [x] T002 Modelos + migración `0070_gov_ctl06_hallazgos` (6 tablas, disparadores y permisos) + registros (setup, MFA, `ResourceKind`) y recuentos de las guardas · DEEPSEEK · pro · SECURITY_SENSITIVE sí
- [x] T003 `schemas_hallazgos.py` y `service_hallazgos.py`: alta, origen, responsable, plan, avances, transiciones, maker-checker, historia, resumen y CSV · DEEPSEEK · pro · SECURITY_SENSITIVE sí
- [x] T004 `api_hallazgos.py` + `main.py` + 10 acciones de auditoría + espejo del catálogo + integración en CTL-04 (proceso y rastreo) · DEEPSEEK · flash
- [x] T005 Frontend: contrato en `api.ts`, rutas, `pantallas.ts`, menú, fixtures · DEEPSEEK · flash
- [x] T006 `HallazgosPage`: resumen, filtros, tabla y exportación · DEEPSEEK · pro
- [x] T007 `RegistrarHallazgoPage` + «Registrar hallazgo» en `MuestraPage` · DEEPSEEK · pro
- [x] T008 `HallazgoPage`: detalle, recomendaciones, plan, avances con evidencia, transiciones e historia · DEEPSEEK · pro
- [x] T009 Pruebas de frontend (vitest) · DEEPSEEK · pro
- [x] T010 E2E `e2e/gobierno-hallazgos.spec.ts` + humo UAT con 8 pantallas · DEEPSEEK · pro
- [x] T011 Mutaciones de negocio · CLAUDE · n-a
- [x] T012 Certificación:
  - suites, E2E ×3 y canónica, base tras la E2E, OpenAPI y residuos;
  - ficha de pantallas, tarjeta UAT y métricas;
  - relevo UAT + humo-uat.
  - · CLAUDE · n-a

## Notas de ejecución (reclasificación por reintentos agotados)

- **T001b**: dividida en tareas nuevas tras agotar sus 2 reintentos. Primero T001e (helpers) y T001f/T001g, que también agotaron los suyos. Después se reclasificó en 7 ficheros temáticos:
  - test_gov_ctl06_{avance,evidencia,verificacion,inmutable,alcance,listado,contrato}.py;
  - T001i (imports);
  - T001-makerchecker (GH6-31/32, para matar CTL6-M01/M02).
- **T009**: un fichero por componente. Tareas nuevas tras los reintentos: T009-RGH-tipos, T009-PDA-b, T009-HLP-06 y HLP-06b (CTL6-M15).
- **T010**: E2E en dos ficheros más el humo de 8 pantallas. Tareas nuevas tras los reintentos:
  - T010d–T010i: espera de respuestas, notificaciones, región de evidencia, timeout de E2E-03, axe tras el título y aserción final;
  - de ellas, T010g y T010h corrigen errores del encargo de Claude: la expresión de la ruta de avances y el permiso verify del responsable.
- **T012a / T012b** (las encontraron las suites completas del ciclo y se corrigieron dentro de él):
  - **T012a:** `test_n9_resourcekinds` fijaba 29 tipos documentales, y CTL-06 añade el 30.º, `GovernmentCorrectiveAction`. DeepSeek ajustó la cifra (flash, 1 intento).
    El docstring quedó con dos «y» seguidas porque el encargo de Claude lo pedía así; no es un defecto del ejecutor.
  - **T012b:** `tests/n9_resource_seeds.py` no tenía semilla para `GovernmentCorrectiveAction`. Por eso fallaban en PostgreSQL las pruebas de frontera entre empresas y entre tenants de ese tipo; en SQLite se saltan.
    DeepSeek añadió una semilla real (cargo → hallazgo → recomendación → acción), en flash y con 1 intento. N9 da 62/62 en PostgreSQL.
