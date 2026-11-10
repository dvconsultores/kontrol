# Evidencia · Clasificación de almacenamiento, zona y etiquetado

**Fecha:** 2026-11-10. **Iniciativa:** `SPEC018_CLASIFICACION_ZONA_ETIQUETADO`. **Datos:** sintéticos.

| Campo | Valor |
|---|---|
| DATABASE_ENGINE | PostgreSQL 16.2 de QA |
| SCHEMA_SOURCE | Alembic, base nueva. Cabeza `0093_fusion_gov_storage`, fusión vacía de `0092_gov_proc07_evaluacion` (PROC-07, P1) y `0092_storage_classification`. `alembic heads` = 1 |
| BROWSER | Google Chrome, `qa/e2e-run.py --con-analizador` (base efímera por corrida) |

## Motor (`tests/test_storage_classification.py`)

En PostgreSQL pasan 15 de 15. En SQLite pasan 14 y se omite 1, la de concurrencia, que exige PostgreSQL.

| Escenario | Qué demuestra |
|---|---|
| Familia por ancestro | Una regla sobre el nodo raíz casa con un producto de una categoría hija. Devuelve zona, etiqueta requerida y razones sin UUID |
| Peso normalizado | 10 000 g caen en el rango de 5 a 20 kg mediante la conversión de unidades; 30 000 g no casan |
| Sin regla | Devuelve `NO_RULE` sin zona y con «No existe una regla de almacenamiento aplicable» |
| Ambigua | Misma prioridad y misma especificidad con destinos distintos dan `AMBIGUOUS`, sin regla y con las candidatas |
| Prioridad y especificidad | Gana la más específica; entre prioridades, gana la 1 |
| Criterio faltante | Una regla por peso con un producto sin peso da `NO_RULE` con «Peso» en lo faltante |
| UOM incompatible | Una unidad de volumen como unidad de peso se rechaza con 422 `UOM_DIMENSION_MISMATCH`, en la regla y en el perfil |
| Zona inválida | Zona de otra empresa: 404. Zona inactiva u otro almacén: 409. Por tipo de zona resuelve las zonas activas del almacén |
| Tipo sin zonas | La regla se descarta y la razón aparece en el resultado |
| Instantánea y vigencia | Reclasificar marca `SUPERSEDED` la anterior. Si cambia la regla, `stale`. Un `expected_version` viejo da 409 `VERSION_CONFLICT`. La instantánea conserva código y destino |
| Permisos | Con solo lectura: 403 al crear regla, perfil o política; 200 al evaluar |
| Aislamiento | Producto o condición de otra empresa: 404. Almacén de otra empresa: 404 |
| Política | Por defecto `DISABLED`, versión 1 al guardar, 409 si la versión es vieja |
| Auditoría | Se registran regla, perfil, política y clasificación |
| Concurrencia | Dos clasificaciones simultáneas dejan exactamente una `CURRENT` |

## Expediente (`tests/test_importaciones_storage.py`)

Pasan 11 de 11 en PostgreSQL y en SQLite.

| Escenario | Qué demuestra |
|---|---|
| Vista y clasificación | Sin clasificar no se puede ubicar. Al clasificar sale la zona, solo la candidata de esa zona y «Genere la etiqueta antes de ubicar» |
| Etiqueta y put-away | Sin etiqueta: 409 `STORAGE_LABEL_REQUIRED`. Etiqueta `ETQ-nnnnnn`, PDF con sha256 igual al de la base, impresión en línea. Ubicar fuera de la zona: 409 `LOCATION_OUTSIDE_DETERMINED_ZONE`. En la zona: 200 y queda en la tabla del expediente |
| Sin etiqueta | Con `NOT_REQUIRED` se ubica sin etiqueta, y generarla da 409 |
| Sin regla, bloquear | Sin candidatas y 409 `STORAGE_NO_RULE_BLOCKED` |
| Sin regla, permitir | Se ofrecen todas las ubicaciones |
| Almacén simple | Con `DISABLED` el comportamiento es el de siempre |
| Regla vencida | Si cambia la regla, 409 `STORAGE_CLASSIFICATION_STALE`. Al reclasificar, la anterior pasa a `SUPERSEDED` |
| Permisos | Con solo Compras: 200 al leer; 403 al clasificar, etiquetar y ubicar |
| Aislamiento | Recepción ajena: 404. Etiqueta de otro expediente: 404 |
| Nada pendiente | Clasificar sin pendientes da 409 `STORAGE_NOTHING_PENDING` |
| Auditoría | Se registra `STORAGE_LABEL_GENERATED` |

## Resto de puertas

| Puerta | Resultado |
|---|---|
| Alembic tras la fusión | `upgrade head`, `downgrade 0091` (por las dos ramas) y `upgrade head` en PostgreSQL: PASS. Termina en `0093` como punto de fusión |
| Regresión mínima en PostgreSQL tras la fusión | 324 de 324. Cubre: put-away 022, estructura 008, catálogo de zonas, maestros, taxonomía, multiestado, inventario, Importaciones (seguimiento, costos, landed cost, reporte, reubicación, almacenamiento), clasificación, catálogo (444) y sus guardas, cabezas, migraciones e instantáneas |
| Convergencia ORM/base | Las tablas nuevas convergen. `test_n10_convergence` sigue fallando solo por las 6 tablas históricas de importaciones (deuda conocida) |
| E2E Chrome (`importaciones.spec.ts`, paso 6) | PASS a 1280, 390 y 320 px tras la fusión. Recorre: zonas en el almacén → condición, perfil, regla y política en Maestros → Almacenamiento → clasificar en el expediente → zona y regla → una sola candidata → etiqueta PDF descargada → put-away en la zona → resto del flujo, incluida la reubicación |
| Axe WCAG 2.2 AA | 0 violaciones en la configuración de reglas, la clasificación del expediente y el etiquetado, a 1280, 390 y 320 px (sonda local) |
| Teclado | Tab pasa de «Etiquetado» a «Crear regla»; Enter activa «Generar etiqueta» |
| Desborde horizontal | Ninguno en esos estados a 390 y 320 px |
| Frontend | TSC, ESLint, build, Vitest completo y guardas del repo (autoridad de pantallas, puertas, contrato de consultas, completitud) |
| Backend estático | Ruff limpio; mypy en 154, igual a la línea base |

## Lo que NO se afirma

- **Rotación:** no clasifica. No existe la Spec 015 ni ninguna señal en el código. `ROTATION_CLASSIFICATION_COMPLETE = 0`.
- **Zonas A a E:** se pueden configurar como cualquier zona; su significado debe validarlo el sponsor.
- **Put-away genérico de Inventario:** no aplica la política. Se aplica en el put-away del expediente.
- **Cobertura de la E2E:** recorre el criterio de condición especial. Los criterios de familia, peso, volumen y tamaño están probados en el backend. Los casos «sin etiqueta» y «sin regla» están probados en backend y Vitest, no en navegador.
- **Etiqueta:** es identificación interna, no regulatoria ni GS1.

## Defectos reales encontrados y corregidos en el ciclo

- **Módulo no versionado:** la regla `storage/` del `.gitignore` ignoraba el módulo de código. Se añadió una negación solo para `resources/backend/app/modules/storage/`.
- **Motor:**
  - las reglas no se ordenaban antes de elegir la ganadora;
  - se perdían las razones de descarte;
  - dos clasificaciones simultáneas dejaban dos `CURRENT` (se serializa con el bloqueo del producto).
- **Frontend:**
  - formularios ocultos tras una autorización con una ruta inventada;
  - el perfil no se guardaba porque mandaba el volumen vacío como texto;
  - carrera al cargar la política;
  - selector de almacén sin `id` (accesibilidad) y sin opción vacía;
  - descarga de etiqueta protegida con un permiso de escritura;
  - lista de almacenes pedida al margen de la autoridad única.
