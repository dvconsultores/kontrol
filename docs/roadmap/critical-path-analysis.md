# ANÁLISIS DE CAMINO CRÍTICO

## Camino A — abastecimiento e inventario físico

```
017 OC ✅parcial
 ├→ 018 Importaciones        ✗ 0 tablas        → habilita 026 landed cost
 └→ 019 Recepción ✅parcial
     ├→ 020 Incidencias      ✗ 0 tablas
     └→ 021 Confirmación ✅parcial (compuerta de calidad)
         └→ 022 Put-away     ✗ 0 proceso        → habilita 031, 032
```

**Dónde se rompe de verdad.** La Spec 008 construyó zonas, pasillos, racks,
niveles y posiciones, y entregó `/locations/ordered` con el recorrido físico
determinista. `inventory_movements` **acepta** `location_id`.

Y `accept_receipt` llama a `record_movement(...)` **sin pasar ubicación**.

De modo que toda la mercancía recibida entra «al almacén» y no a un sitio. La
estantería existe y está vacía en el modelo. Eso es el hueco 022, y es también
la razón por la que `pick_list_lines` no tiene ni ubicación ni secuencia: no
habría nada que poner en ellas.

## Camino B — comercial y despacho

```
012 ✅ COMPLETE
 └→ 029 Cotización/pedido  ← todas sus dependencias satisfechas
     └→ 030 Crédito/reserva      ⛔ D0-03 decisión de negocio
         └→ 031 Cola de picking  ⛔ 022
             └→ 032 Picking      ⛔ 022
                 └→ 033 Confirmación ✗
                     └→ 034 Facturación ⛔ 033 + fiscal
                         └→ 035 Despacho
037 CxC ✅parcial ← 034
```

**Dónde se rompe.** En dos sitios distintos y por motivos distintos: 030 espera
una **decisión**, y 031/032 esperan una **capacidad**. Solo 029 no espera nada.

## Camino C — fiscal

```
014 ✅parcial
 └→ 039 Motor fiscal    ⛔ D0-07
     ├→ 040 Retenciones ⛔ D0-07  → bloquea 028
     ├→ 041 IGTF        ⛔ D0-07
     └→ 042 Documentos  ⛔ D0-07
         └→ 043 Libros  ⛔ D0-07
             └→ 056 Homologación ⛔ D0-07
```

Un solo bloqueo, externo a la ingeniería, gobierna seis Specs. Se puede
**construir** contra él; no se puede **liberar**.

## Camino D — transversal

```
045 ✅ COMPLETE      046 ✅ RECONVERGED
048 Integraciones ✅parcial
 ├→ 013 tasa BCV automática
 └→ 047 Notificaciones ✗
049 → 050 ← 023, 034, 037, 038
054 QA ← todas          055 Hardening
```

## El nudo, en una frase

Tres caminos esperan algo que la ingeniería no decide —la validación legal, el
momento de la reserva, la API de SICA— y **un solo camino espera código con
todas sus dependencias satisfechas**: el que empieza en 029.

## Grados de salida hoy

| Nodo | Desbloquea directamente | Peso |
|---|---|---:|
| 022 Put-away | 031, 032, y la calidad de 023 | 3 |
| 029 Cotización/pedido | 030, y da consumidor a 012 | 2 |
| 020 Incidencias | 021 → 022 | 1 (en cadena, 3) |
| 018 Importaciones | 026 | 1 |
| 048 Integraciones | 013, 047 | 2 |
| 033 Confirmación | 034, 035 | 2 |

022 desbloquea más, pero **no está lista**: su prerequisito declarado es 021, y
el de 021 es 020. 029 desbloquea menos y **es la única sin prerequisitos
pendientes**.
