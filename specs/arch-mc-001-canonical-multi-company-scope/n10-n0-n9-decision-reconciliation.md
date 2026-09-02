# N10 — RECONCILIACIÓN DE DECISIONES N0–N9

| Decisión | Estado original | Estado final | Evidencia |
|---|---|---|---|
| Varias empresas por tenant | Propuesta en N0 | **Vigente** | `Company.tenant_id`; fixture T1(A,B) · T2(C) en `conftest_multicompany` |
| `CompanyContext` como única autoridad por petición | N1 | **Vigente** | `get_company_context`; 342 operaciones la declaran |
| `UserScope` es la autoridad de acceso, `UserRole` no | N1 | **Vigente y aplicada donde faltaba** | N10 la aplicó en `resolve_actors`, que recibía la empresa y no la usaba |
| La empresa nunca se toma del tenant | N2 | **Vigente** | `test_no_company_scope_writer_uses_tenant_id`; N10 cerró las dos últimas lecturas que filtraban por tenant |
| Alcance declarado en todo modelo | N3 | **Vigente y simétrico** | N10 extendió el contrato al alcance de tenant: 0 modelos sin ruta verificable |
| Expandir `tenant_id` en cinco tablas | N3 (`0032`) | **Revocada** | N7 reclasificó tres a empresa; N10 retiró las cinco columnas en `0039` |
| Migración de legado sin escritura y repetible | N4 | **Vigente** | `qa/n4-legacy-hostile-seed.py` + `test_mc_preflight` |
| Backfill real de legado | N4 | **NO APLICA** | No hay instalaciones heredadas desplegadas |
| Fiscal separado y versionado por instalación | P4 | **Vigente** | `LegalSource` INSTALLATION, `TaxRuleVersion` GLOBAL; sin cabecera de empresa por diseño |
| La empresa activa es de la pestaña | N6 | **Vigente** | `companyProvider` · 278 pruebas de frontend |
| La empresa deja de ser una cadena y pasa a ser una referencia | N7 | **Vigente** | 331 claves foráneas; paridad ORM/base = 0 |
| La capa de transición se retira | N8 | **Vigente** | `legacy_scope_id` y `scope_backfill_class` en ejecución: 0 |
| Registro documental cerrado, 23 tipos | N9 | **Vigente** | `test_n9_resourcekinds` (48 pruebas) |
| El catálogo de roles es del tenant | Implícita desde N0 | **Corregida a instalación** | No hay `tenant_id` ni camino a uno, no existe ruta para crear roles, y un segundo tenant reutiliza el `ADMIN` existente |

## La única decisión que N10 revocó

La de `0032`. No se revocó en N10: se había revocado en N7, y lo que N10
encontró fue que **la revocación nunca llegó al esquema**. Tres tablas
reclasificadas a empresa seguían llevando la columna de tenant que el plan
anterior les había puesto, vacía y con clave foránea real.

Es la forma más silenciosa de contradicción: no hay ningún documento que mienta
—`canonical-scope-matrix.md` registra la corrección con su motivo— y aun así el
sistema conserva la estructura de la decisión anterior.
