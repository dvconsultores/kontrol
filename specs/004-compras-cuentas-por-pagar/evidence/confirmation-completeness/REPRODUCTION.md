# Reproducción del residuo de confirmación (antes de la reparación)

- **Fecha:** 2026-11-13.
- **HEAD:** `5b7e1b9`, con el árbol limpio.
- **Motor:** PostgreSQL de QA (`ktest`).

La sonda es diagnóstica, de Claude, y vive fuera del repositorio. Reutiliza los helpers ya auditados de `tests/test_spec015_received_unconfirmed.py` (`_orden`, `_recibir`, `_confirmar`, `_sin_confirmar`) y llama al servicio real.

## Escenario

1. Orden de 100 con destino al almacén W.
2. Recepción de 100, con 80 aceptadas y 20 rechazadas en la aceptación.
3. Conteo y confirmación: 50 a DISPONIBLE y 10 a RECHAZADO. Faltan 20 por decidir.
4. Segunda confirmación de las 20 restantes.

## Resultado observado

```text
REPRO estado=CONFIRMADA saldos={'RECIBIDO': '20.000000', 'DISPONIBLE': '50.000000', 'RECHAZADO': '10.000000'}
      sin_confirmar=0 segunda=ALREADY_CONFIRMED
```

```text
DEFECT_REPRODUCED=1
RESIDUE_QUANTITY=20
RECEIPT_MARKED_CONFIRMED=1
RESIDUE_STILL_RECIBIDO=1
SECOND_CONFIRMATION_POSSIBLE=0
PLANNING_SEES_RESIDUE=0   (recibido_sin_confirmar = 0)
```

Las 20 unidades quedan en `RECIBIDO`, no se pueden vender, la confirmación no puede repetirse y la planificación tampoco las ve: no tienen ninguna ruta de decisión.

## E2E-INVCONF-ORDER-DEPENDENCY (preflight)

`inventory-confirmation.spec.ts` se ejecutó sola sobre una base efímera recién sembrada (`qa/e2e-run.py --con-analizador`). Fallaron los tres casos con `TypeError: Cannot read properties of undefined (reading 'id')` en `(almacenes.items ?? almacenes)[0].id`: la siembra no crea almacenes.

```text
E2E_INVCONF_ORDER_DEPENDENCY_REPRODUCED=1  TEST_HARNESS_ONLY=1  LOCAL_TO_TOUCHED_FLOW=1
```

Se corrige en la tarea B, solo en el arnés: crear sucursal y almacén si no hay ninguno, como ya hace `conteo-independiente.spec.ts`.
