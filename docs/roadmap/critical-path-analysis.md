# ANÁLISIS DE CAMINO CRÍTICO

## Camino A — abastecimiento e inventario físico

```
017 OC ✅parcial
 ├→ 018 Importaciones        ✗ 0 tablas        → habilita 026 landed cost
 └→ 019 Recepción ✅ COMPLETE 2026-09-03
     ├→ 020 Incidencias      ✅ COMPLETE 2026-09-03 (receipt_incidents, migración 0045)
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
     └→ 030 Crédito/reserva      ✅ COMPLETE 2026-09-02 (ORDER_CONFIRMATION, migración 0043)
          └→ 031 Cola/ruta         ⛔ existencia ubicada (022), no 030
               └→ 032 Picking      ⛔ 031 + 022

  Reauditado 2026-09-03: la ruta crítica del producto pasa por la cadena de ENTRADA.
  019 ✅ COMPLETE → 020 ✅ COMPLETE → **023 capacidad multiestado ▶ lista para retomar** → 021 ⛔ → 022 ⛔ → 031 → 032
  Las dos primeras cayeron el mismo día. El bloqueo de 021 cambió de naturaleza
  dos veces el 2026-09-03: el ciclo dirigido de 023 demostró que no era una
  carencia del motor sino dos decisiones de producto; el checkpoint D0-10 las
  cerró esa misma jornada. Lo que queda entre 020 y 021 ya no es una decisión:
  es un ciclo de implementación de 023, con la matriz de transiciones declarada
  y el delta estructural medido.
  Lo comercial está cerrado y espera a que el almacén sepa dónde está lo que vende.
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
             └→ 056 Validación fiscal y liberación ⛔ D0-07 (reglas)
```

Un solo bloqueo, externo a la ingeniería, gobierna seis Specs. Se puede
**construir** contra él; no se puede **liberar**.

> **2026-10-07.** El riesgo externo de la **homologación del software ante el SENIAT** bajo SNAT/2024/000121
> deja de formar parte de la ruta crítica: esa providencia fue derogada por SNAT/2026/00084 (G.O. N.º
> 43.435, 12-08-2026). Lo que sigue bloqueando es la validación profesional de las reglas (D0-07), y
> el trabajo técnico fiscal no cambia. Ruta fiscal ahora: implementación → validación contra la
> normativa vigente → QA/UAT → liberación.

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
| 018 Importaciones | 026 | 1 |
| 048 Integraciones | 013, 047 | 2 |
| 033 Confirmación | 034, 035 | 2 |

**Reauditado 2026-09-03.** 020 sale de esta tabla: está implementada. 022 sigue
siendo el nodo de mayor peso y sigue sin estar lista, pero su cadena se acortó de
tres eslabones a dos: `021 → 022`. Y el prerequisito de 021 ya no es una Spec
entera, es una capacidad concreta del motor de saldos de 023 —escribir estados de
mercancía distintos de `DISPONIBLE`—, que el `ADR-D0-010` declara y ningún código
ejerce.
