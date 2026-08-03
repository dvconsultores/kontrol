# Paquete de revisión legal/contable — 001-fundacion (T-048)

| Campo | Valor |
|---|---|
| Fecha | 2026-08-04 |
| Revisores requeridos | Abogado tributario venezolano · Contador público · Equipo de homologación |
| Estado | PENDIENTE de revisión humana (no bloquea la fundación local; sí bloquea producción) |
| Ruta | `docs/evidence/legal-review-package.md` |

## Qué debe revisarse

1. **Matriz normativa** — `docs/governance/authority-matrix.md`
   - Confirmar vigencia y estado `LEGAL_VALIDATION_REQUIRED` de cada norma:
     COT, Ley IVA, Ley ISLR, Ley IGTF, Decreto 4.972, Providencias
     SNAT/2011/00071, 2018/0141, 2024/000102, 2024/000121, 2025/000054,
     2016/0004/0005, 2022/000013, 2025/000091, Decreto 1.808, SICA (DM/N.º
     025-12), SIGESAI, SACS 122-2016.
   - Confirmar alícuotas IVA (16/8/0/adicional), IGTF (0% y 3%) y retención IVA
     (75/100).
2. **Modalidad inicial de facturación** — la fundación NO emite fiscal; validar
   que la preparación del núcleo fiscal (LegalSource, TaxRuleVersion, series,
   lotes) no implique cumplimiento declarado sin homologación.
3. **Modelo de licenciamiento** — `specs/001-fundacion/license-foundation.md`
   - Firma asimétrica Ed25519, ciclo anual 1-abr/31-mar, modos de acceso,
     fecha confiable, no eliminación de datos.
4. **Conservación documental** — validar plazos (10 años facturación digital,
   SNAT/2024/000102) para auditoría y archivos.
5. **Retenciones ISLR (Decreto 1.808)** — confirmar que el modelo de reglas
   versionadas soporta concepto, sujeto, base, tarifa, sustraendo y UT.
6. **Privacidad** — confirmar que la autoridad central no almacena datos
   operativos del cliente y que el soporte remoto requiere autorización.

## Entregables de la revisión

- Firma/validación de la matriz normativa con fecha.
- Decisión sobre el estado de cada norma (vigente / derogada / requiere ajuste).
- Nota de aceptación o rechazo del riesgo de CVE `react-router` (solo modo RSC)
  si corresponde antes de producción.

## Registro

| Elemento | Revisado por | Fecha | Resultado |
|---|---|---|---|
| Matriz normativa | (pendiente) | | |
| Modalidad fiscal | (pendiente) | | |
| Licenciamiento | (pendiente) | | |
| Conservación | (pendiente) | | |
| Retenciones ISLR | (pendiente) | | |
| Privacidad | (pendiente) | | |
