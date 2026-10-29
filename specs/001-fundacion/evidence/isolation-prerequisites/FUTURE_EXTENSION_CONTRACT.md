# FUTURE_EXTENSION_CONTRACT — cómo encajaría Gobierno en el modelo de alcance (ciclo 07)

**Solo arquitectura. No autoriza implementar nada.** `GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0`. Aquí no se crean modelos, tablas, migraciones, rutas ni pantallas de Gobierno.

## 1. Dimensiones

| Dimensión | Hoy | Futuro (línea base `9a41503`) | No equivaler |
|---|---|---|---|
| tenant | frontera dura de datos (OD-ISO-01) | alojará uno o varios `GovernmentEntity` en una instalación de Gobierno | tenant ≠ ente (§7 del encargo) |
| company | alcance de autorización dentro del tenant (OD-ISO-02) | no aplica a Gobierno (la empresa privada es una entidad comercial) | company ≠ ente |
| entity | — | unidad de aislamiento de Gobierno (TENANT_SCOPE_CONTRACT): `entity_id NOT NULL` con FK en toda fila de Gobierno | — |
| unit | — | alcance de usuario dentro del ente (ORG_SCOPE_CONTRACT), con jerarquía explícita | — |
| authority | — | `AuthorityGrant` vigente en la fecha civil (AUTHORITY_SCOPE_CONTRACT) | — |

## 2. Puntos de extensión

Son las primitivas del núcleo que Gobierno extendería, sin duplicar autorización (OD-ISO-09):

1. **`app/core/scope.Scope`.** Se añade `ENTITY` (y, si procede, `UNIT`) al enum. Las guardas vigentes ya exigen `__scope__` en todo modelo y la ruta de autoridad en los derivados (`__scope_authority__`, con FK no anulable). La lista cerrada `ALCANCE_DE_INSTALACION_JUSTIFICADO` (`tests/test_iso_guardas.py`) sigue exigiendo motivo para lo que no se aísla.
2. **Contexto por petición.** `CompanyContext` es el patrón: la cabecera propone y el servidor resuelve, valida y autoriza. Un `EntityContext` análogo saldría de la vinculación persona → cargo → ente (GOV-ORG-007). El frontend nunca decide (guarda `src/tests/alcance-frontend.test.ts`).
3. **Contrato de relaciones.** La regla «cargar el objeto relacionado y comprobar su dimensión antes de persistir; ajeno = inexistente» (`SCOPE_ERROR_MATRIX.md`) se aplica igual con `entity_id`.
4. **Escáner de invariantes.** `app/ops/scope_scan.py` resuelve la «empresa de cada fila» por columna o por cadena de autoridad. Añadir `entity_de(tabla)` con la misma técnica (subconsulta con rol) da la regla «ninguna arista cruza entes» sin código nuevo de recorrido.
5. **Arnés hostil.** `tests/hostil_mundo.py` declara `DIMENSIONES = ("tenant", "company")`. Gobierno añadiría `"entity"`, `"unit"` y `"authority"` y sus recetas de siembra con centinelas. `CasoHostil` y `ejecutar_caso` ya comprueban estado, código, ausencia de fugas, inmutabilidad y auditoría. Los barridos (`tests/test_iso_barridos.py`) recorren automáticamente toda ruta nueva que dependa del contexto.
6. **Guardas de rutas.** Toda ruta sin contexto necesita clase y motivo (`RUTAS_SIN_EMPRESA_CLASIFICADAS`). Las rutas `/api/v1/gov/...` dependerían del contexto de ente o quedarían clasificadas.
7. **Almacén.** El aislamiento es por mapeo opaco validado (`STORAGE_SCOPE_INVENTORY.md`). La línea base de Gobierno pide un `storage_key` con prefijo de ente: es compatible, porque el prefijo solo organiza el espacio y la autoridad sigue siendo la fila acotada. Es una decisión de Gobierno, sin migrar claves del núcleo (OD-ISO-07).
8. **Copia y restauración.** El ciclo 06 restaura por instalación. «Restaurar un ente sin exponer otro» exige exportar e importar por ente, que es de Gobierno y queda fuera.

## 3. Requisitos de Gobierno que el núcleo deja como punto de extensión

| Requisito | Estado en el núcleo | Qué falta (Gobierno) |
|---|---|---|
| RNF-GOV-001: aislamiento de datos, llaves, configuración y permisos | datos y permisos: tenant/empresa certificados (ciclo 07); llaves: secretos por instalación | llaves y configuración por ente (`TenantPolicy`, secretos de integración por ente) |
| E2E-06: «100 % denegado **y auditado**» | denegado: certificado; auditado: solo `COMPANY_SCOPE_DENIED` (403); el 404 de no enumeración no se audita (ciclo 04) | hay que decidir si un intento entre entes genera un evento propio (p. ej. `GOV_SCOPE_DENIED`) sin inundar la bitácora; requiere entrada nueva de catálogo y OD de Gobierno |
| GOV-ORG-001: sin compartir reglas entre tenants | OD-ISO-10 elimina la escritura global desde empresa; las fuentes legales siguen siendo de instalación (P4) | perfil normativo por ente |
| GOV-CTL-004: el administrador técnico sin autoridad funcional | hoy la configuración de instalación (licencia, homologación, fuentes legales) la muta un administrador de tenant | rol de plataforma separado (deuda INSTALLATION-AUTHORITY-FROM-ANY-TENANT, §11 del delta) |
| ORG_SCOPE y AUTHORITY_SCOPE | no existen (`branch_ids` está latente) | unidades y grants; `UserScope.branch_id` como precedente sin escritor |

## 4. Prohibido mientras no haya autorización

Implementar `GovernmentEntity`, `GovernmentUnit` o `AuthorityGrant` · tablas `gov_*` · rutas `/api/v1/gov` · pantallas de Gobierno · condicionales «si es Gobierno» en el núcleo.

`FUTURE_GOV_SCOPE_EXTENSION_CONTRACT = COMPLETE`.
