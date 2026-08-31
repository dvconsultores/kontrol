# BARRIDO DE SEGURIDAD ENTRE EMPRESAS — N5

## 1. Qué se midió, y por qué son dos cosas

| Fallo | Pregunta | Resultado |
|---|---|---|
| **Fuga** | ¿Puede A acceder al dato de B? | **0** |
| **Mezcla** | ¿Sabe la base de quién es la fila? | **0** |

La segunda no se puede deducir de la primera. Si `company_id` guardara el
tenant, el filtro sería correcto sobre un dato indistinguible: nadie vería nada
ajeno, y aun así ninguna fila sabría a qué empresa pertenece.

La prueba que la mide recorre el catálogo de PostgreSQL y pregunta, tabla por
tabla —**123 declaradas de empresa**—, si alguna fila dice pertenecer a algo que
no es una empresa: ni un tenant, ni un identificador inexistente.

## 2. Las dos familias de arquitectura

Buscan por estructura lo que ninguna prueba de dominio ve. Se apoyan en el AST y
en las dependencias declaradas, nunca en comentarios ni en nombres: un
comentario correcto se puede escribir encima de un defecto.

### Familia 1 — la ruta que no comprueba nada

Nació de `deactivate_party`. Aquella ruta no confundía el tenant con la empresa:
sencillamente no comparaba nada, y por eso el barrido de N2 —que buscaba el
patrón `company_id = tenant_id`— no podía verla.

Detecta rutas que reciben un identificador por la URL, cargan la entidad con
`db.get(...)` y no mencionan el contexto de empresa en todo el cuerpo.

### Familia 2 — el cuerpo que elige la empresa

Nació de la Spec 045. Detecta rutas que pasan `body.company_id` a un servicio o
a un modelo sin contrastarlo antes con el contexto validado.

**Encontró un caso que ninguna prueba de dominio había tocado:**
`create_branch`. Una sucursal podía crearse en otra empresa declarándola en el
cuerpo, y el listado de sucursales devolvía las de todas las empresas del
tenant. Corregido.

## 3. Defectos encontrados y corregidos en esta fase

| Módulo | Defecto | Cómo apareció |
|---|---|---|
| `company_context` | Un rol global concedía acceso a todas las empresas | Prueba de aislamiento base |
| `master_data` | `deactivate_party` no acotaba en absoluto | Barrido de rutas sin filtro |
| `purchasing` | La fuente de una aplicación no se comprobaba: el pago de B saldaba la deuda de A | Prueba A/P |
| `purchasing`, `sales`, `inventory` | La clave de idempotencia no acotaba empresa | Prueba A/B |
| `organization` (almacenes) | 29 rutas resolvían el alcance por tenant | Prueba de control de inventario |
| `organization` (sucursales) | El cuerpo elegía la empresa; el listado no acotaba | Familia 2 |
| `organization` (auditoría) | El rastro anotaba el tenant pero no la empresa | Barrido transversal |
| `regulatory` | Un permiso de A amparaba un vehículo de B | Prueba regulatoria |
| `treasury` | El arqueo de caja se auditaba sin autor | Prueba de auditoría |
| `approvals` (045) | El cuerpo imponía la empresa; el listado no filtraba nada | Reproducción dirigida |
| `documents` (046) | El alcance admitía cualquier empresa del tenant | Reproducción dirigida |

## 4. Lo que el barrido reveló sobre el método

Tres de estos once no los encontró una prueba de dominio, sino un control:

- **`create_branch`** salió de una prueba estructural, no funcional.
- **El listado de almacenes** salió de la prueba que existía solo para
  confirmar que el fixture funcionaba, en el módulo que llamábamos «referencia
  positiva» porque su dato siempre fue correcto. Lo era; su lectura no.
- **El rastro sin empresa** salió del barrido transversal, después de que cada
  dominio hubiera dado por buena su propia auditoría.

Es la misma lección otra vez: lo que no se interroga expresamente no está
probado, por bien que se comporte lo que sí se interrogó.
