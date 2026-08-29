# REGISTRO DE RIESGOS — SPEC 008

| ID | Riesgo | Prob. | Impacto | Sev. | Mitigación |
|---|---|---|---|---|---|
| **RSK-008-01** | **La jerarquía resulta inusable**: siete niveles, formularios encadenados y un árbol que nadie mantiene | **Alta** | **Alto** | **ALTA** | La interfaz muestra **solo los tramos que el almacén declara** (FR-008-078). Un almacén simple ve una pantalla simple. Es la decisión de diseño central de la Spec |
| **RSK-008-02** | Convertir `zone`/`aisle`/`rack` de texto a entidades **inventa datos** | Media | **Alto** | **ALTA** | Sin conversión automática: el texto se conserva en `legacy_path` y la creación de la jerarquía es decisión del cliente (CL-008-15, AC-008-17) |
| **RSK-008-03** | La FK sobre saldos y conteos falla por referencias huérfanas | **Alta** | Alto | **ALTA** | `0018` **clasifica** antes de escribir: repara lo reconstruible, anula solo lo legítimo conservando `legacy_location_id`, y **bloquea** ante lo crítico (`migration-0018-policy.md`). Seis casos probados sobre PostgreSQL |
| **RSK-008-04** | Regresión en `inventory`, el módulo mejor probado | Media | **Alto** | **ALTA** | Su batería completa es criterio de salida; las dos conversiones no cambian comportamiento, solo integridad |
| **RSK-008-05** | El orden físico no es determinista con tramos nulos y la Spec 031 hereda un recorrido inestable | Media | Alto | ALTA | Orden total con `NULLS FIRST` y desempate por código; prueba de estabilidad entre llamadas (AC-008-08) |
| **RSK-008-06** | Cargar la estructura completa colapsa con decenas de miles de ubicaciones | Media | Medio | MEDIA | `depth` y paginación; las ubicaciones nunca vienen por defecto (AC-008-19) |
| **RSK-008-07** | Se persiste `FULL` u ocupación y queda desincronizado del saldo | Baja | Alto | MEDIA | Prohibido por FR-008-041; la ocupación se deriva en la Spec 023 |
| **RSK-008-08** | Alguien codifica las zonas del cliente como enum «porque es lo que pidió» | Media | **Alto** | **ALTA** | R-008-3 y AC-008-22: búsqueda de literales como criterio de salida |
| **RSK-008-09** | Permitir reubicar una ubicación con stock corrompe el Kardex histórico | Baja | **Crítico** | MEDIA | Rechazo explícito (FR-008-056); el traslado físico es un movimiento, no una edición |
| **RSK-008-10** | Retirar el `cascade delete-orphan` rompe algún flujo que dependía de él | Baja | Medio | BAJA | Ningún flujo borra almacenes hoy; la regresión lo verifica |
| **RSK-008-11** | 008 crece hacia un WMS: slotting, optimización de ruta, volumetría | Media | Medio | MEDIA | Fuera de alcance explícito; capacidad y restricciones acotadas al MVP (CL-008-12, CL-008-13) |
| **RSK-008-12** | La ubicación vuelve a ser un maestro que nadie escribe | Media | **Alto** | **ALTA** | Los contratos para 019, 022, 023, 025, 031, 032 se declaran y verifican en T-008-098; las FK se imponen **antes** que la API (fase F2, P23) |
| **RSK-008-13** | La creación masiva genera cientos de ubicaciones erróneas difíciles de deshacer | Media | Medio | MEDIA | Vista previa obligatoria antes de crear (AC-008-23) |

| **RSK-008-14** | **Pérdida silenciosa de dato histórico**: `0018` anula referencias para poder terminar y nadie se entera hasta que se consulta el Kardex | Media | **Crítico** | **ALTA** | Prohibido por R-008-4. Anular exige clase C justificada; `legacy_location_id` conserva siempre el original; el reporte deja rastro por fila. Lo crítico **bloquea** en vez de perderse (R-008-5) |
| **RSK-008-15** | **Destrucción estructural por edición simple**: alguien retira un tramo de un almacén en operación y reinterpreta retroactivamente su histórico | Media | **Crítico** | **ALTA** | Régimen `OPERATIONAL` (R-008-6): los tramos utilizados no se eliminan, reordenan ni colapsan. Bloqueo en backend, no en la UI (AC-008-39) |
| **RSK-008-16** | La reconstrucción de clase B **adivina**: elige «la más probable» entre varias candidatas y corrompe el dato con apariencia de rigor | Media | Alto | **ALTA** | Solo se repara con candidata **unívoca**; dos candidatas degradan la fila a clase C o D. `legacy_path` queda excluido como fuente |
| **RSK-008-17** | El bloqueo estructural se implementa deshabilitando botones y la API queda abierta | Media | Alto | MEDIA | P6 y FR-008-093; T-008-068e invoca cada bloqueo saltándose el frontend |
| **RSK-008-18** | La regla de bloqueo paraliza despliegues legítimos: una base sucia impide actualizar indefinidamente | Media | Medio | MEDIA | Solo la clase **D** bloquea, y exige saldo vivo o referencia crítica. El ruido —saldo cero, almacén sin ubicaciones— es clase C y no detiene nada. El reporte dice exactamente qué filas resolver |

## Riesgo dominante

**RSK-008-01.** El fracaso probable de esta Spec no es técnico: es que nadie
mantenga la estructura porque la interfaz es insoportable. La mitigación no es
cosmética —adaptar la interfaz a `structure_levels`— y condiciona el diseño de
cuatro de las siete pantallas.

## El riesgo que los dos controles del Gate cierran

Antes del Gate, `0018` tenía permiso para anular referencias «sin abortar» y
`structure_levels` era un campo editable. Ambas cosas eran **pérdida de dato
histórico autorizada por omisión**: nada en la documentación las impedía, y ambas
habrían pasado la revisión porque la migración termina y el `UPDATE` funciona.

RSK-008-14 y RSK-008-15 son esos dos agujeros, ahora explícitos, con regla que los
prohíbe y prueba que lo verifica.

## Riesgo que esta Spec cierra

El GAP Analysis documentó que `locations` era un maestro que ninguna transacción
escribía. **RSK-008-12** es ese riesgo, ahora explícito y con mitigación
verificable: FK reales antes que la API, y contratos declarados para las seis
Specs consumidoras.
