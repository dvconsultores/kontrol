# ADAPTACIÓN A TAMAÑOS — N6

| Ancho | Selector visible | Utilizable | Sin desbordar | Veredicto |
|---|---|---|---|---|
| 320 | sí | sí | sí | **PASS** |
| 375 | sí | sí | sí | **PASS** |
| 768 | sí | sí | sí | **PASS** |
| 1024 | sí | sí | sí | **PASS** |
| 1280 | sí | sí | sí | **PASS** |
| 1440 | sí | sí | sí | **PASS** |

En los seis tamaños se comprueba además que el cambio de empresa funciona de
verdad, no solo que el control quepa.

## El nombre largo

El arranque de pruebas siembra la segunda empresa como «INVERSIONES SEGUNDA
EMPRESA COMPAÑIA ANONIMA» a propósito. Los nombres jurídicos venezolanos son
largos, y un selector que no los recorte empuja la cabecera y provoca scroll
horizontal en toda la aplicación.

El nombre se recorta con el nombre completo en `title`, y el ancho del control
está acotado. En los tamaños pequeños se ocultan el código y el RIF, que son
secundarios frente a la razón social.

## Un ajuste en las pruebas

Al ancho de un móvil, las notificaciones cubren la cabecera y bloquean el clic
sobre el selector. Las pruebas las cierran antes de operar. Es comportamiento
del sistema de notificaciones, anterior a N6 y ajeno a esta fase; se registra
aquí para que no se pierda.
