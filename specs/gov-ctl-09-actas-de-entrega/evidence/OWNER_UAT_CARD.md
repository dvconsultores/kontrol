# OWNER UAT CARD · CTL-09 «Actas de entrega» (GOV-CTL-011)

```
MÓDULO: Gobierno · PROCESO: CTL-09 Actas de entrega de órganos y entidades
ESTADO: OWNER_UAT_READY (pendiente de su prueba; OWNER_ACCEPTED solo lo da usted)
MENÚ:   Gobierno › Actas de entrega (debajo de «Expedientes de cuenta»)
NORMA:  Normas para regular la entrega de los órganos y entidades de la Administración Pública (CGR), arts. 10 a 22

ROLES:
  - Levantar y suscribir el acta, registrar remisión y observaciones: gobierno_actas:view + gobierno_actas:manage.
  - Registrar la verificación de la UAI: gobierno_actas:verify, en OTRA cuenta de usuario. Ni quien suscribió, ni el
    funcionario saliente, ni el receptor pueden registrarla.

QUÉ ES Y QUÉ NO ES:
  KONTROL arma el acta a partir de la ocupación saliente (Ocupación de cargos), genera al corte los anexos que ya tiene
  (cuentas bancarias y expedientes de cuenta, cargos y ocupantes, índice del archivo con expedientes y actos) y deja resolver
  los demás con documentos adjuntos o con la constancia del art. 19 cuando falta la información. Al suscribir congela el
  contenido, calcula su huella y genera el PDF. NO calcula plazos en días hábiles (no hay calendario oficial) ni inventaría
  bienes, presupuesto o contratos: esos anexos se resuelven con documentos o constancia.

USE SOLO DATOS SINTÉTICOS.
```

## Pasos

1. **Requisito.** Debe existir una ocupación de cargo (Gobierno › Ocupación de cargos) del funcionario que entrega, y al
   menos otro funcionario que recibe.
2. **Crear el acta.** Abra Gobierno › Actas de entrega y pulse «Nueva acta». Elija la ocupación saliente, el receptor, la
   modalidad «Entrega por el saliente», motivo, fundamento y lugar. La fecha de corte viene con la fecha de hoy.
   - Esperado: la ficha «Acta AE-<año>-NNNN» en estado Borrador, con el saliente congelado (funcionario, cargo y unidad).
3. **Anexos.** En «Anexos», A11_1, A11_2 y A11_5 aparecen resueltos con contenido generado al corte; pulse «Ver contenido
   generado» para revisarlo. El aviso «Anexos obligatorios pendientes» lista A11_3 y A11_4.
4. **Resolver pendientes.** En A11_3 y A11_4 escriba una constancia (art. 19) y pulse «Guardar constancia», o adjunte un
   documento en «Documentos del acta» y márquelo en el anexo con «Guardar documentos».
   - Esperado: el aviso desaparece y «Suscribir acta» se habilita.
5. **Suscribir.** Indique la fecha de suscripción y pulse «Suscribir acta» (pide MFA).
   - Esperado: estado Suscrita, «Huella del acta» visible y botón «Descargar acta (PDF)».
6. **Remisión y observaciones.** Registre la remisión a la UAI (art. 21) y una observación (art. 22).
7. **Negativa: la verificación no la hace quien suscribe.** Con la misma cuenta (si tiene verify) intente «Registrar
   verificación».
   - Esperado: rechazo «La verificación no puede registrarla quien suscribió, el saliente o el receptor.».
8. **Verificación por la UAI.** Con OTRA cuenta que tenga gobierno_actas:verify, abra el acta y registre la verificación
   «Conforme» con número de informe y fundamento.
   - Esperado: estado Verificada, con la verificación visible.
9. **Integridad.** Pulse «Verificar integridad».
   - Esperado: «Resultado: Íntegra», con huella y PDF correctos.
10. **Teléfono.** Repita la consulta de la ficha en un teléfono o a 320 px: sin desplazamiento horizontal.

## Lo que queda fuera (no es un defecto de esta entrega)

- Plazos de entrega, remisión y verificación en días hábiles (DOC-03 bloqueado, sin calendario oficial).
- Anexos de bienes, presupuesto, plan operativo y contratos con datos propios: sus módulos no existen todavía en Gobierno.
