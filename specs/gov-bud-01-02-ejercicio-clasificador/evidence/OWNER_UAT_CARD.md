# OWNER UAT CARD · BUD-01 + BUD-02 «Ejercicios presupuestarios»

```
MÓDULO: Gobierno · PRESUPUESTO: BUD-01 ejercicio presupuestario + BUD-02 clasificador versionado
MENÚ:   Gobierno · Presupuesto › Ejercicios presupuestarios
ROLES:  gobierno_presupuesto:view (consultar), :manage (crear y configurar), :approve (aprobar, reconducir, precompromiso; MFA),
        :close (cerrar; MFA)
BASE:   LOPPM arts. 229, 234-236, 239, 248, 250 · D-GOV-02 = A/1/1/1 (aprobado + ejecución; clasificador del ente; niveles
        configurables; precompromiso apagado por defecto)
USE SOLO DATOS SINTÉTICOS. El clasificador lo registra el ente: KONTROL no trae códigos ONAPRE.
```

## Pasos

1. **Crear.** «Nuevo ejercicio»: Año 2027 → «Crear ejercicio».
   - Esperado: estado Borrador, moneda funcional de la empresa y precompromiso «No activo».
   - Negativa: el mismo año otra vez da «Ya existe el ejercicio de ese año».
2. **Niveles.** «Nivel 1» = Sector → «Añadir nivel» → «Nivel 2» = Programa → «Guardar niveles».
3. **Categorías.** Nivel 1, código 01, «Sector salud» → «Agregar categoría». Luego Nivel 2 con superior 01, código 02 → aparece «01.02».
   - Negativa: el código «a b» se rechaza con su mensaje.
   - Negativa: una categoría con hijos no se puede eliminar.
4. **Documentos.** En «Documentos del ejercicio», adjunte dos PDF: la procedencia del clasificador y la ordenanza.
5. **Clasificador.**
   - Registre Edición, Procedencia y Documento de procedencia → «Guardar clasificador».
   - Importe un CSV con la cabecera `tipo,codigo,denominacion,nivel,codigo_padre,vigente_desde,vigente_hasta` (por ejemplo RECURSO 301; EGRESO 401; EGRESO 401.01 con padre 401).
   - Negativa: un CSV con una fila mala no importa nada y señala la fila.
6. **Pendiente para fijar.** La lista desaparece cuando hay niveles, categorías, clasificador con documento y partidas de recursos y egresos.
7. **Aprobar** (con MFA). «Ordenanza de presupuesto sancionada», Referencia, Fecha de sanción y Documento → «Aprobar ejercicio».
   - Esperado: «El ejercicio está fijado…», el fundamento con su huella y desaparecen los controles de edición.
8. **Historia.** Cada paso aparece en la Historia y en la bitácora institucional (CTL-02).
9. **Reconducción** (opcional). En un ejercicio del año en curso en Borrador, «Reconducción del presupuesto anterior» con fecha de publicación ≥ 16-dic del año anterior.
   - Negativa: en un año futuro se rechaza (LOPPM art. 234).
10. **Cierre.** «Cerrar ejercicio» solo procede después del 31-dic del año: en el año en curso se rechaza (LOPPM art. 248).
11. **Precompromiso.** Activarlo con fecha y motivo: queda en la historia y no crea reservas.
12. **Teléfono.** A 390 y 320 px la página se lee sin desplazamiento horizontal.

## Fuera de alcance

- Formulación (D02-A).
- Créditos y montos.
- Disponibilidad, compromiso, causado y pagado.
- Modificaciones.
- Formularios ONAPRE.
- La sanción tardía de un reconducido (RECONDUCIDO → APROBADO), que va a BUD-05.
- La exportación del clasificador (BUD-02 REPORTS): pendiente de decisión.
