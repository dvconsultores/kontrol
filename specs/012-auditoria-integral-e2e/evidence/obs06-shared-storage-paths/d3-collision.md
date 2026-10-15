# D3 · Colisión de nombres
Inventario (`writer-inventory.md`): las exportaciones se nombran `report-<clave>-<AAAAMMDDhhmmss>.<csv|pdf>` (resolución
de **un segundo**, `reporting/service.py:235-236`); los documentos usan un token opaco de 32 caracteres (sin colisión
práctica). La sonda aplica la fórmula real con la marca de segundo inyectada en dos procesos consecutivos.
| Registro | Valor |
|---|---|
| `file_ref` | `report-executive_ventas-20261015050000.csv` en los dos procesos, en el **mismo fichero** (`<tmp>/kontrol-test-storage/exports/…`) |
| A: existía antes | no |
| B: existía antes | **sí**, con el contenido de A (`pid=<A>`) |
| B sobrescribió a A | **YES** (sin error: `write_text` sobre el mismo nombre) |
Clase: `CROSS_PROCESS_COLLISION` realista para exportaciones (dos corridas o dos exportaciones del mismo informe en el
mismo segundo); no aplica a documentos. Fichero de la sonda retirado.
