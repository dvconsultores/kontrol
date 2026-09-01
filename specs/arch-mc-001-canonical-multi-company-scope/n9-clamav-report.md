# ANÁLISIS ANTIVIRUS — N9

## 1. Escáner real, no simulado

| | |
|---|---|
| Producto | **ClamAV 1.4.3** |
| Bases de firmas | 3 (`main`, `daily`, `bytecode`), completas |
| Modo | Real. Sin simulación en la aceptación |

## 2. Máquina de estados

`PENDING_SCAN` → `CLEAN` · `INFECTED` · `SCAN_FAILED`

Solo `CLEAN` permite la entrega. El propio módulo lo escribe en su cabecera: no
poder analizar un archivo **significa** `SCAN_FAILED`, y lo que no está `CLEAN`
no se entrega.

## 3. Comprobado

| Caso | Resultado |
|---|---|
| Archivo limpio | `CLEAN`, se entrega |
| EICAR | `INFECTED`, se rechaza y **no se almacena** |
| Escáner ausente | `SCAN_FAILED`, nunca `CLEAN` |
| Análisis desactivado | Se declara, no se disfraza |
| Entrega con análisis pendiente o fallido | Bloqueada |

La tercera fila es la que importa: un escáner que no responde no puede producir
un falso limpio, porque la ausencia de respuesta no es una respuesta negativa.
