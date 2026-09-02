# N10 — FRONTEND Y CONTRATO CON EL BACKEND

N10 no cambió el frontend. Comprobó que su contrato con el backend sigue
alineado después de los cambios del backend, y actualizó una cifra que había
envejecido.

## Regresión

| Comprobación | Resultado |
|---|---|
| Vitest | 278 / 278 |
| `tsc -b` | limpio |
| ESLint (`--max-warnings 0`) | limpio |
| `npm run build` | limpio |

En una de las tres ejecuciones apareció un error no reproducible en el
desmontaje, sin prueba fallida. No se reprodujo en las otras dos y no se
presenta como aprobado ni como fallo: se registra.

## El efecto de los cambios del backend

Diez operaciones pasaron a exigir la cabecera de empresa. Ninguna requirió tocar
el frontend, y el motivo es una decisión de N6: la cabecera la pone el cliente
en un único sitio, a partir de la empresa activa de la pestaña, y la lista de
rutas exentas enumera la excepción, no la regla. `/organization/establishments`
no está en esa lista, así que ya la enviaba.

## La caché, revisada por si acaso

`GET /organization/establishments` pasó de ser de tenant a ser de empresa. Su
clave de consulta es `["organization", "establishments", branchId]` y **no**
lleva la empresa.

No hace falta que la lleve. `queryKeyHashFn` antepone la empresa activa a toda
clave cuya raíz no esté en `RAICES_SIN_EMPRESA`, y `"organization"` no lo está.
Es exactamente el motivo por el que N6 lo resolvió en la función de hash y no
consulta por consulta: la clave que nadie recordó actualizar quedó separada de
todos modos.

Contaminación entre empresas: 0. Entre pestañas: 0.

## Una cifra que envejeció

El comentario de `client.ts` justificaba la lista de exenciones diciendo «casi
todo es de empresa —123 de 153 modelos—». Hoy son **136 de 166**. El argumento
no cambia; el número sí, y un número obsoleto en documentación activa es
justamente lo que N10 tenía que eliminar.
