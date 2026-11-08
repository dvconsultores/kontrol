# ENTERPRISE-DELIVERY-AND-IMPORTS-018 · registro de intentos

Llamadas secuenciales; todo el código lo propone DeepSeek salvo resolución mecánica de conflictos de la fusión.

| Subtarea | Intento | Modelo | Coste | Resultado |
|---|---|---|---|---|
| EDI-A migración de fusión | ATTEMPT | flash | $0,000237 | AUDIT_PASS |
| EDI-C backend de importaciones | ATTEMPT | pro | $0,016642 | AUDIT_REJECT parcial: nombre con `select("name")`, ids `UUID` contra columnas de texto, imports, duplicados, SEARCH sin coincidencia. Informe final truncado |
| EDI-C | RETRY_1 | pro | $0,008753 | Corrige `require_write_allowed` ausente en mutaciones, ids como cadena y consultas de nombre. **Desviación:** tres SEARCH idénticos de coincidencia múltiple aplicados como uno global; un bloque de prueba inventado descartado. `api.py` de ATTEMPT retirado para que entrara el nuevo |
| EDI-C | RETRY_2 | flash | $0,000117 | Sangría en `database.py` y restos en pruebas. Bloques dictados por Claude. Presupuesto cerrado |

### EDI-D (nueva subtarea)
- PREVIOUS_SUBTASK: EDI-C, presupuesto cerrado
- NEW_ROOT_CAUSE: MODELO_NO_CARGA. `app.core.scopes` no existe (es `app.core.scope`), `__table_args__` duplicado e ids anotados como UUID. El brief de Claude no dio la ruta real
- NEW_TECHNICAL_BOUNDARY: solo `imports/models.py`
- EVIDENCE: ModuleNotFoundError en las 9 pruebas; mypy 156
| EDI-D | ATTEMPT | flash | $0,000103 | Bloques dictados por Claude. AUDIT_PASS |
| EDI-D | RETRY_1 | flash | $0,000532 | Corrige el filtro que vaciaba el listado y pruebas. Bloques dictados por Claude |
| EDI-E pantallas | ATTEMPT | pro | $0,013505 | AUDIT_REJECT: `TextInput` tratado como valor (brief de Claude sin ese contrato), empresa nula, prueba sin QueryClientProvider. Rutas, menú, filtro y textos de Terceros aplicados |
| EDI-E | RETRY_1 | pro | $0,017724 | Páginas aplicadas; TSC y ESLint limpios. 4 de 7: defecto real, el listado siempre en error |
| EDI-E | RETRY_2 | flash | $0,000158 | Bloques dictados por Claude. Presupuesto cerrado |
| EDI-F E2E de importaciones | — | — | — | Llamada solo de pruebas 1 de 2 permitidas; lleva también el selector pendiente de EDI-E, con presupuesto cerrado |
| EDI-F | ATTEMPT | flash | $0,000766 | Aplicada. Corrida en Chrome real: destapó los defectos de EDI-G. Sonda temporal local, sin commitear |

### EDI-G (nueva subtarea)
- NEW_ROOT_CAUSE: DEFECTOS_VISIBLES_SOLO_EN_NAVEGADOR: expediente sin refrescar tras cada acción, avisos sin `role="alert"` y persistentes, campos sin etiqueta visible
- NEW_TECHNICAL_BOUNDARY: integración real de interfaz y backend
- EVIDENCE: la red muestra PATCH 200 sin GET posterior del detalle
| EDI-G | ATTEMPT | flash | $0,001263 | Bloques dictados por Claude tras depurar en navegador. Duda de DeepSeek resuelta: el prefijo coincide. AUDIT_PASS |
| EDI-G | RETRY_1 | flash | $0,000173 | Quita la key que borraba lo escrito; hallado por la E2E real. Bloques dictados por Claude |

| EDI-H semilla documental | ATTEMPT | flash | $0,000180 | Declara ImportDocument en la guarda N9. Bloques dictados. AUDIT_PASS |

## Totales

13 llamadas · $0,060653. Llamadas solo de pruebas: 2 (EDI-F, EDI-H). Reintentos: 6.
**Declaración:** EDI-C RETRY_2, EDI-D y su RETRY_1, EDI-E RETRY_2, EDI-G y su RETRY_1, y EDI-H llevan bloques dictados literalmente por Claude tras depurar; DeepSeek los transcribió. La resolución de conflictos de la fusión y las declaraciones de cabeza y contador las aplicó Claude como ajuste mecánico.
