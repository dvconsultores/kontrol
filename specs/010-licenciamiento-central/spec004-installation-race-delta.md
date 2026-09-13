# SPEC 004 · DELTA DIRIGIDO — CARRERA EN LA CREACIÓN DE LA INSTALACIÓN

> Iniciado el 2026-09-13. Dueño: **Spec 004 global — Licenciamiento**
> (`spec-equivalence-map.md` línea 11: «004 Licenciamiento · `001-fundacion` +
> `010-licenciamiento-central`»). **No** es la carpeta `004-compras`, que
> corresponde a la Spec 028. No se crea otra Spec.
>
> Este delta es de **concurrencia e idempotencia**. La política de licencia
> —ciclo anual del 1 de abril al 31 de marzo, aviso del 1 al 20 de abril, aviso
> crítico del 21 al 30, solo lectura desde el 1 de mayo sin renovar, autoridad
> horaria `America/Caracas`, licencia firmada con clave asimétrica del
> proveedor, identidad persistente de instalación— **no se toca**.

## 1. `/speckit.specify`

Dos peticiones simultáneas para crear **la** instalación no pueden crear dos
instalaciones, ni dos identidades, ni devolver un 500; convergen de forma
determinista en una sola.

## 2. `/speckit.clarify` — la identidad, investigada

| Punto | Hallazgo |
|---|---|
| Autoridad | FR-001-002: «al primer arranque, el backend genera `installation_uuid`, par de claves… persistidos en volumen protegido». FR-001-003: persiste ante recreación. **Una** identidad por despliegue |
| Clave natural | **Ninguna**. `installation_uuid` es único pero **aleatorio**: dos altas generan dos valores distintos y **no chocan** en el índice |
| Tabla | `installations`, alcance `GLOBAL`; `tenants.installation_id` → `installations.id` (1:1 en la fundación, CL-02) |
| Creación | `licensing/service.py · get_or_create_installation`: `select(Installation).limit(1)`; si no hay, genera clave Ed25519, **escribe la privada con `O_TRUNC`** y confirma la fila |
| Llamadas | `GET /license/installation-request` (**sin autenticación**) y `POST /setup/initialize` |
| Lecturas singulares | `get_installation` y `setup_status`: `limit(1)` **sin orden** |
| Ligadura de licencia | `import_license` rechaza con `LICENSE_INSTALLATION_MISMATCH` (423) si `payload.installation_id` no es el de la instalación. **Ninguna prueba lo ejerce** |

### El defecto es peor que un 500

Como el UUID es aleatorio, la carrera no llega a ningún índice: **se crean dos
instalaciones**. La segunda sobrescribe el fichero de clave privada, así que la
clave del volumen corresponde a una fila y la otra fila guarda una clave pública
huérfana. Y como las lecturas hacen `limit(1)` sin orden, qué instalación ve el
sistema —y contra cuál se valida una licencia— queda al plan de PostgreSQL.

Alcanzable sin credenciales: dos `GET /license/installation-request` a la vez
contra una instalación recién desplegada.

### Preguntas

**¿Una instalación por base?** Resuelta con autoridad: FR-001-002, CL-02 y la
semántica singular de `get_installation`. **0 preguntas materiales.**

## 3. `/speckit.plan`

**Opción elegida: bloqueo consultivo transaccional de PostgreSQL** alrededor del
alta, que P13 enumera expresamente («control de concurrencia (locks…)»).

1. `pg_advisory_xact_lock` con una clave fija de la instalación al empezar
   `get_or_create_installation`; se libera al confirmar.
2. Bajo el bloqueo, **releer** con orden determinista (`created_at`, `id`); si ya
   hay instalación, devolverla sin generar ni escribir nada.
3. Solo quien gana el bloqueo genera la clave y **escribe el fichero**.
4. `get_installation` y `setup_status` leen con el mismo orden determinista.

**Opción descartada: índice único «singleton» en la tabla.** Cambiaría el esquema
(migración, paridad P26) para un invariante que el bloqueo ya garantiza, y
algunos *fixtures* de pruebas insertan instalaciones propias. No aporta frente al
defecto real, que es la escritura del fichero, no solo la fila.

## 4. Compuerta constitucional

| Principio | Cumplimiento |
|---|---|
| P13 · integridad transaccional | bloqueo + relectura bajo bloqueo |
| P21 · paridad del motor | la prueba de carrera corre en PostgreSQL real |
| P24 · instalación limpia | la carrera se prueba sobre una base temporal **migrada de cero** |
| P25 · altas concurrentes | la base gobierna; ningún error escapa; ninguna duplicación |
| P27 · mutaciones | tres, con semántica observable |
| Política de licencia | intacta |

## 5. `/speckit.checklist` y `/speckit.tasks`

1. Bloqueo y relectura determinista en el servicio.
2. Orden determinista en `get_installation` y `setup_status`.
3. Prueba de carrera forzada: dos llamadas **reales**, la primera retenida
   después de obtener el bloqueo hasta ver a la segunda esperando en
   PostgreSQL. Aserciones: **1 fila**, mismo `installation_uuid` para ambas,
   ninguna excepción, y la clave pública del fichero **coincide** con la de la
   fila.
4. Reintento idempotente: una segunda llamada devuelve la misma identidad y no
   reescribe el fichero.
5. Hostiles: licencia correctamente firmada para **otra** instalación →
   `LICENSE_INSTALLATION_MISMATCH` sin tocar el estado; identificador
   falsificado; repetición.
6. Mutaciones: **M004-RACE-01** quitar el bloqueo; **M004-RACE-02** crear otra
   aunque bajo el bloqueo ya exista; **M004-RACE-03** quitar la ligadura de la
   licencia.
7. Regresión del licenciamiento (`test_license.py`, `test_licensing_central.py`)
   y regresión completa.

## 6. `/speckit.analyze`

| | |
|---|---|
| BLOCKER | 0 |
| CRITICAL | 0 |
| CONTRADICTIONS | 0 |
| MATERIAL OQ | 0 |
| UNKNOWN | 0 |
| TRACEABILITY | 100 % — cada requisito del §1 y cada punto del §2 trazado a una tarea del §5 |

**Autorización expresa consumible.** La implementación empieza cuando termine la
regresión del cierre de la Spec 013, para no contaminar su evidencia.

## 7. Implementación y evidencia

### Implementación

`app/modules/licensing/service.py`: `_BLOQUEO_ALTA_INSTALACION`,
`_instalacion_canonica` (orden por `created_at`, `id`) y
`_bloquear_alta_de_instalacion` (`pg_advisory_xact_lock`). `get_or_create_installation`
lee, bloquea, **relee** y solo entonces genera la clave y escribe el fichero. Las
dos lecturas singulares del servicio usan `_instalacion_canonica`;
`setup/api.py · setup_status` usa el mismo orden. La política de licencia no se
tocó.

### Pruebas · `tests/test_spec004_installation_race.py`

Sobre una base temporal **migrada de cero** en cada módulo (P24).

| Prueba | Qué exige |
|---|---|
| `test_dos_altas_simultaneas_dejan_una_instalacion_y_una_sola_clave` | dos llamadas reales; la segunda **observada esperando** el bloqueo en `pg_stat_activity`; 1 fila; misma identidad; un solo par de claves; la clave del volumen corresponde a la fila |
| `test_repetir_la_peticion_no_crea_otra_identidad_ni_reescribe_la_clave` | reintento idempotente sin reescribir el fichero |
| `test_con_dos_filas_heredadas_todas_las_lecturas_eligen_la_mas_antigua` | con la más nueva primero en disco, `get_installation`, `get_or_create_installation` y `setup_status` eligen la más antigua |
| `test_una_licencia_firmada_para_otra_instalacion_se_rechaza_sin_tocar_el_estado` ×2 | identificador ajeno y falsificado → `LICENSE_INSTALLATION_MISMATCH`, sin `LicenseState`, un evento de rechazo |
| `test_control_positivo_la_licencia_de_esta_instalacion_si_se_acepta` | la firma de la prueba es buena: el rechazo de arriba no es accidental |

Dirigidas junto con `test_license.py` (ciclo anual, aviso, aviso crítico, solo
lectura desde el 1 de mayo, retroceso de reloj, firmas) y
`test_licensing_central.py`: **32/32**, sin saltos, Ruff limpio.

### Mutaciones

| | Mutación | Resultado |
|---|---|---|
| M004-RACE-01 | sin bloqueo | cae · «la segunda alta nunca esperó a la primera» |
| M004-RACE-02 | bajo el bloqueo crea otra aunque ya exista | cae · «cada petición se quedó con una identidad distinta» |
| M004-RACE-03 | sin ligadura licencia ↔ instalación | cae · la licencia ajena se acepta (2 casos) |

Servicio restaurado byte a byte después de cada una.

### Un intento de evidencia que no vale · P27

Se lanzaron 16 `GET /license/installation-request` anónimos y simultáneos contra
un uvicorn apuntando a una base **vacía**, dos veces: con el código corregido y
con M004-RACE-01 aplicada como línea base. **Las dos pasadas dejaron una sola
instalación.** La ráfaga no llegó a entrar en la ventana de carrera: la primera
petición confirmaba antes de que las demás leyeran.

Por eso **no se presenta como evidencia de exclusión**: una prueba que da el mismo
resultado con y sin el defecto no demuestra nada sobre el defecto. Queda como
comprobación funcional de la ruta de aprovisionamiento anónima sobre base limpia
—16 respuestas 200, una identidad, 0 trazas, 0 respuestas 5xx—. La evidencia de
la exclusión es la prueba forzada y su mutación M004-RACE-01. No se añadieron
retardos al servidor para provocarla: sería instrumentar la ruta de producción
para fabricar evidencia.

### Regresión completa

| Ejecución | Resultado |
|---|---|
| Primera, con el delta aplicado | `EXIT=1` · 1 fallo, 1401 pasan, 8 saltos. El fallo, `test_sin_politica_no_se_triangula`, **no** es de este delta: códigos aleatorios de 256 valores en las pruebas de la 013 que coincidían. `TEST_DEFECT` demostrado forzando la coincidencia y corregido en `109395a` |
| Final | `EXIT=0` · **1410** · **1402 pasan · 8 saltos · 0 fallos · 0 errores** · 8 saltos S3, 0 fuera de S3 |

La ejecución final trae **una advertencia** de hilo en
`test_documents_security.py::test_dos_subidas_simultaneas_no_producen_dos_v2`:
una `UniqueViolation` de `uq_document_versions_number` sin capturar en la subida
que pierde la carrera. Es **`PREEXISTING`** y de la **Spec 046**: aparece en una de
las cuatro regresiones del día, el módulo de documentos y esa prueba no se tocaron
en esta secuencia (último cambio `00d7cd2`). Programada como deuda en
`docs/roadmap/next-spec-decision.md`.

## 8. `/speckit.converge` dirigido

| Criterio | Resultado |
|---|---|
| Carrera forzada | **pasa**: la segunda alta espera y relee |
| Instalaciones creadas | **1** |
| HTTP 500 | **0** |
| Identidad duplicada | **0** · la clave del volumen corresponde a la fila |
| Reintento idempotente | **pasa**: misma identidad, fichero sin reescribir |
| Regresión de la licencia | **0** — ciclo anual, avisos, solo lectura, firmas, reloj e identidad en verde |
| Mutaciones | **3/3 caen** |
| Evidencia inválida declarada | la ráfaga HTTP, que no reprodujo la carrera ni con el defecto |
| UNKNOWN | 0 |
| Trazabilidad | 100 % |

**Veredicto del delta: `SPEC004 · carrera en la creación de la instalación —
COMPLETE / CONVERGED`.** La Spec 004 global conserva su estado
(`BLOCKED_BY_BUSINESS_DECISION`, D0-06): este delta no lo cambia.
