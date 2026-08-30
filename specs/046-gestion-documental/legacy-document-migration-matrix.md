# MATRIZ DE MIGRACIÓN DOCUMENTAL LEGADA — SPEC 046

**Obligatoria (§110, §155).** No se declara «sin legacy» sin búsqueda
exhaustiva: se buscó y **sí hay** referencias documentales previas.

Fecha: 2026-08-30. Auditoría del modelo completo, 69 columnas con semántica de
referencia revisadas una a una.

---

## 1. Hallazgo de partida

| Comprobación | Resultado |
|---|---|
| Columnas con semántica de referencia en el modelo | **69** |
| De ellas, con semántica **documental real** | **13** |
| Con clave foránea a un archivo | **0** |
| `file_metadata` | Existe con `sha256`, `storage_key`, `mime_type`, `size` |
| Consumidores de `file_metadata` | **0** — solo aparece en `models.py` |
| Endpoints de subida (`UploadFile`) | **0** |
| Capacidad de subida en el frontend | **0** — sin `type="file"`, sin `FormData` |
| Único mecanismo real de archivo | `reporting`: exportaciones generadas por el servidor |

`python-multipart==0.0.31` **ya está** en `requirements.txt` y el volumen
`kontrol-storage:/data/storage` **ya existe** en `compose.yaml`: la
infraestructura está preparada y nunca se usó.

> `file_metadata` es un maestro *write-only* más: la tabla existe, tiene los
> campos correctos, y **nada la escribe ni la lee**. Es el mismo patrón que el
> GAP Analysis bautizó con las Sucursales, y que las Specs 008 y 011 ya
> encontraron en `locations` y en `presentations`.

---

## 2. Las cuatro clases (§111)

Aplicadas a cada columna documental legada:

### A · `VALID_MANAGED_FILE`
Existe un binario administrado por KONTROL, localizable y verificable.

### B · `EXTERNAL_REFERENCE`
La columna guarda una referencia externa (número, código, URL de tercero), no un
archivo de KONTROL. **No es candidata a migración**: se marca como tal.

### C · `MISSING_FILE`
La base afirma que hay archivo y el binario no está. **No se inventa**: se
registra `MISSING_LEGACY_FILE` (§114).

### D · `UNVERIFIED_LEGACY`
Texto de forma indeterminada: puede ser nombre, número o ruta. Requiere revisión
antes de tocarse.

### E · `MIGRATION_BLOCKER`
Migrarlo destruiría o falsearía evidencia. Detiene la migración.

---

## 3. Matriz por columna

| Tabla | Campo | Tipo | Storage actual | Referencia existente | Clase esperada | Migración | Riesgo |
|---|---|---|---|---|---|---|---|
| `file_metadata` | *(tabla entera)* | — | `storage_key`, sin binario escrito | Ninguna | **Vacía de uso** | **Evoluciona** a `stored_files`; sin backfill (ADR: `SAFE_MIGRATION`) | Bajo |
| `regulatory.official_documents` | `file_ref` + `hash` | `String(255)` | Ninguno verificable | Ninguna FK | `UNVERIFIED_LEGACY` | Conservar el texto; crear documento solo si hay binario | **Alto** — es evidencia regulatoria |
| `regulatory.permit_instances` | `file_ref` | `String(255)` | Ninguno | Ninguna FK | `UNVERIFIED_LEGACY` | Ídem | **Alto** |
| `regulatory.official_registrations` | `file_ref` | `String(255)` | Ninguno | Ninguna FK | `UNVERIFIED_LEGACY` | Ídem | Medio |
| `regulatory.transport_vehicles` | `documents` | `String` | Ninguno | Texto libre | `UNVERIFIED_LEGACY` | Conservar; 035 decidirá su estructura | Medio |
| `regulatory.transport_drivers` | `documents` | `String` | Ninguno | Texto libre | `UNVERIFIED_LEGACY` | Ídem | Medio |
| `regulatory.regulatory_profiles` | `required_documents` | `String` | — | Configuración, no archivo | `EXTERNAL_REFERENCE` | **Ninguna**: es una lista de requisitos, no un archivo | Bajo |
| `homologation.homologation_records` | `evidence_sha256` | `String(64)` | **Ninguno** | Hash **sin archivo** | **`MIGRATION_BLOCKER` potencial** | Ver §4 | **Crítico** |
| `licensing.license_renewal_requests` | `payment_proof_ref` | `String` | Ninguno | Texto | `UNVERIFIED_LEGACY` | Conservar; 040 vinculará el comprobante real | Medio |
| `master_data.party_bank_accounts` | `evidence` | `String` | Ninguno | Texto | `UNVERIFIED_LEGACY` | Conservar | Bajo |
| `inventory.inventory_adjustments` | `evidence_ref` | `String` | Ninguno | Texto | `UNVERIFIED_LEGACY` | Conservar | Bajo |
| `fiscal.legal_sources` | `file_id` | `String` | Ninguno | Nombre sugerente, **sin FK** | `UNVERIFIED_LEGACY` | Conservar; puede referirse a una fuente externa | Medio |
| `reporting.report_exports` | `file_ref` | `String(255)` | **`/data/storage/exports/`** | Nombre generado por el servidor | **`VALID_MANAGED_FILE`** | **Ninguna en el MVP** — ver §5 | Bajo |
| `reporting.report_jobs` | `result_ref` | `String` | Ídem | Ídem | `VALID_MANAGED_FILE` | Ninguna en el MVP | Bajo |

### Recuento esperado

| Clase | Columnas |
|---|---:|
| `VALID_MANAGED_FILE` | 2 (exportaciones) |
| `EXTERNAL_REFERENCE` | 1 |
| `UNVERIFIED_LEGACY` | **9** |
| `MIGRATION_BLOCKER` potencial | 1 |
| Tabla que evoluciona sin backfill | 1 |

---

## 4. El caso crítico: un hash sin archivo

`homologation_records.evidence_sha256` guarda el SHA-256 de una evidencia cuyo
binario **no está en ninguna parte**. Es la situación exacta que R-D0-08-4
declara inadmisible: *«un adjunto sin hash verificable no es evidencia»* — y
aquí ocurre lo simétrico y peor, **un hash sin adjunto**.

> **R-046-5.** Un hash histórico sin binario **no se convierte en documento**.
> Crear un `Document` para él afirmaría que existe una evidencia que nadie puede
> abrir. Se conserva la columna, se marca `LEGACY_HASH_WITHOUT_FILE` y se
> reporta. Si en el futuro aparece el binario, se verifica contra ese hash antes
> de admitirlo: entonces sí es evidencia.

Que esto sea `MIGRATION_BLOCKER` **o** una incidencia registrada depende de si
esos registros de homologación son actos formales vigentes. Es una de las tres
cuestiones escaladas (`ESC-046-02`).

---

## 5. Por qué las exportaciones no se migran en el MVP

`reporting` ya tiene un mecanismo funcional, auditado y con descarga autorizada.
Absorberlo dentro de 046 en el MVP sería **scope creep sobre una Spec ajena
(050)** y añadiría riesgo sin resolver ninguna de las ocho Specs bloqueadas.

Se declara la convergencia como **`FUTURE_CAPABILITY`** con contrato: cuando 050
lo requiera, una exportación podrá materializarse como `Document` sin cambiar su
API. 046 **no** absorbe 050 ahora.

---

## 6. Estrategia de migración

Consecuencia de la clase, no de la conveniencia:

1. **`file_metadata` evoluciona** a `stored_files`. Está vacía de uso real: se
   extiende sin backfill, como el ADR anticipó (`SAFE_MIGRATION`).
2. **Las 9 columnas `UNVERIFIED_LEGACY` no se tocan.** Se conservan tal cual y se
   marcan. No se crea un `Document` por cada texto: eso inventaría archivos.
3. **Si aparece un binario localizable** (§113), la importación calcula su hash,
   preserva el original byte a byte, crea la metadata y **registra la
   procedencia**. Nunca mueve destructivamente sin verificar (§115).
4. **Si la base afirma archivo y no está** (§114), se registra
   `MISSING_LEGACY_FILE`. No se declara migración completa sin evidencia.
5. **El hash sin archivo** (§4) no genera documento.

## 7. Qué se prueba

Los cinco casos de `test-plan.md` §8, con fixture que incluye: referencia válida,
archivo faltante, nombre inseguro, MIME no soportado y hash sin binario (§125).
