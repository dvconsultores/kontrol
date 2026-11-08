# CTL-02 · Bitácora institucional append-only

## 1. Lo que podrá hacer el usuario

Desde **Gobierno › Bitácora institucional**, Control Interno o el auditor localiza un evento y responde quién operó técnicamente, a qué funcionario representaba, qué cargo ejercía, en qué unidad y ente, con qué autoridad y categorías, desde qué sesión e IP, cuándo, bajo qué correlación, qué cambió y si fue éxito, rechazo o denegación. Lo ve como era en ese momento, aunque después cambie la ocupación o el vínculo.

## 2. Fuentes

GOV-CTL-002 y GOV-CTL-003 (P0; N18, N20, N27). N40 no es material. Reutiliza `AuditEvent` (006/051), su catálogo cerrado, ORG-06 y CTL-04.

## 3. Decisiones de diseño

Son de Claude. Ninguna requiere a la dueña.

| Id | Decisión |
|---|---|
| OD-CTL02-01 | Sin segunda bitácora: una columna JSON nula `institutional_context` en `audit_events`, protegida por los disparadores existentes |
| OD-CTL02-02 | La instantánea se calcula al registrar el evento. Nunca se reconstruye ni se reescribe; los eventos previos quedan sin contexto y se rotulan como anteriores |
| OD-CTL02-03 | Enriquecimiento central: `record_audit` llama a un proveedor registrado por Gobierno. El núcleo no conoce Gobierno |
| OD-CTL02-04 | Aplica a los eventos del catálogo con `owner_module = government`. Enterprise queda idéntico, también en sesión e IP |
| OD-CTL02-05 | Sin vínculo vigente: estado `SIN_VINCULO`, sin funcionario, cargo ni autoridad. Nunca se inventa |
| OD-CTL02-06 | La instantánea no guarda el documento del funcionario ni montos de competencia |
| OD-CTL02-07 | Consultas sensibles: las salidas de datos (10 exportaciones y descargas de Gobierno, todas ya auditadas). No se audita cada GET |
| OD-CTL02-08 | Autenticación: los eventos de sesión del tenant son visibles solo para cuentas vinculadas alguna vez a este ente; su contexto es «no aplica» |
| OD-CTL02-09 | Pantalla propia sin capacidad nueva: `gobierno_auditoria:view`. CTL-04 sigue siendo población y muestreo |
| OD-CTL02-10 | Los 403 de capacidad siguen sin evento: es comportamiento de plataforma y registrarlos exige tocar la ruta común de permisos |

## 4. Requisitos funcionales

- **FR-001** Todo evento de Gobierno con usuario y ente guarda su instantánea institucional, sesión e IP.
- **FR-002** Las denegaciones y rechazos conservan el evento y su contexto aunque la operación no ocurra.
- **FR-003** Listar con filtros por fecha, acción, usuario técnico, funcionario, unidad, correlación y resultado.
- **FR-004** Ver el detalle: actor técnico, actor efectivo, cargo, unidad, ente, autoridad, categorías, roles, sesión, IP, instante, correlación, antes y después seguros.
- **FR-005** Otro ente responde 404 y sus eventos no aparecen.
- **FR-006** La instantánea no cambia si cambian después la ocupación o el vínculo.

## 5. Fuera de alcance

CTL-03, operaciones de comprometer, pagar o aprobar, exportación de la bitácora, retroalimentar eventos antiguos.

## 6. Criterios de éxito

- **SC-001** Desde el menú se responde quién era quién en un evento concreto, sin consultar el estado actual.
- **SC-002** Ningún evento sin identidad muestra funcionario, cargo o autoridad.
