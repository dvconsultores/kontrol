# D2 · Visibilidad entre procesos
A escribe `marcador-<pidA>` en `<storage>/sonda/` y `<backup>/sonda/` y termina; B arranca con la ruta del marcador de A y
lista su propio almacén; luego al revés.
| Registro | Valor |
|---|---|
| `B_SEES_A` | **YES** (ruta visible y el marcador de A aparece en el listado de B: 4 marcadores en almacén y 4 en respaldos tras las corridas de D1) |
| `A_SEES_B` | **YES** |
| Marcador de A tras terminar A | existe (nadie limpia) |
Un proceso ve, lista y podría leer o sobrescribir lo que otro escribió. Marcadores sintéticos retirados al terminar el diagnóstico.
