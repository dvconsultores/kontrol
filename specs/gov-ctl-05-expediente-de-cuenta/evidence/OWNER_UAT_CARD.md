# OWNER UAT CARD · CTL-05 «Expedientes de cuenta» (GOV-CTL-006, GOV-CTL-007)

```
MÓDULO: Gobierno · PROCESO: CTL-05 Expediente de cuenta y reportes de rendición
ESTADO: OWNER_UAT_READY (pendiente de su prueba; OWNER_ACCEPTED solo lo da usted)
MENÚ:   Gobierno › Expedientes de cuenta (debajo de «Paquetes de auditoría»)
NORMA:  Resolución CGR 01-00-000167 (G.O. 40.492): formación, participación, rendición, examen y calificación de las cuentas

ROLES:
  - Formar la cuenta: gobierno_rendicion:view + gobierno_rendicion:form (el administrador «con todo» las tiene).
  - Registrar la calificación y el fenecimiento: gobierno_rendicion:qualify, en OTRA cuenta de usuario. Ni quien formó la
    cuenta ni el funcionario cuentadante pueden registrarla (el examen es de un órgano de control distinto).

QUÉ ES Y QUÉ NO ES:
  KONTROL organiza los soportes de la cuenta de un período (hechos reales de Gobierno: actos, ocupaciones, notificaciones,
  muestras, hallazgos y sus documentos), los enumera, congela el corte y genera el reporte de rendición con cifras
  reproducibles. La CALIFICACIÓN (conforme u objetada) la emite el órgano de control fiscal: KONTROL solo la REGISTRA, nunca la
  calcula. Sin montos: Presupuesto, Pagos y Contabilidad aún no existen en Gobierno.

USE SOLO DATOS SINTÉTICOS.
```

## Pasos

1. **Crear el expediente.** Abra Gobierno › Expedientes de cuenta y pulse «Nuevo expediente».
2. **Período y responsable.** Indique denominación, período, fecha de corte y responsable. El responsable sale de las ocupaciones de cargo (ORG-04). Pulse «Crear expediente».
   - Esperado: la ficha en estado «En formación», con el responsable congelado (funcionario, cargo, unidad y figura).
3. **Hechos disponibles.** La sección «Hechos disponibles del período» lista los hechos reales del ente dentro del corte. Puede filtrarlos por proceso y por texto, y la lista va paginada.
4. **Formar el índice.** Pulse «Incorporar» en dos o más hechos.
   - En «Índice de piezas» aparecen numerados por fecha, con referencia, proceso, usuario y número de soportes.
   - Una pieza se puede «Retirar» mientras la cuenta esté en formación.
   - Con «Editar cabecera» puede corregir los datos de la cuenta.
5. **Abrir las fuentes.** Cada pieza tiene «Ver en la bitácora» y, cuando existe, «Abrir fuente», que abre el acto, la ocupación, el hallazgo u otra fuente.
6. **Reporte.** «Reporte de rendición» muestra el aviso «Reporte provisional».
   - Cada cifra indica fuente, filtro, período, conjunto, regla y resultado.
   - Hay una fila por proceso y otras para los soportes y los hallazgos asociados.
7. **Cerrar (formar).** Pulse «Formar la cuenta».
   - Esperado: estado «Formada» y «Corte congelado el … · huella …».
   - Desaparecen «Hechos disponibles» y la opción de retirar piezas.
8. **Reabrir en solo lectura.** Salga y vuelva a abrir la ficha desde el listado: todo sigue igual y ya no se puede editar.
9. **El corte no cambia.** Registre en Gobierno un hecho nuevo, por ejemplo un funcionario, y vuelva a la ficha. El índice y la huella no cambian. Pulse «Verificar integridad».
   - Esperado: «Válido · snapshot: OK · informe: OK».
10. **Exportar.** Use «Descargar PDF», el informe guardado al formar, y «Descargar índice (CSV)».
11. **Rendición y calificación.**
    1. Registre la participación con fecha y oficio. Verá el plazo de 90 días y «En plazo» o «Fuera de plazo».
    2. Con la cuenta calificadora, registre la calificación del órgano de control (conforme u objetada, informe definitivo, órgano y fundamento) y después el fenecimiento (auto).
    3. Si lo intenta con la misma cuenta que formó el expediente, verá «quien registra no puede ser quien formó la cuenta».
12. **Subsanación (opcional).** Sobre una cuenta formada o participada, use «Crear nueva versión (subsanación)» con un motivo.
    - Esperado: nace la versión 2 en formación con las mismas piezas, y la 1 queda «Sustituida» e intacta.
13. **Teléfono.** A 390 px, el listado y la ficha se leen sin desplazamiento horizontal.

## Qué decirnos

- ¿El reporte de rendición contiene lo que el órgano de control le pediría en su cuenta?
- ¿Falta algún tipo de soporte que espera ver como pieza?
