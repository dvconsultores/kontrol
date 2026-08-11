# CLEANUP-PLAN — RUN `KONTROL-QA-20260810-234937`

No se crearon datos ni se emitieron documentos → **no hay limpieza que ejecutar**.

## Plan condicional (si se re-ejecuta la prueba y se crean datos QA)
- Conservar documentos QA (facturas, notas, movimientos, pagos, cobros, auditoría) para trazabilidad.
- NO eliminar GLOBAL DV.
- Los maestros ficticios QA (proveedores ALFA/BETA, clientes ORION/NOVA, productos QA-*, almacenes ALM-VAL-QA/ALM-CCS-QA, sucursales VAL-QA/CCS-QA) pueden desactivarse al final SI no rompen trazabilidad y solo si pertenecen a este RUN_ID.
- NO ejecutar limpieza destructiva: no DROP/TRUNCATE, no `docker compose down -v`, no reset de BD, no borrado de volúmenes.

**NO EJECUTADO** (no aplica esta ejecución).
