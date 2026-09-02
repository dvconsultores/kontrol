# N10 — REGISTRO DE DEUDA

Toda la deuda de ARCH-MC-001, clasificada. Sin escondites: S3 y el planificador
de retención aparecen aunque no bloqueen nada.

## P0 interna de ARCH-MC-001

**Ninguna.** Las doce que N10 encontró se corrigieron dentro de N10, con prueba
en rojo antes y en verde después. Están en `n10-global-security-report.md`.

## P1 externa — depende del entorno, no del código

| Deuda | Estado | Responsable | Motivo |
|---|---|---|---|
| Backend de S3 | `IMPLEMENTED_NOT_VERIFIED` | Infraestructura | El adaptador existe y sus pruebas se saltan porque no hay un servicio S3 real en este entorno. No se declara verificado lo que no se ejecutó |

Las pruebas que se saltan son las de `test_documents_storage.py`. Ninguna otra.

## P1 interna — capacidad ausente, no defecto

| Deuda | Responsable | Motivo |
|---|---|---|
| Planificador de retención | Spec 052 | La capacidad de retención existe; falta quien la dispare periódicamente. No es de ARCH-MC-001 |
| Productores de eventos del outbox | Spec futura de eventos | `outbox_events` está migrada y **no tiene ningún productor**: cero eventos escritos, cero eventos con empresa incorrecta. No se inventa una arquitectura de eventos para llenarla |

## Capacidades futuras que N10 encontró y no implementó

Regla de N10: un defecto que contradice un requisito se corrige; una capacidad
que nunca fue requisito se registra con responsable y no se implementa.

| Capacidad | Responsable | Qué hay hoy |
|---|---|---|
| Roles propios por tenant | Spec de identidad futura | El catálogo de roles es **de la instalación**: lo crea el arranque, no existe ruta para crear otros, y un segundo tenant reutiliza el `ADMIN` existente. `Role.__scope__` lo dice ahora explícitamente. El día que se creen roles por tenant, `list_roles` y `assign_role_to_user` tendrán que filtrar por tenant — hoy no filtran porque hoy no hay nada que filtrar |
| Unificar las dos rutas de conversión de unidades | Spec 011 | `/catalogos/unidades/{id}/conversiones` y `/unidades/{id}/conversiones-fisicas` crean la misma fila. N10 igualó la comprobación de pertenencia en ambas; la segunda además exige la misma dimensión. Retirar una es un cambio de contrato, fuera del alcance de una convergencia |

## Lo que dejó de ser deuda en N10

| Era | Ahora |
|---|---|
| Cinco columnas `tenant_id` vacías de una expansión sin contracción | Retiradas en `0039` |
| Dos columnas obligatorias en el ORM y anulables en la base | Ajustadas en `0039` |
| Ocho modelos de tenant sin ruta declarada a su tenant | Cuatro la declaran, cuatro se reclasificaron |
