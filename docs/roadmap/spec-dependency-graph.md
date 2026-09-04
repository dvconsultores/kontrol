# GRAFO DE DEPENDENCIAS — 56 SPECS

Notación: `A → B` significa «A debe existir antes que B».
`⛔` marca la dependencia que hoy está incumplida (se construyó B sin A).

## Capa 0 — Plataforma (sin dependencias)

```
001 Fundación
 ├→ 002 Seguridad ──→ 003 Usuarios/roles/alcance
 ├→ 005 Design System
 ├→ 006 Auditoría/observabilidad
 ├→ 052 Instalador ──→ 053 Backup/continuidad
 └→ 055 Seguridad y hardening
004 Licenciamiento  ← 001, 002
```

## Capa 1 — Maestros

```
007 Organización        ← 001, 003
 └→ 008 Almacenes físicos          (zona/pasillo/rack/nivel/posición)
009 Terceros            ← 007
010 Productos/servicios ← 007
 └→ 011 Unidades/presentaciones/conversiones
012 Maestros comerciales ← 009, 010, 011
013 Maestros financieros ← 007
014 Maestros fiscales/regulatorios ← 007, 009, 010
046 Gestión documental  ← 001
```

## Capa 2 — Inventario (núcleo)

```
023 Núcleo inventario/Kardex ← 008, 010, 011
 ├→ 024 Lotes/seriales
 ├→ 025 Transferencias/conteos/ajustes
 └→ 026 Costos y valoración ← 018 (para landed cost)
```

## Capa 3 — Abastecimiento

```
015 Requisiciones      ← 009, 010, 023, 045
 └→ 016 Cotización proveedores
     └→ 017 Orden de compra
         ├→ 018 Importaciones          ← 046 (expediente documental)
         └→ 019 Recepción física       ← 008, 023
             ├→ 020 Incidencias de recepción ← 046 ✅ (2026-09-03)
             └→ 021 Confirmación de inventario recibido ← 011 ✅, 020 ✅
                 └→ 022 Put-away        ← 008 ✅ (008 cerrada; 023 aún sin dimensión de ubicación)
027 Factura proveedor/match ← 017, 019
 └→ 028 CxP y pagos ← 040 (retenciones)
```

## Capa 4 — Comercial y preparación

```
029 Cotización y pedido comercial ← 009, 010, 011, 012  ⛔ (se construyó sin 012)
 └→ 030 Crédito/aprobación/reserva ✅ COMPLETE (2026-09-02) ← 012 ✅, 023 ✅(motor), 045 ✅ · D0-03 ✅

Cadena operativa reauditada el 2026-09-03 (`operational-chain-capability-matrix.md`). Las aristas
dejan de nombrar Specs y nombran capacidades:

```
019 Recepción física ✅ COMPLETE / CONVERGED (2026-09-03)
 ├→ 021 (camino feliz: sin incidencia)
 └→ 020 Incidencias ✅ COMPLETE / CONVERGED (2026-09-03)
      └→ 021 Confirmación ✅ COMPLETE / CONVERGED (2026-09-04)
           └→ 022 Put-away ⛔ estado de origen (021)   [008 ya entrega las ubicaciones]
                └→ 031 Cola y ruta ⛔ existencia ubicada (022)   [030 ya satisfecho]
                     └→ 032 Picking ⛔ 031 + 022   [024 y 030 satisfechos]
```
     └→ 031 Cola y ruta de picking ← 008 ✅, 022, 032  (008 entrega `/locations/ordered`)
         └→ 032 Picking y consolidación ← 008, 011, 023
             └→ 033 Confirmación independiente de pedido ← 032, 045
                 └→ 034 Liberación y facturación ← 033, 039, 042  ⛔ (034 existe sin 033)
                     └→ 035 Despacho ← 034, 044, 046
                         └→ 036 Devoluciones/NC/ND ← 034, 023
037 CxC ← 034
```

## Capa 5 — Finanzas y fiscal

```
039 Motor fiscal ← 014
 ├→ 040 Retenciones IVA/ISLR ← 014, 039
 ├→ 041 IGTF ← 038, 039
 └→ 042 Documentos fiscales y contingencia ← 014, 039
     └→ 043 Libros y cierres ← 040, 041, 042
038 Tesorería ← 013, 028, 037
044 SICA/SIGESAI/SACS ← 014, 035
```

## Capa 6 — Transversales

```
045 Motor de aprobaciones ← 003     (bloquea 015, 017, 025, 030, 033)
047 Notificaciones y tareas ← 045, 048
048 Integraciones ← 001            (habilita 013 tasas BCV, 047 correo, 046 storage)
```

## Capa 7 — Información y liberación

```
049 Dashboard ← 023, 028, 034, 037, 038
050 Reportes ← 049, 046
051 Auditoría avanzada ← 006
054 QA integral ← todas
056 Homologación y release ← 039..043, 054, 055
```

## Dependencias incumplidas (deuda estructural ya contraída)

| # | Se construyó | Sin su prerequisito | Consecuencia observable |
|---|---|---|---|
| D-01 | 023 Inventario | ~~008 Almacenes físicos completos~~ **RESUELTA 2026-08-30** | `location_id` es FK real en movimiento, saldo y línea de conteo |
| D-02 | 029/030 Ventas | 012 Maestros comerciales | Precio tecleado por línea, lista de precios como texto libre |
| D-03 | 034 Facturación | 033 Confirmación de pedido | Se factura sin compuerta y sin vínculo al pedido |
| D-04 | 031/032 Picking | ~~008~~ **desbloqueada** + 022 Put-away | 008 entrega orden físico determinista; falta 022 |
| D-05 | 015/017/025/030 | 045 Motor de aprobaciones | **RESUELTA 2026-08-29**: las cuatro implementaciones ad-hoc migradas al motor único (Spec 045 COMPLETE_100) |
| D-06 | 019 Recepción | ~~020~~ **cerrada** + 021 | Recepción contable que salta la liberación; la cuarentena ya tiene dónde declararse |
| D-07 | 026 Costos | 018 Importaciones | Sin landed cost: el costo de importación no se distribuye |
| D-08 | Todas las líneas | 011 en transacción | Sin UoM ni presentación por línea |

## Nodos de mayor grado de salida (desbloquean más trabajo)

| Spec | Bloquea directamente | Peso |
|---|---|---:|
| **008 Almacenes físicos** | 022, 031, 032, 023(calidad), 019 | 5 |
| ~~045 Motor de aprobaciones~~ **(cerrada)** | 015, 017, 025, 030, 033, 047 — **desbloqueadas** | 6 |
| **012 Maestros comerciales** | 029, 030, 034 | 3 |
| **ARCH-MC-001 (remediación)** — N0/N1/N2/N3 COMPLETE · N4 preflight COMPLETE · backfill NOT_STARTED | **bloquea 012, REM-046-001 y la convergencia de 046**; toda Spec futura con datos de empresa | — |
| ~~046 Gestión documental~~ **(cerrada 2026-08-30)** | 019, 027, 035, 044, 056 — **desbloqueadas**; 018 y 040 quedan por causas no documentales (020 cerró el 2026-09-03 usando el enlace documental); **028 y 038 siguen bloqueadas** (`REM-046-001`) | 4 |
| **033 Confirmación de pedido** | 034, 035 | 2 |
| **048 Integraciones** | 013(BCV), 046(storage), 047(correo) | 3 |

---

# ACTUALIZACIÓN — 2026-09-02

Posterior a `ARCH-MC-001 — COMPLETE / GLOBALLY CONVERGED` y a
`SPEC 012 — COMPLETE / CONVERGED`. Medido contra el repositorio en `3027da6`.

## Dependencias incumplidas — estado actual

| # | Estado | Comprobación |
|---|---|---|
| D-01 | **RESUELTA** | `location_id` es FK real en movimiento y saldo |
| D-02 | **RESUELTA** | Spec 012 cerrada: `resolve_price` devuelve precio y versión |
| D-03 | Vigente | 034 sigue facturando sin la compuerta de 033 |
| D-04 | Parcial | 008 entrega el orden físico; **falta 022** |
| D-05 | **RESUELTA** | Motor único de aprobaciones |
| D-06 | **Parcial** | 020 cierra la mitad: la excepción se registra, se escala y se resuelve. Sigue vigente por 021: nadie confirma antes de que el asiento exista |
| D-07 | Vigente | Sin 018 no hay *landed cost* |
| D-08 | **RESUELTA** | Unidad y presentación congeladas en línea |

## Nodos de mayor grado de salida, hoy

| Spec | Bloquea directamente | Peso | ¿Lista? |
|---|---|---:|---|

| **029 Cotización/pedido** | 030; da consumidor a 012 | 2 | **Sí** |
| **031 Cola y ruta de picking** | 032, 033 | 2 en cadena | **Sí** — la 022 entrega existencia ubicada |
| 048 Integraciones | 013 (BCV), 047 | 2 | Sí |
| 033 Confirmación | 034, 035 | 2 | No — espera 032 |
| ~~008~~, ~~045~~, ~~046~~, ~~012~~, ~~ARCH-MC-001~~ | cerradas | — | — |

## La deuda que 012 dejó abierta a propósito

`resolve_price` existe y **ninguna línea de venta la llama**:
`sales_quote_lines`, `sales_order_lines` y `sales_invoice_lines` siguen con
`unit_price` tecleado y **cero** columnas de origen.

No es un defecto de 012 —`FR-012-070` dice que prepara el contrato y no
implementa el proceso de sus consumidoras— sino la razón por la que 029 es la
siguiente.
