# RECEPCION-ALMACEN-TEXTO-LIBRE · registro de intentos

Ledger propio. Llamadas secuenciales, sin commits en rojo.

| Subtarea | Intento | Coste | Resultado |
|---|---|---|---|
| ALMREC-A prueba roja y servicio | 1 | $0,001492 | AUDIT_PASS; tres pruebas ajustadas en C |
| ALMREC-B producto | 1 | $0,000502 | AUDIT_PASS |
| ALMREC-C ajuste de pruebas | 1 | $0,000394 | AUDIT_PASS |
| ALMREC-E E2E preparada | 1 | $0,000302 | AUDIT_PASS; sin ejecutar |

Coste total: $0,002690 en 4 llamadas.

## Reconciliación del registro (ciclo RECEPCION-LINEA-ORDEN-INTEGRIDAD-01, 2026-11-07)

La tabla anterior se conserva tal como se escribió. La dueña no aceptó la clasificación de ALMREC-C
como «ajuste, no retry formal». Revisión:

- ALMREC-C corrigió pruebas que ALMREC-A había escrito. Fallaban porque elegían el almacén antes de
  que cargaran las opciones: un error de esas pruebas, dentro del mismo fichero y del mismo objetivo.
- No hubo causa raíz nueva ni frontera técnica nueva que la justifique como subtarea distinta.

`ALMREC_C_IS_SAME_SEMANTIC_SUBTASK_AS_A = 1`. Contador efectivo:

| Subtarea | Contador real |
|---|---|
| ALMREC-A (prueba roja y servicio) | ATTEMPT + RETRY_1 (la llamada registrada como ALMREC-C) |
| ALMREC-B | ATTEMPT |
| ALMREC-E | ATTEMPT |

`ALMREC_EFFECTIVE_RETRY_COUNT = 1`, por tanto `DEEPSEEK_RETRIES` del ciclo fue 1, no el 0 informado.
Quedó dentro del máximo de 2, así que los cambios certificados no se invalidan. No se reinicia ningún
presupuesto.
