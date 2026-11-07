# Delta CTL-10 POST-CLOSURE-01 · T042 y T043

Autorización: encargo GOV-CTL-FUNCTIONAL-04 · CTL-10 POST-CLOSURE-01 de la dueña, que nombra T042 y T043. Decisiones: OD-CTL10-T042 = IMPLEMENT_FILTERED_CONTEXT_LINK; OD-CTL10-T043 = IMPLEMENT_REQUIRED_TEST.

## T042 · OBS-CTL10-LISTA-01

- **Requisito:** spec, Edge Cases: «Más de 5 pendientes: la muestra trae 5 y el total el recuento real; el enlace de lista lleva a la lista filtrada.»
- **Comportamiento actual:** `ruta_lista` es `/gobierno/hallazgos` o `/gobierno/actos`; ambas abren la lista completa.
- **Causa raíz:** la guarda no emite contexto, y las dos listas tampoco leen la URL. Además, la lista de hallazgos no puede expresar la población del control: sus filtros son `estado` exacto y `riesgo` exacto, y el control cuenta «distinto de CERRADO con riesgo igual o superior».
- **Diseño:**
  - Hallazgos: `/gobierno/hallazgos?abiertos=true&riesgo_minimo=<R>`. Dos filtros opcionales y aditivos en la lista y en el CSV; sin ellos, el resultado no cambia.
  - Actos: `/gobierno/actos?anio=<ejercicio>&estado=EMITIDO`. Filtros ya existentes, solo frontend. El año se añade al selector si está fuera de los seis recientes.
  - La URL es la fuente de verdad, igual que `regla_id` en Conflictos SoD. Un envoltorio remonta la lista con `key` al cambiar la URL, de modo que volver por el menú limpia el contexto.
  - Un valor de URL no válido se ignora: se ve la lista general.
  - Hallazgos muestra un aviso visible con «Quitar filtro»; «Limpiar filtros» también lo retira. En actos los filtros ya son visibles en sus selectores.
  - La población de riesgo tiene una sola fuente: `riesgos_desde` en `service_hallazgos`, usada también por CTL-10.
- **Fuera:** pantalla nueva, menú nuevo, permisos, esquema. MIGRATION_ADDED = 0. CROSS_VERTICAL_SEMANTIC_CHANGE_REQUIRED = 0.

## T043

- **Requisito:** spec, Edge Cases, y FR-013: muestra de hasta 5 y total real.
- **Esperado:** con más de 5 pendientes, `muestra` trae 5, `pendientes` el recuento real, `details.total` lo suma, y la lista enlazada devuelve ese mismo total.

## ROUTES_ALLOWED

`resources/backend/app/modules/government/{service_hallazgos,schemas_hallazgos,api_hallazgos,service_cierres}.py` · `resources/backend/tests/test_gov_ctl10_lista_contexto.py` · `resources/frontend/src/modules/gobierno/api.ts` · `resources/frontend/src/modules/gobierno/hallazgos/HallazgosPage{,.test}.tsx` · `resources/frontend/src/modules/gobierno/actos/ActosPage{,.test}.tsx` · `resources/frontend/src/modules/gobierno/cierres/BloqueoDeCierre.test.tsx` · `resources/frontend/e2e/gobierno-cierres.spec.ts` · fixtures regenerados de frontend · evidencia de este delta.

## ROUTES_FORBIDDEN

Otras Specs de Gobierno, Enterprise, copia y RPO, SPEC057, TRE-08, producción, infraestructura, núcleo compartido, menús, migraciones, SNAT.
