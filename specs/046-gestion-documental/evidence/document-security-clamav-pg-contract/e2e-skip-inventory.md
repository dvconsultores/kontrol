# Las cuatro omitidas E2E (`ENTORNO-SIN-CLAMSCAN`)

El runner (`qa/e2e_corrida.py` 212–230, 309) resuelve `clamscan` como lo hace el backend y exporta
`KONTROL_E2E_SCANNER_AVAILABLE=false` cuando no hay binario o el análisis está apagado; las specs leen esa variable.

| Spec · prueba | Flujo | Por qué se omite | Analizador | EICAR | Podría correr con analizador en QA | PG-only | Dueña |
|---|---|---|---|---|---|---|---|
| `documents.spec.ts` · «carga, versión y descarga por la interfaz real» | subir PDF limpio, versionar, descargar | sin `clamscan` ninguna carga con análisis obligatorio crea versión (`SCAN_FAILED`) | sí | no | sí | n/a (E2E siempre PostgreSQL) | 046 |
| `documents.spec.ts` · «una versión histórica no se reinterpreta al cargar otra» | dos cargas | ídem | sí | no | sí | — | 046 |
| `documents.spec.ts` · «un reintento tras el fallo no deja el formulario sin salida» | carga fallida y reintento | ídem | sí | no | sí | — | 046 |
| `documents-a11y.spec.ts` · «la carga de archivo es operable solo con teclado» | carga por teclado hasta versión creada | ídem | sí | no | sí | — | 046 |

`E2E_SKIP_UNKNOWN = 0`. Las cuatro son manifestaciones del mismo hecho (binario ausente); ninguna usa EICAR.
