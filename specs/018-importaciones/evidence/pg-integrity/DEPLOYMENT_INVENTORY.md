# Inventario de despliegue de Importaciones (solo lectura)

**PRODUCTION_IMPORTS_DEPLOYMENT_STATUS = UNKNOWN.** No se conectó a ningún entorno. `PRODUCTION_TOUCHED = 0`.

| Fuente revisada | Qué muestra |
|---|---|
| Ramas remotas | Solo existe `develop` |
| `.github/workflows/build-main.yml` | Publica la etiqueta de producción `main` al hacer push a `main`, que no existe. Por este flujo, esa etiqueta no se pudo generar |
| `.github/workflows/build-dev.yml` | Cada push a `develop` publica imágenes `latest` |
| `compose.yaml` | Etiqueta por defecto `latest`, Watchtower activo, y `alembic upgrade head` al arrancar |
| `docs/roadmap/next-spec-decision.md` (2026-09-16) | «No hay instalaciones desplegadas». Es anterior a Importaciones |
| Registro de imágenes, CI remoto, manifiestos o registros de migración de un entorno real | **Sin acceso** |

## Conclusión

No hay evidencia de un despliegue con Importaciones, y tampoco evidencia de que no exista. Falta saber si algún entorno corre con `latest`.

## Riesgo que debe conocer la dueña

Un entorno con `latest` y Watchtower recibe solo cada push a `develop` y aplica las migraciones al arrancar. Eso significa dos cosas:

- Si existe, hoy puede tener el defecto: crear un expediente falla con 500.
- Si existe, este push le aplicará `0086` y `0087` automáticamente. `0086` solo añade defaults y no reescribe filas.

Una instalación con la etiqueta `main` no recibe nada de esto.
