# Programar descarga · registro de intentos

Todo con `deepseek-v4-pro` y `stream=true`. Tope global de 8 llamadas por ciclo; máximo 2 reintentos por subproblema.

| Llamada | Subproblema | Entrada/salida (tokens) | Coste | Resultado |
|---|---|---|---|---|
| DEEPSEEK_CALL_1 | A. Backend y pruebas | 5895/3344 | $0,005474 | Producto (`programar_descarga`, endpoint, payload del expediente, catálogo 477): AUDIT_PASS y aplicado. 17 PASS en PostgreSQL. Quedaban un E402 de ruff y `__import__("json")` en la prueba |
| DEEPSEEK_CALL_2 | B. Pantalla y E2E, más el reintento 1 de A | 5222/4794 | $0,006442 | Tipos, `ImportacionRecepcion`, columna de Recepciones y arreglo de la prueba (A·R1): AUDIT_PASS y aplicados. Rechazado el bloque E2E: `expect.poll` sin `await` y lectura del texto antes de que se refrescara la tarjeta |
| DEEPSEEK_CALL_3 | B·R1 | 1403/1082 | $0,001552 | AUDIT_PASS. E2E 14/14 a 1280; `importaciones` a 390 y 320 |

```text
TOTAL_CALLS=3  TOTAL_RETRIES=2  SUBPROBLEMS=2  MAX_RETRIES_SINGLE_SUBPROBLEM=1  GLOBAL_CAP_REACHED=0
TOTAL_COST=$0,013468
```

**Implementado por Claude:** ninguna línea de producto, prueba ni QA. Claude hizo:
- la autoridad, el contrato y la auditoría;
- la regeneración mecánica de las fixtures;
- las mediciones con sondas fuera del repositorio;
- los documentos.

**Incidencia de proceso:** el puente vuelve a avisar de que no pudo garantizar una copia byte a byte del brief.
