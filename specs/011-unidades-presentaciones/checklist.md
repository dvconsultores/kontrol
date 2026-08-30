# CHECKLIST — SPEC 011

## Modelo

- [ ] `UnitOfMeasure` con dimensión validada, `decimals` y `rounding_mode`
- [ ] Catálogo global **vacío**; sin unidades entregadas por KONTROL
- [ ] Unidad global de solo lectura para la empresa
- [ ] `UnitConversion` en `NUMERIC`, con `factor > 0` y misma dimensión
- [ ] `Presentation` con `code`, `status`, `company_id`, `dispatchable`
- [ ] `content` legado **conservado**, no usado para calcular
- [ ] `ProductPresentationVersion` con factor, vigencia y `exact_in_base`
- [ ] Índice único parcial: una sola versión abierta por presentación
- [ ] `base_unit_id` obligatoria en productos, opcional en servicios
- [ ] `base_unit_locked` irreversible con el primer movimiento

## Conversión

- [ ] Un **solo** lugar en el código donde se convierte
- [ ] `resolve_conversion`, `to_base`, `to_base_bulk`, `freeze`
- [ ] Conversión física y comercial separadas
- [ ] Cadena presentación → unidad → base resuelta
- [ ] Redondeo en un solo lugar, según la unidad base
- [ ] Fracción no declarada rechazada con `CONVERSION_NOT_EXACT`
- [ ] Fecha efectiva = fecha del documento
- [ ] Sin versión aplicable → error, nunca factor inventado

## Snapshot

- [ ] 4 columnas + `uom_source` en las 17 tablas `MUST_HAVE_NOW`
- [ ] `inventory_balances`, `cost_layers` y `triple_matches` **sin** esas columnas
- [ ] Una unidad y una presentación **por línea**, no por cantidad
- [ ] Símbolo y etiqueta congelados solo en documentos emitidos
- [ ] `base_quantity` calculada en backend, nunca aceptada del cliente
- [ ] Snapshot fijado al emitir; recálculo mientras es borrador
- [ ] Línea emitida inmutable

## Tipos

- [ ] 0 columnas de cantidad o factor en `Float`
- [ ] `NUMERIC(18,6)` en cantidad, factor y cantidad base
- [ ] Cambios de valor por conversión de tipo **reportados**

## Migración

- [ ] Cuatro clases implementadas y excluyentes
- [ ] `factor = 1` solo demostrado, nunca por defecto
- [ ] Clase C con `uom_id` nulo y marcada, sin adivinar
- [ ] Clase D: cero escrituras sobre líneas fiscales
- [ ] Bloqueo por umbral configurable
- [ ] `quantity` original intacta en todos los casos
- [ ] Reporte con los once recuentos y su invariante
- [ ] `assigned_presentation = 0`
- [ ] Idempotente
- [ ] Nunca evidenciada en modo `--sql`
- [ ] `NOT NULL` solo tras reporte limpio

## API y seguridad

- [ ] Rutas bajo la convención vigente de `maestros`
- [ ] 15 códigos de error estables con `reason` y `allowed_actions`
- [ ] Sin endpoint que edite una versión de factor
- [ ] `If-Match` con el mecanismo existente
- [ ] Permisos con la convención del proyecto, sin sistema paralelo
- [ ] Auditoría transversal, sin tabla local
- [ ] Aislamiento multiempresa verificado invocando la API directamente

## Frontend

- [ ] 2 pantallas con URL propia
- [ ] Presentaciones en página completa, no modal
- [ ] «Una CAJA equivale a 100 UND», no «Factor = 100»
- [ ] Vista previa informativa
- [ ] Historial de versiones sin edición
- [ ] Numéricos vacíos al inicio
- [ ] Producto sin presentaciones: pantalla limpia
- [ ] Selectores con búsqueda asíncrona

## Verificación final

- [ ] Suite completa sobre PostgreSQL 18.x
- [ ] 6 casos de migración y 4 de conversión de tipo
- [ ] Regresión de `inventory`, `purchasing` y `sales`
- [ ] axe WCAG 2.2 AA y responsive en las pantallas de 011
- [ ] Cross-browser en tres navegadores
- [ ] 0 literales de unidad o presentación en el código
- [ ] Contratos declarados para las 14 Specs consumidoras
