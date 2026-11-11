# FUENTES · CTL-09 (GOV-CTL-011)

| Id | Fuente | Uso |
|---|---|---|
| IR §7.11 | GOV-CTL-011 (P0): «Gestionar actas de entrega por cambio de responsable/autoridad con corte de bancos, bienes, cuentas, contratos y expedientes.» Fuentes: N34 y N21 | Requisito sponsor |
| N34 | **Normas para Regular la Entrega de los Órganos y Entidades de la Administración Pública y de sus Respectivas Oficinas o Dependencias**, G.O. 39.229 (28-07-2009). Texto oficial leído (PDF con texto de la CEBM) | Norma rectora |
| N21 | Res. CGR 01-00-000167, art. 14: cuando el cuentadante cesa antes del cierre, se hace corte de la cuenta a la fecha del cese y se anexa al acta de entrega | Enlace con CTL-05 |

## N34: artículos que fijan el diseño

- **Arts. 3 y 4: obligación de entregar.** Quien administra, maneja o custodia recursos entrega al cesar. Se hace mediante acta, en la toma de posesión del sustituto o dentro de los 3 días hábiles siguientes. Sin sustituto, se entrega a quien designe la máxima autoridad.
- **Art. 6: responsable de la entrega.** En el órgano o entidad es su presidente o máxima autoridad; en las oficinas o dependencias, sus jefes.
- **Arts. 8 y 9: autoría del acta.**
  - La elabora y suscribe el **saliente** (art. 8).
  - Si el saliente no la hace, el entrante (o el designado) levanta un acta detallada **con dos testigos y el auditor interno**, y remite copia certificada a la UAI (art. 9).
- **Art. 10: contenido del acta.** Lugar y fecha; órgano o dependencia; quién entrega y quién recibe; motivo y fundamento legal; relación de anexos; suscripción.
- **Art. 11: anexos obligatorios.**
  1. Estado de cuentas (situación presupuestaria, financiera y patrimonial, cuando sea aplicable).
  2. Número de cargos.
  3. Inventario de bienes muebles e inmuebles.
  4. Situación de la ejecución del plan operativo.
  5. Índice general del archivo.
  6. Cualquier otra información.
- **Art. 17: anexos adicionales de una Alcaldía o hacienda municipal.**
  1. Situación del Tesoro.
  2. Ejecución del presupuesto de ingresos y egresos y derechos pendientes.
  3. Situación de las cuentas.
  4. Inventario de terrenos ejidos y propios.
  5. Ingresos por venta de terrenos.
- **Art. 18: corte.** Los anexos llevan fecha de corte al cese. La exactitud es responsabilidad de quien entrega.
- **Art. 19: información inexistente.** Si el acta o sus anexos no tienen la información requerida, **se deja constancia de tal condición y de los motivos**.
- **Art. 20: observaciones en el acta.** Se especifican los errores, deficiencias u omisiones advertidos.
- **Art. 21: copias.** Original y 3 copias certificadas; una va a la UAI dentro de los 5 días hábiles.
- **Art. 22: observaciones del receptor.** Las informa por escrito al órgano de control dentro de los 120 días hábiles.
- **Art. 23: verificación.** La UAI verifica la sinceridad y exactitud del acta, y el resultado consta en un informe.

## Conclusión de la compuerta

**`MATERIAL_BLOCKER_FOUND = 0`.**

- **Dominios ausentes:** bienes, plan operativo, presupuesto y contratos no existen en Gobierno. Su anexo se cubre con **documento** o con la **constancia del art. 19**, que es la vía que da la propia norma. No es un producto reducido falso.
- **Lo que KONTROL genera con corte al cese:**
  - cuentas bancarias (TRE-01);
  - expedientes de cuenta (CTL-05);
  - cargos y ocupación (ORG-03 y ORG-04);
  - índice del archivo: expedientes de contratación (PROC-03), actos (DOC-02) y expedientes de cuenta.
- **Plazos en días hábiles (arts. 4, 21 y 22):** dependen de un calendario oficial que no existe (DOC-03 está BLOCKED). KONTROL registra las fechas y no calcula vencimientos hábiles.
