# CNT-09 · Fuentes leídas (2026-11-16)

| Código | Instrumento | Uso en CNT-09 |
|---|---|---|
| N11 | Decreto-Ley de Contrataciones Públicas (G.O. 6.154 Ext.), texto extraído (sha256 `16293cac197c…`, fuera del repositorio) | Art. 137: los responsables designados (supervisor) deben «verificar el cumplimiento de las obligaciones contraídas», «informar por escrito el avance» y «proponer los correctivos necesarios». La alerta sirve a esa verificación, pero **no la sustituye**: ni conforma, ni recibe, ni decide. |
| N20 | Normas Generales de Control Interno | Escaneo sin capa de texto. Solo aporta el principio general de control oportuno; no fija plazos ni preavisos. |
| PROC-10 | `garantias_reglas.DIAS_POR_VENCER = 15` (PDD-PROC10-07, días naturales) y `service_garantias._vigencia` | Única autoridad para «garantía por vencer» y «vencida». CNT-09 la importa y no duplica la cifra. |
| CNT-01 + CNT-02 | `service_contratos_ejecucion.terminos_efectivos` | Fecha de fin efectiva del contrato, con la prórroga formalizada vigente. |
| CNT-03 | Hitos (`fecha_prevista`, estado, `_cumplidos`) y entregables (`fecha_vencimiento`, estado, `_conforme`); acto CIERRE | Qué sigue pendiente. La conformidad real manda: una entrega sin conformar no cumple. |
| Spec 047 | `crear_alerta`, `resolver_alerta_de_sistema`, `Alert`, `/alerts`, `catalogo.ORIGENES` y el planificador | El único motor de alertas. |

## Lo que no hay y no se inventa

- **Calendario hábil institucional.** El plazo de firma de 8 días hábiles de CNT-01 queda en `DEFERRED_BY_CALENDAR_AUTHORITY`.
- **Preavisos legales** para contratos, hitos y entregables. Solo se usan los que configure la institución; sin configuración, solo hay alertas de «vence hoy» y «vencido».
