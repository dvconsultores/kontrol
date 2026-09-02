# SPEC 012 — SEGURIDAD DE LAS RUTAS HIJAS

## El riesgo, medido

La Spec 012 es la jerarquía más profunda de KONTROL: lista → versión → ítem.
Cinco de sus catorce rutas reciben el identificador de un padre por la URL, y
esa es la forma exacta de los nueve defectos que N10 encontró y corrigió.

| Ruta | Eslabones que resuelve |
|---|---|
| `POST /listas-precio/{id}/versiones` | lista |
| `POST /listas-precio/{id}/versiones/{vid}/transicion` | lista → versión |
| `GET /listas-precio/{id}/versiones/{vid}/items` | lista → versión |
| `POST /listas-precio/{id}/versiones/{vid}/items` | lista → versión |
| `GET /listas-precio/{id}` | lista |

## El contrato, implementado

`version_de_la_lista` no carga la versión por su identificador: carga **la
lista bajo el contexto** y después exige que la versión cuelgue de esa lista.
Comprobar solo `version_id` dejaría pasar una versión legítima que pertenece a
otra empresa.

```
CompanyContext → lista de esta empresa → versión de esa lista → permiso → escribir
```

## La matriz, ejecutada

| Caso | Contexto | Padre | Esperado | Real |
|---|---|---|---|---|
| N-01 | A | Lista de A | PASS | **PASS** |
| N-02 | A | Lista de B | 404 | **404** |
| N-03 | T1/A | Lista de T2/C | 404 | **404** |
| N-06 | `uab` en A | Lista de B | 404 | **404** |
| N-06b | `uab` en B | Lista de B | PASS | **PASS** |
| N-08 | A | Lista de A + versión de B | 404 | **404** |
| Lectura | A | Ítems de una versión de B | 404 | **404** |

**N-06 y N-06b van juntas a propósito.** Sin la segunda, la primera no probaría
la empresa: podría estar bloqueando por falta de acceso a B. Con las dos se sabe
que `uab` alcanza B y que aun así no puede tocarlo desde el contexto A.

**N-08 es el caso que solo aparece con tres niveles.** La lista es legítima y de
A; la versión es legítima y de B. Un servicio que comprobara solo el primer
eslabón escribiría el ítem.

## La empresa no viene del cuerpo

Los dos resolutores —precio y descuento— usan esquemas con `extra="forbid"`.
Un cuerpo que declare `company_id` se **rechaza** con `422`; no se ignora en
silencio, porque ignorarlo dejaría al cliente creyendo que operó donde pidió.

Dos pruebas de arquitectura lo sostienen: ninguna clase de entrada del módulo
declara `company_id`, y todas prohíben campos desconocidos. Las dos fallan en
construcción.

## La guarda que ya existía

`test_ninguna_ruta_recibe_un_id_de_empresa_sin_ver_el_contexto` recorre el AST
de los módulos de empresa. El módulo comercial quedó bajo ella al nacer, sin
añadir nada y —lo que importa— **sin añadir ninguna excepción**.
