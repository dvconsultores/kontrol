# Plan · TRE-09

## CONSTITUTION GATE

```text
GOV_TRE_011_CLEAR=1   N39_CLEAR=1 (guardar tasa, fecha y fuente; no recalcular la historia)
CANONICAL_CURRENCY=VES   VED_LEGACY_RULE_CLEAR=1   RATE_CONVENTION_CLEAR=1 (1 MONEDA = X VES)
RATE_DATE_SELECTION_CLEAR=1 (APROBADA con la mayor fecha efectiva <= fecha de la operación)
PROVENANCE_CLEAR=1   MAKER_CHECKER_CLEAR=1   BUD08_CONSUMER_CLEAR=1   MONETARY_COMPARISON_CLEAR=1
P1_P2_OVERLAP=0 (no se tocan CNT-01 ni PROC-08)   MATERIAL_DECISION_REQUIRED=0   CONSTITUTION_GATE=PASS
```

## Decisiones de diseño (Claude)

| ID | Decisión |
|---|---|
| PDD-T09-01 | La selección es «vigente por fecha»: la mayor fecha efectiva ≤ D. No se exige una tasa del mismo día, porque el BCV no publica los fines de semana ni los feriados. |
| PDD-T09-02 | La evidencia exigida para aprobar es un documento con sha256 vinculado a la tasa, además de la referencia obligatoria. Es la opción más fuerte de §15. |
| PDD-T09-03 | La anulación (en BORRADOR o APROBADA) exige `approve` y MFA, con motivo de 10 o más caracteres. Los compromisos ya emitidos conservan su copia. |
| PDD-T09-04 | La copia de BUD-08 va dentro del `snapshot` inmutable y con huella: no se añaden columnas a una tabla con trigger de inmutabilidad. |
| PDD-T09-05 | ORG-03 conserva su rechazo de VED (borde ya incompatible). BUD-01, BUD-06 y BUD-08 normalizan al escribir. |
| PDD-T09-06 | Hay una vista previa de solo lectura de la verificación de límite, para que el sponsor vea la tasa antes de confirmar; el POST la recalcula y la copia recoge lo que realmente se usó. |

## Arquitectura

- **Backend:** `government/monedas.py` (canonical_currency, rate_to_ves); `models.GovernmentOfficialExchangeRate`; migración 0114 (tabla, índices únicos parciales, triggers, siembra de capacidades); `schemas_tasas.py`, `service_tasas.py` (crear, corregir, aprobar, anular, listar, detalle, tasa_aplicable, verificar_limite) y `api_tasas.py` (prefijo `/gobierno/tesoreria/tasas`); ResourceKind; auditoría; MFA; `setup/api.py`.
- **BUD-08:** `service_presupuesto_compromiso.emitir` delega en `verificar_limite`; ruta `GET /{year_id}/compromisos/verificacion-limite`. BUD-01 y BUD-06 normalizan la moneda.
- **Frontend:** `tesoreria/tasas/TasasOficialesPage.tsx` (lista con filtros, alta, detalle con historia, AdjuntosPanel, aprobar, corregir, anular), router, Sidebar, pantallas.ts; en `CompromisosEjercicio.tsx`, vista previa y bloque de conversión.
- **Precisión:** Numeric(28,12). El maestro privado usa (14,6), su copia (18,8) e importaciones (24,12); el BCV publica 8 decimales.
