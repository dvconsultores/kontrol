# PLAN DE PRUEBAS — ARCH-MC-001

## 1. Qué hay que demostrar

Tres cosas. Si las tres se cumplen, la remediación sirvió.

1. Que **dos empresas del mismo tenant no se ven**.
2. Que el histórico **no se inventó**.
3. Que **nada de lo que ya funcionaba dejó de funcionar**.

## 2. Fixture obligatorio

```
T1 ─ Company A   ─ almacén, banco, serie fiscal propios
   └ Company B   ─ almacén, banco, serie fiscal propios
T2 ─ Company C

UA (solo A) · UB (solo B) · UAB (A+B) · UC (T2)
```

**Ninguna prueba de dominio se acepta con una sola empresa** (`FR-MC-081`).

## 3. Arquitectura — fallan en construcción

| Prueba | Qué impide |
|---|---|
| `test_all_persistent_models_have_declared_scope` | Una entidad sin alcance |
| `test_company_id_always_references_company` | Que la columna vuelva a mentir |
| `test_tenant_id_always_references_tenant` | Lo mismo, al revés |
| `test_no_writer_assigns_tenant_to_company` | La reaparición del defecto |
| `test_derived_scope_has_mandatory_path` | Una ruta que puede ser nula |
| `test_every_route_declares_scope` | Un endpoint sin clasificar |

## 4. Unidad e integración — PostgreSQL 18.x

Por dominio: separación A/B en listar, leer, modificar y borrar; escritura que
ignora la empresa del cliente; derivación correcta; conflicto entre rutas.

## 5. Seguridad — `AMC-01`..`AMC-17`

Una prueba por amenaza, ninguna excluida: IDOR, cabecera falsificada,
almacenamiento manipulado, contexto obsoleto, escalada, fuga por caché, consulta
sin acotar, asignación masiva, trabajo de fondo, vínculo entre empresas,
aplicación de pago cruzada, existencias, factura, número fiscal, informe,
auditoría, pestañas.

## 6. Fiscal — prioridad máxima

| Prueba | Exigencia |
|---|---|
| Series independientes | A y B numeran sin colisión |
| Rango de control | El de A no se consume desde B |
| Libro de ventas | El de A no contiene documentos de B |
| Libro de compras | Ídem |
| Retención | Conserva su empresa agente |
| Reimpresión | Muestra la empresa emisora, no la activa |

## 7. Migración

Seis bases: limpia · anterior a la normalización · monoempresa histórica ·
multiempresa determinista · ambigua · con crítico fiscal.

Se exige: informe previo sin escribir · clasificación correcta · **aborto** ante
crítico sin resolver, sin escrituras destructivas parciales · paridad de
importes, cantidades, bases y números.

## 8. E2E multiempresa — 20 pasos

Con A activa: tercero, compra, stock, venta, operación financiera. Cambiar a B:
los equivalentes. Comprobar que A no muestra B ni B muestra A, que la base
conserva la propiedad, que los documentos de 046 se vinculan a la empresa
correcta y que el histórico no cambia al cambiar de contexto.

Más: E2E fiscal A/B, E2E de empresa falsificada, y pestañas simultáneas.

## 9. Regresión de lo cerrado

008 completa · 011 conversión y congelado · 045 motor e integración con 046 ·
046 con **ClamAV real** incluyendo EICAR y falso seguro.

## 10. Global

Backend · `tsc` · `eslint` · Vitest · `vite build` · OpenAPI · Playwright en tres
navegadores · recorrido de rutas. **0 fallos.** Todo `skip` justificado; ningún
escenario multiempresa omitido como `skip`.

## 11. Rendimiento

`EXPLAIN` sobre las tablas con volumen antes y después. Acotar por empresa no
puede degradar el plan.
