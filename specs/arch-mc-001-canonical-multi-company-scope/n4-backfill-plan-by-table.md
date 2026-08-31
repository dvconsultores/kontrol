# PLAN DE BACKFILL POR TABLA — ARCH-MC-001

**Nada de esto se ha ejecutado.** Es el contrato que el backfill deberá cumplir
cuando se autorice, escrito antes de escribir para poder contrastarlo después.

## 1. Contrato de paridad

Lo que el backfill **no puede cambiar**, en ninguna tabla:

| Grupo | Ejemplos |
|---|---|
| Importes | totales, impuestos, bases imponibles, retenciones |
| Cantidades | existencias, cantidades de línea, cantidades base |
| Numeración | números de documento, de control, correlativos |
| Fechas | emisión, vencimiento, contabilización |
| Referencias | claves foráneas ajenas al alcance |

Lo único que cambia es **la propiedad**: `company_id`, `legacy_scope_id`,
`scope_backfill_class` y las relaciones estrictamente necesarias.

## 2. Forma de cada paso

Para cada tabla, en este orden:

```
1. contar   → filas por clase, antes de tocar nada
2. escribir → solo MC-A y MC-B, con predicado explícito
3. guardar  → el valor anterior va a legacy_scope_id
4. marcar   → scope_backfill_class registra con qué clase se decidió
5. verificar→ el número de filas actualizadas coincide con lo previsto
6. abortar  → si no coincide, se revierte la ola completa
```

> **Guarda de recuento.** Si el `UPDATE` afecta a un número distinto del
> previsto, se aborta. Un `UPDATE` que toca de más es indistinguible de uno
> correcto hasta que alguien revisa un libro.

## 3. Tratamiento por clase

| Clase | Qué hace el backfill |
|---|---|
| `MC-A` | Rellena con la única empresa que existía en el intervalo |
| `MC-B` | Rellena con la empresa que dice su autoridad |
| `MC-C` | **No toca la fila.** Marca la clase y la encola para revisión |
| `MC-D` | Ídem |
| `MC-E` | Ídem, y **bloquea su ola** |
| `INVALID_LEGACY_SCOPE` | No toca. Se reporta como dato ya roto, no como pendiente |
| `CROSS_TENANT` | No toca. **P0 de integridad**, se escala antes de seguir |
| `OK` | No toca: ya es correcta |

## 4. SQL previsto — forma general

Para `MC-A` (determinista por intervalo):

```sql
UPDATE <tabla> t
   SET legacy_scope_id       = t.company_id,
       company_id            = :empresa,
       scope_backfill_class  = 'MC-A'
 WHERE t.company_id = :tenant
   AND t.created_at < :corte_multiempresa
   AND t.legacy_scope_id IS NULL;
```

Para `MC-B` (derivada de su autoridad):

```sql
UPDATE <tabla> t
   SET legacy_scope_id       = t.company_id,
       company_id            = a.company_id,
       scope_backfill_class  = 'MC-B'
  FROM <autoridad> a
 WHERE a.id = t.<columna_autoridad>
   AND t.legacy_scope_id IS NULL
   AND a.company_id IS NOT NULL;
```

Ningún `UPDATE` sin `WHERE` acotado. Ninguno sin `legacy_scope_id IS NULL`, que
lo hace idempotente: repetirlo no vuelve a tocar lo ya migrado.

## 5. Olas propuestas

El orden lo fija el DAG, no la prioridad declarada:

| Ola | Contenido | Depende de |
|---|---|---|
| 1 | Autoridades: accesos usuario–empresa | — |
| 2 | Maestros | 1 |
| 3 | Compras · inventario · ventas (raíces) | 2 |
| 4 | Financiero: CxP, CxC, tesorería | 3 |
| 5 | **Fiscal** | 2, 3, 4 |
| 6 | Regulatorio, auditoría, eventos, informes | todas |

Cada ola es autorizable por separado. Un bloqueo en la 5 no impide cerrar la 3.

## 6. Puerta por ola

| Paso | Exigencia |
|---|---|
| Antes | Respaldo o punto de restauración |
| Antes | Recuento previo por clase |
| Durante | `UPDATE` con predicado y guarda de recuento |
| Después | Recuento posterior coincide con lo previsto |
| Después | Paridad de importes, cantidades y números |
| Después | Aislamiento A/B probado en ese dominio |
| Después | Ningún escritor incorrecto nuevo |

## 7. Recuperación

Cada ola es reversible mientras no se ejecute la contracción (N8): el valor
anterior sigue en `legacy_scope_id`.

```sql
UPDATE <tabla>
   SET company_id = legacy_scope_id,
       legacy_scope_id = NULL,
       scope_backfill_class = NULL
 WHERE scope_backfill_class = :clase;
```

Después de N8 ya no hay vuelta atrás, y por eso N8 va al final y no antes.

## 8. Precondiciones que no dependen del código

| Precondición | Por qué |
|---|---|
| Respaldo verificado | La Spec 053 está `SKELETON_ONLY`: los guiones solo se validaron con `bash -n` |
| Versión con N1/N2 desplegada | Si no, entre el snapshot y la migración se siguen creando filas con el tenant |
| Ventana sin escritura, por dominio | Evita que una fila cambie mientras se clasifica |
| Preflight repetido sobre el snapshot final | Este informe caduca en cuanto la base sigue recibiendo escrituras |
