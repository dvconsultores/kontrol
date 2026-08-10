# Spec 012 — Checklist de Auditoría Fiscal (T-16)

**Estado: guía lista para ejecutar** (requiere equipo fiscal + documentos
oficiales y datos reales). No se afirma resultado fiscal alguno.

## Alcance
Validar contra normativa y Providencias vigentes de Venezuela (SENIAT):
IVA, ISLR, IGTF, retenciones, numeración, números de control, notas, libros,
períodos/cierre e inmutabilidad de documentos emitidos.

## Checklist
### Impuestos y retenciones
- [ ] IVA: base, cuota, tasas históricas; snapshots por línea en facturas.
- [ ] Retenciones ISLR/IVA: reglas versionadas, período, tasas; retención sufrida (ventas) y practicada (compras).
- [ ] IGTF: tasas por moneda (VED/USD), base de cálculo.
- [ ] No redondear al operar: dinero en `Numeric(18,2)`, tasas en `Numeric(14,6)` (migración 0012).

### Documentos y numeración
- [ ] Correlativos de facturación y números de control asignados por el núcleo fiscal (007) sin huecos/solapes.
- [ ] Notas de crédito/débito referencian documento original y respetan límite al saldo ajustable.
- [ ] Libros (ventas/compras) y períodos/cierre: cálculos de totales correctos.

### Inmutabilidad
- [ ] Documentos emitidos (facturas) inmutables: corrección solo por nota/anulación; reversos vinculados.
- [ ] Snapshot por línea (producto, precio, impuesto, tasa) guardado en el documento.
- [ ] Verificar en PostgreSQL real (SQLite no replica constraints/triggers).

### Evidencia
- [ ] Contrastar totales de un período con declaraciones de referencia.
- [ ] Revisar el módulo de homologación/liberación (010/011) para versiones de reglas fiscales.

## Notas
- Este checklist NO sustituye la opinión de un contador público autorizado.
- Ejecutar contra un ambiente de pruebas con datos representativos antes de producción.
