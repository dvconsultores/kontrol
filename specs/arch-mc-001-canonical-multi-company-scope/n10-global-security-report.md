# N10 — BARRIDO GLOBAL DE SEGURIDAD

> Doce defectos reales. Ninguno se dedujo leyendo: cada uno se reprodujo con una
> petición que devolvió `200` antes de la corrección y `404` después.

## Cómo se buscaron

N5 buscó el defecto donde la petición **declara** la empresa: un id en la URL
cargado con `db.get`, o una empresa impuesta desde el cuerpo. N10 buscó lo
contrario — la ruta que no declara nada — recorriendo el AST de los módulos de
empresa en busca de funciones que reciben un `*_id` y no piden `CompanyContext`.

Trece rutas. Siete eran defectos. Las otras seis se justificaron una por una, y
tres de ellas se comprobaron ejecutándolas, porque «parece protegida» y «está
protegida» son afirmaciones distintas.

## Escrituras entre empresas

| # | Ruta | Qué comprobaba | Qué pasaba |
|---|---|---|---|
| 1 | `POST /sales/quotes/{id}/lines` | nada | B añadía una línea a la cotización de A |
| 2 | `POST /sales/returns/{id}/lines` | nada | B añadía una línea a la devolución de A |
| 3 | `POST /purchasing/quotes/{id}/lines` | nada | idéntico en compras |
| 4 | `POST /purchasing/receipts/{id}/lines` | la cantidad | B recibía mercancía contra la recepción de A |
| 5 | `POST /purchasing/returns/{id}/lines` | nada | idéntico en devoluciones |
| 6 | `POST /treasury/reconciliation-lines/{id}/resolve` | el estado | B daba por conciliada una línea de A |
| 7 | `POST /approvals/requests/{id}/cancel` | la transición | B cancelaba la solicitud de A |
| 8 | `POST /maestros/catalogos/unidades/{id}/conversiones` | nada | B relacionaba dos unidades privadas de A |
| 9 | `POST /organization/establishments` | el **tenant** | A abría un establecimiento en una sucursal de B |

El permiso no salvaba a ninguna. `compras:create` dice que el usuario puede
crear líneas de compra; no dice en qué empresa. Sin contexto no hay nada que
comparar, y el servicio guarda la línea bajo el padre que le den.

La octava tenía además una hermana correcta: `/unidades/{id}/conversiones-fisicas`
de la Spec 011 sí comprobaba pertenencia y dimensión. Dos rutas creaban la misma
fila y solo una miraba algo.

## Lecturas entre empresas

| # | Ruta | Qué hacía |
|---|---|---|
| 10 | `GET /organization/establishments` | filtraba por `Company.tenant_id == user.tenant_id` |

Compartir tenant no es compartir empresa. El establecimiento es donde se emiten
los documentos fiscales: verlo es ver la estructura fiscal ajena.

## Autorización que cruzaba empresa y tenant

**11 — La elegibilidad de aprobadores ignoraba la empresa que se le pasaba.**

`resolve_actors` recibe `company_id` y no lo usaba. Con `resolver_type: ROLE`
buscaba el rol por código —el catálogo es de la instalación— y tomaba **todas**
las asignaciones, sin mirar `UserRole.company_id`. Con `SCOPE_OWNER`, todos los
usuarios activos de la instalación.

Resultado comprobado: un usuario de la empresa B aprobó un paso de una solicitud
de la empresa A, y lo mismo habría valido desde otro tenant.

Se corrige con la autoridad que ya existía y no se estaba usando:
`accessible_company_ids`, la misma que decide a qué empresa entra una petición.
`UserRole` dice qué puede hacer alguien; nunca dónde.

## Cruces de tenant en identidad

| # | Ruta | Qué hacía |
|---|---|---|
| 12 | `GET /users` | `select(User)` sin `where`: el censo de la instalación |
| 12b | `POST /users/{id}/roles` | `get_user` por id, sin mirar el tenant |
| 12c | `DELETE /users/{id}/roles/{role_id}` | igual |
| 12d | `POST /users/{id}/roles` | `company_id` del cuerpo, sin comprobar de quién era |

`GET /users` devolvía nombre, correo, último acceso y roles de todos los
usuarios de la instalación a quien solo administra su tenant.

## Un fallo que solo aparece al ejecutar

Al probar 12d la ruta respondió **500**: la auditoría escribía
`entity_id=f"{user_id}:{role_id}"` —73 caracteres— en una columna de 36. Nadie
lo había visto porque la ruta no se ejercitaba con una asignación que no fuera
duplicada. Se audita la asignación, que tiene id propio.

## Resultado

| Métrica | Antes de N10 | Después |
|---|---:|---:|
| Escrituras entre empresas | 9 | **0** |
| Lecturas entre empresas | 1 | **0** |
| Cruces de tenant | 4 | **0** |
| Autorización que ignora la empresa | 1 | **0** |
| Respaldo Tenant→Company en consultas | 2 | **0** |

## Lo que impide que vuelvan

`test_n10_cross_company_writes.py` (11 pruebas) y `test_n10_cross_tenant.py`
(4) reproducen cada caso. Y en `test_architecture_scope.py`,
`test_ninguna_ruta_recibe_un_id_de_empresa_sin_ver_el_contexto` recorre el AST:
una ruta nueva de módulo de empresa que reciba un id sin ver el contexto falla en
construcción. Su lista de excepciones exige motivo, y una segunda prueba impide
que una excepción sobreviva a la ruta que la justificaba.

## Un decimotercer hallazgo, sin víctima

Al retirar el último llamante de `branch_in_tenant` —la creación de
establecimientos— los tres ayudantes de `organization/service.py` quedaron sin
uso: `company_in_tenant`, `branch_in_tenant` y `warehouse_in_tenant`.

Los tres responden a la misma pregunta, «¿es de una empresa de este tenant?», y
esa pregunta era la equivocada en todos los sitios donde se usaban. N8 ya había
retirado `warehouse_in_tenant_scope` por ese motivo; estos tres eran su cola.

Se retiran. No se conservan «por si acaso»: un ayudante que solo sirve para el
patrón que esta remediación eliminó es una invitación a reutilizarlo.
