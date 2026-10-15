# Campaña de mutaciones (GOOD → PASS · MUTATED → FAIL · RESTORED → PASS desde copias GOOD; `__pycache__` purgado;
`PYTHONDONTWRITEBYTECODE=1`; juego: O11-01…06 + prueba objetivo; guion `<scratch>/o11/mutar.py`)
| Id | Mutación | Fichero | Detectada por | Resultado |
|---|---|---|---|---|
| M-01 | vuelve la constante de importación `SERVER_TIME` | módulo objetivo | O11-05 | 1 failed → restaurada 7/7 |
| M-02 | el reloj del servidor nace 5 min **detrás** de la activación | módulo objetivo | O11-01, O11-03, objetivo | detectada |
| M-03 | aserción incondicional (`is not None`) | objetivo | O11-05 | detectada |
| M-04 | tolerancia de una hora (`abs(...) < timedelta(hours=1)`) | objetivo | O11-05 | detectada |
| M-05 | reloj naive del anfitrión (`datetime.now()`) | transporte falso | O11-01, O11-03, O11-04, O11-05 | detectada |
| M-06 | `utcnow()` contra la convención | transporte falso | O11-01, O11-03, O11-04, O11-05 | detectada |
| M-07 | el producto adopta el servidor sin regla monótona | `service.py` (restaurado) | O11-02, O11-03, O11-06 | detectada |
| M-08 | `time.sleep(0)` en el módulo objetivo | módulo objetivo | O11-05 | detectada |
| M-09 | reintento `for … range(2): # retry` alrededor del sync | objetivo | O11-05 + objetivo (`idempotent` ya no es False) | detectada |
| M-10 | `pytest.skip` en el objetivo | objetivo | O11-05 (y el skip visible) | detectada |
| M-11 | `_now()` del producto pierde la zona | `service.py` (restaurado) | O11-01, O11-03, O11-06 | detectada |
| M-12 | regla monótona del producto invertida (`>`) | `service.py` (restaurado) | O11-01, O11-02, O11-03, O11-06 | detectada |
| M-13 | la regresión envejecida pierde sus aserciones (`is not None`) | O11-02 | **superviviente en la primera pasada** → O11-05 reforzado con el contrato de sus propias aserciones por AST → detectada en la reejecución | detectada |
**13/13 detectadas** (12 en la primera pasada; M-13 tras reforzar el contrato). Cada mutación restaurada con copia idéntica
(`filecmp`) y 7/7 tras restaurar. Fuente: `<scratch>/o11/dirigidas.txt`.
