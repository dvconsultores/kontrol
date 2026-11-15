# CNT-01 · Ficha de pantalla

## Rutas

| Pantalla | Ruta | Menú |
|---|---|---|
| Lista | `/gobierno/contratos` | Gobierno · Contratos › **Contratos y órdenes** |
| Ficha y borrador | `/gobierno/contratos/:contratoId` | Desde la lista o desde el expediente |
| Origen | Gobierno · Contrataciones › Expedientes › expediente › sección **Recomendación y decisión** | Panel «Contrato u orden» con el botón **Crear contrato u orden**, o el enlace **Ver contrato u orden** si ya existe |

## Lista «Contratos y órdenes»

- **Filtros:** Estado (Borrador o Formalizado) y Tipo (Contrato, Orden de compra u Orden de servicio).
- **Columnas:** Identificación (enlace), Tipo, Estado, Expediente, Decisión, Contratista, Monto y Plazo.
- **Sin registros:** «Sin contratos ni órdenes. Cree uno desde la decisión ADJUDICADA de un expediente de contratación.»

## Ficha

1. **Origen (solo lectura).** Muestra estos datos y no deja editarlos:
   - expediente (enlace) y adjudicación (DEC-NN, fecha y acto);
   - oferta (R-NNNN);
   - contratista, su documento y representante;
   - objeto, monto y moneda.

   Si la adjudicación dejó de estar vigente, aparece el aviso «La adjudicación de origen ya no está vigente».
2. **Datos del instrumento (borrador).**
   - Campos: tipo, inicio y fin del plazo, referencia del instrumento, descripción complementaria (no sustituye el objeto) e instrumento firmado (documento vinculado al expediente).
   - Botón «Guardar datos». Mientras guarda, los botones se desactivan y al terminar aparece «Cambios guardados.».
3. **Cobertura presupuestaria.**
   - Tabla de CDP elegibles (VIGENTES, en la moneda del contrato y con saldo libre): certificación, ejercicio, partida, fuente, saldo libre y monto asignado.
   - Resumen: «Asignado / Falta», y «Cobertura completa» cuando corresponde.
   - Nota: vincular no consume la CDP (BUD-08).
4. **Garantías.** Casillas de las garantías REGISTRADAS de la oferta adjudicada. Si no hay ninguna, se dice que puede formalizarse sin ellas si la institución no las exige.
5. **Formalización.**
   - Lista «Falta para formalizar».
   - «Cargo firmante», con los cargos que tienen hoy FIRMAR × CONTRATACIONES.
   - Panel «Control del límite del firmante»: cargo, límite y resultado (Dentro del límite, Sin límite, Excede el límite o No comparable por moneda), con el mensaje del backend.
   - «Formalizar» abre una confirmación. Si hay error, el mensaje del backend aparece en un `role="alert"`; si todo va bien, «Formalizado: CT-AAAA-NNNN».
6. **Instrumento formalizado.**
   - Datos: código, tipo, plazo, referencia, documento (con huella abreviada y enlace «Ver documento»), firmante, fecha de formalización y huella del contrato.
   - Cobertura y garantías congeladas.
   - Nota: las adendas pertenecen a CNT-02.

## Reglas visuales y de accesibilidad

- No se muestran UUID.
- Una columna en móvil y dos desde `sm`.
- Las tablas con desplazamiento son una `region` enfocable (`tabIndex=0`) con nombre accesible.
- Los errores van en `role="alert"` y las confirmaciones en `role="status"`.
- Sin desplazamiento horizontal de página a 390 ni a 320 px. Axe sin violaciones serias ni críticas.
