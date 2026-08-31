# EVIDENCIA POSTGRESQL — N5

## 1. Motor

| | |
|---|---|
| Versión | **PostgreSQL 18.6** |
| Zona horaria del clúster | **UTC** |
| Antivirus (documental) | ClamAV 1.4.3 con firmas completas |

Ninguna prueba de aceptación de N5 se ejecutó sobre SQLite. El fixture
multiempresa se salta expresamente si la URL no es PostgreSQL, en lugar de
degradarse a un motor más permisivo y dar por buena una evidencia que no lo es.

## 2. Por qué el motor importa aquí

Dos de las comprobaciones centrales solo tienen sentido contra la base real:

**La propiedad persistida.** Que la API filtre bien no dice nada si el dato
guardado lleva el tenant: sería un filtro correcto sobre un dato indistinguible.
Cada dominio resuelve el propietario con `SELECT company_id FROM <tabla> WHERE
id = ...` en vez de leerlo de la respuesta.

**El barrido de mezcla.** Recorre `pg_tables` del esquema de la corrida y
pregunta, tabla por tabla —123 declaradas de empresa—, si alguna fila apunta a
un tenant o a un identificador que no existe en `companies`.

## 3. Consultas de la evidencia

```sql
-- ¿alguna fila pertenece a algo que no es una empresa?
SELECT count(*) FROM <tabla> t
WHERE t.company_id IS NOT NULL
  AND (t.company_id IN (SELECT id FROM tenants)
       OR NOT EXISTS (SELECT 1 FROM companies c WHERE c.id = t.company_id));

-- ¿algún número de control cuelga de un lote de otra empresa?
SELECT count(*) FROM control_numbers n
JOIN control_number_batches b ON b.id = n.batch_id
WHERE n.company_id <> b.company_id;

-- ¿alguna auditoría se contradice con el tenant de su empresa?
SELECT count(*) FROM audit_events a
JOIN companies c ON c.id = a.company_id
WHERE a.tenant_id IS NOT NULL AND a.tenant_id <> c.tenant_id;
```

Todas devuelven **0**.

## 4. Un detalle del entorno que invalidó una prueba

El primer barrido de las 123 tablas revisó **cero** y aun así habría pasado si
la aserción no hubiera exigido un mínimo. La suite crea un esquema propio por
corrida, y la consulta preguntaba por `public`.

Se corrigió usando `current_schema()`, y la prueba conserva la aserción
`revisadas > 50` precisamente para que un barrido vacío vuelva a fallar en lugar
de felicitarse.

## 5. Transacciones

Las comprobaciones de propiedad abren su propia sesión sobre el mismo motor y
leen después del commit de la operación. No se inspecciona el estado dentro de
la transacción que lo produjo, donde un rollback posterior dejaría la evidencia
sin respaldo.
