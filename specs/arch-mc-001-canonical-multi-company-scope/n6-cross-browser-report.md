# CROSS-BROWSER — N6

**75 pruebas** ejecutadas en los tres motores. Sin fallos.

| Capacidad | Chromium | Firefox | WebKit |
|---|---|---|---|
| Resolución con una empresa | PASS | PASS | PASS |
| Selección obligatoria con varias | PASS | PASS | PASS |
| Cabecera por empresa | PASS | PASS | PASS |
| Sin tenant en la cabecera | PASS | PASS | PASS |
| Preferencia al recargar | PASS | PASS | PASS |
| Aislamiento entre pestañas | PASS | PASS | PASS |
| Aislamiento de caché | PASS | PASS | PASS |
| Almacenamiento manipulado | PASS | PASS | PASS |
| Cabecera forzada a empresa ajena | PASS | PASS | PASS |
| Cabecera forzada a otro tenant | PASS | PASS | PASS |
| Contexto propio funcional | PASS | PASS | PASS |
| Cuerpo que no impone la empresa | PASS | PASS | PASS |
| Cambio de usuario en el navegador | PASS | PASS | PASS |

## WebKit

Los puntos que en fases anteriores dieron problemas de entorno se comprobaron
expresamente: `sessionStorage` por pestaña, cookies sobre http en local
—`KONTROL_COOKIE_SECURE=false`, sin lo cual WebKit rechaza cookies `Secure` y
falla toda la autenticación—, y la navegación entre pestañas.

Ninguno requirió tratamiento especial en el código: el mecanismo de contexto por
pestaña se comporta igual en los tres motores.

## Accesibilidad y tamaños

Las doce pruebas de accesibilidad y adaptación se ejecutan en Chromium, que es
donde corre axe-core en esta instalación. Los tres motores comparten el mismo
marcado, y el comportamiento de teclado se verificó también en Firefox y WebKit
dentro de la suite multiempresa.
