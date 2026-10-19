# Impacto medido del cierre de `get_db` tras la respuesta (FastAPI 0.141)

Sondas desechables, sin producto: una dependencia con `yield` anota su entrada y su salida.

| Sonda | V0 (FastAPI 0.115.6) | V2 (FastAPI 0.141.1) |
|---|---|---|
| ¿Llega la respuesta antes de que termine la salida? (salida lenta de 0,3 s) | no | **sí** |
| ¿`Depends` admite `scope`? | no | sí |
| Respuesta de 20 MB leída despacio (~1,5 s): salida respecto a las cabeceras | −0,001 s | −0,000 s |
| Ídem: salida respecto al fin de la lectura del cliente | −1,487 s | −1,469 s |
| ¿Se retiene la dependencia (y su conexión) mientras el cliente lee? | no | **no** |
| Escenario C2 del producto (`sonda_u03`): conexiones prestadas al recibir la última respuesta | 0 | 10, y 0 a los 50 ms (15 = 15, sin fugas) |

**Lectura:** con 0.141 la sesión de `get_db` se cierra justo después de que el cuerpo se entrega al socket, no antes.
- La conexión **no** queda retenida por un cliente lento.
- El efecto es una ventana de milisegundos entre que el cliente recibe la respuesta y que la conexión vuelve al pool.
- Solo lo nota una prueba que comprueba el pool en ese mismo instante (U03 y U04 en SQLite).
- `get_db` solo hace `db.close()` en su salida: no hay commit ni auditoría diferidos.

**Clasificación:** PACKAGE_VERSION_INCOMPATIBILITY de impacto medido despreciable para el producto. Su resolución
(adaptar la prueba a la semántica nueva, o fijar el cierre previo con `Depends(get_db, scope=...)`) es una decisión
técnica del ciclo de normalización.
