# PUERTA PREVIA AL BACKFILL — ARCH-MC-001

Fecha: 2026-08-31 · Este documento decide si puede escribirse una sola fila.

## 1. Estado de las fases

| Fase | Estado |
|---|---|
| N0 · Gobierno y ADR | **COMPLETE** |
| N1 · `CompanyContext` | **COMPLETE** |
| N2 · Cortar la hemorragia | **COMPLETE** |
| **N3 · Expansión de esquema** | **COMPLETE** |
| **N4 · Preflight** | **COMPLETE** |
| N4 · Backfill | **NOT_STARTED** |
| N5 · Dominios | PENDING |
| N6 · Frontend | PENDING |
| N7 · Restricciones | PENDING |
| N8 · Contracción | PENDING |
| N9 · `REM-046-001` | PENDING |
| N10 · Convergencia | PENDING |

## 2. Condiciones de la puerta

| Condición | Exigido | Real | Resultado |
|---|---|---|---|
| PostgreSQL | 18.x | **18.6**, UTC | **PASS** |
| N0 · modelos con alcance declarado | 166 | 153 modelos, **0 sin declarar** | **PASS** |
| N1 · `CompanyContext` operativo | sí | cabecera validada en servidor | **PASS** |
| N2 · escritores incorrectos | **0** | **0** (234 remediados) | **PASS** |
| N2 · lectores incorrectos | **0** | **0** | **PASS** |
| Rutas derivadas por FK anulable | **0** | **0** | **PASS** |
| N3 · instalación limpia → `head` | PASS | PASS | **PASS** |
| N3 · SQL en modo offline | PASS | 172 sentencias | **PASS** |
| N3 · base legacy → `head` | PASS | 8 migraciones | **PASS** |
| N3 · datos legacy sin reinterpretar | sí | conteos y huella idénticos | **PASS** |
| N4 · preflight sin escrituras | sí | conteos y Alembic sin cambio | **PASS** |
| N4 · todas las tablas clasificadas | 80 | 80 | **PASS** |
| N4 · pruebas del clasificador | PASS | **17/17** | **PASS** |

## 3. Clasificación medida

| Clase | Filas |
|---|---:|
| `MC-A` determinista | 3 |
| `MC-B` reconstruible | 1 |
| `MC-C` ambigua | 2 |
| `MC-D` sin evidencia | 0 |
| **`MC-E` crítica** | **1** |
| `OK` ya correcta | 1 |
| **Total** | **8** |

Sobre el fixture legacy representativo. Una base de producción daría otras
cifras con el mismo ejecutor y los mismos criterios.

## 4. Crítico

| Criticidad | MC-C | MC-D | MC-E |
|---|---:|---:|---:|
| fiscal | 0 | 0 | **1** |
| financiero | 0 | 0 | 0 |
| inventario | 0 | 0 | 0 |
| no crítico | 2 | 0 | 0 |

El `MC-E` es una serie de numeración fiscal de un tenant que ya tenía dos
empresas cuando se creó, sin ninguna autoridad que desempate. **No se rellena.**

## 5. Restricciones

| Comprobación | Valor |
|---|---:|
| Filas que hoy impiden la FK a `companies` | 7 |
| Filas que quedarían nulas con `NOT NULL` | 0 |
| Únicos con `company_id` revisados | 13 |
| Colisiones al estrechar de tenant a empresa | **0** |
| Secuencias de PostgreSQL | 0 |

Las 7 que bloquean la FK son exactamente las que aún guardan el tenant.
Desaparecen con el backfill; ninguna es corrupción preexistente.

## 6. Decisión

```
BACKFILL AUTHORIZED: NO — CHECKPOINT REQUERIDO
```

**No es un fallo.** Es el punto de control pedido: primero se mide, luego se
decide, y solo entonces se escribe.

## 7. Lo que hay que decidir antes de autorizar

| Asunto | Quién decide |
|---|---|
| Qué hacer con el `MC-E` fiscal: revisión manual auditada, o dejar la serie sin empresa hasta que alguien la reclame | Negocio, con el especialista fiscal |
| Si las 2 filas `MC-C` de maestros se resuelven manualmente o se dejan marcadas | Negocio |
| Si el preflight debe ejecutarse sobre una copia de producción antes de autorizar | Producto |

Ninguno depende de esta implementación: son decisiones sobre datos reales.

## 8. Estado de lo bloqueado

| Elemento | Estado |
|---|---|
| Spec 012 | `APTA_DOCUMENTALMENTE — BLOCKED_BY_ARCH_MC_001` |
| `REM-046-001` | `BLOCKED_BY_ARCH_MC_001` |
