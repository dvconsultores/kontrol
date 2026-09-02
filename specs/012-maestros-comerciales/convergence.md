# CONVERGENCIA — SPEC 012

## Puerta

| Invariante | Resultado |
|---|---:|
| Entidades implementadas | 11 / 11 |
| Alcance correcto | 11 / 11 |
| Indeterminadas | 0 |
| Directas de empresa esperadas / implementadas | 8 / 8 |
| Derivadas esperadas / implementadas | 3 / 3 |
| Claves foráneas con destino equivocado | 0 |
| Rutas derivadas rotas | 0 |
| Empresa redundante en derivadas | 0 |
| Rutas hijas aseguradas | 5 / 5 |
| Ataque del usuario con acceso a A+B | **bloqueado** |
| Fuga entre empresas | 0 |
| Fuga entre tenants | 0 |
| Mezcla de datos | 0 |
| Respaldo Tenant→Company | 0 |
| Empresa desde el cuerpo | 0 |
| Identificador del padre como autoridad | 0 |
| Regresión de la unidad de plataforma | 0 |
| Importes en coma flotante | 0 |
| Versionado | PASS |
| Configuración en tiempo de ejecución | PASS |
| Integración de aprobación | PASS |
| Desviación con OpenAPI | 0 |
| Desviación de empresa en el frontend | 0 |
| Trazabilidad | 100% |
| Deuda interna de la Spec 012 | 0 |

## Lo que se comparó

Requisitos, aclaraciones, plan, modelo de datos, contratos, checklist, tareas,
código, migraciones, catálogo de PostgreSQL, API, OpenAPI, frontend, pruebas,
evidencia y trazabilidad.

## Cuatro correcciones dentro del ciclo

Ninguna era una decisión comercial nueva; las cuatro eran fallos propios.

**La exclusión vivía solo en la migración.** Su prueba pasaba en verde sin
comprobar nada, porque las suites levantan el esquema desde el ORM. Es la
lección de N7 vista desde dentro: un esquema de pruebas más débil que el de
producción no prueba producción. Ahora la declara también el ORM.

**Dos restricciones protegían el dato y mentían al usuario.** El código
duplicado y el solape de vigencias terminaban en `500`: la base hacía su trabajo
y la respuesta no lo contaba. Ahora son `409` con su motivo.

**Una prueba negativa fallaba por el motivo equivocado.** La de la clave foránea
del ítem saltaba antes por la restricción de «artículo o categoría». Con un
artículo real, falla por lo que dice comprobar.

**Un salto ambiental escondía una comprobación.** Se sembró el nodo de taxonomía
en vez de saltar la prueba.

## Un hallazgo ajeno, reportado y no silenciado

El clasificador de N4 preguntaba al catálogo del destino por sus restricciones
pero no por la existencia de la tabla, y planificaba revisar tablas que una
instalación heredada no tiene. El hueco estaba desde N4; la Spec 012 fue la
primera en añadir tablas de empresa nuevas y lo destapó.

No es una regresión de ARCH-MC-001 —nada que funcionara dejó de funcionar— sino
un límite que nadie había alcanzado. Se corrigió completando lo que el propio
docstring de `planes()` prometía, y queda escrito en `migration-report.md` y en
el checkpoint.

## Veredicto

`SPEC 012 — COMPLETE / CONVERGED`
