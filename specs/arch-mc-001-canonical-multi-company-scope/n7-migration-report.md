# MIGRACIONES — N7

## 1. La cadena

| Migración | Qué hace | Tablas |
|---|---|---:|
| `0033_n7_company_fk` | Claves foráneas de empresa | 80 |
| `0034_n7_tenant_fk` | Claves foráneas de tenant, más la empresa de la auditoría | 5 |
| `0035_n7_not_null` | Empresa obligatoria | 9 |
| `0036_n7_consistency` | Coherencia empresa/almacén por clave compuesta | 5 |
| `0037_n7_tenant_company_fk` | Empresa opcional pero referenciada | 9 |

Head anterior: `0032_mc_expand_tenant_scoped`
Head nuevo: `0037_n7_tenant_company_fk`

Cinco migraciones separadas por naturaleza del cambio, no por dominio. Si una
falla, se sabe qué clase de garantía quedó sin aplicar; revertir una clase es
limpio, revertir «lo de compras» no lo sería.

Ninguna migra datos. Son cambios de esquema puros.

## 2. Instalación limpia

PostgreSQL 18.6 vacío → `alembic upgrade head`.

| Resultado | |
|---|---:|
| Migraciones aplicadas | 37 |
| Claves foráneas resultantes | 327 |
| Head | `0037_n7_tenant_company_fk` |

## 3. SQL sin conexión

`alembic upgrade 0032:head --sql` produce **105** sentencias `ALTER TABLE` /
`ADD CONSTRAINT` válidas. Se pueden revisar antes de aplicarlas, que es lo que
un cliente con una instalación seria va a querer hacer.

## 4. Fixture hostil: la prueba que debe fallar

Se preparó una base en `0032` y se sembró a propósito el defecto histórico de
KONTROL: un tercero cuyo `company_id` es el identificador del **tenant**.

Al migrar a head:

```
ForeignKeyViolation
violates foreign key constraint "fk_parties_company"
```

| Comprobación | Resultado |
|---|---|
| La migración aborta | **sí** |
| `alembic_version` avanza | **no**: se queda en `0032` |
| Escrituras parciales | **ninguna**: 242 claves, exactamente la línea base |
| La fila hostil sobrevive | **sí**, intacta |

Que falle **es** el resultado correcto. Una instalación con datos heredados
inválidos tiene que detenerse y avisar, no inventarse una empresa para que la
migración pase.

## 5. Una lección de método

El primer intento de este fixture sembró mal —una columna que no existe— así que
la migración pasó y pareció que no había nada que probar. Un fixture hostil que
no llega a insertar datos hostiles no demuestra nada, y habría quedado
registrado como evidencia de aborto sin serlo.

Se rehízo consultando las columnas obligatorias reales antes de insertar.

## 6. Reversión

Cada migración tiene su `downgrade`. Como no migran datos, revertir es exacto:
se retira la restricción y el esquema vuelve al estado anterior sin pérdida.

## 7. Contrato para las Specs futuras

**Spec 052 — instalador.** Una actualización de una instalación con datos exige,
en este orden: respaldo verificado, preflight aislado, migración de datos,
verificación y solo entonces validación de restricciones. El fixture hostil
demuestra por qué: sin ese orden, la migración se detiene a mitad.

**Spec 053 — actualizador.** El respaldo verificado es precondición, no
recomendación.
