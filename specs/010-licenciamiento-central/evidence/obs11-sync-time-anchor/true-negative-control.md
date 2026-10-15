# Control de verdadero negativo
`test_verdadero_negativo_servidor_atrasado`: activación, luego sync con `server_time = ahora − 10 min`. El sync responde
`SUCCESS` y `last_reliable_date` queda **estrictamente posterior** al reloj del servidor (conserva la activación): la regla
monótona del producto (servicio 849–852) funciona. PASS en SQLite y PostgreSQL. Conclusión: el rojo de la suite completa es
exactamente este verdadero negativo disparado por una referencia envejecida; la prueba lo etiquetaba como fallo.
