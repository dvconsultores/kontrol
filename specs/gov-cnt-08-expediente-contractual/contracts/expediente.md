# Contrato de datos · CNT-08

Los importes son cadenas con 2 decimales (`_t`), las fechas son ISO `YYYY-MM-DD` y los instantes ISO-8601 en UTC. Una clave sin dato vale `null`, nunca se omite.

## Lista · GET /gobierno/expedientes-contractuales

**Query:**

| Parámetro | Tipo | Filtro |
|---|---|---|
| `codigo` | ≤40 | ilike sobre `codigo` |
| `expediente` | ≤40 | ilike sobre `expediente_numero` |
| `contratista` | ≤100 | ilike sobre el nombre o el documento |
| `tipo` | tipo de instrumento | Exacto |
| `vigencia` | POR_INICIAR, EN_PLAZO o VENCIDO | Se aplica después de proyectar |
| `supervisor` | ≤100 | ilike sobre `funcionario_nombre` de la designación VIGENTE con `desde <= hoy` |
| `desde`, `hasta` | fecha | Sobre `fecha_formalizacion` |
| `limit` | 1–100, por defecto 25 | — |
| `offset` | ≥0 | — |

Solo se listan contratos FORMALIZADO de la empresa, ordenados por `fecha_formalizacion` y después `codigo`, ambos descendentes.

```json
{"items": [ITEM], "total": 0, "limit": 25, "offset": 0}
ITEM = {
  "id": "…", "codigo": "CT-2026-0001", "tipo": "CONTRATO", "tipo_etiqueta": "Contrato",
  "contratista": {"nombre": "…", "documento": "…"}, "objeto": "…",
  "monto_original": "50000.00", "monto_vigente": "60000.00", "moneda": "USD",
  "fecha_inicio": "2026-01-01", "fecha_fin_original": "2026-06-30", "fecha_fin_vigente": "2026-07-30",
  "vigencia": "EN_PLAZO", "vigencia_etiqueta": "En plazo",
  "supervisor": {"nombre": "…", "cargo": "…"} | null,
  "expediente": {"id": "…", "numero": "…"},
  "fecha_formalizacion": "2026-01-01", "modificaciones": 2,
  "ultimo_paquete": {"codigo": "EC-2026-0001", "generado_en": "…", "verificacion": "VALIDO" | null} | null,
  "ultima_actuacion": {"fecha": "2026-02-01", "titulo": "…", "proceso": "CNT-02"} | null
}
```

`ultima_actuacion` es la actuación más reciente, por fecha y después por fecha de registro, entre:
- la formalización CNT-01;
- las modificaciones formalizadas CNT-02 (por `fecha_instrumento`);
- las designaciones CNT-04 con `desde <= hoy`;
- los paquetes CNT-08.

Si hay filtro `vigencia`, se proyectan todos los contratos que pasan los filtros SQL y después se pagina.

## Expediente · GET /gobierno/contratos/{id}/expediente

```json
{
 "contrato": {"id","codigo","tipo","tipo_etiqueta","estado"},
 "resumen": {
   "codigo","tipo_etiqueta",
   "contratista": {"nombre","documento","representante"},
   "objeto","monto_original","monto_vigente","moneda",
   "fecha_inicio","fecha_fin_original","fecha_fin_vigente","vigencia","vigencia_etiqueta",
   "adjudicacion_referencia","expediente_numero",
   "supervisor_actual": {"referencia","nombre","cargo","unidad"} | null,
   "cobertura": {"total_asignado","completa","moneda"},
   "ejecucion": {"estado": "SOURCE_PROCESS_NOT_AVAILABLE", "mensaje": "…"}
 },
 "origen": {
   "expediente": {"id","numero","objeto","tipo_contratacion","modalidad","unidad","estado","fecha_inicio","enlace"},
   "oferta": {"id","referencia","oferente","documento","recibida_en"}
 },
 "adjudicacion": {"id","referencia","fecha","resultado","motivacion","vigente",
                   "acto": {"id","etiqueta","enlace"} , "cargo": "…" | null, "enlace"},
 "presupuesto": {
   "certificados": [{"id","codigo","fecha","monto","moneda","estado","concepto",
                     "asignado_contrato","asignado_modificaciones","comprobante_sha256","enlace"}],
   "compromisos": [{"id","codigo","fecha","estado","moneda","total","concepto",
                    "lineas": [{"certificado_codigo","monto"}],"comprobante_sha256","enlace"}],
   "control": {…control_compromisos de CNT-01…},
   "efectos": "Este expediente no crea certificaciones ni compromisos ni cambia disponibilidades."
 },
 "instrumento": {
   "original": {"monto","moneda","fecha_inicio","fecha_fin","referencia_instrumento","fecha_formalizacion",
                "firmante": {"cargo","funcionario","conversion"},
                "documento": {"id","titulo","version","sha256"} | null, "huella","enlace"},
   "vigente": {…historia(...)["vigente"] de CNT-02…},
   "fecha_consulta": "2026-…"
 },
 "garantias": [{"instrumento_id","referencia","tipo_etiqueta","emisor","monto","moneda",
                "vigente_desde","vigente_hasta","estado","estado_etiqueta",
                "documento": {"id","version","sha256"},
                "eventos": [{"accion","accion_etiqueta","fecha","motivo"}], "enlace"}],
 "modificaciones": {"cantidad": 0, "historial": [{…nodo de CNT-02…, "enlace"}]},
 "supervision": {"vigente","programada","historia"},
 "ejecucion": {"proceso": "CNT-03", "estado": "SOURCE_PROCESS_NOT_AVAILABLE", "mensaje": "…"},
 "fuentes_futuras": [{"proceso","titulo","estado","mensaje"}],
 "actos": [{"id","etiqueta","tipo","numero","fecha","estado","asunto","rol","enlace"}],
 "documentos": [DOC],
 "cronologia_total": 0,
 "permisos": {"auditoria": true, "ver_paquetes": true, "generar_paquete": true}
}
DOC = {"clave","tipo","tipo_etiqueta","titulo","proceso","referencia","version","sha256","fecha",
       "estado": "DISPONIBLE" | "RESERVADO","sellado": bool,"document_id","version_id","descarga","enlace"}
```

`sellado` es True cuando el documento del gestor tiene un sello activo (`documents.service.documento_sellado`). En ese caso `descarga` es null (D08-09): la autoridad documental no lo entrega y el paquete lo declara EXCLUIDO con motivo SELLADO.

```json
```

### Valores fijos

- **Enlaces:**

  | Elemento | Enlace |
  |---|---|
  | Expediente PROC-03, adjudicación y garantías | `/gobierno/contrataciones/expedientes/{file_id}` |
  | CDP y compromisos | `/gobierno/presupuesto/ejercicios/{year_id}` |
  | Contrato y supervisión | `/gobierno/contratos/{id}` |
  | Modificación | `/gobierno/contratos/{id}/modificaciones/{mid}` |
  | Acto | `/gobierno/actos/{acto_id}` |
  | Documento del gestor | `/documentos/{document_id}` |

- **Descargas:**

  | Origen | Ruta |
  |---|---|
  | Documento del gestor | `/documentos/{document_id}/versiones/{version_id}/descargar` |
  | CDP | `/gobierno/presupuesto/ejercicios/{year_id}/certificaciones/{id}/documento` |
  | Compromiso | `/gobierno/presupuesto/ejercicios/{year_id}/compromisos/{id}/documento` |

- **`rol` de un acto:** ADJUDICACION, DESIGNACION_SUPERVISOR o FOLIO.
- **`tipo_etiqueta` de un documento:**

  | Tipo | Etiqueta |
  |---|---|
  | INSTRUMENTO | Instrumento contractual |
  | MODIFICACION | Modificación contractual |
  | GARANTIA | Garantía |
  | FOLIO | Folio del expediente de contratación |
  | ACTO | Acto administrativo |
  | COMPROBANTE_CDP | Comprobante de certificación |
  | COMPROBANTE_COMPROMISO | Comprobante de compromiso |

- **`fuentes_futuras`:** su `estado` es SOURCE_PROCESS_NOT_AVAILABLE.

  | Proceso | Título |
  |---|---|
  | CNT-03 | Ejecución: hitos, entregables y valuaciones |
  | CNT-05 | Bloqueo de pagos por encima del monto contractual |
  | CNT-06 | Penalidades y retenciones |
  | CNT-07 | Terminación, resolución o rescisión |
  | TRE-04 | Pagos |

  El `mensaje` es «El módulo aún no está disponible: el expediente no puede afirmar si hubo actuaciones de este tipo.»
- **Permisos:** `permisos` sale de `authority.capabilities_in_company`.

## Cronología · GET …/expediente/cronologia

**Query:** `proceso` (uno de los procesos de R4), `desde` y `hasta` (sobre `fecha`), `limit` (1–200, por defecto 50) y `offset`.

```json
{"items": [EV], "total": 0, "limit": 50, "offset": 0,
 "procesos": ["PROC-03","PROC-10","BUD-06","BUD-08","CNT-01","CNT-02","CNT-04","CNT-08"]}
EV = {"orden","fecha","fecha_registro","fecha_documento","fecha_efectiva","tipo","tipo_etiqueta",
      "proceso","fuente_id","titulo","actor","autoridad","unidad","documentos": ["clave",…],"estado","enlace"}
```

## Auditoría · GET …/expediente/auditoria

**Query:** `limit` (1–200, por defecto 50) y `offset`.

```json
{"items": [{"id","fecha","proceso","proceso_nombre","accion","accion_etiqueta","entidad","usuario","enlace"}],
 "total": 0, "limit": 50, "offset": 0}
```

El `enlace` es `/gobierno/auditoria?evento={id}`.

## Integridad · GET …/expediente/integridad

```json
{"verificado_en": "…", "resumen": {"VERIFIED":0,"MISSING":0,"MISMATCH":0,"NOT_APPLICABLE":0},
 "documentos": [{"clave","titulo","tipo","sha256_registrado","resultado","detalle"}]}
```

## Paquetes

- **POST …/expediente/paquetes:** cuerpo `{"proposito": "…"}` → PAQUETE.
- **GET …/expediente/paquetes**, con `limit` (1–100, por defecto 20) y `offset` → `{"items": [PAQUETE], "total"}`.

```json
PAQUETE = {"id","codigo","numero_generacion","proposito","generado_en","generado_por","corte",
           "eventos","documentos_incluidos","documentos_excluidos","archivos","bytes",
           "huella_paquete","huella_manifiesto","nombre_archivo",
           "ultima_verificacion": {"resultado","verificado_en"} | null}
```

- **POST …/paquetes/verificar** (multipart, campo `archivo`):

```json
{"resultado","motivos": [{"codigo","ruta"}],
 "paquete": {"id","codigo","contrato_codigo"} | null,
 "huella_archivo","bytes_archivo","identico","verificacion_id"}
```
