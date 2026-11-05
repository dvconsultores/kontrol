# Tareas · GOV-TRE-01 Cuentas bancarias públicas (TRE-01, GOV-TRE-001)

- Todo el código lo escribe DeepSeek con un encargo de Claude; Claude audita, aplica, prueba y certifica.
- `RETRY_MAX: 2`. `EGRESS_SAFE`: sí; números de cuenta sintéticos.

## Phase 0: Preflight
- [x] T000 OBS-CERT-GOV-01: controles de integridad versionados (`qa/gobierno_integridad*.py`, `qa/e2e-gobierno-regresion.sh`, `test_gobierno_integridad_runner.py`) · commit `2b1dc6f`

## Phase 1: Corte vertical

### Backend
- [x] T001 [RED] Pruebas `tests/test_gov_tre01_*.py`: bancos; cuenta (alta, validaciones, número, enmascarado); acto; autorizados e historia; estados; alcance y permisos; concurrencia · DEEPSEEK · pro · SECURITY_SENSITIVE sí
- [x] T002 Modelos + migración `0073_gov_tre01_cuentas` + permisos y registros + recuentos · DEEPSEEK · pro · SECURITY_SENSITIVE sí
- [x] T003 `schemas_cuentas.py` + `service_cuentas.py` · DEEPSEEK · pro · SECURITY_SENSITIVE sí
- [x] T004 `api_cuentas.py` + `main.py` + 12 acciones de auditoría + espejo + CTL-04 + catálogo SoD · DEEPSEEK · flash
- [x] T005 Controles de integridad T1.. en el runner versionado · DEEPSEEK · flash

### Frontend
- [x] T006 Contrato en `api.ts`, rutas, `pantallas.ts`, menú y fixtures · DEEPSEEK · flash
- [x] T007 `CuentasPage` (S1) + `NuevaCuentaPage` (S2) · DEEPSEEK · pro
- [x] T008 `CuentaPage` (S3) · DEEPSEEK · pro
- [x] T009 `BancosPage` (S4) · DEEPSEEK · pro
- [x] T010 Pruebas de frontend (vitest) · DEEPSEEK · pro

### Validación y cierre
- [x] T011 E2E `e2e/gobierno-tesoreria.spec.ts` + humo UAT con 12 pantallas · DEEPSEEK · pro
- [x] T012 Mutaciones de negocio · CLAUDE · n-a
- [x] T013 Certificación completa, ficha, tarjeta UAT, métricas, relevo UAT y humo · CLAUDE · n-a
