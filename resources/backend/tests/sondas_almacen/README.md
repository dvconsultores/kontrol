# Sondas del almacén de pruebas

Módulos de prueba deliberadamente pequeños —y uno deliberadamente roto— que
`tests/test_almacen_de_pruebas.py` ejecuta en procesos aparte, en serie o a la vez, para comprobar
que cada proceso de `pytest` recibe su propio almacén (`KONTROL_STORAGE_PATH`) y sus propios
respaldos (`KONTROL_BACKUP_PATH`), que dentro del proceso la configuración, el proveedor documental,
las exportaciones y la aplicación entera ven la misma raíz, que un marcador sintético escrito por un
proceso no lo ve otro, que dos exportaciones con el mismo nombre no se pisan entre procesos y que
nada queda en disco al terminar, pase o falle la prueba (SPEC054 · OBS-06).

Cada sonda cuenta lo que vio por líneas JSON en el fichero `KONTROL_SONDA_INFORME`: rutas y nombres
de marcadores sintéticos. Nunca documentos ni respaldos reales.

No se llaman `test_*.py` a propósito: `pytest tests` no los recoge. Solo corren cuando se les nombra
por su ruta.
