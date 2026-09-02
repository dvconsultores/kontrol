# SPEC 012 — CONTRATO DE SEGURIDAD DE RUTAS HIJAS

> Este documento existe por un hallazgo de N10, no por una precaución teórica.

## Lo que pasó

N10 recorrió el AST buscando rutas de módulos de empresa que recibieran un
identificador por la URL y no pidieran `CompanyContext`. Encontró trece. Nueve
eran defectos reales, reproducidos con una petición que devolvió `200`:

- la empresa B añadía una línea a la cotización de venta de A;
- a su devolución;
- a la cotización de compra;
- a la recepción de mercancía;
- resolvía una línea de conciliación bancaria de A;
- cancelaba su solicitud de aprobación.

Ninguna se salvaba por el permiso. `compras:create` dice que el usuario puede
crear líneas de compra; **no dice en qué empresa**. Sin contexto no hay nada que
comparar, y el servicio guarda la línea bajo el padre que le den.

## Por qué esto es un problema de la Spec 012 en particular

La Spec 012 es, estructuralmente, una jerarquía de tres niveles:

```
PriceList → PriceListVersion → PriceListItem
```

Sus contratos generan exactamente la forma del defecto:

```
POST /comercial/listas-precio/{id}/versiones
POST /comercial/listas-precio/{id}/versiones/{vid}/items
POST /comercial/listas-precio/{id}/versiones/{vid}/activar
```

Es la Spec con más rutas hijas de todo KONTROL. Si se implementa con el patrón
que N10 encontró, reintroduce nueve defectos de una sola vez.

## El contrato, obligatorio

Toda ruta con un identificador de padre en la URL sigue esta secuencia, en este
orden:

```
1. Usuario autenticado
2. CompanyContext resuelto por la autoridad canónica
3. Padre cargado ACOTADO por CompanyContext
4. Padre inaccesible o inexistente → 404, sin distinguir cuál de los dos
5. Permiso validado
6. Hijo creado tomando la empresa DEL PADRE, nunca del cuerpo
7. Auditoría con la empresa resuelta
```

Prohibido, sin excepción:

```
parent_id (de la URL) → service(parent_id)
```

## Por qué 404 y no 403

Un `403` sobre un recurso de otra empresa confirma que ese recurso existe. Con
identificadores secuenciales o adivinables eso es un inventario ajeno servido de
a un bit por petición.

`404` para el inaccesible y para el inexistente. El usuario no puede distinguir
«no es tuyo» de «no existe», que es justo lo que no debe poder distinguir.

## Lo que el cuerpo nunca decide

`POST /comercial/precio/resolver` declaraba `company_id` en su carga útil.

Se retira. La empresa la pone `CompanyContext`, como en las 342 operaciones que
hoy publican `X-Kontrol-Company`. Si el cuerpo lo trae, o se ignora o se
contrasta y se rechaza si difiere — nunca se obedece.

Es literalmente la vulnerabilidad que la Spec 045 estrenó: operando en A se
declaraba B en el cuerpo y la política quedaba guardada en B.

## Las pruebas que este contrato exige

Cada una debe fallar **por la frontera de empresa**, no por carga útil
inválida, ni por autenticación, ni por estado. Una prueba que se rechaza por el
motivo equivocado no prueba lo que dice — es la lección que N5 dejó escrita y
que N10 volvió a encontrar dos veces.

### Ataque por identificador de padre

| Caso | Contexto | Padre | Resultado |
|---|---|---|---|
| N-01 | Empresa A | Lista de A | **PASS** |
| N-02 | Empresa A | Lista de B | **BLOCK 404** |
| N-03 | Empresa A | Lista de C (otro tenant) | **BLOCK 404** |
| N-04 | Empresa B | Lista de B | **PASS** |

En N-02 y N-03 la carga útil es **válida y de la empresa del contexto**: si la
petición se rechazara con `422` no habría llegado siquiera a la comprobación de
empresa, y la prueba pasaría sin comprobar nada.

### El usuario con acceso a las dos

| Caso | Usuario | Contexto | Padre | Resultado |
|---|---|---|---|---|
| N-05 | UAB (A+B) | A | Lista de A | **PASS** |
| N-06 | UAB (A+B) | A | Lista de B | **BLOCK 404** |

N-06 es el caso que más se olvida. Tener acceso a B no autoriza a operar sobre B
cuando la petición dice A. La autoridad es el contexto de **esta** petición, no
el conjunto de lo que el usuario podría alcanzar en otra.

### Los tres niveles

| Caso | Contexto | Lista | Versión | Resultado |
|---|---|---|---|---|
| N-07 | A | de A | de esa lista | **PASS** |
| N-08 | A | de A | **de una lista de B** | **BLOCK 404** |
| N-09 | A | de B | cualquiera | **BLOCK 404** |

N-08 es el que solo aparece con tres niveles: la lista es legítima y la versión
no le pertenece. Comprobar únicamente el primer eslabón lo dejaría pasar.

## La guarda que ya existe

`test_ninguna_ruta_recibe_un_id_de_empresa_sin_ver_el_contexto`, en
`tests/test_architecture_scope.py`, recorre el AST de los módulos de empresa y
falla **en construcción** si aparece una ruta nueva con esta forma.

Cuando el módulo comercial se implemente quedará bajo esa prueba
automáticamente. No hay que añadir nada: hay que no añadir una excepción.

Y si alguien la añadiera, una segunda prueba —
`test_la_lista_de_excepciones_no_guarda_rutas_que_ya_no_existen`— impide que
esa excepción sobreviva a la ruta que la justificaba.
