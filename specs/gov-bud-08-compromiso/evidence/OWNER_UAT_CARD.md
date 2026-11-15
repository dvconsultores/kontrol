# OWNER UAT CARD · BUD-08 «Compromiso presupuestario»

```
MÓDULO: Gobierno · PRESUPUESTO: BUD-08 compromiso presupuestario (GOV-BUD-012)
MENÚ:   Gobierno · Presupuesto › Ejercicios presupuestarios › (abrir un ejercicio APROBADO o RECONDUCIDO del año en curso) › sección «Compromisos»
ROLES:  gobierno_presupuesto:view (consultar y descargar); gobierno_presupuesto:commit (registrar y anular; SENSITIVE, con MFA)
BASE:   LOPPM arts. 242 y 248 · D-GOV-02 = A · ARCH §8 (quien certifica no compromete) · ORG-03 (COMPROMETER × PRESUPUESTO, límite por operación) · ORG-06
USE SOLO DATOS SINTÉTICOS. No es causado (BUD-09), ni modificación (BUD-10), ni precompromiso (BUD-07), ni caja (TRE-02).
```

## Antes de empezar

1. Necesita un ejercicio del año en curso aprobado. Debe tener al menos una CDP vigente, emitida por **otro usuario** con `gobierno_presupuesto:certify` (tarjeta de BUD-06).
2. En la estructura vigente debe existir un cargo con la competencia **COMPROMETER en materia de PRESUPUESTO** (ORG-03). Puede ser sin límite o con un límite en la moneda del ejercicio.
3. El documento de soporte (orden, contrato o acto) debe estar vinculado al ejercicio en «Adjuntos».
4. Su usuario necesita `gobierno_presupuesto:commit`, que exige MFA. No debe ser quien emitió la CDP.

## Pasos

1. **Elegir la CDP.** En «Compromisos», elija la CDP en «Certificación de la imputación 1». Aparecen su crédito y los montos certificado, consumido y remanente.
2. **Compromiso parcial.** Escriba un monto menor que el remanente, el concepto, la autoridad (cargo y límite) y el soporte. Verá el expediente, heredado de la CDP, y el total. Pulse «Registrar compromiso». Aparece «Compromiso CP-AAAA-NNNN registrado por …».
3. **Sin doble descuento.** En la «Tabla de disponibilidad», el disponible del crédito **no cambia**: el monto pasa de certificado a comprometido (columna «Comprometido»). La CDP queda como «Vigente · Parcialmente consumida».
4. **Segundo compromiso.** Comprometa otra parte del remanente. Pruebe también «Añadir imputación» para usar varias CDP en un mismo compromiso.
5. **Negativa: exceso.** Intente comprometer más que el remanente. Se rechaza y no se crea nada.
6. **Negativa: CDP en uso.** Una CDP con compromisos vigentes no muestra «Anular» y muestra «Con compromisos vigentes». Si se intenta anular, se rechaza.
7. **Negativa: quien certifica no compromete.** Si el usuario que emitió la CDP intenta comprometerla, se bloquea y el intento queda en la bitácora.
8. **Negativa: límite.** Con un cargo cuyo límite sea menor que el total, o que esté en otra moneda, se bloquea. No hay conversión.
9. **Documento.** Pulse «Descargar CP-…». El PDF muestra:
   - código, ente, ejercicio, fecha, expediente y concepto;
   - las imputaciones (CDP, categoría, unidad, partida, fuente y monto);
   - total, moneda, autoridad y límite, soporte y su huella, y la huella del compromiso.

   No es firma electrónica.
10. **Anular.** Escriba el motivo (al menos 10 caracteres) y pulse «Anular CP-…». El compromiso queda «Anulado: motivo» y el remanente vuelve a la CDP.
11. **Historia.** La Historia del ejercicio muestra «Compromiso presupuestario registrado» y «… anulado». También quedan en la bitácora (CTL-02).
12. **Teléfono.** A 390 y 320 px la página no se desplaza horizontalmente; las tablas se desplazan dentro de su región.

## Observación para la dueña

**OBS-BUD08-VES-VED.**
- ORG-03 admite límites de cargo en VES, USD o EUR.
- Si el ente opera en VED, un cargo **con límite** no puede compararse sin conversión, y el compromiso se bloquea (falla segura).
- Los cargos **sin límite** funcionan normalmente.
- Igualar VES y VED es una decisión monetaria que corresponde a la dueña.

## Fuera de alcance

- Precompromiso (BUD-07), causado (BUD-09), modificaciones (BUD-10) y ledger (BUD-11).
- Maestro de proveedores o beneficiarios.
- Reverso parcial.
- Caja (TRE-02).
- Firma electrónica (DOC-05).
- REPORTING es NOT_APPLICABLE.
