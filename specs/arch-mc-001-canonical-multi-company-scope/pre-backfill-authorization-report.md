# INFORME DE AUTORIZACIÓN PREVIA AL BACKFILL — ARCH-MC-001

Fecha: 2026-08-31 · Fase: N4 · **Preflight sobre datos reales**

---

## 1. Veredicto

```
REAL_DATA_PREFLIGHT BLOCKED — REAL DATA COPY NOT AVAILABLE
BACKFILL AUTHORIZED: NO
```

**No existe ningún conjunto de datos real que analizar.** No es un problema de
permisos ni de acceso: es que KONTROL todavía no ha estado en producción.

---

## 2. La evidencia de que no existe

Se buscó, no se supuso.

| Búsqueda | Resultado |
|---|---|
| Volcados o respaldos en el repositorio | **ninguno** |
| Volcados en `/home`, `/tmp`, `/var/tmp` | **ninguno** |
| Fichero `.env` con una base real | **no existe**; solo `.env.example` con `TU_HOST_DB` y `REEMPLAZAR_POR_CONTRASENA_SEGURA` |
| PostgreSQL escuchando con datos de negocio | **ninguno** |

Y lo que lo explica, en el propio gobierno del proyecto:

| Fuente | Dice |
|---|---|
| `56-specs-gap-analysis.md` · Spec **052** Instalador | *«**Nunca ejecutado**; sin rollback probado»* |
| `56-specs-gap-analysis.md` · Spec **053** Backup | `SKELETON_ONLY` — *«Scripts solo validados con `bash -n`»* |
| `KONTROL_GAP_ANALYSIS_ROADMAP_MAESTRO.md` | *«backup/restore nunca ejecutado, rollback nunca probado»* |
| `compose.yaml` | *«La base de datos es **EXTERNA** (cada cliente la suya)»* |

**El instalador nunca se ha ejecutado.** No hay una instalación de la que sacar
una copia, y por el modelo de despliegue tampoco habrá *una* base: habrá una por
cliente, cada una con su propia historia de empresas.

Clasificación del conjunto disponible, según el vocabulario del encargo:
**`REPRESENTATIVE_FIXTURE_ONLY`**.

---

## 3. Lo que **no** voy a hacer

No usar el fixture como sustituto de datos reales, ni presentar sus cifras como
si midieran riesgo efectivo. Sobre 18 filas sembradas por mí, un «97 % de
cobertura automática» sería un número cierto y completamente inútil: mediría mi
propia semilla, no la realidad de un cliente.

Las cifras del apartado 5 se presentan por lo que son: **la validación del
instrumento**, no la medición del paciente.

---

## 4. Aislamiento del entorno usado

| Comprobación | Estado |
|---|---|
| Producción afectada | **NO** — no existe |
| Base analizada | `kontrol_legacy`, sandbox local |
| PostgreSQL | **18.6**, UTC |
| Transacción de solo lectura | **sí**, `SET TRANSACTION READ ONLY` |
| Escritura rechazada por el motor | **verificado** — `ReadOnlySqlTransaction` |
| Workers, cron, colas | ninguno en ejecución |
| Salidas externas: SMTP, webhooks, pasarelas, SICA/SIGESAI/SACS | ninguna configurada |

---

## 5. Validación del instrumento

Sobre el fixture, con las formas del legado sembradas a propósito:

| Clase | Filas | Qué demuestra |
|---|---:|---|
| `MC-A` | 3 | Determinismo por intervalo, incluida la trampa del recuento actual |
| `MC-B` | 1 | La autoridad del dominio gana al intervalo |
| `MC-C` | 2 | Ambigüedad tras la segunda empresa: no se resuelve |
| `MC-D` | 0 | — |
| **`MC-E`** | **1** | Serie fiscal ambigua: crítica, bloquea su ola |
| `OK` | 1 | Lo ya correcto no se reclasifica |
| **`INVALID_LEGACY_SCOPE`** | **1** | Un valor huérfano es un dato **roto**, no un hueco |

| Garantía | Resultado |
|---|---|
| Cero escrituras | conteos y versión de Alembic idénticos |
| Repetibilidad | dos corridas, **0 diferencias** |
| Pruebas del clasificador | **23/23** |

---

## 6. Lo que se ha preparado para cuando exista la copia

| Capacidad | Estado |
|---|---|
| Clasificación `MC-A`..`MC-E` | Lista |
| `INVALID_LEGACY_SCOPE` y `CROSS_TENANT` | **Añadidas en esta fase** |
| `MASTER_ASSIGN` / `CLONE` / `DERIVE` / `MANUAL` / `BLOCKED` | **Añadidas en esta fase** |
| Determinismo por intervalo, con empresas inactivas incluidas | Listo y probado |
| Prioridad de evidencia: autoridad de dominio sobre intervalo | Lista |
| Conflicto entre autoridades: no se desempata solo | Listo |
| Solo lectura en dos capas | **Añadida en esta fase**, verificada |
| Preparación de FK, `NOT NULL` y únicos | Lista |
| Plan de backfill por tabla y contrato de paridad | Escrito |
| Olas y puertas por ola | Escritas |
| DAG de dependencias | Escrito |

Ejecutar el preflight sobre una copia real es, a partir de aquí, **un comando**.

---

## 7. Una decisión de producto que este hallazgo hace visible

El modelo es **una base por cliente**. Eso significa que no habrá un preflight,
sino **uno por instalación**: cada cliente tendrá su propia historia de empresas,
sus propios `MC-E` y su propia cola de revisión.

Con el instalador `Nunca ejecutado`, hay una oportunidad que conviene no
desaprovechar: **si ARCH-MC-001 se completa antes del primer despliegue, no
habrá backfill que hacer**. Ninguna instalación nueva nacería con el defecto, y
las clases `MC-C`, `MC-D` y `MC-E` no llegarían a existir.

El backfill solo hace falta para instalaciones que ya operan. Hoy no hay
ninguna.

---

## 8. Qué haría falta para autorizar el backfill

| Requisito | Estado |
|---|---|
| Copia aislada y autorizada del conjunto a migrar | **No disponible** |
| Fecha del snapshot y su antigüedad | n/d |
| Versión con N1/N2 desplegada en ese entorno | n/d |
| Respaldo verificado (Spec 053 operativa) | **`SKELETON_ONLY`** |
| Ventana de escritura acordada | n/d |

Ninguno depende de esta implementación.

---

## 9. Recomendación

1. **No autorizar backfill.** No hay nada que migrar.
2. **Continuar ARCH-MC-001 por N5** —normalizar los dominios— que no necesita
   datos reales y es lo que impide que el defecto siga creciendo.
3. **Reejecutar este preflight** contra la primera instalación real que exista,
   antes de su primera actualización. El instrumento ya está listo.
4. Si se decide desplegar antes de cerrar ARCH-MC-001, tratar ese despliegue
   como el punto donde empieza a acumularse deuda reconstruible, y fechar el
   snapshot desde el primer día.

---

## 10. Estado

| Elemento | Estado |
|---|---|
| N0 · N1 · N2 · N3 | COMPLETE |
| N4 · marco de preflight | **COMPLETE** |
| N4 · preflight sobre datos reales | **BLOCKED — no existe copia real** |
| N4 · backfill | `NOT_STARTED` |
| N5–N10 | PENDING |
| Spec 012 | `APTA_DOCUMENTALMENTE — BLOCKED_BY_ARCH_MC_001` |
| `REM-046-001` | `BLOCKED_BY_ARCH_MC_001` |

```
BACKFILL AUTHORIZED: NO — AWAITING EXPRESS AUTHORIZATION
```
