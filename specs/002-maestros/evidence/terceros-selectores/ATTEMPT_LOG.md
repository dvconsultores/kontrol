# TERCEROS-SELECTORES-E-INTEGRIDAD-DE-ROL-01 · registro de intentos

Ledger propio. Llamadas secuenciales, una a la vez.

## Justificación de TER-K (registrada antes de su llamada)

- PREVIOUS_SUBTASK: TER-C (pruebas de dominio, presupuesto cerrado) y TER-D (implementación y ajustes, presupuesto cerrado).
- PREVIOUS_ROOT_CAUSE: frontera de dominio sin rol ni estado. Ya corregida y en verde.
- NEW_SUBTASK: TER-K, prevista en el §38 del encargo.
- NEW_ROOT_CAUSE: 0.
- NEW_TECHNICAL_BOUNDARY: 1. Fase de mutación: seis filas de la matriz sin prueba que las distinga (B4, B6, B12, B16, B21 y B31).
- WHY_DIFFERENT: fichero nuevo y pruebas nuevas. No corrige ninguna prueba ni código de TER-C o TER-D.
- EVIDENCE: `mutbt` con 25 de 31 muertos sobre el árbol con TER-D aplicada.

## Llamadas

| Subtarea | Intento | Modelo | Coste | Resultado |
|---|---|---|---|---|
| TER-C pruebas rojas de dominio y API | ATTEMPT | pro | $0,007442 | AUDIT_REJECT: `supplier_id` en `create_schedule`, pruebas de API saltadas en SQLite, BR-09 enrevesado |
| TER-C | (sin respuesta) ×2 | pro | desconocido | La API respondió `terminated`; el puente reintentó y la sesión se cerró. Sin propuesta: no consume el hueco. El puente no debía reintentar |
| TER-C | RETRY_1 | pro | $0,005475 | Dominio en rojo por la causa correcta. AUDIT_REJECT: `_operador` inventado, porque el brief de Claude cortó el helper |
| TER-C | RETRY_2 | flash | $0,000360 | AUDIT_PASS. Presupuesto cerrado |
| TER-D autoridad backend y filtro | ATTEMPT | pro | $0,005789 | Producto correcto, 48 de 48. AUDIT_REJECT por forma (función dentro del recuadro de comentario) y 3 pruebas previas a ajustar |
| TER-D | RETRY_1 | pro | $0,004805 | Ajustes correctos; `test_terceros_http.py` con `reloj` y RIF inventado |
| TER-D | RETRY_2 | flash | $0,000230 | AUDIT_PASS. Presupuesto cerrado |
| TER-A prueba roja de pantallas | ATTEMPT | pro | $0,004692 | AUDIT_REJECT: import dinámico con alias y `.default` |
| TER-A | RETRY_1 | pro | $0,006931 | AUDIT_PASS; 57 de 57 en rojo, reproducido |
| TER-E selector y `extraParams` | ATTEMPT | flash | $0,000580 | AUDIT_PASS |
| TER-F ventas | ATTEMPT | flash | $0,001131 | AUDIT_PASS |
| TER-G compras | ATTEMPT | flash | $0,001398 | AUDIT_PASS |
| TER-H fiscal y regulatorio | ATTEMPT | flash | $0,000588 | AUDIT_PASS |
| TER-I pruebas del selector y caché | ATTEMPT | pro | $0,008439 | AUDIT_REJECT: 8 de 24 en rojo por errores de la prueba |
| TER-I | RETRY_1 | pro | $0,011312 | 24 de 24, pero TS-17b no mataba T6 (ids distintos) |
| TER-I | RETRY_2 | flash | $0,000188 | AUDIT_PASS; T6 muerto. Presupuesto cerrado |
| TER-K supervivientes de mutación | ATTEMPT | flash | $0,000669 | AUDIT_PASS; 6 de 6 mutantes muertos |
| TER-L E2E preparada | ATTEMPT | flash | $0,001239 | AUDIT_PASS por lectura y TSC; **sin ejecutar** |

Total: 17 llamadas con respuesta, $0,061268, más 2 sin respuesta de coste desconocido. Reintentos: 7. Excepciones de la dueña: 0.

## Notas

- **Errores de Claude:** el comando recuperado del arnés de mutaciones volvió a lanzar 18 mutaciones por accidente (árbol restaurado y verificado después); el brief de TER-C recortó un helper con `sed`; el inventario decía 16 selectores y son 14.
- **Interrupción:** el scratchpad se perdió con el reinicio. Los briefs y el arnés se recuperaron del transcript.
