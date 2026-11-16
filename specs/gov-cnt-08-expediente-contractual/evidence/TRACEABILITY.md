# CNT-08 · Trazabilidad (22/22)

Las pruebas PG están en `tests/test_gov_cnt08_expediente_contractual.py`; la E2E, en `e2e/gobierno-expediente-contractual.spec.ts`.

| Contrato | Código | Prueba |
|---|---|---|
| C08-01 Raíz contractual | `contrato_formalizado` (404 de otra empresa por `_cargar`; 409 en BORRADOR) | `test_borrador_y_aislamiento`; M6 muerta |
| C08-02 Origen | `proyeccion` → `origen` (PROC-03 y PROC-06) | `test_expediente_completo`; E2E paso 4 |
| C08-03 Presupuesto | `certificados_trazados`, `compromisos_trazados`, `control_compromisos`, «efectos» | `test_expediente_completo`; E2E paso 6 |
| C08-04 Contrato original | `instrumento.original` sale de `ficha` de CNT-01 | `test_expediente_completo` (50000.00 y la ficha intacta); M1 muerta |
| C08-05 Condiciones vigentes | `historia(...)["vigente"]` de CNT-02, sin recalcular | `test_expediente_completo` (60000.00); E2E pasos 7–8 |
| C08-06 Garantías | `_garantias_publicas` (PROC-10) | E2E paso 9 |
| C08-07 Supervisión | `supervision` y `supervisor_vigente` de CNT-04; consulta en una fecha | `test_expediente_completo` (SUP-01); E2E paso 10 |
| C08-08 Ejecución | Integrada con CNT-03 publicado por P1 (0119): `ejecucion` y `resumen.ejecucion` salen de `service_contratos_ejecucion.ejecucion`, y `_eventos_cnt03` lleva sus hechos a la cronología; P2 no escribe hitos, entregables ni valuaciones | `test_ejecucion_cnt03_integrada`; Vitest (d); E2E paso 11 |
| C08-09 Índice documental | `entradas_documentales` y `EntradaDocumental.publico`; `sellado` respeta el sello (D08-09): sin descarga suelta, EXCLUIDO por SELLADO en el paquete | `test_expediente_completo`; `test_documento_sellado`; Vitest (c); E2E pasos 12–13 |
| C08-10 Actos | `_actos_publicos` (DOC-02) | E2E paso 5 |
| C08-11 Cronología | `cronologia_completa` y `cronologia` (orden jurídico, filtros, paginación; excluye CONTRATO y GARANTIA de PROC-03) | `test_cronologia_orden_filtros_y_paginacion`; M2 muerta; E2E paso 15 |
| C08-12 Auditoría | `auditoria` (AuditEvent por `entity_id`, `_resumenes`) | `test_auditoria_acotada_y_permiso`; E2E paso 16 |
| C08-13 Integridad | `resultado_integridad` (VERIFIED, MISSING, MISMATCH, NOT_APPLICABLE) | `test_integridad`; M3 muerta; E2E paso 14 |
| C08-14 Acceso de control fiscal | Permisos existentes; `permisos` en la respuesta; solo lectura | `test_auditoria_acotada_y_permiso`; `test_mfa_y_permisos_reutilizados` |
| C08-15 Paquete | `generar` con las primitivas de DOC-08; ZIP determinista; SHA256SUMS | `test_paquete_generar_descargar_verificar`; E2E pasos 17–18 |
| C08-16 Verificación | `verificar` (VALIDO, INVALIDO, INCOMPLETO y PAQUETE_NO_REGISTRADO) | `test_paquete_generar_descargar_verificar`; M5 muerta; E2E paso 19 |
| C08-17 Snapshot | REPEATABLE READ en `generar` | `test_paquete_snapshot_consistente`; M4 muerta |
| C08-18 Aislamiento | `company_id` y `tenant_id` en cada consulta | `test_borrador_y_aislamiento`; verificación desde otra empresa; E2E paso 20; barridos ISO |
| C08-19 Listados acotados | `limit`/`offset` (100 en la lista, 200 en la cronología) | `test_listado_filtros_y_paginacion` y cronología (422 por encima del límite) |
| C08-20 Navegación a la fuente | `enlace` en cada elemento | `test_expediente_completo` (enlace de la modificación); E2E |
| C08-21 Fuentes futuras | `FUENTES_FUTURAS` (CNT-05, CNT-06, CNT-07, TRE-04); CNT-03 salió de la lista al publicarse | `test_expediente_completo` |
| C08-22 E2E y UAT | E2E del sponsor, OWNER_UAT_CARD | E2E 1/1 y humo UAT |
