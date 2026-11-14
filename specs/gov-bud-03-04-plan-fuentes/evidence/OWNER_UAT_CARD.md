# OWNER UAT CARD · BUD-03 + BUD-04 «Plan operativo, metas y fuentes de financiamiento»

```
MÓDULO: Gobierno · PRESUPUESTO: BUD-03 plan operativo, objetivos, responsables y metas físicas + BUD-04 fuentes de financiamiento
MENÚ:   Gobierno · Presupuesto › Ejercicios presupuestarios › (abrir un ejercicio) › secciones «Plan operativo y metas» y
        «Fuentes de financiamiento»
ROLES:  gobierno_presupuesto:view (consultar), :manage (registrar y modificar en Borrador)
BASE:   LOPPM arts. 233, 239, 246, 247 · N31 LOPPP · D-GOV-02 = A/1/1/1
USE SOLO DATOS SINTÉTICOS. KONTROL no trae planes, fuentes ni códigos oficiales: los registra el ente.
```

## Antes de empezar

1. Hay un ejercicio en **Borrador**, con niveles y categorías (por ejemplo 01 «Sector salud» y 01.02 «Atención primaria»), y con dos PDF adjuntos en «Documentos del ejercicio». Si no existe, siga la tarjeta de BUD-01/02.
2. La **estructura organizativa (ORG-02)** del mismo año está VIGENTE y tiene unidades activas.

## Pasos

1. **Plan.** En «Plan operativo y metas», complete «Denominación del plan» y elija el «Documento del plan» → «Guardar plan».
2. **Objetivos.** Cree O1 y O2 con su descripción (botón «Crear objetivo»).
   - Negativa: un código repetido se rechaza.
3. **Responsables.** En la tabla «Unidades responsables y objetivos», en la fila 01 elija la unidad (se muestra «código · nombre») y el objetivo O1 → «Guardar vínculo de 01».
   - Solo se ofrecen las unidades activas de la estructura VIGENTE del mismo año.
4. **Negativa del objetivo.** Intente eliminar O1, que está vinculado: se rechaza.
5. **Meta física.** Categoría «01.02 · Atención primaria», descripción «Consultas atendidas», unidad «consulta», cantidad 1200.5, indicador «Consultas por mes» → «Crear meta».
   - Negativa: con cantidad 0 o con 5 decimales se rechaza.
6. **Fuente.** En «Fuentes de financiamiento», cree F01 «Ingresos propios» con su procedencia (al menos 10 caracteres). El documento es opcional y la vigencia, si no se indica, empieza el 1 de enero.
   - Negativa: F01 repetido se rechaza.
   - Negativa: una vigencia fuera del año del ejercicio se rechaza.
7. **Restricción.** En «Restricciones de F01», registre la descripción, el fundamento (p. ej. «Afectación legal, LOPPM art. 246») y la partida 401 → «Añadir restricción a F01».
   - Negativa: una partida que no existe, o que es de RECURSO, se rechaza.
8. **Recargar.** Recargue la página: todo sigue ahí.
9. **Historia.** En la Historia del ejercicio aparecen PLAN_REGISTRADO, OBJETIVO_CREADO, CATEGORIA_VINCULADA, META_CREADA, FUENTE_CREADA y RESTRICCION_AGREGADA. También quedan en la bitácora institucional (CTL-02).
10. **Fijar.** Apruebe el ejercicio (tarjeta de BUD-01/02, paso 7). Entonces:
    - desaparecen los controles de edición del plan y de las fuentes;
    - el fundamento incluye el plan y las fuentes en su fotografía.
11. **Teléfono.** A 390 y 320 px las dos secciones se leen sin desplazamiento horizontal.

## Fuera de alcance

- Créditos y montos, y el control de «créditos huérfanos», que llega con BUD-05.
- Disponibilidad, compromiso, causado y pagado.
- El avance físico de las metas (REP-02).
- Reportes: REPORTING es NOT_APPLICABLE en BUD-03 y BUD-04.
