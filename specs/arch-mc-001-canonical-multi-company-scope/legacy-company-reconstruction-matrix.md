# MATRIZ DE RECONSTRUCCIÓN DEL LEGADO — ARCH-MC-001

**Normativa.** Gobierna el relleno de N4, igual que
`legacy-document-migration-matrix.md` gobernó la `0024` de la Spec 046.

## 1. Principio

> **No se inventa empresa.**

Una fila que guarda el tenant no dice a qué empresa pertenece. Si el tenant tuvo
una sola empresa durante todo el intervalo en que la fila pudo crearse, se deduce
con certeza. Si tuvo dos, no se deduce: se anota y se detiene.

## 2. Clases

| Clase | Significado | Acción |
|---|---|---|
| **MC-A** `DETERMINISTIC` | El tenant tuvo **una sola** empresa en todo el intervalo relevante | Rellenar |
| **MC-B** `RECONSTRUCTIBLE` | Existe una ruta histórica única: almacén, sucursal, cuenta o cabecera | Rellenar desde esa ruta |
| **MC-C** `AMBIGUOUS` | Más de una empresa posible | **Anotar**; revisión manual |
| **MC-D** `NON_RECONSTRUCTIBLE` | Sin evidencia | **Anotar**; no se rellena |
| **MC-E** `CRITICAL_NON_RECONSTRUCTIBLE` | Sin evidencia **y** fiscal, financiera o de inventario | **Bloquea la migración final** |

## 3. Cómo se decide MC-A

**No** basta `count(companies) == 1` hoy (`FR-MC-052`).

Se reconstruye, por tenant, el instante en que dejó de ser monoempresa:

```
multi_company_cutover_at(tenant) = min(companies.created_at) de la 2ª empresa
```

- Fila creada **antes** de ese instante → **MC-A**.
- Fila creada **después**, o sin `created_at` fiable → **no** es MC-A.
- Tenant que nunca tuvo una segunda → todas sus filas **MC-A**.

Se auditan además activación y desactivación de empresas: una empresa creada y
desactivada dentro del intervalo sigue siendo una empresa posible.

## 4. Rutas de reconstrucción admitidas — MC-B

En orden de preferencia. La evidencia histórica pesa más que la inferencia.

| Ruta | Ejemplo | Condición |
|---|---|---|
| Almacén | movimiento → almacén → empresa | El almacén ya tiene FK real (Spec 008) |
| Sucursal | documento → sucursal → empresa | FK obligatoria |
| Cuenta bancaria | movimiento → cuenta → empresa | FK obligatoria |
| Cabecera | línea → documento → empresa | FK obligatoria |
| Serie fiscal | documento → serie → empresa | FK obligatoria |

**No admitidas:** inferir por proximidad temporal, por usuario que creó la fila,
por proveedor o cliente, o por cualquier heurística. Una ruta que puede
equivocarse no es una ruta.

## 5. Conflictos

Si dos rutas dan empresas distintas —una orden de la empresa A recibida en un
almacén de la B— la fila es **MC-C**, no se elige la «más probable», y el
conflicto se reporta. Puede revelar un dato ya corrupto, y taparlo sería peor.

## 6. Invariantes de la migración

| Invariante | Valor exigido |
|---|---:|
| Empresas inventadas | **0** |
| Filas MC-E rellenadas automáticamente | **0** |
| Columnas heredadas modificadas antes de verificar | **0** |
| Importes, cantidades o bases imponibles alterados | **0** |
| Números de documento alterados | **0** |

Si alguna se incumple, la migración **aborta** sin escrituras destructivas
parciales.

## 7. Informe previo, sin escribir

Antes de cualquier cambio (`FR-MC-058`):

```
===== INFORME PREVIO DE ALCANCE MULTIEMPRESA =====
tenants: N   empresas por tenant: {1: N, 2: N, …}
tenants que dejaron de ser monoempresa: N

| Tabla | Filas | MC-A | MC-B | MC-C | MC-D | MC-E | Acción |
```

Se puede ejecutar contra producción sin riesgo.

## 8. Resolución manual

Para MC-C y MC-D existe un mecanismo auditable (`FR-MC-055`) que registra la
fila, la evidencia mostrada, quién decidió, cuándo, con qué justificación, el
valor anterior y el nuevo.

**No** se admite un CSV opaco como única vía. Sobre dato fiscal, la resolución
queda auditada como cualquier otra operación fiscal (`§92`).

## 9. Informe final

| Tabla | Total | MC-A | MC-B | MC-C | MC-D | MC-E | Migradas | Manuales | Bloqueadas |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|

Por tabla, sin agregados que oculten un dominio.
