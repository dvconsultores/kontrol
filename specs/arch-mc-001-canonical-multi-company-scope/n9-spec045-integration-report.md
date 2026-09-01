# INTEGRACIÓN CON LA SPEC 045 — N9

## 1. La cadena

```
ApprovalRequest  →  DocumentLink  →  frozen_version_id  →  DocumentVersion
```

`046` ofrece la capacidad de congelar; **`045` decide cuándo**: al resolverse
una aprobación, sus documentos quedan atados a la versión usada.

Es deliberado que el disparo sea del consumidor. 046 no sabe cuándo una entidad
ajena se vuelve inmutable, y adivinarlo congelaría versiones que aún podían
cambiar.

## 2. Comprobado

| Caso | Resultado |
|---|---|
| Vínculo a una solicitud de aprobación | PASS |
| Congelado por el consumidor | PASS — una versión congelada |
| Nueva versión posterior | PASS — se crea la 2 |
| El vínculo sigue en la versión 1 | **PASS** |
| Una versión congelada no se desvincula | PASS |
| Una versión referenciada no se purga | PASS |

La cuarta fila es la que da sentido a la aprobación: si al mirar una solicitud
resuelta se resolviera la versión **actual**, se estaría diciendo que se aprobó
un documento que nadie aprobó.

## 3. `CVG-045-04`

Estado en la convergencia de 045: **`RESOLVED_BY_SPEC_046`**, cerrado el
2026-08-30, con cero cambios en el modelo de 045.

N9 lo reconfirma contra el sistema actual. Sigue resuelto.

## 4. La seguridad de 045 no se reabre

La vulnerabilidad que N5 corrigió —el cuerpo de la petición imponiendo la
empresa— sigue cerrada, y su prueba sigue verde. N9 no toca el motor de
aprobaciones, ni la segregación de funciones, ni los flujos.
