# AAL · Ficha de pantalla

**Ruta:** Gobierno › Expedientes de contratación › un expediente › sección **Decisión** › formulario de decisión.

**Cuándo aparece:** cuando se han elegido un acto y el resultado «Adjudicada», y existe la opción propuesta de la recomendación.

## Panel «Control del límite de autoridad»

`section` con nombre accesible y un `h3`.

| Campo | Valor | Si falta |
|---|---|---|
| Monto declarado de la oferta | Total con tributos de la versión vigente | «No declarado» |
| Moneda | VES, USD o EUR | «—» |
| Autoridad efectiva | Nombre del cargo que dicta el acto | «Cargo del acto» |
| Límite de aprobación | «50000.00 USD» o «Sin límite» | «Sin competencia vigente» |
| Resultado de validación | Dentro del límite · Sin límite · Excede el límite · No comparable por moneda · Monto no declarado | — |

Debajo va el mensaje del backend. Es rojo cuando no permite adjudicar, y en ese caso nombra el monto, el límite y el cargo, y dice qué hacer.

## Comportamiento

- El panel **anticipa**; no decide. El botón «Registrar decisión» no se desactiva: al confirmar, el backend repite la comprobación con los datos vigentes y bloqueados.
- El bloqueo (409) se muestra en el `role="alert"` de la confirmación con el mensaje del backend. No se registra nada y no hay forma de continuar.
- Al cambiar el acto, el panel se recalcula con los datos del acto nuevo.
- Sin UUID; 1 columna en móvil y 2 desde `sm`; textos con `break-words`; sin desplazamiento horizontal a 390 ni a 320.
