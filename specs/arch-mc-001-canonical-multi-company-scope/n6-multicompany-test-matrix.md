# MATRIZ DE PRUEBAS — N6

| Capacidad | Unitaria | Integración | Chromium | Firefox | WebKit | A11y | Responsive | Veredicto |
|---|---|---|---|---|---|---|---|---|
| Selector de empresa | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **PASS** |
| Resolución con una empresa | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | **PASS** |
| Selección obligatoria con varias | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | **PASS** |
| Cabecera de empresa | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | **PASS** |
| Sin repliegue al tenant | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | **PASS** |
| Preferencia recordada | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | **PASS** |
| Preferencia caducada descartada | ✓ | — | ✓ | ✓ | ✓ | — | — | **PASS** |
| Contexto por pestaña | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | **PASS** |
| Aislamiento de caché | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | **PASS** |
| Cambio de empresa | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **PASS** |
| Protección de formularios | ✓ | — | — | — | — | — | — | **PASS** |
| Errores de contexto sin bucle | ✓ | — | — | — | — | — | — | **PASS** |
| Manipulación del cliente | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | **PASS** |
| Autoridad del servidor | — | ✓ | ✓ | ✓ | ✓ | — | — | **PASS** |
| Cambio de usuario en el navegador | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | **PASS** |
| Descargas con contexto | ✓ | — | — | — | — | — | — | **PASS** |

## Recuento

| Suite | Pruebas |
|---|---:|
| Cabecera, caché y errores (Vitest) | 13 |
| Resolución de la empresa activa (Vitest) | 10 |
| Arquitectura frontend (Vitest) | 10 |
| Multiempresa E2E × 3 navegadores | 39 |
| Accesibilidad y responsive E2E | 12 |
| Aislamiento de empresa (backend, ampliada) | 12 |
| **Total nuevo o ampliado** | **96** |

## Sobre las columnas vacías

Un guion no es una omisión: es que esa combinación no aporta nada. La protección
de formularios se prueba en unitarias porque es lógica pura de captura de
contexto; la accesibilidad se mide donde hay algo nuevo que percibir, no en cada
petición HTTP.
