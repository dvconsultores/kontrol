# INVENTARIO DE LO TRANSITORIO — N8

## 1. Las dos columnas

`legacy_scope_id` y `scope_backfill_class`, en **80 tablas**, añadidas por las
migraciones `0025`–`0031`.

Su propósito era guardar el valor anterior y la clasificación de cada fila
mientras un backfill reconstruía la empresa. **Ese backfill nunca hizo falta**:
no existe ninguna instalación desplegada, así que la ventana se cerró antes de
que hubiera nada que reconstruir.

## 2. Clasificación de cada hallazgo

| Dónde | Cuántos | Clase | Acción |
|---|---:|---|---|
| Migraciones `0025`–`0031` | 7 ficheros | `MIGRATION_ONLY` | Se conservan: son el histórico |
| Modelos ORM | **0** | — | Nada que retirar |
| Servicios, repositorios, esquemas | **0** | — | Nada que retirar |
| Pruebas funcionales | **0** | — | Nada que retirar |
| Frontend | **0** | — | Nada que retirar |
| Esquema de PostgreSQL | 80 tablas | `ACTIVE_RUNTIME_LEGACY` | **Retiradas** en `0038` |

## 3. Lecturas y escrituras antes del borrado

| | |
|---|---:|
| Lecturas en runtime | **0** |
| Escrituras en runtime | **0** |
| Dependencias del clasificador de N4 | **0** |
| Dependencias de fixtures | **0** |

Nunca llegaron al modelo operativo, así que retirarlas fue un `DROP` limpio y no
una desconexión. Es el mejor resultado posible y conviene decir por qué ocurrió:
N3 las creó por precaución, N4 concluyó que no había nada que migrar, y entre
una cosa y otra nadie las conectó.

## 4. Lectura doble, escritura doble, repliegues

Se buscaron los patrones —`coalesce`, `nuevo or heredado`, escritura simultánea
de ambos, `company_id or tenant_id`— y el resultado fue:

| Patrón | Encontrados |
|---|---:|
| Lectura doble | **0** |
| Escritura doble | **0** |
| Repliegue de empresa a tenant | **1** |
| Cargas útiles con propiedad heredada | **0** |

El único hallazgo activo es `warehouse_in_tenant_scope`, tratado en
`n8-fallback-removal-report.md`.

## 5. El módulo de migración ya estaba aislado

Importaciones de `app.core.mc` desde módulos productivos: **0**. No hizo falta
separarlo; hizo falta que siguiera funcionando, que es otra cosa y resultó ser
el trabajo real de la fase.

## 6. Lo que se conserva a propósito

Las migraciones `0025`–`0031` mantienen su texto. No se reescriben para fingir
que las columnas nunca existieron: la evidencia histórica de por qué se
añadieron es lo que explica por qué se pueden retirar.
