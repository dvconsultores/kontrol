# REGULATORIO — EVIDENCIA A/B

PostgreSQL 18.6 · **10 pruebas** · Veredicto: **PASS**

No se toca ninguna capacidad SICA, SIGESAI ni SACS. Solo se comprueba de quién
es cada cosa.

## Por qué importa aquí

Un permiso es una autorización nominal: la tiene una empresa concreta ante un
organismo concreto. Prestarlo a otra empresa del grupo es exactamente lo que la
autoridad no permite, y produce un despacho que en el registro oficial no
existe.

## Cobertura

| Comprobación | Resultado |
|---|---|
| Permisos con su empresa, verificado en la base | PASS |
| Listado sin intersección | PASS |
| Transicionar el permiso ajeno | BLOCKED |
| Emitir un permiso con el tipo de otra empresa | BLOCKED |
| Homologar un tipo contra la autoridad de otra empresa | BLOCKED |
| Vehículos y conductores sin mezcla | PASS |
| Permiso de A amparando un vehículo de B | BLOCKED |
| Documentos oficiales sin mezcla | PASS |
| Alcance desde el otro tenant | BLOCKED |
| Ninguna fila hacia una empresa inexistente (11 tablas) | PASS |

## Defecto encontrado

`create_permit` aceptaba `vehicle_id` sin comprobar de quién era el vehículo. Un
permiso de la empresa A podía amparar una unidad de la empresa B: sobre el papel,
un despacho autorizado que el organismo no reconocería. Corregido.
