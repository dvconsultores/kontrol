# OWNER UAT CARD · BUD-06 «Disponibilidad y certificación presupuestaria»

```
MÓDULO: Gobierno · PRESUPUESTO: BUD-06 disponibilidad en tiempo real y certificación de disponibilidad (GOV-BUD-009, GOV-BUD-010)
MENÚ:   Gobierno · Presupuesto › Ejercicios presupuestarios › (abrir un ejercicio APROBADO o RECONDUCIDO del año en curso) ›
        sección «Disponibilidad y certificaciones»
ROLES:  gobierno_presupuesto:view (consultar y descargar), gobierno_presupuesto:certify (emitir y anular; SENSITIVE, con MFA)
BASE:   LOPPM arts. 242, 248 y 250 · D-GOV-02 = A/1/1/1 · ORG-03 (competencia FIRMAR × PRESUPUESTO) · ORG-06
USE SOLO DATOS SINTÉTICOS. No es disponibilidad de caja (TRE-02), ni precompromiso (BUD-07), ni compromiso (BUD-08).
```

## Antes de empezar

1. Hay un ejercicio del **año en curso** aprobado, con al menos un crédito (tarjetas de BUD-01 a BUD-05).
2. En la estructura organizativa vigente del año existe un cargo VIGENTE con la competencia **FIRMAR en materia de PRESUPUESTO** (tarjeta de ORG-03).
3. Su usuario tiene `gobierno_presupuesto:certify`, que exige MFA.

## Pasos

1. **Disponibilidad.** Abra el ejercicio. En la «Tabla de disponibilidad» cada crédito muestra su categoría, unidad ejecutora, partida, fuente, crédito, certificado y disponible, con totales.
   - Pruebe los filtros por categoría, unidad, partida y fuente.
2. **Emitir.** En «Emitir certificación»:
   - elija el crédito (el texto muestra el disponible);
   - escriba el monto (p. ej. 300,00) y el concepto;
   - en expediente, elija uno de contratación (PROC-03) o escriba la referencia institucional;
   - elija el firmante (cargo · unidad) y pulse «Emitir certificación».

   Aparece «Certificación CDP-AAAA-NNNN emitida: saldo antes …, saldo después …».
3. **Efecto inmediato.** El disponible del crédito baja en el monto certificado.
4. **Documento.** En «Certificaciones emitidas», pulse «Descargar CDP-…».
   - El PDF muestra el identificador, el ente, el ejercicio, la fecha, el expediente, el concepto, la categoría, la unidad, la partida, la fuente, el monto, el saldo antes y después, el firmante y su cargo, el estado y la huella.
   - Es una constancia institucional, **no una firma electrónica**.
5. **Negativa: exceso.** Intente certificar más que el disponible. Se rechaza con un mensaje que indica el disponible y el monto solicitado, y no se crea nada.
6. **Anular.** Escriba el motivo (al menos 10 caracteres) y pulse «Anular CDP-…».
   - El disponible vuelve a subir.
   - La certificación queda como «Anulada: motivo»; no se borra.
7. **Historia.** En la Historia del ejercicio aparecen «Certificación de disponibilidad emitida» y «… anulada». También quedan en la bitácora institucional (CTL-02).
8. **Sin capacidad.** Un usuario con solo `view` consulta y descarga, pero no ve «Emitir certificación» ni «Anular».
9. **Teléfono.** A 390 y 320 px la sección se usa sin desplazamiento horizontal de la página; las tablas se desplazan dentro de su región.

## Fuera de alcance

- Precompromiso o reserva (BUD-07), compromiso (BUD-08), modificaciones (BUD-10) y ledger (BUD-11).
- Disponibilidad de caja (TRE-02).
- Firma electrónica (DOC-05).
- Reportes: REPORTING es NOT_APPLICABLE.
