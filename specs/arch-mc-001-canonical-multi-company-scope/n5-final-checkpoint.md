# N5 — CHECKPOINT FINAL

PostgreSQL **18.6** en UTC · ClamAV 1.4.3 · **112 pruebas** nuevas de aislamiento

## 1. Qué demostró esta fase

N2 ya había convertido 234 puntos al contexto de empresa, y el checkpoint
anterior dejó siete dominios como `NORMALIZED_PENDING_AB_PROOF`: escribían y
leían bien, pero nadie los había interrogado con dos empresas del mismo tenant.

Al interrogarlos aparecieron **once defectos reales**, entre ellos dos
vulnerabilidades de seguridad en Specs cerradas y una fuga de lectura en el
módulo que se citaba como referencia positiva.

Esa es la conclusión de la fase, más que cualquier tabla: *implementado* y
*probado* no son lo mismo, y la diferencia no es teórica.

## 2. Los once defectos

| # | Dónde | Qué pasaba |
|---|---|---|
| 1 | `company_context` | Un rol global concedía acceso a todas las empresas |
| 2 | `master_data` | `deactivate_party` no acotaba en absoluto |
| 3 | `purchasing` | El pago de una empresa cancelaba la deuda de otra |
| 4 | `purchasing` | La idempotencia devolvía el pago de otra empresa |
| 5 | `sales` | La idempotencia devolvía la **factura fiscal** de otra empresa |
| 6 | `inventory` | La idempotencia devolvía el movimiento de otra empresa |
| 7 | `organization` | 29 rutas de almacén resolvían el alcance por tenant |
| 8 | `organization` | `create_branch` dejaba elegir la empresa por el cuerpo |
| 9 | `organization` | La auditoría anotaba el tenant pero no la empresa |
| 10 | `regulatory` | Un permiso de A amparaba un vehículo de B |
| 11 | `treasury` | El arqueo de caja se auditaba sin autor |

Más las dos vulnerabilidades P0 de 045 y 046, cerradas en esta misma fase.

## 3. Los tres que no encontró ninguna prueba de dominio

Vale la pena separarlos, porque dicen algo sobre el método.

**`create_branch`** salió de una prueba estructural sobre el AST, no de una
funcional. Nadie había pensado en crear una sucursal desde la empresa
equivocada.

**El listado de almacenes** salió de la prueba de control: la que existía solo
para confirmar que el fixture funcionaba, en el módulo llamado «referencia
positiva» porque su dato siempre fue correcto. Lo era. Su lectura no.

**El rastro sin empresa** salió del barrido transversal, después de que seis
dominios hubieran dado por buena su propia auditoría.

## 4. Fuga y mezcla

| Fallo | Pregunta | Resultado |
|---|---|---|
| **Fuga** | ¿Puede A acceder al dato de B? | **0** |
| **Mezcla** | ¿Sabe la base de quién es la fila? | **0** |

La segunda se mide recorriendo el catálogo de PostgreSQL y preguntando, tabla
por tabla —123 declaradas de empresa—, si alguna fila apunta a un tenant o a un
identificador inexistente. Ninguna prueba de dominio puede hacer eso.

## 5. Operaciones entre empresas, bloqueadas

Dinero entre cuentas · existencias entre almacenes · pago contra deuda ajena ·
cobro contra cuenta por cobrar ajena · recepción en almacén ajeno · despacho
desde almacén ajeno · emisión fiscal con serie o rango ajenos · permiso con
vehículo ajeno · lectura y descarga de documentos ajenos · escritura de
políticas en empresa ajena.

Cada bloqueo va acompañado de su prueba positiva. Sin ellas, un sistema
completamente roto pasaría la mitad de esa lista.

Ninguna capacidad intercompany se implementó. Las operaciones se impiden y se
registran como `FUTURE_INTERCOMPANY_CAPABILITY`.

## 6. Pruebas que estaban mal y cómo

Cuatro pruebas —tres mías, una preexistente— pasaban sin comprobar lo que decían.
Se dejan documentadas porque el patrón se repite.

**El libro fiscal, en vacío.** Pedía el libro por `IVA` cuando el de ventas es
`VENTAS`. Dos libros sin filas no se contaminan: el aislamiento quedaba
demostrado por no haber datos.

**El picking, por el motivo equivocado.** La orden estaba en borrador y el
rechazo llegaba por el estado, no por la empresa, sin tocar nunca la
comprobación que pretendía interrogar.

**Los payloads inválidos.** Varias pruebas de tesorería recibían 422 por cuerpo
mal formado y lo contaban como bloqueo. Un 422 significa que la petición murió
en la validación de forma.

**El tenant sin empresa.** `test_documents_security` usaba un segundo tenant sin
ninguna empresa como prueba de aislamiento. Ese usuario no ve documentos ajenos
porque no tiene dónde mirar, no porque el sistema lo separe.

Las cuatro son ahora más estrictas.

## 7. Estado de las pruebas

| | |
|---|---|
| Backend | 592 pruebas · 581 pasan · 8 saltadas · **0 fallos inesperados** |
| Arquitectura | 7 PASS · 3 EXPECTED_RED (N7/N8) · **0 UNEXPECTED_RED** |
| Frontend | tsc, eslint, 245/245 Vitest, build |
| OpenAPI | 294 rutas, sin pérdida |
| Route crawl | 79 rutas sin 404 ni errores de consola |
| Refresco de sesión | 23/23, sin regresión de rotación ni de concurrencia |

Las tres rojas de arquitectura son las mismas de siempre: constraints de N7 y
retirada de columnas legacy de N8. No se tocan aquí.

## 8. Lo que N5 deja escrito para otras fases

**N8 — contrato.** `X-Kontrol-Company` no aparece en OpenAPI: la dependencia lee
la cabecera del `Request` en lugar de declararla. Funciona y 112 pruebas la
usan, pero un consumidor que lea solo el contrato no sabría que existe.

**Spec 052 — instalador.** `MANDATORY_PER_INSTALLATION_PREFLIGHT`: toda
instalación existente pasa el preflight antes de actualizar, y no depende de que
el cliente crea tener una sola empresa. El preflight es lo que lo decide.

**Spec 053 — actualizador.** Respaldo verificado antes de cualquier migración
que toque `company_id`. La expansión de N3 es reversible; una normalización de
datos, no.

**Capacidades ausentes, documentadas sin inventarlas.** `outbox_events` está
migrada pero ningún módulo escribe en ella; los maestros no registran auditoría
de negocio. En ambos casos queda la regla escrita para cuando existan, no una
implementación improvisada.

## 9. Veredicto

**`ARCH-MC-001 — N5 COMPLETE`**

`SPEC 012 APTA_DOCUMENTALMENTE — BLOCKED_BY_ARCH_MC_001`
`REM-046-001 BLOCKED_BY_ARCH_MC_001`
`N4 Real Backfill — NOT_APPLICABLE — NO DEPLOYED LEGACY INSTALLATIONS`

N6 a N10 quedan pendientes y no se inician.
