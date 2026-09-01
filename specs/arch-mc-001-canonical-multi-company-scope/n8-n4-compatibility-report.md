# COMPATIBILIDAD DEL PREFLIGHT DE N4 — N8

## 1. El hallazgo

**El clasificador quedó ciego después de N7.**

`planes()` decide qué tablas hay que revisar excluyendo aquellas cuya
`company_id` ya tiene clave foránea. Antes de N7 eso valía para 17 tablas;
después vale para todas, así que devolvía **cero planes**.

Contra una instalación heredada —cuyo esquema no tiene esas claves— seguiría
mirando el modelo vigente y devolviendo cero. La herramienta que la Spec 052
necesita para decidir si una actualización es segura habría respondido «no hay
nada que revisar» a una base llena de filas que sí había que revisar.

Se registró como limitación al cerrar N7. En N8 dejó de ser aceptable, porque
N8 es la fase que promete conservar la capacidad de migración.

## 2. Por qué no se vio antes

Porque las dos pruebas que lo habrían detectado se estaban saltando. Ver
`n8-skipped-tests-audit.md`.

## 3. La corrección

`planes()` acepta ahora una conexión al destino y le pregunta a **su** catálogo
qué columnas de empresa carecen de clave foránea allí.

La división es deliberada:

| Qué | De dónde | Por qué |
|---|---|---|
| Qué entidad es de empresa | Modelos | Semántica del dominio: no cambia entre versiones |
| Por qué autoridad deriva | Modelos | Ídem |
| Si su propiedad ya está garantizada | **Catálogo del destino** | Eso sí cambia entre versiones |

`preflight.py` ya consultaba `information_schema` del destino y no hizo falta
tocarlo. El problema estaba solo en cómo se elegía el conjunto de trabajo.

## 4. Comprobación

Sobre el fixture hostil reconstruido, después de retirar las columnas
transitorias:

| Comprobación | Resultado |
|---|---|
| El preflight no escribe nada | PASS |
| Clasifica `MC-A` (determinista por intervalo) | PASS |
| Clasifica `MC-B` (derivable por almacén) | PASS |
| Clasifica `MC-C` (ambigua) | PASS |
| Clasifica `MC-E` (fiscal crítica) | PASS |
| Reconoce `OK` (ya correcta) | PASS |
| No rebaja de clase ninguna fila crítica | PASS |
| Repetible | PASS |

**23 pruebas**, todas ejecutándose de verdad.

## 5. Lo que N8 deja disponible para la Spec 052

Una herramienta que analiza el catálogo de la base que se le indique, con el
fixture hostil como artefacto reproducible para verificarla.

`MANDATORY_PER_INSTALLATION_PREFLIGHT` sigue siendo el contrato: toda
instalación existente pasa el preflight antes de actualizar, y no depende de que
el cliente crea tener una sola empresa. El preflight es lo que lo decide.
