# SPEC 001 · DELTA DIRIGIDO POLICY-CLOCK-LOCAL — LA FECHA DE NEGOCIO ES DE CARACAS

> Delta transversal dentro de la Spec 001 (Fundación), con la Spec 052 como apoyo de
> despliegue. Corrige la deuda que la auditoría de solo lectura demostró: KONTROL no
> garantizaba en ninguna capa que su **día civil de negocio** fuera el de
> `America/Caracas`. No reabre CLOCK-013 ni los deltas FLOAT-038.

## 0. Checkpoint

| Comprobación | Valor |
|---|---|
| `EXPECTED_HEAD` / `ACTUAL_HEAD` | `eb2558b` / `eb2558b` — coinciden |
| `COMMITS_AFTER_EB2558B` | **0** |
| `ACTUAL_BRANCH` | `develop` |
| `WORKTREE_STATE` | dos informes de auditoría sin confirmar (ver abajo) |

### Ficheros sin confirmar, clasificados

| Fichero | Origen | Relación con este delta | Decisión |
|---|---|---|---|
| `KONTROL_MASTER_COMPLETENESS_AUDIT.md` | Auditoría maestra de completitud | Ninguna | Se preserva; no se mueve ni se confirma |
| `qa/audits/KONTROL-AUDIT-POLICY-CLOCK-LOCAL-20260917/` | La auditoría que **origina** este delta | Directa: es su evidencia previa | Se preserva tal cual; su incorporación al repositorio es decisión documental de la dueña, no de este delta |

## 1. Decisión de la dueña

| | |
|---|---|
| `BUSINESS_TIMEZONE` | **`America/Caracas`** |
| Estado | `OWNER_DECISION_RATIFIED` |
| Alcance | **día civil de negocio** |
| Instantes técnicos | siguen en **UTC**, conforme a `ADR-D0-001` |

No se pregunta de nuevo qué zona usar. Este delta no decide: implementa.

## 2. Dueña canónica

| Papel | Spec | Motivo |
|---|---|---|
| **Principal** | **SPEC 001 — Fundación** | La autoridad temporal de negocio es arquitectura compartida: define de dónde sale «hoy» para todo el producto |
| Apoyo | **SPEC 052 — Instalador y despliegue** | El cinturón de seguridad del runtime: contenedor, plantillas y unidad del planificador |
| Dominios impactados | 012, 013, 015-017, 027-028, 029-038, 039-043, 044, 049 | Consumen la fecha de negocio; no la gobiernan |

`OWNER_IDENTITY_CONFLICT = 0`.

## 3. Semántica canónica

| Concepto | Definición |
|---|---|
| `INSTANTE_TÉCNICO` | `datetime.now(UTC)`, con zona. Sellos de auditoría, `created_at`, tokens, planificador. **No se toca** |
| `AHORA_DE_NEGOCIO` | El mismo instante, convertido a `America/Caracas` |
| `HOY_DE_NEGOCIO` | `AHORA_DE_NEGOCIO.date()` |

`HOY_DE_NEGOCIO` **nunca** se deriva de `date.today()`, que es el día civil del proceso.

## 4. Inventario físico, recontado

No se dan por buenas las cifras de la auditoría. Medido sobre `eb2558b`:

| Fuente | Backend | Comentario |
|---|---:|---|
| `date.today()` | **26** | Coincide con la auditoría |
| `datetime.now(UTC)` | **152** | Instantes técnicos, correctos, intocables |
| `datetime.now()` sin zona | **0** | — |
| `utcnow()` | **1** | `app/shared/mixins.py:13`, que devuelve `datetime.now(UTC)`: técnico |
| `ZoneInfo`, `astimezone`, `pytz` | **0** | No hay una sola conversión en el producto |
| `CURRENT_DATE` / `CURRENT_TIMESTAMP` | **0** | Ninguna regla de negocio pregunta la fecha a PostgreSQL |

### Frontend — la auditoría dijo 9; son menos

El recuento de la auditoría incluía formateos de presentación. Medido con el patrón
completo (`new Date()`, `Date.now()`, `toISOString`, `getFullYear/Month/Date`,
`Intl.DateTimeFormat`, `toLocaleDateString`): **15 apariciones**, de las cuales

| Clase | Nº | Cuáles |
|---|---:|---|
| `PRESENTATION_ONLY` | 9 | `MiLicenciaPage` (3), `PoliticasPage` (2), `DelegacionesPage` (1), `NotificationContext` (identificador, ni siquiera es fecha), `RecepcionesPage`, `DelegacionesPage:61` (convierten lo que teclea la persona a instante) |
| **`REQUEST_PAYLOAD`** | **2** | `ListasPrecioPage.tsx:93` (`valid_from`) y `MaestrosPage.tsx:119` (`rate_date`): **envían una fecha civil derivada del navegador** |
| `DEFAULT_UI_DATE` | 1 | `TasasPage.tsx:60` `ahoraLocal()`: prefija el control con la hora local de quien registra |
| Instante | 3 | `TasasPage:149` y los dos de conversión a `toISOString()` |

Solo los **2** de `REQUEST_PAYLOAD` son autoridad de fecha de negocio.

## 5. Clasificación de los 26 usos de backend

| Clase | Nº | Usos |
|---|---:|---|
| **C · `EXPLICIT_OPERATION_DATE_FALLBACK`** | **14** | `commercial:395`, `fiscal:133`, `fiscal:164`, `sales:445`, `rates:342`, `treasury:145`, `191`, `534`, `535`, `657`, `875`, `889`, `902`, `955` |
| **A · `PURE_BUSINESS_TODAY`** | **12** | `purchasing:1352`, `1580`, `1643`, `regulatory:263`, `reporting:76`, `sales:2575`, `2703`, `2934`, `3964`, `treasury:398`, `485`, `828` |
| E · `TECHNICAL_TIMESTAMP` | 152 | Los `datetime.now(UTC)`: fuera de alcance por definición |
| F · `HISTORICAL_SEMANTICS_RISK` | **0** | Ninguno reinterpreta datos ya escritos: los 26 deciden qué día es **hoy** para operaciones nuevas |
| G · `FISCAL_HISTORICAL_RISK` | **0** | `fiscal:133/164` seleccionan la regla vigente **para el cálculo en curso**; ningún documento emitido se recalcula |
| H · `UNKNOWN` | **0** | — |

**Impacto histórico: cero.** Este delta cambia de dónde sale «hoy», no lo que ya está
escrito. No hay migración de datos, ni recálculo, ni reapertura de cierres.

## 6. Licenciamiento — corrección de la auditoría previa

La auditoría afirmó que las fronteras del contrato de licencia se evaluaban en UTC y por
tanto cuatro horas antes de lo pactado. **Eso era incorrecto**, y esta comprobación lo
rectifica: el contrato emite los hitos **con el desfase de Caracas**
(`specs/001-fundacion/contracts/license-contract.md:18-21` → `"2026-04-01T00:00:00-04:00"`),
las licencias de prueba también, `_dt` conserva el desfase y `compute_mode` compara
instantes. Ejecutado contra el motor real:

```
read_only_start = 2027-05-01T00:00:00-04:00
30 abr 23:59 Caracas (1 may 03:59 UTC) -> CRITICAL_RENEWAL_NOTICE
 1 may 00:00 Caracas (1 may 04:00 UTC) -> READ_ONLY
 1 may 00:00 UTC (30 abr 20:00 Caracas) -> CRITICAL_RENEWAL_NOTICE
```

**Licenciamiento ya es correcto.** No se corrige nada; se añade una prueba que fije ese
comportamiento para que nadie lo rompa. `license_timezone`, la constante que nadie lee,
**no se toca**: retirarla es limpieza ajena, de la Spec 004.

## 7. `/speckit.specify`

| ID | Requisito | Prioridad |
|---|---|---|
| FR-001-102 | `America/Caracas` es la **única** zona para el día civil de negocio, declarada en un solo sitio del código | P0 |
| FR-001-103 | Los instantes técnicos conservan su semántica **UTC**: ni uno se convierte | P0 |
| FR-001-104 | El día de negocio **no depende** de la zona del proceso, el contenedor, el anfitrión, la integración continua ni el navegador | P0 |
| FR-001-105 | Existe un ayudante canónico para el día y el instante de negocio, y es determinista sobre un instante dado | P0 |
| FR-001-106 | Los 26 usos de `date.today()` del producto migran a ese ayudante conservando su semántica exacta | P0 |
| FR-001-107 | Una fecha explícita recibida **siempre** manda sobre el «hoy» de respaldo | P0 |
| FR-001-108 | El despliegue declara `America/Caracas` como **defensa adicional**, nunca como autoridad | P1 |
| FR-001-109 | PostgreSQL permanece en UTC mientras ninguna regla derive de él la fecha de negocio | P0 |
| FR-001-110 | El planificador conserva sus instantes UTC | P0 |
| FR-001-111 | El frontend no usa la zona del navegador como autoridad de una fecha de negocio que envía al servidor | P0 |
| FR-001-112 | Las fronteras de licencia se evalúan según el calendario de Caracas, y queda probado | P0 |
| FR-001-113 | Fiscal y regulatorio cambian **solo** su fuente de fecha: ninguna regla, ninguna tasa, ninguna homologación | P0 |
| FR-001-114 | **Cero** reinterpretación automática de datos históricos | P0 |
| FR-001-115 | Existe una guarda que impide reintroducir el reloj local en la lógica de negocio | P0 |
| FR-001-116 | El mismo instante absoluto produce la **misma** fecha de negocio bajo cualquier zona del proceso | P0 |
| FR-001-117 | Las regresiones vigentes siguen verdes, incluidas CLOCK-013 y FLOAT-038-A/B/C | P0 |

Criterios de aceptación, tras `AC-017`:

| ID | Criterio |
|---|---|
| AC-018 | **Dado** el instante `2026-09-17T02:36Z`, **entonces** el día de negocio es `2026-09-16` bajo UTC, Caracas, Ámsterdam y Kiritimati |
| AC-019 | **Dado** dos políticas vigentes desde el 16 y desde el 17, **cuando** se pregunta cuál rige en ese instante, **entonces** es la del 16 en las cuatro zonas |
| AC-020 | **Dado** una fecha explícita, **entonces** manda sobre el «hoy» de respaldo |
| AC-021 | **Dado** el proceso en Caracas, **entonces** los sellos técnicos siguen siendo UTC con zona |
| AC-022 | **Dado** la frontera de licencia del 1 de mayo, **entonces** cambia a las 00:00 de Caracas y no a las de UTC |

## 8. `/speckit.clarify`

| # | Pregunta | Resolución | Material |
|---|---|---|---|
| 1 | Recuento backend | **26**, recontado | No |
| 2 | Recuento frontend | 15 apariciones; **2** son autoridad de negocio | No |
| 3 | Ubicación del ayudante | `app/shared/`, junto a `money.py`, que es el precedente de política transversal | No |
| 4 | Fuente de configuración | `business_timezone` en `Settings`, valor `America/Caracas` | No |
| 5 | Papel de `license_timezone` | Constante muerta de la Spec 004. **No se toca**: retirarla es limpieza ajena | No |
| 6 | Dónde va el cinturón de despliegue | `compose.yaml`, `.env.example`, unidad del planificador | No |
| 7 | Implicaciones del planificador | Dispara por intervalo y compara instantes UTC: sin cambio de lógica | No |
| 8 | Clasificación de cada uso backend | §5, sin `UNKNOWN` | No |
| 9 | Clasificación de cada uso frontend | §4, sin `UNKNOWN` | No |
| 10 | Riesgo sobre datos persistidos | **Ninguno**: los 26 deciden el «hoy» de operaciones nuevas | No |
| 11 | Riesgo fiscal histórico | **Ninguno**: no se recalcula ningún documento emitido | No |
| 12 | ¿Alguna columna guarda «hoy»? | Sí (`opened_at`, `closed_at`, `approved_at`, `due_date`…), y se seguirán escribiendo con el día de negocio correcto **de ahora en adelante** | No |
| 13 | ¿Alguna fecha explícita debe quedar intacta? | Todas: la precedencia `explícita > hoy` se conserva literalmente | No |
| 14 | Semántica de las ventanas de licencia | Ya correcta, con desfase de Caracas en el contrato (§6) | No |
| 15 | Estrategia de pruebas | Unitarias del ayudante sobre instante fijo · matriz de cuatro zonas · políticas cruzadas · frontera de licencia · no regresión de instantes técnicos | No |
| 16 | Estrategia de la guarda | Análisis del árbol sintáctico sobre `app/modules` y `app/core`, con lista blanca explícita | No |
| 17 | Regresión de UTC técnico | Prueba dedicada con el proceso en Caracas | No |
| 18 | Navegador | Deja de ser autoridad en los 2 sitios que envían fecha | No |
| 19 | PostgreSQL | Sigue en UTC; no participa | No |
| 20 | ¿Migración o cambio de esquema? | **Ninguno** | No |

**MATERIAL OQ = 0 · UNKNOWN = 0.** No aparece necesidad de reinterpretar histórico, ni
de recalcular nada fiscal, ni de migrar fechas almacenadas.

## 9. `/speckit.plan`

`W01` checkpoint · `W02` dueña · `W03` decisión registrada · `W04` inventario backend ·
`W05` inventario frontend · `W06` riesgo histórico · `W07` diseño del ayudante ·
`W08` configuración · `W09` licenciamiento (probar, no corregir) · `W10`-`W16` remediación
por dominio · `W17` frontend · `W18` cinturón de despliegue · `W19` planificador ·
`W20` guarda estática · `W21` unitarias · `W22` matriz de zonas · `W23` fronteras de
licencia · `W24` no regresión fiscal · `W25` no regresión de UTC técnico ·
`W26` multiempresa · `W27` mutaciones · `W28` regresión completa · `W29` frontend ·
`W30` E2E pertinente · `W31` analyze final · `W32` trazabilidad · `W33` convergencia.

### Diseño elegido — C = A + B + guarda

**A · Ayudante canónico** (`app/shared/clock.py`), la autoridad:

```
ZONA_DE_NEGOCIO           → ZoneInfo(settings.business_timezone)
ahora_de_negocio(instante=None) → instante (o now(UTC)) convertido a esa zona
hoy_de_negocio(instante=None)   → su .date()
```

Determinista: sobre un instante dado devuelve siempre lo mismo, sin tocar el entorno.

**B · Cinturón de despliegue**: `TZ=America/Caracas` en `compose.yaml`, `.env.example` y
la unidad del planificador. **No es la autoridad**: el código debe ser correcto aunque el
anfitrión esté en otra zona, y las pruebas lo demostrarán ejecutándose en Ámsterdam.

**Guarda**: análisis sintáctico que prohíbe `date.today()` en `app/modules` y `app/core`,
con lista blanca vacía salvo justificación escrita.

## 10. CONSTITUTION GATE

| # | Puerta | Veredicto |
|---|---|---|
| G-CLOCK-01 | Dueña resuelta | **PASA** — 001, apoyo 052 |
| G-CLOCK-02 | `America/Caracas` ratificada | **PASA** |
| G-CLOCK-03 | Semántica UTC técnica preservada | **PASA** — los 152 instantes no se tocan |
| G-CLOCK-04 | Usos de backend inventariados | **PASA** — 26/26 clasificados |
| G-CLOCK-05 | Usos de frontend inventariados | **PASA** — 15, de los que 2 son autoridad |
| G-CLOCK-06 | Impacto histórico clasificado | **PASA** — cero |
| G-CLOCK-07 | Sin reinterpretación automática | **PASA** |
| G-CLOCK-08 | Sin cambio de regla fiscal | **PASA** — `D0-07` sigue abierta |
| G-CLOCK-09 | Diseño del ayudante explícito | **PASA** — §9 |
| G-CLOCK-10 | Defensa de despliegue definida | **PASA**, y declarada como defensa, no autoridad |
| G-CLOCK-11 | PostgreSQL coherente | **PASA** — UTC, sin participación |
| G-CLOCK-12 | Planificador coherente | **PASA** |
| G-CLOCK-13 | Fronteras de licencia cubiertas | **PASA** — probadas |
| G-CLOCK-14 | Pruebas de independencia del anfitrión | **PASA** |
| G-CLOCK-15 | Guarda estática definida | **PASA** |
| G-CLOCK-16 | Sin refactor ajeno | **PASA** |
| G-CLOCK-17 | Sin cambio de esquema | **PASA** |
| G-CLOCK-18 | Material OQ = 0 | **PASA** |
| G-CLOCK-19 | UNKNOWN = 0 | **PASA** |
| G-CLOCK-20 | Trazabilidad 100 % | **PASA** |

## 11. `/speckit.checklist`

- [ ] HEAD verificado · árbol clasificado · dueña y apoyo confirmados
- [ ] Decisión de la dueña registrada · `ADR-D0-001` revisado
- [ ] Relojes de backend y de frontend recontados y clasificados
- [ ] Riesgo histórico y fiscal clasificados como cero, con motivo
- [ ] Licenciamiento analizado y **probado**, no modificado
- [ ] `active_policy` analizado · ayudante diseñado · configuración decidida
- [ ] Despliegue y planificador revisados · PostgreSQL revisado
- [ ] Pruebas planificadas: instante fijo, matriz de zonas, licencia, UTC técnico, frontend
- [ ] Guarda planificada · mutaciones planificadas · sin migración oculta
- [ ] Material OQ = 0 · UNKNOWN = 0 · trazabilidad 100 %

## 12. `/speckit.tasks`

| ID | Tarea | Ficheros | Requisito | Mutación |
|---|---|---|---|---|
| T-01 | Ayudante canónico y ajuste de configuración | `app/shared/clock.py`, `app/core/config.py` | 102, 103, 105 | 02, 03 |
| T-02 | Tesorería: 13 usos | `treasury/rates.py`, `treasury/service.py` | 106, 107 | 01 |
| T-03 | Ventas: 5 usos | `sales/service.py` | 106, 107 | 01 |
| T-04 | Compras: 3 usos | `purchasing/service.py` | 106 | 01 |
| T-05 | Fiscal: 2 usos, solo fuente de fecha | `fiscal/service.py` | 106, 113 | 01 |
| T-06 | Regulatorio, reportes y comercial: 3 usos | tres servicios | 106 | 01 |
| T-07 | Frontend: los 2 que envían fecha de negocio | `ListasPrecioPage.tsx`, `MaestrosPage.tsx`, helper de `lib/` | 111 | 06 |
| T-08 | Cinturón de despliegue | `compose.yaml`, `.env.example`, unidad systemd | 108 | — |
| T-09 | Guarda estática | `tests/test_business_clock_guard.py` | 115 | 05 |
| T-10 | Unitarias del ayudante, matriz de zonas y política cruzada | `tests/test_business_clock.py` | 104, 116 | 01, 02, 03 |
| T-11 | Fronteras de licencia | mismo fichero | 112 | 04 |
| T-12 | No regresión de instantes técnicos | mismo fichero | 103 | 02 |

**Requisitos huérfanos: 0. Tareas huérfanas: 0.**

## 13. `/speckit.analyze` previo a implementar

| Contador | Valor |
|---|---:|
| BLOCKER / CRITICAL / CONTRADICTIONS | 0 / 0 / 0 |
| OWNER_IDENTITY_CONFLICT | 0 |
| ORPHAN REQUIREMENTS / TASKS | 0 / 0 |
| MATERIAL OQ / UNKNOWN | 0 / 0 |
| Riesgo histórico / fiscal | 0 / 0 |
| Cambios de esquema previstos | 0 |
| TRACEABILITY | 100 % |

Se consume la autorización expresa y se implementa.

## 14. `/speckit.implement`

| Fichero | Cambio |
|---|---|
| `app/shared/clock.py` | **Nuevo.** `zona_de_negocio()`, `ahora_de_negocio()`, `hoy_de_negocio()`. La autoridad, en el código |
| `app/core/config.py` | `business_timezone: str = "America/Caracas"` |
| 8 servicios de backend | Los **26** usos migran a `hoy_de_negocio()`. Cero `date.today()` en el producto |
| `treasury/rates.py` | Además, la **ventana del día** pasa a ser la de Caracas (ver abajo) |
| `src/lib/fecha-de-negocio.ts` | **Nuevo.** `hoyDeNegocio()` con `Intl` y la zona nombrada |
| `ListasPrecioPage.tsx`, `MaestrosPage.tsx` | Dejan de enviar el día del navegador |
| `compose.yaml`, `.env.example`, unidad systemd | `TZ=America/Caracas` como **cinturón**, declarado como tal |
| `tests/test_business_clock.py`, `tests/test_business_clock_guard.py` | **Nuevos**, 24 pruebas |
| 16 ficheros de prueba | Adaptados: siembran con el día de negocio, que es lo que el producto resuelve |
| `e2e/helpers/ventas.ts` | `hoy()` pasa a ser el día de negocio: el E2E es un cliente más |

**Migraciones: 0. Cambios de esquema: 0. Reinterpretación de histórico: 0.**

### Lo que el delta descubrió a mitad de camino

Convertir la **fecha** a Caracas no bastaba. El módulo de tasas traducía una fecha
suelta `D` a la ventana `D 00:00 UTC … D 23:59:59 UTC`, de modo que, con el día de
negocio ya en Caracas, una tasa registrada «ahora» caía **fuera** de su propio día
durante las cuatro horas de diferencia: el mismo defecto, movido de sitio. Lo detectó
el E2E de tesorería, no un razonamiento.

La ventana pasa a ser la del calendario de negocio. No cambia el algoritmo de selección
—orden, prioridad, arrastre, caducidad—: cambia a qué calendario pertenece el día que se
consulta, que es exactamente lo que la dueña ratificó.

### Adaptación de pruebas, no relajación

Dieciséis ficheros sembraban «hoy» con el reloj del proceso para algo que el producto
resuelve por día de negocio. Ahora siembran con el día de negocio. Ninguna aserción se
debilita; ninguna se elimina. El fichero de CLOCK-013 **no se toca**: aquel delta lo dejó
sin reloj y su guarda sigue intacta.

## 15. Evidencia — `evidence/policy-clock-local/`

| Fichero | Contenido |
|---|---|
| `experimento-politica.txt` | El caso que originó todo, antes y después |
| `matriz-de-zonas.txt` | El conjunto dirigido bajo cuatro zonas |
| `licenciamiento.txt` | La corrección de la auditoría previa, con la salida del motor |
| `mutaciones.txt` | CLOCK-POLICY-01..06 |
| `e2e.txt` | E2E y la clasificación de sus fallos |
| `regresion.txt` | La regresión completa |

### Matriz de zonas — conjunto dirigido

| Zona del proceso | Día civil | Resultado |
|---|---|---|
| `America/Caracas` | 2026-09-16 | **verde** |
| `UTC` | 2026-09-17 | **verde** |
| `Europe/Amsterdam` | 2026-09-17 | **verde** |
| `Pacific/Kiritimati` | 2026-09-17 | **verde** |

### La política, antes y después

| Zona | Antes | Después |
|---|---|---|
| `America/Caracas` | POL-16 | POL-16 |
| `UTC` | **POL-17** | POL-16 |
| `Europe/Amsterdam` | **POL-17** | POL-16 |
| `Pacific/Kiritimati` | **POL-17** | POL-16 |

### Mutaciones

| Mutación | Qué reintroduce | Resultado |
|---|---|---|
| CLOCK-POLICY-01 | El reloj local en el respaldo de `active_policy` | **muere** — 3 zonas |
| CLOCK-POLICY-02 | El ayudante devuelve el día en UTC | **muere** — 3 pruebas |
| CLOCK-POLICY-03 | Se retira `ZoneInfo` y manda el anfitrión | **muere** — 3 pruebas |
| CLOCK-POLICY-04 | La licencia se lee sin zona | **muere** — la frontera de mayo |
| CLOCK-POLICY-05 | Se cuela `date.today()` en la regla vigente | **muere** — la guarda |
| CLOCK-POLICY-06 | El navegador vuelve a decidir la fecha | **muere** — 3 pruebas de frontend |

6/6 efectivas. Dos exigieron rehacerse: la 01 porque mi prueba pasaba la fecha explícita
y no tocaba el respaldo —defecto de la prueba, corregido con un caso nuevo—, y la 05
porque la primera versión rompía la sintaxis, y una mutación que no compila no demuestra
nada. La restauración de la 06 no se verificó al primer intento: `git checkout` no
restituye un fichero sin seguimiento. Corregido a mano y comprobado.

## 16. Regresión y comprobaciones

| Suite | Resultado |
|---|---|
| Backend completo, `TZ=Europe/Amsterdam` | **1.656 pasadas · 0 fallos · 8 saltadas (S3)** de 1.664 |
| Frontend | vitest **376/376** · ESLint limpio · `vite build` correcto · ~~`tsc` limpio~~ |
| ↳ **Corrección (2026-09-19)** | El `tsc` de aquella ejecución fue `tsc --noEmit -p tsconfig.json`, y ese `tsconfig.json` es un *solution config* (`files: []`): recorre **cero ficheros** y termina en 0 siempre. Medido en el ciclo `BUILD-TSC-TESORERIA`. En ese momento la rama **ya no compilaba** —`e43cf48` había introducido un error de tipos—, así que aquella línea daba por limpio un gate que no miró nada. La orden válida es `npm run typecheck` (`tsc -b`). Ninguna conclusión de esta delta cambia: el defecto estaba en tesorería, no aquí |
| E2E de los flujos tocados (tesorería y tasas) | **29/29** |
| E2E completa | 163 pasadas / 39 fallos, **ninguno de fechas** (§17) |
| CLOCK-013 | **verde** bajo las cuatro zonas |
| FLOAT-038-A/B/C | **verdes** |
| Multiempresa y permisos | **verdes** |

## 17. Clasificación de lo encontrado

| Hallazgo | Clase | Tratamiento |
|---|---|---|
| El día de negocio salía del reloj del anfitrión | `PRODUCT_CLOCK_DEFECT` | **Corregido** |
| La ventana del día seguía siendo la de UTC | `PRODUCT_CLOCK_DEFECT`, descubierto dentro del delta | **Corregido** |
| Pruebas y E2E que sembraban con el reloj del proceso | `TEST_DEFECT` | Adaptados |
| Licenciamiento «evaluaba en UTC» | **Afirmación errónea de la auditoría previa** | Rectificada y fijada con prueba |
| `E2E-HELPER-EMPRESA-AMBIGUO` y `E2E-046-TIPOS` en la suite completa | `PREEXISTING_SEALED`, deudas registradas | **No absorbidas** |
| `n6-multicompany` sin su base | `EXTERNAL_ENVIRONMENT` | Declarado |
| Clúster, antivirus y semillas perdidos al rotar `/tmp` | `EXTERNAL_ENVIRONMENT` | Reconstruidos |

`NEW_REGRESSION_POLICY_CLOCK = 0` · `HISTORICAL_DATA_RISK = 0` ·
`FISCAL_HISTORICAL_RISK = 0` · `AUTH_MC_INTERMITTENT = 0` · `UNKNOWN = 0`.

## 18. `/speckit.analyze` final y trazabilidad

| Requisito | Prueba | Mutación |
|---|---|---|
| FR-001-102 | `business_timezone` única; `test_el_ayudante_existe_y_es_la_unica_fuente` | 03 |
| FR-001-103 | `test_los_instantes_tecnicos_siguen_siendo_utc_con_zona` | 02 |
| FR-001-104 | `test_el_dia_de_negocio_no_cambia_con_la_zona_del_proceso[4 zonas]` | 02, 03 |
| FR-001-105 | `test_el_dia_de_negocio_es_el_de_caracas` | 02 |
| FR-001-106 | 26/26 migrados; guarda estática | 05 |
| FR-001-107 | `test_una_fecha_explicita_manda_sobre_el_hoy_de_negocio` | 01 |
| FR-001-108 | `compose.yaml`, `.env.example`, unidad systemd | — |
| FR-001-109 | PostgreSQL en UTC, sin participación | — |
| FR-001-110 | Planificador intacto; instantes UTC | 02 |
| FR-001-111 | 4 pruebas de `fecha-de-negocio.test.ts` | 06 |
| FR-001-112 | `test_las_fronteras_de_licencia_son_las_de_caracas` | 04 |
| FR-001-113 | Fiscal: solo fuente de fecha; regresión fiscal verde | 05 |
| FR-001-114 | Sin migración ni recálculo: 0 ficheros de datos tocados | — |
| FR-001-115 | `test_la_logica_de_negocio_no_lee_el_reloj_del_proceso` | 05 |
| FR-001-116 | `test_sin_fecha_la_politica_sale_del_calendario_de_negocio[4 zonas]` | 01 |
| FR-001-117 | Regresión 1.656/0; CLOCK-013 y FLOAT-038 verdes | — |

| Contador final | Valor |
|---|---:|
| `date.today()` sin aprobar en lógica de negocio | **0** |
| Autoridad de fecha en el anfitrión | **0** |
| Autoridad de fecha en el navegador | **0** |
| Regresión de UTC técnico | **0** |
| Reinterpretación de histórico | **0** |
| Cambios de regla fiscal | **0** |
| BLOCKER / CRITICAL / CONTRADICTIONS | 0 / 0 / 0 |
| ORPHAN REQUIREMENTS / TASKS | 0 / 0 |
| MATERIAL OQ / UNKNOWN | 0 / 0 |
| **TRACEABILITY** | **100 %** |

## 19. Deudas no absorbidas

E2E-031-RESERVAS · E2E-HELPER-EMPRESA-AMBIGUO · INBOX-045-AISLAMIENTO · E2E-046-TIPOS ·
ORPHAN-046-SINGLE · IDEM-046-TRUNC · paginación de la bandeja · AUTH-MC-INTERMITENTE ·
D0-06 · D0-07 · OQ-048 · MD-049 · camino tras `EXPIRED` · Spec 018 · certificación de
compras · Spec 053 · deriva heredada de 21 operaciones · DT-03/04/06/07/10..18 ·
`license_timezone`, constante muerta de la Spec 004.

## 20. Estado resultante

| | |
|---|---|
| **POLICY-CLOCK-LOCAL** | **CLOSED / CONVERGED** |
| Spec 001 | sigue `PARTIALLY_IMPLEMENTED`: cerrar esta deuda no la completa |
| Spec 052 | sigue `PARTIALLY_IMPLEMENTED` |
| `D0-07` | **abierta**: este delta no homologa nada |
| CLOCK-013, FLOAT-038-A/B/C, MIGR-0033 | cerrados y verdes; ninguno reabierto |
