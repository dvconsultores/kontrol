# Tareas · GOV-DOC-08 Paquete de auditoría exportable (DOC-08, GOV-DOC-010)

- Todo el código lo escribe DeepSeek con un encargo de Claude; Claude audita, aplica, prueba y certifica.
- `RETRY_MAX: 2`.
- `EGRESS_SAFE`: sí. Datos sintéticos; sin contraseñas ni rutas del equipo en los encargos.
- Cada encargo apunta a un solo fichero y no pasa de unos 17 000 caracteres (lección del puente en CTL-06).

## Phase 1: Corte vertical

### Backend
- [x] T001 [RED] Pruebas backend `tests/test_gov_doc08_*.py`, un fichero por tema:
  - paquete (fixtures, vista previa y generación);
  - contenido (ZIP, manifiesto, huellas, SHA256SUMS, referencias cruzadas y hallazgos);
  - documentos (inclusión y exclusión);
  - descarga;
  - verificación (válido, alterado, incompleto, versión no soportada, ZIP inseguro);
  - alcance (tenant, empresa, permisos, idempotencia, límites, inmutabilidad y auditoría).
  - · DEEPSEEK · pro · SECURITY_SENSITIVE sí · TEST pytest PG · DONE_WHEN falla por ausencia de producto
- [x] T002 Modelos + migración `0071_gov_doc08_paquetes` (2 tablas, disparadores y permisos) + registros (setup, MFA) y recuentos de las guardas · DEEPSEEK · pro · SECURITY_SENSITIVE sí
- [x] T003a `documents.service.puede_leer_archivo` y delegación de `_assert_can_read_file` (AD-DOC08-04) · DEEPSEEK · pro · SECURITY_SENSITIVE sí · TEST suites de documentos
- [x] T003b `schemas_paquetes.py` · DEEPSEEK · flash
- [x] T003c `service_paquetes.py`:
  - candidatos, inclusión y vista previa;
  - construcción del ZIP, generación e idempotencia;
  - descarga, manifiesto y verificación.
  - · DEEPSEEK · pro · SECURITY_SENSITIVE sí
- [x] T004 `api_paquetes.py` + `main.py` + 4 acciones de auditoría + espejo del catálogo + integración en CTL-04 (proceso y rastreo) · DEEPSEEK · flash

### Frontend
- [x] T005 Contrato en `api.ts`, rutas, `pantallas.ts`, menú y fixtures · DEEPSEEK · flash
- [x] T006 `GenerarPaquetePage` + botón y sección en `MuestraPage` · DEEPSEEK · pro
- [x] T007 `PaquetesPage` + panel de verificación · DEEPSEEK · pro
- [x] T008 `PaquetePage` · DEEPSEEK · pro
- [x] T009 Pruebas de frontend (vitest) · DEEPSEEK · pro

### Validación y cierre
- [x] T010 E2E `e2e/gobierno-paquetes.spec.ts` + humo UAT con 9 pantallas · DEEPSEEK · pro
- [x] T011 Mutaciones de negocio · CLAUDE · n-a
- [x] T012 Certificación:
  - suites, E2E ×3 y canónica, base tras la E2E, OpenAPI y residuos;
  - ficha de pantallas, tarjeta UAT y métricas;
  - relevo UAT + humo-uat.
  - · CLAUDE · n-a

## Notas de ejecución (correcciones y reintentos)

- **RED demostrado:** las 5 suites `tests/test_gov_doc08_*.py` se ejecutaron sobre un worktree de ENTRY_HEAD `6afd8d0`. Fallan al recolectar (`ImportError: service_paquetes`), es decir, el producto no existía.
- **Errores de encargo de Claude, corregidos dentro del ciclo:**
  - el import de `Field` sin usar (T003b-r1);
  - la ruta del modelo `User` sin mostrar (T004a-r1);
  - el orden del import en `main.py` (T004b-r1);
  - la clave de auditoría `bytes`, prohibida por el catálogo, que pasa a `tamano_bytes` (T004c, spec §8 corregida);
  - la firma ambigua de `_motivo_de_limite` (T003c-2-r1);
  - el fixture `gobierno` de scope función usado desde un fixture de módulo (T001a-r2, `_activar_gobierno`);
  - `queryFn` escrito como valor en los encargos de T007a y T008 (r1/r2);
  - la puerta de autoridad de `VerificarPaquete`, exigida por la guarda `gate-coverage` (T007b-r2);
  - el andamio de vitest sin la posición del import dinámico (T009a/b-r1);
  - el mutante M10 mal construido (M10b).
- **Defectos del ejecutor rechazados y corregidos:**
  - tipos de mypy en `service_paquetes` (T003c-r2/r3);
  - estados en minúsculas e índices sobre `null` (T008-r1);
  - doble envío del formulario y falta de estilos (T006a-r1);
  - helpers, rutas y fixtures inventados en las pruebas (T001b/d/e reintentos).
- **T001e** se dividió en T001e1 (alcance) y T001e2 (integridad) tras el rechazo del primer intento.
- **Mutaciones:** DOC8-M17 sobrevivía por un hueco real de PQT-01. La prueba se reforzó por fila (T009c-r1).
- **Guardas de recuento movidas por DOC-08:**
  - catálogo de auditoría 282 → 286 (CATB-03);
  - proceso DOC-08 en GX-02;
  - permisos 109 → 111;
  - MFA: SENSITIVE 49 y STANDARD 45;
  - cabeza de migraciones 0071 (T002c, T004d).
