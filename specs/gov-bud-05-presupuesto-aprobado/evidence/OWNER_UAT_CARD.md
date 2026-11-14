# OWNER UAT CARD · BUD-05 «Presupuesto aprobado: ingresos, créditos, existencias del Tesoro y cuadre»

```
MÓDULO: Gobierno · PRESUPUESTO: BUD-05 presupuesto aprobado con su acto (alcance v1 de D-GOV-02 = A)
MENÚ:   Gobierno · Presupuesto › Ejercicios presupuestarios › (abrir un ejercicio) › sección «Presupuesto aprobado»
ROLES:  gobierno_presupuesto:view (consultar), :manage (registrar en Borrador), :approve (aprobar, tarjeta de BUD-01/02)
BASE:   LOPPM arts. 229, 238, 239, 240, 242, 246 · D-GOV-02 = A/1/1/1 · OD-BUD05-01 = A · OD-BUD05-02
USE SOLO DATOS SINTÉTICOS. KONTROL no trae partidas, fuentes ni montos oficiales: los transcribe el ente desde su ordenanza.
```

## Antes de empezar

1. Hay un ejercicio en **Borrador** con:
   - las categorías 01 y su hija 01.02;
   - un clasificador **con su documento de procedencia**, con las partidas RECURSO 301, EGRESO 401, su hija 401.01, y EGRESO 402;
   - dos o más PDF en «Documentos del ejercicio».

   Si no existe, siga la tarjeta de BUD-01/02.
2. En «Fuentes de financiamiento» (tarjeta de BUD-03/04):
   - F01 tiene la restricción a la partida 401;
   - F02 no tiene restricciones.

## Pasos

1. **Ingreso.** En «Presupuesto de ingresos», elija «301 · …», escriba el monto 1.000.000,00 y pulse «Registrar ingreso».
   - Negativa: la misma partida otra vez se rechaza.
2. **Crédito.** En «Créditos presupuestarios»:
   - elija la categoría «01.02 · …» y la fuente «F01 · …»;
   - compruebe el aviso «La fuente F01 solo financia las partidas 401» y que la partida 402 **no** aparece;
   - elija «401.01 · …», escriba 1.200.000,00 y pulse «Registrar crédito».
3. **Cuadre.** La sección «Cuadre (LOPPM art. 240)» dice **«No cuadra»**: los créditos superan los ingresos.
4. **Edición.** En la fila del crédito, escriba 900.000,00 y pulse «Guardar crédito 01.02 · 401.01 · F01». Ahora el cuadre dice **«El presupuesto cuadra»**.
5. **Existencias del Tesoro (opcional).** Escriba el monto 100.000,00, la fecha de corte de hoy y la certificación (un PDF del ejercicio), y pulse «Declarar existencias». El cuadre suma la **mitad** (50.000,00).
6. **Fuente libre.** Registre un crédito 01.02 × 402 × F02. Se acepta porque F02 no tiene restricciones.
7. **Recargar.** Recargue la página: todo sigue ahí.
8. **Aprobar.** Apruebe el ejercicio (tarjeta de BUD-01/02, paso 7).
   - Si los créditos superan los ingresos más la mitad de las existencias, aparece el error del cuadre (LOPPM 240) y no se aprueba.
   - Si cuadra:
     - desaparecen los controles de la sección;
     - aparece «El presupuesto aprobado está fijado y ya no se modifica.»;
     - el fundamento tiene huella.
9. **Historia.** En la Historia del ejercicio aparecen «Ingreso estimado registrado», «Crédito registrado», «Crédito modificado» y «Existencias del Tesoro declaradas». También quedan en la bitácora institucional (CTL-02).
10. **Teléfono.** A 390 y 320 px la sección se lee sin desplazamiento horizontal de la página.

## Fuera de alcance

- La formulación: escenarios, supuestos, techos, y anteproyecto y proyecto como flujo (GOV-BUD-006 y parte de 007). Es LATER_PHASE por D-GOV-02 A.
- Disponibilidad y certificación (BUD-06), compromiso, causado y pagado.
- Modificaciones presupuestarias (BUD-10).
- Reportes: REPORTING es NOT_APPLICABLE en BUD-05.
