# N4 — INFORME CRÍTICO DE ALCANCE

Las filas que **no** se pueden rellenar sin inventar la empresa. Son el objeto
de este preflight: medirlas antes de escribir, no descubrirlas después.

## 1. Resumen por criticidad

| Criticidad | MC-C | MC-D | MC-E |
|---|---:|---:|---:|
| financiero | 0 | 0 | 0 |
| fiscal | 0 | 0 | 1 |
| inventario | 0 | 0 | 0 |
| no crítico | 2 | 0 | 0 |

## 2. Detalle fila a fila

| Tabla | Id | Valor actual | Fecha | Clase | Criticidad | Rutas disponibles |
|---|---|---|---|---|---|---|
| `catalog_items` | `it-1` | `ten-2` | 2026-06-01 | **MC-C** | — | (ninguna) |
| `fiscal_number_series` | `fs-1` | `ten-2` | 2026-06-01 | **MC-E** | fiscal | (ninguna) |
| `parties` | `pa-3` | `ten-2` | 2026-06-01 | **MC-C** | — | (ninguna) |

> Identificadores técnicos del fixture. No hay datos personales ni secretos.

## 3. Política de aborto

| Condición | Efecto |
|---|---|
| `MC-E` fiscal > 0 | **La ola fiscal no se ejecuta** |
| `MC-E` financiera > 0 | La ola financiera correspondiente no se ejecuta |
| `MC-E` inventario > 0 | La ola de inventario correspondiente no se ejecuta |
| Cualquier `MC-E` sin resolver | **ARCH-MC-001 no puede declararse cerrada** |

Un `MC-E` de un dominio no detiene las olas de otro: aislar el bloqueo
es lo que permite avanzar sin inventar nada. Pero ninguno se rebaja de clase
por resultar incómodo.

## 4. Qué falta para resolver cada clase

| Clase | Qué falta | ¿Puede resolverse técnicamente? |
|---|---|---|
| `MC-C` | Una autoridad de dominio que desempate, o una decisión humana | Solo con revisión manual auditada |
| `MC-D` | Cualquier evidencia | No; requiere decisión |
| `MC-E` | Ídem, y además bloquea por ser crítica | No; requiere decisión, y detiene su ola |
