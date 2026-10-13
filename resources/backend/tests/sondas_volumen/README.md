# Sondas del volumen de instalación

Módulos de prueba deliberadamente pequeños —y uno deliberadamente roto— que
`tests/test_volumen_de_instalacion.py` ejecuta en procesos aparte, en serie o a la vez, para
comprobar que cada proceso de `pytest` recibe su propia raíz de volumen de instalación, cada
módulo su propio volumen vacío, que la clave sintética que escribe un proceso no la ve ni la
pisa otro, y que nada queda en disco al terminar, pase o falle la prueba.

Cada sonda cuenta lo que vio por líneas JSON en el fichero `KONTROL_SONDA_INFORME`: rutas,
modos y huellas sha256 truncadas. Nunca el contenido de la clave.

No se llaman `test_*.py` a propósito: `pytest tests` no los recoge. Solo corren cuando se
les nombra por su ruta.
