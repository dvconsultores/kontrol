# ARCH-MC-001 / N10 — CONVERGENCIA GLOBAL

## Qué es N10

N10 no añade capacidades. Comprueba que las diez fases anteriores describen **un
solo sistema**, y elimina las diferencias entre lo que KONTROL declara y lo que
hace.

La medición encontró siete. Ninguna se resolvió cambiando el documento para que
coincidiera con el código: en cada una se determinó primero cuál de las dos
partes tenía razón.

---

## FR / NFR de N10

| Id | Requisito | Estado |
|---|---|---|
| FR-N10-001 | Una sola definición canónica de Tenant | PASS |
| FR-N10-002 | Una sola definición canónica de Company | PASS |
| FR-N10-003 | Tenant no sustituye a Company | PASS |
| FR-N10-004 | `CompanyContext` es la única autoridad por petición | PASS |
| FR-N10-005 | El frontend no es autoridad de seguridad | PASS |
| FR-N10-006 | `UserRole` no amplía el acceso a empresas | PASS |
| FR-N10-007 | El alcance vigente del usuario define el acceso | PASS |
| FR-N10-008 | Respaldo Tenant→Company = 0 | PASS |
| FR-N10-009 | Lectura dual de pertenencia = 0 | PASS |
| FR-N10-010 | Escritura dual de pertenencia = 0 | PASS |
| FR-N10-011 | Alcance indeterminado = 0 | PASS |
| FR-N10-012 | Todo modelo y tabla vigente tiene alcance clasificado | PASS |
| FR-N10-013 | Todo COMPANY directo tiene FK correcta a `companies` | PASS |
| FR-N10-014 | Todo TENANT directo tiene FK correcta a `tenants` | PASS |
| FR-N10-015 | Toda ruta derivada es válida | PASS — **corregido en N10** |
| FR-N10-016 | Rutas derivadas anulables = 0 | PASS |
| FR-N10-017 | Rutas derivadas ambiguas = 0 | PASS |
| FR-N10-018 | FK huérfanas = 0 | PASS |
| FR-N10-019 | FK con destino equivocado = 0 | PASS |
| FR-N10-020 | Desviación ORM / Alembic / PostgreSQL = 0 | PASS — **corregido en N10** |
| FR-N10-021 | Desviación ejecución / OpenAPI = 0 | PASS |
| FR-N10-022 | Desviación de contrato frontend / backend = 0 | PASS |
| FR-N10-023 | El aislamiento por empresa de la API es consistente | PASS — **corregido en N10** |
| FR-N10-024 | Fuga entre empresas = 0 | PASS — **corregido en N10** |
| FR-N10-025 | Fuga entre tenants = 0 | PASS |
| FR-N10-026 | Mezcla de datos = 0 | PASS |
| FR-N10-027 | Escritores incorrectos = 0 | PASS — **corregido en N10** |
| FR-N10-028 | Lectores incorrectos = 0 | PASS |
| FR-N10-029 | Contaminación de caché entre empresas = 0 | PASS |
| FR-N10-030 | Violaciones de contexto en formularios = 0 | PASS |
| FR-N10-031 | Contaminación entre pestañas = 0 | PASS |
| FR-N10-032..034 | El clasificador N4 sigue operativo, sin escritura y repetible | PASS |
| FR-N10-035..038 | Clases MC y estrategias de maestro siguen funcionales | PASS |
| FR-N10-039..041 | Registro documental cerrado, cardinalidad y verificación conductual | PASS |
| FR-N10-042 | `REM-046-001` sigue cerrada | PASS |
| FR-N10-043 | La Spec 046 sigue reconvergida | PASS |
| FR-N10-044 | Los documentos congelados mantienen su invariancia | PASS |
| FR-N10-045 | El almacenamiento en disco sigue verificado | PASS |
| FR-N10-046 | ClamAV no produce limpio falso | PASS |
| FR-N10-047 | S3 se clasifica con honestidad | PASS |
| FR-N10-048..049 | Fiscal P0: separación por empresa y paridad de cálculo | PASS |
| FR-N10-050..055 | Compras, Ventas, Inventario, Tesorería, Regulatory y Auditoría | PASS |
| FR-N10-056..057 | La documentación final refleja el sistema; lo anterior queda marcado | PASS |
| FR-N10-058 | Deuda P0 interna = 0 | PASS |
| FR-N10-059 | Toda deuda restante tiene responsable, prioridad y motivo | PASS |
| FR-N10-060 | Trazabilidad global = 100% | PASS |
| FR-N10-061 | Fallos inesperados = 0 | PASS |
| FR-N10-062 | ARCH-MC-001 solo converge si todo lo anterior pasa | PASS |

---

## Cómo se corrigió cada cosa

Regla del §97, aplicada sin excepción: se corrige lo que contradice un requisito
existente de ARCH-MC-001; lo que es una capacidad ausente se registra con
responsable y **no** se implementa.

| Hallazgo | ¿Requisito o capacidad? | Qué se hizo |
|---|---|---|
| Nueve escrituras entre empresas | Requisito FR-N10-024/027 | Corregidas |
| Lectura de establecimientos por tenant | Requisito FR-N10-028 | Corregida |
| Elegibilidad de aprobadores sin empresa | Requisito FR-N10-006/007 | Corregida |
| `GET /users` sin filtro de tenant | Requisito FR-N10-025 | Corregido |
| Roles de otro tenant asignables | Requisito FR-N10-025 | Corregido |
| Cinco columnas fantasma | Requisito FR-N10-020 | Retiradas |
| Ocho alcances no verificables | Requisito FR-N10-012/014 | Declarados o reclasificados |
| Desbordamiento de `entity_id` | Requisito FR-N10-055 | Corregido |
| **Roles propios por tenant** | **Capacidad** | Registrada, no implementada |
| **Unificar las dos rutas de conversión** | **Capacidad** | Registrada, no implementada |

## La forma del defecto dominante

Nueve de los doce comparten una misma forma, y merece la pena nombrarla porque
seguirá apareciendo mientras haya entidades con hijos:

> Una entidad padre está protegida. Su hijo se crea por una ruta que recibe el
> id del padre por la URL, no pide contexto de empresa, y llama al servicio con
> ese id tal cual.

La cotización de ventas estaba protegida; sus líneas, no. La conciliación estaba
protegida; sus líneas, no. La sucursal estaba protegida; sus establecimientos,
no.

Es una forma que ninguna prueba de dominio ve, porque cada dominio prueba su
entidad principal. Por eso la guarda de N10 es estructural y no de
comportamiento: recorre el AST y falla en construcción.

Y es la razón por la que la Spec 012 tendrá que nacer con ella en mente: una
lista de precios con versiones e ítems genera exactamente
`POST /price-lists/{id}/items`.
