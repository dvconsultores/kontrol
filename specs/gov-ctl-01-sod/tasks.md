# Tareas · GOV-CTL-01 Matriz de segregación de funciones (CTL-01, GOV-CTL-001)

- Todo el código lo escribe DeepSeek con un encargo de Claude; Claude audita, aplica, prueba y certifica.
- `RETRY_MAX: 2`.
- `EGRESS_SAFE`: sí.
- Un fichero por encargo, de hasta unos 15 000 caracteres.

**Lecciones aplicadas de DOC-08:**
- `queryFn: () => …`;
- `useAutoridad` en todo POST de UI;
- el import dinámico de vitest, a nivel de módulo;
- `--project` explícitos en la E2E;
- un fixture de módulo activa «gobierno» por su cuenta;
- clave `bytes` prohibida en la auditoría.

## Phase 1: Corte vertical

### Backend
- [x] T001 [RED] Pruebas backend `tests/test_gov_ctl01_*.py`: reglas (alta, validaciones, edición, activación, duplicado, cierre, historia, concurrencia de versión); guarda en DOC-02 y en CTL-06 (bloquea al mismo usuario y al mismo objeto, permite a otro usuario y a otro objeto, regla futura, vencida, cerrada o de otra empresa, bidireccional, sin mutación, auditoría del bloqueo); conflictos (consulta y filtros, alcance); permisos y MFA · DEEPSEEK · pro · SECURITY_SENSITIVE sí
- [x] T002 Modelos + migración `0072_gov_ctl01_sod` + permisos y registros (setup, MFA) + recuentos de las guardas · DEEPSEEK · pro · SECURITY_SENSITIVE sí
- [x] T003 `schemas_sod.py` + `service_sod.py`: catálogo, reglas, guarda y conflictos · DEEPSEEK · pro · SECURITY_SENSITIVE sí
- [x] T004 Integración de la guarda en `service_actos.py` (6 acciones B posibles; DOC02_REGISTRAR crea el objeto y solo actúa como acción previa) y `service_hallazgos.py` (8; ídem CTL06_REGISTRAR) · DEEPSEEK · pro · SECURITY_SENSITIVE sí
- [x] T005 `api_sod.py` + `main.py` + 5 acciones de auditoría + espejo del catálogo + integración en CTL-04 · DEEPSEEK · flash

### Frontend
- [x] T006 Contrato en `api.ts`, rutas, `pantallas.ts`, menú y fixtures · DEEPSEEK · flash
- [x] T007 `ReglasSodPage` (S1) + `NuevaReglaSodPage` (S2) · DEEPSEEK · pro
- [x] T008 `ReglaSodPage` (S3) + `ConflictosSodPage` (S4) · DEEPSEEK · pro
- [x] T009 `ConflictoSoD` (alerta) integrado en `ActoPage` y `HallazgoPage` · DEEPSEEK · pro
- [x] T010 Pruebas de frontend (vitest) · DEEPSEEK · pro

### Validación y cierre
- [x] T011 E2E `e2e/gobierno-sod.spec.ts` + humo UAT con 10 pantallas · DEEPSEEK · pro
- [x] T012 Mutaciones de negocio · CLAUDE · n-a
- [x] T013 Certificación:
  - suites, E2E ×3, regresión y canónica, base tras la E2E, OpenAPI y residuos;
  - ficha de pantallas, tarjeta UAT y métricas;
  - relevo UAT + humo-uat.
  - · CLAUDE · n-a

## Notas de ejecución (correcciones y reintentos)

- **RED demostrado:** las 4 suites `tests/test_gov_ctl01_*.py` se ejecutaron sobre un worktree de ENTRY_HEAD `9dd2fe6`. Fallan al recolectar (`ImportError: GovernmentSoDRuleHistory`), es decir, el producto no existía.
- **Integración de la guarda:** `DOC02_REGISTRAR` y `CTL06_REGISTRAR` crean el objeto y solo actúan como acción previa (A), así que la guarda queda integrada en 6 acciones de DOC-02 y 8 de CTL-06. En cada una corre después de las validaciones de dominio y antes de la primera escritura.
- **Errores de encargo de Claude, corregidos dentro del ciclo:**
  - el nombre `CABECERA_CLIENTE` en lugar de `CABEZA_CLIENTE` (T002c-r1);
  - el orden del import de `User` (T003c-r1);
  - el docstring y el formato pedidos en la API (T005a-r1);
  - la firma de `classify` y el código `VALIDATION_ERROR` del esquema (T001a-r2);
  - los estilos de S1 no fijados (T007a-r1);
  - la sangría de un ancla (reenvío sin consumir reintento);
  - la espera general «/^Proceso/» en S3 (T010c-r2);
  - la ruta de los mutantes de interfaz (repetidos);
  - el prefijo «Regla » del código en la E2E (T011a-r1).
- **Defectos del ejecutor rechazados y corregidos:**
  - f-strings inválidos en Python 3.11 (T001a-r1);
  - respuestas HTTP tratadas como dict, id equivocado y `try/finally` incompleto (T001b-r1/r2);
  - doble activación de la regla (T001c-r1);
  - empresa como cadena e import sin usar (T001d-r1);
  - props inventadas en `LoadingState`/`ErrorState` y `p.codigo` en lugar de `p.proceso` (T007b-r1, T008b-r1);
  - `notify` sin desestructurar, `AsyncButton` sin Promise y `HistoriaSod.id` (T008a-r1);
  - `help` puesto en `TextInput` y avisos de `useMemo` (T007b-r2, T008b-r2);
  - selectores de vitest (T010b/c/d-r1).
- **Regresiones destapadas en la certificación, corregidas:**
  - **DA-08 (DOC-08):** apagaba «gobierno» solo en la instantánea `ctl06-test`, mientras la licencia usa la más reciente por `taken_at`. Con las suites nuevas el orden cambió y dejó de bloquear. Ahora apaga todas las instantáneas de la instalación (T013-r).
  - **CTL4-E2E-06 (CTL-04), axe `target-size` a 1280 px:** el filtro «Acción» se ensanchaba con la etiqueta de auditoría más larga, la nueva de CTL-01, y tapaba el botón de búsqueda. Corrección: `max-w-xs` en los filtros Proceso y Acción (T013b). Pasa 18/18 en los tres navegadores.
- **Guardas de recuento movidas por CTL-01:**
  - catálogo de auditoría 286 → 291 (CATB-03);
  - proceso CTL-01 en GX-02;
  - permisos 111 → 114;
  - MFA: SENSITIVE 50 y STANDARD 47;
  - cabeza de migraciones 0072.
