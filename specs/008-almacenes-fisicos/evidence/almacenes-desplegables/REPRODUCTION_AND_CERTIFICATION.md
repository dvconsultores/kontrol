# ALMACENES-DESPLEGABLES-TRUNCADOS · reproducción y certificación

## RED, antes del arreglo (`5335eb0`)
`selectoresDeAlmacen.test.tsx`, con servidor simulado fiel al contrato: 50 por defecto, 100 máximo, orden por código.

`WAREHOUSE_51_EXISTS = 1`, `WAREHOUSE_51_ACCESSIBLE_BY_ACTOR = 1`, `WAREHOUSE_51_RETURNED_BY_FIRST_PAGE = 0`, `WAREHOUSE_51_MISSING_FROM_SELECTOR_BEFORE_FIX = 1` en 8 pantallas, para los almacenes 51 y 120. PutAway y Preparación pasaban. El valor por defecto consta en `warehouse_api.py` (`limit: int = Query(50, ge=1, le=100)`); la reproducción usa el simulador, no el backend real.

`ROOT_CAUSE_PROVEN = 1`.

## Arreglo
`listAllWarehouses(companyId?)`, `useAlmacenesDeEmpresa` y `AvisoDeAlmacenes`. `BACKEND_CHANGE_REQUIRED = 0`.

Cambios de conducta deliberados:
- PutAway y Preparación pasan a clave de caché por empresa y envían `company_id`.
- Las diez pantallas muestran carga, vacío y error. Un fallo de página posterior no pinta lista parcial.
- Sin empresa activa, PutAway y Preparación ya no consultan.

## Verde
Vitest 1408, TSC, ESLint y build. Mutaciones: 15 de 15 muertas por aserción (M1 a M9 exigidas, más 6 de autoridad y avisos).

OpenAPI 689 = 689. Sin cambio de backend: SQLite `NOT_REQUIRED_FOR_FRONTEND_ONLY_CHANGE`.

## No ejecutado
E2E `almacenes-selectores.spec.ts` preparada, sin ejecutar: exige PostgreSQL. La interfaz no se ha comprobado en navegador real.
