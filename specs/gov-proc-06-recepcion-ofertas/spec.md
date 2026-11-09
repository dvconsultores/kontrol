# PROC-06 · Recepción de ofertas (GOV-PROC-007)

**Autorización**: mandato de la dueña «PROCUREMENT-RELEASE-03», 2026-11-09 (Constitución P2). **Fuentes:** `evidence/FUENTES.md`.

## Qué podrá hacer el usuario que antes no podía

Desde el expediente, registrar cada oferta recibida con su oferente declarado, canal, fecha y hora, quién la recibió, sus documentos fijados y, cuando aplique, su sello hasta la apertura; concluir la recepción y ver que queda pendiente de apertura. Nadie puede leer el contenido sellado, ni siquiera por la descarga directa.

## Fuera de alcance

Abrir, calificar y evaluar (PROC-07, GOV-PROC-008/009). Validar RNC/SNC y maestro de oferentes (PROC-05, bloqueado). Levantar el sello: llega con la apertura.

## Requisitos

- **FR-001** Recepción desde la sección «Ofertas» de la ficha, con referencia correlativa por expediente.
- **FR-002** Oferente con identidad **declarada** (nombre, documento, representante), rotulada como no validada en RNC/SNC.
- **FR-003** Canal: acto público (LCP art. 92), unidad contratante (LCP art. 99), medios electrónicos (LCP arts. 104-105). Tipo de sobre: único, calificación u oferta (LCP art. 78).
- **FR-004** Sello temporal: fecha y hora efectiva declarada, no futura, más fecha de registro del sistema; ninguna se edita.
- **FR-005** Documentos: fija la versión recibida y su huella, sin copiar archivos. Un sobre físico cerrado no tiene archivo: se registra su estado.
- **FR-006** Integridad comprobada contra el almacenamiento, sin entregar contenido.
- **FR-007** Confidencialidad: el sello se aplica en la capa documental, y cubre metadatos y bytes en toda ruta normal. Obligatoria en concursos (LCP art. 92) y si la modalidad no está declarada; en consulta de precios y contratación directa decide la unidad con motivo.
- **FR-008** Concursos: exige comisión vinculada o declaración de que no interviene (LCP art. 92, RLCP art. 33).
- **FR-009** Concluir la recepción impide admitir más ofertas (LCP art. 92).
- **FR-010** Cada recepción entra en la cronología, sin contenido; y el expediente muestra «Pendiente de apertura».
- **FR-011** Capacidad `gobierno_ofertas`: `view`, `receive`. No se concede apertura ni evaluación. SoD de CTL-01 y auditoría de CTL-02.
- **FR-012** Sin duplicar: un oferente y tipo de sobre por expediente; otro ente 404.

## Criterios de éxito

- **SC-001** Flujo de §25 del mandato en navegador real.
- **SC-002** Un usuario con todos los permisos documentales no obtiene metadatos ni bytes de un documento sellado por ninguna ruta de `/documentos`.
