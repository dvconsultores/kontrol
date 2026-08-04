# WIREFRAMES — 007-NUCLEO-FISCAL

| Campo | Valor |
|---|---|
| Iniciativa | 007-nucleo-fiscal |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Ruta | `specs/007-nucleo-fiscal/wireframes/README.md` |

> Aplicación de las guías DOC-08 (WF-02 maestro-detalle; WF-05 estados y transiciones). Todos los grids sin scroll horizontal (FR-007-101).

## 1. Configuración fiscal (WF-02)

- **Fuentes legales**: lista + detalle (autoridad, tipo, número, gaceta, publicación, vigencias, archivo).
- **Reglas**: pestaña por tipo (IVA / Retención IVA / ISLR / IGTF); campos base, tasa, mínimo, sustraendo; versión y vigencia; validación de solape.
- **Perfiles fiscales**: por empresa/tercero/rubro con clasificaciones.

## 2. Numeración y números de control (WF-05)

- **Series**: `establecimiento | tipo documento | prefijo | siguiente | estado`.
- **Lotes de control**: `imprenta | rango desde/hasta | recibido | estado | conteos`.
- **Controles**: `lote | valor | estado (AVAILABLE/RESERVED/USED/VOID/LOST/DAMAGED) | documento`.
- Acciones: crear serie, cargar lote, reservar.

## 3. Emisión e impresión (WF-05)

- **Documentos fiscales**: lista de `FiscalDocument` con serie, número, control, moneda fiscal, tasa, hash (corto), estado.
- **Detalle**: pestaña de datos fiscales + eventos de impresión (`PrintEvent`: copia, impresora, usuario, motivo, hora).
- Acciones: emitir (idempotente), imprimir, reimprimir (con motivo).

## 4. Notas fiscales

- Lista de notas con referencia obligatoria a la factura, causal y montos.
- Validación visual del saldo ajustable disponible (límites).

## 5. Retenciones (WF-05)

- **Lista**: `tipo | tercero | base | tasa | monto | período | estado`.
- **Detalle**: cálculo con snapshot + comprobante.
- Acciones por estado: aprobar, practicar, emitir comprobante, declarar, pagar, conciliar, revertir.

## 6. Períodos y libros

- **Períodos fiscales**: `tipo | inicio | fin | estado (OPEN/CLOSED/REOPENED) | aprobaciones`; acción de cierre/reapertura.
- **Libros**: vistas por período (ventas, compras, retenciones) reconstruibles con equivalentes en Bs; exportación posterior (009).

## 7. Navegación

- Sidebar (lucide-react): `Fiscal` → Configuración · Numeración y control · Emisión · Notas · Retenciones · Períodos y libros.
- Rutas: `/fiscal/configuracion`, `/fiscal/numeracion`, `/fiscal/emision`, `/fiscal/notas`, `/fiscal/retenciones`, `/fiscal/libros`.
