# Tarjeta de prueba de la dueña

**Dirección:** http://127.0.0.1:5173, en el equipo de P2. **Acceso:** fichero local protegido, nunca en Git. **Datos:** sintéticos.

**Límites conocidos:** `UAT_DATABASE_ENGINE = PostgreSQL`, `UAT_SCHEMA_SOURCE = Alembic`, con Vite, no el empaquetado de producción. Al primer ingreso pide dar de alta la verificación en dos pasos. El menú también muestra Gobierno por la licencia de prueba; no forma parte de esta tarjeta. Solo es accesible desde ese equipo. El bloqueo de pago a proveedores no aprobados afectará a los proveedores existentes cuando se despliegue: decisión pendiente.

## Terceros (Maestros → Terceros)

1. Pulse «Nuevo tercero», cree un proveedor con RIF y marque el rol Proveedor. Debe llevarle a su ficha sin pedir confirmación.
2. Edite la razón social y guarde.
3. Agregue una dirección y un contacto, y agregue el rol Cliente.
4. Intente registrar un pago en Compras → CxP. Debe rechazarlo: «El proveedor no está aprobado para recibir pagos.»
5. Pulse «Aprobar proveedor». Debe decir que falta una cuenta bancaria verificada.
6. Agregue una cuenta, escriba la evidencia, verifíquela y apruebe. El pago ya debe registrarse.
7. Edite la cuenta. El proveedor vuelve a «Pendiente» y el historial lo muestra.

## Importaciones (Compras → Importaciones)

Necesita un proveedor y una orden de compra aprobada de ese proveedor.

1. Pulse «Nueva importación», ponga un código y elija el proveedor.
2. Intente vincular la orden. Debe decir qué falta negociar.
3. Complete INCOTERM, condiciones de pago y de entrega, guarde y vincule la orden. El estado pasa a «Orden vinculada».
4. Pulse «Confirmar documentación». Debe decir qué documentos faltan.
5. En cada documento: escriba la referencia, pulse «Recibir», adjunte un PDF y pulse «Validar». Necesita un tipo documental que admita PDF, en Documentos → Tipos documentales.
6. Pulse «Confirmar documentación». El estado pasa a «Documentación completa» y el historial lo muestra.

### Continuar la importación

Antes de pagar, apruebe al proveedor en Maestros → Terceros (RIF y cuenta bancaria verificada). El expediente enlaza a su ficha si falta.

7. En «Finanzas», elija «Anticipo», escriba un monto y pulse «Registrar». El anticipo aparece en la lista, y se aprueba o ejecuta en Cuentas por pagar.
8. Intente registrar un pago con un proveedor sin aprobar. Debe rechazarlo y ofrecer «Ver proveedor».
9. En «Seguimiento», designe un agente, escriba origen y destino y pulse «Guardar seguimiento». El resumen muestra al agente.
10. Registre el hito «Salida» con su fecha. Aparece en la línea de tiempo y rellena la salida real.
11. En «Correcciones», cree un faltante. Si estaba en «Documentación completa», el expediente vuelve a «Orden vinculada» y no deja confirmar hasta resolverlo.
12. Escriba la resolución, pulse «Resolver» y vuelva a pulsar «Confirmar documentación».
13. En «Resumen», pulse «Confirmar despacho». El estado pasa a «Despachada», desaparece «Cancelar importación» y el historial muestra «Despacho confirmado».
14. Reduzca la ventana al ancho de un teléfono y recargue: el menú arranca plegado y el expediente se lee sin desplazamiento lateral.

### Recibir y ubicar

Necesita un almacén con una ubicación activa, en Organización.

15. Tras despachar, en «Recepción» escriba un código, elija el almacén y pulse «Crear recepción». No pide la orden: es la del expediente. El resumen pasa a «Esperando arribo».
16. En «Arribo» indique los bultos y confirme. Pasa a «En recepción».
17. Pulse «Abrir recepción». Registre la línea y pulse confirmar, enviar a calidad, conforme y aceptar. Pulse «Volver al expediente».
18. Pulse «Gestionar incidencias», registre un daño, escálelo y trátelo. Vuelva: la incidencia aparece en «Diferencias e inventario» y el expediente dice «Por confirmar inventario».
19. Pulse «Confirmar inventario», registre el conteo y confirme. Vuelva: dice «Por ubicar».
20. En «Ubicación», elija el destino y pulse «Ubicar». Dice «Recibida y ubicada», con la ubicación y la cantidad.

**Límite:** un put-away hecho desde el menú de Inventario, sin pasar por el expediente, no se le atribuye.

### Costos de importación: gastos

Necesita una tasa en Tesorería para la moneda del gasto, con fecha igual o anterior a la del gasto.

21. En «Costos de importación», registre un gasto en una moneda sin tasa. Debe rechazarlo y ofrecer «Registrar tasa en Tesorería»; nunca asume tasa 1.
22. Registre la tasa y repita. El gasto muestra la moneda, la tasa, su fuente y fecha, y el equivalente en moneda funcional. Ejemplo: `1.250,50 × 36,125 = 45.174,31`.
23. Pulse «Anular gasto», escriba el motivo y confirme. Sigue en la lista como «Anulado» con su motivo, deja de sumar y el historial lo muestra.
24. Compruebe «Capas de costo de esta importación»: el costo aparece en la moneda de la orden.

**En teléfono:** cada acción deja una notificación que se cierra a mano con su ✕; solo se ve la más reciente.

### Costos de importación: repartir y aplicar al costo (landed cost)

Necesita un expediente recibido, con capas de costo, y un gasto registrado.

25. En la tarjeta del gasto, en «Clasificación del costo», elija «Capitalizable» y pulse «Guardar clasificación». Sin esa clasificación, la vista previa explica que no se puede aplicar.
26. En «Criterio de reparto» elija «Por valor», «Por cantidad» o «Manual». No hay criterio marcado de antemano. En «Manual», escriba el importe de cada producto.
27. Pulse «Generar vista previa». Ve «Vista previa: aún no se ha aplicado nada», la tabla por producto (base, participación, importe asignado, costo actual y costo resultante) y «El reparto cuadra exactamente». Si en «Manual» no cuadra, muestra la diferencia y no deja aplicar.
28. Pulse «Aplicar costo», revise el resumen y pulse «Confirmar aplicación». El costo efectivo de la capa y su «Valor en inventario» suben; Inventario → Valorización también lo refleja.
29. Intente aplicar de nuevo el mismo gasto: el sistema lo impide.
30. En «Historial de aplicación», pulse «Revertir aplicación», escriba el motivo y confirme. Queda «Revertido», el valor vuelve exactamente al anterior y el historial conserva ambas operaciones.
31. Si alguna mercancía de ese expediente ya salió del inventario, la aplicación y la reversión se bloquean y lo explican: el costo no se aplica de forma retroactiva.

### Reporte formal de diferencias

Necesita una recepción del expediente con alguna diferencia: una incidencia registrada (paso 18) o una cantidad que no coincide.

32. En «Diferencias e inventario», busque «Reporte formal de diferencias · REC-…» de esa recepción. Una recepción sin diferencias dice «Sin diferencias» y no deja emitir.
33. Con diferencias, dice «Diferencias detectadas sin reporte». Pulse «Emitir reporte formal». Ve una referencia del tipo `DIF-000001-R1` (el número es correlativo por empresa), «Revisión 1», «Emitido por» con su nombre de usuario y el estado «Reporte emitido».
34. Pulse «Descargar PDF»: se descarga un PDF con esa referencia en el nombre. Ábralo: trae la cabecera del expediente, las líneas con diferencia, las incidencias con su tratamiento y las evidencias.
35. Pulse «Imprimir»: el PDF se abre en otra pestaña, listo para imprimir.
36. Registre otra incidencia en esa recepción y vuelva al expediente: dice «Nueva revisión disponible». Pulse «Emitir nueva revisión». Sale `…-R2` con el mismo número. La R1 no cambia.
37. En «Historial de revisiones» están R2 y R1, cada una con su botón de descarga.
38. En Compras → Recepciones, abra esa recepción: «Reporte formal de diferencias» lista sus reportes, permite descargarlos y abre el expediente con «Abrir expediente IMP-…».

**Límites:** la referencia es interna, no un folio legal. El reporte no se aprueba, no se firma y no se envía al proveedor. Un usuario sin permiso de crear en Compras lo consulta y lo descarga, pero no lo emite.

**Aún no disponible:** reubicar por error y validación física de la ubicación (siguiente ciclo); clasificación y zonas de almacén, pendientes de validar por el sponsor. Comparación completa con el documento del sponsor: pendiente.
