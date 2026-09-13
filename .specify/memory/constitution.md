# CONSTITUCIÓN DE KONTROL

| Campo | Valor |
|---|---|
| Producto | KONTROL — Plataforma Administrativa Empresarial para Venezuela |
| Documento | Constitución del proyecto |
| Versión | 1.2 |
| Estado | Aprobada · enmendada en Gate G0 (E-01, E-02, E-03) · enmiendas E-04 a E-07 pendientes de ratificación |
| Fecha | 2026-08-03 · última enmienda 2026-08-29 |
| Autoridad | Nivel 2 — Constitución de KONTROL |
| Fuentes | Documento Maestro de Requerimientos (Volumen 1); Estándar Maestro de Frontend y Arquitectura Técnica v1.0; Especificación de Licenciamiento Anual; Leyes Venezolanas (base jurídico-funcional) |
| Ruta | `.specify/memory/constitution.md` |

> La Constitución define los principios no negociables del proyecto. Ninguna Spec, ADR, decisión o implementación puede contradecirla sin un proceso formal de enmienda trazable y aprobado por Producto, Arquitectura, Seguridad, Legal y QA.

---

## Principios no negociables

### Principio 1 — Spec antes que código
No se implementa ninguna función sin una Spec aprobada mediante el flujo Spec Kit.
No se programa código productivo antes de completar `/speckit.specify → /speckit.clarify → /speckit.plan → /speckit.checklist → /speckit.tasks → /speckit.analyze` y obtener autorización expresa.

### Principio 2 — Autorización expresa
No se ejecuta `/speckit.implement` sin autorización expresa del responsable del proyecto.
El silencio, los mensajes ambiguos o las aprobaciones genéricas no constituyen autorización.
La autorización debe mencionar expresamente el código de la iniciativa (por ejemplo, `001-fundacion`).

### Principio 3 — Trazabilidad completa
Toda función mantiene la cadena:
**Requisito → Spec → Plan → Tarea → Código → Prueba → Evidencia.**
No existe requisito sin prueba; no existe tarea sin requisito; no existe código sin tarea.

### Principio 4 — Núcleo fiscal separado
El núcleo fiscal permanece separado de los módulos administrativos.
Las reglas fiscales se versionan (TaxRuleVersion, FiscalRelease) y nunca se reescriben.
Los documentos fiscales emitidos son inmutables; toda corrección se realiza mediante nota de débito, nota de crédito, anulación o reverso vinculado.
Una actualización administrativa no puede alterar documentos históricos ni una versión fiscal homologada.

### Principio 5 — Datos históricos protegidos
No se modifica ni elimina físicamente:
- Facturas emitidas, notas emitidas, retenciones practicadas.
- Pagos aprobados, cobros aplicados, movimientos de inventario, cierres.
- Permisos utilizados, eventos de auditoría, licencias emitidas, activaciones registradas.

### Principio 6 — Seguridad en backend
El frontend no es autoridad sobre: permisos, alcance, licencia, integridad, estados, acciones permitidas, multiempresa, reglas fiscales ni reglas regulatorias.
El backend y la base de datos validan cada operación (deny by default).

### Principio 7 — Frontend uniforme
Todas las rutas respetan el sistema de diseño y los componentes compartidos.
No se permiten variantes locales de formularios, tablas, botones, loaders, mensajes, modales, validaciones, estados o errores sin ADR.

### Principio 8 — No hardcodear reglas de negocio
No se hardcodean: impuestos, alícuotas, tasas, monedas, rubros, categorías, plazos fiscales, fechas de licenciamiento, reglas regulatorias, permisos, roles, estados transaccionales ni límites contratados.
Todas las reglas críticas son versionadas y con fuente.

### Principio 9 — Instalación independiente por cliente
Cada cliente tiene una instalación independiente mediante Docker Compose en su propio servidor.
No se comparte entre clientes: base de datos, volúmenes, secretos, procesos, archivos, configuración, identidad de instalación, licencia ni logs.

### Principio 10 — Calidad demostrable
No se declara una función terminada sin pruebas y evidencia.
La ausencia de error técnico no equivale a calidad de producto (Estándar de Frontend, prohibición expresa).

### Principio 11 — Accesibilidad y responsive
Toda interfaz cumple WCAG 2.2 AA y funciona en escritorio, laptop, tablet, móvil, zoom ampliado y solo teclado.
Las tablas no usan scroll horizontal; se adaptan a tarjetas en móvil.

### Principio 12 — Decisiones documentadas
Toda excepción o decisión arquitectónica relevante se formaliza mediante ADR con responsable, alternativas, justificación, riesgo y estado de aprobación.

### Principio 13 — Integridad transaccional
Los procesos críticos utilizan transacciones atómicas, restricciones (constraints), idempotencia, control de concurrencia (locks/versión/ETag), estados explícitos y auditoría.
No se permite doble envío, sobrescritura silenciosa ni reintentos no idempotentes en operaciones críticas.

### Principio 14 — Infraestructura reproducible
La instalación debe reconstruirse a partir de: código, imágenes versionadas, Compose, migraciones, seeds idempotentes, variables documentadas y backups verificados.
No se usa `latest` en producción.

### Principio 15 — Datos del cliente protegidos
El licenciamiento no otorga al propietario de KONTROL acceso automático a los datos comerciales del cliente.
La autoridad central de licencias no almacena facturas, inventario, clientes, proveedores ni operaciones del cliente.

### Principio 16 — Gestión de versiones
Las dependencias y las imágenes Docker están versionadas con archivos lock e imágenes fijadas.
No se usan dependencias `latest` ni rangos abiertos en producción.

### Principio 17 — No retrabajo por inconsistencia visual
No se permite que cada módulo resuelva individualmente formularios, tablas, botones, loaders, mensajes, modales, validaciones, estados y errores.
Los componentes compartidos son obligatorios y se prueban una sola vez.

### Principio 18 — Política de modales
KONTROL no usa modales para crear/editar entidades, matrices, DataTables, configuraciones extensas, documentos, permisos ni procesos complejos.
Los formularios complejos usan ruta y pantalla completa con URL propia.
Los modales se reservan para confirmación breve (desactivar, eliminar, anular, reversar, descartar cambios, alertas).

### Principio 19 — Reglas normativas versionadas y con fuente
Toda norma fiscal o regulatoria (IVA, ISLR, IGTF, retenciones, SICA, SIGESAI, SACS, facturación) se modela con fuente legal, Gaceta, vigencia, versión y evidencia.
El estado `LEGAL_VALIDATION_REQUIRED` se utiliza ante cualquier duda de vigencia o contradicción normativa; no se declara cumplimiento sin verificación.

### Principio 20 — No sustitución de organismos oficiales
KONTROL no fabrica permisos, guías ni certificados de organismos externos (SENIAT, SUNAGRO/SICA, INSAI/SIGESAI, SACS).
Registra, valida, adjunta y bloquea según el documento oficial; la integración automática solo se habilita mediante convenio/API oficial aprobada.

### Principio 21 — Paridad del motor de persistencia
La evidencia de calidad solo es válida sobre el motor de persistencia de producción.
Ninguna función se declara terminada con evidencia obtenida sobre un motor distinto del que operará el cliente.
PostgreSQL es obligatorio en desarrollo integrado, pruebas de integración y contrato, E2E, QA, staging y producción; cualquier excepción es explícita, declarada y acotada a pruebas que no ejercitan el dialecto.

### Principio 22 — Autoridad única por capacidad transversal
Las capacidades transversales —aprobaciones, gestión documental, auditoría, notificaciones, permisos y reglas normativas— tienen una sola implementación en la plataforma.
Ningún módulo implementa su propia versión de una capacidad transversal.

### Principio 23 — Captura anticipada de datos no reconstruibles
Cuando un dato no pueda derivarse a posteriori de ninguna otra fuente, su captura se implementa en cuanto la decisión que lo exige queda aprobada, aunque la funcionalidad que lo explota se planifique para una fase posterior.
Proteger lo registrado (P5) no basta: hay que registrar lo que después será imposible reconstruir.

### Principio 24 — La instalación limpia es evidencia obligatoria
Toda Spec que toque modelos, migraciones, restricciones, valores por defecto, semillas o catálogos demuestra su comportamiento sobre un PostgreSQL **recién creado**: de cero a la cabeza de migraciones, semilla mínima, flujos dirigidos y E2E.
Una base con meses de datos acumulados no basta: oculta exactamente los defectos del primer día de un cliente.

### Principio 25 — Las altas concurrentes las gobierna la base
«Buscar la fila y, si no está, crearla» sobre una restricción única no es protección suficiente bajo concurrencia: la autoridad es la base.
La colisión esperada se maneja en la transacción, se traduce al conflicto de dominio o al resultado canónico que corresponda, no escapa como error 500 y no duplica el registro. Se captura **solo** la violación única de esa restricción; cualquier otro error de integridad se vuelve a lanzar.
Una prueba de concurrencia **fuerza** la carrera y demuestra que ocurrió; nunca acepta un error 500, un `IntegrityError` ni una excepción arbitraria como rechazo válido.

### Principio 26 — Paridad entre modelos y migraciones
Toda restricción que el negocio necesita existe, con el mismo nombre, en los modelos y en las migraciones. La base construida desde los modelos y la base migrada imponen restricciones equivalentes.
Una restricción que solo vive en la migración no se ejerce en las pruebas que construyen el esquema desde los modelos.

### Principio 27 — Una mutación solo cuenta si cambia lo observable
Una mutación es evidencia solo si introduce un defecto real, cambia la semántica observable, hace fallar la prueba por ese defecto y no por un accidente distinto.
Si el código mutado produce el mismo resultado para el caso probado, la mutación no es válida y se sustituye. Una ejecución sin resultado legible —código de salida de herramienta, argumentos mal pasados— no cuenta ni como detectada ni como superviviente.

---

## Jerarquía de autoridad (resumen)

| Nivel | Fuente |
|---|---|
| 1 | Normas oficiales venezolanas vigentes (leyes, decretos, providencias, resoluciones, Gacetas) |
| 2 | Constitución de KONTROL (este documento) |
| 3 | Documentos maestros vigentes de KONTROL (Maestro, Arquitectura Funcional, Modelo de Datos, Wireframes, Arquitectura Técnica, Estándar Frontend, Licenciamiento, Spec Kit, QA, Homologación) |
| 4 | Specs aprobadas |
| 5 | ADR aprobados |
| 6 | Contratos (OpenAPI, eventos, archivos, esquemas) |
| 7 | Código y pruebas (deben obedecer la Spec; no justifican contradicciones) |
| 8 | Antecedentes INNOVA y manuales de terceros (solo referencias; no autoridad legal ni arquitectónica) |

---

## Control de versiones

| Versión | Fecha | Cambio | Autor | Aprobación |
|---|---|---|---|---|
| 1.0 | 2026-08-03 | Creación inicial derivada de los documentos maestros y la base jurídico-funcional | Equipo de gobierno de KONTROL | Producto, Arquitectura, Seguridad, Legal, QA |
| 1.1 | 2026-08-29 | **Gate G0** — incorporación de los principios 21, 22 y 23 (enmiendas E-01, E-02, E-03 de `D0-constitution-diff.md`). Ninguna enmienda contradice un principio vigente; las tres refuerzan P5, P10 y P17. Fundamento documental: `ADR-D0-001`, `ADR-D0-002`, `ADR-D0-008`, `ADR-D0-009`, `ADR-D0-011` y `docs/governance/d0-foundational-decisions/D0-historical-data-risk.md` | Gate G0 de gobierno arquitectónico | Arquitectura, Seguridad, QA · **ratificación de Producto y Legal pendiente** (registrada en `docs/governance/G0-final-resolution.md`) |
| 1.2 | 2026-09-13 | **Enmiendas E-04 a E-07** — principios 24 (instalación limpia como evidencia), 25 (altas concurrentes gobernadas por la base), 26 (paridad modelos ↔ migraciones) y 27 (calidad de mutaciones). Refuerzan P13, P14 y P21 sin contradecir ninguno. Fundamento: ciclo de la Spec 013 (`specs/006-tesoreria/spec013-clarifications.md` §7 y `spec013-convergence.md`), donde la reinstalación de cero destapó una familia de errores 500 por carreras de alta, la unicidad vivía solo en la migración y dos mutaciones dejaron de ser válidas contra el código final | Instrucción expresa de Producto (secuencia controlada post-Spec 013) | **Ratificación de Arquitectura, Seguridad, QA y Legal pendiente** |

