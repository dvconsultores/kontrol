# SPEC 029 — INVARIANCIA HISTÓRICA

## La afirmación

Una cotización emitida el día 1 sigue diciendo lo que dijo el día 1, aunque el
maestro cambie el día 2.

## Cómo se comprueba

No leyendo el código. Cambiando el maestro y volviendo a leer el documento.

| Prueba | Qué se cambia después | Qué debe seguir igual |
|---|---|---|
| `test_una_cotizacion_no_se_recalcula_cuando_cambia_la_lista` | V1 se supera; nace V2 a 120 | La línea sigue a 100 y sigue apuntando a V1 |
| `test_el_historico_sobrevive_al_archivado_de_su_version` | V1 se archiva | La línea sigue a 77 y su versión sigue siendo legible |
| `test_la_conversion_no_reprecia_en_silencio` | V2 a 999 entre aceptar y convertir | El pedido nace a 60 |

La segunda es la que prueba que la referencia basta: la Spec 012 garantiza que
una versión no se borra, solo se archiva, así que la clave foránea sigue
resolviendo cuando el maestro ya no está vigente.

## Dos mecanismos, dos motivos

**El precio va por referencia.** El valor ya está en la línea y la versión no
muta: `price_source_version_id` apunta a algo que no cambiará.

**La condición de pago va por snapshot.** Un maestro de condiciones **sí** se
edita en sitio: alguien puede corregir «30 días» a «45» sobre la misma fila.
Una referencia haría que todos los documentos empezaran a decir 45. El snapshot
dice lo que dijo entonces.

La distinción no es estilística: depende de si el dato al que se apunta es
inmutable. Cuando lo es, la referencia es mejor —no duplica—; cuando no lo es,
la referencia miente con el tiempo.

## Lo que esto hace posible

Reconstruir una cotización antigua sin consultar los maestros actuales. Es la
diferencia entre saber qué se ofreció y adivinar qué se habría ofrecido hoy.

## La guarda

`test_spec029_architecture.py` falla en construcción si alguien retira una
columna de evidencia, si el origen deja de apuntar a la versión, si la evidencia
se vuelve obligatoria —lo que impediría el legado— o si la conversión empieza a
llamar al resolutor.

Ocho pruebas estructurales. Existen porque esta deuda tardó dos Specs en
cerrarse y no debe reabrirse en una tarde.
