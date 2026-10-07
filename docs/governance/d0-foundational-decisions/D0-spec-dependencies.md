# DEPENDENCIAS: QUÉ SPECS NO PUEDEN COMENZAR HASTA CERRAR QUÉ DECISIÓN

Una Spec «no puede comenzar» cuando escribirla sin la decisión produciría un diseño que habría que
rehacer, no meramente ajustar.

## Bloqueo directo

| Decisión | Estado | Specs que NO pueden comenzar |
|---|---|---|
| D0-01 | **CLOSED** | — (ninguna bloqueada para empezar; **las 56 para cerrarse**) |
| D0-02 | **CLOSED** | 045, 015, 017, 025, 030, 033 → **desbloqueadas** |
| D0-03 | **CLOSED** | 030, 029, 031, 032, **023** → **desbloqueadas** |
| D0-04 | **CLOSED** | 008, 022, 031, 032 → **desbloqueadas** |
| D0-05 | **CLOSED** | 012, 029, 034 → **desbloqueadas** |
| D0-06 | **CLOSED / IMPLEMENTED** (frontera, 2026-10-07) | Ninguna. Sincronización autenticada implementada (2026-10-07); 004 sigue abierta solo por la prueba contra red real desplegada y la rotación de claves |
| D0-07 | LEGAL_VALIDATION_PENDING | Ninguna. 039-043 y 056 no pueden **cerrarse** sin validación |
| D0-08 | **CLOSED** | 046, 018, 020, 035 → **desbloqueadas** |
| D0-09 | **CLOSED** | 011, 019, 021, 029, 032 → **desbloqueadas** |

> **Corrección G0:** esta tabla omitía `023` en D0-03 (el motor de saldos recibe la dimensión de
> ubicación y la restricción de no sobre-reserva, que son modelo). Corregido arriba.
| D0-10 | **CLOSED** | 021, 022, 032 → **desbloqueadas** |
| D0-11 | **CLOSED** | 034 → **desbloqueada** |
| D0-12 | **CLOSED** | 033, 034 → **desbloqueadas** |
| D0-13 | **CLOSED** | 007 → **desbloqueada** |

## Cadena de dependencias entre Specs, ya con D0 resuelto

```
D0 cerrado
   │
   ├─► 045 Aprobaciones ─────┐
   ├─► 008 Almacenes ────┐    │
   ├─► 046 Documentos ───┤    │
   ├─► 012 Comercial ────┤    │
   └─► 011 Unidades ─────┤    │
                         │    │
        007 Dimensiones ─┤    │
                         ▼    ▼
        019 Recepción ──► 020 Incidencias ──► 021 Confirmación ──► 022 Put-away
                                                                      │
        018 Importación ──► 026 Landed cost                           │
                                                                      ▼
        029 Pedido ──► 030 Reserva ──► 031 Cola/ruta ──► 032 Picking ──► 033 Confirmación
                                                                              │
                                                                              ▼
                                                                     034 Facturación ──► 035 Despacho
```

## Regla de precedencia derivada

> Ninguna Spec de la cadena de preparación (031→035) debe escribirse antes de 008, 011 y 046.
> Ninguna Spec de la cadena de entrada (019→022) debe escribirse antes de 008, 009 (UOM), 046 y 010.
> **034 es la última de su cadena**, no la primera, pese a ser la más visible para el negocio.

## Specs que ya no dependen de ninguna decisión abierta

Las **34** Specs restantes (56 − 22 bloqueadas). Solo 004 y el bloque fiscal 039-043/056 tienen su **cierre**
condicionado a decisiones externas al software, y ninguna de ellas impide comenzar el trabajo.
