# PLAN — SPEC 008

## 1. Constitution Gate

| Principio | Cómo lo cumple 008 |
|---|---|
| **P5** Datos históricos protegidos | Sin borrado con historial; se retira el `cascade delete-orphan`; la reubicación con stock se rechaza |
| **P6** Seguridad en backend | Alcance, jerarquía y `allowed_actions` decididos en servidor |
| **P8** No hardcodear reglas | Zonas, tipos, estructura y política de código son **datos** |
| **P10** Calidad demostrable | Evidencia sobre PostgreSQL, E2E y tres navegadores |
| **P11** Accesibilidad y responsive | WCAG 2.2 AA y 320–1920 px sin scroll horizontal |
| **P13** Integridad transaccional | FK reales, restricciones de coherencia, `If-Match` |
| **P17/P22** Autoridad única | Auditoría, permisos y aprobaciones consumen las capacidades existentes |
| **P18** Política de modales | Configuración en pantalla completa |
| **P21** Paridad de motor | Toda la evidencia sobre PostgreSQL |
| **P23** Captura anticipada | La FK de ubicación se impone **antes** de que 019/022 generen historial |

**Sin contradicción con los 29 ADR vigentes.** `ADR-D0-004` se implementa; `ADR-011`
ya incorpora `Zone` en la cadena tras su actualización en el Gate G0.

## 2. Qué se implementa y qué no

| Se implementa | NO se implementa |
|---|---|
| 6 entidades de la jerarquía + 2 catálogos | StockLedger y saldos por ubicación (023) |
| Conversión de 2 referencias a FK real | Put-away (022) |
| Secuencia física y consulta ordenada | Recepción física (019) |
| Código y etiqueta derivada | Ruta y algoritmo de picking (031/032) |
| Estados y reglas de desactivación | Transferencias, conteos, devoluciones (025/036) |
| API de estructura y búsqueda | Impresión de etiquetas |
| 5 pantallas + sustitución de 2 existentes | Planos y adjuntos (046) |
| Migración de datos con `legacy_path` | Conversión automática de texto a jerarquía |

## 3. Arquitectura

```
organization/                       ← módulo existente, se extiende
  models.py    Warehouse (extendido)
               WarehouseZone · WarehouseAisle · WarehouseRack · WarehouseLevel
               WarehouseLocation (sustituye a Location)
               ZoneType · LocationType   ← catálogos por empresa
  service.py   StructureService  · jerarquía y coherencia
               LocationService   · código, etiqueta, secuencia, búsqueda
               DeactivationRules · qué se puede desactivar o borrar
  api.py       endpoints de los 6 nodos + estructura + búsqueda
```

> **Regla de acoplamiento.** `organization` **no importa** `inventory`. La
> comprobación de «tiene movimientos» se resuelve con una consulta por
> identificador, no importando el modelo del otro módulo, para no invertir la
> dependencia entre un maestro y su consumidor.

## 4. Decisiones técnicas

| Tema | Decisión | Fundamento |
|---|---|---|
| Jerarquía | Entidades separadas; hoja con la cadena completa | CL-008-01, CL-008-02 |
| Coherencia de cadena | `CHECK` + FK compuestas donde el dialecto lo permita; validación en servicio como refuerzo | FR-008-051 |
| Orden físico | `ORDER BY` plano con `NULLS FIRST` y desempate por código | research §3 |
| Código | Política por almacén; generado por defecto | CL-008-06 |
| Etiqueta | **Derivada**, nunca persistida | CL-008-07 |
| `FULL` | Derivado, no persistido | CL-008-05 |
| Estructura | `depth` + paginación; ubicaciones solo bajo petición | CL-008-08 |
| Reubicación con stock | Rechazada | CL-008-09 |
| Concurrencia | `If-Match` sobre nodos editables; único por código en base de datos | ADR-013 |
| Migración de texto | `legacy_path`, sin conversión automática | CL-008-15 |

## 5. Fases

Ordenadas por dependencia real, **no** por «DB → API → UI».

| Fase | Contenido | Depende de | Por qué aquí |
|---|---|---|---|
| **F1 · Modelo e integridad** | 6 entidades + 2 catálogos, restricciones de coherencia, retirada del cascade, migración `0017` | PostgreSQL | Nada puede validarse sin el esquema |
| **F2 · Conversión de referencias** | Las 2 `String(36)` pasan a FK; migración `0018` con `legacy_path` | F1 | **Antes que la API**: si se pospone, cada movimiento nuevo amplía la deuda (P23) |
| **F3 · Reglas de dominio** | Código y etiqueta, secuencia, desactivación, reubicación, `allowed_actions`, **régimen de mutabilidad estructural** | F1 | Es donde vive el valor; se prueba sin API |
| **F4 · API** | 6 nodos, estructura, búsqueda ordenada, permisos, auditoría | F3 | — |
| **F5 · Pruebas de backend** | Unidad, integración y concurrencia **sobre PostgreSQL** | F4 | Antes del frontend: valida el contrato que la UI consumirá |
| **F6 · Frontend** | 5 pantallas, sustitución de las 2 existentes | F4, F5 | — |
| **F7 · E2E y cierre** | E2E, cross-browser, axe, responsive, convergencia | F6 | — |

> F2 va deliberadamente **antes** de la API. Es la aplicación del Principio 23: el
> dato que no se captura no se recupera, y cada día sin la FK amplía el conjunto
> de saldos y conteos que apuntan a ninguna parte.

## 6. Migraciones previstas

| Migración | Tipo | Contenido | Clasificación |
|---|---|---|---|
| `0017_warehouse_structure` | Esquema | 6 tablas nuevas, extensión de `warehouses`, `locations` → `warehouse_locations` con columnas nuevas, retirada del cascade, índices y restricciones | `SAFE_MIGRATION` |
| `0018_location_fk_and_legacy` | Datos + esquema | Clasificación de huérfanas, reparación y anulación justificada, `legacy_path` y `legacy_location_id`, las 2 referencias a FK real, reporte de migración | `BACKFILL_REQUIRED` + `MANUAL_REVIEW_REQUIRED` + `BLOCKING_ON_CRITICAL` |

Ambas se validan sobre PostgreSQL con base limpia y con base pre-008 con datos,
usando `qa/pg-migration-validation.sh` como patrón.

**Riesgo declarado de `0018`:** si existen saldos o conteos apuntando a
ubicaciones inexistentes, la FK fallará. La política que gobierna ese caso está
en **`migration-0018-policy.md`** y es normativa. En resumen:

1. `0018` **clasifica** cada referencia antes de escribir nada:
   `VALID_REFERENCE`, `RECONSTRUCTIBLE_ORPHAN`,
   `NON_RECONSTRUCTIBLE_BUT_NULL_ALLOWED` o `CRITICAL_NON_RECONSTRUCTIBLE`.
2. **Prohibido** anular una referencia solo para que la migración termine.
   Anular exige que la reconstrucción sea imposible **y** que el modelo histórico
   admita la ausencia; el valor original queda siempre en `legacy_location_id`.
3. Una sola referencia crítica **aborta la migración** de forma controlada, con
   el reporte completo emitido y sin ninguna escritura aplicada.
4. La migración produce un reporte auditable: recuentos por clase y detalle de
   cada referencia modificada o crítica.

Esto **endurece** —no contradice— la lección de `0016` en la Spec 045. Allí lo
correcto fue no abortar por filas irrelevantes; aquí lo correcto es abortar
cuando la pérdida sería irrecuperable. La regla común es la misma: **la
migración nunca destruye dato en silencio.**

`0018` no se evidencia nunca en modo `--sql`: el modo offline no lee datos y por
tanto no puede clasificar.

## 7. Impacto en módulos existentes

| Módulo | Cambio | Riesgo |
|---|---|---|
| `organization` | Extensión mayor: 6 entidades, servicios, 20+ endpoints | Medio |
| `inventory` | 2 referencias pasan a FK; sin cambio de comportamiento | **Alto**: es el módulo mejor probado; su regresión es criterio de salida |
| `frontend/organizacion` | 2 páginas sustituidas, 5 nuevas | Medio |
| `purchasing`, `sales` | Ninguno directo | Bajo — su regresión igualmente se ejecuta |

## 8. Estrategia de pruebas

Toda la evidencia sobre PostgreSQL (`qa/pg-provision.sh`).

- **Unidad**: coherencia de cadena, generación de código, etiqueta derivada, orden físico, reglas de desactivación.
- **Integración**: los 6 nodos por API, jerarquía inválida, duplicados, alcance, borrado protegido.
- **Concurrencia**: dos creaciones del mismo código; desactivación mientras otra operación usa la ubicación.
- **Regresión**: `inventory`, `purchasing`, `sales`, `regulatory` y flujos de proceso, sin cambio de expectativa.
- **E2E**: los 12 casos del §48 del encargo, adaptados a que los tramos son opcionales.
- **Cross-browser**: Chromium, Firefox, WebKit. WebKit **no** se llama Safari.
- **Accesibilidad y responsive**: solo sobre las pantallas que 008 crea o modifica
  (§43); las 22 violaciones preexistentes detectadas en el cierre de 045 **no** se
  corrigen aquí.

## 9. Restricciones de esta iniciativa

- Prohibido `/speckit.implement` sin autorización expresa que mencione `008` (P2).
- Prohibido hardcodear zonas, estructura o reglas de un cliente concreto.
- Prohibido implementar 019, 022, 023, 025, 031, 032, 036 o 046.
- Prohibido duplicar permisos, auditoría o aprobaciones.
- SQLite no es evidencia suficiente.

## 10. Políticas normativas anexas

Dos documentos de esta Spec son **normativos**, no explicativos, y gobiernan la
implementación con el mismo peso que `spec.md`:

| Documento | Gobierna | Control |
|---|---|---|
| `migration-0018-policy.md` | Clasificación de referencias huérfanas, regla de anulación, regla de bloqueo, reporte de migración | Control 1 |
| `structure-mutability-policy.md` | Regímenes `INITIAL`/`OPERATIONAL`, metadata frente a estructura, borrado y desactivación por nodo, límite de la reestructuración | Control 2 |

Ninguno amplía el alcance funcional de 008: ambos **restringen** lo que la
implementación puede hacer.
