# Plan · CNT-07

## Arquitectura

**Autoridad nueva:** `app/modules/government/service_contratos_terminacion.py`, con estas funciones:

| Función | Qué hace |
|---|---|
| `situacion_contractual(db, company_id, contract_id, fecha)` | SITUACION (C07-14). Sin contexto de usuario, para que la usen las guardas y CNT-09 |
| `fecha_limite(db, company_id, contract_id)` | `date \| None` |
| `exigir_vigente_en(db, company_id, contract_id, fecha)` | Lanza `GOV_CONTRACT_TERMINATED` si `fecha > fecha_limite` |
| `vista(db, ctx, user, contrato_id)` | VISTA, con `requisitos` y `consecuencias` |
| `crear_borrador`, `actualizar_borrador`, `descartar_borrador` | Crean, editan con `If-Match` y descartan el borrador |
| `formalizar(db, ctx, user, contrato_id, version)` | Formaliza la actuación |
| `reporte_csv(db, ctx, figura, desde, hasta)` | `(nombre, bytes)` |
| `requisitos(db, ctx, contrato, t)` | Lista de requisitos; la usan `vista` y `formalizar`, que aplica exactamente los mismos |

**Piezas reutilizadas:**
- **DOC-02:** `GovernmentAct`, `_autoridad_valida` y `_etiqueta_acto`.
- **Identidad:** `exigir_autoridad_funcional`.
- **DOC-04:** `GovernmentNotification` y `clave_identificacion`.
- **CNT-03:** `ejecucion()`, `terminos_efectivos()` y `_flujo`.
- **CNT-01:** `_documento_valido`, `verificar_integridad`, `sellar_documento` y `congelar_vinculo`, como en CNT-02.
- **PROC-10:** `GovernmentContractGuarantee` / `_garantias`.
- **BUD-08:** compromisos del expediente, con el mismo filtro que `compromisos_trazados`.
- **SoD:** `evaluar_antes_de_actuar`.
- **Auditoría:** `_auditar` y `record_audit_after_rollback`.

**Consumidores (guardas mínimas, una llamada a `exigir_vigente_en` en cada punto de spec §Guardas):**
- `service_contratos_ejecucion.py` (CNT-03, de P1);
- `service_contratos_modificaciones.formalizar` (CNT-02);
- `service_contratos_supervision.designar` (CNT-04);
- `service_contratos_alertas.condiciones` (CNT-09): excluye los contratos con `situacion_contractual(..., hoy).estado == "EXTINGUIDO"`;
- `service_contratos.ficha` (CNT-01): añade `situacion`.

**CNT-08:** `ORDEN_PROCESO` incorpora CNT-07 después de CNT-03. Además:
- `FUENTES_FUTURAS` pierde CNT-07;
- `proyeccion` gana `terminacion`, con SITUACION y TERMINACION formalizada;
- `_eventos_cnt07` añade a la cronología un evento por la apertura (si la hay) y otro por la formalización, con la fecha del acto, la de registro y la de eficacia separadas;
- `ids_del_expediente` incluye el id de la terminación;
- el manifiesto la recoge sola desde `ORDEN_PROCESO`.

**Frontend:**
- `modules/gobierno/contratos/TerminacionContratoPage.tsx`, en la ruta `gobierno/contratos/:contratoId/terminacion` (registrada en `pantallas.ts` con `gobierno_contratos:view`).
- Enlace «Terminación / resolución / rescisión» en `ContratoPage`, junto a «Ejecución del contrato», y la situación en la cabecera.
- En CNT-08, sección 10 «Terminación / resolución / rescisión»: pasan a ser 15 secciones.

**Migración:** `0122_gov_cnt07_terminacion`, que contiene:
- la tabla, los índices y el trigger PG;
- la concesión de `gobierno_contratos:terminate` a FUNCIONAL_COMPLETO, con el patrón de 0119.

**Catálogos:**
- `CATALOGO_DE_PERMISOS` y `SENSITIVE_PERMISSIONS`;
- `audit_catalog_entries`: +5, con lo que el catálogo pasa de 579 a 584;
- `CATALOGO_SOD["PROC-03"]`: +2.

## Pruebas

| Tipo | Contenido |
|---|---|
| PG | `tests/test_gov_cnt07_terminacion.py`: los casos de §46 del encargo |
| Mutaciones | M1–M8 del encargo |
| Vitest | `TerminacionContratoPage.test.tsx`, más el ajuste de las 15 secciones en el expediente |
| E2E | `e2e/gobierno-contratos-terminacion.spec.ts`: recorrido del sponsor de §48 y negativos de §49, a 1280, 390 y 320 px, con Axe |

## Riesgos

- **Ficheros compartidos con P1:** `router.tsx`, `pantallas.ts`, `ContratoPage`, `service_contratos_ejecucion` y `models.py`. Se reconcilian con una fusión ordinaria.
- **Tope de DeepSeek de 8 llamadas:** las tareas son grandes y autocontenidas, y los reintentos van con defectos exactos tras la sonda.
