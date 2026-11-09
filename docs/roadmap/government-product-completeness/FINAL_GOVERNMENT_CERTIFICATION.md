# FINAL_GOVERNMENT_CERTIFICATION — gate acumulado de KONTROL Gobierno

Creado por la directiva PRODUCT-FIRST de la dueña (2026-11-08). Durante la construcción, cada vertical se valida con pruebas funcionales, negativas materiales y una certificación razonable. Lo exhaustivo se ejecuta aquí, una vez, cuando Gobierno esté funcionalmente completo o llegue a un hito mayor.

## Campaña pendiente

PostgreSQL completo · SQLite completo · Alembic desde cero y desde la cabeza anterior · E2E completa en Chromium, Firefox y WebKit · mutaciones exhaustivas · OpenAPI global · seguridad · SoD · maker-checker · concurrencia · auditoría · aislamiento · accesibilidad · adaptación a pantallas · regresión canónica · regresión cruzada con Enterprise cuando corresponda · base tras la E2E · residuos · UAT integral.

## Pendientes acumulados por vertical

| Origen | Pendiente | Estado de lo ya medido |
|---|---|---|
| ORG-06 | PostgreSQL y SQLite completos sobre el árbol final | La última PG completa, sin `pg_dump` por error de montaje: 4654 pasan; 30 fallos de copias atribuidos al montaje y 1 por la carrera de CTL-10, ya corregida. Después, dirigido en PG 827/0. SQLite completa: 2793/0, anterior a la corrección de CTL-10 |
| ORG-06 | Regresión de Gobierno, E2E canónica y controles de base tras la E2E | No ejecutados sobre ORG-06 |
| ORG-06 | E2E en los tres navegadores sobre el árbol final | 27/27 antes de los últimos arreglos, que no tocan frontend salvo la fecha de una prueba; después, Chromium 3/3 |
| CTL-02 | PostgreSQL y SQLite completos, regresión de Gobierno, E2E canónica, tres navegadores, mutaciones y controles de base tras la E2E | Dirigido en PG 1212/0, incluye núcleo de auditoría, autenticación, aislamiento y copias. Vitest 1430/1430. BIT-E2E-01 en Chromium con Axe a tres anchos. Sin mutaciones |
| PROC-02 | PostgreSQL y SQLite completos, regresión de Gobierno, E2E canónica, tres navegadores, mutaciones, Axe en las pantallas, controles de base tras la E2E y runner de integridad con controles propios | Backend dirigido y E2E Chromium; ver el inventario de la vertical |
| PROC-03 | PostgreSQL y SQLite completos, regresión de Gobierno, E2E canónica, tres navegadores, mutaciones, Axe en las pantallas, prueba de Vitest de las pantallas, controles de base tras la E2E, runner de integridad, y acciones no ejercitadas por interfaz (ver tarjeta) | Backend dirigido 1208/0 antes de la corrección final; dirigido posterior 172 pruebas con 1 fallo (OBS-N9-COLISION-01); E2E Chromium 2/2 |

## Observaciones abiertas

| Id | Observación | Severidad |
|---|---|---|
| OBS-PG-LOCKS-01 | La restauración usa `pg_restore --single-transaction`. Soltar el esquema toma 6305 bloqueos y el techo medido con los valores por defecto de PostgreSQL es 12851. No se midió cuántos toma la restauración ni qué valor tiene producción. Hay que medirlo antes de que el esquema crezca mucho más | MEDIA |
| OBS-CTL10-CC01 | `test_cc01` falló 5 de 60 veces en `fba4a31`: CTL-10 se certificó con una carrera latente que daba 500. Corregida en ORG-06 con la prueba determinista `test_cc01b`. Conviene buscar el mismo patrón (índice único parcial sin captura de `IntegrityError` en la transición) en otras verticales | MEDIA |
| OBS-E2E-FECHA-01 | Una E2E calculaba «ayer» con la fecha UTC y solo pasaba de madrugada. Corregida en ORG-06. `rates.spec.ts` y `receipts.spec.ts` (Enterprise, fuera de P1) usan un cálculo parecido, sin verificar si les afecta | BAJA |
| OBS-QA-SONDA-01 | Las sondas de `test_pgs_26` compiten por `CREATE EXTENSION` en una base de QA recién creada. No ocurre dentro de la suite | BAJA |
| OBS-AUDIT-403-01 | Los 403 por capacidad no generan evento, tampoco en la bitácora: registrarlos exige tocar la ruta común de permisos. Quedan registrados rechazos y denegaciones de negocio y de autenticación. Decidir si Gobierno los necesita | MEDIA |
| OBS-BITACORA-RENDIMIENTO-01 | Los filtros por funcionario y unidad buscan en el JSON como texto, acotados por tenant y ente. Medir con volumen real antes de producción | BAJA |
| OBS-UI-NOTIF-01 | Las notificaciones de la plataforma tapan los botones de la cabecera mientras se muestran, y una de empresa persiste. Afecta a las pantallas con acciones arriba a la derecha | BAJA |
| OBS-N9-COLISION-01 | Cerrada en 12d7980: código único por kind; N9 en verde en PostgreSQL. | Cerrada |
| OBS-UI-320-01 | Cerrada: defecto del armazón compartido, corregido; a 320 y 390 px con carga directa, sin desborde del documento y con menú en panel. Queda 1 px de desplazamiento interno en la ficha a 320 px. | Cerrada |
| OBS-HUMO-EXP-01 | Cerrada en 12d7980: el humo publicado cubre Expedientes. | Cerrada |
