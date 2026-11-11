# PROC-10 · Garantías y cauciones (GOV-PROC-013)

**Autorización:** mandato de la dueña «KONTROL — PROGRAMMER 1 · PROC-10 · GOV-PROC-013 · GARANTÍAS Y CAUCIONES», 2026-11-10
(Constitución P2). **Fuentes:** `FUENTES.md`. **Decisiones de diseño:** `DECISIONES.md` (PDD-PROC10-01 a 23).

## Qué podrá hacer el usuario que antes no podía

En la ficha del expediente, sección «Garantías y cauciones», la Unidad Contratante:
1. Registra lo que exige el pliego o las condiciones (requisito): tipo, regla legal, porcentaje o monto fijo, vigencia mínima,
   fundamento y documento.
2. Registra cada garantía o caución recibida: sujeto (oferente o adjudicatario), emisor del catálogo, referencia, monto, moneda,
   fechas, documento firmado.
3. Ve si es suficiente, insuficiente o no evaluable (y qué dato falta), su vigencia, los días restantes y si está por vencer o vencida.
4. La renueva o, si la regla lo permite, la sustituye, sin perder el instrumento anterior.
5. Con un acto DOC-02 del contratante, la libera o la ejecuta. Ve el historial completo y la cronología del expediente.

No crea contrato (CNT-01), no inventa montos base y no simula retenciones ni pagos.

## Historias

- **US1 (P0) Registrar y entender.** Como Unidad Contratante registro requisitos y garantías y veo de inmediato cuántas hay requeridas,
  registradas, suficientes, por vencer, vencidas, liberadas y ejecutadas, sin depender de colores.
- **US2 (P0) Renovar y sustituir.** Renuevo una garantía (prórroga de oferta incluida) o la sustituyo cuando la regla lo permite;
  la historia anterior sigue visible.
- **US3 (P0) Liberar y ejecutar.** Con un acto competente libero o ejecuto una garantía, con motivo, soporte y, al ejecutar, monto.

## Requisitos

- **FR-001 Reglas versionadas.** Catálogo único de reglas con tipo, fuente, Gaceta, vigencia, etapa, forma de cálculo, base, porcentaje
  mínimo y máximo, moneda exigida, emisores admitidos, sustitución, coexistencia, retención alternativa y condiciones de liberación y
  ejecución. Solo se usan reglas vigentes a la fecha de negocio.
- **FR-002 Emisor.** Catálogo del ente: tipo (BANCO, ASEGURADORA, SOCIEDAD_GARANTIAS_RECIPROCAS, OTRO), nombre y RIF únicos en el ente;
  BANCO se enlaza a un banco activo del catálogo de TRE-01.
- **FR-003 Requisito.** Regla vigente; PORCENTAJE dentro del rango de la regla, o MONTO_FIJO mayor que cero con moneda (VES si la regla
  la exige); vigencia mínima opcional; fundamento; documento del expediente. OTRA exige nombre. Inmutable. Referencia REQ-nn.
- **FR-004 Registro.** Requisito del expediente; sujeto válido para la etapa (mantenimiento: oferta recibida; los demás: la oferta de la
  decisión vigente ADJUDICADA); emisor activo del ente; referencia; monto > 0; moneda; fecha de emisión ≤ vigente hasta; vigente desde ≤
  vigente hasta; documento. Sin segunda garantía activa para el mismo requisito y sujeto salvo coexistencia; sin duplicar emisor y
  referencia entre registradas. Referencia GAR-nn.
- **FR-005 Suficiencia.** Calculada al leer, por criterios (documento, emisor, moneda, monto, vigencia mínima, vigencia a la fecha):
  SUFICIENTE, INSUFICIENTE o NO_EVALUABLE con el dato faltante. Nunca SUFICIENTE sin poder evaluar el monto.
- **FR-006 Vigencia.** Desde, hasta, días restantes, y estado derivado FUTURA, VIGENTE, POR_VENCER (≤ 15 días) o VENCIDA según el reloj
  institucional.
- **FR-007 Renovación.** Solo de una garantía REGISTRADA: nuevo instrumento encadenado, mismo requisito, tipo, sujeto y emisor; vigente
  hasta posterior a la anterior; documento nuevo; motivo. La anterior queda RENOVADA, intacta.
- **FR-008 Sustitución.** Solo si la regla la permite: nuevo instrumento (emisor y monto pueden cambiar), motivo y documento. La anterior
  queda SUSTITUIDA.
- **FR-009 Liberación.** De una REGISTRADA: acto DOC-02 válido, motivo, fecha, documento opcional; precondición VERIFICADA o
  SOPORTADA_POR_ACTO. Queda LIBERADA.
- **FR-010 Ejecución.** De una REGISTRADA: acto DOC-02 válido, motivo, monto ejecutado (0 < monto ≤ monto del instrumento, misma
  moneda), documento opcional. Queda EJECUTADA. Una sola vez.
- **FR-011 Historia.** Toda actuación es una fila inmutable con fecha, actor, motivo, documento, acto y monto cuando corresponda. Nada se
  borra ni se reescribe.
- **FR-012 Permisos y seguridad.** `gobierno_garantias` view, manage, release (MFA), execute (MFA). Aislamiento por ente en lectura y
  escritura, documentos, emisores, actos y ofertas. SoD configurable de CTL-01. Identidad de ORG-06 al actuar con un acto.
- **FR-013 Concurrencia.** If-Match del expediente; renovar, sustituir, liberar y ejecutar se excluyen entre sí sobre el mismo instrumento.
- **FR-014 Auditoría y cronología.** 7 eventos CTL-02; clase GARANTIA en la cronología del expediente.
- **FR-015 Interfaz.** Sección «Garantías y cauciones» en la ficha: resumen textual, requisitos, emisores, garantías con suficiencia y
  vigencia, formularios de registro, renovación, sustitución, liberación y ejecución con confirmación en la misma pantalla, historial.
  Sin UUID visibles. 1280, 390 y 320 px; Axe sin violaciones serias o críticas.

## Fuera de alcance

Contrato y orden contractual (CNT-01), pliego y prórroga de la oferta (PROC-04), retenciones y pagos, alertas enviadas, reporte formal
(`REPORT_GATE_PROC10 = NOT_APPLICABLE`), retiro de requisitos.

## Criterios de aceptación

- SC-001 La dueña registra un requisito de mantenimiento con monto fijo y una garantía, ve INSUFICIENTE por vigencia, la renueva y ve
  SUFICIENTE con la garantía anterior en el historial (E2E).
- SC-002 Una garantía de fiel cumplimiento del adjudicatario se muestra NO_EVALUABLE nombrando el monto del contrato (E2E).
- SC-003 Liberar con acto y MFA deja la garantía LIBERADA, visible en historial, cronología y auditoría (E2E).
- SC-004 Ejecutar, sustituir, negativas materiales y concurrencia, verificados en PostgreSQL.
