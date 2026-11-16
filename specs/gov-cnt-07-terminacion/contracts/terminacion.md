# Contrato de datos · CNT-07

**Convenciones:**
- Los importes son cadenas con 2 decimales.
- Las fechas jurídicas son ISO `YYYY-MM-DD`.
- Los instantes son ISO-8601 con hora (los fixtures de Vitest usan esta forma real).
- Una clave sin dato vale `null`.

## Modelo · `gov_contract_terminations`

| Columna | Tipo | Regla |
|---|---|---|
| `id`, `company_id`, `contract_id`, `file_id` | String(36) | FK; `file_id` = `contrato.file_id` |
| `estado` | String(12) | BORRADOR o FORMALIZADA |
| `figura` | String(32) | RESCISION_NO_IMPUTABLE, RESOLUCION_MUTUO_ACUERDO o RESCISION_IMPUTABLE |
| `causal` | String(32) | Catálogo de C07-03 |
| `causal_referencia` | String(200), null | Obligatoria con CLAUSULA_CONTRATO |
| `hechos`, `fundamento` | String(4000) | 20–4000 caracteres al formalizar; en BORRADOR pueden ser parciales |
| `act_id` | FK `gov_acts`, null | Acto decisorio |
| `apertura_act_id` | FK `gov_acts`, null | Solo en IMPUTABLE |
| `document_id`, `document_version_id`, `documento_sha256`, `documento_titulo` | null | Documento del acuerdo, solo en MUTUO_ACUERDO |
| `conclusion_alcance` | String(1000), null | Junto con `conclusion_hasta`: ambos o ninguno |
| `conclusion_hasta` | Date, null | — |
| `fecha_acto`, `fecha_eficacia` | Date, null | Se copian del acto al formalizar |
| `codigo` | String(20), null | `{código del contrato}/TER`, al formalizar (una sola extinción por contrato) |
| `snapshot` | JSON, null | — |
| `huella` | String(64), null | — |
| `formalizado_en` | DateTime(tz), null | — |
| `formalizado_por` | String(36), null | — |

Además lleva `version`, `created_at`, `updated_at` y `created_by`.

**Índices únicos parciales** sobre `contract_id`: uno donde `estado='BORRADOR'` y otro donde `estado='FORMALIZADA'`.

**Trigger PG** `kontrol_gov_contract_termination_guard`:
- DELETE solo en BORRADOR;
- UPDATE prohibido si `OLD.estado='FORMALIZADA'`;
- TRUNCATE prohibido;
- `MESSAGE='GOV_CONTRACT_TERMINATION_IMMUTABLE'`.

## Rutas (prefijo `/gobierno/contratos`)

| Método y ruta | Permiso | Resultado |
|---|---|---|
| GET `/{id}/terminacion` | `gobierno_contratos:view` | VISTA |
| POST `/{id}/terminacion` | `terminate` | Crea el BORRADOR (cuerpo BORRADOR_IN) → VISTA, 201 |
| PATCH `/{id}/terminacion/borrador` | `terminate` | `If-Match` → VISTA |
| DELETE `/{id}/terminacion/borrador` | `terminate` | `If-Match` → 204 |
| POST `/{id}/terminacion/formalizar` | `terminate` | `If-Match` → VISTA |
| GET `/terminaciones/reporte.csv?figura=&desde=&hasta=` | `view` | CSV |

Todas las rutas llevan además `require_module("gobierno")`; las de escritura, también `require_write_allowed`.

```json
BORRADOR_IN = {"figura","causal","causal_referencia","hechos","fundamento","act_id","apertura_act_id",
               "document_id","document_version_id","conclusion_alcance","conclusion_hasta"}
```

Todas las claves son opcionales en el PATCH; en el POST, `figura` es obligatoria.

```json
VISTA = {
 "contrato": {"id","codigo","contratista": {"nombre","documento"},"objeto","tipo_contratacion": "OBRAS"|"BIENES_SERVICIOS",
              "fecha_formalizacion","enlace"},
 "situacion": SITUACION,
 "catalogo": {"figuras": [{"codigo","etiqueta","fuente","causales": [{"codigo","etiqueta","fuente"}]}]},
 "borrador": TERMINACION | null,
 "formalizada": TERMINACION | null,
 "requisitos": [{"codigo","cumplido": bool,"mensaje"}],
 "opciones": {"actos": [{"id","etiqueta","estado","fecha","fecha_eficacia","emisor_cargo"}],
             "documentos": [{"id","titulo","version"}]},
 "notificaciones": [{"id","destinatario","identificacion","estado","fecha_notificacion","es_contratista": bool,"enlace"}],
 "consecuencias": CONSECUENCIAS,
 "garantias": [{"referencia","tipo_etiqueta","emisor","monto","moneda","estado","estado_etiqueta","vigente": bool,"enlace"}],
 "obligaciones": [{"codigo","mensaje","fuente"}],
 "permisos": {"terminar": bool}
}
```

**SITUACION**

```json
SITUACION = {"estado": "VIGENTE"|"EXTINGUIDO","estado_etiqueta","figura","figura_etiqueta","fecha_eficacia",
             "fecha_limite_ejecucion","cumplimiento_cnt03": bool,
             "alerta_acto_base": null | {"estado": "REVOCADO"|"NULO","mensaje","enlace"}}
```

**TERMINACION**

```json
TERMINACION = {"id","codigo","estado","version","figura","figura_etiqueta","causal","causal_etiqueta","causal_referencia",
               "hechos","fundamento","acto": ACTO|null,"apertura": ACTO|null,
               "documento": {"id","version_id","titulo","sha256"}|null,
               "conclusion": {"alcance","hasta"}|null,
               "fecha_acto","fecha_eficacia","formalizado_en","formalizado_por","huella"}
ACTO = {"id","etiqueta","tipo","numero","fecha","estado","fecha_eficacia","emisor_cargo","funcionario","enlace"}
```

**CONSECUENCIAS** (la fecha de corte es la de eficacia si está FORMALIZADA, y hoy si no)

```json
CONSECUENCIAS = {"fecha_corte","moneda","monto_vigente","valuado_conformado","valuado_presentado",
                 "saldo_no_ejecutado","saldo_por_valuar_cnt03","facturado_conforme",
                 "recepciones": {"total","definitiva": bool},"estado_ejecucion","estado_ejecucion_etiqueta",
                 "hitos": {"total","cumplidos"},
                 "compromisos": [{"codigo","estado","total","moneda","enlace"}],
                 "indemnizacion": {"regla","estado": "CONSECUENCIA_PENDIENTE_CNT06","mensaje"},
                 "efectos": "Esta actuación no crea pagos, causado, penalidades ni anulaciones presupuestarias."}
```

Reglas de las cifras:
- `saldo_no_ejecutado` = `monto_vigente` − `valuado_conformado`, donde `monto_vigente` sale de `terminos_efectivos(fecha_corte)`.
- Los valores de ejecución salen de `service_contratos_ejecucion.ejecucion()["resumen"]` sin recalcular.
- `indemnizacion.regla`:
  - NO_IMPUTABLE: «RLCP art. 191: precio de lo ejecutado, materiales e indemnización del 10 % al 5 % de lo no ejecutado según el avance.»
  - MUTUO_ACUERDO: «LCP art. 154: no procede indemnización alguna.» Con `estado` = `"NO_PROCEDE"`.
  - IMPUTABLE: «RLCP art. 194: indemnización a favor del contratante en la misma forma y cuantía del art. 191; puede deducirse o ejecutarse la garantía en PROC-10.»
  - Sin figura: `null`.

**Requisitos.** Códigos fijos en este orden:

| Código | Cuándo aplica |
|---|---|
| `FIGURA` | Siempre |
| `CAUSAL` | Siempre |
| `MOTIVACION` | Siempre |
| `ACTO_EFICAZ` | Siempre |
| `AUTORIDAD` | Siempre |
| `NOTIFICACION_CONTRATISTA` | Siempre |
| `NOTIFICACION_GARANTES` | Solo en rescisiones con garantías vigentes |
| `APERTURA` | Solo en IMPUTABLE |
| `DOCUMENTO_ACUERDO` | Solo en MUTUO_ACUERDO |
| `CONCLUSION` | Solo si hay conclusión autorizada |
| `SIN_HECHOS_POSTERIORES` | Siempre |

**Obligaciones:**
- Toda rescisión: `EVALUACION_DESEMPENO_SNC` (LCP 51).
- IMPUTABLE, además: `PUBLICACION_SNC` (LCP 8).
- Si hay compromisos VIGENTE: `REVISAR_COMPROMISO_BUD08`.
- Si hay garantías vigentes: `REVISAR_GARANTIAS_PROC10`.

**Etiquetas:**

| Tipo | Valor | Etiqueta |
|---|---|---|
| Figura | RESCISION_NO_IMPUTABLE | Rescisión unilateral por causa no imputable al contratista |
| Figura | RESOLUCION_MUTUO_ACUERDO | Resolución por mutuo acuerdo |
| Figura | RESCISION_IMPUTABLE | Rescisión por causa imputable al contratista |
| Estado | VIGENTE | Vigente |
| Estado | EXTINGUIDO | Extinguido |

## Errores

| Código | HTTP |
|---|---|
| `GOV_CONTRACT_TERMINATION_NOT_FORMALIZED` | 409 |
| `GOV_CONTRACT_TERMINATION_ALREADY_EXISTS` | 409 |
| `GOV_CONTRACT_TERMINATION_DRAFT_EXISTS` | 409 |
| `GOV_CONTRACT_TERMINATION_NOT_FOUND` | 404 (no hay borrador) |
| `GOV_CONTRACT_TERMINATION_IF_MATCH_REQUIRED` | 428 |
| `GOV_CONTRACT_TERMINATION_STALE` | 409, con `details.version_actual` |
| `GOV_CONTRACT_TERMINATION_INVALID` | 422; `details.campo` y `details.motivo` (uno de los requisitos) |
| `GOV_CONTRACT_TERMINATION_LATER_FACTS` | 409; `details.hechos` = `[{proceso, tipo, fecha}]` |
| `GOV_CONTRACT_TERMINATED` | 409; `details` = `{fecha_limite, figura}`, en las guardas de CNT-02, CNT-03 y CNT-04 |

## CSV

Columnas, en este orden:

```
codigo_terminacion, codigo_contrato, contratista, documento_contratista, figura, causal, causal_referencia,
fecha_acto, fecha_eficacia, acto, conclusion_hasta, monto_vigente, valuado_conformado, saldo_no_ejecutado,
moneda, formalizado_en
```

- Los valores de ejecución salen del `snapshot`.
- Solo filas FORMALIZADA de la empresa, ordenadas por `fecha_eficacia` descendente.
- Nombre del fichero: `terminaciones-contractuales.csv`.
