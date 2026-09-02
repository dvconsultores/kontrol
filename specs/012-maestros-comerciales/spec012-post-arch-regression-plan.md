# SPEC 012 — PLAN DE PRUEBAS PARA LA IMPLEMENTACIÓN FUTURA

> Especificación de pruebas. **Ninguna se construye en este ciclo.**

## Arnés

El que ya existe: `tests/conftest_multicompany.py`.

```
T1 ─ Empresa A ─ Sucursal A1
   └ Empresa B ─ Sucursal B1
T2 ─ Empresa C ─ Sucursal C1
```

Usuarios: `ua` (solo A) · `ub` (solo B) · `uab` (A+B) · `uc` (T2).

No se crea un arnés nuevo. Probar el aislamiento con una sola empresa no prueba
nada: si el sistema solo conoce una, no puede confundirla con otra.

## A. Pruebas de arquitectura — fallan en construcción

| Id | Qué comprueba |
|---|---|
| A-01 | Los once modelos de 012 declaran `__scope__` |
| A-02 | Los ocho directos tienen `company_id` obligatoria con FK a `companies` |
| A-03 | Los tres derivados declaran `__scope_authority__` con FK obligatoria |
| A-04 | Ningún derivado lleva `company_id` redundante |
| A-05 | Ninguna ruta de 012 recibe un id sin ver el contexto |
| A-06 | Ninguna consulta de 012 filtra por tenant donde debe filtrar por empresa |
| A-07 | Ninguna ruta acepta la empresa desde el cuerpo |

A-01 a A-04 quedan cubiertas por las pruebas de arquitectura vigentes en cuanto
los modelos existan. A-05 y A-07 también: ese es el sentido de que sean
estructurales y no por módulo.

## B. Integridad en PostgreSQL — sobre el catálogo real

| Id | Qué comprueba |
|---|---|
| B-01 | FK real de las ocho `company_id` |
| B-02 | `NOT NULL` en toda columna de autoridad |
| B-03 | Unicidad por empresa: mismo `code` en A y en B **se permite** |
| B-04 | Unicidad por empresa: `code` repetido dentro de A **falla** |
| B-05 | Exclusión de solape entre versiones `ACTIVE` de una lista |
| B-06 | Dos borradores **sí** pueden solapar |
| B-07 | `item_id` y `category_id` excluyentes: ambos o ninguno **falla** |
| B-08 | Índices únicos parciales sobre la unicidad de ítems con columnas anulables |
| B-09 | SQL directo: ítem colgando de una versión de otra empresa **falla** |
| B-10 | Instalación limpia migrada a cabeza, y arranque con T1(A,B) y T2(C) |

B-03 y B-04 son la misma restricción vista desde los dos lados. Solo con las dos
se sabe que la unicidad es **por empresa** y no global ni inexistente.

B-06 importa porque una restricción de exclusión sin su `WHERE` impediría
trabajar: dos borradores en paralelo son legítimos.

## C. Seguridad multiempresa

Para **cada uno** de los ocho maestros directos:

| Id | Contexto | Objetivo | Resultado |
|---|---|---|---|
| C-01 | A | Propio de A | **PASS** |
| C-02 | A | De B | **BLOCK 404** |
| C-03 | A | De C (otro tenant) | **BLOCK 404** |
| C-04 | `uab` en contexto A | De B | **BLOCK 404** |

C-04 es el que más se olvida: acceso a B no es autorización sobre B cuando la
petición dice A.

## D. Rutas hijas — el ataque por identificador de padre

Definidas en `nested-resource-security-contract.md`, casos N-01 a N-09.

Regla que gobierna todas: **cada prueba debe fallar por la frontera de empresa**.
Si falla por carga útil inválida, por estado o por autenticación, no prueba lo
que dice. Es la lección que N5 dejó escrita y que N10 volvió a tropezar dos veces
—una conciliación en borrador y una orden no receptible— antes de corregir las
semillas.

## E. Resolución de precio

| Id | Qué comprueba |
|---|---|
| E-01 | Determinismo: dos resoluciones idénticas devuelven lo mismo, incluida la versión |
| E-02 | Devuelve el precio **y** la versión que lo produjo |
| E-03 | Sin lista aplicable declara ausencia; **no** devuelve cero |
| E-04 | Precedencia configurada por empresa: A y B resuelven distinto con los mismos datos |
| E-05 | Empate irresoluble se reporta como error de configuración |
| E-06 | Una lista de B nunca participa en una resolución de A |
| E-07 | La empresa **no** se toma del cuerpo |

E-04 es la prueba de que la precedencia es dato y no código: si estuviera
codificada, A y B no podrían diferir.

## F. Histórico y congelado

| Id | Qué comprueba |
|---|---|
| F-01 | Documento aprobado con precio congelado; se supera la versión; el documento no cambia |
| F-02 | Se archiva la lista entera; el documento sigue reconstruyéndose |
| F-03 | Cambia la tasa de cambio; el documento emitido no cambia |
| F-04 | Cambia la presentación en 011; el documento emitido no cambia |
| F-05 | `DELETE` sobre versión referenciada responde `409` |
| F-06 | La reconstrucción sale del snapshot, no de recalcular |

F-06 se comprueba destruyendo la posibilidad de recalcular: se archiva la
versión y se exige que la reconstrucción siga funcionando.

## G. Descuentos y aprobación

| Id | Qué comprueba |
|---|---|
| G-01 | Bajo el límite: pasa sin solicitud |
| G-02 | Sobre el límite: **abre solicitud** en la 045, no bloquea |
| G-03 | La solicitud nace en la empresa correcta |
| G-04 | Un aprobador de B **no** figura como elegible en una solicitud de A |
| G-05 | El descuento registra política, versión y nivel de autorización |

G-04 está aquí por lo que N10 encontró: la elegibilidad recibía la empresa y no
la usaba, y un usuario de B aprobó un paso de A. La 012 será una consumidora
intensiva de ese motor, así que lo comprueba desde su lado.

## H. Frontend

| Id | Qué comprueba |
|---|---|
| H-01 | Toda consulta de 012 queda separada por empresa en la caché |
| H-02 | Pestaña A y pestaña B simultáneas, sin contaminación |
| H-03 | Formulario abierto en A, cambio de selector a B, envío: **no** se convierte en B |
| H-04 | Estados de carga, error, vacío, prohibido y no encontrado |
| H-05 | Sin desbordamiento horizontal entre 320 y 1440 |
| H-06 | WCAG 2.2 AA sin violaciones serias |

H-01 sale gratis: `queryKeyHashFn` antepone la empresa a toda clave cuya raíz no
esté exenta, y `comercial` no lo estará. La prueba confirma que sigue siendo
cierto, no lo implementa.

## I. Sin valores comerciales codificados

| Id | Qué comprueba |
|---|---|
| I-01 | Los once catálogos nacen **vacíos** tras la instalación limpia |
| I-02 | Ningún porcentaje, plazo, límite ni umbral aparece como literal en el código |
| I-03 | La precedencia por defecto se **siembra como dato** y es reordenable |

I-03 es la frontera fina de `P8`: sembrar un orden por defecto en una tabla no
lo viola; codificarlo sí.

## J. Regresión

Ninguna de las 166 tablas ni de las 404 operaciones vigentes cambia de
comportamiento. Suite completa del backend y del frontend, con el mismo criterio
de N10: fallos inesperados **0**, y todo salto con motivo, responsable y
prioridad.
