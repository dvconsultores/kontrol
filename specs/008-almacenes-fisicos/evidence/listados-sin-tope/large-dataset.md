# Dataset controlado (W08)

Sintético, en proceso, sin producción ni PII: empresa D1 (tenant DEMO) con **1 100 listas de preparación** (`PK-00000…PK-01099`,
cada una sobre su pedido `SO-nnnnn` de un cliente sintético `CLI-1`) repartidas entre **300 almacenes** (`W0000…W0299`) en la
reproducción, y 7 almacenes (`W0…W6`) con cinco grupos de diez listas de **instante compartido** en la suite de pruebas
(`tests/test_listados_sin_tope.py`); empresa C2 (tenant T2) con 50 listas y 1 almacén que no deben aparecer. Cubre: página 1,
página intermedia, última página parcial (1 100 = 11 × 100; 55 × 20; 11 × 99 + 11), `offset`/`page` más allá del total, por
encima del máximo, y > 1 000 filas. Se crea en una base en memoria (SQLite) o en el schema del módulo (PostgreSQL) y
desaparece con la prueba.
